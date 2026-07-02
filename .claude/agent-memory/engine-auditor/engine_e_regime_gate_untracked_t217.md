---
name: engine-e-regime-gate-untracked-t217
description: T-217 regime_gate.py shipped hmm_regime_label (WIRED into A's conjunctive selector, default-OFF) + an unwired RegimeGate per-edge subsystem; neither in capability_ledger; DESIGN_FIDELITY row1 STALE (says NEVER-BUILT, now BUILT+DORMANT)
metadata:
  type: project
---

The 2026-06-22 Engine-E ledger audit (capability_ledger.md + DESIGN_FIDELITY.md
vs code) found the exact buried-capability class the registry exists to prevent,
recurring one merge wave later.

**Finding (UNTRACKED, MEDIUM):** `engines/engine_e_regime/regime_gate.py:63`
`hmm_regime_label()` maps causal HMM `p_crisis`
(`regime_meta["hmm_regime"]["probabilities"]["crisis"]`) → {calm/cautious/crisis}.
It IS imported + called on the live path by Engine A's conjunctive selector at
`engines/engine_a_alpha/signal_processor.py:546-548`
(`_CONJ_REGIME_GATE = {calm:1.0, cautious:0.5, crisis:0.0}`). Real, wired, but
reachable only under `EnsembleSettings.mode="conjunctive"` (default
`weighted_mean`, signal_processor.py:76; no prod config flips it) → correctly
DORMANT. NOT a phantom: prod `hmm_3state_v1.pkl` emits a `crisis` state key, so
the label is functional if mode flips. NO capability_ledger row existed.

**Finding (UNTRACKED, LOW):** the rest of regime_gate.py — `RegimeGate` class
(:108), `gate_from_sharpe` (:77), `build_gates_from_stats` (:87),
`to_file`/`from_file` (:132/:137) — has ZERO production importers (grep
engines/backtester/orchestration/core/live_trader). No `regime_gate*.json`
artifact on disk. Built-but-inert per-edge overlay scaffold; also untracked.

**Finding (STALE):** `DESIGN_FIDELITY.md:19` row 1 (conjunctive selector) still
reads "NEVER-BUILT → BUILDING NOW (A/T-216)". It is now BUILT
(`signal_processor.py:510 _conjunctive_aggregate`) + DORMANT (default-OFF). The
registry whose entire purpose is to stop never-built-asserted-as-built is itself
one merge behind on its flagship row.

**Why:** the auditor's own playbook ([[doc_gap_pattern_refuted_verdict_buries_shipped_capability]])
predicts this: a capability ships behind a default-OFF flag in one task (T-217),
gets consumed in a sibling task (T-216), and no one updates the CAPABILITY-STATE
registry because the VERDICT registries (CURRENT_STATE/TASK_LEDGER/MEMORY) carry
the decision and look complete. capability_ledger + DESIGN_FIDELITY both lagged
the T-216/T-217 wave by exactly one merge.

**How to apply:** when auditing E after a merge wave, the fastest tell is
`git log --oneline -- engines/engine_e_regime/` then grep each new symbol for
importers OUTSIDE the engine. `hmm_regime_label` had a live importer; the rest
didn't — split the finding by reachability (mode-gated vs never-wired), don't
lump. Also re-check DESIGN_FIDELITY status legend on every audit: its CORE rows
(conjunctive selector, hmm_p_crisis) flip status as the build lands and the
registry does not auto-update. OK rows this pass: advisory.py:242 output dict,
the multires/transition_warning DORMANT entries, the HMM-crisis-model
"never-loaded-by-prod" row (config/regime_settings.json:101 still legacy).
