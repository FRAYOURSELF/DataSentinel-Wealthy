import json

import fakeredis

from worker.tasks import prime_jobs


class DummyRetry(Exception):
    pass


def test_compute_and_finalize_segments(monkeypatch):
    redis_client = fakeredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(prime_jobs, "_redis", lambda: redis_client)

    job_id = "job-1"
    redis_client.hset(
        f"prime_job:{job_id}:meta",
        mapping={
            "status": "running",
            "n": 30,
            "segment_size": 10,
            "total_segments": 3,
            "completed_segments": 0,
            "failed_segments": 0,
            "queued_segments": 3,
        },
    )

    result1 = prime_jobs.compute_prime_segment.run(job_id=job_id, start=2, end=10)
    result2 = prime_jobs.compute_prime_segment.run(job_id=job_id, start=11, end=20)
    result3 = prime_jobs.compute_prime_segment.run(job_id=job_id, start=21, end=30)

    assert result1["count"] > 0
    assert result2["count"] > 0
    assert result3["count"] > 0

    final = prime_jobs.finalize_prime_job.run([], job_id=job_id)
    assert final["job_id"] == job_id

    stored = json.loads(redis_client.get(f"prime_job:{job_id}:result"))
    assert stored == [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
    assert redis_client.hget(f"prime_job:{job_id}:meta", "status") == "completed"
