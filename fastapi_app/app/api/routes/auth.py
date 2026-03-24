from fastapi import APIRouter, Depends, HTTPException, Request
from redis import Redis
from sqlalchemy.orm import Session

from app.clients.celery_client import celery_app
from app.core.config import settings
from app.core.security import create_access_token
from app.db.clickhouse import get_clickhouse_client
from app.db.sqlite import get_db_session
from app.repositories.event_repo import EventRepository
from app.schemas.auth import LoginRequest, LoginResponse
from app.services.auth_service import AuthService
from app.services.rate_limiter import LoginRateLimiter

router = APIRouter(prefix="", tags=["auth"])


def _extract_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db_session),
    redis_client: Redis = Depends(get_redis_client),
):
    auth_service = AuthService(db)
    clickhouse = get_clickhouse_client()
    event_repo = EventRepository(clickhouse)
    client_ip = _extract_client_ip(request)
    request_size = int(request.headers.get("content-length", "0"))
    rate_limiter = LoginRateLimiter(redis_client)

    is_allowed, reason = rate_limiter.check_allow(client_ip, payload.username)
    if not is_allowed:
        event_id = auth_service.new_event_id()
        event_repo.insert_login_event(
            event_id=event_id,
            user_id=-1,
            username=payload.username,
            ip_address=client_ip,
            request_size=request_size,
            status_code=429,
        )
        raise HTTPException(status_code=429, detail=reason)

    user = auth_service.authenticate(payload.username, payload.password)

    if not user:
        rate_limiter.record_failure(client_ip, payload.username)
        event_id = auth_service.new_event_id()
        event_repo.insert_login_event(
            event_id=event_id,
            user_id=-1,
            username=payload.username,
            ip_address=client_ip,
            request_size=request_size,
            status_code=401,
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")

    rate_limiter.clear_failures(client_ip, payload.username)
    previous_ip = event_repo.get_last_success_ip(user.id)
    different_device = previous_ip is not None and previous_ip != client_ip
    event_id = auth_service.new_event_id()
    event_repo.insert_login_event(
        event_id=event_id,
        user_id=user.id,
        username=user.username,
        ip_address=client_ip,
        request_size=request_size,
        status_code=200,
    )

    celery_app.send_task(
        "worker.tasks.ip_check.check_login_ip",
        kwargs={
            "event_id": event_id,
            "user_id": user.id,
            "username": user.username,
            "ip_address": client_ip,
        },
    )

    access_token, expires_in = create_access_token(subject=user.username, user_id=user.id)
    message = "Login successful"
    if different_device:
        message = "Login successful. You are on a different device/IP."
    return LoginResponse(
        success=True,
        message=message,
        user_id=user.id,
        event_id=event_id,
        access_token=access_token,
        token_type="bearer",
        expires_in=expires_in,
        different_device=different_device,
    )
