#!/usr/bin/env bash
# Run the Web SDK browser regression pages in headless Chrome.
# Usage: bash scripts/run-web-sdk-tests.sh   (CHROME_BIN and AMAN_WEB_TEST_PORT are optional)
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
port="${AMAN_WEB_TEST_PORT:-8097}"
chrome="${CHROME_BIN:-}"
if [ -z "$chrome" ]; then
  for candidate in google-chrome google-chrome-stable chromium chromium-browser \
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
    if command -v "$candidate" >/dev/null 2>&1 || [ -x "$candidate" ]; then
      chrome="$candidate"
      break
    fi
  done
fi
if [ -z "$chrome" ]; then
  echo "Chrome or Chromium is required; set CHROME_BIN." >&2
  exit 2
fi

profile="$(mktemp -d)"
python3 -m http.server "$port" --bind 127.0.0.1 --directory "$root" >/dev/null 2>&1 &
server_pid=$!
trap 'kill "$server_pid" 2>/dev/null; wait "$server_pid" 2>/dev/null || true; rm -rf "$profile"' EXIT
for _ in $(seq 1 50); do
  if python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$port/tests/web/fixtures/tag.js', timeout=1)" 2>/dev/null; then
    break
  fi
  sleep 0.1
done

status=0
for page in managed-tags-nonce managed-tags-no-nonce; do
  # Bound each Chrome run: headless Chrome can keep running after dumping the DOM.
  dom="$(python3 - "$chrome" "$profile/$page" "http://127.0.0.1:$port/tests/web/$page.html" ${CHROME_FLAGS:-} <<'PY'
import os, signal, subprocess, sys
chrome, profile, url, *extra = sys.argv[1:]
command = [chrome, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={profile}",
           *extra, "--virtual-time-budget=15000", "--dump-dom", url]
process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
try:
    output, _ = process.communicate(timeout=60)
except subprocess.TimeoutExpired:
    os.killpg(process.pid, signal.SIGKILL)
    output, _ = process.communicate()
sys.stdout.write(output.decode("utf-8", "replace"))
PY
)"
  if printf '%s' "$dom" | grep -q 'data-result="pass"'; then
    echo "PASS $page"
  else
    echo "FAIL $page"
    printf '%s\n' "$dom" | sed -n '/<pre id="results">/,/<\/pre>/p'
    status=1
  fi
done
exit "$status"
