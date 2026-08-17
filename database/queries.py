from datetime import datetime

from database.db import get_db


def _user_date_filter(user_id, date_from, date_to):
    where = "WHERE user_id = ?"
    params = [user_id]
    if date_from and date_to:
        where += " AND date BETWEEN ? AND ?"
        params += [date_from, date_to]
    return where, params


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT name, email, created_at FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()

    if row is None:
        return None

    member_since = datetime.strptime(row["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%B %Y")
    return {"name": row["name"], "email": row["email"], "member_since": member_since}


def get_summary_stats(user_id, date_from=None, date_to=None):
    conn = get_db()
    where, params = _user_date_filter(user_id, date_from, date_to)

    totals = conn.execute(
        f"SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS cnt FROM expenses {where}",
        params,
    ).fetchone()

    if totals["cnt"] == 0:
        conn.close()
        return {"total_spent": 0, "transaction_count": 0, "top_category": "—"}

    top = conn.execute(
        f"SELECT category FROM expenses {where} "
        "GROUP BY category ORDER BY SUM(amount) DESC LIMIT 1",
        params,
    ).fetchone()
    conn.close()

    return {
        "total_spent": totals["total"],
        "transaction_count": totals["cnt"],
        "top_category": top["category"],
    }


def get_recent_transactions(user_id, limit=10, date_from=None, date_to=None):
    conn = get_db()
    where, params = _user_date_filter(user_id, date_from, date_to)
    params.append(limit)

    rows = conn.execute(
        "SELECT date, description, category, amount FROM expenses "
        f"{where} ORDER BY date DESC, id DESC LIMIT ?",
        params,
    ).fetchall()
    conn.close()

    return [
        {"date": r["date"], "description": r["description"], "category": r["category"], "amount": r["amount"]}
        for r in rows
    ]


def get_category_breakdown(user_id, date_from=None, date_to=None):
    conn = get_db()
    where, params = _user_date_filter(user_id, date_from, date_to)

    rows = conn.execute(
        "SELECT category AS name, SUM(amount) AS amount FROM expenses "
        f"{where} GROUP BY category ORDER BY amount DESC",
        params,
    ).fetchall()
    conn.close()

    if not rows:
        return []

    total = sum(r["amount"] for r in rows)
    breakdown = [
        {"name": r["name"], "amount": r["amount"], "pct": round(r["amount"] / total * 100)}
        for r in rows
    ]

    remainder = 100 - sum(item["pct"] for item in breakdown)
    largest = max(breakdown, key=lambda item: item["amount"])
    largest["pct"] += remainder

    return breakdown


def insert_expense(user_id, amount, category, expense_date, description):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, expense_date, description),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()
