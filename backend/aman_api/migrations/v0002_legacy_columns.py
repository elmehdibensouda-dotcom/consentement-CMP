"""Bring databases created by pre-migration releases to the current columns."""
import sqlite3


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def upgrade(conn: sqlite3.Connection) -> None:
    property_columns = _columns(conn, "properties")
    policy_columns = _columns(conn, "policies")
    if "origin" not in property_columns:
        conn.execute("ALTER TABLE properties ADD COLUMN origin TEXT")
    if "environment" not in property_columns:
        conn.execute(
            "ALTER TABLE properties ADD COLUMN environment TEXT NOT NULL DEFAULT 'development' "
            "CHECK (environment IN ('development','staging','production'))"
        )
    if "revision" not in policy_columns:
        conn.execute("ALTER TABLE policies ADD COLUMN revision INTEGER NOT NULL DEFAULT 1")
    if "last_edited_by" not in policy_columns:
        conn.execute("ALTER TABLE policies ADD COLUMN last_edited_by TEXT REFERENCES users(id)")
    conn.execute("UPDATE policies SET last_edited_by=created_by WHERE last_edited_by IS NULL")
