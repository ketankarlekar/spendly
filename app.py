
import datetime
import os

from flask import Flask, flash, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash

from database.db import get_db, init_db, seed_db, create_user, close_db, get_user_by_email
from database.queries import (
    get_user_by_id, get_summary_stats,
    get_recent_transactions, get_category_breakdown,
)

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
    db_user = get_user_by_id(session["user_id"])
    user = {
        "name": name,
        "email": session.get("user_email", ""),
        "member_since": db_user["member_since"] if db_user else "",
        "initials": initials,
    }

    raw_from = request.args.get("date_from", "").strip()
    raw_to = request.args.get("date_to", "").strip()
    date_from = date_to = None
    try:
        if raw_from:
            datetime.datetime.strptime(raw_from, "%Y-%m-%d")
            date_from = raw_from
        if raw_to:
            datetime.datetime.strptime(raw_to, "%Y-%m-%d")
            date_to = raw_to
    except ValueError:
        date_from = date_to = None

    if date_from and date_to and date_from > date_to:
        flash("Start date must be before end date.")
        date_from = date_to = None

    today = datetime.date.today()
    presets = {
        "this_month": (today.replace(day=1).isoformat(), today.isoformat()),
        "last_3_months": ((today - datetime.timedelta(days=90)).isoformat(), today.isoformat()),
        "last_6_months": ((today - datetime.timedelta(days=180)).isoformat(), today.isoformat()),
    }

    active_preset = "all_time"
    if date_from and date_to:
        active_preset = "custom"
        for preset_key, (pf, pt) in presets.items():
            if date_from == pf and date_to == pt:
                active_preset = preset_key
                break

    stats = get_summary_stats(session["user_id"], date_from, date_to)
    transactions = get_recent_transactions(session["user_id"], date_from=date_from, date_to=date_to)
    categories = get_category_breakdown(session["user_id"], date_from, date_to)

    return render_template("profile.html", user=user, stats=stats,
                           transactions=transactions, categories=categories,
                           date_from=date_from, date_to=date_to,
                           presets=presets, active_preset=active_preset)


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
