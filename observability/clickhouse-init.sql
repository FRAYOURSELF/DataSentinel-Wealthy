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
ORDER BY (user_id, timestamp);

CREATE TABLE IF NOT EXISTS login_events_ip_check_audit (
    event_id UUID,
    user_id Int64,
    username String,
    ip_address String,
    status String,
    checked_at DateTime
)
ENGINE = MergeTree
ORDER BY (user_id, checked_at);
