from context_image_harvester.state import RunState


def test_state_round_trip(tmp_path):
    state = RunState(tmp_path / "state.json")
    state.records.append(
        {
            "item_id": 1,
            "file": "images/a.jpg",
            "direct_image_url": "https://example.com/a.jpg",
        }
    )
    state.completed_item_ids.add(1)
    state.sha256.add("abc")
    state.phashes.append("0000000000000000")
    state.seen_urls.add("https://example.com/a.jpg")
    state.serpapi_requests_used = 3
    state.save()

    loaded = RunState(tmp_path / "state.json")
    loaded.load()
    assert loaded.completed_item_ids == {1}
    assert loaded.sha256 == {"abc"}
    assert loaded.phashes == ["0000000000000000"]
    assert loaded.seen_urls == {"https://example.com/a.jpg"}
    assert loaded.serpapi_requests_used == 3


def test_old_state_derives_seen_urls_from_records(tmp_path):
    path = tmp_path / "state.json"
    path.write_text(
        '{"records":[{"item_id":1,"direct_image_url":"https://example.com/a.jpg"}]}'
    )
    state = RunState(path)
    state.load()
    assert state.seen_urls == {"https://example.com/a.jpg"}
