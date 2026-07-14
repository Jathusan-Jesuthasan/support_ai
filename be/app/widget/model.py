from typing import List
from uuid import UUID
from pydantic import Field

from app.shared.base_model import BaseEntity


class WidgetSettings(BaseEntity):
    """
    Represents the customer-facing chat widget appearance and domain whitelists for a company.
    """
    widget_id: UUID = Field(..., description="Unique UUID identifier for the widget settings")
    company_id: UUID = Field(..., description="Tenant workspace UUID reference")
    theme_color: str = Field("#000000", description="Hex/HSL color code for widget header and UI highlights")
    welcome_message: str = Field("Hello! How can we help you today?", description="Initial message greeting shown to users")
    bot_name: str = Field("SupportBot", description="Display name of the automated chat bot assistant")
    allowed_domains: List[str] = Field(default_factory=list, description="List of whitelisted origins permitted to load widget (CORS)")
    is_enabled: bool = Field(True, description="Flag indicating if the public chat widget is currently active")
