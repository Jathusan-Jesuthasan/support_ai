from typing import Optional
from fastapi import APIRouter, Depends, Query

from app.core.enums import MembershipRole
from app.core.dependencies import PermissionChecker
from app.analytics.schema import (
    AnalyticsEventResponse,
    AnalyticsEventListCursorResponseEnvelope,
    AnalyticsDashboardResponse,
    AnalyticsDashboardResponseEnvelope
)
from app.chat.schema import CursorPaginationMeta
from app.analytics.service import AnalyticsService

router = APIRouter()


def get_analytics_service() -> AnalyticsService:
    """
    Dependency provider yielding the AnalyticsService instance.
    """
    return AnalyticsService()


@router.get(
    "/analytics/dashboard",
    response_model=AnalyticsDashboardResponseEnvelope,
    summary="Retrieve company dashboard aggregated metrics"
)
async def get_dashboard_stats(
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Aggregates message volumes, helpfulness feedback ratios, and escalation rates. Requires OWNER or ADMIN.
    """
    company_id = membership_ctx["company_id"]
    stats = await service.get_dashboard_stats(company_id)
    return AnalyticsDashboardResponseEnvelope(status="success", data=AnalyticsDashboardResponse(**stats))


@router.get(
    "/analytics/events",
    response_model=AnalyticsEventListCursorResponseEnvelope,
    summary="List telemetry event logs streams"
)
async def list_events(
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    membership_ctx: dict = Depends(PermissionChecker([MembershipRole.OWNER, MembershipRole.ADMIN])),
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Retrieves cursor-paginated raw event telemetry entries. Requires OWNER or ADMIN.
    """
    company_id = membership_ctx["company_id"]
    items, next_cursor, has_more = await service.list_events(company_id, limit, cursor)
    
    response_data = [
        AnalyticsEventResponse(
            event_id=e.event_id,
            company_id=e.company_id,
            event_type=e.event_type,
            event_metadata=e.event_metadata,
            created_at=e.created_at,
            created_by=e.created_by
        ) for e in items
    ]
    meta = CursorPaginationMeta(limit=limit, next_cursor=next_cursor, has_more=has_more)
    return AnalyticsEventListCursorResponseEnvelope(status="success", data=response_data, meta=meta)
