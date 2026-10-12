"""Consent-event admission quotas: tenant isolation and the global emergency cap."""
from __future__ import annotations

import unittest
from unittest.mock import patch
from uuid import uuid4

from fastapi import HTTPException

from backend.aman_api import main as api
from test_security_regressions import SecurityFixture, make_request


class ConsentCapacityTests(SecurityFixture):
    def event(self, event_id: str | None = None, action: str = "reject_all") -> api.ConsentEventBody:
        return api.ConsentEventBody(
            eventId=event_id or str(uuid4()), policyVersion="1", channel="web", action=action,
            purposes={"essential": True, "analytics": action == "accept_all"},
        )

    def record(self, property_id: str, body: api.ConsentEventBody, ip: str = "198.51.100.90") -> dict:
        origin = {"property-a": "https://bank-a.example", "property-b": "https://bank-b.example"}[property_id]
        return api.record_consent_event(property_id, body, make_request(ip, extra_headers=(("origin", origin),)))

    def assert_refused(self, property_id: str, status: int = 503) -> HTTPException:
        with self.assertRaises(HTTPException) as raised:
            self.record(property_id, self.event())
        self.assertEqual(raised.exception.status_code, status)
        self.assertTrue(raised.exception.headers.get("Retry-After"))
        return raised.exception

    def test_organization_over_quota_does_not_block_another_organization(self) -> None:
        with patch.object(api, "CONSENT_EVENT_ACTIVE_ORGANIZATION_LIMIT", 1):
            self.assertTrue(self.record("property-a", self.event())["recorded"])
            refused = self.assert_refused("property-a")
            self.assertIn("organization", refused.detail)
            self.assertTrue(self.record("property-b", self.event())["recorded"])

    def test_property_over_quota_does_not_block_another_organization(self) -> None:
        with patch.object(api, "CONSENT_EVENT_ACTIVE_PROPERTY_LIMIT", 1):
            self.assertTrue(self.record("property-a", self.event())["recorded"])
            self.assertIn("property", self.assert_refused("property-a").detail)
            self.assertTrue(self.record("property-b", self.event())["recorded"])

    def test_global_emergency_cap_refuses_every_property_and_logs_an_error(self) -> None:
        with patch.object(api, "CONSENT_EVENT_ACTIVE_TOTAL_LIMIT", 1):
            self.assertTrue(self.record("property-a", self.event())["recorded"])
            with self.assertLogs("aman.consent", level="ERROR"):
                refused = self.assert_refused("property-b")
            self.assertIn("emergency", refused.detail)

    def test_capacity_warning_is_logged_and_reported_before_the_global_cap(self) -> None:
        with patch.object(api, "CONSENT_EVENT_ACTIVE_TOTAL_LIMIT", 10), \
                patch.object(api, "CONSENT_EVENT_CAPACITY_WARNING_PERCENT", 20):
            self.assertTrue(self.record("property-a", self.event())["recorded"])
            self.assertEqual(api.consent_event_capacity_state(), "ok")
            with self.assertLogs("aman.consent", level="WARNING"):
                self.assertTrue(self.record("property-b", self.event())["recorded"])
            self.assertEqual(api.consent_event_capacity_state(), "warning")
            readiness = api.readiness()
            self.assertIn(b'"consentEventCapacity":"warning"', readiness.body)

    def test_expired_events_are_excluded_from_quotas_and_purged(self) -> None:
        now = api.utc_now()
        with api.transaction() as conn:
            conn.execute(
                "INSERT INTO consent_events(event_id,property_id,policy_version,channel,action,purposes,recorded_at,expires_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (str(uuid4()), "property-a", "1", "web", "reject_all", '{"analytics":false,"essential":true}',
                 now - 100, now - 1),
            )
        with patch.object(api, "CONSENT_EVENT_ACTIVE_ORGANIZATION_LIMIT", 1):
            self.assertTrue(self.record("property-a", self.event())["recorded"])
        with api.connection() as conn:
            remaining = conn.execute("SELECT COUNT(*) AS n FROM consent_events WHERE expires_at<=?", (now,)).fetchone()["n"]
        self.assertEqual(remaining, 0)

    def test_deduplication_is_unchanged(self) -> None:
        event_id = str(uuid4())
        self.assertEqual(self.record("property-a", self.event(event_id))["recorded"], True)
        self.assertEqual(self.record("property-a", self.event(event_id)), {"recorded": False, "duplicate": True})
        with self.assertRaises(HTTPException) as raised:
            self.record("property-a", self.event(event_id, action="accept_all"))
        self.assertEqual(raised.exception.status_code, 409)

    def test_quota_settings_must_be_positive_integers(self) -> None:
        for name in ("AMAN_CONSENT_EVENT_ACTIVE_ORGANIZATION_LIMIT", "AMAN_CONSENT_EVENT_CAPACITY_WARNING_PERCENT"):
            with self.subTest(name=name), patch.dict("os.environ", {name: "0"}):
                with self.assertRaises(RuntimeError):
                    api.positive_int_setting(name, 1, maximum=100 if "PERCENT" in name else None)


if __name__ == "__main__":
    unittest.main()
