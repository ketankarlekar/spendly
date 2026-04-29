# Spendly — Personal Expense Tracker

A web app to log expenses, understand spending patterns, and take control of your financial life — one transaction at a time.

Built with Flask and SQLite.

## Features

- User registration and login
- Add, edit, and delete expenses
- Category-wise spending breakdown (Bills, Food, Health, Transport, etc.)
- Filter expenses by date range
- Monthly spending summaries

## Tech Stack

- **Backend:** Python 3, Flask
- **Database:** SQLite
- **Frontend:** HTML, CSS, JavaScript (Jinja2 templates)

## Getting Started

### Prerequisites

- Python 3.10+

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/ketankarlekar/spendly.git
   cd spendly
   ```

2. Create and activate a virtual environment:
   ```bash
   python3 -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the app:
   ```bash
   python3 app.py
   ```

5. Open your browser and go to `http://127.0.0.1:5001`

## Opening `spendly.db`

`spendly.db` is a SQLite database file, so it will not open as a normal text file.

- No extra Python dependency is required for SQLite because Python includes `sqlite3`.
- To inspect the database from this project, run:
  ```bash
  python inspect_db.py
  ```
- To open it in the SQLite shell, run:
  ```bash
  sqlite3 spendly.db
  ```
  Then try `.tables` or `SELECT * FROM expenses;`

## Project Structure

```
spendly/
├── app.py                  # Flask app and all routes
├── requirements.txt
├── database/
│   ├── __init__.py
│   └── db.py               # get_db(), init_db(), seed_db()
├── static/
│   ├── css/
│   │   ├── style.css       # Global styles
│   │   └── landing.css     # Landing page only
│   └── js/
│       └── main.js
├── templates/
│   ├── base.html           # Shared layout
│   ├── landing.html
│   ├── login.html
│   ├── register.html
│   ├── privacy.html
│   └── terms.html
└── tests/
    └── conftest.py         # Pytest fixtures
```

## Running Tests

```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_foo.py

# Filter by test name
pytest -k "test_login"

# Show print output
pytest -s
```
