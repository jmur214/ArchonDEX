---
task_id: T-2026-06-18-216
title: Conjunctive "trade like a trader" selector — BUILD + honest test vs the robo gate (the central thesis)
date: 2026-06-18
scope: Engine-A signal construction (ensemble_mode=conjunctive, default-OFF, additive/canon-safe); measured vs the T-203 robo gate; builds T-208's design
status: PRE-REGISTRATION committed BEFORE the build/run; results appended after
references: docs/Audit/conditional_selection_design_t208_2026_06_18.md (the design); T-205 quality; T-156 (averaging washes out); core/combined_candidate_scorecard.evaluate_deploy_readiness; engine_b_risk/factor_analysis.is_it_beta_or_edge
---

# T-216 — Conjunctive Selector: Build + Honest Test

## 1. PRE-REGISTRATION (committed before build/run)

### 1.1 The thesis (the project's central original idea, never tested)

"Fundamentals say it's a good buy → THEN technicals confirm the entry →
and only in the right regime." Today the ensemble AVERAGES independent
edge votes (weighted-mean + shrinkage), which T-156 showed washes them
out. The conjunctive version makes the dimensions MULTIPLICATIVE gates.
Literature prior < 20% (12/13 edges factor-negative) — but a clean
measured pass/fail on the central thesis beats an un-tested "what if."

### 1.2 The ONE structure (fixed — no search, per T-208)

Per-ticker, computed from the edges that fired this bar
(categories via `EDGE_CATEGORY_MAP`: technical = momentum /
trend_following / mean_reversion; fundamental = fundamental):

- **`s_tech`** = weighted-mean norm over TECHNICAL edges (the same
  weighted-mean the legacy uses, restricted to technical). No technical
  edge fired → `s_tech = 0` (no entry signal → no trade).
- **`g_fund` ∈ [0,1]** = the fundamental confirmation gate. `f_agg` =
  weighted-mean norm over FUNDAMENTAL edges (the quality/value signal —
  same edges T-205 repointed). `g_fund = clip(0.5 + f_agg, 0, 1)` if ≥1
  fundamental edge fired, **else `g_fund = 0`** (require fundamental
  confirmation — this is the conjunction; a great-technical name with no
  fundamental opinion does NOT trade).
- **`g_regime` ∈ [0,1]** = regime gate, reusing the regime_summary the
  existing `regime_gate` hook reads. Fixed map: robust_expansion 1.0,
  emerging_expansion 1.0, cautious_decline 0.5, market_turmoil 0.0,
  default/benign 1.0.
- **`conjunctive_score = clip(s_tech × g_fund × g_regime, −1, 1)`** —
  replaces the averaged `agg` ONLY when `ensemble.mode == "conjunctive"`.

This reuses the existing edges + the regime hook; no new alpha, no
engine-boundary cross. It is Engine-A signal construction only.

### 1.3 Default-OFF / canon-safe (invariant)

`EnsembleSettings.mode` defaults to `"weighted_mean"` → the legacy path
is bitwise-unchanged. **Proof obligation: 2024 cell canon-md5 UNCHANGED
with mode at default.** The conjunctive branch executes only when the
config opts in.

### 1.4 The gate (fixed) + N_trials

- **Gate:** `core/combined_candidate_scorecard.evaluate_deploy_readiness(
  candidate_equity, account="roth", w_dbmf=0.0)` — the T-203 robo gate,
  Roth, after-tax, net-of-cost, vs the 60_40 + schwab_like proxies.
  **PASS = `passed=True`** (beats ALL proxies on `ci_low(Sharpe)` OR a
  ≥20% shallower MaxDD). Plus the `is_it_beta_or_edge()` verdict
  (B/T-209) on the conjunctive returns.
- Substrate: the honest substrate (PIT universe + realistic costs ON),
  crisis-inclusive. Compute-bound full-cycle → **local first-cut now +
  flag a cloud cell for the canonical** (like C/T-211).
- **N_trials += 1** (this ONE structure). No space search; any variant
  is a new trial. Pre-registered before the run (CLAUDE.md #7).

### 1.5 Honest deliverable either way

- **H1** — conjunctive clears the robo gate → the central thesis is
  VINDICATED (a huge, report-it-loud result).
- **H0** — a clean, well-measured MISS → the central thesis is honestly
  CLOSED with evidence, not left as a permanent "we never tried."
- Both are real answers; whichever it is gets reported plainly. A likely
  side-finding: the conjunction (require-fundamental-confirmation) may
  shrink the tradeable set sharply (fundamentals cover ~50% of names and
  must fire) → if trades are too few to evaluate, THAT is the finding
  (the conjunction is too restrictive at our coverage).

---

## 2. RESULTS

[APPENDED AFTER THE PRE-REGISTRATION COMMIT — see git history.]
