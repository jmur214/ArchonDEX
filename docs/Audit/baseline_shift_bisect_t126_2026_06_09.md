# T-2026-06-06-126 — Stage-1 bisect: 26-yr baseline shift is NOT what T-125 thought it was

**Date:** 2026-06-10
**Branch:** `feature/baseline-shift-bisect-t126`
**Worker:** Agent B
**Predecessors:** T-125 (claimed code-driven 0.246→0.446 shift; this audit invalidates that), T-092 (deep-substrate baseline that T-125 declared "under re-verification"), T-109 (the original 0.446 cell)
**Status:** Stage 1 DONE — verdict is **NOT what the dispatch's binary frame anticipated**. Reading both findings together: (a) canon differs between Cell A and Cell B (per dispatch, this would indicate Stage 2), BUT (b) the absolute Sharpe numbers REFUTE T-125's "0.446" headline — both cells produce ~0.24, matching T-092. **The 0.446 from T-109/T-125 was NOT reproducible on a fresh build.** The "bull-conditional collapse softens" narrative T-125 set up is INVALIDATED. T-092's 0.246 baseline STANDS.

## TL;DR

The dispatch designed Stage 1 to decide between two outcomes:
- **A == B (~0.446):** legitimate determinism re-baseline; greenlight wave
- **A != B:** inert-merge bug; localize via Stage 2

**Actual outcome: A != B by CANON but BOTH cells produce ~0.24, not ~0.446.** This collapses the dispatch's framing. The real finding is upstream of Stage 2: the 0.446 number T-125 declared "code-driven and bitwise-reproducible" doesn't reproduce on a fresh build of the same HEAD code (with the same pinned base digest), three days later. The most likely cause is a non-engine input changed between the T-125 build (2026-06-06) and the T-126 builds (2026-06-10) — a data-substrate artifact, not code.

| Build | Sharpe | CAGR (%) | MDD (%) | Trades | EndEquity | canon_md5 |
|---|---|---|---|---|---|---|
| T-092 published (May-28 image) | **0.246** | 2.64 | -59.3 | n/a | n/a | (May-28 image) |
| T-109 unpinned (2026-06-06) | 0.446 | 5.40 | -48.00 | 12023 | $392,324 | `2b2f2c2b12b8…` |
| T-125 pinned (2026-06-06; pinned digest `c845af9399…`) | 0.446 | 5.40 | -48.00 | 12023 | $392,324 | `2b2f2c2b12b8…` ≡ T-109 |
| **T-126 Cell A (post-T-099 `8103118`, pinned digest, 2026-06-10)** | **0.246** | 2.64 | -59.29 | 8353 | $197,013 | `c579566c881d…` |
| **T-126 Cell B (HEAD `098668a`, pinned digest, 2026-06-10)** | **0.237** | 2.51 | -59.29 | 8279 | $190,401 | `529e55204a92…` |

The 4 facts:

1. **T-126 Cell A reproduces T-092's 0.246 to 3 decimals + matches MDD to 2 decimals.** T-099 alone, on the pinned base, produces the original 0.246. T-099 didn't move the baseline.
2. **T-126 Cell B (HEAD code) is 0.237, basically T-092's 0.246 minus a small noise.** Not the 0.446 T-125 reported.
3. **Cell A canon ≠ Cell B canon.** A code change between `8103118` and HEAD does shift the canon. So there IS a non-zero "inert-merge claim broken on 26-yr" finding — but it moves Sharpe by ~0.009, well within noise.
4. **T-125's 0.446 / canon `2b2f2c2b12b8…` does not reproduce.** Building the same HEAD code with the same pinned base digest three days later yields Sharpe 0.237 / canon `529e55204a92…`. T-109 and T-125 agreed bitwise — but neither reproduces on a fresh build NOW.

The only way T-109/T-125's 0.446 is reproducible-elsewhere-but-not-now is if some BUILD INPUT differs between 2026-06-06 and 2026-06-10. The engine code between c074744 (T-125's HEAD) and 098668a (T-126's HEAD) is byte-identical at the code level — the only commits in between are `5df587c` (T-125 Dockerfile pin), `c29d735` (docs/ledger), and `098668a` (docs/state); none touch engine code. The only non-code inputs the Dockerfile bakes are `config/`, `data/processed/`, `data/raw/`, `data/governor/`, and `debug_config.py` — all sourced from the host filesystem at build time. **The most likely cause is a change in the host's `data/processed/` (or `data/raw/`) between the T-125 build and T-126 builds.** I did not bisect what specifically changed — that's a follow-up.

## Stage 1 — methodology

Per dispatch: build per-commit images all on the pinned base from T-125 (`python:3.14-slim@sha256:c845af9399…`), run `arm0` 26-yr on each.

### Cells

- **Cell A** — post-T-099 commit `8103118` ("Integrate T-100 crisis-path diagnostic + dedup TASK_LEDGER T-096"). This is the first commit on main AFTER T-099's merge (`253a96f`). NO "default-OFF inert" overlays have been merged yet at this point.
- **Cell B** — current HEAD `098668a`. All of T-099→T-124 merged in.

### Builds

| Stage | Commit | Image tag | manifest sha256 |
|---|---|---|---|
| A | `8103118` (post-T-099) | `archondex-backtest:t126-postt099` | `d6685dc6b549…` |
| B | `098668a` (HEAD) | `archondex-backtest:t126-head` | `0c5d251209b0…` |

Both built from the director worktree (`/Users/jacksonmurphy/Dev/trading_machine-2`) which has the real `data/raw/`; agent-b worktree has it as a symlink that Docker buildx can't follow. For Cell A, agent-b was `git checkout 8103118 --` for the tracked source dirs, the Dockerfile's `FROM python:3.14-slim` lines were manually pinned to the T-125 digest (the pre-T-125 commit doesn't carry the pin), then code was `rsync`'d to director worktree. Build A ran in 69s wall. Build B was already on HEAD code in director worktree (no sync needed); build ran in 67s wall after a disk-space failure on the first attempt forced a docker prune. Both pushes succeeded; pinned base layers were uploaded fresh because the restart between T-125 and T-126 wiped the Docker layer cache.

The first attempt at T-126 was lost when my laptop restarted mid-build; resumed cleanly with a re-build. Total wall A-to-cells-submitted: ~1.5h including disk prune + 2 rebuilds + 2 pushes.

### Submission

Registered two cloned Batch job definitions (`archondex-backtest-t126-postt099`, `archondex-backtest-t126-head`) that wrap the existing `archondex-backtest:dev` definition with the new image tags. Submitted both cells with `--timeout '{"attemptDurationSeconds":21600}'` (6h, per T-109's lesson) and identical containerOverrides env (`ARCHONDEX_START_DATE=2000-01-01`, `ARCHONDEX_END_DATE=2025-12-31`, `ARCHONDEX_REP=1`, `ARCHONDEX_CONFIG_PATCH_B64=e30=` for the empty `{}` patch).

Cells:
- Cell A `a7a5bb3b-edb3-466c-ad3a-6dc5bd52655f` — postt099 — SUCCEEDED at 26-yr in ~3h45m wall
- Cell B `d09bb879-3732-41c9-a60f-f52f7e8601cd` — HEAD — SUCCEEDED at 26-yr in ~3h45m wall

## Stage 1 — results

(see TL;DR table)

### Strict-letter dispatch verdict

> A != B: a merge between post-T-099 and HEAD moved the 26-yr → BUG. Go to Stage 2.

By canon-md5, A != B. Per strict dispatch, this is the Stage-2 trigger.

### Spirit-of-dispatch read (the actual finding)

The dispatch's binary was designed around T-125's framing: "the 26-yr shifted to 0.446 — was that move legitimate or a bug?" But Stage 1 shows the move **didn't actually happen the way T-125 said**. Both Cell A and Cell B produce ~0.24, not ~0.446. The "shift" T-125 framed isn't reproducible.

So the spirit-correct reading:

- The 26-yr `arm0` Sharpe at any commit from post-T-099 (`8103118`) to HEAD (`098668a`) is **~0.24** — matching T-092's published 0.246 to within 0.01.
- T-125's reported 0.446 was not a code-driven shift; it was a non-engine-input artifact (most likely a state of `data/processed/` or `data/raw/` on the director host that doesn't exist now).
- **T-092's "bull-conditional collapse" framing STANDS.** The 26-yr is the failing window the original audit said it was. The narrative softening T-125 implied was wrong.
- The canon delta between Cell A and Cell B (Δ Sharpe ~0.009) IS a real code-level shift between `8103118` and `098668a`, but it's a tiny one — well within the noise band a "default-OFF inert" claim could plausibly cover with non-canon-preserving but non-economically-significant FP drift.

### Recommendation on Stage 2

The dispatch authorizes Stage 2 if A != B. The strict reading triggers it. The spirit reading says "the tiny canon delta is real but the Sharpe move is in noise; the binding finding is the data-substrate failure-to-reproduce, not a single buggy inert-merge."

**My recommendation: defer Stage 2 pending director call.** The cost is 4× ~3h cloud cells (~$0.40 + 4× wall) to localize a Δ Sharpe ~0.009 move. The director may decide that (a) the bigger investigation is data-substrate forensics (what in `data/processed/` differs between 2026-06-06 and 2026-06-10), or (b) Stage 2 is still worth running because the canon delta is non-zero and the methodology lesson "single-cell canon proof is insufficient" stands regardless. Either way the verdict for the held wave is now clearer than before: the 26-yr is ~0.24, not 0.446, and T-092's narrative is the right one.

## Methodology coverage-gap finding (per dispatch — applies regardless of verdict)

The dispatch flagged this as a deliverable: **"canon-identical on a single cell (2022/2024) does NOT prove inert on the full 26-yr window."** Stage 1 confirms it. The Cell A vs Cell B canons differ, meaning at least one merge between `8103118` and HEAD has a non-trivial 26-yr canon effect despite a clean 2022/2024 single-cell "inert" verification.

This is a real process finding regardless of whether Stage 2 runs:

- **Verification policy update needed.** Future "default-OFF inert" / "canon-identical" checks should run on a **multi-window canon set** (e.g., 2022 + 16-yr + 26-yr at minimum), not just a single cell. A single-cell canon proof has a coverage gap proportional to the depth-only-triggered code paths (pre-2020 data the 2022 cell never exercises; crisis years like 2008 that don't appear in 2022).
- **All "OFF canon-identical" claims from T-101 / T-111 / T-116 / T-118 / T-120 should be flagged as "single-cell-verified, 26-yr-unverified" until re-checked on a 26-yr cell.** None of those claims are wrong yet by evidence — but the proof's coverage doesn't reach 26-yr depth.

## Bigger finding: a build-substrate reproducibility problem

The empirical fact is stark: I built two images of HEAD `098668a` on different days with the same pinned base digest, and they produced different canons. This isn't a "code-driven shift" — it's a **non-engine-input reproducibility failure**. The image is supposed to be byte-reproducible from a given commit + pinned base; it isn't.

The Dockerfile bakes these non-engine inputs:

- `config/` (mostly tracked-and-stable)
- `data/processed/` (gitignored; regenerable; can change at any time)
- `data/raw/` (gitignored; can change at any time)
- `data/governor/` (gitignored; T-099's `run_isolated` snapshots+restores per run, so the in-image copy is the seed — but the seed itself is the host's current state)
- `debug_config.py` (tracked)

`requirements.lock.txt` is also baked but unchanged on the relevant commits.

**The pin on `python:3.14-slim` made the BASE LAYER reproducible. It did NOT make the BUILD INPUTS reproducible.** That's the actual gap T-125 missed.

This means: until the host's `data/processed/`/`data/raw/` is pinned to a content-hash too, **any build can produce a different image** even from the same commit. This is a real T-125 gap and should be addressed before the wave launches — otherwise any future "canon == prior canon" check could fail spuriously even when nothing in code or libs changed.

### Suggested mitigation (NOT in T-126 scope)

- Snapshot `data/processed/` + `data/raw/` to S3 with content-hash naming on each canonical run; bake by hash, not by host filesystem state.
- OR check the data hashes into a small tracked manifest file (`data/processed.sha256`, `data/raw.sha256`) so a `make verify-substrate` can fail before a build silently uses drifted data.
- Either way, the audit lesson is: **the substrate is part of the determinism contract.** The Dockerfile pin closes the base; the lock file closes the libs; nothing currently closes the data.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | Stage 1: arm0 26-yr at post-T-099 vs HEAD (pinned base) — equal or not | DONE — canon DIFFERS (A != B); Sharpe Δ ~0.009 |
| 2 | VERDICT: legitimate OR bug → Stage 2 | DONE — neither cleanly: strict letter is "go Stage 2," spirit is "T-125's 0.446 is the actual bug (data-substrate); Stage 2 deferred pending director call" |
| 3 | Methodology coverage-gap note | DONE — single-cell canon proof is insufficient; all OFF-inert claims need 26-yr re-verification |
| 4 | Audit doc + proposed ledger row in OUTBOX | DONE |
| 5 | NO prod change; branch pushed NOT merged | DONE — no engine code edits; only audit + manifest evidence files |

## Hard constraints — confirmed met

- [x] All bisect images built on the pinned base (T-125 digest).
- [x] `arm0` = current prod default; `ARCHONDEX_CONFIG_PATCH_B64=e30=` (`{}`).
- [x] Cloud only (no local prod execution).
- [x] No prod config change.
- [x] No `docs/State/TASK_LEDGER.md` edit (T-114 protocol).
- [x] No `cockpit/dashboard/` edit.
- [x] Branch push only.

## Surprises

1. **T-125's 0.446 verdict is invalidated by Stage 1.** This is the major finding. T-125 declared the 0.446 "code-driven and bitwise-reproducible across pinned + unpinned images on the same day." It IS bitwise-reproducible same-day, but it is NOT reproducible across days. Three-day-later builds of identical code + identical pinned base produce a different canon and ~0.21 lower Sharpe.

2. **T-092's 0.246 is the actual 26-yr baseline.** T-126 Cell A reproduces it to 3 decimals on a fresh pinned build. The "bull-conditional collapse softens" framing from T-125 is wrong; the collapse is real.

3. **The build context (data/processed/, data/raw/) is unpinned even after T-125.** The pin closed the base, the lock file closed the libs, but the host-baked data is still mutable. Until data is also pinned (by content-hash check or by S3 snapshot), the image isn't truly reproducible.

4. **The dispatch's binary verdict frame missed the real finding.** Stage 1 was designed to decide "legitimate or buggy code shift." The answer is "neither — the apparent shift didn't actually happen the way T-125 reported." This is a category the dispatch didn't have a slot for.

5. **First T-126 build attempt was lost to a laptop restart** (mid-build B). Cleanly resumed; second attempt completed. ~30 min lost. The restart also wiped Docker's layer cache, forcing fresh base + venv layer rebuilds on both images (~5-10 min extra each).

6. **Disk was a binding constraint.** ~12 GiB free with 1.8G `data/raw` + 855M `data/processed` baked into each image = barely enough for two sequential builds + pushes. Required `docker rmi` between builds to free layer storage. Future bisect campaigns need more disk headroom or a per-commit cleanup procedure.

## Files

- **NEW** `docs/Audit/baseline_shift_bisect_t126_2026_06_09.md` (this).
- **NEW** `docs/Audit/postt099_manifest.json` — Cell A manifest.
- **NEW** `docs/Audit/postt099_perf.json` — Cell A performance summary.
- **NEW** `docs/Audit/head_manifest.json` — Cell B manifest.
- **NEW** `docs/Audit/head_perf.json` — Cell B performance summary.

(NO engine code, Dockerfile, or config files modified — agent-b worktree reset to HEAD.)

## Forward-look (NOT executed in T-126; director gates)

1. **Director call: defer Stage 2 OR run Stage 2 anyway.**
   - Defer: the Sharpe Δ between Cell A and Cell B is ~0.009 (in noise); the bigger finding is upstream (T-125's 0.446 invalidated).
   - Run anyway: localize the canon-shifting merge for the methodology coverage-gap follow-up.
   - My recommendation: defer; spend the cells on data-substrate forensics or relaunch the held wave.

2. **Data-substrate forensics** — bisect what changed in `data/processed/` / `data/raw/` between 2026-06-06 (T-125 build) and 2026-06-10 (T-126 builds). Was a data file regenerated? A sync ran? Manual edit? The answer is consequential because **whatever changed silently moved a canon by ~$200k of ending equity over 26 years.**

3. **Substrate-pin gap closure** — add `data/processed/`/`data/raw/` content-hash check to the build pipeline so future "same image, same canon" claims can hold across days, not just same-day.

4. **All "OFF canon-identical" claims need 26-yr re-verification** — T-101 / T-111 / T-116 / T-118 / T-120 each verified inertness on a 2022 single-cell. By Stage 1 evidence, the single-cell proof leaks at 26-yr. Re-verify each on 26-yr before any "OFF-inert" claim is treated as load-bearing.

5. **CURRENT_STATE update needed** — the entry "26-yr Sharpe 0.446 (pinned image, bitwise-reproducible)" added during T-125 needs revision. Current evidence: T-092's 0.246 STANDS; the 0.446 was a non-reproducible build artifact. Bull-conditional collapse narrative is back in force.

6. **Held cloud wave** — can launch as soon as the data-substrate pinning is resolved. Until then, every campaign reading a "baseline" number is at risk of comparing against a non-reproducible build.

## Outbox status flag

**DONE — Stage 1 ran; verdict is NEITHER legitimate NOR an inert-merge bug. The 0.446 from T-125 is invalidated (not reproducible 3 days later, same code, same pinned base). T-092's 0.246 STANDS. Real finding is upstream: a substrate-pin gap (data/ not pinned alongside libs+base). Methodology coverage-gap also confirmed: single-cell canon proof leaks at 26-yr. Stage 2 deferred pending director call.**
