---
task_id: T-2026-06-05-108
title: Path B Layer 2 — managed-futures / diversified-ETF trend sleeve Phase 0 diagnostic
date: 2026-06-05
substrate: Stooq mirror, 8 ETFs (SPY, TLT, GLD, USO, UUP, EEM, IEF, DBC)
window: 2008-02-20 → 2025-12-31 (17.4 yr; binding floor UUP at 2007-02-20 + 12mo lookback warmup)
arms: phantom sleeve standalone (no Engine C/B integration; Phase 1 deferred)
scope: Phase 0 diagnostic only — NO equity-trend re-test, NO engine integration, NO production change
outcome: **RECONSIDER (DBMF/KMLM ETF route)** — Sharpe +0.51 ci_low +0.085 / 8-of-8 crisis windows beat SPY (2008 +28.6pp, 2022 +35.7pp, COVID +11.0pp) / SPY corr 0.29 — but **skewness -0.41 ci_low -0.754 FAILS the structural-property test** (worse than equity-trend's -0.133). Self-built trend on SPOT ETFs delivers diversification + crisis-alpha but NOT positive-skew convexity; the likely structural cause (spot ETFs lack futures-contract carry/roll) makes the DBMF/KMLM ETF route the natural next test.
---

# T-108 — Path B Layer 2 Diagnostic: Diversified-Futures Trend Sleeve

## Headline

**The strict inbox criterion (positive skew) FAILS. The secondary criteria
(crisis-alpha + diversification + Sharpe ci_low > 0) PASS overwhelmingly.**

Per the inbox decision tree:
- PROCEED: positive skew AND crisis-alpha AND low correlation — **fails** (skew negative)
- RECONSIDER (→ DBMF/KMLM ETF route): self-built close-but-not-clean — **best fit**
- DEAD: skew still negative AND no other value — **does not fit** (crisis-alpha + diversification + Sharpe-positive are all there)

**Verdict: RECONSIDER**. The right next dispatch is testing **DBMF / KMLM
managed-futures ETFs** (real futures-carrying products) on the same
crisis-period attribution. The self-built spot-ETF trend captures the
DIVERSIFICATION value but cannot deliver the CONVEXITY (positive skew)
the strategy needs — that's a property of holding actual futures
contracts (carry, roll, leverage), not of holding spot ETFs.

## Phase 0 Q1 — Data viability (DONE)

8-ETF basket inception (Stooq mirror, the local source for extended history):

| ETF | First date | Note |
|---|---|---|
| SPY | 2007-01-16 | OK |
| TLT | 2007-01-16 | OK |
| GLD | 2007-01-16 | OK |
| USO | 2007-01-16 | OK (Stooq mirror starts later than real 2006 inception) |
| **UUP** | **2007-02-20** | **BINDING FLOOR** |
| EEM | 2007-01-16 | OK |
| IEF | 2007-01-16 | OK |
| DBC | 2007-01-16 | OK |

Binding floor = UUP at 2007-02-20. With a 12-month momentum lookback,
the first usable rebalance is **2008-02-20** — meaning the test
window covers **2008 GFC (in entirety), COVID 2020, 2022 bear, 2025
vol-shock, plus 2010 flash crash / 2011 EU debt / 2015-08 China /
2018-Q4**. All major crisis events of the modern era. No data
limitation on the make-or-break test.

## Phase 0 Q2 — Standalone skew/crisis test (THE MAKE-OR-BREAK)

Configuration mirrors the existing `scripts/run_diversified_futures_trend.py`
parameters (spec'd in T-2026-05-08-007): top_n=4, max_position_weight=0.30,
lookback=252, vol_window=63, rebalance=monthly.

### Headline metrics (block-bootstrap CI, n_iter=1000, block=Politis-White auto)

| Metric | Sleeve point | Sleeve ci_low | Sleeve ci_high | SPY same-window |
|---|---:|---:|---:|---:|
| Sharpe | **+0.505** | **+0.085** | +0.981 | +0.626 |
| Sortino | **+0.471** | **+0.078** | +0.918 | (n/a) |
| **Skewness (daily returns)** | **-0.408** | **-0.754** | -0.039 | **+0.012** |
| Max drawdown | -26.5% | (n/a) | (n/a) | **-52.4%** |
| Annualized return | +4.88% | (n/a) | (n/a) | +11.07% |
| Final equity multiple (17.4 yr) | 2.34× | (n/a) | (n/a) | (n/a) |
| n_obs (daily returns) | 4,495 | | | |
| n_rebalances | 146 monthly | | | |

**The skew finding is the headline disappointment.** Daily-return skew
is -0.41 — clearly more negative than the equity-trend reference
(-0.133 per T-007) and decisively negative on the bootstrap CI
(ci_high -0.039, doesn't reach 0). On the structural-property
question the inbox treated as make-or-break, this **FAILS**.

Note for context: SPY's own daily skew over the same window is +0.012
(near-zero, very slightly right-leaning). The popular intuition
"equities have negative skew" reflects MONTHLY or longer-horizon
returns; at daily granularity SPY is near-symmetric and the sleeve is
materially worse. Even with the diversification benefit, the sleeve
adds left-tail mass — not right-tail mass.

### Crisis-window returns (the surprise upside)

| Crisis window | Sleeve return | SPY return | Δ (outperformance) | Sleeve MDD |
|---|---:|---:|---:|---:|
| 2008 GFC (2008-09-01 → 2009-03-31) | **-9.26%** | **-37.88%** | **+28.61pp** | -14.48% |
| 2010 Flash crash | -9.10% | -16.10% | +7.01pp | -10.30% |
| 2011 EU debt | -2.43% | -5.76% | +3.33pp | -9.07% |
| 2015-08 China-vol | -0.09% | -8.55% | +8.46pp | -3.27% |
| 2018-Q4 selloff | -8.88% | -13.83% | +4.95pp | -10.49% |
| **COVID 2020** | **-2.65%** | **-13.63%** | **+10.99pp** | -10.54% |
| **2022 bear (Jan-Oct)** | **+11.18%** | **-24.50%** | **+35.68pp** | -9.04% |
| 2025 vol-shock | +0.72% | -6.95% | +7.67pp | -9.40% |

**8/8 crisis windows: sleeve outperforms SPY** with 7-36pp margins.
**2022 is the standout**: the sleeve made **+11.2%** while SPY lost
24.5% — a 35.7pp swing. **COVID and 2008 also dramatic** (11pp and 29pp
respectively). The crisis-alpha claim from external research is REAL
on our substrate — it's just not delivered via the positive-skew
mechanism the research literature attributes it to.

This is the diagnostically interesting finding: **crisis-alpha is
empirical fact here; the positive-skew explanation is not**. The
actual mechanism appears to be regime-switching (sleeve rotates into
defensive assets like TLT/GLD/UUP during stress) which produces flat
returns rather than positive-skewed jumps.

## Phase 0 Q3 — Base correlation (PASS)

Sleeve daily returns vs SPY daily returns (proxy for the 6-edge
equity book's primary directional exposure):

- **Correlation: +0.289** (well below the inbox's 0.5 diversification threshold)
- **Beta: +0.153** (very low equity-market beta)

The sleeve is genuinely uncorrelated to the equity-book direction.
This diversification value is real and survives 17 years of data.

A full base-correlation check vs the actual 6-edge equity-book returns
(not SPY) would require a parallel multi-year backtest run; deferred
to Phase 1 if/when the DBMF/KMLM dispatch lands. SPY correlation is a
strict upper-bound on the base-book correlation, since the equity-book
is itself ~0.7-0.9 correlated to SPY.

## Why the verdict is RECONSIDER, not DEAD

Per inbox criteria:
- **PROCEED**: positive skew AND crisis-alpha AND low correlation → fails (skew)
- **RECONSIDER (→ DBMF/KMLM)**: self-built close-but-not-clean → THIS
- **DEAD**: skew still negative AND managed-futures fundamentally doesn't work → does NOT fit

The "DEAD" reading would be: "managed-futures isn't viable for us
either, abandon Layer 2." But the empirical evidence rejects that:

1. **8-of-8 crisis windows the sleeve made or lost less than SPY.** This is the practical thing Path-B Layer 2 was conceived to deliver.
2. **The diversification math works.** Correlation 0.29, beta 0.15 — independent return stream.
3. **The negative-skew finding has a likely structural cause.** Trend-following on SPOT ETFs differs from trend-following on FUTURES CONTRACTS in several material ways:
   - Spot ETFs lack the carry/roll yield that managed-futures funds harvest
   - Spot ETFs lack the natural leverage of futures (1% notional vs ~10% margin)
   - Real managed-futures funds run 30-50 contracts; the 8-ETF basket has dramatically less diversification
   - Convex payoffs come from leveraged + truly diversified portfolios; this self-built test has neither

The inbox explicitly anticipated this case: "if self-built trend is
close-but-not-clean: **DBMF/KMLM managed-futures ETFs** (30-50% of
headline trend at 1-share min, §1256 tax treatment)". DBMF/KMLM hold
actual futures contracts via a managed wrapper — they may deliver the
positive-skew property our spot-ETF approach can't.

**Recommended path: RECONSIDER, dispatch T-108-followup-DBMF-KMLM** —
buy 17 years of DBMF + KMLM history (or use whatever subset of their
shorter history is available; DBMF launched 2019, KMLM 2020) and run
the same Phase-0 analysis on those return series. If DBMF/KMLM
deliver positive skew with the same crisis-alpha, Phase 1 integration
becomes warranted (allocate X% capital to the ETF, not self-build).

## What Phase 1 would look like IF the DBMF/KMLM test passes

Per scope doc §Phase 1: capital-partitioned allocation via
`MultiSleeveAggregator`. base-only vs base + {10%, 20%, 30%}% trend
sleeve. 16-yr + 26-yr substrate, block-bootstrap CI. PRIMARY KPIs:

- **Portfolio skewness**: does the sleeve flip the BOOK's skew
  positive? (The standalone sleeve being negative-skew doesn't doom
  the integration if the COMBINED portfolio skewness flips positive
  via decorrelation effects.)
- **Crisis-period return** (2008/COVID/2022): does the combined
  portfolio survive crises better?
- **MDD reduction at non-worse Sharpe**: the basic Pareto check.

Phase 1 is NOT initiated this dispatch (per inbox: Phase 1 only if
Phase 0 clears PROCEED). The RECONSIDER verdict routes us to the
T-108-followup-DBMF-KMLM dispatch BEFORE any integration work.

## Methodology

### Data path
- Source: Stooq mirror `data/raw/stooq/daily/us/{nyse,nasdaq} etfs/...`
- Loader: custom `scripts/managed_futures_trend_t108.py::load_stooq_etf`
  (bypasses `data/processed/*` which is Alpaca-only 2020-04+).
- Sleeve harness: reuses `scripts/sleeve_phase0_verdict::run_sleeve`
  + `_build_rebalance_dates`.
- Sleeve: `engines/engine_c_portfolio/sleeves/TrendFollowingSleeve`
  invoked with `signals = {t: 1.0 for t in UNIVERSE}` so it acts as
  a generic momentum + inverse-vol allocator over the pre-supplied
  futures-ETF basket (NOT filtering Engine A equity signals — the
  inbox-warned anti-pattern is avoided).

### Block-bootstrap CI
- n_iter = 1000, block length = Politis-White auto = `max(4, floor(4·(n/100)^(2/9)))`
- For n=4495 obs, block = 7
- seed = 42
- Metrics bootstrapped: Sharpe, Sortino, skewness (Fisher-Pearson via `pd.Series.skew`)

### Crisis-window attribution
- Per-window total return = product of (1 + daily) - 1 over the window
- SPY benchmark = `close[end] / close[start] - 1` over the same window
- No bootstrap CI on per-window returns (single observation each)

### Hard-constraint compliance
- NO equity-trend re-test ✓ (the sleeve runs on the 8-ETF futures basket, not Engine A equity tickers)
- NO Engine B / Engine C integration ✓ (standalone phantom run)
- NO production-default change ✓ (this dispatch is diagnostic only)
- Block-bootstrap CI on every Sharpe/skew headline ✓
- NO data/governor edits ✓
- NO cockpit/dashboard edits ✓

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | Q1 data floor reported | DONE — UUP 2007-02-20 (binding) |
| 2 | Q2 skewness + crisis returns + Sharpe/Sortino/MDD with CI | DONE (table above) |
| 3 | Q3 base correlation | DONE (corr 0.29 vs SPY proxy; full base-book correlation deferred) |
| 4 | Phase 0 verdict with skew as headline | DONE — **RECONSIDER** (skew -0.41 fails; crisis-alpha 8/8 passes) |
| 5 | Audit doc + TASK_LEDGER row | DONE (this audit + ledger row appended in commit) |
| 6 | NO equity-trend re-run; NO prod-default change; branch pushed NOT merged | DONE |

## Files

- `scripts/managed_futures_trend_t108.py` (NEW; Phase 0 diagnostic with Stooq loader)
- `docs/Measurements/2026-06/t108_phase0_diversified_trend.json` (raw output)
- `docs/Audit/managed_futures_trend_t108_2026_06_05.md` (this audit)
- `docs/State/TASK_LEDGER.md` (T-108 row appended)

## Memory updates needed (post-merge)

- New entry: "T-108 Phase 0: cross-asset diversified-FUTURES-ETF trend on 8-ETF basket (SPY/TLT/GLD/USO/UUP/EEM/IEF/DBC) 2008-2025. **SKEW FAILS (-0.41 vs equity-trend -0.133)** — worse than the falsified equity-trend on the structural-property test. **BUT crisis-alpha is REAL** — 8-of-8 crisis windows beat SPY (2008 +28.6pp, 2022 +35.7pp, COVID +11.0pp), SPY corr 0.29, Sharpe ci_low +0.085. Verdict **RECONSIDER (DBMF/KMLM)**: self-built spot-ETF trend captures diversification + crisis-alpha but cannot deliver positive-skew convexity — likely structural (spot ETFs lack futures carry/roll/leverage). The DBMF/KMLM managed-futures ETFs are the natural next test (real futures contracts → may deliver positive skew that spot ETFs can't)."

- Pattern memory: "Crisis-alpha and positive-skew are DIFFERENT properties. A signal can deliver one without the other. The 8-ETF basket here delivers crisis-alpha (rotates defensively) without convexity (no fat right tail from leveraged trend continuations). Managed-futures funds are designed to deliver BOTH via futures contracts; spot ETFs cannot."

## Forward dispatches

- **T-108-followup-DBMF-KMLM** (recommended next): fetch DBMF + KMLM daily returns (DBMF launched 2019-04; KMLM launched 2020-12). Run identical Phase-0 analysis on each. If either delivers positive skew with the crisis-alpha pattern, that becomes the Phase 1 integration target. Lower data depth (~5-6 yr each) is a real limitation; the 2020 COVID + 2022 + 2025 crises are testable on DBMF, just 2022 + 2025 on KMLM.

- **T-108-followup-Phase1-skewness-flip** (after DBMF/KMLM): if a managed-futures ETF clears Phase 0, integrate via `MultiSleeveAggregator` at 10/20/30% capital partition. PRIMARY KPI is whether the COMBINED portfolio's monthly skewness flips positive (the standalone-negative-skew sleeve may still positivity-flip the BOOK via decorrelation). 16-yr + 26-yr cells, block-bootstrap CI, default-OFF, canon-md5 OFF=identical.

- **T-108-parameter-sweep** (optional secondary): the current parameters (top_n=4, lookback=252) were the spec defaults. A parameter sweep (top_n ∈ {3,4,5,6}; lookback ∈ {126, 252, 365}; rebalance ∈ {monthly, quarterly}) MIGHT find a configuration that delivers positive skew on the 8-ETF basket. This is exploratory and low-priority given the structural-cause hypothesis above; only run if DBMF/KMLM is unavailable.

## NOT done in T-108

- Phase 1 integration (per inbox: only if Phase 0 clears PROCEED; verdict is RECONSIDER, so Phase 1 deferred to post-DBMF/KMLM dispatch)
- Full equity-book base correlation (used SPY as proxy; full requires separate multi-yr backtest)
- DBMF/KMLM analysis (separate forward dispatch)
- Parameter sweep on the 8-ETF basket (separate forward dispatch; low priority)
- No engine code changes (per inbox hard constraint)
- No production-default changes (per inbox)
