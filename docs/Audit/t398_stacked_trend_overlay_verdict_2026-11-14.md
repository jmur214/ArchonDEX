---
task_id: T-398
title: A buy-and-hold stacked trend overlay (100% equity + trend, the RSST structure) vs 1× equity, on investable net-of-fee trend returns — verdict
date: 2026-11-14
author: regime-analyst lens (in-session worktree subagent), branch research/stacked-trend-overlay-t398
outcome: "H1 NOT MET — the interval straddles zero. 100% equity + 100% trend on a 14-fund live composite, 2010-09 → 2025-12: Δ log wealth +0.37 %/yr, 95 % CI [−3.89, +4.17] %/yr vs 1× equity; active IR 0.05 against an MBL line of 0.55 (pinned gate) and 0.76 (N ≈ 372). Not supported on investable evidence; the door is shut for deployment."
status: COMPLETE — awaiting the director's read and an independent review by execution. Determinism ×2 is bit-identical. N_trials +1, recorded on acknowledgment.
reproduce: "python scripts/t398_stacked_trend_overlay.py integrity && python scripts/t398_stacked_trend_overlay.py gates && python scripts/t398_stacked_trend_overlay.py smoke && python scripts/t398_stacked_trend_overlay.py run --tag A && python scripts/t398_stacked_trend_overlay.py run --tag B   # reads the md5-verified snapshot data/t398_local/inputs/ (fetched once)"
---

# T-398 verdict — equity plus a trend overlay vs equity alone, on returns an investor could have earned

## 0. The answer

**H1 is NOT MET, and the interval straddles zero.** This is the outcome the pre-registration expected.
It is not "inconclusive but promising".

The director ran this test as an estimate, not as a gate. The reason, in the director's words: this is
a class-(2) question — a long-lived premium whose adoption is the owner's belief, not a gate pass. So
the outputs that matter are the investable estimate itself, the measured over-capture `h_L` read
against B-5's two break-evens (6.56 and 2.00 %/yr), the 2011–2019 drought cost, the worst three-year
relative shortfall and the crash-window correlation. H1 is scored exactly as frozen.

**The decision cell.** 100% equity + 100% trend held as one stacked fund, on an equal-weight composite
of 14 live trend funds, with a 1.00% fund fee, a 50 bp financing spread and a 1.0 %/yr survivorship
haircut, 2010-09-01 → 2025-12-31 (15.3 years):

| | point | 95% CI (21-day block bootstrap, 1,000 resamples, seed 0; MetricsEngine) |
|---|---|---|
| Δ log terminal wealth, total | **+0.057** | [−0.596, +0.640] |
| Δ log wealth per year | **+0.37 %/yr** | **[−3.89, +4.17] %/yr** |

- The sensitivities agree: [−3.65, +4.10] with the project-standard block and [−4.49, +4.04] with
  252-day blocks.
- The active information ratio is **0.05**. The MBL line needs 0.55 at the pinned gate and 0.76 at
  N ≈ 372. It is not close.
- The smaller overlays say the same: +50% is +0.26 [−1.86, +2.16]; +25% is +0.15 [−0.91, +1.10].

**The five things the owner's decision turns on.**

| | measured |
|---|---|
| What the overlay added, after every cost | +0.37 %/yr, anywhere from −3.9 to +4.2 |
| The 2011–2019 drought | cost 1.2 %/yr for nine years: **10% behind SPY** by the end of 2019 |
| The worst three years | **25% behind SPY** over 2022-06 → 2025-06; still behind its earlier peak at the end of 2025 |
| In stock-market falls | correlation with stocks −0.14 [−0.31, −0.02] across seven falls of 10% or more. **It lost more than SPY in five of the seven**, and saved 20 points in 2022 |
| Is AQR's paper factor too rich by enough to matter? | Over-capture `h_L` = +1.1 %/yr, CI [−4.2, +5.8]. **Still not pinned** |

**Where the +0.37 %/yr came from.** The total gain over SPY is +5.7 log points. Calendar 2022 alone
contributed +15.8. The other 14.3 years sum to −10.0, which is −0.7 %/yr. The first four months
(September–December 2010, three funds) contributed +7.0. The sign of the point estimate rests on one
year and one quarter.

**What this means for a Roth holder, in plain English.** Holding an RSST-style fund instead of SPY
over the last 15 years would have left you about where SPY left you — about 4% more money at the end
on a contribution schedule like yours ($358k against $343k) — and the data cannot tell that from
nothing, or from a loss. To get there you would have spent seven years behind SPY (2015 to 2022), been
paid back in a single year (2022), and then fallen 25% behind again by mid-2025. The crash in 2020 was
no shallower, and four of the other falls were deeper. Nothing here says the overlay loses. Nothing
here is a reason to buy it.

## 1. What was run

- **Pre-registration:** `docs/Sources/prereg_t398_stacked_trend_overlay_2026-11-14.md`.
  - **Frozen at `ac01413`** (sha256 `b6ac769a…`; lines 1–567 byte-identical throughout).
  - **Amendment 1** (`3136454`): the director's acknowledgment and rulings; pre-data implementation
    decisions.
  - **Amendment 2** (`28ef661`): the membership-and-ER table, from metadata, before any price.
  - **Run log A2.1** (`89c5d88`): the fetch, the integrity halt, BTOP50.
  - **Amendment 3** (`cddef75`): the director's rulings on the halt.
  - Each was committed alone, before the step it governs. The measurement code was committed at
    `9fe85c9`, after amendment 3 and before it was run on the data; the run is on `f1ee6eb`.
- **Harness:** `scripts/t398_stacked_trend_overlay.py`; 28 tests in
  `tests/test_t398_stacked_trend_overlay.py`. Standalone; never `BacktestController`. B-5's parsers,
  bootstrap replay and substrate loader are imported, never edited.
- **Determinism ×2:** runs A and B are bit-identical, file for file:

  | md5 | file |
  |---|---|
  | `d2e73967846574d724e13e4b6b2052aa` | `results.json` |
  | `8c1614e8186ce712084b25743a649da4` | `returns_W-L3.csv` |
  | `ca03d4bf84b2cbf8f67ab1b2312846e5` | `returns_W-L1.csv` |
  | `5d595dcf745649f1cee7fc31da3d91b0` | `monthly_W-L3.csv` |
  | `1c36fe3e09eb63482d00f799e113a5ce` | `run_manifest.json` |

- **Independent recomputation.** A separate script with its own calendar, membership, composite and
  arm code reproduced the decision cell's total (0.057262), the IR (0.0471), both drawdowns, the flat
  decade and the worst three years exactly. Its own-seed bootstrap gave [−3.75, +3.96] %/yr.
- **The bootstrap replay equals `MetricsEngine` on the decision cell** to under 1e-9 by assertion; the
  quoted H1 numbers are `MetricsEngine`'s own.
- **Inputs** (`data/t398_local/inputs/MANIFEST.json`, fetched once on 2026-11-14):
  - yfinance `fetch_yf_tr` (Adj Close, `auto_adjust=False`) for the candidates and the anchors;
  - byte copies of B-5's H.15 3-month bill and NY Fed SOFR files and of the AQR TSMOM file, each
    md5-checked against the prereg;
  - the T-306 equity leg, md5 `c2030019…`.
- **Windows.** W-L3 (decision): 2010-09-01 → 2025-12-31, 3,857 days, 15.33 years. W-L1 (reported):
  2007-03-01 → 2025-12-31, 4,741 days, 18.84 years; one fund until 2010.
- **Nothing dated 2026 enters a window.** The pinned T-306 equity file itself holds rows to 2026-04-17;
  the harness cuts the calendar at 2025-12-31 and halts if a window date exceeds it.
- **Census.** The largest financing-base gap is 1 business day. No fund price date falls off the
  equity calendar.

## 2. The composite: 14 funds, and one that is gone

| ticker | entered | ER used | note |
|---|---|---|---|
| RYMFX | 2007-03-01 | 1.99% | strategy change about 2012; the only member before 2010 |
| AQMIX | 2010-02-01 | **1.25%** | from memory, unverified (amendment 3) |
| ASFYX | 2010-09-01 | 1.45% | the third member: W-L3 opens here |
| WTMF | 2011-02-01 | 0.66% | strategy changes |
| EVOIX | 2011-11-01 | 1.34% | bond-sleeve collateral; now named Winton Managed Futures Trend |
| GMSSX | 2012-03-01 | 0.80% | |
| FMF | 2013-09-03 | 0.98% | strategy change; a thinly traded ETF |
| PQTIX | 2014-02-03 | 1.51% | |
| ABYIX | 2014-08-01 | 1.79% | |
| LOTIX | 2014-08-01 | 1.81% | |
| AHLIX | 2014-09-02 | 1.56% | |
| DBMF | 2019-06-03 | 0.85% | |
| KMLM | 2021-01-04 | 0.90% | |
| CTA | 2022-04-01 | 0.86% | |

Members by year: 3 in 2010, 5, 6, 7, then 11 from 2014, 12 in 2019, 13 in 2021, 14 from 2022.

**A dead fund left the composite.** CSAIX, the Credit Suisse managed-futures fund, was a pre-registered
candidate. Yahoo no longer has its history, so it returned nothing and is out under rule (a). Every
fund above is a survivor. **The 1.0 %/yr survivorship haircut in the decision cell is the only
allowance for that**, and it is a judgment, not a measurement.

**The composite itself, 2010-09 → 2025-12:**
- net of the funds' own fees it earned **+1.89 %/yr over cash**, at 7.9% volatility: a Sharpe of 0.24;
- gross of those fees, which is what the stacked fund's 1.00% replaces, +3.21 %/yr;
- its daily correlation with equity over the whole window is +0.07.

**AQMIX's expense ratio.** Yahoo reports 3.09%. The pre-declared cap would have used 2.00%. The
director ruled, before any return existed, that the decision cell uses the fund's net ratio, and 1.25%
"from memory, unverified" if it could not be read from sec.gov. It could not: the permission layer
refused the read before any request was sent. The correction is against the arm. Its size is in §6
(S7): 0.09 %/yr.

## 3. Evaluability gates and validations

All four gates pass; H1 is evaluable.

| gate | value | bar | |
|---|---|---|---|
| E1 depth of W-L3 | 15.33 years | ≥ 12 | pass |
| E2 composite (without DBMF) vs DBMF, monthly correlation, 79 months | 0.867 | ≥ 0.50 | pass |
| E3 integrity | 45 flags, all ruled (amendment 3) | none unruled | pass |
| E4 md5 of every input | match | match | pass |

Reported validations:
- **V1, the synthetic stack against live RSST** (2023-10-02 → 2025-12-31, 565 days). Live minus
  synthetic: **−0.4 %/yr, CI [−7.6, +6.1]**; tracking error 9.2%; daily correlation 0.94. The
  construction is not contradicted. On 2.25 years it cannot be confirmed either, which is why this was
  never a gate. B-5's AQR-based synthetic missed the same fund by −2.9 %/yr.
- **V2.** Each ETF against the composite without it: DBMF correlation 0.87 (+2.4 %/yr above the
  composite), KMLM 0.78 (−2.4 %/yr), CTA 0.61 (+7.0 %/yr on 45 months). Shape only, for the two live
  equity-plus-trend funds: BLNDX 0.78, MAFIX 0.86.
- **V3.** The composite against AQR TSMOM, monthly, on W-L3: 0.71.

## 4. The arms

Δ is Δ log wealth per year against 1× equity. Brackets are the primary 95% CI; "auto" is the
project-standard block and "252" is 252-day blocks (neither decides). ΔMDD is arm minus benchmark;
negative means deeper. Sortino carries its ci_low.

### W-L3 — 2010-09-01 → 2025-12-31 (15.33 yr; the decision window)

| arm | Δ %/yr [95% CI] | auto / 252 CI | CAGR | ×wealth | vol | MaxDD (trough) | ΔMDD | Sortino [ci_low] | IR (needs 0.55 / 0.76) |
|---|---|---|---|---|---|---|---|---|---|
| benchmark 1× equity | — | — | 14.92% | ×8.44 | 17.1% | −33.7% (2020-03) | — | 1.105 [0.496] | — |
| **+100% — DECISION** | **+0.37 [−3.89, +4.17]** | [−3.65, +4.10] / [−4.49, +4.04] | 15.35% | ×8.93 | 19.3% | −34.3% (2020-03) | −0.6 | 1.051 [0.418] | 0.05 |
| +50% | +0.26 [−1.86, +2.16] | [−1.75, +2.12] / [−2.18, +2.11] | 15.22% | ×8.79 | 17.8% | −34.0% | −0.3 | 1.101 [0.484] | 0.07 |
| +25% | +0.15 [−0.91, +1.10] | [−0.85, +1.08] / [−1.07, +1.08] | 15.09% | ×8.64 | 17.3% | −33.9% | −0.1 | 1.110 [0.496] | 0.08 |

No arm is shallower than equity in the window's deepest drawdown. The overlay raises volatility by 2.3
points at +100% and lowers the Sortino ratio.

### W-L1 — 2007-03-01 → 2025-12-31 (18.84 yr; one fund until 2010; reported)

| arm | Δ %/yr [95% CI] | 252 CI | CAGR | MaxDD (trough) | ΔMDD | IR (needs 0.50 / 0.68) |
|---|---|---|---|---|---|---|
| benchmark | — | — | 10.68% | −55.3% (2009-03) | — | — |
| +100% | +0.20 [−3.69, +4.10] | [−3.46, +4.06] | 10.90% | −50.4% | +4.9 | 0.02 |
| +50% | +0.18 [−1.76, +2.13] | [−1.66, +2.13] | 10.88% | −51.9% | +3.3 | 0.04 |
| +25% | +0.11 [−0.86, +1.08] | [−0.81, +1.09] | 10.81% | −53.4% | +1.8 | 0.05 |

Adding 2007–2010 changes nothing in the wealth answer. It makes the 2008–2009 drawdown 4.9 points
shallower, on the evidence of a single fund.

### The break-even spread curve (characterization)

| arm | Δ at s = 0 | point crosses zero at | ci_low at s = 0 |
|---|---|---|---|
| +100% | +0.88 %/yr | 87 bp | −3.38 %/yr |
| +50% | +0.52 | 102 bp | −1.60 |
| +25% | +0.28 | 110 bp | −0.78 |

Financing does not decide it: `ci_low` is below zero with a free spread. The lower bound would reach
zero only if the trend leg had earned about **3.8 %/yr more** than it did.

## 5. What a won't-sell investor would have sat through

| | +100% | +50% | +25% |
|---|---|---|---|
| Worst 3 years of relative wealth | **−25.1%** (2022-06-15 → 2025-06-20) | −13.2% | −6.8% |
| Longest stretch below its earlier relative peak | **6.9 years** (2015-04-14 → 2022-03-24) | 6.9 years | 6.9 years |
| Deepest point below a relative peak | −26.3% (2025-05-14) | −14.0% | −7.2% |
| Still below its peak at the end of 2025? | yes | yes | yes |
| 2011–2019, the flat decade | **−10.2%** (−1.19 %/yr) | −4.7% | −2.2% |
| Calendar 2022 | **+17.1%** | +8.4% | +4.2% |
| 2020–2025 | +9.9% (+1.58 %/yr) | +5.4% | +2.8% |

- The drought was shorter in cost than predicted (1.2 %/yr against an expected 1.5–3) and exactly as
  long as feared.
- **The worst three years are the most recent three.** After 2022 the overlay gave back everything
  2022 had paid and more.

### In equity drawdowns

Seven benchmark falls of 10% or more inside W-L3:

| peak → trough | days | benchmark | +100% arm | trend leg's excess return | corr daily | corr 5-day |
|---|---|---|---|---|---|---|
| 2011-04-29 → 2011-10-03 | 108 | −18.6% | **−24.4%** | −6.2% | −0.11 | −0.15 |
| 2015-07-20 → 2016-02-11 | 143 | −13.1% | −8.8% | +6.0% | −0.37 | −0.52 |
| 2018-01-26 → 2018-02-08 | 9 | −10.1% | **−17.6%** | −8.0% | **+0.61** | — |
| 2018-09-20 → 2018-12-24 | 65 | −19.4% | **−21.6%** | −2.1% | +0.01 | +0.15 |
| 2020-02-19 → 2020-03-23 | 23 | −33.7% | **−34.2%** | −0.6% | −0.14 | — |
| 2022-01-03 → 2022-10-12 | 195 | −24.5% | −4.7% | **+27.8%** | −0.36 | −0.28 |
| 2025-02-19 → 2025-04-08 | 34 | −18.8% | **−25.2%** | −7.5% | **+0.51** | +0.73 |

- **Pooled over the 577 episode days:** correlation **−0.14, CI [−0.31, −0.02]** (paired 21-day block
  bootstrap). On the other 3,280 days it is +0.17.
- **Two of the seven episodes exceed T-316's +0.30 bar:** early 2018 and early 2025. In both, a trend
  program that was long stocks after a rally fell with them.
- **The arm lost more than the benchmark in five of the seven.** It was the better holding in the two
  slow falls, 2015–16 and 2022.
- **These correlation figures carry extra daily noise** from the reversing price prints in the fund
  data (Appendix A). The episode returns and drawdowns are not affected.

**The regime reading (the macro lens).** The trend leg is a slow-bear hedge, not a crash hedge. It paid
in the one sustained, inflation-driven bear market in the window and cost money at the start of every
fast fall. That is the mirror image of the bond stack B-5 tested, which failed in exactly that regime.
By stock–bond correlation regime (B-5's definition): in the positive-correlation years 2022–2024 the
+100% arm made +1.50 %/yr, CI [−11.5, +13.1]; in the other years +0.10 %/yr, CI [−4.0, +3.7]. Three
years is not a sample. The classification is after the fact and is not a rule anyone could have
traded.

**The accumulation scorecard** ($10k in August 2010, $5k each January; $85k paid in):

| | terminal |
|---|---|
| benchmark | $343,276 |
| +100% | $357,895 |
| +50% | $353,604 |
| +25% | $349,164 |

## 6. Sensitivities (all on the +100% arm; none decides)

| | window | members | Δ %/yr [95% CI] | 252-day CI |
|---|---|---|---|---|
| **Decision cell** | 2010-09 → | 3–14 | **+0.37 [−3.89, +4.17]** | [−4.49, +4.04] |
| S5 no survivorship haircut | same | 3–14 | +1.37 [−2.89, +5.17] | [−3.49, +5.04] |
| S6 survivorship haircut 2.0 %/yr | same | 3–14 | −0.62 [−4.89, +3.17] | [−5.49, +3.04] |
| S4 no ER gross-up (double fee) | same | 3–14 | −0.94 [−5.20, +2.86] | [−5.80, +2.73] |
| S7 AQMIX's ER as written (2.00%) | same | 3–14 | +0.46 [−3.81, +4.26] | [−4.41, +4.12] |
| Spread zero instead of 50 bp | same | 3–14 | +0.88 [−3.38, +4.68] | [−3.98, +4.54] |
| S3 screener: 4 more fund families | same | 4–18 | +0.42 [−3.67, +4.05] | [−4.36, +4.00] |
| S1 pure-play (without the four flagged funds) | 2012-03 → | 3–10 | +1.28 [−3.31, +5.70] | [−3.06, +6.50] |
| … decision composite on S1's window | 2012-03 → | 6–14 | +0.50 [−3.73, +4.47] | — |
| S2 ETFs only | 2019-06 → | 3–5 | +1.66 [−4.60, +8.15] | [−4.35, +7.85] |
| … decision composite on S2's window | 2019-06 → | 12–14 | +1.58 [−5.36, +8.33] | — |

- **No sensitivity clears.** Every interval straddles zero by a wide margin.
- **The sign of the point estimate depends on two numbers nobody has measured.** It is positive at a
  survivorship haircut of 1.0 %/yr and negative at 2.0. It is negative if the stacked fund cannot
  deliver its trend program for less than these funds charged.
- **The candidate list was not flattering.** The category screen added four fund families the list had
  missed (Arrow, Grant Park, LoCorr Macro, LoCorr Long/Short Commodity). With them the answer moves by
  0.05 %/yr. One of the four (MFTTX) carries 34 integrity flags of its own; it is listed, not ruled.
- **The four flagged-strategy funds pull the composite down by about 0.8 %/yr** on a common window.
  That is the cost of including funds whose strategies drifted, and it is also what answers "what if
  their data is bad": without them the result is still not distinguishable from zero.

## 7. The frictionless factor on the same window, and the over-capture

| | window | Δ %/yr [95% CI] | IR |
|---|---|---|---|
| AQR, +50% (B-5, quoted) | 1985–2025 | +5.11 [+3.25, +6.95] | 0.81 |
| AQR, +50% (B-5, quoted) | 2000–2025 | +3.47 [+0.99, +5.99] | 0.53 |
| **AQR, +50%, this study** | **2010-09 → 2025-12** | **+1.40 [−1.91, +4.50]** | 0.22 |
| AQR, +100%, this study | 2010-09 → 2025-12 | +2.40 [−4.24, +8.60] | 0.18 |
| Live composite, +50% (with the haircut) | 2010-09 → 2025-12 | +0.26 [−1.86, +2.16] | 0.07 |
| DBMF live, +50% (B-5, quoted) | 2019-06 → 2025-12 | +2.58 [−1.70, +7.04] | 0.46 |

**The paper factor itself stopped clearing.** On the months an investor could actually have bought a
trend fund, AQR's own overlay is +1.40 %/yr with an interval through zero. The factor earned
4.32 %/yr over cash in this window. Most of the distance between B-5's +5.11 and the investable +0.26
is **the era, not the fees**: the paper premium was far larger before 2010.

**The measured over-capture.** `h_L` = AQR minus the composite gross of fund fees, on the 184 months of
W-L3:

| block | `h_L` %/yr | 95% CI |
|---|---|---|
| 1 month (primary) | **+1.10** | **[−4.17, +5.78]** |
| automatic (6 months) | +1.10 | [−3.07, +5.10] |
| 12 months | +1.10 | [−3.67, +5.18] |

Tracking error between the two is 9.3 %/yr.

**The pre-named transport reading: "the haircut is still not pinned."**
- Its lower bound is not above 2.00, so the 2000–2025 AQR clearance is not voided.
- Its lower bound is not above 6.56, so the 1985–2025 clearance is not closed.
- Its upper bound with the survivorship haircut added (6.78) is not below 2.00, so neither window is
  shown to survive.
- The point (+1.10, or +2.10 with the survivorship haircut) sits at the 2000–2025 break-even and well
  below the 1985–2025 one. It is better measured than the two earlier readings (2.9 and 5.3 on about
  2.5 years each) and still spans every threshold.

**The AQR file is restated.** Its two vintages on disk differ by more than 10 bp in 126 of 481 common
months (correlation 0.998; mean difference −0.05 %/yr). The series is not point-in-time.

**Level 2 did not run.** SG Trend and SG CTA need a registration, which was not made. BarclayHedge's
BTOP50 page serves only 2022–2026 without a login, so the first of the director's two conditions
failed. **Disclosure:** while that page was being checked, a printed passage showed the BTOP50's
late-2025 and 2026 monthly figures. They were not loaded or used. Any later use of 2026 as a holdout
for a trend *index* must carry this disclosure. The fund and equity holdout is intact.

## 8. Predictions (prereg §11) vs outcomes, line by line

| prediction | outcome | hit? |
|---|---|---|
| 3 members at the W-L3 start; 12 to 15 by 2022 | 3; 14 | hit |
| Composite volatility 7–10 %/yr | 7.9% | hit |
| Composite net excess +0.3 to +2.0 %/yr | +1.89 | hit (upper end) |
| Composite gross of fund ERs +1.5 to +3.5 %/yr | +3.21 | hit |
| Decision cell point −1.5 to +1.0 %/yr | +0.37 | hit |
| CI half-width 3.5–5.5 %/yr | 4.03 | hit |
| ci_low between −6 and −3 %/yr | −3.89 | hit |
| **H1 NOT MET** | NOT MET | hit |
| +50% within ±0.6; +25% within ±0.3; neither clears | +0.26; +0.15; neither | hit |
| S5 point −0.5 to +2.0; ci_low < 0 | +1.37; −2.89 | hit |
| S1 above the broad composite by 0 to +1.0 %/yr | +0.78 on a common window | hit |
| Flat decade −10% to −30% of relative wealth | −10.2% | hit (at the mild edge) |
| Worst 3-year shortfall −15% to −30% | −25.1% | hit |
| 2022: Δ +12 to +28 pp | +15.8 pp (log); +17.1% | hit |
| Arm MaxDD −30% to −42%; benchmark about −34%; not shallower in 2020 | −34.3%; −33.7%; deeper by 0.5 | hit |
| Pooled drawdown correlation −0.35 to +0.25 | −0.14 | hit |
| At least two episodes above +0.30; early 2018 the worst; 2022 negative | two; 2018 at +0.61; 2022 at −0.36 | hit |
| `h_L` point +1 to +6 %/yr | +1.10 | hit (low edge) |
| `h_L` CI half-width about 4 | 5.0 (primary); 4.1 (automatic) | **miss** on the primary |
| `h_L` resolves neither break-even | resolves neither | hit |
| AQR on W-L3, +50%: +0.5 to +3; far below +5.11 | +1.40 | hit |
| V1: synthetic minus live RSST −4 to +6 %/yr; includes zero | +0.4; [−6.1, +7.6] | hit |
| E2 correlation 0.65–0.85 | 0.867 | **miss** (just above) |
| §12: decision cell about −1.0 to +0.3 %/yr | +0.37 | **miss** by 0.07 |
| §12: a nine-year stretch costing 1.5–3 %/yr | 1.19 %/yr | **miss** (milder) |

The forecast was written from memory of these funds' returns, so a high hit rate shows that the memory
was accurate and nothing more. The pre-data power analysis was right: the interval is ±4.0 %/yr around
a point near zero.

## 9. Caveats (each disclosed; none changes the verdict)

1. **Survivorship.** The composite is 14 survivors; one pre-registered fund is already gone. The
   1.0 %/yr haircut is a judgment. At 2.0 the point is negative (S6).
2. **The fee substitution.** The decision cell adds back each fund's own fee (1.3% on average) and
   charges 1.00% once. Without the add-back the point is −0.94 %/yr (S4). Three members carry manager
   fees inside swaps that are not in their reported ratios, which works against the arm.
3. **AQMIX's expense ratio is unverified.** 1.25% from memory, against Yahoo's 3.09%. The effect is
   0.09 %/yr (S7).
4. **Fund price data.** 45 integrity flags were raised and accepted as-is by the director (Appendix A).
   Yahoo's Adj Close handled every large year-end distribution. Its defects are one-day prints that
   reverse, net asset values that arrive a day late, and a thinly traded ETF's closing prices. They
   are wealth-neutral and add daily noise.
5. **KMLM 2022-12-28.** Raw −10.29%, adjusted −3.32%, on a day with a recorded distribution. This may
   be a distribution Yahoo under-records by about 3%. If it is, the error is against the arm, by about
   0.01 %/yr on the composite.
6. **The window opens at an adverse moment for trend** (after 2008, before the flat decade) and ends
   after three poor years. It is the investable record. W-L1 adds 2008 on one fund and does not change
   the wealth answer.
7. **One composite is not one fund.** A holder owns a single manager's program. DBMF, KMLM and CTA
   differ from the composite by −2.4 to +7.0 %/yr. RSST has 2.25 years of history.
8. **Substrate (`[NN-SUBSTRATE-REVERIFY]`).** Conditional on the T-306 build of 2026-07-10 and on
   Yahoo's Adj Close as fetched on 2026-11-14. Every window is after 1993, where the equity leg is
   SPY's total return.
9. **The 50 bp spread is conservative** for a futures-financed fund. At zero the point is +0.88 %/yr
   and the lower bound −3.38.
10. **Honest N.** +1, recorded on acknowledgment (`config/honest_n_trials.json` on main, `9fed69f`);
    not recorded again here. The MBL line is quoted at this branch's pinned gate (37.08) and at 372.28.
    The measured IR is less than a tenth of either line.
11. **The sec.gov read did not happen.** The permission layer refused it. The owner can read AQMIX's
    net expense ratio from its summary prospectus in a minute; it would move the result by under
    0.1 %/yr.

## 10. What this means

**For the program.** The stacked trend overlay is **not supported on investable evidence**. Per the
pre-named outcome, the door is shut for deployment and the interval is the record: over 2010–2025 the
overlay was worth somewhere between −3.9 and +4.2 %/yr at +100%, and between −1.9 and +2.2 at +50%.

Three things are now on record that were not before:
- **B-5's +5.11 %/yr is not an estimate of what the overlay is worth today.** The same paper factor on
  2010–2025 gives +1.40 with an interval through zero. The headline was earned before trend funds
  existed for retail investors.
- **Fees and frictions are not the main story.** The measured over-capture is +1.1 %/yr, not the 2.9
  or 5.3 of the two short readings, though its interval still spans them.
- **The question cannot be settled by more backtesting.** No free long net index exists: SG's needs a
  registration and BarclayHedge's history is behind a login. Even a 26-year index would have had about
  a 4% chance of clearing as specified.

**For a Roth holder.** RSST, or half SPY and half RSST, is a legitimate thing to hold on a belief that
trend-following's long history continues. It is not something this program's evidence recommends. The
honest description: roughly SPY's return, two more points of volatility, deeper losses at the start of
most sell-offs, one large payoff in a slow inflationary bear market, and stretches of seven years
behind. 1× SPY remains the honest default.

**A forward clock (ruling R-13; a proposal, nothing built, `paper_trader/` untouched).** The only
instrument that accrues real evidence is the live fund. A report-only shadow on the T-316 pattern
would cost no trial:
- **The book:** a hypothetical 100% RSST held beside its SPY twin, daily, from the first record.
- **Gate A — it behaves like the structure tested here.** Over each rolling 12 months, live RSST minus
  this harness's synthetic stays inside ±9 %/yr (one tracking error). A breach means the product is
  not the thing that was measured.
- **Gate B — the crash coincidence is bounded.** In the next SPY fall of 10% or more, RSST's fall is no
  more than 8 points deeper than SPY's (the worst episode here was 7.5).
- **What it cannot do:** confirm an edge. At the information ratio measured here that takes decades.
  Its use is to catch a structural failure early, and it should be framed that way from the first
  line.

---

## Appendix A — the 45 integrity flags, by class (all ACCEPTED AS-IS; amendment 3, ruling 1)

No price was changed, dropped, smoothed or re-sourced. Figures are one-day Adj Close returns. "D1" is a
raw fall of 3% or more with no recorded distribution on a quiet day for the other funds; "D2" is five
or more identical closes; "D4" is a one-day move above 8%. Raw equals adjusted on all 36 D1 flags.

**A. Prints that reverse within one to three days (11 flags; wealth-neutral)**

| fund | date | check | return | what reverses it |
|---|---|---|---|---|
| RYMFX | 2017-04-21 | D1 | −7.84% | +8.97% the next day |
| RYMFX | 2017-04-24 | D4 | +8.97% | the reversal of the line above |
| FMF | 2022-03-14 | D4 | +8.47% | −4.90% and −3.21% over the next two days |
| FMF | 2022-03-15 | D1 | −4.90% | part of the same three days |
| FMF | 2022-03-16 | D1 | −3.21% | part of the same three days |
| FMF | 2014-11-26 | D1 | −3.06% | undoes +2.84% the day before |
| FMF | 2018-11-08 | D1 | −4.18% | undoes +4.36% the day before |
| FMF | 2020-03-31 | D1 | −4.57% | undoes +6.69% the day before |
| FMF | 2016-11-09 | D1 | −3.48% | +3.56% the next day |
| FMF | 2016-12-07 | D1 | −3.71% | +3.20% the next day |
| WTMF | 2024-11-22 | D1 | −3.35% | undoes +4.58% the day before |

**B. FMF closing-price noise that does not reverse in a day (8 flags; cannot be resolved without a net
asset value source)**

| date | return | others' median | note |
|---|---|---|---|
| 2014-04-04 | −6.51% | −0.07% | prior day exactly 0.00; the least explicable flag |
| 2014-05-05 | −3.65% | −0.19% | |
| 2016-03-17 | −3.19% | +0.41% | |
| 2016-09-23 | −3.47% | −0.22% | |
| 2016-09-30 | −3.53% | −0.20% | |
| 2016-10-24 | −3.29% | +0.25% | |
| 2016-11-01 | −3.45% | −0.74% | |
| 2017-03-02 | −4.23% | −0.94% | five other funds below −1% |

These are two to three standard deviations on FMF's own trailing volatility; its close-to-close series
was that noisy in 2016. No distribution is within 100 days of any of them.

**C. Losses on market days (19 flags; real)**

| fund | date | check | return | context |
|---|---|---|---|---|
| CTA | 2023-03-13 | D4 | −11.67% | the bank-failure rates reversal; 12 of 13 others below −1% |
| CTA | 2023-12-13 | D1 | −3.23% | a Federal Reserve day |
| CTA | 2025-08-01 | D1 | −3.46% | a payrolls day |
| LOTIX | 2020-02-27 | D1 | −3.94% | SPY −4.49% |
| LOTIX | 2020-03-12 | D1 | −4.29% | SPY −9.57% |
| LOTIX | 2024-08-01 | D1 | −3.09% | five others below −1% |
| LOTIX | 2024-08-05 | D4 | −8.82% | the yen-carry unwind; 9 of 13 others below −1% |
| LOTIX | 2024-10-07 | D1 | −3.07% | six others below −1% |
| GMSSX | 2024-10-07 | D1 | −4.20% | the same day; its prior day was exactly 0.00 |
| DBMF | 2020-03-09 | D1 | −3.02% | SPY −7.81% |
| DBMF | 2020-03-12 | D1 | −3.90% | SPY −9.57% |
| DBMF | 2021-12-01 | D1 | −3.01% | SPY −1.11% |
| DBMF | 2024-08-02 | D1 | −3.31% | six others below −1% |
| KMLM | 2021-05-13 | D1 | −3.42% | four others below −1% |
| KMLM | 2022-06-30 | D1 | −3.97% | four others below −1% |
| KMLM | 2022-07-12 | D1 | −3.10% | three others below −1% |
| KMLM | 2022-09-07 | D1 | −3.13% | three others below −1% |
| PQTIX | 2015-01-15 | D1 | −3.10% | the Swiss franc unpeg |
| RYMFX | 2014-02-03 | D1 | −3.02% | SPY −2.25% |

**D. A net asset value that arrived a day late (2 flags; prior day exactly 0.00)**

| fund | date | return | context |
|---|---|---|---|
| PQTIX | 2023-11-06 | −3.18% | others +0.45%; the prior session was a sharp rates reversal |
| EVOIX | 2020-05-19 | −3.27% | others −0.20%; a recorded distribution four days earlier |

**E. Identical closes (5 flags)**

| fund | dates | closes |
|---|---|---|
| RYMFX | 2007-02-22 → 2007-03-02 | seven at $25.00: the launch seed period; touches two days of W-L1 only |
| EVOIX | 2012-11-27 → 2012-12-03 | five |
| EVOIX | 2012-12-24 → 2012-12-31 | five |
| EVOIX | 2013-03-05 → 2013-03-11 | five |
| FMF | 2013-09-23 → 2013-09-27 | five, in its first weeks |

**What the check cleared.** Across the 14 funds, 70 raw falls of 3% or more matched a recorded
distribution and were neutral in Adj Close (for example ASFYX 2022-12-29: raw −24.4%, adjusted
+0.05%). The failure the halt was built for did not occur.

## Reproduce

```bash
# inputs: metadata and prices were fetched ONCE (each command refuses a second run);
# every later step reads the md5-verified snapshot under data/t398_local/
python scripts/t398_stacked_trend_overlay.py integrity     # lists the 45 flags; exit 0 with the rulings file
python scripts/t398_stacked_trend_overlay.py gates         # -> data/t398_local/gates.json
python scripts/t398_stacked_trend_overlay.py smoke         # -> smoke.json (never quoted)
python scripts/t398_stacked_trend_overlay.py run --tag A   # -> data/t398_local/run_A/
python scripts/t398_stacked_trend_overlay.py run --tag B   # determinism twin
md5 -r data/t398_local/run_A/* data/t398_local/run_B/*
python -m pytest tests/test_t398_stacked_trend_overlay.py -q
```
