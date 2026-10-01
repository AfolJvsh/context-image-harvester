from __future__ import annotations

import json
from pathlib import Path


class RunState:
    def __init__(self, path: Path):
        self.path = path
        self.records: list[dict] = []
        self.completed_item_ids: set[int] = set()
        self.sha256: set[str] = set()
        self.phashes: list[str] = []
        self.seen_urls: set[str] = set()
        self.serpapi_requests_used = 0

    def load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.records = list(data.get("records", []))
        self.completed_item_ids = {int(x) for x in data.get("completed_item_ids", [])}
        self.sha256 = set(data.get("sha256", []))
        self.phashes = list(data.get("phashes", []))
        persisted_urls = data.get("seen_urls", [])
        self.seen_urls = set(persisted_urls)
        if not self.seen_urls:
            self.seen_urls = {
                str(record["direct_image_url"])
                for record in self.records
                if record.get("direct_image_url")
            }
        self.serpapi_requests_used = int(data.get("serpapi_requests_used", 0))

    def drop_item(self, item_id: int, output: Path) -> None:
        keep: list[dict] = []
        for record in self.records:
            if int(record.get("item_id", -1)) != item_id:
                keep.append(record)
                continue
            for key in ("file", "source_original"):
                relative = record.get(key)
                if relative:
                    path = output / relative
                    if path.exists() and path.is_file():
                        path.unlink()
        self.records = keep
        self.completed_item_ids.discard(item_id)
        self.sha256 = {record["sha256"] for record in keep if record.get("sha256")}
        self.phashes = [record["phash"] for record in keep if record.get("phash")]
        self.seen_urls = {
            str(record["direct_image_url"])
            for record in keep
            if record.get("direct_image_url")
        }
        self.save()

    def save(self) -> None:
        payload = {
            "records": self.records,
            "completed_item_ids": sorted(self.completed_item_ids),
            "sha256": sorted(self.sha256),
            "phashes": self.phashes,
            "seen_urls": sorted(self.seen_urls),
            "serpapi_requests_used": self.serpapi_requests_used,
        }
        temp = self.path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        temp.replace(self.path)
