---
task_id: B-1
title: Pre-registration — raw-signal decile re-evaluation of the foundry features + cross-sectional Engine A edges
date: 2026-09-30
worker: Agent A (prereg); the RUN is staffed separately (likely C after RR-1)
branch: research/raw-signal-decile-b1
status: DRAFT — awaiting director FREEZE before any run. Nothing has been run. N_trials per §9.
---

# B-1 — does the price vocabulary have anything, tested the way the literature tests it?

## 1. The question (H1 verbatim from the brief)

Every foundry feature was previously tested as a single-gene long `CompositeEdge` bolted onto the
6-edge book, through the full backtester, under the RR-1 sizing defect and a Gate 4 with no power.
None was ever evaluated as **rank → decile → monthly rebalance** — the construction the anomaly
literature uses. B-1 does that.

**H1 (brief, verbatim):** at least one non-calendar signal has BH-adjusted IC p < 0.05 **AND**
25%-satellite Δ log wealth `ci_low > 0` on 2000–2025.

**Refutation (brief):** zero signals meet both ⇒ "exhausted price vocabulary" is confirmed on the
construction the literature uses. **§3 narrows what that sentence can honestly claim** — read it
before the freeze.

B-1 runs in a **standalone harness** (the T-249 / T-311 / T-318 pattern), not through
`BacktestController`, so it is not blocked on RR-1.

## 2. THE HARD PRE-COMMITMENTS (the anti-overfit controls)

1. **No sign flipping.** Each signal's sign is declared in §4 on the **raw value the code computes**
   (not on the feature's name — `reversal_1m` is the raw past return, so its sign is −). A signal
   that "clears" in the opposite direction is reported as **not clearing**, never flipped.
2. **Orientation check before any return exists.** If panel build finds an Engine A edge's native
   score oriented against its declared literature claim, the harness **stops and escalates** — the
   sign is never corrected silently. No return has been computed at that point, so nothing leaks.
3. **No signal added or removed after the run** — the inventory in §4 is closed at freeze.
4. **No window shopping.** 2000-01 → 2025-12 for the main family; the one sensitivity window in
   §7 is pre-named here and cannot become the headline.
5. **Construction frozen:** deciles (not quintiles/terciles), equal weight, month-end rebalance,
   one-month hold, 10 bps round trip, 50 bps/yr borrow on LS shorts. No weighting-scheme search.
6. **Nothing is deployed from B-1.** Any survivor goes to RR-6's Gate 1′ under the corrected
   referee *and* to a survivorship-complete re-verification (§3.6) first.

## 3. Pre-run findings that change the construction (measured today — proposals for the FREEZE)

These were found while preparing the prereg, by execution against the real code and data. Each
comes with its evidence and a proposed treatment. **The director rules on each at freeze.**

### 3.1 17 of the 35 foundry features are MARKET-WIDE — they cannot be ranked into deciles
Evaluated each feature for 8 large caps (AAPL XOM JNJ WMT JPM KO INTC CAT) on 2015-03-31,
2019-09-30 and 2022-06-30. **17 take the identical value for every ticker on a date** (calendar and
macro series); 13 vary across tickers; 5 returned no data locally (all macro). A cross-sectional
rank of a market-wide feature is all ties: deciles are undefined and the Spearman IC has zero
variance. The brief's "≈45-signal" family does not exist as specified.

- **Calendar** (10 — §5.3): handled as the brief already says, by a dummy regression.
- **Macro timing** (11): `vix_change_5d`, `vix_term_structure_slope`, `vvix_or_proxy`,
  `dxy_change_20d`, `faber_multi_asset_trend_above_10mo_sma`, `dispersion_60d`,
  `correlation_average_60d`, `anfci_z_60d`, `hy_oas_change_20d`, `hyg_lqd_spread`,
  `cot_commercial_net_long`. **Proposed: NOT tested by B-1.** They are timing signals and need a
  time-series construction (predict next-month market return), which the brief does not specify.
  **Consequence stated now so it cannot be forgotten later: B-1's refutation covers
  cross-sectional price signals only. Macro timing is untested by B-1.**
  *Director decision:* add a macro-timing family here (+1 N_trial) or leave it to its own brief.
  Four of the eleven (`anfci_z_60d`, `hy_oas_change_20d`, `hyg_lqd_spread`, `cot_commercial_net_long`)
  have no local data today and would HALT any panel regardless.

### 3.2 The declared `ticker_independent` flag is wrong for 15 features
`Feature.ticker_independent` defaults to `False` and is set `True` on only two features. **15
features declared cross-sectional are measured market-wide** (VIX, DXY, every calendar dummy,
`faber_…`, and others). **The panel builder must classify by MEASURED cross-sectional variance,
never by this flag** — trusting it would rank constants. (The flag itself is a foundry defect for
its owner; out of B-1's scope.)

### 3.3 `pair_zscore_60d` is structurally ineligible
Defined for **10 hand-picked tickers** (JPM/BAC, XOM/CVX, KO/PEP, HD/LOW, V/MA) and `None` for
every other name. It passed the cross-sectional probe only because JPM and XOM are pair members.
In a ~500-name universe it is ~98% missing. **Excluded.**

### 3.4 `earnings_proximity_5d` returns a constant 0.0 — not NaN — before ~2020-04
Probed 10 large caps each quarter 2016–2025: **every name returns exactly `0.0` through
2020-01-28 and `None` never once**; values vary across names from 2020-04 onward (e.g.
2024-01-31: AAPL 0.8, XOM 0.6). The earnings calendar's coverage starts ≈ 2020-04; before that the
feature reports a plausible "far from earnings" value instead of "unknown".
**This defeats the brief's census as written**, which halts on NaN share only: a constant `0.0`
passes, and would be ranked as a giant tie for 20 of 26 years.
- **Proposed census amendment:** a signal-month with **zero cross-sectional variance counts as
  unusable, exactly like NaN**; HALT any signal unusable in > 10% of its window's months.
- `earnings_proximity_5d` moves to the **short-window sub-arm** (§5.2).
- **The foundry has three spellings of "missing"**: `None` (most features), `NaN`
  (`dxy_change_20d` — found when this prereg's own reproduce snippet miscounted it, since
  `NaN != NaN` makes a set of NaNs look like variation), and a constant `0.0`
  (`earnings_proximity_5d`). **The census treats all three identically as unusable.**

### 3.5 Five Engine A edges duplicate foundry features — one hypothesis each
`momentum_12_1_v1` ≈ `mom_12_1`, `momentum_6_1_v1` ≈ `mom_6_1`, `short_term_reversal_v1` ≈
`reversal_1m`, `low_vol_factor_v1` ≈ `realized_vol_60d`, `betting_against_beta_v1` ≈ `beta_252d`.
Counting both would double-count one economic hypothesis in the BH family.
**Proposed:** the foundry feature is the canonical BH member (explicit point-in-time
per-(ticker, date) scalar); the Engine A version is reported beside it as a **definition-
sensitivity row, excluded from the BH count.** (`dist_52w_high`, listed in the brief among the
Engine A edges, exists only as the foundry feature — counted once.)

### 3.6 ★ Survivorship: point-in-time coverage is 54% in 2000
`members_on()` (PIT S&P 500) against the price files in `data/processed/`:

| date | members | with a price file | coverage |
|---|---|---|---|
| 2000-06-30 | 492 | 265 | **53.9%** |
| 2003-06-30 | 494 | 301 | 60.9% |
| 2006-06-30 | 497 | 327 | 65.8% |
| 2009-06-30 | 499 | 376 | 75.4% |
| 2012-06-30 | 497 | 397 | 79.9% |
| 2015-06-30 | 500 | 420 | 84.0% |
| 2018-06-30 | 506 | 464 | 91.7% |
| 2021-06-30 | 505 | 493 | 97.6% |
| 2024-06-30 | 503 | 497 | 98.8% |

The missing names are predominantly those later delisted, acquired or removed. No survivorship-
complete large-cap panel exists for 2000–2025 (T-265 is small-cap, 2016+). The brief's census
checks NaN share per signal, never universe coverage.

**The bias runs one way — UP.** Survivors are the names that did well, so every long leg is
flattered, and the 25%-satellite comparison against SPY (which *did* hold the delisted names) is
flattered twice. **Pre-committed interpretation, fixed now before any number exists:**
- **A refutation (nothing clears) is CONSERVATIVE and stands** — nothing cleared even with the
  bias helping it.
- **A survivor is NOT evidence.** It is "cleared on a survivor-biased substrate" and requires
  re-verification on survivorship-complete data (a paid CRSP-class source) before it counts.
- The census reports coverage per month; the verdict states the coverage-weighted share of the
  window below 80%.

### 3.7 The wealth leg carries an equal-weight tilt
Decile portfolios are **equal-weighted**; SPY is **cap-weighted**. Any decile — including a random
one — carries the equal-weight premium over SPY, so "Δ log wealth vs 100% SPY" mixes signal with
the EW tilt. **Proposed diagnostic (does not change H1):** also report Δ log wealth of the same
25% satellite against a 25% **equal-weight-universe** sleeve (all eligible names, same rebalance).
A signal that clears against SPY but not against the EW universe is labeled **"EW tilt, not
signal"**. *Director decision:* keep H1's wealth leg against SPY as briefed, or require it to clear
both.

## 4. Signal inventory — declared signs on the RAW computed value

### 4.1 Main family — cross-sectional, full window (15 BH members)

| # | Signal | Raw value (as coded) | Sign | Literature |
|---|---|---|---|---|
| 1 | `mom_12_1` | 12-month return, skip last month | **+** | Jegadeesh-Titman 1993 |
| 2 | `mom_6_1` | 6-month return, skip last month | **+** | Jegadeesh-Titman 1993 |
| 3 | `reversal_1m` | last-21-day return (NOT inverted) | **−** | Jegadeesh 1990; Lehmann 1990 |
| 4 | `dist_52w_high` | close / 252-day max − 1, in (−1, 0] | **+** | George-Hwang 2004 |
| 5 | `realized_vol_60d` | annualized 60-day log-return std | **−** | Ang-Hodrick-Xing-Zhang 2006 |
| 6 | `beta_252d` | 252-day OLS beta vs SPY | **−** | Black 1972; Frazzini-Pedersen 2014 |
| 7 | `skew_60d` | 60-day return skewness | **−** | Amaya et al. 2015; Bali et al. 2011 |
| 8 | `high_minus_low_60d` | 60-day (max − min) / mean | **−** | range-volatility → low-risk anomaly |
| 9 | `drawdown_60d` | close / 60-day max − 1 | **+** ⚠ | anchoring (George-Hwang) — **low confidence**: a reversal reading predicts −; declared + and frozen |
| 10 | `ma_cross_50_200` | (SMA50 − SMA200) / SMA200 | **+** | Han-Zhou-Zhu 2016 trend factor |
| 11 | `moving_avg_distance_50d` | log(close / SMA50) | **+** | Han-Zhou-Zhu 2016 |
| 12 | `vol_regime_5_60` | 5-day vol / 60-day vol | **−** ⚠ | vol-shock → low-risk anomaly — **low confidence** |
| 13 | `overnight_intraday_v1` | native edge score | **+** | Lou-Polk-Skouras 2019 (native orientation) |
| 14 | `volume_anomaly_v1` | native edge score (event-sparse) | **+** | Gervais-Kaniel-Mingelgrin 2001 (nearest) |
| 15 | `herding_v1` | native edge score (event-sparse) | **+** | contrarian on herding extremes (native) |

**Definition-sensitivity rows (reported, NOT in the BH count):** `momentum_12_1_v1`,
`momentum_6_1_v1`, `short_term_reversal_v1`, `low_vol_factor_v1`, `betting_against_beta_v1`.

**Excluded:** `pair_zscore_60d` (§3.3); the 17 market-wide features (§3.1); `earnings_proximity_5d`
moves to §5.2.

### 4.2 Sparse-signal rule (frozen)
A signal is **sparse** if, in the median month, > 50% of eligible names share its modal value
(`volume_anomaly_v1` and `herding_v1` are expected to be). For a sparse signal: Arm L = equal-
weight long of names whose signed value is strictly favorable that month; a month with fewer than
10 such names takes the EW-universe return and is **counted and reported** (never silently
filled). IC is Spearman on the (tied) values.

## 5. Arms, families, multiple testing

### 5.1 Arms (per the brief)
- **Arm L** — top-decile (by declared sign) equal-weight long, one-month hold, 10 bps round trip.
- **Arm LS** — top minus bottom decile, 50 bps/yr borrow on the short leg. **Diagnostic only** —
  a Roth cannot short.
- Per signal: monthly Spearman IC and its Newey-West t (6 lags); Arm L and LS Sharpe/Sortino with
  1000-iteration paired block bootstrap (6-month blocks); **the goal metric** — Δ log terminal
  wealth of (75% SPY + 25% Arm L, monthly rebalance) vs 100% SPY, paired block-bootstrap `ci_low`;
  the §3.7 EW-universe diagnostic; turnover, cost drag (bps/yr), MaxDD.

### 5.2 Short-window sub-arm (2020-04 → 2025-12, ≈ 5.7 years) — its own BH family
`earnings_proximity_5d` (+, earnings-announcement premium — Frazzini-Lamont 2007; Barber et al.
2013) and the six SimFin fundamentals edges in native orientation (all **+**):
`value_book_to_market` (Fama-French 1992), `value_earnings_yield` (Basu 1977),
`quality_gross_profitability` (Novy-Marx 2013), `quality_roic`, `accruals_inv_sloan` (Sloan 1996 —
native longs low accruals), `accruals_inv_asset_growth` (Cooper-Gulen-Schill 2008 — native longs
low growth). **Exploratory by construction:** 5.7 years cannot clear the minimum backtest length
for anything quotable; the result can only nominate, never confirm.

### 5.3 Calendar sub-family — its own BH family
`fomc_drift`, `pre_fomc_reduce`, `pre_holiday`, `sell_in_may_halloween`, `january_effect`,
`triple_witching_premium`, `tax_loss_season`, `month_of_year_dummy`, `weekday_dummy`,
`days_to_quarter_end`. Several are **daily** effects (weekday, pre-holiday, triple witching, FOMC
drift) that a monthly rebalance cannot see, so each is tested as a **daily dummy regression** of the
equal-weight-universe return on the feature, Newey-West t, with its **T-196 sign (+ on the raw
value, as T-196 tested it)**. Calendar signals are excluded from H1 ("non-calendar") by the brief.

### 5.4 Multiple testing
BH-FDR at q = 0.05 **within each family** (main: 15 over IC t-stats; short-window: 7; calendar:
10). The vol-family signals (5, 6, 8, 12) are positively dependent; BH controls FDR under positive
regression dependence (Benjamini-Yekutieli 2001), so plain BH is valid here.

## 6. Pre-named outcomes (all of them, including the uncomfortable ones)

| Outcome | What it means | What it does NOT mean |
|---|---|---|
| **H1 met** by a non-calendar signal | Cleared **on a survivor-biased substrate** (§3.6). Goes to survivorship-complete re-verification and RR-6 Gate 1′. | Not evidence yet. Not deployable. |
| **H1 met, but not against the EW universe** (§3.7) | "EW tilt, not signal." Reported as such. | Not a signal discovery. |
| **IC clears BH, wealth leg fails** | A real ranking signal that does not pay as a long-only satellite at this weight (the expected shape for low-risk signals — §8). | Not a refutation of the anomaly; not a deployable satellite. |
| **Nothing meets H1** | **Refutation, scoped:** the cross-sectional price vocabulary, on the literature's construction, clears nothing even with survivorship bias helping it. Conservative, and it stands. | **Not** a verdict on macro timing (§3.1), fundamentals over a long window (§5.2), or calendar effects beyond §5.3. |
| **A signal clears with the WRONG sign** | Reported as not clearing, with the opposite-sign statistic shown. | Never flipped (§2.1). |

## 7. Substrate + conventions (as briefed; reuse, do not re-derive)
PIT S&P 500 members via `engines/data_manager/membership.py::members_on`; prices from
`data/processed/`, 2000-01 → 2025-12, **price-only** on both legs (the dividend-yield differential
across deciles is a disclosed second-order bias; a `tr_reconciled` arm for the SPY twin only).
Panel cached at `data/research/b1/signal_panel_<md5>.parquet` with a census block (n_signals;
n_tickers/month; **coverage of PIT members/month**; NaN share and **zero-variance share** per
signal; HALT per §3.4). Determinism ×2 (bit-identical md5) before any number is quoted.
**The one pre-named sensitivity window:** 2012-01 → 2025-12, where coverage exceeds 80% — reported
beside the headline, never substituted for it.

## 8. Predictions (frozen here; the verdict compares against them)

- **(a) Main family, IC clearing BH at q = 0.05: 3** (plausible range 1–5).
- **(b) The three strongest by IC t in the declared sign:** 1. `beta_252d` (−), 2.
  `realized_vol_60d` (−), 3. `dist_52w_high` (+). The low-risk anomaly is the most-replicated in
  large caps; 52-week-high anchoring has held up post-2000 and is less crash-prone than 12-1
  momentum, which I rank fourth (2009 crash, large-cap decay).
- **(c) The expected split:** the two low-risk signals clear the IC bar but **fail the wealth leg**
  — long-only lowest-vol/lowest-beta deciles lagged SPY through the 2009–2021 bull, so high
  risk-adjusted IC does not become terminal wealth at 25%. `dist_52w_high` is the single most likely
  to clear **both** bars.
- **Calendar family:** 0 clear (T-196 found none; daily calendar effects are largely arbitraged
  post-2000). **Short-window family:** 0 clear.

## 9. Honest prior + N_trials

- **P(H1 met on this substrate) ≈ 18%** — close to the brief's 20%; the upward survivorship bias
  makes clearing *easier*.
- **P(an H1 survivor holds on survivorship-complete data) ≈ 45%**, so **≈ 8% that B-1 finds
  something real** — consistent with the brief's 8% for a non-momentum survivor.
- **N_trials:** the brief counts **+2** (Arm L family; Arm LS family). Honest-N counts every
  separately reported family whose best member could be quoted: **+4** (main L, main LS, short-
  window, calendar), **+5** if the director adds macro timing (§3.1). *Director decision at freeze.*

## 10. Scope exclusions (stated so they cannot creep in)
- No macro-timing construction unless added at freeze (§3.1).
- No machine-learned combination of signals (that is B-4's frozen-GBM brief).
- No quintile/tercile or weighting-scheme variants; no window other than §7's two.
- No re-selection of signals, signs or windows after the run.
- No deployment, and no long-short anything in a Roth.

## 11. Sequence
Draft → **director FREEZE (rules on §3.1, §3.4, §3.5, §3.7, §9)** → run (staffed separately) →
results + verdict appended here, predictions in §8 compared line by line → outbox.

## Reproduce the pre-run findings
```bash
# §3.1-3.2 market-wide vs cross-sectional, declared flag vs measured (execute, don't read)
python - <<'PY'
import importlib, pkgutil, datetime as dt
import core.feature_foundry.features as pkg
for m in pkgutil.iter_modules(pkg.__path__): importlib.import_module(f"{pkg.__name__}.{m.name}")
from core.feature_foundry.feature import get_feature_registry
T = ["AAPL","XOM","JNJ","WMT","JPM","KO","INTC","CAT"]
D = [dt.date(2015,3,31), dt.date(2019,9,30), dt.date(2022,6,30)]
for f in get_feature_registry().list_features():
    # filter NaN as well as None: NaN != NaN, so a set of NaNs looks like 'variation'
    # (dxy_change_20d returns NaN, not None, when its data is missing)
    vary = sum(len({round(v,10) for t in T
                    if (v := f(t, d)) is not None and v == v}) > 1 for d in D)
    print(f.feature_id, f.ticker_independent, vary)
PY
# §3.6 coverage: members_on(date) ∩ {files in data/processed}
```
