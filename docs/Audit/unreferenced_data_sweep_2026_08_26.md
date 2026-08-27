# Unreferenced-data sweep — 1.1 GB archived, 811 MB deliberately KEPT

**Date:** 2026-08-26 · **Agent:** B · LOW-priority queue item · `[NN-ARCHIVE]` (moved, never deleted)

## Archived
`data/research/wfo_train` (556 MB, 123 run dirs) + `data/research/wfo_test` (546 MB) →
**`data/Archive_wfo_runs_2026_08_26/`**. Engine D walk-forward outputs stamped 2026-01-26.

Verified dead before moving: **zero references** to `wfo_train`/`wfo_test` in any
`.py`/`.json`/`.yml`/`.sh`. Every `wfo` hit in the codebase resolves to the *module*
`engines/engine_d_discovery/wfo.py`, not these directories. Regenerable Discovery output.
`data/research/wfo_summary.json` (4 KB) **left in place**.

Effect: `data/research/` **1.7 GB → 639 MB**. No tracked file touched.

## ⚠ Destination correction
The dispatch said "→ `Archive/`". **Repo-root `Archive/` is TRACKED in git** (106 tracked
files). Moving ~1.1 GB there would have committed gigabytes of otherwise-gitignored data,
against "never commit large data files". Used the existing `data/Archive_*` precedent
(cf. `data/Archive_earnings_finnhub_2026_04_25`), which stays inside the gitignored `data/`
tree. Flagging so the convention is explicit next time.

## KEPT — `data/processed_alpaca_backup_2026_05_23` (811 MB)
**Do not archive this yet.** Checking whether it was redundant is what surfaced an open HIGH
defect, and it is the forensic record of that defect.

Every file in it is exactly **1,513 rows from 2020-04-09** — the pre-backfill Alpaca-only
substrate. Diffed against `data/processed/`:

| | |
|---|---|
| identical ticker sets | 730 vs 730, **zero** either-way difference |
| **still byte-matching the shallow backup** | **12 of 730** |
| the 12 | `DBC, DKNG, EEM, GLD, IEF, IWM, MARA, QQQ, RIOT, TLT, USO, UUP` |
| **load-bearing among them** | **`DBC, GLD, IEF, IWM, QQQ, TLT`** |

**The deep-history backfill of `data/processed/` was PARTIAL and nothing detects it.** SPY
(1993+) and AAPL (1984+) *were* deepened — which is exactly why the truncation is invisible:
the headline tickers look fine while the sleeve/regime ETFs are still 2020-onward.

Any consumer reading `data/processed/<T>_1d.csv` over a deep window silently gets a 2020-04
truncation on those 12. **The HMM's `tlt_ret_20d` blindness (same-day finding, 82% of the
panel NaN) is one instance of this, not the whole defect.**

Deep, dividend-reconciled versions of all six critical tickers already exist in
`data/processed/tr_reconciled/` (GLD/TLT to 2005-02-22) — the fix is a **repoint or a
completed backfill, not data acquisition**. Logged HIGH in `health_check.md`.

The backup stays until that is resolved: it is the only record of which tickers were left
behind, and 811 MB is a cheap insurance premium against re-deriving it.

## Not touched
`data/edgar/` (2.7 GB) — per the dispatch, `edgar/sections` has a future consumer in the
parser repair. `data/raw/` (1.8 GB), `data/intel/` (539 MB), `data/trade_logs/` (360 MB) —
not in scope, not audited here.
