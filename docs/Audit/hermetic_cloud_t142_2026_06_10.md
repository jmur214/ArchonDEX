# T-2026-06-10-142 — Hermetic cloud runs: yfinance network burn killed + CONTAMINATION FINDING (live earnings dates feed local canons)

**Date:** 2026-06-11
**Branch:** `feature/hermetic-cloud-t142`
**Worker:** Agent B
**Predecessors:** T-134 (the 52%-of-wall yfinance profile + logger-drain finding), T-088/silent-bug audit (split-only-cache contamination hazard), T-127 (CloudWatch recovery pattern, partially retired here)
**Status:** DONE — hermetic mode shipped (7 gated sites, launcher cloud-default, fail-loud + strict tiers); print-storm gated; **the dispatch's pre-registered contamination branch FIRED: canon CHANGES hermetic off→on — live network data has been feeding local signals.**

## TL;DR

1. **Hermetic mode** (`core/hermetic.py`, env `ARCHONDEX_HERMETIC`: off|warn|strict): all 7 yfinance call sites in the cell path are gated BEFORE their swallow-all try-blocks. `warn` (cloud default via the launcher since this task) blocks the network call with a loud greppable `[HERMETIC] BLOCKED site=… ticker=…` line and proceeds on the existing no-data path; `strict` raises. Local default unchanged (env unset = off; documented override).
2. **CONTAMINATION FINDING (loud, as pre-registered):** on the standard local 2022 cell, **canon CHANGES off→on**: `0145c03a…`/Sharpe 0.464 → `f47b63b2…`/Sharpe 0.285. Mechanism: `earnings_vol_edge` fetches earnings dates from LIVE yfinance at run time (in-memory cache only — every run re-fetches) and those dates feed signals → trades. **The established local canon family (`0145c03a…`, the T-101/T-111/T-116/T-118 OFF-reference) has been partially built on live Yahoo data all along.** It reproduced only because *historical* earnings dates are de-facto stable — but it is a live network dependency in the measurement path: an API change, rate-limit day, or data revision silently moves local canons.
3. **Miss inventory (one hermetic cell):** **42 blocked calls, all one site** — `earnings_vol_edge._get_earnings_dates`, one per scored ticker. The other 6 gates (price fallback, dividends, SPY live download, earnings pipeline, spinoff×2) never fired — the price substrate is complete; the other edges are inactive in the prod ensemble. So "what production cells were actually fetching": **earnings dates, per ticker, every cell, forever** — and on Fargate that is the 52%-of-wall timeout burn T-134 profiled.
4. **Logger drain fixed:** the 2 per-bar full-dict snapshot prints + the per-fill print are now gated behind the existing level checks (content unchanged when enabled). Trade-off flagged: this retires the T-127 CloudWatch log-scrape recovery channel (acceptable at 6h timeouts).
5. **Non-hermetic default proven byte-identical:** after all changes, the T-138 golden master (full-pipeline replay at rtol=1e-9) + 6 property invariants + forbidden-pattern lint = **9/9 green** — the strongest available proof that the off-path is untouched.

## Wall-time

- **Local:** modest — local yfinance calls succeed quickly (~42 calls ≈ 1-3 min of a ~18-min cell). The pair ran inside one ~35-min task.
- **Cloud (the 2× claim):** the burn is container-side (timeouts/rate-limits — T-134 measured 52% of wall inside yfinance wrappers on a 1-yr cell). Projection: removing it ≈ **~2.1× cell speed**; plus reduced CloudWatch ingest from the print-storm gating. **Empirical before/after on a cloud cell: deferred to the first post-merge campaign** (every cell is hermetic-default then — the number falls out for free). Local Docker disk exhaustion (Docker Desktop VM file at 2.8 GiB host headroom) blocked building the test image this session; building on a recovered-disk session works identically via `build_backtest_image.sh`.
- **Combined estimate for a 52-cell campaign** (T-134 maxvCpus=100 + T-140 pins + this): wall ≈ longest cell ≈ **~1.5-2 h at 16-yr depth / ~2 h at 26-yr** (vs 8-14 h pre-bundle).

## The contamination finding — implications (director attention)

- **Cloud canon baselines will MOVE when this merges** (cloud cells flip to hermetic-default): comparisons against pre-T-142 cloud canons (e.g., `529e5520…` 26-yr, `0a62b754…` 2022) are cross-regime. The campaign canary (T-134) guards within-campaign consistency; **cross-campaign references need a one-time re-baseline on the first hermetic image.** Same for the local reference family (`0145c03a…` → hermetic-local equivalent `f47b63b2…` when measuring hermetically).
- **The right long-term fix for earnings data:** bake a static earnings-dates parquet into the substrate (manifest-pinned like everything else) and point `earnings_vol_edge` at it — kills the dependency AND the 42-calls-per-cell burn at the data layer. Flagged as follow-up (data_manager/earnings pipeline already has the cache infra).
- **Determinism re-read:** local↔cloud canon divergence (`0145c03a` vs `0a62b754` for the same 2022 cell) has been a known-but-unexplained constant; differing yfinance outcomes (local succeeds / container times out) is now a CANDIDATE mechanism for part of it. Not proven here; the earnings-parquet fix would settle it.

## What shipped (files)

- **NEW** `core/hermetic.py` — the gate (mode docs, miss-counting, strict tier).
- **MOD** 7 call sites: `engines/data_manager/data_manager.py` (price fallback — also the T-088 split-only hazard), `engines/data_manager/earnings_data.py`, `engines/engine_a_alpha/edges/earnings_vol_edge.py`, `…/dividend_initiation_drift_v1.py`, `…/_helpers/spinoff_detector.py` (×2), `engines/engine_a_alpha/alpha_engine.py` (SPY live fallback).
- **MOD** `backtester/backtest_controller.py` + `engines/engine_c_portfolio/portfolio_engine.py` — print-storm gated behind `is_controller_debug()` / `is_debug_enabled("PORTFOLIO")`.
- **MOD** `scripts/submit_arms_campaign.py` — `ARCHONDEX_HERMETIC=1` in every cloud cell's env (launcher side per dispatch; entrypoint untouched — A owns it in T-140).

## Acceptance

| Criterion | Status |
|---|---|
| Hermetic mode (cloud-default, fail-loud with names) + miss inventory + what production fetched | DONE — 7 sites; launcher default; 42 blocked calls = earnings dates per scored ticker, single site |
| Logger drain fixed; wall before/after | DONE (gated); local pair measured; cloud empirical deferred to first post-merge campaign (projection ~2.1×) — Docker-disk blocker documented |
| Canon-unchanged proof OR the contamination finding | **THE FINDING** — canon changes off→on (`0145c03a`→`f47b63b2`), mechanism identified (live earnings dates in signals), implications + re-baseline requirement documented |
| Audit + ledger row in outbox | DONE |

## Hard constraints — confirmed

- [x] Non-hermetic default path byte-identical — golden master (1e-9) + properties + lint green post-change.
- [x] data_manager shared-infra changes autonomous; entrypoint/job-def untouched.
- [x] No TASK_LEDGER write; branch push only.

## Surprises

1. **The "canon-irrelevant fallback" premise was FALSE** — exactly what the dispatch's verify step existed to catch. Live earnings dates have been a silent input to every local measurement involving `earnings_vol_edge`.
2. **One site explains everything** — 42/42 blocked calls are earnings-date fetches; the feared price-data gaps (data_manager fallback) never fired. The substrate is complete; the burn was a single edge's data dependency.
3. **Docker Desktop VM disk exhaustion** (2.8 GiB host headroom after two prunes — the VM file grows monotonically) blocked the cloud test image this session. Needs a Docker-side disk reclaim (user action) or a fresh session.
