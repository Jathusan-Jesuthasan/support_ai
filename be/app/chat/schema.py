from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from app.core.enums import ConversationStatus, SenderType


# ==========================================
# Cursor Pagination Metadata
# ==========================================

class CursorPaginationMeta(BaseModel):
    """
    Metadata block for cursor-paginated logs.
    """
    limit: int = Field(..., description="Max number of items requested")
    next_cursor: Optional[str] = Field(None, description="Base64 encoded JSON string representing the cursor for the next page")
    has_more: bool = Field(..., description="Flag indicating if there are more items to retrieve")


# ==========================================
# Citation Schemas
# ==========================================

class CitationResponse(BaseModel):
    document_id: UUID = Field(..., description="Reference UUID to the source document chunk")
    source_title: str = Field(..., description="Filename or title of the source document")
    chunk_index: int = Field(..., description="Sequence chunk index order")


# ==========================================
# Message Schemas
# ==========================================

class MessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1, description="Message text content")


class FeedbackScoreUpdateRequest(BaseModel):
    score: int = Field(..., description="Feedback score rating: -1 = negative, 0 = neutral/none, 1 = positive")

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        if v not in (-1, 0, 1):
            raise ValueError("Score must be one of: -1, 0, 1")
        return v


class MessageResponse(BaseModel):
    message_id: UUID
    conversation_id: UUID
    company_id: UUID
    sender_type: SenderType
    content: str
    citations: List[CitationResponse] = []
    feedback_score: int
    created_at: datetime
    updated_at: datetime


class MessageResponseEnvelope(BaseModel):
    status: str = "success"
    data: MessageResponse


class MessageListCursorResponseEnvelope(BaseModel):
    status: str = "success"
    data: List[MessageResponse]
    meta: CursorPaginationMeta


# ==========================================
# Conversation Schemas
# ==========================================

class ConversationCreateRequest(BaseModel):
    user_identifier: Optional[str] = Field(None, description="Client/Guest tracking cookie hash identifier")


class ConversationStatusUpdateRequest(BaseModel):
    status: ConversationStatus = Field(..., description="Target status for the conversation")


class ConversationResponse(BaseModel):
    conversation_id: UUID
    company_id: UUID
    user_identifier: str
    status: ConversationStatus
    last_message_at: datetime
    created_at: datetime
    updated_at: datetime


class ConversationResponseEnvelope(BaseModel):
    status: str = "success"
    data: ConversationResponse


class ConversationListCursorResponseEnvelope(BaseModel):
    status: str = "success"
    data: List[ConversationResponse]
    meta: CursorPaginationMeta


# ==========================================
# Product Schemas
# ==========================================

class ProductCreateRequest(BaseModel):
    sku: str = Field(..., min_length=1, description="Stock Keeping Unit unique code")
    name: str = Field(..., min_length=1, description="Product display name")
    description: str = Field(..., description="Detailed description context")
    price: float = Field(..., gt=0.0, description="Listing price value")
    url: Optional[str] = Field(None, description="Optional purchase link web path")
    is_available: bool = Field(True, description="Availability flag indicator")


class ProductResponse(BaseModel):
    product_id: UUID
    company_id: UUID
    sku: str
    name: str
    description: str
    price: float
    url: Optional[str]
    is_available: bool
    created_at: datetime
    updated_at: datetime


class ProductResponseEnvelope(BaseModel):
    status: str = "success"
    data: ProductResponse


class ProductListResponseEnvelope(BaseModel):
    status: str = "success"
    data: List[ProductResponse]
