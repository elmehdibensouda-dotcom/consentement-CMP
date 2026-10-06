"""Initial PostgreSQL schema for a new Aman preproduction database.

This version is intentionally separate from SQLite migrations. The SQL schema
is shared as a starting snapshot; PostgreSQL-only invariants are added here.
"""
from __future__ import annotations

import re

from .migrations.v0001_initial_schema import SCHEMA_SQL


VERSION = 1
NAME = "initial_schema"


def upgrade(connection) -> None:
    # SQLite's INTEGER is 64-bit; PostgreSQL INTEGER is not. Keep epoch times
    # wide enough for long-lived sessions, retention horizons, and audit dates.
    schema_sql = re.sub(r"\b([a-z_]+_at)\s+INTEGER\b", r"\1 BIGINT", SCHEMA_SQL)
    for statement in schema_sql.split(";"):
        if statement.strip():
            connection.execute(statement)
    connection.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_one_published_policy_per_property "
        "ON policies(property_id) WHERE status='published'"
    )
