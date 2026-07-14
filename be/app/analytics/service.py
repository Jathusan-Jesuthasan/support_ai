import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

from app.core.enums import AnalyticsEventType
from app.analytics.model import AnalyticsEvent
from app.analytics.repository import AnalyticsRepository


class AnalyticsService:
    """
    Coordinates platform telemetry logging and metric aggregations.
    """

    def __init__(self, analytics_repo: Optional[AnalyticsRepository] = None) -> None:
        self.analytics_repo = analytics_repo or AnalyticsRepository()

    async def log_event(
        self,
        company_id: UUID,
        event_type: AnalyticsEventType,
        event_metadata: Dict[str, Any],
        created_by: Optional[UUID] = None
    ) -> AnalyticsEvent:
        """
        Creates and logs a new telemetry event.
        """
        event = AnalyticsEvent(
            event_id=uuid.uuid4(),
            company_id=company_id,
            event_type=event_type,
            event_metadata=event_metadata,
            created_at=datetime.now(timezone.utc),
            created_by=created_by
        )
        return await self.analytics_repo.create(event)

    async def get_dashboard_stats(self, company_id: UUID) -> Dict[str, Any]:
        """
        Aggregates dashboard telemetry statistics.
        """
        return await self.analytics_repo.get_dashboard_metrics(company_id)

    async def list_events(
        self,
        company_id: UUID,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> Tuple[List[AnalyticsEvent], Optional[str], bool]:
        """
        Lists cursor-paginated events.
        """
        return await self.analytics_repo.list_events(company_id, limit, cursor)
