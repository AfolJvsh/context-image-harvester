from __future__ import annotations

import io
import math
from collections.abc import Iterable

from PIL import Image

from .hashing import hamming
from .models import Item, PreparedCandidate
from .utils import terms

PROVIDER_TRUST = {
    "pexels": 1.0,
    "wikimedia": 0.95,
    "serpapi-google": 0.45,
    "serpapi-bing": 0.40,
}
REAL_PHOTO_POSITIVE = [
    "a real camera photograph",
    "an authentic documentary photograph",
    "a natural professional editorial photo",
]
REAL_PHOTO_NEGATIVE = [
    "an AI generated image",
    "a digital illustration",
    "a 3d render",
    "a vector graphic or cartoon",
]


class ClipScorer:
    def __init__(self, model_name: str, pretrained: str):
        try:
            import open_clip
            import torch
        except ImportError as exc:
            raise RuntimeError(
                "CLIP ranking requires the optional dependencies: pip install 'context-image-harvester[clip]'"
            ) from exc
        self.torch = torch
        self.open_clip = open_clip
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained
        )
        self.model = self.model.to(self.device).eval()
        self.tokenizer = open_clip.get_tokenizer(model_name)

    def _image_features(self, image_bytes: bytes):
        torch = self.torch
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        with torch.no_grad():
            features = self.model.encode_image(image_tensor)
            features /= features.norm(dim=-1, keepdim=True)
        return features

    def score(self, prompt: str, image_bytes: bytes) -> float:
        torch = self.torch
        image_features = self._image_features(image_bytes)
        text = self.tokenizer([prompt]).to(self.device)
        with torch.no_grad():
            text_features = self.model.encode_text(text)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            cosine = (image_features @ text_features.T).item()
        return max(0.0, min(1.0, (cosine + 1.0) / 2.0))

    def photo_score(self, image_bytes: bytes) -> float:
        torch = self.torch
        labels = REAL_PHOTO_POSITIVE + REAL_PHOTO_NEGATIVE
        image_features = self._image_features(image_bytes)
        text = self.tokenizer(labels).to(self.device)
        with torch.no_grad():
            text_features = self.model.encode_text(text)
            text_features /= text_features.norm(dim=-1, keepdim=True)
            logits = 100.0 * image_features @ text_features.T
            probs = logits.softmax(dim=-1)[0]
        positive = probs[: len(REAL_PHOTO_POSITIVE)].sum().item()
        return max(0.0, min(1.0, positive))


def metadata_score(item: Item, prepared: PreparedCandidate) -> float:
    desired = terms(
        item.name
        + " "
        + item.semantic_prompt()
        + " "
        + " ".join(item.search_queries)
        + " "
        + " ".join(item.must_include)
    )
    observed_text = (
        prepared.candidate.title
        + " "
        + prepared.candidate.description
        + " "
        + prepared.candidate.categories
    )
    observed = terms(observed_text)
    base = 0.0 if not desired or not observed else len(desired & observed) / len(desired | observed)

    required = terms(" ".join(item.must_include))
    avoided = terms(" ".join(item.must_avoid))
    required_bonus = 0.0
    if required:
        required_bonus = 0.20 * (len(required & observed) / len(required))
    avoid_penalty = 0.0
    if avoided:
        avoid_penalty = 0.35 * (len(avoided & observed) / len(avoided))
    return max(0.0, min(1.0, base + required_bonus - avoid_penalty))


def resolution_score(prepared: PreparedCandidate) -> float:
    pixels = prepared.width * prepared.height
    return min(1.0, math.log1p(pixels) / math.log1p(3840 * 2160))


def annotate_scores(
    item: Item,
    candidates: Iterable[PreparedCandidate],
    semantic_weight: float,
    resolution_weight: float,
    provider_weight: float,
    metadata_weight: float,
    clip_scorer: ClipScorer | None,
) -> list[PreparedCandidate]:
    out: list[PreparedCandidate] = []
    semantic_prompt = item.semantic_prompt()
    for prepared in candidates:
        prepared.metadata_score = metadata_score(item, prepared)
        prepared.resolution_score = resolution_score(prepared)
        prepared.provider_score = PROVIDER_TRUST.get(prepared.candidate.provider, 0.25)
        prepared.semantic_score = (
            clip_scorer.score(semantic_prompt, prepared.review_bytes)
            if clip_scorer
            else prepared.metadata_score
        )
        prepared.photo_score = (
            clip_scorer.photo_score(prepared.review_bytes)
            if clip_scorer
            else min(1.0, prepared.provider_score + 0.20)
        )
        base_score = (
            semantic_weight * prepared.semantic_score
            + resolution_weight * prepared.resolution_score
            + provider_weight * prepared.provider_score
            + metadata_weight * prepared.metadata_score
        )
        prepared.final_score = base_score * (0.70 + 0.30 * prepared.photo_score)
        out.append(prepared)
    return out


def select_diverse(
    candidates: list[PreparedCandidate],
    limit: int,
    diversity_weight: float,
    duplicate_threshold: int,
) -> list[PreparedCandidate]:
    remaining = list(candidates)
    selected: list[PreparedCandidate] = []
    while remaining and len(selected) < limit:
        best = None
        best_score = -1.0
        for candidate in remaining:
            if selected:
                distances = [hamming(candidate.phash, chosen.phash) for chosen in selected]
                min_distance = min(distances)
                if min_distance <= duplicate_threshold:
                    continue
                diversity = min_distance / 64.0
            else:
                diversity = 1.0
            score = candidate.final_score + diversity_weight * diversity
            if score > best_score:
                best_score = score
                best = candidate
        if best is None:
            break
        selected.append(best)
        remaining.remove(best)
    return selected
