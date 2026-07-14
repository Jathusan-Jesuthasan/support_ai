import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict
from app.core.config import get_settings

# Thread/Task-safe context variables for distributed request tracing
correlation_id_context: contextvars.ContextVar[Any] = contextvars.ContextVar("correlation_id", default=None)
user_id_context: contextvars.ContextVar[Any] = contextvars.ContextVar("user_id", default=None)
company_id_context: contextvars.ContextVar[Any] = contextvars.ContextVar("company_id", default=None)


# Standard LogRecord attributes that should not be extracted as custom extra fields
RESERVED_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "taskName", "message", "asctime"
}


class JSONFormatter(logging.Formatter):
    """
    Custom logging formatter converting LogRecords into structured JSON strings.
    Automatically appends active distributed tracing and tenant context variables.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "file": record.pathname,
            "line": record.lineno,
        }

        # Format and append stack trace details if exception info exists
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        # Retrieve active request and tenant variables from task context
        corr_id = correlation_id_context.get()
        user_id = user_id_context.get()
        company_id = company_id_context.get()

        if corr_id:
            log_payload["correlation_id"] = corr_id
        if user_id:
            log_payload["user_id"] = user_id
        if company_id:
            log_payload["company_id"] = company_id

        # Safely extract extra variables attached during logging
        for key, value in record.__dict__.items():
            if key not in RESERVED_ATTRS and key not in log_payload:
                log_payload[key] = value

        if hasattr(record, "extra") and isinstance(record.extra, dict):
            for key, value in record.extra.items():
                if key not in log_payload:
                    log_payload[key] = value

        return json.dumps(log_payload)



def setup_logging() -> None:
    """
    Bootstraps the root logging configuration.
    Sets levels, clears duplicate handlers, and configures output formatters.
    """
    settings = get_settings()
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # Reset root logger handlers to prevent duplicate outputs
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)

    # Human-readable format for development.
    # Structured JSON for production/staging environments.
    if settings.ENVIRONMENT in ("development", "testing") and not settings.DEBUG:
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        formatter = JSONFormatter()

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Prevent noisy dependency logging from cluttering logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("motor").setLevel(logging.WARNING)
