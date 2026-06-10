# T-2026-06-09-127 — Substrate pin + forensics: the 0.446 was STALE HOST BYTECODE, not data drift

**Date:** 2026-06-10
**Branch:** `feature/data-substrate-pin-t127`
**Worker:** Agent B
**Predecessors:** T-125 (claimed 0.446 code-driven — wrong), T-126 (claimed 0.446 was data-drift + that T-092's 0.246 stands — half right, wrong mechanism, and built on contaminated builds), T-092 (the original 0.246)
**Status:** DONE. Mechanism PROVEN bitwise. Build pipeline made reproducible by construction. The week-long 0.246/0.446 saga is closed.

## TL;DR — the verdict chain

1. **There was NO data drift. Ever.** All 14,037 baked data files (`data/processed`, `data/raw`, `data/governor`) are byte-identical between the "0.446" images and the "0.237" images. The dispatch's hypothesis (shared `data/` mutated by agent work) is refuted — the substrate has been stable since May.
2. **The 0.446 was a stale-bytecode artifact.** The June-6 images baked the Mac host's nested `__pycache__` trees (the `.dockerignore` pattern `__pycache__/` only matches at context ROOT — classic gotcha). 237 host-compiled `.pyc` files had valid headers (mtime+size match), so container Python **loaded host bytecode instead of compiling the baked source** for essentially every engine module. Host Python is 3.14.4, container is 3.14.5 — same pyc magic, different compiler patchlevels, **provably different bytecode for identical source** (marshal-compare confirmed in-container). At 26-yr depth that difference cascades into different trades.
3. **Bitwise proof (Cell P):** the EXACT T-125 image with only `__pycache__` removed produces canon `529e55204a92…`, Sharpe **0.237**, MDD **-59.29** — bitwise identical to T-126's clean HEAD build. With pycache: `2b2f2c2b12b8…`, Sharpe **0.446**, MDD **-48.0**. One variable, flipped verdict.
4. **The true current-config (hmm-ON) 26-yr baseline is ~0.237 / MDD -59.3** (Cell C, the clean-pipeline build, finalizes the exact canonical number below). T-092's "bull-conditional collapse" narrative **STANDS — no softening**. T-101's `hmm_enabled=true` does NOT rescue the deep window.
5. **Part B shipped:** builds are now reproducible by construction — `git archive` (never the worktree) + committed substrate manifest (sha256 over 14,032 files) verified before every build + content-addressed S3 snapshot + `.dockerignore` nested-pattern fix.

## The corrected history of the 26-yr baseline

| Run | Image built from | pycache state | regime cfg | 26-yr Sharpe | MDD | canon |
|---|---|---|---|---|---|---|
| T-092 (May-31) | May-28 worktree bake | host pycs baked (that era) | hmm OFF (pre-T-101) | 0.246 | -59.3 | (n/a) |
| T-109 (Jun-6) | director worktree @ c074744 | host pycs baked, valid → **LOADED** | hmm ON | **0.446** | -48.0 | `2b2f2c2b…` |
| T-125 (Jun-6 img, ran Jun-9) | director worktree (post-merge-wave, NOT c074744 as claimed) | host pycs baked, valid → **LOADED** | hmm ON | **0.446** | -48.0 | `2b2f2c2b…` ≡ T-109 |
| T-126 Cell A (Jun-10) | chimera (8103118 + leftover HEAD-new files) | host pycs baked but **headers invalidated** by rsync/checkout mtimes → fresh compile | hmm OFF (8103118-era file) | 0.246 | -59.29 | `c579566c…` |
| T-126 Cell B (Jun-10) | clean HEAD content (verified post-hoc) | host pycs baked, mostly invalid → fresh compile | hmm ON | 0.237 | -59.29 | `529e5520…` |
| **T-127 Cell P** (Jun-10) | T-125 image **minus pycache only** | **NONE** | hmm ON | **0.237** | **-59.29** | **`529e5520…` ≡ Cell B** |
| **T-127 Cell C** (Jun-10) | **clean pipeline: git archive @ 9374871 + verified data** | none (archive has no pycs) | hmm ON | see §Cell C | see §Cell C | see §Cell C |

The single weirdest fact of the saga — T-109 and T-125 images carrying **different code** yet producing **bitwise-identical** 26-yr canons — is exactly what the pyc mechanism predicts: for modules whose host pyc was valid in both images, **both containers executed the same host bytecode regardless of their baked source**. The pyc layer made the source code partially irrelevant.

And the T-125→T-126 "non-reproducibility" that T-126 attributed to data drift: the June-10 builds went through my `git checkout`/`rsync` staging, which reset `.py` mtimes → invalidated the baked pycs' headers → container compiled the actual source → different (correct!) behavior. The "drift" was the **taint turning off**.

## Part A — forensics detail

### What did NOT change (eliminations, each proven)

- **`data/processed` + `data/raw` + `data/governor`:** zero mtime changes Jun-5→Jun-10 on the host; byte-identical (null-safe full manifests, 14,037 files incl. the space-path Stooq dirs) across the 0.446-image and the 0.237-image. *Note: my first image manifests used `xargs md5sum` which silently dropped ~12k space-containing Stooq paths; redone with `-print0`/`xargs -0`. T-126's image diffs had the same blind spot.*
- **HMM model files:** all 8 `.pkl`s tracked in git, identical md5 in both images.
- **Tracked config:** identical in both images (incl. `regime_settings.json` = hmm-ON at both builds' commits).
- **5 untracked `config/*backup*` junk files** (present only in June-6 images): **no code reads them** (full grep sweep) — inert clutter, a red herring I chased for an hour.

### The mechanism (proven in 3 steps)

1. **Detection:** in-container scan of the T-125 image found **237 `.pyc` files with VALID headers** (source mtime+size match → Python loads them without recompiling) covering essentially every engine/core/backtester module — all compiled by the HOST (Mac, venv Python 3.14.4), not the container (3.14.5).
2. **Bytecode difference confirmed:** in-container `marshal`-compare — the baked pyc bytecode ≠ the container's own compile of the *identical source* (method sanity-checked: same-interpreter double-compile is marshal-stable). Same pyc magic across 3.14.4/3.14.5, different compiler output.
3. **Behavioral proof at scale (Cell P):** `:t127-nopyc` = the T-125 image with one change — `find /app -name __pycache__ -exec rm -rf` — re-ran arm0 26-yr: canon flipped from `2b2f2c2b…` (0.446/-48.0) to `529e5520…` (0.237/-59.29), **bitwise-matching the clean HEAD build**. One variable. QED.

Why single-year cells never caught it: a 2008-only run on both images produced **bitwise-identical** canons (`354cb577…`, local R1/R2 test). The 3.14.4-vs-3.14.5 bytecode delta only expresses through an FP-sensitive path that needs the right multi-year conditions to flip a decision — the T-057c-det sensitivity class, surfacing through the build system this time.

### My own errors in T-126 (owned)

T-126's conclusions were built on contaminated builds and a sloppy check, and its audit shipped two wrong claims:

1. **Contaminated director worktree:** my June-9 `git checkout 8103118 -- … && rsync -a --delete` into the director worktree left **8 tracked files at 8103118-state** (incl. `config/regime_settings.json` = hmm-OFF) and **deleted the 5 untracked config backups**. My post-restart `git status | head -10` TRUNCATED the modified-files list right before the contamination would have shown. All 8 files + Dockerfile now restored to HEAD (verified each was exactly-8103118 content first — no real work stomped).
2. **Chimera Cell A:** `git checkout <commit> -- paths` does NOT delete files that didn't exist at that commit — so "8103118" Cell A actually contained HEAD-era `regime_transition_overlay.py` + `spot_etf_trend_sleeve.py`. Its 0.246 result happens to be consistent (those files are import-dead at 8103118), but the build was not what the audit said it was.
3. **Wrong attribution:** T-126 declared "data-drift / substrate-pin gap" without identifying any actual drifted data. The substrate-pin gap is REAL (and Part B closes it) but the operative mechanism was bytecode, and the "T-092 0.246 STANDS" conclusion — while CORRECT — was right for the wrong reason.

The deeper root cause across T-109/T-125/T-126: **builds baked live worktree state** (host pycache, untracked junk, uncommitted/stale tracked files), and no provenance was recorded. Part B makes this class structurally impossible.

## Part B — the pin (shipped, commit `9374871`)

1. **`scripts/build_backtest_image.sh <git-ref> [tag]`** — stages from `git archive` (the COMMIT, never the worktree; no pycs/junk by construction), stages data with junk excluded, **verifies data against the committed manifest** (fail-loud with exact drifted paths), builds with provenance labels (`org.archondex.commit`, `org.archondex.substrate-manifest-md5`) + a `sha-<short>` tag.
2. **`scripts/gen_substrate_manifest.py` + `config/substrate_manifest.sha256`** — sha256 over all 14,032 substrate files (manifest-md5 `a40d5483112b3d0b7a4e00fa8a05231a`), committed. Deliberate substrate changes = regenerate + commit in the same PR; silent drift = build failure.
3. **S3 snapshot (durable, content-addressed):** `s3://archondex-results-407539788432/substrate/a40d5483112b3d0b7a4e00fa8a05231a/` — 14,033 objects / 2.78 GB (substrate + manifest).
4. **`.dockerignore` fix:** `**/__pycache__`, `**/*.pyc`, `**/.DS_Store`, `config/*backup*`, `config/*.pre-*` — the bare rooted patterns were the original hole.
5. **Local write-safety:** NOT chmod'd (data wasn't actually the mutation source, and a blanket `a-w` risks breaking legit refresh pipelines). The manifest-verify gate at build time is the enforcement point; a chmod proposal is left to the director (propose-first, affects all agents' shared dir).

**Cross-day reproducibility argument:** two builds of the same ref now stage identical code (git archive is content-addressed) + manifest-verified identical data + digest-pinned base (T-125) + lock-pinned libs → identical `/app` trees by construction. The remaining nonreproducible surface (pip-installed venv layer internals) does not affect `/app` content or runtime semantics at fixed lock + fixed base.

## Part C — the canonical baseline (Cell C, clean pipeline)

Cell C = `:t127-clean`, built by the NEW pipeline from commit `9374871` (= origin/main `0ab1ec4` + T-127 infra only; engine dirs byte-identical to `0ab1ec4`), substrate manifest-verified, hmm-ON tracked config, no pycache.

**RESULT: canon `529e55204a92462337169fb0b3f3a4fd`, Sharpe 0.237, CAGR 2.51%, MDD -59.29%, 8,279 trades, ending equity $190,401.14.**

**Bitwise identical to Cell P (June-6 image minus pycache) and Cell B (June-10 worktree bake).** Three images built by three different paths on different days → ONE canon. That IS the cross-day reproducibility the dispatch demanded, demonstrated rather than argued. The canonical 26-yr arm0 baseline at current prod config is:

> **Sharpe 0.237 / CAGR 2.51% / MDD -59.29% / canon `529e5520…`** (clean-pipeline build, substrate `a40d5483…`, base digest `c845af93…`, commit-provenance labeled)

The dispatch's Part-C acceptance line ("confirm it reproduces 0.246") was written under T-126's story and is overtaken: the clean number at CURRENT config (hmm-ON) is ~0.237; the 0.246 belongs to the hmm-OFF-era config (T-092, reproduced by T-126 Cell A). Both deep-window numbers are catastrophic versus the 16-yr window — **the strategic picture (bull-conditional collapse) is unchanged and confirmed**.

### CURRENT_STATE implications

- **26-yr baseline (current prod config, clean build): ~0.237 / MDD -59.3.** Not 0.446 (bytecode artifact), and marginally below T-092's 0.246.
- **T-092 narrative (collapse REAL) stands.**
- **T-101 ("HMM wired, bitwise-INERT, capability-failure") at 26-yr:** hmm-ON (0.237) vs hmm-OFF-era (0.246) — the wire is approximately inert-to-slightly-negative at depth on clean builds. The tantalizing "HMM kill-switch works (+0.20 Sharpe, -11pp MDD)" hypothesis raised mid-T-127 forensics is **DEAD — it was the bytecode artifact**, not the HMM.
- **All June-6-era cloud results (T-109 static-20 A/B included) ran on pyc-tainted images** and need re-verification before being load-bearing: the static-20 REJECT verdict was *within-image* A/B (both arms equally tainted), so its directional conclusion plausibly survives, but its absolute numbers don't.
- **The held cloud wave can launch** on `:t127-clean`-style builds (pipeline + pinned substrate + 3/3 det floor from T-125).

## Acceptance vs dispatch

| # | Dispatch criterion | Status |
|---|---|---|
| 1 | Forensics: WHAT changed 06-06→06-10, WHEN, WHICH process; is substrate at T-082 state | DONE — **nothing in data/ changed** (byte-proof); the "drift" was baked-pycache taint turning off when my T-126 staging reset mtimes; substrate stable since May (manifest `a40d5483…` now pins it) |
| 2 | Substrate pinned; same-commit builds byte-reproducible; local data write-safe | DONE — git-archive build script + committed manifest + S3 snapshot; reproducible by construction; write-safety = manifest gate (chmod left propose-first) |
| 3 | Pinned arm0 26-yr reproduces 0.246; cross-day reproducibility | OVERTAKEN BY FORENSICS — clean hmm-ON baseline is **0.237** (canon `529e5520…`, reproduced bitwise across 3 independent builds: Cell B, Cell P, Cell C); 0.246 = hmm-OFF-era config (Cell A). Reproducibility: 3 builds → 1 canon |
| 4 | Audit + proposed ledger row in outbox | DONE |
| 5 | NO prod change; branch pushed NOT merged | DONE — infra-only commit; engine code untouched |

## Hard constraints — confirmed

- [x] Infra/data scope only; no Engine B logic, no prod config change (`config/risk_settings.prod.json` untouched; `regime_settings.json` only RESTORED to HEAD in the director worktree — undoing my own T-126 damage).
- [x] Substrate pinned AS-IS (proven = the stable state all images shared; T-082-consistent).
- [x] No `data/governor/*` manual edits; no `cockpit/dashboard/`; no TASK_LEDGER write (proposed row in outbox).
- [x] Branch push only.

## Surprises

1. **The dispatch's premise was wrong, productively.** No data drifted, ever. The image's data legs were identical across every build in the saga. The real hole was bytecode.
2. **`__pycache__` baked into images executed IN PLACE OF the source** — 237 modules. Host 3.14.4 vs container 3.14.5 compile the same source to different bytecode (same magic), and at 26-yr depth that flips real trading decisions (+0.21 Sharpe, -11pp MDD — the artifact was LARGER than most real effects this project has measured).
3. **Cross-image bitwise agreement (T-109 ≡ T-125) was the pyc layer masking code differences** — the most counterintuitive fact of the saga, fully explained.
4. **Single-cell canon checks can't catch this class either** (2008-only: bitwise identical across tainted/clean images). The T-126 "multi-window inertness" lesson extends: *build-provenance* checks (what bytes actually run) matter as much as result checks.
5. **T-092's 0.246 itself was likely produced on a pyc-baked image too** (May-28 worktree build). It happens to match the clean hmm-OFF-era number (Cell A, 0.246) — but treat pre-T-127 absolute numbers as provenance-unverified history; the clean-pipeline canon is the going-forward reference.
6. **My T-126 audit shipped wrong mechanism attribution from contaminated builds** — full error chain owned in §Part A. The truncated `git status | head -10` check is now a personal anti-pattern: never truncate a cleanliness check.

## Files

- **NEW** `scripts/build_backtest_image.sh` — clean-source build pipeline.
- **NEW** `scripts/gen_substrate_manifest.py` — manifest generate/verify.
- **NEW** `config/substrate_manifest.sha256` — pinned substrate (14,032 files, `a40d5483…`).
- **MOD** `.dockerignore` — nested-pattern fix + junk-class exclusions.
- **NEW** `docs/Audit/data_substrate_pin_t127_2026_06_09.md` (this).
- **NEW** `docs/Audit/t127_cell_{nopyc,clean}_{manifest,perf}.json` — cell evidence.
- (Director worktree repaired: 8 files + Dockerfile restored to HEAD — not part of this branch.)

## Forward-look (director gates)

1. **Adopt `scripts/build_backtest_image.sh` as the ONLY image-build path** (deprecate raw `docker build .` in CLOUD_USAGE.md; optionally wire into the CI workflow once `AWS_ROLE_TO_ASSUME` lands).
2. **Re-baseline ledger entries measured on June-6-era images** where absolute numbers are load-bearing (T-109 static-20 directional verdict likely survives; absolute Sharpes don't).
3. **CURRENT_STATE update:** 26-yr = **0.237 (hmm-ON, clean, canon `529e5520…`)**; 0.446 retired as bytecode artifact; collapse narrative confirmed; wave UNBLOCKED on clean builds.
4. **Optional follow-up:** identify WHICH module's 3.14.4-vs-3.14.5 bytecode delta flips behavior (disassembly diff of the 237) — interesting for the FP-guard program (T-057c-det class), not blocking.
5. **Consider pinning the HOST dev Python to the container's exact patchlevel** (3.14.5) to kill the class at the source for local runs too.
