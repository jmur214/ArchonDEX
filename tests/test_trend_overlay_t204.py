# tests/test_trend_overlay_t204.py
"""T-204 — the trend overlay signal logic: threshold, OFF-default inertness,
and (the one that matters) NO lookahead.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.trend_overlay import (
    LOOKBACK_DAYS,
    TrendOverlay,
    buy_hold_returns,
    overlay_returns,
    sleeve_returns,
)


def _ramp_then_drop():
    # 10 up, then 10 down — a clean trend flip for threshold + causality.
    up = np.linspace(100, 120, 10)
    down = np.linspace(119, 100, 10)
    idx = pd.date_range("2020-01-01", periods=20, freq="B")
    return pd.Series(np.concatenate([up, down]), index=idx)


class TestSignal:
    def test_long_when_above_trend_flat_when_below(self):
        close = _ramp_then_drop()
        sig = TrendOverlay(lookback_days=3, enabled=True).exposure(close)
        # first 2 bars: SMA undefined → NaN
        assert sig.iloc[:2].isna().all()
        # during the up-ramp, close > rising SMA → long (1.0)
        assert sig.iloc[5] == 1.0
        # deep in the down-leg, close < SMA → flat (0.0)
        assert sig.iloc[-1] == 0.0

    def test_off_default_is_inert_full_exposure(self):
        close = _ramp_then_drop()
        sig = TrendOverlay(lookback_days=3).exposure(close)   # enabled=False
        defined = sig.dropna()
        assert (defined == 1.0).all()        # never silently de-risks
        assert sig.iloc[:2].isna().all()     # still NaN before SMA defined

    def test_nan_before_sma_defined(self):
        close = _ramp_then_drop()
        sig = TrendOverlay(lookback_days=5, enabled=True).exposure(close)
        assert sig.iloc[:4].isna().all()
        assert not np.isnan(sig.iloc[4])


class TestNoLookahead:
    def test_position_uses_prior_day_signal(self):
        close = _ramp_then_drop()
        k = 3
        sig = TrendOverlay(k, enabled=True).exposure(close)
        ret = close.pct_change()
        strat = overlay_returns(close, k)            # off -> cash
        # On every bar, the strategy return must equal sig_{t-1} * ret_t.
        expected = (sig.shift(1) * ret).dropna()
        pd.testing.assert_series_equal(strat, expected, check_names=False)

    def test_a_flip_does_not_use_same_day_signal(self):
        # If the signal flips to 0 at the close of day t (price crossed below
        # its MA), the LOSS of day t is still taken at the prior (long)
        # position — we cannot have acted on information not yet known.
        close = _ramp_then_drop()
        k = 3
        sig = TrendOverlay(k, enabled=True).exposure(close)
        strat = overlay_returns(close, k)
        flips = sig.index[(sig == 0.0) & (sig.shift(1) == 1.0)]
        assert len(flips) >= 1
        t = flips[0]
        ret_t = close.pct_change().loc[t]
        # position over day t is the prior LONG signal (1.0) → full asset return
        assert np.isclose(strat.loc[t], 1.0 * ret_t)


class TestDefensiveLegAndSleeve:
    def test_cash_vs_bond_defensive_leg_differ_when_off(self):
        close = _ramp_then_drop()
        bonds = pd.Series(0.001, index=close.index)   # +10bps/day defensive
        cash = overlay_returns(close, 3)
        bond = overlay_returns(close, 3, defensive_returns=bonds)
        # while flat, the bond-leg earns the defensive return, cash earns 0
        assert (bond.loc[cash == 0.0] > 0).any()
        assert (cash.loc[cash == 0.0] == 0.0).all()

    def test_sleeve_equal_weight_sums_components(self):
        a = _ramp_then_drop()
        b = _ramp_then_drop() * 1.01
        closes = {"A": a, "B": b}
        sleeve = sleeve_returns(closes, 3)
        ra = overlay_returns(a, 3) * 0.5
        rb = overlay_returns(b, 3) * 0.5
        expected = pd.concat([ra, rb], axis=1).dropna(how="all").sum(axis=1, min_count=1).dropna()
        pd.testing.assert_series_equal(sleeve, expected, check_names=False)


class TestDeterminism:
    def test_same_input_same_output(self):
        close = _ramp_then_drop()
        r1 = overlay_returns(close, LOOKBACK_DAYS[10] if len(close) > 210 else 3)
        r2 = overlay_returns(close, LOOKBACK_DAYS[10] if len(close) > 210 else 3)
        pd.testing.assert_series_equal(r1, r2)

    def test_buy_hold_is_plain_pct_change(self):
        close = _ramp_then_drop()
        pd.testing.assert_series_equal(buy_hold_returns(close), close.pct_change().dropna())
