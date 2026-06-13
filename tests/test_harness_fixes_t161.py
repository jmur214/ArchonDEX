"""Tests for T-2026-06-12-161 harness fixes (no backtest / no network).

Covers:
  #1 ensure_data timeout seatbelt — cached path untouched; uncached fail-loud
  #2 PIT-mask fail-loud counter — ON filters, BAD-mask counts, OFF inert
  #3 OFF inertness — OFF returns the IDENTICAL slice object (definitive proof
     of the T-154 partial flag, harness-free)
"""
from __future__ import annotations

import pandas as pd
import pytest

from backtester.backtest_controller import BacktestController


# ---- #2 + #3: PIT-mask logic via the pure _apply_pit_mask method ---------- #

def _ctl(mask):
    """A BacktestController with ONLY the pit attributes set (no __init__ —
    bypasses the heavy engine wiring; we test the pure mask method)."""
    c = BacktestController.__new__(BacktestController)
    c.pit_membership_mask = mask
    c.pit_mask_fallback_bars = 0
    c._pit_fallback_logged = False
    return c


def _slice():
    idx = pd.date_range("2020-01-01", periods=3)
    return {"AAA": pd.DataFrame({"Close": [1, 2, 3]}, index=idx),
            "BBB": pd.DataFrame({"Close": [4, 5, 6]}, index=idx)}


def test_off_path_returns_identical_object():
    """OFF (mask None) MUST return the same object — byte-inert vs pre-hook."""
    c = _ctl(None)
    sl = _slice()
    out = c._apply_pit_mask(sl, pd.Timestamp("2020-06-01"))
    assert out is sl                      # identity, not just equality
    assert c.pit_mask_fallback_bars == 0


def test_on_path_filters_to_members():
    mask = pd.DataFrame({"AAA": [True], "BBB": [False]},
                        index=pd.DatetimeIndex([pd.Timestamp("2019-01-01")]))
    c = _ctl(mask)
    out = c._apply_pit_mask(_slice(), pd.Timestamp("2020-06-01"))
    assert set(out) == {"AAA"}            # BBB not in-index → dropped
    assert c.pit_mask_fallback_bars == 0


def test_bad_mask_fails_loud_not_silent(capsys):
    """A mask whose .asof raises must COUNT the fallback, not silently revert."""
    class _Bad:
        def asof(self, ts):
            raise RuntimeError("boom")
    c = _ctl(_Bad())
    sl = _slice()
    out = c._apply_pit_mask(sl, pd.Timestamp("2020-06-01"))
    assert out is sl                      # falls back to full slice...
    assert c.pit_mask_fallback_bars == 1  # ...but LOUDLY (counted)
    assert "PIT-FALLBACK" in capsys.readouterr().out
    # logged once: a second failure increments count, no second log line
    c._apply_pit_mask(sl, pd.Timestamp("2020-07-01"))
    assert c.pit_mask_fallback_bars == 2
    assert "PIT-FALLBACK" not in capsys.readouterr().out


# ---- #1: ensure_data seatbelt — cached untouched, uncached fail-loud ------ #

def test_ensure_data_cached_path_skips_network(monkeypatch, capsys):
    from engines.data_manager import data_manager as dmmod
    dm = dmmod.DataManager.__new__(dmmod.DataManager)
    dm.api_key, dm.secret_key, dm.base_url = None, None, None  # offline

    cached = pd.DataFrame({"Open": [1.0] * 20, "High": [1.0] * 20,
                           "Low": [1.0] * 20, "Close": [1.0] * 20,
                           "Volume": [1] * 20},
                          index=pd.date_range("2020-01-01", periods=20))
    monkeypatch.setattr(dm, "load_cached", lambda t, tf: cached)
    # if the network/yfinance branch is reached for a cached ticker, blow up
    monkeypatch.setattr(dm, "_fetch_yfinance",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError("network touched")))
    out = dmmod.DataManager.ensure_data(dm, ["AAA"], "2020-01-01", "2020-01-31")
    assert out["AAA"] is cached           # cached returned, network untouched
    assert "FETCH-FAIL" not in capsys.readouterr().out


def test_ensure_data_uncached_fails_loud(monkeypatch, capsys):
    from engines.data_manager import data_manager as dmmod
    dm = dmmod.DataManager.__new__(dmmod.DataManager)
    dm.api_key, dm.secret_key, dm.base_url = None, None, None  # offline → yf only
    monkeypatch.setattr(dm, "load_cached", lambda t, tf: pd.DataFrame())
    monkeypatch.setattr(dm, "_fetch_yfinance", lambda *a, **k: pd.DataFrame())
    out = dmmod.DataManager.ensure_data(dm, ["ZZZ"], "2020-01-01", "2020-01-31")
    assert out["ZZZ"].empty
    log = capsys.readouterr().out
    assert "FETCH-FAIL" in log and "ZZZ" in log   # named + loud, non-fatal


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
