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
