from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class Item:
    id: int
    name: str
    prompt: str
    search_queries: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Candidate:
    provider: str
    title: str
    description: str
    image_url: str
    page_url: str
    creator: str = ""
    license: str = ""
    license_url: str = ""
    rights_status: str = "unknown"
    categories: str = ""
    mime: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Candidate:
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{k: value.get(k, "") for k in allowed})


@dataclass(slots=True)
class PreparedCandidate:
    candidate: Candidate
    sha256: str
    phash: str
    width: int
    height: int
    review_bytes: bytes
    source_bytes: bytes
    metadata_score: float = 0.0
    resolution_score: float = 0.0
    provider_score: float = 0.0
    semantic_score: float = 0.0
    final_score: float = 0.0
