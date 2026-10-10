"""Persistence operations for pending changes to the two-person publication rule."""
from __future__ import annotations

from typing import Any

from .database import Connection


def get_pending_change(conn: Connection, org_id: str, now: int) -> Any:
    return conn.execute(
        "SELECT c.id,c.requested_by AS \"requestedBy\",u.email AS \"requestedByEmail\","
        "c.require_two_person_publish,c.created_at AS \"createdAt\",c.expires_at AS \"expiresAt\" "
        "FROM approval_setting_changes c JOIN users u ON u.id=c.requested_by "
        "WHERE c.org_id=? AND c.approved_at IS NULL AND c.revoked_at IS NULL AND c.expires_at>? "
        "ORDER BY c.created_at DESC LIMIT 1",
        (org_id, now),
    ).fetchone()


def get_change(conn: Connection, org_id: str, change_id: str) -> Any:
    return conn.execute(
        "SELECT id,requested_by,require_two_person_publish,expires_at,approved_at,revoked_at "
        "FROM approval_setting_changes WHERE org_id=? AND id=?",
        (org_id, change_id),
    ).fetchone()


def create_change(
    conn: Connection, change_id: str, org_id: str, requested_by: str, enabled: bool,
    created_at: int, expires_at: int,
) -> None:
    conn.execute(
        "INSERT INTO approval_setting_changes(id,org_id,requested_by,require_two_person_publish,created_at,expires_at) "
        "VALUES(?,?,?,?,?,?)",
        (change_id, org_id, requested_by, int(enabled), created_at, expires_at),
    )


def mark_change_approved(conn: Connection, change_id: str, approved_by: str, approved_at: int) -> None:
    conn.execute(
        "UPDATE approval_setting_changes SET approved_by=?,approved_at=? WHERE id=?",
        (approved_by, approved_at, change_id),
    )


def revoke_pending_changes(conn: Connection, org_id: str, revoked_by: str, now: int) -> list[Any]:
    rows = conn.execute(
        "SELECT id FROM approval_setting_changes WHERE org_id=? AND approved_at IS NULL "
        "AND revoked_at IS NULL AND expires_at>?",
        (org_id, now),
    ).fetchall()
    conn.execute(
        "UPDATE approval_setting_changes SET revoked_by=?,revoked_at=? WHERE org_id=? "
        "AND approved_at IS NULL AND revoked_at IS NULL AND expires_at>?",
        (revoked_by, now, org_id, now),
    )
    return rows
