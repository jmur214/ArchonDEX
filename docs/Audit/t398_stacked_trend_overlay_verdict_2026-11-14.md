---
task_id: T-398
title: A buy-and-hold stacked trend overlay (100% equity + trend, the RSST structure) vs 1× equity, on investable net-of-fee trend returns — verdict
date: 2026-11-14
author: regime-analyst lens (in-session worktree subagent), branch research/stacked-trend-overlay-t398
outcome: "H1 NOT MET — the interval straddles zero. 100% equity + 100% trend on a 14-fund live composite (AQMIX's expense ratio 1.25% from memory, unverified), 2010-09 → 2025-12: Δ log wealth +0.37 %/yr, 95 % CI [−3.89, +4.17] %/yr vs 1× equity; active IR 0.05, CI [−0.48, +0.55], against an MBL line of 0.76 at the gate in force (N_eff 372.28) and 0.55 at the pre-T-391 pin. Not supported on investable evidence; the door is shut for deployment. Sensitivity S3 (the category screen) rests on unruled data and decides nothing."
status: COMPLETE — reviewed independently by execution at `04063c2` (measurement confirmed; write-up, tests and labels NOT READY); review round 1 applied 2026-11-14, see the last section. Determinism ×2 is bit-identical. N_trials +1, recorded on acknowledgment.
reproduce: "restore the archived snapshot (see Reproduce), then: python scripts/t398_stacked_trend_overlay.py integrity && python scripts/t398_stacked_trend_overlay.py gates && python scripts/t398_stacked_trend_overlay.py smoke && python scripts/t398_stacked_trend_overlay.py run --tag A && python scripts/t398_stacked_trend_overlay.py run --tag B && python scripts/t398_stacked_trend_overlay.py determinism"
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
haircut, 2010-09-01 → 2025-12-31 (15.3 years). Each fund's own fee is added back; **AQMIX's is 1.25%,
from memory and unverified** (amendment 3; the as-written 2.00% is sensitivity S7, +0.083 %/yr).

| | point | 95% CI (21-day block bootstrap, 1,000 resamples, seed 0; MetricsEngine) |
|---|---|---|
| Δ log terminal wealth, total | **+0.057** | [−0.596, +0.640] |
| Δ log wealth per year | **+0.37 %/yr** | **[−3.89, +4.17] %/yr** |

- The sensitivities agree: [−3.65, +4.10] with the project-standard block and [−4.49, +4.04] with
  252-day blocks.
- The active information ratio is **0.05, CI [−0.48, +0.55]** (the same bootstrap). The MBL line needs
  0.76 at the gate in force (N_eff 372.28) and 0.55 at the pre-T-391 pin (37.08). The point is not
  close to either; the interval's upper end is below the line in force.
- The smaller overlays say the same: +50% is +0.26 [−1.86, +2.16]; +25% is +0.15 [−0.91, +1.10].
- **S3, the category-screen sensitivity, decides nothing** and rests on fund data whose integrity flags
  were never ruled (§6).

**The five things the owner's decision turns on.** Two frames are used below and they are different
questions. **"Since the start"** compares the holder with SPY from 2010-09-01. **"Below its own high"**
compares the holder with the best lead over SPY they had already reached.

| | measured |
|---|---|
| What the overlay added, after every cost | +0.37 %/yr, anywhere from −3.9 to +4.2 |
| 2011–2019, the drought | cost 1.2 %/yr over those nine years. A holder who started in January 2011 was **10.2% behind SPY** at the end of 2019; the holder from the 2010-09 start was **3.7% behind** |
| The worst three years | relative wealth **fell 25.1%** between the 2022-06-14 close and 2025-06-20 (the 756-day window's first return day is 2022-06-15, the date §5's table uses): from 30.9% ahead of SPY since the start to 2.0% behind. At the end of 2025 the holder was 5.9% ahead since the start and 20% below their own high |
| In stock-market falls | correlation with stocks −0.14 [−0.31, −0.02] across seven falls of 10% or more; the exclusion of zero rests on two of the seven (§5). **It lost more than SPY in five of the seven**, and saved 20 points in 2022 |
| Is AQR's paper factor too rich by enough to matter? | Over-capture `h_L` = +1.1 %/yr, CI [−4.2, +5.8]. **Still not pinned** |

**Where the +0.37 %/yr came from: any single large year moves the sign.** The total gain over SPY is
+5.7 log points. Seven of the sixteen calendar-year contributions are larger than that in size.
Removing any one of 2022 (+15.8), 2014 (+10.9) or September–December 2010 (+7.0, three funds) turns
the total negative. Removing any one of 2018 (−8.6), 2023 (−8.1), 2011 (−6.7) or 2012 (−6.4) more than
doubles it. The point estimate is the small difference of a few large years, not a steady +0.37.

**What this means for a Roth holder, in plain English.** Holding an RSST-style fund instead of SPY
from September 2010 to the end of 2025 would have left you 5.9% ahead of SPY on a lump sum, and about
4% ahead on a contribution schedule like yours ($358k against $343k). The data cannot tell that from
nothing, or from a loss.

*Measured since the start*, you were behind SPY on 39% of days, at worst by 8.8% (October 2013), and
continuously behind for at most 2.6 years (January 2012 to September 2014).

*Measured against the best lead you had already reached*, it was harder. In April 2015 you were 17.8%
ahead of SPY; it took 6.9 years, to March 2022, to regain that lead. During those years you were still
ahead of SPY since the start on 58% of days, and behind at the ends of 2018, 2019 and 2020. Calendar
2022 took the lead to 32.7%. By May 2025 all of it was gone: you were 2.3% behind SPY since the start,
which is 26% below that high.

The crash in 2020 was no shallower, and four of the other falls were deeper. Nothing here says the
overlay loses. Nothing here is a reason to buy it.

## 1. What was run

- **Pre-registration:** `docs/Sources/prereg_t398_stacked_trend_overlay_2026-11-14.md`.
  - **Frozen at `ac01413`** (sha256 `b6ac769a…`; lines 1–567 byte-identical throughout).
  - **Amendment 1** (`3136454`): the director's acknowledgment and rulings; pre-data implementation
    decisions.
  - **Amendment 2** (`28ef661`): the membership-and-ER table, from metadata, before any price.
  - **Run log A2.1** (`89c5d88`): the fetch, the integrity halt, BTOP50.
  - **Amendment 3** (`cddef75`): the director's rulings on the halt.
  - Each was committed alone, before the step it governs. The measurement code was committed at
    `9fe85c9`, after amendment 3; the first run is on `f1ee6eb`. What that ordering does and does not
    establish is set out under "Order of events" below.
- **Harness:** `scripts/t398_stacked_trend_overlay.py`; 42 tests in
  `tests/test_t398_stacked_trend_overlay.py` (28 at the first verdict; see the review section for the
  reversion proof). Standalone; never `BacktestController`. B-5's parsers, bootstrap replay and
  substrate loader are imported, never edited.
- **Determinism ×2:** runs A and B are bit-identical, file for file, and
  `python scripts/t398_stacked_trend_overlay.py determinism` now enforces it (prereg §18):

  | file | md5, first verdict (`f1ee6eb`) | md5, re-stamped on the merged tree |
  |---|---|---|
  | `returns_W-L3.csv` | `8c1614e8186ce712084b25743a649da4` | **unchanged** |
  | `returns_W-L1.csv` | `ca03d4bf84b2cbf8f67ab1b2312846e5` | **unchanged** |
  | `monthly_W-L3.csv` | `5d595dcf745649f1cee7fc31da3d91b0` | **unchanged** |
  | `results.json` | `d2e73967846574d724e13e4b6b2052aa` | see below |
  | `run_manifest.json` | `1c36fe3e09eb63482d00f799e113a5ce` | follows `results.json` |

  **`results.json` was re-stamped; the measurement was not re-done. This is not a new trial.**
  - `d2e73967…` is the first verdict's file. It embeds the honest-N gate as read on this branch before
    T-391 merged (N_eff 36.92).
  - `b2a77c87564af43ddab891347efe30d9` is the **same code** run on the tree after main `39c47aa` was
    merged in (T-391's recorder). The file embeds the live gate reading, so that one field changed
    (36.92 → 372.28).
  - `a13fbc9fc9cbfd14cfd05781c86bbd2b` is the review-round-1 file (unchanged after main `fc7254b` was
    merged in: the gate still reads 372.28). Of the 2,285 values in the first file, 3 differ: that
    gate reading and two label strings (the prereg reference now names amendment 3; the decision-cell
    string now says AQMIX's ratio is unverified). 137 values were added: an interval on every IR and
    on the composite's Sharpe ratio, the anchors' flag counts, and the file bindings. No measured number in
    the first file changed (the gate reading is a number, but an input read from the live gate, not a
    measurement of this study). The three return CSVs are byte-identical across all three. Note for anyone reading
    `results.json` by key: `honest_n.n_eff_conservative_plus1` (37.08) and every
    `mbl.ir_needed_neff_gate_plus1` (0.551) are the PRE-T-391 pin, not the gate in force; the gate in
    force is `honest_n.n_eff_conservative` (372.28), and the IR it needs is 0.757 (§8).
- **Independent recomputation** (`scripts/t398_independent_recompute.py`, committed in review round 1).
  It shares no measurement code with the harness except the financing base, which it takes from
  `h.financing_base()` (B-5's H.15/SOFR parser): its own calendar, membership, composite and arm. So it
  cannot catch an error in the cash rate; the review's own from-scratch code parsed H.15 and SOFR itself
  and matched the composite to 6.8e-20. It
  reproduces the decision cell's total (0.057262), the IR (0.0471), the flat decade, 2022 and the worst
  three years to within 1e-9 and exits non-zero otherwise. Its own-seed bootstrap gives
  [−3.75, +3.96] %/yr. The reviewer's separate implementation agreed to 1e-16 per bar.
- **The bootstrap replay equals `MetricsEngine` on the decision cell** to under 1e-9 by assertion; the
  quoted H1 numbers are `MetricsEngine`'s own.
- **Inputs** (`data/t398_local/inputs/MANIFEST.json`, fetched once on 2026-11-14):
  - yfinance `fetch_yf_tr` (Adj Close, `auto_adjust=False`) for the candidates and the anchors;
  - byte copies of B-5's H.15 3-month bill and NY Fed SOFR files and of the AQR TSMOM file, each
    md5-checked against the prereg;
  - the T-306 equity leg, md5 `c2030019…`.
- **Windows.** W-L3 (decision): 2010-09-01 → 2025-12-31, 3,857 days, 15.33 years. W-L1 (reported):
  2007-03-01 → 2025-12-31, 4,741 days, 18.84 years; one fund until 2010.
- **Nothing dated 2026 enters a window — but pinned files with 2026 rows are cut, not refused.** Prereg
  §18 says the harness halts on "any row dated 2026 in a loaded series". As built, that halt applies to
  the fetched fund and anchor price files. The pinned inputs are different: the T-306 equity file holds
  rows to 2026-04-17, the bond file to 2026-07-08, the H.15 file to 2026-11-09 and the AQR file to
  2026-05. They are read whole and **cut at 2025-12-31**; the harness halts only if a *window* date
  exceeds that. This is narrower than §18's wording and is disclosed as such.
- **Census.** The largest financing-base gap is 1 business day. No fund price date falls off the
  equity calendar.

### Order of events, and what the record can and cannot show

Local times on 2026-11-14, from git and from the files' own times:

| time | event |
|---|---|
| 00:21:02 | prereg committed (`ac01413`) |
| 00:25:56 | amendment 1 committed |
| 00:28:07 | **metadata fetched — from code not yet committed** |
| 00:29:19 | amendment 2 (membership and ER) committed |
| 00:30:47 | acquisition code committed (`61eeb7b`) |
| 00:32:40 | prices fetched, from the committed code |
| 00:33:18 | per-flag integrity evidence written (an uncommitted scratch script) |
| 00:34:34 | **the two BarclayHedge requests — from code not yet committed** (`b3d2cc7` at 00:36:23) |
| 00:39:00 | amendment 3 committed |
| 00:43:58 | **the screener call — from code not yet committed** |
| 00:46:47 | measurement code and its tests committed (`9fe85c9`) |
| 00:46:50 → | rulings file, S3 prices (00:47:02), gates, smoke; `f1ee6eb` at 00:47:25; then runs A and B |

- **What this establishes.** Each amendment was committed before the step it governs. Every gate, smoke
  and run output is dated after the measurement code's commit.
- **What it cannot establish.** The measurement code was written between 00:39 and 00:46 **with the
  prices already on disk**. No commit or file time can prove that code was not executed on those prices
  before it was committed. It was not: before the commit it was only compiled and run through its 28
  synthetic tests. That is this author's account, not something the record proves.
- **Three network steps ran from uncommitted code:** the metadata fetch, the two BarclayHedge requests
  and the screener call. In each case the code was committed minutes later; that it was committed without
  change to the command that had run is this author's account, not something the record proves.
- **Fund prices were looked at before the measurement code existed.** The integrity evidence, sent to
  the director for the halt ruling, shows one-day returns on the 45 flagged dates and around year-end
  distributions. It is data quality work and it is also exposure to the data.
- **The metadata files hold performance fields.** Yahoo's `info` for each fund carries a year-to-date
  return, a trailing three-month return, a 52-week change and Morningstar ratings. In November 2026
  the first three describe the 2026 holdout period. They were stored raw, not printed and not used. No
  discretionary membership choice followed them: rule (b) admitted all 15 candidates, and the only
  exclusion (CSAIX) was Yahoo returning no prices. The screener response carries the same three return
  fields for each of its 60 funds (§6, S3).

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
- net of the funds' own fees it earned **+1.89 %/yr over cash**, at 7.9% volatility: a Sharpe ratio of
  0.24, **CI [−0.29, +0.73]** (21-day block bootstrap, `MetricsEngine`; [−0.38, +0.71] with 252-day
  blocks). The interval includes zero: on this window the composite's own premium over cash is not
  distinguishable from nothing;
- gross of those fees, which is what the stacked fund's 1.00% replaces, +3.21 %/yr;
- its daily correlation with equity over the whole window is +0.07.

**AQMIX's expense ratio.** Yahoo reports 3.09%. The pre-declared cap would have used 2.00%. The
director ruled, before any return existed, that the decision cell uses the fund's net ratio, and 1.25%
"from memory, unverified" if it could not be read from sec.gov. It could not: the permission layer
refused the read before any request was sent. The correction is against the arm. Its size is in §6
(S7): 0.083 %/yr.

## 3. Evaluability gates and validations

All four gates pass; H1 is evaluable.

| gate | value | bar | |
|---|---|---|---|
| E1 depth of W-L3 | 15.33 years | ≥ 12 | pass |
| E2 composite (without DBMF) vs DBMF, monthly correlation, 79 months | 0.867 | ≥ 0.50 | pass |
| E3 integrity | 45 flags, all ruled (amendment 3) | none unruled | pass |
| E4 md5 of every input | match | match | pass |

Reported validations. Lines that use an anchor fund are **marked with that anchor's integrity flags,
which are listed and were never ruled** (A1.1-12):
- **V1, the synthetic stack against live RSST** (2023-10-02 → 2025-12-31, 565 days). Live minus
  synthetic: **−0.4 %/yr, CI [−7.6, +6.1]**; tracking error 9.2%; daily correlation 0.94. The
  construction is not contradicted. On 2.25 years it cannot be confirmed either, which is why this was
  never a gate. B-5's AQR-based synthetic missed the same fund by −2.9 %/yr.
  **Marked: RSST carries 15 unruled flags.**
- **V2.** Each ETF against the composite without it: DBMF correlation 0.87 (+2.4 %/yr above the
  composite), KMLM 0.78 (−2.4 %/yr), CTA 0.61 (+7.0 %/yr on 45 months). Shape only, for the two live
  equity-plus-trend funds: BLNDX 0.78, MAFIX 0.86.
  **Marked: BLNDX carries 2 unruled flags and its equity proxy VT 82; MAFIX carries 5 and its equity
  proxy SPY 101.**
- **V3.** The composite against AQR TSMOM, monthly, on W-L3: 0.71.

Why the anchors carry so many flags: the D1 check asks whether the *trend candidates* had a quiet day.
A fund that holds equity falls 3% on an ordinary bad day for stocks while the trend funds do not, so
the check fires. That makes most of these flags uninformative, not cleared. None was examined. The reason holds for
SPY, VT, MAFIX and BLNDX (77 of their 81 D1 flags fall on days SPY fell at least 2 %), less well for
RSST, the V1 anchor (3 of its 13); V1 decides nothing.

## 4. The arms

Δ is Δ log wealth per year against 1× equity. Brackets are the primary 95% CI; "auto" is the
project-standard block and "252" is 252-day blocks (neither decides). ΔMDD is arm minus benchmark;
negative means deeper. Sortino carries its ci_low. Each IR carries its 95% interval from the same
21-day block bootstrap (`MetricsEngine`).

### W-L3 — 2010-09-01 → 2025-12-31 (15.33 yr; the decision window)

| arm | Δ %/yr [95% CI] | auto / 252 CI | CAGR | ×wealth | vol | MaxDD (trough) | ΔMDD | Sortino [ci_low] | IR [95% CI] (line: 0.76; pre-T-391 0.55) |
|---|---|---|---|---|---|---|---|---|---|
| benchmark 1× equity | — | — | 14.92% | ×8.44 | 17.1% | −33.7% (2020-03) | — | 1.105 [0.496] | — |
| **+100% — DECISION** | **+0.37 [−3.89, +4.17]** | [−3.65, +4.10] / [−4.49, +4.04] | 15.35% | ×8.93 | 19.3% | −34.3% (2020-03) | −0.6 | 1.051 [0.418] | 0.05 [−0.48, +0.55] |
| +50% | +0.26 [−1.86, +2.16] | [−1.75, +2.12] / [−2.18, +2.11] | 15.22% | ×8.79 | 17.8% | −34.0% | −0.3 | 1.101 [0.484] | 0.07 [−0.46, +0.57] |
| +25% | +0.15 [−0.91, +1.10] | [−0.85, +1.08] / [−1.07, +1.08] | 15.09% | ×8.64 | 17.3% | −33.9% | −0.1 | 1.110 [0.496] | 0.08 [−0.45, +0.58] |

No arm is shallower than equity in the window's deepest drawdown. The overlay raises volatility by 2.3
points at +100% and lowers the Sortino ratio.

### W-L1 — 2007-03-01 → 2025-12-31 (18.84 yr; one fund until 2010; reported)

| arm | Δ %/yr [95% CI] | 252 CI | CAGR | MaxDD (trough) | ΔMDD | IR [95% CI] (line: 0.68; pre-T-391 0.50) |
|---|---|---|---|---|---|---|
| benchmark | — | — | 10.68% | −55.3% (2009-03) | — | — |
| +100% | +0.20 [−3.69, +4.10] | [−3.46, +4.06] | 10.90% | −50.4% | +4.9 | 0.02 [−0.44, +0.49] |
| +50% | +0.18 [−1.76, +2.13] | [−1.66, +2.13] | 10.88% | −51.9% | +3.3 | 0.04 [−0.42, +0.51] |
| +25% | +0.11 [−0.86, +1.08] | [−0.81, +1.09] | 10.81% | −53.4% | +1.8 | 0.05 [−0.41, +0.52] |

Adding 2007–2010 changes nothing in the wealth answer. It makes the 2008–2009 drawdown 4.9 points
shallower, on the evidence of a single fund.

### The break-even spread curve (characterization)

| arm | Δ at s = 0 | point crosses zero at | ci_low at s = 0 |
|---|---|---|---|
| +100% | +0.88 %/yr | 87 bp | −3.38 %/yr |
| +50% | +0.52 | 102 bp | −1.60 |
| +25% | +0.28 | 110 bp | −0.78 |

Financing does not decide it: `ci_low` is below zero with a free spread. The lower bound would reach
zero only if the trend leg had earned about **3.9 %/yr more** than it did.

## 5. What a won't-sell investor would have sat through

Two frames, kept apart. The first table is the pre-registered set (§8.4): every row is a change in
relative wealth over a stated span, or a distance **below the arm's own earlier relative high**. None
of its rows says where the holder stood against SPY since the start.

| pre-registered (§8.4): spans and below-own-high | +100% | +50% | +25% |
|---|---|---|---|
| Worst 3-year change in relative wealth | **−25.1%** (2022-06-15 → 2025-06-20) | −13.2% | −6.8% |
| Longest stretch below its own earlier relative high | **6.9 years** (2015-04-14 → 2022-03-24) | 6.9 years | 6.9 years |
| Deepest point below its own earlier relative high | −26.3% (2025-05-14) | −14.0% | −7.2% |
| Still below its own high at the end of 2025? | yes | yes | yes |
| Change over 2011–2019, the flat decade | **−10.2%** (−1.19 %/yr) | −4.7% | −2.2% |
| Change over calendar 2022 | **+17.1%** | +8.4% | +4.2% |
| Change over 2020–2025 | +9.9% (+1.58 %/yr) | +5.4% | +2.8% |

The second table is the **since-start frame**: the holder's wealth against SPY's from 2010-09-01. It
was added in review round 1 and is a post-hoc description (`probes`), computed from the same series.

| since the 2010-09-01 start | +100% | +50% | +25% |
|---|---|---|---|
| Share of days behind SPY | 39% | 33% | 31% |
| Furthest behind | −8.8% (2013-10-09) | −4.3% | −2.1% |
| Longest unbroken stretch behind | 2.6 years (2012-01-19 → 2014-09-03) | 1.3 years | 1.3 years |
| At the April 2015 relative high (2015-04-13) | +17.8% | +8.9% | +4.4% |
| At the end of 2019 | **−3.7%** | −1.2% | −0.45% |
| Furthest ahead | +32.7% (2022-10-20) | +16.3% | +8.1% |
| On 2025-05-14 (the deepest point below its own high) | −2.3% | +0.0% | +0.3% |
| On 2025-06-20 (the end of the worst three years) | −2.0% | +0.1% | +0.4% |
| At the end of 2025 | **+5.9%** | +4.1% | +2.3% |

Year-end standing of the +100% arm since the start, in %: 2010 +7.3, 2011 +0.3, 2012 −5.9, 2013 −3.2,
2014 +7.9, 2015 +7.8, 2016 +2.3, 2017 +3.4, 2018 −5.1, 2019 −3.7, 2020 −0.9, 2021 +3.3, 2022 +20.9,
2023 +11.6, 2024 +8.0, 2025 +5.9.

- **Read together:** during the 6.9 years below its April 2015 high, the +100% holder was behind SPY
  since the start on 42% of days and ahead on 58%.
- **"10% behind by the end of 2019" is a January 2011 starter.** The holder from September 2010 was
  3.7% behind, because the last four months of 2010 added 7.3%.
- The drought cost less per year than predicted (1.2 %/yr against an expected 1.5–3).
- **The worst three years are the most recent three.** Between mid-2022 and mid-2025 the overlay gave
  back everything 2022 had paid and more: from 30.9% ahead since the start to 2.0% behind.

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
- **That interval's exclusion of zero rests on two episodes** (a post-hoc leave-one-out probe). Without
  2015–16 it is −0.10 [−0.29, +0.03]; without 2022 it is −0.05 [−0.25, +0.09]. Leaving out any one of
  the other five keeps the interval below zero. The honest reading is "about zero to mildly negative,
  on the strength of the two slow falls".
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
| **Decision cell** (AQMIX's ER 1.25%, from memory, unverified) | 2010-09 → | 3–14 | **+0.37 [−3.89, +4.17]** | [−4.49, +4.04] |
| S5 no survivorship haircut | same | 3–14 | +1.37 [−2.89, +5.17] | [−3.49, +5.04] |
| S6 survivorship haircut 2.0 %/yr | same | 3–14 | −0.62 [−4.89, +3.17] | [−5.49, +3.04] |
| S4 no ER gross-up (double fee) | same | 3–14 | −0.94 [−5.20, +2.86] | [−5.80, +2.73] |
| S7 AQMIX's ER as written (Yahoo's 3.09%, capped at 2.00%) | same | 3–14 | +0.46 [−3.81, +4.26] | [−4.41, +4.12] |
| Spread zero instead of 50 bp | same | 3–14 | +0.88 [−3.38, +4.68] | [−3.98, +4.54] |
| S3 screener: 4 more fund families — **unruled data; decides nothing** | same | 4–18 | +0.42 [−3.67, +4.05] | [−4.36, +4.00] |
| S1 pure-play (without the four flagged funds) | 2012-03 → | 3–10 | +1.28 [−3.31, +5.70] | [−3.06, +6.50] |
| … decision composite on S1's window | 2012-03 → | 6–14 | +0.50 [−3.73, +4.47] | — |
| S2 ETFs only | 2019-06 → | 3–5 | +1.66 [−4.60, +8.15] | [−4.35, +7.85] |
| … decision composite on S2's window | 2019-06 → | 12–14 | +1.58 [−5.36, +8.33] | — |

- **No sensitivity clears.** Every interval straddles zero by a wide margin. Every sensitivity's IR
  interval also straddles zero; the widest reach is S2's, [−0.52, +0.97] on 6.6 years.
- **The sign of the point estimate depends on two numbers nobody has measured.** It is positive at a
  survivorship haircut of 1.0 %/yr and negative at 2.0. It is negative if the stacked fund cannot
  deliver its trend program for less than these funds charged.
- **The four flagged-strategy funds pull the composite down by about 0.8 %/yr** on a common window.
  That is the cost of including funds whose strategies drifted, and it is also what answers "what if
  their data is bad": without them the result is still not distinguishable from zero.

**S3 in full, because it was not run as written and its data was never ruled.**
- **As written (§4.4):** the composite of *every* fund the category screen returns, oldest share class
  per fund, rules (c) to (e) applied.
- **As run:** the 14 decision members under their pre-registered tickers, plus one share class of each
  fund family the screen returned that the decision composite did not already hold. That added four:
  Arrow Managed Futures (MFTTX), Grant Park Multi Alternative (GPAIX), LoCorr Long/Short Commodity
  (LCSCX) and LoCorr Macro (LFMIX). Rule (e), which removes stacked funds, was **not coded**; none of
  the four was checked against it. The screen covers mutual funds only, so it could not add an ETF.
- **When the selection rule was fixed.** The screener response was on disk at 00:43:58 and its symbols,
  names and first-trade dates had been printed. The rule (oldest class; ties by lowest fee, then
  symbol) was committed at 00:46:47. The S3 prices were fetched at 00:47:02. So the rule preceded the
  prices by seconds and followed the response by three minutes. The response also carries each fund's
  year-to-date, three-month and 52-week returns; they were not printed or used, and the rule does not
  read them.
- **Its integrity flags were listed and never ruled: 41 in all.** MFTTX 34, LCSCX 3, LFMIX 3, GPAIX 1.
- **What it supports, and no more:** on unruled data, adding the four families moves the point by
  0.05 %/yr. That is weak evidence that the from-memory candidate list was not flattering. It is not a
  finding, and it decides nothing.

## 7. The frictionless factor on the same window, and the over-capture

| | window | Δ %/yr [95% CI as frozen] | automatic / 12-month block CI |
|---|---|---|---|
| AQR, +50% (B-5, quoted) | 1985–2025 | +5.11 [+3.25, +6.95] | [+3.29, +6.87] / [+3.13, +6.96] (B-5) |
| AQR, +50% (B-5, quoted) | 2000–2025 | +3.47 [+0.99, +5.99] | [+1.06, +5.80] / [+1.12, +5.72] (B-5) |
| **AQR, +50%, this study** | **2010-09 → 2025-12** | **+1.40 [−1.91, +4.50]** | **[−1.59, +4.38] / [−1.74, +4.20]** |
| AQR, +100%, this study | 2010-09 → 2025-12 | +2.40 [−4.24, +8.60] | [−3.62, +8.34] / [−3.82, +7.91] |
| Live composite, +50% (with the haircut; daily) | 2010-09 → 2025-12 | +0.26 [−1.86, +2.16] | 252-day [−2.18, +2.11] |
| DBMF live, +50% (B-5, quoted) | 2019-06 → 2025-12 | +2.58 [−1.70, +7.04] | [−2.76, +7.07] / [−2.57, +6.14] (B-5) |

**Which interval to read on the monthly rows.** The frozen primary for monthly series is a 1-month
block. On monthly data that is iid resampling, which the project standard does not accept. It is
printed because it is what was frozen. **A reader should use the automatic-block column** (6 months
for this study's 184 months; 5 to 8 months in B-5's rows). The
AQR arm's IR on this window is 0.22, CI [−0.27, +0.65] at 6-month blocks (+50%), and 0.18,
[−0.30, +0.62] (+100%). B-5's quoted rows carry B-5's point IRs (0.81, 0.53, 0.46), which have no
interval on record and are not repeated here.

**The paper factor itself stopped clearing.** On the months an investor could actually have bought a
trend fund, AQR's own overlay is +1.40 %/yr with an interval through zero.

**On point estimates, most of the distance between B-5's +5.11 and the investable +0.26 is the era
rather than the fees. The intervals do not establish that.**
- The point estimates: same factor, same +50% arm, +5.11 on 1985–2025 and +1.40 on 2010–2025, a fall of
  3.7 %/yr. The live composite is a further 1.1 below: about 0.5 is the survivorship haircut and about
  0.55 the measured over-capture.
- What cuts against it, twice over. First, `h_L`'s interval is wide: its upper bound is 5.8 %/yr per
  100% of trend, which is 2.9 at +50% and of the same order as the 3.7 era gap. Second, `h_L` is
  measured on 2010–2025 only. It says nothing about what fees and trading costs would have taken
  before 2010, when the paper premium was earned and only one of these 14 funds (RYMFX, from 2007) existed
  (whether any 1 %-fee trend fund existed then is from memory, unverified). "Era" and "fees" are not
  separable on this evidence.
- **The factor's own mean by era — a post-hoc description; the eras were chosen after the fact**
  (`probes`; `MetricsEngine` block bootstrap, automatic block). 1985-01 → 2010-08 (308 months):
  **+16.6 %/yr over cash, CI [+12.7, +20.8]**. 2010-09 → 2025-12 (184 months): **+4.3 %/yr, CI
  [−1.8, +10.5]**. The gap is 12.3 %/yr with a naive standard error of 4.1 (independent months
  assumed). So the paper premium was larger before 2010 by more than sampling noise on that naive
  reading, and the later era's own mean is not distinguishable from zero.

**The measured over-capture.** `h_L` = AQR minus the composite gross of fund fees, on the 184 months of
W-L3:

| block | `h_L` %/yr | 95% CI |
|---|---|---|
| 1 month (the frozen primary; iid on monthly data) | **+1.10** | **[−4.17, +5.78]** |
| automatic (6 months) — the one to read | +1.10 | [−3.07, +5.10] |
| 12 months | +1.10 | [−3.67, +5.18] |

Tracking error between the two is 9.3 %/yr.

**The frozen seed gives an unusually low lower bound.** Across 50 bootstrap seeds at the 1-month block,
`h_L`'s lower bound ranges from −4.17 to −3.08 with a median of −3.53; seed 0, the frozen one, is the
lowest of the 50. The frozen seed is kept and quoted. No reading in the transport table below changes
at any of the 50 seeds or at either longer block.

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
| Arm MaxDD −30% to −42%; benchmark about −34%; not shallower in 2020 | −34.3%; −33.7% (ΔMaxDD −0.6); in the 2020 episode the arm's return was 0.5 points lower | hit |
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
   charges 1.00% once. Without the add-back the point is −0.94 %/yr (S4). From memory, and not checked
   against any prospectus: three members (EVOIX, ABYIX, LOTIX) carry manager fees inside swaps that are
   not in their reported ratios, which would work against the arm.
3. **AQMIX's expense ratio is unverified.** 1.25% from memory, against Yahoo's 3.09%. The effect is
   0.083 %/yr (S7).
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
    not recorded again here. That row cites the ledger line rather than the prereg file; the recorder
    has no update path, so the citation is left as it is. The MBL line is quoted at the gate in force
    (N_eff 372.28, which already includes this trial) and at the pre-T-391 pin (37.08). The measured IR
    is 0.047, CI [−0.48, +0.55]: the point is less than a tenth of either line.
11. **The sec.gov read did not happen.** The permission layer refused it. The owner can read AQMIX's
    net expense ratio from its summary prospectus in a minute; it would move the result by under
    0.1 %/yr.
12. **Exposure to the data before the measurement code was committed** is set out in §1 ("Order of
    events"). The ordering of commits is on record; that the code was not run early is the author's
    account.
13. **Interval choices.** The frozen bootstrap seed (0) gives `h_L` its lowest lower bound among 50
    seeds, and the frozen 1-month block on monthly series is iid resampling. Both are kept as frozen
    and the automatic-block intervals are printed beside them (§7). No reading changes.

## 10. What this means

**For the program.** The stacked trend overlay is **not supported on investable evidence**. Per the
pre-named outcome, the door is shut for deployment and the interval is the record: over 2010–2025 the
overlay was worth somewhere between −3.9 and +4.2 %/yr at +100%, and between −1.9 and +2.2 at +50%.

Three things are now on record that were not before:
- **B-5's +5.11 %/yr is not an estimate of what the overlay is worth today.** The same paper factor on
  2010–2025 gives +1.40 with an interval through zero. On point estimates the headline was earned
  mostly before 2010-09, when only one of these 14 funds existed: the factor's mean was +16.6 %/yr before 2010-09 and
  +4.3 after (a post-hoc description, §7).
- **On point estimates, fees and frictions in 2010–2025 are the smaller part.** The measured
  over-capture is +1.1 %/yr, not the 2.9 or 5.3 of the two short readings. Its interval still spans
  them, and it says nothing about what fees would have taken before 2010. The evidence does not
  separate "era" from "fees".
- **The question cannot be settled by more backtesting.** No free long net index exists: SG's needs a
  registration and BarclayHedge's history is behind a login. By the census's pre-data estimate (not a
  measurement), even a 26-year index would have had about a 4% chance of clearing as specified.

**For a Roth holder.** RSST, or half SPY and half RSST, is a legitimate thing to hold on a belief that
trend-following's long history continues. It is not something this program's evidence recommends. The
honest description: roughly SPY's return, two more points of volatility, deeper losses at the start of
most sell-offs, and one large payoff in a slow inflationary bear market. Against SPY since the start
the holder was behind on four days in ten, never by more than 9%. Against the best lead they had
already reached, they waited seven years (2015-04 → 2022-03) to regain the April 2015 lead once, and at
the end of 2025 they are 20% below the higher October 2022 lead (10.1% below the April 2015 one). 1× SPY remains
the honest default.

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

**The durable copy of the snapshot is outside the repository:**
`/Users/jacksonmurphy/Dev/_research_snapshots/t398_stacked_trend_overlay_2026-11-14/` (archived by the
director; `inputs/MANIFEST.json` md5 `ba344f0446527e36718c529ba7ec2acf`; its `run_A/results.json` is
the first verdict's file, md5 `d2e73967846574d724e13e4b6b2052aa`). **The worktree copy under
`data/t398_local/` is not durable**: it is gitignored and goes when the worktree is removed. The
metadata and prices were fetched once and cannot be fetched again to the same bytes.

```bash
# 1. restore the snapshot into the tree (inputs, rulings, and the S3 and screen files)
SNAP=/Users/jacksonmurphy/Dev/_research_snapshots/t398_stacked_trend_overlay_2026-11-14
mkdir -p data/t398_local
cp -R "$SNAP"/inputs "$SNAP"/inputs_s3 "$SNAP"/meta "$SNAP"/screen "$SNAP"/integrity_rulings.json data/t398_local/
md5 -q data/t398_local/inputs/MANIFEST.json                 # ba344f0446527e36718c529ba7ec2acf
# 2. every step below reads only that md5-verified snapshot; nothing is fetched
python scripts/t398_stacked_trend_overlay.py integrity     # lists the 45 flags; exit 0 with the rulings file
python scripts/t398_stacked_trend_overlay.py gates         # -> gates.json, bound to the manifest and the integrity file
python scripts/t398_stacked_trend_overlay.py smoke         # -> smoke.json (never quoted)
python scripts/t398_stacked_trend_overlay.py run --tag A   # -> data/t398_local/run_A/
python scripts/t398_stacked_trend_overlay.py run --tag B   # determinism twin
python scripts/t398_stacked_trend_overlay.py determinism   # exit 2 unless A and B match file for file
python scripts/t398_stacked_trend_overlay.py probes        # the post-hoc descriptions (since-start frame, by year, ...)
python scripts/t398_independent_recompute.py               # separate code; exit 2 unless it agrees to 1e-9
python -m pytest tests/test_t398_stacked_trend_overlay.py -q
```

The three return CSVs must come out with the md5s in §1. `results.json` embeds the honest-N gate as
read on the day, so its md5 moves whenever the trials record does; compare the CSVs, not that file.

---

## Review round 1 (2026-11-14) — what changed, and why

An independent reviewer executed the branch at `04063c2` and reported **NOT READY: the measurement
stands; the write-up, the tests and a merge conflict do not.** Every cell the reviewer recomputed from
their own implementation matched (the decision cell to 1e-16 per bar). Nothing below is a new trial,
and the frozen prereg (lines 1–567) is byte-identical.

### Sentences changed (was → now → why)

| # | was | now | why |
|---|---|---|---|
| 1 | "you would have spent seven years behind SPY (2015 to 2022), been paid back in a single year (2022), and then fallen 25% behind again by mid-2025" (§0) | "In April 2015 you were 17.8% ahead of SPY; it took 6.9 years, to March 2022, to regain that lead. During those years you were still ahead of SPY since the start on 58% of days, and behind at the ends of 2018, 2019 and 2020. Calendar 2022 took the lead to 32.7%. By May 2025 all of it was gone: you were 2.3% behind SPY since the start, which is 26% below that high." | **False as worded.** It stated the below-own-high frame as if it were since-start. |
| 2 | "cost 1.2 %/yr for nine years: 10% behind SPY by the end of 2019" (§0 table) | "A holder who started in January 2011 was 10.2% behind SPY at the end of 2019; the holder from the 2010-09 start was 3.7% behind" | The 10% is a January 2011 starter. |
| 3 | "25% behind SPY over 2022-06 → 2025-06; still behind its earlier peak at the end of 2025" (§0 table) | "relative wealth fell 25.1% between 2022-06-14 and 2025-06-20: from 30.9% ahead of SPY since the start to 2.0% behind. At the end of 2025 the holder was 5.9% ahead since the start and 20% below their own high" | Same error: a fall, stated as a standing. |
| 4 | "and stretches of seven years behind" (§10) | "Against SPY since the start the holder was behind on four days in ten, never by more than 9%. Against the best lead they had already reached, they waited seven years to get it back once and are 20% below it now." | Same error. |
| 5 | §5 had one table mixing the frames | Two tables: the pre-registered spans and below-own-high rows, and a since-start table with year-end standings | So neither frame can be read as the other. |
| 6 | "Calendar 2022 alone contributed +15.8. … The sign of the point estimate rests on one year and one quarter." (§0) | "any single large year moves the sign … Removing any one of 2022 (+15.8), 2014 (+10.9) or September–December 2010 (+7.0) turns the total negative. Removing any one of 2018, 2023, 2011 or 2012 more than doubles it." | Right arithmetic, one-sided. 2014 also exceeds the total. |
| 7 | "a Sharpe of 0.24" (§2) | "a Sharpe ratio of 0.24, CI [−0.29, +0.73]" | `[NN-SHARPE-CI]`: a bare point. |
| 8 | "The active information ratio is 0.05" and every IR in the tables | each IR with its interval; the decision cell's is 0.05 [−0.48, +0.55] | Same rule. B-5's quoted point IRs were removed from §7. |
| 9 | "Most of the distance … is the era, not the fees: the paper premium was far larger before 2010." (§7) and "Fees and frictions are not the main story." (§10) | "On point estimates … The intervals do not establish that", with the factor's era means and their intervals, and "The evidence does not separate 'era' from 'fees'" | An inference from three point estimates. |
| 10 | "0.09 %/yr" for the AQMIX correction (§2, caveat 3) | "0.083 %/yr" | The number was rounded up. |
| 11 | The decision cell stated without AQMIX's label (§0, frontmatter, §6 row) | "AQMIX's is 1.25%, from memory and unverified" at each | The label was missing where the cell is stated. |
| 12 | "The candidate list was not flattering." (§6) | "on unruled data … weak evidence … It is not a finding, and it decides nothing", with S3 as written against S3 as run, when its rule was fixed, and its 41 unruled flags by fund | S3 was not run as written and its data was never ruled. |
| 13 | V1 and V2 lines without marks (§3) | each marked with its anchor's unruled flag count | A1.1-12 requires the mark. |
| 14 | the pooled drawdown correlation's interval stated alone (§5) | plus the leave-one-out: zero is excluded only with both 2015–16 and 2022 in | The exclusion rests on two episodes. |
| 15 | "about 3.8 %/yr more" (§4) | "about 3.9 %/yr more" | Arithmetic: the lower bound is −3.89. |
| 16 | "deeper by 0.5" (§8) | "ΔMaxDD −0.6; in the 2020 episode the arm's return was 0.5 points lower" | 0.5 was the episode return, not the drawdown gap. |
| 17 | "would have had about a 4% chance" (§10) | "By the census's pre-data estimate (not a measurement) …" | Unlabelled estimate. |
| 18 | "Three members carry manager fees inside swaps" (caveat 2) | "From memory, and not checked against any prospectus: three members (EVOIX, ABYIX, LOTIX) …" | Unlabelled memory. |
| 19 | "A separate script … reproduced …" (§1) | the script is committed: `scripts/t398_independent_recompute.py` | The claim had no artifact. |
| 20 | "halts if a window date exceeds it" (§1) | "pinned files with 2026 rows are cut, not refused" and how that is narrower than §18 | A fail-closed gap, now stated. |
| 21 | one md5 for `results.json` | three, with what each embeds; the CSVs unchanged | The file embeds the live gate reading. |
| 22 | "MBL … 0.55 (pinned gate) and 0.76 (N ≈ 372)" | "0.76 at the gate in force (N_eff 372.28) and 0.55 at the pre-T-391 pin" | T-391 merged; the gate reads 372.28. |
| 23 | the Reproduce block pointed at `data/t398_local/` | it points at the archived snapshot and says the worktree copy is not durable | The inputs cannot be re-fetched. |
| 24 | no account of ordering | §1 "Order of events": what commit and file times show, what they cannot, the three network steps run from uncommitted code, and the performance fields in the stored metadata | Disclosure. |
| 25 | `h_L`'s interval at the frozen seed and block only | plus the seed spread (seed 0 is the lowest of 50) and "read the automatic block" on monthly rows | Disclosure; nothing frozen changed. |

### Code and tests

- **`run` no longer trusts `gates.json` and `integrity.json` by existence.** Each records the md5 of the
  manifest it was computed against (the integrity file also its rulings; the gates also the integrity
  file). A mismatch halts.
- **`determinism`** implements prereg §18's halt: it compares runs A and B file for file and exits 2 on
  any mismatch or missing file.
- **`probes`** writes the post-hoc descriptions used above. They are labelled post-hoc in the code and
  in the file, and they decide nothing.
- **Labels.** `PREREG_REF` names amendment 3. The T-391 comment says it is merged. The decision-cell
  string in `results.json` says AQMIX's ratio is from memory, unverified.
- **Tests: 28 → 42.** The new ones drive `Panel.excess`, `Panel.composite` and `Panel.window`
  on a synthetic snapshot instead of restating the formula in the test body.

**Reversion proof.** Each line below was changed alone, the T-398 test module was run, and the file was
restored. Before round 1 the first seven all left 28 tests passing.

| # | single-line reversion | result | failing test |
|---|---|---|---|
| 1 | cash not subtracted in `Panel.excess` | **caught** | `test_panel_excess_is_the_funds_return_minus_cash_plus_its_own_fee` (+1) |
| 2 | the fund's fee added twice | **caught** | the same two |
| 3 | composite = sum, not mean | **caught** | `test_panel_composite_is_the_equal_weight_mean_and_counts_members` |
| 4 | the fewer-than-three-members halt removed | **caught** | `test_window_halts_when_the_composite_drops_below_three_members` |
| 5 | `run`'s unruled-flag refusal removed | **caught** | `test_run_refuses_an_unruled_flag_and_stale_gate_files` |
| 6 | `verify_snapshot` skips the md5 comparison | **caught** | `test_verify_snapshot_passes_a_clean_snapshot_and_halts_on_any_changed_byte` |
| 7 | `_corr`'s guard changed to a bare `== 0` | **caught** | `test_fp_guard_uses_tolerance_on_a_tiny_but_nonzero_std` (the `_corr` input's std ≈ 4.2e-17; the `_ann_ratio` input's ≈ 1.8e-18; both non-zero, below 1e-12) |
| 8 | `run` no longer checks the file bindings | **caught** | `test_run_refuses_an_unruled_flag_and_stale_gate_files` |
| 9 | the determinism comparison always says "identical" | **caught** | `test_determinism_command_exits_nonzero_on_a_mismatch_or_a_missing_run` |
| 10 | `_ann_ratio`'s guard changed to a bare `== 0` | **caught** | `test_fp_guard_uses_tolerance_on_a_tiny_but_nonzero_std` |
| 11 | a stale integrity file accepted | **caught** | `test_bindings_pass_when_consistent_and_halt_on_each_stale_file` |
| 12 | stale gates accepted after the integrity file changed | **caught** | the same |
| 13 | the substrate md5 check removed | **caught** | `test_verify_snapshot_halts_on_a_changed_substrate` |

### Left as it is, and said so

- **The trials row.** `config/honest_n_trials.json` records T-398 at +1 and cites the ledger line. The
  recorder has no update path, so the citation is not repointed to the prereg file. No row was added.
- **The frozen seed and the 1-month block** are kept; the alternatives are printed beside them.
- **S3** is reported as run, with the difference from §4.4 stated. It was not re-run as written: that
  would mean fetching more unruled funds for a number that decides nothing.
- **The 41 S3 flags and the anchors' flags** remain unruled.


## Review round 2 (2026-11-17) — text only, applied by the director

The delta review at `edca72b` found the code, tests, numbers, gates and merge ready and three sentences false as worded. Fixed in place, no number changed, no re-run: (A) the independent-recompute script takes the financing base from the harness (`h.financing_base()`), so the claim it shares no measurement code was false — now stated with its consequence; (B) "before trend funds existed for retail investors" was contradicted by RYMFX (2007) — now "mostly before 2010-09, when only one of these 14 funds existed", and "no 1%-fee fund existed" labelled from memory; (C) "No number in the first file changed" → "No measured number". Notes applied: the pre-T-391 keys in `results.json` named (D); the two dates of the worst three years reconciled (E); the "it" in the closing paragraph split into the 2015 and 2022 leads (F); the uncommitted-network-step claim labelled the author's account (G); both FP-guard stds and the RSST anchor-flag exception stated (H). The prereg's in-place label edit (I) is left as disclosed.
