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
  on disk: 956 read, 79 with a census, **0 verdict flips**. The one record carrying an error was already
  NON-CANONICAL through `census_error`. No locally recorded run was ever certified clean by this defect. S3-held
  records were not scanned.
- **health_check:** the HIGH row's anchor (`backtest_controller.py:1333`, `census["edges_blind"] = []` in the
  except branch) is the line this unit removes. Close the row at merge.
