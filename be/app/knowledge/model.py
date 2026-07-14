from typing import List, Optional
from uuid import UUID
from pydantic import Field
from app.shared.base_model import BaseEntity, EmbeddedModel
from app.core.enums import DocumentStatus


class ChunkMetadata(EmbeddedModel):
    """
    Metadata stored along with a document text chunk.
    """
    source_title: str = Field(..., description="The name of the source file")
    file_type: str = Field(..., description="File extension, e.g. PDF, TXT, MD, DOCX")
    summary: Optional[str] = Field("", description="Optional short summary of the chunk or parent document")
    tags: List[str] = Field(default_factory=list, description="Extracted category tags")
    page_number: Optional[int] = Field(None, description="Page number where the chunk is located")
    section: Optional[str] = Field(None, description="Header context section")
    language: str = Field("en", description="Language code")
    embedding_model: str = Field("text-embedding-004", description="Model name used to vectorize this chunk")
    version: int = Field(1, description="Version index of the chunk")


class Knowledge(BaseEntity):
    """
    Represents a tenant knowledge source file/configuration.
    """
    knowledge_id: UUID = Field(..., description="Unique UUID identifier for the knowledge source")
    company_id: UUID = Field(..., description="Company owner UUID")
    name: str = Field(..., description="Friendly name of the knowledge source")
    description: Optional[str] = Field(None, description="Brief description")
    source_type: str = Field(..., description="MANUAL, WEB_CRAWL, or FILE_UPLOAD")
    status: DocumentStatus = Field(DocumentStatus.UPLOADED, description="The processing status of this source")
    current_version: int = Field(1, description="Current active version of the document")
    file_url: Optional[str] = Field(None, description="Path/URL to the uploaded raw file")


class Document(BaseEntity):
    """
    Represents an individual text chunk and its vector embedding in the documents collection.
    """
    document_id: UUID = Field(..., description="Unique UUID for this text chunk")
    parent_document_id: UUID = Field(..., description="Groups chunks of the same source file (refers to knowledge.knowledge_id)")
    knowledge_id: UUID = Field(..., description="Refers to knowledge.knowledge_id")
    company_id: UUID = Field(..., description="Company owner UUID")
    chunk_index: int = Field(..., description="Index order of this chunk")
    chunk_order: Optional[int] = Field(None, description="Index order of this chunk (alias for chunk_index)")
    content: str = Field(..., description="Raw text payload")
    vector_embedding: Optional[List[float]] = Field(None, description="768-dimension vector embedding array")
    metadata: ChunkMetadata = Field(..., description="Granular chunk metadata details")
