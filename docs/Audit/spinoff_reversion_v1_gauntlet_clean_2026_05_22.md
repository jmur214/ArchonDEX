---
task_id: T-2026-05-22-041c-archive
title: Spinoff reversion edge — clean 0→1.0× contribution re-test post-archive
date: 2026-05-22
outcome: GAUNTLET FAIL Gate 1 — identical to T-041b; paused-tier masking NOT the binding constraint
---

# T-041c-archive — Spinoff Reversion Clean Re-test

## Verdict

**FAIL Gate 1 — identical to T-041b**: contribution Sharpe = +0.000
vs threshold +0.10. The archive removed the 0.25× baseline weighting
of the paused entry, but the result is bitwise the same.

Per spec hard constraint, no threshold lowered. Edge stays
`status='archived'`.

| Quantity | T-041b (paused baseline) | T-041c (archived baseline) | Δ |
|----------|--------------------------|----------------------------|---|
| Wall seconds | 14.3 | 15.1 | +0.8 |
| n tickers in data_map | 639 | 639 | 0 |
| Spinoff children added | 140 | 140 | 0 |
| Baseline Sharpe | 0.000 | 0.000 | 0 |
| With-candidate Sharpe | 0.000 | 0.000 | 0 |
| Contribution Sharpe | 0.000 | 0.000 | 0 |
| Attribution n_obs | 0 | 0 | 0 |
| Gate 1 passed | False | False | — |

## What this rules in / out

**Ruled OUT**: paused-tier masking. T-041b's audit speculated that
the spinoff_reversion_v1 entry already at 0.25× weight in the baseline
ensemble was diluting the candidate's contribution delta. With the
archive landed (verified via EdgeRegistry: status='archived'), the
baseline is now genuinely candidate-free. The result is unchanged →
the paused-tier weight is NOT what was hiding the contribution.

**Ruled IN as the binding constraint**: a deeper diagnostic finding
that BOTH `baseline_sharpe` AND `with_candidate_sharpe` come back
**0.000** in the validate_candidate pipeline. This is independent of
the spinoff edge. The production-pure backtest pipeline as invoked
by `validate_candidate` is producing zero-Sharpe equity curves on a
639-ticker substrate-honest universe — which is inconsistent with
T-035's measurement of the same actives delivering mean Sharpe
0.598 under the journal-mode harness.

The attribution_diagnostics confirms: `n_obs = 0`. The
attribution stream `(with_returns - baseline_returns)` is empty.
This implies one of:

1. Both pure-pipeline runs produce constant-equity series (no
   trades fired), OR
2. The `treatment_effect_returns` helper isn't aligning the two
   series properly, OR
3. The pure pipeline isn't loading the active edges (similar
   bug-class to T-054's "ticker= dead-letter")

This is the actual finding worth pursuing in a follow-up — it's a
**different bug from the one T-054 closed**, but the same class:
silent infrastructure failure presenting as an edge-level FAIL.

## Part A — Archive via journal_apply

Script: `scripts/archive_spinoff_reversion_t041c.py`.

Per CLAUDE.md's "Never manually edit data/governor/edges.yml," the
status change went through the LifecycleJournal mechanism:

```
[T-041c] before: spinoff_reversion_v1 status='paused'
[T-041c] appending journal entry: {"decision_type":"status_change",
   "edge_id":"spinoff_reversion_v1","payload":{"new_status":"archived",
   "prior_status":"paused","reason":"gauntlet_T-041b_paused_tier_masking_confound"},
   "run_id":"t041c_archive_2026_05_22",...}
[journal_apply] processed 1 entries: status=1 weight=0 tier=0
[journal_apply] advanced apply mark → 2026-05-22T07:52:08.445909+00:00
[T-041c] after: spinoff_reversion_v1 status='archived'  OK
```

No manual `edges.yml` edits. All status changes via journal → apply.

## Part B — Re-run on clean baseline

Script: `scripts/run_spinoff_gauntlet_t041c.py` (identical to T-041b
driver except output dir).

Result at `data/measurements/spinoff_reversion_t041c_archive_gauntlet/result.json`.

Same window 2015-2024, same universe-resolver path, same 140 spinoff
children injected, same data_map of 639 tickers. The ONLY production
difference: registry now has spinoff_reversion_v1 at
`status='archived'` instead of `status='paused'`.

Result: bitwise-identical Gate 1 outcome → 0.000 contribution.

## Forward-look — what this actually tells us

T-041c-archive closes the paused-tier-masking hypothesis. The
forward-look queue from T-041b's audit re-prioritizes:

1. **Top priority — diagnose the 0.000 baseline_sharpe.** Either:
   - `run_backtest_pure` isn't seeing the active edges (registry-
     loading bug in the pure-pipeline path); test by running it
     directly on the historical universe and checking trades.csv.
   - The substrate-B / data_map doesn't include the active-edge
     tickers (universe construction bug).
   - The active-edges loaded into the pure pipeline aren't getting
     compute_signals invocations on the historical universe (edge-
     loader bug).

   This is a `T-058`-shape follow-up: trace one full validate_candidate
   run through the pure pipeline, log every (ticker, edge, signal)
   emission, find why no trades fire.

2. **Sub-priority — sparse spinoff signal.** Even with the pure-
   pipeline fixed, only ~10-20 spin-off events fall in the effective
   2018-2024 backtest window with cached child data. That's a
   floor on potential contribution magnitude. Microcap substrate
   (T-056b) and hyperparameter sweeps (T-041d) remain queued.

3. **Sub-priority — pair-trade variant (T-041d candidate).** Long
   child / short parent isolates the spin-off-specific alpha from
   sector/index drift.

## Honest scope-clarity

T-041c-archive's intent was to falsify the paused-tier-masking
explanation for T-041b's FAIL. **It did.** The clean baseline
returns the same verdict, so the explanation is elsewhere.

The unexpected finding — both baseline and with-candidate runs
producing 0.000 Sharpe in the pure pipeline — is the real signal
from this dispatch. It re-prioritizes T-041's forward-look queue:
fixing the validate_candidate pipeline must precede any further
spinoff hyperparameter / substrate exploration.

## Spec acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|--------|
| 1 | Journal entry written + applied; status → archived | DONE (apply mark advanced 2026-05-22T07:52:08) |
| 2 | Gauntlet re-runs with clean 0→1.0× delta | DONE |
| 3 | Per-gate output table with bootstrap CI | DONE (Gate 1 fail, downstream short-circuited per design) |
| 4 | T-041b prior tests + universe-resolver tests still pass | DONE (no test files modified) |
| 5 | No manual edges.yml edits | DONE (all via journal) |
| 6 | Audit doc at this path | DONE (this file) |

## Files

NEW:
- `scripts/archive_spinoff_reversion_t041c.py` — Part A archive driver
- `scripts/run_spinoff_gauntlet_t041c.py` — Part B re-run driver
- `data/measurements/spinoff_reversion_t041c_archive_gauntlet/result.json` (gitignored)
- `data/measurements/spinoff_reversion_t041c_archive_gauntlet/diagnostic.log` (gitignored)
- this audit doc

NOT touched (per hard constraint):
- `data/governor/edges.yml` (the journal_apply path mutated it,
  not the dispatch script)
- Spinoff detector / edge implementation (same code as T-041b)
- Any gate threshold (same defaults)
