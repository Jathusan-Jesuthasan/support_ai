from enum import Enum


class ErrorCode(str, Enum):
    """
    Standardized platform business error codes.
    Aligns with 05-api-standards.md specifications.
    """

    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    IDEMPOTENCY_VIOLATION = "IDEMPOTENCY_VIOLATION"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    TENANT_SUSPENDED = "TENANT_SUSPENDED"


class CompanyStatus(str, Enum):
    """
    Lifecycle states for tenant companies.
    """

    ACTIVE = "ACTIVE"
    PENDING = "PENDING"
    SUSPENDED = "SUSPENDED"
    ARCHIVED = "ARCHIVED"


class MembershipRole(str, Enum):
    """
    RBAC Roles within a tenant company workspace.
    """

    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"


class MembershipStatus(str, Enum):
    """
    Lifecycle states of a user's membership inside a company workspace.
    """

    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"


class SessionStatus(str, Enum):
    """
    Status of a user session.
    """

    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class TokenType(str, Enum):
    """
    Authentication token classification types.
    """

    ACCESS = "ACCESS"
    REFRESH = "REFRESH"


class ConversationStatus(str, Enum):
    """
    Widget chat session states.
    """

    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ESCALATED = "ESCALATED"


class DocumentStatus(str, Enum):
    """
    Lifecycle and vector index states of uploaded knowledge base documents.
    """

    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class ApprovalStatus(str, Enum):
    """
    State of administrative approval workflows.
    """

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AIProvider(str, Enum):
    """
    Generative AI and embedding service providers.
    """

    GEMINI = "GEMINI"
    OPENAI = "OPENAI"
    CLAUDE = "CLAUDE"
    OLLAMA = "OLLAMA"


class SenderType(str, Enum):
    """
    Message sender categories.
    """
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    HUMAN_AGENT = "HUMAN_AGENT"


class AnalyticsEventType(str, Enum):
    """
    Types of tracked analytics log events.
    """
    MESSAGE_SENT = "MESSAGE_SENT"
    HELP_HELPFUL = "HELP_HELPFUL"
    HELP_UNHELPFUL = "HELP_UNHELPFUL"
    AGENT_HANDOVER = "AGENT_HANDOVER"

