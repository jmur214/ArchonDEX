# 00 — What the machine is (Phase 0, from code, 2026-09-30)

> Alpha-frontier review, branch `research/alpha-frontier-2026-09-30`. One page. Every
> claim is from code read this session (file:line), not from docs. Where docs and
> code disagree, the disagreement is named.

## Universe and data
- **Backtest universe:** 109 hand-listed tickers, today's mega/large caps plus recent
  IPOs (COIN, PLTR, MARA…), no delisted names (`config/backtest_settings.json:5-115`);
  `use_historical_universe: false` (`:165`). A point-in-time S&P 500 membership swap
  exists (`orchestration/mode_controller.py:804-863`, `engines/data_manager/membership.py`)
  and several cloud measurement scripts hardcode it on; the default CLI path does not.
  Window 2021-01-01 → 2024-12-31 (`:3-4`). A 26-yr "canonical" equity substrate
  (Alpaca 2020+ spliced onto Stooq, split-only) and a 1926+ index-level multi-decade
  substrate (T-306) exist for research scripts; neither is the default.
- **Prices are price-only.** Alpaca `adjustment="split"` (`engines/data_manager/data_manager.py:756`),
  yfinance fallback forced split-only (`:85-100`), no dividend crediting anywhere in
  `backtester/` or `engines/engine_c_portfolio/`. Benchmarks prefer dividend-reconciled
  files (`core/benchmark.py:100-104`). So every equity-book Sharpe is a price-only
  strategy vs a total-return SPY.
- **Non-price data wired into Engine A:** SimFin free fundamentals (~2020+, 4 value/
  accruals edges), OpenInsider Form 4 (641 tickers), FRED macro (edges retired), yfinance
  earnings dates (PEAD family), VADER news CSVs (edge weight key never matches its ID).
  Archived with **no Engine A consumer:** 6.89M-row SEC Form 4, 13F panel, 8-K panel,
  10-K similarity panel, 771k-article news panel, FINRA short data, SEC FTD, T-265
  survivorship-complete small-cap panel (4,674 tickers, 2016+), CEF daily panel,
  minute features. `data/` is gitignored and absent in this container; S3 layout is
  reconstructed from code, not listed.

## Signal families (Engine A, 50 modules)
Momentum (MA-cross, 12-1, 6-1, cross-sectional), mean-reversion (Bollinger, RSI, gap,
panic, pairs, short-term reversal), value/quality/accruals (SimFin), events (PEAD ×3,
earnings-vol, insider cluster, dividend initiation, spinoff), macro (5, retired),
breadth/herding, calendar/seasonality, low-vol/BAB, overnight, news sentiment, and
GA-generated composites over a 35-feature foundry (18 non-price features: 7 FRED, 9
calendar, 1 CFTC, 1 earnings-proximity; zero fundamentals, zero text). Long/short
signals exist in code; the production allocator zeroes every short (`min_weight: 0.0`,
`config/portfolio_settings.json:6`, clip at `engines/engine_c_portfolio/policy.py:329`).

## How a signal becomes a position
Per bar: signals with `side != none` → score = strength × sign → Engine C mean-variance
over **only the names that fired this bar**, Σw = 1, clip to [0, 0.30], no renormalize
(`policy.py:248, 322-330`; `optimizer.py:86, 118`) → Engine B target-weight delta order
if |Δ|/target ≥ 5% (`engines/engine_b_risk/risk_engine.py:1094-1110`) with ATR stop 1.8×
and take-profit 2.5× on every entry (`:1389-1394`, `config/risk_settings.prod.json:6-7`),
trailing stop 1.5 ATR on by default (`:61-63`), no off-switch for stops. Fill at next
open with a flat 1 bp half-spread (single-row Series → `engines/execution/slippage_model.py:316-319`);
impact model implemented but unreachable. Stops fill at the stop level on gap-throughs
(`backtester/execution_simulator.py:445-450`). Sizing equity = `portfolio.capital`
(set once to initial capital, `backtester/backtest_controller.py:158, 325`) + market
value (`:647`) — not cash + MV — which is the mechanism behind the documented 1.7–2.3×
gross and negative cash. Idle cash earns 0% (`portfolio_engine.py:90, 353`). Borrow cost
is a post-hoc curve-B annotation, not in fills.

## How a position becomes a P&L number
Equity = cash + MV (`portfolio_engine.py:353`); daily `pct_change` → Sharpe = mean/std·√252
with rf = 0 (`core/metrics_engine.py:103-114`); block bootstrap = fixed-length moving
block, block = max(5, n^(1/3)) ≈ 14–25 days (`:923, 940-950`) — not Politis-White as
CLAUDE.md says; ci_low = 2.5th percentile; 500 iterations on the backtest path
(`backtest_controller.py:1166-1173`).

## How a P&L number becomes a verdict
- **Discovery (Engine D):** 9 gates in `validate_candidate` (`discovery.py:948-1857`):
  MBL pre-flight (fails open to N=1 without the registry), Gate 1 contribution > +0.10
  Sharpe vs the incumbent 6-edge book through the full backtester above, PBO ≥ 0.60,
  WFO (metric only), permutation p < 0.05 (null is a point mass — `significance.py:84`),
  universe-B > 0, FF5+Mom α (report-only), substrate-B, DSR ≥ 0.95 at N = batch size.
  Production passes `significance_threshold=None` and then **overwrites** the verdict:
  promote iff ensemble Sharpe > 0 ∧ PBO ≥ 0.7 ∧ BH-reject of the degenerate p
  (`mode_controller.py:1338, 1397-1403`). Recorded history: 93/93 candidates died at
  Gate 1; 0 promotions ever.
- **Governance (Engine F):** retire an active edge when block-bootstrap `ci_low` of its
  per-trade dollar-PnL Sharpe (annualized by √252 regardless of trade frequency) is
  below SPY-total-return Sharpe − 0.3 (`lifecycle_manager.py:267-275, 742-745`); promote
  on the same threshold (no hysteresis). Factor-α retirement gate is inert (no
  `factors=` passed, `governor.py:653-656`).
- **Program-level verdicts** (sleeve, tilts, leverage) come from standalone research
  scripts on the T-306 substrate with the T-bill rate credited to cash — a different
  cash convention from the equity backtester — and a `ci_low` rule that, applied to a
  SPY-shaped 12-yr series, returns ≈ 0.2–0.3.

## What the deploy candidate actually holds
Account-2, live since 2026-09-15: **85% VOO / 15% MTUM / SGOV as cash**, machine-executed
market orders, Rule-B contributions, single-account wash guard. It is the S&P 500 with
a long-only momentum tilt. Its terminal-wealth edge over SPY is bounded by the 15%
sleeve's excess return; nothing produced by Engines A/D/F is in it.
