import calendar
import sqlite3
from datetime import date, datetime

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from database.db import create_user, get_user_by_email, init_db, seed_db
from database.queries import (
    get_category_breakdown,
    get_recent_transactions,
    get_summary_stats,
    get_user_by_id,
)

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-in-production"


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _months_ago(reference_date, months):
    # month_index counts months since year 0, Jan=0; // and % roll negative
    # values back across a year boundary (e.g. Jan - 3 -> Oct of prev. year).
    month_index = reference_date.month - 1 - months
    year = reference_date.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(reference_date.day, last_day))


def _match_preset(date_from, date_to, preset_ranges):
    if date_from is None and date_to is None:
        return "all_time"
    return next(
        (name for name, (f, t) in preset_ranges.items() if (date_from, date_to) == (f, t)),
        None,
    )


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

    user_id = session["user_id"]
    today = date.today()

    parsed_from = _parse_date(request.args.get("date_from"))
    parsed_to = _parse_date(request.args.get("date_to"))

    if parsed_from and parsed_to and parsed_from > parsed_to:
        flash("Start date must be before end date.", "error")
        parsed_from = parsed_to = None

    date_from = parsed_from.isoformat() if parsed_from else None
    date_to = parsed_to.isoformat() if parsed_to else None

    preset_ranges = {
        "this_month": (today.replace(day=1).isoformat(), today.isoformat()),
        "last_3_months": (_months_ago(today, 3).isoformat(), today.isoformat()),
        "last_6_months": (_months_ago(today, 6).isoformat(), today.isoformat()),
    }

    active_preset = _match_preset(date_from, date_to, preset_ranges)
    filter_note = "All Time" if active_preset == "all_time" else "Filtered"

    profile_user = get_user_by_id(user_id)
    stats_raw = get_summary_stats(user_id, date_from=date_from, date_to=date_to)

    initials = "".join(word[0] for word in profile_user["name"].split()[:2]).upper()
    user = {
        "name": profile_user["name"],
        "email": profile_user["email"],
        "initials": initials,
        "member_since": profile_user["member_since"],
    }

    stats = [
        {"label": "Total spent", "value": f"₹{stats_raw['total_spent']:,.2f}", "note": filter_note, "icon": "wallet"},
        {"label": "Transactions", "value": str(stats_raw["transaction_count"]), "note": filter_note, "icon": "swap"},
        {"label": "Top category", "value": stats_raw["top_category"], "note": "", "icon": "tag"},
    ]

    transactions = [
        {
            "date": t["date"],
            "description": t["description"],
            "category": t["category"],
            "amount": f"₹{t['amount']:,.2f}",
        }
        for t in get_recent_transactions(user_id, date_from=date_from, date_to=date_to)
    ]

    categories = [
        {
            "name": c["name"],
            "total": f"₹{c['amount']:,.2f}",
            "percent": min(100, max(10, round(c["pct"] / 10) * 10)),
        }
        for c in get_category_breakdown(user_id, date_from=date_from, date_to=date_to)
    ]

    return render_template(
        "profile.html", user=user, stats=stats,
        transactions=transactions, categories=categories,
        selected_from=date_from, selected_to=date_to,
        active_preset=active_preset, preset_ranges=preset_ranges,
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
