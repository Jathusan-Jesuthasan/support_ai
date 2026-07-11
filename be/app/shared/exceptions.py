from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any, List, Optional, TypedDict
from app.core.enums import ErrorCode


class ErrorDetail(TypedDict, total=False):
    """
    Type-safe representation of detailed validation or payload anomalies.

    Properties:
        field: The path or name of the invalid property.
        issue: A descriptive message indicating why validation failed.
        value: The raw invalid value submitted (optional).
    """

    field: str
    issue: str
    value: Any


class SupportAIException(Exception):
    """
    Base exception class for all SupportAI application errors.

    Purpose:
        Provides a uniform class structure mapping to HTTP status codes,
        business logic errors, and details.

    Typical usage:
        Inherited by specialized platform errors. Not intended to be raised directly.

    Expected HTTP Status:
        500 Internal Server Error (default).
    """

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_SERVER_ERROR,
        status_code: HTTPStatus = HTTPStatus.INTERNAL_SERVER_ERROR,
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or []
        self.timestamp = timestamp or datetime.now(timezone.utc)

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}: [{self.error_code.value}] "
            f"{self.message} (HTTP {self.status_code.value})"
        )


class BadRequestException(SupportAIException):
    """
    Purpose:
        Indicates that the client sent a malformed request body, header, or query.

    Typical usage:
        Raised when query parameter syntax is invalid or required HTTP headers are missing.

    Expected HTTP Status:
        400 Bad Request
    """

    def __init__(
        self,
        message: str = "Bad request",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.BAD_REQUEST,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details,
            timestamp=timestamp,
        )


class AuthenticationException(SupportAIException):
    """
    Purpose:
        Indicates authentication failure due to missing, invalid, or malformed credentials.

    Typical usage:
        Raised during password mismatch or when no Bearer token is provided.

    Expected HTTP Status:
        401 Unauthorized
    """

    def __init__(
        self,
        message: str = "Could not validate credentials",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.UNAUTHORIZED,
            status_code=HTTPStatus.UNAUTHORIZED,
            details=details,
            timestamp=timestamp,
        )


class TokenExpiredException(AuthenticationException):
    """
    Purpose:
        Indicates specifically that the client's JWT Access Token has expired.

    Typical usage:
        Raised by the JWT authentication dependency to prompt the client to rotate tokens.

    Expected HTTP Status:
        401 Unauthorized
    """

    def __init__(
        self,
        message: str = "Authentication token has expired",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            details=details,
            timestamp=timestamp,
        )
        self.error_code = ErrorCode.TOKEN_EXPIRED


class SessionExpiredException(AuthenticationException):
    """
    Purpose:
        Indicates specifically that the user's refresh token session has expired.

    Typical usage:
        Raised when a user submits an expired refresh token during token rotation.

    Expected HTTP Status:
        401 Unauthorized
    """

    def __init__(
        self,
        message: str = "Session has expired",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            details=details,
            timestamp=timestamp,
        )
        self.error_code = ErrorCode.SESSION_EXPIRED


class AuthorizationException(SupportAIException):
    """
    Purpose:
        Indicates that an authenticated user lacks the required RBAC permissions.

    Typical usage:
        Raised when a MEMBER attempts to access an OWNER-only endpoint.

    Expected HTTP Status:
        403 Forbidden
    """

    def __init__(
        self,
        message: str = "Permission denied",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.FORBIDDEN,
            status_code=HTTPStatus.FORBIDDEN,
            details=details,
            timestamp=timestamp,
        )


class TenantSuspendedException(AuthorizationException):
    """
    Purpose:
        Indicates that the target tenant company workspace has been suspended.

    Typical usage:
        Raised by the workspace resolution dependency when checking target company status.

    Expected HTTP Status:
        403 Forbidden
    """

    def __init__(
        self,
        message: str = "Company workspace is suspended",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            details=details,
            timestamp=timestamp,
        )
        self.error_code = ErrorCode.TENANT_SUSPENDED


class NotFoundException(SupportAIException):
    """
    Purpose:
        Indicates that the requested resource (entity UUID) does not exist in the database.

    Typical usage:
        Raised by a service when lookups by ID (e.g. `get_company_by_id`) yield no records.

    Expected HTTP Status:
        404 Not Found
    """

    def __init__(
        self,
        message: str = "Resource not found",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            status_code=HTTPStatus.NOT_FOUND,
            details=details,
            timestamp=timestamp,
        )


class ConflictException(SupportAIException):
    """
    Purpose:
        Indicates that the request conflicts with current state of the server/database.

    Typical usage:
        Raised when a concurrent edit collision occurs.

    Expected HTTP Status:
        409 Conflict
    """

    def __init__(
        self,
        message: str = "Resource conflict",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.CONFLICT,
            status_code=HTTPStatus.CONFLICT,
            details=details,
            timestamp=timestamp,
        )


class DuplicateResourceException(ConflictException):
    """
    Purpose:
        Indicates specifically that the resource already exists.

    Typical usage:
        Raised during signup if the email is already registered, or if a company slug is taken.

    Expected HTTP Status:
        409 Conflict
    """

    def __init__(
        self,
        message: str = "Resource already exists",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            details=details,
            timestamp=timestamp,
        )


class ValidationException(SupportAIException):
    """
    Purpose:
        Indicates that payload properties did not comply with validation rules.

    Typical usage:
        Raised when field values fail format constraints (e.g. invalid emails or weak passwords).

    Expected HTTP Status:
        400 Bad Request
    """

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.VALIDATION_FAILED,
            status_code=HTTPStatus.BAD_REQUEST,
            details=details,
            timestamp=timestamp,
        )


class RateLimitException(SupportAIException):
    """
    Purpose:
        Indicates that the client exceeded their allotted request rate.

    Typical usage:
        Raised by rate-limiting interceptors when Redis sliding window checks fail.

    Expected HTTP Status:
        429 Too Many Requests
    """

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=HTTPStatus.TOO_MANY_REQUESTS,
            details=details,
            timestamp=timestamp,
        )


class IdempotencyException(SupportAIException):
    """
    Purpose:
        Indicates a duplicate operation submission violating an idempotency key locks policy.

    Typical usage:
        Raised when a POST request is re-sent before the first transaction has completed.

    Expected HTTP Status:
        409 Conflict
    """

    def __init__(
        self,
        message: str = "Idempotency key violation",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.IDEMPOTENCY_VIOLATION,
            status_code=HTTPStatus.CONFLICT,
            details=details,
            timestamp=timestamp,
        )


class ServiceUnavailableException(SupportAIException):
    """
    Purpose:
        Indicates that an internal infrastructure dependency or third-party service is offline.

    Typical usage:
        Raised when MongoDB pings timeout, or Gemini/OpenAI API requests yield 503 errors.

    Expected HTTP Status:
        503 Service Unavailable
    """

    def __init__(
        self,
        message: str = "Upstream service temporarily unavailable",
        details: Optional[List[ErrorDetail]] = None,
        timestamp: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            message=message,
            error_code=ErrorCode.SERVICE_UNAVAILABLE,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            details=details,
            timestamp=timestamp,
        )
