from __future__ import annotations

import os

from ..models import Candidate, Item
from ..utils import clean
from .base import Provider


class PexelsProvider(Provider):
    name = "pexels"

    def search(self, item: Item, limit: int) -> list[Candidate]:
        key = os.getenv("PEXELS_API_KEY", "").strip()
        if not key:
            return []
        collected: list[Candidate] = []
        seen: set[str] = set()
        for query in item.search_queries:
            payload = {"query": query, "limit": min(limit, 80)}
            cached = self.cache.get(self.name, payload)
            if cached is not None:
                self.metrics.cache_hits[self.name] += 1
                photos = cached
            else:
                self.metrics.provider_searches[self.name] += 1
                response = self.session.get(
                    "https://api.pexels.com/v1/search",
                    params={"query": query, "per_page": min(limit, 80)},
                    headers={"Authorization": key},
                    timeout=self.timeout,
                )
                response.raise_for_status()
                photos = response.json().get("photos", [])
                self.cache.set(self.name, payload, photos)
            for photo in photos:
                src = photo.get("src") or {}
                image_url = src.get("large2x") or src.get("large") or src.get("original")
                if not image_url or image_url in seen:
                    continue
                seen.add(image_url)
                collected.append(Candidate(
                    provider=self.name,
                    title=clean(photo.get("alt")) or f"Pexels photo {photo.get('id', '')}",
                    description=clean(photo.get("alt")),
                    image_url=image_url,
                    page_url=photo.get("url", ""),
                    creator=clean(photo.get("photographer")),
                    license="Pexels License",
                    license_url="https://www.pexels.com/license/",
                    rights_status="verified-provider",
                ))
                if len(collected) >= limit:
                    return collected
        return collected
