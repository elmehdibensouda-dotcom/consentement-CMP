"""Persistence queries for organization-scoped audit history and exports."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from .database import Connection


def list_audit_events(conn: Connection, org_id: str, limit: int) -> list[Any]:
    return conn.execute(
        "SELECT e.id,e.actor_user_id,u.email AS actor_email,e.action,e.resource_type,e.resource_id,e.occurred_at,e.details "
        "FROM audit_events e JOIN users u ON u.id=e.actor_user_id "
        "WHERE e.org_id=? ORDER BY e.occurred_at DESC LIMIT ?",
        (org_id, limit),
    ).fetchall()


def iter_audit_export_events(
    conn: Connection,
    org_id: str,
    start: int | None,
    end: int | None,
    limit: int,
) -> Iterator[Any]:
    """Stream a bounded, chronologically ordered audit window from the database."""
    clauses = ["e.org_id=?"]
    parameters: list[Any] = [org_id]
    if start is not None:
        clauses.append("e.occurred_at>=?")
        parameters.append(start)
    if end is not None:
        clauses.append("e.occurred_at<=?")
        parameters.append(end)
    parameters.append(limit)
    cursor = conn.execute(
        "SELECT id,actor_user_id,actor_email,action,resource_type,resource_id,occurred_at,details FROM ("
        "SELECT e.id,e.actor_user_id,u.email AS actor_email,e.action,e.resource_type,e.resource_id,e.occurred_at,e.details "
        "FROM audit_events e JOIN users u ON u.id=e.actor_user_id WHERE " + " AND ".join(clauses) +
        " ORDER BY e.occurred_at DESC,e.id DESC LIMIT ?) ORDER BY occurred_at ASC,id ASC",
        parameters,
    )
    yield from cursor
