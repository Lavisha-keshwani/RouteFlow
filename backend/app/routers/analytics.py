"""Analytics routes (admin only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models.user import User
from app.schemas.notification import AnalyticsSummary
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get(
    "/summary",
    response_model=AnalyticsSummary,
    summary="Operational analytics derived from live order data",
)
def analytics_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
) -> AnalyticsSummary:
    return AnalyticsService(db).summary()
