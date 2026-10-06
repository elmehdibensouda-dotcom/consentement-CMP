"""Immutable, ordered SQLite schema migrations."""
from dataclasses import dataclass
from types import ModuleType
from typing import Callable

import sqlite3

from . import v0001_initial_schema, v0002_legacy_columns, v0003_rate_limit_buckets


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    module: ModuleType
    upgrade: Callable[[sqlite3.Connection], None]
    applied_at: Callable[[], int]


def _now() -> int:
    import time
    return int(time.time())


MIGRATIONS = (
    Migration(1, "initial_schema", v0001_initial_schema, v0001_initial_schema.upgrade, _now),
    Migration(2, "legacy_columns", v0002_legacy_columns, v0002_legacy_columns.upgrade, _now),
    Migration(3, "rate_limit_buckets", v0003_rate_limit_buckets, v0003_rate_limit_buckets.upgrade, _now),
)
