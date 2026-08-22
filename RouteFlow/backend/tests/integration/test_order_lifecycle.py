"""Integration test: full order lifecycle and price-snapshot immutability."""
from decimal import Decimal


def _quote_payload():
    return {
        "pickup_address": "12 Gandhi Road, Velachery",
        "drop_address": "5 North Usman Road, T Nagar",
        "length_cm": 50,
        "width_cm": 40,
        "height_cm": 30,
        "actual_weight_kg": 8,
        "order_type": "B2C",
        "payment_type": "COD",
    }


def test_quote_detects_zones_and_prices(client, customer_headers):
    resp = client.post("/api/orders/quote", json=_quote_payload(), headers=customer_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Velachery (CHN-02) -> T Nagar (CHN-01) is inter-zone.
    assert body["zone_type"] == "INTER_ZONE"
    assert body["pickup_zone"] == "CHN-02"
    assert body["drop_zone"] == "CHN-01"
    # volumetric 12kg > actual 8kg -> bracket 10-20 B2C inter = 170 + COD 30 = 200
    assert Decimal(str(body["chargeable_weight"])) == Decimal("12.000")
    assert Decimal(str(body["base_charge"])) == Decimal("170.00")
    assert Decimal(str(body["cod_surcharge"])) == Decimal("30.00")
    assert Decimal(str(body["total_charge"])) == Decimal("200.00")


def test_full_lifecycle_to_delivered(client, customer_headers, admin_headers):
    create = client.post("/api/orders", json=_quote_payload(), headers=customer_headers)
    assert create.status_code == 201, create.text
    order = create.json()
    order_id = order["id"]
    assert order["status"] == "PENDING_CONFIRMATION"
    assert order["order_number"].startswith("RF-")

    assert client.post(f"/api/orders/{order_id}/confirm", headers=customer_headers).status_code == 200
    assigned = client.post(f"/api/admin/orders/{order_id}/auto-assign", headers=admin_headers)
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["decision"]["explanation"]

    for status in ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"]:
        resp = client.patch(
            f"/api/orders/{order_id}/status", json={"status": status}, headers=admin_headers
        )
        assert resp.status_code == 200, resp.text

    detail = client.get(f"/api/orders/{order_id}", headers=customer_headers).json()
    assert detail["status"] == "DELIVERED"
    assert detail["delivered_at"] is not None
    # Immutable timeline records every transition.
    new_statuses = [h["new_status"] for h in detail["status_history"]]
    assert new_statuses == [
        "PENDING_CONFIRMATION",
        "CONFIRMED",
        "ASSIGNED",
        "PICKED_UP",
        "IN_TRANSIT",
        "OUT_FOR_DELIVERY",
        "DELIVERED",
    ]


def test_invalid_status_transition_rejected(client, customer_headers, admin_headers):
    order = client.post("/api/orders", json=_quote_payload(), headers=customer_headers).json()
    order_id = order["id"]
    client.post(f"/api/orders/{order_id}/confirm", headers=customer_headers)
    # Jump straight to DELIVERED without assignment/pickup -> invalid.
    resp = client.patch(
        f"/api/orders/{order_id}/status", json={"status": "DELIVERED"}, headers=admin_headers
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"


def test_price_snapshot_is_immutable_after_rate_change(client, customer_headers, admin_headers):
    created = client.post("/api/orders", json=_quote_payload(), headers=customer_headers).json()
    order_id = created["id"]
    original_total = Decimal(str(created["total_charge"]))
    client.post(f"/api/orders/{order_id}/confirm", headers=customer_headers)

    # Admin raises the B2C inter-zone 10-20kg rate.
    rates = client.get(
        "/api/admin/rates", params={"order_type": "B2C", "zone_type": "INTER_ZONE"}, headers=admin_headers
    ).json()
    target = next(r for r in rates if Decimal(str(r["max_weight_kg"])) == Decimal("20.000"))
    upd = client.patch(
        f"/api/admin/rates/{target['id']}", json={"base_charge": 999}, headers=admin_headers
    )
    assert upd.status_code == 200, upd.text

    # Existing order keeps its snapshot price.
    after = client.get(f"/api/orders/{order_id}", headers=customer_headers).json()
    assert Decimal(str(after["total_charge"])) == original_total

    # A fresh quote reflects the new rate.
    new_quote = client.post("/api/orders/quote", json=_quote_payload(), headers=customer_headers).json()
    assert Decimal(str(new_quote["base_charge"])) == Decimal("999.00")


def test_idempotent_order_creation(client, customer_headers):
    headers = {**customer_headers, "Idempotency-Key": "abc-123"}
    first = client.post("/api/orders", json=_quote_payload(), headers=headers)
    second = client.post("/api/orders", json=_quote_payload(), headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
