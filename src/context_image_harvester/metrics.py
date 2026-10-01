from __future__ import annotations

from collections import Counter
from threading import Lock


class Metrics:
    def __init__(self) -> None:
        self.rejections: Counter[str] = Counter()
        self.provider_searches: Counter[str] = Counter()
        self.cache_hits: Counter[str] = Counter()
        self.downloaded = 0
        self._lock = Lock()

    def reject(self, reason: str) -> None:
        with self._lock:
            self.rejections[reason] += 1

    def record_download(self) -> None:
        with self._lock:
            self.downloaded += 1

    def as_dict(self) -> dict:
        with self._lock:
            return {
                "downloaded_candidates": self.downloaded,
                "rejections": dict(sorted(self.rejections.items())),
                "provider_searches": dict(sorted(self.provider_searches.items())),
                "cache_hits": dict(sorted(self.cache_hits.items())),
            }
