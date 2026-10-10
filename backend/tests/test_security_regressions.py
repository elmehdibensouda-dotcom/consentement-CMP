"""Focused security regressions for the local Aman API."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException, Response
from starlette.requests import Request

from backend.aman_api import main as api


def make_request(
    client_ip: str = "198.51.100.10",
    *,
    cookies: str | None = None,
    extra_headers: tuple[tuple[str, str], ...] = (),
) -> Request:
    headers = [(name.lower().encode("latin-1"), value.encode("latin-1")) for name, value in extra_headers]
    if cookies:
        headers.append((b"cookie", cookies.encode("latin-1")))
    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "server": ("127.0.0.1", 8099),
            "client": (client_ip, 12345),
            "root_path": "",
            "path": "/v1/auth/login",
            "raw_path": b"/v1/auth/login",
            "query_string": b"",
            "headers": headers,
        }
    )


class SecurityFixture(unittest.TestCase):
    """Shared two-organization fixture for security regression suites."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_database_path = api.DATABASE_PATH
        api.DATABASE_PATH = Path(self.temp_dir.name) / "aman-test.sqlite3"
        api._LOGIN_FAILURES.clear()
        api._LOGIN_BLOCKED_UNTIL.clear()
        api.init_db()
        with api.transaction() as conn:
            conn.execute(
                "INSERT INTO users(id,email,password_hash,created_at,disabled) VALUES(?,?,?,?,0)",
                ("active-user", "active@example.com", api.hash_password("correct-password"), api.utc_now()),
            )
            conn.execute(
                "INSERT INTO users(id,email,password_hash,created_at,disabled) VALUES(?,?,?,?,1)",
                ("disabled-user", "disabled@example.com", api.hash_password("correct-password"), api.utc_now()),
            )
            for user_id, email in (
                ("admin-user", "admin@example.com"),
                ("editor-user", "editor@example.com"),
                ("viewer-user", "viewer@example.com"),
                ("other-owner", "other-owner@example.com"),
            ):
                conn.execute(
                    "INSERT INTO users(id,email,password_hash,created_at) VALUES(?,?,?,?)",
                    (user_id, email, api.hash_password("correct-password"), api.utc_now()),
                )
            now = api.utc_now()
            conn.execute(
                "INSERT INTO organizations(id,name,require_two_person_publish,created_at) VALUES(?,?,1,?)",
                ("org-a", "Banque A", now),
            )
            conn.execute(
                "INSERT INTO organizations(id,name,require_two_person_publish,created_at) VALUES(?,?,1,?)",
                ("org-b", "Banque B", now),
            )
            for user_id, role in (
                ("active-user", "owner"),
                ("admin-user", "admin"),
                ("editor-user", "editor"),
                ("viewer-user", "viewer"),
            ):
                conn.execute(
                    "INSERT INTO memberships(org_id,user_id,role,created_at) VALUES(?,?,?,?)",
                    ("org-a", user_id, role, now),
                )
            conn.execute(
                "INSERT INTO memberships(org_id,user_id,role,created_at) VALUES(?,?,?,?)",
                ("org-b", "other-owner", "owner", now),
            )
            conn.execute(
                "INSERT INTO properties(id,org_id,name,channel,environment,origin,created_at) VALUES(?,?,?,?,?,?,?)",
                ("property-a", "org-a", "Site A", "web", "production", "https://bank-a.example", now),
            )
            conn.execute(
                "INSERT INTO properties(id,org_id,name,channel,environment,origin,created_at) VALUES(?,?,?,?,?,?,?)",
                ("property-b", "org-b", "Site B", "web", "production", "https://bank-b.example", now),
            )
            policy = self.sample_policy("property-a", "1", "published")
            conn.execute(
                "INSERT INTO policies(id,property_id,version,revision,last_edited_by,status,body,created_by,created_at,published_by,published_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                ("published-policy", "property-a", 1, 1, "active-user", "published", json.dumps(policy), "active-user", now, "admin-user", now),
            )
            draft = self.sample_policy("property-a", "2", "draft")
            conn.execute(
                "INSERT INTO policies(id,property_id,version,revision,last_edited_by,status,body,created_by,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                ("draft-policy", "property-a", 2, 2, "active-user", "draft", json.dumps(draft), "active-user", now),
            )
            other_policy = self.sample_policy("property-b", "1", "published")
            conn.execute(
                "INSERT INTO policies(id,property_id,version,revision,last_edited_by,status,body,created_by,created_at,published_by,published_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                ("other-policy", "property-b", 1, 1, "other-owner", "published", json.dumps(other_policy), "other-owner", now, "other-owner", now),
            )

    def tearDown(self) -> None:
        api.DATABASE_PATH = self.previous_database_path
        api._LOGIN_FAILURES.clear()
        api._LOGIN_BLOCKED_UNTIL.clear()
        self.temp_dir.cleanup()

    @staticmethod
    def sample_policy(property_id: str, version: str = "draft", status: str = "draft", retention_days: int = 180) -> dict:
        notice = {
            "controllerName": "Banque fictive",
            "contact": "privacy@example.com",
            "processingReference": "démo",
            "dataCategories": ["préférences"],
            "recipients": ["aucun"],
            "transfers": ["aucun"],
        }
        return {
            "schemaVersion": 1,
            "propertyId": property_id,
            "policyVersion": version,
            "status": status,
            "languages": ["fr", "ar"],
            "defaultLanguage": "fr",
            "retentionDays": retention_days,
            "purposes": [
                {"id": "essential", "label": {"fr": "Essentiel", "ar": "أساسي"},
                 "description": {"fr": "Nécessaire", "ar": "ضروري"}, "required": True,
                 "consentRequired": False, "channels": ["web"]},
                {"id": "analytics", "label": {"fr": "Audience", "ar": "الجمهور"},
                 "description": {"fr": "Mesure", "ar": "قياس"}, "required": False,
                 "consentRequired": True, "channels": ["web"]},
            ],
            "notice": notice,
        }

    def session(self, user_id: str = "active-user") -> tuple[Request, str]:
        token = f"session-{user_id}"
        csrf = f"csrf-{user_id}"
        with api.transaction() as conn:
            conn.execute(
                "INSERT INTO sessions(token_hash,csrf_hash,user_id,expires_at,created_at) VALUES(?,?,?,?,?)",
                (api.digest(token), api.digest(csrf), user_id, api.utc_now() + 3600, api.utc_now()),
            )
        return make_request(cookies=f"{api.SESSION_COOKIE}={token}; {api.CSRF_COOKIE}={csrf}"), csrf

    def assert_http_status(self, expected: int, callback) -> HTTPException:
        with self.assertRaises(HTTPException) as raised:
            callback()
        self.assertEqual(raised.exception.status_code, expected)
        return raised.exception


class SecurityRegressionTests(SecurityFixture):
    def test_login_failure_runs_one_password_kdf_for_known_missing_and_disabled_users(self) -> None:
        results = []
        emails = ("active@example.com", "missing@example.com", "disabled@example.com")
        for index, email in enumerate(emails, start=10):
            with patch.object(api, "check_password", wraps=api.check_password) as check:
                with self.assertRaises(HTTPException) as raised:
                    api.login(
                        api.LoginBody(email=email, password="wrong-password"),
                        make_request(f"198.51.100.{index}"),
                        Response(),
                    )
            results.append((raised.exception.status_code, raised.exception.detail, check.call_count))

        self.assertEqual(
            results,
            [(401, "Email or password is incorrect", 1)] * len(emails),
        )

    def test_new_database_and_wal_sidecars_are_private_without_changing_process_umask(self) -> None:
        old_umask = os.umask(0o022)
        try:
            conn = api.db_connect()
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("CREATE TABLE permission_probe (value INTEGER)")
            conn.execute("INSERT INTO permission_probe VALUES (1)")
            database_mode = api.DATABASE_PATH.stat().st_mode & 0o777
            sidecar_modes = {
                path.name: path.stat().st_mode & 0o777
                for path in api.DATABASE_PATH.parent.glob(api.DATABASE_PATH.name + "-*")
            }
            conn.close()
            self.assertEqual(os.umask(0o022), 0o022)
        finally:
            os.umask(old_umask)

        self.assertEqual(database_mode, 0o600)
        self.assertEqual(set(sidecar_modes.values()), {0o600})

    def test_existing_database_permissions_are_not_changed(self) -> None:
        api.DATABASE_PATH = Path(self.temp_dir.name) / "legacy.sqlite3"
        old_umask = os.umask(0o022)
        try:
            fd = os.open(api.DATABASE_PATH, os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o644)
            os.close(fd)
            os.chmod(api.DATABASE_PATH, 0o644)
            conn = api.db_connect()
            conn.close()
            mode = api.DATABASE_PATH.stat().st_mode & 0o777
        finally:
            os.umask(old_umask)

        self.assertEqual(mode, 0o644)

    def test_database_symlink_is_rejected(self) -> None:
        api.DATABASE_PATH = Path(self.temp_dir.name) / "aliased.sqlite3"
        target = Path(self.temp_dir.name) / "target.sqlite3"
        target.write_bytes(b"")
        api.DATABASE_PATH.symlink_to(target)

        with self.assertRaisesRegex(PermissionError, "regular file"):
            api.db_connect()

    def test_group_or_world_writable_non_sticky_database_directory_is_rejected(self) -> None:
        shared_dir = Path(self.temp_dir.name) / "shared"
        shared_dir.mkdir()
        shared_dir.chmod(0o777)
        api.DATABASE_PATH = shared_dir / "aman.sqlite3"

        try:
            with self.assertRaisesRegex(PermissionError, "private directory"):
                api.db_connect()
        finally:
            shared_dir.chmod(0o700)

    def test_missing_scrypt_fails_startup_and_password_check_returns_false(self) -> None:
        async def run_lifespan() -> None:
            async with api.lifespan(None):
                self.fail("The API must not start without hashlib.scrypt")

        with patch.object(api, "hashlib", SimpleNamespace()):
            with self.assertRaisesRegex(RuntimeError, "hashlib.scrypt"):
                asyncio.run(run_lifespan())
            self.assertFalse(api.check_password("wrong-password", "scrypt$00112233445566778899aabbccddeeff$" + "0" * 128))

    def test_csrf_rejects_missing_mismatched_and_forged_tokens(self) -> None:
        request, csrf = self.session()
        context = api.current_session(request)
        self.assert_http_status(403, lambda: api.require_csrf(make_request(), context, None))
        self.assert_http_status(403, lambda: api.require_csrf(request, context, "wrong-token"))
        forged = make_request(cookies=f"{api.CSRF_COOKIE}=attacker-token")
        self.assert_http_status(403, lambda: api.require_csrf(forged, context, "attacker-token"))
        api.require_csrf(request, context, csrf)

    def test_viewer_and_editor_cannot_run_reserved_mutations(self) -> None:
        viewer_request, viewer_csrf = self.session("viewer-user")
        self.assert_http_status(
            403,
            lambda: api.create_property(
                "org-a", api.PropertyBody(name="New site", channel="ios"), viewer_request, viewer_csrf
            ),
        )
        editor_request, editor_csrf = self.session("editor-user")
        self.assert_http_status(
            403,
            lambda: api.update_member_role(
                "org-a", "viewer-user", api.MemberRoleBody(role="admin"), editor_request, editor_csrf
            ),
        )
        self.assert_http_status(
            403,
            lambda: api.publish_policy("org-a", "draft-policy", editor_request, editor_csrf),
        )

    def test_tenant_scoped_routes_return_not_found_for_non_member(self) -> None:
        request, csrf = self.session()
        empty_policy = api.PolicyBody(policy={})
        scan_report = api.ScanReportBody(
            schema="aman-local-inventory-v1",
            scannedAt="2026-10-05T12:00:00Z",
            page="https://bank-b.example/",
            scope="current-page-only; no network upload",
            limitations=[],
            cookies=[],
            resources=[],
        )
        calls = [
            lambda: api.invite_member("org-b", api.InviteBody(email="new@example.com", role="viewer"), request, csrf),
            lambda: api.list_invitations("org-b", request),
            lambda: api.revoke_invitation("org-b", "missing-invite", request, csrf),
            lambda: api.list_members("org-b", request),
            lambda: api.update_member_role("org-b", "other-owner", api.MemberRoleBody(role="viewer"), request, csrf),
            lambda: api.remove_member("org-b", "other-owner", request, csrf),
            lambda: api.create_ownership_transfer("org-b", api.OwnershipTransferBody(proposedOwnerId="other-owner"), request, csrf),
            lambda: api.get_pending_ownership_transfer("org-b", request),
            lambda: api.revoke_pending_ownership_transfer("org-b", request, csrf),
            lambda: api.create_property("org-b", api.PropertyBody(name="New iOS", channel="ios"), request, csrf),
            lambda: api.list_properties("org-b", request),
            lambda: api.update_property_origin("org-b", "property-b", api.PropertyOriginBody(origin="https://bank-b.example"), request, csrf),
            lambda: api.import_scan_report("org-b", "property-b", scan_report, request, csrf),
            lambda: api.list_scan_reports("org-b", "property-b", request, limit=10),
            lambda: api.get_scan_report("org-b", "property-b", "missing-report", request),
            lambda: api.delete_scan_report("org-b", "property-b", "missing-report", request, csrf),
            lambda: api.create_policy_draft("org-b", "property-b", empty_policy, request, csrf),
            lambda: api.list_property_policies("org-b", "property-b", request),
            lambda: api.update_policy_draft("org-b", "other-policy", empty_policy, request, csrf),
            lambda: api.get_policy("org-b", "other-policy", request),
            lambda: api.publish_policy("org-b", "other-policy", request, csrf),
            lambda: api.list_audit("org-b", request),
            lambda: api.export_audit("org-b", request, None, None, 100),
            lambda: api.consent_metrics("org-b", "property-b", request, days=30),
            lambda: api.export_consent_events("org-b", "property-b", request, days=30),
        ]
        self.assertEqual(len(calls), 25)
        for index, call in enumerate(calls):
            with self.subTest(route=index):
                self.assert_http_status(404, call)

    def test_two_person_publish_blocks_self_publication(self) -> None:
        request, csrf = self.session()
        self.assert_http_status(
            409,
            lambda: api.publish_policy("org-a", "draft-policy", request, csrf),
        )

    def test_published_policy_is_immutable_and_stale_revision_conflicts(self) -> None:
        request, csrf = self.session()
        self.assert_http_status(
            409,
            lambda: api.update_policy_draft(
                "org-a", "published-policy", api.PolicyBody(policy={}), request, csrf
            ),
        )
        self.assert_http_status(
            409,
            lambda: api.update_policy_draft(
                "org-a", "draft-policy",
                api.PolicyBody(policy=self.sample_policy("property-a", "draft", "draft"), expectedRevision=1),
                request, csrf,
            ),
        )

    def test_web_cookie_retention_over_180_days_is_rejected(self) -> None:
        policy = self.sample_policy("property-a", retention_days=181)
        self.assert_http_status(
            422,
            lambda: api.validate_policy(policy, "property-a", "web"),
        )
        self.assertEqual(api.validate_policy(self.sample_policy("property-a", retention_days=180), "property-a", "web")["retentionDays"], 180)

    def test_web_property_origin_rejects_userinfo_paths_and_non_loopback_http(self) -> None:
        for value in ("https://user:pass@bank.example", "https://bank.example/private", "http://bank.example"):
            with self.subTest(origin=value):
                self.assert_http_status(422, lambda: api.canonical_property_origin(value))

    def test_consent_event_rejects_invalid_reject_all_unknown_stale_and_missing_purposes(self) -> None:
        base = {"eventId": str(uuid4()), "policyVersion": "1", "channel": "web", "action": "reject_all"}
        request = make_request(extra_headers=(("origin", "https://bank-a.example"),))
        reject_with_optional_true = api.ConsentEventBody(**base, purposes={"essential": True, "analytics": True})
        self.assert_http_status(422, lambda: api.record_consent_event("property-a", reject_with_optional_true, request))
        unknown = api.ConsentEventBody(**{**base, "eventId": str(uuid4())}, purposes={"essential": True, "analytics": False, "other": False})
        self.assert_http_status(422, lambda: api.record_consent_event("property-a", unknown, request))
        stale = api.ConsentEventBody(**{**base, "eventId": str(uuid4()), "policyVersion": "old"}, purposes={"essential": True, "analytics": False})
        self.assert_http_status(409, lambda: api.record_consent_event("property-a", stale, request))
        missing = api.ConsentEventBody(**{**base, "eventId": str(uuid4())}, purposes={"essential": True})
        self.assert_http_status(422, lambda: api.record_consent_event("property-a", missing, request))

    def test_invalid_consent_requests_do_not_consume_property_rate_limit(self) -> None:
        def bucket_count(scope: str, value: str) -> int:
            bucket_hash = api.rate_limit_hash(scope, value)
            with api.connection() as conn:
                row = conn.execute(
                    "SELECT request_count FROM rate_limit_buckets WHERE scope=? AND bucket_hash=?",
                    (scope, bucket_hash),
                ).fetchone()
            return row["request_count"] if row else 0

        def body() -> api.ConsentEventBody:
            return api.ConsentEventBody(
                eventId=str(uuid4()),
                policyVersion="1",
                channel="web",
                action="reject_all",
                purposes={"essential": True, "analytics": False},
            )

        wrong_origin = make_request(
            "198.51.100.21", extra_headers=(("origin", "https://attacker.example"),)
        )
        self.assert_http_status(403, lambda: api.record_consent_event("property-a", body(), wrong_origin))
        self.assertEqual(bucket_count("consent_client", "198.51.100.21"), 1)
        self.assertEqual(bucket_count("consent_property", "property-a"), 0)

        unknown_property = make_request(
            "198.51.100.22", extra_headers=(("origin", "https://bank-a.example"),)
        )
        self.assert_http_status(
            404, lambda: api.record_consent_event("unknown-property", body(), unknown_property)
        )
        self.assertEqual(bucket_count("consent_client", "198.51.100.22"), 1)
        self.assertEqual(bucket_count("consent_property", "unknown-property"), 0)

        valid_request = make_request(
            "198.51.100.23", extra_headers=(("origin", "https://bank-a.example"),)
        )
        self.assertEqual(api.record_consent_event("property-a", body(), valid_request)["recorded"], True)
        self.assertEqual(bucket_count("consent_client", "198.51.100.23"), 1)
        self.assertEqual(bucket_count("consent_property", "property-a"), 1)

    def test_consent_event_id_cannot_be_reused_with_different_values(self) -> None:
        def property_bucket_count() -> int:
            bucket_hash = api.rate_limit_hash("consent_property", "property-a")
            with api.connection() as conn:
                row = conn.execute(
                    "SELECT request_count FROM rate_limit_buckets WHERE scope=? AND bucket_hash=?",
                    ("consent_property", bucket_hash),
                ).fetchone()
            return row["request_count"] if row else 0

        event_id = str(uuid4())
        request = make_request(extra_headers=(("origin", "https://bank-a.example"),))
        first = api.ConsentEventBody(
            eventId=event_id, policyVersion="1", channel="web", action="reject_all",
            purposes={"essential": True, "analytics": False},
        )
        changed = api.ConsentEventBody(
            eventId=event_id, policyVersion="1", channel="web", action="custom",
            purposes={"essential": True, "analytics": True},
        )
        self.assertEqual(api.record_consent_event("property-a", first, request)["recorded"], True)
        self.assertEqual(property_bucket_count(), 1)
        self.assert_http_status(409, lambda: api.record_consent_event("property-a", changed, request))
        self.assertEqual(property_bucket_count(), 2)

    def test_logout_invalidates_session(self) -> None:
        request, csrf = self.session()
        self.assertEqual(api.logout(request, Response(), csrf), {"ok": True})
        self.assert_http_status(401, lambda: api.current_session(request))


if __name__ == "__main__":
    unittest.main()
