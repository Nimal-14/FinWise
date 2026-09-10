# FinWise

A complete personal-finance application using FastAPI, SQLAlchemy, HTML, CSS,
and vanilla JavaScript. It uses a responsive dark interface and keeps the code
formatted with Ruff and Prettier.

## Run locally

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8010
```

Open http://127.0.0.1:8010. Interactive API documentation is at http://127.0.0.1:8010/docs. Port `8010` is used because `8000` is already occupied on this machine.

The default database is SQLite, so no external service is required while learning. To use PostgreSQL:

```bash
docker compose up -d postgres
cp .env.example .env
uv run uvicorn app.main:app --reload --port 8010
```

PostgreSQL uses local port `5433` because `5432` was already occupied on this machine.

## Tests

```bash
uv run pytest
```

Formatting and linting:

```bash
uv run ruff format app tests
uv run ruff check app tests
```

## Features

- Registration, login, logout, protected APIs, and isolated user data
- Profile, currency, onboarding status, and monthly-budget preferences
- Bank, cash, and wallet accounts with automatic balance updates
- Debit and credit cards linked to accounts
- Expense, income, and transfer transactions with editing and deletion
- Search, category/type filters, pagination-ready API responses
- Dashboard totals, category breakdown, budget progress, and monthly trends
- Natural-language transaction parsing and a finance assistant
- SQLite for simple local development and optional PostgreSQL through Docker
- OpenAPI documentation at `/docs` and an automated end-to-end API test suite

## Recommended learning order

1. Trace authentication and transaction requests from JavaScript to FastAPI.
2. Study the SQLAlchemy relationships and account-balance updates.
3. Extend the test suite before changing financial calculations.
4. Add Alembic migrations before deploying to a shared environment.
5. Replace the deterministic assistant with an external AI provider only when
   the core application is reliable.
