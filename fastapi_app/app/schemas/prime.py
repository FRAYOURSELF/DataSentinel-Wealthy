from pydantic import BaseModel, Field


class PrimeJobCreateRequest(BaseModel):
    n: int = Field(gt=1, le=2_000_000)
    segment_size: int = Field(default=50_000, gt=1_000, le=200_000)


class PrimeJobCreateResponse(BaseModel):
    job_id: str
    status: str
    n: int


class PrimeJobStatusResponse(BaseModel):
    job_id: str
    status: str
    total_segments: int
    completed_segments: int
    failed_segments: int
    n: int


class PrimeJobResultResponse(BaseModel):
    job_id: str
    status: str
    primes: list[int] | None = None
