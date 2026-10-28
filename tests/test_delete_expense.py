from database.db import get_db


# ── helpers ──────────────────────────────────────────────────────────────────


def register_and_login(client, email="owner@example.com", password="password123"):
    client.post(
        "/register", data={"name": "Owner", "email": email, "password": password}
    )
    client.post("/login", data={"email": email, "password": password})


def insert_expense(
    app, user_id, amount=10.0, category="Food", date="2026-01-01", description="Test"
):
    with app.app_context():
        db = get_db()
        db.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        db.commit()
        return db.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_user_id(app, email):
    with app.app_context():
        row = (
            get_db()
            .execute("SELECT id FROM users WHERE email = ?", (email,))
            .fetchone()
        )
        return row["id"]


def expense_exists(app, expense_id):
    with app.app_context():
        row = (
            get_db()
            .execute("SELECT id FROM expenses WHERE id = ?", (expense_id,))
            .fetchone()
        )
        return row is not None


# ── route tests ───────────────────────────────────────────────────────────────


def test_delete_unauthenticated_redirects_to_login(client, app):
    user_id = None
    client.post(
        "/register",
        data={"name": "Owner", "email": "o@example.com", "password": "password123"},
    )
    user_id = get_user_id(app, "o@example.com")
    expense_id = insert_expense(app, user_id)

    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_delete_nonexistent_expense_returns_404(client):
    register_and_login(client)
    response = client.post("/expenses/99999/delete")
    assert response.status_code == 404


def test_delete_wrong_owner_returns_403(client, app):
    # Register owner and create expense
    client.post(
        "/register",
        data={"name": "Owner", "email": "owner@example.com", "password": "password123"},
    )
    owner_id = get_user_id(app, "owner@example.com")
    expense_id = insert_expense(app, owner_id)

    # Log in as a different user
    client.post(
        "/register",
        data={"name": "Other", "email": "other@example.com", "password": "password123"},
    )
    client.post(
        "/login", data={"email": "other@example.com", "password": "password123"}
    )

    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 403


def test_delete_get_method_returns_405(client):
    register_and_login(client)
    response = client.get("/expenses/1/delete")
    assert response.status_code == 405


def test_delete_success_redirects_to_profile(client, app):
    register_and_login(client)
    user_id = get_user_id(app, "owner@example.com")
    expense_id = insert_expense(app, user_id)

    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


def test_delete_removes_expense_from_db(client, app):
    register_and_login(client)
    user_id = get_user_id(app, "owner@example.com")
    expense_id = insert_expense(app, user_id)

    assert expense_exists(app, expense_id)
    client.post(f"/expenses/{expense_id}/delete")
    assert not expense_exists(app, expense_id)


def test_delete_expense_absent_from_profile_page(client, app):
    register_and_login(client)
    user_id = get_user_id(app, "owner@example.com")
    insert_expense(app, user_id, description="Gone soon")

    with app.app_context():
        expense_id = (
            get_db()
            .execute("SELECT id FROM expenses WHERE description = ?", ("Gone soon",))
            .fetchone()["id"]
        )

    client.post(f"/expenses/{expense_id}/delete")
    response = client.get("/profile")
    assert b"Gone soon" not in response.data


# ── template tests ────────────────────────────────────────────────────────────


def test_profile_shows_delete_button_for_each_transaction(client, app):
    register_and_login(client)
    user_id = get_user_id(app, "owner@example.com")
    insert_expense(app, user_id, description="Lunch")

    response = client.get("/profile")
    assert response.status_code == 200
    assert b"btn-delete" in response.data


def test_profile_delete_form_posts_to_correct_url(client, app):
    register_and_login(client)
    user_id = get_user_id(app, "owner@example.com")
    expense_id = insert_expense(app, user_id, description="Coffee")

    response = client.get("/profile")
    assert f"/expenses/{expense_id}/delete".encode() in response.data
