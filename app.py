import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_user_by_email, init_db, seed_db

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not name or not email or not password or not confirm_password:
        flash("All fields are required.", "error")
        return render_template("register.html", name=name, email=email), 400

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template("register.html", name=name, email=email), 400

    try:
        create_user(name, email, password)
    except sqlite3.IntegrityError:
        flash("An account with this email already exists.", "error")
        return render_template("register.html", name=name, email=email), 400

    flash("Account created successfully. Please sign in.", "success")
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("profile"))

    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    user = get_user_by_email(email) if email and password else None

    if user is None or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.", "error")
        return render_template("login.html"), 400

    session["user_id"] = user["id"]
    flash(f"Welcome back, {user['name']}!", "success")
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = {
        "name": "Aditi Rao",
        "email": "aditi.rao@example.com",
        "initials": "AR",
        "member_since": "March 2024",
    }

    stats = [
        {"label": "Total spent", "value": "₹42,180", "note": "This month", "icon": "wallet"},
        {"label": "Transactions", "value": "24", "note": "Last 30 days", "icon": "swap"},
        {"label": "Top category", "value": "Food", "note": "₹12,400 spent", "icon": "tag"},
    ]

    transactions = [
        {"date": "12 Aug 2026", "description": "Grocery run", "category": "Food", "amount": "₹1,850"},
        {"date": "10 Aug 2026", "description": "Metro card top-up", "category": "Transport", "amount": "₹500"},
        {"date": "08 Aug 2026", "description": "Electricity bill", "category": "Bills", "amount": "₹2,340"},
        {"date": "05 Aug 2026", "description": "Movie night", "category": "Entertainment", "amount": "₹800"},
    ]

    categories = [
        {"name": "Food", "total": "₹12,400", "percent": 40},
        {"name": "Bills", "total": "₹9,300", "percent": 30},
        {"name": "Transport", "total": "₹6,200", "percent": 20},
        {"name": "Entertainment", "total": "₹3,100", "percent": 10},
    ]

    return render_template(
        "profile.html", user=user, stats=stats,
        transactions=transactions, categories=categories,
    )


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
