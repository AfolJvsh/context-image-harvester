import io
import socket

import numpy as np
from PIL import Image

from context_image_harvester.downloader import CandidateDownloader
from context_image_harvester.metrics import Metrics
from context_image_harvester.models import Candidate


class FakeResponse:
    status_code = 200
    headers = {"Content-Type": "image/jpeg"}

    def __init__(self, blob):
        self.blob = blob

    def raise_for_status(self):
        return None

    def iter_content(self, _):
        yield self.blob

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FakeSession:
    def __init__(self, response):
        self.response = response

    def get(self, *args, **kwargs):
        return self.response


def jpeg_bytes(size=(1200, 800)):
    buf = io.BytesIO()
    rng = np.random.default_rng(42)
    pixels = rng.integers(0, 256, size=(size[1], size[0], 3), dtype=np.uint8)
    Image.fromarray(pixels, "RGB").save(buf, "JPEG", quality=90)
    return buf.getvalue()


def test_downloader_accepts_valid_public_image(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))
    ])
    blob = jpeg_bytes()
    downloader = CandidateDownloader(
        FakeSession(FakeResponse(blob)), Metrics(), timeout=5, max_download_bytes=5_000_000, max_pixels=5_000_000
    )
    candidate = Candidate("pexels", "photo", "", "https://example.test/a.jpg", "https://example.test")
    result = downloader.prepare(candidate)
    assert result.reason is None
    assert result.prepared is not None
    assert result.prepared.width == 1200


def test_downloader_rejects_private_url(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *args, **kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.10", 443))
    ])
    downloader = CandidateDownloader(
        FakeSession(FakeResponse(jpeg_bytes())), Metrics(), timeout=5, max_download_bytes=5_000_000, max_pixels=5_000_000
    )
    candidate = Candidate("serpapi-google", "", "", "https://internal.test/a.jpg", "")
    result = downloader.prepare(candidate)
    assert result.prepared is None
    assert result.reason == "unsafe_url"
