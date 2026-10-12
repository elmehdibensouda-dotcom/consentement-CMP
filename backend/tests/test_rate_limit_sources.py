"""Rate-limit source, proxy trust, and per-account sign-in throttling regressions."""
from __future__ import annotations

import asyncio
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException, Response
from starlette.requests import Request
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from backend.aman_api import main as api
from backend.aman_api.client_address import parse_trusted_proxies, rate_limit_address
from test_security_regressions import SecurityFixture, make_request

ROOT = Path(__file__).resolve().parents[2]


def response_cookies(response: Response) -> dict[str, str]:
    cookies = {}
    for name, value in response.raw_headers:
        if name == b"set-cookie":
            pair = value.decode("latin-1").split(";", 1)[0]
            key, _, cookie_value = pair.partition("=")
            cookies[key] = cookie_value
    return cookies


class ClientAddressTests(unittest.TestCase):
    def test_ipv6_clients_share_a_bucket_per_64_prefix(self) -> None:
        self.assertEqual(rate_limit_address("2001:db8:1:2::1"), rate_limit_address("2001:db8:1:2:ffff:eeee:dddd:9"))
        self.assertNotEqual(rate_limit_address("2001:db8:1:2::1"), rate_limit_address("2001:db8:1:3::1"))

    def test_ipv4_mapped_ipv6_is_treated_as_the_ipv4_client(self) -> None:
        self.assertEqual(rate_limit_address("::ffff:198.51.100.7"), "198.51.100.7")
        self.assertEqual(rate_limit_address("198.51.100.7"), "198.51.100.7")
        self.assertNotEqual(rate_limit_address("::ffff:198.51.100.7"), rate_limit_address("::ffff:198.51.100.8"))

    def test_missing_or_non_ip_peer_falls_back_to_a_shared_unknown_bucket(self) -> None:
        self.assertEqual(rate_limit_address(None), "unknown")
        self.assertEqual(rate_limit_address("testclient"), "unknown")

    def test_forged_forwarded_for_is_ignored_without_a_trusted_proxy(self) -> None:
        request = make_request("198.51.100.30", extra_headers=(("x-forwarded-for", "203.0.113.99"),))
        self.assertEqual(api.client_ip(request), "198.51.100.30")

    def test_trusted_proxy_configuration_rejects_wildcards_and_malformed_entries(self) -> None:
        for value in ("*", "10.0.0.1,*", "10.0.0.1,,10.0.0.2", "10.0.0.1,", "proxy.internal", "10.0.0.1/24", "300.0.0.1"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    parse_trusted_proxies(value)

    def test_trusted_proxy_configuration_accepts_explicit_addresses_and_networks(self) -> None:
        self.assertEqual(parse_trusted_proxies(""), [])
        self.assertEqual(parse_trusted_proxies("   "), [])
        self.assertEqual(
            parse_trusted_proxies(" 10.0.0.0/8 , 192.0.2.10 ,2001:DB8::/32"),
            ["10.0.0.0/8", "192.0.2.10", "2001:db8::/32"],
        )

    def _client_ip_behind_uvicorn(self, peer: str, forwarded_for: str, trusted: str) -> str:
        seen: dict[str, str] = {}

        async def capture(scope, receive, send):
            seen["ip"] = api.client_ip(Request(scope))

        middleware = ProxyHeadersMiddleware(capture, trusted_hosts=parse_trusted_proxies(trusted))
        scope = {
            "type": "http", "http_version": "1.1", "method": "POST", "scheme": "http",
            "server": ("127.0.0.1", 8000), "client": (peer, 40000), "root_path": "",
            "path": "/v1/auth/login", "raw_path": b"/v1/auth/login", "query_string": b"",
            "headers": [(b"x-forwarded-for", forwarded_for.encode("latin-1"))],
        }
        asyncio.run(middleware(scope, None, None))
        return seen["ip"]

    def test_allowed_proxy_cidr_propagates_the_client_address_through_uvicorn(self) -> None:
        self.assertEqual(self._client_ip_behind_uvicorn("10.1.2.3", "203.0.113.5", "10.0.0.0/8"), "203.0.113.5")

    def test_untrusted_peer_cannot_supply_a_forwarded_address(self) -> None:
        self.assertEqual(self._client_ip_behind_uvicorn("198.51.100.1", "203.0.113.5", "10.0.0.0/8"), "198.51.100.1")


class ContainerProxyFlagTests(unittest.TestCase):
    """Run the staging entrypoint with a stub interpreter that echoes the Uvicorn command."""

    def run_entrypoint(self, trusted: str | None) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as directory:
            stub = Path(directory) / "python"
            stub.write_text(
                "#!/bin/sh\n"
                'if [ "$2" = "uvicorn" ]; then printf "%s\\n" "$*"; exit 0; fi\n'
                f'exec "{sys.executable}" "$@"\n'
            )
            stub.chmod(stub.stat().st_mode | stat.S_IXUSR)
            env = {
                "PATH": f"{directory}:{os.environ.get('PATH', '')}",
                "AMAN_ENVIRONMENT": "staging",
                "AMAN_DATABASE_URL": "postgresql://placeholder.invalid/aman",
                "AMAN_RATE_LIMIT_HASH_KEY": "x" * 32,
                "PYTHONPATH": str(ROOT),
            }
            if trusted is not None:
                env["AMAN_TRUSTED_PROXY_IPS"] = trusted
            return subprocess.run(
                ["sh", str(ROOT / "ops/container/entrypoint.sh"), "serve"],
                cwd=ROOT, env=env, capture_output=True, text=True, timeout=30,
            )

    def test_proxy_headers_are_disabled_without_a_trusted_proxy(self) -> None:
        result = self.run_entrypoint(None)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--no-proxy-headers", result.stdout)
        self.assertNotIn("--forwarded-allow-ips", result.stdout)

    def test_valid_trusted_proxy_enables_uvicorn_proxy_headers_for_that_network_only(self) -> None:
        result = self.run_entrypoint("10.0.0.0/8,192.0.2.10")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--proxy-headers --forwarded-allow-ips 10.0.0.0/8,192.0.2.10", result.stdout)

    def test_invalid_trusted_proxy_stops_the_container(self) -> None:
        result = self.run_entrypoint("*")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("uvicorn", result.stdout)


class SignInThrottleTests(SecurityFixture):
    def login(self, email: str, password: str, ip: str, cookies: str | None = None) -> Response:
        response = Response()
        api.login(api.LoginBody(email=email, password=password), make_request(ip, cookies=cookies), response)
        return response

    def failed_login(self, email: str, ip: str, cookies: str | None = None) -> HTTPException:
        with self.assertRaises(HTTPException) as raised:
            self.login(email, "wrong-password", ip, cookies)
        return raised.exception

    def test_failures_from_ip_a_do_not_block_a_user_signing_in_from_ip_b(self) -> None:
        for index in range(api.LOGIN_FAILURE_LIMIT):
            self.failed_login(f"spray-{index}@example.com", "198.51.100.40")
        self.assertEqual(self.failed_login("spray-x@example.com", "198.51.100.40").status_code, 429)
        self.login("active@example.com", "correct-password", "198.51.100.41")

    def test_distributed_failures_throttle_only_the_targeted_account(self) -> None:
        for index in range(api.LOGIN_ACCOUNT_FAILURE_LIMIT):
            self.failed_login("active@example.com", f"203.0.113.{index + 1}")
        with self.assertRaises(HTTPException) as raised:
            self.login("active@example.com", "correct-password", "203.0.113.200")
        self.assertEqual(raised.exception.status_code, 429)
        self.assertTrue(raised.exception.headers.get("Retry-After"))
        self.login("admin@example.com", "correct-password", "203.0.113.201")

    def test_account_throttle_does_not_reveal_whether_the_account_exists(self) -> None:
        outcomes = []
        for email in ("active@example.com", "missing@example.com"):
            for index in range(api.LOGIN_ACCOUNT_FAILURE_LIMIT):
                self.failed_login(email, f"192.0.2.{index + 1}")
            blocked = self.failed_login(email, "192.0.2.250")
            outcomes.append((blocked.status_code, blocked.detail, sorted(blocked.headers)))
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(outcomes[0][0], 429)

    def test_account_throttle_is_temporary(self) -> None:
        start = api.utc_now()
        for index in range(api.LOGIN_ACCOUNT_FAILURE_LIMIT):
            self.failed_login("active@example.com", f"203.0.113.{index + 1}")
        later = start + api.LOGIN_ACCOUNT_LOCK_SECONDS + 1
        original = api.utc_now
        api.utc_now = lambda: later
        try:
            self.login("active@example.com", "correct-password", "203.0.113.150")
        finally:
            api.utc_now = original

    def test_recognized_device_is_not_locked_out_by_third_party_failures(self) -> None:
        first = self.login("active@example.com", "correct-password", "198.51.100.60")
        device = response_cookies(first)[api.DEVICE_COOKIE]
        self.assertTrue(device)
        for index in range(api.LOGIN_ACCOUNT_FAILURE_LIMIT):
            self.failed_login("active@example.com", f"203.0.113.{index + 1}")
        self.assertEqual(self.failed_login("active@example.com", "198.51.100.61").status_code, 429)
        self.login("active@example.com", "correct-password", "198.51.100.62",
                   cookies=f"{api.DEVICE_COOKIE}={device}")

    def test_device_cookie_is_bound_to_its_account(self) -> None:
        first = self.login("admin@example.com", "correct-password", "198.51.100.70")
        device = response_cookies(first)[api.DEVICE_COOKIE]
        for index in range(api.LOGIN_ACCOUNT_FAILURE_LIMIT):
            self.failed_login("active@example.com", f"203.0.113.{index + 1}")
        with self.assertRaises(HTTPException) as raised:
            self.login("active@example.com", "correct-password", "198.51.100.71",
                       cookies=f"{api.DEVICE_COOKIE}={device}")
        self.assertEqual(raised.exception.status_code, 429)

    def test_successful_sign_in_does_not_reset_the_source_failure_counter(self) -> None:
        for index in range(api.LOGIN_FAILURE_LIMIT - 1):
            self.failed_login(f"spray-{index}@example.com", "198.51.100.80")
        self.login("active@example.com", "correct-password", "198.51.100.80")
        self.assertEqual(self.failed_login("spray-last@example.com", "198.51.100.80").status_code, 429)


if __name__ == "__main__":
    unittest.main()
