from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.core.enums import ConversationStatus
from app.analytics.model import AnalyticsEvent
from app.chat.repository import encode_cursor, decode_cursor


class AnalyticsRepository:
    """
    Handles persistence and metrics calculations for platform analytics data.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def create(self, event: AnalyticsEvent) -> AnalyticsEvent:
        payload = event.to_mongo()
        await self.db["analytics"].insert_one(payload)
        return event

    async def list_events(
        self,
        company_id: UUID,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> Tuple[List[AnalyticsEvent], Optional[str], bool]:
        """
        Retrieves a cursor-paginated list of telemetry events, ordered by created_at DESC.
        """
        query: Dict[str, Any] = {
            "company_id": company_id
        }

        if cursor:
            c_data = decode_cursor(cursor)
            if c_data:
                c_time = datetime.fromisoformat(c_data["t"])
                c_id = UUID(c_data["id"])
                query["$or"] = [
                    {"created_at": {"$lt": c_time}},
                    {"created_at": c_time, "event_id": {"$lt": c_id}}
                ]

        cursor_obj = self.db["analytics"].find(query).sort([
            ("created_at", -1),
            ("event_id", -1)
        ]).limit(limit + 1)

        raw_docs = await cursor_obj.to_list(length=limit + 1)
        
        has_more = len(raw_docs) > limit
        
        items: List[AnalyticsEvent] = []
        for doc in raw_docs[:limit]:
            e = AnalyticsEvent.from_mongo(doc)
            if e:
                items.append(e)

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = encode_cursor(last_item.created_at, last_item.event_id)

        return items, next_cursor, has_more

    async def get_dashboard_metrics(self, company_id: UUID) -> Dict[str, Any]:
        """
        Computes dashboard stats by counting documents across chat collections.
        """
        total_convs = await self.db["conversations"].count_documents({
            "company_id": company_id,
            "is_deleted": False
        })
        
        total_msgs = await self.db["messages"].count_documents({
            "company_id": company_id,
            "is_deleted": False
        })

        helpful = await self.db["messages"].count_documents({
            "company_id": company_id,
            "feedback_score": 1,
            "is_deleted": False
        })

        unhelpful = await self.db["messages"].count_documents({
            "company_id": company_id,
            "feedback_score": -1,
            "is_deleted": False
        })

        escalated = await self.db["conversations"].count_documents({
            "company_id": company_id,
            "status": ConversationStatus.ESCALATED.value,
            "is_deleted": False
        })

        escalation_rate = 0.0
        if total_convs > 0:
            escalation_rate = (escalated / total_convs) * 100.0

        return {
            "total_conversations": total_convs,
            "total_messages": total_msgs,
            "helpful_ratings": helpful,
            "unhelpful_ratings": unhelpful,
            "escalation_rate": round(escalation_rate, 2)
        }
