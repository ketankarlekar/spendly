"""
Tests for Step 8: Edit Expense

Spec: .claude/specs/08-edit-expense.md

Covers:
- Auth guard on GET and POST
- 404 for non-existent expense id (GET and POST)
- 403 when the logged-in user does not own the expense (GET and POST)
- Happy-path GET: 200, form rendered, fields pre-filled with existing values
- Happy-path POST: DB row updated, redirect to /profile
- Updated values visible in /profile Recent Transactions list
- Edit link on each /profile transaction row points to the correct URL
- Validation errors: blank amount, zero amount, non-numeric amount, invalid
  category, malformed date — each must show an error and must NOT update the DB
- On validation failure the form re-renders with the submitted values pre-filled
- Optional description: empty string saves as NULL without error

Fixtures used from conftest.py: app, client
A module-level helper _register_and_login() and DB-insertion helpers follow
the same patterns established in test_date_filter.py.
"""

import pytest
from werkzeug.security import generate_password_hash

from database.db import get_db, get_expense_by_id


# ------------------------------------------------------------------ #
# Module-level helpers
# ------------------------------------------------------------------ #


def _register_and_login(
    client, email="owner@example.com", password="testpass1", name="Owner User"
):
    """Register a fresh user and log in; returns the email used."""
    client.post("/register", data={"name": name, "email": email, "password": password})
    client.post("/login", data={"email": email, "password": password})
    return email


def _insert_user(
    app, name="Owner User", email="owner@example.com", password="testpass1"
):
    """Insert a user directly into the DB and return their integer id."""
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password)),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def _insert_expense(
    app, user_id, amount=50.0, category="Food", date="2025-06-15", description="Lunch"
):
    """Insert one expense and return its integer id."""
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def _fetch_expense(app, expense_id):
    """Return the expense row as a dict (or None) from the DB."""
    with app.app_context():
        row = get_expense_by_id(expense_id)
        return dict(row) if row else None


def _edit_url(expense_id):
    return f"/expenses/{expense_id}/edit"


# ------------------------------------------------------------------ #
# Auth guard
# ------------------------------------------------------------------ #


class TestAuthGuard:
    """Unauthenticated requests must be redirected to /login."""

    def test_get_unauthenticated_redirects_to_login(self, client):
        response = client.get(_edit_url(999))
        assert response.status_code == 302, "GET must redirect unauthenticated user"
        assert (
            "/login" in response.headers["Location"]
        ), "Redirect target must be /login"

    def test_post_unauthenticated_redirects_to_login(self, client):
        response = client.post(
            _edit_url(999),
            data={
                "amount": "10.00",
                "category": "Food",
                "date": "2025-06-01",
                "description": "test",
            },
        )
        assert response.status_code == 302, "POST must redirect unauthenticated user"
        assert (
            "/login" in response.headers["Location"]
        ), "Redirect target must be /login"

    def test_get_unauthenticated_does_not_leak_data(self, app, client):
        """No expense data may be returned before authentication."""
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, amount=123.45)
        response = client.get(_edit_url(expense_id))
        assert (
            response.status_code == 302
        ), "Unauthenticated GET must redirect, not return expense data"


# ------------------------------------------------------------------ #
# 404 — non-existent expense id
# ------------------------------------------------------------------ #


class TestNotFound:
    """Requests for expense ids that do not exist must return 404."""

    def test_get_nonexistent_id_returns_404(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        response = client.get(_edit_url(999999))
        assert (
            response.status_code == 404
        ), "GET for non-existent expense id must return 404"

    def test_post_nonexistent_id_returns_404(self, app, client):
        _insert_user(app)
        _register_and_login(client)
        response = client.post(
            _edit_url(999999),
            data={
                "amount": "10.00",
                "category": "Food",
                "date": "2025-06-01",
                "description": "",
            },
        )
        assert (
            response.status_code == 404
        ), "POST for non-existent expense id must return 404"


# ------------------------------------------------------------------ #
# 403 — expense belongs to a different user
# ------------------------------------------------------------------ #


class TestOwnershipCheck:
    """Users must not be able to view or modify another user's expense."""

    def _setup_two_users(self, app, client):
        """
        Create owner (user A) with an expense.
        Log in as attacker (user B).
        Returns the expense id owned by user A.
        """
        owner_id = _insert_user(app, name="Owner", email="owner@example.com")
        expense_id = _insert_expense(app, owner_id, amount=77.0)

        # Register and log in as a second user
        _insert_user(
            app, name="Attacker", email="attacker@example.com", password="testpass1"
        )
        _register_and_login(
            client, email="attacker@example.com", password="testpass1", name="Attacker"
        )
        return expense_id

    def test_get_other_users_expense_returns_403(self, app, client):
        expense_id = self._setup_two_users(app, client)
        response = client.get(_edit_url(expense_id))
        assert (
            response.status_code == 403
        ), "GET on another user's expense must return 403"

    def test_post_other_users_expense_returns_403(self, app, client):
        expense_id = self._setup_two_users(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "1.00",
                "category": "Food",
                "date": "2025-01-01",
                "description": "",
            },
        )
        assert (
            response.status_code == 403
        ), "POST on another user's expense must return 403"

    def test_post_other_users_expense_does_not_modify_db(self, app, client):
        expense_id = self._setup_two_users(app, client)
        original = _fetch_expense(app, expense_id)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "1.00",
                "category": "Bills",
                "date": "2020-01-01",
                "description": "tampered",
            },
        )
        after = _fetch_expense(app, expense_id)
        assert (
            after["amount"] == original["amount"]
        ), "Amount must not be changed by a different user"
        assert (
            after["category"] == original["category"]
        ), "Category must not be changed by a different user"


# ------------------------------------------------------------------ #
# Happy path GET
# ------------------------------------------------------------------ #


class TestGetEditForm:
    """GET /expenses/<id>/edit must return 200 and a pre-filled form."""

    def test_get_returns_200(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.get(_edit_url(expense_id))
        assert (
            response.status_code == 200
        ), "GET edit form must return 200 for the owning user"

    def test_get_renders_edit_form_tag(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.get(_edit_url(expense_id))
        assert b"<form" in response.data, "Edit form page must contain a <form> element"

    def test_get_prefills_amount(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, amount=99.99)
        _register_and_login(client)
        response = client.get(_edit_url(expense_id))
        # The amount value should appear somewhere in the rendered HTML
        assert (
            b"99.99" in response.data
        ), "Existing amount must be pre-filled in the edit form"

    def test_get_prefills_category(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, category="Transport")
        _register_and_login(client)
        response = client.get(_edit_url(expense_id))
        data = response.data.decode("utf-8", errors="replace")
        # The selected category option should be marked selected
        assert (
            "Transport" in data
        ), "Existing category must appear pre-filled in the edit form"

    def test_get_prefills_date(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, date="2025-03-22")
        _register_and_login(client)
        response = client.get(_edit_url(expense_id))
        assert (
            b"2025-03-22" in response.data
        ), "Existing date must be pre-filled in the edit form"

    def test_get_prefills_description(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, description="Dinner at Mario's")
        _register_and_login(client)
        response = client.get(_edit_url(expense_id))
        assert (
            "Dinner at Mario".encode("utf-8") in response.data
        ), "Existing description must be pre-filled in the edit form"

    def test_get_form_action_points_to_correct_url(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.get(_edit_url(expense_id))
        data = response.data.decode("utf-8", errors="replace")
        expected_action = f"/expenses/{expense_id}/edit"
        assert expected_action in data, f"Form action must point to {expected_action}"

    def test_get_contains_all_seven_categories(self, app, client):
        """The category dropdown must list all seven allowed categories."""
        categories = [
            "Food",
            "Transport",
            "Bills",
            "Health",
            "Entertainment",
            "Shopping",
            "Other",
        ]
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.get(_edit_url(expense_id))
        data = response.data.decode("utf-8", errors="replace")
        for cat in categories:
            assert (
                cat in data
            ), f"Category '{cat}' must appear in the edit form dropdown"

    def test_get_extends_base_template(self, app, client):
        """The rendered page must include landmarks from base.html."""
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.get(_edit_url(expense_id))
        # base.html always renders a <html> or <body> tag
        assert (
            b"<html" in response.data or b"<!DOCTYPE" in response.data
        ), "Edit form must extend base.html and render a full HTML document"


# ------------------------------------------------------------------ #
# Happy path POST
# ------------------------------------------------------------------ #


class TestPostUpdateExpense:
    """Valid POST must update the DB row and redirect to /profile."""

    def test_valid_post_redirects_to_profile(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "25.00",
                "category": "Bills",
                "date": "2025-07-01",
                "description": "Updated description",
            },
        )
        assert response.status_code == 302, "Successful POST must redirect (302)"
        assert (
            "/profile" in response.headers["Location"]
        ), "Redirect after update must go to /profile"

    def test_valid_post_updates_amount_in_db(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, amount=10.00)
        _register_and_login(client)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "250.75",
                "category": "Food",
                "date": "2025-07-01",
                "description": "",
            },
        )
        row = _fetch_expense(app, expense_id)
        assert row is not None, "Expense row must still exist after update"
        assert (
            abs(row["amount"] - 250.75) < 0.001
        ), "Amount must be updated to 250.75 in the DB"

    def test_valid_post_updates_category_in_db(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, category="Food")
        _register_and_login(client)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "50.00",
                "category": "Health",
                "date": "2025-07-01",
                "description": "",
            },
        )
        row = _fetch_expense(app, expense_id)
        assert (
            row["category"] == "Health"
        ), "Category must be updated to 'Health' in the DB"

    def test_valid_post_updates_date_in_db(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, date="2025-01-01")
        _register_and_login(client)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "50.00",
                "category": "Food",
                "date": "2025-09-30",
                "description": "",
            },
        )
        row = _fetch_expense(app, expense_id)
        assert (
            row["date"] == "2025-09-30"
        ), "Date must be updated to '2025-09-30' in the DB"

    def test_valid_post_updates_description_in_db(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, description="Old description")
        _register_and_login(client)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "50.00",
                "category": "Food",
                "date": "2025-07-01",
                "description": "New description",
            },
        )
        row = _fetch_expense(app, expense_id)
        assert (
            row["description"] == "New description"
        ), "Description must be updated in the DB"

    def test_valid_post_empty_description_stores_null(self, app, client):
        """Empty description string must be treated as NULL when updating."""
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, description="Had a value")
        _register_and_login(client)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "50.00",
                "category": "Food",
                "date": "2025-07-01",
                "description": "",
            },
        )
        row = _fetch_expense(app, expense_id)
        assert (
            row["description"] is None or row["description"] == ""
        ), "Empty description must be stored as NULL (or empty) in the DB"

    def test_updated_values_appear_on_profile(self, app, client):
        """After a successful update the new values must show on /profile."""
        user_id = _insert_user(app)
        expense_id = _insert_expense(
            app, user_id, amount=10.00, category="Food", date="2025-07-01"
        )
        _register_and_login(client)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "333.33",
                "category": "Health",
                "date": "2025-08-15",
                "description": "Physio session",
            },
        )
        profile_response = client.get("/profile")
        data = profile_response.data.decode("utf-8", errors="replace")
        assert (
            "333.33" in data
        ), "Updated amount must appear in Recent Transactions on /profile"
        assert (
            "Health" in data
        ), "Updated category must appear in Recent Transactions on /profile"
        assert (
            "Physio session" in data
        ), "Updated description must appear in Recent Transactions on /profile"

    def test_post_with_decimal_amount_succeeds(self, app, client):
        """Amounts with cents must be accepted."""
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "0.01",
                "category": "Other",
                "date": "2025-07-01",
                "description": "",
            },
        )
        assert (
            response.status_code == 302
        ), "Minimum positive decimal amount (0.01) must be accepted"


# ------------------------------------------------------------------ #
# Edit link on /profile
# ------------------------------------------------------------------ #


class TestProfileEditLink:
    """Each transaction row on /profile must carry an Edit link to the correct URL."""

    def test_profile_shows_edit_link_for_expense(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.get("/profile")
        data = response.data.decode("utf-8", errors="replace")
        expected_href = f"/expenses/{expense_id}/edit"
        assert (
            expected_href in data
        ), f"Profile must contain an Edit link pointing to {expected_href}"

    def test_profile_edit_link_text_is_edit(self, app, client):
        user_id = _insert_user(app)
        _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.get("/profile")
        data = response.data.decode("utf-8", errors="replace")
        assert "Edit" in data, "Profile transaction row must contain 'Edit' link text"

    def test_profile_multiple_expenses_each_has_correct_edit_link(self, app, client):
        user_id = _insert_user(app)
        id1 = _insert_expense(app, user_id, amount=10.0, date="2025-05-01")
        id2 = _insert_expense(app, user_id, amount=20.0, date="2025-05-02")
        _register_and_login(client)
        response = client.get("/profile")
        data = response.data.decode("utf-8", errors="replace")
        assert (
            f"/expenses/{id1}/edit" in data
        ), f"Edit link for expense {id1} must appear on /profile"
        assert (
            f"/expenses/{id2}/edit" in data
        ), f"Edit link for expense {id2} must appear on /profile"

    def test_profile_no_expenses_no_edit_link(self, app, client):
        """When a user has no transactions no Edit links should appear."""
        _insert_user(app)
        _register_and_login(client)
        response = client.get("/profile")
        data = response.data.decode("utf-8", errors="replace")
        assert (
            "/edit" not in data
        ), "No Edit links should appear when the user has no expenses"


# ------------------------------------------------------------------ #
# Validation errors
# ------------------------------------------------------------------ #


class TestValidationErrors:
    """Invalid POST submissions must return an error page, not update the DB."""

    def _setup(self, app, client):
        """Create a user and one expense, log in, return expense_id."""
        user_id = _insert_user(app)
        expense_id = _insert_expense(
            app, user_id, amount=50.0, category="Food", date="2025-06-01"
        )
        _register_and_login(client)
        return expense_id

    # --- amount validation ---

    def test_blank_amount_shows_error(self, app, client):
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "",
                "category": "Food",
                "date": "2025-06-01",
                "description": "",
            },
        )
        assert (
            response.status_code == 200
        ), "Blank amount must re-render the form (200), not redirect"
        assert (
            b"Amount" in response.data
        ), "Error message about amount must appear when amount is blank"

    def test_blank_amount_does_not_update_db(self, app, client):
        expense_id = self._setup(app, client)
        original = _fetch_expense(app, expense_id)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "",
                "category": "Food",
                "date": "2025-06-01",
                "description": "",
            },
        )
        after = _fetch_expense(app, expense_id)
        assert (
            abs(after["amount"] - original["amount"]) < 0.001
        ), "DB row must not be updated when amount is blank"

    def test_zero_amount_shows_error(self, app, client):
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "0",
                "category": "Food",
                "date": "2025-06-01",
                "description": "",
            },
        )
        assert (
            response.status_code == 200
        ), "Zero amount must re-render the form (200), not redirect"
        assert (
            b"Amount" in response.data or b"positive" in response.data
        ), "Error message must mention amount or positive number for zero amount"

    def test_zero_amount_does_not_update_db(self, app, client):
        expense_id = self._setup(app, client)
        original = _fetch_expense(app, expense_id)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "0",
                "category": "Food",
                "date": "2025-06-01",
                "description": "",
            },
        )
        after = _fetch_expense(app, expense_id)
        assert (
            abs(after["amount"] - original["amount"]) < 0.001
        ), "DB row must not be updated when amount is zero"

    def test_negative_amount_shows_error(self, app, client):
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "-5.00",
                "category": "Food",
                "date": "2025-06-01",
                "description": "",
            },
        )
        assert (
            response.status_code == 200
        ), "Negative amount must re-render the form (200)"

    def test_nonnumeric_amount_shows_error(self, app, client):
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "not-a-number",
                "category": "Food",
                "date": "2025-06-01",
                "description": "",
            },
        )
        assert (
            response.status_code == 200
        ), "Non-numeric amount must re-render the form (200)"

    # --- category validation ---

    def test_invalid_category_shows_error(self, app, client):
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "10.00",
                "category": "InvalidCat",
                "date": "2025-06-01",
                "description": "",
            },
        )
        assert (
            response.status_code == 200
        ), "Invalid category must re-render the form (200)"
        assert (
            b"category" in response.data.lower() or b"valid" in response.data.lower()
        ), "Error message must mention category or valid selection"

    def test_invalid_category_does_not_update_db(self, app, client):
        expense_id = self._setup(app, client)
        original = _fetch_expense(app, expense_id)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "10.00",
                "category": "Luxury",
                "date": "2025-06-01",
                "description": "",
            },
        )
        after = _fetch_expense(app, expense_id)
        assert (
            after["category"] == original["category"]
        ), "Category must not be updated in the DB when an invalid category is submitted"

    def test_empty_category_shows_error(self, app, client):
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "10.00",
                "category": "",
                "date": "2025-06-01",
                "description": "",
            },
        )
        assert (
            response.status_code == 200
        ), "Empty category must re-render the form (200)"

    # --- date validation ---

    def test_malformed_date_shows_error(self, app, client):
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "10.00",
                "category": "Food",
                "date": "not-a-date",
                "description": "",
            },
        )
        assert (
            response.status_code == 200
        ), "Malformed date must re-render the form (200)"
        assert (
            b"date" in response.data.lower() or b"valid" in response.data.lower()
        ), "Error message must mention date or valid input"

    def test_malformed_date_does_not_update_db(self, app, client):
        expense_id = self._setup(app, client)
        original = _fetch_expense(app, expense_id)
        client.post(
            _edit_url(expense_id),
            data={
                "amount": "10.00",
                "category": "Food",
                "date": "32-13-2025",
                "description": "",
            },
        )
        after = _fetch_expense(app, expense_id)
        assert (
            after["date"] == original["date"]
        ), "Date must not be updated in the DB when a malformed date is submitted"

    def test_wrong_date_format_shows_error(self, app, client):
        """Date given as DD/MM/YYYY instead of YYYY-MM-DD must be rejected."""
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "10.00",
                "category": "Food",
                "date": "01/06/2025",
                "description": "",
            },
        )
        assert (
            response.status_code == 200
        ), "Wrong date format must re-render the form (200)"

    @pytest.mark.parametrize(
        "bad_date",
        [
            "",
            "2025/06/01",
            "June 1 2025",
            "01-06-2025",
            "20250601",
            "9999-99-99",
        ],
    )
    def test_various_bad_dates_rejected(self, app, client, bad_date):
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "10.00",
                "category": "Food",
                "date": bad_date,
                "description": "",
            },
        )
        assert (
            response.status_code == 200
        ), f"Bad date '{bad_date}' must re-render the form, not redirect"

    @pytest.mark.parametrize(
        "bad_amount,bad_category,bad_date",
        [
            ("", "Food", "2025-06-01"),
            ("0", "Food", "2025-06-01"),
            ("-1", "Food", "2025-06-01"),
            ("abc", "Food", "2025-06-01"),
            ("10.00", "Nope", "2025-06-01"),
            ("10.00", "Food", "bad-date"),
        ],
    )
    def test_invalid_submissions_do_not_redirect(
        self, app, client, bad_amount, bad_category, bad_date
    ):
        """Every invalid submission must stay on the form page, never redirect."""
        expense_id = self._setup(app, client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": bad_amount,
                "category": bad_category,
                "date": bad_date,
                "description": "",
            },
        )
        assert response.status_code == 200, (
            f"Invalid input (amount={bad_amount!r}, category={bad_category!r}, "
            f"date={bad_date!r}) must not redirect"
        )


# ------------------------------------------------------------------ #
# On validation failure — form re-populates with submitted values
# ------------------------------------------------------------------ #


class TestFormRepopulationOnError:
    """
    When POST validation fails the re-rendered form must contain the
    submitted values (not the original DB values), so the user does not
    lose their in-progress edits.
    """

    def test_submitted_amount_repopulated_after_bad_category(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, amount=10.0)
        _register_and_login(client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "88.88",
                "category": "INVALID",
                "date": "2025-06-01",
                "description": "keep me",
            },
        )
        assert (
            b"88.88" in response.data
        ), "Submitted amount must be repopulated after a category validation error"

    def test_submitted_date_repopulated_after_bad_amount(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, date="2025-01-01")
        _register_and_login(client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "",
                "category": "Food",
                "date": "2025-12-25",
                "description": "",
            },
        )
        assert (
            b"2025-12-25" in response.data
        ), "Submitted date must be repopulated after an amount validation error"

    def test_submitted_description_repopulated_after_bad_date(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, description="Old text")
        _register_and_login(client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "20.00",
                "category": "Food",
                "date": "not-a-date",
                "description": "Typed by user",
            },
        )
        assert (
            b"Typed by user" in response.data
        ), "Submitted description must be repopulated after a date validation error"

    def test_error_message_present_on_validation_failure(self, app, client):
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id)
        _register_and_login(client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "0",
                "category": "Food",
                "date": "2025-06-01",
                "description": "",
            },
        )
        # Template renders error inside class="auth-error" or similar wrapper
        assert (
            b"error" in response.data.lower() or b"Amount" in response.data
        ), "A visible error message must be present when validation fails"

    def test_submitted_category_repopulated_after_bad_date(self, app, client):
        """The selected category option must reflect the submitted value, not the original."""
        user_id = _insert_user(app)
        expense_id = _insert_expense(app, user_id, category="Food")
        _register_and_login(client)
        response = client.post(
            _edit_url(expense_id),
            data={
                "amount": "20.00",
                "category": "Shopping",
                "date": "bad-date",
                "description": "",
            },
        )
        data = response.data.decode("utf-8", errors="replace")
        assert (
            "Shopping" in data
        ), "Submitted category 'Shopping' must appear in the re-rendered form"


# ------------------------------------------------------------------ #
# Data isolation — own vs foreign expenses
# ------------------------------------------------------------------ #


class TestDataIsolation:
    """Expenses must only be visible and editable by their owner."""

    def test_user_can_only_see_own_expenses_via_edit_link_on_profile(self, app, client):
        """
        User B's edit links must not appear in User A's profile.
        """
        # User B has an expense
        user_b_id = _insert_user(app, name="User B", email="b@example.com")
        b_expense_id = _insert_expense(app, user_b_id, amount=500.0)

        # Log in as User A (different user, no expenses)
        _insert_user(app, name="User A", email="a@example.com")
        _register_and_login(client, email="a@example.com", name="User A")

        profile_response = client.get("/profile")
        data = profile_response.data.decode("utf-8", errors="replace")
        assert (
            f"/expenses/{b_expense_id}/edit" not in data
        ), "User A's profile must not contain edit links to User B's expenses"

    def test_get_edit_form_is_isolated_to_owner(self, app, client):
        """
        A user who owns an expense can GET the edit form;
        another logged-in user gets 403.
        """
        owner_id = _insert_user(app, name="Owner", email="owner2@example.com")
        expense_id = _insert_expense(app, owner_id)

        # Intruder logs in
        _insert_user(app, name="Intruder", email="intruder@example.com")
        _register_and_login(client, email="intruder@example.com", name="Intruder")
        response = client.get(_edit_url(expense_id))
        assert (
            response.status_code == 403
        ), "Intruder must receive 403, not the edit form"
