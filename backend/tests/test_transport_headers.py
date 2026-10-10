"""HSTS only over confirmed HTTPS, and a report-only CSP on the static console."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

from backend.aman_api import main as api


class TransportHeaderTests(unittest.TestCase):
    def get(self, base_url: str, path: str = "/health"):
        return TestClient(api.app, base_url=base_url).get(path)

    def test_hsts_is_absent_over_http(self) -> None:
        self.assertNotIn("strict-transport-security", self.get("http://testserver").headers)

    def test_hsts_is_sent_over_https_without_subdomains_by_default(self) -> None:
        header = self.get("https://testserver").headers.get("strict-transport-security")
        self.assertEqual(header, f"max-age={api.HSTS_MAX_AGE_SECONDS}")

    def test_hsts_subdomains_and_disable_switch_are_explicit(self) -> None:
        with patch.object(api, "HSTS_INCLUDE_SUBDOMAINS", True):
            self.assertEqual(
                self.get("https://testserver").headers.get("strict-transport-security"),
                f"max-age={api.HSTS_MAX_AGE_SECONDS}; includeSubDomains",
            )
        with patch.object(api, "HSTS_MAX_AGE_SECONDS", 0):
            self.assertNotIn("strict-transport-security", self.get("https://testserver").headers)

    def test_hsts_settings_reject_invalid_values(self) -> None:
        for name, value in (("AMAN_HSTS_MAX_AGE", "-1"), ("AMAN_HSTS_MAX_AGE", "soon"),
                            ("AMAN_HSTS_INCLUDE_SUBDOMAINS", "yes")):
            with self.subTest(name=name, value=value), patch.dict("os.environ", {name: value}):
                with self.assertRaises(RuntimeError):
                    api.load_hsts_settings()

    def test_console_pages_carry_a_report_only_csp_and_api_routes_do_not(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, "admin.html").write_text("<!doctype html><title>console</title>", encoding="utf-8")
            route_count = len(api.app.router.routes)
            api.app.mount("/console-csp-probe", StaticFiles(directory=directory, html=True))
            try:
                with patch.object(api, "CONSOLE_PATH_PREFIXES", ("/console-csp-probe/",)):
                    page = self.get("http://testserver", "/console-csp-probe/admin.html")
                    api_response = self.get("http://testserver", "/health")
            finally:
                del api.app.router.routes[route_count:]
        self.assertEqual(page.status_code, 200)
        policy = page.headers.get("content-security-policy-report-only", "")
        for directive in ("default-src 'self'", "script-src 'self'", "object-src 'none'", "base-uri 'none'",
                          "frame-ancestors 'none'", "form-action 'self'"):
            self.assertIn(directive, policy)
        self.assertNotIn("content-security-policy", page.headers)
        self.assertNotIn("content-security-policy-report-only", api_response.headers)


if __name__ == "__main__":
    unittest.main()
