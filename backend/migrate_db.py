"""Apply pending local SQLite or PostgreSQL migrations for Aman."""
from aman_api.main import DATABASE_PATH, LOGGER, init_db, migration_database_connection


def main() -> int:
    init_db()
    with migration_database_connection(DATABASE_PATH, LOGGER) as conn:
        version = conn.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()["version"]
    print(f"Aman database schema is current at migration {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
