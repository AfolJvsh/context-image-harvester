from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class HarvesterConfig:
    output: Path
    per_item: int = 8
    per_provider: int = 25
    phash_distance: int = 8
    serpapi_max: int = 110
    max_download_mb: int = 25
    timeout: int = 35
    max_pixels: int = 50_000_000
    download_workers: int = 4
    rights_mode: str = "review"
    cache_dir: Path = Path(".cache/context-image-harvester")
    cache_ttl_hours: int = 168
    resume: bool = False
    enable_clip: bool = False
    clip_model: str = "ViT-B-32"
    clip_pretrained: str = "laion2b_s34b_b79k"
    semantic_weight: float = 0.55
    resolution_weight: float = 0.10
    provider_weight: float = 0.10
    metadata_weight: float = 0.10
    diversity_weight: float = 0.15
