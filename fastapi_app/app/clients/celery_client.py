from celery import Celery

from app.core.config import settings

celery_app = Celery("fastapi_client", broker=settings.celery_broker_url, backend=settings.celery_result_backend)
