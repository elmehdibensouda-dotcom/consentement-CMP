#!/bin/sh
set -eu
umask 077

load_secret_file() {
    variable_name="$1"
    file_path="$2"
    if [ -n "$file_path" ]; then
        if [ ! -r "$file_path" ]; then
            printf '%s\n' "Configured secret file for $variable_name is not readable." >&2
            exit 1
        fi
        secret_value=$(cat "$file_path")
        if [ -z "$secret_value" ]; then
            printf '%s\n' "Configured secret file for $variable_name is empty." >&2
            exit 1
        fi
        export "$variable_name=$secret_value"
    fi
}

load_secret_file AMAN_DATABASE_URL "${AMAN_DATABASE_URL_FILE:-}"
load_secret_file AMAN_MIGRATION_DATABASE_URL "${AMAN_MIGRATION_DATABASE_URL_FILE:-}"
load_secret_file AMAN_RATE_LIMIT_HASH_KEY "${AMAN_RATE_LIMIT_HASH_KEY_FILE:-}"
load_secret_file AMAN_EMAIL_SMTP_PASSWORD "${AMAN_EMAIL_SMTP_PASSWORD_FILE:-}"

if [ "${AMAN_ENVIRONMENT:-staging}" != "staging" ]; then
    printf '%s\n' "This container is for staging only; AMAN_ENVIRONMENT must be staging." >&2
    exit 1
fi

if [ -z "${AMAN_DATABASE_URL:-}" ]; then
    printf '%s\n' "AMAN_DATABASE_URL (or AMAN_DATABASE_URL_FILE) is required; this container does not fall back to SQLite." >&2
    exit 1
fi

if [ -z "${AMAN_RATE_LIMIT_HASH_KEY:-}" ]; then
    printf '%s\n' "AMAN_RATE_LIMIT_HASH_KEY (or AMAN_RATE_LIMIT_HASH_KEY_FILE) is required." >&2
    exit 1
fi

case "${AMAN_PORT:-8000}" in
    ''|*[!0-9]*)
        printf '%s\n' "AMAN_PORT must be a numeric TCP port." >&2
        exit 1
        ;;
esac

if [ "${AMAN_PORT:-8000}" -lt 1 ] || [ "${AMAN_PORT:-8000}" -gt 65535 ]; then
    printf '%s\n' "AMAN_PORT must be between 1 and 65535." >&2
    exit 1
fi

command_name="${1:-serve}"
case "$command_name" in
    serve)
        exec python -m uvicorn backend.aman_api.main:app \
            --host 0.0.0.0 \
            --port "$AMAN_PORT" \
            --no-access-log
        ;;
    migrate)
        exec python /app/backend/migrate_db.py
        ;;
    create-admin)
        exec python /app/backend/create_admin.py
        ;;
    *)
        printf '%s\n' "Unknown command. Use serve, migrate, or create-admin." >&2
        exit 2
        ;;
esac
