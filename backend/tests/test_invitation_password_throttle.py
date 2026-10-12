"""Invitation acceptance must not offer an unthrottled password oracle for existing accounts."""
from __future__ import annotations

import secrets
import unittest

from fastapi import HTTPException, Response

from backend.aman_api import main as api
from backend.aman_api.invitation_repository import create_invitation
from test_security_regressions import SecurityFixture, make_request


class InvitationPasswordThrottleTests(SecurityFixture):
    def invite(self, email: str, org_id: str = "org-b") -> str:
        token = secrets.token_urlsafe(40)
        with api.transaction() as conn:
            create_invitation(conn, secrets.token_hex(16), org_id, email, "viewer", api.digest(token),
                              "other-owner", api.utc_now() + 3600)
        return token

    def accept(self, token: str, password: str, ip: str) -> dict:
        return api.accept_invitation(api.AcceptInviteBody(token=token, password=password), make_request(ip))

    def test_distributed_wrong_passwords_throttle_the_invited_account(self) -> None:
        token = self.invite("active@example.com")
        for index in range(api.LOGIN_ACCOUNT_FAILURE_LIMIT):
            with self.assertRaises(HTTPException) as raised:
                self.accept(token, "wrong-password-value", f"203.0.113.{index + 1}")
            self.assertIn(raised.exception.status_code, (401, 429))
        with self.assertRaises(HTTPException) as raised:
            self.accept(token, "correct-password", "203.0.113.200")
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.detail, api.LOGIN_THROTTLED_DETAIL)

    def test_invitation_failures_share_the_sign_in_account_budget(self) -> None:
        token = self.invite("active@example.com")
        for index in range(api.LOGIN_ACCOUNT_FAILURE_LIMIT):
            with self.assertRaises(HTTPException):
                self.accept(token, "wrong-password-value", f"203.0.113.{index + 1}")
        with self.assertRaises(HTTPException) as raised:
            api.login(api.LoginBody(email="active@example.com", password="correct-password"),
                      make_request("198.51.100.150"), Response())
        self.assertEqual(raised.exception.status_code, 429)

    def test_other_accounts_remain_usable(self) -> None:
        token = self.invite("active@example.com")
        for index in range(api.LOGIN_ACCOUNT_FAILURE_LIMIT):
            with self.assertRaises(HTTPException):
                self.accept(token, "wrong-password-value", f"203.0.113.{index + 1}")
        other_token = self.invite("editor@example.com")
        self.assertEqual(self.accept(other_token, "correct-password", "203.0.113.201"),
                         {"ok": True, "accountCreated": False})
        api.login(api.LoginBody(email="admin@example.com", password="correct-password"),
                  make_request("203.0.113.202"), Response())

    def test_wrong_password_still_reports_the_existing_account_mismatch(self) -> None:
        token = self.invite("active@example.com")
        with self.assertRaises(HTTPException) as raised:
            self.accept(token, "wrong-password-value", "203.0.113.50")
        self.assertEqual(raised.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
