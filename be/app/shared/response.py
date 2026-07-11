from typing import Any, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

# Generic TypeVar representing dynamic inner response payloads
T = TypeVar("T")


class PaginationMeta(BaseModel):
    """
    Metadata block for standard offset-paginated collections.
    """

    page: int = Field(..., description="Current page index (1-based)")
    limit: int = Field(..., description="Number of items requested per page")
    total_items: int = Field(..., description="Total count of available matching items in DB")
    total_pages: int = Field(..., description="Calculated total count of pages")


class SuccessResponse(BaseModel, Generic[T]):
    """
    Standard envelope wrapper for single resource responses.
    """

    status: str = Field("success", description="Status code flag, always 'success'")
    data: T = Field(..., description="Target data object returned by the API")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard envelope wrapper for offset-paginated list resources.
    """

    status: str = Field("success", description="Status code flag, always 'success'")
    data: List[T] = Field(..., description="Page list of target data objects")
    meta: PaginationMeta = Field(..., description="Offset pagination metadata details")


class ErrorDetailSchema(BaseModel):
    """
    Type-safe validation context detailed payload structure.
    """

    field: str = Field(..., description="Path or name of the invalid property")
    issue: str = Field(..., description="Descriptive message indicating validation failure")
    value: Optional[Any] = Field(None, description="The raw invalid value submitted")


class ErrorResponseBody(BaseModel):
    """
    Enveloped body of API failure contexts.
    """

    code: str = Field(..., description="Machine-readable platform business error code")
    message: str = Field(..., description="Description of the error encounter")
    details: List[ErrorDetailSchema] = Field(
        default_factory=list, description="List of field-specific validation contexts"
    )


class ErrorResponse(BaseModel):
    """
    Standard envelope wrapper for error responses.
    """

    status: str = Field("error", description="Status code flag, always 'error'")
    error: ErrorResponseBody = Field(..., description="Failure context metadata body")
