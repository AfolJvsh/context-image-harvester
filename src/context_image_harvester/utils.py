from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

from .models import Item


def clean(value: object) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def slug(text: str, limit: int = 64) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return value[:limit].rstrip("-") or "image"


def _string_list(value: Any) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        rendered = clean(item)
        if rendered and rendered not in out:
            out.append(rendered)
    return out


def _context(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, Any] = {}
    for key, raw in value.items():
        clean_key = clean(key)
        if not clean_key:
            continue
        if isinstance(raw, list):
            rendered = _string_list(raw)
        elif isinstance(raw, (str, int, float, bool)):
            rendered = clean(raw)
        else:
            continue
        if rendered:
            out[clean_key] = rendered
    return out


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
        queries = _string_list(value.get("search_queries"))
        name = clean(value.get("name") or value.get("service") or value.get("title") or f"Prompt {idx}")
        context = _context(value.get("context"))
        must_include = _string_list(value.get("must_include"))
        must_avoid = _string_list(value.get("must_avoid") or value.get("negative_terms"))
        item = Item(
            int(value.get("id", idx)),
            name,
            prompt,
            queries,
            context,
            must_include,
            must_avoid,
        )
        if not item.search_queries:
            item.search_queries = [short_query(item)]
        items.append(item)
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
        "reviewing", "working", "workplace", "business", "image", "photo",
    }
    source = " ".join([item.name, item.prompt, item.context_text(), " ".join(item.must_include)])
    words: list[str] = []
    for word in re.findall(r"[a-z0-9]+", source.lower()):
        if len(word) > 2 and word not in stop and word not in words:
            words.append(word)
    return " ".join(words[:10]) or item.name


def terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2}
