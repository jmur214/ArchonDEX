# tests/test_sleeve_btc_t288.py
"""T-288 fleet Account 3 — the BTC-augmented sleeve (T-272): 95% ensemble sleeve
+ 5% IBIT, each gated by its own {2,5,10}mo ensemble trend, cash off.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from paper_trader.sleeve_btc_constructor import (BTC_LEG_WEIGHT, SleeveBtcConstructor,
                                                 _base_weights)


def _series(vals):
    idx = pd.date_range("2020-01-01", periods=len(vals), freq="B")
    return pd.Series(np.asarray(vals, float), index=idx)


def _up(n=40):
    return _series(np.linspace(100, 200, n))


def _down(n=40):
    return _series(np.linspace(200, 100, n))


def _c():
    return SleeveBtcConstructor(speeds=(5, 10, 20), deadband=0.10)


class TestSleeveBtc:
    def test_base_weights_sleeve95_ibit5(self):
        w = _base_weights()
        assert w["IBIT"] == pytest.approx(0.05)
        assert sum(w[t] for t in ("SPY", "AGG", "GLD")) == pytest.approx(0.95)
        assert w["SPY"] == pytest.approx(0.95 / 3)

    def test_all_on_targets_and_buys(self):
        closes = {t: _up() for t in ("SPY", "AGG", "GLD", "IBIT")}
        plan = _c().construct(10000.0, {}, closes)
        assert all(plan.signals[t] == 1.0 for t in ("SPY", "AGG", "GLD", "IBIT"))
        assert plan.targets["SPY"] == pytest.approx(0.95 / 3, abs=1e-3)
        assert plan.targets["IBIT"] == pytest.approx(0.05, abs=1e-3)
        # full-exposure target weights sum to 100% (95% sleeve + 5% IBIT)
        assert sum(plan.targets.values()) == pytest.approx(1.0, abs=2e-3)
        assert len(plan.orders) == 4 and all(o.side == "buy" and o.edge == "sleeve_btc"
                                             for o in plan.orders)

    def test_ibit_trend_off_flips_to_cash(self):
        closes = {"SPY": _up(), "AGG": _up(), "GLD": _up(), "IBIT": _down()}
        plan = _c().construct(10000.0, {"IBIT": 5}, closes)
        assert plan.signals["IBIT"] == 0.0 and plan.targets["IBIT"] == 0.0
        ibit = [o for o in plan.orders if o.ticker == "IBIT"][0]
        assert ibit.side == "sell" and ibit.qty == 5 and ibit.engine_side == "exit"

    def test_ibit_qty_is_5pct_leg(self):
        # IBIT priced $50, $10k cap, exposure 1 → 0.05*10000/50 = 10 shares
        closes = {"SPY": _up(), "AGG": _up(), "GLD": _up(),
                  "IBIT": _series(np.concatenate([np.linspace(20, 50, 39), [50.0]]))}
        plan = _c().construct(10000.0, {}, closes)
        assert plan.target_qty["IBIT"] == int(np.floor(0.05 * 10000.0 / 50.0))

    def test_off_from_flat_is_cash(self):
        closes = {t: _down() for t in ("SPY", "AGG", "GLD", "IBIT")}
        plan = _c().construct(10000.0, {}, closes)
        assert all(v == 0.0 for v in plan.signals.values())
        assert plan.orders == []

    def test_fail_closed_short_history(self):
        closes = {"SPY": _up(5), "AGG": _up(), "GLD": _up(), "IBIT": _up()}
        with pytest.raises(ValueError):
            _c().construct(10000.0, {}, closes)

    def test_tif_flows_to_orders(self):
        closes = {t: _up() for t in ("SPY", "AGG", "GLD", "IBIT")}
        plan = SleeveBtcConstructor(speeds=(5, 10, 20), tif="day").construct(10000.0, {}, closes)
        assert plan.orders and all(o.tif == "day" for o in plan.orders)
