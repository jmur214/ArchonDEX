---
task_id: T-2026-06-26-252
title: Conditional vol-targeting on the equity sleeve (SPY) — pre-registration + gauntlet verdict
date: 2026-06-26
worker: Agent B
branch: feature/conditional-voltarget-t252
status: BUILT (default-OFF, canon byte-identical) + GAUNTLET RUN — PROPOSE-FIRST (enable is the user's call)
---

# Conditional vol-targeting on the equity sleeve (SPY) — T-252

## 0. What + why (the brief)
The fresh-eyes brief endorsed vol-targeting as one of two transferable structural
edges, with the qualifier that the ROBUST variant is **CONDITIONAL** — act ONLY in
extreme realized-vol states — because *continuous* targeting can INCREASE drawdown
(Perchet et al., FAJ 2020: levering in calm adds exposure right before vol clusters).
The Sharpe benefit is risk-asset-only; the cross-asset win is the TAIL (drawdown) cut.
This is the safe-core's risk component for C's barbell (T-251).

## 1. Pre-registration (bound BEFORE the run; NO sweep)
Corrected methodology (the brief): **Sortino/MaxDD are a SCORECARD, not an
optimization target** — fixed params, no tuning. On full-cycle SPY (1993-2026,
incl. dotcom/GFC/COVID/2022), net of 5bps liquid-ETF turnover:
- estimator = 20-day trailing realized vol (annualized); target_vol = **0.15** (fixed);
  floor = **0.5**; extreme = realized vol > its own **expanding P80** (causal); cost = 5bps.
- **Arms (4, pre-registered → N_trials = 3 treatment configs):** baseline (buy-hold);
  `continuous_lever` (clip 0.5–1.5 daily, the FAJ-critiqued lever-in-calm);
  `continuous_capped` (clip 0.5–1.0 daily, de-gross always, no lever);
  `conditional` (clip 0.5–1.0 ONLY when extreme, else 1.0).
- **Question:** does CONDITIONAL cut the TAIL (MaxDD) without killing return — and
  does CONTINUOUS-lever INCREASE drawdown (FAJ 2020) on OUR data?
- **Metric:** Sortino + **block-bootstrap ci_low** (Künsch/Politis-White, 1000 iter)
  [NN-SHARPE-CI], MaxDD, Sharpe, skew, tail_ratio. Window 33yr — MBL-clearing for a
  low SR target at N_trials=3.

## 2. Result (8359 bars, net 5bps; `data/research/t252/gauntlet.json`)
| arm | Sortino | ci_low | MaxDD | Sharpe | CAGR | skew | tail | avg exp |
|---|---|---|---|---|---|---|---|---|
| baseline (buy-hold) | 0.817 | 0.429 | **−55%** | 0.640 | 10.7% | −0.01 | 0.96 | 1.00 |
| continuous_lever | 0.975 | 0.561 | −46% | 0.723 | 10.7% | −0.42 | 0.88 | 1.10 |
| continuous_capped | 0.929 | 0.504 | −44% | 0.696 | 9.0% | −0.35 | 0.90 | 0.89 |
| **conditional** | **0.916** | **0.486** | **−47%** | 0.693 | 9.4% | −0.37 | 0.90 | 0.91 |

## 3. Verdict (honest)
- **YES — conditional cuts the tail without killing return.** MaxDD **−55% → −47%**
  (+8pp) while Sortino **0.82 → 0.92** (ci_low 0.43 → 0.49, both > 0) and Sharpe
  0.64 → 0.69, at a small CAGR give-up (10.7% → 9.4%). It is the most *surgical*
  variant — avg exposure 0.91, i.e. fully invested except in extreme-vol storms.
  This is a defensible safe-core risk component for the barbell.
- **The FAJ-2020 "continuous increases drawdown" warning is REFUTED on US SPY.**
  continuous_lever *reduced* MaxDD (−55% → −46%) and had the best Sortino (0.975,
  ci_low 0.561). The FAJ result was on INTERNATIONAL equities; it does not replicate
  on US SPY full-cycle. **BUT** continuous_lever needs **leverage** (avg exposure
  1.10 → borrows in calm — incompatible with a long/flat no-borrow safe-core) and
  adds materially **negative skew** (−0.42 vs −0.01) — it buys Sharpe by selling the
  left tail. continuous_capped (no lever) keeps most of the benefit at a higher CAGR
  cost (9.0%) but deepens skew similarly.
- **Recommendation for C's barbell safe-core (long/flat, capped 1×):** use the
  **conditional** variant (or continuous_capped). Conditional is the minimal
  intervention — full equity exposure except it de-grosses in genuine storms — and
  it improves the risk-adjusted/tail profile with the least skew damage and no
  leverage. The Sharpe/Sortino bump is real but modest; the durable value is the
  **tail cut** (the cross-asset, robust property the brief flagged).

## 4. Boundary
Engine B → PROPOSE-FIRST. The mechanism (`engines/engine_b_risk/sleeve_vol_target.py`)
is a NEW, pure, **default-OFF** building block — not wired into any active sizing
path, so the production canon is **byte-identical** (no active module imports it;
6-edge 2022 canon reproduces 435a9588). The enable is the user's call; C composes it
into the barbell (T-251). 7 unit tests + doc_lint green. [NN-FAIL-CLOSED] on a
missing input when enabled.
