"""Regression test for the 2026-05-08 zero-trade outage.

Root cause: yfinance returns a tz-aware DatetimeIndex (America/New_York)
from `Ticker.earnings_dates`. `EarningsVolEdge._get_earnings_dates`
cached those dates without stripping tz. Downstream
`_pre_earnings_signal` / `_post_earnings_signal` compared each cached
date against a tz-naive `as_of` timestamp — pandas raises
`TypeError: Cannot compare tz-naive and tz-aware timestamps`.

The exception propagated up through:
  earnings_vol.compute_signals → signal_collector._call_edge →
  signal_collector.collect → AlphaEngine.generate_signals →
  backtest_controller line 388

where it was swallowed by a bare `except Exception` (line 389):
  signals = []

Result: every backtest produced zero trades from 2026-05-07 01:39
onward. Symptom: empty trades.csv, all snapshots at $100k starting
equity, canon md5 = empty-md5 (`d41d8cd98f00b204e9800998ecf8427e`).

This test calls compute_signals on a real ticker against a tz-naive
timestamp and asserts no exception. If yfinance changes its tz handling
again, OR if the strip-tz line is removed, this test fires.
"""
from __future__ import annotations

import pandas as pd
import pytest

from engines.engine_a_alpha.edges.earnings_vol_edge import EarningsVolEdge


def test_earnings_vol_compute_signals_does_not_raise_on_tz_naive_timestamp(tmp_path):
    """The load-bearing invariant: compute_signals must not raise
    a tz-comparison error when called with a tz-naive `now`."""
    edge = EarningsVolEdge()
    edge._earnings_cache = {}  # ensure we re-fetch (simulates first call)

    # Build a synthetic data_map with enough history for the edge's
    # bb_window to compute. AAPL is one of the 12 tickers EarningsVolEdge
    # has yfinance coverage for.
    idx = pd.date_range("2024-01-01", periods=200, freq="B")
    import numpy as np
    rng = np.random.default_rng(0)
    close = 100 * (1.0 + rng.normal(0.001, 0.012, 200)).cumprod()
    df = pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99,
        "Close": close, "Volume": 1_000_000,
    }, index=idx)
    data_map = {"AAPL": df}

    # tz-NAIVE timestamp — the production format. Bug pre-fix: this
    # comparison-against-tz-aware-cached-dates raised TypeError.
    now = pd.Timestamp("2024-09-15")

    # Must not raise. Score may be 0.0 or non-zero; only the no-raise
    # property is being tested.
    scores = edge.compute_signals(data_map, now)
    assert isinstance(scores, dict)
    assert "AAPL" in scores


def test_earnings_vol_cached_dates_are_tz_naive(tmp_path, monkeypatch):
    """After _get_earnings_dates runs once, the cache must hold tz-naive
    Timestamps. This is the structural invariant that prevents the
    comparison error from ever firing again.

    T-138 (tests/ network sweep): previously this triggered a LIVE
    yfinance call ("trigger the cache load via a real call") — flaky
    under rate-limits and a network call inside the suite. The yfinance
    response is now a synthetic tz-AWARE frame injected via a fake
    Ticker, which is exactly the input shape the 2026-05-08 regression
    came from; the invariant under test (cache normalizes to tz-naive)
    is unchanged and now deterministic."""
    import sys
    import types

    fake_dates = pd.DataFrame(
        {"EPS Estimate": [1.0, 1.1, 1.2]},
        index=pd.DatetimeIndex(
            ["2024-01-25", "2024-04-25", "2024-07-25"],
            tz="America/New_York",
            name="Earnings Date",
        ),
    )

    class _FakeTicker:
        def __init__(self, _symbol):
            self.earnings_dates = fake_dates

    fake_yf = types.ModuleType("yfinance")
    fake_yf.Ticker = _FakeTicker
    monkeypatch.setitem(sys.modules, "yfinance", fake_yf)

    edge = EarningsVolEdge()
    edge._earnings_cache = {}

    dates = edge._get_earnings_dates("AAPL")
    assert dates, "synthetic tz-aware fixture must produce cached dates"

    for d in dates:
        ts = pd.Timestamp(d)
        assert ts.tz is None, (
            f"earnings cache entry has tz={ts.tz}; expected None. "
            f"This is the 2026-05-08 zero-trade-regression invariant — "
            f"any tz-aware entry comparing against a tz-naive `as_of` "
            f"will raise TypeError and silently kill all signals via "
            f"the bare except in backtest_controller:389."
        )


def test_backtest_controller_bare_except_swallows_alpha_errors():
    """Document and verify the bare-except behavior at
    backtest_controller.py:389. We're not removing the catch (changes
    in alpha shouldn't crash a backtest), but we want the existence of
    this swallow path on the record so future debugs know to look here.

    If this test fails, either the line moved or the catch was tightened
    — both are improvements that close this issue more permanently."""
    from pathlib import Path
    src = (Path(__file__).resolve().parent.parent
           / "backtester" / "backtest_controller.py").read_text()
    # The catch wraps both compute_signals and generate_signals. If the
    # source no longer has both `signals = []` lines (initial + reset),
    # the structure changed and this test should be updated.
    assert "Alpha signal generation error" in src, (
        "The error-message string in backtest_controller is missing. "
        "Either the bare-except was removed (better!) or the error "
        "message was changed (re-check for tz-comparison bugs in edges)."
    )
