from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urljoin, urlparse


class UnsafeURL(ValueError):
    pass


def _is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def validate_public_http_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURL("only http/https URLs are allowed")
    if not parsed.hostname:
        raise UnsafeURL("URL has no hostname")
    host = parsed.hostname.rstrip(".")
    if host.lower() in {"localhost", "localhost.localdomain"}:
        raise UnsafeURL("localhost is not allowed")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, parsed.port or 443)}
    except socket.gaierror as exc:
        raise UnsafeURL(f"hostname resolution failed: {exc}") from exc
    if not addresses or any(not _is_public_ip(addr) for addr in addresses):
        raise UnsafeURL("hostname resolves to a non-public network address")
    return url


def redirect_target(current_url: str, location: str) -> str:
    return validate_public_http_url(urljoin(current_url, location))
