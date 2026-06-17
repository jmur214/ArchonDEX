---
task_id: T-2026-06-16-175
title: SimFin fundamentals drift — root cause, reconciliation, and the simfin-blind re-anchor finding
date: 2026-06-16
worker: Agent B
branch: feature/simfin-reconcile-t175
---

# SimFin drift reconcile (T-175)

## Bottom line
The recurring simfin manifest-drift and the "foreign writer" are explained, and a **bigger latent defect** surfaced: `data/processed/fundamentals_simfin.parquet` is the panel the 4 active value/accruals edges consume, but it was **unmanifested + not reliably baked + cannot be regenerated under hermetic** → those edges ran **blind in the cloud**, including in the T-140-fu3 re-anchor. Reconciled by pinning the (reproducible) canonical parquet into the manifest.

## 1. The "foreign writer" — not external
`engines/data_manager/fundamentals/simfin_adapter.py::build_and_cache()` writes `data/processed/fundamentals_simfin.parquet` (PROCESSED_PATH). It is called by `load_panel()`, which `_fundamentals_helpers.get_panel()` invokes for the 4 active simfin edges (`value_earnings_yield_v1`, `value_book_to_market_v1`, `accruals_inv_sloan_v1`, `accruals_inv_asset_growth_v1`). So **any local backtest run that exercises those edges (with a SIMFIN_API_KEY present) lazily regenerates the parquet into the shared `data/processed/`**. That is the "foreign" writer the director + D saw mutating the shared dir — a runtime cache side-effect, not an external process.

## 2. The deeper defect — the panel can't load under hermetic
`load_raw_panels()` calls `_ensure_simfin_configured()`, which **raises `RuntimeError("SIMFIN_API_KEY not set")` unconditionally** when no key is present — even though `sf.load_income(...)` then reads the *cached* CSVs from disk (no network). So:
- Under hermetic (cloud), there is no key → `build_and_cache` cannot rebuild → `get_panel()` catches the exception (`_fundamentals_helpers.py:90-92`) and returns `None` → **the 4 edges silently degrade to no-signal.**
- Therefore the parquet **must be baked** for the cloud edges to work. It was **NOT** in the manifest and **NOT** in the `be219d7f` S3 substrate (I had archived it in T-140-fu3 UPDATE-4, mis-reading it as a freely-regenerable cache). **The T-140-fu3 re-anchor cloud cells ran simfin-blind** (the 26yr trades show 0 occurrences of any of the 4 edges).

## 3. Impact — MATERIAL
Clean local A/B on 2022 (hermetic, mean_variance), parquet present vs absent:

| | canon | Sharpe | simfin fills |
|---|---|---|---|
| panel LIVE (parquet present) | `80b501a8` | **0.537** | 161 |
| panel BLIND (absent + no key) | `68841b0f` | **0.21** | 0 |

**Δ +0.33 Sharpe** from the 4 edges on local-2022 — different canon, materially different metric. (Local arch ≠ cloud arch, so this is not the cloud delta; the cloud re-anchor blind-2022 canon was `eb48742e`/1.512. But it proves the edges move the book non-trivially.) **The T-140-fu3 anchors (2022 `eb48742e`, 16yr `3e9ea427`, 26yr `158fe678`) are a degraded 17-edge book and should be RE-RUN with the panel baked.**

## 4. Reconciliation (the "re-pin with provenance" option)
- The parquet is **byte-reproducible**: `build_and_cache(force=True)` from the manifest-tracked raw simfin (`data/raw/simfin/*.csv`, `us-income = 50b418a5…`) produces hash **`9ab68608…`** — **identical to the `data/processed_alpaca_backup_2026_05_23/` copy** (confirms the backup is canonical + the raw vintage is unchanged since 05-23).
- **Action:** restored the canonical parquet to `data/processed/` (mtime newer than raw so the freshness check returns it without rebuild) and **regenerated the manifest to include it**: `be219d7f` (14118 files) → **`6e36e42d`** (14119 files); the diff is exactly one line (the parquet). It is now tracked → baked → verified.
- **Why this is robust:** the parquet hash is reproducible, so a future runtime regen (same raw) yields the same hash → verify still passes (no spurious drift). If the raw simfin is ever *deliberately* updated, the regen hash changes → verify fails **loudly** (the correct signal to re-`generate` + re-bake the panel). The recurring whack-a-mole is resolved: the file is no longer "EXTRA".
- The `data/processed_alpaca_backup_2026_05_23/` dir is treated as read-only reference (NOT deleted); it is already `.dockerignore`d (`data/processed_*backup*/`).

## 5. Follow-ups
- **RE-RUN the re-anchor** on a panel-baked image (new manifest `6e36e42d` → re-sync S3 + rebuild + N≥5). The cov-pin determinism finding STANDS (lottery dead); only the anchor *values* change (the simfin edges rejoin). Flagged to director — it's a ~9h spend.
- **PROPOSE (propose-first, data_manager):** relax `_ensure_simfin_configured` to not require the key when the cached CSVs already exist (offline read), so the panel can rebuild under hermetic if the baked parquet's freshness check ever fails — belt-and-suspenders against silent blinding. Not implemented unilaterally.
- **Provenance/stooq in the backup** (`_data_provenance_*.json`, `stooq_us_daily`) are pre-Alpaca-migration artifacts superseded by the Alpaca substrate; their absence from live is the migration, not a loss (orthogonal to simfin).
