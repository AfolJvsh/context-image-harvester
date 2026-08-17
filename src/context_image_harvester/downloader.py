from __future__ import annotations

import hashlib
import io
import tempfile
import warnings
from dataclasses import dataclass

import requests
from PIL import Image, ImageOps, UnidentifiedImageError

from .hashing import phash
from .metrics import Metrics
from .models import Candidate, PreparedCandidate
from .security import UnsafeURL, redirect_target, validate_public_http_url

ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}


@dataclass(slots=True)
class DownloadResult:
    prepared: PreparedCandidate | None
    reason: str | None = None


class CandidateDownloader:
    def __init__(
        self,
        session: requests.Session,
        metrics: Metrics,
        timeout: int,
        max_download_bytes: int,
        max_pixels: int,
        redirect_limit: int = 5,
    ):
        self.session = session
        self.metrics = metrics
        self.timeout = timeout
        self.max_download_bytes = max_download_bytes
        self.max_pixels = max_pixels
        self.redirect_limit = redirect_limit

    def _get(self, url: str) -> requests.Response:
        current = validate_public_http_url(url)
        for _ in range(self.redirect_limit + 1):
            response = self.session.get(
                current,
                timeout=self.timeout,
                stream=True,
                allow_redirects=False,
            )
            if response.status_code in {301, 302, 303, 307, 308}:
                location = response.headers.get("Location")
                response.close()
                if not location:
                    raise UnsafeURL("redirect without Location header")
                current = redirect_target(current, location)
                continue
            response.raise_for_status()
            return response
        raise UnsafeURL("too many redirects")

    def prepare(self, candidate: Candidate) -> DownloadResult:
        try:
            response = self._get(candidate.image_url)
        except UnsafeURL:
            return DownloadResult(None, "unsafe_url")
        except requests.Timeout:
            return DownloadResult(None, "timeout")
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else 0
            return DownloadResult(None, f"http_{code or 'error'}")
        except requests.RequestException:
            return DownloadResult(None, "network_error")

        with response:
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type and content_type not in ALLOWED_MIME:
                return DownloadResult(None, "bad_mime")
            raw_length = response.headers.get("Content-Length", "").strip()
            if raw_length.isdigit() and int(raw_length) > self.max_download_bytes:
                return DownloadResult(None, "too_large")

            try:
                with tempfile.SpooledTemporaryFile(max_size=5 * 1024 * 1024) as handle:
                    total = 0
                    digest = hashlib.sha256()
                    for chunk in response.iter_content(256 * 1024):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > self.max_download_bytes:
                            return DownloadResult(None, "too_large")
                        digest.update(chunk)
                        handle.write(chunk)
                    if total < 20_000:
                        return DownloadResult(None, "too_small_file")
                    self.metrics.downloaded += 1
                    handle.seek(0)
                    blob = handle.read()
            except OSError:
                return DownloadResult(None, "stream_error")

        try:
            old_limit = Image.MAX_IMAGE_PIXELS
            Image.MAX_IMAGE_PIXELS = self.max_pixels
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(blob)) as source:
                    source.verify()
                with Image.open(io.BytesIO(blob)) as source:
                    source = ImageOps.exif_transpose(source).convert("RGB")
                    width, height = source.size
                    if width * height > self.max_pixels:
                        return DownloadResult(None, "too_many_pixels")
                    if width < 900 or height < 560:
                        return DownloadResult(None, "too_small_dimensions")
                    image_phash = phash(source)

                    target_ratio = 16 / 10
                    if width / height > target_ratio:
                        crop_width = int(height * target_ratio)
                        left = (width - crop_width) // 2
                        review_image = source.crop((left, 0, left + crop_width, height))
                    else:
                        crop_height = int(width / target_ratio)
                        top = (height - crop_height) // 2
                        review_image = source.crop((0, top, width, top + crop_height))
                    if review_image.width > 1600:
                        review_image = review_image.resize((1600, 1000), Image.Resampling.LANCZOS)
                    review_bytes = io.BytesIO()
                    review_image.save(review_bytes, "JPEG", quality=88, optimize=True, progressive=True)

                    source_image = source
                    if source_image.width > 1800:
                        new_height = round(source_image.height * (1800 / source_image.width))
                        source_image = source_image.resize((1800, new_height), Image.Resampling.LANCZOS)
                    source_bytes = io.BytesIO()
                    source_image.save(source_bytes, "JPEG", quality=90, optimize=True, progressive=True)
            Image.MAX_IMAGE_PIXELS = old_limit
        except (Image.DecompressionBombError, Image.DecompressionBombWarning):
            return DownloadResult(None, "decompression_bomb")
        except (UnidentifiedImageError, OSError, ValueError):
            return DownloadResult(None, "invalid_image")
        finally:
            try:
                Image.MAX_IMAGE_PIXELS = old_limit
            except UnboundLocalError:
                pass

        return DownloadResult(
            PreparedCandidate(
                candidate=candidate,
                sha256=digest.hexdigest(),
                phash=image_phash,
                width=width,
                height=height,
                review_bytes=review_bytes.getvalue(),
                source_bytes=source_bytes.getvalue(),
            )
        )
