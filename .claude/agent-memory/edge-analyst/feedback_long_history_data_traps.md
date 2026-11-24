---
name: feedback-long-history-data-traps
description: Statistical traps in century-long free data (Shiller, French daily, JST, T-306) that bias leverage/allocation studies — check these before designing any multi-decade arm
metadata:
  type: feedback
---

Before any multi-decade allocation or leverage design, check these traps.

**Data**
- **Shiller P is a monthly AVERAGE of daily closes.** That understates σ and adds autocorrelation. Never model levered or variance-drag arms on Shiller; use it for unlevered cohort extensions only.
- **French `6_Portfolios_ME_Prior_12_2_Daily` is constructed DAILY** (prior window −250 to −21 days), so it rebalances daily. It is not an MTUM proxy; use the monthly file. Its missing values are −99.99 / −999 sentinels.
- **French daily before 1952 has six-day weeks** (~294 bars/yr). Accrue fees, financing and haircuts by calendar days, not 1/252 per bar, or 1927–51 is overcharged by ~17 % (T-399 R.9).
- **T-306's post-1993 equity leg is processed SPY**, which carries the pre-seam DRIP error and a fee add-back convention. Using French Mkt+RF for the whole span avoids both.

**Statistics**
- **A deterministic fee or cash drag has zero tracking error.** The t-stat of "fund A minus fund B" can clear 2.96 for a trivial claim. Say what a pass would certify.
- **A bootstrap of a century of returns treats the realized mean as known.** Parameter uncertainty (SE ≈ 1.8 pp on the equity premium) must be a separate belief or δ row.
- **Overlapping 40-year cohorts:** ~2.5 independent windows per century. Never quote a cohort share as a probability.

**Code**
- **`MetricsEngine.bootstrap_distribution` is a fixed-length moving block** with an n^(1/3) block, despite its docstring saying "stationary / Politis-White". It returns zeros below 4 observations, a fail-open path, so guard the length.

**Added 2026-11-20 (T-409 rev. 3, while building the study code):**
- **FRED CPIAUCNS has no 2025-10.** BLS never published October 2025 (the federal shutdown). Declare the gap explicitly; never let a loader fill silently.
- **T-287's published "$929k vs $495k" drops 64 SPY days.** These are bond-market holidays: T-284's curves and the inner join sit on the bond synthetic's calendar, the T-297 class. Like for like (fee-free, as the published curve) the calendar-complete buy-hold is $1,025,316 vs $515,736 (ratio 1.99; my first $1,009,638 subtracted a 9 bp fee the curve never had — the reviewer caught it). Always check a "known number" for calendar holes before using it as a control target.
- **`xlrd` is not a declared dependency**, so Shiller's .xls cannot be read in study code. The repo's `data/macro/shiller_ie_data.csv` has P and D (dividends to 2024-06) but no CPI or GS10.
- **pypdf text extraction interleaves Rev. Proc. tables** (the single and head-of-household rows, Table 2, got mixed; I first misnamed it married-filing-separately). Verify brackets against the published cumulative "$X plus Y %" amounts, not threshold lists.

**Why:** found while designing T-409 (2026-11-19). Each one silently biases levered-vs-1× comparisons, mostly toward leverage.

**How to apply:** check this list when any prereg uses Shiller, French daily, JST or T-306, or quotes a gate t on an allocation contrast.

See [[project-t409-real-money-home-2026-11-19]], [[feedback-annualization-periods-trap-2026-11-11]].
