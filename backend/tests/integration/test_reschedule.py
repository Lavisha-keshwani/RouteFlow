"""Integration test: failed-delivery and reschedule workflow."""
from datetime import date, timedelta


PAYLOAD = {
    "pickup_address": "5 Beach Road, Adyar",
    "drop_address": "17 Nungambakkam High Road, Nungambakkam",
    "length_cm": 25,
    "width_cm": 25,
    "height_cm": 25,
    "actual_weight_kg": 5,
    "order_type": "B2C",
    "payment_type": "COD",
}


def _create_and_advance(client, customer_headers, admin_headers, upto):
    order = client.post("/api/orders", json=PAYLOAD, headers=customer_headers).json()
    order_id = order["id"]
    client.post(f"/api/orders/{order_id}/confirm", headers=customer_headers)
    client.post(f"/api/admin/orders/{order_id}/auto-assign", headers=admin_headers)
    for status in ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY"]:
        client.patch(f"/api/orders/{order_id}/status", json={"status": status}, headers=admin_headers)
        if status == upto:
            break
    return order_id


def test_fail_then_reschedule_creates_new_attempt(client, customer_headers, admin_headers):
    order_id = _create_and_advance(client, customer_headers, admin_headers, "OUT_FOR_DELIVERY")

    fail = client.post(
        f"/api/orders/{order_id}/fail",
        json={"failure_reason": "CUSTOMER_UNAVAILABLE", "notes": "No answer"},
        headers=admin_headers,
    )
    assert fail.status_code == 200, fail.text
    assert fail.json()["status"] == "FAILED"

    new_date = (date.today() + timedelta(days=2)).isoformat()
    resched = client.post(
        f"/api/orders/{order_id}/reschedule",
        json={"new_date": new_date, "reason": "Customer requested new date"},
        headers=customer_headers,
    )
    assert resched.status_code == 200, resched.text
    detail = resched.json()
    # A new attempt is created; original failed attempt is preserved.
    assert len(detail["attempts"]) == 2
    assert detail["attempts"][0]["status"] == "FAILED"
    # Auto-reassigned -> back to ASSIGNED.
    assert detail["status"] == "ASSIGNED"
    assert detail["assigned_agent_id"] is not None

    # Timeline preserved the failure and reschedule events.
    statuses = [h["new_status"] for h in detail["status_history"]]
    assert "FAILED" in statuses
    assert "RESCHEDULED" in statuses


def test_delivered_order_cannot_be_rescheduled(client, customer_headers, admin_headers):
    order_id = _create_and_advance(client, customer_headers, admin_headers, "OUT_FOR_DELIVERY")
    client.patch(f"/api/orders/{order_id}/status", json={"status": "DELIVERED"}, headers=admin_headers)

    new_date = (date.today() + timedelta(days=2)).isoformat()
    resp = client.post(
        f"/api/orders/{order_id}/reschedule",
        json={"new_date": new_date},
        headers=customer_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "RESCHEDULE_NOT_ALLOWED"
