from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.core.enums import DocumentStatus


class KnowledgeCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="The name of the knowledge source")
    description: Optional[str] = Field(None, max_length=1000, description="Brief description")
    source_type: str = Field("FILE_UPLOAD", description="MANUAL, WEB_CRAWL, or FILE_UPLOAD")


class KnowledgeUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Updated name")
    description: Optional[str] = Field(None, max_length=1000, description="Updated description")


class KnowledgeResponse(BaseModel):
    knowledge_id: UUID = Field(..., description="Unique UUID identifier for the knowledge source")
    company_id: UUID = Field(..., description="Company owner UUID")
    name: str = Field(..., description="Name of the knowledge source")
    description: Optional[str] = Field(None, description="Description")
    source_type: str = Field(..., description="Source type classification")
    status: DocumentStatus = Field(..., description="Processing status")
    current_version: int = Field(..., description="Current version number")
    file_url: Optional[str] = Field(None, description="raw file storage path or URL")
    created_at: datetime = Field(..., description="UTC creation timestamp")
    updated_at: datetime = Field(..., description="UTC last update timestamp")


class KnowledgeResponseEnvelope(BaseModel):
    status: str = "success"
    data: KnowledgeResponse


class KnowledgeListResponseEnvelope(BaseModel):
    status: str = "success"
    data: List[KnowledgeResponse]
