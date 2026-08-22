"""Integration tests: admin override, analytics, notifications and smoke checks."""

ORDER = {
    "pickup_address": "10 Main Road, Velachery",
    "drop_address": "5 North Usman Road, T Nagar",
    "length_cm": 30,
    "width_cm": 20,
    "height_cm": 15,
    "actual_weight_kg": 4,
    "order_type": "B2C",
    "payment_type": "COD",
}


def _confirmed_order(client, customer_headers):
    order = client.post("/api/orders", json=ORDER, headers=customer_headers).json()
    client.post(f"/api/orders/{order['id']}/confirm", headers=customer_headers)
    return order["id"]


def test_admin_override_bypasses_state_machine_but_records_history(client, customer_headers, admin_headers):
    order_id = _confirmed_order(client, customer_headers)
    # CONFIRMED -> DELIVERED is not a legal forward transition, but admins may override.
    resp = client.post(
        f"/api/admin/orders/{order_id}/override",
        json={"status": "DELIVERED", "reason": "Delivered manually, system out of sync"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    detail = resp.json()
    assert detail["status"] == "DELIVERED"
    assert detail["delivered_at"] is not None

    transitions = [(h["old_status"], h["new_status"]) for h in detail["status_history"]]
    assert ("CONFIRMED", "DELIVERED") in transitions


def test_normal_status_update_still_rejects_illegal_jump(client, customer_headers, admin_headers):
    order_id = _confirmed_order(client, customer_headers)
    resp = client.patch(
        f"/api/orders/{order_id}/status", json={"status": "DELIVERED"}, headers=admin_headers
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_notifications_recorded_on_status_change(client, customer_headers):
    _confirmed_order(client, customer_headers)
    resp = client.get("/api/notifications", headers=customer_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] >= 1
    events = {n["event_type"] for n in body["items"]}
    assert "ORDER_CONFIRMED" in events


def test_analytics_summary_is_admin_only(client, customer_headers, admin_headers):
    assert client.get("/api/analytics/summary", headers=customer_headers).status_code == 403

    resp = client.get("/api/analytics/summary", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    for key in (
        "total_orders",
        "delivery_success_rate",
        "revenue",
        "orders_by_status",
        "agent_utilization",
    ):
        assert key in body


def test_analytics_reflects_delivered_revenue(client, customer_headers, admin_headers):
    order_id = _confirmed_order(client, customer_headers)
    client.post(f"/api/admin/orders/{order_id}/auto-assign", headers=admin_headers)
    for status in ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"]:
        client.patch(
            f"/api/orders/{order_id}/status", json={"status": status}, headers=admin_headers
        )
    summary = client.get("/api/analytics/summary", headers=admin_headers).json()
    assert summary["delivered"] >= 1
    # COD B2C inter-zone (0,5] = 80 + 30 = 110 realised revenue.
    assert float(summary["revenue"]) >= 110.0


def test_smoke_health_root_and_openapi(client):
    assert client.get("/health").json() == {"status": "healthy"}
    assert client.get("/").json()["service"] == "RouteFlow"
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    assert "/api/orders/quote" in schema.json()["paths"]
