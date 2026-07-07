---
task_id: T-2026-07-08-295
title: Rate-path backfill — a free historical market-implied rate baseline (+ hand-off to A)
date: 2026-07-08
worker: Agent B
branch: feature/rate-path-history-t295
status: DONE — 0 N_trials (data infra). Reconstruction baseline built; forward Kalshi archive is the live overlay.
---

# T-295 — the reconstructed rate-path baseline (for A's amended G1 gate)

**The gap this closes.** Our Kalshi KXFED rate-path archive (T-290 d2) only
started accruing 2026-07-07, so A's prediction-resolution harness starts cold.
No free FedWatch-style *archive* exists (CME sells ~1yr). But the historical
market-implied path RECONSTRUCTS from free raw ZQ (30-day fed-funds) futures and
cross-checks against the free Minneapolis Fed option-implied densities. Per
Diercks-Katz-Wright (FEDS 2026-010) Kalshi BEATS futures/surveys on the Fed path
near meetings — so **this reconstruction is the BASELINE; the forward Kalshi
archive is the better-calibrated live overlay.**

## Which series A should prefer at each date
| date range | series to use | why |
|---|---|---|
| **< 2026-07-07** | the T-295 reconstruction (`rate_path_reconstructed.parquet`) | the only free historical market-implied path |
| **≥ 2026-07-07** | the Kalshi KXFED archive (`kalshi_kxfed_snapshots.parquet`, T-290 d2) | better-calibrated near meetings (Diercks-Katz-Wright); full bucket distribution |

## `data/macro_data/alt/rate_path_reconstructed.parquet` — two series
Long-form; `series_type` discriminates. **Read the distinction — they are NOT
interchangeable** (director build-note 1):

### 1. `implied_effr_frontcont` — the DEEP historical path (USE THIS for level)
- **What:** `implied_effr = 100 − price` of the **front-continuous** ZQ future
  (`ZQ=F`). The front contract settles to the **month-AVERAGE** effective fed
  funds rate, and the continuous series **rolls monthly** — so this is a
  ~1-month-ahead implied-EFFR *level*, the honest deep baseline.
- **Depth / source:** ~10 years, **2016-07-06 → present**, daily. Source:
  Yahoo Finance `ZQ=F`. Columns: `date, price, implied_effr, source, snap_date`.
- **Validation vs FRED EFFR** (overlap ≈1963 trading days): mean |diff| **3.6 bp**,
  median **0.5 bp**, corr **0.9989**. The small mean gap is the *expected-change*
  component embedded near meetings — i.e. the signal, not error.

### 2. `meeting_prob` — meeting-dated two-outcome move probabilities (near-term only)
- **What:** per FOMC meeting (dated via the T-290 d3 `macro_calendar` module),
  the CME FedWatch **two-outcome** implied probability of a 25 bp move, solved
  from the **individual meeting-month** contract (`ZQ<code><yy>.CBT`):
  `month_avg = (n_before·r_start + n_after·r_end)/N` → solve `r_end` → `P(25bp) =
  |r_end − r_start| / 0.25`.
- **Depth:** **active meetings ONLY (~2 yr forward)** — Yahoo delists expired
  contracts, so individual-contract history does not reach the deep past. This
  series ACCRUES FORWARD via `snap_date` (like the Kalshi archive).
- **⚠ Stated limitation (verbatim):** this is a **two-outcome approximation**
  (no-change vs a single 25 bp move). It **cannot** represent a 50 bp move or the
  full bucket distribution — **that exists ONLY in our forward Kalshi KXFED
  archive.** It is also a single-meeting-per-contract-month method.
- Columns: `date (meeting), snap_date, contract, contract_price, r_start_effr,
  target_upper, implied_post_rate, implied_change_bp, prob_25bp_move, direction,
  method, source`.

## Cross-check — `fed_tracker_minneapolis.parquet`
Minneapolis Fed Market-based Probability Densities (MPD), option-implied,
vintage-stamped (`snap_date`), idempotent `_append`. **20 years, 2006-01-12 →
2026-06-03, 14,124 rows, 14 columns** (asset, date, + 12 density stats defined
in the separate `mpd_data_dictionary.csv`).

**Honest scope caveat:** the MPD assets are `LR3y3m`/`LR5y3m` (LONG-rate 3y/5y
swap densities), plus equities/commodities/FX/inflation — there is **no direct
fed-funds / SOFR short-rate probability** in this file. So it is a
**related-but-different-tenor** market-based-rate reference, **not a clean
fed-funds-path cross-check** of the ZQ reconstruction. The clean validation of
the reconstruction is therefore the **FRED EFFR check above (corr 0.9989)**; the
Minneapolis series is archived as a secondary long-rate expectations reference.

**Atlanta Fed Market Probability Tracker:** BEST-EFFORT — the data file is not
resolvable (the CQER page moved and the known xlsx paths 404). Per the task,
**Minneapolis MPD + the FRED EFFR validation suffice**; not chased further.

## Source note (a named source died)
- **stooq** (a task-named ZQ source) is now behind a JavaScript proof-of-work
  anti-bot wall — CSV endpoint returns a challenge, not data. Logged in
  `health_check.md` as a MEDIUM cross-cutting finding.
- **FRED** has the realized rates (EFFR/DFEDTARU) but NOT ZQ futures prices.
- → Yahoo `ZQ=F` + individual `ZQ<code><yy>.CBT` are the viable free source.

## Rebuild
`python -m scripts.build_rate_path_history_t295` (idempotent; safe to re-run
daily — it dedups and the `meeting_prob` series accrues forward).
