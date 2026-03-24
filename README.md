# DataSentinel-Wealthy

Production-ready backend system with:
- FastAPI (auth + prime APIs)
- Celery + Redis (background jobs)
- SQLite (users)
- ClickHouse (login events)
- VictoriaMetrics + Grafana (metrics)
- Locust (load test)

Prime computation is now handled directly in FastAPI for sync APIs, and segmented in Celery for async jobs.

## Project Structure

- `fastapi_app/`
- `celery_worker/`
- `locust/`
- `observability/`
- `docker-compose.yml`

## APIs

### Public
- `POST /login`
- `GET /health`
- `GET /metrics`

### Protected (Bearer token required)
- `GET /check-prime?number=x`
- `GET /primes?n=x`
- `POST /prime-jobs`
- `GET /prime-jobs/{job_id}`
- `GET /prime-jobs/{job_id}/result`

## Local Run (No Docker)

### 1) Prerequisites

```bash
brew install redis clickhouse victoriametrics grafana
```

### 2) Start Redis

```bash
brew services start redis
redis-cli ping
```

### 3) Start ClickHouse

```bash
mkdir -p $HOME/clickhouse-data
clickhouse server -- --path=$HOME/clickhouse-data --http_port=8123 --tcp_port=9000 --listen_host=127.0.0.1
```

Health check in another terminal:

```bash
clickhouse client --query "SELECT 1"
curl -s http://localhost:8123/ping
```

### 4) Create and activate Python venv

```bash
cd /Users/sahil.agarwal1/Desktop/Wealthy
python3 -m venv .venv
source .venv/bin/activate
pip install -r fastapi_app/requirements.txt
pip install -r celery_worker/requirements.txt
pip install -r requirements-test.txt
```

### 5) Start FastAPI

```bash
cd /Users/sahil.agarwal1/Desktop/Wealthy
source .venv/bin/activate
mkdir -p /Users/sahil.agarwal1/Desktop/Wealthy/.local

export SQLITE_PATH=/Users/sahil.agarwal1/Desktop/Wealthy/.local/users.db
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_PORT=8123
export CLICKHOUSE_USER=default
export CLICKHOUSE_PASSWORD=
export CLICKHOUSE_DATABASE=default

cd fastapi_app
PYTHONPATH=. python -m scripts.init_db
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6) Start Celery worker

Use local Redis + solo mode for accurate local metrics:

```bash
cd /Users/sahil.agarwal1/Desktop/Wealthy/celery_worker
source /Users/sahil.agarwal1/Desktop/Wealthy/.venv/bin/activate
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/0
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_PORT=8123
celery -A worker.celery_app.celery_app worker --loglevel=INFO --pool=solo --concurrency=1
```

### 7) Start VictoriaMetrics

```bash
victoria-metrics -promscrape.config=/Users/sahil.agarwal1/Desktop/Wealthy/observability/prometheus-local.yml
```

### 8) Start Grafana

```bash
mkdir -p /opt/homebrew/etc/grafana/provisioning/datasources
cp /Users/sahil.agarwal1/Desktop/Wealthy/observability/grafana/provisioning/datasources/datasource-local.yml \
  /opt/homebrew/etc/grafana/provisioning/datasources/
brew services restart grafana
```

Grafana URL: `http://localhost:3000` (`admin/admin`)

## Docker Run

If Docker works in your environment:

```bash
docker-compose up --build
```

## Authentication & Protected Calls

Get token:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"alice_password"}' | jq -r '.access_token')
```

Protected request:

```bash
curl -s "http://localhost:8000/check-prime?number=104729" \
  -H "Authorization: Bearer $TOKEN"
```

## Quick End-to-End Smoke

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/login -H "Content-Type: application/json" -d '{"username":"alice","password":"alice_password"}' | jq -r '.access_token')
curl -s "http://localhost:8000/check-prime?number=104729" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/primes?n=50000" -H "Authorization: Bearer $TOKEN"
JOB_ID=$(curl -s -X POST http://localhost:8000/prime-jobs -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"n":300000,"segment_size":50000}' | jq -r '.job_id')
curl -s "http://localhost:8000/prime-jobs/$JOB_ID" -H "Authorization: Bearer $TOKEN"
curl -s "http://localhost:8000/prime-jobs/$JOB_ID/result" -H "Authorization: Bearer $TOKEN"
```

## Tests

```bash
cd /Users/sahil.agarwal1/Desktop/Wealthy
source .venv/bin/activate
python -m pytest -q
```

## Notes

- Runtime/generated folders should not be committed (`.venv`, `__pycache__`, `.local`, `access`, `preprocessed_configs`, `victoria-metrics-data`).
- Prime async metrics for Celery are most reliable in local mode with `--pool=solo`.

## Screenshots

<img width="1724" height="1082" alt="Screenshot 2026-03-24 at 2 32 24 PM" src="https://github.com/user-attachments/assets/191acbbc-45bb-4519-8521-0aa56f0157c0" />
<img width="1728" height="1085" alt="Screenshot 2026-03-24 at 2 32 43 PM" src="https://github.com/user-attachments/assets/c6968a15-f057-40a7-8842-fddafe46e286" />
<img width="1725" height="1087" alt="Screenshot 2026-03-24 at 2 32 51 PM" src="https://github.com/user-attachments/assets/610e66d1-d353-4db3-982e-393aeb1e33a5" />
