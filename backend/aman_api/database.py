"""Database connection contracts and SQLite/PostgreSQL adapter selection."""
from __future__ import annotations

import hashlib
import logging
import os
import sqlite3
import stat
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any, Generator, Protocol, Sequence

from .migrations import MIGRATIONS


class DatabaseError(Exception):
    """Database failure exposed to application code, independent of a driver."""


class IntegrityError(DatabaseError):
    """Constraint violation exposed to application code."""


class Connection(Protocol):
    """Small DB-API surface used by Aman business logic."""

    def execute(self, statement: str, parameters: Sequence[Any] = ()) -> Any: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...
    def close(self) -> None: ...
    def begin_write_transaction(self) -> None: ...
    def lock_property(self, property_id: str) -> None: ...
    def lock_rate_limit_scope(self, scope: str) -> None: ...
    def lock_rate_limit_bucket(self, scope: str, bucket_hash: str) -> None: ...
    def initialize_schema(self) -> int: ...
    def require_current_schema(self) -> None: ...


class SQLiteConnection:
    """Adapt a SQLite handle to Aman’s driver-independent connection contract."""

    def __init__(self, native: sqlite3.Connection):
        self.native = native

    def execute(self, statement: str, parameters: Sequence[Any] = ()) -> sqlite3.Cursor:
        try:
            return self.native.execute(statement, parameters)
        except sqlite3.IntegrityError as error:
            raise IntegrityError(str(error)) from error
        except sqlite3.Error as error:
            raise DatabaseError(str(error)) from error

    def commit(self) -> None:
        try:
            self.native.commit()
        except sqlite3.Error as error:
            raise DatabaseError(str(error)) from error

    def rollback(self) -> None:
        try:
            self.native.rollback()
        except sqlite3.Error as error:
            raise DatabaseError(str(error)) from error

    def close(self) -> None:
        self.native.close()

    def begin_write_transaction(self) -> None:
        self.execute("BEGIN IMMEDIATE")

    def lock_property(self, property_id: str) -> None:
        # BEGIN IMMEDIATE already serializes SQLite writers.
        return None

    def lock_rate_limit_scope(self, scope: str) -> None:
        # BEGIN IMMEDIATE already serializes SQLite writers.
        return None

    def lock_rate_limit_bucket(self, scope: str, bucket_hash: str) -> None:
        # BEGIN IMMEDIATE already serializes SQLite writers.
        return None

    def initialize_schema(self) -> int:
        try:
            self.native.execute("PRAGMA journal_mode = WAL")
            return apply_sqlite_migrations(self.native)
        except sqlite3.Error as error:
            raise DatabaseError(str(error)) from error

    def require_current_schema(self) -> None:
        try:
            require_current_sqlite_schema(self.native)
        except sqlite3.Error as error:
            raise DatabaseError(str(error)) from error


def connect_sqlite(database_path: Path, logger: logging.Logger) -> SQLiteConnection:
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
    native = sqlite3.connect(database_path, timeout=10)
    native.row_factory = sqlite3.Row
    native.execute("PRAGMA foreign_keys = ON")
    return SQLiteConnection(native)


def connect_database(database_path: Path, logger: logging.Logger) -> Connection:
    """Open the configured database through the selected persistence adapter."""
    database_url = os.environ.get("AMAN_DATABASE_URL")
    if database_url:
        from .postgres import connect_postgres

        return connect_postgres(database_url)
    return connect_sqlite(database_path, logger)


def connect_migration_database(database_path: Path, logger: logging.Logger) -> Connection:
    """Open the operator connection used only by the migration command."""
    runtime_url = os.environ.get("AMAN_DATABASE_URL")
    migration_url = os.environ.get("AMAN_MIGRATION_DATABASE_URL")
    if migration_url and not runtime_url:
        raise RuntimeError("AMAN_DATABASE_URL must identify the API database when AMAN_MIGRATION_DATABASE_URL is set")
    if runtime_url:
        from .postgres import connect_postgres_migration

        return connect_postgres_migration(runtime_url, migration_url)
    return connect_sqlite(database_path, logger)


@contextmanager
def database_connection(database_path: Path, logger: logging.Logger) -> Generator[Connection, None, None]:
    conn = connect_database(database_path, logger)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def migration_database_connection(database_path: Path, logger: logging.Logger) -> Generator[Connection, None, None]:
    conn = connect_migration_database(database_path, logger)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def database_transaction(database_path: Path, logger: logging.Logger) -> Generator[Connection, None, None]:
    conn = connect_database(database_path, logger)
    try:
        conn.begin_write_transaction()
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def close_database_pool() -> None:
    """Close process-wide pools during application shutdown, if configured."""
    if os.environ.get("AMAN_DATABASE_URL"):
        from .postgres import close_postgres_pool

        close_postgres_pool()


def _rate_limit_bucket(conn: Connection, scope: str, bucket_hash: str, now: int):
    conn.execute(
        "INSERT INTO rate_limit_buckets(scope,bucket_hash,window_started_at,request_count,blocked_until) "
        "VALUES(?,?,?,0,0) ON CONFLICT(scope,bucket_hash) DO NOTHING",
        (scope, bucket_hash, now),
    )
    conn.lock_rate_limit_bucket(scope, bucket_hash)
    return conn.execute(
        "SELECT window_started_at,request_count,blocked_until FROM rate_limit_buckets "
        "WHERE scope=? AND bucket_hash=?",
        (scope, bucket_hash),
    ).fetchone()


def login_rate_limit_status(database_path: Path, logger: logging.Logger, bucket_hash: str, now: int) -> int:
    with database_connection(database_path, logger) as conn:
        row = conn.execute(
            "SELECT blocked_until FROM rate_limit_buckets WHERE scope='login' AND bucket_hash=?",
            (bucket_hash,),
        ).fetchone()
    return max(0, row["blocked_until"] - now) if row else 0


def record_login_failure(
    database_path: Path,
    logger: logging.Logger,
    bucket_hash: str,
    now: int,
    window_seconds: int,
    limit: int,
    block_seconds: int,
    max_buckets: int,
) -> int:
    with database_transaction(database_path, logger) as conn:
        conn.lock_rate_limit_scope("login")
        exists = conn.execute(
            "SELECT 1 FROM rate_limit_buckets WHERE scope='login' AND bucket_hash=?", (bucket_hash,)
        ).fetchone()
        if exists is None:
            active = conn.execute(
                "SELECT COUNT(*) AS n FROM rate_limit_buckets "
                "WHERE scope='login' AND (window_started_at>? OR blocked_until>?)",
                (now - max(window_seconds, 1200), now),
            ).fetchone()["n"]
            if active >= max_buckets:
                return block_seconds
        row = _rate_limit_bucket(conn, "login", bucket_hash, now)
        if row["blocked_until"] > now:
            return row["blocked_until"] - now
        start = row["window_started_at"]
        count = row["request_count"]
        if start <= now - window_seconds:
            start = now
            count = 0
        count += 1
        blocked_until = now + block_seconds if count >= limit else 0
        conn.execute(
            "UPDATE rate_limit_buckets SET window_started_at=?,request_count=?,blocked_until=? "
            "WHERE scope='login' AND bucket_hash=?",
            (start, count, blocked_until, bucket_hash),
        )
        return max(0, blocked_until - now)


def clear_login_rate_limit(database_path: Path, logger: logging.Logger, bucket_hash: str) -> None:
    with database_transaction(database_path, logger) as conn:
        conn.lock_rate_limit_scope("login")
        conn.execute("DELETE FROM rate_limit_buckets WHERE scope='login' AND bucket_hash=?", (bucket_hash,))


def consume_rate_limits(
    database_path: Path,
    logger: logging.Logger,
    requests: Sequence[tuple[str, str, int]],
    now: int,
    window_seconds: int,
    max_buckets_per_scope: int,
    transaction_connection: Connection | None = None,
) -> tuple[int, bool]:
    """Atomically check and increment limits, optionally within an existing transaction."""
    transaction = (
        database_transaction(database_path, logger)
        if transaction_connection is None
        else nullcontext(transaction_connection)
    )
    with transaction as conn:
        scopes = sorted({scope for scope, _, _ in requests})
        for scope in scopes:
            conn.lock_rate_limit_scope(scope)

        cutoff = now - window_seconds
        missing_by_scope: dict[str, int] = {scope: 0 for scope in scopes}
        for scope, bucket_hash, _ in requests:
            row = conn.execute(
                "SELECT window_started_at,request_count FROM rate_limit_buckets "
                "WHERE scope=? AND bucket_hash=?",
                (scope, bucket_hash),
            ).fetchone()
            if row is None:
                missing_by_scope[scope] += 1
        for scope in scopes:
            active = conn.execute(
                "SELECT COUNT(*) AS n FROM rate_limit_buckets "
                "WHERE scope=? AND (window_started_at>? OR blocked_until>?)",
                (scope, now - 1200, now),
            ).fetchone()["n"]
            if active + missing_by_scope[scope] > max_buckets_per_scope:
                return window_seconds, True

        rows = {}
        for scope, bucket_hash, _ in sorted(requests):
            rows[(scope, bucket_hash)] = _rate_limit_bucket(conn, scope, bucket_hash, now)

        retry_after = 0
        for scope, bucket_hash, limit in requests:
            row = rows[(scope, bucket_hash)]
            if row["window_started_at"] > cutoff and row["request_count"] >= limit:
                retry_after = max(retry_after, row["window_started_at"] + window_seconds - now)
        if retry_after:
            return max(1, retry_after), False

        for scope, bucket_hash, _ in requests:
            row = rows[(scope, bucket_hash)]
            if row["window_started_at"] <= cutoff:
                start, count = now, 1
            else:
                start, count = row["window_started_at"], row["request_count"] + 1
            conn.execute(
                "UPDATE rate_limit_buckets SET window_started_at=?,request_count=?,blocked_until=0 "
                "WHERE scope=? AND bucket_hash=?",
                (start, count, scope, bucket_hash),
            )
    return 0, False


def prune_rate_limit_buckets(database_path: Path, logger: logging.Logger, now: int) -> None:
    with database_transaction(database_path, logger) as conn:
        conn.execute(
            "DELETE FROM rate_limit_buckets WHERE window_started_at<=? AND blocked_until<=?",
            (now - 1200, now),
        )


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
