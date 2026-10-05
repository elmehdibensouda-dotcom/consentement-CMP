"""Create the first Aman local administrator; there is no public sign-up route."""
import getpass
import re
import secrets
import sys

from aman_api.main import hash_password, init_db, transaction, utc_now


def main() -> int:
    init_db()
    email = input("Admin email: ").strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        print("Enter a valid email address.", file=sys.stderr)
        return 2
    password = getpass.getpass("Password (12+ characters): ")
    if len(password) < 12:
        print("Password must be at least 12 characters.", file=sys.stderr)
        return 2
    user_id = secrets.token_hex(16)
    try:
        with transaction() as conn:
            conn.execute("INSERT INTO users(id,email,password_hash,created_at) VALUES(?,?,?,?)",
                         (user_id, email, hash_password(password), utc_now()))
    except Exception as exc:
        print(f"Could not create admin: {exc}", file=sys.stderr)
        return 1
    print("Initial admin created. Sign in through the API; there is no public account-creation endpoint.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
