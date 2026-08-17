from database.db import get_db, get_user_by_email
from database.queries import insert_expense
from tests.conftest import register_new_user

DEMO_USER_ID = 1


# ------------------------------------------------------------------ #
# insert_expense                                                      #
# ------------------------------------------------------------------ #

def test_insert_expense_returns_row_id(client):
    expense_id = insert_expense(DEMO_USER_ID, 42.50, "Food", "2026-08-01", "Lunch")
    assert isinstance(expense_id, int)
    assert expense_id > 0


def test_insert_expense_persists_row(client):
    expense_id = insert_expense(DEMO_USER_ID, 15.00, "Transport", "2026-08-02", "Bus fare")
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()

    assert row["user_id"] == DEMO_USER_ID
    assert row["amount"] == 15.00
    assert row["category"] == "Transport"
    assert row["date"] == "2026-08-02"
    assert row["description"] == "Bus fare"


def test_insert_expense_null_description(client):
    expense_id = insert_expense(DEMO_USER_ID, 5.00, "Other", "2026-08-03", None)
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()

    assert row["description"] is None


# ------------------------------------------------------------------ #
# GET /expenses/add                                                   #
# ------------------------------------------------------------------ #

def test_add_expense_get_unauthenticated_redirects(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_add_expense_get_authenticated_renders_form(client):
    register_new_user(client)
    response = client.get("/expenses/add")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Add Expense" in body
    assert "Food" in body


# ------------------------------------------------------------------ #
# POST /expenses/add                                                  #
# ------------------------------------------------------------------ #

def test_add_expense_post_unauthenticated_redirects(client):
    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_add_expense_post_valid_redirects_to_profile(client):
    register_new_user(client)
    response = client.post(
        "/expenses/add",
        data={"amount": "25.50", "category": "Food", "date": "2026-08-05", "description": "Groceries"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


def test_add_expense_post_valid_creates_db_row(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    client.post(
        "/expenses/add",
        data={"amount": "25.50", "category": "Food", "date": "2026-08-05", "description": "Groceries"},
    )
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()
    conn.close()

    assert row["amount"] == 25.50
    assert row["category"] == "Food"
    assert row["date"] == "2026-08-05"
    assert row["description"] == "Groceries"


def test_add_expense_post_missing_amount(client):
    register_new_user(client)
    response = client.post(
        "/expenses/add",
        data={"amount": "", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 400
    assert "required" in response.get_data(as_text=True).lower()


def test_add_expense_post_zero_amount(client):
    register_new_user(client)
    response = client.post(
        "/expenses/add",
        data={"amount": "0", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 400
    assert "greater than zero" in response.get_data(as_text=True).lower()


def test_add_expense_post_negative_amount(client):
    register_new_user(client)
    response = client.post(
        "/expenses/add",
        data={"amount": "-5", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 400


def test_add_expense_post_non_numeric_amount(client):
    register_new_user(client)
    response = client.post(
        "/expenses/add",
        data={"amount": "abc", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 400
    assert "valid number" in response.get_data(as_text=True).lower()


def test_add_expense_post_description_too_long(client):
    register_new_user(client)
    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "2026-08-01", "description": "x" * 201},
    )
    assert response.status_code == 400
    assert "200 characters" in response.get_data(as_text=True)


def test_add_expense_post_invalid_category(client):
    register_new_user(client)
    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "NotACategory", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 400
    assert "category" in response.get_data(as_text=True).lower()


def test_add_expense_post_invalid_date(client):
    register_new_user(client)
    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "not-a-date", "description": ""},
    )
    assert response.status_code == 400
    assert "date" in response.get_data(as_text=True).lower()


def test_add_expense_post_missing_description_is_optional(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    response = client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 302
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM expenses WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()
    conn.close()

    assert row["description"] is None


def test_add_expense_post_does_not_leak_across_users(client):
    register_new_user(client)
    client.post(
        "/expenses/add",
        data={"amount": "10", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    conn = get_db()
    count = conn.execute(
        "SELECT COUNT(*) AS c FROM expenses WHERE user_id = ?", (DEMO_USER_ID,)
    ).fetchone()["c"]
    conn.close()

    assert count == 8


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def new_user_id_for(client):
    return get_user_by_email("new@example.com")["id"]
