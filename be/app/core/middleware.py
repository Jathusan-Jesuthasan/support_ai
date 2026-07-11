import logging
import time
import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logging import company_id_context, correlation_id_context

logger = logging.getLogger("supportai.middleware")


class TracingMiddleware(BaseHTTPMiddleware):
    """
    Global ASGI middleware for request tracking and performance monitoring.
    Ingests correlation tags and logs latency metrics.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Resolve trace ID from headers or generate new UUID
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())

        # 2. Bind ID to context variables for structured logs and background tasks
        correlation_token = correlation_id_context.set(correlation_id)

        # 3. Capture and bind Tenant context if supplied in headers
        company_id = request.headers.get("X-Company-ID")
        company_token = company_id_context.set(company_id)

        # Attach Correlation ID to request state for access in endpoints
        request.state.correlation_id = correlation_id

        try:
            start_time = time.perf_counter()
            response: Response = await call_next(request)
            process_time = (time.perf_counter() - start_time) * 1000

            # Inject Correlation ID back into response headers for client tracking
            response.headers["X-Correlation-ID"] = correlation_id

            # Log request parameters and performance metrics
            logger.info(
                f"{request.method} {request.url.path} completed in {process_time:.2f}ms",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "latency_ms": round(process_time, 2),
                },
            )
            return response
        finally:
            # 4. Clean up ContextVars to prevent memory leaks across request threads
            correlation_id_context.reset(correlation_token)
            company_id_context.reset(company_token)
