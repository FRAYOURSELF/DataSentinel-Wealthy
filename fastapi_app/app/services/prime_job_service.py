import json
import math
import uuid

from redis import Redis

from app.clients.celery_client import celery_app


class PrimeJobService:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client

    def create_job(self, n: int, segment_size: int) -> str:
        job_id = str(uuid.uuid4())
        total_segments = math.ceil((n - 1) / segment_size)

        self.redis.hset(
            f"prime_job:{job_id}:meta",
            mapping={
                "status": "queued",
                "n": n,
                "segment_size": segment_size,
                "total_segments": total_segments,
                "completed_segments": 0,
                "failed_segments": 0,
            },
        )

        segments = []
        start = 2
        while start <= n:
            end = min(start + segment_size - 1, n)
            segments.append({"start": start, "end": end})
            start = end + 1

        self.redis.set(f"prime_job:{job_id}:segments", json.dumps(segments))
        celery_app.send_task("worker.tasks.prime_jobs.dispatch_prime_segments", args=[job_id])
        return job_id

    def get_status(self, job_id: str) -> dict | None:
        meta = self.redis.hgetall(f"prime_job:{job_id}:meta")
        if not meta:
            return None
        return {
            "job_id": job_id,
            "status": meta.get("status", "unknown"),
            "n": int(meta.get("n", 0)),
            "total_segments": int(meta.get("total_segments", 0)),
            "completed_segments": int(meta.get("completed_segments", 0)),
            "failed_segments": int(meta.get("failed_segments", 0)),
        }

    def get_result(self, job_id: str) -> dict | None:
        meta = self.redis.hgetall(f"prime_job:{job_id}:meta")
        if not meta:
            return None
        result = self.redis.get(f"prime_job:{job_id}:result")
        return {
            "job_id": job_id,
            "status": meta.get("status", "unknown"),
            "primes": json.loads(result) if result else None,
        }
