import logging

from celery import Celery

from worker.config import BROKER_URL, OTEL_EXPORTER_OTLP_ENDPOINT, RESULT_BACKEND
from worker.instrumentation import TASKS_QUEUED, start_metrics_server

logger = logging.getLogger(__name__)

celery_app = Celery(
    "worker",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["worker.tasks.ip_check", "worker.tasks.prime_jobs"],
)
celery_app.conf.update(
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    broker_connection_retry_on_startup=True,
)


def _init_tracing():
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception as exc:
        logger.warning("Celery tracing disabled; OpenTelemetry dependencies unavailable: %s", exc)
        return

    resource = Resource.create({"service.name": "celery-worker"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=OTEL_EXPORTER_OTLP_ENDPOINT, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    CeleryInstrumentor().instrument()


@celery_app.on_after_configure.connect
def setup_observability(sender, **kwargs):
    _init_tracing()
    start_metrics_server(port=9103)


@celery_app.task(name="worker.tasks.metrics.bump_queue")
def bump_queue(count: int = 1):
    TASKS_QUEUED.inc(count)
