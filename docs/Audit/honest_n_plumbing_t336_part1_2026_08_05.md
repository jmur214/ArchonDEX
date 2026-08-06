---
task_id: T-2026-07-30-336-part1
title: T-336 Part 1 — T-200 honest-N plumbing COMPLETED (registry refresh, Gate-8 threading, OOS-lock activation)
date: 2026-08-05
worker: Agent B
branch: feature/t336-honestn-oas
status: DONE — both integration-bar artifacts produced. ⚠ Contains a POLICY-LEVEL behaviour change in Engine D that needs the director's explicit confirmation (§b).
---

# T-336 Part 1 — the measurement-integrity debt, paid

## (a) Registry refreshed: **125 → 231** (`compute_n_effective()` now returns 231)
The registry was **frozen at 125 rows since 2026-05-08** — it is built by scanning run
DIRECTORIES, and the project long ago moved to task-based measurement runs whose artifacts
don't land there. So every DSR/MBL deflation has been fed **125** while CURRENT_STATE
reported honest N ≈ 260+.

**Reconstruction method (documented, auditable, idempotent)** —
`scripts/backfill_run_registry_t336.py`:
1. Existing run-dir rows untouched (`source='run_dir'`).
2. Parse `docs/State/TASK_LEDGER.md` for each task row's recorded increment
   (`N_trials += k`, `N+=k`) → insert `k` rows tagged `source='ledger:<task_id>'`.
3. Keys are `ledger:<task>:<i>` ⇒ **re-running adds 0** (verified).
4. Explicit `N+=0` rows are parsed and recorded as **zero** trials (re-analyses consume no
   multiple-testing budget) — skipped deliberately, not silently dropped.

Result: 26 ledger task-rows carrying N, 106 increments, **125 → 231**.

**Honest limits (stated):** the ledger is the project's own record — a measured task that
never recorded its increment cannot be recovered by this method, so **231 is a LOWER
BOUND** (the true figure is nearer CURRENT_STATE's ~260). No PCA/correlation reduction is
applied, matching `compute_n_effective`'s own stated policy.

**Immediate consequence for `[NN-MBL]`:** at N=231, `T_required = 2·ln(231)/SR²` →
**30.4 yr at SR 0.598** (was 24.1 yr at N=75). The T-306 deep substrate (58-64yr) still
clears that; the shallow 26yr window now fails it by a wider margin than previously stated.

## (b) Gate 8 now deflates on the honest N — ⚠ **a policy-level behaviour change**
`validate_candidate(..., n_trials_for_dsr: int = 1)` meant **Gate 8 was SILENTLY SKIPPED in
every default run** (`gate_8_passed: True  # Default True = SKIPPED`). The multiple-testing
correction the gate exists to apply was off, against a 200+-trial history.

Now `n_trials_for_dsr: Optional[int] = None` → resolves at call time to
`compute_n_effective()`, with a fail-safe fallback to 1 if the registry read errors
(never block on a bad read). Explicit ints still override.

**INTEGRATION-BAR ARTIFACT 1 — the deflation visibly uses the refreshed N:**
```
candidate raw Sharpe        : 1.562   (passes a naive gate)
DSR @ n_trials=1            : 0.9983  -> Gate 8 PASS   [LEGACY default: SKIPPED]
DSR @ n_trials=231          : 0.5464  -> Gate 8 FAIL   [T-336 honest N]
```
**⚠ DIRECTOR CONFIRMATION REQUESTED.** This is the intent of the dispatch, but it is a
*policy* change, not just plumbing: Gate 8 now **evaluates by default**, and at N=231 the
DSR bar is severe. Discovery has promoted **zero edges in project history**; this makes
promotion strictly harder. I believe that is the honest consequence of a 231-trial history
— a candidate that cannot clear DSR at our real N genuinely has not earned promotion — but
the program should adopt it deliberately rather than inherit it from a default I changed.

Two existing tests failed on this change. **Both encoded the old default** (one literally
commented `# n_trials_for_dsr defaults to 1`) while their names claim to isolate a single
gate; I pinned `n_trials_for_dsr=1` in those two so they test what they say, and added a
new test asserting the *new* default resolves to the honest N and actually bites. I did not
"make tests pass" — the tests were pinned for a stated reason and the changed behaviour is
now itself covered.

## (c) OOS lock ACTIVATED — it had zero callers and no config file
Created `config/oos_window.json` (`active: true`, window starts 2026-07-01, code-state hash
pinned). **Frozen parameters chosen to match commitments this program has already made:**
`ensemble_speeds` (the T-260-deep *"NO RE-SELECTION — {42,105,210} does not change"*
pre-commitment), `sleeve_deadband`, `sleeve_asset_weights`, `damping_band_B`,
`exposure_cap`. **The lock is what makes those pre-commitments enforceable rather than
remembered** — and T-314's frozen baseline depends on them.

Wired a real caller: `scripts/sweep_cap_recalibration.py` (it retunes a cap) now calls
`assert_not_tuning_in_oos` and **exits 3** on refusal.

**INTEGRATION-BAR ARTIFACT 2 — a deliberate violation, refused end-to-end:**
```
$ python -m scripts.sweep_cap_recalibration --run a1
REFUSED by the OOS lock: Parameter 'exposure_cap' is frozen by the OOS lock
(window starts 2026-07-01). Sweep window 2026-01-01..2026-12-31 overlaps the OOS window.
... To proceed: (a) restrict the sweep to data BEFORE 2026-07-01, (b) explicitly retire the
lock in config/oos_window.json with a recorded rationale, or (c) roll the OOS window forward.
```
Controls confirm no false positives: an **unfrozen** parameter is allowed, and a frozen
parameter swept **entirely before** the window is allowed.

## Tests / hygiene
`tests/test_oos_lock_activation_t336.py` (7 new). **320 passed** across the
discovery/gate/mbl/registry/dsr/oos selection; **3,295 collect clean**.
