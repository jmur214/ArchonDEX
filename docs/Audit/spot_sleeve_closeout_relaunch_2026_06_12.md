---
task_id: T-2026-06-11-157-relaunch (sleeve A/B close-out on published anchors)
title: Sleeve A/B relaunch on T-155 anchors — A/B INVALID (16-yr anchor gate FAILED); the published anchors are NOT durable (P0)
date: 2026-06-12
substrate: image sha-5323a3c (arm64), job def archondex-backtest-t155-anchor:3, substrate 553edca7 — the T-155-certified "9/9 bitwise-unanimous" anchor environment
scope: pure measurement (sleeve flag in arm config_patch only; no engine/flag changes); the relaunch the director fired after T-155 published anchors
outcome: "**A/B INVALID + P0 ESCALATION.** The relaunch caught the published anchors FAILING to reproduce on their own certified image/job-def. arm0_off 16-yr drew `9153ff15`/0.945 — the MINORITY attractor — not the published anchor `62db5c0d`/1.021 (gate FAIL). The 2022 canary split 2-vs-1 (`0a62b754`×2, `0c6b8811`×1). arm0_off 26-yr DID reproduce its anchor (`529e5520`/0.237, gate PASS). Cross-check vs the original T-128 cells: 3 of 6 reproduced BITWISE across two different images and two days; 3 flipped — pure per-task lottery, image-independent. Mechanism BOUNDED: fleet 8/8 uniform Graviton2; eigh microbench 8/8 bitwise; SLSQP microbench 6/6 bitwise; MVO universe order sorted (identical keys across split reps) — every isolated culprit RULED OUT. The residue is FP-dust in the full-pipeline cov()→MVO output on zero-weight names, surviving the T-140 thread pins. T-155's 9/9 unanimity was a fortunate draw, not proof of determinism. The sleeve question CANNOT be closed on this substrate; relaunches fired on these anchors (C's T-118 overlay) are at risk."
---

# Sleeve A/B Relaunch — the anchors didn't hold

## 1. What was asked vs what happened

The director cleared the gate (T-155 Part 3: image `sha-5323a3c`, job def
`archondex-backtest-t155-anchor:3`, "9/9 bitwise-unanimous, canon
continuity every window") and fired the sleeve A/B relaunch with a
standing HARD anchor gate: in-campaign arm0 must reproduce 26-yr
`529e5520`/0.237 and 16-yr `62db5c0d`/1.021.

**The anchor gate FAILED on the 16-yr window.** The relaunch is the
control that caught the certified anchors not being durable.

## 2. Results (9 cells: 6 A/B + 3 canary)

| Cell | Canon | Sharpe | Anchor | Gate |
|---|---|---|---|---|
| arm0_off / 26-yr | `529e5520` | 0.237 | `529e5520`/0.237 | **PASS** ✓ |
| arm0_off / 16-yr | **`9153ff15`** | **0.945** | `62db5c0d`/1.021 | **FAIL** ✗ |
| arm1_on_25pct / 26-yr | `d85e8510` | 0.425 | — | — |
| arm1_on_25pct / 16-yr | `feb71dab` | 0.957 | — | — |
| arm2_on_30pct / 26-yr | `638a8435` | 0.356 | — | — |
| arm2_on_30pct / 16-yr | `893422e8` | 0.906 | — | — |
| canary 2022 rep1 | `0c6b8811` | 1.603 | `0a62b754` | minority |
| canary 2022 rep2 | `0a62b754` | 1.600 | `0a62b754` | majority |
| canary 2022 rep3 | `0a62b754` | 1.600 | `0a62b754` | majority |

arm0 16-yr landed on the `9153ff15`/0.945 family — the minority
attractor B identified (vs the `62db5c0d`/1.021 anchor). The canary
split 2-vs-1 at 1-yr scale. Nondeterminism is live on the certified
image.

## 3. The cross-check that proves it's the lottery (not the image)

Original T-128 (2026-06-10, image `t127-clean`, NO thread pins) vs this
relaunch T-128b (2026-06-12, image `sha-5323a3c`, WITH pins):

| Cell | T-128 | T-128b | Reproduced? |
|---|---|---|---|
| arm0 16-yr | `62db5c0d`/1.021 | `9153ff15`/0.945 | **FLIP** |
| arm1 16-yr | `feb71dab`/0.957 | `feb71dab`/0.957 | SAME (bitwise) |
| arm2 16-yr | `893422e8`/0.906 | `893422e8`/0.906 | SAME (bitwise) |
| arm0 26-yr | `2b2f2c2b`/0.446 | `529e5520`/0.237 | FLIP |
| arm1 26-yr | `d85e8510`/0.425 | `d85e8510`/0.425 | SAME (bitwise) |
| arm2 26-yr | `7727afe7`/0.530 | `638a8435`/0.356 | FLIP |

**3 of 6 cells reproduced BITWISE across two different images on two
different days; 3 flipped.** The cells that reproduced did so
bitwise across *different images* — canon is image-independent
(T-127's bytecode theory remains dead) and the flips are pure
per-task lottery draws. arm0 flipped in BOTH windows; arm1 was a rock
in both. This is the lottery in its cleanest demonstration: identical
config, identical image semantics, different canon per task.

## 4. Mechanism — every isolated culprit ruled out (18 probe jobs)

On the certified job def `archondex-backtest-t155-anchor:3`:

| Probe | n | Result | Conclusion |
|---|---|---|---|
| CPU part / OpenBLAS core | 8 | **8/8** `0xd0c` Neoverse-N1 (Graviton2), core `neoversen1` | Fleet UNIFORM — not hardware heterogeneity |
| `eigh` on fixed seeded matrix, single-thread | 8 | **8/8** bitwise `ae997a32` | The eigh kernel is deterministic (T-140 pins hold) |
| `scipy.optimize.minimize` SLSQP on fixed QP, single-thread | 6 | **6/6** bitwise `b1ade87c`, nit 37 | The MVO solver is deterministic in isolation |
| MVO universe ordering (from `resolve_universe`) | — | `sorted(set(...))`; MVO log keys identical across split reps | Input column order is NOT the source |

The MVO-target log of the two split canary reps diverges only in
floating-point dust on zero-weight names (`BKNG: 3.73e-17` vs `0.0`;
`BSX: 1.14e-18` vs `3.73e-17`) — the real allocation weights agree to
~15 digits. That dust occasionally tips a downstream rounding /
min-notional / whole-share threshold and flips a single trade, which
the canon (md5 over trades.csv) records, and the flip compounds over
the window.

**The residue lives in the full-pipeline `returns_df.cov() → MVO`
path, not in any isolated kernel.** The T-140 thread pins genuinely
fixed Vector B (the eigh/SLSQP kernels are now deterministic, proven
8/8 + 6/6) but a residual nondeterminism source in the assembled
pipeline survives them. Naming the exact site needs a dedicated
determinism dispatch — the microbenchmark approach has exhausted the
obvious culprits and the next step is bisecting the live cov/MVO call
inside a real run (capturing the Sigma matrix bytes per task).

## 5. Why T-155 got 9/9 and this relaunch did not

Each cell has some modest probability `p` of drawing the minority
attractor. T-155's 9 cells all landing majority is plausible at
small-to-moderate `p`; a later batch catching a 2-vs-1 canary plus a
16-yr minority draw is the same `p` showing its tail. **T-155's 9/9
was evidence consistent with determinism, but not proof of it — a
single batch of unanimous draws cannot distinguish "p=0" from "p small."
The standing N≥5-per-window-unanimity rule is exactly the right gate;
it simply needs to be applied to the arm0 anchor in EVERY campaign
(which the relaunch did, and which is how this was caught).**

## 6. The sleeve verdict (what can and cannot be said)

- **16-yr: INVALID.** arm0 is on the wrong attractor (0.945 vs the
  1.021 anchor). Against the drawn baseline, on25 0.957 reads +0.012;
  against the true anchor it reads −0.064. The delta's sign is
  unresolvable — exactly the lottery confound the anchor gate exists
  to catch.
- **26-yr: arm0 anchor PASSED (0.237), but arm1/arm2 are single
  lottery draws** (arm2 26-yr flipped canon vs T-128). Face value:
  on25 0.425, on30 0.356 both exceed the 0.237 baseline (+0.19, +0.12)
  — directionally consistent with the T-108/T-115 "crisis-era help"
  thesis, but NOT gated (each arm needs N≥5 unanimity; the substrate
  isn't delivering it).
- **Net: the sleeve question CANNOT be closed on this substrate.** The
  honest close-out is blocked not by the sleeve's economics but by the
  substrate's nondeterminism. The sleeve chapter stays OPEN.

## 7. Blast radius (P0)

- **The published anchors are not durable.** Relaunches the director
  fired on `sha-5323a3c` / `t155-anchor:3` — C's T-118 overlay
  campaign (the de-gross headline experiment) foremost — inherit this
  risk. Any cross-arm verdict from those campaigns needs its own
  in-campaign arm0 anchor check; if arm0 drew the minority attractor,
  the arm deltas are confounded exactly as here.
- **What survives:** within-task results (any single cell's internal
  consistency); the T-140 pins' fix of the eigh/SLSQP kernels (proven
  still holding); all local work. The 26-yr anchor `529e5520`/0.237
  reproduced and is corroborated (T-127, T-128b) — the 26-yr baseline
  is solid. The 16-yr anchor `62db5c0d`/1.021 is the majority but is
  NOT bitwise-durable per task.

## 8. Recommendation

1. **Do not treat the T-155 anchors as a deterministic substrate for
   cross-arm verdicts** until the residual full-pipeline source is
   found and fixed. Re-hold cross-task/cross-arm cloud comparisons (the
   within-cloud caveat from T-158/T-162 is now sharper: even
   within-cloud, same-config canon is not guaranteed per task).
2. **Dedicated determinism dispatch (T-140-followup-2):** capture the
   `Sigma` matrix bytes + the SLSQP input/output per task inside a real
   run across N tasks; bisect where the FP-dust enters the assembled
   pipeline (prime suspects: `returns_df.cov()` reduction, NaN-fill
   ordering, or a pandas/numpy reduction not covered by the BLAS
   thread pins). The microbenchmarks have ruled out the kernels in
   isolation — the bug is in composition.
3. **Sleeve A/B re-runs only after** the substrate delivers
   N≥5-per-window arm0 unanimity. The harness + spec are staged and
   ready.

## 9. Files

- `data/cloud_runs/t128b-sleeve-closeout-relaunch_*.json` (9 cells; local + S3 `t128b-sleeve-closeout-relaunch/`)
- 18 probe job logs in CloudWatch `/aws/batch/job` (hw ×8, slsqp ×6, the earlier hw set; job names `t128b-hwprobe-*`, `t128b-slsqp-*`)
- this audit

## 10. Memory updates needed (post-merge)

- "Sleeve A/B relaunch (2026-06-12): the T-155 published anchors are
  NOT durable — on the certified image `sha-5323a3c`/jobdef
  `t155-anchor:3`, arm0 16-yr drew the MINORITY attractor
  `9153ff15`/0.945 (anchor is `62db5c0d`/1.021), canary split 2-vs-1.
  26-yr arm0 reproduced (`529e5520`/0.237). Cross-check vs T-128: 3/6
  cells reproduced bitwise across two images/days, 3 flipped = pure
  per-task lottery, image-independent. Mechanism BOUNDED: fleet 8/8
  uniform Graviton2, eigh 8/8 + SLSQP 6/6 microbench unanimous, MVO
  order sorted — residue is full-pipeline cov()→MVO FP-dust surviving
  the T-140 pins. T-155's 9/9 was a lucky draw, not proof. Sleeve
  question can't be closed on this substrate; C's T-118 overlay + any
  relaunch on these anchors inherit the risk. Needs a determinism
  dispatch that bisects the assembled cov/MVO path (kernels already
  cleared)."
