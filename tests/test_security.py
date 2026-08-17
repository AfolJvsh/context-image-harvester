import socket

import pytest

from context_image_harvester.security import UnsafeURL, validate_public_http_url


def test_rejects_non_http_scheme():
    with pytest.raises(UnsafeURL):
        validate_public_http_url("file:///etc/passwd")


def test_rejects_private_resolution(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 80))
    ])
    with pytest.raises(UnsafeURL):
        validate_public_http_url("http://example.test/image.jpg")


def test_accepts_public_resolution(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
    ])
    assert validate_public_http_url("https://example.test/image.jpg").startswith("https://")
