import time

from celery.signals import task_failure, task_postrun, task_prerun, task_success
from prometheus_client import Counter, Gauge, Histogram, start_http_server

TASKS_QUEUED = Gauge("celery_tasks_queued", "Estimated queued Celery tasks")
TASKS_ACTIVE = Gauge("celery_tasks_active", "Active Celery tasks")
TASKS_SUCCESS = Counter("celery_tasks_success_total", "Successful tasks", ["task_name"])
TASKS_FAILURE = Counter("celery_tasks_failure_total", "Failed tasks", ["task_name"])
TASK_DURATION = Histogram("celery_task_duration_seconds", "Task execution duration", ["task_name"])

_TASK_START_TIMES: dict[str, float] = {}


def start_metrics_server(port: int = 9103):
    start_http_server(port)


@task_prerun.connect
def _task_prerun_handler(task_id=None, task=None, **kwargs):
    TASKS_ACTIVE.inc()
    # queued gauge is only incremented for segment tasks at dispatch time,
    # so decrement it only when a segment task actually starts running.
    if task and task.name == "worker.tasks.prime_jobs.compute_prime_segment":
        TASKS_QUEUED.dec()
    if task_id:
        _TASK_START_TIMES[task_id] = time.perf_counter()


@task_postrun.connect
def _task_postrun_handler(task_id=None, task=None, **kwargs):
    TASKS_ACTIVE.dec()
    if task_id and task_id in _TASK_START_TIMES:
        elapsed = time.perf_counter() - _TASK_START_TIMES.pop(task_id)
        TASK_DURATION.labels(task_name=task.name).observe(elapsed)


@task_success.connect
def _task_success_handler(sender=None, **kwargs):
    if sender:
        TASKS_SUCCESS.labels(task_name=sender.name).inc()


@task_failure.connect
def _task_failure_handler(sender=None, **kwargs):
    if sender:
        TASKS_FAILURE.labels(task_name=sender.name).inc()
