"""Client address normalization for rate limits and trusted-proxy configuration.

The API never parses forwarding headers itself. When AMAN_TRUSTED_PROXY_IPS is
set, the container entrypoint enables Uvicorn's proxy-header handling for those
peers only, and the application keeps reading ``request.client.host``.
Run this module to validate the setting and print the normalized list.
"""
from __future__ import annotations

import ipaddress
import os
import sys
from typing import Optional

IPV6_RATE_LIMIT_PREFIX = 64


def parse_trusted_proxies(raw_value: str) -> list[str]:
    """Return explicit proxy IPs/CIDRs, rejecting wildcards and malformed entries."""
    if not raw_value.strip():
        return []
    trusted = []
    for item in raw_value.split(","):
        entry = item.strip()
        if not entry:
            raise ValueError("AMAN_TRUSTED_PROXY_IPS contains an empty entry")
        if entry == "*":
            raise ValueError("AMAN_TRUSTED_PROXY_IPS must list explicit proxy addresses; '*' is not allowed")
        try:
            network = ipaddress.ip_network(entry, strict=True)
        except ValueError as error:
            raise ValueError(f"AMAN_TRUSTED_PROXY_IPS entry is not an IP address or network: {entry!r}") from error
        single_host = network.prefixlen == network.max_prefixlen and "/" not in entry
        trusted.append(str(network.network_address) if single_host else network.compressed)
    return trusted


def rate_limit_address(host: Optional[str]) -> str:
    """Group a peer address into its rate-limit bucket: IPv4 as-is, IPv6 by /64."""
    if not host:
        return "unknown"
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        return "unknown"
    if isinstance(address, ipaddress.IPv6Address):
        if address.ipv4_mapped is not None:
            return str(address.ipv4_mapped)
        return ipaddress.ip_network(f"{address}/{IPV6_RATE_LIMIT_PREFIX}", strict=False).compressed
    return str(address)


def main() -> int:
    try:
        trusted = parse_trusted_proxies(os.environ.get("AMAN_TRUSTED_PROXY_IPS", ""))
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    print(",".join(trusted))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
