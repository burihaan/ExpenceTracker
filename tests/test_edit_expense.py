from database.db import get_db, get_user_by_email
from database.queries import get_expense_by_id, insert_expense, update_expense
from tests.conftest import register_new_user

DEMO_USER_ID = 1


# ------------------------------------------------------------------ #
# get_expense_by_id                                                   #
# ------------------------------------------------------------------ #

def test_get_expense_by_id_returns_expense_for_owner(client):
    expense_id = insert_expense(DEMO_USER_ID, 42.50, "Food", "2026-08-01", "Lunch")
    expense = get_expense_by_id(expense_id, DEMO_USER_ID)

    assert expense["id"] == expense_id
    assert expense["amount"] == 42.50
    assert expense["category"] == "Food"
    assert expense["date"] == "2026-08-01"
    assert expense["description"] == "Lunch"


def test_get_expense_by_id_returns_none_for_wrong_user(client):
    expense_id = insert_expense(DEMO_USER_ID, 42.50, "Food", "2026-08-01", "Lunch")
    assert get_expense_by_id(expense_id, DEMO_USER_ID + 999) is None


def test_get_expense_by_id_returns_none_for_nonexistent_id(client):
    assert get_expense_by_id(999999, DEMO_USER_ID) is None


# ------------------------------------------------------------------ #
# update_expense                                                      #
# ------------------------------------------------------------------ #

def test_update_expense_updates_row_for_owner(client):
    expense_id = insert_expense(DEMO_USER_ID, 10.00, "Food", "2026-08-01", "Lunch")
    rows_affected = update_expense(expense_id, DEMO_USER_ID, 99.00, "Bills", "2026-08-02", "Rent")

    assert rows_affected == 1
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()

    assert row["amount"] == 99.00
    assert row["category"] == "Bills"
    assert row["date"] == "2026-08-02"
    assert row["description"] == "Rent"


def test_update_expense_no_effect_for_wrong_user(client):
    expense_id = insert_expense(DEMO_USER_ID, 10.00, "Food", "2026-08-01", "Lunch")
    rows_affected = update_expense(expense_id, DEMO_USER_ID + 999, 99.00, "Bills", "2026-08-02", "Rent")

    assert rows_affected == 0
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()

    assert row["amount"] == 10.00
    assert row["category"] == "Food"


# ------------------------------------------------------------------ #
# GET /expenses/<id>/edit                                             #
# ------------------------------------------------------------------ #

def test_edit_expense_get_unauthenticated_redirects(client):
    expense_id = insert_expense(DEMO_USER_ID, 10.00, "Food", "2026-08-01", "Lunch")
    response = client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_edit_expense_get_own_expense_renders_prefilled_form(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 42.50, "Food", "2026-08-01", "Lunch")

    response = client.get(f"/expenses/{expense_id}/edit")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "Edit Expense" in body
    assert 'value="42.5"' in body
    assert 'value="2026-08-01"' in body
    assert 'value="Lunch"' in body


def test_edit_expense_get_prefilled_category_selected(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 42.50, "Bills", "2026-08-01", "Rent")

    response = client.get(f"/expenses/{expense_id}/edit")
    body = response.get_data(as_text=True)

    assert 'value="Bills" selected' in body


def test_edit_expense_get_other_users_expense_returns_404(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 42.50, "Food", "2026-08-01", "Lunch")

    client.get("/logout")
    register_new_user(client, name="Other User", email="other@example.com")
    response = client.get(f"/expenses/{expense_id}/edit")
    assert response.status_code == 404


def test_edit_expense_get_nonexistent_id_returns_404(client):
    register_new_user(client)
    response = client.get("/expenses/999999/edit")
    assert response.status_code == 404


# ------------------------------------------------------------------ #
# POST /expenses/<id>/edit                                            #
# ------------------------------------------------------------------ #

def test_edit_expense_post_unauthenticated_redirects(client):
    expense_id = insert_expense(DEMO_USER_ID, 10.00, "Food", "2026-08-01", "Lunch")
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "20", "category": "Food", "date": "2026-08-02", "description": ""},
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_edit_expense_post_valid_redirects_to_profile(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "25.50", "category": "Bills", "date": "2026-08-05", "description": "Electricity"},
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


def test_edit_expense_post_valid_updates_db_row(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "25.50", "category": "Bills", "date": "2026-08-05", "description": "Electricity"},
    )
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()

    assert row["amount"] == 25.50
    assert row["category"] == "Bills"
    assert row["date"] == "2026-08-05"
    assert row["description"] == "Electricity"


def test_edit_expense_post_other_users_expense_returns_404(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    client.get("/logout")
    register_new_user(client, name="Other User", email="other@example.com")
    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "999", "category": "Bills", "date": "2026-08-05", "description": ""},
    )
    assert response.status_code == 404

    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row["amount"] == 10.00


def test_edit_expense_post_missing_amount(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 400
    assert "required" in response.get_data(as_text=True).lower()


def test_edit_expense_post_zero_amount(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "0", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 400
    assert "greater than zero" in response.get_data(as_text=True).lower()


def test_edit_expense_post_non_numeric_amount(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "abc", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 400
    assert "valid number" in response.get_data(as_text=True).lower()


def test_edit_expense_post_invalid_category(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "10", "category": "NotACategory", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 400
    assert "category" in response.get_data(as_text=True).lower()


def test_edit_expense_post_invalid_date(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "10", "category": "Food", "date": "not-a-date", "description": ""},
    )
    assert response.status_code == 400
    assert "date" in response.get_data(as_text=True).lower()


def test_edit_expense_post_clears_description(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.post(
        f"/expenses/{expense_id}/edit",
        data={"amount": "10", "category": "Food", "date": "2026-08-01", "description": ""},
    )
    assert response.status_code == 302

    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row["description"] is None


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def new_user_id_for(client):
    return get_user_by_email("new@example.com")["id"]
