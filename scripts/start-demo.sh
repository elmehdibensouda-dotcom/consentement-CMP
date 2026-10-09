#!/usr/bin/env bash
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$REPO_ROOT/.venv"
PYTHON="$VENV_DIR/bin/python"
DEMO_MODE="${1:-full}"
case "$DEMO_MODE" in
  full)
    DEMO_DB="$REPO_ROOT/.local/alamane-demo.sqlite3"
    ;;
  --web-only)
    DEMO_DB="$REPO_ROOT/.local/alamane-web-pilot.sqlite3"
    ;;
  *)
    echo "Usage: $0 [--web-only]" >&2
    exit 2
    ;;
esac

cd "$REPO_ROOT"

if [[ -n "${AMAN_DATABASE_URL:-}" || -n "${AMAN_MIGRATION_DATABASE_URL:-}" ]]; then
  echo "Refusing to start the local demo while PostgreSQL connection URLs are set; unset them to protect shared databases." >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3.11+ is required. Install Python, then run this script again." >&2
  exit 1
fi
if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "Python 3.11+ is required." >&2
  exit 1
fi

if ! python3 - 8000 8001 <<'PY'
import errno
import socket
import sys

for value in sys.argv[1:]:
    port = int(value)
    with socket.socket() as listener:
        try:
            listener.bind(("127.0.0.1", port))
        except OSError as exc:
            if exc.errno in {errno.EACCES, errno.EPERM}:
                print(
                    f"Cannot check port {port} on 127.0.0.1 because this environment blocks local network access; "
                    "run the demo from a local terminal with permission to bind loopback ports.",
                    file=sys.stderr,
                )
            else:
                print(f"Port {port} on 127.0.0.1 is unavailable; stop the service using it, then retry.", file=sys.stderr)
            raise SystemExit(1)
PY
then
  exit 1
fi

if [[ ! -x "$PYTHON" ]]; then
  python3 -m venv "$VENV_DIR"
fi
if ! "$PYTHON" -c 'import fastapi, uvicorn, jsonschema, pydantic, email_validator' >/dev/null 2>&1; then
  "$PYTHON" -m pip install -r backend/requirements.txt
fi

mkdir -p "$REPO_ROOT/.local"
export AMAN_DATABASE_PATH="$DEMO_DB"
export AMAN_ENVIRONMENT=development
export AMAN_CORS_ORIGINS=http://localhost:8000

"$PYTHON" backend/migrate_db.py

user_count=$("$PYTHON" - <<'PY'
import os
import sqlite3
connection = sqlite3.connect(os.environ["AMAN_DATABASE_PATH"])
try:
    print(connection.execute("SELECT COUNT(*) FROM users WHERE disabled=0").fetchone()[0])
finally:
    connection.close()
PY
)

if [[ "$user_count" == "0" ]]; then
  echo "Create the local demo administrator. The password is entered without echo and stays on this machine."
  "$PYTHON" backend/create_admin.py
  user_count=$("$PYTHON" - <<'PY'
import os
import sqlite3
connection = sqlite3.connect(os.environ["AMAN_DATABASE_PATH"])
try:
    print(connection.execute("SELECT COUNT(*) FROM users WHERE disabled=0").fetchone()[0])
finally:
    connection.close()
PY
  )
fi

if [[ "$user_count" == "1" ]]; then
  owner_email=$("$PYTHON" - <<'PY'
import os
import sqlite3
connection = sqlite3.connect(os.environ["AMAN_DATABASE_PATH"])
try:
    print(connection.execute("SELECT email FROM users WHERE disabled=0").fetchone()[0])
finally:
    connection.close()
PY
  )
else
  read -r -p "Email of the local account that will own the fictional demo: " owner_email
fi
if [[ -z "$owner_email" ]]; then
  echo "An active account email is required to prepare the demo." >&2
  exit 1
fi

if [[ "$DEMO_MODE" == "--web-only" ]]; then
  seed_output=$("$PYTHON" backend/seed_demo.py --web-only --owner-email "$owner_email")
else
  seed_output=$("$PYTHON" backend/seed_demo.py --owner-email "$owner_email")
fi
printf '%s\n' "$seed_output"
property_id=$(printf '%s\n' "$seed_output" | sed -n 's/^web property ID: //p')
if [[ -z "$property_id" ]]; then
  echo "Could not read the demo property ID from the seed command." >&2
  exit 1
fi

"$PYTHON" -m uvicorn backend.aman_api.main:app --host 127.0.0.1 --port 8001 --no-access-log &
api_pid=$!
"$PYTHON" -m http.server 8000 --bind 127.0.0.1 &
web_pid=$!

cleanup() {
  kill "$api_pid" "$web_pid" 2>/dev/null || true
  wait "$api_pid" "$web_pid" 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

ready=0
for attempt in {1..40}; do
  if ! kill -0 "$api_pid" 2>/dev/null || ! kill -0 "$web_pid" 2>/dev/null; then
    break
  fi
if "$PYTHON" - <<'PY' >/dev/null 2>&1
from urllib.request import ProxyHandler, build_opener

opener = build_opener(ProxyHandler({}))

for url in (
    "http://127.0.0.1:8001/health/ready",
    "http://127.0.0.1:8000/index.html",
):
    with opener.open(url, timeout=1) as response:
        if response.status != 200:
            raise SystemExit(1)
PY
  then
    ready=1
    break
  fi
  sleep 0.25
done
if [[ "$ready" != "1" ]]; then
  echo "The local API or website did not become ready. The script will stop both servers." >&2
  exit 1
fi

echo
if [[ "$DEMO_MODE" == "--web-only" ]]; then
  echo "ALAMANE local Web-only pilot demo is ready (fictional data only; not a client deployment)."
else
  echo "ALAMANE local demo is ready (fictional data only)."
fi
echo "Console:   http://localhost:8000/index.html"
echo "Demo site: http://localhost:8000/demo-site.html?property=$property_id"
echo "API docs:  http://localhost:8001/docs"
echo "Database:  $DEMO_DB"
echo "Press Ctrl+C to stop both local servers."

if [[ "${OSTYPE:-}" == darwin* ]] && command -v open >/dev/null 2>&1; then
  open "http://localhost:8000/index.html"
fi

while kill -0 "$api_pid" 2>/dev/null && kill -0 "$web_pid" 2>/dev/null; do
  sleep 1
done
echo "A local server stopped." >&2
exit 1
