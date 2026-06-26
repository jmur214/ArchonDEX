# paper_trader/sleeve_constructor.py
"""SleeveOrderConstructor — the trend-sleeve as the paper-loop content layer (T-238).

The validated 3-asset trend sleeve (T-204/T-236) is the first strategy cleared
for paper validation. It is FAR simpler than the equity book: an equal-weight
SPY/AGG/GLD long-flat 5-month absolute-momentum overlay. This module turns it
into the daily order set the cloud paper loop submits — reusing the validated
signal from `core/trend_overlay.py` (forks nothing).

Causality: the loop runs in the morning (OPG window). The latest COMPLETE
daily bar is yesterday's close, so the latest `TrendOverlay.exposure` value IS
yesterday's signal — the position to hold today. We act on it via OPG orders
that fill at today's open. No lookahead (we never read today's close).

Turnover control (Carver buffering, T-148): whole-share rounding already
buffers small drifts; on top we trade an asset only when its target weight
moves by ≥ ``deadband`` OR its long/flat state FLIPS (de-gross / re-gross is
always acted). This suppresses no-op micro-rebalances + tiny auction orders.

OFF by default everywhere else: this module is only invoked when the cloud
driver runs with ``--strategy trend_sleeve`` (the reconcile-only pulse is
unchanged).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

from core.trend_overlay import TrendOverlay
from paper_trader.order_construction import OrderSpec

SLEEVE_UNIVERSE = ("SPY", "AGG", "GLD")
SLEEVE_LOOKBACK = 105          # 5 months — the T-204/T-236 pre-registered config
SLEEVE_DEADBAND = 0.10         # Carver weight-band: skip a rebalance < this (non-flip)


@dataclass
class SleevePlan:
    """The constructed rebalance plan — orders + the full target/held context
    (so the loop can log + the tracker can record exactly what was decided)."""
    orders: List[OrderSpec]
    targets: Dict[str, float] = field(default_factory=dict)      # ticker -> target weight
    target_qty: Dict[str, int] = field(default_factory=dict)
    held_qty: Dict[str, int] = field(default_factory=dict)
    signals: Dict[str, float] = field(default_factory=dict)      # ticker -> 1.0/0.0


class SleeveOrderConstructor:
    def __init__(self, universe=SLEEVE_UNIVERSE, lookback: int = SLEEVE_LOOKBACK,
                 deadband: float = SLEEVE_DEADBAND, tif: str = "opg"):
        self.universe = tuple(universe)
        self.lookback = int(lookback)
        self.deadband = float(deadband)
        self.tif = tif

    def latest_signal(self, close: pd.Series) -> float:
        """The most-recent as-of-close long/flat signal (== yesterday's, live).
        Requires ≥ lookback bars; raises if insufficient (the caller HALTs —
        we never trade an undefined signal)."""
        sig = TrendOverlay(self.lookback, enabled=True).exposure(close.astype(float)).dropna()
        if sig.empty:
            raise ValueError(f"insufficient history for the {self.lookback}d signal")
        return float(sig.iloc[-1])

    def construct(self, equity: float, current_positions: Dict[str, int],
                  closes: Dict[str, pd.Series]) -> SleevePlan:
        """Build the rebalance plan for the sleeve.

        equity            : paper account equity ($).
        current_positions : signed qty per ticker we currently hold (broker truth).
        closes            : per-asset daily close series (≥ lookback bars each).
        """
        n = len(self.universe)
        plan = SleevePlan(orders=[])
        for tkr in self.universe:
            close = closes.get(tkr)
            if close is None or len(close.dropna()) < self.lookback:
                raise ValueError(f"[NN-FAIL-CLOSED] {tkr}: missing/short price history")
            sig = self.latest_signal(close)
            last_px = float(close.dropna().iloc[-1])
            if last_px <= 0:
                raise ValueError(f"[NN-FAIL-CLOSED] {tkr}: non-positive last price")

            target_w = (1.0 / n) * sig                       # EW × long/flat; off → 0 (cash)
            target_qty = int(math.floor(equity * target_w / last_px))
            held = int(current_positions.get(tkr, 0))
            held_w = held * last_px / equity if equity > 0 else 0.0
            plan.signals[tkr] = sig
            plan.targets[tkr] = round(target_w, 4)
            plan.target_qty[tkr] = target_qty
            plan.held_qty[tkr] = held

            flip = (target_qty == 0 and held > 0) or (target_qty > 0 and held == 0)
            if not flip and abs(target_w - held_w) < self.deadband:
                continue                                     # Carver buffer: no-op rebalance
            delta = target_qty - held
            if delta == 0:
                continue
            plan.orders.append(OrderSpec(
                ticker=tkr, side=("buy" if delta > 0 else "sell"), qty=abs(delta),
                tif=self.tif, engine_side=("long" if delta > 0 else "exit"),
                edge="trend_sleeve"))
        return plan
