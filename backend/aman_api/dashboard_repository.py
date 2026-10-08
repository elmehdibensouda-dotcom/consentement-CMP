"""Persistence queries that provide the multi-organization dashboard sources."""
from __future__ import annotations

from typing import Any

from .database import Connection


def load_dashboard_sources(
    conn: Connection,
    user_id: str,
    metrics_since: int,
    now: int,
) -> tuple[list[Any], list[Any], list[Any], list[Any]]:
    """Load only organizations and activity visible to the signed-in member."""
    organizations = conn.execute(
        "SELECT o.id,o.name,m.role FROM organizations o "
        "JOIN memberships m ON m.org_id=o.id WHERE m.user_id=? ORDER BY o.name",
        (user_id,),
    ).fetchall()
    properties = conn.execute(
        "SELECT p.id,p.org_id,o.name AS organization_name,p.name,p.channel,p.environment,p.origin,p.created_at,"
        "(SELECT MAX(x.version) FROM policies x WHERE x.property_id=p.id AND x.status='published') "
        "AS published_version,"
        "(SELECT COUNT(*) FROM policies x WHERE x.property_id=p.id AND x.status='draft') AS draft_count,"
        "(SELECT MAX(x.version) FROM policies x WHERE x.property_id=p.id AND x.status='draft') "
        "AS draft_version "
        "FROM properties p JOIN organizations o ON o.id=p.org_id "
        "JOIN memberships m ON m.org_id=o.id "
        "WHERE m.user_id=? ORDER BY o.name,p.name",
        (user_id,),
    ).fetchall()
    recent_events = conn.execute(
        "SELECT e.id,e.org_id,o.name AS organization_name,e.actor_user_id,u.email AS actor_email,e.action,"
        "e.resource_type,e.resource_id,e.occurred_at,e.details "
        "FROM audit_events e JOIN organizations o ON o.id=e.org_id "
        "JOIN users u ON u.id=e.actor_user_id "
        "JOIN memberships m ON m.org_id=o.id "
        "WHERE m.user_id=? ORDER BY e.occurred_at DESC,e.id DESC LIMIT 12",
        (user_id,),
    ).fetchall()
    consent_counts = conn.execute(
        "SELECT ce.property_id,"
        "SUM(CASE WHEN ce.recorded_at>=? THEN 1 ELSE 0 END) AS decision_count,"
        "SUM(CASE WHEN ce.recorded_at>=? AND ce.action='accept_all' THEN 1 ELSE 0 END) AS accept_all_count,"
        "SUM(CASE WHEN ce.recorded_at>=? AND ce.action='reject_all' THEN 1 ELSE 0 END) AS reject_all_count,"
        "SUM(CASE WHEN ce.recorded_at>=? AND ce.action='custom' THEN 1 ELSE 0 END) AS custom_count,"
        "MAX(ce.recorded_at) AS latest_decision_received_at "
        "FROM consent_events ce JOIN properties p ON p.id=ce.property_id "
        "JOIN memberships m ON m.org_id=p.org_id "
        "WHERE m.user_id=? AND ce.expires_at>? "
        "GROUP BY ce.property_id",
        (metrics_since, metrics_since, metrics_since, metrics_since, user_id, now),
    ).fetchall()
    return organizations, properties, recent_events, consent_counts
