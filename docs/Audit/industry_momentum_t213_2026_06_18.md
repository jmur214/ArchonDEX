---
task_id: T-2026-06-18-213
title: Industry/sector momentum on GICS SPDRs, sector-neutral (Moskowitz-Grinblatt) — composable OFF-default signal
date: 2026-06-18
scope: cross-sectional SIGNAL only (OFF-default, NOT wired to the live portfolio — composition is a later Engine-C step); standalone validation only; NO beat-the-robo measurement
status: PRE-REGISTRATION committed BEFORE any backtest; results appended after
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

[APPENDED AFTER THE PRE-REGISTRATION COMMIT — see git history.]
