---
task_id: B-1
title: Pre-registration — raw-signal decile re-evaluation of the foundry features + cross-sectional Engine A edges
date: 2026-09-30
worker: Agent A (prereg); the RUN is staffed separately (likely C after RR-1)
branch: research/raw-signal-decile-b1
status: FROZEN 2026-10-13 (director-acknowledged; rulings issued 2026-10-01) — NOTHING RUN. The run waits for the director's word (C's campaign 8/8). N_trials +4 at run.
---

# B-1 — does the price vocabulary have anything, tested the way the literature tests it?

## 1. The question (H1 verbatim from the brief)

Every foundry feature was previously tested as a single-gene long `CompositeEdge` bolted onto the
6-edge book, through the full backtester, under the RR-1 sizing defect and a Gate 4 with no power.
None was ever evaluated as **rank → decile → monthly rebalance** — the construction the anomaly
literature uses. B-1 does that.

**H1 (brief, verbatim):** at least one non-calendar signal has BH-adjusted IC p < 0.05 **AND**
25%-satellite Δ log wealth `ci_low > 0` on 2000–2025.

**H1 AS RULED (2026-10-01, binding):** at least one non-calendar, cross-sectional signal has
BH-adjusted IC p < 0.05 **AND** 25%-satellite Δ log wealth `ci_low > 0` against **BOTH** 100% SPY
**and** the 25% equal-weight-universe sleeve (§3.7). Beating SPY alone does NOT meet H1.

**Refutation (brief):** zero signals meet both ⇒ "exhausted price vocabulary" is confirmed on the
construction the literature uses. **As ruled, that claim covers CROSS-SECTIONAL price signals only;
macro timing is UNTESTED by B-1** (§3.1).

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
  **RULED 2026-10-01: LEFT OUT — its own brief later.** A timing construction invented inside B-1
  would muddy the decisive test. The sentence above stands verbatim and is carried into
  CURRENT_STATE, so B-1's H0 cannot quietly regrow to cover macro timing.
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
signal"**. **RULED 2026-10-01: the wealth leg must clear BOTH** — against SPY and against the
EW-universe sleeve. A signal that beats SPY only is "EW tilt, not signal" and does **NOT** meet H1:
the EW premium is purchasable (RSP) at zero research cost, and the hypothesis is about the signal.

*A consequence worth stating (not part of the ruling):* both legs of the EW-relative comparison draw
from the **same** survivor-biased universe, so it largely differences out survivorship's LEVEL bias
(§3.6). It does not remove the part where the signal itself predicts survival (momentum winners and
low-vol names are likelier to survive), so §3.6's asymmetric reading still binds.

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
| **H1 met** (vs BOTH benchmarks) by a non-calendar signal | Cleared **on a survivor-biased substrate** (§3.6). Goes to survivorship-complete re-verification and RR-6 Gate 1′. | Not evidence yet. Not deployable. |
| **Clears vs SPY but NOT vs the EW universe** (§3.7) | "EW tilt, not signal." **Does NOT meet H1** (ruling 2). Reported as such. | Not a signal discovery. |
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

- **P(H1 met on this substrate) ≈ 18%** under the brief's SPY-only wealth leg — close to the
  brief's 20%; the upward survivorship bias makes clearing *easier*.
- **Under H1 AS RULED (both benchmarks): ≈ 12%.** Restated before any data, because the
  hypothesis changed, not because anything was seen. The extra requirement mostly removes cases
  that were the EW tilt rather than the signal, so the probability of a *real* finding is unchanged.
- **P(an H1 survivor holds on survivorship-complete data) ≈ 45%**, so **≈ 8% that B-1 finds
  something real** — consistent with the brief's 8% for a non-momentum survivor.
- **N_trials:** the brief counts **+2** (Arm L family; Arm LS family). Honest-N counts every
  separately reported family whose best member could be quoted: **+4** (main L, main LS, short-
  window, calendar). **RULED 2026-10-01: +4** — count what could be quoted. (Macro timing is out,
  so the +5 case does not arise.)

## 10. Scope exclusions (stated so they cannot creep in)
- No macro-timing construction (ruled out 2026-10-01; its own brief later).
- No machine-learned combination of signals (that is B-4's frozen-GBM brief).
- No quintile/tercile or weighting-scheme variants; no window other than §7's two.
- No re-selection of signals, signs or windows after the run.
- No deployment, and no long-short anything in a Roth.

## 11. Sequence
Draft (09-30) → rulings (10-01) → **FROZEN 2026-10-13** → **WAIT for the director's word** (C's
RE-SCORE campaign reports 8/8; one heavy job at a time on the 8 GB host) → panel build → run
(standalone harness, never through `BacktestController`) → results + verdict appended here,
predictions in §8 compared line by line → outbox.

### 11.1 LAUNCH CHECKLIST — operational addendum, 2026-10-13 (post-freeze; alters NO frozen term)
Written so the run is a copy-paste, not a judgment. **The two harness scripts do not exist yet** —
building them is the run's first step — so the CLI below is their **SPEC**: the build implements
exactly these flags, adds both commands to `docs/Core/execution_manual.md` (`[NN-NO-GUESS-CLI]`),
and records any deviation in the verdict. Run from the **agent-a worktree**.

**Step 0 — gates (every one must pass, else STOP and report):**
- [ ] The director's word received: C's RE-SCORE campaign reports 8/8.
- [ ] **One heavy job at a time (8 GB host):** `pgrep -fl "rescore_rr1|run_isolated|submit_substrate|pytest"` prints nothing.
- [ ] **Disk ≥ 5.0 GB free** (`rescore_rr1.MIN_FREE_GB`), checked at start **and again before every
      write** — the campaign checks only at cell start, and a mid-run ENOSPC is the 09-30 class.
- [ ] **Swap ≥ 1 GB free** (`sysctl vm.swapusage`); otherwise wait — swap growth on this host comes
      out of the same disk.
- [ ] Tree clean on `research/raw-signal-decile-b1`; frozen text intact: §4 and §8 section hashes
      `ba6cc7bff764` / `cb9f4c3e185b` (the 09-30 values; verify with the command in
      §11.2).
- [ ] **Code provenance:** the harness prints the resolved `__file__` of itself,
      `core.feature_foundry` and `engines.data_manager.membership`; all must sit under the agent-a
      worktree. Note `data/processed/` and `data/research/` are **symlinks into the main repo** — the
      census records their resolved real paths.

**Step 1 — env pins (exactly `run_isolated`'s set; export BEFORE python starts):**
```bash
export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_DYNAMIC=FALSE
```
Both scripts assert these at import and **REFUSE (exit non-zero) if any differs. They never
re-exec** — a re-exec discards in-process state, the class that once ran both arms of a paired
test on the same code.

**Step 2 — smoke, to measure before committing hours:**
```bash
/usr/bin/time -l python -m scripts.build_signal_panel_b1 --start 2024-01 --end 2024-12 --out data/research/b1/smoke/
```
Record wall time and peak RSS (`maximum resident set size`). Extrapolate to 312 months. **If the
projected peak RSS exceeds 2 GB or the runtime exceeds 8 h, STOP** and report — that is a
sequencing decision for the director, not a reason to trim the panel.

**Step 3 — the panel (full window):**
```bash
/usr/bin/time -l python -m scripts.build_signal_panel_b1 --start 2000-01 --end 2025-12 --out data/research/b1/
```
Writes `signal_panel_<md5>.parquet` and `census_<md5>.json`. **The census, asserted — any failure
HALTS (`[NN-FAIL-CLOSED]`) and every value goes in the verdict:**
- **Coverage per month, every month** (not samples): `n_pit_members`, `n_with_price`,
  `coverage_pct` — the §3.6 table at full resolution, plus the share of the window below 80%.
- **Classification by MEASURED cross-sectional variance**, never the declared flag (§3.2); it must
  equal the §4 inventory — any mismatch HALTS.
- **Unusable signal-month = NaN OR None OR zero cross-sectional variance** (`std < 1e-12`,
  `[NN-FP-GUARDS]`) — all three spellings of missing (§3.4). HALT any signal unusable in > 10% of
  its window's months. Short-window signals are checked over 2020-04 → 2025-12 only.
- **Sparse flag** per §4.2 (modal share > 50% in the median month), recorded per signal.
- **Engine A orientation check** (§2.2) before any return exists: native score vs declared
  literature direction — a mismatch HALTS and escalates; never flipped.
- **Input manifest:** resolved real paths of `data/processed/` and the membership file, and the md5
  of the sorted `(file, size, mtime)` list — the substrate the run actually read.
- **Family counts:** main 15 (+5 definition-sensitivity rows), short-window 7, calendar 10.

**Step 4 — the harness, run 1:**
```bash
python -m scripts.raw_signal_decile_b1 --panel data/research/b1/signal_panel_<md5>.parquet \
  --out data/research/b1/run1/ --seed 0 --boot-iter 1000 --boot-block-months 6
```
One row per signal: IC, Newey-West t (6 lags), BH-adjusted p within its family; Arm L and LS
Sharpe/Sortino with paired-bootstrap `ci_low`; 25%-satellite Δ log wealth `ci_low` **vs 100% SPY
AND vs the EW-universe sleeve** (H1 as ruled); turnover, cost drag (bps/yr), MaxDD. Calendar
(daily dummy regression) and short-window families in their own tables.

**Step 5 — determinism ×2:** rerun Step 4 with `--out data/research/b1/run2/`. Compare a
**canonical** md5 — rows sorted by signal, floats rounded to 12 significant digits, serialized as
JSON — between run1 and run2: **must be bit-identical**. (Parquet bytes are not compared; writer
metadata is not the measurement.) Record the panel md5 beside it.

**Step 6 — the one pre-named sensitivity window (§7):** Step 4 with `--start 2012-01`, reported
beside the headline, never instead of it.

**Step 7 — the verdict:** `docs/Audit/b1_raw_signal_decile_verdict_<date>.md`, YAML frontmatter
(`task_id, title, date, author, outcome, status, reproduce`) per the program's rails; the full
results table inline (the data under `data/` is gitignored); the §4/§8 section-hash check stated;
§8's predictions compared line by line; **N_trials +4** recorded.

### 11.2 Verify the frozen text before launch
```bash
F=docs/Sources/prereg_b1_raw_signal_decile_2026-09-30.md
for sec in "## 4. Signal inventory" "## 8. Predictions"; do
  awk -v h="$sec" 'index($0,h)==1{f=1} f&&/^## /&&index($0,h)!=1{exit} f' "$F" | shasum -a 256 | cut -c1-12
done   # expect ba6cc7bff764 then cb9f4c3e185b
```

### 11.3 Run log (operational; alters NO frozen term)

**2026-10-14 14:11 — step 0 + step 2 (the smoke).** Builder `scripts/build_signal_panel_b1.py`
at `37e8734` (17 tests). All five gates **PASSED OUTRIGHT** at launch (G3 swap 1,253 MB free;
an earlier 14:04 reading of 975 MB had recovered), so **no waiver was used.** A watchdog was
armed voluntarily and was **defective**: `pgrep -f` matched the `/usr/bin/time` wrapper (its argv
contains the same command), so it read RSS 0 and would have killed the wrapper, not Python.
It was not needed. For any future run, target the child: `pgrep -P "$(pgrep -f '^/usr/bin/time -l python -m scripts.build_signal_panel_b1')"`.

**Measured (2024-01 → 2024-12, 12 month-ends):** 75 s wall, **peak RSS 900 MB** (peak footprint
1.33 GB), 0 swaps. Projection to 312 months: **~30–40 min, peak RSS ~1.1 GB** (the price cache
is capped by the 730 existing files, 516 used here; the panel itself is ~30 MB). **Inside the stop
rule** (≤ 2 GB, ≤ 8 h).

**Census: HALT — no panel written** (fail-closed, before any return or IC exists):
1. `herding_v1` — unusable in **8 of 12** months (median modal share 1.0). It is a daily EVENT
   edge (fires on herding days); sampled at month-end it is all zeros most months. Structurally
   invisible to a month-end construction — the `pair_zscore_60d` class.
2. `earnings_proximity_5d` — unusable in **4 of 12** months: the month-ends between earnings
   seasons have no name within 5 business days of a report.
3. *At risk, not halted:* `volume_anomaly_v1` unusable in 1 of 12 months (8.3% vs the 10% bar).

**Passing evidence:** all five §2.2 orientation checks fire and pass (Spearman +0.63, +0.56,
−0.63, −0.56, −0.81 in the declared directions); coverage 98.6%; SimFin fundamentals edges
have data and are usable. Forward returns: 5,885 full, 23 delisting proxies, 60 names whose
file lacks the exact month-end date (NaN, ~1%) — reported in the verdict.

**Status:** the two HALTs need a director ruling on the frozen inventory **before** the full
run. They are pre-run findings: no return, IC or wealth number has been computed.

**2026-10-14 — DIRECTOR RULING on the two HALTs (post-freeze, pre-data).** See the
amendment section below. Builder updated at the next commit; 21 tests. Implementation note:
the first cut applied the `volume_anomaly_v1` pre-ruling only on the 10% branch, so a
herding-like signal (> 50% unusable, which fails the classification check first) would have
HALTED instead. The test caught it; the pre-ruling now keys on the unusable share.

**2026-10-14 14:16–14:33 — step 3, full run A (2000-01 → 2025-12) at `e595ae5`.** All five gates
**PASSED OUTRIGHT** at 14:16:55: G1 the director's GO after D's suite; G2 disk 10.60 GB; G3 swap
1,094 MB free; G4 clean tree at `e595ae5`; G5 §4 `ba6cc7bff764`, §8 `cb9f4c3e185b`. The watchdog
targeted the child (the fix above). **Measured:** 312 month-ends, 109,366 rows, 963 s wall, **peak
RSS 972 MB**, 693 tickers cached. Inside the stop rule.

**Census:**
- `volume_anomaly_v1` unusable in **29.8%** of 312 months → the **pre-ruled exclusion APPLIED
  AUTOMATICALLY** and is recorded in `auto_excluded_pre_ruled`; main family 14 → 13.
- Every other main and sensitivity signal: **0.0% unusable**, all CROSS-SECTIONAL. Orientation
  **5/5 pass** (+0.555, +0.520, −0.605, −0.446, −0.829), none untestable. Coverage 52.7% (2000-01)
  → 99.4% (2025-12); 49.0% of months below 80% (the §3.6 asymmetry, as pre-stated). Forward
  returns: 108,886 full, 112 delisting proxies, 361 with no price at the month-end (NaN, reported,
  never filled), 7 with no price after.
- **HALT — no panel written:** four short-window SimFin edges over the 10% bar:
  `value_earnings_yield_v1`, `quality_gross_profitability_v1` and `quality_roic_v1` 12 of 69 months
  (17.4%), `accruals_inv_asset_growth_v1` 15 of 69 (21.7%). `value_book_to_market_v1` and
  `accruals_inv_sloan_v1` 3 of 69 (4.3%, under the bar). Run B (determinism) did not start.

**Diagnosis** (read-only; the builder's own functions; no return computed; 95 s, 260 MB): for
every edge the unusable months are **one contiguous run at the window START**, and none falls after
2021-06. The SimFin FREE panel's first filings for the PIT universe arrive at publish 2020-07: 0
names with any filing at the 2020-04 and 2020-05 month-ends, 1 at 2020-06, 143 at 2020-07, 295+
from 2020-08. Below 30 scored names the edges abstain to all-0.0 (`min_universe=30`). The
latest-value edges (B/M, Sloan) need one filing, so they are usable from 2020-07. The TTM edges
need four published quarters, so they are usable from 2021-04 (129 names with four filings).
Asset growth needs a year-ago balance sheet, so it is usable from 2021-07. From 2021-07 on, every
month has ≥ 322 names with four filings. **The window's 2020-04 start never described SimFin
coverage.** §3.4 anchored it to the earnings calendar for `earnings_proximity_5d`, which the
amendment then excluded.

**My defect:** the smoke year (2024) sat mid-window and could not see a warm-up at the window
start. The smoke's "SimFin fundamentals edges have data and are usable" was true of 2024 only.
A smoke must include each family's first months. The census also gave a share without naming
the months, which is why this diagnosis needed a separate script. It now names them
(`unusable_months`; the lock fails on the prior builder with `KeyError`).

**Known properties for the verdict (no action taken):** (1) The SimFin edges emit a stateful
basket transition: 1.0 on entry, 0.3 while held, 0 otherwise. Under §4.2, Arm L is therefore the
whole top-quintile basket (both values are favorable). Spearman IC, however, ranks new entrants
above held members, so the IC partly measures entry versus holding, not only the factor level.
The state starts empty, so a family's first window month emits the whole basket as entries.
(2) SimFin FREE filings thin out after publish 2025-Q2. For the 2025-07 → 2025-12 month-ends,
filings run up to two quarters older than a live investor's: PIT-safe, but less informative.

**Status:** the short window (§5.2, 2020-04 → 2025-12) needs a director ruling before the re-run.
This is a pre-data finding: no return, IC or wealth number has been computed.

## DIRECTOR FREEZE — 2026-10-13 (rulings issued 2026-10-01; BINDING)
Frozen as amended. The load-bearing terms, quoted so they cannot drift:
1. **Macro timing is OUT.** B-1's refutation covers **cross-sectional price signals only**; macro
   timing is **UNTESTED by B-1** and gets its own brief.
2. **The wealth leg must clear BOTH** 100% SPY **and** the EW-universe sleeve. Beating SPY alone is
   "EW tilt, not signal" and does not meet H1.
3. **N_trials +4** at run (main L, main LS, short-window, calendar).
4. **Survivorship (§3.6), endorsed as written:** a null STANDS; a survivor is NOT evidence until
   re-verified on survivorship-complete data — and a survivor becomes the concrete case for
   re-asking the free-data ruling.
5. §3.2–§3.5 stand **as drafted** (classify by measured variance; `pair_zscore_60d` excluded; a
   zero-variance month counts as unusable like NaN, for all three spellings of missing; one BH
   member per duplicated hypothesis, foundry canonical). The signs (§4) and predictions (§8) are
   unchanged from the 09-30 draft; nothing has been run.

## POST-FREEZE, PRE-DATA INVENTORY AMENDMENT — 2026-10-14 (director ruling; BINDING)
Made **before any return, IC or wealth number existed**, after the smoke's census HALT
(§11.3). §4's text is unchanged; this section governs where it differs.
1. **`herding_v1` and `earnings_proximity_5d` are EXCLUDED** as structurally ineligible for a
   month-end construction — the `pair_zscore_60d` disposition, same reason: a daily event edge
   is silent at month-end; it is not a weak signal, it is not a month-end signal. **Main family
   15 → 14, short-window 7 → 6, N_trials unchanged at +4.** No month-aggregated herding
   construction is invented: a construction the brief does not specify is a new hypothesis and
   gets its own brief (the macro-timing reasoning).
2. **`volume_anomaly_v1` is PRE-RULED:** if the full-window census trips the 10% unusable bar,
   the same exclusion applies **automatically and is recorded as such** — no decision is made
   after seeing anything.
3. **§8's predictions stay byte-identical** and are compared as written against the reduced
   inventory; the verdict states the inventory change beside the comparison.
4. **The 60 names lacking the exact month-end date → NaN forward return: reported, never
   filled.**

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
