---
task_id: census fail-closed (Agent R, item-(d) review; health_check HIGH, anchor backtest_controller.py:1333)
title: A census block that crashed is never a clean census
date: 2026-10-15
author: Agent D
type: PROPOSAL — referee code, propose-first; R reviews, the director merges
n_trials: 0
---

# A census block that crashed is never a clean census

**The defect (Agent R).** `_build_census`'s edges block caught any exception and wrote `edges_blind = []` and
`edges_errored = {}` (PASSING values) plus `edges_blind_error`, and `assert_census` never read
`edges_blind_error`. A crash inside the edges census therefore produced a census that PASSED invariants 1 and 1b.
That is the measurement path's own gate degrading to a plausible pass (`[NN-FAIL-CLOSED]`, `[NN-CENSUS]`).

## Scope — which runs this reaches

The gate (`core/census.py` `assert_census`) is called by three kinds of caller:
- the measurement path's census check: local `run_isolated` / `run_substrate_arms`, and the cloud entrypoint;
- Discovery's Gate-1 candidate census;
- the paper heartbeat.

**The live cloud paper fleet is NOT reached.** `paper_trader/scheduler.py`'s `_record_heartbeat` calls
`heartbeat.record_run(…)` with `summary=None`, so the heartbeat never evaluates a census on the fleet path.
Verified by reading the call, not inferred. The change therefore alters only what is certified CANONICAL among
backtests, measured runs and Gate-1 candidates. On the 955 recorded summaries it changes no verdict (955 distinct files: an earlier count of 956 included `data/research/performance_summary.json` twice, because this worktree's `data/research` is a symlink to the canonical tree's — corrected on R's check; the double-counted file carries no census, so the 79 and the 0 flips stand).

## The audit — every except branch in `_build_census`, against what the gate reads

| block | its except branch wrote | gate before | after this unit |
|---|---|---|---|
| edges (invariants 1/1b) | `edges_blind=[]`, `edges_errored={}`, `edges_blind_error` | **PASSED** (R's finding) | writes only `edges_blind_error`; the gate fails on it |
| fundamentals (invariant 4) | `fundamentals_blind=0`, `fundamentals_blind_error` | **PASSED** (same shape, found in this audit) | writes only `fundamentals_blind_error`; the gate fails on it |
| trades (invariant 3) | `n_trades=-1`, `trades_empty=True`, `trades_canon_error` | failed, via `trades_empty` | unchanged writes. But `n_trades=-1` **alone** passed the gate (`== 0`); it is now `<= 0`, found by the new contract |
| data_exclusions | `{"error": …}` | **PASSED** (the gate never read `data_exclusions`) | the gate fails an errored record; the key joins `CENSUS_GATING_KEYS` |
| data_feed (invariant 7) | `{"error": …}` | failed | unchanged (the tolerable pattern) |
| config_provenance (invariant 6) | an inner `except` sets `rec["error"]`, so `degraded=True` | failed | unchanged (the tolerable pattern) |

**Seen, not changed: two keys with no except branch default to a PASSING value.** These are for a ruling.
- `n_resolved` comes from `getattr(self, "_census_n_resolved", 0)`. At 0, the universe-shrink check is skipped.
- `regime_total_bars` comes from `getattr(…, 0)`. At 0, the regime check is skipped (`regime_total_bars > 0`).

A run that never set either counter passes both invariants without measuring them. Whether 0 can be legitimate
(a run with the regime layer configured off) is the question.

## The change

- **`core/census.py`:**
  - the gate fails on any `<block>_error` key (other than `census_error`, which was already handled) and on an
    errored `data_exclusions` record;
  - invariant 3 reads `n_trades <= 0`, not `== 0`;
  - invariant 8 is documented in the module docstring.
- **`backtester/backtest_controller.py`:** the edges and fundamentals except branches write only their error
  record; the PASSING values are gone.
- **`tests/test_contracts.py`, the Layer-2d gating check in AST form:**
  - each gating key must be assigned on `_build_census`'s SUCCESS path, outside every except handler;
  - keys with a source-of-truth producer must be assigned FROM it (`config_provenance` ←
    `_census_config_provenance`, `data_feed` ← `data_feed_summary`, `data_exclusions` ← `exclusions_applied`);
  - the old regex form was satisfied by an except branch writing a passing value;
  - new: **every except branch is EXECUTED** (its own statements, with a planted exception) and planted into a
    canonical census. The gate must say NON-CANONICAL, and every gating value the branch writes must fail the
    gate on its own ("never a passing value").

## Locks and proof

- `tests/test_census_fail_closed.py` drives the real `BacktestController._build_census`:
  - a crash planted inside the edges block makes the run NON-CANONICAL, and no passing values are written;
  - the same for the fundamentals block;
  - `n_trades` of −1 or 0 is never a traded run;
  - positive control: the same setup without the plant is CANONICAL.
- `scripts/census_fail_closed_reversion_proof.py`: **6 of 6 bite, each for the right reason.** The last case
  assigns `edges_blind` only in the except branch: the old regex contract passed that; the AST contract fails it.
- 49 census-touching test files: **585 passed / 0 failed**.
- **First artifact, read-only.** The old and new gates were run over every recorded `performance_summary.json`
  on disk: 955 read, 79 with a census, **0 verdict flips**. The one record carrying an error was already
  NON-CANONICAL through `census_error`. No locally recorded run was ever certified clean by this defect. S3-held
  records were not scanned.
- **health_check:** the HIGH row's anchor (`backtest_controller.py:1333`, `census["edges_blind"] = []` in the
  except branch) is the line this unit removes. Close the row at merge.

## Fixup — NO silent zero (the director's ruling on the held-out counters, 2026-10-15)

`n_resolved` and the regime counters came from `getattr(..., 0)`, and the gate SKIPPED an invariant whose
counter read 0. So a run that never set a counter passed invariants 2 and 5 without either being measured.

**Producer (`backtest_controller.py`):**
- the regime counters start **UNSET** (`None`) and become set on the first bar the per-bar tally sees in
  `_detect_regime`;
- a counter that was never set is **ABSENT** from the census;
- the census declares `census_kind: "backtest"`, and `regime_layer: "on"` or `"off"`, where "off" means no
  detector;
- a declared-off layer also records `regime_off_label`, taken from `CENSUS_REGIME_OFF_LABEL` (the brief that
  pre-registers the layer as off by design).

**Gate (`core/census.py`), applied to a BACKTEST census:**
- an absent counter fails: "counter never set";
- a measured 0 fails: `n_resolved == 0` means no universe, and `regime_total_bars == 0` means the layer
  produced nothing;
- a declared-off layer fails unless the census carries the label;
- with the label, the regime invariant is not applied, and the run is canonical with the declaration recorded.

**Discovery's Gate-1 candidate census** declares `census_kind: "candidate"` and is not asked for the backtest
counters. Before this unit it passed only because absent counters read as a skipped 0, so it now declares what
it is. **An undeclared census is treated as a backtest**, the strictest kind.

**Fixtures that relied on the silent zero were made as complete as production:**
- `tests/test_gate1_candidate_census_t347.py` kept a hand-written COPY of the candidate block, whose own
  docstring said "not a private copy". The copy drifted the day `census_kind` landed, so it now calls the real
  `candidate_census_block`.
- My own lock's controller sets the counters a real run sets.

**Locks** (`tests/test_census_fail_closed.py`):
- an absent counter fails;
- a measured 0 fails, for both counters;
- a declared-off layer fails unlabelled and is canonical labelled;
- the real `_detect_regime` tally turns an unset counter into a set one;
- the candidate census is not asked for backtest counters.

**Proof:** `scripts/census_fail_closed_reversion_proof.py` now runs **12 of 12**, each for the right reason. One
honest note: with the explicit `regime_total_bars == 0` check reverted, a measured 0 STILL fails, through the
100%-unknown check (the producer writes `frac = 1.0` at 0 bars, and the old `regime_total_bars > 0` guard is gone).
That lock bites on the message, which names the true cause.

**Tests:** 49 census-touching test files, **591 passed / 0 failed**.

**First artifact, re-run:** old gate against new over 955 recorded summaries (79 with a census): canonical
**13 → 13, 0 flips**. No recorded run relied on a skipped zero.

**The live fleet is NOT reached.** The cloud paper scheduler's `_record_heartbeat` calls `record_run` with
`summary=None`, so the heartbeat never evaluates a census there. Verified by reading `paper_trader/scheduler.py`.
