import json

from celery import chord
from celery.exceptions import MaxRetriesExceededError
from redis import Redis

from worker.celery_app import celery_app
from worker.config import REDIS_URL
from worker.instrumentation import TASKS_QUEUED
from worker.utils.primes import primes_in_segment


def _redis() -> Redis:
    return Redis.from_url(REDIS_URL, decode_responses=True)


@celery_app.task(bind=True, max_retries=5, default_retry_delay=2, name="worker.tasks.prime_jobs.dispatch_prime_segments")
def dispatch_prime_segments(self, job_id: str):
    redis = _redis()
    raw = redis.get(f"prime_job:{job_id}:segments")
    if not raw:
        raise ValueError("segments missing")

    segments = json.loads(raw)
    redis.hset(f"prime_job:{job_id}:meta", "status", "running")

    header = []
    for segment in segments:
        redis.hincrby(f"prime_job:{job_id}:meta", "queued_segments", 1)
        TASKS_QUEUED.inc()
        header.append(compute_prime_segment.s(job_id, segment["start"], segment["end"]))

    callback = finalize_prime_job.s(job_id)
    chord(header)(callback)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=2, name="worker.tasks.prime_jobs.compute_prime_segment")
def compute_prime_segment(self, job_id: str, start: int, end: int):
    redis = _redis()
    try:
        primes = primes_in_segment(start, end)
        redis.rpush(f"prime_job:{job_id}:partial", json.dumps(primes))
        redis.hincrby(f"prime_job:{job_id}:meta", "completed_segments", 1)
        redis.hincrby(f"prime_job:{job_id}:meta", "queued_segments", -1)
        return {"start": start, "end": end, "count": len(primes)}
    except Exception as exc:
        try:
            TASKS_QUEUED.inc()
            raise self.retry(exc=exc)
        except MaxRetriesExceededError:
            redis.hincrby(f"prime_job:{job_id}:meta", "failed_segments", 1)
            redis.hset(f"prime_job:{job_id}:meta", "status", "failed")
            redis.hincrby(f"prime_job:{job_id}:meta", "queued_segments", -1)
            raise


@celery_app.task(name="worker.tasks.prime_jobs.finalize_prime_job")
def finalize_prime_job(_segment_results, job_id: str):
    redis = _redis()
    partials = redis.lrange(f"prime_job:{job_id}:partial", 0, -1)

    all_primes = []
    for partial in partials:
        all_primes.extend(json.loads(partial))

    all_primes.sort()
    redis.set(f"prime_job:{job_id}:result", json.dumps(all_primes))
    redis.hset(f"prime_job:{job_id}:meta", mapping={"status": "completed", "queued_segments": 0})
    return {"job_id": job_id, "count": len(all_primes)}
