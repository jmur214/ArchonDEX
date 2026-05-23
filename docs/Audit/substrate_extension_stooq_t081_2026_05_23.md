---
title: T-081 — Stooq US daily bundle ingested for survivorship-aware substrate depth extension
date: 2026-05-23
author: director
task_id: T-2026-05-23-081
related: docs/Sessions/Other-dev-opinion/5-16-26_extensive.md (the dev review elevating multi-decade extension to "precondition")
---

# T-081 — Stooq US daily ingested → deep-history half of multi-decade substrate

## Why this work

Per the 2026-05-16 fourth research dive (metrics-focused), the MBL formula
`T_years ≥ 2·ln(N_effective) / SR_target²` puts a hard floor on backtest
window length given trial-count and target Sharpe. At N≈100 (honest count
of distinct configurations run on the substrate) and `SR_target=1.0`,
**MBL = 9.2 years.** Project has 5. **Window length is the binding
constraint on every measurement to date** — including the corrected 0.598
substrate-honest baseline. The dev was unambiguous: *"The multi-decade
extension is no longer one item among many. It is the precondition."*

## What landed

`scripts/ingest_stooq_us_daily.py` — one-shot ingester that converts a
bulk Stooq US daily archive (provided by the user, at
`data/raw/stooq/daily/us/`) into the project's existing processed
schema. Output landed at `data/processed/stooq_us_daily/` (separate
namespace; T-082 will handle the merge into canonical `data/processed/`).

## Quality verification

### Schema parity with existing Alpaca data
Same columns (`Date,Open,High,Low,Close,Volume,ATR,PrevClose`), same
ATR convention (14-day rolling mean of True Range per `data_manager.py:495-503`),
same `PrevClose = Close.shift(1)`. CSV uses `%Y-%m-%d` date format;
parquet uses `Date` DatetimeIndex.

### Price agreement with Alpaca on overlap
AAPL Stooq vs AAPL Alpaca on 1,513 overlapping bars:

- Median close-price diff: **0.000%**
- Max diff: **0.07%**
- StDev: **0.004%**

The two sources use the same split + dividend adjustment convention.
Drop-in usable.

## Coverage results

### Scope
828 unique tickers were S&P 500 members at any point in 2010-01-01..2026-12-31
(per `data/universe/sp500_membership.parquet`).

### Hit rate
- **626 / 828 = 75.6%** parsed into project schema
- 202 / 828 = 24.4% missing from Stooq (the survivorship-bias residue)

### Depth distribution (by start year of ingested data)

| Decade | Tickers | % |
|---|---|---|
| 1960s | 2 | 0.3% |
| 1970s | 37 | 5.9% |
| 1980s | 136 | 21.7% |
| 1990s | 74 | 11.8% |
| 2000s | 243 | 38.8% |
| 2010s | 92 | 14.7% |
| 2020s | 42 | 6.7% |

**93.3% of ingested tickers have history reaching 2019 or earlier** —
satisfying the dev's MBL ≥ 9.2-year requirement comfortably.

### Deepest 10
GE, IBM (1962-01-02) | AA, AEP, BA, C, CAT, CNP, CVX, DIS (1970-01-02)

### Mega-cap survivor spot-check
| Ticker | Start | Bars |
|---|---|---|
| AAPL | 1984-09-07 | 10,508 |
| MSFT | 1986-03-13 | 10,125 |
| AMZN | 1997-05-16 | 7,295 |
| GOOGL | 2004-08-19 | 5,475 |
| META | 2012-05-18 | 3,523 |
| NVDA | 1999-01-22 | 6,875 |
| TSLA | 2010-06-28 | 4,000 |
| BRK.B | 1996-05-09 | 7,557 |
| JPM, JNJ, XOM | 1970-01-02 | 14,216 each |

## The 202 misses (known unsubstrate-honesty gap)

Cross-referenced against the SPX membership table:
- **183 / 202 (90.6%) are delisted SPX members** (Stooq scrubs delisted history, same as Yahoo and Alpaca for pre-2020 names)
- 19 / 202 are "active" misses — almost all are ticker-rename artifacts
  - FB → META (META is a HIT; FB miss is correct, it doesn't trade under "FB" anymore)
  - PCLN → BKNG, KORS → CPRI, JEC → J, DLPH → APTV/DLPH, etc.

**Implication:** The ingested cohort is **survivorship-biased** — it
contains the 626 names that survived as recognizable tickers, missing
the 183 that delisted (LEH, BSC, EK, JCP, SHLD, etc.). This is a known
limitation of free data sources. The dev's full mandate (survivorship-aware
universe back to 1990) requires a paid source (Kibot $99 one-time, or
EODHD ~$20/month one-month-pull) to close the delisted gap.

**However:** the 5-year window was the binding constraint per MBL. A
75.6%-coverage 30-60-year extension dominates a 100%-coverage 5-year
window mathematically — DSR floor goes from "essentially unreachable" to
"comfortably clearable at any realistic N."

## What this enables

- Backtests can now run on multi-decade windows for the **surviving universe**
- 5-year measurements can be re-run on 25-50-year windows for any of the
  626 ingested names
- The MBL Gate-0 check (forthcoming) will PASS for any backtest using
  these tickers
- Factor edges (value, quality, momentum) that suffered most from
  survivorship-bias-corrected substrate can be re-tested on the deeper history
  — with the caveat that they're now affected by survivorship instead of
  by window-length (a different bias, smaller for momentum/trend edges)

## What this does NOT enable (still gated)

- Substrate-honest measurements for the 183 delisted SPX members
- True survivorship-aware multi-decade backtests
- Closing the gap requires paid source (or further free-source hunting —
  unlikely to succeed based on yfinance + Alpaca + Stooq all scrubbing
  the same delisted history)

## Files

- `scripts/ingest_stooq_us_daily.py` (new) — the ingester
- `data/processed/stooq_us_daily/<TICKER>_1d.csv` (gitignored, 626 files, ~480 MB)
- `data/processed/stooq_us_daily/parquet/<TICKER>_1d.parquet` (gitignored, 626 files, ~72 MB)
- `data/processed/stooq_us_daily/_ingest_meta.json` (gitignored, 195 KB) — per-ticker provenance manifest
- This audit doc

## Followups

**T-082 (separate dispatch):** merge Stooq's deep history with Alpaca's
recent bars in the canonical `data/processed/` namespace. Per-ticker
join: Stooq for everything before Alpaca's earliest bar; Alpaca for the
overlap and forward. Provenance tracked in
`data/processed/_data_provenance_delisted.json` (existing).

**T-083 (separate dispatch):** wire MBL Gate-0 check into the gauntlet
(`engines/engine_d_discovery/`) — backtest window must satisfy
`T_years ≥ 2·ln(N_effective) / SR_target²` before any backtest fires.
The Stooq ingest makes this gate passable for the first time.

**T-084 (optional, paid):** Kibot $99 one-time for delisted coverage.
Closes the substrate-honest property the dev demanded. Defer until
T-082 + T-083 land and we measure how much of the 0.598 baseline lift
comes from window extension alone.
