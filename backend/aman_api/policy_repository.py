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


def get_property_channel(conn: Connection, org_id: str, property_id: str) -> Any:
    return conn.execute(
        "SELECT id,channel FROM properties WHERE id=? AND org_id=?",
        (property_id, org_id),
    ).fetchone()


def next_policy_version(conn: Connection, property_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(version),0)+1 AS n FROM policies WHERE property_id=?",
        (property_id,),
    ).fetchone()
    return int(row["n"])


def insert_policy_draft(
    conn: Connection,
    policy_id: str,
    property_id: str,
    version: int,
    actor_id: str,
    body: str,
    created_at: int,
) -> None:
    conn.execute(
        "INSERT INTO policies(id,property_id,version,revision,last_edited_by,status,body,created_by,created_at) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (policy_id, property_id, version, 1, actor_id, "draft", body, actor_id, created_at),
    )


def get_policy_for_draft_update(conn: Connection, policy_id: str, org_id: str) -> Any:
    return conn.execute(
        "SELECT p.id,p.property_id,p.version,p.revision,p.status,pr.channel FROM policies p "
        "JOIN properties pr ON pr.id=p.property_id WHERE p.id=? AND pr.org_id=?",
        (policy_id, org_id),
    ).fetchone()


def update_policy_draft(
    conn: Connection,
    policy_id: str,
    expected_revision: int,
    actor_id: str,
    body: str,
) -> int:
    cursor = conn.execute(
        "UPDATE policies SET body=?,revision=revision+1,last_edited_by=? "
        "WHERE id=? AND revision=? AND status='draft'",
        (body, actor_id, policy_id, expected_revision),
    )
    return cursor.rowcount
