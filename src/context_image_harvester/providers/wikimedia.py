from __future__ import annotations

import time

from ..models import Candidate, Item
from ..utils import clean, short_query
from .base import Provider


class WikimediaProvider(Provider):
    name = "wikimedia"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.blocked_until = 0.0
        self.last_request = 0.0

    def _request(self, params: dict) -> dict | None:
        now = time.time()
        if now < self.blocked_until:
            return None
        elapsed = now - self.last_request
        if elapsed < 2.0:
            time.sleep(2.0 - elapsed)
        params = dict(params)
        params["maxlag"] = 5
        for attempt in range(3):
            self.last_request = time.time()
            self.metrics.provider_searches[self.name] += 1
            response = self.session.get(
                "https://commons.wikimedia.org/w/api.php", params=params, timeout=self.timeout
            )
            if response.status_code in {429, 503}:
                raw = response.headers.get("Retry-After", "").strip()
                try:
                    retry_after = max(1, int(raw))
                except ValueError:
                    retry_after = 15 * (2**attempt)
                self.blocked_until = time.time() + retry_after
                return None
            response.raise_for_status()
            data = response.json()
            error = data.get("error") or {}
            if error.get("code") in {"maxlag", "ratelimited"}:
                time.sleep(8 * (2**attempt))
                continue
            return data
        return None

    def search(self, item: Item, limit: int) -> list[Candidate]:
        payload = {"query": short_query(item), "limit": min(limit, 50)}
        cached = self.cache.get(self.name, payload)
        if cached is not None:
            self.metrics.cache_hits[self.name] += 1
            data = cached
        else:
            data = self._request({
                "action": "query",
                "generator": "search",
                "gsrsearch": payload["query"],
                "gsrnamespace": 6,
                "gsrlimit": payload["limit"],
                "prop": "imageinfo",
                "iiprop": "url|size|extmetadata|mime",
                "iiurlwidth": 1800,
                "format": "json",
                "formatversion": 2,
            })
            if not data:
                return []
            self.cache.set(self.name, payload, data)
        out: list[Candidate] = []
        for page in ((data.get("query") or {}).get("pages") or []):
            infos = page.get("imageinfo") or []
            if not infos:
                continue
            info = infos[0]
            ext = info.get("extmetadata") or {}
            def em(key: str, metadata=ext) -> str:
                return clean((metadata.get(key) or {}).get("value"))

            license_name = em("LicenseShortName")
            license_url = em("LicenseUrl")
            out.append(Candidate(
                provider=self.name,
                title=clean(str(page.get("title", "")).replace("File:", "")),
                description=em("ImageDescription"),
                image_url=info.get("thumburl") or info.get("url", ""),
                page_url=info.get("descriptionurl", ""),
                creator=em("Artist") or em("Credit"),
                license=license_name or "Wikimedia Commons",
                license_url=license_url,
                rights_status="verified-metadata" if license_name or license_url else "manual-review",
                categories=em("Categories"),
                mime=info.get("mime", ""),
            ))
        return out[:limit]
