"""Add cross-process rate-limit storage to a PostgreSQL deployment."""

VERSION = 2
NAME = "rate_limit_buckets"


def upgrade(connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS rate_limit_buckets ("
        "scope TEXT NOT NULL, bucket_hash TEXT NOT NULL, window_started_at BIGINT NOT NULL, "
        "request_count INTEGER NOT NULL, blocked_until BIGINT NOT NULL DEFAULT 0, "
        "PRIMARY KEY(scope,bucket_hash))"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_rate_limit_window "
        "ON rate_limit_buckets(window_started_at,blocked_until)"
    )
