# Wider-Breadth Trend Sleeve — PRE-REGISTRATION (T-214, 2026-06-18)

**Written BEFORE any backtest** (CLAUDE.md `[NN-MBL]`). Tests whether MORE
cross-asset breadth strengthens the positive-skew convexity that T-204 found
appears only in the diversified sleeve (not SPY-long/flat alone). Reuses the
merged `core/trend_overlay.py` (no rebuild). Every arm counts toward
`N_trials`.

## The overfit trap this guards against
"More assets always looks better in-sample," and "which assets work best" is
a search. So the asset set is **FIXED here by a principled macro-spanning
rationale, NOT by what backtests well** — and the lookback grid is the SAME
{3,5,10mo} as T-204 (no lookback re-search).

## Pre-registered asset set — "Wide-9" (one-or-two per macro class)
| class | tickers |
|---|---|
| equity (3 regions) | SPY (US), EFA (intl developed), EEM (emerging) |
| rates (3 types) | AGG (aggregate), TLT (long Treasury), TIP (TIPS) |
| real assets (3) | GLD (gold), DBC (broad commodity), VNQ (REIT) |

Rationale: span the macro spectrum so different crises (deflationary 2008,
liquidity 2020, inflationary 2022) are met by *some* asset that trends.
GSG excluded (redundant with DBC for broad commodity; DBC is less
energy-concentrated than GSG). No "best subset" search — this set is locked.

## Data + window
Stooq daily, on-disk, deterministic. DBC inception (2006-02-03) bounds the
common window → **all sleeves evaluated on 2006-02-03 → 2026-05-22** so the
3-asset-vs-Wide-9 comparison is apples-to-apples (same window). Covers
2008/2020/2022 crises.

## Signal + construction (reuse T-204)
- Per asset: long/flat absolute momentum, `close > SMA_k`, **cash off-leg**
  (T-204: cash beat AGG — bonds fell *with* stocks in 2022). Causal
  (`signal.shift(1)`, no lookahead) — `overlay_returns()` from the module.
- **Weighting (both pre-registered):**
  - **Equal-weight** (primary; directly comparable to T-204's EW sleeve).
  - **Inverse-vol** (risk-parity; weight ∝ 1/σ on a CAUSAL trailing
    60-day return-vol per asset, renormalized daily). Motivated by the
    basket's heterogeneous vols (TLT/EEM/DBC ~3-4× TIP/AGG) — does
    down-weighting the vol-bombs improve the tail?

## Pre-registered grid (ALL count toward N_trials)
**Wide-9 sleeve × lookback {3,5,10mo} × weighting {equal, inverse-vol} =
6 arms. N_trials += 6.** The T-204 3-asset EW sleeve is RE-RUN on the common
window as the comparison baseline (a re-measurement of an already-counted
config, not a new trial).

## Metrics (fixed now; via core/metrics_engine.py)
Per arm: CAGR, Sharpe (point + block-bootstrap `ci_low`, 1000 iter, seed=0),
Sortino, MDD, daily + **monthly skew** (the convexity test), per-crisis-window
drawdown (GFC 2007-10→2009-03, COVID 2020-02→2020-04, 2022). Plus the
**mean pairwise return correlation in calm vs in each crisis window** — the
direct test of the honest caveat below.

## Decision rules (fixed now) — does breadth buy REAL convexity?
The wider sleeve "wins over the 3-asset" only if, vs the 3-asset EW on the
SAME window, it:
1. **strengthens monthly skew** (more positive), AND
2. **cuts MDD and/or crisis-window drawdowns further**, AND
3. **holds capture-efficiency > 0.70** (Sharpe(sleeve)/Sharpe(its own
   buy-hold) — not a chop drag).
If breadth improves calm-period diversification but the **crisis correlation
spikes toward 1** (everything-sells-off) so the crisis MDD does NOT improve,
the verdict is **"breadth = in-sample flattery, not real tail
diversification"** — and that is the honest finding to report, not buried.

## Honest caveat acknowledged up front
More ETFs diversify in CALM regimes but cross-asset correlations rise toward
1 in a liquidity crisis (2008/2020) — the breadth may protect the slow grind
(2022, where assets diverged) far more than the sharp everything-sells-off.
The calm-vs-crisis correlation table is the explicit check.

## Out of scope (deferred, as before)
- Composing into Engine C/B sizing — propose-first.
- The beat-the-robo / `evaluate_deploy_readiness` measurement — post-gate
  (a stronger sleeve could feed C's composition v2; that decision is the
  director's).
- OFF-default; canon unchanged; standalone validation only.
