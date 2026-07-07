# paper_trader/sleeve_btc_constructor.py
"""SleeveBtcConstructor — the BTC-augmented sleeve as a paper-loop content layer
(T-272 arm traded for real, T-288 fleet Account 3).

The deploying ensemble sleeve (95%) + a 5% IBIT leg under the SAME {2,5,10}mo
trend rule (T-272): each asset held at its own ensemble exposure {0,⅓,⅔,1},
cash off. Construction mirrors T-272's
    variant = (1 − 0.05) · sleeve  +  0.05 · trend_ruled_btc_leg
so the three defensive assets share 95% equal-weight and IBIT takes 5%; every
leg is gated long/flat by its OWN ensemble trend.

**Signal on IBIT itself** (the traded ETF), not BTC-USD: IBIT is executable in
the lean image via the same ETF close path, and comparing this account's
IBIT-signal track to the report-only BtcShadowTracker (which reads BTC-USD 24/7)
IS the live construction/basis check the fleet spec asks for — divergence is a
tracker-math bug or a wrapper-basis drift to flag ([NN-SUBSTRATE-REVERIFY]).

Reuses `SleeveOrderConstructor.latest_signal` by composition (the defensive
sleeve module is byte-unchanged). Whole shares, cash off-legs, Carver deadband,
FAIL-CLOSED on short history. EXPLORATORY per T-272 ([NN-MBL]: 11yr = one bull
era; IBIT wrapper only ~2.5yr) — paper Account 3 forward-validates EXECUTION +
the IBIT-vs-spot basis, NOT the wealth claim.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

from paper_trader.order_construction import OrderSpec
from paper_trader.sleeve_constructor import SLEEVE_SPEEDS, SleeveOrderConstructor

SLEEVE_ASSETS = ("SPY", "AGG", "GLD")
BTC_TICKER = "IBIT"
SLEEVE_BTC_UNIVERSE = SLEEVE_ASSETS + (BTC_TICKER,)
BTC_LEG_WEIGHT = 0.05                       # T-272 frozen: 5% BTC leg
SLEEVE_BTC_SPEEDS = SLEEVE_SPEEDS           # {42,105,210}d — the same ensemble
SLEEVE_BTC_DEADBAND = 0.10


def _base_weights() -> Dict[str, float]:
    """Per-asset FULL-exposure weight: the 3 sleeve assets share (1−5%) equal-
    weight, IBIT takes 5%. Multiplied by each asset's ensemble exposure."""
    ew = (1.0 - BTC_LEG_WEIGHT) / len(SLEEVE_ASSETS)
    w = {t: ew for t in SLEEVE_ASSETS}
    w[BTC_TICKER] = BTC_LEG_WEIGHT
    return w


@dataclass
class SleeveBtcPlan:
    orders: List[OrderSpec]
    targets: Dict[str, float] = field(default_factory=dict)
    target_qty: Dict[str, int] = field(default_factory=dict)
    held_qty: Dict[str, int] = field(default_factory=dict)
    signals: Dict[str, float] = field(default_factory=dict)      # per-asset exposure {0,⅓,⅔,1}


class SleeveBtcConstructor:
    def __init__(self, universe=SLEEVE_BTC_UNIVERSE, speeds=SLEEVE_BTC_SPEEDS,
                 deadband: float = SLEEVE_BTC_DEADBAND, tif: str = "day"):
        self.universe = tuple(universe)
        self.speeds = tuple(int(s) for s in speeds)
        self.deadband = float(deadband)
        self.tif = tif
        self._base = _base_weights()
        self._signal = SleeveOrderConstructor(speeds=self.speeds)   # reuse the ensemble

    def construct(self, equity: float, current_positions: Dict[str, int],
                  closes: Dict[str, pd.Series]) -> SleeveBtcPlan:
        """95% ensemble sleeve + 5% IBIT, each gated by its own ensemble trend.
        Sizing off ``equity`` (the caller passes min(account_equity, cap))."""
        plan = SleeveBtcPlan(orders=[])
        for tkr in self.universe:
            close = closes.get(tkr)
            if close is None or len(close.dropna()) < max(self.speeds):
                raise ValueError(f"[NN-FAIL-CLOSED] {tkr}: missing/short price history")
            exposure = self._signal.latest_signal(close)     # fractional {0,⅓,⅔,1}
            last_px = float(close.dropna().iloc[-1])
            if last_px <= 0:
                raise ValueError(f"[NN-FAIL-CLOSED] {tkr}: non-positive last price")

            target_w = self._base[tkr] * exposure             # base weight × its own trend
            target_qty = int(math.floor(equity * target_w / last_px))
            held = int(current_positions.get(tkr, 0))
            held_w = held * last_px / equity if equity > 0 else 0.0
            plan.signals[tkr] = exposure
            plan.targets[tkr] = round(target_w, 4)
            plan.target_qty[tkr] = target_qty
            plan.held_qty[tkr] = held

            flip = (target_qty == 0 and held > 0) or (target_qty > 0 and held == 0)
            if not flip and abs(target_w - held_w) < self.deadband:
                continue
            delta = target_qty - held
            if delta == 0:
                continue
            plan.orders.append(OrderSpec(
                ticker=tkr, side=("buy" if delta > 0 else "sell"), qty=abs(delta),
                tif=self.tif, engine_side=("long" if delta > 0 else "exit"),
                edge="sleeve_btc"))
        return plan
