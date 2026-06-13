# paper_trader/order_construction.py
"""PaperOrderConstructor — wires the PRODUCTION order-construction path
(Engine A → Engine C → Engine B) into the paper loop, READ-ONLY.

It faithfully mirrors ``BacktestController._prepare_orders`` (the
canonical assembly): Engine A signals → a {ticker: signed-score} map →
``compute_target_allocations`` (dyn-opt ON, the whole-share integer
book auction orders require) → ``prepare_order(target_weights=…)`` per
signal → an ``OrderSpec`` ready for OrderManager.stage(). Engines are
INJECTED (the loop owner builds them exactly as mode_controller does);
this adapter only CALLS them — no engine-logic change, no engine
construction here. That keeps it unit-testable with fakes and keeps the
read-only-import contract literal.

The auction TIF routing follows the PaperConfig convention: entries
(long/short) → OPG (opening auction), signal exits (exit/cover) → CLS
under moo_moc, else OPG. Whole-share is guaranteed upstream by dyn-opt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd

from paper_trader.order_manager import TimeInForce
from paper_trader.paper_config import PaperConfig

# Engine B order side → broker buy/sell.
_SIDE_TO_BUYSELL = {"long": "buy", "cover": "buy", "short": "sell", "exit": "sell"}
_ENTRY_SIDES = {"long", "short"}


@dataclass
class OrderSpec:
    ticker: str
    side: str          # "buy" | "sell"
    qty: int
    tif: str           # "opg" | "cls"
    engine_side: str   # original Engine B side (long/short/exit/cover) — attribution
    edge: Optional[str] = None

    def stage_args(self) -> Dict[str, Any]:
        return {"ticker": self.ticker, "side": self.side,
                "qty": self.qty, "tif": TimeInForce(self.tif)}


class PaperOrderConstructor:
    def __init__(self, alpha_engine, portfolio_engine, risk_engine,
                 paper_config: PaperConfig):
        self.alpha = alpha_engine
        self.portfolio = portfolio_engine    # Engine C (built with dyn-opt ON)
        self.risk = risk_engine
        self.cfg = paper_config

    # ------------------------------------------------------------------ #
    def _signal_map(self, signals: List[dict]) -> Dict[str, float]:
        """Mirror _prepare_orders: {ticker: score × side_mult}, dropping
        side=='none'. strength → confidence → signal."""
        out: Dict[str, float] = {}
        for s in signals:
            if "ticker" not in s:
                continue
            side = str(s.get("side", "none")).lower()
            if side == "none":
                continue
            raw = float(s.get("strength", s.get("confidence", s.get("signal", 0.0))))
            out[s["ticker"]] = raw * (1.0 if side == "long" else -1.0)
        return out

    def _tif_for(self, engine_side: str) -> str:
        if self.cfg.auction_execution == "moo_moc" and engine_side in ("exit", "cover"):
            return "cls"
        return "opg"

    def construct(
        self,
        data_map: Dict[str, pd.DataFrame],
        now: pd.Timestamp,
        equity: float,
        current_positions: Optional[Dict[str, int]] = None,
        regime_meta: Optional[dict] = None,
    ) -> List[OrderSpec]:
        """Run the real A→C→B pipeline and return stage-able OrderSpecs.

        current_positions: signed integer qty per ticker (from the
        LedgerStore) — fed to prepare_order so target-weight sizing is
        delta-correct against what we actually hold.
        """
        current_positions = current_positions or {}
        signals = self.alpha.generate_signals(data_map, now, regime_meta=regime_meta) or []

        signal_map = self._signal_map(signals)
        target_weights = self.portfolio.compute_target_allocations(
            signals=signal_map, price_data=data_map, equity=equity,
            regime_meta=regime_meta,
        )

        specs: List[OrderSpec] = []
        for sig in signals:
            tkr = sig.get("ticker")
            if not tkr or tkr not in data_map:
                continue
            curr_qty = int(current_positions.get(tkr, 0))
            try:
                order = self.risk.prepare_order(
                    signal=sig, equity=equity, df_hist=data_map[tkr],
                    current_qty=curr_qty, target_weights=target_weights,
                    regime_meta=regime_meta,
                )
            except TypeError:
                # tolerate an engine variant without regime_meta kwarg
                order = self.risk.prepare_order(
                    signal=sig, equity=equity, df_hist=data_map[tkr],
                    current_qty=curr_qty, target_weights=target_weights,
                )
            if not order:
                continue
            engine_side = str(order.get("side", "")).lower()
            buysell = _SIDE_TO_BUYSELL.get(engine_side)
            qty = abs(int(order.get("qty", 0)))
            if buysell is None or qty <= 0:
                continue
            specs.append(OrderSpec(
                ticker=str(order.get("ticker", tkr)).upper(), side=buysell,
                qty=qty, tif=self._tif_for(engine_side), engine_side=engine_side,
                edge=order.get("edge"),
            ))
        return specs
