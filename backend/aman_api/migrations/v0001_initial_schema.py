"""Create the current SQLite schema on an empty database."""
import sqlite3


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  disabled INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS organizations (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  require_two_person_publish INTEGER NOT NULL DEFAULT 1,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS memberships (
  org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('owner','admin','editor','viewer')),
  created_at INTEGER NOT NULL,
  PRIMARY KEY (org_id, user_id)
);
CREATE TABLE IF NOT EXISTS invitations (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  email TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','editor','viewer')),
  token_hash TEXT NOT NULL UNIQUE,
  invited_by TEXT NOT NULL REFERENCES users(id),
  expires_at INTEGER NOT NULL,
  accepted_at INTEGER
);
CREATE TABLE IF NOT EXISTS ownership_transfers (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  current_owner_id TEXT NOT NULL REFERENCES users(id),
  proposed_owner_id TEXT NOT NULL REFERENCES users(id),
  token_hash TEXT NOT NULL UNIQUE,
  created_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  accepted_at INTEGER,
  revoked_at INTEGER
);
CREATE TABLE IF NOT EXISTS properties (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('web','ios','android')),
  environment TEXT NOT NULL DEFAULT 'development' CHECK (environment IN ('development','staging','production')),
  origin TEXT,
  created_at INTEGER NOT NULL,
  UNIQUE (org_id, name, channel)
);
CREATE TABLE IF NOT EXISTS policies (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  revision INTEGER NOT NULL DEFAULT 1,
  last_edited_by TEXT REFERENCES users(id),
  status TEXT NOT NULL CHECK (status IN ('draft','published','retired')),
  body TEXT NOT NULL,
  created_by TEXT NOT NULL REFERENCES users(id),
  created_at INTEGER NOT NULL,
  published_by TEXT REFERENCES users(id),
  published_at INTEGER,
  UNIQUE (property_id, version)
);
CREATE INDEX IF NOT EXISTS idx_memberships_user ON memberships(user_id);
CREATE INDEX IF NOT EXISTS idx_properties_org ON properties(org_id);
CREATE INDEX IF NOT EXISTS idx_policies_property_status ON policies(property_id, status);
CREATE TABLE IF NOT EXISTS sessions (
  token_hash TEXT PRIMARY KEY,
  csrf_hash TEXT NOT NULL,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE TABLE IF NOT EXISTS audit_events (
  id TEXT PRIMARY KEY,
  org_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
  actor_user_id TEXT NOT NULL REFERENCES users(id),
  action TEXT NOT NULL,
  resource_type TEXT NOT NULL,
  resource_id TEXT NOT NULL,
  occurred_at INTEGER NOT NULL,
  details TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_audit_org_time ON audit_events(org_id, occurred_at DESC);
CREATE TABLE IF NOT EXISTS consent_events (
  event_id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  policy_version TEXT NOT NULL,
  channel TEXT NOT NULL CHECK (channel IN ('web','ios','android')),
  action TEXT NOT NULL CHECK (action IN ('accept_all','reject_all','custom')),
  purposes TEXT NOT NULL,
  recorded_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_consent_events_property_time ON consent_events(property_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_consent_events_expiry ON consent_events(expires_at);
CREATE TABLE IF NOT EXISTS scan_reports (
  id TEXT PRIMARY KEY,
  property_id TEXT NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  imported_by TEXT NOT NULL REFERENCES users(id),
  scanned_at INTEGER NOT NULL,
  imported_at INTEGER NOT NULL,
  page_origin TEXT NOT NULL,
  resource_count INTEGER NOT NULL,
  cookie_count INTEGER NOT NULL,
  report_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_scan_reports_property_time ON scan_reports(property_id, imported_at DESC);
"""


def upgrade(conn: sqlite3.Connection) -> None:
    statement = ""
    for line in SCHEMA_SQL.splitlines(keepends=True):
        statement += line
        if sqlite3.complete_statement(statement):
            if statement.strip():
                conn.execute(statement)
            statement = ""
    if statement.strip():
        raise RuntimeError("Incomplete SQL in migration 1")
