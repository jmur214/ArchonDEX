# T-162 — The allocator-vs-BLAS disambiguation cell (pre-registered)

**Date:** 2026-06-12
**Agent:** C (branch `feature/allocator-disambig-t162`, off origin/main `6448a55`)
**Status at this commit:** PRE-REGISTRATION ONLY — expectations committed BEFORE the cell runs (CLAUDE.md #7 discipline). Results section intentionally empty.

## The collision being disambiguated

B's T-155 Part 3 attributed the persistent local↔cloud 2022 canon split — local `0145c03a…`/Sharpe 0.464 vs cloud anchor `0a62b754…`/Sharpe 1.6 — to **platform BLAS** (macOS Accelerate vs Linux OpenBLAS), having controlled data (pinned earnings, byte-identical), arch (arm64 both), and state (hermetic). B could not have known my T-158 finding (merged mid-saga): **B's local cell ran with `data/research/allocation_recommendations.json` present → the adaptive allocator (mode override fires every bar); the cloud container has no such file → mean_variance.** The comparison is allocator-confounded, and a 0.464-vs-1.6 Sharpe gap looks like two systems, not FP noise. One displaced-artifact cell separates the mechanisms.

## Pre-registered design

**The cell:** ONE local 2022 arm0 run, controls matched to B's T-155 local verify cell exactly:
- `ARCHONDEX_HERMETIC=strict` (B's verify mode; earnings pin is parquet-primary/automatic since T-155),
- thread pins `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1` (the T-140 fix; VECLIB is the macOS-Accelerate analogue),
- `PYTHONHASHSEED=0`, `scripts.run_isolated --task q1 --year 2022` (governor-isolated),
- **with the allocator artifact DISPLACED** (copy-preserved, never deleted): `data/research/allocation_recommendations.json` → `.t162_held`, original moved aside; restored after and **md5-verified** (pre-displacement md5: `bfa539466599066c35dc985c667848dd`).

**Mechanism check (runs first, also pre-registered):** with the artifact displaced, the T-158 probe technique must show the mode override does NOT fire — live `optimize` calls > 0 and `_apply_vol_target`/`_apply_exposure_cap` calls == 0 on a 2022-Q1 probe window. If the override still fires from some other source, STOP — the cell would not be measuring what it claims.

## Pre-registered hypotheses (committed before any result is known)

| Hypothesis | Prediction for the displaced-artifact local 2022 cell | Reading |
|---|---|---|
| **H-alloc** | canon == `0a62b754…` (bitwise) and Sharpe ≈ 1.6 | The allocator explains the split ENTIRELY; platform BLAS contributes nothing canon-visible on this workload. B's BLAS attribution re-dated to "allocator artifact." |
| **H-mix** | Sharpe lands ≈ 1.6 (cloud family) but canon ≠ `0a62b754` and ≠ `0145c03a` | Allocator DOMINANT (the 0.464→1.6 gap is the allocator), BLAS/platform FP residual real at the bitwise level. Cross-substrate comparisons need allocator control AND can never be expected bitwise. |
| **H-BLAS** | Sharpe stays near 0.464 / canon lands elsewhere entirely | Allocator does NOT explain the split; platform FP (or an unknown third mechanism) is material even at Sharpe scale. My T-158-based confound claim was wrong in magnitude. |

**Honest prior (stated for the record):** H-mix is the most likely — matching the allocator should move the local cell into the cloud's Sharpe family (the gap is too large for FP), but bitwise canon agreement across two BLAS implementations would be unusual for an `eigh`-bearing workload even thread-pinned. H-alloc-bitwise would be the cleanest possible outcome; H-BLAS would refute my own T-158 confound framing — and is exactly why this is worth one cell.

**Decision implications (pre-committed):**
- H-alloc or H-mix → the allocator-identity decision (archive the Apr-23 artifact vs commit it to config) becomes the binding lever on local/cloud comparability; B's "cloud is the substrate of record" stands unchanged (cloud is internally consistent either way).
- H-BLAS → reopen the platform-FP lane (B's attribution stands); the allocator divergence remains a real-but-secondary hygiene issue.
- In ALL cases: no cross-substrate canon comparison without (a) allocator state matched and (b) thread pins; bitwise expectations only within-platform.

**Cost/N:** LOCAL only, zero N_trials (mechanism cell; no performance hypothesis is being selected on). Diagnostic-only: no flag flips, no config edits; artifact restored + md5-verified.

---

## Results (EMPTY at pre-registration commit — filled after the cell)

_(to be appended)_
