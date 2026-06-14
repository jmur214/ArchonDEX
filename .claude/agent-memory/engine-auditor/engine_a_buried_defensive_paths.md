---
name: engine-a-buried-defensive-paths
description: Engine A (Alpha) ships two undocumented crisis de-gross paths the living docs miss — the risk_scalar brake in SignalProcessor and the active macro_yield_curve tilt edge
metadata:
  type: project
---

Engine A contains crisis/regime de-gross capabilities that NONE of the living docs (CURRENT_STATE.md, engine_charters.md, high_level_engine_function.md) surface as A capabilities. Found during the 2026-06-04 buried-capability audit (motivated by the Engine B+E `portfolio_vol_target_crisis_multiplier=0.40` advisory.py path that was buried because T-055 was refuted).

**Why:** Same buried-capability mechanism as Engine B+E — defensive paths that got touched during refuted experiments (T-057 confidence gate, T-055 vol-target) had their negative VERDICTs recorded in MEMORY/CURRENT_STATE but the still-shipped CAPABILITY was never documented.

**How to apply:** When scoping T-092 Path B (HMM crisis kill-switch), these are pre-existing de-gross layers the kill-switch design must account for — otherwise crisis de-gross gets double/triple-applied.

Two HIGH/MEDIUM Path-B-relevant findings:

1. **`risk_scalar` crisis brake INSIDE A** — `signal_processor.py:543-551`. When `advisory.regime_summary in ("stressed","crisis")`, A multiplies every edge norm by `advisory.risk_scalar`. ACTIVE, default-ON. This is a CHARTER VIOLATION: docs attribute risk_scalar consumption only to Engine B (`high_level_engine_function.md:35`, Double-Counting Matrix `engine_charters.md:551` gives A a dash). Same fact applied in A (shrink forecast) AND B (shrink size) = the exact double-count the matrix WARNING exists to prevent. Charter line 88: "A should be opinionated about direction but NOT protective about risk."

2. **`macro_yield_curve_v1` edge — ACTIVE** (`macro_yield_curve_edge.py:199`). Emits uniform -0.3 tilt across the WHOLE universe on curve inversion = a crisis de-gross overlay in the alpha layer. Three siblings (credit_spread, unemployment_momentum, real_rate) implement the same mechanism but auto-register `status="retired"` (reclassified 2026-05-02 → Engine E HMM inputs); inert-default-off but fully importable. All fire only when FRED cache is populated (abstain to zeros on fresh clone) — verify actual contribution on canonical substrate, don't assume.

Other A capabilities undocumented in living docs but lower Path-B relevance: confidence_gate (default-off, T-057 REFUTED), fill_share_capper (default-ON cap=0.25, anti-concentration), metalearner Layer-3 (default-off), per_ticker metalearner (default-off), paused_max_weight soft-pause ceiling (default-ON 0.5), SignalGate ML (gated on model file presence), MLPredictor RF gate (gated on data/models/rf_model.pkl presence), ALPHA_FORCE_SIGNALS + env threshold overrides, the DISABLED directional-regime-bias block (signal_processor.py:578-582, commented out).
