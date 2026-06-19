# core/trend_overlay.py
"""Trend overlay — a standalone long/flat absolute-momentum signal (T-204).

The homegrown, positive-skew analogue of the bought DBMF/KMLM managed-
futures sleeve (T-170): AQR "A Century of Evidence on Trend-Following"
(positively skewed, crisis-alpha; skew grows over horizon). It targets the
thing that actually loses to the Schwab robo — the −33% MDD — by stepping
a beta exposure to a defensive leg when price falls below its trend.

This module is a PURE SIGNAL GENERATOR. It is OFF by default and is NOT
wired into portfolio sizing — composing it into Engine C/B is a later,
propose-first step. It only emits the recommended long/flat exposure; the
consumer decides what to do with it.

Causality: ``exposure(close)`` returns ``signal_t = 1 if close_t > SMA_k_t``,
both as-of the day-``t`` close. To BACKTEST without lookahead, the position
held over day ``t+1`` is ``signal_t`` — i.e. apply ``signal.shift(1)`` to
next-day returns. The shift is the consumer's job (``overlay_returns``
below does it), so the raw signal stays an honest as-of-close state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np
import pandas as pd

# Pre-registered lookbacks (months → trading days). 10mo/210d ≈ the
# canonical AQR 200-day / 10-month rule.
LOOKBACK_DAYS: Dict[int, int] = {3: 63, 5: 105, 10: 210}


@dataclass(frozen=True)
class TrendOverlay:
    """A long/flat absolute-momentum overlay for ONE asset.

    lookback_days : the SMA window (price > SMA → long, else flat).
    enabled       : OFF by default — a guard so the overlay can ship dark
                    and only act when a composer explicitly turns it on.
    """
    lookback_days: int
    enabled: bool = False

    def trend(self, close: pd.Series) -> pd.Series:
        """Trailing simple moving average of close over ``lookback_days``."""
        return close.rolling(self.lookback_days, min_periods=self.lookback_days).mean()

    def exposure(self, close: pd.Series) -> pd.Series:
        """As-of-close long/flat signal: 1.0 when close > its trend, else
        0.0; NaN until the SMA is defined. When ``enabled`` is False the
        overlay is inert and recommends full exposure (1.0) on every
        defined bar — it must never silently de-risk a book that has not
        opted in. The validation harness constructs the overlay with
        ``enabled=True`` explicitly."""
        close = close.astype(float)
        ma = self.trend(close)
        if not self.enabled:
            sig = pd.Series(1.0, index=close.index)
            sig[ma.isna()] = np.nan
            return sig
        sig = (close > ma).astype(float)
        sig[ma.isna()] = np.nan
        return sig


def overlay_returns(
    close: pd.Series,
    lookback_days: int,
    *,
    defensive_returns: Optional[pd.Series] = None,
) -> pd.Series:
    """Daily returns of the long/flat overlay applied to ONE asset, with no
    lookahead (position over day t = signal_{t-1}).

    When "off" (signal 0) the capital earns ``defensive_returns`` if given
    (e.g. AGG), else 0.0 (cash). Returns are aligned to the asset's return
    index; bars before the SMA is defined are dropped.
    """
    close = close.astype(float)
    asset_ret = close.pct_change()
    sig = TrendOverlay(lookback_days, enabled=True).exposure(close)
    pos = sig.shift(1)                      # act on yesterday's signal
    if defensive_returns is None:
        strat = pos * asset_ret             # off → cash (0%)
    else:
        dfr = defensive_returns.reindex(asset_ret.index).fillna(0.0)
        strat = pos * asset_ret + (1.0 - pos) * dfr
    return strat.dropna()


def sleeve_returns(
    closes: Dict[str, pd.Series],
    lookback_days: int,
    *,
    weights: Optional[Dict[str, float]] = None,
) -> pd.Series:
    """Daily returns of an equal-weight diversified trend SLEEVE: each asset
    held long/flat (→ cash when off), rebalanced to its target weight by the
    signal each day. No lookahead. Assets default to equal weight."""
    keys = list(closes.keys())
    w = weights or {k: 1.0 / len(keys) for k in keys}
    parts = []
    for k in keys:
        r = overlay_returns(closes[k], lookback_days)   # off → cash
        parts.append(r.rename(k) * w[k])
    mat = pd.concat(parts, axis=1)
    # Sum across assets; require at least one asset defined on a bar.
    return mat.dropna(how="all").sum(axis=1, min_count=1).dropna()


def buy_hold_returns(close: pd.Series) -> pd.Series:
    """Buy-and-hold daily returns of one asset (the comparison baseline)."""
    return close.astype(float).pct_change().dropna()
