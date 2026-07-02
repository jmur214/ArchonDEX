---
name: engine-c-buried-crisis-degross
description: Engine C already has its OWN regime-conditional crisis de-gross path (sibling to the Engine B/E one), buried because T-055 vol-target work was refuted
metadata:
  type: project
---

Engine C (`engines/engine_c_portfolio/policy.py`) contains a regime-conditional crisis de-gross that NO living doc surfaces — the exact failure mode flagged for Engine B/E.

**The buried capabilities (all in `policy.py`) — LINE NUMBERS DRIFTED, re-verified 2026-06-22:**
- `_apply_vol_target` (def at :404; ceiling logic :440, clamp :445 — was 334-352): regime-aware UPSIDE CEILING. Caps leverage to 1.0× in `market_turmoil`/`cautious_decline`/`stressed`/`crisis`, 1.4× in `transitional`, legacy 2.0× in benign/unknown. Reads label from `regime_meta["macro_regime"].label` (5-state HMM) then `forward_stress_regime.state`. Engine-C SIBLING to Engine B's `portfolio_vol_target_crisis_multiplier=0.40`.
- `_apply_vol_target` downside FLOOR = 0.3 (clamp lower bound, :445): keeps ≥30% gross in vol spikes — a de-gross LIMITER.
- `_apply_exposure_cap` (def at :463 — was 370-391): consumes Engine E `suggested_exposure_cap`. DOUBLE-CONSUMED with Engine B. Boundary ambiguity (C vs B) undocumented.

**Reachability is WEAKER than the prior memory stated (corrected 2026-06-22):** both overlays live ONLY in the adaptive-mode branch (after the mean_variance early-`return` at `policy.py:292`). The prior memory said `data/research/allocation_recommendations.json` recommends adaptive for every regime → overlays flip on. BUT that file is now ABSENT on disk → `_apply_regime_overrides` (`policy.py:115`) hits its `except: return` (:146-147) → mode stays mean_variance → these overlays do NOT fire in prod. CURRENT_STATE confirms "mean_variance is production; adaptive artifact archived (T-167)." The file is gitignored/regenerable so it COULD reappear live; treat reachability as "no (prod mean_variance; adaptive-only, recommendations file absent)" not "mode-gated active". The capability_ledger rows 44-46 still state the old (overstated) reachability — STALE.

**Why it was buried (the pattern):** T-055e/g/h vol-target work touched this code, was REFUTED on 12-yr (Δ Sharpe -0.214), so MEMORY recorded the negative VERDICT not the shipped CAPABILITY. Same root cause as the Engine B/E crisis path discovery that motivated the T-092 Path B audit. See [[engine_f_evolution_controller_does_d_work]] for a different drift pattern.

**Also buried in Engine C — sleeve scaffold has GROWN (re-checked 2026-06-22):** `sleeves/` ships `MultiSleeveAggregator` + `TrendFollowingSleeve` (CTA momentum/inverse-vol) + `MoonshotSleeve` (asymmetric-upside) — all default-OFF, imported ONLY by research `scripts/` (managed_futures_*, sleeve_phase0_verdict), NEVER by the controller → still orphaned. NEW since the prior audit: `sleeves/spot_etf_trend_sleeve.py` (`SpotETFTrendSleeve`, T-120) — this one IS wired into `portfolio_engine.py` init (:79-85) + snapshot equity (:322-331) behind `spot_sleeve_enabled` (policy.py:44, default OFF). Its crisis-MDD thesis is REFUTED (T-128r, "NOT a drawdown hedge") but it still ships wired — refuted-verdict-buries-shipped-capability. None of the four sleeves is in capability_ledger or DESIGN_FIDELITY (DESIGN_FIDELITY only lumps "sleeve" into a blanket REFUTED row).

**How to apply:** When Path B asks "what crisis de-gross does the system already have?", the answer spans THREE engines: E (advisory crisis label), B (vol-target crisis multiplier + drawdown kill-switch, both default-OFF) AND C (regime-aware vol ceiling + exposure-cap, BUT prod-unreachable while the recommendations file is absent + mode=mean_variance). Don't assume C is purely passive accounting — but also don't overstate the C overlays as live; they are adaptive-only and prod runs mean_variance. See [[engine_c_untracked_post_merge_capabilities]] for the wider untracked-capability sweep.
