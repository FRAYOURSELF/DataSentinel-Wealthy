import httpx
from fastapi import APIRouter, Depends, HTTPException
from redis import Redis

from app.core.auth import get_current_user
from app.core.config import settings
from app.schemas.prime import (
    PrimeJobCreateRequest,
    PrimeJobCreateResponse,
    PrimeJobResultResponse,
    PrimeJobStatusResponse,
)
from app.services.prime_job_service import PrimeJobService

router = APIRouter(prefix="", tags=["primes"], dependencies=[Depends(get_current_user)])


def get_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


@router.get("/check-prime")
async def check_prime(number: int):
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(f"{settings.go_prime_service_url}/check-prime", params={"number": number})
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@router.get("/primes")
async def primes(n: int):
    if n <= 200_000:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{settings.go_prime_service_url}/primes", params={"n": n})
        if response.status_code >= 400:
            raise HTTPException(status_code=response.status_code, detail=response.text)
        return response.json()
    raise HTTPException(status_code=400, detail="n too large for sync endpoint; use /prime-jobs")


@router.post("/prime-jobs", response_model=PrimeJobCreateResponse)
def create_prime_job(payload: PrimeJobCreateRequest, redis_client: Redis = Depends(get_redis_client)):
    service = PrimeJobService(redis_client)
    job_id = service.create_job(payload.n, payload.segment_size)
    return PrimeJobCreateResponse(job_id=job_id, status="queued", n=payload.n)


@router.get("/prime-jobs/{job_id}", response_model=PrimeJobStatusResponse)
def get_prime_job(job_id: str, redis_client: Redis = Depends(get_redis_client)):
    service = PrimeJobService(redis_client)
    status = service.get_status(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="job not found")
    return PrimeJobStatusResponse(**status)


@router.get("/prime-jobs/{job_id}/result", response_model=PrimeJobResultResponse)
def get_prime_job_result(job_id: str, redis_client: Redis = Depends(get_redis_client)):
    service = PrimeJobService(redis_client)
    result = service.get_result(job_id)
    if not result:
        raise HTTPException(status_code=404, detail="job not found")
    return PrimeJobResultResponse(**result)
