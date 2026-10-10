"""Aman API: local development control plane, not a production bank deployment.

The API uses SQLite for a runnable local vertical slice. Production must move to
managed PostgreSQL, TLS, a secret manager, external rate limiting, migrations,
centralized monitoring, and a reviewed hosting/data-transfer arrangement.
"""
from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import os
import secrets
import time
import csv
import io
import asyncio
import logging
import re
from contextlib import asynccontextmanager, contextmanager, suppress
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, Literal, Optional, Tuple
from urllib.parse import urlsplit

from fastapi import Body, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from jsonschema import Draft202012Validator
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StrictBool, constr

from .database import (
    Connection,
    DatabaseError,
    IntegrityError,
    close_database_pool,
    connect_database,
    database_connection,
    database_transaction,
    clear_login_rate_limit,
    migration_database_connection,
    consume_rate_limits,
    login_rate_limit_status,
    prune_rate_limit_buckets,
    record_login_failure,
)
from .consent_metrics_repository import (
    load_consent_metric_sources,
    load_organization_consent_metric_sources,
)
from .consent_event_repository import (
    count_events_for_export,
    count_organization_events_for_export,
    iter_events_for_export,
    iter_organization_events_for_export,
)
from .approval_setting_repository import (
    create_change as persist_approval_setting_change,
    get_change as get_approval_setting_change,
    get_pending_change as get_pending_approval_setting_change,
    mark_change_approved as mark_approval_setting_change_approved,
    revoke_pending_changes as revoke_pending_approval_setting_changes,
)
from .client_address import rate_limit_address
from .dashboard_repository import load_dashboard_sources
from .audit_repository import append_audit_event, iter_audit_export_events, list_audit_events
from .property_repository import (
    create_property as persist_property,
    get_public_property,
    get_property_for_organization,
    get_property_for_origin_update,
    has_scan_reports,
    list_properties as list_property_rows,
    update_property_origin as persist_property_origin,
)
from .scan_report_repository import (
    delete_scan_report as delete_scan_report_row,
    get_scan_report as get_scan_report_row,
    insert_scan_report,
    list_scan_reports as list_scan_report_rows,
)
from .published_policy_repository import get_published_policy as load_published_policy
from .policy_repository import (
    get_policy_for_organization,
    get_policy_for_draft_update,
    get_policy_for_publication,
    get_policy_body,
    get_published_policy_id,
    get_property_channel,
    insert_policy_draft,
    list_property_policies as list_property_policy_rows,
    mark_policy_published,
    next_policy_version,
    retire_policy,
    update_policy_draft as persist_policy_draft_update,
)
from .organization_repository import (
    create_organization as persist_organization_creation,
    get_member_role,
    get_organization_approval_setting,
    list_members as list_member_rows,
    list_user_organizations,
    remove_member as persist_member_removal,
    update_organization_approval_setting,
    update_member_role as persist_member_role_update,
)
from .auth_repository import (
    create_session as persist_session_creation,
    delete_expired_sessions,
    delete_session,
    get_session_csrf_hash,
    get_session_user,
    get_user_credentials,
    list_auth_user_organizations,
)
from .invitation_repository import (
    add_invited_member,
    create_invited_user,
    create_invitation,
    get_invitation_for_acceptance,
    get_invitation_preview,
    get_invitation_for_revocation,
    get_invitation_for_resend,
    get_invited_user_account,
    get_user_for_invitation,
    has_active_invitation,
    is_organization_member,
    list_organization_invitations,
    mark_invitation_accepted,
    revoke_invitation as persist_invitation_revocation,
    rotate_invitation_token,
)
from .invitation_delivery import (
    InvitationEmailConfigurationError,
    load_invitation_email_config,
    send_invitation_email,
)
from .ownership_transfer_repository import (
    create_transfer as persist_ownership_transfer,
    get_membership_role as get_ownership_membership_role,
    get_pending_transfer,
    get_transfer_by_token_hash,
    has_active_transfer,
    list_pending_transfers_for_revocation,
    mark_transfer_accepted,
    revoke_other_pending_transfers,
    revoke_pending_transfers,
    update_member_role as persist_ownership_member_role,
)


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "consent-policy.schema.json"
DEFAULT_DATABASE_PATH = Path.home() / ".alamane" / "aman-dev.sqlite3"
DATABASE_PATH = Path(os.environ.get("AMAN_DATABASE_PATH", str(DEFAULT_DATABASE_PATH)))
ENVIRONMENT = os.environ.get("AMAN_ENVIRONMENT", "development").lower()
SESSION_COOKIE = "aman_session"
CSRF_COOKIE = "aman_csrf"
SESSION_TTL_SECONDS = 8 * 60 * 60
INVITE_TTL_SECONDS = 72 * 60 * 60
OWNERSHIP_TRANSFER_TTL_SECONDS = 24 * 60 * 60
APPROVAL_SETTING_CHANGE_TTL_SECONDS = 24 * 60 * 60
LOGIN_FAILURE_LIMIT = 20
LOGIN_WINDOW_SECONDS = 10 * 60
LOGIN_LOCK_SECONDS = 10 * 60
LOGIN_RATE_MAX_BUCKETS = 20000
# Per-account throttle: bounded and temporary, so a third party cannot lock an account
# for long; browsers that already signed in to the account (device cookie) are exempt.
LOGIN_ACCOUNT_FAILURE_LIMIT = 10
LOGIN_ACCOUNT_WINDOW_SECONDS = 15 * 60
LOGIN_ACCOUNT_LOCK_SECONDS = 15 * 60
LOGIN_DEVICE_FAILURE_LIMIT = 10
DEVICE_COOKIE = "aman_device"
DEVICE_COOKIE_TTL_SECONDS = 90 * 24 * 60 * 60
LOGIN_THROTTLED_DETAIL = "Too many sign-in attempts. Try again later."
CONSENT_EVENT_WINDOW_SECONDS = 60
CONSENT_EVENT_CLIENT_LIMIT = 120
CONSENT_EVENT_PROPERTY_LIMIT = 6000
def positive_int_setting(name: str, default: int, maximum: Optional[int] = None) -> int:
    raw_value = os.environ.get(name, str(default))
    try:
        parsed = int(raw_value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a positive integer") from error
    if parsed < 1 or (maximum is not None and parsed > maximum):
        raise RuntimeError(f"{name} must be a positive integer" + (f" no greater than {maximum}" if maximum else ""))
    return parsed


# Admission quotas isolate tenants; the total is an emergency bound on storage growth
# that refuses new events for every property once reached.
CONSENT_EVENT_ACTIVE_TOTAL_LIMIT = positive_int_setting("AMAN_CONSENT_EVENT_ACTIVE_TOTAL_LIMIT", 500_000)
CONSENT_EVENT_ACTIVE_ORGANIZATION_LIMIT = positive_int_setting("AMAN_CONSENT_EVENT_ACTIVE_ORGANIZATION_LIMIT", 50_000)
CONSENT_EVENT_ACTIVE_PROPERTY_LIMIT = positive_int_setting("AMAN_CONSENT_EVENT_ACTIVE_PROPERTY_LIMIT", 25_000)
CONSENT_EVENT_CAPACITY_WARNING_PERCENT = positive_int_setting(
    "AMAN_CONSENT_EVENT_CAPACITY_WARNING_PERCENT", 80, maximum=100
)
CONSENT_EVENT_MAX_BUCKETS = 20000
INVITATION_PREVIEW_LIMIT = 120
INVITATION_ACCEPT_LIMIT = 20
INVITATION_RATE_WINDOW_SECONDS = 60
INVITATION_RATE_MAX_BUCKETS = 20000
INVITATION_CREATE_LIMIT = 10
INVITATION_RESEND_LIMIT = 5
SCAN_REPORT_MAX_BYTES = 1_048_576
API_REQUEST_MAX_BYTES = 1_048_576
POLICY_MAX_BYTES = 524_288
CONSENT_EVENT_MAX_BYTES = 16_384
SCAN_REPORTS_PER_PROPERTY = 20
# Kept as empty compatibility hooks for older test harnesses; rate state is DB-backed.
_LOGIN_FAILURES: Dict[str, list[int]] = {}
_LOGIN_BLOCKED_UNTIL: Dict[str, int] = {}
_CONFIGURED_RATE_LIMIT_HASH_KEY = os.environ.get("AMAN_RATE_LIMIT_HASH_KEY", "").encode("utf-8")
_RATE_LIMIT_HASH_KEY = _CONFIGURED_RATE_LIMIT_HASH_KEY or secrets.token_bytes(32)
COOKIE_SECURE = ENVIRONMENT != "development"
if ENVIRONMENT == "production":
    raise RuntimeError(
        "This development API is not production-deployable: it uses SQLite and has no reviewed deployment controls."
    )
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("AMAN_CORS_ORIGINS", "http://localhost:8000").split(",")
    if origin.strip()
]

SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
POLICY_VALIDATOR = Draft202012Validator(SCHEMA)
LOGGER = logging.getLogger("aman.consent")


class RequestBodyLimitMiddleware:
    """Bound API request bodies before FastAPI parses JSON or validates models."""

    def __init__(self, app):
        self.app = app

    @staticmethod
    def limit_for(scope) -> Optional[int]:
        if scope.get("type") != "http" or scope.get("method") not in {"POST", "PUT", "PATCH"}:
            return None
        path = scope.get("path", "")
        if re.fullmatch(r"/v1/public/properties/[^/]+/consent-events", path):
            return CONSENT_EVENT_MAX_BYTES
        if re.fullmatch(r"/v1/organizations/[^/]+/(?:properties/[^/]+/policies|policies/[^/]+)", path):
            return POLICY_MAX_BYTES
        if path.startswith("/v1/"):
            return API_REQUEST_MAX_BYTES
        return None

    async def __call__(self, scope, receive, send):
        limit = self.limit_for(scope)
        if limit is None:
            await self.app(scope, receive, send)
            return

        headers = {key.lower(): value for key, value in scope.get("headers", [])}
        raw_length = headers.get(b"content-length")
        if raw_length and raw_length.isdigit() and int(raw_length) > limit:
            await self.reject(send)
            return

        body = bytearray()
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return
            chunk = message.get("body", b"")
            if len(body) + len(chunk) > limit:
                await self.reject(send)
                return
            body.extend(chunk)
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay_receive():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": bytes(body), "more_body": False}
            return await receive()

        await self.app(scope, replay_receive, send)

    @staticmethod
    async def reject(send):
        body = b'{"detail":"Request body exceeds the configured limit"}'
        await send({"type": "http.response.start", "status": 413, "headers": [
            (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode("ascii"))
        ]})
        await send({"type": "http.response.body", "body": body})


def utc_now() -> int:
    return int(time.time())


def db_connect() -> Connection:
    return connect_database(DATABASE_PATH, LOGGER)


@contextmanager
def connection() -> Generator[Connection, None, None]:
    with database_connection(DATABASE_PATH, LOGGER) as conn:
        yield conn


@contextmanager
def transaction() -> Generator[Connection, None, None]:
    with database_transaction(DATABASE_PATH, LOGGER) as conn:
        yield conn


def init_db() -> None:
    ensure_scrypt_available()
    ensure_rate_limit_hash_key()
    with migration_database_connection(DATABASE_PATH, LOGGER) as conn:
        conn.initialize_schema()
    with connection() as conn:
        conn.execute("DELETE FROM consent_events WHERE expires_at <= ?", (utc_now(),))
        conn.commit()
    prune_rate_limit_buckets(DATABASE_PATH, LOGGER, utc_now())


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1, dklen=64)
    return f"scrypt${salt.hex()}${derived.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        kind, salt_hex, hash_hex = stored.split("$", 2)
        if kind != "scrypt":
            return False
        candidate = hash_password(password, bytes.fromhex(salt_hex)).split("$", 2)[2]
        return hmac.compare_digest(candidate, hash_hex)
    except (ValueError, TypeError, AttributeError):
        return False


def ensure_scrypt_available() -> None:
    if not callable(getattr(hashlib, "scrypt", None)):
        raise RuntimeError(
            "This Python/OpenSSL build does not provide hashlib.scrypt, which is required for ALAMANE password authentication."
        )


def client_ip(request: Request) -> str:
    """Return the rate-limit source for a request.

    Only the socket peer is used. Behind a reverse proxy, Uvicorn rewrites it from
    X-Forwarded-For solely for peers listed in AMAN_TRUSTED_PROXY_IPS.
    """
    return rate_limit_address(request.client.host if request.client else None)


def login_client_key(request: Request) -> str:
    return rate_limit_hash("login", client_ip(request))


def login_account_key(email: str) -> str:
    return rate_limit_hash("login_account", email)


def device_cookie_value(account_key: str, nonce: Optional[str] = None) -> str:
    nonce = nonce or secrets.token_urlsafe(18)
    mac = hmac.new(_RATE_LIMIT_HASH_KEY, f"device:{account_key}:{nonce}".encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{nonce}.{mac}"


def recognized_device(request: Request, account_key: str) -> Optional[str]:
    """Return the device nonce when the request carries this account's device cookie."""
    value = request.cookies.get(DEVICE_COOKIE, "")
    nonce, separator, _ = value.partition(".")
    if not separator or not nonce or len(value) > 256:
        return None
    if not hmac.compare_digest(value, device_cookie_value(account_key, nonce)):
        return None
    return nonce


def rate_limit_hash(scope: str, value: str) -> str:
    return hmac.new(_RATE_LIMIT_HASH_KEY, f"{scope}:{value}".encode("utf-8"), hashlib.sha256).hexdigest()


def ensure_rate_limit_hash_key() -> None:
    if os.environ.get("AMAN_DATABASE_URL") and len(_CONFIGURED_RATE_LIMIT_HASH_KEY) < 32:
        raise RuntimeError("AMAN_RATE_LIMIT_HASH_KEY must contain at least 32 bytes when PostgreSQL is configured")


def login_throttled(retry_after: int) -> HTTPException:
    return HTTPException(status_code=429, detail=LOGIN_THROTTLED_DETAIL,
                         headers={"Retry-After": str(max(1, retry_after))})


def enforce_login_rate_limit(client_key: str, scope: str = "login") -> None:
    retry_after = login_rate_limit_status(DATABASE_PATH, LOGGER, client_key, utc_now(), scope)
    if retry_after:
        raise login_throttled(retry_after)


def note_failed_login(client_key: str) -> int:
    return record_login_failure(
        DATABASE_PATH, LOGGER, client_key, utc_now(), LOGIN_WINDOW_SECONDS, LOGIN_FAILURE_LIMIT, LOGIN_LOCK_SECONDS,
        LOGIN_RATE_MAX_BUCKETS,
    )


def note_failed_account_login(scope: str, bucket_hash: str, limit: int) -> int:
    # Secondary limits fail open at bucket capacity: the source limit still applies.
    return record_login_failure(
        DATABASE_PATH, LOGGER, bucket_hash, utc_now(), LOGIN_ACCOUNT_WINDOW_SECONDS, limit,
        LOGIN_ACCOUNT_LOCK_SECONDS, LOGIN_RATE_MAX_BUCKETS, scope=scope, block_when_full=False,
    )


def clear_login_failures(client_key: str, scope: str = "login") -> None:
    clear_login_rate_limit(DATABASE_PATH, LOGGER, client_key, scope)


def enforce_account_rate_limit(request: Request, email: str) -> Tuple[str, Optional[str]]:
    """Apply the per-account throttle, unless this browser already signed in to the account.

    Returns the account bucket and, for a recognized browser, its device bucket.
    """
    account_key = login_account_key(email)
    nonce = recognized_device(request, account_key)
    device_key = rate_limit_hash("login_device", f"{account_key}:{nonce}") if nonce else None
    if device_key and not login_rate_limit_status(DATABASE_PATH, LOGGER, device_key, utc_now(), "login_device"):
        return account_key, device_key
    enforce_login_rate_limit(account_key, "login_account")
    return account_key, None


def note_failed_password(client_key: str, account_key: str, device_key: Optional[str]) -> None:
    retry_after = max(
        note_failed_login(client_key),
        note_failed_account_login("login_device", device_key, LOGIN_DEVICE_FAILURE_LIMIT) if device_key
        else note_failed_account_login("login_account", account_key, LOGIN_ACCOUNT_FAILURE_LIMIT),
    )
    if retry_after:
        raise login_throttled(retry_after)


def enforce_consent_event_rate_limit(
    request: Request,
    property_id: Optional[str] = None,
    transaction_connection: Optional[Connection] = None,
) -> None:
    """Rate-limit by source before lookup, then by property after request validation."""
    now = utc_now()
    remote_ip = client_ip(request)
    if property_id is None:
        limits = (("consent_client", rate_limit_hash("consent_client", remote_ip), CONSENT_EVENT_CLIENT_LIMIT),)
    else:
        limits = (("consent_property", rate_limit_hash("consent_property", property_id), CONSENT_EVENT_PROPERTY_LIMIT),)
    retry_after, capacity_limited = consume_rate_limits(
        DATABASE_PATH,
        LOGGER,
        limits,
        now,
        CONSENT_EVENT_WINDOW_SECONDS,
        CONSENT_EVENT_MAX_BUCKETS,
        transaction_connection=transaction_connection,
    )
    if capacity_limited:
        raise HTTPException(status_code=429, detail="Consent event capacity is temporarily limited",
                            headers={"Retry-After": str(max(1, retry_after))})
    if retry_after:
        raise HTTPException(status_code=429, detail="Too many consent events; retry later",
                            headers={"Retry-After": str(retry_after)})


def enforce_invitation_rate_limit(
    request: Request,
    operation: str,
    limit: int,
    identity: Optional[str] = None,
) -> None:
    """Atomically bound invitation attempts by socket peer or HMAC-scoped actor."""
    now = utc_now()
    remote_ip = client_ip(request)
    scope = "invitation_" + operation
    limits = ((scope, rate_limit_hash(scope, identity or remote_ip), limit),)
    retry_after, capacity_limited = consume_rate_limits(
        DATABASE_PATH, LOGGER, limits, now, INVITATION_RATE_WINDOW_SECONDS, INVITATION_RATE_MAX_BUCKETS
    )
    if capacity_limited:
        raise HTTPException(status_code=429, detail="Invitation service is temporarily busy. Try again later.",
                            headers={"Retry-After": str(max(1, retry_after))})
    if retry_after:
        raise HTTPException(
            status_code=429,
            detail="Too many invitation attempts from this network. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )


def consent_event_capacity_level(active_total: int) -> str:
    if active_total >= CONSENT_EVENT_ACTIVE_TOTAL_LIMIT:
        return "exhausted"
    if active_total * 100 >= CONSENT_EVENT_ACTIVE_TOTAL_LIMIT * CONSENT_EVENT_CAPACITY_WARNING_PERCENT:
        return "warning"
    return "ok"


def consent_event_capacity_state() -> str:
    with connection() as conn:
        active_total = conn.execute(
            "SELECT COUNT(*) AS event_count FROM consent_events WHERE expires_at>?", (utc_now(),)
        ).fetchone()["event_count"]
    return consent_event_capacity_level(active_total)


def audit(conn: Connection, org_id: str, actor: str, action: str,
          resource_type: str, resource_id: str, details: Optional[dict] = None) -> None:
    append_audit_event(
        conn, secrets.token_hex(16), org_id, actor, action, resource_type, resource_id, utc_now(),
        json.dumps(details or {}, separators=(",", ":"), ensure_ascii=False),
    )


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)


class OrganizationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=160)
    requireTwoPersonPublish: bool = True


class OrganizationApprovalSettingsBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requireTwoPersonPublish: bool


class PropertyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=2, max_length=180)
    channel: Literal["web", "ios", "android"]
    environment: Literal["development", "staging", "production"] = "development"
    origin: Optional[str] = Field(default=None, min_length=1, max_length=512)


class PropertyOriginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    origin: str = Field(min_length=1, max_length=512)


class InviteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    role: Literal["admin", "editor", "viewer"]


class MemberRoleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["admin", "editor", "viewer"]


class OwnershipTransferBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    proposedOwnerId: str = Field(min_length=1, max_length=128)


class AcceptOwnershipTransferBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=40, max_length=256)


class AcceptInviteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=40, max_length=256)
    password: str = Field(min_length=12, max_length=1024)


class InvitationPreviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=40, max_length=256)


class PolicyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    policy: Dict[str, Any]
    expectedRevision: Optional[int] = Field(default=None, ge=1)


class PublishPolicyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: constr(strip_whitespace=True, min_length=5, max_length=500)


class ConsentEventBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    eventId: str = Field(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
    policyVersion: str = Field(min_length=1, max_length=64)
    channel: Literal["web", "ios", "android"]
    action: Literal["accept_all", "reject_all", "custom"]
    purposes: Dict[constr(pattern=r"^[a-z][a-z0-9_-]{1,63}$"), StrictBool] = Field(max_length=64)


class ScanCookieBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=256)
    classification: Literal["à examiner", "essentiel", "mesure d’audience", "personnalisation", "publicité"]


class ScanResourceBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str = Field(min_length=1, max_length=48)
    url: str = Field(min_length=1, max_length=2048)
    origin: str = Field(min_length=1, max_length=512)
    firstParty: StrictBool
    detail: str = Field(default="", max_length=200)
    amanControl: Optional[Literal["marker_present", "marker_missing"]] = None
    classification: Literal["à examiner", "essentiel", "mesure d’audience", "personnalisation", "publicité"]


class ScanReportBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_name: Literal["aman-local-inventory-v1"] = Field(alias="schema")
    scannedAt: datetime
    page: str = Field(min_length=1, max_length=2048)
    scope: Literal["current-page-only; no network upload"]
    limitations: list[str] = Field(max_length=10)
    cookies: list[ScanCookieBody] = Field(max_length=250)
    resources: list[ScanResourceBody] = Field(max_length=750)


class SessionContext(BaseModel):
    user_id: str
    email: str
    session_hash: str


def require_csrf(request: Request, context: SessionContext, x_aman_csrf: Optional[str]) -> None:
    cookie_value = request.cookies.get(CSRF_COOKIE)
    if not cookie_value or not x_aman_csrf or not hmac.compare_digest(cookie_value, x_aman_csrf):
        raise HTTPException(status_code=403, detail="CSRF validation failed")
    with connection() as conn:
        row = get_session_csrf_hash(conn, context.session_hash)
    if not row or not hmac.compare_digest(digest(cookie_value), row["csrf_hash"]):
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def current_session(request: Request) -> SessionContext:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    token_hash = digest(token)
    with connection() as conn:
        row = get_session_user(conn, token_hash)
        if not row or row["expires_at"] <= utc_now() or row["disabled"]:
            delete_session(conn, token_hash)
            raise HTTPException(status_code=401, detail="Session expired")
    return SessionContext(user_id=row["user_id"], email=row["email"], session_hash=token_hash)


def membership(conn: Connection, org_id: str, user_id: str) -> str:
    row = get_member_role(conn, org_id, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    return row["role"]


def require_role(role: str, allowed: set) -> None:
    if role not in allowed:
        raise HTTPException(status_code=403, detail="Insufficient organization role")


def validate_policy(body: Dict[str, Any], property_id: str, channel: str) -> dict:
    errors = sorted(POLICY_VALIDATOR.iter_errors(body), key=lambda err: list(err.path))
    if errors:
        first = errors[0]
        field_path = ".".join(str(part) for part in first.path) or "policy"
        raise HTTPException(status_code=422, detail=f"Policy schema: {field_path}: {first.message}")
    if body["propertyId"] != property_id:
        raise HTTPException(status_code=422, detail="Policy propertyId must match its property")
    if body["status"] != "draft":
        raise HTTPException(status_code=422, detail="Policies must be submitted as draft")
    purpose_ids = [purpose["id"] for purpose in body["purposes"]]
    if len(purpose_ids) != len(set(purpose_ids)):
        raise HTTPException(status_code=422, detail="Purpose IDs must be unique within a policy")
    if channel == "web" and body["retentionDays"] > 180:
        raise HTTPException(status_code=422, detail="Web cookie-choice retention cannot exceed 180 days in this Morocco-focused policy flow")
    if channel not in {channel for purpose in body["purposes"] for channel in purpose["channels"]}:
        raise HTTPException(status_code=422, detail=f"At least one purpose must target the {channel} channel")
    for purpose in body["purposes"]:
        if purpose["required"] and purpose["consentRequired"]:
            raise HTTPException(status_code=422, detail="Required purposes cannot require an optional consent choice")
        if purpose.get("initiallyEnabled", False) and purpose["consentRequired"] and not purpose["required"]:
            raise HTTPException(status_code=422, detail="A purpose requiring a positive choice cannot start enabled")
        if purpose["required"] and purpose.get("initiallyEnabled", True) is False:
            raise HTTPException(status_code=422, detail="Required purposes must start enabled")
    return body


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_scrypt_available()
    ensure_rate_limit_hash_key()
    try:
        with connection() as conn:
            conn.require_current_schema()
        sweeper = asyncio.create_task(purge_expired_consent_events())
        try:
            yield
        finally:
            sweeper.cancel()
            with suppress(asyncio.CancelledError):
                await sweeper
    finally:
        close_database_pool()


async def purge_expired_consent_events() -> None:
    """Physically remove expired local event records while the API is running."""
    while True:
        await asyncio.sleep(60)
        try:
            with transaction() as conn:
                conn.execute("DELETE FROM consent_events WHERE expires_at <= ?", (utc_now(),))
            prune_rate_limit_buckets(DATABASE_PATH, LOGGER, utc_now())
        except DatabaseError:
            LOGGER.exception("Consent event expiry sweep failed")


app = FastAPI(title="Aman Consent API", version="0.1.0", lifespan=lifespan)
STATIC_CONSOLE_DIR = Path(os.environ.get("AMAN_STATIC_CONSOLE_DIR", str(ROOT / "console")))
if STATIC_CONSOLE_DIR.is_dir():
    app.mount(
        "/console",
        StaticFiles(directory=STATIC_CONSOLE_DIR, html=True),
        name="console",
    )

    @app.get("/aman-cmp.js", include_in_schema=False)
    def serve_web_consent_sdk():
        return FileResponse(
            STATIC_CONSOLE_DIR / "aman-cmp.js",
            media_type="application/javascript",
        )

app.add_middleware(RequestBodyLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Content-Type", "X-Aman-CSRF", "If-None-Match"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
    if ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.middleware("http")
async def limit_scan_upload_size(request: Request, call_next):
    scan_upload = request.method == "POST" and re.fullmatch(
        r"/v1/organizations/[^/]+/properties/[^/]+/scans", request.url.path
    )
    if scan_upload:
        if request.headers.get("content-type", "").split(";", 1)[0].strip().lower() != "application/json":
            return JSONResponse({"detail": "Scan reports must be uploaded as application/json"}, status_code=415)
        raw_length = request.headers.get("content-length")
        if not raw_length or not raw_length.isdecimal():
            return JSONResponse({"detail": "A Content-Length header is required for scan imports"}, status_code=411)
        if int(raw_length) > SCAN_REPORT_MAX_BYTES:
            return JSONResponse({"detail": "Scan report exceeds the 1 MiB import limit"}, status_code=413)
    return await call_next(request)


@app.middleware("http")
async def property_public_cors(request: Request, call_next):
    """Allow a registered web property to call only the public API, without cookies."""
    route = re.fullmatch(r"/v1/public/properties/([^/]+)/(policy|consent-events)", request.url.path)
    origin = request.headers.get("origin")
    if not route or not origin:
        return await call_next(request)
    property_id, resource = route.groups()
    expected_method = "GET" if resource == "policy" else "POST"
    with connection() as conn:
        prop = get_public_property(conn, property_id)
    if not prop or prop["channel"] != "web" or not prop["origin"] or origin != prop["origin"]:
        return await call_next(request)

    if request.method == "OPTIONS":
        requested_method = request.headers.get("access-control-request-method", "").upper()
        requested_headers = {
            item.strip().lower()
            for item in request.headers.get("access-control-request-headers", "").split(",")
            if item.strip()
        }
        allowed_headers = {"content-type", "if-none-match"}
        if requested_method != expected_method or not requested_headers.issubset(allowed_headers):
            return Response(status_code=403)
        return Response(status_code=204, headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": f"{expected_method}, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, If-None-Match",
            "Access-Control-Max-Age": "600",
            "Vary": "Origin",
        })

    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Expose-Headers"] = "ETag"
    if "Access-Control-Allow-Credentials" in response.headers:
        del response.headers["Access-Control-Allow-Credentials"]
    response.headers["Vary"] = "Origin"
    return response


@app.get("/health")
def health():
    return {"service": "aman-consent-api", "status": "ok", "environment": ENVIRONMENT}


@app.get("/health/ready")
def readiness():
    """Report ready only when the configured database and its schema are usable."""
    try:
        with connection() as conn:
            conn.execute("SELECT 1").fetchone()
            conn.require_current_schema()
        capacity = consent_event_capacity_state()
    except Exception as error:
        LOGGER.warning("Readiness check failed (%s)", type(error).__name__)
        return JSONResponse(
            {"service": "aman-consent-api", "status": "not_ready"},
            status_code=503,
            headers={"Cache-Control": "no-store"},
        )
    # Capacity is reported, not gated: an exhausted event store must not take the console down.
    return JSONResponse(
        {"service": "aman-consent-api", "status": "ready", "consentEventCapacity": capacity},
        headers={"Cache-Control": "no-store"},
    )


@app.post("/v1/auth/login")
def login(body: LoginBody, request: Request, response: Response):
    client_key = login_client_key(request)
    enforce_login_rate_limit(client_key)
    email = str(body.email).strip().lower()
    account_key, device_key = enforce_account_rate_limit(request, email)
    with connection() as conn:
        user = get_user_credentials(conn, email)
    password_hash = (
        user["password_hash"]
        if user and not user["disabled"]
        else f"scrypt${secrets.token_bytes(16).hex()}${'0' * 128}"
    )
    password_matches = check_password(body.password, password_hash)
    if not user or user["disabled"] or not password_matches:
        note_failed_password(client_key, account_key, device_key)
        raise HTTPException(status_code=401, detail="Email or password is incorrect")

    # The source counter is not reset on success, so one valid account cannot be
    # used to keep guessing other accounts from the same source.
    clear_login_failures(account_key, "login_account")
    if device_key:
        clear_login_failures(device_key, "login_device")

    token = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    now = utc_now()
    with transaction() as conn:
        delete_expired_sessions(conn, now)
        persist_session_creation(
            conn, digest(token), digest(csrf_token), user["id"], now + SESSION_TTL_SECONDS, now,
        )
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=COOKIE_SECURE,
                        samesite="strict", max_age=SESSION_TTL_SECONDS, path="/")
    response.set_cookie(CSRF_COOKIE, csrf_token, httponly=False, secure=COOKIE_SECURE,
                        samesite="strict", max_age=SESSION_TTL_SECONDS, path="/")
    response.set_cookie(DEVICE_COOKIE, device_cookie_value(account_key), httponly=True, secure=COOKIE_SECURE,
                        samesite="strict", max_age=DEVICE_COOKIE_TTL_SECONDS, path="/v1/auth/login")
    return {"csrfToken": csrf_token, "expiresAt": now + SESSION_TTL_SECONDS}


@app.post("/v1/auth/logout")
def logout(request: Request, response: Response, x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    with transaction() as conn:
        delete_session(conn, context.session_hash)
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="strict")
    response.delete_cookie(CSRF_COOKIE, path="/", samesite="strict")
    return {"ok": True}


@app.get("/v1/auth/me")
def who_am_i(request: Request):
    context = current_session(request)
    csrf_token = request.cookies.get(CSRF_COOKIE)
    with connection() as conn:
        session = get_session_csrf_hash(conn, context.session_hash)
        orgs = list_auth_user_organizations(conn, context.user_id)
    if not session or not csrf_token or not hmac.compare_digest(digest(csrf_token), session["csrf_hash"]):
        raise HTTPException(status_code=403, detail="CSRF token unavailable; sign in again")
    return {"userId": context.user_id, "email": context.email,
            "csrfToken": csrf_token,
            "organizations": [dict(row) for row in orgs]}


@app.get("/v1/dashboard")
def dashboard(request: Request):
    """Return real control-plane counts only for organizations in the current session."""
    context = current_session(request)
    now = utc_now()
    metrics_since = now - 30 * 86_400
    with connection() as conn:
        organizations, properties, recent_events, consent_counts = load_dashboard_sources(
            conn, context.user_id, metrics_since, now
        )

    property_items = [dict(row) for row in properties]
    counts_by_property = {row["property_id"]: dict(row) for row in consent_counts}
    for item in property_items:
        counts = counts_by_property.get(item["id"], {})
        item["consent_decision_count_30d"] = counts.get("decision_count", 0)
        item["consent_accept_all_count_30d"] = counts.get("accept_all_count", 0)
        item["consent_reject_all_count_30d"] = counts.get("reject_all_count", 0)
        item["consent_custom_count_30d"] = counts.get("custom_count", 0)
        item["latest_decision_received_at"] = counts.get("latest_decision_received_at")
    organization_items = [dict(row) for row in organizations]
    for organization in organization_items:
        scoped = [item for item in property_items if item["org_id"] == organization["id"]]
        organization["property_count"] = len(scoped)
        organization["published_property_count"] = sum(item["published_version"] is not None for item in scoped)
        organization["draft_count"] = sum(item["draft_count"] for item in scoped)
        organization["consent_decision_count_30d"] = sum(item["consent_decision_count_30d"] for item in scoped)
        organization["consent_accept_all_count_30d"] = sum(item["consent_accept_all_count_30d"] for item in scoped)
        organization["consent_reject_all_count_30d"] = sum(item["consent_reject_all_count_30d"] for item in scoped)
        organization["consent_custom_count_30d"] = sum(item["consent_custom_count_30d"] for item in scoped)
        organization["latest_decision_received_at"] = max(
            (item["latest_decision_received_at"] for item in scoped if item["latest_decision_received_at"] is not None),
            default=None,
        )
    events = [{**dict(row), "details": json.loads(row["details"])} for row in recent_events]
    return {
        "summary": {
            "organization_count": len(organization_items),
            "property_count": len(property_items),
            "published_property_count": sum(item["published_version"] is not None for item in property_items),
            "draft_count": sum(item["draft_count"] for item in property_items),
            "consent_decision_count_30d": sum(item["consent_decision_count_30d"] for item in property_items),
            "consent_accept_all_count_30d": sum(item["consent_accept_all_count_30d"] for item in property_items),
            "consent_reject_all_count_30d": sum(item["consent_reject_all_count_30d"] for item in property_items),
            "consent_custom_count_30d": sum(item["consent_custom_count_30d"] for item in property_items),
        },
        "organizations": organization_items,
        "properties": property_items,
        "recent_events": events,
    }


@app.post("/v1/auth/invitations/preview")
def preview_invitation(body: InvitationPreviewBody, request: Request):
    enforce_invitation_rate_limit(request, "preview", INVITATION_PREVIEW_LIMIT)
    now = utc_now()
    with connection() as conn:
        invite = get_invitation_preview(conn, digest(body.token), now)
    if not invite:
        raise HTTPException(status_code=400, detail="Invitation is invalid or expired")
    email_local, email_domain = invite["email"].rsplit("@", 1)
    masked_email = f"{email_local[:1]}***@{email_domain}"
    return {
        "organizationName": invite["organization_name"],
        "role": invite["role"],
        "inviteeEmailMasked": masked_email,
        "expiresAt": invite["expires_at"],
    }


@app.post("/v1/auth/invitations/accept", status_code=status.HTTP_201_CREATED)
def accept_invitation(body: AcceptInviteBody, request: Request):
    enforce_invitation_rate_limit(request, "accept", INVITATION_ACCEPT_LIMIT)
    now = utc_now()
    token_hash = digest(body.token)
    with transaction() as conn:
        invite = get_invitation_for_acceptance(conn, token_hash)
        if invite:
            conn.lock_invitation(invite["id"])
            invite = get_invitation_for_acceptance(conn, token_hash)
        if not invite or invite["accepted_at"] or invite["expires_at"] <= now:
            raise HTTPException(status_code=400, detail="Invitation is invalid or expired")
        existing_user = get_invited_user_account(conn, invite["email"])
        if existing_user:
            if existing_user["disabled"]:
                raise HTTPException(status_code=403, detail="This Aman account is disabled")
            if not check_password(body.password, existing_user["password_hash"]):
                raise HTTPException(status_code=401, detail="The password does not match the invited Aman account")
            user_id = existing_user["id"]
            account_created = False
        else:
            user_id = secrets.token_hex(16)
            create_invited_user(conn, user_id, invite["email"], hash_password(body.password), now)
            account_created = True
        if is_organization_member(conn, invite["org_id"], user_id):
            raise HTTPException(status_code=409, detail="This account is already a member of the organization")
        add_invited_member(conn, invite["org_id"], user_id, invite["role"], now)
        mark_invitation_accepted(conn, invite["id"], now)
        audit(conn, invite["org_id"], user_id, "member.joined", "user", user_id, {"role": invite["role"]})
    return {"ok": True, "accountCreated": account_created}


@app.post("/v1/auth/ownership-transfers/accept")
def accept_ownership_transfer(body: AcceptOwnershipTransferBody, request: Request,
                             x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    with transaction() as conn:
        transfer = get_transfer_by_token_hash(conn, digest(body.token))
        if not transfer:
            raise HTTPException(status_code=400, detail="Ownership transfer is invalid or expired")
        conn.lock_organization(transfer["org_id"])
        transfer = get_transfer_by_token_hash(conn, digest(body.token))
        if not transfer or transfer["accepted_at"] is not None or transfer["revoked_at"] is not None \
                or transfer["expires_at"] <= now:
            raise HTTPException(status_code=400, detail="Ownership transfer is invalid or expired")
        if transfer["proposed_owner_id"] != context.user_id:
            raise HTTPException(status_code=403, detail="This transfer is addressed to another Aman account")
        source = get_ownership_membership_role(conn, transfer["org_id"], transfer["current_owner_id"])
        target = get_ownership_membership_role(conn, transfer["org_id"], context.user_id)
        if not source or source["role"] != "owner" or not target or target["role"] != "admin":
            raise HTTPException(status_code=409, detail="Organization ownership changed before acceptance")
        persist_ownership_member_role(conn, transfer["org_id"], transfer["current_owner_id"], "admin")
        persist_ownership_member_role(conn, transfer["org_id"], context.user_id, "owner")
        mark_transfer_accepted(conn, transfer["id"], now)
        revoke_other_pending_transfers(conn, transfer["org_id"], transfer["id"], now)
        audit(conn, transfer["org_id"], context.user_id, "organization.ownership_transferred",
              "organization", transfer["org_id"],
              {"fromUserId": transfer["current_owner_id"], "toUserId": context.user_id})
    return {"ok": True, "organizationId": transfer["org_id"], "role": "owner"}


@app.get("/v1/organizations")
def list_organizations(request: Request):
    context = current_session(request)
    with connection() as conn:
        rows = list_user_organizations(conn, context.user_id)
    return {"organizations": [dict(row) for row in rows]}


@app.post("/v1/organizations", status_code=status.HTTP_201_CREATED)
def create_organization(body: OrganizationBody, request: Request,
                        x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    org_id = secrets.token_urlsafe(18)
    now = utc_now()
    with transaction() as conn:
        persist_organization_creation(
            conn, org_id, body.name.strip(), body.requireTwoPersonPublish, context.user_id, now,
        )
        audit(conn, org_id, context.user_id, "organization.created", "organization", org_id)
    return {"id": org_id, "name": body.name.strip(), "role": "owner",
            "requireTwoPersonPublish": body.requireTwoPersonPublish}


def approval_settings_payload(conn: Connection, org_id: str, enabled: bool, now: int) -> dict:
    pending = get_pending_approval_setting_change(conn, org_id, now)
    return {
        "id": org_id,
        "requireTwoPersonPublish": enabled,
        "pendingChange": {
            "id": pending["id"],
            "requestedBy": pending["requestedBy"],
            "requestedByEmail": pending["requestedByEmail"],
            "requireTwoPersonPublish": bool(pending["require_two_person_publish"]),
            "createdAt": pending["createdAt"],
            "expiresAt": pending["expiresAt"],
        } if pending else None,
    }


@app.get("/v1/organizations/{org_id}/approval-settings")
def get_organization_approval_settings(org_id: str, request: Request):
    context = current_session(request)
    with connection() as conn:
        membership(conn, org_id, context.user_id)
        row = get_organization_approval_setting(conn, org_id)
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found")
        return approval_settings_payload(conn, org_id, bool(row["require_two_person_publish"]), utc_now())


@app.put("/v1/organizations/{org_id}/approval-settings")
def update_organization_approval_settings(
    org_id: str,
    body: OrganizationApprovalSettingsBody,
    request: Request,
    response: Response,
    x_aman_csrf: Optional[str] = Header(default=None),
):
    """Strengthen the rule at once; weakening it only opens a request for a second approver."""
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    with transaction() as conn:
        conn.lock_organization(org_id)
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
        row = get_organization_approval_setting(conn, org_id)
        if not row:
            raise HTTPException(status_code=404, detail="Organization not found")
        previous = bool(row["require_two_person_publish"])
        if body.requireTwoPersonPublish:
            for change in revoke_pending_approval_setting_changes(conn, org_id, context.user_id, now):
                audit(conn, org_id, context.user_id, "organization.approval_setting_change_revoked",
                      "approval_setting_change", change["id"], {"reason": "rule_kept_enabled"})
            if not previous:
                update_organization_approval_setting(conn, org_id, True)
                audit(conn, org_id, context.user_id, "organization.approval_setting_updated", "organization", org_id,
                      {"requireTwoPersonPublish": {"before": False, "after": True}})
            return approval_settings_payload(conn, org_id, True, now)
        if not previous:
            return approval_settings_payload(conn, org_id, False, now)
        if get_pending_approval_setting_change(conn, org_id, now):
            raise HTTPException(status_code=409, detail="A change to the approval rule is already awaiting approval")
        change_id = secrets.token_hex(16)
        persist_approval_setting_change(
            conn, change_id, org_id, context.user_id, False, now, now + APPROVAL_SETTING_CHANGE_TTL_SECONDS,
        )
        audit(conn, org_id, context.user_id, "organization.approval_setting_change_requested",
              "approval_setting_change", change_id,
              {"requireTwoPersonPublish": {"before": True, "after": False}})
        response.status_code = status.HTTP_202_ACCEPTED
        return approval_settings_payload(conn, org_id, True, now)


@app.post("/v1/organizations/{org_id}/approval-settings/changes/{change_id}/approve")
def approve_approval_setting_change(org_id: str, change_id: str, request: Request,
                                    x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    with transaction() as conn:
        conn.lock_organization(org_id)
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
        change = get_approval_setting_change(conn, org_id, change_id)
        if not change:
            raise HTTPException(status_code=404, detail="Approval rule change not found")
        if change["approved_at"] is not None or change["revoked_at"] is not None or change["expires_at"] <= now:
            raise HTTPException(status_code=409, detail="This approval rule change is no longer pending")
        if change["requested_by"] == context.user_id:
            raise HTTPException(status_code=403, detail="A different owner or administrator must approve this change")
        row = get_organization_approval_setting(conn, org_id)
        enabled = bool(change["require_two_person_publish"])
        mark_approval_setting_change_approved(conn, change_id, context.user_id, now)
        update_organization_approval_setting(conn, org_id, enabled)
        audit(conn, org_id, context.user_id, "organization.approval_setting_updated", "organization", org_id,
              {"requireTwoPersonPublish": {"before": bool(row["require_two_person_publish"]), "after": enabled},
               "changeId": change_id, "requestedBy": change["requested_by"], "approvedBy": context.user_id})
        return approval_settings_payload(conn, org_id, enabled, now)


@app.delete("/v1/organizations/{org_id}/approval-settings/changes/{change_id}")
def revoke_approval_setting_change(org_id: str, change_id: str, request: Request,
                                   x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    with transaction() as conn:
        conn.lock_organization(org_id)
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
        change = get_approval_setting_change(conn, org_id, change_id)
        if not change:
            raise HTTPException(status_code=404, detail="Approval rule change not found")
        if change["approved_at"] is not None or change["revoked_at"] is not None or change["expires_at"] <= now:
            raise HTTPException(status_code=409, detail="This approval rule change is no longer pending")
        revoke_pending_approval_setting_changes(conn, org_id, context.user_id, now)
        audit(conn, org_id, context.user_id, "organization.approval_setting_change_revoked",
              "approval_setting_change", change_id, {"requestedBy": change["requested_by"]})
    return {"ok": True}


@app.post("/v1/organizations/{org_id}/invitations", status_code=status.HTTP_201_CREATED)
def invite_member(org_id: str, body: InviteBody, request: Request,
                  x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    with connection() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
    enforce_invitation_rate_limit(
        request, "admin_create", INVITATION_CREATE_LIMIT, f"{org_id}:{context.user_id}"
    )
    try:
        email_config = load_invitation_email_config()
    except InvitationEmailConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Invitation email delivery is misconfigured") from exc
    token = secrets.token_urlsafe(40)
    now = utc_now()
    with transaction() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
        org_row = conn.execute("SELECT name FROM organizations WHERE id=?", (org_id,)).fetchone()
        if not org_row:
            raise HTTPException(status_code=404, detail="Organization not found")
        org_name = org_row["name"]
        email = str(body.email).strip().lower()
        existing_user = get_user_for_invitation(conn, email)
        if existing_user and existing_user["disabled"]:
            raise HTTPException(status_code=409, detail="This Aman account is disabled")
        if existing_user and is_organization_member(conn, org_id, existing_user["id"]):
            raise HTTPException(status_code=409, detail="This account is already a member of the organization")
        if has_active_invitation(conn, org_id, email, now):
            raise HTTPException(status_code=409, detail="An active invitation already exists for this email")
        invite_id = secrets.token_hex(16)
        create_invitation(
            conn, invite_id, org_id, email, body.role, digest(token), context.user_id,
            now + INVITE_TTL_SECONDS,
        )
        audit(conn, org_id, context.user_id, "member.invited", "invitation", invite_id,
              {"role": body.role, "deliveryMethod": "smtp" if email_config else "manual"})

    delivery = "manual"
    if email_config:
        try:
            send_invitation_email(email_config, email, org_name, body.role, token, now + INVITE_TTL_SECONDS)
            delivery = "sent"
        except Exception:
            delivery = "failed"
            LOGGER.warning("SMTP invitation delivery failed for invitation_id=%s", invite_id)
        try:
            with transaction() as conn:
                audit(conn, org_id, context.user_id, "member.invitation_delivery_updated", "invitation",
                      invite_id, {"method": "smtp", "status": delivery})
        except Exception:
            LOGGER.exception("Could not record invitation delivery status for invitation_id=%s", invite_id)

    result = {"expiresAt": now + INVITE_TTL_SECONDS, "delivery": delivery}
    if delivery != "sent":
        result["invitationToken"] = token
    return result


@app.post("/v1/organizations/{org_id}/invitations/{invitation_id}/resend")
def resend_invitation(org_id: str, invitation_id: str, request: Request,
                      x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    with connection() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
    enforce_invitation_rate_limit(
        request, "admin_resend", INVITATION_RESEND_LIMIT, f"{org_id}:{context.user_id}"
    )
    try:
        email_config = load_invitation_email_config()
    except InvitationEmailConfigurationError as exc:
        raise HTTPException(status_code=503, detail="Invitation email delivery is misconfigured") from exc
    token = secrets.token_urlsafe(40)
    now = utc_now()
    expires_at = now + INVITE_TTL_SECONDS
    with transaction() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
        conn.lock_invitation(invitation_id)
        invite = get_invitation_for_resend(conn, org_id, invitation_id)
        if not invite:
            raise HTTPException(status_code=404, detail="Invitation not found")
        if invite["accepted_at"] is not None:
            raise HTTPException(status_code=409, detail="Invitation has already been accepted")
        existing_user = get_user_for_invitation(conn, invite["email"])
        if existing_user and existing_user["disabled"]:
            raise HTTPException(status_code=409, detail="This Aman account is disabled")
        if existing_user and is_organization_member(conn, org_id, existing_user["id"]):
            raise HTTPException(status_code=409, detail="This account is already a member of the organization")
        org_row = conn.execute("SELECT name FROM organizations WHERE id=?", (org_id,)).fetchone()
        if not org_row:
            raise HTTPException(status_code=404, detail="Organization not found")
        org_name = org_row["name"]
        if not rotate_invitation_token(conn, org_id, invitation_id, digest(token), context.user_id, expires_at):
            raise HTTPException(status_code=409, detail="Invitation has already been accepted")
        audit(conn, org_id, context.user_id, "member.invitation_resent", "invitation", invitation_id,
              {"role": invite["role"], "deliveryMethod": "smtp" if email_config else "manual"})

    delivery = "manual"
    if email_config:
        try:
            send_invitation_email(email_config, invite["email"], org_name, invite["role"], token, expires_at)
            delivery = "sent"
        except Exception:
            delivery = "failed"
            LOGGER.warning("SMTP invitation resend failed for invitation_id=%s", invitation_id)
        try:
            with transaction() as conn:
                audit(conn, org_id, context.user_id, "member.invitation_delivery_updated", "invitation",
                      invitation_id, {"method": "smtp", "status": delivery, "resent": True})
        except Exception:
            LOGGER.exception("Could not record invitation resend status for invitation_id=%s", invitation_id)

    result = {"invitationId": invitation_id, "expiresAt": expires_at, "delivery": delivery}
    if delivery != "sent":
        result["invitationToken"] = token
    return result


@app.get("/v1/organizations/{org_id}/invitations")
def list_invitations(org_id: str, request: Request):
    context = current_session(request)
    with connection() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
        rows = list_organization_invitations(conn, org_id)
    now = utc_now()
    invitations = [
        {**dict(row), "status": "pending" if row["expiresAt"] > now else "expired"}
        for row in rows
    ]
    return {"invitations": invitations}


@app.delete("/v1/organizations/{org_id}/invitations/{invitation_id}")
def revoke_invitation(org_id: str, invitation_id: str, request: Request,
                      x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    with transaction() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
        conn.lock_invitation(invitation_id)
        invite = get_invitation_for_revocation(conn, org_id, invitation_id)
        if not invite:
            raise HTTPException(status_code=404, detail="Invitation not found")
        if invite["accepted_at"] is not None:
            raise HTTPException(status_code=409, detail="Invitation has already been accepted")
        persist_invitation_revocation(conn, org_id, invitation_id)
        audit(conn, org_id, context.user_id, "member.invitation_revoked", "invitation", invitation_id,
              {"role": invite["role"]})
    return {"ok": True}


@app.get("/v1/organizations/{org_id}/members")
def list_members(org_id: str, request: Request):
    context = current_session(request)
    with connection() as conn:
        membership(conn, org_id, context.user_id)
        rows = list_member_rows(conn, org_id)
    return {"members": [dict(row) for row in rows]}


@app.put("/v1/organizations/{org_id}/members/{member_id}")
def update_member_role(org_id: str, member_id: str, body: MemberRoleBody, request: Request,
                       x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    with transaction() as conn:
        conn.lock_organization(org_id)
        actor_role = membership(conn, org_id, context.user_id)
        require_role(actor_role, {"owner", "admin"})
        target = get_member_role(conn, org_id, member_id)
        if not target:
            raise HTTPException(status_code=404, detail="Organization member not found")
        if target["role"] == "owner":
            raise HTTPException(status_code=409, detail="The owner role requires a separate ownership-transfer process")
        previous_role = target["role"]
        if previous_role != body.role:
            persist_member_role_update(conn, org_id, member_id, body.role)
            audit(conn, org_id, context.user_id, "member.role_changed", "membership", member_id,
                  {"from": previous_role, "to": body.role})
    return {"userId": member_id, "role": body.role}


@app.delete("/v1/organizations/{org_id}/members/{member_id}")
def remove_member(org_id: str, member_id: str, request: Request,
                  x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    with transaction() as conn:
        conn.lock_organization(org_id)
        actor_role = membership(conn, org_id, context.user_id)
        require_role(actor_role, {"owner", "admin"})
        target = get_member_role(conn, org_id, member_id)
        if not target:
            raise HTTPException(status_code=404, detail="Organization member not found")
        if target["role"] == "owner":
            raise HTTPException(status_code=409, detail="The owner cannot be removed from the organization")
        persist_member_removal(conn, org_id, member_id)
        audit(conn, org_id, context.user_id, "member.removed", "membership", member_id,
              {"previousRole": target["role"]})
    return {"ok": True}


@app.post("/v1/organizations/{org_id}/ownership-transfers")
def create_ownership_transfer(org_id: str, body: OwnershipTransferBody, request: Request,
                              x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    token = secrets.token_urlsafe(40)
    now = utc_now()
    with transaction() as conn:
        conn.lock_organization(org_id)
        actor_role = membership(conn, org_id, context.user_id)
        require_role(actor_role, {"owner"})
        target = get_ownership_membership_role(conn, org_id, body.proposedOwnerId)
        if not target or target["role"] != "admin":
            raise HTTPException(status_code=422, detail="The proposed owner must be an existing organization admin")
        if has_active_transfer(conn, org_id, now):
            raise HTTPException(status_code=409, detail="An ownership transfer is already awaiting acceptance")
        transfer_id = secrets.token_hex(16)
        expires_at = now + OWNERSHIP_TRANSFER_TTL_SECONDS
        persist_ownership_transfer(
            conn, transfer_id, org_id, context.user_id, body.proposedOwnerId, digest(token), now, expires_at,
        )
        audit(conn, org_id, context.user_id, "organization.ownership_transfer_proposed",
              "ownership_transfer", transfer_id, {"proposedOwnerId": body.proposedOwnerId})
    return {"id": transfer_id, "token": token, "expiresAt": expires_at,
            "delivery": "development-only; transmit through a reviewed secure channel"}


@app.get("/v1/organizations/{org_id}/ownership-transfers/pending")
def get_pending_ownership_transfer(org_id: str, request: Request):
    context = current_session(request)
    with connection() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner"})
        row = get_pending_transfer(conn, org_id, context.user_id, utc_now())
    return {"transfer": dict(row) if row else None}


@app.delete("/v1/organizations/{org_id}/ownership-transfers/pending")
def revoke_pending_ownership_transfer(org_id: str, request: Request,
                                     x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    with transaction() as conn:
        conn.lock_organization(org_id)
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner"})
        rows = list_pending_transfers_for_revocation(conn, org_id, context.user_id, now)
        if not rows:
            raise HTTPException(status_code=404, detail="No pending ownership transfer")
        revoke_pending_transfers(conn, org_id, context.user_id, now)
        for row in rows:
            audit(conn, org_id, context.user_id, "organization.ownership_transfer_revoked",
                  "ownership_transfer", row["id"])
    return {"ok": True}


@app.post("/v1/organizations/{org_id}/properties", status_code=status.HTTP_201_CREATED)
def create_property(org_id: str, body: PropertyBody, request: Request,
                   x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    if body.channel == "web":
        if not body.origin:
            raise HTTPException(status_code=422, detail="A web property requires a configured origin")
        origin = canonical_property_origin(body.origin, allow_loopback_http=body.environment == "development")
    else:
        if body.origin is not None:
            raise HTTPException(status_code=422, detail="Only web properties can have a browser origin")
        origin = None
    property_id = secrets.token_urlsafe(24)
    now = utc_now()
    try:
        with transaction() as conn:
            role = membership(conn, org_id, context.user_id)
            require_role(role, {"owner", "admin", "editor"})
            persist_property(conn, property_id, org_id, body.name.strip(), body.channel,
                             body.environment, origin, now)
            audit(conn, org_id, context.user_id, "property.created", "property", property_id,
                  {"channel": body.channel, "environment": body.environment, "origin": origin})
    except IntegrityError:
        raise HTTPException(status_code=409, detail="A property with this name and channel already exists; use a distinct name for each environment")
    return {"id": property_id, "orgId": org_id, "name": body.name.strip(), "channel": body.channel,
            "environment": body.environment, "origin": origin}


@app.get("/v1/organizations/{org_id}/properties")
def list_properties(org_id: str, request: Request):
    context = current_session(request)
    with connection() as conn:
        membership(conn, org_id, context.user_id)
        rows = list_property_rows(conn, org_id)
    return {"properties": [dict(row) for row in rows]}


def canonical_property_origin(value: str, *, allow_loopback_http: bool = False) -> str:
    page, origin = canonical_scan_url(value)
    parts = urlsplit(value)
    if page != f"{origin}/":
        raise HTTPException(status_code=422, detail="A property origin must contain only scheme, host, and optional port")
    host = parts.hostname or ""
    loopback = host.lower() == "localhost"
    try:
        ip = ipaddress.ip_address(host)
        loopback = ip.is_loopback
    except ValueError:
        pass
    scheme = parts.scheme.lower()
    if scheme != "https" and not (allow_loopback_http and scheme == "http" and loopback):
        raise HTTPException(status_code=422, detail="Web property origins require HTTPS; HTTP loopback is limited to development")
    return origin


@app.put("/v1/organizations/{org_id}/properties/{property_id}/origin")
def update_property_origin(org_id: str, property_id: str, body: PropertyOriginBody, request: Request,
                           x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    with transaction() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin", "editor"})
        prop = get_property_for_origin_update(conn, org_id, property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        if prop["channel"] != "web":
            raise HTTPException(status_code=422, detail="Only web properties can have a browser origin")
        origin = canonical_property_origin(body.origin, allow_loopback_http=prop["environment"] == "development")
        if prop["origin"] != origin:
            if has_scan_reports(conn, property_id):
                raise HTTPException(status_code=409, detail="Delete this property's inventory reports before changing its origin")
            persist_property_origin(conn, property_id, origin)
            audit(conn, org_id, context.user_id, "property.origin_updated", "property", property_id,
                  {"previousOrigin": prop["origin"], "origin": origin})
    return {"id": property_id, "origin": origin}


def canonical_scan_url(value: str) -> Tuple[str, str]:
    if value.strip() != value or any(ord(char) < 32 for char in value):
        raise HTTPException(status_code=422, detail="Scan URLs must not contain whitespace controls")
    try:
        parts = urlsplit(value)
        host = parts.hostname
        _ = parts.port
    except ValueError:
        raise HTTPException(status_code=422, detail="Scan report contains an invalid URL")
    if (parts.scheme.lower() not in {"http", "https"} or not host or parts.username is not None or
            parts.password is not None or parts.query or parts.fragment or "?" in value or "#" in value):
        raise HTTPException(status_code=422, detail="Scan URLs must be HTTP(S), omit credentials, query, and fragment")
    try:
        normalized_host = ipaddress.ip_address(host)
        host_text = f"[{normalized_host.compressed}]" if normalized_host.version == 6 else normalized_host.compressed
    except ValueError:
        try:
            host_text = host.encode("idna").decode("ascii").lower()
        except UnicodeError:
            raise HTTPException(status_code=422, detail="Scan URL contains an invalid host")
        if "%" in host_text or not re.fullmatch(
            r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*\.?",
            host_text,
        ):
            raise HTTPException(status_code=422, detail="Scan URL contains an invalid host")
    port = parts.port
    if port == (443 if parts.scheme.lower() == "https" else 80):
        port = None
    origin = f"{parts.scheme.lower()}://{host_text}{f':{port}' if port else ''}"
    return f"{origin}{parts.path or '/'}", origin


@app.post("/v1/organizations/{org_id}/properties/{property_id}/scans", status_code=status.HTTP_201_CREATED)
def import_scan_report(org_id: str, property_id: str, body: ScanReportBody, request: Request,
                       x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    if body.scannedAt.tzinfo is None or body.scannedAt.utcoffset() is None:
        raise HTTPException(status_code=422, detail="Scan timestamp must include a timezone")
    now = utc_now()
    scanned_at = int(body.scannedAt.timestamp())
    if scanned_at > now + 300:
        raise HTTPException(status_code=422, detail="Scan timestamp cannot be in the future")
    page, page_origin = canonical_scan_url(body.page)
    report = body.model_dump(mode="json", by_alias=True)
    report["page"] = page
    for item in report["resources"]:
        resource_url, resource_origin = canonical_scan_url(item["url"])
        item["url"] = resource_url
        item["origin"] = resource_origin
        item["firstParty"] = resource_origin == page_origin
    report_json = json.dumps(report, separators=(",", ":"), ensure_ascii=False)
    report_id = secrets.token_hex(16)
    with transaction() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin", "editor"})
        prop = get_property_for_organization(conn, org_id, property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        if prop["channel"] != "web":
            raise HTTPException(status_code=422, detail="Browser inventory reports can only be attached to web properties")
        if not prop["origin"]:
            raise HTTPException(status_code=409, detail="Set this property's web origin before importing an inventory")
        if page_origin != prop["origin"]:
            raise HTTPException(status_code=422, detail="The scanned page origin does not match this web property")
        insert_scan_report(
            conn, report_id, property_id, context.user_id, scanned_at, now, page_origin,
            len(report["resources"]), len(report["cookies"]), report_json, SCAN_REPORTS_PER_PROPERTY,
        )
        audit(conn, org_id, context.user_id, "scan.imported", "scan_report", report_id,
              {"resourceCount": len(report["resources"]), "cookieCount": len(report["cookies"]),
               "scannedAt": scanned_at})
    return {
        "id": report_id, "propertyId": property_id, "scannedAt": scanned_at,
        "importedAt": now, "pageOrigin": page_origin,
        "resourceCount": len(report["resources"]), "cookieCount": len(report["cookies"]),
    }


@app.get("/v1/organizations/{org_id}/properties/{property_id}/scans")
def list_scan_reports(org_id: str, property_id: str, request: Request,
                      limit: int = Query(default=20, ge=1, le=20)):
    context = current_session(request)
    with connection() as conn:
        membership(conn, org_id, context.user_id)
        prop = get_property_for_organization(conn, org_id, property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        rows = list_scan_report_rows(conn, property_id, limit)
    return {"reports": [dict(row) for row in rows], "retainedPerProperty": SCAN_REPORTS_PER_PROPERTY}


@app.get("/v1/organizations/{org_id}/properties/{property_id}/scans/{report_id}")
def get_scan_report(org_id: str, property_id: str, report_id: str, request: Request):
    context = current_session(request)
    with connection() as conn:
        membership(conn, org_id, context.user_id)
        row = get_scan_report_row(conn, org_id, property_id, report_id)
    if not row:
        raise HTTPException(status_code=404, detail="Scan report not found")
    result = dict(row)
    result["report"] = json.loads(result.pop("report_json"))
    return result


@app.delete("/v1/organizations/{org_id}/properties/{property_id}/scans/{report_id}")
def delete_scan_report(org_id: str, property_id: str, report_id: str, request: Request,
                       x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    with transaction() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin", "editor"})
        prop = get_property_for_organization(conn, org_id, property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        deleted = delete_scan_report_row(conn, property_id, report_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Scan report not found")
        audit(conn, org_id, context.user_id, "scan.deleted", "scan_report", report_id)
    return {"deleted": True}


@app.post("/v1/organizations/{org_id}/properties/{property_id}/policies", status_code=status.HTTP_201_CREATED)
def create_policy_draft(org_id: str, property_id: str, body: PolicyBody, request: Request,
                        x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    with transaction() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin", "editor"})
        prop = get_property_channel(conn, org_id, property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        conn.lock_property(property_id)
        policy = validate_policy(body.policy, property_id, prop["channel"])
        if body.expectedRevision is not None:
            raise HTTPException(status_code=422, detail="expectedRevision is only valid when updating a draft")
        version = next_policy_version(conn, property_id)
        policy_id = secrets.token_hex(16)
        policy["policyVersion"] = str(version)
        insert_policy_draft(
            conn, policy_id, property_id, version, context.user_id,
            json.dumps(policy, ensure_ascii=False, separators=(",", ":")), now,
        )
        audit(conn, org_id, context.user_id, "policy.draft_created", "policy", policy_id,
              {"version": version, "channel": prop["channel"]})
    return {"id": policy_id, "propertyId": property_id, "version": version, "status": "draft"}


@app.get("/v1/organizations/{org_id}/properties/{property_id}/policies")
def list_property_policies(org_id: str, property_id: str, request: Request):
    context = current_session(request)
    with connection() as conn:
        membership(conn, org_id, context.user_id)
        prop = get_property_for_organization(conn, org_id, property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        rows = list_property_policy_rows(conn, property_id)
    return {"policies": [dict(row) for row in rows]}


@app.put("/v1/organizations/{org_id}/policies/{policy_id}")
def update_policy_draft(org_id: str, policy_id: str, body: PolicyBody, request: Request,
                        x_aman_csrf: Optional[str] = Header(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    with transaction() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin", "editor"})
        row = get_policy_for_draft_update(conn, policy_id, org_id)
        if not row:
            raise HTTPException(status_code=404, detail="Policy not found")
        conn.lock_property(row["property_id"])
        row = get_policy_for_draft_update(conn, policy_id, org_id)
        if not row:
            raise HTTPException(status_code=404, detail="Policy not found")
        if row["status"] != "draft":
            raise HTTPException(status_code=409, detail="Published policy versions are immutable")
        if body.expectedRevision is None:
            raise HTTPException(status_code=428, detail="expectedRevision is required when updating a draft")
        if row["revision"] != body.expectedRevision:
            raise HTTPException(status_code=409, detail="This draft changed since it was opened; reload it before saving")
        policy = validate_policy(body.policy, row["property_id"], row["channel"])
        policy["policyVersion"] = str(row["version"])
        updated = persist_policy_draft_update(
            conn, policy_id, body.expectedRevision, context.user_id,
            json.dumps(policy, ensure_ascii=False, separators=(",", ":")),
        )
        if updated != 1:
            raise HTTPException(status_code=409, detail="This draft changed while it was being saved; reload it")
        audit(conn, org_id, context.user_id, "policy.draft_updated", "policy", policy_id,
              {"version": row["version"], "revision": row["revision"] + 1, "updatedAt": now})
    return {"id": policy_id, "version": row["version"], "revision": row["revision"] + 1, "status": "draft"}


@app.get("/v1/organizations/{org_id}/policies/{policy_id}")
def get_policy(org_id: str, policy_id: str, request: Request):
    context = current_session(request)
    with connection() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin", "editor", "viewer"})
        row = get_policy_for_organization(conn, policy_id, org_id)
    if not row:
        raise HTTPException(status_code=404, detail="Policy not found")
    return {**dict(row), "policy": json.loads(row["body"])}


@app.post("/v1/organizations/{org_id}/policies/{policy_id}/publish")
def publish_policy(org_id: str, policy_id: str, request: Request,
                   x_aman_csrf: Optional[str] = Header(default=None),
                   body: Optional[PublishPolicyBody] = Body(default=None)):
    context = current_session(request)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    with transaction() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin"})
        row = get_policy_for_publication(conn, policy_id, org_id)
        if not row:
            raise HTTPException(status_code=404, detail="Policy not found")
        conn.lock_property(row["property_id"])
        row = get_policy_for_publication(conn, policy_id, org_id)
        if not row:
            raise HTTPException(status_code=404, detail="Policy not found")
        if row["status"] != "draft":
            raise HTTPException(status_code=409, detail="Only a draft can be published")
        requires_second_person = row["require_two_person_publish"] or row["environment"] == "production"
        last_editor_id = row["last_edited_by"] or row["created_by"]
        if requires_second_person and last_editor_id == context.user_id:
            raise HTTPException(status_code=409, detail="A different owner or administrator must publish after the last draft edit")
        if body is None:
            raise HTTPException(status_code=422, detail="A publication reason is required for the audit record")
        current = get_published_policy_id(conn, row["property_id"])
        if current:
            retire_policy(conn, current["id"])
        policy_body = get_policy_body(conn, policy_id)
        policy_body = json.loads(policy_body)
        policy_body["status"] = "published"
        mark_policy_published(
            conn, policy_id, json.dumps(policy_body, ensure_ascii=False, separators=(",", ":")),
            context.user_id, now,
        )
        audit(conn, org_id, context.user_id, "policy.published", "policy", policy_id,
              {"version": row["version"], "channel": row["channel"], "previousPolicyId": current["id"] if current else None,
               "reason": body.reason})
    return {"id": policy_id, "propertyId": row["property_id"], "version": row["version"],
            "status": "published", "publishedAt": now}


@app.get("/v1/organizations/{org_id}/audit")
def list_audit(org_id: str, request: Request, limit: int = 100):
    context = current_session(request)
    with connection() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin", "editor", "viewer"})
        rows = list_audit_events(conn, org_id, max(1, min(limit, 500)))
    return {"events": [
        {**dict(row), "details": json.loads(row["details"])} for row in rows
    ]}


def audit_csv_cell(value: Any) -> str:
    """Keep exported cells from being interpreted as spreadsheet formulas."""
    text = "" if value is None else str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


@app.get("/v1/organizations/{org_id}/audit/export")
def export_audit(
    org_id: str,
    request: Request,
    start: Optional[int] = Query(default=None, alias="from", ge=0),
    end: Optional[int] = Query(default=None, alias="to", ge=0),
    limit: int = Query(default=10_000, ge=1, le=10_000),
):
    context = current_session(request)
    with connection() as conn:
        role = membership(conn, org_id, context.user_id)
        require_role(role, {"owner", "admin", "editor", "viewer"})
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=422, detail="The 'from' timestamp must be before or equal to 'to'")

    def csv_rows():
        yield "\ufeff"
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(["event_id", "occurred_at_epoch", "actor_user_id", "actor_email", "action",
                         "resource_type", "resource_id", "details_json"])
        yield buffer.getvalue()
        buffer.close()

        with connection() as conn:
            for row in iter_audit_export_events(conn, org_id, start, end, limit):
                buffer = io.StringIO(newline="")
                writer = csv.writer(buffer, lineterminator="\r\n")
                details = json.dumps(json.loads(row["details"]), ensure_ascii=False, separators=(",", ":"))
                writer.writerow([audit_csv_cell(row[key]) for key in
                                 ("id", "occurred_at", "actor_user_id", "actor_email", "action", "resource_type", "resource_id")] +
                                [audit_csv_cell(details)])
                yield buffer.getvalue()
                buffer.close()

    return StreamingResponse(
        csv_rows(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="aman-audit-{org_id}.csv"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/v1/public/properties/{property_id}/policy")
def get_published_policy(property_id: str, request: Request, if_none_match: Optional[str] = Header(default=None)):
    with connection() as conn:
        row = load_published_policy(conn, property_id)
    if not row:
        raise HTTPException(status_code=404, detail="No published policy")
    etag = '"' + digest(row["body"])[:32] + '"'
    if if_none_match and hmac.compare_digest(if_none_match, etag):
        return Response(status_code=304, headers={"ETag": etag, "Cache-Control": "public, max-age=30"})
    return Response(content=row["body"], media_type="application/json",
                    headers={"ETag": etag, "Cache-Control": "public, max-age=30"})


@app.post("/v1/public/properties/{property_id}/consent-events")
def record_consent_event(property_id: str, body: ConsentEventBody, request: Request):
    """Record a client-reported decision without visitor or device identifiers."""
    origin = request.headers.get("origin")
    enforce_consent_event_rate_limit(request)
    now = utc_now()
    event_id_conflict = False
    duplicate_event = False
    storage_capacity_full = False
    storage_capacity_detail = ""
    storage_retry_after = 1
    with transaction() as conn:
        row = conn.execute(
            "SELECT pr.org_id,pr.channel,pr.origin,p.body FROM properties pr JOIN policies p ON p.property_id=pr.id "
            "WHERE pr.id=? AND p.status='published'",
            (property_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No published policy")
        if row["channel"] == "web":
            if not origin or origin != row["origin"]:
                raise HTTPException(status_code=403, detail="Consent event origin does not match this web property")
        elif origin:
            raise HTTPException(status_code=403, detail="Native consent events must not send a browser Origin header")
        policy = json.loads(row["body"])
        if body.channel != row["channel"]:
            raise HTTPException(status_code=422, detail="Consent event channel does not match this property")
        if body.policyVersion != policy["policyVersion"]:
            raise HTTPException(status_code=409, detail="Consent event policy version is no longer current")
        if len(body.purposes) > 64:
            raise HTTPException(status_code=422, detail="Too many purpose decisions")
        configured = {purpose["id"]: purpose for purpose in policy["purposes"]
                      if body.channel in purpose["channels"]}
        if set(body.purposes) != set(configured):
            raise HTTPException(status_code=422, detail="Consent event purposes do not match the published policy")
        if any(configured[purpose_id]["required"] and not allowed
               for purpose_id, allowed in body.purposes.items()):
            raise HTTPException(status_code=422, detail="Required purposes cannot be refused")
        optional_values = [body.purposes[purpose_id] for purpose_id, purpose in configured.items()
                           if not purpose["required"]]
        if body.action == "accept_all" and not all(optional_values):
            raise HTTPException(status_code=422, detail="accept_all must enable every optional purpose")
        if body.action == "reject_all" and any(optional_values):
            raise HTTPException(status_code=422, detail="reject_all must disable every optional purpose")

        enforce_consent_event_rate_limit(request, property_id, transaction_connection=conn)
        # Serialize global and per-property capacity checks across PostgreSQL workers.
        conn.lock_rate_limit_scope("consent_event_storage")

        purposes_json = json.dumps(body.purposes, sort_keys=True, separators=(",", ":"))
        existing = conn.execute("SELECT * FROM consent_events WHERE event_id=?", (body.eventId,)).fetchone()
        if existing:
            same_event = (
                existing["property_id"] == property_id
                and existing["policy_version"] == body.policyVersion
                and existing["channel"] == body.channel
                and existing["action"] == body.action
                and existing["purposes"] == purposes_json
            )
            if not same_event:
                event_id_conflict = True
            else:
                duplicate_event = True
        else:
            conn.execute("DELETE FROM consent_events WHERE expires_at <= ?", (now,))
            # Tenant quotas first, so one saturated property or organization reports its own
            # limit; the global emergency bound applies only when every tenant is within quota.
            scopes = (
                ("property", "WHERE property_id=? AND expires_at>?", (property_id, now),
                 CONSENT_EVENT_ACTIVE_PROPERTY_LIMIT),
                ("organization",
                 "WHERE property_id IN (SELECT id FROM properties WHERE org_id=?) AND expires_at>?",
                 (row["org_id"], now), CONSENT_EVENT_ACTIVE_ORGANIZATION_LIMIT),
                ("global", "WHERE expires_at>?", (now,), CONSENT_EVENT_ACTIVE_TOTAL_LIMIT),
            )
            for scope_name, where, parameters, limit in scopes:
                count = conn.execute(
                    f"SELECT COUNT(*) AS event_count FROM consent_events {where}", parameters
                ).fetchone()["event_count"]
                if scope_name == "global":
                    previous_level = consent_event_capacity_level(count)
                    next_level = consent_event_capacity_level(count + 1)
                    if previous_level == "ok" and next_level == "warning":
                        LOGGER.warning("Consent event storage reached %s%% of its emergency limit",
                                       CONSENT_EVENT_CAPACITY_WARNING_PERCENT)
                if count < limit:
                    continue
                storage_capacity_full = True
                first_expiry = conn.execute(
                    f"SELECT MIN(expires_at) AS first_expiry FROM consent_events {where}", parameters
                ).fetchone()["first_expiry"]
                storage_retry_after = max(1, int(first_expiry) - now) if first_expiry is not None else 60
                if scope_name == "global":
                    LOGGER.error("Consent event storage reached its emergency limit; all properties refuse new events")
                    storage_capacity_detail = (
                        "Consent event storage reached its global emergency limit; retry after the indicated time"
                    )
                else:
                    storage_capacity_detail = (
                        f"This {scope_name} reached its active consent event quota; retry after the indicated time"
                    )
                break
            if not storage_capacity_full:
                conn.execute(
                    "INSERT INTO consent_events(event_id,property_id,policy_version,channel,action,purposes,recorded_at,expires_at) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (body.eventId, property_id, body.policyVersion, body.channel, body.action, purposes_json,
                     now, now + int(policy["retentionDays"]) * 86_400),
                )
    if event_id_conflict:
        # Raise after commit so the valid conflicting attempt remains charged to the property quota.
        raise HTTPException(status_code=409, detail="Consent event identifier was already used")
    if storage_capacity_full:
        raise HTTPException(
            status_code=503,
            detail=storage_capacity_detail,
            headers={"Retry-After": str(storage_retry_after)},
        )
    if duplicate_event:
        return {"recorded": False, "duplicate": True}
    return {"recorded": True, "duplicate": False, "recordedAt": now}


@app.get("/v1/organizations/{org_id}/properties/{property_id}/consent-metrics")
def consent_metrics(org_id: str, property_id: str, request: Request,
                    days: int = Query(default=30, ge=1, le=180)):
    """Return organization-scoped aggregate counts, never individual decisions."""
    context = current_session(request)
    since = utc_now() - days * 86_400
    with connection() as conn:
        membership(conn, org_id, context.user_id)
        prop = get_property_for_organization(conn, org_id, property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        now = utc_now()
        rows, policy_labels = load_consent_metric_sources(conn, property_id, since, now)
        active_event_count = conn.execute(
            "SELECT COUNT(*) AS event_count FROM consent_events WHERE property_id=? AND expires_at>?",
            (property_id, now),
        ).fetchone()["event_count"]
    purpose_counts: Dict[Tuple[str, str], Dict[str, int]] = {}
    for row in rows:
        for purpose_id, allowed in json.loads(row["purposes"]).items():
            key = (row["policy_version"], purpose_id)
            counts = purpose_counts.setdefault(key, {"allowed": 0, "declined": 0})
            counts["allowed" if allowed else "declined"] += 1
    actions = {name: sum(row["action"] == name for row in rows)
               for name in ("accept_all", "reject_all", "custom")}
    total = len(rows)
    return {
        "propertyId": property_id,
        "channel": prop["channel"],
        "periodDays": days,
        "decisionCount": total,
        "activeEventCount": active_event_count,
        "activeEventLimit": CONSENT_EVENT_ACTIVE_PROPERTY_LIMIT,
        "actions": actions,
        "purposes": [
            {
                "policyVersion": version,
                "purposeId": purpose_id,
                "purposeLabelFr": policy_labels.get(version, {}).get(purpose_id, {}).get("fr"),
                "purposeLabelAr": policy_labels.get(version, {}).get(purpose_id, {}).get("ar"),
                **counts,
            }
            for (version, purpose_id), counts in sorted(purpose_counts.items())
        ],
        "firstRecordedAt": rows[-1]["recorded_at"] if rows else None,
        "lastRecordedAt": rows[0]["recorded_at"] if rows else None,
    }


@app.get("/v1/organizations/{org_id}/consent-metrics")
def organization_consent_metrics(org_id: str, request: Request,
                                 days: int = Query(default=30, ge=1, le=180)):
    """Return cross-property aggregates while preserving each property's policy labels."""
    context = current_session(request)
    now = utc_now()
    since = now - days * 86_400
    with connection() as conn:
        membership(conn, org_id, context.user_id)
        properties, events, labels, active_counts = load_organization_consent_metric_sources(
            conn, org_id, since, now
        )

    action_names = ("accept_all", "reject_all", "custom")
    by_property: Dict[str, Dict[str, Any]] = {}
    for prop in properties:
        by_property[prop["id"]] = {
            "propertyId": prop["id"],
            "propertyName": prop["name"],
            "channel": prop["channel"],
            "decisionCount": 0,
            "activeEventCount": active_counts.get(prop["id"], 0),
            "activeEventLimit": CONSENT_EVENT_ACTIVE_PROPERTY_LIMIT,
            "actions": {name: 0 for name in action_names},
            "purposes": {},
            "firstRecordedAt": None,
            "lastRecordedAt": None,
        }
    total_actions = {name: 0 for name in action_names}
    for row in events:
        item = by_property.get(row["property_id"])
        if item is None:
            continue
        item["decisionCount"] += 1
        item["actions"][row["action"]] = item["actions"].get(row["action"], 0) + 1
        total_actions[row["action"]] = total_actions.get(row["action"], 0) + 1
        item["lastRecordedAt"] = item["lastRecordedAt"] or row["recorded_at"]
        item["firstRecordedAt"] = row["recorded_at"]
        for purpose_id, allowed in json.loads(row["purposes"]).items():
            key = (str(row["policy_version"]), purpose_id)
            counts = item["purposes"].setdefault(key, {"allowed": 0, "declined": 0})
            counts["allowed" if allowed else "declined"] += 1

    output_properties = []
    for item in by_property.values():
        property_id = item["propertyId"]
        property_labels = labels.get(property_id, {})
        purposes = []
        for (version, purpose_id), counts in sorted(item["purposes"].items()):
            label = property_labels.get(version, {}).get(purpose_id, {})
            purposes.append({
                "policyVersion": version,
                "purposeId": purpose_id,
                "purposeLabelFr": label.get("fr"),
                "purposeLabelAr": label.get("ar"),
                **counts,
            })
        item["purposes"] = purposes
        output_properties.append(item)
    return {
        "organizationId": org_id,
        "periodDays": days,
        "decisionCount": len(events),
        "activeEventCount": sum(active_counts.values()),
        "activeEventLimit": CONSENT_EVENT_ACTIVE_ORGANIZATION_LIMIT,
        "actions": total_actions,
        "properties": output_properties,
    }


@app.post("/v1/organizations/{org_id}/properties/{property_id}/consent-events/export")
def export_consent_events(org_id: str, property_id: str, request: Request,
                          days: int = Query(default=30, ge=1, le=3650),
                          x_aman_csrf: Optional[str] = Header(default=None)):
    """Export retained SDK-reported decisions; this is not proof of visitor identity or display."""
    context = current_session(request)
    with connection() as conn:
        membership(conn, org_id, context.user_id)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    since = now - days * 86_400
    with transaction() as conn:
        membership(conn, org_id, context.user_id)
        prop = get_property_for_organization(conn, org_id, property_id)
        if not prop:
            raise HTTPException(status_code=404, detail="Property not found")
        matching_events = count_events_for_export(conn, property_id, since, now)
        audit(conn, org_id, context.user_id, "consent_events.export_requested", "property", property_id,
              {"periodDays": days, "eventCountAtRequest": matching_events})

    def csv_rows():
        yield "\ufeff"
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(["event_id", "received_at_epoch", "expires_at_epoch", "property_id",
                         "policy_version", "channel", "action", "purposes_json"])
        yield buffer.getvalue()
        buffer.close()

        with connection() as conn:
            cursor = iter_events_for_export(conn, property_id, since, now)
            for row in cursor:
                buffer = io.StringIO(newline="")
                writer = csv.writer(buffer, lineterminator="\r\n")
                purposes = json.dumps(json.loads(row["purposes"]), ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":"))
                writer.writerow([audit_csv_cell(row[key]) for key in
                                 ("event_id", "recorded_at", "expires_at", "property_id",
                                  "policy_version", "channel", "action")] +
                                [audit_csv_cell(purposes)])
                yield buffer.getvalue()
                buffer.close()

    return StreamingResponse(
        csv_rows(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="aman-decisions-{property_id}-{days}d.csv"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post("/v1/organizations/{org_id}/consent-events/export")
def export_organization_consent_events(org_id: str, request: Request,
                                       days: int = Query(default=30, ge=1, le=3650),
                                       x_aman_csrf: Optional[str] = Header(default=None)):
    """Export retained SDK-reported decisions across the member's organization."""
    context = current_session(request)
    with connection() as conn:
        membership(conn, org_id, context.user_id)
    require_csrf(request, context, x_aman_csrf)
    now = utc_now()
    since = now - days * 86_400
    with transaction() as conn:
        membership(conn, org_id, context.user_id)
        matching_events = count_organization_events_for_export(conn, org_id, since, now)
        audit(conn, org_id, context.user_id, "consent_events.export_requested", "organization", org_id,
              {"periodDays": days, "eventCountAtRequest": matching_events, "scope": "organization"})

    def csv_rows():
        yield "\ufeff"
        buffer = io.StringIO(newline="")
        writer = csv.writer(buffer, lineterminator="\r\n")
        writer.writerow(["event_id", "received_at_epoch", "expires_at_epoch", "property_id",
                         "property_name", "policy_version", "channel", "action", "purposes_json"])
        yield buffer.getvalue()
        buffer.close()

        with connection() as conn:
            cursor = iter_organization_events_for_export(conn, org_id, since, now)
            for row in cursor:
                buffer = io.StringIO(newline="")
                writer = csv.writer(buffer, lineterminator="\r\n")
                purposes = json.dumps(json.loads(row["purposes"]), ensure_ascii=False, sort_keys=True,
                                      separators=(",", ":"))
                writer.writerow([audit_csv_cell(row[key]) for key in
                                 ("event_id", "recorded_at", "expires_at", "property_id", "property_name",
                                  "policy_version", "channel", "action")] + [audit_csv_cell(purposes)])
                yield buffer.getvalue()
                buffer.close()

    return StreamingResponse(
        csv_rows(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="aman-decisions-{org_id}-{days}d.csv"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
