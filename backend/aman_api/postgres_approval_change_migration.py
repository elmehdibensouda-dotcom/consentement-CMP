"""Add pending two-person approval-setting changes to a PostgreSQL deployment."""
import re

from .migrations.v0005_approval_setting_changes import SCHEMA_SQL

VERSION = 3
NAME = "approval_setting_changes"


def upgrade(connection) -> None:
    for statement in SCHEMA_SQL:
        connection.execute(re.sub(r"\b([a-z_]+_at)\s+INTEGER\b", r"\1 BIGINT", statement))
