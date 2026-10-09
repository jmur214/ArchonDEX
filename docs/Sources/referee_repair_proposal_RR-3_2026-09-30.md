---
task_id: RR-3 (alpha-frontier program, §3.1)
title: Referee repair proposal — honest N fails closed, exact E[max], correlation-aware N_eff
date: 2026-09-30
author: Agent D
branch: fix/referee-rr3-honest-n (NOT pushed, NOT merged)
type: REFEREE REPAIR PROPOSAL — propose-only. Agent R reviews → director → the USER rules on merge.
n_trials: 0 — a correction to the referee, not a hypothesis. Any historical cell re-run under it is a RE-SCORE.
---

# RR-3 — honest N

## 0. What the user is being asked to rule on

1. **Merge the repair** (code + tests on `fix/referee-rr3-honest-n`). §1–§4 are the case.
2. **Accept that it LOOSENS the local gate and TIGHTENS the cloud gate** (§6). A referee repair that makes
   passing easier is the direction that deserves the most scrutiny; every estimator choice below is set to its
   strictest reasonable value for that reason.
3. **Pick the population N_raw is counted over** (§5.2) — the registry as-is (the brief's default and what the
   code does), or a rebuilt one. This is a real choice with consequences either way, not a detail.
4. **The `[NN-MBL]` text in CLAUDE.md** (§5.3) — proposed, not edited.

---

## 1. The defect was four layers, not one

The brief cites two sites. Verified on the base, the absorption of a missing registry runs through **four
successive layers**, each of which would have caught the raise the brief's fix introduces:

| # | where | what it did |
|---|---|---|
| 1 | `mbl_gate.compute_n_effective` | `return 1` when the registry is absent (and `max(1, 0)` when empty) — **cited** |
| 2 | `discovery.validate_candidate`, Gate 0 | `except (ValueError, FileNotFoundError):` *"Log + proceed — better to run the gauntlet than to crash on a precondition check"* — **not cited** |
| 3 | Gate 8 + `validate_candidate`'s outer handler | `except Exception: n = 1  # fail-safe: never block on a bad read` — **cited**; then the outer handler converts any non-programmer error into "candidate failed" — **not cited** |
| 4 | `mode_controller._run_discovery_cycle` | the whole cycle inside `except Exception: print("[DISCOVERY][WARN] Discovery cycle failed")` — **not cited** |

> **Fixing only what the brief names turns its xfail green and changes nothing in production.** Layer 2 would
> have swallowed the new `FileNotFoundError` and proceeded; had it not, layer 3 would have marked every
> candidate failed; had it not, layer 4 would have ended the cycle as one WARN line and "0 promoted" — a null
> result indistinguishable from a real one (the T-177 shape).

Note the comment at layer 3, *"fail-safe: never block on a bad read."* In a measurement path that inverts what
*safe* means: `N=1` skipped Gate 8, whose default reads `gate_8_passed=True`.

## 2. It was not latent: every cloud Discovery cell ran Gate 0 at N=1

`data/observability/` is in `.dockerignore` (line 50), is never `COPY`'d by `Dockerfile.backtest`, and nothing
pulls it from S3. So in **every cloud container** the registry is absent → `compute_n_effective()` = 1 →
MinBTL = 0 → **Gate 0 passed for every candidate**, and `enable_mbl_gate` defaults to `True`. Gate 8 in the
cycle used the batch size (`max(1, len(batch))`, `mode_controller.py:1248`); the T-195 foundry harness passed
`n_trials_for_dsr=len(feats)` (35).

This adds a third independent defect under **T-196's verdict**, which is **already demoted to UNTESTED**
(RR-1/RR-2). It changes nothing about that status; it adds one more correction B-1's re-test inherits.

## 3. The data — the brief's first deliverable of value

`python -m scripts.rr3_empirical_rho --s3-mirror <mirror>` → `data/observability/n_effective_2026-09-30.json`.
Deterministic (fixed seeds), read-only over run evidence.

### 3.1 The population problem, found before any number was computed

The brief asks for ρ̄ "across registered runs". **That is uncomputable.** The run registry
(`run_registry.sqlite`, 231 rows = 125 runs + 106 ledger-reconstructed trial counts) is a **manual `rebuild()`
snapshot** of whatever sat in `data/trade_logs/` at its last run, **2026-08-05** — nothing calls it
automatically. Checked against every place evidence could be:

| | registered runs (125) | on disk (121 dirs) | S3 results bucket (1,201 runs) |
|---|---|---|---|
| registered run found here | — | **0** | **0** (full id or 8-char prefix, in **any** of 120,036 keys) |
| run here that is registered | — | **0** | **0** |

**The registry and the surviving evidence are disjoint sets.** So this measures the **executed-run universe**
— every run whose equity curve survives — which is labelled as such in the artifact and never blended with the
registry's count. It is a far larger sample of our trials than the registry ever held.

(An S3 listing was first unreachable from this machine; I recorded it as UNVERIFIABLE rather than absent, and
resolved it when connectivity returned. "Absent" would have been a confident claim about an absence.)

### 3.2 The table

| stage | runs |
|---|---|
| discovered (S3 1,201 + local 121) | **1,322** |
| valid (≥60 daily returns, finite positive non-flat equity, not census-zero-trade) | **912** — excluded: 400 empty/unparseable, 6 short, 4 never traded |
| after deduping determinism reps | **252** — 660 removed across 133 rep groups; the largest group is **46 identical runs** |

**72% of valid runs are determinism reps**, each counted as its own trial by `SELECT COUNT(*)`.

| overlap threshold | ρ̄ | 95% CI (run bootstrap) | pairs | within-campaign | across-campaign |
|---|---|---|---|---|---|
| ≥ 252 days | 0.605 | [0.571, 0.640] | 2,317 | 0.781 | 0.593 |
| ≥ 120 days | 0.458 | [0.434, 0.481] | 14,454 | 0.596 | 0.443 |
| ≥ 60 days | 0.459 | [0.432, 0.482] | 15,111 | 0.592 | 0.443 |

| ONC (per calendar year, 26 years, 1,279 run-year blocks) | clusters | compression | 95% CI (year bootstrap) |
|---|---|---|---|
| published recursive form (LdP 2020 §4.2) | 75 | 0.059 | [0.041, 0.087] |
| base form, euclidean silhouette | 77 | 0.060 | [0.042, 0.091] |
| base form, precomputed-distance silhouette | 120 | 0.094 | [0.049, **0.160**] |

**N_eff and the resulting bar** (gate inputs = the conservative bounds, §4):

| population | N_raw | N_eff equicorr | N_eff ONC | **N_eff (gate)** | SR_req 12y: old → new | SR_req 26y: old → new | MinBTL @SR=1: old → new |
|---|---|---|---|---|---|---|---|
| registry | 231 | 33.5 | 36.9 | **36.9** | 0.952 → **0.623** | 0.647 → **0.423** | 10.88 → **4.66** yrs |
| executed universe | 252 | 35.3 | 40.3 | **40.3** | 0.960 → 0.633 | 0.652 → 0.430 | 11.06 → 4.81 yrs |

"old" = the `2·ln N` bound at raw N (what the gate used). Of the 10.88 → 4.66 years, **10.88 → 7.91 is the
exact-vs-bound correction** and **7.91 → 4.66 is correlation**.

### 3.3 Pre-registration outcome

**H1 (ρ̄ > 0.3): SUPPORTED at every overlap setting**, including the gate's (≥60d: 0.459, CI floor 0.432). The
refutation branch (ρ̄ < 0.1) is not close. Our trials are heavily correlated: even **across** campaigns ρ̄ ≈
0.44–0.59 — most of what the program counted as independent tests were re-measurements of shared exposure.

### 3.4 Measurement choices, each disclosed because each moved a number

- **The 252-day primary is not neutral.** One single-calendar-year cell has ~249–251 returns, so a 252-day
  threshold silently **excludes the same-year cell pairs** — the lower-correlation ones (ρ ≈ 0.31–0.41 in
  2021–25). That is why ρ̄ falls 0.605 → 0.458 at 120 days. The gate takes the lowest ci_low across settings.
- **The silhouette convention changes the cluster count** (0.059–0.060 vs 0.094). My first pass used one,
  then I switched to the "published" one — which **lowered N_eff**, a non-conservative change made in the name
  of rigour. Both are now reported; the gate takes the highest ci_high.
- **ONC is the less conservative method on this data** (its criterion favours coarse k=2 splits when clusters
  overlap; 22 of 26 years return 2–4 clusters). So the default is `method="conservative"` = the larger of ONC
  and equicorrelated, not ONC by assumption.
- **Dedupe key.** The brief names `trades_canon_md5`, but only 67 surviving runs carry one (the census postdates
  most runs) and recomputing it means fetching 16.6 GB of trade files. Identical trades imply identical equity,
  so I dedupe on the md5 of the daily equity series rounded to cents (absorbing T-057c's cross-container FP
  drift), **cross-checked against census md5 wherever both exist: 0 conflicts in 67.**
- **Silent exclusions were removed.** The first ONC pass dropped 2022 entirely because one zero-variance column
  made its correlation NaN; now the column is dropped and counted (1), never the year.

## 4. The gate reads CI bounds, not point estimates

N_eff moves 231 → 61 → 10 as ρ̄ goes 0 → 0.3 → 0.68. With that much leverage, gating on a point estimate would
let estimation error loosen the bar. `[NN-SHARPE-CI]`'s logic, applied to the trial count: the artifact's
`gate_inputs` are **ρ̄'s lowest ci_low across overlap settings (0.432) and the highest compression ci_high
across ONC forms (0.160)**, and `compute_n_effective_correlated` takes the **larger** of the two N_eff
estimates. No single measurement choice can loosen the bar.

Two floors, stated so they cannot be undone by a noisy estimate: N_eff is floored at **2** (at N_eff=1 MinBTL is
0 — defect 1's door reached by another route), and a negative ρ̄ **never** licenses more trials than were run.

## 5. One N — the reconciliation

### 5.1 The series, sourced where I could source them

| figure | source | what it is |
|---|---|---|
| ~75 | CLAUDE.md `[NN-MBL]` | an early accumulated-trial estimate |
| 231 | `run_registry.sqlite` | 125 registered runs + 106 ledger-reconstructed trial counts (`backfill_run_registry_t336.py`), frozen 2026-08-05 |
| ~260 | CURRENT_STATE ("effective ~260+") | an estimate adding campaigns the registry missed |
| 76–78, ~295 | cited in the brief | **I did not trace these and do not assign them a provenance** |
| 1,322 / 912 / 252 | this measurement | executed runs / valid / distinct |

**A fifth inconsistency worth knowing:** CLAUDE.md says the 5-year window requires *"SR ≥ 1.55"* at ~75 trials.
Its own formula gives **1.31** at N=75; 1.55 corresponds to N≈406 under the bound. The number cannot be derived
from the text around it.

**The one definition proposed:** *Honest N for Discovery Gate 0/8 = `compute_n_effective_correlated()` — the
registry's raw count adjusted by the measured trial correlation at its conservative bounds. At 2026-09-30:
N_raw 231 → N_eff 36.9.* It fails closed; an un-establishable N is a halt, never 1.

### 5.2 ⚠️ The population question — the user's call

The code follows the brief: N_raw = the registry. But the registry (a) is a stale manual snapshot, (b)
**undercounts** executed runs (1,322 executed, 252 distinct, vs 125 registered runs), and (c) **mixes
substrates**: its 106 ledger rows include research trials on the T-306 multidecade substrate (T-282/312/318…)
alongside Discovery-substrate trials (T-196's 35). Under `[NN-MBL]`, N counts configurations run *on the same
substrate*, so (c) arguably **over**counts Discovery's N. Options:

- **A. Keep the registry as N_raw** (what the branch does). Conservative on (c), stale on (a)/(b). N_eff 36.9.
- **B. Rebuild the registry from the executed universe** (S3 + local), per substrate. More honest, and changes
  referee bookkeeping data — so it is a separate proposal, not done here. The executed-universe row above shows
  where it lands today: N_eff 40.3.

The two agree within ~10% today. That is luck, not design, and should not be relied on.

### 5.3 Proposed `[NN-MBL]` text (CLAUDE.md is NOT edited)

Replace *"At our current ~75 accumulated N_trials, the 5-year substrate-honest window requires SR ≥ 1.55 to
clear DSR — our corrected 0.598 baseline cannot clear it regardless of measurement discipline."* with:

> MinBTL uses the exact form `E[max_N]² / SR²` (`2·ln N` is its upper bound, kept only for comparison). Honest N
> is correlation-aware and FAILS CLOSED: `compute_n_effective_correlated()` — the run registry's count (231 at
> 2026-09-30) adjusted by the measured trial correlation (ρ̄ 0.46–0.61; the gate reads the conservative bound)
> to N_eff ≈ 37. At that N_eff a 5-year window needs SR ≥ 0.97, 12 years ≥ 0.62, 26 years ≥ 0.42. An N that
> cannot be established halts the measurement; it is never 1.

The sentence's conclusion survives the correction: at SR ≥ 0.97 the honest PIT base (≈0.1–0.3) still cannot
clear a 5-year window, so *"the 5-year window is exploratory"* stands unchanged.

## 6. Which way the bar moves — stated plainly

| path | before | after | direction |
|---|---|---|---|
| **cloud** Discovery Gate 0 | N=1 → MinBTL **0** (vacuous) | N_eff 36.9 → MinBTL 4.66 yrs @SR1 | **TIGHTER** |
| local Discovery Gate 0 | bound @231 → 10.88 yrs | exact @36.9 → 4.66 yrs | **LOOSER** |
| Gate 8 (production cycle) | batch size (≤10) | N_eff 36.9 | **TIGHTER** |
| Gate 8 (callers passing N) | their N | their N, now also used by Gate 0 | same |

The local loosening is real and large (~57% fewer required years). It is legitimate only because both
components are corrections of documented errors (the bound used as the gate; independent-trial counting), and
it is why §3.4/§4 set every estimator to its strictest value. A concrete check that the gate keeps its teeth:
T-336's "plausible candidate" (a 900-day series, annualised SR 1.56) scores DSR **0.998** at N=1 (cloud's
effective state), **0.546** at raw N=231, **0.780** at N_eff=36.9 — still well below the 0.95 bar.

## Verdicts this does not change

**T-251, T-259, T-279, T-282, T-284, T-312, T-318** are paired-difference CIs against zero, not DSR-gated, so
none of them flips. Verified rather than assumed — none of their scripts imports or calls anything RR-3 changes:

| verdict | script | touches `mbl_gate` / `compute_n_effective*` / `deflated_sharpe` / `validate_candidate`? |
|---|---|---|
| T-251 | `barbell_gauntlet_t251.py` | no |
| T-259 | `offleg_ab_t259.py` | no |
| T-279 | `premium_tier_t279.py` | no |
| T-282 | `trend_gated_leverage_t282.py` | no |
| T-284 | `fullequity_gated_leverage_t284.py` | no |
| T-312 | `offense_campaign_t312_t315.py` | no |
| T-318 | `tilt_decision_measure_t318_t320.py` | no |

**More generally, no historical MBL PASS can be overturned by RR-3.** Research scripts that compute MinBTL
inline (T-236/255/260/266/269/311) used the bound at raw N — both conservative — so anything that passed there
passes under the exact, correlated form. The only non-conservative computation was cloud Discovery's N=1, and
the verdict resting on it (T-196) is already UNTESTED.

## 8. What changes

- **Code:** `core/measurement/mbl_gate.py` (fail-closed N, exact MinBTL with `upper_bound=` for comparison,
  `expected_max_normal`, `n_eff_equicorrelated`, `compute_n_effective_correlated`, `resolve_cycle_n_trials`,
  named `HonestNUnavailableError(FileNotFoundError)`); `engines/engine_d_discovery/discovery.py` (Gate 0 and
  Gate 8 fail closed; one N per evaluation; an unparseable window fails Gate 0 instead of skipping it; the outer
  handler re-raises the honest-N error; N and its source recorded in every result); 
  `orchestration/mode_controller.py` (N resolved **first**, before hunting and before `save_candidates` writes
  `edges.yml`; the registry N replaces the batch size; the cycle handler re-raises the honest-N error only).
- **New:** `scripts/rr3_empirical_rho.py`; `tests/test_honest_n_rr3.py`.
- **Dependents to restate on merge** (my supersession-dependents rule, applied to this change): CLAUDE.md
  `[NN-MBL]` (§5.3), `docs/Core/NON_NEGOTIABLES.md`, `docs/Core/execution_manual.md`, `docs/HANDOFF.md`, and my
  own open pre-registration **T-342**, whose Gate-0 line ("SR ≥ 0.70–0.75") used the bound at N=127–260 and
  would read ~0.47 at N_eff 36.9 on its 19.7-year window. Frozen audits are not touched
  (`[NN-AUDITS-NOT-CURRENT]`).

## 9. Verification

- **The brief's three xfails pass**; the other 13 still xfail (no strict XPASS). Only those three markers removed.
- `python -m scripts.probe_mbl_n_effective` reproduces (38.7% overstatement at N=260).
- **20 new tests, each driving a real entrypoint** — and **proven by reversion**: reverting each layer's fix in
  isolation makes its test fail (layers 1, 2, 3, 4 each checked; all restored, 20/20 clean).
- **Hermeticity.** Run with every N source pointed at nothing, 8 existing tests turned out to pass only because
  this laptop holds the registry — before RR-3 they passed everywhere because N silently became 1. Six were made
  hermetic by passing an explicit N (what production now does; the suite already had that precedent). Two
  T-336 tests assert the real registry's refresh state **by design** and failed data-less before RR-3 too; left
  as they are.
- **Five existing tests locked the defects** — two asserted the `2·ln N` numbers as "the dev spec", one required
  *"no registry file → return 1"*. Corrected, not deleted: the dev-spec figures are kept as assertions **of the
  bound**, the exact values added, and the fail-open test inverted (with empty and 0-byte registries added —
  a 0-byte `run_registry.db` phantom really does sit beside the registry).
- **Full suite: 3,961 passed, 2 failed** — both in `test_pulse_news_wiring_t290b.py::TestRepoRelativeRoot`, and
  both **fail identically on the untouched base** (worktree-path dependent). Not RR-3's.

## 10. Findings for other briefs (not acted on)

- **RR-2 / NEW-4:** `test_gate_6_fails_on_factor_decomposition_exception` asserted `passed_all_gates is False`
  after a Gate-6 exception. That held **only through Gate 8** — Gate 6 is report-only by design ("diagnostic,
  not killed"). With Gate 8 skipped (N=1), the same candidate **passes all gates with an attribution Sharpe of
  7.3×10¹⁶** — a constant-return stream through the unguarded std in `stream_sharpe` (xfail NEW-4). The test
  now passes an explicit realistic N and says in a comment which gate holds the assertion.
- **Foundry harness:** `scripts/run_foundry_eval_t195.py` still passes `n_trials_for_dsr=len(feats)`. Any re-run
  (e.g. under B-1) should pass the honest N; left unchanged as a closed task's script.
- **Registry hygiene:** `core/observability/run_registry.py` defaults to a **cwd-relative** path while `mbl_gate`
  uses an absolute one — the split-in-two class the janitor already hit with its ledger. And a 0-byte
  `data/observability/run_registry.db` phantom exists (it now correctly reads as unavailable, not N=1).

## 11. What I did not do, and why

- **No `honest_n` key in `performance_summary.json.census`.** The census is built in
  `backtester/backtest_controller.py` — RR-1's file, in flight on another branch — and a fail-closed N read in
  *every* backtest's census would halt every cloud cell (the registry isn't in the image), a blast radius far
  beyond Discovery. The N is recorded with the decision that uses it: every Discovery result carries
  `n_trials_for_dsr`, `n_trials_source`, `gate_0_n_effective(_source)` (→ `discovery_log.jsonl`). If a census
  key is still wanted, it should be a non-fatal `unavailable` field — a design decision, flagged here.
- **No registry rebuild** (§5.2 B) — it changes referee bookkeeping data; a separate proposal.
- **No CLAUDE.md or NON_NEGOTIABLES edit** — proposed in §5.3.
- **`mode_controller.py` is shared with RR-2**, whose hunks sit at ~1338–1403; mine are at the cycle's top,
  ~1248, ~1305 and the handler at ~1441. Non-overlapping, but the same file — noted for whoever merges second.

## 12. Operational consequence on merge

**Cloud `--discover` will HALT with `HonestNUnavailableError` until an N is supplied** — by passing
`n_trials_for_dsr` explicitly, or by shipping the registry and `n_effective_*.json` into the container. That is
the intended behaviour: the alternative is what happened until now, gating at N=1.

## 13. Deviations from the brief

- **Base branch:** the brief's setup bases on `origin/main`, which does **not** contain the review (the merge
  `4160cc5` is on the director's local `main`, 8 commits ahead, unpushed), so `tests/test_referee_repairs_proposed.py`
  and the probe don't exist there. The branch is based on local `main` (`ff62940`), the only base where the
  acceptance criteria are satisfiable.
- **Population** (§3.1), **dedupe key** (§3.4), **census key** (§11), and **default method = conservative** (§4)
  — each stated where it is made, with the reason.

---
**PROPOSAL ONLY — not pushed, not merged. The referee is never autonomously modified.** R reviews, then the
director, then the user rules. N_trials: 0.
