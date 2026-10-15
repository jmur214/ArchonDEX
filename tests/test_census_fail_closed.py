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


def _controller(alpha, *, counters=True, regime_detector=object()):
    """As a real run leaves it: __init__ sets n_resolved; the per-bar regime tally sets the regime
    counters on the first bar; a regime detector is wired. `counters=False` is a controller whose
    counters were NEVER set."""
    ctrl = object.__new__(BacktestController)
    ctrl.alpha = alpha
    ctrl.data_map = {"SPY": pd.DataFrame({"Close": [1.0]})}
    ctrl.regime_detector = regime_detector
    if counters:
        ctrl._census_n_resolved = 1
        ctrl._census_regime_total_bars, ctrl._census_regime_unknown_bars = 40, 3
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


# --------------------------------------------------------------------------- #
# NO silent zero (ruling 2026-10-15): n_resolved and the regime counters
# --------------------------------------------------------------------------- #
def test_a_counter_that_was_never_set_is_ABSENT_and_FAILS(tmp_path):
    """`getattr(..., 0)` + a gate that SKIPPED a 0 let a run that never set its counters pass
    invariants 2 and 5 unmeasured. Revert the getattr defaults → the keys read 0 → the gate skips."""
    census = _controller(_Alpha(), counters=False)._build_census(_trades(tmp_path))
    assert "n_resolved" not in census and "regime_total_bars" not in census
    v = _verdict(census)
    assert not v.canonical
    assert any("n_resolved: counter never set" in f for f in v.failures), v.failures
    assert any("regime_total_bars: counter never set" in f for f in v.failures), v.failures


@pytest.mark.parametrize("field, expect", [("n_resolved", "no universe"),
                                           ("regime_total_bars", "produced nothing")])
def test_a_measured_ZERO_fails_its_own_invariant(tmp_path, field, expect):
    """A measured 0 is not a skip: no universe / a regime layer that produced nothing. Revert the
    gate to its old skip-on-0 → passes."""
    ctrl = _controller(_Alpha())
    if field == "n_resolved":
        ctrl._census_n_resolved = 0
    else:
        ctrl._census_regime_total_bars, ctrl._census_regime_unknown_bars = 0, 0
    v = _verdict(ctrl._build_census(_trades(tmp_path)))
    assert not v.canonical
    assert any(expect in f for f in v.failures), v.failures


def test_a_regime_layer_OFF_is_DECLARED_and_canonical_only_with_the_pre_registration_label(
        tmp_path, monkeypatch):
    """No detector = the layer is OFF. Unlabelled → NON-CANONICAL (a different experiment). With
    CENSUS_REGIME_OFF_LABEL = the brief that declares it, the census carries the declaration AND the
    label, and the run is canonical — every bar was regime-unknown, by design."""
    monkeypatch.delenv("CENSUS_REGIME_OFF_LABEL", raising=False)
    ctrl = _controller(_Alpha(), regime_detector=None)
    ctrl._census_regime_total_bars, ctrl._census_regime_unknown_bars = 40, 40     # all unknown
    census = ctrl._build_census(_trades(tmp_path))
    assert census["regime_layer"] == "off" and "regime_off_label" not in census
    v = _verdict(census)
    assert not v.canonical and any("no pre-registered label" in f for f in v.failures), v.failures

    monkeypatch.setenv("CENSUS_REGIME_OFF_LABEL", "docs/Sources/some_brief_regime_off.md")
    census = ctrl._build_census(_trades(tmp_path))
    assert census["regime_off_label"] == "docs/Sources/some_brief_regime_off.md"
    v = _verdict(census)
    assert v.canonical, v.failures


def test_the_real_per_bar_tally_turns_an_UNSET_counter_into_a_SET_one():
    """The counters start None; `_detect_regime` (once per bar) sets them on the first bar.
    Revert the None start → a never-run tally reads as a measured 0 again."""
    ctrl = object.__new__(BacktestController)
    ctrl.regime_detector = None
    ctrl._census_regime_total_bars = ctrl._census_regime_unknown_bars = None
    ctrl._detect_regime(pd.Timestamp("2024-01-02"), {})
    assert (ctrl._census_regime_total_bars, ctrl._census_regime_unknown_bars) == (1, 1)


def test_a_GATE1_candidate_census_is_not_asked_for_backtest_counters():
    """Discovery's candidate census declares census_kind 'candidate' and carries no run-shape
    counters; the gate must not refuse it for their absence (it is not a backtest)."""
    from engines.engine_d_discovery.discovery import candidate_census_block

    class _C:
        nonzero_calls, errors = 5, 0
    block = candidate_census_block("cand_v1", _C(), n_trades=50)
    v = _verdict(block)
    assert v.canonical, v.failures          # the consequence first: an undeclared block is refused
    assert block.get("census_kind") == "candidate" and "n_resolved" not in block
