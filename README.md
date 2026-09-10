# FinWise

FinWise is a clean, lightweight personal finance and expense tracker built with **FastAPI**, **SQLAlchemy**, and a **vanilla HTML/CSS/JavaScript** frontend. It features a warm, human-crafted design focused on clarity, practicality, and fast interaction without heavy framework bloat.

---

## Features

- **Authentication & Security**: Secure token-based session authentication with PBKDF2 password hashing and user-isolated financial data.
- **Human-Crafted UI**: Clean, paper-and-ink aesthetic inspired by classic notebooks—zero dark-mode crypto clutter or framework overhead.
- **Financial Dashboard**:
  - Live metric cards: Net Cash Flow, Total Income, Total Expenses, and Accounts Balance.
  - Category spending breakdown with progress bars.
  - Recent transaction feed with quick links.
- **Accounts & Cards**:
  - Track multiple accounts (Bank, Cash, Wallets) with automatic balance adjustments upon transactions.
  - Manage payment cards (Debit and Credit) linked to accounts.
- **Transaction Ledger**:
  - Log expenses, income, and transfers between accounts.
  - Search transactions, filter by type (Expense, Income, Transfer) or category.
  - Edit or delete transactions with automatic balance reconciliation.
- **Smart Quick Add**: Natural-language expense entry (e.g., *"Spent 250 on lunch"*).
- **Analytics & Budgeting**:
  - Monthly budget limit tracking and usage percentage.
  - 6-month historical spending trend chart.
- **Financial Assistant**: Built-in chat assistant for quick insights on your balance, budget, and top spending areas.
- **Database Support**: Zero-config SQLite for local development; ready for PostgreSQL via Docker Compose.
- **Database Migrations**: Pre-configured with Alembic.
- **Tested & Formatted**: Automated integration test suite with pytest, formatted using Ruff and Prettier.

---

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy, Pydantic, Uvicorn
- **Frontend**: Vanilla JavaScript (ES6+), HTML5, Custom CSS
- **Database**: SQLite (default) / PostgreSQL (optional)
- **Tooling**: `uv` package manager, Alembic, Ruff, Prettier, Pytest

---

## Project Structure

```text
FinWise/
├── app/
│   ├── static/
│   │   ├── app.js          # Frontend application logic & state management
│   │   ├── index.html      # Single-page interface markup
│   │   └── styles.css      # Custom human-crafted design system
│   ├── config.py           # Application settings & environment config
│   ├── database.py         # SQLAlchemy engine and session factory
│   ├── domain.py           # Database models (User, Account, Card, Transaction, etc.)
│   └── main.py             # FastAPI routing, auth, business logic & static mounting
├── migrations/             # Alembic database migrations
├── tests/
│   ├── conftest.py         # Pytest fixtures & isolated test client
│   └── test_full_app.py    # End-to-end integration tests
├── compose.yaml            # Optional Docker Compose for PostgreSQL
├── pyproject.toml          # Project metadata & dependencies
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or standard `pip`

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/Nimal-14/FinWise.git
cd FinWise
uv sync
```

### 2. Run the Application

Start the development server with hot-reloading:

```bash
uv run uvicorn app.main:app --reload --port 8010
```

Open your browser and visit:
- **Application**: [http://127.0.0.1:8010](http://127.0.0.1:8010)
- **Interactive API Documentation (Swagger)**: [http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs)
- **Alternative Docs (ReDoc)**: [http://127.0.0.1:8010/redoc](http://127.0.0.1:8010/redoc)

*(Port `8010` is used by default to avoid conflicts on systems with port `8000` occupied).*

---

## Optional: PostgreSQL with Docker

To use PostgreSQL instead of SQLite:

1. Start the PostgreSQL container:
   ```bash
   docker compose up -d postgres
   ```
2. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
3. Run the application:
   ```bash
   uv run uvicorn app.main:app --reload --port 8010
   ```

*(PostgreSQL runs on port `5433` as defined in `compose.yaml`).*

---

## Running Tests & Quality Checks

Run the automated integration test suite:

```bash
uv run pytest
```

Check code formatting and linting:

```bash
# Python
uv run ruff check app tests
uv run ruff format --check app tests

# Frontend
npx prettier --check app/static/*
```

