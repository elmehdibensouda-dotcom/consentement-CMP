"""SQLite connection lifecycle and versioned schema migration support."""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import stat
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from .migrations import MIGRATIONS


def connect_sqlite(database_path: Path, logger: logging.Logger) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    parent_mode = database_path.parent.stat().st_mode
    if parent_mode & (stat.S_IWGRP | stat.S_IWOTH) and not parent_mode & stat.S_ISVTX:
        raise PermissionError("SQLite databases must be stored in a private directory or a sticky shared directory")
    try:
        database_fd = os.open(database_path, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600)
    except FileExistsError:
        existing = database_path.lstat()
        if not stat.S_ISREG(existing.st_mode):
            raise PermissionError("The configured SQLite database must be a regular file")
        if hasattr(os, "getuid") and existing.st_uid != os.getuid():
            raise PermissionError("The configured SQLite database must be owned by the current user")
        if existing.st_mode & (stat.S_IRGRP | stat.S_IROTH):
            logger.warning("An existing SQLite database is group/world-readable; review its mode and WAL/SHM files")
    else:
        os.close(database_fd)
    conn = sqlite3.connect(database_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def sqlite_connection(database_path: Path, logger: logging.Logger) -> Generator[sqlite3.Connection, None, None]:
    conn = connect_sqlite(database_path, logger)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def sqlite_transaction(database_path: Path, logger: logging.Logger) -> Generator[sqlite3.Connection, None, None]:
    conn = connect_sqlite(database_path, logger)
    try:
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _migration_checksum(migration) -> str:
    source = Path(migration.__file__).read_bytes()
    return hashlib.sha256(source).hexdigest()


def apply_sqlite_migrations(conn: sqlite3.Connection) -> int:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, applied_at INTEGER NOT NULL)"
    )
    conn.commit()
    current_rows = conn.execute("SELECT version,name,checksum FROM schema_migrations ORDER BY version").fetchall()
    applied = {row["version"]: row for row in current_rows}
    known_versions = {migration.version for migration in MIGRATIONS}
    if any(version not in known_versions for version in applied):
        raise RuntimeError("Database schema is newer than this Aman API version")

    for migration in MIGRATIONS:
        checksum = _migration_checksum(migration.module)
        previous = applied.get(migration.version)
        if previous:
            if previous["name"] != migration.name or previous["checksum"] != checksum:
                raise RuntimeError(f"Applied database migration {migration.version} was changed")
            continue

        conn.execute("BEGIN IMMEDIATE")
        try:
            migration.upgrade(conn)
            conn.execute(
                "INSERT INTO schema_migrations(version,name,checksum,applied_at) VALUES(?,?,?,?)",
                (migration.version, migration.name, checksum, migration.applied_at()),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        applied[migration.version] = {"name": migration.name, "checksum": checksum}
    return MIGRATIONS[-1].version if MIGRATIONS else 0


def require_current_sqlite_schema(conn: sqlite3.Connection) -> None:
    try:
        applied = conn.execute("SELECT version,name,checksum FROM schema_migrations ORDER BY version").fetchall()
    except sqlite3.OperationalError as error:
        raise RuntimeError("Aman database schema is not initialized; run `python backend/migrate_db.py` first") from error

    applied_by_version = {row["version"]: row for row in applied}
    expected_versions = [migration.version for migration in MIGRATIONS]
    if sorted(applied_by_version) != expected_versions:
        raise RuntimeError("Aman database schema is behind; run `python backend/migrate_db.py` first")
    for migration in MIGRATIONS:
        row = applied_by_version[migration.version]
        if row["name"] != migration.name or row["checksum"] != _migration_checksum(migration.module):
            raise RuntimeError(f"Applied database migration {migration.version} does not match this API version")
