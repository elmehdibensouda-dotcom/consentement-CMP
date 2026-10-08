"""Persistence operations for organization ownership transfers."""
from __future__ import annotations

from typing import Any

from .database import Connection


def get_transfer_by_token_hash(conn: Connection, token_hash: str) -> Any:
    return conn.execute(
        "SELECT id,org_id,current_owner_id,proposed_owner_id,expires_at,accepted_at,revoked_at "
        "FROM ownership_transfers WHERE token_hash=?",
        (token_hash,),
    ).fetchone()


def get_membership_role(conn: Connection, org_id: str, user_id: str) -> Any:
    return conn.execute(
        "SELECT role FROM memberships WHERE org_id=? AND user_id=?",
        (org_id, user_id),
    ).fetchone()


def update_member_role(conn: Connection, org_id: str, user_id: str, role: str) -> None:
    conn.execute(
        "UPDATE memberships SET role=? WHERE org_id=? AND user_id=?",
        (role, org_id, user_id),
    )


def mark_transfer_accepted(conn: Connection, transfer_id: str, accepted_at: int) -> None:
    conn.execute("UPDATE ownership_transfers SET accepted_at=? WHERE id=?", (accepted_at, transfer_id))


def revoke_other_pending_transfers(
    conn: Connection, org_id: str, accepted_transfer_id: str, revoked_at: int,
) -> None:
    conn.execute(
        "UPDATE ownership_transfers SET revoked_at=? WHERE org_id=? AND accepted_at IS NULL "
        "AND revoked_at IS NULL AND id<>?",
        (revoked_at, org_id, accepted_transfer_id),
    )


def has_active_transfer(conn: Connection, org_id: str, now: int) -> bool:
    return conn.execute(
        "SELECT id FROM ownership_transfers WHERE org_id=? AND accepted_at IS NULL "
        "AND revoked_at IS NULL AND expires_at>? LIMIT 1",
        (org_id, now),
    ).fetchone() is not None


def create_transfer(
    conn: Connection,
    transfer_id: str,
    org_id: str,
    current_owner_id: str,
    proposed_owner_id: str,
    token_hash: str,
    created_at: int,
    expires_at: int,
) -> None:
    conn.execute(
        "INSERT INTO ownership_transfers(id,org_id,current_owner_id,proposed_owner_id,token_hash,created_at,expires_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (transfer_id, org_id, current_owner_id, proposed_owner_id, token_hash, created_at, expires_at),
    )


def get_pending_transfer(conn: Connection, org_id: str, current_owner_id: str, now: int) -> Any:
    return conn.execute(
        "SELECT t.id,t.created_at,t.expires_at,u.email AS proposedOwner "
        "FROM ownership_transfers t JOIN users u ON u.id=t.proposed_owner_id "
        "WHERE t.org_id=? AND t.current_owner_id=? AND t.accepted_at IS NULL "
        "AND t.revoked_at IS NULL AND t.expires_at>? ORDER BY t.created_at DESC LIMIT 1",
        (org_id, current_owner_id, now),
    ).fetchone()


def list_pending_transfers_for_revocation(
    conn: Connection, org_id: str, current_owner_id: str, now: int,
) -> list[Any]:
    return conn.execute(
        "SELECT id FROM ownership_transfers WHERE org_id=? AND current_owner_id=? "
        "AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at>?",
        (org_id, current_owner_id, now),
    ).fetchall()


def revoke_pending_transfers(conn: Connection, org_id: str, current_owner_id: str, now: int) -> None:
    conn.execute(
        "UPDATE ownership_transfers SET revoked_at=? WHERE org_id=? AND current_owner_id=? "
        "AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at>?",
        (now, org_id, current_owner_id, now),
    )
