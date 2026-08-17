from context_image_harvester.models import Candidate, PreparedCandidate
from context_image_harvester.ranking import select_diverse


def prepared(phash, score):
    return PreparedCandidate(
        candidate=Candidate("pexels", "", "", "https://example.com/a.jpg", "https://example.com"),
        sha256=phash,
        phash=phash,
        width=1600,
        height=1000,
        review_bytes=b"x",
        source_bytes=b"y",
        final_score=score,
    )


def test_diverse_selection_avoids_near_duplicate():
    candidates = [
        prepared("0000000000000000", 0.9),
        prepared("0000000000000001", 0.89),
        prepared("ffffffffffffffff", 0.7),
    ]
    selected = select_diverse(candidates, 2, diversity_weight=0.15, duplicate_threshold=8)
    assert [c.phash for c in selected] == ["0000000000000000", "ffffffffffffffff"]
