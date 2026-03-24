from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "auth-prime-api"
    environment: str = "dev"

    sqlite_path: str = "/data/users.db"
    redis_url: str = "redis://redis:6379/0"
    clickhouse_host: str = "clickhouse"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_database: str = "default"

    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/1"

    otel_service_name: str = "fastapi-app"
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    jwt_secret_key: str = "development-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    login_attempts_per_minute: int = 20
    login_attempts_per_user_per_minute: int = 10
    login_max_failures_before_block: int = 8
    login_failure_window_seconds: int = 900
    login_block_seconds: int = 900

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
