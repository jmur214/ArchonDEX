# paper_trader/sleeve_constructor.py
"""SleeveOrderConstructor — the trend-sleeve as the paper-loop content layer (T-238).

The validated 3-asset trend sleeve (T-204/T-236) is the first strategy cleared
for paper validation. It is FAR simpler than the equity book: an equal-weight
SPY/AGG/GLD long-flat trend overlay. The DEPLOYING spec is D's T-260 multi-speed
ensemble — per-asset exposure = the MEAN of the {2,5,10}-month binary long/flat
signals → a FRACTIONAL {0, ⅓, ⅔, 1} exposure (more robust than any single
lookback: Sortino ci_low 0.644→0.757, MaxDD −11.8→−11.1%). This module turns it
into the daily order set the cloud paper loop submits — reusing the validated
signals from `core/trend_overlay.py` (forks nothing; just averages three speeds).

Causality: the loop runs in the morning. The latest COMPLETE daily bar is
yesterday's close, so the latest averaged `TrendOverlay.exposure` value IS
yesterday's signal — the position to hold today. No lookahead (never today's
close). The fractional target flows through the SAME whole-share delta path, so
a partial de-gross (⅓→⅔ etc.) is a normal rebalance the Carver deadband buffers.

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
# D's T-260 multi-speed ensemble: per-asset exposure = MEAN of the {2,5,10}-month
# binary long/flat signals → fractional {0, ⅓, ⅔, 1}. EXACTLY D's pre-registered
# spec (scripts/multispeed_robustness_t260.py: multi([42,105,210])), no re-tuning.
SLEEVE_SPEEDS = (42, 105, 210)          # 2, 5, 10 months (252-day-year convention)
SLEEVE_DEADBAND = 0.10         # Carver weight-band: skip a rebalance < this (non-flip)


@dataclass
class SleevePlan:
    """The constructed rebalance plan — orders + the full target/held context
    (so the loop can log + the tracker can record exactly what was decided)."""
    orders: List[OrderSpec]
    targets: Dict[str, float] = field(default_factory=dict)      # ticker -> target weight
    target_qty: Dict[str, int] = field(default_factory=dict)
    held_qty: Dict[str, int] = field(default_factory=dict)
    signals: Dict[str, float] = field(default_factory=dict)      # ticker -> ensemble exposure {0,⅓,⅔,1}


class SleeveOrderConstructor:
    def __init__(self, universe=SLEEVE_UNIVERSE, speeds=SLEEVE_SPEEDS,
                 deadband: float = SLEEVE_DEADBAND, tif: str = "opg"):
        self.universe = tuple(universe)
        self.speeds = tuple(int(s) for s in speeds)
        self.deadband = float(deadband)
        self.tif = tif

    def latest_signal(self, close: pd.Series) -> float:
        """The most-recent as-of-close ENSEMBLE exposure (== yesterday's, live):
        the MEAN of the {2,5,10}-month binary long/flat signals → fractional
        {0, ⅓, ⅔, 1} (D's T-260 spec). FAIL-CLOSED: every speed must be defined
        at the latest bar (≥ that speed's history) — a NaN would silently degrade
        the ensemble to a shorter-lookback subset, so we raise instead (the
        caller HALTs; we never trade a partially-defined signal)."""
        close = close.astype(float)
        latest = [TrendOverlay(s, enabled=True).exposure(close).iloc[-1]
                  for s in self.speeds]
        if any(pd.isna(v) for v in latest):
            raise ValueError(f"[NN-FAIL-CLOSED] not all speeds {self.speeds} "
                             f"defined at the latest bar (insufficient history)")
        return float(sum(float(v) for v in latest) / len(latest))

    def construct(self, equity: float, current_positions: Dict[str, int],
                  closes: Dict[str, pd.Series]) -> SleevePlan:
        """Build the rebalance plan for the sleeve.

        equity            : paper account equity ($).
        current_positions : signed qty per ticker we currently hold (broker truth).
        closes            : per-asset daily close series (≥ max(speeds) bars each).
        """
        n = len(self.universe)
        plan = SleevePlan(orders=[])
        for tkr in self.universe:
            close = closes.get(tkr)
            if close is None or len(close.dropna()) < max(self.speeds):
                raise ValueError(f"[NN-FAIL-CLOSED] {tkr}: missing/short price history")
            sig = self.latest_signal(close)                  # fractional {0, ⅓, ⅔, 1}
            last_px = float(close.dropna().iloc[-1])
            if last_px <= 0:
                raise ValueError(f"[NN-FAIL-CLOSED] {tkr}: non-positive last price")

            target_w = (1.0 / n) * sig                       # EW × ensemble exposure; 0 → cash
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
