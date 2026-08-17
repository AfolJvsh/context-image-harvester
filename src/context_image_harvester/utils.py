from __future__ import annotations

import html
import json
import re
from pathlib import Path

from .models import Item


def clean(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def slug(text: str, limit: int = 64) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return value[:limit].rstrip("-") or "image"


def load_items(path: Path) -> list[Item]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("prompts") or data.get("items") or []
    if not isinstance(data, list):
        raise ValueError("Prompt file must be a JSON list or object containing prompts/items.")

    items: list[Item] = []
    for idx, value in enumerate(data, start=1):
        if isinstance(value, str):
            prompt = clean(value)
            if prompt:
                items.append(Item(idx, f"Prompt {idx}", prompt, [prompt]))
            continue
        if not isinstance(value, dict):
            continue
        prompt = clean(value.get("prompt") or value.get("search_query") or value.get("query"))
        if not prompt:
            continue
        queries = value.get("search_queries") or []
        if isinstance(queries, str):
            queries = [queries]
        queries = [clean(q) for q in queries if clean(q)]
        name = clean(value.get("name") or value.get("service") or value.get("title") or f"Prompt {idx}")
        items.append(Item(int(value.get("id", idx)), name, prompt, queries or [prompt]))
    if not items:
        raise ValueError("No valid prompts found.")
    ids = [item.id for item in items]
    if len(ids) != len(set(ids)):
        raise ValueError("Item IDs must be unique.")
    return items


def short_query(item: Item) -> str:
    stop = {
        "professional", "real", "photography", "photograph", "editorial", "modern",
        "using", "with", "and", "the", "of", "on", "for", "from", "performing",
        "reviewing", "working", "workplace", "business",
    }
    words: list[str] = []
    for word in re.findall(r"[a-z0-9]+", (item.name + " " + item.prompt).lower()):
        if len(word) > 2 and word not in stop and word not in words:
            words.append(word)
    return " ".join(words[:8]) or item.name


def terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}
