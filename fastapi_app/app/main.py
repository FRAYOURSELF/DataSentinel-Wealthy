import logging

from fastapi import FastAPI

from app.api.routes.auth import router as auth_router
from app.api.routes.primes import router as prime_router
from app.db.clickhouse import get_clickhouse_client
from app.db.sqlite import Base, engine
from app.instrumentation.metrics import install_metrics
from app.instrumentation.tracing import install_tracing
from app.repositories.event_repo import EventRepository

app = FastAPI(title="Auth + Prime API", version="1.0.0")
logger = logging.getLogger(__name__)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    try:
        clickhouse = get_clickhouse_client()
        EventRepository(clickhouse).create_table_if_not_exists()
    except Exception as exc:
        # App remains available even if analytics store is temporarily unavailable.
        logger.warning("ClickHouse initialization skipped: %s", exc)


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth_router)
app.include_router(prime_router)
install_metrics(app)
install_tracing(app)
