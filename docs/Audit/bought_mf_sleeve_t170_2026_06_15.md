---
task_id: T-2026-06-15-170
title: Bought managed-futures crisis sleeve (separate-account allocation) — buy-vs-build A/B
date: 2026-06-15
scope: allocation evaluation on REAL ETF returns (DBMF/KMLM) + literature-cited index estimate for the deep window; NO trend model built/replicated; no live-money path
status: PRE-REGISTRATION committed BEFORE running (honest-N); results appended after
outcome: "[PENDING — committed before any combined-portfolio number is unblinded.]"
---

# T-170 — Bought MF Crisis Sleeve (Separate-Account)

## 1. PRE-REGISTRATION (committed before any result)

### 1.1 Why this escapes the T-128r refutation

T-118r (de-gross) and T-128r (capital-partitioned spot sleeve) both
died as in-house crisis defenses. T-128r's refutation was specific:
the **capital-partitioned** design fails because Engine A/B's sizing is
not scale-invariant (T-121) — the sleeve shares the book's constraint
stack. A **separate-account, own-capital** managed-futures allocation
escapes that entirely: it is its own account with its own capital and
NO shared sizing/MVO/constraint stack. The combined portfolio is then
a clean linear combination of two INDEPENDENT daily return streams —
`r_combined = (1−x)·r_base + x·r_mf`, rebalanced — which is
analytically valid (the thing T-128r's integrated path was not). This
is buy-vs-build: we evaluate the ALLOCATION to a bought product
(real ETF returns, real ER), we do NOT build or replicate a trend
model.

### 1.2 The data-depth reality (stated honestly, before results)

On-disk tradeable history:
- **DBMF** (iMGP DBi Managed Futures): 2019-05-10 → 2026-05 (~7yr).
- **KMLM** (KFA Mount Lucas Managed Futures): 2020-12-08 → 2026-05 (~5.4yr).
- **Robo-proxy assets** SPY / AGG / IEF: 2005-02 → 2026 (~21yr).
- **Base book**: 2000-2025 (the T-128r 26-yr arm0 curve).

**No bought managed-futures product, and no robo ETF, has dotcom-era
(2000-02) data; no MF product has GFC (2008) data** (DBMF/KMLM both
postdate 2018). Therefore:
- **Recent window (real, rigorous):** 2019-05→2025-12 (DBMF) and
  2020-12→2025-12 (KMLM). Covers COVID-2020 + the 2022 bear — two real
  crises. This is the leg that can actually be *backtested* with real
  products and real cost (ETF NAV returns are already net of the
  ~0.85-0.90% ER, so cost is realistic by construction).
- **Deep window (dotcom/GFC) — LITERATURE-CITED ESTIMATE, NOT a
  backtest:** no real product exists. We cite the SG Trend Index
  published crisis returns from our own research record
  (`docs/Sources/Research_2026_05_31/finding_1...`, Hurst-Ooi-Pedersen
  2017): **2008 SG Trend +20.9%, 2022 +27.3%; TSMOM positive in 8/10
  worst 60/40 drawdowns**; and T-108's own self-built spot-trend GFC
  analog (+28.6pp vs SPY in 2008). The deep-window claim is presented
  as a literature+analog ESTIMATE of what a bought MF sleeve would have
  done, explicitly flagged as un-backtestable here. What we CAN show on
  real data for the deep window is the base book's actual dotcom/GFC
  drawdown (the hole the sleeve would need to fill).

### 1.3 The A/B (fixed)

- **Arms:** base-alone; base + x% MF on separate capital, x ∈ {10, 20, 30%}.
- **MF product:** DBMF (primary, longest real history) + KMLM (cross-check).
- **Combination:** `r_comb = (1−x)·r_base + x·r_mf`, annually rebalanced
  to the target weights (separate accounts, no shared constraint).
- **Robo benchmark:** 60% SPY + 40% AGG, annually rebalanced, same window.
- **Windows:** recent-real (DBMF 2019-05→2025-12; KMLM 2020-12→2025-12);
  deep-estimate (2008 GFC + 2000-02 dotcom — base-actual + cited MF).

### 1.4 The read (fixed)

Per window per allocation, combined-portfolio: Sharpe + block-bootstrap
ci_low (block=7, n=1000, seed=42), MDD (rel + abs pp vs base), CAGR,
and per-crisis max-drawdown (COVID-2020, 2022 on real data; GFC/dotcom
on the base + cited-MF estimate). Plus the robo proxy on every window.

### 1.5 Decision rule (fixed, pre-registered — analogous to T-118b)

The bought MF sleeve is a **recommend-to-paper candidate** iff:
1. **Combined MDD reduction ≥ 25%** (vs base) on the real recent window
   (the crisis-defense core — a higher bar than T-128r's 15% because a
   separate-account allocation gives up return to a low-Sharpe product,
   so it must earn its keep on drawdown), AND
2. **Combined Sharpe ci_low NOT down** vs base-alone (the diversification
   doesn't cost risk-adjusted return), AND
3. **Crisis-window behavior confirmed:** the sleeve actually cuts the
   COVID-2020 and 2022 drawdowns on real data (and the cited estimate
   is directionally consistent for GFC).

Plus the benchmark gate: **does base+MF-sleeve beat the robo** (60/40)
on the same window where base-alone does/doesn't? Report explicitly.

Per CLAUDE.md #6 the gate is ci_low. Per #9 verdicts are on the
current substrate. The deep-window estimate is NOT gate-eligible
(literature, not measurement) — it informs, it doesn't decide.

### 1.6 N-trials policy

**N_trials += 1** for the recent-window real-ETF allocation test (a new
measurement of the bought-sleeve hypothesis). The deep-window
literature citation is N += 0 (no backtest). Pre-registered before
unblinding per CLAUDE.md #7.

---

## 2. RESULTS

[APPENDED AFTER THE PRE-REGISTRATION COMMIT — see git history.]
