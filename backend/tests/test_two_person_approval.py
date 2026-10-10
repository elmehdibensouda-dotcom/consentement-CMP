"""Two-person publication: weakening the rule needs a second, audited approver."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from fastapi import Response

from backend.aman_api import main as api
from test_security_regressions import SecurityFixture


class TwoPersonApprovalTests(SecurityFixture):
    def setUp(self) -> None:
        super().setUp()
        now = api.utc_now()
        with api.transaction() as conn:
            conn.execute(
                "INSERT INTO properties(id,org_id,name,channel,environment,origin,created_at) VALUES(?,?,?,?,?,?,?)",
                ("property-staging", "org-a", "Site recette", "web", "staging", "https://recette.bank-a.example", now),
            )
            draft = self.sample_policy("property-staging", "1", "draft")
            conn.execute(
                "INSERT INTO policies(id,property_id,version,revision,last_edited_by,status,body,created_by,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                ("staging-draft", "property-staging", 1, 1, "active-user", "draft", json.dumps(draft), "active-user", now),
            )

    def put_setting(self, user_id: str, enabled: bool) -> tuple[dict, int]:
        request, csrf = self.session(user_id)
        response = Response()
        result = api.update_organization_approval_settings(
            "org-a", api.OrganizationApprovalSettingsBody(requireTwoPersonPublish=enabled), request,
            response, x_aman_csrf=csrf,
        )
        return result, response.status_code

    def setting(self) -> bool:
        with api.connection() as conn:
            row = conn.execute("SELECT require_two_person_publish FROM organizations WHERE id='org-a'").fetchone()
        return bool(row["require_two_person_publish"])

    def approve(self, user_id: str, change_id: str) -> dict:
        request, csrf = self.session(user_id)
        return api.approve_approval_setting_change("org-a", change_id, request, x_aman_csrf=csrf)

    def publish(self, user_id: str, policy_id: str) -> dict:
        request, csrf = self.session(user_id)
        return api.publish_policy("org-a", policy_id, request, csrf, api.PublishPolicyBody(reason="Mise en recette"))

    def test_admin_request_to_weaken_is_pending_and_not_applied(self) -> None:
        result, status = self.put_setting("admin-user", False)
        self.assertEqual(status, 202)
        self.assertTrue(result["requireTwoPersonPublish"])
        self.assertEqual(result["pendingChange"]["requestedBy"], "admin-user")
        self.assertTrue(self.setting())

    def test_owner_cannot_weaken_then_publish_own_draft_alone(self) -> None:
        result, _ = self.put_setting("active-user", False)
        change_id = result["pendingChange"]["id"]
        self.assert_http_status(409, lambda: self.publish("active-user", "staging-draft"))
        self.assert_http_status(403, lambda: self.approve("active-user", change_id))
        self.assertTrue(self.setting())
        self.assert_http_status(409, lambda: self.publish("active-user", "staging-draft"))

    def test_second_owner_or_admin_applies_the_weakening_with_both_identities_audited(self) -> None:
        result, _ = self.put_setting("active-user", False)
        change_id = result["pendingChange"]["id"]
        self.assertEqual(self.approve("admin-user", change_id)["requireTwoPersonPublish"], False)
        self.assertFalse(self.setting())
        with api.connection() as conn:
            rows = conn.execute(
                "SELECT actor_user_id,action,details FROM audit_events WHERE org_id='org-a' "
                "AND action LIKE 'organization.approval_setting%' ORDER BY occurred_at,rowid"
            ).fetchall()
        actions = [(row["actor_user_id"], row["action"]) for row in rows]
        self.assertIn(("active-user", "organization.approval_setting_change_requested"), actions)
        self.assertIn(("admin-user", "organization.approval_setting_updated"), actions)
        applied = json.loads(next(row["details"] for row in rows if row["action"] == "organization.approval_setting_updated"))
        self.assertEqual(applied["requestedBy"], "active-user")
        self.assertEqual(applied["approvedBy"], "admin-user")

    def test_editor_and_viewer_cannot_request_or_approve(self) -> None:
        result, _ = self.put_setting("active-user", False)
        for user_id in ("editor-user", "viewer-user"):
            with self.subTest(user=user_id):
                self.assert_http_status(403, lambda: self.put_setting(user_id, False))
                self.assert_http_status(403, lambda: self.approve(user_id, result["pendingChange"]["id"]))

    def test_second_approver_who_did_not_edit_can_publish(self) -> None:
        self.assertEqual(self.publish("admin-user", "staging-draft")["status"], "published")

    def test_production_stays_protected_when_the_organization_setting_is_disabled(self) -> None:
        with api.transaction() as conn:
            conn.execute("UPDATE organizations SET require_two_person_publish=0 WHERE id='org-a'")
        self.assert_http_status(409, lambda: self.publish("active-user", "draft-policy"))
        self.assertEqual(self.publish("active-user", "staging-draft")["status"], "published")

    def test_enabling_is_immediate_and_cancels_a_pending_weakening(self) -> None:
        result, _ = self.put_setting("active-user", False)
        change_id = result["pendingChange"]["id"]
        enabled, status = self.put_setting("admin-user", True)
        self.assertEqual(status, 200)
        self.assertIsNone(enabled["pendingChange"])
        self.assert_http_status(409, lambda: self.approve("admin-user", change_id))
        with api.transaction() as conn:
            conn.execute("UPDATE organizations SET require_two_person_publish=0 WHERE id='org-a'")
        enabled, status = self.put_setting("admin-user", True)
        self.assertEqual(status, 200)
        self.assertTrue(self.setting())

    def test_pending_weakening_expires(self) -> None:
        result, _ = self.put_setting("active-user", False)
        later = api.utc_now() + api.APPROVAL_SETTING_CHANGE_TTL_SECONDS + 1
        with patch.object(api, "utc_now", lambda: later):
            self.assert_http_status(409, lambda: self.approve("admin-user", result["pendingChange"]["id"]))
        self.assertTrue(self.setting())

    def test_second_request_while_one_is_pending_conflicts(self) -> None:
        self.put_setting("active-user", False)
        self.assert_http_status(409, lambda: self.put_setting("admin-user", False))

    def test_requester_can_withdraw_a_pending_weakening(self) -> None:
        result, _ = self.put_setting("active-user", False)
        request, csrf = self.session("active-user")
        api.revoke_approval_setting_change("org-a", result["pendingChange"]["id"], request, x_aman_csrf=csrf)
        self.assert_http_status(409, lambda: self.approve("admin-user", result["pendingChange"]["id"]))
        request, _ = self.session("viewer-user")
        self.assertIsNone(api.get_organization_approval_settings("org-a", request)["pendingChange"])


if __name__ == "__main__":
    unittest.main()
