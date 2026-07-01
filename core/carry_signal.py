# core/carry_signal.py
"""Cross-asset time-series CARRY sleeve (T-247).

Carry = the return an asset earns if its price does not move (the yield you are
paid to hold it). This is the natural return-side complement to the trend sleeve
(T-236): carry is the return engine, trend is the crash hedge for carry's
liquidation risk. Koijen-Moskowitz-Pedersen-Vrugt, "Carry" (JFE 2018).

This is a PURE SIGNAL GENERATOR. It is OFF by default and is NOT wired into
portfolio sizing — composing it into Engine C/B is a later, propose-first step.
It mirrors ``core/trend_overlay.py``: per-asset long/flat state, equal-weight
sleeve, causal (position held over day ``t+1`` is ``signal_t``), and it FAILS
CLOSED — an asset whose carry input is not available on disk is EXCLUDED from the
sleeve, never faked with a plausible number (`[NN-FAIL-CLOSED]`).

Carry definitions (causal, from on-disk FRED + price data only):
  - Bond / duration (AGG, IEF, TLT, …): carry = yield-curve slope
    ``DGS10 − DGS3MO``. A positive slope is positive carry + roll-down; an
    inverted curve is negative carry (and a recession signal) → step to cash.
  - Gold (GLD, IAU): carry = ``−(real short rate) = −(DGS3MO − T10YIE)``.
    Non-yielding gold's carry is the negative real financing cost; a negative
    real rate → positive gold carry.

Assets whose carry needs data NOT on disk — equity earnings/dividend yield,
commodity roll yield (futures curve), FX rate-differentials — are NOT faked. The
constructor omits them (fail-closed). The T-247 pre-registration + the data-gap
finding live in ``scripts/carry_sleeve_gauntlet_t247.py``.

Causality: ``carry_t`` uses FRED values as-of day ``t`` (a slow macro state,
forward-filled onto the price calendar until it next prints); the position held
over day ``t+1`` is ``signal_t``. The return functions apply ``.shift(1)`` so the
raw signal stays an honest as-of-close state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional

import numpy as np
import pandas as pd

# Asset → carry-source class. Extend as longer diversifier histories are sourced.
BOND_ASSETS: frozenset[str] = frozenset({"AGG", "IEF", "TLT", "BND", "GOVT", "SCHZ"})
GOLD_ASSETS: frozenset[str] = frozenset({"GLD", "IAU", "SGOL"})


def bond_carry(dgs10: pd.Series, dgs3mo: pd.Series) -> pd.Series:
    """Yield-curve slope (10y − 3m), percent. >0 → positive bond carry+roll-down."""
    return (dgs10.astype(float) - dgs3mo.astype(float)).dropna()


def gold_carry(dgs3mo: pd.Series, t10yie: pd.Series) -> pd.Series:
    """−(real short rate) = −(nominal 3m − breakeven inflation). >0 → positive gold carry."""
    return (-(dgs3mo.astype(float) - t10yie.astype(float))).dropna()


def build_carries(
    assets: Iterable[str], macro: Mapping[str, pd.Series]
) -> Dict[str, pd.Series]:
    """Map each known asset to its causal carry series from on-disk macro data.

    ``macro`` holds FRED Series keyed by name (``DGS10``/``DGS3MO``/``T10YIE``).
    Fail-closed: an asset whose carry class or required series is unavailable is
    omitted from the result (it will be excluded from the sleeve, not faked)."""
    out: Dict[str, pd.Series] = {}
    for a in assets:
        if a in BOND_ASSETS and "DGS10" in macro and "DGS3MO" in macro:
            out[a] = bond_carry(macro["DGS10"], macro["DGS3MO"])
        elif a in GOLD_ASSETS and "DGS3MO" in macro and "T10YIE" in macro:
            out[a] = gold_carry(macro["DGS3MO"], macro["T10YIE"])
        # else: no defined on-disk carry source → omit (fail-closed)
    return out


@dataclass(frozen=True)
class CarrySignal:
    """Long/flat carry state for ONE asset from its carry estimate.

    ``carry > threshold`` → long (1.0); else flat (0.0 → cash). OFF-default: when
    ``enabled`` is False the signal is inert (recommends full 1.0 exposure) and
    never silently de-risks a book that has not opted in. The validation harness
    constructs it with ``enabled=True`` explicitly.
    """

    threshold: float = 0.0
    enabled: bool = False

    def exposure(self, carry: pd.Series, index: pd.Index) -> pd.Series:
        """As-of-day carry → long/flat, forward-filled onto the price ``index``.

        Carry is a slow macro state valid until it next prints, so ffill is the
        causal reindex (uses only the last-known value). NaN before the carry
        series begins → NaN signal (that bar is dropped, never traded blind)."""
        c = (
            carry.reindex(carry.index.union(index))
            .sort_index()
            .ffill()
            .reindex(index)
        )
        if not self.enabled:
            sig = pd.Series(1.0, index=index)
            sig[c.isna()] = np.nan
            return sig
        sig = (c > self.threshold).astype(float)
        sig[c.isna()] = np.nan
        return sig


def carry_overlay_returns(
    close: pd.Series,
    carry: pd.Series,
    *,
    threshold: float = 0.0,
    defensive_returns: Optional[pd.Series] = None,
) -> pd.Series:
    """Daily returns of the long/flat carry overlay on ONE asset, no lookahead
    (position over day ``t`` = ``signal_{t-1}``). When flat, capital earns
    ``defensive_returns`` if given (e.g. cash@rf), else 0.0."""
    close = close.astype(float)
    asset_ret = close.pct_change()
    sig = CarrySignal(threshold, enabled=True).exposure(carry, close.index)
    pos = sig.shift(1)  # act on yesterday's carry state
    if defensive_returns is None:
        strat = pos * asset_ret
    else:
        dfr = defensive_returns.reindex(asset_ret.index).fillna(0.0)
        strat = pos * asset_ret + (1.0 - pos) * dfr
    return strat.dropna()


def carry_sleeve_returns(
    closes: Mapping[str, pd.Series],
    carries: Mapping[str, pd.Series],
    *,
    threshold: float = 0.0,
    weights: Optional[Dict[str, float]] = None,
    cash_returns: Optional[pd.Series] = None,
) -> pd.Series:
    """Daily returns of an equal-weight cross-asset carry SLEEVE: each asset held
    long/flat, rebalanced by its carry each day, no lookahead. When an asset is
    flat (carry ≤ threshold) its weight earns ``cash_returns`` (the risk-free /
    short rate — carry's flat leg is cash, NOT a 0% drag); None → 0.0.
    FAIL-CLOSED: only assets present in BOTH ``closes`` and ``carries`` (with a
    non-empty carry series) are traded; an asset with no defined carry is
    excluded, not faked."""
    keys = [
        k
        for k in closes
        if k in carries and carries[k] is not None and len(carries[k]) > 0
    ]
    if not keys:
        raise ValueError(
            "carry_sleeve_returns: no asset has a defined carry series (fail-closed)"
        )
    w = weights or {k: 1.0 / len(keys) for k in keys}
    parts = []
    for k in keys:
        r = carry_overlay_returns(
            closes[k], carries[k], threshold=threshold, defensive_returns=cash_returns
        )
        parts.append(r.rename(k) * w[k])
    mat = pd.concat(parts, axis=1)
    return mat.dropna(how="all").sum(axis=1, min_count=1).dropna()


def buy_hold_returns(close: pd.Series) -> pd.Series:
    """Buy-and-hold daily returns of one asset (the static-exposure baseline)."""
    return close.astype(float).pct_change().dropna()
