import pytest
from werkzeug.security import generate_password_hash

from database.db import get_db

def test_get_recent_transactions_returns_newest_first(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("T", "t@t.com", generate_password_hash("pass1234")))
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                   (user_id, 10.0, "Food", "2026-01-02"))
        db.execute("INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
                   (user_id, 5.0, "Food", "2026-01-01"))
        db.commit()
        from database.queries import get_recent_transactions
        rows = get_recent_transactions(user_id)
    assert len(rows) == 2
    assert rows[0]["date"] == "2026-01-02"


def test_get_recent_transactions_empty(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("E", "e@e.com", generate_password_hash("pass1234")))
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.commit()
        from database.queries import get_recent_transactions
        rows = get_recent_transactions(user_id)
    assert rows == []

def test_get_summary_stats_with_expenses(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("S", "s@s.com", generate_password_hash("pass1234")))
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.executemany(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            [(user_id, 100.0, "Bills", "2026-01-01"),
             (user_id, 40.0, "Food", "2026-01-02")]
        )
        db.commit()
        from database.queries import get_summary_stats
        stats = get_summary_stats(user_id)
    assert stats["total_spent"] == pytest.approx(140.0)
    assert stats["transaction_count"] == 2
    assert stats["top_category"] == "Bills"


def test_get_summary_stats_no_expenses(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("N", "n@n.com", generate_password_hash("pass1234")))
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.commit()
        from database.queries import get_summary_stats
        stats = get_summary_stats(user_id)
    assert stats == {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

def test_get_category_breakdown_percentages_sum_to_100(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("C", "c@c.com", generate_password_hash("pass1234")))
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.executemany(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            [(user_id, 30.0, "Food", "2026-01-01"),
             (user_id, 20.0, "Bills", "2026-01-02"),
             (user_id, 50.0, "Other", "2026-01-03")]
        )
        db.commit()
        from database.queries import get_category_breakdown
        cats = get_category_breakdown(user_id)
    assert sum(c["percentage"] for c in cats) == 100
    assert cats[0]["name"] == "Other"


def test_get_category_breakdown_empty(app):
    with app.app_context():
        db = get_db()
        db.execute("INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                   ("Z", "z@z.com", generate_password_hash("pass1234")))
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.commit()
        from database.queries import get_category_breakdown
        cats = get_category_breakdown(user_id)
    assert cats == []

def test_profile_unauthenticated_redirects(client):
    response = client.get('/profile')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_profile_authenticated_shows_live_data(app, client):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", generate_password_hash("demo123"))
        )
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        db.executemany(
            "INSERT INTO expenses (user_id, amount, category, date) VALUES (?, ?, ?, ?)",
            [(user_id, 120.00, "Bills", "2026-04-08"),
             (user_id, 45.50,  "Food",  "2026-04-01")]
        )
        db.commit()

    client.post('/login', data={"email": "demo@spendly.com", "password": "demo123"})
    response = client.get('/profile')
    assert response.status_code == 200
    assert b'Demo User' in response.data
    assert b'demo@spendly.com' in response.data
    assert '&#x20b9;'.encode() in response.data or '₹'.encode() in response.data
    assert b'Bills' in response.data
