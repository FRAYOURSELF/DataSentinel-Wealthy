import time

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from starlette.responses import Response

REQUEST_COUNT = Counter("fastapi_http_requests_total", "Total HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("fastapi_http_request_duration_seconds", "HTTP latency", ["method", "path"])
REQUEST_SIZE = Histogram("fastapi_http_request_size_bytes", "HTTP request size", ["method", "path"])


def install_metrics(app):
    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next):
        method = request.method
        path = request.url.path
        start_time = time.perf_counter()

        request_length = request.headers.get("content-length")
        if request_length is not None and request_length.isdigit():
            REQUEST_SIZE.labels(method=method, path=path).observe(float(request_length))

        response = await call_next(request)
        elapsed = time.perf_counter() - start_time

        status_class = f"{response.status_code // 100}xx"
        REQUEST_COUNT.labels(method=method, path=path, status=status_class).inc()
        REQUEST_LATENCY.labels(method=method, path=path).observe(elapsed)
        return response

    @app.get("/metrics")
    async def metrics_endpoint():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
