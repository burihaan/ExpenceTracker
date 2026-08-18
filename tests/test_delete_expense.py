from database.db import get_db, get_user_by_email
from database.queries import delete_expense_by_id, insert_expense
from tests.conftest import register_new_user

DEMO_USER_ID = 1


# ------------------------------------------------------------------ #
# delete_expense_by_id                                                #
# ------------------------------------------------------------------ #

def test_delete_expense_by_id_removes_row_for_owner(client):
    expense_id = insert_expense(DEMO_USER_ID, 42.50, "Food", "2026-08-01", "Lunch")

    delete_expense_by_id(expense_id, DEMO_USER_ID)

    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row is None, "Expected the expense row to be removed from the DB"


def test_delete_expense_by_id_no_effect_for_wrong_user(client):
    expense_id = insert_expense(DEMO_USER_ID, 42.50, "Food", "2026-08-01", "Lunch")

    rows_affected = delete_expense_by_id(expense_id, DEMO_USER_ID + 999)

    assert rows_affected == 0, "Expected 0 rows deleted when user_id does not match"
    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row is not None, "Expense belonging to another user must remain in the DB"
    assert row["amount"] == 42.50
    assert row["category"] == "Food"


def test_delete_expense_by_id_nonexistent_id_no_error(client):
    conn = get_db()
    count_before = conn.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()["c"]
    conn.close()

    rows_affected = delete_expense_by_id(999999, DEMO_USER_ID)

    assert rows_affected == 0, "Expected 0 rows deleted for a non-existent expense id"

    conn = get_db()
    count_after = conn.execute("SELECT COUNT(*) AS c FROM expenses").fetchone()["c"]
    conn.close()
    assert count_after == count_before, "Deleting a non-existent expense must not change the DB"


# ------------------------------------------------------------------ #
# POST /expenses/<id>/delete                                          #
# ------------------------------------------------------------------ #

def test_delete_expense_post_unauthenticated_redirects_to_login(client):
    expense_id = insert_expense(DEMO_USER_ID, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.post(f"/expenses/{expense_id}/delete")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]

    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row is not None, "Expense must not be deleted while unauthenticated"


def test_delete_expense_post_own_expense_redirects_to_profile(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.post(f"/expenses/{expense_id}/delete")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/profile")


def test_delete_expense_post_own_expense_removes_row_from_db(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    client.post(f"/expenses/{expense_id}/delete")

    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row is None, "Expense should no longer exist in the DB after deletion"


def test_delete_expense_post_deleted_expense_absent_from_profile(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Distinctive Lunch Description")

    client.post(f"/expenses/{expense_id}/delete")

    response = client.get("/profile")
    body = response.get_data(as_text=True)
    assert "Distinctive Lunch Description" not in body


def test_delete_expense_post_other_users_expense_returns_404(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    client.get("/logout")
    register_new_user(client, name="Other User", email="other@example.com")

    response = client.post(f"/expenses/{expense_id}/delete")
    assert response.status_code == 404

    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row is not None, "Expense belonging to another user must not be deleted"
    assert row["amount"] == 10.00


def test_delete_expense_post_nonexistent_id_returns_404(client):
    register_new_user(client)
    response = client.post("/expenses/999999/delete")
    assert response.status_code == 404


def test_delete_expense_get_not_allowed_returns_405(client):
    register_new_user(client)
    user_id = new_user_id_for(client)
    expense_id = insert_expense(user_id, 10.00, "Food", "2026-08-01", "Lunch")

    response = client.get(f"/expenses/{expense_id}/delete")
    assert response.status_code == 405

    conn = get_db()
    row = conn.execute("SELECT * FROM expenses WHERE id = ?", (expense_id,)).fetchone()
    conn.close()
    assert row is not None, "A GET request must never delete the expense"


# ------------------------------------------------------------------ #
# Helpers                                                              #
# ------------------------------------------------------------------ #

def new_user_id_for(client):
    return get_user_by_email("new@example.com")["id"]
