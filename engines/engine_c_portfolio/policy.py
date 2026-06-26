# engines/engine_c_portfolio/policy.py
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PortfolioPolicyConfig:
    """
    Configuration for the portfolio policy allocator.
    """
    mode: str = "adaptive"               # adaptive | parrondo_fixed
    target_volatility: float = 0.15      # portfolio-level target annualized vol (15%)
    vol_target_enabled: bool = True      # toggle the _apply_vol_target overlay for A/B
    exposure_cap_enabled: bool = True    # toggle the advisory exposure cap overlay for A/B
    min_weight: float = -0.1             # minimum per-asset weight (for shorts)
    max_weight: float = 0.25             # maximum per-asset weight

    # T-2026-06-25-230 — DEPLOYABLE cash-account mode (default OFF; OFF ⇒
    # canon byte-identical). D's T-215 found the mean_variance book runs to
    # ~2.32× gross (borrowing) + holds shorts (min_weight −0.1) — neither is
    # executable in a $5–15K CASH Roth (no margin, no borrow, no short). When
    # ON, `_apply_deployable_constraints` projects the allocator's output onto
    # the executable cone: LONG-ONLY (zero shorts), per-name [0,
    # deployable_max_weight], and gross Σw ≤ deployable_max_gross (no leverage;
    # the cash residual 1−Σw is simply uninvested). A default-OFF projection of
    # the final weights — the director reviews before any default-flip.
    deployable_cash_account: bool = False
    deployable_max_weight: float = 0.25  # per-name cap when deployable (long-only)
    deployable_max_gross: float = 1.0    # Σw cap when deployable (no leverage)

    # T-2026-06-26-241 — moonshot probe C1: top-K CONCENTRATION / conviction-
    # weighting (default OFF; OFF ⇒ canon byte-identical). The diversified book
    # may CANCEL alpha (the ensemble-alpha paradox); C1 asks whether concentrating
    # into the top-K highest-conviction names (|combined signal score|),
    # conviction-weighted, surfaces an upside half. Amplifies the right tail via
    # ASSET SELECTION, NOT gross (cash Roth = no leverage — gross is preserved,
    # just reallocated into fewer names). The director reviews before any flip.
    concentration_enabled: bool = False
    concentration_top_k: int = 10        # number of highest-conviction names to hold
    vol_lookback: int = 20               # bars to use for rolling volatility
    rebalance_threshold: float = 0.02    # rebalance if deviation exceeds 2%
    risk_free_rate: float = 0.0
    debug: bool = False
    
    # Parrondo / Fixed Mode Settings
    fixed_allocations: Optional[Dict[str, float]] = None # e.g. {"SPY": 0.5, "SHV": 0.5}

    # T-2026-06-06-120 — spot 8-ETF crisis-diversifier sleeve, Phase 1 wiring.
    # When `spot_sleeve_enabled=True`, PortfolioEngine partitions capital:
    # the equity book runs on `(1 - spot_sleeve_capital_pct)` of initial
    # capital; the spot 8-ETF basket sleeve (SPY/TLT/GLD/USO/UUP/EEM/IEF/DBC,
    # monthly rebalance, top-N=4, lookback=252, vol_window=63, max_pos=0.30)
    # runs independently on the remaining `spot_sleeve_capital_pct` and its
    # PnL is added to `equity` via PortfolioEngine.snapshot(). Faithful
    # capital-partition match to T-115's analytical result.
    #
    # Default OFF preserves pre-T-120 production behavior and canon-md5
    # bitwise-identical (no sleeve code runs when False). Production flag-flip
    # requires the T-120 A/B evidence + director/user gate; this dispatch
    # ships the wiring + measurement, not the prod-default change.
    spot_sleeve_enabled: bool = False
    spot_sleeve_capital_pct: float = 0.25

    # T-2026-06-10-139 — Carver dynamic optimization (integer-position
    # layer). When `dynamic_optimization_enabled=True`,
    # PortfolioEngine.compute_target_allocations post-processes the
    # allocator's unrounded target weights into integer-share-feasible
    # weights via the greedy tracking-error minimizer in
    # `dynamic_optimizer.py` (concept port of pysystemtrade's
    # dynamic_small_system_optimise). Engine B's Path A then lands
    # exactly on the chosen whole-share positions — no Engine B change.
    #
    # Default OFF preserves pre-T-139 production behavior canon-md5
    # bitwise-identical (the post-processing branch never runs and the
    # optimizer module is never imported when False). Production
    # flag-flip requires integrated A/B evidence + director/user gate;
    # T-139 ships wiring + fixture demonstration, not the prod change.
    dynamic_optimization_enabled: bool = False
    dynopt_shadow_cost: float = 10.0             # Carver default
    dynopt_cost_per_trade_bps: float = 10.0      # matches turnover_flat_cost_bps
    dynopt_tracking_error_buffer: float = 0.02   # Carver default (annualized TE)
    dynopt_buying_power_fraction: float = 1.0    # gross Σ|w| hard cap
    dynopt_max_weight_per_asset: Optional[float] = None
    dynopt_cov_lookback: int = 60                # matches HRPConfig.cov_lookback
    dynopt_use_ledoit_wolf: bool = True          # matches HRPConfig

    # T-2026-06-11-148 — Carver position buffering (10% inertia).
    # When enabled, PortfolioEngine.compute_target_allocations
    # post-processes targets through trade-to-edge buffering
    # (position_buffering.py), composing AFTER dynamic optimization
    # when both are on. POSITION-level trade-to-edge — NOT T-098's
    # refuted weight-level no-trade-or-full-trade band; see the module
    # docstring + docs/Audit/position_buffering_t148_2026_06_11.md.
    # Default OFF = pre-T-148 behavior canon-bitwise. No prod flip; a
    # real enable rides a pre-registered A/B (the T-098 precedent
    # demands the deep-window test before any adoption claim).
    position_buffering_enabled: bool = False
    buffer_fraction: float = 0.10                # Carver convention

    # T-2026-06-18-211 — Phase-1 COMPOSITION (default OFF; OFF ⇒ bitwise-identical
    # canon). When ON, a post-processor (engines/engine_c_portfolio/
    # phase1_composition.py) shapes the book: (a) defensive tilt — zero the A/T-205
    # high-IVOL/lottery exclusions + haircut non-quality longs toward the quality
    # set, renormalized so the tilt is a RELATIVE shift not a de-gross; (b) trend
    # overlay — scale gross by the E/T-204 EW SPY/AGG/GLD 5-month long/flat
    # exposure scalar (the drawdown-cutting lever; cash when flat). Engine-C scope
    # only — NOT an Engine-B admission gate; vol-target (Engine B) is EXCLUDED.
    phase1_composition_enabled: bool = False
    phase1_quality_haircut: float = 0.5          # non-quality long multiplier (1.0 = off)
    phase1_trend_lookback_days: int = 105        # 5-month SMA (E/T-204 best config)
    phase1_trend_assets: tuple = ("SPY", "AGG", "GLD")


class PortfolioPolicy:
    """
    Determines target position weights.
    Modes:
      - 'adaptive': Inverse Volatility weighted by Signal Strength (Bensdorp).
      - 'parrondo_fixed': Rebalance to fixed targets regardless of signals (Parrondo).
    """

    def __init__(self, cfg: Optional[PortfolioPolicyConfig] = None):
        self.cfg = cfg or PortfolioPolicyConfig()
        self._base_cfg_snapshot = {
            "max_weight": self.cfg.max_weight,
            "target_volatility": self.cfg.target_volatility,
            "rebalance_threshold": self.cfg.rebalance_threshold,
            "mode": self.cfg.mode,
        }

    # ------------------------------------------------------------------ #
    def _apply_regime_overrides(self, regime_meta: Optional[Dict] = None) -> None:
        """Temporarily override cfg params from allocation recommendations for this regime."""
        # Reset to base first
        for k, v in self._base_cfg_snapshot.items():
            setattr(self.cfg, k, v)

        if not regime_meta:
            return

        # Check for allocation recommendations in advisory
        advisory = regime_meta.get("advisory", {})
        if not advisory:
            return

        alloc_rec = advisory.get("allocation_recommendation")
        if not alloc_rec or not isinstance(alloc_rec, dict):
            # Try loading from disk
            try:
                from engines.engine_c_portfolio.allocation_evaluator import AllocationEvaluator
                evaluator = AllocationEvaluator()
                evaluator.load_recommendations()

                macro = regime_meta.get("macro_regime")
                if isinstance(macro, dict):
                    label = macro.get("label", "_global")
                elif isinstance(macro, str):
                    label = macro
                else:
                    label = "_global"

                alloc_rec = evaluator.get_config_for_regime(label)
            except Exception:
                return

        if not alloc_rec:
            return

        # Apply overrides (only for known safe keys)
        for key in ("max_weight", "target_volatility", "rebalance_threshold", "mode"):
            if key in alloc_rec:
                setattr(self.cfg, key, alloc_rec[key])

    # ------------------------------------------------------------------ #
    def compute_vol_estimates(self, price_data: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """
        Compute annualized volatility per asset based on the last N bars.
        Returns dict: {ticker: vol}
        """
        vols = {}
        for tkr, df in price_data.items():
            if "Close" not in df.columns or len(df) < self.cfg.vol_lookback:
                continue
            returns = df["Close"].pct_change().dropna()
            if returns.empty:
                continue
            vol = returns.tail(self.cfg.vol_lookback).std() * np.sqrt(252)
            vols[tkr] = float(vol)
        return vols

    # ------------------------------------------------------------------ #
    def allocate(self,
                 signals: Dict[str, float],
                 price_data: Dict[str, pd.DataFrame],
                 equity: float,
                 current_weights: Dict[str, float] = None,
                 regime_meta: Optional[Dict] = None) -> Dict[str, float]:
        """
        Compute target weights for each asset.
        """
        # --- Apply learned allocation recommendations (regime-conditional) ---
        self._apply_regime_overrides(regime_meta)

        # 1. Parrondo / Fixed Mode
        # Ignores 'signals' (Alpha) effectively, or treats signal existence as 'tradable'.
        # Returns hardcoded weights to force mechanical rebalancing.
        if self.cfg.mode == "parrondo_fixed" and self.cfg.fixed_allocations:
            # Normalize just in case
            raw = self.cfg.fixed_allocations
            total = sum(abs(v) for v in raw.values())
            if total > 0:
                return {k: v/total for k, v in raw.items()}
            return raw

        # 2. Mean-Variance Optimization Mode (Professional)
        if self.cfg.mode == "mean_variance":
            mvo_weights = self._allocate_mean_variance(signals, price_data, current_weights)
            if mvo_weights is not None:
                return mvo_weights
            # None ⇒ <5 bars of history → fall through to adaptive

        # 3. Adaptive Mode (Default) (Inverse Vol Model)
        return self._allocate_adaptive(signals, price_data, regime_meta)

    # ------------------------------------------------------------------ #
    def _allocate_mean_variance(self,
                                signals: Dict[str, float],
                                price_data: Dict[str, pd.DataFrame],
                                current_weights: Dict[str, float] = None
                                ) -> Optional[Dict[str, float]]:
        """Mean-variance (MVO) allocation. Extracted verbatim from ``allocate``
        (T-246 god-function split; byte-identical). Returns the MVO target
        weights, ``{}`` when no returns are available, or ``None`` when there is
        too little history (<5 bars) — the None signals ``allocate`` to fall
        through to the adaptive mode (preserving the original ``pass``)."""
        if self.cfg.mode == "mean_variance":
            # Lazy import to avoid circular dep if not used
            from .optimizer import PortfolioOptimizer
            optimizer = PortfolioOptimizer(risk_aversion=1.0) # Could be configurable in cfg

            # Prepare Inputs: Mu (Expected Returns) and Sigma (Covariance)
            mu_series = pd.Series(signals)
            
            # Sigma: Compute covariance
            returns_map = {}
            for tkr in price_data:
                if tkr in signals:
                    df = price_data[tkr]
                    if not df.empty and "Close" in df.columns:
                        returns_map[tkr] = df["Close"].pct_change()
            
            if not returns_map:
                return {} 
                
            returns_df = pd.DataFrame(returns_map).fillna(0.0)
            if len(returns_df) < 5:
                pass 
            else:
                # T-140-fu3: deterministic (fixed-reduction-order) cov — pandas
                # .cov() routes through OpenBLAS gemm whose accumulation order
                # varies across Fargate tasks (~1e-15 Sigma drift → the lottery).
                from .optimizer import deterministic_cov
                sigma_df = deterministic_cov(returns_df) * 252.0
                mu_series = mu_series.reindex(sigma_df.columns).fillna(0.0)

                # T-140-fu2 env-gated capture probe: byte-hash each
                # intermediate so a multi-task cloud run can NAME the first
                # bitwise-divergent array (returns_df -> Sigma -> mu) in the
                # cov->MVO composition. Off by default; zero cost when unset.
                if os.environ.get("ARCHONDEX_COV_MVO_PROBE"):
                    import hashlib as _hl
                    def _h(a):
                        return _hl.md5(np.ascontiguousarray(
                            np.asarray(a, dtype=np.float64)).tobytes()).hexdigest()[:12]
                    _cols = _hl.md5("|".join(map(str, returns_df.columns)).encode()).hexdigest()[:12]
                    print(f"[COVMVO_PROBE] cols={_cols} returns_hash={_h(returns_df.values)} "
                          f"sigma_hash={_h(sigma_df.values)} mu_hash={_h(mu_series.values)} "
                          f"nrows={len(returns_df)}", flush=True)

                # --- Diversification: Load Sector Map ---
                # T-2026-06-13-167: `os` is module-level (line 4). A function-local
                # `import os` HERE made `os` local to allocate() for the whole
                # scope, so the earlier os.environ.get(...) at the T-140-fu2
                # cov→MVO probe (~line 220) raised UnboundLocalError on EVERY
                # mean_variance bar. The controller's broad except swallowed it →
                # silent 0-trades. The Apr-23 allocator artifact (adaptive mode)
                # masked this locally; archiving it (mean_variance = production)
                # exposed it. Removed the shadowing local import.
                import json
                sector_map = {}
                try:
                    # Try default location
                    if os.path.exists("config/sector_map.json"):
                        with open("config/sector_map.json", "r") as f:
                            sector_map = json.load(f)
                except Exception:
                    pass
                
                # Build Constraints
                
                # Align current_weights to mu_series index (tickers)
                c_weights_arr = np.zeros(len(mu_series))
                if current_weights:
                    # Normalize input weights just in case
                    for i, tkr in enumerate(mu_series.index):
                        c_weights_arr[i] = current_weights.get(tkr, 0.0)

                constraints = {
                    "sector_map": sector_map,
                    "max_sector_exposure": 0.30, # Hardcoded for now
                    "current_weights": c_weights_arr,
                    "cost_penalty": 0.0020 # 20bps friction
                }

                # Run Optimization
                abs_mu = mu_series.abs()
                weights_series = optimizer.optimize(abs_mu, sigma_df, constraints=constraints)
                
                # Re-apply signs and clamp to [min_weight, max_weight]
                weights_out = {}
                for tkr, w in weights_series.items():
                    signed_w = w * np.sign(signals.get(tkr, 0))
                    capped = float(np.clip(signed_w, self.cfg.min_weight, self.cfg.max_weight))
                    weights_out[tkr] = capped

                if self.cfg.debug:
                    print(f"[POLICY] min_weight={self.cfg.min_weight} max_weight={self.cfg.max_weight}")
                    print("[POLICY] MVO Targets (Optimized & Diversified):", weights_out)
                # T-241 concentrate (no-op OFF) → T-230 deployable cone (no-op OFF)
                return self._apply_deployable_constraints(
                    self._apply_concentration(weights_out, signals))
        return None
    # ------------------------------------------------------------------ #
    def _allocate_adaptive(self,
                           signals: Dict[str, float],
                           price_data: Dict[str, pd.DataFrame],
                           regime_meta: Optional[Dict] = None) -> Dict[str, float]:
        """Adaptive (inverse-vol) allocation — the default mode and the
        fall-through target when mean_variance has too little history (<5 bars)
        or parrondo_fixed has no fixed_allocations. Extracted verbatim from
        ``allocate`` (T-246 god-function split; byte-identical)."""
        if not signals:
            return {}

        vols = self.compute_vol_estimates(price_data)
        if not vols:
            # Fallback if no vol data: Equal Weight
            n = len(signals)
            return {t: (1.0/n) * np.sign(s) for t, s in signals.items()} if n > 0 else {}

        inv_vols = {}
        # Filter only tickers with vol data. Sorted so set-intersection iteration
        # order is stable across runs — FP aggregation of `total` downstream is
        # order-dependent, and an unsorted set here was the second source of
        # backtest non-determinism.
        available_tickers = sorted(set(signals.keys()).intersection(vols.keys()))

        for tkr in available_tickers:
            s_strength = signals[tkr]
            vol = vols[tkr]
            if vol <= 0 or not np.isfinite(vol):
                continue
            # Bensdorp Logic: Weight = Signal / Volatility
            inv_vols[tkr] = abs(s_strength) / vol

        if not inv_vols:
            return {}

        total = sum(inv_vols.values())
        weights = {}
        for tkr, iv in inv_vols.items():
            raw_w = (iv / total) * np.sign(signals[tkr])
            capped = np.clip(raw_w, self.cfg.min_weight, self.cfg.max_weight)
            weights[tkr] = float(capped)

        if self.cfg.debug:
            print("[POLICY] Vol estimates:", vols)
            print("[POLICY] Target weights (pre-overlay):", weights)

        # --- Portfolio-level vol targeting overlay ---
        if self.cfg.vol_target_enabled:
            weights = self._apply_vol_target(weights, price_data, regime_meta)

        # --- Advisory exposure cap (from Engine E regime detection) ---
        if self.cfg.exposure_cap_enabled:
            weights = self._apply_exposure_cap(weights, regime_meta)

        if self.cfg.debug:
            print("[POLICY] Final weights (post-overlay):", weights)

        # T-241 concentrate (no-op OFF) → T-230 deployable cone (no-op OFF)
        return self._apply_deployable_constraints(
            self._apply_concentration(weights, signals))

    # ------------------------------------------------------------------ #
    def requires_rebalance(self,
                           current_weights: Dict[str, float],
                           target_weights: Dict[str, float]) -> bool:
        """
        Determine whether the portfolio should rebalance based on deviation.
        """
        if not current_weights:
            return True
        dev = 0.0
        count = 0
        for t, target in target_weights.items():
            curr = current_weights.get(t, 0.0)
            dev += abs(target - curr)
            count += 1
        
        # Check for assets held but no longer in target
        for t, curr in current_weights.items():
            if t not in target_weights and abs(curr) > 0.001:
                dev += abs(curr)
                # count already handled partially, but really dev matters total
        
        avg_dev = dev / max(1, count)
        return avg_dev > self.cfg.rebalance_threshold

    # ------------------------------------------------------------------ #
    def _estimate_portfolio_vol(self, weights: Dict[str, float],
                                price_data: Dict[str, pd.DataFrame]) -> float:
        """Estimate annualized portfolio volatility from weights and recent returns."""
        tickers = [t for t in weights if t in price_data and abs(weights[t]) > 1e-9]
        if len(tickers) < 2:
            # Single asset or empty: return asset vol or fallback
            if tickers:
                vols = self.compute_vol_estimates(price_data)
                return vols.get(tickers[0], self.cfg.target_volatility)
            return self.cfg.target_volatility

        # Build returns matrix
        returns_map = {}
        for tkr in tickers:
            df = price_data[tkr]
            if "Close" in df.columns and len(df) >= self.cfg.vol_lookback:
                returns_map[tkr] = df["Close"].pct_change().tail(self.cfg.vol_lookback)

        if len(returns_map) < 2:
            return self.cfg.target_volatility

        returns_df = pd.DataFrame(returns_map).dropna()
        if len(returns_df) < 5:
            return self.cfg.target_volatility

        from .optimizer import deterministic_cov  # T-140-fu3 (same fixed-order cov)
        cov = deterministic_cov(returns_df) * 252.0  # annualized
        w_arr = np.array([weights.get(t, 0.0) for t in cov.columns])
        port_var = float(w_arr @ cov.values @ w_arr)
        return float(np.sqrt(max(port_var, 1e-12)))

    # ------------------------------------------------------------------ #
    def _apply_vol_target(self, weights: Dict[str, float],
                          price_data: Dict[str, pd.DataFrame],
                          regime_meta: Optional[Dict] = None) -> Dict[str, float]:
        """Scale weights so portfolio vol matches target_volatility.

        Asymmetric upside clamp (R1 audit-week-of, the "Minsky fix"):
        the symmetric [0.3, 2.0] clamp let the system run at 2× leverage
        whenever realized vol fell below target — i.e. it leveraged into
        calm markets, which is the textbook Minsky setup. The fix caps
        the upside at 1.0 (no leverage) in stressed/crisis regimes and
        only allows the legacy 2.0 ceiling in benign regimes.

        The downside floor (0.3) is unchanged — when realized vol spikes,
        keep at least 30% gross so the system isn't fully flat in the
        most informative environment.
        """
        if not weights:
            return weights

        port_vol = self._estimate_portfolio_vol(weights, price_data)
        if port_vol < 1e-9:
            return weights

        # Regime-aware upside ceiling. Sourced from Engine E's macro/forward
        # stress regime label when available; defaults to legacy 2.0 ceiling
        # under no-regime-context (preserves baseline reproducibility).
        upside_ceiling = 2.0
        regime_label = None
        if regime_meta:
            # Try the macro_regime label first (5-state HMM), then forward_stress.
            macro = regime_meta.get("macro_regime") or {}
            regime_label = macro.get("label") if isinstance(macro, dict) else None
            if regime_label is None:
                fs = regime_meta.get("forward_stress_regime") or {}
                regime_label = fs.get("state") if isinstance(fs, dict) else None
        if regime_label in ("market_turmoil", "cautious_decline", "stressed", "crisis"):
            upside_ceiling = 1.0  # no leverage in adverse regimes
        elif regime_label in ("transitional",):
            upside_ceiling = 1.4  # half-step
        # else: benign / unknown → legacy 2.0

        vol_scalar = float(np.clip(self.cfg.target_volatility / port_vol, 0.3, upside_ceiling))

        if abs(vol_scalar - 1.0) > 0.01:
            weights = {t: w * vol_scalar for t, w in weights.items()}
            # Re-clamp to max_weight
            weights = {t: float(np.clip(w, self.cfg.min_weight, self.cfg.max_weight))
                       for t, w in weights.items()}
            if self.cfg.debug:
                print(
                    f"[POLICY] Vol target: port_vol={port_vol:.3f} "
                    f"target={self.cfg.target_volatility:.3f} "
                    f"scalar={vol_scalar:.2f} ceiling={upside_ceiling:.1f} "
                    f"regime={regime_label or 'none'}"
                )

        return weights

    # ------------------------------------------------------------------ #
    def _apply_concentration(self, weights: Dict[str, float],
                             signals: Dict[str, float]) -> Dict[str, float]:
        """T-241 moonshot probe C1 — concentrate the book into the top-K
        highest-CONVICTION names (|combined signal score|), conviction-weighted,
        preserving the book's GROSS (reallocate, don't lever — cash Roth has no
        margin). Dropped names → 0. Gated by `concentration_enabled` (default
        OFF) ⇒ OFF returns the weights unchanged and the canon is byte-identical.
        Deterministic (conviction desc, ticker asc tie-break — no FP-order
        lottery, per the engine_c determinism rule)."""
        if not getattr(self.cfg, "concentration_enabled", False) or not weights:
            return weights
        k = int(getattr(self.cfg, "concentration_top_k", 10))
        # conviction = |combined signal score| over the WHOLE book (NOT the
        # post-allocator weights — the mean_variance optimizer already
        # concentrates to ~5 names, so subsetting its output would be a no-op
        # for any K≥5). C1 OVERRIDES the allocator's selection with the top-K
        # conviction names, conviction-weighted, on the allocator's gross.
        conv = {t: abs(float(s)) for t, s in signals.items() if abs(float(s)) > 1e-12}
        if k <= 0 or len(conv) <= k:
            return weights                                   # ≤ K conviction names → nothing to do
        gross = sum(abs(w) for w in weights.values()) or 1.0  # preserve the allocator's gross
        # rank by conviction DESC, then ticker ASC — fully deterministic.
        topk = sorted(conv.keys(), key=lambda t: (-conv[t], t))[:k]
        tot = sum(conv[t] for t in topk) or 1.0
        out = {t: 0.0 for t in set(weights) | set(topk)}     # drop non-top-K; add top-K conviction
        for t in topk:
            out[t] = (conv[t] / tot) * gross * (1.0 if float(signals.get(t, 0.0)) >= 0 else -1.0)
        if self.cfg.debug:
            print(f"[POLICY][C1] concentrated {len(conv)}→{len(topk)} conviction "
                  f"names (gross {gross:.3f} preserved, conviction-weighted)")
        return out

    # ------------------------------------------------------------------ #
    def _apply_deployable_constraints(self, weights: Dict[str, float]) -> Dict[str, float]:
        """T-230 — project the allocator's weights onto what a $5–15K CASH Roth
        can actually execute: LONG-ONLY (zero shorts — no borrow), each name in
        [0, deployable_max_weight], and gross Σw ≤ deployable_max_gross (no
        leverage; the residual 1−Σw is uninvested cash). Gated by
        `deployable_cash_account` (default OFF) → OFF ⇒ this returns the weights
        unchanged and the canon is byte-identical. [NN-FAIL-CLOSED] N/A (pure
        deterministic projection; no load-bearing input to be missing)."""
        if not getattr(self.cfg, "deployable_cash_account", False) or not weights:
            return weights
        mw = float(getattr(self.cfg, "deployable_max_weight", 0.25))
        mg = float(getattr(self.cfg, "deployable_max_gross", 1.0))
        # long-only + per-name clamp to [0, mw]; shorts (w<0) → 0
        out = {t: float(np.clip(w, 0.0, mw)) for t, w in weights.items()}
        gross = sum(out.values())   # all >= 0 → gross == Σw
        if mg > 0 and gross > mg:
            scale = mg / gross
            out = {t: w * scale for t, w in out.items()}   # de-lever to gross ≤ mg
        if self.cfg.debug:
            print(f"[POLICY][DEPLOYABLE] long-only + gross Σw {gross:.3f}→"
                  f"{min(gross, mg):.3f} (cap {mg}, per-name ≤ {mw})")
        return out

    # ------------------------------------------------------------------ #
    def _apply_exposure_cap(self, weights: Dict[str, float],
                            regime_meta: Optional[Dict] = None) -> Dict[str, float]:
        """Enforce advisory gross exposure cap from Engine E."""
        if not weights or not regime_meta:
            return weights

        advisory = regime_meta.get("advisory", {})
        if not advisory:
            return weights

        cap = advisory.get("suggested_exposure_cap")
        if cap is None:
            return weights

        cap = float(cap)
        gross = sum(abs(w) for w in weights.values())
        if gross > cap and gross > 1e-9:
            scale = cap / gross
            weights = {t: w * scale for t, w in weights.items()}
            if self.cfg.debug:
                print(f"[POLICY] Exposure cap: gross={gross:.3f} > cap={cap:.3f}, scaling by {scale:.2f}")

        return weights