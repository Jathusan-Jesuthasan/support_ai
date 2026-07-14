from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import Field

from app.shared.base_model import BaseEntity, EmbeddedModel
from app.core.enums import ConversationStatus, SenderType


class Citation(EmbeddedModel):
    """
    Embedded model representing grounding source references for an assistant response.
    """
    document_id: UUID = Field(..., description="The document chunk UUID references")
    source_title: str = Field(..., description="File name or web page title")
    chunk_index: int = Field(..., description="Zero-based sequence order of the chunk in the file")


class Message(BaseEntity):
    """
    Represents an individual message log within a chat session.
    """
    message_id: UUID = Field(..., description="Unique UUID identifier for the message")
    conversation_id: UUID = Field(..., description="The conversation UUID this message belongs to")
    company_id: UUID = Field(..., description="Tenant identifier to enforce logical isolation")
    sender_type: SenderType = Field(..., description="Sender categorization classification")
    content: str = Field(..., description="Text content payload of the message")
    citations: List[Citation] = Field(default_factory=list, description="Grounding reference chunks used for context")
    feedback_score: int = Field(0, description="Customer feedback classification score: -1 = negative, 0 = neutral/none, 1 = positive")


class Conversation(BaseEntity):
    """
    Represents a tenant-isolated support widget session.
    """
    conversation_id: UUID = Field(..., description="Unique business UUID identifier for the chat session")
    company_id: UUID = Field(..., description="The company workspace UUID reference")
    user_identifier: str = Field(..., description="Anonymized guest tracking string (e.g. cookie hash)")
    status: ConversationStatus = Field(ConversationStatus.OPEN, description="Current workflow state of the conversation")
    last_message_at: datetime = Field(..., description="Timestamp tracking active communication times")


class Product(BaseEntity):
    """
    Represents a product catalog item used for metadata retrieval and RAG context augmentation.
    """
    product_id: UUID = Field(..., description="Unique UUID identifier for the product item")
    company_id: UUID = Field(..., description="Tenant workspace UUID reference")
    sku: str = Field(..., description="Stock Keeping Unit code")
    name: str = Field(..., description="Product name")
    description: str = Field(..., description="Detailed product description")
    price: float = Field(..., description="Base pricing value of the product")
    url: Optional[str] = Field(None, description="Direct URL path link to the product details")
    is_available: bool = Field(True, description="Flag indicating if the product catalog item is active and in-stock")
