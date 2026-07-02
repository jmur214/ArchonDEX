---
name: engine-f-untracked-active-lifecycle
description: The F-side buried-capability blind spot is INVERTED from B/C/E — F's ON capabilities (lifecycle, allocation-eval) are untracked; only the OFF ones got ledger rows
metadata:
  type: project
---

When auditing Engine F against the capability registry (capability_ledger.md +
DESIGN_FIDELITY.md), the buried-capability blind spot manifests DIFFERENTLY than
in B/C/E. In B/C/E the buried capabilities were defensive ones that are OFF
(crisis multipliers, de-gross, sleeves). In F it's the OPPOSITE: the ledger
tracked only the three OFF/inert items (learned_edge_affinity, factor-α gate,
regime-conditional weighting) + the missing RegimePerfAnalytics, and MISSED the
F capabilities that are actually ON and mutating prod state.

**Why:** the capability_ledger was seeded from the 2026-06-04 audit whose lens
was "what defensive lever survives a REFUTED verdict" — so it indexed dormant
knobs and skipped the always-on autonomous machinery. F's most consequential
behavior (autonomous lifecycle: active→paused→retired→revive, DIRECT-MUTATES
edges.yml) lives ONLY at the system-level DESIGN_FIDELITY row, never as a
capability_ledger row with flag-state/wired-path.

**How to apply:** for F specifically, after grepping the OFF flags also check
the DEFAULT-TRUE flags in config/governor_settings.json and trace them to a prod
caller. As of 2026-06-22 the untracked-but-ACTIVE set is:
- `lifecycle_enabled=true` + `lifecycle_readonly=false` → governor.evaluate_lifecycle
  (governor.py:602) → LifecycleManager.evaluate, reached from mode_controller.py:1045
  (backtest post-run) and governor.py:600 (paper/live). MUTATES edges.yml + lifecycle_history.csv.
- `allocation_evaluation_enabled=true` → governor.py:558-576 writes
  data/research/allocation_recommendations.json (the de-facto producer Engine C
  policy.py:62 falls back to). auto_apply_allocation=false so it stops short of portfolio_policy.json.
- MDD-25% kill-switch (disable_mdd_threshold=-0.25) gated by the same lifecycle_enabled=true.
Default-OFF (correctly): tier_reclassification_enabled=false (governor.evaluate_tiers).

See [[doc_gap_pattern_refuted_verdict_buries_shipped_capability]] for the
general mode; this is the inverted (ON-not-OFF) instance.
