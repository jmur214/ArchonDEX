# engines/engine_b_risk/risk_engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import logging
import math
import pandas as pd
import numpy as np
from debug_config import is_debug_enabled, is_info_enabled

logger = logging.getLogger(__name__)

# Programmer-error exceptions that MUST propagate through Engine B's
# narrow-catch sites. Matches the gauntlet remediation (commits 453e04e,
# ee42ab7), the backtest_controller fix (T-2026-05-08-005, commit
# 129c7ba), and the Engine A batch (T-2026-05-08-011, commit 7c9dac0).
# Critical-blast-radius reason for Engine B specifically: a silent
# TypeError in the drawdown-halt path defeats the kill switch without
# anyone noticing. That is the catastrophic-failure mode for live
# trading. Re-raising programmer errors makes the bug surface
# immediately rather than silently fall back to "no kill."
_PROGRAMMER_ERRORS = (
    TypeError, AttributeError, NameError, AssertionError, ImportError,
)


@dataclass
class RiskConfig:
    """
    Risk and constraint configuration (config-driven).
    """
    # Per-trade sizing knobs (Small Account Tuned)
    risk_per_trade_pct: float = 0.025       # risk budget per trade (2.5% for small accounts to allow concentration)
    atr_stop_mult: float = 1.5              # stop distance = mult * ATR
    atr_tp_mult: float = 3.0                # take-profit distance = mult * ATR
    cap_atr_to_pct_of_price: float = 0.20   # clamp extreme ATR (e.g., 20% of price)
    atr_floor_pct_of_price: float = 0.005   # floor ATR (e.g., 0.5% of price)
    max_pos_value_pct: float = 0.30         # cap single-name notional as % of equity
    min_qty: int = 1
    round_qty: bool = True
    min_notional: float = 10.0              # Lowered for fractional/small capabilities
    force_min_qty_on_signal: bool = True     # if sizing rounds to 0, optionally force 1 share when safe

    # Portfolio-level constraints
    max_positions: int = 5
    max_gross_exposure: float = 1.0         # Σ|qty*px| / equity
    allow_shorts: bool = True
    min_bars_warmup: int = 30               # require history length before trading

    # Allocation alignment (optional, via PortfolioPolicy)
    enforce_target_allocations: bool = True
    rebalance_tolerance: float = 0.05       # relative drift threshold before rebalancing

    # Sector Constraints
    max_sector_exposure_pct: float = 0.30   # max 30% allocation to a single sector
    sector_map_path: str = "config/sector_map.json"

    # Trailing Stop & Dynamic Config
    high_vol_stop_mult: float = 2.5         # Widen stops in High Vol regime
    low_vol_stop_mult: float = 1.0          # Tighten stops in Low Vol regime
    trailing_stop_activation_r: float = 1.0 # Profit > 1R starts trailing
    trailing_stop_dist_atr: float = 1.5     # Trail distance in ATR
    enable_trailing: bool = True

    # Churn control
    cooldown_bars: int = 0                  # require N bars between orders per ticker (0=off)

    # Liquidity Constraints (Professional Grade)
    max_pct_adv: float = 0.01               # Limit trade size to 1% of Average Daily Volume
    adv_window: int = 20                    # Lookback for ADV calculation

    # Advisory consumption toggle (Engine E → Risk). When False, risk engine
    # ignores suggested_max_positions, suggested_exposure_cap, risk_scalar, and
    # correlation-regime sector-cap adjustments. Default True preserves behavior.
    risk_advisory_enabled: bool = True

    # Drawdown-gated kill switch (R1 audit-week-of, propose-first).
    # When enabled, current_drawdown_pct sourced from PortfolioEngine.snapshot()
    # de-grosses new sizing or halts new entries entirely as drawdown deepens.
    # OFF by default — does not affect any backtest output until explicitly
    # enabled via config. Engine B charter requires user approval for behavior
    # changes; this scaffold ships INERT.
    drawdown_kill_switch_enabled: bool = False
    drawdown_warn_threshold: float = 0.05        # 5% — log only
    drawdown_degrade_threshold: float = 0.10     # 10% — halve new sizing
    drawdown_halt_threshold: float = 0.15        # 15% — block new entries
    drawdown_degrade_scaler: float = 0.5         # multiplier applied above degrade
    # T-2026-06-05-111 PoC: Path-A wiring for the drawdown kill-switch.
    # When True AND drawdown_kill_switch_enabled is also True, the halt
    # branch's `return None` and the degrade branch's size multiplier
    # are applied PRE-PATH (i.e., before the Path-A vs Path-B branch).
    # Halt blocks new entries on Path A (production); degrade multiplies
    # Path A's `target_notional`.
    # Default False to preserve T-106 verified canon-md5 baseline
    # bitwise-identical. Only effective when paired with
    # drawdown_kill_switch_enabled=True. Reviewable reference impl per
    # T-111 propose-first dispatch — does NOT change main's default
    # behavior; awaits a director-gated A/B before any prod flip.
    drawdown_kill_switch_apply_on_path_a: bool = False

    # T-2026-06-06-116 PoC — Path-A wiring for the HMM-modulated advisory
    # risk_scalar de-gross. SIBLING of the T-111 drawdown lift above.
    # The Engine-E advisory.risk_scalar (modulated by the validated HMM,
    # T-101) is consumed ONLY in the legacy Path-B `else:` block
    # (`risk_scaler *= advisory_risk_scalar`, ~line 987), which production
    # (Path A, target_weight) never reaches — so the HMM's risk-off signal
    # never affects production sizing (T-101 proved flipping `hmm_enabled`
    # on did nothing for exactly this reason). When True AND
    # `risk_advisory_enabled` is also True, the same `advisory_risk_scalar`
    # value Path B uses is applied multiplicatively to Path A's
    # `target_notional` (composes with optimizer_weight, portfolio_vol_scalar,
    # and T-111's _drawdown_size_mult). Default False → mult stays 1.0 →
    # canon-md5 bitwise-identical to current main. Reviewable reference impl
    # per the T-116 propose-first dispatch; does NOT change main's default
    # behavior and awaits a director-gated A/B before any prod flip. The
    # double-count interaction with the LIVE suggested_exposure_cap +
    # suggested_max_positions floors is documented in
    # docs/Audit/hmm_riskscalar_path_a_lift_t116_2026_06_06.md.
    advisory_risk_scalar_apply_on_path_a: bool = False

    # Portfolio-level vol-targeting (T-2026-05-12-055, Moreira-Muir 2017).
    # Sizing modifier applied AFTER all existing risk constraints
    # (drawdown halt / kill-switch) and BEFORE the final order is emitted.
    # NEVER overrides risk gates — if kill-switch blocks, no order is
    # placed and vol-target is irrelevant. OFF by default; A/B harness
    # validates lift before director flag-flip (T-055b).
    portfolio_vol_target_enabled: bool = False
    portfolio_vol_target_annual_vol: float = 0.10        # 10% retail-fit
    portfolio_vol_target_window_days: int = 60           # rolling-60d realized
    portfolio_vol_target_floor: float = 0.5              # don't degross below 50%
    portfolio_vol_target_ceiling: float = 2.0            # don't lever above 200%
    portfolio_vol_target_min_returns_required: int = 60  # warmup gate

    # T-2026-05-22-055d additions — EWMA estimator alternative for the
    # vol-target overlay. Defaults preserve T-055 behavior (rolling).
    portfolio_vol_target_estimator_type: str = "rolling"
    portfolio_vol_target_ewma_lambda: float = 0.94       # RiskMetrics standard

    # T-2026-05-23-055e additions — regime-conditional target multiplier.
    # When `portfolio_vol_target_regime_aware=True`, the base
    # `portfolio_vol_target_annual_vol` is multiplied by one of the four
    # multipliers below based on advisory["regime_summary"]. Defaults
    # preserve T-055d behavior (regime_aware=False → multiplier ignored).
    portfolio_vol_target_regime_aware: bool = False
    portfolio_vol_target_benign_multiplier: float = 1.0
    portfolio_vol_target_cautious_multiplier: float = 0.85
    portfolio_vol_target_stressed_multiplier: float = 0.60
    portfolio_vol_target_crisis_multiplier: float = 0.40

    # T-2026-06-11-153 — vol-estimator collapse fixes (PROPOSE-FIRST,
    # both default-inert). D's T-150 measured the production-spec
    # EWMA(0.94) collapsing to near-zero variance on quiet stretches —
    # exactly where a vol-targeter dividing by sigma over-levers. The
    # T-153 assessment quantified it on the canonical 26-yr history:
    # BOTH estimators (ewma AND rolling) emit sigma < 2% annual on ~14%
    # of live bars (min 3e-06 — past the `<=0` guard), requesting the
    # 2.0x ceiling off a garbage estimate (up to 1.57x over-lever vs a
    # sanity-floored sigma).
    # Fix A: sigma-floor guard (consumer-side, protects ALL estimators).
    # Fix B: estimator_type="yang_zhang" (D's T-150 winner; range-based,
    # collapse-immune) — selected via the EXISTING
    # portfolio_vol_target_estimator_type key; default stays "rolling".
    # NOTE the whole feature is also gated by
    # portfolio_vol_target_enabled=False (prod default) — these knobs
    # are dormant until the director-gated enable A/B.
    portfolio_vol_target_floor_enabled: bool = False
    portfolio_vol_target_floor_annual: float = 0.02
    portfolio_vol_target_floor_full_sample_frac: float = 0.0
    portfolio_vol_target_yz_window_days: int = 21

    # T-2026-06-06-118 — HMM regime-TRANSITION-triggered gross-exposure
    # overlay (the pre-registered "culmination" experiment; propose-first).
    # Converts the validated Engine-E combined posterior
    # (p_crisis + p_stressed) from a LEVEL (disqualified by T-105's 44-50%
    # always-on / 198-265d p90 dwell) into a TRANSITION trigger: de-gross
    # Path-A target_notional when the k-day change in the combined posterior
    # crosses `regime_overlay_degross_delta`, with ASYMMETRIC hysteresis
    # (re-gross strictly slower — requires `regime_overlay_regross_bars`
    # consecutive calm bars at/below `regime_overlay_regross_level`).
    # Consumes ONLY the per-bar posterior the live backtest already computes
    # causally (predict_proba_at, 60-bar growing window — T-089-verified);
    # adds NO new inference, so it cannot introduce look-ahead. Logic lives
    # in engines/engine_b_risk/regime_transition_overlay.py.
    # Default OFF -> multiplier 1.0 -> canon-md5 bitwise-identical to the
    # T-092 baseline. The campaign sweeps degross_level {1.0,0.5,0.0} x
    # k_days {3,5,10} x 4 hysteresis pairs = ~36 configs (pre-registered in
    # docs/Audit/hmm_transition_trigger_overlay_t118_2026_06_06.md).
    regime_transition_overlay_enabled: bool = False
    regime_overlay_degross_level: float = 1.0     # gross mult applied when armed
    regime_overlay_k_days: int = 5                # Delta(p_combined) lookback (bars)
    regime_overlay_degross_delta: float = 0.40    # tau_on: arm when Delta_k >= this
    regime_overlay_regross_level: float = 0.30    # tau_off: calm ceiling on p_combined
    regime_overlay_regross_bars: int = 10         # n_off: consecutive calm bars to disarm


class RiskEngine:
    """
    Engine B — Risk / Sizing / Constraints.
    ...
    """

    def __init__(
        self,
        cfg: Dict[str, Any],
        wash_sale_cfg: Optional[Dict[str, Any]] = None,
        lt_hold_cfg: Optional[Dict[str, Any]] = None,
    ):
        # Only pass known keys to the dataclass. Warn loudly on unknown
        # keys — silent drops were the cause of the T-088 risk-config
        # mismatch (config/risk_settings.prod.json used legacy names
        # risk_per_trade / max_position_value that the dataclass doesn't
        # recognize, so prod ran on 2.5%-default risk_per_trade_pct
        # instead of the intended 0.5%). Any future config-key drift
        # surfaces in the logs now.
        known = set(RiskConfig.__annotations__)
        cfg_filtered = {k: v for k, v in cfg.items() if k in known}
        unknown = [k for k in cfg.keys() if k not in known]
        for k in unknown:
            logger.warning(
                "[RiskConfig] ignoring unknown config key: %s (value=%r) — "
                "dataclass default will be used instead",
                k, cfg[k],
            )
        self.cfg = RiskConfig(**cfg_filtered)
        self.portfolio = None  # injected by controller
        self.last_skip_reason: Optional[str] = None
        self.last_skip_by_ticker: Dict[str, str] = {}

        # Internal: bar-index bookkeeping for cooldown (per ticker)
        self._last_action_bar: Dict[str, int] = {}

        # T-2026-06-11-153: per-bar data_map reference cache (set by
        # manage_positions; read only by the yang_zhang vol-target
        # estimator). None until the first bar / on the live path.
        self._last_data_map: Optional[Dict[str, pd.DataFrame]] = None

        # Tax-aware modules (Path A, 2026-05). Default-disabled — when
        # neither cfg block has ``enabled=True``, ``record_fill`` /
        # ``should_block_buy`` / ``should_defer_exit`` are no-ops, so
        # behavior on main matches pre-Path-A. Cfg blocks come from
        # ``config/portfolio_settings.json`` via ModeController.
        from engines.engine_b_risk.wash_sale_avoidance import (
            WashSaleAvoidance, WashSaleAvoidanceConfig,
        )
        from engines.engine_b_risk.lt_hold_preference import (
            LTHoldPreference, LTHoldPreferenceConfig,
        )
        ws_dict = wash_sale_cfg or {}
        lt_dict = lt_hold_cfg or {}
        self.wash_sale = WashSaleAvoidance(WashSaleAvoidanceConfig(**{
            k: v for k, v in ws_dict.items()
            if k in WashSaleAvoidanceConfig.__annotations__
        }))
        self.lt_hold = LTHoldPreference(LTHoldPreferenceConfig(**{
            k: v for k, v in lt_dict.items()
            if k in LTHoldPreferenceConfig.__annotations__
        }))
        
        # Load Sector Map
        self.sector_map = {}
        try:
            import json
            import os
            if os.path.exists(self.cfg.sector_map_path):
                with open(self.cfg.sector_map_path, 'r') as f:
                    self.sector_map = json.load(f)
            else:
                # Try relative path from project root if running as module
                alt_path = os.path.join(os.getcwd(), self.cfg.sector_map_path)
                if os.path.exists(alt_path):
                     with open(alt_path, 'r') as f:
                        self.sector_map = json.load(f)
                
                elif is_debug_enabled("RISK"):
                    print(f"[RISK][WARN] Sector map not found at {self.cfg.sector_map_path}")
        except Exception as e:
            print(f"[RISK][ERROR] Failed to load sector map: {e}")

        # T-2026-06-06-118 — HMM transition-trigger gross-exposure overlay.
        # Stateful per-portfolio tracker; default-OFF -> inert (observe()
        # short-circuits to 1.0 and is never advanced). Fed once per bar
        # from manage_positions; read in prepare_order (Path A).
        from engines.engine_b_risk.regime_transition_overlay import (
            RegimeTransitionOverlay, RegimeOverlayConfig,
        )
        self.regime_overlay = RegimeTransitionOverlay(RegimeOverlayConfig(
            enabled=bool(self.cfg.regime_transition_overlay_enabled),
            degross_level=float(self.cfg.regime_overlay_degross_level),
            k_days=int(self.cfg.regime_overlay_k_days),
            degross_delta=float(self.cfg.regime_overlay_degross_delta),
            regross_level=float(self.cfg.regime_overlay_regross_level),
            regross_bars=int(self.cfg.regime_overlay_regross_bars),
        ))

    # ------------------------------------------------------------------ #
    # Path A — fill listener for tax-aware modules. Called by
    # BacktestController._execute_fills / _evaluate_stops after each
    # PortfolioEngine.apply_fill so the wash_sale ledger sees losses
    # immediately and lt_hold sees entry timestamps. No-op when both
    # modules are disabled (the default-on-main configuration).
    # ------------------------------------------------------------------ #
    def record_fill(self, fill: Dict[str, Any], ts) -> None:
        if fill is None:
            return
        ticker = str(fill.get("ticker", ""))
        post_fill_qty = None
        if ticker and self.portfolio is not None:
            try:
                pos = self.portfolio.positions.get(ticker)
                if pos is not None:
                    post_fill_qty = int(pos.qty)
            except Exception:
                post_fill_qty = None
        try:
            self.wash_sale.record_fill(fill, ts)
        except Exception:
            pass
        try:
            self.lt_hold.record_fill(fill, ts, post_fill_qty=post_fill_qty)
        except Exception:
            pass

    def _get_sector(self, ticker: str) -> str:
        s = self.sector_map.get(ticker, "Unknown")
        return s

    def _sector_exposure(self, sector: str, price_map: Dict[str, float]) -> float:
        """Calculate current exposure to a specific sector (0.0 to 1.0)."""
        if not self.portfolio or not sector or sector == "Unknown":
            return 0.0
        
        eq = float(self.portfolio.total_equity(price_map))
        if eq <= 0:
            return 0.0
            
        sector_val = 0.0
        for t, pos in self.portfolio.positions.items():
            if pos.qty == 0: continue
            if self._get_sector(t) == sector:
                px = price_map.get(t, pos.avg_price if pos.avg_price else 0.0)
                sector_val += abs(pos.qty * px) # Gross exposure
        
        return sector_val / eq

    # Main prepare_order insertion point is below...
    # (Updated prepare_order to follow in next block)
    
    # ... helpers ...
    
    def prepare_order(self, signal, equity, df_hist, price_data=None, current_qty=0, target_weights=None):
        # ... (start of prepare_order same as before) ...
        ticker = str(signal.get("ticker"))
        side = str(signal.get("side", "none")).lower()
        
        # ... (validation, warmup, cooldown, flip logic) ...
        # Copy existing checks here (abbreviated for tool call, will use multi_replace or ensure context matches)
        # Actually, best to insert the sector check right before sizing.
        
        # Let's use a targeted replace for the specific insertion point to allow cleaner diff.
        # This block is just defining the class structure.
        return None # Placeholder for this specific tool call approach

        
    # ------------------------------------------------------------------ #
    # Lifecycle Management (Trailing Stops)
    def manage_positions(self, current_prices: Dict[str, float], regime_meta: Dict[str, Any] = None, data_map: Optional[Dict[str, pd.DataFrame]] = None) -> List[Dict[str, Any]]:
        """
        Check all open positions and generate 'update' orders (e.g. moving stops).
        Shared logic for Backtest and Live.

        Parameters
        ----------
        data_map : optional dict of {ticker: DataFrame} with ATR column
            When provided, trailing stops use real ATR instead of a price-based estimate.
        """
        # T-2026-06-11-153 — cache the per-bar data_map reference so the
        # yang_zhang vol-target estimator can reach OHLC frames without
        # changing any prepare_order call signature (threading price_data
        # into prepare_order is NOT canon-inert — the sector-check block
        # reads it when present). A reference assignment with no reader
        # on the default path ("rolling"/"ewma" ignore it) — zero
        # behavioral change until estimator_type="yang_zhang" is enabled.
        if data_map is not None:
            self._last_data_map = data_map

        # T-2026-06-06-118 — advance the regime-transition overlay ONCE per
        # bar. This method runs every bar in the backtest loop (before
        # prepare_order), so it is the per-bar hook for the overlay's
        # combined-posterior buffer. Placed BEFORE the enable_trailing
        # early-return so the buffer never gaps. Idempotent by timestamp;
        # strict no-op (no state touched) when the overlay is disabled.
        if self.cfg.regime_transition_overlay_enabled and regime_meta:
            _ov_ts = regime_meta.get("timestamp")
            if _ov_ts:
                self.regime_overlay.observe(
                    _ov_ts,
                    self.regime_overlay.combined_posterior(regime_meta),
                )

        if not self.portfolio or not self.cfg.enable_trailing:
            return []

        updates = []

        # Default regime if missing
        if not regime_meta:
            regime_meta = {"volatility": "normal"}

        vol_state = regime_meta.get("volatility", "normal")

        # Regime-adaptive trailing distance (matches entry stop behavior)
        if vol_state == "high":
            trail_dist_mult = self.cfg.high_vol_stop_mult
        elif vol_state == "low":
            trail_dist_mult = self.cfg.low_vol_stop_mult
        else:
            trail_dist_mult = self.cfg.trailing_stop_dist_atr

        for ticker, pos in self.portfolio.positions.items():
            if pos.qty == 0:
                continue

            curr_price = current_prices.get(ticker)
            if not curr_price:
                continue

            # -- update state --
            is_long = pos.qty > 0

            # Initial State Init (if new position)
            if pos.highest_high < 0 and is_long:
                 pos.highest_high = pos.avg_price
            if pos.lowest_low > 1e8 and not is_long:
                 pos.lowest_low = pos.avg_price

            # Track Extremes
            if is_long:
                if curr_price > pos.highest_high:
                    pos.highest_high = curr_price
            else:
                if curr_price < pos.lowest_low:
                     pos.lowest_low = curr_price

            # -- Compute ATR for this ticker --
            # Use real ATR from data_map when available; fall back to price estimate
            estimated_atr = curr_price * 0.015  # fallback
            if data_map and ticker in data_map:
                df = data_map[ticker]
                if "ATR" in df.columns and not df["ATR"].dropna().empty:
                    real_atr = float(df["ATR"].dropna().iloc[-1])
                    estimated_atr = self._effective_atr(curr_price, real_atr)

            # -- Check Activation --
            # Activate trailing when price moves 1R in favor (1R ≈ stop_mult * ATR)
            activation_dist = estimated_atr * trail_dist_mult
            threshold_pct = activation_dist / curr_price if curr_price > 0 else 0.015

            dist_from_entry = (curr_price - pos.avg_price) / pos.avg_price if pos.avg_price else 0
            if not is_long: dist_from_entry = -dist_from_entry

            if dist_from_entry > threshold_pct:
                pos.trailing_active = True

            if not pos.trailing_active:
                continue

            # -- Calculate Trailing Stop Level --
            trail_dist = estimated_atr * trail_dist_mult

            new_stop = None
            if is_long:
                proposed = pos.highest_high - trail_dist
                # Only move UP
                if pos.stop is None or proposed > pos.stop:
                    new_stop = proposed
            else:
                proposed = pos.lowest_low + trail_dist
                # Only move DOWN
                if pos.stop is None or proposed < pos.stop:
                    new_stop = proposed

            if new_stop is not None:
                updates.append({
                    "ticker": ticker,
                    "action": "update_stop",
                    "new_stop": new_stop,
                    "meta": {"reason": "trailing_stop", "regime": vol_state,
                             "atr": estimated_atr, "trail_mult": trail_dist_mult}
                })

        return updates

    # ------------------------------------------------------------------ #
    # Helpers
    def _fail(self, ticker: str, reason: str) -> None:
        self.last_skip_reason = reason
        self.last_skip_by_ticker[ticker] = reason

    def _bar_index(self, df_hist: pd.DataFrame) -> int:
        """Return a monotone bar index for cooldown comparisons."""
        # Using length-1 as a simple increasing counter (0..N-1)
        return int(max(len(df_hist) - 1, 0))

    def _last_row(self, df: pd.DataFrame) -> pd.Series:
        if isinstance(df, pd.DataFrame) and not df.empty:
            return df.iloc[-1]
        return pd.Series(dtype=float)

    def _effective_atr(self, price: float, atr: float) -> float:
        cap = self.cfg.cap_atr_to_pct_of_price * price
        floor = self.cfg.atr_floor_pct_of_price * price
        a = float(atr)
        if a > cap:
            a = cap
        if a < floor:
            a = floor
        return a

    def _positions_count(self) -> int:
        try:
            return sum(1 for p in self.portfolio.positions.values() if p.qty != 0)  # type: ignore[union-attr]
        except Exception:
            return 0

    def _compute_portfolio_vol_scalar(
        self, advisory: Optional[Dict[str, Any]] = None,
    ) -> float:
        """T-2026-05-12-055: portfolio-level vol-target sizing modifier.

        Returns 1.0 (no-op passthrough) when:
        - the feature is disabled (cfg.portfolio_vol_target_enabled=False, default),
        - self.portfolio is None (no controller injection yet), OR
        - the snapshot history is shorter than the warmup window.

        Otherwise returns a value in [floor, ceiling] per Moreira-Muir.
        This is a SIZING MODIFIER — it NEVER overrides kill-switch or
        drawdown-halt. Those gates run elsewhere in prepare_order and
        short-circuit before this scalar is applied.

        T-2026-05-23-055e: optional `advisory` kwarg threads the
        Engine E regime_summary through to the regime-conditional
        target multiplier. When `portfolio_vol_target_regime_aware=False`
        (default) OR advisory is None, behavior is identical to T-055d.
        """
        if not self.cfg.portfolio_vol_target_enabled:
            return 1.0
        if self.portfolio is None:
            return 1.0
        try:
            from engines.engine_b_risk.vol_target import (
                VolTargetConfig, compute_portfolio_vol_scale,
            )
            vt_cfg = VolTargetConfig(
                enabled=True,
                target_annual_vol=self.cfg.portfolio_vol_target_annual_vol,
                realized_vol_window_days=self.cfg.portfolio_vol_target_window_days,
                leverage_floor=self.cfg.portfolio_vol_target_floor,
                leverage_ceiling=self.cfg.portfolio_vol_target_ceiling,
                min_returns_required=self.cfg.portfolio_vol_target_min_returns_required,
                estimator_type=self.cfg.portfolio_vol_target_estimator_type,
                ewma_lambda=self.cfg.portfolio_vol_target_ewma_lambda,
                regime_aware=self.cfg.portfolio_vol_target_regime_aware,
                benign_target_multiplier=self.cfg.portfolio_vol_target_benign_multiplier,
                cautious_target_multiplier=self.cfg.portfolio_vol_target_cautious_multiplier,
                stressed_target_multiplier=self.cfg.portfolio_vol_target_stressed_multiplier,
                crisis_target_multiplier=self.cfg.portfolio_vol_target_crisis_multiplier,
                # T-153: sigma-floor guard (Fix A) + yang_zhang option
                # (Fix B). All default-inert; see RiskConfig comments.
                vol_floor_enabled=self.cfg.portfolio_vol_target_floor_enabled,
                vol_floor_annual=self.cfg.portfolio_vol_target_floor_annual,
                vol_floor_full_sample_frac=self.cfg.portfolio_vol_target_floor_full_sample_frac,
                yz_window_days=self.cfg.portfolio_vol_target_yz_window_days,
            )
            history = getattr(self.portfolio, "history", None) or []
            return compute_portfolio_vol_scale(
                history, vt_cfg, advisory=advisory,
                data_map=self._last_data_map,
                positions=getattr(self.portfolio, "positions", None),
            )
        except _PROGRAMMER_ERRORS:
            # Same fail-loud discipline as the drawdown kill switch: a
            # TypeError / AttributeError here is a bug in vol_target
            # logic, not a missing-data condition. Surface it.
            raise
        except Exception as e:
            # Operational error (e.g., transient snapshot shape drift):
            # fall back to 1.0 so the order pipeline degrades to "no
            # vol-target overlay" rather than dropping the trade.
            logger.warning(
                "[RISK] portfolio vol-target scalar fell back to 1.0 "
                "(no overlay applied): %s: %s",
                type(e).__name__, e,
            )
            return 1.0

    def _gross_exposure(self, price_map: Dict[str, float]) -> float:
        """
        Approximate gross exposure = Σ|qty*px| / equity.
        Requires portfolio reference; returns 0.0 if unavailable.
        """
        if self.portfolio is None:
            return 0.0
        eq = float(self.portfolio.total_equity(price_map))  # type: ignore[union-attr]
        if eq <= 0:
            return float("inf")
        gross = 0.0
        for t, pos in self.portfolio.positions.items():  # type: ignore[union-attr]
            if pos.qty == 0:
                continue
            px = float(price_map.get(t, pos.avg_price if pos.avg_price else 0.0))
            gross += abs(pos.qty * px)
        return gross / eq

    def _check_liquidity(self, ticker: str, qty: int, df_hist: pd.DataFrame) -> bool:
        """
        Professional Check: Ensure we don't exceed x% of Average Daily Volume (ADV).
        """
        if df_hist is None or "Volume" not in df_hist.columns:
            # If no volume data, pass (or fail strict). Failing strict is safer for Pro mode.
            if is_debug_enabled("RISK"):
                print(f"[RISK][WARN] No Volume column for {ticker}. Liquidity check skipped (unsafe).")
            return True # Soft pass for now, strictly should be False
            
        # Calculate ADV
        vol_window = self.cfg.adv_window
        if len(df_hist) < vol_window:
            adv = df_hist["Volume"].mean() # Fallback to whatever we have
        else:
            adv = df_hist["Volume"].iloc[-vol_window:].mean()
            
        if adv <= 0:
            return False # No liquidity
            
        # Check size
        limit_qty = adv * self.cfg.max_pct_adv
        if abs(qty) > limit_qty:
            if is_debug_enabled("RISK"):
                print(f"[RISK][FAIL] Liquidity fail {ticker}: Req {abs(qty)} > Limit {int(limit_qty)} (ADV={int(adv)})")
            return False
            
        return True

    # ------------------------------------------------------------------ #
    # Main
    def prepare_order(
        self,
        signal: Dict[str, Any],
        equity: float,
        df_hist: pd.DataFrame,
        price_data: Optional[Dict[str, pd.DataFrame]] = None,
        current_qty: int = 0,
        target_weights: Optional[Dict[str, float]] = None,
        regime_meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Build an order dict or return None if constraints block it.

        Parameters
        ----------
        signal : dict
            From AlphaEngine. Expected keys: {'ticker', 'side' in {'long','short','none'}, ...}
        equity : float
            Current total equity.
        df_hist : DataFrame
            Historical bars for the *ticker* (must include 'Close'; ATR preferred).
        price_data : Optional[Dict[str, DataFrame]]
            Optional whole-universe data (unused by default, kept for future cross checks).
        current_qty : int
            Current signed quantity for the ticker (0 if flat).
        target_weights : Optional[Dict[str, float]]
            Optional target weights from PortfolioPolicy (ticker → weight).

        Returns
        -------
        dict | None
            {'ticker','side','qty','stop','take_profit', 'meta': {...}}  or None.
        """
        ticker = str(signal.get("ticker"))
        side = str(signal.get("side", "none")).lower()

        # Reset last-skip for this ticker
        self.last_skip_by_ticker.pop(ticker, None)
        self.last_skip_reason = None

        # Validate side
        from debug_config import is_debug_enabled
        if side not in ("long", "short", "none"):
            self._fail(ticker, "invalid_side")
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
            return None

        # Warmup
        import os
        debug_override = os.getenv("BACKTEST_DEBUG") or os.getenv("ALPHA_DEBUG")
        if len(df_hist) < self.cfg.min_bars_warmup and not debug_override:
            self._fail(ticker, "warmup_insufficient_bars")
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
            return None
        elif len(df_hist) < self.cfg.min_bars_warmup and debug_override:
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Warmup insufficient but BACKTEST_DEBUG override enabled for {ticker}")

        # Cooldown (optional): require N bars between orders per ticker
        if self.cfg.cooldown_bars > 0:
            bi = self._bar_index(df_hist)
            last_bi = self._last_action_bar.get(ticker, -10_000)
            if (bi - last_bi) < int(self.cfg.cooldown_bars):
                self._fail(ticker, "cooldown_active")
                if is_debug_enabled("RISK"):
                    print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
                return None

        # Exit / neutral signals
        if side == "none" and current_qty != 0:
            # Path A — long-term hold preference. When enabled (default
            # off), defer signal-driven exits in the 300-364 day window
            # if the federal ST→LT tax-rate delta exceeds estimated
            # alpha lift of exiting now. Hard cap at 380 days. Hard SL/TP
            # exits bypass this gate entirely (they happen in
            # ExecutionSimulator, not here).
            try:
                if self.lt_hold.cfg.enabled:
                    now_ts = pd.Timestamp(df_hist.index[-1]) if len(df_hist) else None
                    last_close = None
                    try:
                        _last = df_hist.iloc[-1].get("Close")
                        last_close = float(_last)
                    except Exception:
                        last_close = None
                    pos_obj = None
                    if self.portfolio is not None:
                        pos_obj = self.portfolio.positions.get(ticker)
                    avg_px = float(pos_obj.avg_price) if pos_obj is not None else 0.0
                    if (
                        now_ts is not None
                        and last_close is not None
                        and avg_px > 0
                        and self.lt_hold.should_defer_exit(
                            ticker=ticker,
                            current_qty=int(current_qty),
                            avg_price=avg_px,
                            current_price=last_close,
                            now=now_ts,
                        )
                    ):
                        self._fail(ticker, "lt_hold_deferred")
                        if is_debug_enabled("RISK"):
                            print(f"[RISK][DEBUG] {ticker} exit deferred — "
                                  f"LT hold preference active "
                                  f"(stats={self.lt_hold.stats})")
                        return None
            except Exception:
                # Fail-open: never let the new module block normal exits if it errors.
                pass
            # Record action bar if we do emit an exit
            self._last_action_bar[ticker] = self._bar_index(df_hist)
            return {
                "ticker": ticker,
                "side": "exit",
                "qty": abs(int(current_qty)),
                "edge": signal.get("edge", "Unknown"),
                "edge_group": signal.get("edge_group"),
                "edge_id": signal.get("edge_id"),
                "edge_category": signal.get("category"),
            }
        if side == "none":
            self._fail(ticker, "neutral_no_position")
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
            return None

        # Flip logic: if holding opposite direction, exit first (entry deferred to next bar by controller)
        if current_qty != 0:
            have_long = current_qty > 0
            want_long = (side == "long")
            if have_long != want_long:
                self._last_action_bar[ticker] = self._bar_index(df_hist)
                return {
                    "ticker": ticker,
                    "side": "exit",
                    "qty": abs(int(current_qty)),
                    "edge": signal.get("edge", "Unknown"),
                    "edge_group": signal.get("edge_group"),
                    "edge_id": signal.get("edge_id"),
                    "edge_category": signal.get("category"),
                }

        # --- Detect flip in signal direction (close and reverse next bar) ---
        # Note: portfolio.positions retains entries with qty=0 after a full
        # exit (fresh Position() is stored back under the ticker). Those
        # zero-qty stubs must not be treated as open positions — otherwise
        # the qty>0/<=0 branch below mislabels a flat stub as "short" and
        # emits a spurious "exit qty=0" order against any incoming long.
        current_pos = None
        try:
            if self.portfolio and ticker in self.portfolio.positions:
                _p = self.portfolio.positions[ticker]
                if _p is not None and int(_p.qty) != 0:
                    current_pos = _p
        except Exception:
            current_pos = None

        if current_pos:
            current_side = "long" if current_pos.qty > 0 else "short"
            if (current_side == "long" and side == "short") or (current_side == "short" and side == "long"):
                self._last_action_bar[ticker] = self._bar_index(df_hist)
                if is_debug_enabled("RISK"):
                    print(f"[RISK][DEBUG] Signal flip detected for {ticker}: closing current {current_side} before reversing.")
                return {
                    "ticker": ticker,
                    "side": "exit",
                    "qty": abs(int(current_pos.qty)),
                    "reason": "flip_reversal",
                    "edge": signal.get("edge", "Unknown"),
                    "edge_group": signal.get("edge_group"),
                    "edge_id": signal.get("edge_id"),
                    "edge_category": signal.get("category"),
                }

        # No-shorts policy
        if side == "short" and not self.cfg.allow_shorts:
            self._fail(ticker, "shorts_not_allowed")
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
            return None

        # Path A — wash-sale avoidance gate. When enabled (default off),
        # refuse new opens on tickers that had a loss-realizing close
        # within `wash_sale.window_days` (default 30, IRS rule). Prevents
        # wash-sale loss disallowance at the source for high-turnover
        # taxable-account deployments. Fail-open on unexpected error.
        try:
            if (
                self.wash_sale.cfg.enabled
                and side in ("long", "short")
                and current_qty == 0
                and len(df_hist) > 0
            ):
                now_ts = pd.Timestamp(df_hist.index[-1])
                if self.wash_sale.should_block_buy(ticker, now_ts):
                    self._fail(ticker, "wash_sale_window_active")
                    if is_debug_enabled("RISK"):
                        print(f"[RISK][DEBUG] {ticker} buy blocked — "
                              f"wash-sale window active "
                              f"(stats={self.wash_sale.stats})")
                    return None
        except Exception:
            pass

        # --- Advisory-driven dynamic constraints (from Engine E) ---
        advisory = (regime_meta or {}).get("advisory", {}) if regime_meta else {}
        effective_max_positions = self.cfg.max_positions
        effective_max_gross = self.cfg.max_gross_exposure
        effective_sector_cap = self.cfg.max_sector_exposure_pct
        advisory_risk_scalar = 1.0

        if advisory and self.cfg.risk_advisory_enabled:
            # Dynamic max positions (can only tighten, never loosen)
            suggested_max_pos = advisory.get("suggested_max_positions")
            if suggested_max_pos is not None:
                effective_max_positions = min(int(suggested_max_pos), self.cfg.max_positions)

            # Dynamic gross exposure cap
            suggested_exposure_cap = advisory.get("suggested_exposure_cap")
            if suggested_exposure_cap is not None:
                effective_max_gross = min(float(suggested_exposure_cap), self.cfg.max_gross_exposure)

            # Risk scalar applied to ATR sizing
            rs = advisory.get("risk_scalar")
            if rs is not None:
                advisory_risk_scalar = float(rs)

            # Correlation regime → dynamic sector limits
            corr_regime = advisory.get("correlation_regime", "normal")
            if corr_regime == "dispersed":
                effective_sector_cap = min(0.40, self.cfg.max_sector_exposure_pct * 1.33)
            elif corr_regime in ("elevated", "spike"):
                effective_sector_cap = min(0.20, self.cfg.max_sector_exposure_pct * 0.67)

        # Portfolio constraints (using advisory-adjusted limits)
        if self._positions_count() >= effective_max_positions and current_qty == 0:
            self._fail(ticker, "max_positions_reached")
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)} (effective_max={effective_max_positions})")
            return None

        # Price & ATR
        row = self._last_row(df_hist)
        close_val = None
        if isinstance(row.get("Close", None), pd.Series):
            close_val = row["Close"].iloc[-1]
        else:
            close_val = row.get("Close")
        if close_val is None or not np.isfinite(close_val):
            self._fail(ticker, "close_missing")
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
            return None
        price = float(close_val)
        raw_atr = float(row.get("ATR", 0.0))
        # --- Sanity filter for abnormal prices/ATR ---
        if price <= 0 or not np.isfinite(price):
            self._fail(ticker, "invalid_price")
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
            return None
        if not np.isfinite(raw_atr) or raw_atr <= 0:
            # Fallback ATR: use rolling stddev of Close prices
            if len(df_hist) > 5 and "Close" in df_hist:
                raw_atr = float(df_hist["Close"].pct_change().rolling(5).std().iloc[-1] * price)
                if is_debug_enabled("RISK"):
                    print(f"[RISK][DEBUG] Fallback ATR used for {ticker}: {raw_atr:.4f}")
            if not np.isfinite(raw_atr) or raw_atr <= 0:
                self._fail(ticker, "invalid_atr_after_fallback")
                if is_debug_enabled("RISK"):
                    print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
                return None
        if raw_atr > price * 0.5:
            if is_info_enabled() or is_debug_enabled("RISK"):
                print(f"[RISK][WARN] Abnormally large ATR for {ticker}: atr={raw_atr}, price={price}")
            raw_atr = price * 0.2  # clamp for safety
        atr = self._effective_atr(price, raw_atr)

        # --- T-2026-05-12-055: portfolio-level vol-target scalar.
        # Pure sizing modifier — applied AFTER existing risk constraints
        # (drawdown halt + kill switch are evaluated separately inside
        # the sizing path and short-circuit BEFORE this multiplication
        # is applied to a final order). Default OFF (cfg flag False) →
        # returns 1.0 → no behavior change. NEVER overrides kill-switch
        # / drawdown-halt logic. Reads from self.portfolio.history with
        # the same defensive try/except discipline as the drawdown
        # kill switch above.
        # T-055e: pass the advisory dict (already extracted at line 707
        # for position-cap / risk-scalar consumers) through to the
        # vol-target overlay. When cfg.portfolio_vol_target_regime_aware
        # is False (default), the overlay ignores the advisory and
        # behaves identically to T-055d.
        portfolio_vol_scalar = self._compute_portfolio_vol_scalar(advisory=advisory)

        # --- Sizing path A: align to target weights (if provided/enabled) ---
        add_qty: int
        chosen_side: str = side
        # Initialize meta from signal to preserve upstream intelligence (regime, edges)
        meta: Dict[str, Any] = signal.get("meta", {}).copy() if signal.get("meta") else {}

        target_weight = None
        if self.cfg.enforce_target_allocations and target_weights:
            target_weight = target_weights.get(ticker)

        # T-2026-06-05-111 PoC — Path-A drawdown kill-switch PRE-PATH block.
        # Lifts the drawdown halt + degrade out of the Path-B `else:` block
        # (where they have been dead in production since R1; see T-106
        # `docs/Audit/drawdown_killswitch_ab_t106_2026_06_05.md`) so they
        # can fire on the live Path A path too.
        #   - Default OFF (both flags False) → block is skipped entirely;
        #     canon-md5 bitwise-identical to pre-T-111 main.
        #   - Active only when BOTH `drawdown_kill_switch_enabled=True`
        #     (existing R1 flag) AND `drawdown_kill_switch_apply_on_path_a=True`
        #     (new T-111 flag). Pairing prevents accidentally activating
        #     the lift while the legacy Path-B block is also enabled, and
        #     keeps director-gated A/B clean.
        # Halt: short-circuits with `return None` regardless of path.
        # Degrade: produces a multiplier `_drawdown_size_mult` that is
        # consumed by Path A (`target_notional *= ...`) below and by
        # Path B (`risk_scaler *= ...`) further down. Composes coherently
        # with the existing Path A advisory caps (`suggested_max_positions`
        # + `suggested_exposure_cap`) — the advisory caps are absolute
        # ceilings (min(suggested, cfg)) while the drawdown multiplier
        # scales `target_notional`, so they stack additively (cap then
        # scale, scaler can only further reduce, never grow). No
        # double-cut risk.
        _drawdown_size_mult: float = 1.0
        if (
            self.cfg.drawdown_kill_switch_enabled
            and self.cfg.drawdown_kill_switch_apply_on_path_a
            and self.portfolio is not None
        ):
            dd_pct = 0.0
            try:
                if self.portfolio.history:
                    dd_pct = float(self.portfolio.history[-1].get("current_drawdown_pct", 0.0))
            except Exception as e:
                # Same fail-loud-on-programmer-error discipline as the
                # legacy Path-B kill-switch (T-2026-05-08-012 narrowed catch).
                if isinstance(e, _PROGRAMMER_ERRORS):
                    raise
                logger.warning(
                    "[RISK] Drawdown calc fell back to 0.0 in PoC pre-path "
                    "block — kill switch may be inert: %s: %s",
                    type(e).__name__, e,
                )
                dd_pct = 0.0
            if dd_pct >= self.cfg.drawdown_halt_threshold:
                self._fail(ticker, "drawdown_halt_path_a")
                if is_debug_enabled("RISK"):
                    print(f"[RISK] PRE-PATH Drawdown halt: {dd_pct*100:.2f}% ≥ "
                          f"{self.cfg.drawdown_halt_threshold*100:.2f}% — blocking new entry for {ticker}")
                return None
            if dd_pct >= self.cfg.drawdown_degrade_threshold:
                _drawdown_size_mult = float(self.cfg.drawdown_degrade_scaler)
                if is_debug_enabled("RISK"):
                    print(f"[RISK] PRE-PATH Drawdown de-gross: {dd_pct*100:.2f}% ≥ "
                          f"{self.cfg.drawdown_degrade_threshold*100:.2f}% — size multiplier ×"
                          f"{_drawdown_size_mult:.2f}")

        # T-2026-06-06-116 PoC — Path-A wiring for the HMM-modulated advisory
        # risk_scalar de-gross. Mirrors the _drawdown_size_mult shape above.
        # `advisory_risk_scalar` was already extracted at ~line 753 (defaults
        # to 1.0; set to advisory['risk_scalar'] only when an advisory is
        # present AND risk_advisory_enabled). It is consumed in Path B
        # (`risk_scaler *= advisory_risk_scalar`) but DEAD on Path A — this
        # block lifts it onto Path A's `target_notional` behind a default-OFF
        # flag. Default OFF (flag False) → mult stays 1.0 → canon-md5
        # bitwise-identical to current main. DOUBLE-COUNT GUARD: composes as
        # min() against the LIVE exposure-cap ceiling (`effective_max_gross`,
        # ~line 1191) — the cap is an absolute ceiling enforced AFTER this
        # multiplier, so "more conservative wins" on total gross (no
        # double-cut). Orthogonal to the live `effective_max_positions`
        # count-floor; the cap-slack count×size compounding is the one item
        # the director-gated A/B must measure (see the T-116 audit doc).
        _advisory_risk_scalar_mult: float = 1.0
        if (
            self.cfg.advisory_risk_scalar_apply_on_path_a
            and self.cfg.risk_advisory_enabled
        ):
            _advisory_risk_scalar_mult = float(advisory_risk_scalar)
            if is_debug_enabled("RISK") and _advisory_risk_scalar_mult != 1.0:
                print(f"[RISK] PRE-PATH advisory risk_scalar de-gross (Path A): "
                      f"size multiplier ×{_advisory_risk_scalar_mult:.3f}")

        # T-2026-06-06-118 — HMM regime-transition gross-exposure overlay.
        # The overlay state is advanced once per bar in manage_positions;
        # here we (idempotently) ensure it is current for this bar and read
        # the gross multiplier. Default OFF -> 1.0 -> canon-identical. When
        # armed, multiplies Path A's target_notional (de-grossing the
        # rebalance target). Uses regime_meta['timestamp'] as the bar key
        # (same source as the manage_positions hook -> idempotent).
        _regime_overlay_mult: float = 1.0
        if self.cfg.regime_transition_overlay_enabled:
            _ov_ts = regime_meta.get("timestamp") if regime_meta else None
            if _ov_ts:
                self.regime_overlay.observe(
                    _ov_ts,
                    self.regime_overlay.combined_posterior(regime_meta),
                )
            _regime_overlay_mult = float(self.regime_overlay.current_multiplier())
            if is_debug_enabled("RISK") and _regime_overlay_mult != 1.0:
                print(f"[RISK] PRE-PATH regime-transition overlay de-gross (Path A): "
                      f"size multiplier ×{_regime_overlay_mult:.3f} "
                      f"(armed={self.regime_overlay.armed})")

        # T-2026-06-26-245 — optimizer_weight (Engine C HRP composition weight)
        # read ONCE here. Path A (target_weight) and Path B (else) below are
        # mutually exclusive, so it is applied exactly once per order — into
        # `target_notional` (Path A) or `risk_scaler` (Path B). Previously read
        # identically in BOTH branches (a DRY duplication — NOT a double-apply;
        # see the T-245 investigation). When method="hrp_composed", the HRP
        # weight (per-ticker HRP × N, clamped) multiplies into sizing so HRP
        # composes with PortfolioPolicy / edge-conviction rather than
        # overriding it. Default 1.0 = strict no-op (method="weighted_sum" or
        # the signal lacks the key).
        sig_meta_in = signal.get("meta") or {}
        optimizer_weight = float(sig_meta_in.get("optimizer_weight", 1.0))
        if target_weight is not None and np.isfinite(target_weight):
            # T-055: portfolio_vol_scalar = 1.0 unless cfg.portfolio_vol_target_enabled.
            # T-111: _drawdown_size_mult = 1.0 unless both
            # drawdown_kill_switch_enabled AND
            # drawdown_kill_switch_apply_on_path_a are True AND drawdown is
            # past the degrade threshold. Composes multiplicatively with
            # target_weight, optimizer_weight, and portfolio_vol_scalar.
            # T-116: _advisory_risk_scalar_mult = 1.0 unless
            # advisory_risk_scalar_apply_on_path_a AND risk_advisory_enabled
            # are both True. Lifts the HMM-modulated advisory.risk_scalar
            # (dead on Path A pre-T-116) onto production sizing.
            # T-118: _regime_overlay_mult = 1.0 unless
            # regime_transition_overlay_enabled AND the transition trigger is
            # armed (k-day Delta in combined HMM posterior crossed tau_on,
            # not yet stood down by the asymmetric hysteresis). De-grosses
            # the rebalance target on a regime transition into stress.
            # T-2026-06-26-243 — NOTE on the executed-book leverage (T-215/T-232):
            # this per-name composition has no CROSS-NAME / CROSS-BAR cash budget,
            # but adding one HERE does NOT fix the borrow. The executed-book
            # leverage (1.70x gross / cash -73k in the T-232 smoke) is CROSS-BAR
            # accumulation of HELD positions that don't re-fire (they are never
            # re-sized — see backtest_controller `_generate_signals`, the
            # held-position block). A per-name cap on `target_notional` only sees
            # the bar's firing names (Sigma tw*ow usually < 1 -> never binds) and
            # cannot trim the held book; T-232 smoke-PROVED that per-name cap
            # insufficient. The correct fix is a BOOK-LEVEL de-gross post-pass
            # (Option A), default-OFF, gated by `deployable_cash_account` -- HELD
            # pending need (deployable equity-book re-run dropped, T-215 = H0).
            target_notional = (
                float(equity) * float(target_weight) * optimizer_weight
                * portfolio_vol_scalar * _drawdown_size_mult
                * _advisory_risk_scalar_mult * _regime_overlay_mult
            )
            current_notional = float(current_qty) * price
            delta_notional = target_notional - current_notional

            # Rebalance tolerance: skip tiny drifts
            denom = max(abs(target_notional), 1e-9)
            if abs(delta_notional) / denom < float(self.cfg.rebalance_tolerance):
                self._fail(ticker, "rebalance_within_tolerance")
                if is_debug_enabled("RISK"):
                    print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
                return None

            add_qty = int(delta_notional / price)
            if add_qty == 0:
                # Try to enforce a minimum 1-share adjustment if rounding-to-zero and notional is meaningful
                if self.cfg.force_min_qty_on_signal and abs(delta_notional) >= float(self.cfg.min_notional):
                    add_qty = 1
                else:
                    self._fail(ticker, "rebalance_rounds_to_zero")
                    if is_debug_enabled("RISK"):
                        print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
                    return None

            chosen_side = "long" if add_qty > 0 else "short"
            add_qty = abs(add_qty)

            meta.update({
                "sizing_mode": "target_weight",
                "target_weight": float(target_weight),
                "target_notional": float(target_notional),
                "current_notional": float(current_notional),
                "delta_notional": float(delta_notional),
            })

        else:
            # --- Sizing path B: ATR-risk sizing (default) ---
            
            # DYNAMIC RISK: Adjust multiplier based on Regime
            # signal.meta might contain 'market_state' -> 'volatility'
            # e.g. {'market_state': {'volatility': 'high'}}
            vol_state = "normal"
            try:
                ms = meta.get("market_state", {})
                if isinstance(ms, dict):
                    vol_state = ms.get("volatility", "normal")
            except Exception:
                pass
                
            stop_mult = self.cfg.atr_stop_mult
            if vol_state == "high":
                stop_mult = self.cfg.high_vol_stop_mult
                if is_debug_enabled("RISK"): print(f"[RISK] High Vol detected: Widening stop to {stop_mult}x ATR")
            elif vol_state == "low":
                stop_mult = self.cfg.low_vol_stop_mult
                if is_debug_enabled("RISK"): print(f"[RISK] Low Vol detected: Tightening stop to {stop_mult}x ATR")
                
            stop_dist = max(stop_mult * atr, 1e-9)
            
            # --- Dynamic Sizing ---
            base_risk_pct = self.cfg.risk_per_trade_pct
            risk_scaler = 1.0

            # 1. ML Gate Confidence (if explicitly set by SignalGate/MLPredictor)
            # Low confidence sizes down, but never to zero — a market-state-only
            # gate should not have veto power over a real alpha signal.
            gate_conf = signal.get("gate_confidence")
            if gate_conf is not None:
                gate_conf = float(gate_conf)
                if gate_conf < 0.5: risk_scaler = 0.3
                elif gate_conf < 0.6: risk_scaler = 0.6
                elif gate_conf < 0.8: risk_scaler = 1.0
                else: risk_scaler = 1.5
            else:
                # 2. Signal strength (from Alpha aggregation)
                strength = float(signal.get("strength", 0.5))
                risk_scaler = 0.5 + strength  # Maps [0,1] to [0.5, 1.5]

            # 3. Governor edge-quality weight (learned from realized performance)
            governor_weight = float(meta.get("governor_weight", 1.0))
            risk_scaler *= governor_weight

            # 4. Advisory risk scalar (Engine E regime brake on sizing)
            risk_scaler *= advisory_risk_scalar

            # 5. optimizer_weight (read once above; Path A/B are exclusive) —
            # HRP composes with the ATR-risk sizing (signal_strength +
            # governor_weight) rather than overwriting it. Default 1.0 = no-op.
            risk_scaler *= optimizer_weight

            # 5b. T-2026-05-12-055 portfolio-level vol-target overlay.
            # `portfolio_vol_scalar` was computed once at the top of
            # prepare_order and equals 1.0 unless the feature is
            # explicitly enabled in cfg. NEVER overrides kill-switch /
            # drawdown-halt (those short-circuit upstream by returning
            # None or applying drawdown_degrade_scaler).
            risk_scaler *= portfolio_vol_scalar

            # 6. Drawdown-gated kill switch (R1 punch-list, OFF by default).
            # Reads current_drawdown_pct from PortfolioEngine.snapshot() via
            # self.portfolio.history. INERT when the flag is False — current
            # behavior unchanged.
            if self.cfg.drawdown_kill_switch_enabled and self.portfolio is not None:
                dd_pct = 0.0
                try:
                    if self.portfolio.history:
                        dd_pct = float(self.portfolio.history[-1].get("current_drawdown_pct", 0.0))
                except Exception as e:
                    # Narrowed-catch (T-2026-05-08-012): the kill switch
                    # silently defaulting to dd_pct=0.0 on TypeError is
                    # the catastrophic-failure mode for live trading.
                    # If Engine C's portfolio_snapshot schema ever
                    # drifts and emits a non-numeric current_drawdown_pct,
                    # the kill switch must FAIL LOUD — not silently fall
                    # back to "no kill." Programmer errors propagate.
                    # Operational errors (KeyError on a stale history
                    # shape, ValueError on a malformed numeric) keep the
                    # 0.0 fallback but warn unconditionally so the
                    # operator sees the kill-switch path is degraded.
                    if isinstance(e, _PROGRAMMER_ERRORS):
                        raise
                    logger.warning(
                        "[RISK] Drawdown calc fell back to 0.0 — "
                        "kill switch may be inert: %s: %s",
                        type(e).__name__, e,
                    )
                    dd_pct = 0.0
                if dd_pct >= self.cfg.drawdown_halt_threshold:
                    self._fail(ticker, "drawdown_halt")
                    if is_debug_enabled("RISK"):
                        print(f"[RISK] Drawdown halt: {dd_pct*100:.2f}% ≥ "
                              f"{self.cfg.drawdown_halt_threshold*100:.2f}% — blocking new entry for {ticker}")
                    return None
                if dd_pct >= self.cfg.drawdown_degrade_threshold:
                    risk_scaler *= self.cfg.drawdown_degrade_scaler
                    if is_debug_enabled("RISK"):
                        print(f"[RISK] Drawdown de-gross: {dd_pct*100:.2f}% ≥ "
                              f"{self.cfg.drawdown_degrade_threshold*100:.2f}% — risk scaler ×"
                              f"{self.cfg.drawdown_degrade_scaler:.2f}")
                elif dd_pct >= self.cfg.drawdown_warn_threshold and is_debug_enabled("RISK"):
                    print(f"[RISK] Drawdown warn: {dd_pct*100:.2f}% ≥ "
                          f"{self.cfg.drawdown_warn_threshold*100:.2f}% (no action)")

            adjusted_risk_pct = base_risk_pct * risk_scaler

            # Cap extreme risk (max 2x base)
            adjusted_risk_pct = min(adjusted_risk_pct, base_risk_pct * 2.0)

            risk_budget = max(0.0, float(equity) * adjusted_risk_pct)

            if is_debug_enabled("RISK") and risk_scaler != 1.0:
                 print(f"[RISK] Dynamic Sizing: {ticker} (strength={signal.get('strength', 'N/A')}, gov_w={governor_weight:.2f}) -> Scaler {risk_scaler:.2f} -> Risk {adjusted_risk_pct*100:.2f}%")

            if risk_budget <= 0:
                self._fail(ticker, "non_positive_risk_budget")
                
            # ... rest of sizing logic ...
            raw_qty = risk_budget / stop_dist
            max_value = float(equity) * self.cfg.max_pos_value_pct
            max_qty_by_value = (max_value / price) if price > 0 else 0.0
            target_qty = min(raw_qty, max_qty_by_value)
            if self.cfg.round_qty:
                target_qty = math.floor(target_qty)

            add_qty = int(max(target_qty - abs(int(current_qty)), 0))
            if is_debug_enabled("RISK"):
                print(
                    f"[RISK][DBG] {ticker} side={side} price={price:.4f} atr={atr:.4f} "
                    f"risk_budget={risk_budget:.2f} stop_dist={stop_dist:.4f} "
                    f"raw_qty={raw_qty:.2f} max_val={max_value:.2f} "
                    f"max_qty_by_value={max_qty_by_value:.2f} target_qty={target_qty:.2f} "
                    f"current_qty={current_qty} vol_state={vol_state}"
                )
            if add_qty <= 0:
                # If sizing rounded down to zero, optionally force a 1-share probe when safe
                forced = False
                if self.cfg.force_min_qty_on_signal and side in ("long", "short") and current_qty == 0:
                    # Ensure ticket clears minimum notional and (roughly) exposure
                    if price >= float(self.cfg.min_notional):
                        try:
                            price_map = {ticker: price}
                            gross_after = self._gross_exposure(price_map) + (abs(1 * price) / max(float(equity), 1e-9))
                            if gross_after <= float(self.cfg.max_gross_exposure):
                                add_qty = 1
                                forced = True
                        except Exception:
                            # If exposure check unavailable, still allow the 1-share probe
                            add_qty = 1
                            forced = True
                if not forced:
                    self._fail(ticker, "no_incremental_size")
                    if is_debug_enabled("RISK"):
                        delta = float(target_qty) - float(abs(current_qty))
                        print(
                            f"[RISK][DEBUG] Rejected signal for {ticker} — reason=no_incremental_size "
                            f"(target_qty={target_qty:.2f}, current_qty={current_qty}, delta={delta:.2f}, "
                            f"side={side})"
                        )
                    return None
                else:
                    meta.update({
                        "sizing_mode": meta.get("sizing_mode", "atr_risk"),
                        "forced_min_qty": True
                    })

            meta.update({
                "sizing_mode": "atr_risk",
                "risk_budget": float(risk_budget),
                "stop_dist": float(stop_dist),
                "atr": float(atr),
                "raw_qty": float(raw_qty),
                "max_value": float(max_value),
                "max_qty_by_value": float(max_qty_by_value),
                "target_qty": float(target_qty),
            })

        # Enforce minimum notional and min qty
        if add_qty < max(int(self.cfg.min_qty), 1):
            self._fail(ticker, "below_min_qty")
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
            return None

        # Liquidity Check (New)
        if not self._check_liquidity(ticker, add_qty, df_hist):
            self._fail(ticker, "liquidity_limit_exceeded")
            # Professional approach: Clip it. 
            vol_window = self.cfg.adv_window
            adv = df_hist["Volume"].iloc[-vol_window:].mean() if len(df_hist) >= vol_window else df_hist["Volume"].mean()
            limit_qty = int(adv * self.cfg.max_pct_adv)
            
            if limit_qty < self.cfg.min_qty:
                if is_debug_enabled("RISK"):
                    print(f"[RISK][DEBUG] Rejected {ticker}: ADV limit {limit_qty} < min_qty {self.cfg.min_qty}")
                return None
            else:
                if is_debug_enabled("RISK"):
                    print(f"[RISK][INFO] Clipping {ticker} qty {add_qty} -> {limit_qty} due to liquidity constraint.")
                add_qty = limit_qty

        # Min Notional Check
        if (add_qty * price) < float(self.cfg.min_notional):
            self._fail(ticker, "below_min_notional")
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
            return None

        # --- Fallback safety: ensure at least minimal order if everything else fails ---
        if add_qty <= 0 and debug_override:
            add_qty = 1
            meta.update({"sizing_mode": "fallback_fixed", "reason": "debug_forced_trade"})
            if is_debug_enabled("RISK"):
                print(f"[RISK][DEBUG] Forcing minimal 1-share trade for {ticker} in debug mode.")

        # Gross exposure guard
        try:
            price_map = {ticker: price}
            # For accurate sector calc, we ideally want a full price_map, but we usually only have 'price_data' if passed.
            # If price_data is None, we rely on portfolio.last_price for others.
            # Construct a best-effort price map for sector check:
            sector_price_map = {ticker: price}
            # If we have a portfolio, use its last known prices for others
            if self.portfolio:
                for t, p in self.portfolio.positions.items():
                    if p.last_price:
                        sector_price_map[t] = p.last_price
                        
            # 1. Sector Constraint Check (using advisory-adjusted cap)
            sector = self._get_sector(ticker)
            if sector and sector != "Unknown" and add_qty > 0:
                current_sec_exp = self._sector_exposure(sector, sector_price_map)
                new_trade_exp = (add_qty * price) / max(float(equity), 1e-9)

                if (current_sec_exp + new_trade_exp) > effective_sector_cap:
                     self._fail(ticker, f"max_sector_exposure_{sector}")
                     if is_debug_enabled("RISK"):
                        print(f"[RISK][DEBUG] Rejected signal for {ticker} — Sector {sector} exposure {current_sec_exp:.1%} + {new_trade_exp:.1%} > {effective_sector_cap:.1%}")
                     return None

            # 2. Gross Exposure Guard (using advisory-adjusted cap)
            gross_after = self._gross_exposure(sector_price_map) + (abs(add_qty * price) / max(float(equity), 1e-9))
            if gross_after > float(effective_max_gross):
                self._fail(ticker, "gross_exposure_limit")
                if is_debug_enabled("RISK"):
                    print(f"[RISK][DEBUG] Rejected signal for {ticker} — reason={self.last_skip_by_ticker.get(ticker)}")
                return None
        except Exception as e:
            # If portfolio not attached or other issue, fail open (but this is logged)
            if is_debug_enabled("RISK"): print(f"[RISK][WARN] Constraint check error: {e}")
            pass

        # Compute SL/TP levels off chosen_side (might differ from signal side if rebalancing)
        if chosen_side == "long":
            stop = price - self.cfg.atr_stop_mult * atr
            tp = price + self.cfg.atr_tp_mult * atr
        else:
            stop = price + self.cfg.atr_stop_mult * atr
            tp = price - self.cfg.atr_tp_mult * atr


        # Record action bar for cooldown purposes
        self._last_action_bar[ticker] = self._bar_index(df_hist)

        # Preserve edge attribution from the signal (if present)
        edge_name = signal.get("edge", "Unknown")
        edge_group = signal.get("edge_group", None)

        order = {
            "ticker": ticker,
            "side": chosen_side,
            "qty": int(add_qty),
            "stop": float(stop),
            "take_profit": float(tp),
            "meta": meta,   # logger will stringify safely
            "edge": edge_name,
            "edge_group": edge_group,
        }
        if "edge_id" in signal:
            order["edge_id"] = signal.get("edge_id")
        if "category" in signal:
            order["edge_category"] = signal.get("category")

        if is_debug_enabled("RISK"):
            print(f"[RISK][DEBUG] Approved order for {ticker}: {order}")
        return order