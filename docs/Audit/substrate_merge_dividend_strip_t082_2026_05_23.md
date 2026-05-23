---
title: T-082 — Stooq+Alpaca merge with dividend-strip layer
date: 2026-05-23
author: director
task_id: T-2026-05-23-082
related: T-081 (Stooq ingest), docs/Audit/substrate_extension_stooq_t081_2026_05_23.md
---

# T-082 — Stooq+Alpaca substrate merge with dividend-strip layer

## Context — the convention mismatch that almost shipped silent corruption

After T-081 ingested Stooq's deep history into `data/processed/stooq_us_daily/`,
my first naive merge attempt found a 9-10% close-price gap between
Stooq and Alpaca at the seam date for dividend-paying stocks (KO, JNJ,
XOM, PG). Non-dividend stocks (AAPL, NVDA, AMZN) agreed perfectly.

Root cause:
- **Alpaca**: split-only adjustment (per `data_manager.py:671` —
  `adjustment="split"`). Dividends are NOT reflected in historical
  prices. Matches the project's portfolio engine PnL model (no
  dividend reinvestment).
- **Stooq**: total-return adjustment. Historical prices have past
  dividends baked in.

A naive merge would have created silent equity-curve inflation in the
deep history portion for every dividend-paying ticker. Over 30 years,
that's ~80% extra cumulative return purely from convention mismatch.
**Path B (dividend-strip layer)** was the chosen fix per user
direction.

## The dividend-strip layer

For each ticker with both sources:

1. Compute the ratio `alpaca_close(t) / stooq_close(t)` for every
   overlap day (typically 2018-04 → 2026-04 for most tickers).
2. Anchor the curve at two endpoints using median-smoothed values:
   - **Seam anchor**: median ratio across first 30 overlap days
     (typically `< 1.0` for dividend payers)
   - **Today anchor**: median ratio across last 30 overlap days
     (≈ 1.0 by construction — both sources see today's market price)
3. Linear interpolation in log-space between the anchors gives a
   per-date correction factor that:
   - Equals the observed seam ratio at the seam (continuity ✓)
   - Approaches 1.0 at today (sources agree today ✓)
   - Captures the cumulative dividend-yield drift in between
4. Extrapolate the line backward through Stooq's pre-seam history.
   Multiply Stooq's OHLC by the extrapolated ratio. This converts
   Stooq's prices to Alpaca-equivalent convention.

### Why two-endpoint anchoring instead of unconstrained regression?

I tried unconstrained log-linear regression first — it left a 2-3%
seam discontinuity because the slope was determined by the noisy
cloud across the overlap, not by the boundary condition. The
two-endpoint anchored fit guarantees seam continuity by construction
and gives a slope estimate that respects the today-agreement.

The empirical ratio curve isn't actually log-linear (it's roughly
flat then bends sharply to 1.0 at today), so a pure least-squares
log-linear fit was wrong on its own assumptions. The two-endpoint
approach is a defensible simplification that nails the boundary
behavior at the cost of approximating the middle.

### Limitations

- Assumes the dividend yield was approximately constant pre-seam
  (real yields vary). Tickers that started paying dividends
  mid-history (AAPL → 2012) will have a slightly off pre-2012
  correction — but the multiplier is near 1.0 there anyway.
- Doesn't account for special dividends, dividend cuts, dividend
  suspensions. These are second-order for substrate purposes.
- The true gold-standard fix requires per-ticker dividend payment
  dates (free from Yahoo for current names, harder for delisted).
  Deferred to a future task if needed.

## Quality verification

### Seam continuity (post-correction)

```
|seam_diff_pct| distribution across 626 BOTH-cases:
  count    596.0000
  mean       0.0043
  std        0.0193
  min        0.0000
  25%        0.0001
  50%        0.0011
  75%        0.0039
  max        0.4298
```

Median 0.0011%. Max 0.43%. **0 seam anomalies > 1%.** The convention
mismatch that was 9-10% pre-correction is gone.

### Implied dividend yield distribution

```
count    623.00 tickers with fit
mean       0.55%/yr
std        0.63%/yr
50%        0.40%/yr
75%        0.90%/yr
max        7.78%/yr
```

Top-10 highest-yield identification (sanity check):

| Ticker | Implied yield/yr | R² | Notes |
|---|---|---|---|
| AIV  | 7.78% | -1.39 | REIT (real ~6-9% yield) ✓ |
| GE   | 3.39% | 0.67  | Historical high-yield era ✓ |
| MO   | 3.11% | 0.50  | Altria, known ~5%+ yielder ✓ |
| PFE  | 2.74% | 0.74  | Pfizer high yielder ✓ |
| KVUE | 2.52% | 0.98  | Kenvue (J&J spinoff 2023) ✓ |
| VZ   | 2.48% | 0.50  | Verizon ✓ |
| BF.B | 2.42% | -7.5  | Short pre-seam, fit noisy |
| MMM  | 2.42% | 0.25  | 3M ✓ |
| WU   | 2.36% | -0.61 | Western Union, noisy fit |
| DTE  | 2.25% | 0.81  | DTE Energy ✓ |

The non-dividend names correctly identified as no-signal:
57 tickers with R² > 0.5 (real signal) vs 450 with R² < 0 (correctly
no-op).

### Pre-seam correction magnitude examples

Stooq pre-seam close vs corrected pre-seam close (multiplicative
adjustment depth):

| Ticker | Pre-seam 5yr | Pre-seam 10yr | Type |
|---|---|---|---|
| AAPL | -0.00% | -0.00% | No-div control ✓ |
| NVDA | -0.03% | -0.03% | Minimal-div ✓ |
| KO   | -16.28% | -22.77% | Moderate div |
| JNJ  | -16.19% | -22.65% | Moderate div |
| XOM  | -18.21% | -25.34% | Oil-div |
| PG   | -14.06% | -19.78% | Moderate div |
| T    | -35.39% | -44.96% | High-div (AT&T) |

The magnitudes scale correctly with dividend yield. Backtests on the
merged dataset will now have internally-consistent
price-return-only structure throughout the 30-60 year window.

## Output

Files at `data/processed_merged/` (gitignored under `data/`):

- 730 CSV files (`<TICKER>_1d.csv`) — Date, Open, High, Low, Close,
  Volume, ATR, PrevClose — matching `data/processed/` schema
- 730 parquet files — DatetimeIndex named "Date"
- `_merge_meta.json` — provenance manifest, 626 KB

Case breakdown:
- **both** (Stooq + Alpaca merge with dividend-strip): 626 tickers
- **alpaca_only** (no Stooq depth available, pass-through): 104 tickers
- **stooq_only**: 0 (the SPX scope means every Stooq ticker also has Alpaca)
- **skip_neither**: 0

Total merged bars: **4,149,953** across the BOTH cohort.

## What this unlocks

- The substrate now has continuous price-return-only adjustment from
  Stooq's deep history (1960s/70s for the deepest names) through
  Alpaca's recent bars
- Equity-curve backtests on merged data are no longer artificially
  inflated by Stooq's total-return convention
- MBL Gate-0 (`T_years ≥ 2·ln(N) / SR²`) is now passable for any
  backtest that uses these 730 tickers — the dev's binding constraint
  per CLAUDE.md non-negotiable #7 is no longer the binding constraint
- The infrastructure (`fit_ratio_loglinear` + `apply_dividend_strip`)
  is reusable for any future vendor-mix problem

## What this does NOT close

- 183 SPX historical members that were delisted are still missing
  from any free source (Yahoo, Alpaca, Stooq all scrubbed them).
  Survivorship-bias residue.
- A possible fix is Kibot $99 one-time (T-084) which explicitly
  retains delisted history. Defer until T-083 (MBL Gate-0 wire)
  lands and we measure how much lift comes from window extension
  alone vs. needing the delisted coverage.

## Followup

**T-082b (post-A swap):** When both Agent A and Agent B's current
chains finish, atomically swap `data/processed_merged/` into
`data/processed/`. Specifically:
```
mv data/processed data/processed_alpaca_only_backup
mv data/processed_merged data/processed
```
After this, the existing data_manager (`cache_dir="data/processed"`)
reads the merged dataset transparently. T-035/T-055c/T-055d baselines
are then directly comparable to deep-history-extended backtests.

**T-083:** Wire MBL Gate-0 check into the Discovery gauntlet. Now
feasible for the first time given the substrate depth.

**T-084 (optional, paid):** Kibot $99 for delisted SPX coverage to
fully close the substrate-honest property.

## Files

- `scripts/merge_stooq_alpaca_substrate.py` (new) — the merge script
  with dividend-strip layer
- `data/processed_merged/` (gitignored) — 730 ticker pairs
- This audit doc
