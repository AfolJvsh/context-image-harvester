from pathlib import Path

import pytest

from context_image_harvester.cli import _safe_output, estimate


def test_estimate_honors_serpapi_cap():
    result = estimate(55, 8, 70)
    assert result["target_images"] == 440
    assert result["worst_case_serpapi_without_cap"] == 110
    assert result["maximum_paid_searches_this_run"] == 70


def test_estimate_accounts_for_adaptive_query_variants():
    result = estimate(3, 8, 20, paid_query_count=5)
    assert result["max_google_searches"] == 5
    assert result["max_bing_searches"] == 5
    assert result["worst_case_serpapi_without_cap"] == 10


def test_safe_output_rejects_current_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError):
        _safe_output(Path("."))


def test_estimate_strict_mode_spends_no_serpapi():
    result = estimate(55, 8, 110, rights_mode="strict", paid_query_count=100)
    assert result["maximum_paid_searches_this_run"] == 0
    assert result["max_google_searches"] == 0
