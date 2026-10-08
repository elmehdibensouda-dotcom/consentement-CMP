"""Persistence operations for bounded, organization-owned scanner reports."""
from __future__ import annotations

from typing import Any

from .database import Connection


def insert_scan_report(
    conn: Connection,
    report_id: str,
    property_id: str,
    imported_by: str,
    scanned_at: int,
    imported_at: int,
    page_origin: str,
    resource_count: int,
    cookie_count: int,
    report_json: str,
    retention_limit: int,
) -> None:
    conn.execute(
        "INSERT INTO scan_reports(id,property_id,imported_by,scanned_at,imported_at,page_origin,resource_count,cookie_count,report_json) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (report_id, property_id, imported_by, scanned_at, imported_at, page_origin,
         resource_count, cookie_count, report_json),
    )
    conn.execute(
        "DELETE FROM scan_reports WHERE property_id=? AND id NOT IN "
        "(SELECT id FROM scan_reports WHERE property_id=? ORDER BY imported_at DESC,id DESC LIMIT ?)",
        (property_id, property_id, retention_limit),
    )


def list_scan_reports(conn: Connection, property_id: str, limit: int) -> list[Any]:
    return conn.execute(
        "SELECT s.id,s.scanned_at,s.imported_at,s.page_origin,s.resource_count,s.cookie_count,u.email AS imported_by "
        "FROM scan_reports s JOIN users u ON u.id=s.imported_by WHERE s.property_id=? "
        "ORDER BY s.imported_at DESC,s.id DESC LIMIT ?",
        (property_id, limit),
    ).fetchall()


def get_scan_report(conn: Connection, org_id: str, property_id: str, report_id: str) -> Any:
    return conn.execute(
        "SELECT s.id,s.scanned_at,s.imported_at,s.page_origin,s.resource_count,s.cookie_count,s.report_json,u.email AS imported_by "
        "FROM scan_reports s JOIN properties p ON p.id=s.property_id JOIN users u ON u.id=s.imported_by "
        "WHERE s.id=? AND s.property_id=? AND p.org_id=?",
        (report_id, property_id, org_id),
    ).fetchone()


def delete_scan_report(conn: Connection, property_id: str, report_id: str) -> int:
    cursor = conn.execute(
        "DELETE FROM scan_reports WHERE id=? AND property_id=?", (report_id, property_id)
    )
    return cursor.rowcount
