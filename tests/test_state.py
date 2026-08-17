from context_image_harvester.state import RunState


def test_state_round_trip(tmp_path):
    state = RunState(tmp_path / "state.json")
    state.records.append({"item_id": 1, "file": "images/a.jpg"})
    state.completed_item_ids.add(1)
    state.sha256.add("abc")
    state.phashes.append("0000000000000000")
    state.save()

    loaded = RunState(tmp_path / "state.json")
    loaded.load()
    assert loaded.completed_item_ids == {1}
    assert loaded.sha256 == {"abc"}
    assert loaded.phashes == ["0000000000000000"]
