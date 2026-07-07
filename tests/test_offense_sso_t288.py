# tests/test_offense_sso_t288.py
"""T-288 fleet Account 2 — the trend-gated 2× SSO offense (T-284 PRIMARY):
SPY {2,5,10}mo ensemble exposure → hold SSO at that weight (2× SPY when fully
on), cash off. Signal on SPY (underlying), price/qty off SSO (traded).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from paper_trader.offense_sso_constructor import OffenseSSOConstructor


def _series(vals):
    idx = pd.date_range("2020-01-01", periods=len(vals), freq="B")
    return pd.Series(np.asarray(vals, float), index=idx)


def _up(n=40):
    return _series(np.linspace(100, 200, n))


def _down(n=40):
    return _series(np.linspace(200, 100, n))


def _c():
    return OffenseSSOConstructor(speeds=(5, 10, 20), deadband=0.10)


class TestOffenseSSO:
    def test_fully_on_buys_sso_to_full_weight(self):
        spy, sso = _up(), _series(np.linspace(60, 80, 40))   # SSO ends at 80
        plan = _c().construct(10000.0, {}, {"SPY": spy, "SSO": sso})
        assert plan.signals["SPY"] == 1.0 and plan.targets["SSO"] == 1.0
        o = [o for o in plan.orders if o.ticker == "SSO"][0]
        assert o.side == "buy" and o.qty == int(np.floor(10000.0 / 80.0)) and o.edge == "offense_sso"

    def test_off_is_cash_from_flat(self):
        spy, sso = _down(), _series(np.linspace(80, 60, 40))
        plan = _c().construct(10000.0, {}, {"SPY": spy, "SSO": sso})
        assert plan.signals["SPY"] == 0.0 and plan.targets["SSO"] == 0.0
        assert plan.orders == []                              # flat → flat, cash off-leg

    def test_off_flips_out_of_held_sso(self):
        spy, sso = _down(), _series(np.linspace(80, 60, 40))
        plan = _c().construct(10000.0, {"SSO": 100}, {"SPY": spy, "SSO": sso})
        o = [o for o in plan.orders if o.ticker == "SSO"][0]
        assert o.side == "sell" and o.qty == 100 and o.engine_side == "exit"

    def test_fractional_gate_scales_sso_weight(self):
        # long SPY decline then rebound → the 3 speeds disagree → exposure ⅔
        spy = _series(np.concatenate([np.linspace(200, 100, 100), np.linspace(100, 120, 22)]))
        sso = _series(np.linspace(60, 80, 122))
        c = OffenseSSOConstructor(speeds=(5, 30, 90), deadband=0.0)
        plan = c.construct(10000.0, {}, {"SPY": spy, "SSO": sso})
        assert plan.signals["SPY"] == pytest.approx(2 / 3)
        assert plan.targets["SSO"] == pytest.approx(2 / 3, abs=1e-3)   # SSO weight = the gate

    def test_signal_on_spy_price_on_sso(self):
        spy, sso = _up(), _series(np.full(40, 100.0))        # SSO flat @ 100
        plan = _c().construct(10000.0, {}, {"SPY": spy, "SSO": sso})
        assert plan.target_qty["SSO"] == int(np.floor(10000.0 / 100.0))

    def test_fail_closed_on_short_spy_history(self):
        with pytest.raises(ValueError):
            _c().construct(10000.0, {}, {"SPY": _up(5), "SSO": _series(np.linspace(60, 80, 40))})

    def test_fail_closed_on_missing_sso_price(self):
        with pytest.raises(ValueError):
            _c().construct(10000.0, {}, {"SPY": _up()})       # no SSO price

    def test_deadband_suppresses_small_nonflip(self):
        spy, sso = _up(), _series(np.full(40, 80.0))
        held = int(np.floor(10000.0 / 80.0))                 # already at target
        plan = _c().construct(10000.0, {"SSO": held}, {"SPY": spy, "SSO": sso})
        assert plan.orders == []

    def test_tif_flows_to_orders(self):
        spy, sso = _up(), _series(np.linspace(60, 80, 40))
        plan = OffenseSSOConstructor(speeds=(5, 10, 20), tif="day").construct(
            10000.0, {}, {"SPY": spy, "SSO": sso})
        assert plan.orders and all(o.tif == "day" for o in plan.orders)
