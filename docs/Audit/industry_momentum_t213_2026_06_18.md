---
task_id: T-2026-06-18-213
title: Industry/sector momentum on GICS SPDRs, sector-neutral (Moskowitz-Grinblatt) — composable OFF-default signal
date: 2026-06-18
scope: cross-sectional SIGNAL only (OFF-default, NOT wired to the live portfolio — composition is a later Engine-C step); standalone validation only; NO beat-the-robo measurement
status: CURRENT (pre-registration committed before any backtest — see git history; results appended after)
references: research brief Tier-2 #5 (Moskowitz-Grinblatt 1999, industry momentum)
---

# T-213 — Industry Momentum (Sector-Neutral)

## 1. PRE-REGISTRATION (committed before any backtest)

### 1.1 Why + the honesty frame

Industry momentum (Moskowitz-Grinblatt 1999, internationally replicated)
is the one cross-sectional "specialization" the research flags as
genuinely robust — and we've never tried it (we did individual-stock
momentum = closet beta, not sector momentum). It's retail-tradeable on
liquid sector ETFs. The discipline that keeps it honest is **ONE
pre-registered structure + sector-NEUTRAL construction** — NOT a
free-form "which lookback works for which sector" search (the overfit
trap the brief warns about).

### 1.2 The ONE structure (fixed — no grid, no search)

- **Universe:** the 9 ORIGINAL GICS SPDRs with clean 2005+ history —
  XLK, XLF, XLE, XLV, XLI, XLY, XLP, XLU, XLB. **XLRE (2015) and XLC
  (2018) are EXCLUDED** — their short, staggered inceptions would bias a
  cross-sectional rank and inject universe-change artifacts. (Brief
  permits "a clean subset"; this is the stability-honest one.)
- **Signal:** trailing **12-1 momentum** — total return from t−252 to
  t−21 trading days (skip the most recent ~month to avoid the
  short-term-reversal contamination, the Jegadeesh-Titman / MG standard).
- **Construction (sector-NEUTRAL — the key control):** dollar-neutral
  long-top-K / short-bottom-K, **K = 3** of 9, equal-weight within each
  leg (long +1/3 each, short −1/3 each, 0 otherwise). The long-winners /
  short-losers cross-section is neutral by construction; we additionally
  REPORT realized per-sector net exposure to confirm it's not a closet
  persistent tilt (e.g. always-long-tech).
- **Rebalance:** monthly (first observable trading day of each month).
- Output: a composable `{sector: weight}` dict; OFF-default standalone
  module, NOT wired to the live portfolio.

### 1.3 Multiple-testing discipline

- **N_trials += 1** — this ONE structure. Lookback (252/21), K (3),
  neutralization (dollar-neutral L/S), and universe (9) are all FIXED
  a-priori from the MG literature, not searched. Any future variant
  (different K/lookback) is a new trial that re-inflates the DSR bar.
- OOS/walk-forward posture: no in-sample parameter was tuned to the
  result; the 2005-2025 run is a single pre-registered measurement.

### 1.4 Standalone validation read (NOT the gate)

- L/S momentum portfolio **Sharpe + MDD + CAGR** vs an equal-weight-9-
  sector benchmark, 2005-2025 (block-bootstrap CI on the L/S Sharpe).
- **Sector-neutrality confirmation:** time-average net exposure per
  sector (should be ≈ 0 — no persistent tilt) + turnover.
- **Orthogonality:** correlation of L/S momentum daily returns to the
  equal-weight benchmark (low ρ ⇒ genuine cross-sectional rotation, not
  hidden beta).
- Honest expectation: a robust-but-MODEST lever; measure it cleanly,
  and a clean "adds nothing orthogonal" is a legitimate finding.

### 1.5 Invariants

- OFF-default, ADDITIVE (new standalone module, NOT on the production
  backtest path) → prod canon UNCHANGED.
- Composition into the live portfolio = a later Engine-C step (T-211),
  NOT done here.
- Unit tests (deterministic, fixture-fed).
- **NO beat-the-robo measurement** (post-composition step).

---

## 2. RESULTS

(Appended after the pre-registration commit — §1 predates these in git
history. Reproducible: `scripts/industry_momentum_t213.py`; tests
`tests/test_industry_momentum_t213.py`. ADDITIVE-ONLY: `git diff
--name-only HEAD` empty → prod canon UNCHANGED; a contract test asserts
the backtest path doesn't import the module.)

### 2.1 Standalone validation (9 SPDRs, 2005-02→2026-05, 5,089 days)

| Portfolio | Sharpe (ci_low) | MDD | CAGR |
|---|---|---|---|
| **L/S sector momentum** (dollar-neutral top-3/bottom-3, monthly) | **0.057 (−0.348)** | −45.8% | −0.35% |
| equal-weight-9 benchmark (long beta) | 0.601 | −53.9% | +9.89% |

- **Sector-neutrality — CONFIRMED:** time-avg net weight per sector sums
  to −0.000; max |avg net| = 0.115 (a mild residual long-XLK lean from
  tech's persistent momentum, not a structural tilt). Dollar-neutral by
  construction; annualized turnover ≈ 10.3×.
- **Orthogonality — CONFIRMED:** corr(L/S, equal-weight-9) = **−0.207**
  (low/negative → a genuine cross-sectional rotation, NOT hidden beta).

### 2.2 Verdict — NULL standalone (orthogonal but unprofitable on our window)

**Sector-neutral industry momentum is NOT a harvestable standalone lever
on the 2005-2025 9-SPDR universe.** L/S Sharpe 0.057 with ci_low −0.348
fails any `ci_low > 0` bar, CAGR is ~flat-negative, and the −45.8% MDD is
the classic **momentum-crash signature** (the 2009 short-covering rally
annihilates the short-losers leg — the well-documented fragility of L/S
momentum). The MG effect either decayed post-publication (momentum
crowding) or is too weak across only 9 coarse GICS sectors in the
post-2009 low-dispersion regime.

**The one genuinely positive structural finding: it IS orthogonal**
(ρ −0.21, dollar-neutral verified) — so it adds diversification but no
return. For the eventual beat-the-robo composition (C/T-211) that makes
it a weak candidate: orthogonality without positive expected return
doesn't lift a portfolio's risk-adjusted/tail profile enough to matter,
and a −0.35 ci_low standalone Sharpe argues against giving it weight.

**Honest expectation met:** the brief flagged "robust-but-modest";
measured cleanly, it's a NULL, not modest. A clean, well-measured null on
a pre-registered single structure is the deliverable — it closes the
"industry momentum" lever honestly without a fishing expedition.

### 2.3 What was NOT done (no overfitting / no fishing)

- The pre-registered ONE structure (12-1, dollar-neutral top-3/bottom-3,
  9 SPDRs, monthly) was measured AS-IS. A long-only sector-momentum tilt
  (overweight strong sectors, no shorts — which avoids the momentum-crash
  short leg) is a DIFFERENT structure = a NEW pre-registration + N_trials
  increment; it was deliberately NOT run here (running it post-hoc because
  the L/S null disappointed would be exactly the search-the-space overfit
  the brief warns against). Flagged as a possible separate dispatch, not
  smuggled in.
- NO beat-the-robo measurement (post-composition step).
