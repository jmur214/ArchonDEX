---
task_id: RR-2
title: "Production Discovery — a Gate-4 null that can reject, and a gauntlet verdict nothing overwrites"
date: 2026-09-30
author: Agent A (owner after the duplicate-session incident; see Provenance)
branch: fix/referee-rr2-discovery-verdict
commits: [9bc1765, 2263d5b]
status: PROPOSAL — not for merge. Agent R reviews -> director -> the USER rules on merge.
n_trials: 0 (corrections, not hypotheses; D6 is a RE-SCORE)
outcome: D1-D5 delivered and proven; D6 DEFERRED behind RR-1 (see §5); five findings for other briefs (§7)
reproduce: |
  git checkout fix/referee-rr2-discovery-verdict
  python scripts/probe_gate4_permutation_null.py        # null_std > 0.3 on all four series
  python -m pytest tests/test_referee_repairs_proposed.py tests/test_significance.py \
    tests/test_evolution_cycle_verdict_rr2.py tests/test_discovery_gate_remediation.py -q
---

# RR-2 — proposal

**The referee is never autonomously modified.** This branch changes the measurement stack
(Gate 4's null and the Discovery promotion rule). Nothing here is merged. It exists to be
reviewed independently by Agent R, then by the director, and ruled on by the user.

## 1. The defects, as found on main

| | Where | What it did |
|---|---|---|
| (a) | `significance.py:84` | Permuted the strategy's **own** returns. Mean and std are permutation-invariant, so every null Sharpe equalled the actual: `null_std` ≈ 1.8e-15, and a Sharpe-5.2 series scored **p = 0.973**. The May audit's sentence "tests whether temporal ordering matters for the Sharpe" was the defect — the Sharpe does not depend on ordering. |
| (b) | `mode_controller.py:1338` (+ 5 scripts) | Passed `significance_threshold=None`, which `validate_candidate` scored as `gate_4_passed = False` for **every candidate ever**. T-196's H1 was structurally unreachable. |
| (c) | `mode_controller.py:1397-1403` | **Overwrote** `passed_all_gates` with `sharpe>0 ∧ survival≥0.7 ∧ BH-reject` — silently dropping Gates 1/5/6/7/8 from promotion and using 0.7 where the gauntlet uses 0.60. |
| (d) **not in the brief** | `scripts/run_evolution_cycle.py:107` | A **second copy** of (c), reachable from the dashboard command runner and `run_autonomous_cycle.py`. It never read the gauntlet's verdict, promoted straight to `status = "active"` on its own rule, and used a **third** survival literal (0.4). It wrote to `m`, not `result`, so the brief's text xfail (`'result["passed_all_gates"] = (' not in src`) could never have seen it. |

## 2. The fixes

**D1 — the null** (`significance.py`). Two valid constructions, both preserving autocorrelation:
- **Stationary-block sign-flip** (always computable): H0 = the stream's true mean is zero and
  symmetric; each geometric block (mean length n^(1/3)) gets one random sign.
- **Block signal-permutation** (only when `signal` and `asset_returns` are passed): block-permute
  the signal against the returns. Destroys alignment, keeps both marginals.
- When both are computable, `p_value` is the **larger** — a candidate must be significant under
  every valid null we can build. p = (1+k)/(1+n) (Phipson & Smyth): a finite permutation test
  never honestly reports 0. Original dict keys kept, so `apply_bh_fdr` is unchanged.
- **Blocks, not the probe's iid reference.** The probe's `sign_flip_null` is iid. On AR(1) H0
  data (φ = 0.5) the iid null rejects **19.0%** at α = 0.05 against the block null's **6.5%** —
  copying the reference would have moved Gate 4 from *zero* power to ~4× false positives
  (`[NN-SHARPE-CI]` rules out iid resampling for exactly this reason).

**D2 — the tests.** The old `returns_low_p_for_real_alpha` asserted only `0 <= p <= 1`: its
*name* promised a power check its assertions never made. Replaced with: SR-3 rejects under both
nulls; SR-0 lands in [0.3, 0.7]; a **size** test (H0 rejection rate 6.5%, with a guard that the
rate is > 0 so the test cannot pass vacuously); and the AR(1) block-vs-iid test above.

**D3 — the threshold.** `config/discovery_settings.json` gains `significance_threshold: 0.05`
and `gate2_survival_threshold: 0.60`, read through one pair of fail-closed readers in
`mode_controller.py`. `validate_candidate` **raises** on `None`. Every caller that passed `None`
was updated — not only the two the brief named, because raising on `None` breaks all of them:
`mode_controller`, `run_foundry_eval_t195`, `run_evolution_cycle`, `run_phase0b_foundry_discover_t193`,
`run_falsifiable_spec`, `verify_gate1_cache_determinism`, `run_discovery_diagnostic_standalone`,
and two test files.

**D4 — the verdict.** Both overwrites are gone. `passed_all_gates` from `validate_candidate`
is authoritative. BH-FDR runs across the batch as a **post-filter that can only demote a
passer** (`bh_fdr_removed` recorded, the count logged), never admit a gate failure. In
`run_evolution_cycle` the gauntlet verdict is now a precondition; its benchmark / Sortino / WFO
checks remain as *additional* strictness.

**D5 — the lock is execution, not text.** The text xfail could be satisfied by rewriting the
line as `result.update(...)` while the overwrite continued, and failed by a comment. Its
replacements drive the real `_run_discovery_cycle` and the real `run_cycle`:
- The stub is **adversarial**: the gauntlet says FAIL, but `sharpe 1.0, survival 0.9, p 0.001`
  — exactly what the deleted rule checked. Without the low p the old code would also promote
  nothing and the test would pass on the buggy code.
- The cycle sits inside a fail-open `try/except Exception: print(WARN)`, so a crash *also*
  "promotes nothing". The test asserts the cycle **reached its registry write**.
- A **positive control**: a clean passer that survives FDR *is* promoted.

## 3. Evidence

**Probe** (`scripts/probe_gate4_permutation_null.py`) — acceptance: `null_std > 0.3` on all four.

| true SR | p (old) | p (new) | null_std (old) | null_std (new) |
|---|---|---|---|---|
| 0.0 | noise | 0.4925 | ~1e-15 | 0.572 |
| 0.5 | noise | 0.1988 | ~1e-15 | 0.578 |
| 1.6 | noise | 0.0070 | ~1e-15 | 0.605 |
| 5.2 | **0.973** | **0.0010** | 1.8e-15 | 0.880 |

Pre-registered refutation (signal-perm `null_std < 0.05`): **not triggered**.

**Reversion** — the unfixed `HEAD` versions swapped in, then restored and verified byte-identical by sha-256:

| Lock | Unfixed code | Fixed code |
|---|---|---|
| D5 (`mode_controller`) | **3 gauntlet failures PROMOTED** — 2/3 tests FAIL (control passes) | 3/3 pass |
| (d) (`run_evolution_cycle`) | failure promoted + `None` threshold — 2/4 FAIL (control passes) | 4/4 pass |

**Suite:** 3,949 passed, 0 failed. RR-2's three xfails pass; the other 13 RR xfails are unchanged.

## 4. Deviations from the brief, each with its reason

1. **Gate-4's call site uses the sign-flip null only.** The brief says the candidate's signal
   panel and the with-arm asset returns are "already in scope at `:1291-1320`". They are not, in
   any form that makes a signal-permutation null valid: Gate 4 runs on
   `attribution = with_candidate.daily_returns − baseline.daily_returns`, a difference of two
   *whole-portfolio* streams whose relation to the candidate's signal runs through the allocator.
   `signal_perm × asset_returns` is not that stream's null. Signal-permutation is implemented and
   tested, and belongs to B-1, where a real signal/return pair exists. *(Ruled by the director.)*
2. **The second overwrite (d) is fixed here.** *(Ruled into scope by the director.)*
3. **Seven extra `None` callers were updated** (§2, D3) — a mechanical consequence of making `None`
   raise; leaving them would have left scripts that crash on their first call.
4. **The threshold readers are private helpers in `mode_controller.py`**, imported by scripts
   (≈1.2 s import cost). This follows the director's reconcile ruling (one reader, keep that
   window's). R may prefer moving them to a public location in the discovery module.
5. **D6 is deferred** — §5.

## 5. D6 — the RE-SCORE: DEFERRED behind RR-1, pre-registered here

The brief asks for `triple_witching` and `january` (T-196's two Gate-1/2 survivors) to be
re-scored through the corrected gauntlet on the T-196 substrate. **Not run.**
`validate_candidate` → `run_backtest_pure` → `BacktestController`, and the program's standing
caveat is explicit: *until RR-1/RR-5 merge, do not run anything through `BacktestController`.*
It is worded for the B briefs, but its reason applies here without change — every gate value in
this re-score (Gate 1 contribution, WFO, and the attribution stream Gate 4 tests) would come
from a referee that sizes from ≈ 2× true equity. A re-score that quotes those numbers would be a
verdict from a known-contaminated referee, which is what `[NN-SUPERSEDED]` exists to prevent.
**If the director reads the caveat as B-only, this is one command away; the ruling is theirs.**

**Pre-registration, frozen now so it cannot drift:** label RE-SCORE (N_trials 0). Run both
features through the corrected gauntlet on the T-196 substrate *after RR-1 merges*; report every
gate's value (0–8) and `bh_fdr_removed`. Expected: both FAIL — at Gate 4 or Gate 8 (calendar
features, no mechanism, and the DSR penalty for the 35-feature family). **A pass on either is
reported as a pass**, and triggers nothing by itself: it would be one surviving candidate under
a referee that has just changed, pending B-1.

## 6. Charter drift — `docs/Core/engine_charters.md:353-365`

The charter describes 4 gates, with thresholds the code does not use. The code's promotion
conjunction (`discovery.py`, `passed_all_gates`) is:

| Gate | Charter says | Code does |
|---|---|---|
| 0 MBL | — | early-return FAIL if the window is shorter than the minimum backtest length |
| 1 | `sharpe > 0` | **contribution** (with − base) `> 0.10` |
| 2 PBO | `> 0.7` | `survival >= gate2_survival_threshold` (**0.60**, config) |
| 3 WFO | `>= 0.6`, a promotion gate | **computed and recorded, never compared** — see §7.2 |
| 4 | Monte Carlo `p < 0.05` | block sign-flip `p < significance_threshold` (config) |
| 5 | — | universe-B Sharpe `> 0` (NaN fails) |
| 6 | — | FF5+Mom factor alpha — **report-only** unless `factor_gate_mode = "kill"` |
| 7 | — | substrate-transfer — **defaults to PASS when skipped** (§7.1) |
| 8 | — | DSR |

**Proposed charter text** (replaces the `Validation result` block and invariants 1 and 4):

> **Validation.** A candidate is promoted to `active` only when `validate_candidate` returns
> `passed_all_gates = True` **and** it survives Benjamini-Hochberg FDR across the cycle's batch.
> `passed_all_gates` is the conjunction of Gate 0 (MBL window), Gate 1 (attribution
> contribution > 0.10), Gate 2 (PBO survival ≥ `gate2_survival_threshold`), Gate 4 (block
> sign-flip permutation p < `significance_threshold`), Gate 5 (universe-B Sharpe > 0), Gate 6
> (factor alpha; report-only unless `factor_gate_mode = "kill"`), Gate 7 (substrate transfer)
> and Gate 8 (DSR). Thresholds live in `config/discovery_settings.json`. No caller may recompute
> or overwrite `passed_all_gates`; BH-FDR may only remove a candidate that already passed.
> Gate 3 (WFO) is recorded but is not currently a promotion condition.

The last sentence states today's truth; whether Gate 3 *should* bind is §7.2's question, not a
charter edit.

## 7. Findings for other briefs (reported, not fixed here — outside RR-2's scope)

1. **Gate 7 has silently PASSED every production candidate — RR-6, and it now matters.**
   `_run_discovery_cycle` builds substrate B with `timeframe=timeframe`; `timeframe` is never
   bound in that function (also true on `origin/main`). The `NameError` is caught by
   `except Exception` → *"Gate 7 substrate-B build failed; gate skipped"* → substrate B = `None`
   → `gate_7_passed` **defaults to True**. Until now the overwrite ignored Gate 7, so this was
   harmless. **Once RR-2 makes the gauntlet authoritative, Gate 7 contributes a free pass to
   every promotion.** RR-6 should land before any promotion cycle runs on RR-2 (none can run
   today: Discovery goes through `BacktestController`, blocked on RR-1).
2. **Gate 3 (WFO) is a phantom gate.** `gate3_consistency_threshold = 0.40` is declared and
   never compared; the charter promises a WFO promotion gate at ≥ 0.6. Production promotion has
   no WFO condition at all. (`run_evolution_cycle` runs its own WFO check at 0.6 while its log
   line says "Target > 0.7" — a fourth pair of disagreeing numbers.) Director to rule whether
   Gate 3 should bind; if so, it is RR-6-shaped work.
3. **`run_evolution_cycle`: a WFO failure never gets a status.** `if not wfo_res: continue`
   leaves the candidate at `"candidate"`, so it is re-queued forever.
4. **A text test certified its own copy of the rule.** `_gate_4_decision` in
   `test_discovery_gate_remediation.py` re-implemented Gate 4 inside the test file and asserted
   against itself — green on the day the rule it described stopped existing. Replaced here with
   an execution test of the real guard; worth a sweep for the same pattern elsewhere.
5. **A threshold reader defined after the `__main__` guard** (`run_foundry_eval_t195.py`, written
   during the incident) raised `NameError` at run time, which the per-candidate `try/except`
   would have turned into an "error" row per candidate. Fixed; confirmed by execution.

## Provenance

After the 2026-09-30 restart, two instances of Agent A edited this worktree concurrently
(13:51–13:57). Commit `9bc1765` (D1, D2) is this owner's; the other instance then wrote a better
D2 size test (my H0 series were demeaned to exactly zero, which pins the statistic at the centre
of any symmetric null — its version is kept), the `mode_controller` post-filter and readers, and
the D5 execution tests. Commit `2263d5b` is the owner's reconcile per the director's ruling: my
duplicate guard, config keys and helper removed; findings (d), the D5 Pass-3 proof and the
reversion runs added.
