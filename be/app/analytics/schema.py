from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.core.enums import AnalyticsEventType
from app.chat.schema import CursorPaginationMeta


class AnalyticsEventResponse(BaseModel):
    event_id: UUID
    company_id: UUID
    event_type: AnalyticsEventType
    event_metadata: Dict[str, Any]
    created_at: datetime
    created_by: Optional[UUID]


class AnalyticsEventListCursorResponseEnvelope(BaseModel):
    status: str = "success"
    data: List[AnalyticsEventResponse]
    meta: CursorPaginationMeta


class AnalyticsDashboardResponse(BaseModel):
    total_conversations: int = Field(..., description="Cumulative count of client conversations initiated")
    total_messages: int = Field(..., description="Cumulative count of message requests logged")
    helpful_ratings: int = Field(..., description="Total helpful support ratings recorded (score=1)")
    unhelpful_ratings: int = Field(..., description="Total unhelpful support ratings recorded (score=-1)")
    escalation_rate: float = Field(..., description="Escalation rate percentage (0.0 to 100.0) reflecting agent handovers")


class AnalyticsDashboardResponseEnvelope(BaseModel):
    status: str = "success"
    data: AnalyticsDashboardResponse
