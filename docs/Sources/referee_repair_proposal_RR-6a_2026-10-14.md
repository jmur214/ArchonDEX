---
task_id: RR-6a (alpha-frontier program §3.1; split from RR-6 on 2026-10-14)
title: RR-6a — gate verdicts that can be trusted
date: 2026-10-14
author: Agent D
branch: fix/referee-rr6a-gate-verdicts (on main 18fa3f4 → abb6c0c)
type: PROPOSAL — referee code, propose-only. R reviews independently; the director merges.
n_trials: 0
---

# RR-6a — gate verdicts that can be trusted

**What the no-promotion ruling waits for.** RR-2 made the gauntlet's verdict authoritative. Since then, a Gate
7 that never ran could promote a candidate. This unit closes the defects and nothing more. RR-6b (Gate 1′
terminal wealth, a held-out window, `oos_lock`, whether Gate 3 should bind) remains its own pre-registered
brief. The scope and its evidence are in `docs/Sources/referee_repair_brief_RR-6_2026-10-14.md`.

## 1. The class, and the one fix for it

Gate results were booleans with **defaults**, so "not evaluated" could not be told apart from a verdict.
Consumers resolved that absence in opposite directions:
- **The promotion decision** read a skipped Gate 7 or Gate 8 as a PASS.
- **The T-195 foundry harness** read the criterion-less Gate 3 as a FAIL.

**Fix.** `engines/engine_d_discovery/gate_verdicts.py` gives each gate one tri-state verdict: **PASSED |
FAILED | NOT_EVALUATED(reason)**.
- `validate_candidate` writes the verdicts, and every gate 0–8 is always present.
- No reader supplies a default. A missing gate raises `KeyError`, which is a programmer error, never a verdict.
- The decision is made in one place (`_seal`). `passed_all_gates` is true iff every **required** gate is
  PASSED.
- A required gate that rendered no verdict **refuses**, and `promotion_refusals` names it and why.
- Kill attribution (`first_failed_gate`) names only a FAILED gate.
- The legacy `gate_N_passed` / `gate_N_evaluated` booleans are derived from the verdicts and written for
  every gate. An unconverted reader therefore never falls through to a default.

**The required set is config:** `config/discovery_settings.json` `required_gates` = gates **0, 1, 2, 4, 5, 7,
8**. `thresholds.required_gates()` refuses:
- `gate_3`, which has no pass criterion;
- unknown ids;
- an empty list;
- any disagreement with `factor_gate_mode`. Gate 6 must be listed iff the mode is `kill`; production runs
  `report`, so Gate 6 is recorded but does not bind, which is unchanged since T-203.

A test pins the set, so changing it is a reviewed diff.

## 2. Per defect: the fix, the lock, and the reversion

Every lock is in `tests/test_rr6a_gate_verdicts.py`. Each drives a real entrypoint: `validate_candidate`,
`_run_discovery_cycle`, `AutonomousEvolution.run_cycle`, or the harness's `foundry_record`.

Every REFUSAL lock has a positive control: the same candidate, with that one gate evaluated, **passes**. Without
it, a refusal could come from another gate. Gate 0 with no window refuses everything, so the lock would hold
on buggy code.

**Reversion record.** `scripts/rr6a_reversion_proof.py` reverts **only** one fix, runs **only** its lock, and
restores the file by sha256. 13 of 13 locks fail, each for the right reason:

| # | fix reverted | lock fails with |
|---|---|---|
| 1 | Gate 7: the bare `timeframe` restored (`mode_controller.py` cycle, both reads) | `{'saved': [], 'substrate_b': [], 'timeframes': []}`: nothing validated, no substrate B |
| 2 | the substrate-B catch-all restored | "a candidate was validated after a programmer error in the build" |
| 3 | a skipped Gate 7 reads PASSED | verdict `passed` ≠ `not_evaluated`; the candidate passes |
| 4 | Gate 8 at N ≤ 1 reads PASSED | `'passed' == 'not_evaluated'` |
| 5 | Gate 0 with no window silently skipped | `'passed' == 'not_evaluated'` |
| 6 | diagnostic attribution: the old `gate_pass_order` with defaults | `'gate_7' is None`: it names a gate that never ran |
| 7 | harness `gates`: the old `gate_{g}_passed` booleans | `None == 'not_evaluated'` |
| 8 | the `gate3_consistency_threshold` parameter restored | `DID NOT RAISE <class 'TypeError'>` |
| 9 | Gate 6: `already_excess=True` removed at the call | α = **−0.0226** (truth +0.025, RF 5%) |
| 10 | Gate 6: a missing factor cache reads PASSED again | `'passed' == 'not_evaluated'` |
| 11 | Gate 5 with-arm reuses the wrapped baseline | the run on `BBB` replayed signals for `AAA` |
| 12 | Gate 7 with-arm reuses the wrapped baseline | the run on `SUBB` replayed signals for `AAA` |
| 13 | re-queue: both WFO rejections keep status `candidate` | `status: 'candidate'` (2 of 2 parametrised cases) |

The script's first draft of lock 8 failed with `ModuleNotFoundError`, not "did not raise", so it would have
bitten vacuously. It now drives the stubbed passer, so a restored parameter makes the call succeed.

**Defect by defect:**
- **Gate 7's free pass.** `_run_discovery_cycle` read a never-bound `timeframe`, and the block's catch-all
  turned the `NameError` into "gate skipped" on every cycle. Now:
  - it reads `self.timeframe`;
  - it re-raises programmer errors;
  - it degrades only on data unavailability, after which Gate 7 is NOT_EVALUATED and refuses.

  A data-failure positive control (`OSError`) proves the degrade path still works.
- **absent = PASS.** Gate 7 with no substrate B, Gate 8 at an explicit N ≤ 1, and Gate 0 with no window are
  all NOT_EVALUATED, and all refuse.
- **absent = FAIL.** The diagnostic row and `foundry_record` name only FAILED gates. `foundry_record` is now
  shared by T-195 and T-193 (`scripts/run_phase0b_foundry_discover_t193.py` calls it), and harness `gates`
  carry the tri-state.

  Honest note on lock 7. With the legacy flags derived, the old harness *loop* already returns `gate_4` on
  new results. The harness defect that remained was the `gates` booleans: a Gate 7 that never ran recorded
  `false`, which reads as a FAIL. Lock 7 is aimed at that, and the `gate_4` attribution is asserted beside it.
- **Gate 3's interface.** `gate3_consistency_threshold` is removed, so passing it raises `TypeError`. Gate 3's
  verdict is always NOT_EVALUATED, with the consistency recorded in its reason.
- **Gate 6.**
  - `regress_returns_on_factors(..., already_excess=True)` for the attribution spread. The default
    (raw-return) convention is unchanged for its other callers, including Engine B's `factor_analysis.py`,
    which is not touched.
  - A missing factor cache, or too little overlap to regress, is NOT_EVALUATED. It used to be a pass.
  - The NEW-5 xfail flips. It now calls the spread convention and asserts that the raw convention still
    subtracts RF.
- **Gate 5/7 cache contamination.** The Gate-1 signal cache keys on the bar timestamp alone. The with-arms on
  Universe B and substrate B now use **unwrapped** baseline edges, so they never replay Universe A's signals.
- **Re-queue forever** (`scripts/run_evolution_cycle.py`). Both WFO rejections set `status: failed` and record
  `rejection_reason`, and the gauntlet rejection now records its reason too.
- **R's F3.** The RR-2 threshold readers moved to `engines/engine_d_discovery/thresholds.py`. `mode_controller`
  re-exports them, because the cycle calls them, and six scripts import from Engine D.
- **Found in passing and fixed** in a file I was already changing: the T-193 harness summary indexed
  `r["killed_by_gate"]` on rows that never carry that key, so a completed sweep raised `KeyError` on its own
  summary line.

**Fixtures that encoded the defect** were changed openly:
- Two tests in `test_discovery_gates_7_8.py` asserted that a skipped gate PASSES.
- The F2 cycle `fake_self` had no `timeframe`. It passed only because the block swallowed every exception.
- The Gate-6 remediation test's reason string now reads `not evaluated:`, where it used to read `failed:`.

**Files affected:** 146 passed, 8 xfailed. The ninth xfail (NEW-5) now passes.

## 2b. Fixup — the director's rulings (a), (b), (c), 2026-10-14

One commit on top of `c982114`. R re-checks that diff alone. Each item has a lock, and each lock is proven by
reversion: cases 14–17 in `scripts/rr6a_reversion_proof.py`. All 17 cases fail for the right reason.

| # | ruling | the change | lock fails, reverted, with |
|---|---|---|---|
| 14 | **(a)** `run_evolution_cycle` validates on a window | It passes `discovery_validation_window(self.data_map)`, the same full-extent window production uses. The helper moved from `mode_controller` to `engines/engine_d_discovery/thresholds.py` (re-exported), so the script does not import the orchestrator. Without a window, this dashboard-reachable path was silently dead: Gate 0 NOT_EVALUATED, every candidate refused. | `(None, None) == ('2012-01-02…', …)` |
| 15 | **(b)** the per-candidate handler catches only the expected class | Only `TimeoutError` (the diagnostic wall-time alarm) is caught, and it renders a fully sealed refusal: every gate NOT_EVALUATED with the reason (`gate_verdicts.refused_result`). The catch-all is gone. `validate_candidate` already turns expected per-candidate failures (census refusals, data errors) into NOT_EVALUATED verdicts itself, so anything that escapes it is a harness defect and fails the cycle. | `DID NOT RAISE <class 'NameError'>`: the candidate was written `failed` |
| 16 | **(c)** the cycle fails loudly | The outer handler re-raises **every** exception. It prints `[DISCOVERY][FAIL] … at stage '<stage>'`, writes a `cycle_failure` row to `discovery_log.jsonl` (`DiscoveryLogger.log_cycle_failure`: stage, error, notes), and adds a stage note to the exception. The stages are: honest-N resolution, regime context, hunt, generate, save, substrate-B build, `validate <id>`, BH-FDR, `write-back <id>`, summary. | `DID NOT RAISE <class 'RuntimeError'>` |
| 17 | **(c)** "which candidate and which gate" | An error `validate_candidate` re-raises carries the note `[validate_candidate] candidate=<id> last_gate_completed=<gate>`. The cycle's failure row records the notes. | the note is absent |

A positive control proves the expected class is still handled: a `TimeoutError` refuses the candidate (`failed`,
every gate NOT_EVALUATED) and the cycle carries on. Lock 2 (a programmer error in the substrate-B build) now also
asserts that the cycle **raises** and logs stage `substrate-B build (Gate 7)`.

Consequence, accepted with the ruling: a failed cycle raises out of `run_backtest(discover=True)` before
`performance_summary.json` is written for that run. RR-3's honest-N halt already behaves this way.

**All 50 test files touching a changed module:** 681 passed / 1 skipped / 3 deselected / 11 xfailed / 0 failed.

## 3. R's F4 — Gate 4's size on skewed streams (measurement, pre-registered)

The pre-registration is the docstring of `scripts/rr6a_gate4_size_skewed.py`, committed at `d15846b` before the
first run. The record is `docs/Measurements/2026-10/rr6a_f4_gate4_size_skewed.json`. It reproduces exactly on a
re-run. M = 400 per cell, and the call is exactly Gate 4's.

| n | normal (control) | lognorm right | **lognorm left** | GARCH normal | **GARCH left** |
|---|---|---|---|---|---|
| 756 | 0.045 [0.029, 0.070] | 0.035 [0.021, 0.058] | **0.100 [0.074, 0.133]** | 0.038 [0.023, 0.061] | **0.113 [0.085, 0.147]** |
| 3269 | 0.048 [0.031, 0.073] | 0.030 [0.017, 0.052] | 0.070 [0.049, 0.099] | 0.065 [0.045, 0.094] | **0.078 [0.055, 0.108]** |

**Reading 2, applied mechanically: SIZE DRIFTS.** The control holds. On **left-skewed** (crash-shaped)
zero-mean streams, Gate 4 rejects at 1.5–2.3× its nominal 5%. Right skew runs slightly conservative. Per the
pre-registration, the replacement null (a stationary bootstrap centred at zero) is **its own propose-first unit**
and is not made here.

Context, not a mitigation claim: Gate 4 is not the last line. Gate 2 (PBO), Gate 8 (DSR at the honest N ≈ 37)
and the BH-FDR post-filter all stand behind it. But a gate's stated size should be its size.

## 4. Consequences the director should know before the next cycle

- **Substrate B will be built for the first time** (first artifact, observed read-only). The fixed build
  resolves a **469-ticker** historical complement on this machine: mode `historical`, 728 cached tickers, 109
  static, window 2021–2024. Every candidate then runs Gate 7's **two extra backtests on 469 tickers**: a real
  runtime cost. Whether the cloud image has those 728 cached tickers is unverified. If it doesn't, Gate 7 is
  NOT_EVALUATED in cloud and **every cloud candidate is refused**. That is fail-closed, and also a capacity
  fact.
- **`run_evolution_cycle` now validates on the production window** (ruling (a), §2b). Before this it had never
  been MinBTL-checked.
- **A Discovery cycle that fails now raises** (ruling (c), §2b). A scheduled `--discover` run that hits a defect
  exits non-zero instead of logging WARN and reporting "nothing found".
- **The T-195 harness** still passes `n_trials_for_dsr = len(feats)`. A single-feature sweep therefore gets
  N = 1, Gate 8 is NOT_EVALUATED, and the candidate is refused. That is correct fail-closed behaviour, but the
  harness should take the honest N (RR-3), which is a follow-up.
- **No historical verdict flips.** Zero candidates have ever passed all gates (0/36 foundry, 0/88
  `discovery_log`, 0 promotions).

## 5. Seen, NOT changed — for R and the director

Items 1 and 2 of the first draft (the per-candidate handler and the outer handler) were ruled INTO RR-6a; see §2b.

3. **`DiscoveryEngine.save_candidates` fails open destructively.** If `edges.yml` fails to parse, it falls back
   to `{"edges": []}` and rewrites the registry with only the candidates being saved, **wiping every existing
   edge**. Ruled to be **its own unit, next, propose-first**. The no-promotion constraint is **extended**: no
   Discovery promotion cycle until RR-6a AND this fix are both on main.
4. **`scripts/sync_docs.py` drift** in three indexes is unrelated to RR-6a and not committed:
   `engines/engine_b_risk/index.md` (outside my rails), `orchestration/index.md` and `scripts/index.md`.
   Ruled: it gets its own docs commit from whoever owns Engine B's index.
5. **`gate_factor_alpha(None)` still returns `(True, "skipped")`** for its other callers. `validate_candidate`
   no longer reaches it with `None`.
6. **The regime-context step's catch-all** (`_run_discovery_cycle` Step 1) still absorbs every exception,
   including programmer errors, and prints "Regime detection skipped". The hunt then runs without regime
   context. This is outside the three rulings, so it is listed here for one.

## 6. Records, health_check, charter

- **The 36 S3 T-196 records: annotate, never rewrite.** The per-gate table is
  `docs/Measurements/2026-10/t196_foundry_per_gate_kill_table.md` (branch `docs/t196-per-gate-kill-table` @
  `1539e17`). The proposed sidecar is `docs/Measurements/2026-10/t196_foundry_records_SIDECAR.md`, to be
  copied beside the records as `foundry-t196/RR6A_NOTE.md`. That S3 write belongs to the director, with R1,
  after the IAM proof.
- **health_check.md.** The open HIGH row's one linted anchor (`config/alpha_settings.prod.json:37`, RR-7) is
  untouched by RR-6a, and doc_lint exits 0 on the branch. Sub-items (7) Gate 6 RF, (8) Gate 5/7 cache, (16)
  Gate 7 free pass and (17) Gate 3 phantom close with this merge. Their prose line references
  (`factor_decomposition.py:233`, `discovery.py:1275, 1535, 1672`) become history. Proposed Status text for
  the merge commit: "**RR-6a MERGED <date> — items (7), (8), (16), (17) FIXED** (tri-state gate verdicts,
  required gates in config; R's review APPROVE; 13 locks proven by reversion). F4: Gate 4 over-rejects 1.5–2.3×
  on left-skewed zero-mean streams, so the replacement null is its own unit. The no-promotion constraint lifts
  per the director's ruling."
- **Charter (`docs/Core/engine_charters.md`, Engine D) — proposal text only, propose-first:** "Each gate renders
  PASSED, FAILED or NOT_EVALUATED(reason). A candidate passes the gauntlet only when every gate listed in
  `required_gates` is PASSED; a gate that did not run never counts as a pass and is never named as the gate
  that killed a candidate."
