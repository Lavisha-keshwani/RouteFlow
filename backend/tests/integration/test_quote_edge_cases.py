"""Integration tests: quote edge cases and pricing correctness via the API."""


def _payload(**overrides):
    base = {
        "pickup_address": "10 Main Road, Velachery",
        "drop_address": "22 Beach Ave, Adyar",
        "length_cm": 20,
        "width_cm": 20,
        "height_cm": 20,
        "actual_weight_kg": 5,
        "order_type": "B2C",
        "payment_type": "PREPAID",
    }
    base.update(overrides)
    return base


def test_intra_zone_boundary_weight_uses_lower_bracket(client, customer_headers):
    # Both Velachery and Adyar are CHN-02; 5.0 kg sits on the (0,5] boundary.
    quote = client.post("/api/orders/quote", json=_payload(), headers=customer_headers).json()
    assert quote["zone_type"] == "INTRA_ZONE"
    assert quote["chargeable_weight"] == "5.000"
    assert quote["base_charge"] == "60.00"
    assert quote["total_charge"] == "60.00"


def test_volumetric_weight_wins_when_larger(client, customer_headers):
    # 50x40x30 -> 12kg volumetric > 8kg actual; inter-zone B2C (10,20] = 170.
    quote = client.post(
        "/api/orders/quote",
        json=_payload(
            drop_address="5 North Usman Road, T Nagar",
            length_cm=50,
            width_cm=40,
            height_cm=30,
            actual_weight_kg=8,
        ),
        headers=customer_headers,
    ).json()
    assert quote["volumetric_weight"] == "12.000"
    assert quote["chargeable_weight"] == "12.000"
    assert quote["zone_type"] == "INTER_ZONE"
    assert quote["base_charge"] == "170.00"


def test_unknown_pickup_zone_returns_error(client, customer_headers):
    resp = client.post(
        "/api/orders/quote",
        json=_payload(pickup_address="999 Nowhere Blvd, Faketown"),
        headers=customer_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "ZONE_NOT_FOUND"


def test_weight_above_configured_range_has_no_rate(client, customer_headers):
    resp = client.post(
        "/api/orders/quote",
        json=_payload(length_cm=10, width_cm=10, height_cm=10, actual_weight_kg=25),
        headers=customer_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "RATE_CARD_NOT_FOUND"


def test_cod_without_configured_surcharge_errors(client, admin_headers, customer_headers):
    # Deactivate the B2C COD surcharge, then a COD quote must fail clearly.
    client.put(
        "/api/admin/cod-surcharges",
        json={"order_type": "B2C", "amount": 30, "is_active": False},
        headers=admin_headers,
    )
    resp = client.post(
        "/api/orders/quote",
        json=_payload(payment_type="COD"),
        headers=customer_headers,
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "COD_SURCHARGE_NOT_FOUND"


def test_zero_dimension_is_validation_error(client, customer_headers):
    resp = client.post(
        "/api/orders/quote", json=_payload(length_cm=0), headers=customer_headers
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_idempotency_key_prevents_duplicate_orders(client, customer_headers):
    headers = {**customer_headers, "Idempotency-Key": "order-key-123"}
    first = client.post("/api/orders", json=_payload(), headers=headers)
    second = client.post("/api/orders", json=_payload(), headers=headers)
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    listing = client.get("/api/orders", headers=customer_headers).json()
    assert listing["total"] == 1
