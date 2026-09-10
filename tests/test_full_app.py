def register(client):
    response = client.post(
        "/api/auth/register",
        json={"name": "Nimal", "email": "nimal@example.com", "password": "password123"},
    )
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['token']}"}


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_complete_finance_flow(client):
    headers = register(client)
    assert client.get("/api/me", headers=headers).json()["name"] == "Nimal"

    account = client.post(
        "/api/accounts",
        headers=headers,
        json={"name": "Salary Account", "kind": "Bank", "balance": "1000"},
    )
    assert account.status_code == 201
    account_id = account.json()["id"]

    card = client.post(
        "/api/cards",
        headers=headers,
        json={
            "name": "Main Card",
            "card_type": "Debit",
            "last_four": "4242",
            "account_id": account_id,
            "limit_amount": 0,
        },
    )
    assert card.status_code == 201

    expense = client.post(
        "/api/transactions",
        headers=headers,
        json={
            "kind": "expense",
            "description": "Lunch",
            "amount": "250.50",
            "category": "Food",
            "payment_mode": "UPI",
            "account_id": account_id,
            "to_account_id": None,
            "transacted_on": "2026-09-10",
            "notes": "",
        },
    )
    assert expense.status_code == 201
    assert client.get("/api/transactions", headers=headers).json()["total"] == 1
    filtered = client.get(
        "/api/transactions?category=Food&min_amount=200&max_amount=300&page=1&size=10",
        headers=headers,
    )
    assert filtered.json()["total"] == 1

    dashboard = client.get("/api/dashboard", headers=headers).json()
    assert dashboard["spent"] == "250.50"
    assert dashboard["categories"][0]["name"] == "Food"
    assert dashboard["monthly_spent"] == "250.50"

    notifications = client.get("/api/notifications", headers=headers)
    assert notifications.status_code == 200

    parsed = client.post(
        "/api/ai/parse", headers=headers, json={"text": "Spent 350 on dinner"}
    )
    assert parsed.status_code == 200
    assert parsed.json()["category"] == "Food"

    chat = client.post(
        "/api/ai/chat", headers=headers, json={"message": "What is my balance?"}
    )
    assert chat.status_code == 200
    assert "balance" in chat.json()["answer"]

    assert (
        client.delete(
            f"/api/transactions/{expense.json()['id']}", headers=headers
        ).status_code
        == 204
    )


def test_authentication_is_required(client):
    assert client.get("/api/transactions").status_code == 401
