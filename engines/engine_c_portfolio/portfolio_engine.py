# engines/engine_c_portfolio/portfolio_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional
import math
import pandas as pd
import numpy as np

from debug_config import is_debug_enabled, is_info_enabled

def is_portfolio_debug():
    return is_debug_enabled("PORTFOLIO"), is_info_enabled

from .policy import PortfolioPolicy, PortfolioPolicyConfig


@dataclass
class Position:
    qty: int = 0                 # signed qty: long >0, short <0
    avg_price: float = 0.0
    stop: float | None = None
    take_profit: float | None = None
    # edge metadata (for attribution)
    edge: Optional[str] = None
    edge_group: Optional[str] = None
    edge_id: Optional[str] = None
    edge_id: Optional[str] = None
    edge_category: Optional[str] = None
    # MTM tracking
    last_price: Optional[float] = None
    
    # Trailing Stop State
    highest_high: float = -1.0  # For Longs: max price since entry
    lowest_low: float = 1e9     # For Shorts: min price since entry
    trailing_active: bool = False # Has the trail trigger been hit?

# Helper accessor to present Position as dict for downstream compatibility
def _as_dict(pos: "Position") -> dict:
    return {
        "qty": pos.qty,
        "avg_price": pos.avg_price,
        "stop": pos.stop,
        "take_profit": pos.take_profit,
        "edge": pos.edge,
        "edge_group": pos.edge_group,
        "edge_id": pos.edge_id,
        "edge_id": pos.edge_id,
        "edge_category": pos.edge_category,
        "edge_category": pos.edge_category,
        "last_price": pos.last_price,
        "highest_high": pos.highest_high,
        "lowest_low": pos.lowest_low,
        "trailing_active": pos.trailing_active,
    }


class PortfolioEngine:
    """
    Core accounting and allocation layer.
    - Tracks signed-qty positions, cash, realized/unrealized PnL.
    - Computes target weights via PortfolioPolicy (Engine C).
    - Ensures accounting identity: equity = cash + Σ(qty * price).
    """

    def __init__(self, initial_capital: float, policy_cfg: Optional[PortfolioPolicyConfig] = None):
        _cfg = policy_cfg or PortfolioPolicyConfig()
        self.policy = PortfolioPolicy(_cfg)

        # T-2026-06-06-120 — spot 8-ETF crisis-diversifier sleeve, Phase 1.
        # When `spot_sleeve_enabled=True`, partition initial capital between
        # the equity book (1 - spot_sleeve_capital_pct) and a self-contained
        # SpotETFTrendSleeve that runs the validated T-115 cross-asset
        # diversified-trend logic on the 8-ETF basket (NOT equity-trend; see
        # SpotETFTrendSleeve docstring for the inbox-flagged anti-pattern
        # warning). The sleeve runs independently from Engine A/B order flow
        # — it tracks its own equity bar-by-bar via Stooq close-prices and
        # contributes its PnL to total portfolio equity in snapshot().
        #
        # Default OFF preserves pre-T-120 production behavior:
        #   self.cash = initial_capital, self.spot_sleeve = None,
        #   snapshot() returns cash + market_value (no sleeve contribution).
        # → canon-md5 bitwise-identical to current main baseline.
        self.spot_sleeve = None
        self._spot_sleeve_capital_pct = 0.0
        if getattr(_cfg, "spot_sleeve_enabled", False):
            from engines.engine_c_portfolio.sleeves.spot_etf_trend_sleeve import (
                SpotETFTrendSleeve,
            )
            self._spot_sleeve_capital_pct = float(_cfg.spot_sleeve_capital_pct)
            sleeve_initial = float(initial_capital) * self._spot_sleeve_capital_pct
            self.spot_sleeve = SpotETFTrendSleeve(initial_capital=sleeve_initial)
            book_initial = float(initial_capital) - sleeve_initial
        else:
            book_initial = float(initial_capital)

        self.cash: float = book_initial
        self.realized_pnl: float = 0.0
        self.positions: Dict[str, Position] = {}
        self.history: List[dict] = []
        self.current_target_weights: Dict[str, float] = {}
        # Running peak equity for the drawdown-gated kill switch (R1
        # punch-list). Initialized to TOTAL starting capital (book + sleeve
        # if T-120 partition active), so drawdowns are measured against the
        # full intended portfolio. Advanced monotonically in snapshot()
        # whenever equity makes a new high.
        self.peak_equity: float = float(initial_capital)

    def _log_debug(self, msg: str):
        if is_debug_enabled("PORTFOLIO"):
            print(f"[PORTFOLIO][DEBUG] {msg}")

    def _log_info(self, msg: str):
        if is_info_enabled("PORTFOLIO"):
            print(f"[PORTFOLIO][INFO] {msg}")

    # --------- core ops ---------
    def _get_or_new(self, ticker: str) -> Position:
        return self.positions.get(ticker, Position())

    def apply_fill(self, fill: dict) -> None:
        # T-142: gated — was an unconditional full-dict print PER FILL
        # (12k+ lines on a 26-yr cell), part of the logger-drain storm.
        if is_debug_enabled("PORTFOLIO"):
            print(f"[DEBUG_PORTFOLIO_APPLY_FILL] Received fill: {fill}")
        """
        Apply a simulated or real fill.
        fill keys:
          ticker, side ∈ {'long','short','exit','cover'}, qty, price
          optional: commission, stop, take_profit
        """
        ticker = str(fill.get("ticker"))
        side = str(fill.get("side", "")).lower()
        qty_raw = int(fill.get("qty", 0))
        price = fill.get("fill_price", None)
        if price is None:
            price = fill.get("price", None)
        if price is None and "bar" in fill:
            # allow passing current bar dict/Series
            bar = fill["bar"]
            price = float(bar["Open"]) if isinstance(bar, dict) else float(getattr(bar, "Open", getattr(bar, "open", np.nan)))
        price = float(price) if price is not None else None
        if price is None:
            return
        commission = float(fill.get("commission", 0.0))

        meta_edge = fill.get("edge")
        meta_edge_group = fill.get("edge_group") or fill.get("edge_category")  # tolerate older key
        meta_edge_id = fill.get("edge_id")
        meta_edge_category = fill.get("edge_category")

        if not ticker or qty_raw <= 0:
            return

        if not hasattr(self, 'realized_pnl') or self.realized_pnl is None:
            self.realized_pnl = 0.0

        self._log_info(f"Applying fill: ticker={ticker}, side={side}, qty={qty_raw}, price={price}")

        pos = self._get_or_new(ticker)

        if side == "exit" and pos.qty < 0:
            side = "cover"

        # ---- CLOSE / REDUCE ----
        if side in ("exit", "cover"):
            if pos.qty == 0:
                return
            exit_qty = min(abs(pos.qty), qty_raw)
            was_long = pos.qty > 0
            sign = 1 if was_long else -1

            # Cash and realized pnl update for closing
            if was_long:
                self.cash += exit_qty * price
            else:
                self.cash -= exit_qty * price

            realized = (price - pos.avg_price) * (exit_qty * sign)
            self.realized_pnl += realized
            fill["pnl"] = round(realized, 2)  # Stamp PnL onto fill — single source of truth
            self._log_info(f"Realized PnL from closing: {realized:.2f}")
            self.cash -= commission

            remaining = abs(pos.qty) - exit_qty
            if remaining > 0:
                pos.qty = remaining * sign
            else:
                pos = Position()
            self.positions[ticker] = pos
            self._log_info(f"Updated position for {ticker}: qty={pos.qty}, avg_price={pos.avg_price}")
            print(f"[DEBUG_PORTFOLIO_STATE] After fill: cash={self.cash}, positions={{t: p.qty for t, p in self.positions.items()}}, realized_pnl={self.realized_pnl}")
            return

        # ---- OPEN / ADD ----
        if side not in ("long", "short"):
            return

        signed_qty = qty_raw if side == "long" else -qty_raw

        # Adjust cash for opening or adding
        if signed_qty > 0:
            self.cash -= signed_qty * price
        else:
            self.cash += abs(signed_qty) * price
        self.cash -= commission

        # Same-direction add or opening new position
        if pos.qty == 0 or (pos.qty > 0 and signed_qty > 0) or (pos.qty < 0 and signed_qty < 0):
            new_abs = abs(pos.qty) + abs(signed_qty)
            total_cost = (abs(pos.qty) * pos.avg_price) + (abs(signed_qty) * price)
            pos.qty += signed_qty
            pos.avg_price = (total_cost / new_abs) if new_abs > 0 else 0.0
            # Extend metadata only if missing
            if meta_edge is not None and pos.edge is None:
                pos.edge = meta_edge
            if meta_edge_group is not None and pos.edge_group is None:
                pos.edge_group = meta_edge_group
            if meta_edge_id is not None and pos.edge_id is None:
                pos.edge_id = meta_edge_id
            if meta_edge_category is not None and pos.edge_category is None:
                pos.edge_category = meta_edge_category
            
            # Update last known price on any add
            pos.last_price = float(price)
        else:
            # Opposite-direction order: first close against existing, realize PnL
            closing = min(abs(pos.qty), abs(signed_qty))
            sign = 1 if pos.qty > 0 else -1
            realized = (price - pos.avg_price) * (closing * sign)
            self.realized_pnl += realized
            self._log_info(f"Realized PnL from closing: {realized:.2f}")

            net_abs = abs(pos.qty) - closing
            if net_abs > 0:
                # partially reduced, keep original side and avg price
                pos.qty = net_abs * sign
            else:
                # fully flattened by the closing portion
                excess = abs(signed_qty) - closing
                if excess > 0:
                    # flip to new side with remaining excess at current price
                    pos.qty = excess * (-sign)
                    pos.avg_price = price
                    # overwrite metadata to new trade's meta
                    pos.edge = meta_edge
                    pos.edge_group = meta_edge_group
                    pos.edge_id = meta_edge_id
                    pos.edge_group = meta_edge_group
                    pos.edge_id = meta_edge_id
                    pos.edge_category = meta_edge_category
                    pos.last_price = float(price)
                else:
                    # exactly flat
                    pos = Position()

        # Only apply the incoming stop/take_profit when the fill's direction
        # matches the resulting net position direction. On an opposite-side
        # fill that merely reduces an existing position, the fill's SL/TP were
        # computed for the *incoming* trade's direction (e.g. a short signal
        # places stops above price) — applying them to the surviving position
        # (still long) inverts the stop geometry and produces phantom
        # profitable "stop" hits on the next bar.
        fill_dir = 1 if side == "long" else (-1 if side == "short" else 0)
        pos_dir = 1 if pos.qty > 0 else (-1 if pos.qty < 0 else 0)
        if fill_dir != 0 and fill_dir == pos_dir:
            if fill.get("stop") is not None:
                pos.stop = float(fill["stop"])
            if fill.get("take_profit") is not None:
                pos.take_profit = float(fill["take_profit"])
        self.positions[ticker] = pos
        self._log_info(f"Updated position for {ticker}: qty={pos.qty}, avg_price={pos.avg_price}")
        print(f"[DEBUG_PORTFOLIO_STATE] After fill: cash={self.cash}, positions={{t: p.qty for t, p in self.positions.items()}}, realized_pnl={self.realized_pnl}")
        return

    # ------------------------------------------------------------------ #
    def snapshot(self, timestamp, price_map: Dict[str, float]) -> dict:
        if not hasattr(self, 'realized_pnl') or self.realized_pnl is None:
            self.realized_pnl = 0.0

        # T-2026-06-04-099 determinism fix: sort + math.fsum.
        # self.positions iteration order is dict-insertion order = trade-
        # history order. Across containers, that order varies (it traces
        # back to signal_collector's outer ticker order; T-057c-det
        # only sorted the inner edge_map). The market_value += ...
        # accumulation is order-dependent FP, so a tiny ULP-level residue
        # in equity propagates into the next bar's risk-budget and target-
        # notional sizing, producing different trades, compounding into
        # T-092's observed 0.19-Sharpe cross-container drift at 26-yr.
        # Sorting positions alphabetically and using math.fsum on the
        # sorted contribution list forces a canonical, higher-precision
        # accumulation order.
        mv_contribs: List[float] = []
        ur_contribs: List[float] = []
        open_positions_count = 0
        for t in sorted(self.positions.keys()):
            pos = self.positions[t]
            if pos.qty == 0:
                continue
            open_positions_count += 1
            if t in price_map:
                px = float(price_map[t])
                pos.last_price = px # Update memory
            else:
                # [VANITY FIX] Use last_price if available, else 0.0. NEVER avg_price.
                # If we have no data and no history, the position is effectively worthless until proven otherwise.
                if pos.last_price is not None:
                    px = pos.last_price
                    if is_debug_enabled("PORTFOLIO"):
                        print(f"[PORTFOLIO][WARN] MTM Gap for {t}: Using last_price {px}")
                else:
                    px = 0.0
                    if is_debug_enabled("PORTFOLIO"):
                        print(f"[PORTFOLIO][A L E R T] MTM Gap for {t}: No data, no history. Valuing at 0.0.")

            mv_contribs.append(float(pos.qty) * px)
            ur_contribs.append((px - pos.avg_price) * float(pos.qty))

        market_value = math.fsum(mv_contribs)
        unrealized = math.fsum(ur_contribs)

        # T-2026-06-06-120 — spot 8-ETF crisis-diversifier sleeve PnL.
        # Advance the self-contained sleeve to today and add its current
        # equity to the portfolio total. When spot_sleeve is None (default
        # OFF), this adds 0.0 — bitwise-identical to pre-T-120 baseline.
        # When ON, the sleeve has been compounding its share of capital
        # bar-by-bar via the 8-ETF basket monthly-trend rule (T-115 spec).
        sleeve_equity = 0.0
        if self.spot_sleeve is not None:
            try:
                self.spot_sleeve.advance_to(pd.to_datetime(timestamp))
                sleeve_equity = float(self.spot_sleeve.equity)
            except Exception as exc:
                # A failing sleeve MUST NOT crash the snapshot path.
                # Log + degrade to last-known sleeve value (or 0 if never advanced).
                if is_debug_enabled("PORTFOLIO"):
                    print(f"[PORTFOLIO][SPOT_SLEEVE][WARN] advance_to failed at {timestamp}: {exc}")
                sleeve_equity = float(getattr(self.spot_sleeve, "equity", 0.0))

        equity = self.cash + market_value + sleeve_equity
        # Advance the running peak; compute drawdown vs peak. peak_equity
        # is monotone non-decreasing so subsequent flat-or-down equity
        # produces a non-negative current_drawdown_pct.
        if equity > self.peak_equity:
            self.peak_equity = equity
        current_drawdown_pct = (
            0.0 if self.peak_equity <= 0.0
            else max(0.0, (self.peak_equity - equity) / self.peak_equity)
        )
        snap = {
            "timestamp": pd.to_datetime(timestamp),
            "cash": self.cash,
            "market_value": market_value,
            "realized_pnl": self.realized_pnl,
            "unrealized_pnl": unrealized,
            "equity": equity,
            "positions": open_positions_count,
            "peak_equity": self.peak_equity,
            "current_drawdown_pct": current_drawdown_pct,
            # T-2026-06-06-120: spot 8-ETF sleeve PnL contribution. Zero when
            # sleeve disabled (default). Downstream consumers that recompute
            # equity from cash + market_value MUST add this back, or they
            # silently drop the sleeve's contribution (see backtest_controller
            # _log_snapshot override at the matching point).
            "sleeve_equity": sleeve_equity,
            # T-2026-06-06-124: gross_notional = Σ|qty·px| per bar. Needed
            # by the T-118 de-gross campaign + the T-116 count×size double-
            # count diagnostic (this book shorts → net market_value ≠ gross).
            # Reuses the existing helper at portfolio_engine.gross_notional
            # — PURELY ADDITIVE, does not feed equity, does not change
            # trades.csv → canon-safe.
            "gross_notional": self.gross_notional(price_map),
        }
        # optional quick-look attribution (counts of open positions by edge)
        try:
            edge_counts = {}
            for t, p in self.positions.items():
                if p.qty == 0:
                    continue
                key = p.edge or "unknown"
                edge_counts[key] = edge_counts.get(key, 0) + 1
            snap["open_pos_by_edge"] = edge_counts
        except Exception:
            pass
        self.history.append(snap)
        self._log_debug(f"Snapshot recorded: {snap}")
        return snap
    # ------------------------------------------------------------------ #
    def total_equity(self, price_map: Dict[str, float]) -> float:
        """
        Compute total portfolio equity = cash + Σ(qty * price).
        """
        # T-2026-06-04-099 determinism fix: sort + math.fsum (matches the
        # snapshot() accumulator above). total_equity is called from
        # mode_controller checkpoints + governor lifecycle and feeds
        # observability paths.
        mv_contribs: List[float] = []
        for t in sorted(self.positions.keys()):
            pos = self.positions[t]
            if pos.qty == 0:
                continue
            if t in price_map:
                px = float(price_map[t])
                # We don't update pos.last_price here generally as total_equity might be called tentatively,
                # but for consistency with snapshot we assume price_map is authoritative current state.
                # However, to simulate 'read-only' equity check, we don't mutate pos.
            else:
                px = pos.last_price if pos.last_price is not None else 0.0

            mv_contribs.append(float(pos.qty) * px)
        return self.cash + math.fsum(mv_contribs)
    # ------------------------------------------------------------------ #
    def compute_target_allocations(
        self,
        signals: Dict[str, float],
        price_data: Dict[str, pd.DataFrame],
        equity: float,
        regime_meta: Optional[Dict] = None,
    ) -> Dict[str, float]:
        """
        Wrapper around PortfolioPolicy.allocate() that stores and returns weights.
        """
        weights = self.policy.allocate(signals, price_data, equity, regime_meta=regime_meta)

        # T-2026-06-10-139 — Carver dynamic optimization (integer-position
        # layer), default OFF. When enabled, re-express the unrounded
        # target weights as the integer-share-feasible book that best
        # tracks them (greedy TE minimizer, dynamic_optimizer.py). When
        # disabled (default), this branch is a no-op and the optimizer
        # module is never imported — pre-T-139 behavior bitwise-identical.
        if getattr(self.policy.cfg, "dynamic_optimization_enabled", False) and weights:
            weights = self._apply_dynamic_optimization(weights, price_data, equity)

        # T-2026-06-11-148 — Carver position buffering (trade-to-edge,
        # 10% inertia), default OFF. Composes AFTER dynamic optimization:
        # when dyn-opt is ON, buffering bands around its integer-implied
        # optimal positions; when OFF, around the unrounded optimal
        # shares. OFF ⇒ this branch is a no-op and the module is never
        # imported — pre-T-148 behavior bitwise-identical.
        if getattr(self.policy.cfg, "position_buffering_enabled", False) and weights:
            weights = self._apply_position_buffering(weights, price_data, equity)

        self.current_target_weights = weights
        self._log_debug(f"Computed target allocations from signals: {signals} -> weights: {weights}")
        return weights

    def _apply_position_buffering(
        self,
        weights: Dict[str, float],
        price_data: Dict[str, pd.DataFrame],
        equity: float,
    ) -> Dict[str, float]:
        """Trade-to-edge buffering post-processor (Engine C scope only).

        Same plumbing contract as _apply_dynamic_optimization: last
        Closes from the bar's price_data (the prices Engine B sizes
        from), current integer positions from self.positions, the bar's
        sizing equity. Fails open to the unmodified weights on any
        precluding input.
        """
        from engines.engine_c_portfolio.position_buffering import (
            apply_position_buffering,
        )

        prices: Dict[str, float] = {}
        for tkr in sorted(weights.keys()):
            df = price_data.get(tkr)
            if df is None or df.empty or "Close" not in df.columns:
                continue
            try:
                last_close = float(df["Close"].iloc[-1])
            except (TypeError, ValueError):
                continue
            if np.isfinite(last_close) and last_close > 0.0:
                prices[tkr] = last_close

        current_positions = {
            t: int(self.positions[t].qty) if t in self.positions else 0
            for t in weights.keys()
        }
        result = apply_position_buffering(
            target_weights=weights,
            prices=prices,
            current_positions=current_positions,
            equity=equity,
            buffer_fraction=float(getattr(self.policy.cfg, "buffer_fraction", 0.10)),
        )
        # Kept for observability; not read by engines.
        self.last_buffering_result = result
        self._log_debug(
            f"[BUFFER] suppressed={len(result.suppressed)} "
            f"edge_trades={len(result.edge_trades)} "
            f"notional {result.notional_traded_unbuffered:,.0f}→"
            f"{result.notional_traded_buffered:,.0f}"
        )
        return result.weights

    def _apply_dynamic_optimization(
        self,
        weights: Dict[str, float],
        price_data: Dict[str, pd.DataFrame],
        equity: float,
    ) -> Dict[str, float]:
        """Post-process unrounded target weights into integer-feasible ones.

        Engine C scope only: consumes the allocator's weights, current
        integer positions, last Closes, and the existing Ledoit-Wolf
        covariance estimator (HRPOptimizer._estimate_cov — the reused
        portfolio-level Σ machinery). Fails open to the unmodified
        weights on any optimization-precluding input.
        """
        from engines.engine_c_portfolio.dynamic_optimizer import (
            DynamicOptimizationConfig,
            optimize_integer_positions,
        )
        from engines.engine_c_portfolio.optimizers.hrp import HRPConfig, HRPOptimizer

        cfg = self.policy.cfg
        lookback = int(getattr(cfg, "dynopt_cov_lookback", 60))

        prices: Dict[str, float] = {}
        returns_map: Dict[str, pd.Series] = {}
        for tkr in sorted(weights.keys()):
            df = price_data.get(tkr)
            if df is None or df.empty or "Close" not in df.columns:
                continue
            close = df["Close"]
            try:
                last_close = float(close.iloc[-1])
            except (TypeError, ValueError):
                continue
            if np.isfinite(last_close) and last_close > 0.0:
                prices[tkr] = last_close
            rets = close.pct_change().dropna().tail(lookback)
            if len(rets) >= 2:
                returns_map[tkr] = rets

        if not returns_map:
            self._log_debug("[DYNOPT] no usable returns history — passing weights through")
            return weights

        returns_df = pd.DataFrame(returns_map).fillna(0.0)
        hrp = HRPOptimizer(HRPConfig(
            cov_lookback=lookback,
            use_ledoit_wolf=bool(getattr(cfg, "dynopt_use_ledoit_wolf", True)),
        ))
        covariance = hrp._estimate_cov(returns_df)

        current_positions = {
            t: int(self.positions[t].qty) if t in self.positions else 0
            for t in weights.keys()
        }

        dyn_cfg = DynamicOptimizationConfig(
            shadow_cost=float(getattr(cfg, "dynopt_shadow_cost", 10.0)),
            cost_per_trade_bps=float(getattr(cfg, "dynopt_cost_per_trade_bps", 10.0)),
            tracking_error_buffer=float(getattr(cfg, "dynopt_tracking_error_buffer", 0.02)),
            buying_power_fraction=float(getattr(cfg, "dynopt_buying_power_fraction", 1.0)),
            max_weight_per_asset=getattr(cfg, "dynopt_max_weight_per_asset", None),
        )
        result = optimize_integer_positions(
            target_weights=weights,
            prices=prices,
            current_positions=current_positions,
            equity=equity,
            covariance=covariance,
            cfg=dyn_cfg,
        )
        # Kept for observability/cockpit consumption; not read by engines.
        self.last_dynopt_result = result
        if result.skipped:
            self._log_debug(f"[DYNOPT] skipped ({result.skip_reason}) — weights passed through")
            return weights
        self._log_debug(
            f"[DYNOPT] TE prior={result.tracking_error_prior:.4f} "
            f"naive={result.tracking_error_naive:.4f} "
            f"optimized={result.tracking_error_optimized:.4f} "
            f"trades={len(result.trades)} buffered={result.buffered}"
        )
        return result.weights

    def target_notional_values(self, equity: float) -> Dict[str, float]:
        """
        Translate current target weights to target dollar notionals.
        """
        return {t: w * equity for t, w in self.current_target_weights.items()}

    # ------------------------------------------------------------------ #
    def gross_notional(self, price_map: Dict[str, float]) -> float:
        g = 0.0
        for t, p in self.positions.items():
            if p.qty == 0:
                continue
            px = float(price_map.get(t, p.avg_price if p.avg_price else 0.0))
            g += abs(p.qty * px)
        self._log_debug(f"Gross notional calculated: {g}")
        return g

    def net_exposure(self, price_map: Dict[str, float]) -> float:
        n = 0.0
        for t, p in self.positions.items():
            if p.qty == 0:
                continue
            px = float(price_map.get(t, p.avg_price if p.avg_price else 0.0))
            n += p.qty * px
        self._log_debug(f"Net exposure calculated: {n}")
        return n

    # --- Helper accessors for downstream compatibility ---
    @property
    def positions_map(self) -> Dict[str, dict]:
        return {t: _as_dict(p) for t, p in self.positions.items()}

    def get_position_info(self, ticker: str) -> dict:
        p = self.positions.get(ticker)
        return _as_dict(p) if p else {}

    def get_avg_price(self, ticker: str) -> Optional[float]:
        p = self.positions.get(ticker)
        return float(p.avg_price) if p else None

    def get_qty(self, ticker: str) -> int:
        p = self.positions.get(ticker)
        return int(p.qty) if p else 0