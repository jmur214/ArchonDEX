# T-256 — THE DATA UNLOCK: manifest & provenance (Wave 0)

**Date:** 2026-07-02 · **Agent:** C · Branch `feature/data-unlock-t256` · **0 N_trials** (data engineering)
Turns the gap audit's "data walls" (`whole_project_gap_audit_2026_07_02.md` Part 3) into substrate. The actual data lives under the gitignored, symlinked `data/` (shared with the main worktree → already preserved there); this doc is the version-controlled provenance record. Regenerate via the committed scripts.

## Part 1 — Stooq deep-ETF ingest (`data/processed/stooq_us_daily/`)
`scripts/ingest_stooq_us_daily.py --tickers <list>` (added a `--tickers` arg — reusable ETF scope). 33 ETFs ingested from the on-disk 1.7GB Stooq bundle, 100% hit rate. Canon-safe: writes the `stooq_us_daily/` namespace; the canonical `data/processed/{SPY,AGG,GLD}_1d.csv` bytes are UNTOUCHED. Windows: QQQ 1999+, GLD/TLT/IEF/LQD/EFA/VNQ/sectors 2005+, DBC 2006+, HYG/BND/BIL 2007+, XLRE 2015+, XLC 2018+, DBMF 2019+, KMLM 2020+ — all → 2026-05-22.

## Part 2 — TR reconciliation (LOAD-BEARING) → `data/processed/tr_reconciled/`
`scripts/reconcile_stooq_tr_t256.py --asof 2026-05-23 --tickers <list>`. Per the T-167 yfinance-splice pattern: TR series = yfinance Adj Close (O/H/L × AdjClose/Close), cross-checked against the on-disk Stooq split-adj close via a **split-jump detector** (max |daily-return divergence|; gradual dividend drift is EXPECTED, a split misalignment is a jump). **33/33 reconciled, 0 price_only, 0 fetch_failed.** Manifest: `data/processed/tr_reconciled/_tr_manifest.json`.

**The TR gap is real and validates the audit** — this is the dividend the split-only Stooq data was silently missing (%/yr):

| ticker | TR gap %/yr | ticker | TR gap %/yr | ticker | TR gap %/yr |
|---|--:|---|--:|---|--:|
| HYG | 3.38 | LQD | 2.48 | AGG | **2.03** |
| DBMF | 3.52 | VNQ | 2.18 | TLT | 1.25 |
| TIP | 2.11 | BND | 1.64 | EFA | 1.40 |
| XLP/XLU | ~1.1–1.2 | **SPY** | **0.685** | GLD/VIXY/SVXY | 0.00 |

- **AGG 2.03%/yr** matches the audit's measurement exactly (Stooq +1.0% vs true TR ~3.0% → ~2% gap). **SPY 0.685%/yr** matches the audit's "sleeve flat-leg ~0.65%/yr understated" headline. GLD/VIXY/SVXY = 0.00 (no dividend — correct). Income/bond ETFs miss the most; this is precisely the bias that would corrupt any carry / total-return study.
- All jumps < 0.12 (< 0.20 tol) → no split errors. FAIL-CLOSED path proven in-run (an over-strict first pass flagged AGG price_only; the corrected split-jump gate reconciled it — the guard fires, then passes on real evidence).

## Part 3 — free fetches (`data/macro/`, `data/raw/cboe/`) — delegated, verified
| dataset | window | source | file |
|---|---|---|---|
| VVIX | 2007-01-03 → 2026-07-01 | yfinance `^VVIX` (never ingested before) | `data/macro/VVIX.parquet` |
| VIX / VIX3M / VIX6M / VIX9D | 2002 / 2006 / 2008 / 2011 → 2026-06/07 | yfinance | `data/macro/VIX*.parquet` |
| SKEW | 1990-01-02 → 2026-07-01 | CBOE CDN | `data/macro/SKEW.csv`(+parquet) |
| Shiller ie_data (P/D/E/CAPE) | 1871 → 2024-09 | Shiller xls (new `scripts/fetch_shiller_ie_data.py`) | `data/macro/shiller_ie_data.csv` |
| CBOE PUT/BXM/BXMD/CLLZ/CMBO/PPUT | 1986/1991/2002 → 2026-07-01 | CBOE CDN | `data/raw/cboe/<SYM>_cdn.csv` |
| CBOE master (1986-2019 daily) | 1986-06-30 → 2019-07-26 | **Wayback xls MIRROR** (load-bearing) | `data/raw/cboe/dailypricehistory_wayback_19862019.xls` |

Caveats (real data limits): VVIX starts **2007** on yfinance, not 2006; `^VXV` delisted → `^VIX3M` (2006+) used. CBOE strategy indices: CDN vs Wayback are on **different base levels** → any future splice must chain by **RETURNS, not price levels**; PUT CDN is sparse pre-~2007 (use the Wayback xls for the dense 1986-2006 daily).

## Part 4 — staleness refresh
VIX-family re-pulled to a common as-of (2026-06/07), aligned with the TR-reconciled ETFs (2026-05). No stale vol-complex remains at the fetch-flag level.

## Part 5 — stale DATA-GAP docstrings corrected (docs-for-AI)
`hyg_lqd_spread.py` (HYG/LQD "not available" → now TR-reconciled 2007/2005), `vix_change_5d.py` (VIX9D/VIX3M "not cached" → now in `data/macro/`), `faber_multi_asset_trend.py` ("T-052 lacks EFA/AGG/VNQ" → all five now deep + TR-reconciled). Docstrings only; feature code + canon untouched. Each notes that repointing the loader to the new data is a follow-up, not done here.

## What each unlock re-opens
- **Multi-asset carry, 21–24yr (T-247 re-test):** the "DATA-BLOCK" was the 2020-04-09 processed truncation — gone. TR-reconciled AGG/TLT/IEF/LQD/HYG/TIP/BND/GLD/DBC/EEM/EFA/VNQ back to 2005-2007 drop the multi-asset-carry MBL bar from ~1.36 (unclearable) toward ~0.68-0.73. (Bond-carry H0 does NOT reopen — it was measured on 2003+ AGG.) **Requires the TR-reconciled files, never the split-only Stooq.**
- **Vol-complex conditioning:** VVIX (2007+, first ingest), VIX term-structure state (2006+), SKEW (1990+) — the evidence-ranked #2/#3 conditioning inputs (audit Part 4). Continuous 0.5-1.5× tilts, NEVER gates (T-220/T-221/T-233).
- **Put-write / income-leg substrate:** CBOE PUT/BXM/BXMD/CLLZ/CMBO/PPUT full-cycle (the "options = paid data" exclusion was wrong at the strategy-index level) — enables the income-leg screener before committing the 3rd sleeve slot (audit Part 4).
- **Carry equity leg:** Shiller earnings/dividend yield completes the equity-carry input.

**T-256 done.** Data engineering, 0 N_trials, no canon change.
