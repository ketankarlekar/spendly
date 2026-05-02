
import os

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash

from database.db import get_db, init_db, seed_db, create_user, close_db, get_user_by_email

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-in-prod")
app.teardown_appcontext(close_db)


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not password:
            error = "All fields are required."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif create_user(name, email, password) is None:
            error = "An account with that email already exists."
        else:
            return redirect(url_for("login"))

        return render_template("register.html", error=error, name=name, email=email)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template("login.html", error="All fields are required.")

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.")

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        session["user_email"] = user["email"]
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    name = session.get("user_name", "")
    initials = "".join(part[0].upper() for part in name.split() if part)[:2]
    user = {
        "name": name,
        "email": session.get("user_email", ""),
        "member_since": "January 2024",
        "initials": initials,
    }

    stats = {
        "total_spent": 1284.50,
        "transaction_count": 12,
        "top_category": "Food",
    }

    transactions = [
        {"date": "2024-01-15", "description": "Grocery run",     "category": "Food",          "amount": 87.30},
        {"date": "2024-01-12", "description": "Bus pass",         "category": "Transport",     "amount": 45.00},
        {"date": "2024-01-10", "description": "Electricity bill", "category": "Bills",         "amount": 120.00},
        {"date": "2024-01-08", "description": "Gym membership",   "category": "Health",        "amount": 60.00},
        {"date": "2024-01-05", "description": "Netflix",          "category": "Entertainment", "amount": 15.99},
    ]

    categories = [
        {"name": "Food",          "total": 432.50, "percentage": 34},
        {"name": "Bills",         "total": 310.00, "percentage": 24},
        {"name": "Transport",     "total": 215.00, "percentage": 17},
        {"name": "Health",        "total": 180.00, "percentage": 14},
        {"name": "Entertainment", "total": 147.00, "percentage": 11},
    ]

    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
