from contextlib import asynccontextmanager
from datetime import date
from decimal import Decimal
from hashlib import pbkdf2_hmac
from pathlib import Path
from secrets import token_urlsafe

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, engine, get_db
from app.domain import Account, Card, SessionToken, Transaction, User

STATIC_DIR = Path(__file__).parent / "static"
CATEGORIES = [
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Health",
    "Entertainment",
    "Education",
    "Salary",
    "Other",
]


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=100)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: str = "Bank"
    balance: Decimal = 0


class CardIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    card_type: str = "Debit"
    last_four: str = Field(pattern=r"^\d{4}$")
    account_id: int | None = None
    limit_amount: Decimal = 0


class TransactionIn(BaseModel):
    kind: str = Field(pattern=r"^(expense|income|transfer)$")
    description: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0)
    category: str = "Other"
    payment_mode: str = "Cash"
    account_id: int | None = None
    to_account_id: int | None = None
    transacted_on: date
    notes: str = ""


class PreferencesIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    currency: str = Field(min_length=3, max_length=3)
    monthly_budget: Decimal = Field(ge=0)
    onboarded: bool = True


class NaturalLanguageIn(BaseModel):
    text: str = Field(min_length=3, max_length=300)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=500)


def hash_password(password: str, salt: str | None = None) -> str:
    actual_salt = salt or token_urlsafe(16)
    digest = pbkdf2_hmac(
        "sha256", password.encode(), actual_salt.encode(), 200_000
    ).hex()
    return f"{actual_salt}${digest}"


def require_user(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    token = db.get(SessionToken, authorization.removeprefix("Bearer "))
    user = db.get(User, token.user_id) if token else None
    if not user:
        raise HTTPException(401, "Invalid session")
    return user


def serialize(row) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}


def apply_balance(db: Session, item: Transaction, reverse: bool = False) -> None:
    sign = Decimal(-1) if reverse else Decimal(1)
    source = db.get(Account, item.account_id) if item.account_id else None
    target = db.get(Account, item.to_account_id) if item.to_account_id else None
    if source:
        source.balance += sign * (
            item.amount if item.kind == "income" else -item.amount
        )
    if target and item.kind == "transfer":
        target.balance += sign * item.amount


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=get_settings().app_name, version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "features": "full"}


@app.post("/api/auth/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(User).where(User.email == data.email.lower())):
        raise HTTPException(409, "Email already registered")
    user = User(
        name=data.name.strip(),
        email=data.email.lower(),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.flush()
    account = Account(user_id=user.id, name="Cash", kind="Cash", balance=0)
    token = SessionToken(token=token_urlsafe(40), user_id=user.id)
    db.add_all([account, token])
    db.commit()
    return {"token": token.token, "user": serialize(user)}


@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == data.email.lower()))
    if not user:
        raise HTTPException(401, "Incorrect email or password")
    salt = user.password_hash.split("$", 1)[0]
    if hash_password(data.password, salt) != user.password_hash:
        raise HTTPException(401, "Incorrect email or password")
    token = SessionToken(token=token_urlsafe(40), user_id=user.id)
    db.add(token)
    db.commit()
    return {"token": token.token, "user": serialize(user)}


@app.post("/api/auth/logout", status_code=204)
def logout(
    authorization: str | None = Header(default=None), db: Session = Depends(get_db)
) -> None:
    if authorization:
        token = db.get(SessionToken, authorization.removeprefix("Bearer "))
        if token:
            db.delete(token)
            db.commit()


@app.get("/api/me")
def me(user: User = Depends(require_user)) -> dict:
    return serialize(user)


@app.put("/api/me")
def preferences(
    data: PreferencesIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    for key, value in data.model_dump().items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return serialize(user)


@app.get("/api/accounts")
def accounts(
    user: User = Depends(require_user), db: Session = Depends(get_db)
) -> list[dict]:
    return [
        serialize(x)
        for x in db.scalars(
            select(Account)
            .where(Account.user_id == user.id, Account.active.is_(True))
            .order_by(Account.id)
        )
    ]


@app.post("/api/accounts", status_code=201)
def add_account(
    data: AccountIn, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> dict:
    row = Account(user_id=user.id, **data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@app.delete("/api/accounts/{row_id}", status_code=204)
def remove_account(
    row_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> None:
    row = db.get(Account, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Account not found")
    row.active = False
    db.commit()


@app.get("/api/cards")
def cards(
    user: User = Depends(require_user), db: Session = Depends(get_db)
) -> list[dict]:
    return [
        serialize(x)
        for x in db.scalars(
            select(Card).where(Card.user_id == user.id).order_by(Card.id)
        )
    ]


@app.post("/api/cards", status_code=201)
def add_card(
    data: CardIn, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> dict:
    row = Card(user_id=user.id, **data.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@app.delete("/api/cards/{row_id}", status_code=204)
def remove_card(
    row_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> None:
    row = db.get(Card, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Card not found")
    db.delete(row)
    db.commit()


@app.get("/api/transactions")
def transactions(
    kind: str | None = None,
    category: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    filters = [Transaction.user_id == user.id]
    if kind:
        filters.append(Transaction.kind == kind)
    if category:
        filters.append(Transaction.category == category)
    if search:
        filters.append(Transaction.description.ilike(f"%{search}%"))
    total = (
        db.scalar(select(func.count()).select_from(Transaction).where(*filters)) or 0
    )
    rows = db.scalars(
        select(Transaction)
        .where(*filters)
        .order_by(Transaction.transacted_on.desc(), Transaction.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    )
    return {
        "items": [serialize(x) for x in rows],
        "total": total,
        "page": page,
        "size": size,
    }


@app.post("/api/transactions", status_code=201)
def add_transaction(
    data: TransactionIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    if data.kind == "transfer" and (
        not data.account_id
        or not data.to_account_id
        or data.account_id == data.to_account_id
    ):
        raise HTTPException(422, "Transfers require two different accounts")
    row = Transaction(user_id=user.id, **data.model_dump())
    db.add(row)
    apply_balance(db, row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@app.put("/api/transactions/{row_id}")
def update_transaction(
    row_id: int,
    data: TransactionIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(Transaction, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Transaction not found")
    apply_balance(db, row, reverse=True)
    for key, value in data.model_dump().items():
        setattr(row, key, value)
    apply_balance(db, row)
    db.commit()
    db.refresh(row)
    return serialize(row)


@app.delete("/api/transactions/{row_id}", status_code=204)
def remove_transaction(
    row_id: int, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> None:
    row = db.get(Transaction, row_id)
    if not row or row.user_id != user.id:
        raise HTTPException(404, "Transaction not found")
    apply_balance(db, row, reverse=True)
    db.delete(row)
    db.commit()


@app.get("/api/dashboard")
def dashboard(
    user: User = Depends(require_user), db: Session = Depends(get_db)
) -> dict:
    rows = list(db.scalars(select(Transaction).where(Transaction.user_id == user.id)))
    expenses = [x for x in rows if x.kind == "expense"]
    income = sum((x.amount for x in rows if x.kind == "income"), Decimal(0))
    spent = sum((x.amount for x in expenses), Decimal(0))
    groups: dict[str, Decimal] = {}
    months: dict[str, Decimal] = {}
    for item in expenses:
        groups[item.category] = groups.get(item.category, Decimal(0)) + item.amount
        month = item.transacted_on.strftime("%Y-%m")
        months[month] = months.get(month, Decimal(0)) + item.amount
    current_month = date.today().strftime("%Y-%m")
    monthly_spent = months.get(current_month, Decimal(0))
    accounts_total = (
        db.scalar(
            select(func.coalesce(func.sum(Account.balance), 0)).where(
                Account.user_id == user.id, Account.active.is_(True)
            )
        )
        or 0
    )
    return {
        "income": income,
        "spent": spent,
        "monthly_spent": monthly_spent,
        "net": income - spent,
        "accounts_total": accounts_total,
        "count": len(rows),
        "budget": user.monthly_budget,
        "categories": [
            {"name": k, "total": v}
            for k, v in sorted(groups.items(), key=lambda x: x[1], reverse=True)
        ],
        "months": [{"month": k, "total": v} for k, v in sorted(months.items())[-6:]],
        "insight": f"Your highest spending category is {max(groups, key=groups.get)}."
        if groups
        else "Add transactions to unlock insights.",
    }


@app.get("/api/notifications")
def get_notifications(
    user: User = Depends(require_user), db: Session = Depends(get_db)
) -> list[dict]:
    stats = dashboard(user, db)
    items = []
    if user.monthly_budget > 0 and stats["monthly_spent"] > user.monthly_budget:
        items.append(
            {
                "id": 1,
                "title": "Budget Alert",
                "message": f"Monthly spending ({user.currency} {stats['monthly_spent']}) has exceeded your budget of {user.currency} {user.monthly_budget}.",
                "kind": "warning",
            }
        )
    return items


@app.post("/api/ai/parse")
def parse_transaction(
    data: NaturalLanguageIn, user: User = Depends(require_user)
) -> dict:
    import re

    match = re.search(
        r"(?:₹|rs\.?|inr)?\s*(\d+(?:\.\d{1,2})?)", data.text, re.IGNORECASE
    )
    if not match:
        raise HTTPException(422, "Include an amount, for example: Spent 250 on lunch")
    lower = data.text.lower()
    category = next(
        (c for c in CATEGORIES if c.lower() in lower),
        "Food"
        if any(x in lower for x in ["lunch", "dinner", "coffee", "restaurant"])
        else "Other",
    )
    kind = (
        "income"
        if any(x in lower for x in ["received", "salary", "earned"])
        else "expense"
    )
    return {
        "kind": kind,
        "amount": match.group(1),
        "description": data.text.strip(),
        "category": category,
        "payment_mode": "Cash",
        "transacted_on": date.today(),
    }


@app.post("/api/ai/chat")
def chat(
    data: ChatIn, user: User = Depends(require_user), db: Session = Depends(get_db)
) -> dict:
    stats = dashboard(user, db)
    message = data.message.lower()
    if "budget" in message:
        answer = f"Your monthly budget is {user.currency} {user.monthly_budget}. You have recorded {user.currency} {stats['spent']} in expenses."
    elif "category" in message:
        answer = stats["insight"]
    elif "balance" in message:
        answer = f"Your combined account balance is {user.currency} {stats['accounts_total']}."
    else:
        answer = f"You recorded {stats['count']} transactions, with {user.currency} {stats['income']} income and {user.currency} {stats['spent']} expenses."
    return {"answer": answer}
