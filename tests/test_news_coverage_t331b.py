"""tests/test_news_coverage_t331b.py — T-331b: separate "the tape is broken" from
"your universe isn't covered".

THE DIAGNOSIS THIS LOCKS: the constrained analyst wrote a free-text `news_degraded`
risk flag on 8 straight notes while the news panel was HEALTHY (2,706 rows through
Aug-18 in-cloud). Its slice was thin because its universe is a 3-ETF sleeve and the
tape is company-tagged — AGG has ZERO coverage by construction. `degraded` must mean
a genuine FAULT; thin coverage is a structural fact, stated as such.
"""
import datetime as dt

import pandas as pd

from intelligence.analyst.context_builder import _news_section


def _panel(rows):
    return pd.DataFrame(rows, columns=["created_at", "symbols", "headline", "content"])


def test_healthy_panel_with_no_matches_is_NOT_degraded():
    """The exact production shape: panel full of company news, none for the ETFs."""
    df = _panel([{"created_at": pd.Timestamp("2026-08-17", tz="UTC"), "symbols": ["NVDA"],
                  "headline": "chip news", "content": "..."}])
    sec = _news_section(dt.date(2026, 8, 18), ["SPY", "AGG", "GLD"], load_panel=lambda as_of: df)
    assert sec["degraded"] is False                      # the FEED is fine
    cov = sec["coverage"]
    assert cov["thin_coverage"] is True                  # ...but THIS slice is empty
    assert cov["symbols_with_zero_coverage"] == ["AGG", "GLD", "SPY"]
    assert cov["panel_rows"] == 1
    assert cov["panel_newest_created_at"].startswith("2026-08-17")


def test_partial_coverage_names_the_uncovered_symbols():
    df = _panel([{"created_at": pd.Timestamp("2026-08-17", tz="UTC"), "symbols": ["SPY"],
                  "headline": "spy news", "content": "..."}])
    cov = _news_section(dt.date(2026, 8, 18), ["SPY", "AGG"], load_panel=lambda as_of: df)["coverage"]
    assert cov["symbols_with_news"] == ["SPY"]
    assert cov["symbols_with_zero_coverage"] == ["AGG"]   # zero BY CONSTRUCTION, not a fault
    assert cov["thin_coverage"] is False


def test_a_REAL_fault_still_sets_degraded():
    empty = _news_section(dt.date(2026, 8, 18), ["SPY"], load_panel=lambda as_of: _panel([]))
    assert empty["degraded"] is True and empty["reason"] == "empty_panel"

    def boom(as_of):
        raise RuntimeError("feed down")
    err = _news_section(dt.date(2026, 8, 18), ["SPY"], load_panel=boom)
    assert err["degraded"] is True and err["reason"].startswith("news_error:")


def test_panel_freshness_is_visible_so_a_real_freeze_is_detectable():
    """A frozen tape must be visible as a STALE max date, not inferred from silence."""
    df = _panel([{"created_at": pd.Timestamp("2026-08-05", tz="UTC"), "symbols": ["SPY"],
                  "headline": "old", "content": "..."}])
    cov = _news_section(dt.date(2026, 8, 18), ["SPY"], load_panel=lambda as_of: df)["coverage"]
    assert cov["panel_newest_created_at"].startswith("2026-08-05")   # 13 days stale, visible
