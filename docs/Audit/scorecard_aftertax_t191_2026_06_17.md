# T-191 — after-tax layer for the deploy-bar scorecard (+ T-182 PAPER_DIR repoint)

**Date:** 2026-06-17
**Agent:** C (branch `feature/scorecard-aftertax-t191`)
**Status:** DONE. The deploy bar (GOAL.md — "beat the Schwab robo net-of-cost **AND after-tax**") now carries both halves. Measurement/tooling, autonomous-OK, no real-money path. REUSES the T-141 tax model; no parallel tax model written.

---

## 1. The problem
T-176's scorecard was net-of-cost only. A Roth dollar and a taxable dollar are not the same, and the robo comparison must be apples-to-apples **per account**. The base book's own backtest already measures this (T-141 `after_tax_detail`): taxable CAGR craters from **+11.25% (Roth) → −0.71% (taxable)** because the production book realizes **100% short-term** gains. But that model needs a fill log — the robo and DBMF lines in the scorecard are synthetic return series with no trades. So the after-tax layer here is **series-level**.

## 2. Design (reuse, don't rebuild)
- **Rates** come from the SAME source the backtest tax model uses: `config/backtest_settings.json::tax_drag_model` via `backtester.tax_drag_model.TaxDragConfig` (`load_tax_rates()`). Effective **ST 34.95%** (fed 30% + IL 4.95%) / **LT 19.95%** (fed 15% + IL 4.95%) — identical to the measured `effective_st_rate`/`effective_lt_rate`.
- **`after_tax_returns(returns, profile, rates)`** applies a **year-end tax on each year's realized positive gain**; within-year daily returns are unchanged (vol/MDD shape preserved); taxes paid reduce the capital that compounds forward; losses carry forward (no rebate), matching the T-141 "year-end synthetic withdrawal + carry-forward" semantics.
- **Per-line realization profile** `TaxProfile(realized_fraction, st_fraction)` — a turnover proxy (T-148: turnover is a tax lever ~29× the cost lever). Defaults keyed by role:
  | line | realized_fraction | st_fraction | rationale |
  |---|---|---|---|
  | `base` | 1.00 | 1.00 | the measured production reality — 100% short-term, full realization (the **3rd taxable indictment**) |
  | `combined` (base+20%DBMF) | 0.84 | 0.84 | 0.8·base + 0.2·DBMF (T-120 monthly-rebal sleeve: slow tilt, low realization, harvestable losses → more LT) |
  | `robo` | 0.20 | 0.30 | tax-efficient buy-hold (low turnover, mostly LT; some ordinary income from bond coupons) |
- **`build_scorecard(account="roth"|"taxable")`** — Roth = no tax (after-tax == pre-tax, the existing net-of-cost block); taxable = the layer applied per line by role. Overridable via `tax_profiles=`/`tax_rates=`.

**Honesty / limits (stated, not hidden):** the per-line profiles are ASSUMPTIONS. The base's *authoritative* after-tax number is its own backtest `after_tax_detail` (FIFO lots, wash-sale modelling); this series-level layer APPROXIMATES it so the robo/sleeve can be judged on the same basis. No wash-sale at the series level. Planning estimates, not tax advice.

## 3. Sample run (2022 base — the only local snapshot; the full drag shows on the 26yr base)
`python -m scripts.run_combined_scorecard --snapshots <portfolio_snapshots.csv> --account {roth,taxable}`

| line | Roth CAGR% | Taxable CAGR% | Roth Sharpe | Taxable Sharpe |
|---|---|---|---|---|
| base | 11.20 | **7.29** | 0.382 | 0.244 |
| base + 20% DBMF | 14.14 | **10.27** | 0.565 | 0.386 |
| robo:60_40 | −16.62 | −16.62 | −1.316 | −1.316 |

Reads: the after-tax layer (a) taxes the base/combined positive 2022 gains (ST-heavy → ~3.9pp CAGR drag), (b) leaves the **robo untouched** — 2022 was a loss year for 60/40, no realized gain to tax (carry-forward), (c) preserves MaxDD (year-end haircut). In this single up-year for the book the candidate still beats the robo even after tax, **but**: 2022 is a single year where the momentum book was up and the robo was down; the honest full-cycle read (GOAL.md) is base-alone likely *loses* to the robo, and after-tax the high-turnover base loses **more** ground (the 26yr `after_tax_detail` shows the −0.71% taxable vs +11.25% Roth gap). The taxable line is materially worse than Roth — surfaced, per the dispatch.

## 4. Task 2 — T-182 PAPER_DIR repoint (my bug, fixed)
T-182's `paper_loader.py` pointed `PAPER_DIR` at the guessed `data/paper/latest/`. The T-185 persistence actually writes JSONL to **`data/paper_state/`** (ledger/orders/recon) and the dead-man's-switch **heartbeat to `data/state/paper_heartbeat.json`**. Repointed both; `load_paper_run` now also reads the heartbeat so the tab shows "the loop ran today, canonical" on flat/dry days **before any fill lands** (relevant the moment E's first fill lands tonight). Verified: loaders degrade gracefully when absent; the dashboard app still constructs (APP OK).

## 5. Files
- `core/combined_candidate_scorecard.py` — `TaxRates`/`TaxProfile`/`DEFAULT_TAX_PROFILES`, `load_tax_rates`, `after_tax_returns`, `build_scorecard(account=...)`, `format_scorecard(account=...)`.
- `scripts/run_combined_scorecard.py` — `--account {roth,taxable}`.
- `tests/test_combined_candidate_scorecard.py` — 7 after-tax tests (15 total green): config-rate load, gaining-book drag, loss-year-no-tax, realization monotonicity, Roth==pretax / taxable-worse, profile defaults, format assumptions.
- `cockpit/dashboard_v2/utils/paper_loader.py` — PAPER_DIR→`data/paper_state`, HEARTBEAT_PATH, heartbeat reading.
No prod change; no flag flips; branch push only.
