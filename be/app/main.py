import logging
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import Dict
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import db_manager
from app.core.enums import ErrorCode
from app.core.logging import setup_logging
from app.core.middleware import TracingMiddleware
from app.shared.exceptions import SupportAIException
from app.shared.response import ErrorDetailSchema, ErrorResponse, ErrorResponseBody

logger = logging.getLogger("supportai.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the startup and shutdown lifecycle events of the FastAPI application.
    Bootstraps logging and database pool connection instances.
    """
    # 1. Setup Root Logger configurations
    setup_logging()
    logger.info("Starting SupportAI application initialization sequence")

    # 2. Establish connections to MongoDB Atlas pool
    await db_manager.connect()
    logger.info("Database connection successfully established")

    yield

    # 3. Clean up and close connection pools during shutdown
    logger.info("Initiating application shutdown sequence")
    db_manager.disconnect()
    logger.info("Database connection pool closed successfully")



# Load cached settings
settings = get_settings()

# Initialize core FastAPI instance
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend service for SupportAI multi-tenant RAG platform.",
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enforce Trace intercepting and Correlation ID assignment
app.add_middleware(TracingMiddleware)

# Configure Cross-Origin Resource Sharing (CORS) rules
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# Exception Interceptors
# =====================================================================


@app.exception_handler(SupportAIException)
async def supportai_exception_handler(
    request: Request, exc: SupportAIException
) -> JSONResponse:
    """
    Intercepts custom platform exceptions and wraps them in our standard ErrorResponse format.
    """
    error_details = [
        ErrorDetailSchema(
            field=d.get("field", ""),
            issue=d.get("issue", ""),
            value=d.get("value"),
        )
        for d in exc.details
    ]

    response_payload = ErrorResponse(
        status="error",
        error=ErrorResponseBody(
            code=exc.error_code.value,
            message=exc.message,
            details=error_details,
        ),
    )

    return JSONResponse(
        status_code=exc.status_code.value,
        content=response_payload.model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Intercepts payload and query parameter validation errors from Pydantic and FastAPI,
    wrapping them in our standard ErrorResponse format.
    """
    error_details = []
    for error in exc.errors():
        # Clean path locator
        loc = ".".join(str(x) for x in error.get("loc", []))
        if loc.startswith("body."):
            loc = loc[5:]

        error_details.append(
            ErrorDetailSchema(
                field=loc,
                issue=error.get("msg", ""),
                value=error.get("input"),
            )
        )

    response_payload = ErrorResponse(
        status="error",
        error=ErrorResponseBody(
            code=ErrorCode.VALIDATION_FAILED.value,
            message="Validation failed",
            details=error_details,
        ),
    )

    return JSONResponse(
        status_code=HTTPStatus.BAD_REQUEST.value,
        content=response_payload.model_dump(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Fallback interceptor catching all uncaught system exceptions, preventing raw stack trace exposure.
    """
    logger.exception("Uncaught application exception intercepted")

    response_payload = ErrorResponse(
        status="error",
        error=ErrorResponseBody(
            code=ErrorCode.INTERNAL_SERVER_ERROR.value,
            message="An unexpected error occurred on the server",
            details=[],
        ),
    )

    return JSONResponse(
        status_code=HTTPStatus.INTERNAL_SERVER_ERROR.value,
        content=response_payload.model_dump(),
    )


# =====================================================================
# Main Application Mounts & Routing
# =====================================================================


@app.get("/", summary="Root Status Checker")
async def read_root() -> Dict[str, str]:
    """
    Root status check. Used by ingress servers to verify route availability.
    """
    return {"message": "SupportAI Backend Running"}


@app.get("/health", summary="Root Health Checker")
async def read_health() -> Dict[str, str]:
    """
    Root level healthcheck endpoint.
    """
    return {"status": "healthy", "version": "v1"}


# Mount the versioned V1 router
app.include_router(api_router, prefix="/api/v1")
