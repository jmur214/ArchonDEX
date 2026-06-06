"""
engines/engine_b_risk/regime_transition_overlay.py
==================================================
T-2026-06-06-118 — HMM regime-TRANSITION-triggered gross-exposure overlay.

This is the "culmination" experiment scaffold (propose-first, default-OFF):
convert the validated Engine-E HMM combined posterior
``p_combined = p_crisis + p_stressed`` from a *level* into a *transition
trigger* that de-grosses new Path-A sizing, with asymmetric hysteresis.

WHY a transition trigger and NOT a level
----------------------------------------
T-105 measured the live (60-bar causal) combined posterior at threshold
0.5: it is in the stressed-or-crisis state **44-50% of the time** with
p90 run-length **198-265 days** (max 632d). Consumed as a *level*
de-gross, that re-creates the documented "always-on light leverage"
pathology even though the signal's AUC is high (T-103 AUC@5d 0.914 on
the crisis model / T-087 0.848 on the production model). The signal IS
informative about *forward* drawdown — so it is usable as a **transition
trigger** (fire on the Δ as the regime shifts toward stress), not as a
continuously-on level. See:
  - docs/Audit/hmm_repoint_window_revalidate_t105_2026_06_05.md
  - docs/Audit/hmm_crisis_retrain_t103_2026_06_04.md
  - docs/Audit/engine_e_regime_rediagnosis_t087_2026_05_30.md
  - docs/Audit/hmm_transition_trigger_overlay_t118_2026_06_06.md (this task)

CAUSAL-PATH CONTRACT (look-ahead-critical)
------------------------------------------
This overlay consumes ONLY the per-bar posterior already produced by the
live backtest path (``regime_meta['hmm_regime']['probabilities']``),
which is computed via ``HMMRegimeClassifier.predict_proba_at`` on a
60-bar GROWING window (filtered/forward-only, last row only) — NEVER the
forward-backward ``predict_proba_sequence``. T-089 verified the live
path is causal (look-ahead inflation bounded +0.0015..+0.006 AUC). This
module adds NO new inference; it only differences a posterior series the
engine already computes causally, so it cannot introduce look-ahead on
its own.

DESIGN (mirrors the T-111/T-116 Path-A multiplier shape)
--------------------------------------------------------
The overlay is a stateful, per-portfolio (NOT per-ticker) tracker. It is
fed the combined posterior once per bar and emits a gross-exposure
multiplier in {degross_level, 1.0}. Engine B multiplies that into Path
A's ``target_notional`` (composing with optimizer_weight,
portfolio_vol_scalar, T-111 _drawdown_size_mult, T-116
_advisory_risk_scalar_mult). Because Path A is target-weight
*rebalancing*, scaling the target IS a gross-exposure scaling: the book
rebalances toward the de-grossed target.

DOUBLE-COUNT NOTE (carried forward from T-116)
----------------------------------------------
This multiplier co-fires with the LIVE advisory floors
(suggested_exposure_cap + suggested_max_positions), all keyed off the
same Engine-E risk_score. Per the T-116 analysis it composes as min()
vs the exposure-cap ceiling (no double-cut on gross) but compounds
multiplicatively (count x size) vs the max_positions floor in the
cap-slack crisis regime. The A/B must log per-cell crisis-window
realized gross. See the T-118 audit doc.

Default OFF -> ``current_multiplier()`` returns 1.0 and ``observe`` is
never called by Engine B, so canon-md5 is bitwise-identical to the
T-092 baseline.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Deque, Optional, Tuple


@dataclass
class RegimeOverlayConfig:
    """Pre-registered overlay parameters (see the T-118 grid).

    The campaign sweeps:
      - degross_level   in {1.0, 0.5, 0.0}   (1.0 = neutral/null arm)
      - k_days          in {3, 5, 10}        (Delta lookback)
      - (degross_delta, regross_level, regross_bars) = one of 4 fixed
        hysteresis pairs (re-gross strictly slower than de-gross).
    """
    enabled: bool = False
    degross_level: float = 1.0      # gross multiplier applied WHEN armed
    k_days: int = 5                 # Delta(p_combined) lookback in bars
    degross_delta: float = 0.40     # tau_on: arm when Delta_k >= this
    regross_level: float = 0.30     # tau_off: p_combined ceiling to count as "calm"
    regross_bars: int = 10          # n_off: consecutive calm bars to disarm


class RegimeTransitionOverlay:
    """Stateful, deterministic, idempotent-by-timestamp transition trigger.

    Call ``observe(now_ts, p_combined)`` once per bar (Engine B does this
    from ``manage_positions``, which runs every bar; ``prepare_order``
    also calls it, guarded idempotently so per-ticker calls on the same
    bar do not double-advance the state). Then read
    ``current_multiplier()`` to get the gross multiplier for the bar.
    """

    def __init__(self, cfg: RegimeOverlayConfig):
        self.cfg = cfg
        # maxlen k+1 so buf[-1]=p_t and buf[0]=p_{t-k} when full.
        self._buf: Deque[float] = deque(maxlen=max(int(cfg.k_days), 1) + 1)
        self._armed: bool = False
        self._bars_calm: int = 0
        self._last_ts: Optional[object] = None
        self._last_mult: float = 1.0

    # ------------------------------------------------------------------ #
    def observe(self, now_ts: object, p_combined: float) -> float:
        """Advance the trigger state for a NEW bar; idempotent within a bar.

        Returns the current multiplier (also available via
        ``current_multiplier``). When disabled, this is a strict no-op
        returning 1.0 and never mutates state.
        """
        if not self.cfg.enabled:
            return 1.0
        # Idempotency: same bar (multiple tickers) must not re-advance.
        if self._last_ts is not None and now_ts == self._last_ts:
            return self._last_mult
        self._last_ts = now_ts

        p = float(p_combined)
        self._buf.append(p)

        k = max(int(self.cfg.k_days), 1)
        if len(self._buf) >= k + 1:
            delta_k = self._buf[-1] - self._buf[0]  # p_t - p_{t-k}, causal
            if not self._armed:
                # De-gross (arm) on a sharp upward transition into stress.
                if delta_k >= self.cfg.degross_delta:
                    self._armed = True
                    self._bars_calm = 0
            else:
                # Re-gross (disarm) — strictly SLOWER/asymmetric: require
                # p_combined to sit at-or-below the calm ceiling for
                # n_off CONSECUTIVE bars before standing down.
                if p <= self.cfg.regross_level:
                    self._bars_calm += 1
                    if self._bars_calm >= int(self.cfg.regross_bars):
                        self._armed = False
                        self._bars_calm = 0
                else:
                    self._bars_calm = 0  # reset on any non-calm bar

        self._last_mult = float(self.cfg.degross_level) if self._armed else 1.0
        return self._last_mult

    # ------------------------------------------------------------------ #
    def current_multiplier(self) -> float:
        """Gross multiplier for the current bar (1.0 when disabled/disarmed)."""
        if not self.cfg.enabled:
            return 1.0
        return self._last_mult

    # ------------------------------------------------------------------ #
    @property
    def armed(self) -> bool:
        return self._armed

    def state(self) -> Tuple[bool, int, float]:
        """(armed, bars_calm, last_mult) — for diagnostics/observability."""
        return self._armed, self._bars_calm, self._last_mult

    @staticmethod
    def combined_posterior(regime_meta: Optional[dict]) -> float:
        """Extract p_crisis + p_stressed from regime_meta, fail-safe to 0.0.

        Returns 0.0 (=> never arms) when the HMM block is absent (HMM
        disabled or schema drift) so the overlay degrades gracefully to
        inert rather than firing on missing data.
        """
        if not regime_meta:
            return 0.0
        hmm = regime_meta.get("hmm_regime") or {}
        probs = hmm.get("probabilities") or {}
        try:
            return float(probs.get("crisis", 0.0)) + float(probs.get("stressed", 0.0))
        except (TypeError, ValueError):
            return 0.0
