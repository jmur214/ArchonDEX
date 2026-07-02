---
name: engine-c-untracked-post-merge-capabilities
description: Engine C's deploy-stack post-processors (phase1_composition/dyn-opt/buffering/spot-sleeve/composer) all ship WIRED-but-default-OFF and are UNTRACKED in capability_ledger; the C ledger section went stale after the T-139/148/120/211 merge wave
metadata:
  type: project
---

Audit 2026-06-22 (engine="C-portfolio", capability-registry-vs-code). The capability_ledger Engine C section (rows 44-51, written 2026-06-04) was never refreshed through a big merge wave, leaving a cluster of UNTRACKED-but-wired capabilities — the same buried-capability blind spot that hid the conjunctive selector.

**The untracked-but-wired Engine C capabilities (all default-OFF, gated in `portfolio_engine.compute_target_allocations`):**
- `phase1_composition.py` (T-211): `apply_phase1_composition` wired at portfolio_engine.py:440-441 behind `phase1_composition_enabled` (policy.py:91). Defensive tilt (A/T-205) + trend-overlay scalar (E/T-204). Composition verdict pending the D/T-215 cloud cell (not refuted, not yet validated).
- `dynamic_optimizer.py` (T-139): `optimize_integer_positions` wired at :424-425 behind `dynamic_optimization_enabled`.
- `position_buffering.py` (T-148): `apply_position_buffering` wired at :433-434 behind `position_buffering_enabled`.
- `sleeves/spot_etf_trend_sleeve.py` `SpotETFTrendSleeve` (T-120): wired into init (:79-85) + snapshot equity (:322-331) behind `spot_sleeve_enabled` (policy.py:44). REFUTED-as-hedge (T-128r) but still wired.
- `composer.py` `PortfolioComposer` (HRP+turnover): reachable, but C-OWNED code DISPATCHED from Engine A (alpha_engine.py:571 construct, :799-800 call). Prod `method=weighted_sum` → strict no-op. The A-dispatch is the documented F4-inversion-fix (heavy logic correctly in C; only the call site is in A) — NOT a fresh boundary violation. Untracked in the ledger.

**Stale-row defects in the EXISTING C ledger rows (rows 44-51):**
1. Every `policy.py` line ref drifted: vol-ceiling 334→440; vol-floor 340→445; `_apply_exposure_cap` 380→463; `_apply_regime_overrides` 86→115; `allocation_recommendation` consumer 62→129. Symbols exist (Layer 3a WARN, not phantom).
2. The `EngineCAllocator`/`allocator.py` "missing-file" row (50) is STALE: the charter + index.md no longer reference allocator.py/EngineCAllocator at all (only a role-table "Allocator" label + "portfolio policy allocator" description). The dangling-doc-ref it describes was removed → retire the row.
3. Vol-target/exposure-cap reachability OVERSTATED: `data/research/allocation_recommendations.json` is ABSENT on disk → `_apply_regime_overrides` early-returns → mode stays mean_variance → those overlays don't fire in prod. Ledger says "mode-gated"; truth is "no (prod mean_variance; adaptive-only, recs file absent)". (gitignored/regenerable so could reappear live.)

**The pattern (matches [[doc_gap_pattern_refuted_verdict_buries_shipped_capability]]):** Engine C's dominant doc-coverage drift is the DEPLOY-STACK ACCRETION — each Carver/composition lever (T-139/148/211) + the spot sleeve (T-120) ships default-OFF + canon-bitwise-when-off, the merge proves OFF-safety, and then nobody adds a ledger row because "it's off, it can't hurt." Default-OFF is precisely the ledger's inclusion criterion (it tracks the flag + reachability so the off knob isn't nobody's responsibility). Five C capabilities accreted this way. Sibling burials in other engines: [[engine_e_buried_defensive_capabilities]], [[engine_b_doc_buried_defensive_capabilities]], [[engine_f_buried_defensive_capabilities]].

**How to apply:** When auditing Engine C, the deploy-stack post-processors live in `portfolio_engine.compute_target_allocations` (grep `_enabled.*and weights` to enumerate the gated branches at ~:424/:433/:440) + the sleeve in init/snapshot. Verify each against the ledger — the ledger lags merges badly here. The composer lives in C but is called from A; check `alpha_engine.py` for the call site, not portfolio_engine. Prod config = `config/portfolio_settings.json` (mode=mean_variance, all `*_enabled`=false, method=weighted_sum). All current C deploy levers are OFF in prod → no live drift, only documentation drift.
