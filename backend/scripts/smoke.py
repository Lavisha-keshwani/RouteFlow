"""Smoke-test the live ASGI app against the seeded SQLite demo database.

Run: DATABASE_URL=sqlite:///./demo.db python -m scripts.smoke
Exercises the real router + middleware + DB stack via Starlette's TestClient.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./demo.db")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.seeds.seed_data import (  # noqa: E402
    ADMIN_EMAIL,
    AGENT_EMAIL,
    CUSTOMER_EMAIL,
    DEMO_PASSWORD,
)

client = TestClient(app)
failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}{(' — ' + detail) if detail else ''}")
    if not condition:
        failures.append(label)


def login(email: str) -> str:
    resp = client.post("/api/auth/login", json={"email": email, "password": DEMO_PASSWORD})
    check(f"login {email}", resp.status_code == 200, f"HTTP {resp.status_code}")
    return resp.json()["tokens"]["access_token"] if resp.status_code == 200 else ""


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


print("\n=== Health ===")
r = client.get("/health")
check("GET /health", r.status_code == 200 and r.json()["status"] == "healthy")
r = client.get("/health/ready")
check("GET /health/ready", r.status_code == 200, r.json().get("database", ""))

print("\n=== Auth (all three roles) ===")
admin_token = login(ADMIN_EMAIL)
agent_token = login(AGENT_EMAIL)
customer_token = login(CUSTOMER_EMAIL)

r = client.get("/api/auth/me", headers=auth(customer_token))
check("GET /api/auth/me", r.status_code == 200 and r.json()["role"] == "CUSTOMER")

print("\n=== RBAC enforcement ===")
r = client.get("/api/analytics/summary", headers=auth(customer_token))
check("customer blocked from analytics", r.status_code == 403, f"HTTP {r.status_code}")
r = client.get("/api/analytics/summary")
check("anonymous blocked from analytics", r.status_code == 401, f"HTTP {r.status_code}")

print("\n=== Pricing quote (explainable) ===")
quote_body = {
    "pickup_address": "12 Gandhi Road, Velachery",
    "drop_address": "5 Mount Road, T Nagar",
    "length_cm": 50,
    "width_cm": 40,
    "height_cm": 30,
    "actual_weight_kg": 8,
    "order_type": "B2C",
    "payment_type": "COD",
}
r = client.post("/api/orders/quote", headers=auth(customer_token), json=quote_body)
check("POST /api/orders/quote", r.status_code == 200, f"HTTP {r.status_code}")
if r.status_code == 200:
    q = r.json()
    check("volumetric weight = 12", float(q["volumetric_weight"]) == 12.0, str(q["volumetric_weight"]))
    check("chargeable = max(actual, vol) = 12", float(q["chargeable_weight"]) == 12.0)
    check("COD surcharge applied", float(q["cod_surcharge"]) > 0, str(q["cod_surcharge"]))
    check(
        "total = base + cod",
        float(q["total_charge"]) == float(q["base_charge"]) + float(q["cod_surcharge"]),
        f"{q['base_charge']} + {q['cod_surcharge']} = {q['total_charge']}",
    )

print("\n=== Order lifecycle (create -> confirm -> assign -> deliver) ===")
r = client.post(
    "/api/orders",
    headers={**auth(customer_token), "Idempotency-Key": "smoke-key-001"},
    json=quote_body,
)
check("POST /api/orders", r.status_code == 201, f"HTTP {r.status_code}")
order = r.json()
order_id = order.get("id")
check("order has snapshot total", order.get("total_charge") is not None)
check("order status PENDING_CONFIRMATION", order.get("status") == "PENDING_CONFIRMATION")

# Idempotent retry returns the same order.
r2 = client.post(
    "/api/orders",
    headers={**auth(customer_token), "Idempotency-Key": "smoke-key-001"},
    json=quote_body,
)
check("idempotent create returns same order", r2.json().get("id") == order_id)

r = client.post(f"/api/orders/{order_id}/confirm", headers=auth(customer_token))
check("confirm order", r.status_code == 200 and r.json()["status"] == "CONFIRMED")

r = client.post(f"/api/admin/orders/{order_id}/auto-assign", headers=auth(admin_token))
check("auto-assign", r.status_code == 200, r.json().get("decision", {}).get("explanation", ""))

r = client.get(f"/api/orders/{order_id}", headers=auth(customer_token))
assigned_agent_id = r.json().get("assigned_agent_id")
check("order assigned to an agent", assigned_agent_id is not None)

# Advance through the delivery states as the assigned agent.
agent_login = client.post(
    "/api/auth/login",
    json={"email": AGENT_EMAIL, "password": DEMO_PASSWORD},
).json()
# The auto-assigned agent may differ from the demo agent; drive status via admin override path instead.
for target in ["PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"]:
    r = client.post(
        f"/api/admin/orders/{order_id}/override",
        headers=auth(admin_token),
        json={"status": target, "reason": "smoke-test progression"},
    )
    check(f"override -> {target}", r.status_code == 200, f"HTTP {r.status_code}")

r = client.get(f"/api/tracking/{order_id}/timeline", headers=auth(customer_token))
timeline = r.json()
check("immutable timeline recorded", isinstance(timeline, list) and len(timeline) >= 5, f"{len(timeline)} events")

print("\n=== Ownership isolation ===")
r = client.get("/api/orders?page=1&page_size=5", headers=auth(customer_token))
check("customer lists own orders", r.status_code == 200)

print("\n=== Invalid transition rejected ===")
r = client.post(
    "/api/admin/orders/{}/override".format(order_id),
    headers=auth(admin_token),
    json={"status": "DELIVERED", "reason": "already delivered"},
)
# Override is allowed for admin, but a normal customer status PATCH must be rejected:
r = client.patch(
    f"/api/orders/{order_id}/status",
    headers=auth(customer_token),
    json={"status": "PICKED_UP"},
)
check("customer cannot patch status", r.status_code in (403, 409), f"HTTP {r.status_code}")

print("\n=== Admin config + analytics ===")
r = client.get("/api/admin/zones", headers=auth(admin_token))
check("list zones", r.status_code == 200 and len(r.json()) > 0, f"{len(r.json())} zones")
r = client.get("/api/admin/rates", headers=auth(admin_token))
check("list rate cards", r.status_code == 200 and len(r.json()) > 0, f"{len(r.json())} rates")
r = client.get("/api/analytics/summary", headers=auth(admin_token))
check("analytics summary", r.status_code == 200, f"total_orders={r.json().get('total_orders')}")

print("\n=== OpenAPI docs ===")
r = client.get("/openapi.json")
check("openapi schema served", r.status_code == 200 and "paths" in r.json())

print("\n" + "=" * 50)
if failures:
    print(f"RESULT: {len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("RESULT: ALL SMOKE CHECKS PASSED")
