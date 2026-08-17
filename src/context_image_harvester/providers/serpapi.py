from __future__ import annotations

import os

from ..models import Candidate, Item
from ..utils import clean
from .base import Provider


class SerpApiProvider(Provider):
    def __init__(self, *args, engine: str, request_budget, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = engine
        self.name = f"serpapi-{'google' if engine == 'google_images' else 'bing'}"
        self.request_budget = request_budget

    def search(self, item: Item, limit: int) -> list[Candidate]:
        key = os.getenv("SERPAPI_API_KEY", "").strip()
        if not key:
            return []
        query = item.search_queries[0] if item.search_queries else item.prompt
        payload = {"engine": self.engine, "query": query, "limit": limit}
        cached = self.cache.get(self.name, payload)
        if cached is not None:
            self.metrics.cache_hits[self.name] += 1
            results = cached
        else:
            if not self.request_budget.consume():
                return []
            params = {"engine": self.engine, "api_key": key, "q": query}
            if self.engine == "google_images":
                params.update({"safe": "active", "num": min(limit, 100)})
            else:
                params.update({"safeSearch": "strict", "count": min(limit, 100), "mkt": "en-US"})
            self.metrics.provider_searches[self.name] += 1
            response = self.session.get("https://serpapi.com/search.json", params=params, timeout=self.timeout)
            response.raise_for_status()
            results = response.json().get("images_results", [])
            self.cache.set(self.name, payload, results)
        out: list[Candidate] = []
        for result in results:
            image_url = result.get("original") or result.get("thumbnail")
            if not image_url:
                continue
            out.append(Candidate(
                provider=self.name,
                title=clean(result.get("title")),
                description=clean(result.get("source")),
                image_url=image_url,
                page_url=result.get("link") or result.get("source") or "",
                license="",
                rights_status="manual-review",
            ))
            if len(out) >= limit:
                break
        return out
