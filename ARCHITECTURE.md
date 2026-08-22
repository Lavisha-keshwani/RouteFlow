# Architecture

RouteFlow is a **modular monolith**. A single FastAPI application is internally split into clean
layers with strict dependency direction: `routers → services → repositories/domain → models`.

## Layers

```
┌─────────────────────────────────────────────────────────────┐
│ routers/        HTTP endpoints. Thin. Parse, authorize, call │
│                 a service, serialize the result.             │
├─────────────────────────────────────────────────────────────┤
│ services/       Business orchestration & transactions.       │
│                 OrderService, PricingService, AssignmentSvc, │
│                 AgentService, RateService, ZoneService,      │
│                 AnalyticsService, AuditService, AuthService. │
├─────────────────────────────────────────────────────────────┤
│ domain/         Pure logic. No FastAPI, no DB.               │
│                 pricing, zones, state_machine, assignment,   │
│                 geo, enums, errors.                          │
├─────────────────────────────────────────────────────────────┤
│ repositories/   Query objects (OrderRepository: filtering,   │
│                 pagination, eager loading).                  │
├─────────────────────────────────────────────────────────────┤
│ models/         SQLAlchemy ORM (source of truth for schema). │
└─────────────────────────────────────────────────────────────┘
```

Cross-cutting: `core/` (config, database, security, dependencies, rate-limit),
`middleware/` (request-id + structured logging, centralized error handling),
`notifications/` (provider abstraction + dispatch), `utils/` (logging, id generation).

## Why these boundaries

- **Thin routers** keep HTTP concerns (status codes, auth dependencies, serialization) out of
  business logic and make services reusable (e.g. the seeder drives `OrderService` directly).
- **A pure domain layer** isolates the most valuable, most-tested logic from frameworks and the
  database. Every rule that an evaluator cares about — volumetric weight, rate selection, legal
  status transitions, assignment scoring — is a pure function.
- **Repository for orders** centralizes complex, security-sensitive query construction
  (role scoping, pagination, filters) and prevents accidental "load everything" queries.

## Request lifecycle

1. `RequestContextMiddleware` assigns an `X-Request-ID`, binds it (and later the user id) to a
   context variable used by the JSON logger, and logs method/path/status/duration.
2. Auth dependencies (`get_current_user`, `require_roles`, ownership helpers) validate the JWT
   and enforce RBAC **server-side**.
3. The router calls a service. Services own the transaction boundary (`commit`/`rollback`).
4. Domain functions compute results; repositories run queries; models persist.
5. Errors raise typed `AppError`s; a global handler renders a consistent
   `{"error": {code, message, details}}` envelope. Unexpected exceptions are logged with a stack
   trace and returned as an opaque `500` (no leakage).

## Key domain modules

- **`domain/pricing.py`** — volumetric & chargeable weight, `PriceBreakdown`, overlap check.
- **`domain/zones.py`** — address normalization + longest-match area resolution.
- **`domain/state_machine.py`** — the transition table and helpers (`can_transition`, …).
- **`domain/assignment.py`** — weighted scoring (`distance`, `zone`, `workload`, `freshness`)
  producing a ranked, explainable decision.
- **`domain/geo.py`** — Haversine distance.

## Concurrency & consistency

- Agent assignment locks candidate rows (`SELECT … FOR UPDATE`) and re-checks capacity inside the
  transaction, so two concurrent assignments can't exceed capacity.
- Order creation is **idempotent** via a stored `Idempotency-Key`.
- Money is `Numeric`; timestamps are UTC; enums are stored as checked `VARCHAR` for portability.

## Notifications

`NotificationService` builds a message, persists a `Notification` row, then attempts delivery via
a channel provider (`EmailNotificationProvider`, `SMSNotificationProvider`). Any provider failure
is recorded on the row (`status = FAILED`) but **never** propagates — an email outage cannot roll
back an order status change.

## Frontend

A Vite + React **(JavaScript/JSX)** SPA styled with **Tailwind CSS v4**. `AuthContext` holds the
session; TanStack Query manages server state with caching and invalidation; role-based routing
guards each area; a small Tailwind component kit (`components/ui.jsx`) keeps the UI consistent. The
API client attaches the JWT and normalizes the backend error envelope into user-facing toasts.

---

## UML & diagrams

### Component / deployment view

```mermaid
flowchart TB
    subgraph Browser
        SPA["React SPA (Vite build)"]
    end
    subgraph Server["FastAPI process"]
        MW["middleware: request-id · errors · rate-limit"]
        RT["routers"]
        SVC["services"]
        DOM["domain (pure)"]
        REPO["repositories"]
        ORM["models (SQLAlchemy)"]
        NOT["notifications"]
    end
    DB[("PostgreSQL")]
    EXT["Email / SMS providers"]
    SPA -->|"/api + JWT"| MW --> RT --> SVC
    SVC --> DOM
    SVC --> REPO --> ORM --> DB
    SVC --> NOT --> EXT
```

### Class diagram — services (the orchestration brains)

```mermaid
classDiagram
    class OrderService {
        +create_order(data, actor, idempotency_key)
        +confirm_order(order_id, actor)
        +assign_agent_manual(order_id, agent_id, actor)
        +auto_assign(order_id, actor)
        +update_status(order_id, status, actor)
        +fail_delivery(order_id, reason, actor)
        +reschedule(order_id, actor, new_date)
        +admin_override_status(order_id, status, actor)
    }
    class PricingService {
        +compute(request) PriceBreakdown
        +quote(request) QuoteResponse
    }
    class AssignmentService {
        +select_for_order(order) AssignmentDecision
    }
    class RateService {
        +lookup_rate_card(order_type, zone_type, weight)
        +get_cod_surcharge_amount(order_type)
    }
    class ZoneService {
        +detect_zone(address)
    }
    class AgentService {
        +engage(agent)
        +release(agent)
    }
    class NotificationService {
        +notify(order, event)
    }
    class AuditService {
        +record(actor, action, entity)
    }
    OrderService --> PricingService
    OrderService --> AssignmentService
    OrderService --> AgentService
    OrderService --> NotificationService
    OrderService --> AuditService
    PricingService --> ZoneService
    PricingService --> RateService
```

### Class diagram — core domain entities

```mermaid
classDiagram
    class Order {
        +order_number
        +status
        +order_type
        +payment_type
        +zone_type
        +base_charge
        +cod_surcharge
        +total_charge
        +rate_card_id
    }
    class Package {
        +length_cm
        +width_cm
        +height_cm
        +actual_weight_kg
        +volumetric_weight_kg
        +chargeable_weight_kg
    }
    class DeliveryAttempt {
        +attempt_number
        +status
        +failure_reason
        +assignment_score
    }
    class OrderStatusHistory {
        +old_status
        +new_status
        +actor_role
        +created_at
    }
    class DeliveryAgent {
        +status
        +active_orders
        +max_active_orders
        +is_assignable()
    }
    Customer "1" --> "*" Order : places
    DeliveryAgent "0..1" --> "*" Order : assigned
    Order "1" --> "1" Package
    Order "1" --> "*" DeliveryAttempt
    Order "1" --> "*" OrderStatusHistory : append-only
    Zone "1" --> "*" Area
    Zone "1" --> "*" Order : pickup/drop
    RateCard "1" --> "*" Order : snapshot
    DeliveryAgent "1" --> "*" DeliveryAttempt
```

### Sequence — auto-assignment scoring

```mermaid
sequenceDiagram
    participant OS as OrderService
    participant AS as AssignmentService
    participant DB as DB (row locks)
    OS->>AS: select_for_order(order)
    AS->>DB: SELECT candidate agents FOR UPDATE
    DB-->>AS: available, in-capacity agents
    AS->>AS: score = 0.40·distance + 0.30·zone + 0.20·workload + 0.10·freshness
    AS-->>OS: ranked list + explanation ("why this agent")
    OS->>DB: engage best agent, ASSIGNED, write attempt + history
```

### Sequence — failed delivery → reschedule

```mermaid
sequenceDiagram
    actor D as Agent
    actor C as Customer
    participant OS as OrderService
    D->>OS: fail(order, reason)
    OS->>OS: attempt.FAILED · order.FAILED · release agent
    OS-->>C: notification (FAILED)
    C->>OS: reschedule(order, new_date)
    OS->>OS: new DeliveryAttempt · FAILED→RESCHEDULED→ASSIGNED
    OS->>OS: auto-assign fresh agent (prefer ≠ previous)
    OS-->>C: notification (RESCHEDULED + ASSIGNED)
```

