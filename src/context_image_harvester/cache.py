from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


class SearchCache:
    def __init__(self, root: Path, ttl_hours: int = 168):
        self.root = root
        self.ttl_seconds = max(0, ttl_hours) * 3600
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, provider: str, payload: dict[str, Any]) -> Path:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        key = hashlib.sha256(raw.encode()).hexdigest()
        directory = self.root / provider
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{key}.json"

    def get(self, provider: str, payload: dict[str, Any]) -> Any | None:
        path = self._path(provider, payload)
        if not path.exists():
            return None
        if self.ttl_seconds and time.time() - path.stat().st_mtime > self.ttl_seconds:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def set(self, provider: str, payload: dict[str, Any], value: Any) -> None:
        path = self._path(provider, payload)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
