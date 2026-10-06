"""Enforce at most one published policy for each property in SQLite."""
import sqlite3


def upgrade(conn: sqlite3.Connection) -> None:
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_one_published_policy_per_property "
        "ON policies(property_id) WHERE status='published'"
    )
