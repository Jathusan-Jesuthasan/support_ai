from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field


class WidgetSettingsUpdateRequest(BaseModel):
    theme_color: Optional[str] = Field(None, description="Hex/HSL color code for brand customisation")
    welcome_message: Optional[str] = Field(None, description="Greeting prompt text displayed to client")
    bot_name: Optional[str] = Field(None, description="Display name for assistant bot")
    allowed_domains: Optional[List[str]] = Field(None, description="Origins whitelisted for domain mapping checks")
    is_enabled: Optional[bool] = Field(None, description="Flag setting widget visibility active status")


class WidgetSettingsResponse(BaseModel):
    widget_id: UUID
    company_id: UUID
    theme_color: str
    welcome_message: str
    bot_name: str
    allowed_domains: List[str]
    is_enabled: bool
    created_at: datetime
    updated_at: datetime


class WidgetSettingsResponseEnvelope(BaseModel):
    status: str = "success"
    data: WidgetSettingsResponse


class WidgetSettingsPublicConfigResponse(BaseModel):
    theme_color: str
    welcome_message: str
    bot_name: str
    is_enabled: bool


class WidgetSettingsPublicConfigResponseEnvelope(BaseModel):
    status: str = "success"
    data: WidgetSettingsPublicConfigResponse
