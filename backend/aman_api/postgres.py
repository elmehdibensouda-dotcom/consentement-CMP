"""PostgreSQL preproduction adapter with bounded pooling and TLS checks."""
from __future__ import annotations

import hashlib
import atexit
import os
from pathlib import Path
from threading import Lock
from types import ModuleType
from typing import Any, Sequence

from psycopg import Connection as PsycopgConnection
from psycopg import Error as PsycopgError
from psycopg import IntegrityError as PsycopgIntegrityError
from psycopg import connect as psycopg_connect
from psycopg.conninfo import conninfo_to_dict
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .database import Connection, DatabaseError, IntegrityError
from . import postgres_migrations, postgres_rate_limit_migration


POSTGRES_MIGRATIONS = (
    (postgres_migrations.VERSION, postgres_migrations.NAME, postgres_migrations, postgres_migrations.upgrade),
    (
        postgres_rate_limit_migration.VERSION,
        postgres_rate_limit_migration.NAME,
        postgres_rate_limit_migration,
        postgres_rate_limit_migration.upgrade,
    ),
)


_POOL_LOCK = Lock()
_POOL: ConnectionPool | None = None
_POOL_CONNINFO: str | None = None


def _connection_options(conninfo: str) -> dict[str, Any]:
    try:
        options = conninfo_to_dict(conninfo)
    except Exception:
        raise RuntimeError("A PostgreSQL connection URL is invalid") from None
    hosts = (options.get("host") or "localhost").split(",")
    local_hosts = {"localhost", "127.0.0.1", "::1", ""}
    is_remote = any(host.strip().strip("[]").lower() not in local_hosts for host in hosts)
    sslmode = options.get("sslmode", "prefer")
    if is_remote and sslmode != "verify-full":
        raise RuntimeError("Remote PostgreSQL requires sslmode=verify-full in its connection URL")
    options["_aman_is_remote"] = is_remote
    return options


def _pool_size() -> int:
    raw_value = os.environ.get("AMAN_DB_POOL_MAX_SIZE", "10")
    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError("AMAN_DB_POOL_MAX_SIZE must be an integer between 1 and 50") from error
    if not 1 <= value <= 50:
        raise RuntimeError("AMAN_DB_POOL_MAX_SIZE must be an integer between 1 and 50")
    return value


def _get_pool(conninfo: str) -> ConnectionPool:
    global _POOL, _POOL_CONNINFO
    with _POOL_LOCK:
        if _POOL is not None and _POOL_CONNINFO == conninfo and not _POOL.closed:
            return _POOL
        if _POOL is not None and not _POOL.closed:
            _POOL.close()
        size = _pool_size()
        pool = ConnectionPool(
            conninfo=conninfo,
            min_size=1,
            max_size=size,
            timeout=10,
            kwargs={"autocommit": True, "row_factory": dict_row},
            open=False,
            name="aman-api",
        )
        try:
            pool.open(wait=True, timeout=15)
        except Exception:
            pool.close()
            raise DatabaseError("Could not establish the configured PostgreSQL connection") from None
        _POOL = pool
        _POOL_CONNINFO = conninfo
        return pool


class PostgreSQLConnection:
    """Adapt psycopg to the same connection contract as the SQLite adapter."""

    def __init__(self, pool: ConnectionPool | None, native: PsycopgConnection):
        self.pool = pool
        self.native = native

    def execute(self, statement: str, parameters: Sequence[Any] = ()):
        try:
            return self.native.execute(_qmark_to_psycopg(statement), parameters)
        except PsycopgIntegrityError as error:
            raise IntegrityError(str(error)) from error
        except PsycopgError as error:
            raise DatabaseError(str(error)) from error

    def commit(self) -> None:
        try:
            self.native.commit()
        except PsycopgError as error:
            raise DatabaseError(str(error)) from error

    def rollback(self) -> None:
        try:
            self.native.rollback()
        except PsycopgError as error:
            raise DatabaseError(str(error)) from error

    def close(self) -> None:
        if self.pool is None:
            self.native.close()
        else:
            self.pool.putconn(self.native)

    def begin_write_transaction(self) -> None:
        self.execute("BEGIN")

    def lock_property(self, property_id: str) -> None:
        self.execute("SELECT id FROM properties WHERE id=? FOR UPDATE", (property_id,))

    def lock_invitation(self, invitation_id: str) -> None:
        self.execute("SELECT id FROM invitations WHERE id=? FOR UPDATE", (invitation_id,))

    def lock_rate_limit_scope(self, scope: str) -> None:
        self.execute("SELECT pg_advisory_xact_lock(hashtextextended(?,0))", ("aman-rate-limit:" + scope,))

    def lock_rate_limit_bucket(self, scope: str, bucket_hash: str) -> None:
        self.execute(
            "SELECT scope FROM rate_limit_buckets WHERE scope=? AND bucket_hash=? FOR UPDATE",
            (scope, bucket_hash),
        )

    def initialize_schema(self) -> int:
        self.begin_write_transaction()
        try:
            self.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                "version INTEGER PRIMARY KEY, name TEXT NOT NULL, checksum TEXT NOT NULL, applied_at BIGINT NOT NULL)"
            )
            self.execute("SELECT pg_advisory_xact_lock(741026061)")
            rows = self.execute("SELECT version,name,checksum FROM schema_migrations ORDER BY version").fetchall()
            applied = {row["version"]: row for row in rows}
            known_versions = {migration[0] for migration in POSTGRES_MIGRATIONS}
            if any(version not in known_versions for version in applied):
                raise RuntimeError("Database schema is newer than this Aman API version")
            for version, name, module, upgrade in POSTGRES_MIGRATIONS:
                checksum = _migration_checksum(version, module)
                previous = applied.get(version)
                if previous:
                    if previous["name"] != name or previous["checksum"] != checksum:
                        raise RuntimeError(f"Applied PostgreSQL migration {version} was changed")
                    continue
                upgrade(self)
                self.execute(
                    "INSERT INTO schema_migrations(version,name,checksum,applied_at) VALUES(?,?,?,?)",
                    (version, name, checksum, _now()),
                )
            self.commit()
            return POSTGRES_MIGRATIONS[-1][0]
        except Exception:
            self.rollback()
            raise

    def require_current_schema(self) -> None:
        try:
            rows = self.execute("SELECT version,name,checksum FROM schema_migrations ORDER BY version").fetchall()
        except DatabaseError as error:
            raise RuntimeError("Aman database schema is not initialized; run `python backend/migrate_db.py` first") from error
        if [row["version"] for row in rows] != [migration[0] for migration in POSTGRES_MIGRATIONS]:
            raise RuntimeError("Aman database schema is behind; run `python backend/migrate_db.py` first")
        for row, (version, name, module, _) in zip(rows, POSTGRES_MIGRATIONS):
            if row["name"] != name or row["checksum"] != _migration_checksum(version, module):
                raise RuntimeError(f"Applied PostgreSQL migration {version} does not match this API version")


def connect_postgres(conninfo: str) -> Connection:
    _connection_options(conninfo)
    pool = _get_pool(conninfo)
    try:
        return PostgreSQLConnection(pool, pool.getconn(timeout=10))
    except Exception:
        raise DatabaseError("Could not obtain a PostgreSQL connection from the configured pool") from None


def connect_postgres_migration(runtime_conninfo: str, migration_conninfo: str | None) -> Connection:
    """Use a one-shot operator connection and enforce distinct remote DB roles."""
    runtime_options = _connection_options(runtime_conninfo)
    if not migration_conninfo:
        if runtime_options["_aman_is_remote"]:
            raise RuntimeError("Remote PostgreSQL requires a separate AMAN_MIGRATION_DATABASE_URL")
        migration_conninfo = runtime_conninfo

    migration_options = _connection_options(migration_conninfo)
    if runtime_options["_aman_is_remote"] or migration_options["_aman_is_remote"]:
        runtime_user = str(runtime_options.get("user") or "").strip()
        migration_user = str(migration_options.get("user") or "").strip()
        if not runtime_user or not migration_user or runtime_user == migration_user:
            raise RuntimeError("Remote PostgreSQL requires distinct explicit API and migration database roles")
        runtime_hosts = tuple(
            host.strip().strip("[]").lower()
            for host in str(runtime_options.get("host") or "localhost").split(",")
        )
        migration_hosts = tuple(
            host.strip().strip("[]").lower()
            for host in str(migration_options.get("host") or "localhost").split(",")
        )
        runtime_port = str(runtime_options.get("port") or "5432")
        migration_port = str(migration_options.get("port") or "5432")
        runtime_database = str(runtime_options.get("dbname") or "").strip()
        migration_database = str(migration_options.get("dbname") or "").strip()
        if (
            not runtime_database
            or runtime_database != migration_database
            or runtime_hosts != migration_hosts
            or runtime_port != migration_port
        ):
            raise RuntimeError("API and migration PostgreSQL URLs must target the same explicit server and database")

    try:
        native = psycopg_connect(migration_conninfo, autocommit=True, row_factory=dict_row)
    except PsycopgError:
        raise DatabaseError("Could not establish the configured PostgreSQL migration connection") from None
    return PostgreSQLConnection(None, native)


def close_postgres_pool() -> None:
    global _POOL, _POOL_CONNINFO
    with _POOL_LOCK:
        if _POOL is not None and not _POOL.closed:
            _POOL.close()
        _POOL = None
        _POOL_CONNINFO = None


def _migration_checksum(version: int, migration: ModuleType) -> str:
    digest = hashlib.sha256()
    digest.update(Path(migration.__file__).read_bytes())
    if version == postgres_migrations.VERSION:
        from .migrations import v0001_initial_schema

        digest.update(Path(v0001_initial_schema.__file__).read_bytes())
    return digest.hexdigest()


def _now() -> int:
    import time

    return int(time.time())


def _qmark_to_psycopg(statement: str) -> str:
    """Translate DB-API qmark binds without rewriting quoted text or comments."""
    output: list[str] = []
    index = 0
    quote: str | None = None
    line_comment = False
    block_comment = False
    while index < len(statement):
        char = statement[index]
        following = statement[index + 1] if index + 1 < len(statement) else ""
        if line_comment:
            output.append(char)
            if char == "\n":
                line_comment = False
        elif block_comment:
            output.append(char)
            if char == "*" and following == "/":
                output.append(following)
                index += 1
                block_comment = False
        elif quote:
            output.append(char)
            if char == quote:
                if following == quote:
                    output.append(following)
                    index += 1
                else:
                    quote = None
        elif char == "'" or char == '"':
            quote = char
            output.append(char)
        elif char == "-" and following == "-":
            output.extend((char, following))
            index += 1
            line_comment = True
        elif char == "/" and following == "*":
            output.extend((char, following))
            index += 1
            block_comment = True
        elif char == "?":
            output.append("%s")
        else:
            output.append(char)
        index += 1
    return "".join(output)


atexit.register(close_postgres_pool)
