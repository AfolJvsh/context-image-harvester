from __future__ import annotations

from collections import Counter


class Metrics:
    def __init__(self) -> None:
        self.rejections: Counter[str] = Counter()
        self.provider_searches: Counter[str] = Counter()
        self.cache_hits: Counter[str] = Counter()
        self.downloaded = 0

    def reject(self, reason: str) -> None:
        self.rejections[reason] += 1

    def as_dict(self) -> dict:
        return {
            "downloaded_candidates": self.downloaded,
            "rejections": dict(sorted(self.rejections.items())),
            "provider_searches": dict(sorted(self.provider_searches.items())),
            "cache_hits": dict(sorted(self.cache_hits.items())),
        }
