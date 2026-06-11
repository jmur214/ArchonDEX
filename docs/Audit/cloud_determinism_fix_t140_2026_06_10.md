---
task_id: T-2026-06-10-140
title: Cloud determinism fix — single-thread BLAS pins + sorted-iteration sweep + canon-anchor hard gate + N≥5 unanimity re-baseline
date: 2026-06-10
scope: cloud entrypoint, run_isolated local parity, campaign launcher gate, 2 sorted-iteration fixes, new pinned image + job def, 10-cell re-baseline campaign
outcome: "**GATE CLEARED — CANON UNANIMITY EVERYWHERE.** 26-yr: 5/5 bitwise `529e5520…`/0.237. 16-yr: 5/5 bitwise `62db5c0d…`/1.021. 2022 canary: 3/3 bitwise `0a62b754…`/1.60. The deterministic environment lands on the 0.237 attractor — T-127's NUMBER is rehabilitated (its mechanism was wrong); `2b2f2c2b`/0.446 is retired as the multi-thread minority attractor. New authoritative anchors published (image `t140-fix` @ commit `e5c00d1`, substrate `147e9d0e`). Perf: 16-yr ~zero cost (129 vs 130-134 min); 26-yr +37% (240 vs 175 min, attribution partly confounded with commit/substrate drift). Bull-conditional collapse (1.021 vs 0.237) CONFIRMED on deterministic substrate."
---

# T-140 — Killing the Cloud Placement Lottery

## 1. The fix (Vector B — multi-threaded LAPACK instability)

T-128's probe evidence: `numpy.linalg.eigh` on a FIXED seeded input
returned different bitwise results across Fargate tasks (5-vs-1 md5
split); with `OMP_NUM_THREADS=1` + `OPENBLAS_NUM_THREADS=1` it went
unanimous 6/6. Mechanism: multi-threaded OpenBLAS/LAPACK reductions
partition work by runtime conditions, changing FP summation order
per task. The production MVO path (`engine_c_portfolio/policy.py` →
`optimizer.py` → `scipy.optimize.minimize` over `w·Σ·w`) hits this
op class every solver iteration; T-128's log-diff showed the canon
divergence starting as MVO epsilon residue on the FIRST bar.

Shipped (belt + suspenders):
- **`scripts/cloud_entrypoint.sh`**: `export OMP_NUM_THREADS=1
  OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_DYNAMIC=FALSE` before
  the harness starts — covers ad-hoc job definitions.
- **Job definition `archondex-backtest-t140-fix`**: same four vars in
  the registered env — covers command overrides that bypass the
  entrypoint.
- **`scripts/run_isolated.py`**: same pins folded into the existing
  `PYTHONHASHSEED=0` re-exec (they must precede numpy's first import).
  Local parity: local was stable in practice, but pinning both sides
  makes local and cloud numerically comparable by construction.

**Local canon-neutrality proof:** at current main, the 2024 cell
produces `5d88e1a0f70f0cd052a7813a6e40b1a9` / Sharpe 0.991 both
UNPINNED (clean main) and PINNED (this branch) — bitwise identical —
and `--runs 3` PASS bitwise with pins. The pins do not change local
results; they remove a cloud-only degree of freedom.

(Note in passing: the local 2024 reference moved from T-124-era
`b6137649…`/0.86 to `5d88e1a0…`/0.991 due to merges on main between
236d8f4 and d0c9779 — verified pre-existing on clean main, unrelated
to this task's changes.)

## 2. The fix (Vector A — per-task-unique directory order)

T-128's probe: `os.listdir("/app/data/processed")` returned the same
732 files in a DIFFERENT order in every one of 6 tasks (Fargate layer
materialization). Any unsorted directory iteration feeding
computation is a per-task coin flip.

**Full sweep: 21 sites audited** across `engines/`, `core/`,
`backtester/`, `orchestration/`, `cockpit/`, and cloud-path
`scripts/` (pattern: `os.listdir | iterdir | glob | rglob | walk |
scandir`, excluding tests/archive):

| Class | Count | Sites |
|---|---|---|
| Already sorted | 9 | `news_sentiment_edge:81`, `earnings_data:327`, `insider_data:298`, `ablation:118/133` (mtime-keyed), `fred_macro:55`, `run_registry:224`, `earnings_calendar:57`, `local_ohlcv:59` |
| Order-insensitive by construction (`max()` over mtimes, set membership, sorted at consumption) | 10 | `fred_macro:76`, `earnings_calendar:80`, `local_ohlcv:79`, `local_ohlcv:125` (sorted wrap), `discovery:744` (set → sorted consumption), `universe_resolver:256` (returns sorted), `run_isolated:385/391/463`, `capital_allocation_loader:45` (UI, mtime-sorted output) |
| **FIXED** | **2** | **`engines/engine_f_governance/evolution_controller.py:113`** — data_map dict built in glob order (computation-feeding; Engine F discovery path); **`core/feature_foundry/model_card.py:230`** — validation-error ordering (hygiene) |

**Engine B touches: ZERO** — no unsorted directory-iteration sites
exist in Engine B (the T-057c signal_collector sort already covered
its known case).

The arm0 backtest path itself contained no unsorted iteration —
consistent with T-128's finding that arm0's divergence vector was
LAPACK (Vector B), not file order (Vector A). Vector A mattered for
discovery-path work and as latent risk.

## 3. Canon-anchor HARD gate (protocol → structure)

`scripts/submit_arms_campaign.py::load_spec` now refuses any
multi-arm spec that lacks BOTH (a) an unpatched baseline arm (empty
`config_patch` — the anchor cell runs inside the campaign) and (b) an
explicit `"anchor": {canon_md5, source, image}` block naming a
verified same-image arm0 canon. Single-arm specs are exempt (they ARE
anchor measurements). 4/4 unit checks pass (blocked bare multi-arm;
allowed baseline-arm, external-anchor, single-arm).

This is the T-128 pre-flight protocol — which caught the invalid
sleeve A/B — made structural instead of procedural.

## 4. Blast radius — what carries the lottery, what survives

The lottery is **older than the June saga**. Re-examining T-092
(May-31, the foundational deep-substrate measurement) per-rep canons:

| T-092 window | Reps | Canons | Verdict |
|---|---|---|---|
| 2010-2025 (16-yr) | 5 | 4× `b9cb088f`/1.018, **1× `eb9f43fd`/0.953** | **SPLIT** |
| 2000-2025 (26-yr) | 4 | 3× `c579566c`/0.246, **1× `a762df52`/0.437** | **SPLIT** |

The two attractor families (~0.24 vs ~0.44 at 26-yr; ~1.02 vs ~0.95
at 16-yr) were present in T-092's own reps and went unflagged —
headline numbers were majority draws. Same for `t109-det-sanity`
(2-vs-1 canon split, Jun-6).

| Verdict (Jun-6 → Jun-10 era) | Status under the lottery |
|---|---|
| **T-092 strategic conclusion** (deep-window collapse; bull-conditional base) | **SURVIVES** — both attractors (0.246 AND 0.437; 0.237 AND 0.446) fail every deployment gate; the strategic picture never depended on which draw you got. Precision of anchors did. |
| **T-092 headline numbers** (16yr 1.018, 26yr 0.246) | Majority draws, not canonical. Superseded by the T-140 re-baseline anchors. |
| **T-109 static-20 A/B directional REJECT** | Plausibly survives (within-image, 1-yr cells where lottery moved canon but Sharpe only in 3rd decimal); absolute numbers carry lottery. Re-verify only if it ever becomes load-bearing. |
| **T-125 "determinism RESTORED 3/3"** | Artifact of same-attractor luck on 3 draws (1-yr cells). The pinned-base-image work itself remains good hygiene. |
| **T-125 re-baseline (26yr 0.446 / 16yr 0.945)** | Single draws. Not canonical. |
| **T-126 bisect ("code-shift" attribution; 0.237 vs 0.246 hmm-ON/OFF reading)** | Single draws per cell — attribution unsafe. |
| **T-127 "bytecode root cause; saga closed"** | **REFUTED-AS-CONFOUNDED** (T-128). The pyc-hygiene fixes (dockerignore, git-archive builds, substrate manifest) stay — good practice, just not the cause. |
| **T-128 sleeve A/B** | Invalid (its own finding). Sleeve chapter OPEN; relaunch on the new anchors. |
| **All local Mac results** (every local measurement, all eras) | **UNAFFECTED** — single-host, `--runs 3` enforced, and the pins are proven canon-neutral locally. |
| **Within-task cloud results** (any single cell's internal consistency) | Valid as individual runs; only CROSS-task comparisons carried the lottery. |

## 5. The re-baseline (N=5 × 2 windows, the acceptance gate)

Campaign `t140-rebaseline-unanimity`: 5 task-reps × {2010-2025,
2000-2025} × arm0 (prod config, hmm-ON) on image
`archondex-backtest:t140-fix` (built at commit `c548ba6` by
`scripts/build_backtest_image.sh` — git-archive clean-source,
manifest-verified substrate `a40d5483…`), job def
`archondex-backtest-t140-fix` (ARM64 Fargate, env pins registered).

**Acceptance = canon UNANIMITY at N=5 per window.**

### Results — GATE CLEARED

Campaign `t140-rebaseline-unanimity` (2026-06-11, 13 cells, 0
failures, summary `data/cloud_runs/t140-rebaseline-unanimity_20260611T055138Z.json`):

| Window | Reps | Canon | Sharpe | Unanimous? |
|---|---|---|---|---|
| 2000-2025 (26-yr) | 5 | `529e55204a92462337169fb0b3f3a4fd` | 0.237 | **YES — 5/5 bitwise** |
| 2010-2025 (16-yr) | 5 | `62db5c0db75f4d6c148a7e53d472cb1e` | 1.021 | **YES — 5/5 bitwise** |
| 2022 (launcher canary) | 3 | `0a62b7541d3dfe697905d279b3eb1431` | 1.60 | **YES — 3/3 bitwise** |

**These are the new authoritative anchors** (prod config, hmm-ON,
image `archondex-backtest:t140-fix` @ commit `e5c00d1`, substrate
manifest `147e9d0e…`, job def `archondex-backtest-t140-fix:1`).

**Which attractor won:** the deterministic environment lands on
**0.237 / `529e5520`** at 26-yr — bitwise-identical to T-127's
Cells B/P/C. T-127's NUMBER is rehabilitated (its bytecode mechanism
remains refuted); `2b2f2c2b`/0.446 is retired as the multi-thread
minority attractor (it was the THREADED-LAPACK draw, sampled by
T-125's re-baseline and T-128's arm0). At 16-yr the anchor matches
T-128's draw (`62db5c0d`/1.021) and sits within rounding of T-092's
majority family (1.018). The 2022 canary matches the historical
majority attractor (`0a62b754`, T-109/T-125).

**Strategic confirmation:** 16-yr 1.021 vs 26-yr 0.237 on a fully
deterministic substrate — the T-092 bull-conditional-collapse
narrative is now CONFIRMED without lottery caveats.

### Perf cost of single-thread BLAS

Like-for-like cloud comparison (same windows, same hardware class;
T-128 unpinned cells Jun-10 vs T-140 pinned cells Jun-11):

| Window | T-128 unpinned wall | T-140 pinned wall (n=5) | Delta |
|---|---|---|---|
| 16-yr | 130–134 min | mean 129 (120–133) min | **~0%** |
| 26-yr | 175 min | mean 240 (234–247) min | **+37%** |
| 2022 1-yr | — | 7 min | — |

Attribution caveat: the +37% at 26-yr is an UPPER bound on pin cost —
commit (9374871→e5c00d1) and substrate manifest (a40d5483→147e9d0e)
also moved between the two measurements, and the 16-yr null delta
argues the pins alone don't cost 37%. Likely the 2000-2009 decade's
heavier solver activity is more single-thread-sensitive, and/or
substrate growth added work. Correctness wins regardless (per
dispatch); if the 26-yr wall matters later, profile then.

Local reference: pinned 2024 cell `real=119.7s` (unpinned same cell
identical canon; timing difference within shared-host noise).

## 6. Files

- `scripts/cloud_entrypoint.sh` — BLAS pins export
- `scripts/run_isolated.py` — local-parity pins in the re-exec
- `scripts/submit_arms_campaign.py` — canon-anchor hard gate
- `engines/engine_f_governance/evolution_controller.py` — sorted glob (Vector A)
- `core/feature_foundry/model_card.py` — sorted glob (hygiene)
- job def `archondex-backtest-t140-fix` (AWS, env-pinned)
- image `archondex-backtest:t140-fix` @ commit `c548ba6` (ECR)
- this audit

## 7. Memory updates needed (post-merge)

- "T-140: cloud placement lottery KILLED — OMP/OPENBLAS/MKL=1 pins
  (entrypoint + job def + local parity), sorted-iteration sweep (21
  sites audited, 2 fixed, 0 Engine-B), canon-anchor hard gate in the
  launcher. Pins proven canon-neutral locally. UNANIMITY GATE CLEARED:
  26-yr 5/5 bitwise `529e5520`/0.237; 16-yr 5/5 `62db5c0d`/1.021;
  2022 canary 3/3 `0a62b754`/1.60 — new authoritative anchors at
  image t140-fix / commit e5c00d1 / substrate 147e9d0e. The 0.237
  attractor won (T-127's number rehabilitated, mechanism stays
  refuted; 0.446 retired as the threaded-LAPACK minority draw).
  Perf: 16-yr ~0%, 26-yr +37% (upper bound, partly confounded).
  The lottery predates June: T-092's own reps were canon-split
  (16yr rep5 0.953 vs 1.018; 26yr rep4 0.437 vs 0.246) — headline
  numbers were majority draws. Strategic conclusions survive (both
  attractors fail all gates); bull-conditional collapse confirmed
  deterministically (1.021 vs 0.237)."
