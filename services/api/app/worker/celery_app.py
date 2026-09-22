from celery import Celery
from ..core.config import settings

celery_app = Celery(
    "partner_integration",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["services.api.app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    timezone="UTC",
    enable_utc=True,

    task_acks_late=True,
    task_reject_on_worker_lost=True,

    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,

    result_expires=3600,

    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
)