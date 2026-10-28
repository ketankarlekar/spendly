"""
Tests for Step 10: Analytics page (GET /analytics).

Spec: .claude/specs/10-analytics.md
"""

import datetime

from database.db import get_db, create_user, create_expense
from database.queries import (
    get_analytics_summary,
    get_monthly_totals,
    get_top_expenses,
)


def _login(client, email="a@example.com", password="testpass1"):
    client.post("/register", data={"name": "A User", "email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})


def _user_id(app, email="a@example.com"):
    with app.app_context():
        return get_db().execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()["id"]


def _add(app, user_id, amount, category, date, description="x"):
    with app.app_context():
        create_expense(user_id, amount, category, date, description)


def test_requires_login(client):
    resp = client.get("/analytics")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_page_is_not_placeholder(client):
    _login(client)
    html = client.get("/analytics").get_data(as_text=True)
    assert "COMING SOON" not in html
    assert "Top 5 Expenses" in html


def test_empty_state(client):
    _login(client)
    html = client.get("/analytics").get_data(as_text=True)
    assert "₹0.00" in html
    assert "No expenses found for this period." in html


def test_summary_figures(client, app):
    _login(client)
    uid = _user_id(app)
    today = datetime.date.today().isoformat()
    _add(app, uid, 100, "Food", today)
    _add(app, uid, 50, "Bills", today)
    with app.app_context():
        s = get_analytics_summary(uid)
    assert s["total_spent"] == 150
    assert s["transaction_count"] == 2
    assert s["avg_per_transaction"] == 75
    assert s["avg_per_day"] == 150
    assert s["change_pct"] is None and s["previous_total"] is None


def test_change_vs_previous_period(client, app):
    _login(client)
    uid = _user_id(app)
    _add(app, uid, 100, "Food", "2026-03-05")  # previous 10-day window
    _add(app, uid, 150, "Food", "2026-03-15")  # current window
    with app.app_context():
        s = get_analytics_summary(uid, "2026-03-11", "2026-03-20")
    assert s["previous_total"] == 100
    assert s["change_pct"] == 50


def test_change_none_when_previous_is_zero(client, app):
    _login(client)
    uid = _user_id(app)
    _add(app, uid, 40, "Food", "2026-03-15")
    with app.app_context():
        s = get_analytics_summary(uid, "2026-03-11", "2026-03-20")
    assert s["previous_total"] == 0
    assert s["change_pct"] is None


def test_monthly_totals_six_months(client, app):
    _login(client)
    uid = _user_id(app)
    today = datetime.date.today()
    _add(app, uid, 30, "Food", today.isoformat())
    _add(app, uid, 99, "Food", "2000-01-01")  # outside the window
    with app.app_context():
        months = get_monthly_totals(uid)
    assert len(months) == 6
    assert months[-1]["month"] == today.strftime("%Y-%m")
    assert months[-1]["total"] == 30
    assert all(m["total"] == 0 for m in months[:-1])


def test_top_expenses_order_and_limit(client, app):
    _login(client)
    uid = _user_id(app)
    for i, amt in enumerate([10, 70, 30, 90, 20, 60, 50]):
        _add(app, uid, amt, "Food", f"2026-03-{i + 1:02d}")
    with app.app_context():
        top = get_top_expenses(uid)
    assert [t["amount"] for t in top] == [90, 70, 60, 50, 30]


def test_date_filter_applies(client, app):
    _login(client)
    uid = _user_id(app)
    _add(app, uid, 11, "Food", "2026-01-10", "inside-range")
    _add(app, uid, 22, "Bills", "2026-02-10", "outside-range")
    html = client.get("/analytics?date_from=2026-01-01&date_to=2026-01-31").get_data(as_text=True)
    assert "inside-range" in html
    assert "outside-range" not in html


def test_reversed_range_flashes_and_falls_back(client, app):
    _login(client)
    uid = _user_id(app)
    _add(app, uid, 11, "Food", "2026-01-10", "some-expense")
    html = client.get("/analytics?date_from=2026-02-01&date_to=2026-01-01").get_data(as_text=True)
    assert "Start date must be before end date." in html
    assert "some-expense" in html


def test_malformed_date_does_not_crash(client):
    _login(client)
    resp = client.get("/analytics?date_from=not-a-date&date_to=2026-01-01")
    assert resp.status_code == 200


def test_users_are_isolated(client, app):
    _login(client)
    with app.app_context():
        other = create_user("Other", "other@example.com", "testpass1")
    _add(app, other, 999, "Food", datetime.date.today().isoformat(), "secret-expense")
    html = client.get("/analytics").get_data(as_text=True)
    assert "secret-expense" not in html
    assert "₹999.00" not in html


def test_no_hardcoded_hex_in_analytics_assets():
    import re
    for path in ("templates/analytics.html", "static/css/analytics.css"):
        with open(path, encoding="utf-8") as f:
            assert not re.search(r"#[0-9a-fA-F]{3,6}\b", f.read()), path
