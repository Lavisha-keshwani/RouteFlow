# Rate Calculation

The rate engine is the heart of RouteFlow. **No business rates are hardcoded** — every charge is
resolved from admin-configured data at request time. The calculation is implemented as pure
functions in [`backend/app/domain/pricing.py`](backend/app/domain/pricing.py) and orchestrated by
[`PricingService`](backend/app/services/pricing_service.py).

## Inputs

| Input | Source |
|-------|--------|
| Pickup & drop address | Request |
| Dimensions `L × B × H` (cm) | Request |
| Actual weight (kg) | Request |
| Order type (`B2B` / `B2C`) | Request |
| Payment type (`PREPAID` / `COD`) | Request |
| Rate cards | Admin config (DB) |
| COD surcharges | Admin config (DB) |
| Area → Zone map | Admin config (DB) |

## Steps

### 1. Zone detection

Both addresses are normalized (lower-cased, punctuation stripped, whitespace collapsed) and
matched against the active Area→Zone map. The **longest** matching area name wins (so
`Anna Nagar West` beats `Anna Nagar`). If either address can't be mapped, the API returns
`ZONE_NOT_FOUND` — the system never guesses.

```
"12 Gandhi Road, Velachery"  → area "Velachery" → zone CHN-02
```

### 2. Volumetric & chargeable weight

```
volumetric_weight = (L × B × H) / VOLUMETRIC_DIVISOR      # divisor default 5000
chargeable_weight = max(actual_weight, volumetric_weight)
```

Example: `50 × 40 × 30 / 5000 = 12 kg` vs actual `8 kg` → **chargeable = 12 kg**.

### 3. Zone type

```
zone_type = INTRA_ZONE  if pickup_zone == drop_zone  else INTER_ZONE
```

### 4. Rate-card lookup

The engine selects the **active** rate card matching `(order_type, zone_type)` whose weight
bracket contains the chargeable weight. Brackets are **half-open `(min, max]`**, so a weight
exactly on a boundary falls into the lower bracket and brackets never overlap:

```
min_weight_kg < chargeable_weight <= max_weight_kg
```

If no bracket matches (e.g. weight above the configured range), the API returns
`RATE_CARD_NOT_FOUND`.

Example rate cards:

| Order | Zone | 0–5 kg | 5–10 kg | 10–20 kg |
|-------|------|--------|---------|----------|
| B2C | Intra | ₹60 | ₹90 | ₹130 |
| B2C | Inter | ₹80 | ₹120 | ₹170 |
| B2B | Intra | ₹80 | ₹120 | ₹180 |
| B2B | Inter | ₹100 | ₹150 | ₹220 |

### 5. COD surcharge

```
cod_surcharge = configured_surcharge(order_type)   if payment_type == COD  else 0
```

Configured per order type (demo: B2B ₹40, B2C ₹30). Prepaid always contributes ₹0. A missing COD
config for a COD order raises `COD_SURCHARGE_NOT_FOUND`.

### 6. Total

```
total_charge = base_charge + cod_surcharge
```

## Worked example

```
Dimensions 50×40×30 cm, actual 8 kg, B2C, COD, Velachery (CHN-02) → T Nagar (CHN-01)

volumetric   = 50×40×30 / 5000 = 12 kg
chargeable   = max(8, 12)      = 12 kg
zone_type    = INTER_ZONE      (CHN-02 ≠ CHN-01)
base_charge  = B2C/INTER/(10,20] = ₹170
cod_surcharge= ₹30
total        = ₹200
```

## Price immutability

When an order is confirmed, `base_charge`, `cod_surcharge`, `total_charge`, `chargeable_weight`
and `rate_card_id` are stored **on the order**. Later rate-card edits change only future quotes;
existing orders keep their snapshot. This is verified by an integration test
(`test_price_snapshot_is_immutable_after_rate_change`).

## Guarantees

- `Decimal`/`Numeric` throughout — no floating-point money.
- Overlapping weight brackets are rejected at configuration time (`OVERLAPPING_WEIGHT_RANGE`).
- All rules are admin-configurable without code changes or redeploys.
