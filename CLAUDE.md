# Spendly — Project Guide for Claude

## What this project is

**Spendly** is a personal expense tracker built as a learning project. It is a
Flask + SQLite web application with server-rendered Jinja2 templates and vanilla
CSS/JS. There is no React, no TypeScript, no ORM.

The project is built step-by-step. Each step has a spec file in
`.claude/specs/`. Steps must be implemented in order because each one depends on
the previous.

---

## Tech stack

| Layer       | Technology                              |
|-------------|------------------------------------------|
| Backend     | Python 3.12, Flask 3.x                  |
| Database    | SQLite via the standard `sqlite3` module |
| Templates   | Jinja2 (Flask's built-in renderer)      |
| Styles      | Vanilla CSS in `static/css/`            |
| Scripts     | Vanilla JS in `static/js/`              |
| Auth        | Flask session (cookie-based)            |
| Tests       | pytest + pytest-flask                   |
| Port        | **5001**                                |

---

## File structure

```
expense-tracker/          ← project root (this file lives here)
├── app.py                ← all Flask routes
├── requirements.txt
├── CLAUDE.md             ← this file
├── database/
│   ├── __init__.py
│   ├── db.py             ← get_db, init_db, seed_db, CRUD helpers
│   └── queries.py        ← read-only query helpers (stats, transactions, etc.)
├── templates/
│   ├── base.html
│   ├── landing.html
│   ├── register.html
│   ├── login.html
│   ├── profile.html
│   ├── add_expense.html
│   ├── analytics.html
│   ├── terms.html
│   └── privacy.html
├── static/
│   ├── css/
│   │   ├── style.css     ← global styles and CSS variables
│   │   ├── profile.css
│   │   ├── analytics.css
│   │   └── landing.css
│   └── js/
│       └── main.js
├── tests/
│   ├── conftest.py
│   ├── test_register.py
│   ├── test_backend_connection.py
│   ├── test_date_filter.py
│   ├── test_08-edit-expense.py
│   ├── test_delete_expense.py
│   └── test_analytics.py
└── .claude/
    ├── agents/           ← subagent definitions
    ├── commands/         ← slash command definitions
    ├── skills/           ← skill definitions
    └── specs/            ← step-by-step feature specs
```

---

## Database schema

### users

| Column        | Type    | Constraints                      |
|---------------|---------|----------------------------------|
| id            | INTEGER | PRIMARY KEY AUTOINCREMENT        |
| name          | TEXT    | NOT NULL                         |
| email         | TEXT    | UNIQUE NOT NULL                  |
| password_hash | TEXT    | NOT NULL                         |
| created_at    | TEXT    | DEFAULT datetime('now')          |

### expenses

| Column      | Type    | Constraints                          |
|-------------|---------|--------------------------------------|
| id          | INTEGER | PRIMARY KEY AUTOINCREMENT            |
| user_id     | INTEGER | NOT NULL REFERENCES users(id)        |
| amount      | REAL    | NOT NULL                             |
| category    | TEXT    | NOT NULL                             |
| date        | TEXT    | NOT NULL (YYYY-MM-DD)                |
| description | TEXT    | nullable                             |
| created_at  | TEXT    | DEFAULT datetime('now')              |

---

## Step roadmap

| # | Spec file                              | Status      |
|---|----------------------------------------|-------------|
| 1 | `01-database-setup.md`                 | ✅ Complete |
| 2 | `02-registration.md`                   | ✅ Complete |
| 3 | `03-login-and-logout.md`               | ✅ Complete |
| 4 | `04-profile-page.md`                   | ✅ Complete |
| 5 | `05-backend-routes-for-profile-page.md`| ✅ Complete |
| 6 | `06-date-filter-for-profile-page.md`   | ✅ Complete |
| 7 | `07-add-expense.md`                    | ✅ Complete |
| 8 | `08-edit-expense.md`                   | ✅ Complete |
| 9 | `09-delete-expense.md`                 | ✅ Complete |
| 10 | `10-analytics.md`                     | ✅ Complete |

---

## Expense categories (fixed list)

```python
EXPENSE_CATEGORIES = [
    "Food", "Transport", "Bills", "Health",
    "Entertainment", "Shopping", "Other"
]
```

This constant lives in `app.py` and is passed to every template that needs it.

---

## Implementation rules (non-negotiable)

- **No ORMs** — raw `sqlite3` only, accessed via `get_db()` in `database/db.py`
- **Parameterised queries only** — use `?` placeholders; never f-strings or
  `.format()` in SQL
- **No new pip packages** — use only what is in `requirements.txt`
- **Passwords hashed with werkzeug** — `generate_password_hash` /
  `check_password_hash`; never store or log plaintext
- **CSS variables** — never hardcode hex values in templates or stylesheets
- **`url_for()` everywhere** — never hardcode URL paths in templates
- **All templates extend `base.html`**
- **DB helpers in `database/db.py`**, read-only queries in `database/queries.py`
- **Routes in `app.py` only** — no inline SQL in routes
- **Vanilla JS** — no frameworks, no bundlers
- **`PRAGMA foreign_keys = ON`** on every DB connection (already set in
  `get_db()`)
- **Port 5001** — `app.run(debug=True, port=5001)`

---

## Running the app

```bash
# activate venv first (Windows PowerShell)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& "c:\Users\Ketan\Downloads\Code & Projects\expense-tracker\venv\Scripts\Activate.ps1"

# start the server
python app.py
# → http://localhost:5001
```

Demo account seeded automatically on first run:
- Email: `demo@spendly.com`
- Password: `demo123`

---

## Running tests

```bash
python -m pytest tests/ -v
```

All tests use an isolated in-memory (or temp-file) SQLite database — no shared
state between runs.

---

## Slash commands (`.claude/commands/`)

| Command               | What it does                                           |
|-----------------------|--------------------------------------------------------|
| `/create-spec`        | Create a spec file and feature branch for the next step|
| `/test-feature`       | Write and run tests for a specific spec                |
| `/code-review-feature`| Run parallel security + quality review on a feature    |
| `/seed-user`          | Insert a single dummy user into the DB                 |
| `/seed-expense`       | Seed dummy expenses for a user                         |

Usage example: `/create-spec 8 edit-expense`

---

## Subagents (`.claude/agents/`)

| Agent                    | Role                                    |
|--------------------------|-----------------------------------------|
| `spendly-test-writer`    | Writes pytest tests from spec           |
| `spendly-test-runner`    | Runs and analyses test results          |
| `spendly-quality-reviewer`| Reviews code quality after a feature   |
| `spendly-security-reviewer`| Reviews security after a feature      |

---

## Skills (`.claude/skills/`)

| Skill                  | Role                                           |
|------------------------|------------------------------------------------|
| `frontend-design`      | Generates Spendly-consistent UI (Jinja2 + CSS) |
