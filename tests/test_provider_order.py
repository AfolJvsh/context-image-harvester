from context_image_harvester.config import HarvesterConfig
from context_image_harvester.harvester import Harvester
from context_image_harvester.models import Candidate, Item, PreparedCandidate


class FakeProvider:
    def __init__(self, name, count):
        self.name = name
        self.count = count
        self.calls = 0

    def search(self, item, limit):
        self.calls += 1
        return [Candidate(self.name, f"{self.name}-{i}", "", f"https://example.com/{self.name}/{i}.jpg", "") for i in range(self.count)]


def test_pexels_can_fill_without_paid_provider(tmp_path, monkeypatch):
    h = Harvester(HarvesterConfig(output=tmp_path / "out", per_item=2, per_provider=3))
    pexels = FakeProvider("pexels", 3)
    google = FakeProvider("serpapi-google", 3)
    h.providers = [pexels, google]

    def fake_prepare(candidates):
        out = []
        for i, c in enumerate(candidates):
            out.append(PreparedCandidate(
                candidate=c,
                sha256=f"{c.provider}-{i}",
                phash=("0000000000000000" if i == 0 else "ffffffffffffffff" if i == 1 else "aaaaaaaaaaaaaaaa"),
                width=1600,
                height=1000,
                review_bytes=b"review",
                source_bytes=b"source",
            ))
        return out

    monkeypatch.setattr(h, "_prepare_many", fake_prepare)
    count = h.process_item(Item(1, "Test", "test photo", ["test photo"]))
    assert count == 2
    assert pexels.calls == 1
    assert google.calls == 0
