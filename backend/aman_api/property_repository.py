"""Persistence operations for organization-owned properties."""
from __future__ import annotations

from typing import Any

from .database import Connection


def create_property(
    conn: Connection,
    property_id: str,
    org_id: str,
    name: str,
    channel: str,
    environment: str,
    origin: str | None,
    created_at: int,
) -> None:
    conn.execute(
        "INSERT INTO properties(id,org_id,name,channel,environment,origin,created_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (property_id, org_id, name, channel, environment, origin, created_at),
    )


def list_properties(conn: Connection, org_id: str) -> list[Any]:
    return conn.execute(
        "SELECT p.id,p.name,p.channel,p.environment,p.origin,p.created_at,("
        "SELECT version FROM policies x WHERE x.property_id=p.id "
        "AND x.status='published' ORDER BY version DESC LIMIT 1) AS published_version "
        "FROM properties p WHERE p.org_id=? ORDER BY p.name",
        (org_id,),
    ).fetchall()


def get_property_for_origin_update(conn: Connection, org_id: str, property_id: str) -> Any:
    return conn.execute(
        "SELECT id,channel,environment,origin FROM properties WHERE id=? AND org_id=?",
        (property_id, org_id),
    ).fetchone()


def get_property_for_organization(conn: Connection, org_id: str, property_id: str) -> Any:
    return conn.execute(
        "SELECT id,channel,origin FROM properties WHERE id=? AND org_id=?",
        (property_id, org_id),
    ).fetchone()


def get_public_property(conn: Connection, property_id: str) -> Any:
    return conn.execute(
        "SELECT origin,channel FROM properties WHERE id=?",
        (property_id,),
    ).fetchone()


def has_scan_reports(conn: Connection, property_id: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM scan_reports WHERE property_id=? LIMIT 1", (property_id,)
    ).fetchone() is not None


def update_property_origin(conn: Connection, property_id: str, origin: str) -> None:
    conn.execute("UPDATE properties SET origin=? WHERE id=?", (origin, property_id))
