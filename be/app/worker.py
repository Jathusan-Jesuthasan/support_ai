import logging
from typing import Any
from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from app.core.config import get_settings
from app.core.logging import setup_logging

# Configure system-wide logging for the worker process
setup_logging()
logger = logging.getLogger("supportai.worker")

# Load central settings
settings = get_settings()

# Initialize Celery app targeting Redis as broker and backend
celery_app = Celery(
    "supportai_worker",
    broker=str(settings.REDIS_URL),
    backend=str(settings.REDIS_URL),
)

# Standard production-ready task executor configurations
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Restart worker child processes periodically to prevent memory leaks
    worker_max_tasks_per_child=1000,
    # Pre-configure module paths containing async task functions.
    # Celery will auto-discover and register tasks inside these modules.
    imports=["app.knowledge.tasks"],
)


@worker_ready.connect
def on_worker_ready(sender: Any = None, **kwargs: Any) -> None:
    """
    Triggered when the Celery worker process starts up and connects to the Redis broker.
    """
    logger.info("Background task worker initialization sequence starting")
    logger.info("Background task worker successfully connected to Redis broker")
    logger.info("Background task worker ready and listening for events")


@worker_shutdown.connect
def on_worker_shutdown(sender: Any = None, **kwargs: Any) -> None:
    """
    Triggered when the Celery worker process receives a termination signal.
    Guarantees clean workspace cleanups.
    """
    logger.info("Background task worker shutdown sequence starting")
    logger.info("Background task worker successfully terminated")
