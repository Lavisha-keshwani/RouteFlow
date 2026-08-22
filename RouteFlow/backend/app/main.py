"""RouteFlow FastAPI application factory and entry point."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler  # noqa: F401  (kept for reference)
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import __version__
from app.core.config import settings
from app.core.rate_limit import limiter
from app.middleware.error_handlers import register_exception_handlers
from app.middleware.request_context import RequestContextMiddleware
from app.routers import (
    admin,
    agents,
    analytics,
    auth,
    health,
    notifications,
    orders,
    tracking,
)
from app.utils.logging import configure_logging

configure_logging("DEBUG" if settings.DEBUG else "INFO")

DESCRIPTION = """
**RouteFlow** — a configurable last-mile delivery management platform.

Roles: `CUSTOMER`, `DELIVERY_AGENT`, `ADMIN`. Authenticate via `/api/auth/login`
and send the access token as a `Bearer` header. Authorization is enforced
server-side on every protected endpoint.

Highlights: configurable rate engine, automatic zone detection, intelligent
agent assignment, an immutable order-status timeline, and a first-class failed
delivery / reschedule workflow.
"""

app = FastAPI(
    title=settings.APP_NAME,
    version=__version__,
    description=DESCRIPTION,
    openapi_tags=[
        {"name": "auth", "description": "Registration, login and tokens."},
        {"name": "orders", "description": "Quote, create, track and manage orders."},
        {"name": "tracking", "description": "Immutable order timeline."},
        {"name": "agents", "description": "Delivery-agent self-service."},
        {"name": "admin", "description": "Zones, areas, rates, agents, assignment."},
        {"name": "analytics", "description": "Operational metrics (admin)."},
        {"name": "notifications", "description": "Notification history."},
        {"name": "health", "description": "Liveness and readiness."},
    ],
)

# --- Rate limiting ---
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# --- Request context / logging ---
app.add_middleware(RequestContextMiddleware)

# --- Error handling ---
register_exception_handlers(app)


@app.exception_handler(RateLimitExceeded)
async def _rate_limited(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": {
                "code": "RATE_LIMITED",
                "message": "Too many requests. Please slow down.",
            }
        },
    )


# --- Routes ---
app.include_router(health.router)
api = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=api)
app.include_router(orders.router, prefix=api)
app.include_router(tracking.router, prefix=api)
app.include_router(agents.router, prefix=api)
app.include_router(admin.router, prefix=api)
app.include_router(analytics.router, prefix=api)
app.include_router(notifications.router, prefix=api)


@app.get("/", tags=["health"], summary="Service metadata")
def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }
