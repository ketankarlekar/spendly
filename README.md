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

- **Backend:** Python, Flask
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

## Project Structure

```
spendly/
├── app.py                  # Flask app and routes
├── requirements.txt
├── database/
│   ├── __init__.py
│   └── db.py               # Database connection and setup
├── static/
│   ├── css/style.css
│   └── js/main.js
└── templates/
    ├── base.html
    ├── landing.html
    ├── login.html
    └── register.html
```

## Running Tests

```bash
pytest
```
