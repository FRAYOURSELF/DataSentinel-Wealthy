from datetime import datetime, timezone

import clickhouse_connect

from worker.celery_app import celery_app
from worker.config import (
    CLICKHOUSE_DATABASE,
    CLICKHOUSE_HOST,
    CLICKHOUSE_PASSWORD,
    CLICKHOUSE_PORT,
    CLICKHOUSE_USER,
)


def _clickhouse_client():
    return clickhouse_connect.get_client(
        host=CLICKHOUSE_HOST,
        port=CLICKHOUSE_PORT,
        username=CLICKHOUSE_USER,
        password=CLICKHOUSE_PASSWORD,
        database=CLICKHOUSE_DATABASE,
    )


@celery_app.task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    name="worker.tasks.ip_check.check_login_ip",
)
def check_login_ip(self, event_id: str, user_id: int, username: str, ip_address: str):
    client = _clickhouse_client()

    row = client.query(
        """
        SELECT ip_address
        FROM login_events
        WHERE user_id = %(user_id)s
          AND status_code = 200
          AND event_id != %(event_id)s
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        parameters={"user_id": user_id, "event_id": event_id},
    ).result_rows

    if not row:
        status = "first_login"
    elif row[0][0] == ip_address:
        status = "same_ip"
    else:
        status = "ip_changed"

    client.command(
        """
        ALTER TABLE login_events
        UPDATE ip_check_status = %(status)s
        WHERE event_id = %(event_id)s
        """,
        parameters={"status": status, "event_id": event_id},
    )

    client.insert(
        "login_events_ip_check_audit",
        [
            [
                event_id,
                user_id,
                username,
                ip_address,
                status,
                datetime.now(timezone.utc).replace(tzinfo=None),
            ]
        ],
        column_names=["event_id", "user_id", "username", "ip_address", "status", "checked_at"],
    )
    return status
