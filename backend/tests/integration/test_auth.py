"""Integration tests for authentication and RBAC."""
from app.seeds.seed_data import CUSTOMER_EMAIL, DEMO_PASSWORD


def test_register_and_login(client):
    resp = client.post(
        "/api/auth/register",
        json={"email": "newuser@example.com", "password": "Secret123!", "full_name": "New User"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["user"]["role"] == "CUSTOMER"
    assert body["tokens"]["access_token"]


def test_duplicate_email_rejected(client):
    payload = {"email": "dup@example.com", "password": "Secret123!", "full_name": "Dup"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    resp = client.post("/api/auth/register", json=payload)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DUPLICATE_RESOURCE"


def test_wrong_password_returns_401(client):
    resp = client.post(
        "/api/auth/login", json={"email": CUSTOMER_EMAIL, "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "AUTHENTICATION_ERROR"


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_returns_current_user(client, customer_headers):
    resp = client.get("/api/auth/me", headers=customer_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == CUSTOMER_EMAIL
