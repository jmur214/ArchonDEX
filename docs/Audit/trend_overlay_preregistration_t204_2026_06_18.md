# Trend-Overlay — PRE-REGISTRATION (T-204, 2026-06-18)

**Written BEFORE any backtest** (per CLAUDE.md `[NN-MBL]` + the task). Every arm
below counts toward `N_trials`. No post-hoc grid changes, no cherry-pick;
the verdict is read against the rules fixed here.

## Hypothesis
A long/flat **absolute-momentum** overlay on liquid equity/bond/gold ETFs
improves the **shape** of beta — positive skew, reduced max-drawdown,
crisis-period protection — versus buy-and-hold, at an acceptable
trend-capture cost. This is the homegrown, positive-skew analogue of the
bought DBMF/KMLM managed-futures sleeve (T-170), and it targets the thing
that actually loses to the Schwab robo: the −33% MDD.

This is a **standalone signal module + standalone validation ONLY**. It is
NOT composed into Engine C/B sizing (that crosses an engine boundary →
propose-first, later), and the **beat-the-robo measurement is NOT run here**
(that is the post-gate composition step, after C's re-aimed gate lands).

## Data (deterministic, on-disk; no network)
Stooq daily ETF closes (split/dividend-adjusted), already in-tree:
- `SPY` `data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt`
- `AGG` `data/raw/stooq/daily/us/nyse etfs/1/agg.us.txt`
- `GLD` `data/raw/stooq/daily/us/nyse etfs/1/gld.us.txt`

All three span **2005-02-25 → 2026-05-22** (5344 bars) — covers the 2008
GFC, 2020 COVID, and 2022 crisis sub-periods (AGG/GLD inception ~2004-05
bounds the window).

## The signal (causal, no lookahead)
For lookback `k` trading days: `signal_t = 1 if close_t > SMA_k(close)_t else 0`
(both `close_t` and the SMA are as-of the day-`t` close). To BACKTEST, the
position held over day `t+1` is `signal_t` — i.e. strategy returns apply
`signal.shift(1)` to next-day asset returns. The module emits the
as-of-close `signal`; the shift is the consumer's (the backtest does it).
No same-day lookahead.

## Pre-registered param grid (ALL arms count toward N_trials)
- **lookback `k` ∈ {3, 5, 10} months** = {63, 105, 210} trading days
  (10mo/210d ≈ the canonical AQR 200-day / 10-month rule).
- **Structures evaluated:**
  - **(A) SPY long/flat** — when SPY is "off" (below trend) the defensive
    leg ∈ **{cash (0%), AGG (hold bonds)}**. 3 lookbacks × 2 legs = **6 arms**.
    This is the canonical capture-efficiency test (vs SPY buy-hold).
  - **(B) 3-asset diversified trend sleeve** — each of SPY/AGG/GLD held
    long/flat (→ cash when off), equal-weight (⅓ each, rebalanced daily by
    the signal). 3 lookbacks → **3 arms**. Tests the cross-asset
    diversification / skew / MDD benefit vs the equal-weight buy-hold of
    the three.
- **Total = 9 arms. N_trials += 9.**

## Metrics reported for EVERY arm (fixed now)
From `core/metrics_engine.py` (no private reimpl): annualized return,
**Sharpe (point + block-bootstrap `ci_low`, 1000 iter, auto block length,
seed=0)**, Sortino, max-drawdown, **return skewness**, time-in-market %,
approximate round-trips/yr (turnover), and per-crisis-window drawdown
(2007-10→2009-03 GFC, 2020-02→2020-04 COVID, 2022-01→2022-10).

## Decision rules (fixed now)
- **Sub-gate (the task's): trend-capture-efficiency = Sharpe(overlay) /
  Sharpe(SPY buy-hold) > 0.70** — below this it is a sideways-market drag,
  not a win. Reported per arm for structure (A).
- **Standalone "shape win" indicators** (descriptive, NOT a deploy gate):
  skew(overlay) > skew(buy-hold); MDD materially less negative; crisis-window
  drawdowns reduced. A positive read here is *necessary-not-sufficient* —
  the deploy decision is the later after-tax robo measurement, not run here.
- **Honest failure is a valid outcome.** If no arm clears capture-efficiency
  > 0.7 AND shows a skew/MDD improvement, the overlay is logged as a chop
  drag and not advanced. No goalpost-moving.

## Caveats acknowledged up front (not discovered after)
- Equity-only/3-ETF trend lacks the cross-asset breadth of true managed
  futures (no commodities/FX/rates curve) → less diversification than DBMF.
- Whipsaw is the cost of convexity — chop years (e.g. 2011, 2015, 2018)
  will show the overlay underperforming buy-hold; that is expected.
- Trend protects best in the **slow grind** (2008, 2022), not the first
  sharp drop (it lags the 2020 V-bottom on the way down AND the recovery).
- 2005-start window is ~21 years — adequate for descriptive shape, but the
  deploy-grade MBL/DSR accounting belongs to the later composed measurement.

## Out of scope (explicitly deferred)
- Composing the overlay into portfolio sizing (Engine C/B) — propose-first.
- The beat-the-robo / `evaluate_deploy_readiness` measurement — post-gate.
- Vol-target and defensive-factor levers (separate Phase-1 components).
