import json

from context_image_harvester.utils import load_items


def test_load_items_supports_search_queries(tmp_path):
    path = tmp_path / "prompts.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": 4,
                    "name": "Repair",
                    "prompt": "technician fixing laptop",
                    "search_queries": ["laptop repair", "repair technician"],
                },
                "simple prompt",
            ]
        )
    )
    items = load_items(path)
    assert items[0].id == 4
    assert items[0].search_queries == ["laptop repair", "repair technician"]
    assert items[1].search_queries == ["simple prompt"]


def test_load_items_supports_structured_context(tmp_path):
    path = tmp_path / "prompts.json"
    path.write_text(
        json.dumps(
            [
                {
                    "id": 1,
                    "name": "Business WiFi",
                    "prompt": "technician installing wifi",
                    "context": {
                        "setting": "modern small business office",
                        "composition": "landscape website hero",
                    },
                    "must_include": ["wireless access point", "technician"],
                    "must_avoid": ["illustration", "server rack"],
                }
            ]
        )
    )
    item = load_items(path)[0]
    assert item.context["setting"] == "modern small business office"
    assert item.must_include == ["wireless access point", "technician"]
    assert item.must_avoid == ["illustration", "server rack"]
    assert "setting: modern small business office" in item.semantic_prompt()
    assert item.search_queries


def test_duplicate_ids_are_rejected(tmp_path):
    path = tmp_path / "prompts.json"
    path.write_text(
        json.dumps(
            [
                {"id": 1, "name": "A", "prompt": "a photo"},
                {"id": 1, "name": "B", "prompt": "b photo"},
            ]
        )
    )
    try:
        load_items(path)
    except ValueError as exc:
        assert "unique" in str(exc)
    else:
        raise AssertionError("expected duplicate IDs to fail")
