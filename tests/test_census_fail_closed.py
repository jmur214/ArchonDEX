"""tests/test_census_fail_closed.py — a census block that CRASHED is never a clean census.

Agent R (item-(d) review, 2026-10-15): `_build_census`'s edges block caught any exception and
wrote edges_blind=[] / edges_errored={} — PASSING values — plus `edges_blind_error`, which
`assert_census` never read. A crash inside the edges census therefore yielded a census that
passed invariants 1 and 1b. The fundamentals block had the identical shape (fundamentals_blind=0).

These locks DRIVE the real `BacktestController._build_census` with a crash planted inside the
block, then the real `assert_census` on the result. A healthy positive control runs the same
setup without the plant and must be CANONICAL — otherwise "NON-CANONICAL" could come from
some other invariant and the lock would hold vacuously.
"""
from __future__ import annotations

import pandas as pd
import pytest

from backtester.backtest_controller import BacktestController
from core.census import assert_census


class _Collector:
    _signal_counts = {"momentum_edge_v1": 12}
    _bars_collected = 40
    _edge_errors: dict = {}
    _edge_error_samples: dict = {}


class _Processor:
    paused_edge_ids: set = set()


class _Alpha:
    def __init__(self, edges=None):
        self.collector = _Collector()
        self.processor = _Processor()
        self.edges = edges if edges is not None else {"momentum_edge_v1": object()}


class _AlphaEdgesCensusCrashes(_Alpha):
    """Reading the signal collector raises — a crash INSIDE the edges census block."""
    def __getattribute__(self, name):
        if name == "collector":
            raise RuntimeError("planted crash inside the edges census")
        return object.__getattribute__(self, name)


def _controller(alpha):
    ctrl = object.__new__(BacktestController)
    ctrl.alpha = alpha
    ctrl.data_map = {"SPY": pd.DataFrame({"Close": [1.0]})}
    return ctrl


def _trades(tmp_path):
    p = tmp_path / "trades.csv"
    pd.DataFrame({"ticker": ["SPY", "SPY", "SPY"], "pnl": [1.0, -0.5, 2.0]}).to_csv(p, index=False)
    return str(p)


def _verdict(census):
    return assert_census({"census": census, "bootstrap_ci_skip_reason": "test"})


def test_POSITIVE_CONTROL_a_healthy_census_is_canonical(tmp_path):
    census = _controller(_Alpha())._build_census(_trades(tmp_path))
    v = _verdict(census)
    assert v.canonical, v.failures
    assert not [k for k in census if k.endswith("_error")]


def test_a_crash_inside_the_edges_census_makes_the_run_NON_CANONICAL(tmp_path):
    """Revert the gate's `_error` rule → the census carries only edges_blind_error, the gate
    ignores it, and the run reads CANONICAL."""
    census = _controller(_AlphaEdgesCensusCrashes())._build_census(_trades(tmp_path))
    assert "planted crash inside the edges census" in census["edges_blind_error"]
    assert "edges_blind" not in census and "edges_errored" not in census, \
        "the except branch must not write PASSING values"
    v = _verdict(census)
    assert not v.canonical
    assert any("edges_blind_error" in f for f in v.failures), v.failures


def test_a_crash_inside_the_fundamentals_census_makes_the_run_NON_CANONICAL(tmp_path, monkeypatch):
    """The audit's second instance: same shape, same lock."""
    import engines.engine_a_alpha.edges._fundamentals_helpers as fh

    def _boom():
        raise RuntimeError("planted crash inside the fundamentals census")
    monkeypatch.setattr(fh, "panel_is_blind", _boom)
    alpha = _Alpha(edges={"momentum_edge_v1": object(), "value_book_to_market_v1": object()})
    alpha.collector._signal_counts = {"momentum_edge_v1": 12, "value_book_to_market_v1": 7}
    census = _controller(alpha)._build_census(_trades(tmp_path))
    assert "planted crash" in census["fundamentals_blind_error"]
    assert "fundamentals_blind" not in census, "the except branch must not write the PASSING 0"
    v = _verdict(census)
    assert not v.canonical
    assert any("fundamentals_blind_error" in f for f in v.failures), v.failures


@pytest.mark.parametrize("n_trades", [-1, 0])
def test_an_unknown_or_zero_trade_count_is_never_a_traded_run(n_trades):
    """`n_trades=-1` is the trades block's 'count unknown' sentinel; the gate read it as valid
    (`== 0`). Revert to `== 0` → -1 passes."""
    v = _verdict({"edges_blind": [], "edges_errored": {}, "n_resolved": 1, "n_in_panel": 1,
                  "n_trades": n_trades, "trades_canon_md5": "0" * 32, "trades_empty": False,
                  "fundamentals_blind": 0, "regime_unknown_frac": 0.1, "regime_total_bars": 10,
                  "config_provenance": {"degraded": False}, "data_feed": {"yfinance_tickers": []},
                  "data_exclusions": {}})
    assert not v.canonical
