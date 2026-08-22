"""Domain-level exceptions.

These carry a stable machine-readable ``code`` and an HTTP ``status_code`` so the
global exception handler can produce consistent error envelopes without leaking
Python stack traces to clients.
"""
from __future__ import annotations

from typing import Any, Optional


class AppError(Exception):
    """Base class for all expected application errors."""

    code: str = "APP_ERROR"
    status_code: int = 400

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or {}


# --- 400 / validation-ish ---
class ValidationError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 400


class InvalidWeightError(AppError):
    code = "INVALID_WEIGHT"
    status_code = 400


class InvalidDimensionsError(AppError):
    code = "INVALID_DIMENSIONS"
    status_code = 400


# --- 401 / 403 ---
class AuthenticationError(AppError):
    code = "AUTHENTICATION_ERROR"
    status_code = 401


class PermissionDeniedError(AppError):
    code = "PERMISSION_DENIED"
    status_code = 403


class UnauthorizedOrderAccessError(AppError):
    code = "UNAUTHORIZED_ORDER_ACCESS"
    status_code = 403


# --- 404 ---
class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class ZoneNotFoundError(AppError):
    code = "ZONE_NOT_FOUND"
    status_code = 404


class RateCardNotFoundError(AppError):
    code = "RATE_CARD_NOT_FOUND"
    status_code = 404


class OrderNotFoundError(AppError):
    code = "ORDER_NOT_FOUND"
    status_code = 404


class AgentNotFoundError(AppError):
    code = "AGENT_NOT_FOUND"
    status_code = 404


# --- 409 / conflict ---
class ConflictError(AppError):
    code = "CONFLICT"
    status_code = 409


class InvalidStatusTransitionError(AppError):
    code = "INVALID_STATUS_TRANSITION"
    status_code = 409


class AgentUnavailableError(AppError):
    code = "AGENT_UNAVAILABLE"
    status_code = 409


class AgentCapacityExceededError(AppError):
    code = "AGENT_CAPACITY_EXCEEDED"
    status_code = 409


class NoAgentAvailableError(AppError):
    code = "NO_AGENT_AVAILABLE"
    status_code = 409


class RescheduleNotAllowedError(AppError):
    code = "RESCHEDULE_NOT_ALLOWED"
    status_code = 409


class DuplicateResourceError(AppError):
    code = "DUPLICATE_RESOURCE"
    status_code = 409


class OverlappingWeightRangeError(AppError):
    code = "OVERLAPPING_WEIGHT_RANGE"
    status_code = 409
