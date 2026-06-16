# T-178 PRE-REGISTRATION — Regime Step 2: dynamic MF-sleeve SIZER A/B

**Status:** LOCKED 2026-06-16, committed BEFORE running. Per CLAUDE.md
#7 + the T-118b template. Step 2 was greenlit-with-caveats after the
adversarial verification of T-172 (causal filter confirmed lookahead-
clean, prefix-vs-full score diff exactly 0.0). The caveats below are
REQUIRED, baked into this design.

## The question

Does a regime-detector-driven **dynamic** MF-sleeve weight BEAT the
**always-on 20%** sleeve — net-of-cost, OUT-of-sample? The detector is
**regime-classification-grade, not sharp-timing-grade** (T-172), so the
utilization is a **fast-crisis SIZER** (heavier MF through the whole
risk-off regime), NOT a precise timer.

## Caveats baked in (from the T-172 verification — required)

1. **Genuinely held-out calm.** T-172's calm-silence/FA were IN-SAMPLE
   (LOCO kept all calm years in training). Here the HMM trains on
   **2000–2012** and is applied OOS to **2013–2025**, so **2013–2019 +
   2021 + 2023–25 are a genuinely held-out calm span** for specificity.
   The operating point is set with **MARGIN** on that held-out calm —
   not at the FA edge.
2. **Fast-crisis framing, not all-crisis timer.** Dotcom (slow
   valuation bear) is structurally weak (T-172); it is IN the training
   span here, not the OOS test. The OOS test contains a fast crisis
   (COVID 2020) + a grind (2022) + held-out calm. **Always-on 20% stays
   the floor** for slow bears; the sizer is expected to win in fast
   risk-off, roughly tie in calm/grind.
3. The p_crisis is a **fixed-params causal forward filter** under the
   train-2000–2012 contract (no growing-prefix re-fit).
4. **T-152-style operating-point calibration** on the deep panel (the
   FIRE trigger set on the held-out-calm FA, with margin).

## Data

- **Base** equity book: the canonical 26yr re-anchor curve
  `data/external/base_curve/t118r_v1_26yr_arm0_3b403882.csv` (158fe678
  arm0, daily 2000–2025, MDD −32.6%) → monthly returns.
- **MF sleeve**: AQR TSMOM (all-asset, monthly, 1985–2025;
  `data/external/aqr/aqr_tsmom_monthly_snapshot_20260615.xlsx`). AQR
  TSMOM is the OPTIMISTIC proxy (T-171: real DBMF/KMLM ~82% corr / 5.81%
  TE distorts the crisis shape). The A/B is run at **raw AQR AND a 0.5×
  haircut** on the MF excess return; the verdict must hold (or be
  reported as not holding) under the haircut.
- **p_crisis**: the T-172 deep-panel HMM (3-state, seed 0) trained on
  2000–2012, causal forward filter, crisis state = max-mean-vol;
  resampled to month-end and **lagged one month** (last month's signal
  sizes this month — no lookahead).

## The two arms (monthly rebal, T-171 convention)

`r_month = (1 − x)·base_month + x·mf_month` − cost.

- **always_on**: `x = 0.20` constant.
- **dynamic**: `x(t) = clip(0.20 + SCALE·(p_lag(t) − BASELINE), X_MIN, X_MAX)`
  with `X_MIN = 0.10` (lighter in clear bull — recover the upside the
  fixed 20% concedes), `X_MAX = 0.40` (heavier in crisis). SCALE,
  BASELINE set with margin on the held-out calm so the sleeve stays
  ≤0.20 through calm and only lifts on a genuine p_crisis regime.

**Net-of-cost:** monthly re-sizing turnover `Σ|Δx|` × a round-trip cost
of **20 bps** (conservative for an ETF sleeve). Always-on pays only its
rebal turnover; dynamic pays its larger re-sizing turnover — the sizer
must beat always-on AFTER paying for its activity.

## Decision rule (locked)

The dynamic sizer **WINS** iff, OOS net-of-cost on 2013–2025, it beats
always-on 20% on the **risk-adjusted** primary (Sharpe, CI-aware) AND
does not worsen MDD — with the win concentrated in the fast-crisis
sub-period (2020) as expected. A bare CAGR bump that doesn't survive the
CI or the haircut does NOT count.

**If it does NOT beat always-on net-of-cost OOS (under the haircut),
that is the honest CEILING — say so plainly: always-on 20% is the
deployable sleeve and the regime timer adds nothing net.**

## Multiplicity / integrity

The operating point (SCALE, BASELINE, X range, cost) is set ONCE on the
held-out-calm specificity target and the fast-crisis-sizer intent,
BEFORE seeing the A/B return comparison. No post-hoc operating-point
tuning to the A/B result. Seed-pinned. N_trials: 1 primary A/B (× the
haircut sensitivity arm). Any re-tuned operating point is a NEW
pre-registration.
