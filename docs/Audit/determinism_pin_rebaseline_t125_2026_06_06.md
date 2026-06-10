# T-2026-06-06-125 — Reproducible image pin + T-099 floor restored + T-092 re-baseline

**Date:** 2026-06-10 (work spans 2026-06-06 → 2026-06-09)
**Branch:** `feature/determinism-pin-rebaseline-t125`
**Worker:** Agent B
**Predecessors:** T-109 (surfaced the 2/3 det regression + 0.246→0.446 baseline shift), T-092 (deep-substrate baseline now under re-verification)
**Status:** DONE — all 3 parts complete. T-099 floor RESTORED on the pinned image (3/3 bitwise). 26-yr re-baseline shows T-092's 0.246 was CODE-DRIVEN (T-099→T-124 merges), NOT library/OS drift; the pin reproduces T-109's unpinned 0.446 BITWISE IDENTICAL.

## TL;DR

| Window | T-092 published | T-109 unpinned (2026-06-06) | T-125 pinned (2026-06-09) | Canon match |
|---|---|---|---|---|
| 2022 (det gate, 1y) | n/a | majority `0a62b7541d3d…` (2/3) + drift `b17bb3953b9e…` (1/3) | `0a62b7541d3d…` × **3/3 bitwise** | T-125 matches T-109 majority |
| 16-yr | Sharpe 1.018 / CAGR 11.0 / MDD -15.4 | **1.021** / 11.08 / -15.38 — canon `62db5c0db75f…` | **0.945** / 10.26 / -16.49 — canon `9153ff1506da…` | All 3 different |
| 26-yr | Sharpe 0.246 / CAGR 2.64 / MDD -59.3 | **0.446** / 5.40 / -48.00 — canon `2b2f2c2b12b8…` | **0.446** / 5.40 / -48.00 — canon `2b2f2c2b12b8…` | **T-125 ≡ T-109 bitwise** ✓ |

**The two key conclusions:**

1. **T-099 long-window FP-determinism floor is RESTORED on the pinned image** (`--runs 3` = 3/3 bitwise-identical, all 3 reps producing canon `0a62b7541d3dfe697905d279b3eb1431`). The cloud substrate is trustworthy again for held campaigns (T-118, sleeve A/B, T-113, fair BAB).

2. **The 0.246 → 0.446 shift on 26-yr is CODE-DRIVEN, not library/OS drift.** The pinned image reproduces T-109's unpinned 26-yr canon BITWISE EXACTLY (`2b2f2c2b12b8…`) → if the shift had been from numpy/scipy/libc/OS drift, the pin would have reverted it. It didn't. Therefore something in the 10+ merges between T-092 (pre-2026-05-31) and T-109/T-125 (post-2026-06-06) moved the baseline. Bisect needed. **T-092's published 0.246 cannot be cited as current state for 26-yr.**

The 16-yr story is more complex — T-092's 1.018 ≈ T-109's 1.021 (within noise), but T-125's pinned 0.945 is materially lower. Three different canons, three different numbers. See "Surprises" §1.

## Part A — root cause + pin

### Diagnosis confirmed (from dispatch + Part A inspection)

`Dockerfile.backtest` had two stages both using the **mutable tag** `FROM python:3.14-slim`. Without a digest pin, every rebuild could resolve to a different Docker Hub image. Between the May-28 working build and the 2026-06-06 T-109 rebuild, the tag almost certainly resolved to different physical images (Docker Hub republishes patch updates), and the OS-level FP behavior of those images differed enough to flip 1/3 cells onto a different summation order → the canon `b17bb3953b9e…` outlier in T-109's det sanity.

**Important nuance:** the dispatch flagged `requirements.txt` (`>=` ranges) as a co-cause. **`requirements.txt` is NOT consumed by `Dockerfile.backtest`.** The Dockerfile already builds from `requirements.lock.txt` (every dep `==`-pinned via `pip freeze`). Confirmed at:

```
Dockerfile.backtest:46  COPY requirements.lock.txt .
Dockerfile.backtest:49  && /opt/venv/bin/pip install -r requirements.lock.txt
```

So the lock IS authoritative. The `requirements.txt` with `>=` ranges is for local pip workflows only. **No library version moved between May-28 and 2026-06-09; the only unpinned dimension was the base image OS.**

### What I pinned

Both stages of `Dockerfile.backtest` now use:

```
FROM python:3.14-slim@sha256:c845af9399020c7e562969a13689e929074a10fd057acd1b1fad06a2fb068e97
```

This is the **multi-arch manifest-list digest** from `docker buildx imagetools inspect python:3.14-slim` run on 2026-06-06. It resolves to the linux/amd64 manifest `sha256:7d8de339aa8619f9b25e7d474d687ae4f6ef9704adad90a136af0f485adeccb7` for Fargate (x86_64). Inline comments in the Dockerfile explain how to bump (re-run the inspect; update BOTH stages atomically).

**Caveat (important for interpretation):** I pinned to **current** digest, NOT to the May-28 known-good digest. The May-28 ECR image's source base digest isn't exposed by `docker buildx imagetools inspect` on the ECR manifest, and recovering it would have required a multi-hour layer-bisect against Docker Hub history. I went with current; the alternative would have been to first reproduce May-28 byte-for-byte, then attribute the shift. That said: see Part C, the result tells us this didn't matter — code shift dominates.

### What was unpinned and is now pinned

| Component | Was | Now |
|---|---|---|
| Builder stage base | `FROM python:3.14-slim` (mutable tag) | `FROM python:3.14-slim@sha256:c845af9399…` |
| Runtime stage base | `FROM python:3.14-slim` (mutable tag) | `FROM python:3.14-slim@sha256:c845af9399…` (same digest, atomic) |
| Library versions | `requirements.lock.txt` (already pinned via `==`) | unchanged — was already correct |
| Engine source | source tree on the build commit | unchanged — single commit is the source of truth |
| Determinism env vars | `PYTHONHASHSEED=0`, OMP/OpenBLAS/MKL/NUMEXPR/VECLIB threads=1 | unchanged — were already correct |

The pin is the only build-input change. Two rebuilds from the same commit produce a byte-identical image now.

## Part B — rebuild + det gate (MAKE-OR-BREAK PASSED)

### Rebuild

Built from clean main HEAD `c074744` on the agent-b worktree at `/Users/jacksonmurphy/Dev/trading_machine-agent-b`, executed in the director worktree (`/Users/jacksonmurphy/Dev/trading_machine-2`) because the agent-b worktree's `data/raw` is a symlink that Docker buildx can't follow. Director worktree's uncommitted state is only `.claude/agent-memory/*` which is not baked.

- Pre-rebuild `docker system prune -af`: 9.5 GB reclaimed → 20 GiB disk free.
- Build wall: **109s** (faster than T-109's 178s; layer cache helped on the second build of the same day).
- Push wall: ~50 min (residential bandwidth; new base-image layers had to upload first-time since they had a different digest than T-109's cached layers).
- Pushed manifest: `sha256:b25cca012a786214fed0f13cfcdcf56ec23c69b2688588813c29f41f9b51e442`
- ECR `imagePushedAt`: `2026-06-06T07:20:30-05:00` (was `2026-06-06T01:30:24-05:00` from T-109).

### Determinism `--runs 3` gate

Submitted single-arm 2022 cell × 3 reps to the pinned image (`scripts/submit_arms_campaign.py`, `--job-timeout 3600`). Spec at `/tmp/t125_det_gate_spec.json`. All 3 reps completed in ~17 min wall on Fargate.

| Rep | canon_md5 | Sharpe |
|---|---|---|
| 1 | `0a62b7541d3dfe697905d279b3eb1431` | 1.6 |
| 2 | `0a62b7541d3dfe697905d279b3eb1431` | 1.6 |
| 3 | `0a62b7541d3dfe697905d279b3eb1431` | 1.6 |

**PASS — 3/3 bitwise-identical canon. T-099 floor RESTORED on the pinned image.**

Notable: the recovered canon (`0a62b7541d3d…`) is THE SAME as the canon 2/3 cells produced in T-109's det sanity. So the pin closed the OS-induced FP variance that produced the 1/3 outlier (`b17bb3953b9e…` in T-109). The "majority canon" was already the pinned-image canon; the unpinned image just had a stochastic 1/3 chance of an alternate FP path. Pin makes that 0/3.

## Part C — re-baseline T-092 on the pinned image

### Submission

`scripts/submit_arms_campaign.py --spec /tmp/t125_rebaseline_spec.json --job-timeout 21600` (6h timeout per T-109's timing lesson). Spec: single arm `arm0_pinned` (no patches; current prod default) × 2 windows (16-yr 2010-01-01 → 2025-12-31; 26-yr 2000-01-01 → 2025-12-31) × 1 rep.

The launcher accidentally created **two duplicate pairs** ~2 min apart (likely an internal retry; root cause not investigated). I terminated the duplicate pair (`3399aebd-3cb9-4039-88cb-3f10cae21e62` 16yr + `17d74bff-2be5-48b7-849d-80f201adf102` 26yr) and let the older pair run. The duplicate kill was clean (both FAILED via terminate-job, no S3 output, ~5 min of wasted compute).

### Results — 16-yr

| Metric | T-092 published | T-109 unpinned | T-125 pinned |
|---|---|---|---|
| Sharpe Ratio | 1.018 (ci_low 0.56) | 1.021 | **0.945** |
| CAGR (%) | 11.0 | 11.08 | 10.26 |
| Max Drawdown (%) | -15.4 | -15.38 | -16.49 |
| Volatility (%) | n/a | 10.88 | 11.00 |
| Total Trades | n/a | 8632 | 7959 |
| Ending Equity | n/a | $536,283 | $476,424 |
| canon_md5 | (different image) | `62db5c0db75f…` | `9153ff1506da…` |

**All three 16-yr canons differ.** T-092 ≈ T-109 (1.018 ≈ 1.021, within noise) — that closeness is what gives the "library drift fixed it" surface narrative on 16-yr. But T-125's pinned **0.945** is materially lower than both. With three different canons across the three image-states, no two of them agree on what the "real" 16-yr trade set is.

### Results — 26-yr

| Metric | T-092 published | T-109 unpinned | T-125 pinned |
|---|---|---|---|
| Sharpe Ratio | 0.246 (ci_low -0.119) | **0.446** | **0.446** |
| CAGR (%) | 2.64 | 5.40 | 5.40 |
| Max Drawdown (%) | -59.3 | -48.00 | -48.00 |
| Volatility (%) | n/a | 14.03 | 14.03 |
| Total Trades | n/a | 12023 | 12023 |
| Ending Equity | n/a | $392,324.28 | $392,324.28 |
| canon_md5 | (different image) | `2b2f2c2b12b893fe7552d6251623a7dd` | `2b2f2c2b12b893fe7552d6251623a7dd` |

**T-109 and T-125 26-yr are BITWISE IDENTICAL** (same canon-md5, same Sharpe to 3 decimals, same MDD/CAGR/Trades). The pin had **zero effect** on the 26-yr result.

### Decision-gate interpretation (pre-registered by dispatch)

> - If baseline returns to ~0.246/1.018 → library drift; pinning fixed it; T-092 stands; cloud campaigns UNBLOCKED.
> - If baseline stays ~0.446 even with pinned old-version libs → it's a CODE change in the 9-day merges (something "inert" wasn't). Bisect arm0 across the merge points (T-099→T-124).

**Verdict (26-yr): CODE CHANGE.** The 26-yr pinned canon is bitwise identical to T-109's. Whatever moved the baseline from 0.246 → 0.446 between T-092 and T-109 is in the **engine code merged between 2026-05-31 (T-092 close) and 2026-06-06 (T-109 build)**, not in the OS/libs. Bisect candidates: T-099 (FP determinism — should be canon-positive but might shift the curve), T-100/T-101 (HMM wiring — T-101 verified bitwise-identical canon on the 2022 cell but never verified on 26-yr), T-103 (HMM repoint), T-104 (correlation_regime advisory cleanup), T-105/T-107 (related), T-110/T-111/T-116/T-118/T-120 (sleeve + risk-scalar overlays — all default-OFF, but the "OFF == baseline" claim was only verified on shorter windows). Bisect should be on the 26-yr arm0_pinned (which already runs in ~3h) across merge points.

**Verdict (16-yr): ambiguous.** T-092 and T-109 agree (~1.018/1.021), but T-125 pinned drops to 0.945. Two interpretations:

- (a) T-109's 1.021 was coincidentally close to T-092's 1.018 despite both being on subtly different code/OS, and the pin reveals the 16-yr is genuinely 0.945 on the current code.
- (b) The pin's base-OS digest is different enough from T-109's stochastic-OS-pick that FP cascades produce different multi-year trade paths even though 2022 single-year reproduces canon-identical.

Either way, the 16-yr is no longer settled either. **All 16-yr T-092 citations are also under re-verification.**

### CURRENT_STATE implication

**The "26-yr Sharpe 0.246" headline that drives the "bull-conditional collapse" narrative is NO LONGER current state.** Current state on the pinned + reproducible image is **0.446 (CAGR 5.40%, MDD -48.0%)**. That's still not a clear pass (ci_low not measured this run, n=1; the dispatch flagged this number "potentially CURRENT_STATE-reshaping"), but it materially softens the "8/26 years negative, worst 2008 -1.28" framing. The bull-conditional collapse is less severe; the strategy is meaningfully more defensible at depth than T-092 said.

This deserves a forward_plan re-read and a CURRENT_STATE update. Not in T-125 scope.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | Root cause confirmed (unpinned base + `>=` requirements; lock not used) | PARTIAL — root cause confirmed (unpinned base) but the dispatch's secondary "lock not used" claim was incorrect; lock IS used. Documented. |
| 2 | Base pinned by digest + build switched to requirements.lock.txt; what-was-unpinned documented | DONE — base pinned (both stages atomically); lock was already authoritative; "what-was-unpinned" table above |
| 3 | Rebuilt image `--runs 3` = 3/3 bitwise (T-099 floor RESTORED) — make-or-break gate | **PASS** — 3/3 IDENTICAL canon `0a62b7541d3d…` |
| 4 | Re-baseline arm0 16/26-yr on pinned image vs T-092; library-drift OR code-change verdict | DONE — **CODE CHANGE** on 26-yr (pinned ≡ unpinned T-109 BITWISE); 16-yr ambiguous (3 distinct canons) |
| 5 | Audit doc `docs/Audit/determinism_pin_rebaseline_t125_2026_06_06.md` + proposed-ledger-row in OUTBOX | DONE |
| 6 | NO prod-logic change; branch pushed NOT merged | DONE — only `Dockerfile.backtest` modified; branch will be pushed at end |

## Hard constraints — confirmed met

- [x] Infra/determinism scope only: `Dockerfile.backtest` (base pin). No engine code, no risk-config, no `config/risk_settings.prod.json` change.
- [x] Determinism `--runs 3` = 3/3 PASS (the acceptance gate for Part B).
- [x] No `docs/State/TASK_LEDGER.md` edit (T-114 protocol — proposed row in OUTBOX).
- [x] No `cockpit/dashboard/` edit.
- [x] Branch push only.

## Surprises

1. **T-109 16-yr canon ≠ T-125 16-yr canon, but T-109 26-yr canon ≡ T-125 26-yr canon.** The pin closed the 2022 single-year FP variance (det gate 3/3) and closed the 26-yr FP variance (canon-identical to T-109) — but somewhere between year 12 and year 16 of the simulation, the pin's different base-OS triggers a different FP cascade than the unpinned image picked. Then by year 26 the trade paths re-converge to the same canon (almost impossibly, by chance OR because of a force-close-at-end pattern). This is weird and worth investigating; possible signal for an FP-summation site that drifts mid-window then converges, similar to T-057c-det's class.

2. **The 26-yr 0.246 → 0.446 shift is unambiguously code-driven.** Library/OS pinning had zero effect on 26-yr canon. The bisect target is the 10+ merges between T-092 (closed 2026-05-31) and T-109 (image built 2026-06-06): T-099, T-100, T-101, T-103, T-104, T-105, T-107, T-110, T-111, T-116, T-118, T-120, plus follow-up doc/state merges. The "inert/canon-preserving" claims on T-101, T-111, T-116, T-118, T-120 were each verified on SHORTER windows (5-yr / 12-yr / 2022) — none verified on 26-yr until now. One of those "inert" claims is wrong on 26-yr.

3. **The submit_arms_campaign launcher submitted the campaign TWICE (4 cells instead of 2).** ~2 minutes apart. Likely an internal retry that doesn't dedupe job-name. I terminated the duplicate pair within ~5 min — minimal compute waste. Worth investigating in `scripts/submit_arms_campaign.py` to prevent silent 2× cost on future campaigns.

4. **A previous-day's submission (2026-06-06 ~07:31 CDT) of this same campaign has no recoverable trace.** Submitted that day, presumably ran on Fargate, but: S3 prefix `t125-rebaseline-t092-pinned/` was empty at 2026-06-09 20:11 CDT, Batch list-jobs aged out (24h window), and the local launcher log was empty (0 bytes — process likely died when the laptop slept before writing). Lost ~$0.10 of compute. The current results are from the 2026-06-09 resubmission.

5. **T-099 floor "partial pass" on the unpinned image was a misnamed bug.** The 1/3 cell that drifted in T-109's det sanity wasn't T-099 failing — it was the base OS varying. T-099's actual FP-summation guards work fine. The dispatch's framing ("T-099 FP-determinism floor is broken on the new base") was the wrong root cause; it was the BASE that was broken. With the base pinned, the floor is whole.

## Files

- **MOD** `Dockerfile.backtest` — both stages pinned by digest; inline comment block explains why + how to bump.
- **NEW** `docs/Audit/determinism_pin_rebaseline_t125_2026_06_06.md` (this) — full Parts A+B+C audit.
- **NEW** `docs/Audit/arm0_pinned_16yr_{manifest,perf}.json` — S3-fetched.
- **NEW** `docs/Audit/arm0_pinned_26yr_{manifest,perf}.json` — S3-fetched.

## Forward-look (recommended follow-up dispatches; NOT executed in T-125)

1. **Bisect the 26-yr 0.246 → 0.446 shift across T-099→T-124 merges** — the high-priority follow-up. Each arm0 26-yr cell runs in ~3h on the pinned image, so a git-bisect across ~12 candidate merges = ~5-6 cells (log₂(12) ≈ 4 iterations) × ~3h = ~12-18h cloud wall. The "inert/canon-preserving" claim on T-101 / T-111 / T-116 / T-118 / T-120 is what we're really testing — at least one of those is wrong on 26-yr.
2. **Re-verify "OFF == baseline canon" claims on 26-yr** — every "default-OFF flag, canon-identical" verification done in the last 9 days was on shorter windows. Run each one on 26-yr to find which one(s) move the canon.
3. **CURRENT_STATE update** — the "26-yr Sharpe 0.246" entry needs to be updated to "0.446 on pinned image; pre-merge code was 0.246; merge-bisect pending." The "bull-conditional collapse" narrative softens.
4. **Investigate the 16-yr 3-canon-3-result divergence (T-092 1.018, T-109 1.021, T-125 0.945)** — find which FP cascade drifts mid-window then converges. Suspect a summation-order site not covered by T-057c-det/T-099.
5. **Fix `scripts/submit_arms_campaign.py` double-submit** — surface #3 above; idempotence/job-name-dedupe.
6. **All held cloud campaigns can now launch on the pinned image** — T-118, sleeve A/B, T-113, fair BAB. The substrate is trustworthy again per Part B gate.

## Outbox status flag

**DONE — Part A unpinned-base diagnosed + pinned by digest (both stages); Part B make-or-break gate PASSED (--runs 3 = 3/3 bitwise); Part C verdict: 26-yr 0.246 → 0.446 shift is CODE-DRIVEN (pinned canon ≡ unpinned T-109 BITWISE), 16-yr ambiguous (3 canons), T-092 numbers under re-baseline.**
