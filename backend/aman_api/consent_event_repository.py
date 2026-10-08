"""Read queries for organization-requested consent event exports."""
from __future__ import annotations

from typing import Any

from .database import Connection


def count_events_for_export(conn: Connection, property_id: str, since: int, now: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS event_count FROM consent_events "
        "WHERE property_id=? AND recorded_at>=? AND expires_at>?",
        (property_id, since, now),
    ).fetchone()
    return int(row["event_count"])


def iter_events_for_export(conn: Connection, property_id: str, since: int, now: int) -> Any:
    """Return an ordered cursor; the route iterates rows without calling fetchall."""
    return conn.execute(
        "SELECT event_id,recorded_at,expires_at,property_id,policy_version,channel,action,purposes "
        "FROM consent_events WHERE property_id=? AND recorded_at>=? AND expires_at>? "
        "ORDER BY recorded_at ASC,event_id ASC",
        (property_id, since, now),
    )
