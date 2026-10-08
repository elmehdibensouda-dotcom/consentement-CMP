"""Persistence queries used to build organization-scoped consent aggregates."""
from __future__ import annotations

import json
from typing import Any

from .database import Connection


def load_consent_metric_sources(
    conn: Connection,
    property_id: str,
    since: int,
    now: int,
) -> tuple[list[Any], dict[str, dict[str, dict[str, str]]]]:
    """Load retained decisions and historical labels for the requested property.

    The route combines these rows into aggregates. Keeping the SQL here means the
    route does not depend on a concrete database driver or query implementation.
    """
    rows = conn.execute(
        "SELECT action,purposes,policy_version,recorded_at FROM consent_events "
        "WHERE property_id=? AND recorded_at>=? AND expires_at>? ORDER BY recorded_at DESC",
        (property_id, since, now),
    ).fetchall()
    versions = sorted({
        int(row["policy_version"])
        for row in rows
        if str(row["policy_version"]).isdigit()
    })

    labels: dict[str, dict[str, dict[str, str]]] = {}
    for offset in range(0, len(versions), 500):
        batch = versions[offset:offset + 500]
        placeholders = ",".join("?" for _ in batch)
        policies = conn.execute(
            "SELECT version,body FROM policies WHERE property_id=? AND status IN ('published','retired') "
            f"AND version IN ({placeholders})",
            (property_id, *batch),
        ).fetchall()
        for policy in policies:
            body = json.loads(policy["body"])
            labels[str(policy["version"])] = {
                purpose["id"]: purpose.get("label", {})
                for purpose in body.get("purposes", [])
            }
    return rows, labels


def load_organization_consent_metric_sources(
    conn: Connection,
    org_id: str,
    since: int,
    now: int,
) -> tuple[list[Any], list[Any], dict[str, dict[str, dict[str, dict[str, str]]]], dict[str, int]]:
    """Load retained SDK decisions and the matching policy labels for one organization."""
    properties = conn.execute(
        "SELECT id,name,channel FROM properties WHERE org_id=? ORDER BY name,id",
        (org_id,),
    ).fetchall()
    events = conn.execute(
        "SELECT e.property_id,p.name AS property_name,p.channel,e.action,e.purposes,"
        "e.policy_version,e.recorded_at FROM consent_events e "
        "JOIN properties p ON p.id=e.property_id "
        "WHERE p.org_id=? AND e.recorded_at>=? AND e.expires_at>? "
        "ORDER BY e.recorded_at DESC,e.event_id DESC",
        (org_id, since, now),
    ).fetchall()
    policy_rows = conn.execute(
        "SELECT pol.property_id,pol.version,pol.body FROM policies pol "
        "JOIN properties p ON p.id=pol.property_id "
        "JOIN (SELECT DISTINCT e.property_id,CAST(e.policy_version AS INTEGER) AS version "
        "FROM consent_events e JOIN properties ep ON ep.id=e.property_id "
        "WHERE ep.org_id=? AND e.recorded_at>=? AND e.expires_at>?) observed "
        "ON observed.property_id=pol.property_id AND observed.version=pol.version "
        "WHERE p.org_id=? AND pol.status IN ('published','retired')",
        (org_id, since, now, org_id),
    ).fetchall()
    labels: dict[str, dict[str, dict[str, dict[str, str]]]] = {}
    for policy in policy_rows:
        property_labels = labels.setdefault(policy["property_id"], {})
        body = json.loads(policy["body"])
        property_labels[str(policy["version"])] = {
            purpose["id"]: purpose.get("label", {})
            for purpose in body.get("purposes", [])
        }
    active_rows = conn.execute(
        "SELECT e.property_id,COUNT(*) AS event_count FROM consent_events e "
        "JOIN properties p ON p.id=e.property_id "
        "WHERE p.org_id=? AND e.expires_at>? GROUP BY e.property_id",
        (org_id, now),
    ).fetchall()
    active_counts = {row["property_id"]: int(row["event_count"]) for row in active_rows}
    return properties, events, labels, active_counts
