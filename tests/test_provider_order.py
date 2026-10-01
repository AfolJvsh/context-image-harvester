from context_image_harvester.config import HarvesterConfig
from context_image_harvester.harvester import Harvester
from context_image_harvester.models import Candidate, Item, PreparedCandidate
from context_image_harvester.providers.serpapi import SerpApiProvider


class FakeProvider:
    def __init__(self, name, count):
        self.name = name
        self.count = count
        self.calls = 0

    def search(self, item, limit):
        self.calls += 1
        return [
            Candidate(
                self.name,
                f"{self.name}-{i}",
                "",
                f"https://example.com/{self.name}/{i}.jpg",
                "",
            )
            for i in range(self.count)
        ]


def prepared_candidates(candidates):
    out = []
    phashes = [
        "0000000000000000",
        "ffffffffffffffff",
        "aaaaaaaaaaaaaaaa",
        "5555555555555555",
    ]
    for i, candidate in enumerate(candidates):
        out.append(
            PreparedCandidate(
                candidate=candidate,
                sha256=f"{candidate.provider}-{candidate.image_url}-{i}",
                phash=phashes[i % len(phashes)],
                width=1600,
                height=1000,
                review_bytes=b"review",
                source_bytes=b"source",
            )
        )
    return out


def test_pexels_can_fill_without_paid_provider(tmp_path, monkeypatch):
    h = Harvester(
        HarvesterConfig(
            output=tmp_path / "out",
            per_item=2,
            per_provider=3,
        )
    )
    pexels = FakeProvider("pexels", 3)
    google = FakeProvider("serpapi-google", 3)
    h.providers = [pexels, google]

    monkeypatch.setattr(
        h,
        "_prepare_many",
        lambda item, candidates: prepared_candidates(candidates),
    )
    count = h.process_item(
        Item(1, "Test", "test photo", ["test photo"])
    )
    assert count == 2
    assert pexels.calls == 1
    assert google.calls == 0


def test_serpapi_tries_second_query_only_when_first_is_short(tmp_path, monkeypatch):
    h = Harvester(
        HarvesterConfig(
            output=tmp_path / "out",
            per_item=2,
            per_provider=2,
            serpapi_max=10,
        )
    )
    provider = SerpApiProvider(
        h.session,
        h.cache,
        h.metrics,
        h.config.timeout,
        engine="google_images",
        request_budget=h.budget,
    )
    calls = []

    def fake_search_query(query, limit):
        calls.append(query)
        count = 1 if len(calls) == 1 else 2
        return [
            Candidate(
                provider.name,
                f"{query}-{i}",
                "",
                f"https://example.com/{len(calls)}/{i}.jpg",
                "",
            )
            for i in range(count)
        ]

    monkeypatch.setattr(provider, "search_query", fake_search_query)
    monkeypatch.setattr(
        h,
        "_prepare_many",
        lambda item, candidates: prepared_candidates(candidates),
    )
    h.providers = [provider]

    count = h.process_item(
        Item(
            1,
            "Test",
            "technician in office",
            ["technician office", "network engineer office"],
        )
    )
    assert count == 2
    assert calls == ["technician office", "network engineer office"]
