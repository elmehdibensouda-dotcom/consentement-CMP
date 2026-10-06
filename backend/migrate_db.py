"""Apply pending local SQLite migrations for Aman."""
from aman_api.main import connection, init_db


def main() -> int:
    init_db()
    with connection() as conn:
        version = conn.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()["version"]
    print(f"Aman database schema is current at migration {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
