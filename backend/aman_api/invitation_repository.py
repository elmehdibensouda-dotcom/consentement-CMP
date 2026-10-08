"""Persistence operations for organization invitations."""
from __future__ import annotations

from typing import Any

from .database import Connection


def get_user_for_invitation(conn: Connection, email: str) -> Any:
    return conn.execute("SELECT id,disabled FROM users WHERE email=?", (email,)).fetchone()


def get_invitation_preview(conn: Connection, token_hash: str, now: int) -> Any:
    return conn.execute(
        "SELECT i.email,i.role,i.expires_at,o.name AS organization_name "
        "FROM invitations i JOIN organizations o ON o.id=i.org_id "
        "WHERE i.token_hash=? AND i.accepted_at IS NULL AND i.expires_at>?",
        (token_hash, now),
    ).fetchone()


def get_invitation_for_acceptance(conn: Connection, token_hash: str) -> Any:
    return conn.execute(
        "SELECT id,org_id,email,role,expires_at,accepted_at FROM invitations WHERE token_hash=?",
        (token_hash,),
    ).fetchone()


def get_invited_user_account(conn: Connection, email: str) -> Any:
    return conn.execute(
        "SELECT id,password_hash,disabled FROM users WHERE email=?",
        (email,),
    ).fetchone()


def create_invited_user(
    conn: Connection, user_id: str, email: str, password_hash: str, created_at: int,
) -> None:
    conn.execute(
        "INSERT INTO users(id,email,password_hash,created_at) VALUES(?,?,?,?)",
        (user_id, email, password_hash, created_at),
    )


def is_organization_member(conn: Connection, org_id: str, user_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM memberships WHERE org_id=? AND user_id=?",
        (org_id, user_id),
    ).fetchone() is not None


def add_invited_member(conn: Connection, org_id: str, user_id: str, role: str, created_at: int) -> None:
    conn.execute(
        "INSERT INTO memberships(org_id,user_id,role,created_at) VALUES(?,?,?,?)",
        (org_id, user_id, role, created_at),
    )


def mark_invitation_accepted(conn: Connection, invitation_id: str, accepted_at: int) -> None:
    conn.execute("UPDATE invitations SET accepted_at=? WHERE id=?", (accepted_at, invitation_id))


def has_active_invitation(conn: Connection, org_id: str, email: str, now: int) -> bool:
    return conn.execute(
        "SELECT 1 FROM invitations WHERE org_id=? AND email=? AND accepted_at IS NULL "
        "AND expires_at>? LIMIT 1",
        (org_id, email, now),
    ).fetchone() is not None


def create_invitation(
    conn: Connection,
    invitation_id: str,
    org_id: str,
    email: str,
    role: str,
    token_hash: str,
    invited_by: str,
    expires_at: int,
) -> None:
    conn.execute(
        "INSERT INTO invitations(id,org_id,email,role,token_hash,invited_by,expires_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (invitation_id, org_id, email, role, token_hash, invited_by, expires_at),
    )


def list_organization_invitations(conn: Connection, org_id: str) -> list[Any]:
    return conn.execute(
        "SELECT i.id,i.email,i.role,i.expires_at AS expiresAt,u.email AS invitedBy "
        "FROM invitations i JOIN users u ON u.id=i.invited_by "
        "WHERE i.org_id=? AND i.accepted_at IS NULL "
        "ORDER BY i.expires_at DESC,i.email",
        (org_id,),
    ).fetchall()


def get_invitation_for_revocation(conn: Connection, org_id: str, invitation_id: str) -> Any:
    return conn.execute(
        "SELECT email,role,accepted_at FROM invitations WHERE id=? AND org_id=?",
        (invitation_id, org_id),
    ).fetchone()


def revoke_invitation(conn: Connection, org_id: str, invitation_id: str) -> None:
    conn.execute("DELETE FROM invitations WHERE id=? AND org_id=?", (invitation_id, org_id))
