from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import Field
from app.shared.base_model import BaseEntity, EmbeddedModel
from app.core.enums import CompanyStatus, MembershipRole, MembershipStatus


class CompanySettings(EmbeddedModel):
    """
    Embedded settings document specific to a tenant company workspace.
    """
    primary_color: str = Field("#000000", description="Brand primary hex color code")
    welcome_message: str = Field("Hello! How can we help you today?", description="Initial greeting message shown in the chat widget")
    allowed_domains: List[str] = Field(default_factory=list, description="Whitelist of CORS domains allowed to embed the widget")
    widget_enabled: bool = Field(True, description="Flag indicating if the customer-facing chat widget is active")
    ai_enabled: bool = Field(True, description="Flag indicating if AI response generation is active")
    email_notifications: bool = Field(True, description="Flag indicating if email system updates are enabled")
    created_from: str = Field("dashboard", description="Origin channel where the workspace was initialized (e.g. 'dashboard')")


class Company(BaseEntity):
    """
    Represents a tenant company workspace identity document in MongoDB.
    """
    company_id: UUID = Field(..., description="Unique business UUID identifier for the company")
    name: str = Field(..., description="Name of the company tenant")
    slug: str = Field(..., description="Unique lowercase URL-friendly identifier")
    status: CompanyStatus = Field(CompanyStatus.ACTIVE, description="Active lifecycle status of the tenant workspace")
    description: Optional[str] = Field(None, description="Optional brief description of the company")
    logo_url: Optional[str] = Field(None, description="Optional URL path to the company branding logo")
    website: Optional[str] = Field(None, description="Optional website URL link")
    industry: Optional[str] = Field(None, description="Optional industry classification name")
    timezone: str = Field("UTC", description="Default operational timezone of the company")
    country: str = Field("US", description="Default operational country location of the company")
    settings: CompanySettings = Field(default_factory=CompanySettings, description="Embedded workspace setup configurations")


class CompanyMember(BaseEntity):
    """
    Junction entity representing a user's membership and RBAC role inside a company workspace.
    """
    membership_id: UUID = Field(..., description="Unique business UUID identifier for the membership")
    company_id: UUID = Field(..., description="UUID reference of the company this membership belongs to")
    user_id: UUID = Field(..., description="UUID reference of the user this membership belongs to")
    role: MembershipRole = Field(..., description="RBAC role of the member within the company")
    status: MembershipStatus = Field(MembershipStatus.ACTIVE, description="Lifecycle status of the membership")
    invited_by: Optional[UUID] = Field(None, description="UUID of the user who issued the membership invitation")
    joined_at: Optional[datetime] = Field(None, description="UTC timestamp of when the user accepted the membership")
    last_active_at: Optional[datetime] = Field(None, description="UTC timestamp of the member's last action in the company")
