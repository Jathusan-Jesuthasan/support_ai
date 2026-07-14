from datetime import datetime
from typing import Dict, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.core.enums import AnalyticsEventType


class AnalyticsEvent(BaseModel):
    """
    SaaS telemetry and performance event log entry document.
    """
    event_id: UUID = Field(..., description="Unique UUID identifier for the logged telemetry event")
    company_id: UUID = Field(..., description="Tenant workspace UUID reference")
    event_type: AnalyticsEventType = Field(..., description="Event type classification category")
    event_metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary JSON metadata payload")
    created_at: datetime = Field(..., description="UTC timestamp of when the event occurred")
    created_by: Optional[UUID] = Field(None, description="The user UUID who triggered the event, if applicable")

    def to_mongo(self) -> Dict[str, Any]:
        """
        Custom serialization helper representing standard field types for MongoDB.
        """
        return {
            "event_id": self.event_id,
            "company_id": self.company_id,
            "event_type": self.event_type.value,
            "event_metadata": self.event_metadata,
            "created_at": self.created_at,
            "created_by": self.created_by
        }

    @classmethod
    def from_mongo(cls, data: Dict[str, Any]) -> "AnalyticsEvent":
        """
        Deserialization helper.
        """
        return cls(
            event_id=data["event_id"],
            company_id=data["company_id"],
            event_type=AnalyticsEventType(data["event_type"]),
            event_metadata=data.get("event_metadata", {}),
            created_at=data["created_at"],
            created_by=data.get("created_by")
        )
