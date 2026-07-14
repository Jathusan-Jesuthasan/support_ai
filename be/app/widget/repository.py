from typing import Any, Dict, Optional
from uuid import UUID
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.core.database import get_database
from app.widget.model import WidgetSettings


class WidgetRepository:
    """
    Manages MongoDB persistence for widget layout configurations.
    """

    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None) -> None:
        self._db = db

    @property
    def db(self) -> AsyncIOMotorDatabase:
        return self._db or get_database()

    async def get_by_company_id(self, company_id: UUID, include_deleted: bool = False) -> Optional[WidgetSettings]:
        query: Dict[str, Any] = {"company_id": company_id}
        if not include_deleted:
            query["is_deleted"] = False
        data = await self.db["widget_settings"].find_one(query)
        return WidgetSettings.from_mongo(data) if data else None

    async def create(self, settings: WidgetSettings) -> WidgetSettings:
        payload = settings.to_mongo()
        await self.db["widget_settings"].insert_one(payload)
        return settings

    async def update(self, settings: WidgetSettings) -> Optional[WidgetSettings]:
        payload = settings.to_mongo()
        payload.pop("_id", None)
        result = await self.db["widget_settings"].replace_one(
            {"widget_id": settings.widget_id},
            payload
        )
        return settings if result.modified_count > 0 or result.matched_count > 0 else None
