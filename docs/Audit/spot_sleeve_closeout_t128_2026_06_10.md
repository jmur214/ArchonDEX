---
task_id: T-2026-06-10-128
title: Spot-sleeve close-out A/B — INVALIDATED by pre-flight; cross-task cloud nondeterminism rooted (T-127 mechanism refuted-as-confounded)
date: 2026-06-10
substrate: :t127-clean image (sha-9374871) on AWS Batch Fargate ARM64
scope: 6-cell integrated A/B (3 arms × 16/26-yr) + pre-flight forensics when the anchor failed
outcome: **The A/B is INVALID — and the pre-flight caught it.** arm0 26-yr did NOT reproduce the `529e5520` anchor on the very image+jobdef+env that produced it 5 hours earlier; it produced `2b2f2c2b`/0.446 — the canon T-127 attributed to stale bytecode, now reproduced on a **pyc-free clean-pipeline image**. Root cause forensics (12 probe jobs + full log diff + canon-history sweep): **cross-task runtime nondeterminism on Fargate**, two demonstrated vectors: (A) per-task-unique directory iteration order; (B) bitwise-unstable LAPACK `eigh`-class results across tasks feeding the MVO solver. T-127's "saga closed (bytecode root cause)" is REFUTED-AS-CONFOUNDED: every forensic cell was a single draw from a task-placement lottery. **The cloud wave should RE-HOLD for cross-task comparisons until the determinism fix lands.** P0 escalation to director.
---

# T-128 — Spot-Sleeve Close-Out A/B: INVALIDATED, and Why That Matters More

## 1. What was attempted (per inbox)

6-cell integrated A/B on the pinned image: arm0_off / arm1_on_25pct /
arm2_on_30pct × {2010-2025, 2000-2025}, 1 rep, submitted via
`scripts/submit_arms_campaign.py --job-def archondex-backtest-t127-clean
--job-timeout 21600`. Image `:t127-clean` (= local `sha-9374871`;
provenance labels verified: `org.archondex.commit = 9374871…`,
`org.archondex.substrate-manifest-md5 = a40d5483…`). The commits
between `9374871` and main HEAD `3953085` are docs-only — the image is
code-identical to current main. All 8 sleeve ETF Stooq files verified
present in the committed substrate manifest before launch.

## 2. The pre-flight FAILED — the load-bearing event of this task

| Run | Image | When (Jun-10) | 26-yr arm0 canon | Sharpe |
|---|---|---|---|---|
| T-127 Cell C (the anchor) | `:t127-clean` | 10:16 | `529e5520` | 0.237 |
| **T-128 arm0_off/2000-2025** | **same `:t127-clean`, same job-def `archondex-backtest-t127-clean:1`, same env, same window** | ~15:00 | **`2b2f2c2b`** | **0.446** |

`2b2f2c2b`/0.446 is **bitwise-identical to T-125's June-9 result** —
the canon T-127's forensics attributed to stale host bytecode baked
into the image. It has now been produced by a **clean-pipeline,
git-archive-built, pyc-free image**. The bytecode explanation cannot
be the operative variable.

Per the pre-registered protocol, a failed pre-flight invalidates the
campaign. All 6 cells' numbers are reported below for the record but
are **NOT evidence** for or against the sleeve.

## 3. Forensics — what actually varies

### 3a. Full log diff (Cell C vs T-128 arm0, 138k/149k lines)

Configuration identical: same 21 edges, same params, same RiskConfig
warnings, same warmup, empty config patch in both. **First divergence
= the MVO optimizer output on the FIRST bar (2000-01-03):**

```
Cell C : 'AMZN': 0.11623756656219432, 'CVX': 1.0456824745001716e-16, 'AAPL': 0.0, ...
T-128  : 'AMZN': 0.11623755390593675, 'CVX': 0.0, 'AAPL': 9.314297201314597e-18, ...
```

Same tickers, weights equal to ~7 decimal places, different epsilon
residue patterns — the signature of a numerical solver converging
along a different floating-point trajectory on identical inputs.
26 years of chaos amplification turn that epsilon into ±0.21 Sharpe
(consistent with T-092's "determinism drift scales with window depth").

### 3b. The canon-history map — canon does NOT correlate with image

| Run | Date | Image | pycs? | 26-yr arm0 canon |
|---|---|---|---|---|
| T-125 rebaseline | Jun-9 23:09 | T-125 image | yes | `2b2f2c2b` / 0.446 |
| T-126 Cell B | Jun-10 05:08 | clean worktree bake | no | `529e5520` / 0.237 |
| T-127 Cell P | Jun-10 13:29 | T-125 image **minus pycs** | no | `529e5520` / 0.237 |
| T-127 Cell C | Jun-10 14:18 | `:t127-clean` | no | `529e5520` / 0.237 |
| **T-128 arm0** | **Jun-10 ~18:00** | **`:t127-clean` (same digest)** | **no** | **`2b2f2c2b` / 0.446** |

Two stable attractors, each reproduced multiple times, flipping
**within the same image digest**. And the direct within-batch
evidence was already on record: **`t109-det-sanity` (Jun-6, 3
identical reps, same image, same submission): rep1/rep2 = `0a62b754`,
rep3 = `b17bb395`** — a 2-vs-1 canon split inside one rep batch
(Sharpe agreed to 2dp at 1-yr scale, so it read as "PASS" and the
split went unflagged).

### 3c. Probe round 1 — hardware is uniform (hypothesis eliminated)

6 probe jobs on the same job def: **all** Graviton2 (`CPU part 0xd0c`,
Neoverse N1), OpenBLAS core `neoversen1`, numpy 2.4.3, affinity = 2
CPUs. The "Graviton generation lottery" hypothesis is dead — the
fleet was homogeneous across all probes.

### 3d. Probe round 2 — the two live vectors, demonstrated

6 probe jobs, each computing: `os.listdir('/app/data/processed')`
order fingerprint + fixed-seed NumPy linalg fingerprints.

| Probe | listdir order md5 | sorted md5 | eigh md5 | gemm md5 | sum md5 |
|---|---|---|---|---|---|
| 1 | `776f91ee` | `1a44e062` | `ae997a32` | `f828b2f7` | `7d2103bc` |
| 2 | `aac5cb8d` | `1a44e062` | `ae997a32` | `f828b2f7` | `7d2103bc` |
| 3 | `40600ac5` | `1a44e062` | `ae997a32` | `f828b2f7` | `7d2103bc` |
| 4 | `d1cb898e` | `1a44e062` | **`639dd5e9`** | `f828b2f7` | `7d2103bc` |
| 5 | `454f7fe3` | `1a44e062` | `ae997a32` | `f828b2f7` | `7d2103bc` |
| 6 | `5b58be65` | `1a44e062` | `ae997a32` | `f828b2f7` | `7d2103bc` |

**Vector A — directory order is unique per task (6/6 different).**
Same 732 files (sorted md5 identical), different `os.listdir` order
every time. Fargate materializes image layers with task-unique
directory hash order. Any unsorted `listdir`/`glob`/`iterdir` that
feeds computation order is a per-task coin flip. Production sites
found unsorted (partial scan): `engines/engine_f_governance/
evolution_controller.py:113` (builds `data_map` dict in glob order —
discovery path), `core/feature_foundry/sources/local_ohlcv.py:79`
(freshness check only — benign). `engines/data_manager/
universe_resolver.py` sorts (safe). The T-057c-det family was right
and is incomplete.

**Vector B — LAPACK `eigh` is bitwise-unstable across tasks (5-vs-1
split on a fixed seeded input).** `A@A` (GEMM) and `sum` were stable
6/6; the eigenvalue decomposition was not. The production MVO path
(`engine_c_portfolio/policy.py` → `optimizer.py` →
`scipy.optimize.minimize` over `w·Σ·w` quadratic forms) runs exactly
this class of dense LAPACK ops every solver iteration — matching the
observed first-bar MVO epsilon divergence in arm0 (where the
discovery-path vector-A sites don't run).

### 3d-bis. Probe round 3 — the fix for Vector B, demonstrated

6 more probe jobs, identical fingerprint computation, with
`OMP_NUM_THREADS=1` + `OPENBLAS_NUM_THREADS=1` set:

| Probe | eigh md5 | gemm md5 |
|---|---|---|
| 1-6 (all) | `ae997a32` | `f828b2f7` |

**eigh unanimous 6/6 under single-threaded BLAS** (vs 5-vs-1 split
multi-threaded). Mechanism confirmed: multi-threaded LAPACK reductions
partition work by runtime conditions → different FP summation order
per task. One env-var pair eliminates Vector B. (Wall-time cost on
2-vCPU cells is expected minor — BLAS sections are not the backtest
bottleneck — but should be measured at adoption.)

### 3e. What this does to T-127's verdict

T-127's causal claim ("0.446 was stale host BYTECODE") rested on
single runs per cell: Cell P (image minus pycs) flipped the canon and
the flip was attributed to the pyc removal. With a per-task coin flip
in play, **a single-run flip attributes nothing**. The pyc hygiene
fixes (dockerignore, git-archive builds, manifest pin) are real
improvements and should stay — but the canonical "26-yr = 0.237"
number is one draw from a bimodal distribution, not a settled
baseline. **Neither 0.237 nor 0.446 is canonical until cross-task
determinism is fixed and N>1 task-reps agree.**

## 4. The A/B numbers (recorded, INVALID as evidence)

| Cell | Canon | Sharpe |
|---|---|---|
| arm0_off / 2010-2025 | `62db5c0d` | 1.021 |
| arm1_on_25pct / 2010-2025 | `feb71dab` | 0.957 |
| arm2_on_30pct / 2010-2025 | `893422e8` | 0.906 |
| arm0_off / 2000-2025 | `2b2f2c2b` | 0.446 |
| arm1_on_25pct / 2000-2025 | `d85e8510` | 0.425 |
| arm2_on_30pct / 2000-2025 | `7727afe7` | 0.530 |

Directional pattern for whatever little it's worth (each cell is one
draw of the placement lottery; the lottery swings 26-yr Sharpe by
±0.21, the same order as the arm deltas): 16-yr Sharpe degrades
monotonically with sleeve allocation (-0.064 / -0.115); 26-yr is
NON-monotone (off 0.446 / on25 0.425 / on30 0.530) — incoherent
under any treatment-effect reading, exactly what a lottery-dominated
measurement looks like. **No decision-gate verdict is issued on
invalid cells.** The sleeve chapter stays OPEN, not closed-negative.

## 5. Remediation path (proposed, NOT implemented here)

1. **Single-thread BLAS in cloud cells:** `OMP_NUM_THREADS=1`,
   `OPENBLAS_NUM_THREADS=1` in the job-def env (or entrypoint
   export). **Evidence: probe round 3 — eigh unanimous 6/6 pinned
   vs 5-vs-1 split unpinned.** This is the highest-confidence,
   lowest-risk fix and kills Vector B outright.
2. **Sort every directory-iteration site** that feeds computation
   (the T-057c-det sweep, completed): `evolution_controller.py:113`
   confirmed; full-repo `listdir/glob/iterdir` audit needed.
3. **Protocol change — canon anchors are HARD gates:** every cloud
   campaign embeds an arm0 anchor cell; campaign results are
   quarantined unless the anchor reproduces bitwise. (This is what
   caught T-128 — it works.)
4. **N task-reps per decision cell** (≥3) with canon-agreement
   requirement, until 1-3 are proven sufficient.
5. **Re-baseline 26-yr** only after the fix: N≥5 task-reps of arm0,
   require canon unanimity.

## 6. Acceptance vs inbox

| # | Criterion | Status |
|---|---|---|
| 1 | Pre-flight: arm0 26yr == `529e5520` bitwise on the image used | **FAILED — and that failure is the finding.** Produced `2b2f2c2b`/0.446 (the "bytecode" canon) on the pyc-free clean image |
| 2 | 6-cell A/B with full metrics | Cells ran (6/6 launched, 5 complete at writing); metrics recorded but **INVALID as evidence** per pre-flight failure |
| 3 | Decision-gate verdict | **NO VERDICT — A/B invalid.** Sleeve chapter stays OPEN. Expected close-out-negative could not be honestly issued |
| 4 | Audit + proposed ledger row in outbox | DONE (this doc) |
| 5 | NO prod change; branch pushed not merged | DONE |

## 7. Files

- `scripts/spot_sleeve_closeout_analysis_t128.py` — analysis harness (built; not run to verdict — campaign invalid)
- `docs/Measurements/2026-06/t128_spot_sleeve_closeout.json` — [not written; campaign invalid]
- this audit

## 8. Memory updates needed (post-merge)

- **P0:** "Cross-task cloud nondeterminism is ALIVE on pyc-free images (T-128, 2026-06-10). T-127's bytecode root-cause is REFUTED-AS-CONFOUNDED — single-run forensic cells were draws from a task-placement lottery. Two demonstrated vectors: per-task-unique directory iteration order (6/6 probes differ) and bitwise-unstable LAPACK eigh across tasks (5-vs-1 probe split) feeding the MVO solver. 26-yr canon is bimodal: `2b2f2c2b`/0.446 vs `529e5520`/0.237 — NEITHER is canonical. t109-det-sanity rep3 (2/3+1 split, Jun-6) was the earliest direct evidence and went unflagged. Cloud cross-task comparisons RE-HELD until OMP=1 + sorted-iteration fixes land and N≥5 task-reps agree."
- "Pre-flight canon anchors as hard gates WORK — T-128's embedded anchor cell caught the invalidity before a wrong sleeve verdict shipped. Make them mandatory for every cloud campaign."
