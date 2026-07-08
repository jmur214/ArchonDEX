# tests/test_news_universe_guard_t290c.py
"""T-290c — the news-universe-collapse guard. A missing sp500_membership_pit
.parquet silently collapses full_universe() to the ~10 (mostly delisted)
special-sits → n_new=0 every day while degraded reads False (looks like a quiet
day; is a dead forward clock). This guard makes it LOUD."""
from __future__ import annotations

import pytest

from scripts.run_paper_cloud_day import _news_universe_collapse_reason

SPECIAL_SITS = ["SIVB", "FRC", "TWTR", "BBBY", "GNC", "JCP", "WLL", "REV", "ATVI", "CBL"]


def test_healthy_universe_is_not_flagged():
    universe = [f"T{i}" for i in range(1205)]        # full membership present
    assert _news_universe_collapse_reason(universe, SPECIAL_SITS) is None


def test_collapsed_to_special_sits_is_flagged_loud():
    reason = _news_universe_collapse_reason(list(SPECIAL_SITS), SPECIAL_SITS)
    assert reason is not None
    assert "COLLAPSED" in reason
    assert "sp500_membership_pit" in reason          # names the missing input


def test_boundary_one_above_special_sits_is_healthy():
    universe = list(SPECIAL_SITS) + ["EXTRA"]        # any real member → healthy
    assert _news_universe_collapse_reason(universe, SPECIAL_SITS) is None


def test_empty_universe_is_flagged():
    assert _news_universe_collapse_reason([], SPECIAL_SITS) is not None
