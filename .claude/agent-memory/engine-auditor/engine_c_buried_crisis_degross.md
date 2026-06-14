---
name: engine-c-buried-crisis-degross
description: Engine C already has its OWN regime-conditional crisis de-gross path (sibling to the Engine B/E one), buried because T-055 vol-target work was refuted
metadata:
  type: project
---

Engine C (`engines/engine_c_portfolio/policy.py`) contains a regime-conditional crisis de-gross that NO living doc surfaces — the exact failure mode flagged for Engine B/E.

**The buried capabilities (all in `policy.py`):**
- `_apply_vol_target` (lines 334-352): regime-aware UPSIDE CEILING. Caps leverage to 1.0× in `market_turmoil`/`cautious_decline`/`stressed`/`crisis`, 1.4× in `transitional`, legacy 2.0× in benign/unknown. Reads label from `regime_meta["macro_regime"].label` (5-state HMM) then `forward_stress_regime.state`. This is the Engine-C SIBLING to Engine B's `portfolio_vol_target_crisis_multiplier=0.40` (`risk_engine.py:116`).
- `_apply_vol_target` downside FLOOR = 0.3 (clamp lower bound): deliberately keeps ≥30% gross in vol spikes — a de-gross LIMITER, relevant to "how hard can Path B cut?".
- `_apply_exposure_cap` (lines 370-391): consumes Engine E `suggested_exposure_cap`. DOUBLE-CONSUMED — Engine B `risk_engine.py:736` applies the same cap to `effective_max_gross`. Boundary ambiguity (C vs B owns exposure-cap enforcement) is undocumented → possible compounding de-gross.

**Why it's reachable despite prod `mode:"mean_variance"`:** both overlays live ONLY in the adaptive-mode branch (after the mean_variance early-return at `policy.py:200`). BUT `data/research/allocation_recommendations.json` recommends `mode:"adaptive"` for every regime, and `_apply_regime_overrides` (`policy.py:86`) treats "mode" as a known-safe override key → the crisis overlays can flip on at allocation time. Governor `allocation_evaluation_enabled=True` (default), `auto_apply_allocation=False`.

**Why it was buried (the pattern):** T-055e/g/h vol-target work touched this code, was REFUTED on 12-yr (Δ Sharpe -0.214), so MEMORY recorded the negative VERDICT not the shipped CAPABILITY. Same root cause as the Engine B/E crisis path discovery that motivated the T-092 Path B audit. See [[engine_f_evolution_controller_does_d_work]] for a different drift pattern.

**Also buried in Engine C:** `sleeves/` ships `MultiSleeveAggregator` + `TrendFollowingSleeve` (CTA momentum/inverse-vol) + `MoonshotSleeve` (asymmetric-upside), all default-OFF and NEVER wired into BacktestController. CURRENT_STATE.md names a future "trend/managed-futures positive-skew sleeve" (Path B Layer 2) without noting this scaffold already exists.

**How to apply:** When Path B asks "what crisis de-gross does the system already have?", the answer spans THREE engines: E (advisory crisis label), B (vol-target crisis multiplier + drawdown kill-switch, both default-OFF) AND C (regime-aware vol ceiling + exposure-cap, reachable via the adaptive-mode flip). Don't assume C is purely passive accounting.
