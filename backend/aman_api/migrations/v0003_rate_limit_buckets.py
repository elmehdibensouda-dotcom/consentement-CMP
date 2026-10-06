"""Persist shared rate-limit counters for SQLite deployments."""
import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS rate_limit_buckets ("
        "scope TEXT NOT NULL, bucket_hash TEXT NOT NULL, window_started_at INTEGER NOT NULL, "
        "request_count INTEGER NOT NULL, blocked_until INTEGER NOT NULL DEFAULT 0, "
        "PRIMARY KEY(scope,bucket_hash))"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rate_limit_window "
        "ON rate_limit_buckets(window_started_at,blocked_until)"
    )
