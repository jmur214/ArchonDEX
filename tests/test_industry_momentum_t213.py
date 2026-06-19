"""T-213 unit tests — industry/sector momentum (sector-neutral).

Deterministic, fixture-fed. Verifies 12-1 momentum, dollar-neutral
long-top-K/short-bottom-K construction, and abstention below the
two-leg floor.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from engines.engine_a_alpha.screens import industry_momentum as im


def _series_with_total_return(total_ret: float, n: int = 300) -> pd.Series:
    """Build a price series whose 12-1 (t-252..t-21) return equals total_ret,
    flat in the skipped last 21 bars so the skip doesn't change it."""
    idx = pd.bdate_range("2020-01-01", periods=n)
    p = np.ones(n)
    # ramp from bar (n-1-252) to (n-1-21); flat before and after.
    start_i, end_i = n - 1 - 252, n - 1 - 21
    p[:start_i] = 1.0
    p[start_i:end_i + 1] = np.linspace(1.0, 1.0 + total_ret, end_i + 1 - start_i)
    p[end_i + 1:] = 1.0 + total_ret
    return pd.Series(p, index=idx)


def test_momentum_12_1_value():
    s = _series_with_total_return(0.30)
    m = im.momentum_12_1(s, s.index[-1])
    assert m is not None and abs(m - 0.30) < 1e-6


def test_momentum_insufficient_history_none():
    idx = pd.bdate_range("2020-01-01", periods=100)
    s = pd.Series(np.linspace(1, 2, 100), index=idx)
    assert im.momentum_12_1(s, s.index[-1]) is None


def test_weights_dollar_neutral_top_bottom():
    # 9 sectors with monotically increasing 12-1 momentum.
    rets = {sec: 0.05 * (i + 1) for i, sec in enumerate(im.GICS9)}
    closes = {sec: _series_with_total_return(r) for sec, r in rets.items()}
    asof = next(iter(closes.values())).index[-1]
    w = im.sector_momentum_weights(closes, asof, top_k=3)
    assert abs(sum(w.values())) < 1e-9, "must be dollar-neutral"
    longs = [s for s, x in w.items() if x > 0]
    shorts = [s for s, x in w.items() if x < 0]
    assert len(longs) == 3 and len(shorts) == 3
    # Top-3 momentum = last 3 GICS9 entries (highest rets); bottom-3 = first 3.
    assert set(longs) == set(im.GICS9[-3:]), longs
    assert set(shorts) == set(im.GICS9[:3]), shorts
    assert all(abs(x) == 1.0 / 3 for x in w.values() if x != 0)


def test_abstains_below_two_leg_floor():
    # Only 4 sectors computable, top_k=3 needs 6 → abstain.
    closes = {sec: _series_with_total_return(0.1) for sec in im.GICS9[:4]}
    asof = next(iter(closes.values())).index[-1]
    assert im.sector_momentum_weights(closes, asof, top_k=3) == {}


def test_not_wired_into_prod_path():
    # OFF-by-construction guard: the backtest path must not import this.
    import importlib.util
    src = importlib.util.find_spec("backtester.backtest_controller").origin
    assert "industry_momentum" not in open(src).read()
