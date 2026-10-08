"""Organization-scoped policy queries for the management console."""
from __future__ import annotations

from typing import Any

from .database import Connection


def list_property_policies(conn: Connection, property_id: str) -> list[Any]:
    return conn.execute(
        "SELECT p.id,p.version,p.revision,p.status,p.created_by,p.created_at,p.published_by,p.published_at,"
        "u.email AS author,COALESCE(editor.email,u.email) AS last_editor,publisher.email AS publisher "
        "FROM policies p JOIN users u ON u.id=p.created_by "
        "LEFT JOIN users editor ON editor.id=p.last_edited_by "
        "LEFT JOIN users publisher ON publisher.id=p.published_by "
        "WHERE p.property_id=? ORDER BY p.version DESC",
        (property_id,),
    ).fetchall()


def get_policy_for_organization(conn: Connection, policy_id: str, org_id: str) -> Any:
    return conn.execute(
        "SELECT p.id,p.property_id,p.version,p.revision,p.last_edited_by,p.status,p.body,p.created_by,p.created_at,"
        "p.published_by,p.published_at,u.email AS author,COALESCE(editor.email,u.email) AS last_editor,publisher.email AS publisher "
        "FROM policies p JOIN properties pr ON pr.id=p.property_id "
        "JOIN users u ON u.id=p.created_by "
        "LEFT JOIN users editor ON editor.id=p.last_edited_by "
        "LEFT JOIN users publisher ON publisher.id=p.published_by "
        "WHERE p.id=? AND pr.org_id=?",
        (policy_id, org_id),
    ).fetchone()
