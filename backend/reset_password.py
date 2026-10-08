"""Reset a local development account password with direct operator access."""
import getpass
import os
import re
import sys

from aman_api.main import ENVIRONMENT, hash_password, init_db, transaction


def main() -> int:
    if ENVIRONMENT != "development" or os.environ.get("AMAN_DATABASE_URL"):
        print(
            "Password reset is limited to the local development SQLite database; "
            "use the approved identity and recovery process for other environments.",
            file=sys.stderr,
        )
        return 2

    init_db()
    email = input("Account email: ").strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        print("Enter a valid email address.", file=sys.stderr)
        return 2

    password = getpass.getpass("New password (12+ characters): ")
    confirmation = getpass.getpass("Confirm new password: ")
    if len(password) < 12 or len(password) > 1024:
        print("Password must be between 12 and 1024 characters.", file=sys.stderr)
        return 2
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 2

    with transaction() as conn:
        user = conn.execute(
            "SELECT id,disabled FROM users WHERE email=?", (email,)
        ).fetchone()
        if not user or user["disabled"]:
            print("No active account found for that email.", file=sys.stderr)
            return 1
        conn.execute(
            "UPDATE users SET password_hash=? WHERE id=?",
            (hash_password(password), user["id"]),
        )
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user["id"],))

    print("Password updated. All existing sessions for this account were revoked.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
