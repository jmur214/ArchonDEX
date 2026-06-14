---
task_id: T-2026-06-13-140-followup-3
title: Deterministic cov() — the real cov→MVO determinism fix (kills the lottery at the source, avoids the N≥5 tax)
date: 2026-06-13
worker: Agent B
branch: feature/determinism-cov-pin-t140fu3
outcome: "Deterministic cov() shipped: pandas .cov()'s OpenBLAS gemm (the alignment/thread-nondeterministic step A's T-140 pins did NOT cover — they fixed eigh/SLSQP kernels) is replaced by np.einsum(optimize=False), numpy's fixed-order C reduction → Sigma byte-identical across tasks BY CONSTRUCTION. Local validation complete + green: det-cov byte-stable across 4 repeats, equals pandas .cov() to 7.8e-16 on the real 2022 MVO statistic (DETERMINISM-only, not a math change), golden master + 360 targeted tests green (no canon regression). The cross-Fargate-task proof (Sigma identical across tasks → one SLSQP fixed point → lottery dead) needs a TRADING current-main cloud image, which is BLOCKED on D's T-164 (current main makes zero cloud trades — the fundamentals-fetch regression D is fixing). The N≥5-per-window unanimity proof + the durable re-anchors are STAGED to fire the moment T-164 lands. If einsum-no-opt also proves cross-task-divergent on Graviton (residual risk — numpy SIMD could be alignment-sensitive), the fallback is the N≥5 + minority-discard protocol (rep count for p≈0.4 below)."
---

# Deterministic cov() (T-140-fu3) — the clean fix

## Does it kill the lottery? (local proof + the mechanistic case)
**Mechanism (from T-140-fu2 + A's bounding):** the lottery is born in `returns_df.cov()`. A proved the eigh/SLSQP kernels are deterministic under the T-140 thread pins (8/8, 6/6) and the universe order is sorted — so the only un-pinned step feeding Sigma is the **OpenBLAS gemm** inside pandas `.cov()` (the demeaned cross-product `Xc.T @ Xc`). OpenBLAS gemm uses blocked-SIMD kernels whose partial-sum accumulation order depends on buffer alignment / kernel dispatch — varying across Fargate tasks even single-threaded — yielding a ~1e-15 Sigma difference → two SLSQP fixed points (~5e-9 active-weight divergence, T-140-fu2 capture) → a flipped trade → the lottery (measured p(minority)≈0.4 at N=5).

**Fix:** `deterministic_cov()` (engines/engine_c_portfolio/optimizer.py) replaces the gemm with `np.einsum("ti,tj->ij", Xc, Xc, optimize=False) / (n-1)` — numpy's own fixed-order C reduction loop, with NO BLAS gemm and NO alignment/thread dependence. Sigma is therefore byte-identical across tasks **by construction**. Wired at both policy.py cov sites (the mean_variance MVO cov — the proven lottery source — and `_estimate_portfolio_vol`). `ARCHONDEX_DET_COV=0` falls back to pandas for baseline capture.

**Local proof (the part NOT blocked):**
- **Byte-stable**: `deterministic_cov(returns_df)` byte-identical across 4 repeats; `optimize()` on the pinned Sigma byte-stable across 4 repeats.
- **Math-safe**: equals pandas `.cov()` to **max 7.77e-16 (relative 7.0e-16)** on the real 2022 109-name MVO statistic — a canonical reduction order of the IDENTICAL statistic, not a different number.
- **No regression**: golden master + 360 targeted (policy/optimizer/portfolio/contract/determinism) tests green.
- **Cost**: einsum-no-opt 1.6ms/call — negligible vs a multi-hour run.

Local cannot exhibit the cross-task divergence (T-140-fu2: the cov→MVO composition is already bitwise-identical across Mac subprocesses; the lottery is Graviton/Fargate-specific). So the local result is necessary-but-not-cross-task-sufficient; the mechanistic argument (gemm removed) is why it should hold on the fleet, to be confirmed by the cloud N≥5.

## Math-safety golden-master result
Golden master GREEN (no canon moved). The golden fixture exercises the path it exercises without a diff; the rigorous math-safety for the MVO cov itself is the direct 7.8e-16 agreement above (a tighter proof than golden alone, since it measures the exact statistic the fix touches).

## Re-anchor status
This IS the re-anchor: pinning the cov picks ONE canonical Sigma, so the cloud canon will move off the old nondeterministic `0a62b754`/`0c6b8811` family — by design. The durable anchors (2022/16yr/26yr) get published from the N≥5-per-window unanimity run on a current-main+cov-pin image. **STAGED, blocked on D's T-164** (below).

## Dependency on D's T-164 (the cloud-proof blocker)
T-140-fu2 surfaced that current main `e58f6e9` makes ZERO cloud trades (aborts after the first "Fetching fundamentals"); D's T-164 owns that fundamentals-fetch-under-hermetic regression. The cov-pin's cross-task proof needs a TRADING current-main image. The moment T-164 lands one:
1. Build current-main + cov-pin (coordinate the build with D).
2. N≥5-per-window (2022/16yr/26yr) on that image, snap+cov-pin ON.
3. Expect bitwise unanimity per window → publish the durable re-anchors (these replace the T-155 anchors).
4. If a window still splits at N≥5 → einsum-no-opt is also cross-task-divergent on Graviton → irreducibility fallback (below).

## Irreducibility fallback spec (if the cov-pin doesn't hold cross-task)
With p(minority)≈0.4 (measured), a simple majority over N reps mis-calls the canon with probability = P(≥N/2 minority draws). For unanimity-gated anchoring (require all-N identical, else discard the cell and re-draw): at p≈0.4, P(all-N majority) = 0.6^N → N=5 gives 0.078 (false-split rate ~92%, too high for unanimity) → unanimity is the WRONG rule at p≈0.4. The right rule is **majority-of-N with a confident margin**: N=9 gives P(majority correct) ≈ 0.90; N=15 ≈ 0.97. Recommend **N=11 majority-canon (discard minority), ~0.93 confidence**, OR a signed-off ~1e-6 weight quantization (math sign-off required; collapses both attractors since they differ at ~5e-9). The cov-pin, if it holds, avoids this tax entirely — which is why it's worth proving first.

## Files
- `engines/engine_c_portfolio/optimizer.py` — `deterministic_cov()` (+ the T-140-fu2 snap, kept).
- `engines/engine_c_portfolio/policy.py` — both cov sites wired to the helper.
- `/tmp/t140fu3_covpin.py` — candidate eval (einsum-no-opt vs addreduce vs pandas; einsum chosen: 1.6ms, 7.8e-16, byte-stable).
- Branch `feature/determinism-cov-pin-t140fu3` @ 11ff735 (pushed, NOT merged).

---

# ADDENDUM (2026-06-13 PM) — T-164 MERGED + C's T-165 pre-flight gate + the regime-load trace

**T-164 landed (merged, in current main):** fundamentals hermetic guard (cloud cells now TRADE), `data/macro/` baked (HMM/macro half fed), `sp500_membership.parquet` baked (real historical universe), plus the cov-pin. The cov-pin's cross-task N≥5 proof is now unblocked — BUT C's T-165 added a **hard pre-flight gate** before the N≥5 spend.

## C's T-165 gate (why the re-anchor is gated)
C refuted "data/macro alone explains the cloud regime death": emptying `data/macro` locally only NaNs the macro columns; the 5-axis PRICE regime (trend/vol/corr/breadth) still builds from `data/processed` and stays *known*. The cloud reportedly showed the price axes *also* unknown → "the benchmark/price data isn't reaching the cloud regime detector — more than just data/macro." Macro-blindness is **not benign** (adaptive-2022 Sharpe 0.464→0.369, −0.095). **Gate:** run ONE T-164 cloud cell, dump the regime log, verify all 5 PRICE axes + macro/HMM are live (non-unknown across the run) BEFORE spending on N≥5. If price axes still dead → trace+fix the cloud regime data-load, don't spend.

## The regime-load trace (B, static, this session)
Traced where the regime detector gets its data in the cloud backtest path:
- **Regime runs IFF "SPY" is in `data_map`.** Both call sites gate on it: `mode_controller.py:1168` (`spy_df = data_map.get("SPY"); if not empty: detect_regime(spy_df, data_map=data_map)`) and `backtest_controller.py:344` (`bm_df = slice_map.get('SPY')`). `detect_regime(benchmark_df, data_map, now)` takes price data as ARGUMENTS (trend/vol off `benchmark_df`=SPY; corr/breadth off `data_map`) — it is NOT disk-loaded inside the detector. So a missing/empty SPY → all 5 price axes unknown.
- **SPY reaches the cloud by static analysis.** `config/backtest_settings.json` has `use_historical_universe: false` → the resolver is skipped and the **static ticker list is used verbatim; that list INCLUDES "SPY"** (line ~97). No launch override flips `use_historical_universe` (checked submit_substrate_run.py / run_isolated.py / cloud_entrypoint.sh; t155-anchor job-def env has none). Even on the historical path, `discover_cached_tickers` scans `data/processed/*_1d.csv` and **`SPY_1d.csv` IS baked** (in the substrate manifest), so SPY survives the `available_filter`. Either way SPY lands in `data_map`.
- **Conclusion / falsifiable prediction:** with T-164's substrate (SPY in the static list + `data/macro` baked), the price axes AND the macro half should BOTH be live in the cloud. C's "trend/vol unknown too" was most likely a *macro-label*-unknown (the trades' `regime_label` is `macro_regime.label`, which goes "unknown" when the macro/HMM half is starved pre-T-164) **conflated with** price-axis death — not the price axes themselves. **Prediction: T-164 restores the full cloud regime; the gate PASSES.** Falsifiable by the pre-flight cell.

## How the gate is checked (no probe code, no double-build)
`regime_history.csv` records all 5 axes (`RegimeHistoryStore.AXES = [trend, volatility, correlation, breadth, forward_stress]`) and saves into the run dir, which `cloud_entrypoint.sh` uploads to S3 recursively (`aws s3 cp --recursive "$RUN_DIR"`). So the pre-flight cell's per-axis distribution + the trades' `regime_label` distribution give the full gate signal directly from existing outputs.

## Status
- Rebased onto current main (T-164/165/166). Branch `covpin-reanchor-t140fu3` (remote tip `31503cc` — has T-164 + cov-pin + the build-script staging fix; image-identical to current main, only docs + a standalone diagnostic script differ).
- **Build-script staging gap fixed** (`31503cc`): T-164's Dockerfile COPYs `data/macro` + `data/universe/sp500_membership.parquet`, but `build_backtest_image.sh` only staged `processed raw` → the build would fail at COPY. Now stages `processed raw macro` + the curated universe file.
- Substrate synced to S3 `substrate/11d32fe8…/` (CI fetches it; the prefix was empty — D had not populated it).
- **NEXT:** CI build (local Docker down) → one 2022 pre-flight cell → check regime_history per-axis → gate PASS ⇒ N≥5 on {2022,16yr,26yr} ⇒ publish anchors; gate FAIL ⇒ trace deeper + report (no spend).

---

# ADDENDUM 2 (2026-06-13 PM) — RE-ANCHOR BLOCKED: the cloud makes ZERO trades (allocator/substrate confound, NOT the cov-pin)

Ran the pre-flight on `sha-31503cc` (current-main + cov-pin, valid image). **Every cloud window made ZERO trades** — 2022, 16yr (2010-2025), 26yr (2000-2025) all `canon=d41d8cd9` (empty), 43-45s runtime. This is NOT the cov-pin, NOT the regime, and NOT my image. Root-caused to three substrate/allocator defects:

## FINDING 1 — the cloud runs `mean_variance`; local runs `adaptive`, because a gitignored research artifact silently overrides the config allocator and is NOT baked.
`PortfolioPolicy.allocate()` calls `_apply_regime_overrides()` FIRST (policy.py:172). That method loads `data/research/allocation_recommendations.json` (`AllocationEvaluator.load_recommendations`, policy.py:120-122) and, for the current regime label, **overrides `cfg.mode`** (policy.py:140-142, "mode" is in the override key set). The artifact maps **every** regime label (`_global`, `cautious_decline`, `emerging_expansion`, `market_turmoil`, `robust_expansion`) to `mode=adaptive`.
- **Local**: artifact present → mode flips to `adaptive` → 1690 trades on 2022 (canon `0145c03a`, Sharpe 0.464 — exactly C's T-165 "regime-LIVE" cell; the COV_MVO_PROBE confirms the mean_variance branch never fires locally).
- **Cloud**: `data/research/` is in **neither `config/substrate_manifest.sha256` nor `Dockerfile.backtest`** → the artifact is **not baked** → `load_recommendations()` hits `if not path.exists(): return` (silent) → no override → `cfg.mode` stays `mean_variance` (the config value).
This is a config-vs-artifact conflict: `config/portfolio_settings.json` says `mean_variance`, a gitignored Apr-23 research artifact says `adaptive`, and locally the artifact wins. The cloud, lacking the artifact, runs what the config actually says.

**Independent corroboration (C's T-165 §2):** C displaced the artifact locally (→ mean_variance) and ran `run_isolated --year 2022` → canon **`d41d8cd9` (empty), 0 trades** — bit-for-bit identical to every cloud cell here. So "cloud = artifact-absent = mean_variance = 0 trades = `d41d8cd9`" is confirmed by C's independent local test, not just inferred. (A cloud `ARCHONDEX_COV_MVO_PROBE` cell did not emit the probe line, but that is uninformative — the 0-trade run aborts before the MVO branch reaches ≥5 returns; C's artifact-displacement test is the clean confirmation.)

## FINDING 2 — `mean_variance` produces ZERO trades on the current governor/substrate state (the re-anchor blocker).
The cov→MVO (`mean_variance`) path — where the placement lottery AND `deterministic_cov` live — yields empty canons in the cloud. The baked governor anchors have **15/21 edges soft-paused (0.25×)** + a lifecycle divergence (`low_vol_factor_v1`, `momentum_edge_v1` audit-vs-registry status_reverted). C's T-165 §2 already saw this ("mean_variance → 0 trades on 2022 current substrate; T-162 traded the day before, then the governor/substrate shifted"). **Consequence: the lottery cannot manifest and the cov-pin's cross-task determinism cannot be proven on the cloud — there are no trades.** The cov-pin remains correct and locally-proven; it is simply un-exercisable on a 0-trade path.

## FINDING 3 — SPY price data is truncated to 2020-2026 (separate substrate bug).
`data/processed/SPY_1d.csv` (and `.parquet`) = **1513 rows, 2020-04-09 → 2026-04-17** (~6 years), while KO/JPM/XOM have the full **1970-2026** (14191 rows). SPY is the benchmark + the regime daily calendar (macro_features.py:229 `daily_idx = spy.index`) + a universe essential. So 16yr/26yr are historically empty regardless of allocator — the "26yr anchor" would really be a ~2020-2026 window. Likely the T-154 "silent regeneration" class C flagged.

## What this means for the re-anchor + the director decision
T-164 was **necessary-but-insufficient** (C predicted insufficiency for regime; the deeper insufficiency is allocator-artifact-not-baked + mean_variance-0-trades + SPY-truncation). The re-anchor cannot publish durable canons until the cloud actually trades on the intended path. **The decision is which allocator the re-anchor should target — and it is NOT B's to make unilaterally (it reframes the whole T-140 lottery premise):**
- **If `adaptive` is the production-intended path** (the artifact sets it for all regimes; local + the historical "regime-LIVE" cells use it): bake `data/research/allocation_recommendations.json` (add to SUBSTRATE_FILES + Dockerfile COPY + sync) and fix SPY truncation → cloud trades like local → re-anchor on **adaptive** canons. BUT then the cov→MVO lottery + cov-pin concern a path production doesn't exercise.
- **If `mean_variance` is the intended path** (where the lottery + the T-155/T-128 anchors live — those cloud cells DID trade under mean_variance historically): diagnose why mean_variance now produces 0 trades (the governor soft-pause/lifecycle-divergence regression since T-162) + fix SPY truncation → re-anchor on **mean_variance**.

These are substrate (D) + Engine-C allocator + director-premise questions. **B has STOPPED the cloud spend** (no N≥5 — empty canons prove nothing) and surfaced the decision rather than autonomously baking the artifact or changing the allocator. Cells run: 3 dual-purpose probes (2022/16yr/26yr rep1, all empty) + 1 COV_MVO_PROBE confirmation — no wasted N≥5.
