"""Integration tests: manual/auto assignment, capacity and agent availability."""
from app.seeds.seed_data import AGENT_EMAIL


CONFIRMABLE = {
    "pickup_address": "10 Main Road, Velachery",
    "drop_address": "22 Beach Ave, Adyar",
    "length_cm": 20,
    "width_cm": 20,
    "height_cm": 20,
    "actual_weight_kg": 3,
    "order_type": "B2C",
    "payment_type": "PREPAID",
}


def _agent_id(client, admin_headers, email=AGENT_EMAIL):
    agents = client.get("/api/admin/agents", headers=admin_headers).json()
    return next(a["id"] for a in agents if a["email"] == email)


def _create_confirmed(client, customer_headers):
    order = client.post("/api/orders", json=CONFIRMABLE, headers=customer_headers).json()
    client.post(f"/api/orders/{order['id']}/confirm", headers=customer_headers)
    return order["id"]


def test_manual_assignment_then_agent_updates_own_order(client, customer_headers, admin_headers, agent_headers):
    order_id = _create_confirmed(client, customer_headers)
    agent_id = _agent_id(client, admin_headers)

    assign = client.post(
        f"/api/admin/orders/{order_id}/assign",
        json={"agent_id": agent_id, "reason": "Nearest agent"},
        headers=admin_headers,
    )
    assert assign.status_code == 200, assign.text

    detail = client.get(f"/api/orders/{order_id}", headers=admin_headers).json()
    assert detail["status"] == "ASSIGNED"
    assert detail["assigned_agent_id"] == agent_id

    # The assigned agent can now advance the status.
    picked = client.patch(
        f"/api/orders/{order_id}/status", json={"status": "PICKED_UP"}, headers=agent_headers
    )
    assert picked.status_code == 200, picked.text
    assert picked.json()["status"] == "PICKED_UP"


def test_manual_assignment_capacity_exceeded(client, customer_headers, admin_headers):
    agent_id = _agent_id(client, admin_headers)
    client.patch(
        f"/api/admin/agents/{agent_id}", json={"max_active_orders": 1}, headers=admin_headers
    )

    first = _create_confirmed(client, customer_headers)
    second = _create_confirmed(client, customer_headers)

    ok = client.post(
        f"/api/admin/orders/{first}/assign", json={"agent_id": agent_id}, headers=admin_headers
    )
    assert ok.status_code == 200, ok.text

    over = client.post(
        f"/api/admin/orders/{second}/assign", json={"agent_id": agent_id}, headers=admin_headers
    )
    assert over.status_code == 409
    assert over.json()["error"]["code"] == "AGENT_CAPACITY_EXCEEDED"


def test_auto_assign_returns_scored_ranking(client, customer_headers, admin_headers):
    order_id = _create_confirmed(client, customer_headers)
    resp = client.post(f"/api/admin/orders/{order_id}/auto-assign", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["candidates_considered"] >= 1
    assert body["decision"]["score"] > 0
    assert body["decision"]["explanation"]
    assert len(body["ranking"]) >= 1


def test_auto_assign_with_no_available_agent(client, customer_headers, admin_headers):
    agents = client.get("/api/admin/agents", headers=admin_headers).json()
    for a in agents:
        client.patch(
            f"/api/admin/agents/{a['id']}", json={"is_active": False}, headers=admin_headers
        )
    order_id = _create_confirmed(client, customer_headers)
    resp = client.post(f"/api/admin/orders/{order_id}/auto-assign", headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "NO_AGENT_AVAILABLE"


def test_agent_cannot_update_unassigned_order(client, customer_headers, agent_headers):
    order = client.post("/api/orders", json=CONFIRMABLE, headers=customer_headers).json()
    client.post(f"/api/orders/{order['id']}/confirm", headers=customer_headers)
    resp = client.patch(
        f"/api/orders/{order['id']}/status", json={"status": "PICKED_UP"}, headers=agent_headers
    )
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "UNAUTHORIZED_ORDER_ACCESS"


def test_agent_self_service_availability_and_location(client, agent_headers):
    avail = client.patch(
        "/api/agents/me/availability", json={"status": "OFFLINE"}, headers=agent_headers
    )
    assert avail.status_code == 200
    assert avail.json()["status"] == "OFFLINE"

    loc = client.patch(
        "/api/agents/me/location",
        json={"latitude": 13.05, "longitude": 80.23},
        headers=agent_headers,
    )
    assert loc.status_code == 200
    assert loc.json()["current_latitude"] == 13.05

    me = client.get("/api/agents/me", headers=agent_headers).json()
    assert me["current_longitude"] == 80.23
