# paper_trader/offense_sso_constructor.py
"""OffenseSSOConstructor — the trend-gated 2× offense as a paper-loop content
layer (T-284 PRIMARY, T-288 fleet Account 2).

T-284's SPY-beating config: **100% SPY at 2× when the {2,5,10}-month ensemble
trend is ON, cash when off** — SSO-implementable, Roth-legal (no margin). The
signal is the SAME multi-speed ensemble the defensive sleeve uses, but computed
on the UNDERLYING SPY (SSO's short, levered history is not the trend to read),
and the fractional exposure {0, ⅓, ⅔, 1} is expressed by holding **SSO** (2×
daily SPY) at that weight — so a fully-on gate is 2× SPY, a ⅔ gate ≈ 1.33×, off
is cash. Whole SSO shares, sized off min(equity, cap) like the sleeve.

Reuses `SleeveOrderConstructor.latest_signal` for the EXACT SPY ensemble signal
(composition — the defensive sleeve module is byte-preserved). Off-leg is cash,
never short. FAIL-CLOSED on short SPY history.

Honest label (carried from T-284, per the max-wealth memory): this is an
EXPOSURE/leverage decision, not an alpha claim; results are directional (paired
Δwealth CI straddles — leverage inflates bootstrap variance); the named failure
mode is chop (2011 −27% while SPY −3%) + SSO's daily-reset vol decay. Paper
Account 2 validates EXECUTION of the gated-2× routing (SSO fills/spreads,
behaviour in live chop) — NOT the wealth claim (that lives in the backtest).
The SSO-vs-stacked-ETF vehicle question (T-294) gates REAL money, not paper.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List

import pandas as pd

from paper_trader.order_construction import OrderSpec
from paper_trader.sleeve_constructor import SLEEVE_SPEEDS, SleeveOrderConstructor

OFFENSE_TRADE_TICKER = "SSO"        # 2× daily SPY (the traded instrument)
OFFENSE_SIGNAL_TICKER = "SPY"       # the underlying the ensemble trend reads
OFFENSE_SPEEDS = SLEEVE_SPEEDS      # {42,105,210}d — EXACTLY the sleeve's ensemble
OFFENSE_DEADBAND = 0.10             # Carver weight-band (same as the sleeve)


@dataclass
class OffensePlan:
    orders: List[OrderSpec]
    targets: Dict[str, float] = field(default_factory=dict)      # ticker -> target weight
    target_qty: Dict[str, int] = field(default_factory=dict)
    held_qty: Dict[str, int] = field(default_factory=dict)
    signals: Dict[str, float] = field(default_factory=dict)      # SPY ensemble exposure {0,⅓,⅔,1}


class OffenseSSOConstructor:
    def __init__(self, trade_ticker=OFFENSE_TRADE_TICKER,
                 signal_ticker=OFFENSE_SIGNAL_TICKER, speeds=OFFENSE_SPEEDS,
                 deadband: float = OFFENSE_DEADBAND, tif: str = "day"):
        self.trade_ticker = trade_ticker
        self.signal_ticker = signal_ticker
        self.speeds = tuple(int(s) for s in speeds)
        self.deadband = float(deadband)
        self.tif = tif
        # compose the EXACT sleeve ensemble signal (no re-implementation, and the
        # defensive sleeve constructor is left byte-unchanged).
        self._signal = SleeveOrderConstructor(speeds=self.speeds)

    def construct(self, equity: float, current_positions: Dict[str, int],
                  closes: Dict[str, pd.Series]) -> OffensePlan:
        """Build the offense rebalance plan.

        closes MUST provide the SIGNAL ticker (SPY) for the ensemble AND the
        TRADE ticker (SSO) for pricing. Sizing is off ``equity`` (the caller
        passes min(account_equity, cap)).
        """
        plan = OffensePlan(orders=[])
        spy = closes.get(self.signal_ticker)
        sso = closes.get(self.trade_ticker)
        if spy is None or len(spy.dropna()) < max(self.speeds):
            raise ValueError(f"[NN-FAIL-CLOSED] {self.signal_ticker}: missing/short "
                             f"history for the ensemble signal")
        if sso is None or sso.dropna().empty:
            raise ValueError(f"[NN-FAIL-CLOSED] {self.trade_ticker}: missing price")

        exposure = self._signal.latest_signal(spy)      # fractional {0, ⅓, ⅔, 1}
        last_px = float(sso.dropna().iloc[-1])
        if last_px <= 0:
            raise ValueError(f"[NN-FAIL-CLOSED] {self.trade_ticker}: non-positive price")

        # 100% SSO when fully on → 2× SPY; the fractional gate scales it; off → cash.
        target_w = float(exposure)
        target_qty = int(math.floor(equity * target_w / last_px))
        held = int(current_positions.get(self.trade_ticker, 0))
        held_w = held * last_px / equity if equity > 0 else 0.0
        plan.signals[self.signal_ticker] = exposure
        plan.targets[self.trade_ticker] = round(target_w, 4)
        plan.target_qty[self.trade_ticker] = target_qty
        plan.held_qty[self.trade_ticker] = held

        flip = (target_qty == 0 and held > 0) or (target_qty > 0 and held == 0)
        if not flip and abs(target_w - held_w) < self.deadband:
            return plan                                  # Carver buffer: no-op
        delta = target_qty - held
        if delta == 0:
            return plan
        plan.orders.append(OrderSpec(
            ticker=self.trade_ticker, side=("buy" if delta > 0 else "sell"),
            qty=abs(delta), tif=self.tif,
            engine_side=("long" if delta > 0 else "exit"), edge="offense_sso"))
        return plan
