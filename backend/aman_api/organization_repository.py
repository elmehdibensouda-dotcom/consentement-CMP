"""Persistence operations for organization and membership administration."""
from __future__ import annotations

from typing import Any

from .database import Connection


def list_user_organizations(conn: Connection, user_id: str) -> list[Any]:
    return conn.execute(
        "SELECT o.id,o.name,o.require_two_person_publish AS requireTwoPersonPublish,m.role,o.created_at "
        "FROM organizations o JOIN memberships m ON m.org_id=o.id "
        "WHERE m.user_id=? ORDER BY o.name",
        (user_id,),
    ).fetchall()


def create_organization(
    conn: Connection,
    org_id: str,
    name: str,
    require_two_person_publish: bool,
    owner_id: str,
    created_at: int,
) -> None:
    conn.execute(
        "INSERT INTO organizations(id,name,require_two_person_publish,created_at) VALUES(?,?,?,?)",
        (org_id, name, int(require_two_person_publish), created_at),
    )
    conn.execute(
        "INSERT INTO memberships(org_id,user_id,role,created_at) VALUES(?,?,?,?)",
        (org_id, owner_id, "owner", created_at),
    )


def list_members(conn: Connection, org_id: str) -> list[Any]:
    return conn.execute(
        "SELECT u.id,u.email,m.role,m.created_at AS joined_at "
        "FROM memberships m JOIN users u ON u.id=m.user_id "
        "WHERE m.org_id=? ORDER BY CASE m.role WHEN 'owner' THEN 0 WHEN 'admin' THEN 1 "
        "WHEN 'editor' THEN 2 ELSE 3 END,u.email",
        (org_id,),
    ).fetchall()


def get_member_role(conn: Connection, org_id: str, user_id: str) -> Any:
    return conn.execute(
        "SELECT role FROM memberships WHERE org_id=? AND user_id=?",
        (org_id, user_id),
    ).fetchone()


def update_member_role(conn: Connection, org_id: str, user_id: str, role: str) -> None:
    conn.execute(
        "UPDATE memberships SET role=? WHERE org_id=? AND user_id=?",
        (role, org_id, user_id),
    )


def remove_member(conn: Connection, org_id: str, user_id: str) -> None:
    conn.execute("DELETE FROM memberships WHERE org_id=? AND user_id=?", (org_id, user_id))
