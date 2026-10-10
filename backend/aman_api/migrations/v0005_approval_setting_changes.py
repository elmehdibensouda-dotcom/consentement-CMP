"""Store pending, two-person changes that weaken an organization's publication approval rule."""
import sqlite3

SCHEMA_SQL = (
    "CREATE TABLE IF NOT EXISTS approval_setting_changes ("
    "id TEXT PRIMARY KEY, "
    "org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE, "
    "requested_by TEXT NOT NULL REFERENCES users(id), "
    "require_two_person_publish INTEGER NOT NULL, "
    "created_at INTEGER NOT NULL, "
    "expires_at INTEGER NOT NULL, "
    "approved_by TEXT REFERENCES users(id), "
    "approved_at INTEGER, "
    "revoked_by TEXT REFERENCES users(id), "
    "revoked_at INTEGER)",
    "CREATE INDEX IF NOT EXISTS idx_approval_setting_changes_org "
    "ON approval_setting_changes(org_id, created_at)",
)


def upgrade(conn: sqlite3.Connection) -> None:
    for statement in SCHEMA_SQL:
        conn.execute(statement)
