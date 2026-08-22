"""Integration tests: admin configuration (zones, areas, rates, COD)."""


def test_admin_creates_zone_area_and_rate(client, admin_headers):
    zone = client.post(
        "/api/admin/zones",
        json={"code": "TST-09", "name": "Test Zone", "city": "Chennai"},
        headers=admin_headers,
    )
    assert zone.status_code == 201, zone.text
    zone_id = zone.json()["id"]

    area = client.post(
        "/api/admin/areas",
        json={"name": "Testville", "zone_id": zone_id},
        headers=admin_headers,
    )
    assert area.status_code == 201, area.text

    rate = client.post(
        "/api/admin/rates",
        json={
            "order_type": "B2C",
            "zone_type": "INTRA_ZONE",
            "min_weight_kg": 20,
            "max_weight_kg": 30,
            "base_charge": 200,
        },
        headers=admin_headers,
    )
    assert rate.status_code == 201, rate.text


def test_rate_card_overlap_is_rejected(client, admin_headers):
    # Seed already has B2C INTRA brackets (0,5], (5,10], (10,20]; (4,10] overlaps.
    resp = client.post(
        "/api/admin/rates",
        json={
            "order_type": "B2C",
            "zone_type": "INTRA_ZONE",
            "min_weight_kg": 4,
            "max_weight_kg": 10,
            "base_charge": 99,
        },
        headers=admin_headers,
    )
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "OVERLAPPING_WEIGHT_RANGE"


def test_moving_area_to_another_zone_changes_detection(client, admin_headers, customer_headers):
    """Move an area between zones and confirm zone detection follows the change."""
    # New isolated area in CHN-01.
    zones = client.get("/api/admin/zones", headers=admin_headers).json()
    chn01 = next(z for z in zones if z["code"] == "CHN-01")
    chn02 = next(z for z in zones if z["code"] == "CHN-02")

    area = client.post(
        "/api/admin/areas",
        json={"name": "Movetown", "zone_id": chn01["id"]},
        headers=admin_headers,
    ).json()

    payload = {
        "pickup_address": "1 Test Road, Movetown",
        "drop_address": "5 North Usman Road, T Nagar",
        "length_cm": 10,
        "width_cm": 10,
        "height_cm": 10,
        "actual_weight_kg": 2,
        "order_type": "B2C",
        "payment_type": "PREPAID",
    }
    # Movetown + T Nagar both in CHN-01 -> intra-zone.
    q1 = client.post("/api/orders/quote", json=payload, headers=customer_headers).json()
    assert q1["zone_type"] == "INTRA_ZONE"

    # Move Movetown to CHN-02 -> now inter-zone.
    moved = client.patch(
        f"/api/admin/areas/{area['id']}",
        json={"zone_id": chn02["id"]},
        headers=admin_headers,
    )
    assert moved.status_code == 200, moved.text
    q2 = client.post("/api/orders/quote", json=payload, headers=customer_headers).json()
    assert q2["zone_type"] == "INTER_ZONE"


def test_cod_surcharge_upsert_updates_quote(client, admin_headers, customer_headers):
    client.put(
        "/api/admin/cod-surcharges",
        json={"order_type": "B2C", "amount": 55},
        headers=admin_headers,
    )
    payload = {
        "pickup_address": "10 Main Road, Velachery",
        "drop_address": "22 Beach Ave, Adyar",
        "length_cm": 20,
        "width_cm": 20,
        "height_cm": 20,
        "actual_weight_kg": 5,
        "order_type": "B2C",
        "payment_type": "COD",
    }
    quote = client.post("/api/orders/quote", json=payload, headers=customer_headers).json()
    assert quote["cod_surcharge"] == "55.00"
    # Intra-zone B2C (0,5] = 60 base + 55 COD = 115.
    assert quote["base_charge"] == "60.00"
    assert quote["total_charge"] == "115.00"
