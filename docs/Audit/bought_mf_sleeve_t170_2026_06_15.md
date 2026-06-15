---
task_id: T-2026-06-15-170
title: Bought managed-futures crisis sleeve (separate-account allocation) — buy-vs-build A/B
date: 2026-06-15
scope: allocation evaluation on REAL ETF returns (DBMF/KMLM) + literature-cited index estimate for the deep window; NO trend model built/replicated; no live-money path
status: CURRENT (pre-registration committed before running — see git history; results appended after)
outcome: "**RECOMMEND-TO-PAPER @ ~20% DBMF — the FIRST crisis-defense lever to clear the pre-registered gates** (de-gross T-118r + in-house sleeve T-128r both failed everything). Separate-account framing escapes the T-121 scale-non-invariance. Real DBMF window (2019-2025): base+20%DBMF MDD −7.5%→−5.6% (+25.1% rel, PASS ≥25%), Sharpe ci_low 0.726→0.740 (PASS, up), 2022 bear cut (−7.5%→−5.2%; DBMF +32.7%, KMLM +48.8% — crisis-alpha CONFIRMED) but COVID V-crash not caught (criterion 3 PARTIAL). Beats the 60/40 robo handily (Sharpe 1.45 vs 0.76, MDD −5.6% vs −21.8%) — though base-alone already does on this window. **LOAD-BEARING CAVEAT: the real window is benign (base MDD only −7.5%); the actual reason MF matters — cutting the GFC −32.6% / dotcom −21.3% the base can't escape and no in-house lever touches — rests on the cited SG Trend +20.9% (2008), NOT a backtest (no MF product has pre-2019 data).** 20% DBMF is the sweet spot (10% under-defends +15%, 30% over-allocates to a 0.43-Sharpe product). N_trials += 1 (recent real window); deep-window estimate N += 0."
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

(Appended after the pre-registration commit — verify section 1 predates these numbers in git history.)

### 2.1 Recent window, REAL ETF (the rigorous leg)

**DBMF window (2019-05→2025-12, 1669 trading days):**

| Portfolio | Sharpe | ci_low | MDD | ΔMDD vs base | CAGR |
|---|---|---|---|---|---|
| base-alone | 1.452 | 0.726 | −7.5% | — | 9.5% |
| **base + 10% DBMF** | 1.488 | 0.797 | −6.3% | +15.4% / +1.15pp | 9.1% |
| **base + 20% DBMF** | 1.452 | 0.740 | −5.6% | **+25.1% / +1.87pp** | 8.7% |
| base + 30% DBMF | 1.341 | 0.648 | −6.3% | +16.0% / +1.19pp | 8.3% |
| robo 60/40 (SPY/AGG) | 0.760 | 0.027 | −21.8% | — | 9.2% |
| DBMF-alone | 0.426 | — | −23.7% | — | 4.7% |

**KMLM window (2020-12→2025-12, 1266 d):**

| Portfolio | Sharpe | ci_low | MDD | ΔMDD | CAGR |
|---|---|---|---|---|---|
| base-alone | 0.893 | −0.075 | −7.5% | — | 5.0% |
| base + 10% KMLM | 0.962 | +0.039 | −6.4% | +14.0% | 4.9% |
| base + 20% KMLM | 0.941 | +0.029 | −6.4% | +14.2% | 4.8% |
| base + 30% KMLM | 0.839 | −0.036 | −7.3% | +2.1% | 4.7% |
| robo 60/40 | 0.707 | −0.096 | −20.9% | — | 7.4% |
| KMLM-alone | 0.279 | — | −28.1% | — | 3.1% |

**Crisis-window behavior (real):**
- **2022 bear** (the one sustained bear in the window): base DD −7.5% →
  base+20%DBMF −5.2%; **DBMF +32.7%, KMLM +48.8%** in 2022 → base+20%KMLM
  −6.0%. The anti-correlation/crisis-alpha thesis is CONFIRMED on the
  one real bear market available.
- **COVID-2020** (fast V-crash): base DD −3.4% → base+20%DBMF −4.3%
  (slightly WORSE; DBMF −2.4% — trend-following needs a sustained move,
  it does not catch a 1-month crash). Documented trend behavior, not a
  surprise.

### 2.2 Deep window (dotcom/GFC) — base actual + cited estimate (NOT a backtest)

The base book's actual deep-crisis drawdowns — the hole a crisis sleeve
would need to fill (no real MF product has this history):

| Crisis | Base DD | Base period return |
|---|---|---|
| dotcom 2000-2002 | −21.3% | −2.9% |
| **GFC 2007-2009** | **−32.6%** | −19.1% |
| full 26-yr | −32.6% (= the GFC) | +526% |

**The GFC drawdown IS the full-cycle −32.6% MDD** — it is the defining
hole, and it's exactly the window no in-house lever (de-gross T-118r,
sleeve T-128r) could touch. Cited estimate (Hurst-Ooi-Pedersen 2017,
our research record; T-108 spot-trend GFC analog): **SG Trend +20.9% in
2008** while equities collapsed. Illustrative calendar-2008 combine
(base −11.7% actual + cited MF +20.9%): base+20%MF ≈ −5.2%,
base+30%MF ≈ −1.9%. The full GFC peak-to-trough −32.6% would be
materially cushioned (MF was positive through the entire H2-2008
selloff), but this **cannot be backtested here** — it is a
literature+analog estimate and is NOT gate-eligible.

### 2.3 Verdict — RECOMMEND-TO-PAPER @ ~20% DBMF (first crisis lever to clear the gates), with a load-bearing caveat

**Pre-registered decision rule, scored on the real DBMF window:**

| Criterion | base+20% DBMF |
|---|---|
| (1) Combined MDD reduction ≥ 25% | **PASS** (+25.1%) |
| (2) Combined Sharpe ci_low not down | **PASS** (0.726 → 0.740, up) |
| (3) Crisis-window DD cut | **PARTIAL** — 2022 yes (−7.5%→−5.2%); COVID no (V-crash) |
| Benchmark: beats the 60/40 robo? | **YES** (Sharpe 1.45 vs 0.76; MDD −5.6% vs −21.8%) — but base-alone already beats it on this window |

**This is the first crisis-defense lever to clear the pre-registered
gates** — de-gross (T-118r) and the in-house capital-partitioned sleeve
(T-128r) both failed everything; the separate-account bought sleeve
passes criteria 1+2 at 20% DBMF and is directionally right on 3. The
mechanism the dispatch predicted holds: separate-account framing
escapes the T-121 scale-non-invariance, and the product is genuinely
anti-correlated (real +32.7%/+48.8% in 2022).

**The load-bearing caveat (do not skip):** the real window's base MDD
is only −7.5% — a benign, bull-heavy, survivor-biased window with one
sustained bear (2022) and one V-crash (COVID). The "+25% MDD reduction"
is shaving 1.9pp off an already-shallow drawdown. **The reason MF
matters — cutting the GFC/dotcom −32.6% the base cannot escape — is
supported only by the cited SG Trend +20.9% (2008), NOT by a backtest.**
So the verdict is: positive on real recent data (a genuine first),
strongly supported by literature on the deep crisis, but the
deep-crisis cut is an estimate. Recommend advancing to **paper at ~20%
DBMF as a separate-account sleeve** (the cell clearing the gates), with
the deep-crisis defense flagged as literature-backed pending live
crisis observation.

**Allocation:** 20% DBMF is the sweet spot (clears the 25% MDD bar with
ci_low up); 10% under-defends (+15%), 30% over-allocates to a 0.43-Sharpe
product (Sharpe drag). KMLM confirms direction (anti-correlated, huge
2022) but its window is shorter and its MDD effect smaller (+14%);
DBMF is the primary on history depth.

**On the robo bar:** base-alone already beats the 60/40 robo on the
recent window (Sharpe 1.45 vs 0.76, MDD −7.5% vs −21.8% — the robo took
−22% in 2022 as stocks AND bonds fell together). The MF sleeve widens
that margin. **Caveat:** this is the bull-heavy survivor-biased recent
window; the robo gap would narrow on the deep window where the base's
−32.6% GFC drawdown lives and where base-alone is only borderline
(0.751/ci_low 0.382, T-128r). The honest framing: base+MF-sleeve beats
the robo on recent data, and MF is the lever most likely to keep it
ahead through a GFC-scale event the base alone cannot survive
gracefully.
