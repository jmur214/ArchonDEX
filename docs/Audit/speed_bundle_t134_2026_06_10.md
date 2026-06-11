# T-2026-06-10-134 — Speed bundle (re-sequenced mid-task by the T-128 addendum)

**Date:** 2026-06-10
**Branch:** `feature/speed-bundle-t134`
**Worker:** Agent B
**Scope note:** the original 5-part brief was re-sequenced by the inbox ADDENDUM after A's T-128 forensics (cross-task placement lottery): **Parts B/C/E executed; Part A code shipped but rep-defaults REVERTED + HELD; Part D data collected but verdict DEFERRED.** Entrypoint/job-def env untouched (A owns them in T-140).

## TL;DR — multipliers achieved

| Part | Result | Multiplier |
|---|---|---|
| B — parallelism | **maxvCpus 8 → 100, self-service** (the "quota wall" was our OWN compute environment, not an AWS account quota; no Service Quotas ticket needed). Empirically working: 14 concurrent cells running, 0 queued, within minutes of the change. | **up to ~12× campaign wall** (52-cell grid: was ceil(52/8)=7 waves → now ~1 wave) |
| C — cache decision | 26-yr cell = **99.0% sim loop / 0.8% load / 0.3% tail** → substrate/feature S3 cache attacks 0.8% of wall = **NO-GO** (the honest negative the dispatch pre-authorized). The profile DID find the real loop composition: **~52% of wall is yfinance network fallback** inside the signal path + a **~logger-drain block** at post-run — two cheap follow-up targets worth ~2× wall, flagged propose-first (they are code changes). | cache: 0×; flagged follow-ups: ~2× potential |
| A — reps→1 + canary | HELD per addendum. Canary machinery shipped + verified end-to-end (cross-task 3/3 bitwise `0a62b754…` on the 2022 reference); rep defaults REVERTED to spec-required/3 until T-140. | (deferred ~3-5× — becomes valid post-T-140) |
| D — slice-vs-native | HELD per addendum (cross-task comparison meaningless under the lottery). Slice methodology validated + slice metrics computed; native-16 cell stored for post-T-140 re-use. | (deferred ~2.3× on multi-window campaigns) |
| E — snapshot | `s3://archondex-results-407539788432/substrate/147e9d0e781ca79eecd716b116f52d10/` — 14,027 objects / 2.78 GB, mirrors the T-131 manifest scope (live governor files excluded). T-131's residual closed. | (hygiene) |

**Next campaign's wall-time estimate vs today's 8-14 h:** a 52-cell single-rep grid at 100 vCPUs ≈ the longest single cell (~2.5-4 h) instead of 7 serialized waves — **~3-4 h now from Part B alone**, before any of the held/deferred multipliers land.

## Part B — the parallelism wall was ours, not AWS's

- `aws batch describe-compute-environments`: `archondex-fargate` had **`maxvCpus: 8`** with 1-vCPU jobs → exactly T-053b's "8 ran, 2 queued". The account-level Fargate quota was never the binding constraint (service-quotas API is denied to our IAM user, but irrelevant — the CE cap bound first).
- `aws batch update-compute-environment --compute-resources maxvCpus=100` — live immediately. **Observed: 14 jobs RUNNING / 0 RUNNABLE within minutes** (C's campaign + this task's cells concurrently; previously hard-capped at 8).
- Total compute cost unchanged (same cell-hours, less wall). The $20/month billing alarm remains the cost guard. If a future campaign actually saturates 100 concurrent vCPUs and queues, THEN file the Service Quotas request (needs console access; CLI user lacks `servicequotas:*`).

## Part C — profile → cache NO-GO + the real loop composition

### Phase timing (free — CloudWatch timestamps of the existing T-127 clean 26-yr cell, job `2ab72ccc`)

| Phase | Wall | Share |
|---|---|---|
| container start → first sim bar (substrate load + edge init) | 111 s | **0.8%** |
| sim loop (6,538 bars) | 14,409 s | **99.0%** (2,204 ms/bar) |
| metrics + block-bootstrap + S3 upload | 36 s | 0.3% |
| TOTAL | 14,557 s (4.04 h) | |

**Cache decision: NO-GO.** The dispatch's rule was explicit: sim-loop-dominated → do not build the cache. An S3 feature/substrate cache addresses the 0.8% load phase; even a perfect cache saves ~2 minutes of a 4-hour cell. Documented and stopped, per the brief.

### Inside the loop (cProfile, 1-yr cell in-container, 432 s wall under profiler)

- `_generate_signals` → `alpha_engine.generate_signals` → `signal_collector.collect`: **352 s cumulative (≈88% of the backtest run)**; 5,478 edge-calls at ~55 ms each.
- **`yfinance/utils.py:89(wrapper)`: 224 s — ~52% of total wall.** Several edges (`earnings_vol_edge`, `dividend_initiation_drift_v1`, `leaps_catalyst_edge`, `fundamental_value`) call yfinance inside the signal path; in cloud/container cells these hit the network per edge-call and "degrade gracefully" (= retry/timeout burn). This is the known yfinance-fallback issue (silent-bug audit 2026-05-31) showing up as the single largest compute component. Canon determinism is unaffected (proven elsewhere) — meaning whatever these calls return does NOT change trades, i.e. **the system pays half its compute for calls whose results are discarded or redundant.**
- **Logger drain:** the main thread spends its post-run blocked in `cockpit/logger.close → threading.join` waiting for the print-queue writer to drain (the per-bar `[DEBUG_SNAPSHOT_PAYLOAD_PRE_LOG]` + per-fill print storm; also CloudWatch ingest cost).
- **Numerical compute is NOT the bottleneck.** The loop's wall is I/O-shaped: network fallback + logging.

### Follow-up targets flagged (propose-first — they are code changes, out of T-134's "no backtest behavior change" scope)

1. **Kill/no-op the yfinance fallback in backtest context** (env flag or offline mode): potential **~2× wall** on every cell, zero canon impact expected (verify with canon A/B).
2. **Demote the per-bar DEBUG print storm** (config-gated): faster drain, smaller CloudWatch bills, less logger-join tail.

## Part A — shipped machinery, HELD defaults (addendum compliance)

- **Shipped + kept:** canary machinery in `submit_arms_campaign.py` — `build_canary_cells()` (3 reps × 1-yr × first arm, riding along every campaign), `check_canary()` (loud UNTRUSTED verdict + exit 2 on divergence), `--no-canary` + `--reps` CLI. **Each canary rep is its own Batch task → the canary is already CROSS-TASK**, which is exactly the shape the addendum wants post-T-140 (upgrade = raise N + treat unanimity as gate).
- **Verified end-to-end live:** `t134-canary-verify` campaign (4 cells, 495 s wall) → canary **3/3 bitwise `0a62b7541d3d…`** (the established 2022 reference). One bug found+fixed in my own check (read `cell.manifest["canon_md5"]`, not a nonexistent attribute — first run printed a false FAIL with `canon=None`).
- **REVERTED per addendum:** rep defaults. `submit_substrate_run.py` back to `--reps` default 3; `submit_arms_campaign.py` back to `reps` spec-required. In-code comments document the HOLD and the T-140 unblock condition.
- **Honest reinterpretation note:** under T-128's placement-lottery finding, my T-109 det-sanity 2/3-vs-1/3 split — which T-125/T-127 attributed to the unpinned base — may instead have been the lottery. T-127's pyc mechanism conclusion still stands on its controlled content-identical image pairs, but cross-task canon agreement (T-125 3/3, T-127 3-builds-1-canon, today's canary 3/3) now carries attractor-luck variance until T-140 pins threads + sweep order. A's re-baseline supersedes where they conflict.

## Part D — HELD; data banked for post-T-140

- **Slice methodology validated:** recomputing full-26-yr metrics from the cell's `portfolio_snapshots.csv` reproduces the published numbers exactly (Sharpe 0.237 / CAGR 2.51 / MDD -59.29) — the slicing harness itself is sound.
- **2010-2025 slice of the 26-yr run:** Sharpe **0.600** / CAGR **5.99%** / MDD **-18.91%** (4,024 bars; 3,835 of 8,279 trades; slice-local running peak for MDD).
- **Native 16-yr cell** (`t134-speed/native16/16yr/rep1`, job `f0c2a3a2`, same `:t127-clean` image): left to complete (sunk cost); result stored in S3 for the post-T-140 comparison. **No verdict drawn** — the comparison is cross-task and therefore meaningless under the lottery. Pre-registered tolerance (|ΔSharpe| < 0.05) stands for whoever re-runs the comparison on T-140-fixed substrate.
- Early read for expectations-setting only: prior 16-yr numbers (all provenance-imperfect) sat ~0.95-1.02 vs slice 0.600 — if that pattern survives T-140, slicing will FAIL the tolerance decisively (warm-up state + capital-scale-dependence, per T-121). That would be the honest "stop wondering" outcome the dispatch named.

## Part E — fresh snapshot

`substrate/147e9d0e781ca79eecd716b116f52d10/`: 14,027 objects / 2.78 GB (manifest-scoped: live governor files excluded, anchors included; manifest itself uploaded alongside). The old `a40d5483…` prefix remains for provenance but is superseded.

## Acceptance vs (re-sequenced) dispatch

| Criterion | Status |
|---|---|
| reps→1 + canary, canary verified | HELD per addendum — canary shipped + verified 3/3; rep defaults reverted; unblock = T-140 |
| Quota increase filed + documented | DONE differently — the wall was our CE's maxvCpus=8; raised to 100 self-service; empirically working (14 concurrent) |
| Cell profile + cache GO/NO-GO | DONE — 99.0% sim-loop → **NO-GO**; loop composition: 52% yfinance fallback + logger drain; 2 follow-ups flagged propose-first |
| Slice-vs-native verdict | HELD per addendum — methodology validated, slice metrics banked, native cell stored, tolerance pre-registered for post-T-140 |
| Fresh S3 snapshot under 147e9d0e | DONE — 14,027 objects |
| Audit + ledger row in outbox; branch pushed not merged | DONE |

## Hard constraints — confirmed

- [x] No behavior change to the backtest; launcher/infra/profiling only (and the launcher REP DEFAULTS were restored per addendum).
- [x] Entrypoint/job-def env untouched (A owns them in T-140).
- [x] C's running campaign undisturbed — except positively (maxvCpus raise).
- [x] No TASK_LEDGER write; branch push only.

## Files

- **MOD** `scripts/submit_arms_campaign.py` — canary machinery (`build_canary_cells`, `check_canary`, `--reps`/`--no-canary`); reps stays spec-required (HOLD documented in-code).
- **MOD** `scripts/submit_substrate_run.py` — `--reps` default restored to 3 with the HOLD note.
- **NEW** `docs/Audit/speed_bundle_t134_2026_06_10.md` (this).
- (Infra, not in-branch: `archondex-fargate` maxvCpus 8→100; S3 `substrate/147e9d0e…/` snapshot.)

## Forward-look

1. **T-140 lands → un-hold Part A:** flip reps default to 1 + upgrade the canary to the campaign gate (it's already cross-task; raise N to ≥3 distinct tasks and require unanimity — the code shape is ready).
2. **T-140 lands → re-run Part D's comparison** (native-16 result is banked; only the verdict was deferred).
3. **yfinance-fallback kill switch** (propose-first): ~2× wall on every cell.
4. **DEBUG print-storm demotion** (propose-first): logger drain + CloudWatch cost.
5. If a campaign saturates 100 vCPUs: file the Service Quotas increase (console access required).
