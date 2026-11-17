---
name: stooq-transient-blocks
description: Raw Stooq has 4,517 transient level offsets (one dividend, revert within days; 2008-05-07 x214, 2013 month-ends x85) that fool ex-date probes and year-end returns; plus yfinance quirks (empty dividends for delisted, dropped live names)
metadata:
  type: reference
---

**Stooq transient blocks** (measured 2026-11-11 vs yfinance TR, 1995+): runs of bars sitting ~one quarterly
dividend off the reference that revert within ≤15 bars — 4,517 blocks over 414 names. Biggest dates:
2008-05-07 (214 names), 2009-01-23 (162), 2011-03-21 (102), 2013-06-28/08-30/09-30/10-31/11-29 (~85 each),
2013-12-03, 2013-12-19→2014-01-03 (sits ON the 2013 year-end), 2015-03-12 (76), 2012-04-05 (69).
Detector: `transient_offsets()` in `scripts/drip_fix_candidate_t384.py` (|d|>0.25 %, undone within 15 bars
to 15 %). They live in raw Stooq, the cache and any candidate that keeps Stooq returns.

**Probe-design lessons (T-384, the obvious optimisation that backfired):**
- An ex-day ±1 window sum is fooled when a block reverts inside it (v1 double-added AEE/HD/PEP 2013).
- Widening to 5-bar medians each side (v2) fixed 2013 but made σ(m) √(10/3)× larger → noisy 2000–01
  ex-dates lost measured labels → fell to the global rule → p95 0.14→0.41. Fix = keep the 3-return
  window, only move an endpoint to the nearest CLEAN bar (v3). Measure noise cost before widening.

**yfinance quirks:** `Ticker(sym).dividends` returns an EMPTY series (no error) for a delisted symbol —
never read it as "non-payer" without prices. Yahoo answers "possibly delisted; no price data found" for
names it dropped in 2026 (AVB, EA, EQR, HOLX, LEG, QRVO, CTRA, ABMD). SATS/BBBY/PSKY now map to recent
securities with months of history (identity check by overlap length catches it). Dividend index can be
tz-aware even when empty — normalise unconditionally.

**Repo lock:** any new script that reads `data/processed/<T>_1d.csv` per ticker must go through
`resolve_universe`/`withhold_declared_tickers` or carry `# ticker-exclusions: bypassed — <reason>` within
2 lines above the read (`tests/test_processed_globbers_2026_10_15.py`).
