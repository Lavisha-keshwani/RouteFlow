"""Integration tests for authorization and ownership enforcement."""
from tests.conftest import auth_header


PAYLOAD = {
    "pickup_address": "12 Gandhi Road, Velachery",
    "drop_address": "5 North Usman Road, T Nagar",
    "length_cm": 30,
    "width_cm": 20,
    "height_cm": 15,
    "actual_weight_kg": 3,
    "order_type": "B2C",
    "payment_type": "PREPAID",
}


def test_customer_cannot_view_another_customers_order(client, customer_headers):
    created = client.post("/api/orders", json=PAYLOAD, headers=customer_headers).json()
    order_id = created["id"]

    other = auth_header(client, "rahul@example.com")
    resp = client.get(f"/api/orders/{order_id}", headers=other)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "UNAUTHORIZED_ORDER_ACCESS"


def test_customer_cannot_access_admin_endpoints(client, customer_headers):
    resp = client.get("/api/admin/zones", headers=customer_headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "PERMISSION_DENIED"


def test_agent_cannot_create_rate_card(client, agent_headers):
    resp = client.post(
        "/api/admin/rates",
        json={
            "order_type": "B2C",
            "zone_type": "INTRA_ZONE",
            "min_weight_kg": 0,
            "max_weight_kg": 5,
            "base_charge": 50,
        },
        headers=agent_headers,
    )
    assert resp.status_code == 403


def test_unauthenticated_requests_rejected(client):
    assert client.get("/api/orders").status_code == 401
    assert client.get("/api/admin/agents").status_code == 401


def test_agent_cannot_update_unassigned_order(client, customer_headers, admin_headers, agent_headers):
    created = client.post("/api/orders", json=PAYLOAD, headers=customer_headers).json()
    order_id = created["id"]
    client.post(f"/api/orders/{order_id}/confirm", headers=customer_headers)

    # Agent that is not assigned to this order cannot advance it.
    resp = client.patch(
        f"/api/orders/{order_id}/status", json={"status": "PICKED_UP"}, headers=agent_headers
    )
    assert resp.status_code in (403, 409)


def test_overlapping_rate_bracket_rejected(client, admin_headers):
    resp = client.post(
        "/api/admin/rates",
        json={
            "order_type": "B2C",
            "zone_type": "INTRA_ZONE",
            "min_weight_kg": 4,
            "max_weight_kg": 8,
            "base_charge": 70,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "OVERLAPPING_WEIGHT_RANGE"
