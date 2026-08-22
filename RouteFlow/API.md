# API Reference

Base URL: `/api`. Interactive docs at `/docs` (Swagger) and `/redoc`.
All protected endpoints require `Authorization: Bearer <access_token>`.

## Conventions

- **Auth**: obtain tokens from `/api/auth/login`; send the access token as a Bearer header.
- **Errors**: consistent envelope

  ```json
  { "error": { "code": "INVALID_STATUS_TRANSITION", "message": "Cannot move order from DELIVERED to IN_TRANSIT." } }
  ```

- **Status codes**: `200` ok · `201` created · `204` no content · `400/422` validation ·
  `401` unauthenticated · `403` forbidden · `404` not found · `409` conflict · `429` rate limited.
- **Idempotency**: `POST /api/orders` honours an `Idempotency-Key` header.
- **Pagination**: list endpoints accept `page`, `page_size` and return `{items,total,page,pageSize,pages}`.

## Auth

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | public | Register a customer, returns user + tokens |
| POST | `/auth/login` | public | Log in, returns user + tokens |
| POST | `/auth/refresh` | public | Exchange a refresh token |
| GET | `/auth/me` | any | Current user |

## Orders (customer / shared)

| Method | Path | Role | Description |
|--------|------|------|-------------|
| POST | `/orders/quote` | customer, admin | Price quote with breakdown (no order created) |
| POST | `/orders` | customer, admin | Create order (admin passes `customer_id`) |
| GET | `/orders` | any | List orders, role-scoped, filterable |
| GET | `/orders/{id}` | owner/admin/assigned agent | Order detail + timeline + attempts |
| POST | `/orders/{id}/confirm` | owner, admin | Confirm a pending order |
| PATCH | `/orders/{id}/status` | assigned agent, admin | Advance status (state-machine checked) |
| POST | `/orders/{id}/fail` | assigned agent, admin | Mark out-for-delivery order failed |
| POST | `/orders/{id}/reschedule` | owner, admin | Reschedule a failed delivery (new attempt) |

### Quote example

Request `POST /api/orders/quote`:

```json
{
  "pickup_address": "12 Gandhi Road, Velachery",
  "drop_address": "5 North Usman Road, T Nagar",
  "length_cm": 50, "width_cm": 40, "height_cm": 30,
  "actual_weight_kg": 8, "order_type": "B2C", "payment_type": "COD"
}
```

Response:

```json
{
  "actual_weight": "8.000", "volumetric_weight": "12.000", "chargeable_weight": "12.000",
  "pickup_zone": "CHN-02", "drop_zone": "CHN-01", "zone_type": "INTER_ZONE",
  "order_type": "B2C", "payment_type": "COD",
  "base_charge": "170.00", "cod_surcharge": "30.00", "total_charge": "200.00", "currency": "INR"
}
```

## Tracking

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/tracking/{id}` | owner/admin/assigned agent | Full detail incl. timeline |
| GET | `/tracking/{id}/timeline` | same | Append-only status history |
| GET | `/tracking/{id}/attempts` | same | All delivery attempts |

## Agent self-service

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/agents/me` | agent | Profile |
| PATCH | `/agents/me/availability` | agent | Set `AVAILABLE`/`BUSY`/`OFFLINE` |
| PATCH | `/agents/me/location` | agent | Report `{latitude, longitude}` |

## Admin

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/admin/zones`, PATCH `/admin/zones/{id}` | Manage zones |
| GET/POST | `/admin/areas`, PATCH `/admin/areas/{id}` | Manage areas / move between zones |
| GET/POST | `/admin/rates`, PATCH/DELETE `/admin/rates/{id}` | Manage rate cards (overlap-checked) |
| GET | `/admin/cod-surcharges`, PUT `/admin/cod-surcharges` | Manage COD surcharges |
| GET/POST | `/admin/agents`, PATCH `/admin/agents/{id}` | Manage agents |
| GET | `/admin/orders` | All orders with filters (`status`, `zone_id`, `agent_id`, `order_type`, `payment_type`, `date_from`, `date_to`) |
| POST | `/admin/orders/{id}/assign` | Manual assignment `{agent_id, reason}` |
| POST | `/admin/orders/{id}/auto-assign` | Auto-assign; returns decision + ranking |
| POST | `/admin/orders/{id}/override` | Status override `{status, reason}` (audited) |

## Analytics & notifications

| Method | Path | Role | Description |
|--------|------|------|-------------|
| GET | `/analytics/summary` | admin | KPIs, orders by status/zone, daily volume, failure rate by zone |
| GET | `/notifications` | customer, admin | Notification history (role-scoped) |

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness — `{"status":"healthy"}` |
| GET | `/health/ready` | Readiness (checks DB) |
