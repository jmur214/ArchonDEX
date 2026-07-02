---
name: paper-tab-degrade-patterns
description: Session theme "silent gaps must be VISIBLE" — degrade-gracefully UI patterns that worked for the Paper tab and the data realities behind them
metadata:
  type: feedback
---

For the going-live Paper run (T-182), the directive was explicit: **every panel must render a clear "no data yet / pending" state when its source is missing — never crash, never blank.** A blank panel hides a silent gap; a labelled pending state surfaces it.

**Why:** the whole session theme is "silent gaps must be VISIBLE." The system has a census/integrity layer precisely because earlier work shipped runs with edges firing 0 signals, fundamentals unloaded, etc. A dashboard that blanks on missing data re-hides exactly what the census exists to expose.

**How to apply (validated patterns):**
- Loaders return a `found`/`persisted` boolean dataclass + a human-readable `note`; the view branches on it and renders an explanatory card, not an empty figure/table.
- The **census banner** is the at-a-glance integrity signal: GREEN "CANONICAL — run clean", RED "NON-CANONICAL" + the `verdict.failures` list, GREY "No census-bearing run yet". Use `core.census.assert_census_file(path)` → `.canonical/.census_present/.failures/.warnings`. This is the most important panel — it answers "is it actually running AND clean."
- The scorecard table is a **doc-mirror, not a recomputation** — label it as such in the UI. Parse the `metric|target|status` pipe table out of the markdown; classify PASS/PENDING with a deliberately simple heuristic (empty/"pending"/"shadow"/"—" → PENDING; "must be 0" met → PASS; ≥/≤ numeric satisfied → PASS). Don't assert FAIL from a doc parse — amber-flag instead.

**Data realities (as of 2026-06):**
- The paper loop (`scripts/run_paper_day_t163.py`) writes to an EPHEMERAL `tempfile.mkdtemp()`, so `data/paper/latest/` usually does NOT exist → `load_paper_run` returns `persisted=False` in the common case. Ledger snapshot schema (last JSONL line): `{cash, positions:{tkr:{qty,avg_price}}, realized_pnl, seq, event, account}`. No live prices, so report cash + position count + realized_pnl + reconcile state, do NOT synthesise equity.
- Most `data/trade_logs/<uuid>/performance_summary.json` predate the census layer → find the NEWEST one with a non-empty `census` block; many are NON-CANONICAL (e.g. `news_sentiment_edge` blind) — that's a feature, the banner shows it.
- Equity-vs-robo: prefer `data/paper/latest/equity.csv`; else fall back to newest `portfolio_snapshots.csv` and LABEL "(backtest base — paper returns pending)". `build_scorecard(base)` from `core.combined_candidate_scorecard` is SLOW (block-bootstrap) → call with small `n_boot` (~300) and lru_cache by source-file mtime so the 2s pulse never recomputes per tick.

Related: [[dashboard-v2-idiom]].
