"""Persistence queries for SDK-facing published consent policies."""
from __future__ import annotations

from typing import Any

from .database import Connection


def get_published_policy(conn: Connection, property_id: str) -> Any:
    return conn.execute(
        "SELECT p.id,p.version,p.body,p.published_at FROM policies p "
        "JOIN properties pr ON pr.id=p.property_id WHERE pr.id=? AND p.status='published'",
        (property_id,),
    ).fetchone()
