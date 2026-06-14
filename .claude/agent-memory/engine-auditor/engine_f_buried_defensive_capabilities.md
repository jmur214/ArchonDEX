---
name: engine-f-buried-defensive-capabilities
description: Engine F (Governance) ships several regime/de-weighting/retirement levers that read "enabled" but are inert on the production call path; relevant to T-092 Path B crisis-robustness pivot.
metadata:
  type: project
---

Engine F audit 2026-06-04 (Path-B doc-gap sweep). Engine F's living docs (CURRENT_STATE.md, MEMORY.md, engine_charters.md) do NOT surface that several shipped defensive/governance capabilities are switched OFF or unwired on the production path.

**Why:** Same root cause as the Engine B/E crisis de-gross discovery — capabilities were built, then either the motivating task was refuted (so MEMORY recorded only the verdict) or the flag/path got disconnected, and no living doc tracks the resulting inert state.

**How to apply (for Path B crisis robustness):** Engine F already contains regime-conditional edge de-weighting that is the natural F-side complement to a B/E crisis kill-switch. The lever exists; it's gated OFF.

Key buried items (file:line — state):
- `RegimePerformanceTracker.get_learned_affinity` regime_tracker.py:180 + `get_regime_weight` :152 — per-edge per-regime Sharpe→weight with kill-switch (Sharpe<=0 → weight 0) and MDD soft-penalty. PRODUCER only called from backtester/backtest_controller.py:346-348, gated on `regime_conditional_enabled` which is FALSE in config/governor_settings.json:13. Entire regime-conditional chain (incl. `get_edge_weights(regime_meta=...)` blend, `_rebuild_regime_weights_from_tracker`) is dead in prod. HIGH Path-B relevance.
- Factor-α retirement gate (factor_alpha_gate.py + lifecycle_manager.py:613) — `factor_alpha_enabled` defaults True but `evaluate_lifecycle` (governor.py:607) never passes `factors=`, so `factors is not None` guard makes it a permanent no-op except via scripts/lifecycle_factor_alpha_reeval_t043.py. Flag reads enabled, path never exercises it.
- `GovernorConfig.disable_mdd_threshold=-0.25` (governor.py:36) — the -25% per-edge kill-switch the charter cites; lives in active weight path. ACTIVE.
- LifecycleManager pause/retire gates (loss-fraction, WR-collapse, zero-fill, sustained-noise, paused-retire, revival-veto) — ACTIVE in prod (lifecycle_enabled=true), strongly defensive (auto de-risk bad edges). Charter only mentions the -25% kill-switch; the richer gate suite is under-documented.

**Cross-cutting pattern (reusable):** In this codebase, "config flag = True" does NOT mean the capability runs. Verify the CALL PATH actually exercises it (passes the required kwargs / isn't gated by a second sibling flag). This is the T-088 risk_per_trade_pct dead-knob family. When auditing any engine for buried capability, grep the producer call sites, not just the flag default. See [[engine_f_evolution_controller_does_d_work]].

**Stale doc refs:** governor.py:20,89 still say "Engine D" (Governance is F). `regime_analytics.py`/`RegimePerfAnalytics` is referenced by charter + index.md but the file does not exist (likely consolidated into RegimePerformanceTracker; sync_docs not regenerated).
