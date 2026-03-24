from datetime import datetime, timezone


class EventRepository:
    def __init__(self, clickhouse_client):
        self.client = clickhouse_client

    def create_table_if_not_exists(self):
        self.client.command(
            """
            CREATE TABLE IF NOT EXISTS login_events (
                event_id UUID,
                user_id Int64,
                username String,
                ip_address String,
                request_size Int64,
                status_code Int16,
                timestamp DateTime,
                ip_check_status String DEFAULT 'pending'
            )
            ENGINE = MergeTree
            ORDER BY (user_id, timestamp)
            """
        )
        self.client.command(
            """
            CREATE TABLE IF NOT EXISTS login_events_ip_check_audit (
                event_id UUID,
                user_id Int64,
                username String,
                ip_address String,
                status String,
                checked_at DateTime
            )
            ENGINE = MergeTree
            ORDER BY (user_id, checked_at)
            """
        )

    def insert_login_event(
        self,
        event_id: str,
        user_id: int,
        username: str,
        ip_address: str,
        request_size: int,
        status_code: int,
    ):
        self.client.insert(
            table="login_events",
            data=[
                [
                    event_id,
                    user_id,
                    username,
                    ip_address,
                    request_size,
                    status_code,
                    datetime.now(timezone.utc).replace(tzinfo=None),
                    "pending",
                ]
            ],
            column_names=[
                "event_id",
                "user_id",
                "username",
                "ip_address",
                "request_size",
                "status_code",
                "timestamp",
                "ip_check_status",
            ],
        )

    def get_last_success_ip(self, user_id: int) -> str | None:
        rows = self.client.query(
            """
            SELECT ip_address
            FROM login_events
            WHERE user_id = %(user_id)s
              AND status_code = 200
            ORDER BY timestamp DESC
            LIMIT 1
            """,
            parameters={"user_id": user_id},
        ).result_rows
        if not rows:
            return None
        return rows[0][0]
