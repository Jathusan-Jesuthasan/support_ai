import re
import zoneinfo
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.core.enums import CompanyStatus
from app.company.model import CompanySettings


# =====================================================================
# Request Schemas
# =====================================================================

class CompanyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="The name of the company tenant")
    slug: Optional[str] = Field(None, min_length=1, max_length=100, description="Optional custom lowercase URL slug")
    description: Optional[str] = Field(None, max_length=1000, description="Brief description of the company")
    website: Optional[str] = Field(None, description="Optional website URL link")
    industry: Optional[str] = Field(None, max_length=100, description="Industry classification name")
    timezone: str = Field("UTC", description="Default operational timezone of the company")
    country: str = Field("US", description="Default operational country location of the company")

    @field_validator("name", "slug", "description", "website", "industry", "timezone", "country", mode="before")
    @classmethod
    def trim_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.lower()
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must contain only lowercase alphanumeric characters and single hyphens")
        return v

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", v):
            raise ValueError("Website must be a valid HTTP or HTTPS URL")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        try:
            zoneinfo.ZoneInfo(v)
        except Exception:
            raise ValueError(f"Invalid timezone: {v}")
        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: str) -> str:
        v = v.upper()
        if not re.match(r"^[A-Z]{2}$", v):
            raise ValueError("Country must be a 2-letter ISO 3166-1 country code (e.g., US, CA)")
        return v


class CompanyUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated name of the company")
    slug: Optional[str] = Field(None, min_length=1, max_length=100, description="Updated unique URL slug")
    description: Optional[str] = Field(None, max_length=1000, description="Updated description of the company")
    website: Optional[str] = Field(None, description="Updated website URL link")
    industry: Optional[str] = Field(None, max_length=100, description="Updated industry classification name")
    timezone: Optional[str] = Field(None, description="Updated timezone")
    country: Optional[str] = Field(None, description="Updated 2-letter country code")
    status: Optional[CompanyStatus] = Field(None, description="Updated status of the company")

    @field_validator("name", "slug", "description", "website", "industry", "timezone", "country", mode="before")
    @classmethod
    def trim_strings(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.lower()
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must contain only lowercase alphanumeric characters and single hyphens")
        return v

    @field_validator("website")
    @classmethod
    def validate_website(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", v):
            raise ValueError("Website must be a valid HTTP or HTTPS URL")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            zoneinfo.ZoneInfo(v)
        except Exception:
            raise ValueError(f"Invalid timezone: {v}")
        return v

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.upper()
        if not re.match(r"^[A-Z]{2}$", v):
            raise ValueError("Country must be a 2-letter ISO 3166-1 country code (e.g., US, CA)")
        return v


# =====================================================================
# Response Schemas
# =====================================================================

class CompanyResponse(BaseModel):
    company_id: UUID = Field(..., description="Unique business UUID identifier for the company")
    name: str = Field(..., description="Name of the company")
    slug: str = Field(..., description="Unique URL slug of the company")
    description: Optional[str] = Field(None, description="Brief description of the company")
    logo_url: Optional[str] = Field(None, description="URL path to the branding logo")
    website: Optional[str] = Field(None, description="Website URL link")
    industry: Optional[str] = Field(None, description="Industry classification name")
    timezone: str = Field(..., description="Operational timezone")
    country: str = Field(..., description="Operational country code")
    status: CompanyStatus = Field(..., description="Lifecycle status of the company")
    settings: CompanySettings = Field(..., description="Embedded configurations")
    created_at: datetime = Field(..., description="UTC creation timestamp")
    updated_at: datetime = Field(..., description="UTC last modification timestamp")


class CompanyListItem(BaseModel):
    company_id: UUID = Field(..., description="Unique business UUID identifier for the company")
    name: str = Field(..., description="Name of the company")
    slug: str = Field(..., description="Unique URL slug")
    status: CompanyStatus = Field(..., description="Lifecycle status")
    created_at: datetime = Field(..., description="UTC creation timestamp")


class CursorPaginationMeta(BaseModel):
    limit: int = Field(..., description="Maximum number of items returned in the page")
    next_cursor: Optional[str] = Field(None, description="Base64 URL-encoded token to fetch the next page")
    has_more: bool = Field(..., description="Flag indicating if more records are available")


# =====================================================================
# Envelope Responses
# =====================================================================

class CompanyResponseEnvelope(BaseModel):
    status: str = "success"
    data: CompanyResponse
    
    
class CompanyListResponse(BaseModel):
    status: str = "success"
    data: List[CompanyListItem]
    meta: CursorPaginationMeta


class CompanyDeleteResponse(BaseModel):
    status: str = "success"
    message: str = Field("Company successfully deleted", description="Detailed success message")
