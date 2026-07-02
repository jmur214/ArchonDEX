# tests/test_sleeve_paper_t238.py
"""T-238 — the trend-sleeve paper content layer: order construction (signal →
EW target → whole-share delta), Carver deadband / flip, fail-closed on short
history, and the forward-tracker vs both robos.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from paper_trader.sleeve_constructor import SleeveOrderConstructor
from paper_trader.sleeve_tracker import SleeveTracker


def _series(values):
    idx = pd.date_range("2020-01-01", periods=len(values), freq="B")
    return pd.Series(np.asarray(values, float), index=idx)


def _up(n=40):    # rising → close > its trailing SMA → signal 1 (long)
    return _series(np.linspace(100, 200, n))


def _down(n=40):  # falling → close < SMA → signal 0 (flat)
    return _series(np.linspace(200, 100, n))


class TestConstructor:
    def _c(self):
        return SleeveOrderConstructor(universe=("SPY", "AGG", "GLD"),
                                      lookback=10, deadband=0.10)

    def test_all_long_from_flat_buys_equal_weight(self):
        closes = {"SPY": _up(), "AGG": _up(), "GLD": _up()}
        plan = self._c().construct(equity=30000.0, current_positions={}, closes=closes)
        # each asset signal long → target ~1/3 each; from flat → 3 buys
        assert all(plan.signals[t] == 1.0 for t in ("SPY", "AGG", "GLD"))
        sides = {o.ticker: (o.side, o.qty) for o in plan.orders}
        assert len(plan.orders) == 3 and all(s[0] == "buy" for s in sides.values())
        # ~$10k / $200 last price = 50 shares each
        assert sides["SPY"][1] == 50

    def test_flat_signal_flips_out_of_a_held_position(self):
        closes = {"SPY": _down(), "AGG": _up(), "GLD": _up()}
        plan = self._c().construct(equity=30000.0,
                                   current_positions={"SPY": 50, "AGG": 50, "GLD": 50},
                                   closes=closes)
        assert plan.signals["SPY"] == 0.0            # SPY below trend → flat
        spy = [o for o in plan.orders if o.ticker == "SPY"][0]
        assert spy.side == "sell" and spy.qty == 50  # flip out fully
        assert spy.engine_side == "exit"

    def test_deadband_suppresses_a_small_nonflip_rebalance(self):
        closes = {"SPY": _up(), "AGG": _up(), "GLD": _up()}
        # already holding ~the target (50 each at $200, equity 30k → w≈0.333)
        plan = self._c().construct(equity=30000.0,
                                   current_positions={"SPY": 50, "AGG": 50, "GLD": 50},
                                   closes=closes)
        assert plan.orders == []                     # within deadband, no churn

    def test_fail_closed_on_short_history(self):
        closes = {"SPY": _up(5), "AGG": _up(), "GLD": _up()}   # SPY too short for lookback 10
        with pytest.raises(ValueError):
            self._c().construct(30000.0, {}, closes)

    def test_off_leg_is_cash_not_a_short(self):
        closes = {"SPY": _down(), "AGG": _down(), "GLD": _down()}
        plan = self._c().construct(30000.0, {}, closes)
        assert all(v == 0.0 for v in plan.signals.values())
        assert all(plan.target_qty[t] == 0 for t in ("SPY", "AGG", "GLD"))
        assert plan.orders == []                     # flat from flat → nothing (cash)


class TestTracker:
    def test_one_day_is_accruing(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        s = t.record("2026-06-26", 30000.0, {"SPY": 200.0, "AGG": 100.0, "GLD": 150.0})
        assert s["status"] == "accruing" and s["n_days"] == 1

    def test_two_days_summarizes_sleeve_and_both_robos(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        t.record("2026-06-26", 30000.0, {"SPY": 200.0, "AGG": 100.0, "GLD": 150.0})
        s = t.record("2026-06-29", 30300.0, {"SPY": 202.0, "AGG": 100.0, "GLD": 151.0})
        assert s["status"] == "tracking"
        assert "max_drawdown" in s["sleeve"]
        assert set(s["robos"]) == {"60_40", "schwab_like"}
        assert "sleeve_mdd_shallower_than_both" in s

    def test_record_is_idempotent_on_date(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        t.record("2026-06-26", 30000.0, {"SPY": 200.0, "AGG": 100.0, "GLD": 150.0})
        t.record("2026-06-26", 30000.0, {"SPY": 200.0, "AGG": 100.0, "GLD": 150.0})
        import json
        pts = json.loads((tmp_path / "trk.json").read_text())["points"]
        assert len(pts) == 1                         # same date overwrites

    def test_bare_3arg_record_has_no_exec_block(self, tmp_path):
        """Default-OFF behavior is byte-unchanged: no execution_gates when the
        driver passes no execution data (existing non-sleeve callers)."""
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        s = t.record("2026-06-26", 30000.0, {"SPY": 200.0, "AGG": 100.0, "GLD": 150.0})
        assert "execution_gates" not in s
        import json
        pt = json.loads((tmp_path / "trk.json").read_text())["points"][0]
        assert "exec" not in pt


class TestExecutionGates:
    """T-238 pre-registered EXECUTION-fidelity gates (report-only)."""
    CLOSES = {"SPY": 200.0, "AGG": 100.0, "GLD": 150.0}

    def _rec(self, t, date, **kw):
        return t.record(date, 30000.0, self.CLOSES,
                        target_weights={"SPY": 1/3, "AGG": 1/3, "GLD": 1/3}, **kw)

    def test_exec_block_and_gates_appear_when_execution_data_supplied(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        s = self._rec(t, "2026-06-26",
                      held_weights={"SPY": 1/3, "AGG": 1/3, "GLD": 1/3})
        assert "execution_gates" in s
        g = s["execution_gates"]
        assert set(g["gates"]) == {"a_tracking_error", "b_slippage_bps",
                                   "c_order_errors", "d_clean_days"}
        # explicit "performance not confirmable in-window" framing rides along
        assert "not validated edge" in g["note"].lower() or \
               "not confirmable" in g["note"].lower()

    def test_tracking_error_passes_when_held_matches_target(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        g = self._rec(t, "2026-06-26",
                      held_weights={"SPY": 1/3, "AGG": 1/3, "GLD": 1/3})["execution_gates"]
        assert g["gates"]["a_tracking_error"]["status"] == "pass"
        assert g["gates"]["a_tracking_error"]["median"] == 0.0

    def test_tracking_error_fails_on_large_drift(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        # held is all SPY → Σ|held−target| = |1−1/3| + 1/3 + 1/3 = 1.33 ≫ 5% p95
        g = self._rec(t, "2026-06-26",
                      held_weights={"SPY": 1.0, "AGG": 0.0, "GLD": 0.0})["execution_gates"]
        assert g["gates"]["a_tracking_error"]["status"] == "fail"
        assert g["overall"] == "fail"

    def test_slippage_gate_pass_and_fail(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        hw = {"SPY": 1/3, "AGG": 1/3, "GLD": 1/3}
        good = self._rec(t, "2026-06-26", held_weights=hw, slippage_bps=2.0)
        assert good["execution_gates"]["gates"]["b_slippage_bps"]["status"] == "pass"
        bad = self._rec(t, "2026-06-29", held_weights=hw, slippage_bps=40.0)
        assert bad["execution_gates"]["gates"]["b_slippage_bps"]["status"] == "fail"

    def test_slippage_gate_accruing_when_no_fills(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        g = self._rec(t, "2026-06-26",
                      held_weights={"SPY": 1/3, "AGG": 1/3, "GLD": 1/3})["execution_gates"]
        assert g["gates"]["b_slippage_bps"]["status"] == "accruing"

    def test_order_error_gate_fails_on_any_error(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        hw = {"SPY": 1/3, "AGG": 1/3, "GLD": 1/3}
        g = self._rec(t, "2026-06-26", held_weights=hw, order_errors=1)["execution_gates"]
        assert g["gates"]["c_order_errors"]["status"] == "fail"
        assert g["gates"]["c_order_errors"]["count"] == 1
        assert g["overall"] == "fail"

    def test_clean_days_accrues_toward_60_then_passes(self, tmp_path):
        from paper_trader.sleeve_tracker import GATE_MIN_CLEAN_DAYS
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        hw = {"SPY": 1/3, "AGG": 1/3, "GLD": 1/3}
        s = self._rec(t, "2026-06-26", held_weights=hw)
        assert s["execution_gates"]["gates"]["d_clean_days"]["status"] == "accruing"
        # fill exactly GATE_MIN_CLEAN_DAYS canonical days → passes
        for i in range(1, GATE_MIN_CLEAN_DAYS):
            s = self._rec(t, f"2026-07-{i:02d}" if i < 31 else f"2026-08-{i-30:02d}",
                          held_weights=hw)
        assert s["execution_gates"]["gates"]["d_clean_days"]["count"] == GATE_MIN_CLEAN_DAYS
        assert s["execution_gates"]["gates"]["d_clean_days"]["status"] == "pass"

    def test_execution_gates_method_reads_persisted_state(self, tmp_path):
        t = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path))
        self._rec(t, "2026-06-26", held_weights={"SPY": 1/3, "AGG": 1/3, "GLD": 1/3},
                  slippage_bps=3.0)
        g = SleeveTracker(path=str(tmp_path / "trk.json"), root=str(tmp_path)).execution_gates()
        assert g["gates"]["b_slippage_bps"]["n"] == 1
        assert g["overall"] in {"pass", "accruing", "fail"}
