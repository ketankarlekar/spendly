import sqlite3

from flask import g, current_app
from werkzeug.security import generate_password_hash


def get_db():
    if 'db' not in g:
        db_path = current_app.config.get('DATABASE', 'spendly.db')
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            email         TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL,
            created_at    TEXT    DEFAULT (datetime('now'))
        )
    ''')
    db.execute('''
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL REFERENCES users(id),
            amount      REAL    NOT NULL,
            category    TEXT    NOT NULL,
            date        TEXT    NOT NULL,
            description TEXT,
            created_at  TEXT    DEFAULT (datetime('now'))
        )
    ''')
    db.commit()


def seed_db():
    db = get_db()
    if db.execute('SELECT 1 FROM users LIMIT 1').fetchone():
        return

    db.execute(
        'INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
        ('Demo User', 'demo@spendly.com', generate_password_hash('demo123'))
    )
    user_id = db.execute('SELECT last_insert_rowid()').fetchone()[0]

    expenses = [
        (user_id, 45.50,  'Food',          '2026-04-01', 'Grocery run'),
        (user_id, 12.00,  'Transport',     '2026-04-05', 'Bus pass top-up'),
        (user_id, 120.00, 'Bills',         '2026-04-08', 'Electricity bill'),
        (user_id, 35.00,  'Health',        '2026-04-12', 'Pharmacy'),
        (user_id, 18.50,  'Entertainment', '2026-04-15', 'Movie tickets'),
        (user_id, 60.00,  'Shopping',      '2026-04-18', 'New shoes'),
        (user_id, 9.99,   'Other',         '2026-04-22', 'Miscellaneous'),
        (user_id, 22.75,  'Food',          '2026-04-25', 'Lunch with friend'),
    ]
    db.executemany(
        'INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)',
        expenses
    )
    db.commit()
