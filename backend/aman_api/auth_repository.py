"""Persistence operations for account authentication and sessions."""
from __future__ import annotations

from typing import Any

from .database import Connection


def get_user_credentials(conn: Connection, email: str) -> Any:
    return conn.execute(
        "SELECT id,password_hash,disabled FROM users WHERE email=?",
        (email,),
    ).fetchone()


def get_session_user(conn: Connection, token_hash: str) -> Any:
    return conn.execute(
        "SELECT s.user_id,s.expires_at,u.email,u.disabled FROM sessions s "
        "JOIN users u ON u.id=s.user_id WHERE s.token_hash=?",
        (token_hash,),
    ).fetchone()


def get_session_csrf_hash(conn: Connection, token_hash: str) -> Any:
    return conn.execute(
        "SELECT csrf_hash FROM sessions WHERE token_hash=?",
        (token_hash,),
    ).fetchone()


def delete_session(conn: Connection, token_hash: str) -> None:
    conn.execute("DELETE FROM sessions WHERE token_hash=?", (token_hash,))


def delete_expired_sessions(conn: Connection, now: int) -> None:
    conn.execute("DELETE FROM sessions WHERE expires_at<=?", (now,))


def create_session(
    conn: Connection, token_hash: str, csrf_hash: str, user_id: str,
    expires_at: int, created_at: int,
) -> None:
    conn.execute(
        "INSERT INTO sessions(token_hash,csrf_hash,user_id,expires_at,created_at) VALUES(?,?,?,?,?)",
        (token_hash, csrf_hash, user_id, expires_at, created_at),
    )


def list_auth_user_organizations(conn: Connection, user_id: str) -> list[Any]:
    return conn.execute(
        "SELECT o.id,o.name,m.role FROM organizations o JOIN memberships m ON m.org_id=o.id "
        "WHERE m.user_id=? ORDER BY o.name",
        (user_id,),
    ).fetchall()
