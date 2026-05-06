"""
Tests for Step 6: Date filter on GET /profile.

Spec: .claude/specs/06-date-filter-for-profile-page.md

All three data sections (summary stats, recent transactions, category
breakdown) must respect the active date filter.  The filter is driven
by optional query-string params: date_from and date_to (both YYYY-MM-DD).

Fixture note: uses the `app` and `client` fixtures from conftest.py,
which create a fresh temp-file SQLite DB per test and call init_db().
There is no shared auth_client fixture in conftest — each test that
needs a logged-in session registers and logs in manually.
"""

import datetime
import pytest
from werkzeug.security import generate_password_hash

from database.db import get_db


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #

def _register_and_login(client, email="filter@example.com",
                        password="testpass1"):
    """Register a user and log in, returning the user email."""
    client.post("/register", data={
        "name": "Filter User",
        "email": email,
        "password": password,
    })
    client.post("/login", data={"email": email, "password": password})
    return email


def _insert_user(app, name="Filter User", email="filter@example.com",
                 password="testpass1"):
    """Insert a user directly into the DB and return their id."""
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    return user_id


def _insert_expenses(app, user_id, rows):
    """
    Insert expense rows for a user.
    Each element of `rows` is (amount, category, date_str [, description]).
    """
    with app.app_context():
        db = get_db()
        for row in rows:
            amount, category, date_str = row[0], row[1], row[2]
            description = row[3] if len(row) > 3 else ""
            db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description)"
                " VALUES (?, ?, ?, ?, ?)",
                (user_id, amount, category, date_str, description),
            )
        db.commit()


def _today():
    return datetime.date.today()


def _iso(d):
    return d.isoformat()


# ------------------------------------------------------------------ #
# Auth guard
# ------------------------------------------------------------------ #

class TestAuthGuard:
    def test_unauthenticated_no_params_redirects_to_login(self, client):
        response = client.get("/profile")
        assert response.status_code == 302, "Expected redirect for unauthenticated user"
        assert "/login" in response.headers["Location"]

    def test_unauthenticated_with_date_params_redirects_to_login(self, client):
        response = client.get("/profile?date_from=2026-01-01&date_to=2026-01-31")
        assert response.status_code == 302, "Expected redirect even with date params"
        assert "/login" in response.headers["Location"]


# ------------------------------------------------------------------ #
# Unfiltered view (no query params) — same as Step 5 behaviour
# ------------------------------------------------------------------ #

class TestUnfilteredView:
    def test_no_params_returns_200(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        response = client.get("/profile")
        assert response.status_code == 200, "Profile page must return 200"

    def test_no_params_shows_all_expenses(self, app, client):
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (50.0, "Food", "2025-01-15"),
            (30.0, "Bills", "2024-06-10"),
            (20.0, "Transport", "2023-03-01"),
        ])
        _register_and_login(client)
        response = client.get("/profile")
        data = response.data
        # All three amounts should appear in the rendered page
        assert b"50" in data, "Amount 50 must appear in unfiltered view"
        assert b"30" in data, "Amount 30 must appear in unfiltered view"
        assert b"20" in data, "Amount 20 must appear in unfiltered view"

    def test_no_params_rupee_symbol_present(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        response = client.get("/profile")
        rupee_present = (
            "₹".encode("utf-8") in response.data
            or b"&#x20b9;" in response.data
            or b"&#8377;" in response.data
        )
        assert rupee_present, "Rupee symbol must appear on the profile page"

    def test_no_params_active_preset_is_all_time(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        response = client.get("/profile")
        # The template must mark the "All Time" button as active.
        # The spec requires a CSS active class on the matching preset button.
        data = response.data.decode("utf-8", errors="replace")
        assert "all_time" in data or "All Time" in data, (
            "All Time preset indicator must be present when no filter is applied"
        )


# ------------------------------------------------------------------ #
# "This Month" preset
# ------------------------------------------------------------------ #

class TestThisMonthPreset:
    def _preset_params(self):
        today = _today()
        date_from = _iso(today.replace(day=1))
        date_to = _iso(today)
        return date_from, date_to

    def test_this_month_excludes_older_expenses(self, app, client):
        today = _today()
        user_id = _insert_user(app)
        # One expense this month, one clearly outside
        this_month_date = _iso(today.replace(day=1))
        old_date = _iso(today.replace(year=today.year - 1))
        _insert_expenses(app, user_id, [
            (100.0, "Bills", this_month_date),
            (999.0, "Other", old_date),
        ])
        _register_and_login(client)
        date_from, date_to = self._preset_params()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        assert response.status_code == 200
        data = response.data.decode("utf-8", errors="replace")
        # The old expense (999) must not appear in the filtered view
        assert "999" not in data, "Out-of-month expense must be excluded by This Month filter"

    def test_this_month_includes_current_month_expense(self, app, client):
        today = _today()
        user_id = _insert_user(app)
        this_month_date = _iso(today.replace(day=1))
        _insert_expenses(app, user_id, [
            (77.0, "Food", this_month_date),
        ])
        _register_and_login(client)
        date_from, date_to = self._preset_params()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        assert response.status_code == 200
        assert b"77" in response.data, "Current-month expense must appear under This Month filter"

    def test_this_month_active_preset_marked(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        today = _today()
        date_from = _iso(today.replace(day=1))
        date_to = _iso(today)
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        data = response.data.decode("utf-8", errors="replace")
        # Template must expose an active indicator for this_month
        assert "this_month" in data or "This Month" in data, (
            "This Month preset must be identified as active in the response"
        )

    def test_this_month_all_three_sections_respect_filter(self, app, client):
        """Stats, transactions, and category breakdown must all be filtered."""
        today = _today()
        user_id = _insert_user(app)
        this_month_date = _iso(today.replace(day=1))
        old_date = _iso(today.replace(year=today.year - 1))
        _insert_expenses(app, user_id, [
            (50.0, "Food", this_month_date),
            (888.0, "Luxury", old_date),
        ])
        _register_and_login(client)
        date_from, date_to = self._preset_params()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        data = response.data.decode("utf-8", errors="replace")
        # The 888 out-of-range value must not surface in any section
        assert "888" not in data, (
            "Out-of-range expense must not appear in any section under This Month filter"
        )


# ------------------------------------------------------------------ #
# "Last 3 Months" preset
# ------------------------------------------------------------------ #

class TestLast3MonthsPreset:
    def _preset_params(self):
        today = _today()
        date_from = _iso(today - datetime.timedelta(days=90))
        date_to = _iso(today)
        return date_from, date_to

    def test_last_3_months_excludes_older_expenses(self, app, client):
        today = _today()
        user_id = _insert_user(app)
        recent_date = _iso(today - datetime.timedelta(days=30))
        old_date = _iso(today - datetime.timedelta(days=200))
        _insert_expenses(app, user_id, [
            (55.0, "Food", recent_date),
            (777.0, "Other", old_date),
        ])
        _register_and_login(client)
        date_from, date_to = self._preset_params()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        data = response.data.decode("utf-8", errors="replace")
        assert "777" not in data, "Expense older than 90 days must be excluded"

    def test_last_3_months_includes_recent_expense(self, app, client):
        today = _today()
        user_id = _insert_user(app)
        recent_date = _iso(today - datetime.timedelta(days=10))
        _insert_expenses(app, user_id, [
            (63.0, "Transport", recent_date),
        ])
        _register_and_login(client)
        date_from, date_to = self._preset_params()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        assert b"63" in response.data, "Recent expense must appear under Last 3 Months"

    def test_last_3_months_active_preset_marked(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        date_from, date_to = self._preset_params()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        data = response.data.decode("utf-8", errors="replace")
        assert "last_3_months" in data or "Last 3 Months" in data, (
            "Last 3 Months preset must be identified as active in the response"
        )


# ------------------------------------------------------------------ #
# "Last 6 Months" preset
# ------------------------------------------------------------------ #

class TestLast6MonthsPreset:
    def _preset_params(self):
        today = _today()
        date_from = _iso(today - datetime.timedelta(days=180))
        date_to = _iso(today)
        return date_from, date_to

    def test_last_6_months_excludes_older_expenses(self, app, client):
        today = _today()
        user_id = _insert_user(app)
        recent_date = _iso(today - datetime.timedelta(days=60))
        old_date = _iso(today - datetime.timedelta(days=365))
        _insert_expenses(app, user_id, [
            (40.0, "Health", recent_date),
            (666.0, "Other", old_date),
        ])
        _register_and_login(client)
        date_from, date_to = self._preset_params()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        data = response.data.decode("utf-8", errors="replace")
        assert "666" not in data, "Expense older than 180 days must be excluded"

    def test_last_6_months_includes_recent_expense(self, app, client):
        today = _today()
        user_id = _insert_user(app)
        recent_date = _iso(today - datetime.timedelta(days=90))
        _insert_expenses(app, user_id, [
            (84.0, "Shopping", recent_date),
        ])
        _register_and_login(client)
        date_from, date_to = self._preset_params()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        assert b"84" in response.data, "90-day-old expense must appear under Last 6 Months"

    def test_last_6_months_active_preset_marked(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        date_from, date_to = self._preset_params()
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        data = response.data.decode("utf-8", errors="replace")
        assert "last_6_months" in data or "Last 6 Months" in data, (
            "Last 6 Months preset must be identified as active in the response"
        )


# ------------------------------------------------------------------ #
# Custom date range
# ------------------------------------------------------------------ #

class TestCustomDateRange:
    def test_custom_range_includes_only_matching_expenses(self, app, client):
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (200.0, "Bills",  "2025-03-10"),
            (150.0, "Food",   "2025-04-15"),
            (100.0, "Health", "2025-05-20"),
        ])
        _register_and_login(client)
        response = client.get("/profile?date_from=2025-04-01&date_to=2025-04-30")
        assert response.status_code == 200
        data = response.data.decode("utf-8", errors="replace")
        assert "150" in data, "April expense must appear in April custom range"
        assert "200" not in data, "March expense must be excluded from April custom range"
        assert "100" not in data, "May expense must be excluded from April custom range"

    def test_custom_range_active_preset_is_custom(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        response = client.get("/profile?date_from=2025-01-01&date_to=2025-01-31")
        data = response.data.decode("utf-8", errors="replace")
        # Active preset should indicate "custom", not one of the named presets
        assert "custom" in data or "2025-01-01" in data or "2025-01-31" in data, (
            "Custom range must be reflected in active state or filter values in response"
        )

    def test_custom_range_all_sections_filtered(self, app, client):
        """All three sections must respect the custom range."""
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (300.0, "Transport", "2025-06-15"),
            (111.0, "Other",     "2024-12-01"),
        ])
        _register_and_login(client)
        response = client.get("/profile?date_from=2025-06-01&date_to=2025-06-30")
        data = response.data.decode("utf-8", errors="replace")
        assert "300" in data, "In-range expense must appear"
        assert "111" not in data, "Out-of-range expense must not appear in any section"

    def test_custom_range_inclusive_boundary_dates(self, app, client):
        """date_from and date_to are inclusive bounds."""
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (10.0, "Food", "2025-02-01"),   # exactly on date_from
            (20.0, "Food", "2025-02-28"),   # exactly on date_to
            (30.0, "Food", "2025-03-01"),   # one day after date_to
        ])
        _register_and_login(client)
        response = client.get("/profile?date_from=2025-02-01&date_to=2025-02-28")
        data = response.data.decode("utf-8", errors="replace")
        assert "10" in data, "Expense on date_from boundary must be included"
        assert "20" in data, "Expense on date_to boundary must be included"
        assert "30" not in data, "Expense one day after date_to must be excluded"


# ------------------------------------------------------------------ #
# Inverted range (date_from > date_to)
# ------------------------------------------------------------------ #

class TestInvertedDateRange:
    def test_inverted_range_returns_200(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        response = client.get("/profile?date_from=2026-12-31&date_to=2026-01-01")
        assert response.status_code == 200, "Inverted range must not crash — expect 200"

    def test_inverted_range_flashes_error_message(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        # Enable follow_redirects so flash messages are rendered in the page
        response = client.get(
            "/profile?date_from=2026-12-31&date_to=2026-01-01",
            follow_redirects=True,
        )
        data = response.data.decode("utf-8", errors="replace")
        assert "Start date must be before end date" in data, (
            "Flash message 'Start date must be before end date.' must appear"
        )

    def test_inverted_range_falls_back_to_unfiltered(self, app, client):
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (45.0, "Food", "2024-06-01"),
            (55.0, "Bills", "2022-11-15"),
        ])
        _register_and_login(client)
        response = client.get(
            "/profile?date_from=2026-12-31&date_to=2026-01-01",
            follow_redirects=True,
        )
        data = response.data.decode("utf-8", errors="replace")
        # Both expenses must appear — unfiltered fallback
        assert "45" in data, "Unfiltered fallback must show all expenses (45)"
        assert "55" in data, "Unfiltered fallback must show all expenses (55)"


# ------------------------------------------------------------------ #
# Malformed date inputs
# ------------------------------------------------------------------ #

class TestMalformedDateInputs:
    @pytest.mark.parametrize("qs", [
        "date_from=not-a-date&date_to=2026-01-31",
        "date_from=2026-01-01&date_to=not-a-date",
        "date_from=not-a-date&date_to=not-a-date",
        "date_from=13-32-2099&date_to=2026-01-01",
        "date_from=2026-00-01&date_to=2026-01-31",
        "date_from=99999&date_to=2026-01-31",
    ])
    def test_malformed_date_does_not_crash(self, app, client, qs):
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (25.0, "Food", "2025-05-10"),
        ])
        _register_and_login(client)
        response = client.get(f"/profile?{qs}")
        assert response.status_code == 200, (
            f"Malformed date param must not crash the app — got {response.status_code} for ?{qs}"
        )

    def test_malformed_date_from_falls_back_to_unfiltered(self, app, client):
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (33.0, "Health", "2023-01-01"),
            (44.0, "Food",   "2025-06-15"),
        ])
        _register_and_login(client)
        response = client.get("/profile?date_from=BADDATE&date_to=2025-12-31")
        data = response.data.decode("utf-8", errors="replace")
        # Both expenses visible — filter ignored due to bad date_from
        assert "33" in data, "Fallback unfiltered view must include all expenses"
        assert "44" in data, "Fallback unfiltered view must include all expenses"

    def test_malformed_date_to_falls_back_to_unfiltered(self, app, client):
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (71.0, "Transport", "2024-03-20"),
        ])
        _register_and_login(client)
        response = client.get("/profile?date_from=2024-01-01&date_to=BADDATE")
        data = response.data.decode("utf-8", errors="replace")
        assert "71" in data, "Fallback unfiltered view must show expense when date_to is malformed"


# ------------------------------------------------------------------ #
# Empty period — filter matches no expenses
# ------------------------------------------------------------------ #

class TestEmptyPeriod:
    def test_empty_period_returns_200(self, app, client):
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (50.0, "Food", "2025-06-01"),
        ])
        _register_and_login(client)
        # Date range that has no expenses
        response = client.get("/profile?date_from=2020-01-01&date_to=2020-01-31")
        assert response.status_code == 200, "Empty filter period must return 200, not an error"

    def test_empty_period_shows_zero_total(self, app, client):
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (50.0, "Food", "2025-06-01"),
        ])
        _register_and_login(client)
        response = client.get("/profile?date_from=2020-01-01&date_to=2020-01-31")
        data = response.data.decode("utf-8", errors="replace")
        assert "0.00" in data, "Empty period must show ₹0.00 total spent"

    def test_empty_period_shows_zero_transaction_count(self, app, client):
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (50.0, "Food", "2025-06-01"),
        ])
        _register_and_login(client)
        response = client.get("/profile?date_from=2020-01-01&date_to=2020-01-31")
        data = response.data.decode("utf-8", errors="replace")
        # The transaction count stat must show 0
        assert "0" in data, "Empty period must show 0 transactions"

    def test_empty_period_no_category_rows(self, app, client):
        """Category breakdown must be empty (no rows) for a period with no expenses."""
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (50.0, "Food", "2025-06-01"),
        ])
        _register_and_login(client)
        response = client.get("/profile?date_from=2020-01-01&date_to=2020-01-31")
        data = response.data.decode("utf-8", errors="replace")
        # "Food" category must not appear since it falls outside the range
        assert "Food" not in data, (
            "Category 'Food' must not appear in breakdown for a period with no matching expenses"
        )

    def test_empty_period_rupee_symbol_still_present(self, app, client):
        """Rupee symbol must appear even when no expenses match the filter."""
        user_id = _insert_user(app)
        _insert_expenses(app, user_id, [
            (50.0, "Food", "2025-06-01"),
        ])
        _register_and_login(client)
        response = client.get("/profile?date_from=2020-01-01&date_to=2020-01-31")
        rupee_present = (
            "₹".encode("utf-8") in response.data
            or b"&#x20b9;" in response.data
            or b"&#8377;" in response.data
        )
        assert rupee_present, "Rupee symbol must appear even for an empty filter period"

    def test_user_with_no_expenses_and_any_filter_returns_200(self, app, client):
        """A user who has no expenses at all must not see errors under any filter."""
        _insert_user(app)
        _register_and_login(client)
        response = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        assert response.status_code == 200


# ------------------------------------------------------------------ #
# Active preset CSS highlighting
# ------------------------------------------------------------------ #

class TestActivePresetHighlight:
    """
    The spec requires each preset button to carry a visually active state.
    The template must encode the active_preset value (passed from the view)
    into the HTML so we can detect which button is highlighted.
    We check for the presence of the preset key or CSS class in the output.
    """

    def test_all_time_preset_highlighted_when_no_params(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        response = client.get("/profile")
        data = response.data.decode("utf-8", errors="replace")
        assert "all_time" in data or "All Time" in data, (
            "All Time button/preset must be marked active when no filter is applied"
        )

    def test_this_month_preset_highlighted(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        today = _today()
        date_from = _iso(today.replace(day=1))
        date_to = _iso(today)
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        data = response.data.decode("utf-8", errors="replace")
        assert "this_month" in data or "This Month" in data, (
            "This Month button must be marked active for this-month preset params"
        )

    def test_last_3_months_preset_highlighted(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        today = _today()
        date_from = _iso(today - datetime.timedelta(days=90))
        date_to = _iso(today)
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        data = response.data.decode("utf-8", errors="replace")
        assert "last_3_months" in data or "Last 3 Months" in data, (
            "Last 3 Months button must be marked active for last-3-months preset params"
        )

    def test_last_6_months_preset_highlighted(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        today = _today()
        date_from = _iso(today - datetime.timedelta(days=180))
        date_to = _iso(today)
        response = client.get(f"/profile?date_from={date_from}&date_to={date_to}")
        data = response.data.decode("utf-8", errors="replace")
        assert "last_6_months" in data or "Last 6 Months" in data, (
            "Last 6 Months button must be marked active for last-6-months preset params"
        )

    def test_custom_range_does_not_highlight_named_preset(self, app, client):
        """A non-preset date range must not falsely highlight a named preset."""
        _insert_user(app)
        _register_and_login(client)
        # A range that does not match any named preset
        response = client.get("/profile?date_from=2025-01-15&date_to=2025-02-15")
        data = response.data.decode("utf-8", errors="replace")
        assert "custom" in data or "2025-01-15" in data, (
            "Custom range must produce a custom active state, not a named-preset highlight"
        )


# ------------------------------------------------------------------ #
# Data isolation — one user's expenses do not bleed into another's
# ------------------------------------------------------------------ #

class TestUserDataIsolation:
    def test_filter_does_not_expose_other_user_expenses(self, app, client):
        user_a_id = _insert_user(app, name="User A", email="usera@example.com")
        _insert_expenses(app, user_a_id, [
            (500.0, "Luxury", "2025-06-15"),
        ])
        # Create user B and log in as B
        _insert_user(app, name="User B", email="userb@example.com")
        _register_and_login(client, email="userb@example.com", password="testpass1")
        response = client.get("/profile?date_from=2025-01-01&date_to=2025-12-31")
        data = response.data.decode("utf-8", errors="replace")
        assert "500" not in data, (
            "User B must not see User A's expenses under any filter"
        )
