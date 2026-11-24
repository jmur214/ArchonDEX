---
task_id: T-414
candidate: O-1 (T-410 census, §5 and §7.2)
title: A defined-risk index option premium (Cboe CNDR) stacked on a 100 % equity core vs the core alone, after section 1256 tax, 1986-06 → 2026-09
date: 2026-11-20
status: CLOSED UNRUN 2026-11-24 (director's ruling after review). 0 trials. Never frozen, never run.
original status (superseded): DRAFT pre-registration. Phase 1 only. NOT FROZEN; `run` refuses (`FROZEN = False`). Nothing measured beyond the 12-roll smoke window.
proposed trials (superseded; 0 consumed): +1 (the decision cell). Not recorded; the director records it at the freeze.
lens: edge-analyst (docs/Core/roles.md)
code: NOT ON MAIN. scripts/t414_o1_stacked_premium.py and tests/test_t414_o1_stacked_premium.py exist only on branch worktree-agent-a4a994237e4b0208e, tip b66b5a2 (code commit 051b2f0)
owner approval: 2026-11-20 ("we want to test and exhaust as many ideas as we can")
---

# T-414 (O-1): selling a small, capped-risk index condor on top of the stock you hold

## Closure notice (2026-11-24)

**CLOSED UNRUN at 0 trials.** The reviewer reproduced the engine to 1e-15 and returned NOT READY, CLOSE UNRUN. The director ruled the same day:
- The public CNDR endpoint (100 → 801.65) pins the sample mean. The result would be a near-certain FAIL that carries no information: conditional pass probability about 0.1 % at c_high and ≤ 1 % at c_low; even at zero cost it needs σ_x below 4.1–4.7 %.
- The trade is untradeable at the owner's size.
- The falsifier claimed more than the test could show.

**Nothing was measured, so nothing is refuted.** Closing is a decision not to spend a trial on a test whose answer the public endpoint already fixes. The scope of that decision is in the §8 correction.

**The look at the endpoint is recorded as outcome-adjacent: any later CNDR or BFLY variant carries +1 for it** (director). The full list of levels displayed is longer than §2 said; see the §2 correction. **Extended by the director's second ruling (2026-11-24): the +1 covers all four series displayed (CNDR, BFLY, PUT and WPUT), for any later variant that uses any of them.**

**How to read this file.** Every original sentence from §0 on is unchanged. Corrections are the blockquotes marked "CORRECTED 2026-11-24". Only the front matter was edited (the original status is kept there) and the closure notice, §15 and §16 were added. The untouched original is `git show b66b5a2:docs/Sources/prereg_o1_stacked_index_premium_t414_DRAFT_2026-11-20.md`.

**Where the code is.** On branch `worktree-agent-a4a994237e4b0208e`, tip `b66b5a2`, not merged. Do not run it and do not fix it. The commands in §13 and the pre-freeze steps in §11 are moot.

## 0. The answer first

**This test can be run honestly, but at your size the trade does not exist as specified, and the test will very probably fail.** Running it costs one trial and about an hour. Its value is closure: a failure closes premium-selling for you in every form.

1. **At about $45k the overlay cannot be held as designed.** The design is a condor whose worst month costs at most 10 % of the account (k = 0.10). One XSP condor at today's index level needs about $3,800–9,000 of margin, depending on volatility (the 10th–90th percentiles since 1990).
   - Never exceeding the 10 % cap leaves the account holding **zero condors in about three months out of four**: 73 %, with a range of 59–91 % depending on the width model. The empty months are the higher-volatility ones, where the premium is richest.
   - Rounding to the nearest contract instead gives one condor whose size swings between about 0 and 1.7 times the target.
   - At $20k it is never possible. The trade becomes holdable at about $100k (1–2 condors, still lumpy) and clean at about $250k (4–5 condors). This holds before the robo question. Options cannot be held inside Schwab's robo [R], so the trade also needs a self-directed margin account with spreads approval [UNVERIFIED].

   > **CORRECTED 2026-11-24 (R3).** The 73 % rests on κ = 1.6, which is too high for a model written on VIX; the reviewer measured κ = 1.29–1.33. The share of rolls with zero condors at $45k is **about 49.5 % (κ 1.3) to about 73 % (κ 1.6)**, and the median at κ 1.3 is 1 condor. "About three months out of four" and the "59–91 %" range are withdrawn. $20k stays at 100 % zero, and "holdable at about $100k, clean at about $250k" holds for κ 1.3–1.9. Wings scale with κ, so margin per condor is about $3.1k–7.3k at κ 1.3 rather than $3.8k–9.0k. See §9.
2. **The census's formula was off by a factor of ten, and the census itself didn't catch it.** The census wrote the overlay as `equity + 0.10 × (CNDR − bills − cost)`. CNDR already holds Treasury bills worth **ten times** the condor's widest wing (Cboe methodology v4.2, §2.1), so 0.10 × CNDR is a condor needing only about 1 % of the account. That is untradeable below roughly $380k–900k. The census's own worst-month (−10 %) and dollar lines describe a multiplier of **1.0** on CNDR's excess return. This prereg freezes m = 1.0.
3. **The chance of a pass is about 2 % (0.5–7 %), not the census's 10 %.**
   - CNDR's level is public, and both the census and I saw it: 100 in June 1986, 801.65 on 2026-11-19. That pins the gross premium at about **2.2 %/yr over bills**, before costs and tax.
   - The index's own design implies a volatility of about 5–8 %/yr.
   - The gating cost from today's quotes is about 1.2 %/yr. After costs, tax at the 60/40 rate, and the drag of a short-volatility position stacked on stock, the overlay's information ratio is about **0.07–0.24**.
   - The bar at 40.25 years is **0.47**.
   - Only lower measured costs or a much lower true volatility could change this (§7).

   > **CORRECTED 2026-11-24 (B1).** "About 2 % (0.5–7 %)" is mis-specified and withdrawn. It treated the sample mean as still random after the endpoint had fixed it. Conditional on the endpoint the pass probability is about **0.1 % at c_high and ≤ 1 % at c_low** (reviewer). See the §7 correction.
4. **Recommendation: freeze and run it once, as a closure estimate** (§11), after a short real-quote cost census if one is cheaply available. Or close it unrun with 0 trials if the director would rather not spend the trial. In either case it does not change your year: at $45k a real effect would be worth about $0–300 a year.

   > **CORRECTED 2026-11-24 (B1, B2).** The recommendation to run was wrong: the run would have told us nothing the endpoint does not. The sentence at the top of this section, "a failure closes premium-selling for you in every form", is also withdrawn (§8).

## 1. Question and hypothesis

**Question.** Does a defined-risk short-index-volatility overlay raise after-tax terminal wealth when it is stacked on a 100 % equity core, so that no stock is sold to fund it? The overlay is CNDR, a monthly 20-delta/5-delta SPX iron condor.

**H1 (the decision).** Over 1986-06-20 → 2026-09-18 (483 monthly roll periods, 40.25 years), measure D = log(W_stack / W_equity) after section 1256 tax at the gating cost.
- Its moving-block-bootstrap 95 % interval must have **ci_low > 0**.
- Its bootstrap t = D / se must be **≥ 2.96**, the expected maximum of N_eff ≈ 372–373 null t-statistics (T-391; `[NN-MBL]`).

**Necessary conditions** (all must hold for a pass):
- **N1 (decay, from the census):** the point D over roll periods starting on or after 2010-01-15 is > 0. That is 200 periods.
- **N2 (backfill, new here):** the point D over roll periods starting on or after 2015-08-21, the first roll after CNDR's launch on 2015-08-03, is > 0. That is 133 periods. Before the launch, CNDR is a backtest that Cboe computed in hindsight (methodology disclaimer). Only the post-launch years are a live calculation.
- **N3 (the owner's loss bound):** the stack is ≥ 0.5 × the equity core over every rolling 10-year and 20-year cohort on the historical path.

**Class.** A priced premium on a long free history (the fresh-eyes audit's class 2). It is not a mined signal. There is no conditioner.

## 2. What was seen before this was written (disclosure)

- **Seen in the data census:** CNDR's first and last levels (100.00 on 1986-06-20; 801.65 on 2026-11-19). The T-410 census also saw the last row.
- **Computed in the census (§4.2):** the bill leg's full-window mean, 2.99 %/yr. This is outcome-free on its own. Together with the endpoint it implies a gross CNDR excess of about 2.16 %/yr (log), pre-cost and pre-tax. The pass arithmetic in §7 conditions on that public number, and the result says so.
- **Not seen or computed:** CNDR's variance, its correlation with equity, any crash month, any subwindow (2010+, post-launch), and any after-cost or after-tax number.
- **The smoke** (§10) ran the full pipeline on the first 12 rolls. Only the output structure and the gate booleans were inspected; all booleans were False by construction, because a 12-roll window cannot reach N1–N3.
- **Design choices made here that differ from the census:** m = 1.0 (forced by the methodology, §0.2); N2 (added for the backfill); the bill rule (CNDR's own, §4.2); a symmetric cost-freeze rule (§5.3); and one data hole (§4.4). None was tuned on an outcome.

> **CORRECTED 2026-11-24 (author; not from the review).** This disclosure was incomplete in four ways.
> - **More levels were displayed than the two CNDR endpoints.** The span check printed the first two and last two rows of CNDR, BFLY, PUT and WPUT, so the endpoints of **all four** option indices were seen, and CNDR's and BFLY's one-day move into 2026-11-19 was visible. Checking the 2020-10-16 hole printed **CNDR's levels for 2020-10-13, -14, -15 and -19**, which are inside the test window. A level inside the window plus the endpoint gives a subwindow return, so "not seen … any subwindow" was false. I computed no return from any of them.
> - The director's +1 covers CNDR and BFLY. PUT's and WPUT's endpoints were seen too; whether the +1 extends to them is the director's call. **Ruled 2026-11-24: it does, for all four series.**
> - **"All booleans were False by construction" was wrong for H1.** N1–N3 cannot be evaluated on 12 rolls, but H1 was evaluated on the smoke window and its False was displayed.
> - **Two departures from the census were not listed here.** The census prescribed a cash buffer equal to the worst overlay month, charged as a drag; this DRAFT demoted it to a sensitivity (§3.4 correction). The census named the T-306 equity and cash series; this DRAFT used French and H.15 (explained in §4.2, not listed here).

> **CORRECTED 2026-11-24 (review, R1).** A third unlisted departure: the census (§7.2) and `[NN-SHARPE-CI]` name the Politis–White block length; this DRAFT fixed a block of 12 rolls (§6) without listing it here or in §11's rulings.

## 3. Construction

### 3.1 The instrument (Cboe CNDR methodology v4.2, last revised 2026-11-13, read today)

| Feature | What the methodology says |
|---|---|
| Positions | Short a 1-month 20-delta SPX put and call; long 5-delta wings. "All option positions are one unit." |
| Collateral | A 1-month T-bill account set to **ten times the widest wing**, so the worst settlement loss is "approximately 10 % of the total value of the account" |
| Roll | The third Friday, or the preceding business day if that is a holiday. Old options settle against the SOQ, AM-settled. New strikes are chosen before 11:00 ET with Black deltas |
| Fill | "The average of the last bid-ask quote … before 11:00 a.m. ET". So the index trades at **mid**, gross of any spread |
| Total return | "The dollar value of option premium … functionally reinvested" |
| Bill accrual | M_t = M_{t−1} · (1 / (1 − 28/360 · USB4WTA))^{(t − (t−1))/28}, calendar days, the 4-week bank-discount rate; "interest is not accumulated … on the roll day" |
| History | Base date 1986-06-20; **launch date 2015-08-03**. Earlier values are a backtest in hindsight (the disclaimer) |

BFLY (iron butterfly: ATM straddle with 5 % OTM wings) uses the same ten-times collateral rule and the same dates (base 1986-06-20, launch 2015-08-03). PUT (ATM monthly put, fully collateralized, filled at the VWAP from 11:30 to 12:00) has base date 1988-06-01 and launch date 2007-06-20. WPUT (weekly ATM put) has base date 2006-01-31 and launch date 2015-08-03.

### 3.2 The overlay's return

Per roll period i (from the close of roll i−1 to the close of roll i):

    x_i = CNDR_i / CNDR_{i−1} − 1 − MV · b_i

- b_i is CNDR's own bill accrual over the period (§4.2).
- MV = 1.02 is the bill account's share of NAV: 1 / (1 − credit/10W), with credit/W ≈ 0.09–0.12 from the design model and today's chain, so the true value is ≈ 1.009–1.012.
- Subtracting MV · b removes the bill interest **and** the interest on the credit. A retail account earns about nothing on that cash. The 1.02 slightly over-subtracts, by about 0.03 %/yr against the overlay (conservative).

### 3.3 The stack and the baseline

    W_i = W_{i−1} · (1 + rE_i) + m · W_{i−1} · (x_i − c) − 0.0002 · |overlay P&L|
    W^E_i = W^E_{i−1} · (1 + rE_i)

- rE is the equity core's total return over the same dates.
- c is the cost per roll in NAV units: c_req × 0.1015, where 0.1015 is the requirement per unit of CNDR NAV, W / (10W − credit).
- Taxes are settled at each year end (§3.5).
- Both arms start at 1.0.

### 3.4 Sizing, rebalancing, financing

- **Sizing: m = 1.0, frozen.** At m = 1 the account holds the condor count CNDR would hold if its bill account were replaced by the equity core. The margin requirement is about 10 % of equity (k = 0.10), and the worst roll loss is bounded near 9–10 % of equity on top of the equity's own move.
- **Rebalancing:** monthly, at the roll. The condor is re-sized on the stack's wealth at that roll and held to cash settlement. It is never closed early: XSP is European and cash-settled, so it carries no assignment risk (Cboe XSP page, read today).
- **Financing (F2, primary):**
  - Under Reg-T, the long stock's loan value carries the spread requirement with no debit [R]. At m = 1 the requirement is about 10 % of equity against a loan value of about 50 %, so there is no margin call even after a 50 % fall when re-sized monthly.
  - A settlement loss is paid by selling equity, and a settlement gain buys equity. That is what "stacked, 100 % invested" means. The sale is mechanical, not behavioural, but it is a sale in a crash month. **The owner must accept that in words before any real version.**
  - A 2 bp equity trading cost is charged on every transfer.
- **F1 (sensitivity):** a bill buffer of 10 % of the stack, the structural worst roll, held instead of equity. This is a displacement. The §1.4 rule of the census says it costs about 0.1 × the equity premium a year.
- **F3 (rejected):** carrying settlement losses as a margin debit. Schwab's small-balance margin rate is about 11–13 % [R]; T-409 found margin "dead".

> **CORRECTED 2026-11-24 (F1 omission).** The T-410 census required the worst-month cash buffer in the primary construction. Leaving it out of the decision cell **sets the sign**: the buffer costs about 0.5–0.8 %/yr (reviewer), while §7's own approximation gives an after-tax D of only about 0.4–0.8 %/yr at c_high before that charge. With the buffer charged, the planning D is about zero or negative.

### 3.5 Tax: section 1256

Verified today against IRS Form 6781 (2025) and its instructions on the form, and IRS Pub. 550 via T-410:
- XSP and SPX are nonequity (broad-based index) options. Gains and losses are **60 % long-term / 40 % short-term**, marked to market at year end; "The wash sale rules don't apply." Cboe's XSP page states the same section 1256 treatment.
- **Net-loss carryback (box D election):** individuals may carry a net section 1256 loss **back 3 years, earliest first**. It is allowed only against those years' section 1256 net gains and only to the extent it does not create an NOL. The amount eligible is the excess of losses over **(gains + $3,000)**; the first $3,000 stays in the loss year as an ordinary capital-loss deduction. Anything left is carried forward.

**The model.**
- **Primary (conservative and scale-free):**
  - Net gains are taxed at τ = 0.6 · 15 % + 0.4 · 24 % + 5 % state = **23.6 %**, the post-school default bracket from T-409.
  - Net losses are carried back 3 years (refunds at τ), then carried forward against later section 1256 gains.
  - There is no $3,000 ordinary offset in the primary (it would favour small accounts), and unused carryforward at the end is worth 0.
  - The whole roll period's P&L is assigned to the calendar year in which the roll ends. The December-to-January period is therefore not split at the 31 December mark, which shifts about two weeks of one period's P&L by one tax year.
  - Tax is paid at year end by selling equity, and refunds buy equity.
- **Sensitivities:** the school-year rate (0.4 · 12 % + 5 % = 9.8 %); a high bracket (0.6 · 20 % + 0.4 · 35 % + 5 % = 31 %); the $3,000 offset at the owner's $45k (3,000/45,000 of starting wealth at 29 %); and pre-tax.
- **Not modelled:**
  - dividend tax and the terminal liquidation tax on the equity core (both arms hold it; to first order the ratio is unaffected);
  - capital gains on the equity lots that F2 sells (highest basis first, labelled);
  - interaction with the robo's or the owner's other capital gains.
- **UNVERIFIED hazard, material:** a short S&P 500 index call spread held against an S&P 500 fund may be an offsetting position under section 1092 (straddles; the index-overlap rules for a stock portfolio against an index option). If it is, condor losses could be deferred and the mixed-straddle rules could change the 60/40 character. The model ignores this. **No real version proceeds until a tax adviser rules on it.**

> **CORRECTED 2026-11-24 (§1092; new).** This is more than a caveat: it can flip the sign of the result, so the modelled tax is a **best case**. An S&P index position against an S&P core fund is likely "related property" (reviewer's citation: 26 CFR 1.246-5(c)(1)(iii)(B) and (e)(2)(ii); I have not read the regulation). In the reviewer's synthetic case, with gains taxed each year and losing condors deferred, D is **−1.00 %/yr at σ 6 %**.
>
> Sizes from the review (R2), synthetic, c_high, after-tax D per year:
>
> | Tax treatment | σ 6 % | σ 4 % |
> |---|---|---|
> | As modelled (best case) | +0.52 % | not supplied |
> | Net-loss years deferred | +0.12 % | not supplied |
> | Each losing condor deferred | −1.00 % | −0.42 % |
>
> The two regulation cites are the 70 % overlap test and fund shares that mimic an index. The review also cites IRS CCA 20131902F, which treated S&P stocks with index puts and calls as a straddle (read there as a search excerpt only, and not by me). It adds an effect this section never mentioned: lost holding period and qualified-dividend status on new core lots.

## 4. Data census (verified 2026-11-20)

### 4.1 Spans and integrity (the code's `census`; no return statistic)

| File | First | Last | Rows | Gaps > 5 days | Zero-change days | Use |
|---|---|---|---|---|---|---|
| CNDR | 1986-06-20 | 2026-11-19 | 10,178 | 2001-09-17 only | 61 (27 in the 1980s; the first week is flat at 100) | **decision** |
| BFLY | 1986-06-20 | 2026-11-19 | 10,178 | 2001-09-17 only | 54 | robustness |
| PUT (CDN) | 1991-03-04 | 2026-11-19 | 5,010 | 7, the last ending 2007-01-03 (sparse before) | 10 | robustness from 2007-01-19 |
| WPUT | 2006-01-31 | 2026-11-19 | 5,232 | none | 56 | robustness from 2006-02-17 |
| VIX | 1990-01-02 | 2026-11-19 | 9,320 | 2001-09-17 only | 50 | tier analysis only |
| SPX | 1975-01-02 | 2026-11-19 | 13,081 | 2001-09-17 only | 22 | reference level for the tier model |
| French F-F daily factors | 1926-07-01 | **2026-09-30** (CRSP 202609) | 26,338 | — | — | equity leg (Mkt-RF + RF) |
| H.15 (B-5's pinned zip) | 3-month 1954-01-04; 4-week 2001-07-31 | 2026-11-09 | 18,205 / 6,321 | — | — | bill leg |

The window ends at the last roll on or before French's end: **2026-09-18**. That gives 483 roll periods. Eleven rolls fall on a Thursday: ten for holidays (Good Friday ×9, plus Juneteenth on 2026-06-19) and one data hole (§4.4).

### 4.2 Legs

- **Equity:** French Mkt-RF + RF, the CRSP value-weighted total-market total return, gross of fees. It is broad-market, not the S&P 500. D is a ratio of two arms holding the same core, so the basis matters only at second order. T-306's spliced file is not used: its post-1993 leg is processed SPY with the pre-seam DRIP error (`feedback_long_history_data_traps`).
- **Bills:** CNDR's own rule (§3.1), using H.15 secondary-market discount rates: the **4-week** bill from 2001-07-31 and the **3-month** bill before that. The 4-week bill did not exist before 2001; what Cboe's backfill used then is not stated. The 3-month bill runs slightly above the 1-month, which makes x slightly conservative before 2001.
  - The rate used is the last one known on the previous business day; any staleness over 7 days halts.
  - Cross-check, outcome-free: over the full window the CNDR-rule bill accrues **2.987 %/yr** (log) and French RF **2.996 %/yr**.
  - French's daily RF is printed to 0.01 %/day, which biases a month's bill by up to about ±0.6 %/yr. So it is used only for this check, never for the subtraction.

### 4.3 Calendar

Every Cboe date in the window is a French date. Five French dates are missing from CNDR (and BFLY): 1991-03-01, 1997-01-31, 2018-12-03, 2019-07-05 and 2020-10-16. The bill accrual over a missing day uses calendar days, so the first four are harmless.

### 4.4 The one hole on a roll date: 2020-10-16

That third Friday was a normal NYSE day: it appears in the SPX, VIX, PUT and French files. It is absent from CNDR and BFLY. The code halts on any such hole unless it is listed. This one is listed in `KNOWN_ROLL_HOLES` with its reason. The roll period ends at the 2020-10-15 close, so October's settlement falls in the next period. The year is the same, and the chained total is unchanged.

### 4.5 Pins and the durable archive

The md5 pins are in `PINNED_MD5`. The bytes now sit only in the session scratchpad (`…/scratchpad/t414/raw/`). **The Cboe files grow every day, so a re-fetch will not match the pins.**

Proposal: archive the eight files now, outside the repo, in the T-398 convention: `/Users/jacksonmurphy/Dev/_research_snapshots/t414_o1_stacked_premium_2026-11-20/inputs/`. Add the quote snapshots (§5.2) under `…/quotes/`, and copy the whole set to `s3://archondex-results-407539788432/research/t414/` if the director wants an off-machine copy. At the freeze, `--inputs` points there. The default `data/research/t414/inputs/` is a director-written alternative.

> **CORRECTED 2026-11-24.** Archived. `/Users/jacksonmurphy/Dev/_research_snapshots/t414_o1_stacked_premium_2026-11-20/` holds `inputs/` and `quotes/`; I checked all eight pinned files against their md5s today and every one matches. (`inputs/` also holds BXM and BXMD, which the study never used.)

## 5. Cost model

### 5.1 What the gross index leaves out

CNDR trades at mid, at 11:00, and holds to cash settlement. A retail taker pays half the quoted spread on each of the four legs at entry, plus commission and fees. There is no exit cost, because the position settles in cash. The cost is expressed per roll as a fraction c_req of the requirement W.

### 5.2 Quote census, 2026-11-20 (Alpaca free plan, indicative feed, Cboe-sourced; the Dec-18-2026 monthly, the contract CNDR rolled into today)

| Snapshot (UTC) | Underlying | S (parity) | ATM IV | Legs (P20 / P5 / C20 / C5) | W (pts) | Credit | Sum of half-spreads | c_req incl. fees | κ |
|---|---|---|---|---|---|---|---|---|---|
| 20:30 | XSP | 694.58 | 0.300 | 635 / 540 / 736 / 763 | 95 | 10.56 | 0.455 | **0.51 %** | 1.65 |
| 20:36 | XSP | 692.49 | 0.309 | 635 / 540 / 735 / 765 | 95 | 11.40 | 0.885 | **0.96 %** | 1.60 |
| 20:30 | SPX | 6943.24 | 0.303 | 6375 / 5450 / 7350 / 7625 | 925 | 107.42 | 3.915 | 0.42 % | 1.59 |
| 20:36 | SPX | 6927.47 | 0.314 | 6340 / 5400 / 7350 / 7630 | 940 | 108.47 | 2.725 | 0.29 % | 1.56 |

- Fees are $0.65 commission (T-402 [S9], [R]) plus an assumed $0.10 exchange and regulatory fee per leg.
- κ = (W/S) / (ATM IV · √(28/365)).
- **Caveats:**
  - It was a stressed day: SPX was down about 3.2 % on the day, with 20-delta put IV about 40 % and 5-delta about 56 %.
  - **The indicative feed is not the NBBO.** It showed a monotonicity violation (the SPX 6370 put bid above the 6375 put bid), and c_req doubled within six minutes.
- XSP is single-listed on Cboe, so Cboe's own quote is the NBBO. Cboe's delayed-quote JSON returned a Cloudflare 403 to a generic client, and I did not work around it. Alpaca serves no historical option quotes (T-410).
- SPX costs about half of XSP per unit of notional, but one SPX condor needs $38k–90k of margin.

> **CORRECTED 2026-11-24.**
> - **(R3) κ here is not the κ of §9.** This column divides by the chain's ATM implied volatility; §9's model multiplies VIX. Calling 1.56–1.65 a confirmation of 1.6 compared two different quantities. On VIX the reviewer measured 1.29–1.33.
> - **(author)** "I did not work around it" was imprecise. After the first 403 I tried two other URLs (the `cdn-api` host and a path without the underscore), both 403, and stopped. I did not change the client identity.
> - **(author)** "XSP is single-listed on Cboe" was from memory, not read on a page today. Treat it as [R].

### 5.3 The freeze rule (fixed now, before any outcome)

**Real-quote census (the preferred route).** It needs at least 10 snapshots, taken near 11:00 ET, on at least 5 roll-like trading days, including at least 2 days with VIX below 18. They must come from a real-quote source:
- one month of Alpaca's $99 OPRA plan (the owner's word);
- Cboe's delayed-quote page read in a browser by a person; or
- Schwab's option chain.

If such a census is taken, set **c_low = its median** and **c_high = its 75th percentile** of XSP c_req, fees included.

**Fallback.** Otherwise the planning values freeze: **c_low = 0.5 %, c_high = 1.0 %** of the requirement per roll, which is about 0.61 and 1.22 %/yr of equity at m = 1. They sit at the two ends of today's indicative XSP census and inside the census's estimate of 0.4–1.3 %.

**Gating.** **c_high gates.**

The rule is symmetric: measured costs can lower c_high. The quotes are outcome-free, so this does not bias the test toward a pass. Note that a lower c_high raises the pass probability (§7).

## 6. Statistic, bootstrap, gates

- **D** = log(W_stack,T / W_equity,T) after tax, reported as D and D/yr.
- **Bootstrap:**
  - A moving-block bootstrap (Künsch 1989) of the joint roll rows (rE, x, bill), with draws **identical to `MetricsEngine.bootstrap_distribution`'s**; the control in §10 proves this.
  - Each of the **2,000** paths is re-simulated after tax, with tax years of 12 consecutive resampled rolls. Seed 0.
  - **Block 12 rolls is primary**, to keep crash clusters whole; 6 and 24 are reported. ci_low is the 2.5th percentile, se is the bootstrap sd (ddof 1), and t = D / se.
- **Gates:** PASS = H1 and N1 and N2 and N3 (§1). Any condition that cannot be evaluated counts as a FAIL.
- **Reported, deciding nothing:**
  - c_low; pre-tax; τ at 9.8 % and 31 %; the $3,000 offset at $45k; buffer F1; MV = 1;
  - blocks 6 and 24; a pre-tax Newey–West t (lag 12);
  - the worst roll of each arm; MDD of each arm at roll granularity; tax paid; unused carryforward.
- **Robustness (descriptive only):**
  - BFLY at m = 1 and the same c_high;
  - PUT from 2007-01-19 and WPUT from 2006-02-17, each at m = 0.10, so the notional is 10 % of equity and the worst case is −10 % of equity, with planning costs of 2 and 5 bp of notional per roll.
  - **They cannot rescue a CNDR failure or veto a CNDR pass.** PUT and WPUT are not delta-neutral: stacked, they add equity beta and are not the same bet.

## 7. Power, MDE and pass probability

- At T = 40.25 years, t = IR · √T. The bar needs IR ≥ **0.467**. 80 % power needs IR ≥ **0.599**.
- **MDE.** At a planning σ_x of 6 %/yr, the after-tax D sd is about 4.6 %/yr, so the MDE is about **2.75 %/yr after tax**. That is roughly a 5 %/yr gross CNDR excess at m = 1, about 2.3 times the 2.2 %/yr the public endpoint shows.
- **Planning σ_x.** A design model (strikes from CNDR's deltas, one 28-day horizon, lognormal and Student-t(4) moves) gives a sd per roll of 1.4–1.8 % of NAV, **4.9–6.2 %/yr**, with a worst roll of −9 %, matching the design floor. Vol clustering and crash runs push the true value higher, so the grid uses 4, 6 and 8 %.
- **Approximation.** D/yr ≈ (1−τ)(μ_x − c) − (1−τ)ρσ_xσ_E − ½((1−τ)σ_x)², with μ_x = 2.16 % + ½σ_x², σ_E = 15 %, and τ = 23.6 %.

| Cost | σ_x | ρ = 0 | ρ = 0.2 | ρ = 0.4 |
|---|---|---|---|---|
| **c_high (gates)** | 4 % | E[t] 1.52 → **P 7.6 %** | 1.33 → 5.2 % | 1.14 → 3.5 % |
| c_high | 6 % | 1.04 → 2.8 % | 0.85 → **1.8 %** | 0.66 → 1.1 % |
| c_high | 8 % | 0.81 → 1.6 % | 0.62 → 1.0 % | 0.43 → 0.6 % |
| c_low (descriptive) | 4 % | 2.49 → 32 % | 2.30 → 25 % | 2.11 → 20 % |
| c_low | 6 % | 1.68 → 10 % | 1.49 → 7.1 % | 1.30 → 4.9 % |
| c_low | 8 % | 1.29 → 4.7 % | 1.10 → 3.1 % | 0.91 → 2.0 % |

**P(pass) ≈ 2 % (0.5–7 %)** at the gating cost.
- N1 and N2 cost little on top (about 0.9× given a pass).
- What would change the answer: a real-quote census with c_high near 0.5 %, together with a true σ_x near 4 %. That is the only route to a double-digit chance.
- The census's 10 % used an unanchored prior over IR and the unscaled formula. **This is planning arithmetic on a public endpoint and a design model, never a measurement.**

> **CORRECTED 2026-11-24 (B1).** The P columns and "P(pass) ≈ 2 % (0.5–7 %)" are withdrawn.
> - **The error.** P = Φ(E[t] − 2.96) gives t a standard deviation of 1, as if the sample mean were still to be drawn. The endpoint *is* the realized sample mean, so given σ_x, ρ and c the t is nearly fixed. Its sd is **0.10–0.3 for σ ≥ 4 %** (reviewer), not 1. The reviewer's synthetic summary file shows 0.10–0.26 at c_low and c_high, and up to 0.35 at zero cost.
> - **What is left to learn is σ_x.** The largest σ_x that still reaches t = 2.96:
>
>   | Cost | ρ = 0 | ρ = 0.2 | ρ = 0.4 |
>   |---|---|---|---|
>   | c_high (gates) | 2.0 % | 1.9 % | 1.8 % |
>   | c_low | 3.35 % | 3.15 % | 3.0 % |
>   | zero cost | 4.7 % | 4.4 % | 4.1 % |
>
>   These are the reviewer's. I re-derived them from the approximation above and got the same values (2.03 / 1.91 / 1.80; 3.35 / 3.15 / 2.97; 4.69 / 4.40 / 4.14).
> - **The design model puts σ_x at 4.9–6.2 %** (mine) or **4.5–5.7 %** (the reviewer's own model). That is above every c_high and c_low limit.
> - **Conditional pass probability: about 0.1 % at c_high and ≤ 1 % at c_low** (reviewer).
> - **"That is the only route to a double-digit chance" is WRONG.** That cell (c_low, σ 4 %) passed **0 of 60** synthetic draws at each of ρ = 0, 0.2 and 0.4 in the reviewer's run of this study's own engine.
> - The 80 %-power and MDE lines are unconditional. Once the endpoint is known they do not describe this test.

## 8. Falsifier, and what a pass licenses

**FAIL** (any of: ci_low ≤ 0, t < 2.96, N1 ≤ 0, N2 ≤ 0, N3 < 0.5):
- **closes premium selling for this owner in every wrapper, in the stacked form.** With T-279 and T-261 (the substitute form), the whole family is closed: put-write, covered call, condor and butterfly.
- BFLY, PUT and WPUT cannot reopen it.
- Reopening needs **new information**, not a re-cut:
  - a quote-based option history (for example OptionMetrics) showing materially lower taker costs, or
  - capital large enough for SPX condors (≥ about $550k), each under its own prereg and trial.

> **CORRECTED 2026-11-24 (B2).** The falsifier overclaimed and is withdrawn. The most a FAIL could have spoken to is one form: **the monthly 20/5-delta SPX condor index (CNDR), m = 1, stacked on 100 % US equity, gross index less planning cost, best-case §1256 tax.** It does **not** close put-write, covered calls, butterflies or spreads, in any wrapper. The owner's 2026-11-14 directive governs: a refutation is scoped to the form tested. T-279 and T-261 keep only their own scopes. Because the study is closed unrun, not even the narrow form has been refuted.

**PASS** licenses **paper only**: the owner puts no real money in the machine until it confidently outperforms. Specifically:
1. a forward archive of real XSP/SPX quotes on CNDR's legs at each roll (D-1), to measure taker costs. Paper option fills are invented (`feedback_paper_probe_taker_only`), so a paper P&L would prove nothing;
2. a tax adviser's ruling on §3.5's straddle hazard;
3. a decision item at ≥ $100k of taxable equity in a self-directed margin account.

There is no options order path in the code (T-396 §3), and building one touches `paper_trader/` and `live_trader/`: propose-first.

## 9. Tier analysis (descriptive; decides nothing)

**Model.** The widest wing in XSP points is W = κ · VIX/100 · √(28/365) · SPX_ref/10.
- SPX_ref = 7,175.83, the 2026-11-19 close: today's granularity at every point in history.
- κ = 1.6 for planning; today's chain gave 1.56–1.65. It is re-set from the §5.3 census at the freeze.
- Under this model, one XSP condor carries 10 · W · $100 of CNDR-equivalent NAV. Holding the decision size at tier B takes n = m · B / (1,000 · W) condors, where m is the multiplier from §3.4 and W is in XSP points.

**Rounding rules.** Floor (never exceed k = 0.10) is the frozen rule; nearest is reported.

Outcome-free contract counts over the 1990-01-19 → 2026-09-18 rolls, VIX only (the code's `census`):

| Tier | Floor: share of rolls with 0 condors | Floor: median condors | Floor: m_eff p10/p50/p90 | Nearest: share with 0 | Nearest: m_eff p10/p50/p90 |
|---|---|---|---|---|---|
| $20k | **100 %** | 0 | 0 / 0 / 0 | 85 % | 0 / 0 / 1.78 |
| **$45k** | **73 %** (59–91 % for κ 1.4–1.9) | 0 | 0 / 0 / 0.91 | 10 % | 0 / 1.13 / 1.69 |
| $100k | 6 % | 1 | 0.52 / 0.73 / 0.93 | 0.7 % | 0.74 / 1.00 / 1.23 |
| $250k | 0.2 % | 4 | 0.76 / 0.89 / 0.98 | 0 % | 0.90 / 1.00 / 1.09 |
| $1M | 0 % | 18 | 0.94 / 0.97 / 0.99 | 0 % | 0.98 / 1.00 / 1.03 |

- Wing widths at κ = 1.6: p10/p50/p90 of **38 / 55 / 90 XSP points**, which is $3.8k / $5.5k / $9.0k of margin per condor. Today's chain: 95 points.
- `run` reports D on each tier's integer path from 1990, under the floor rule and c_high. Fixed per-contract fees ($3 per condor per roll) are below 0.1 %/yr at these widths and are folded into c_req.

> **CORRECTED 2026-11-24 (R3).** The table is for κ = 1.6, which is κ on ATM implied volatility. The model uses VIX, where the reviewer measured **κ = 1.29–1.33**. My κ range (1.4–1.9) did not contain that value.
> - **$45k, floor: about 49.5 % of rolls with zero condors at κ 1.3, to about 73 % at κ 1.6; median 1 at κ 1.3** (reviewer's recount on VIX only). This fits the threshold arithmetic: floor gives zero when VIX is above 17.4 at κ 1.3, against 14.2 at κ 1.6.
> - **$20k: still 100 % zero** (at κ 1.3 a condor would need VIX below 7.7).
> - **"Holdable at $100k, clean at $250k" holds for κ 1.3–1.9.**
> - Consequences of linear scaling: wings p10/p50/p90 at κ 1.3 are about 31 / 45 / 73 XSP points ($3.1k / $4.5k / $7.3k per condor). §0.2's "$380k–900k" becomes about $310k–730k, §5.2's SPX "$38k–90k" about $31k–73k, and §8's "$550k" about $450k.
> - The m_eff and nearest-rounding columns were **not** recomputed at κ 1.3; do not quote them.

## 10. Phase-1 controls and smoke (run 2026-11-20)

Every control runs on the study's own code path, and **any miss halts** with exit 2.

| Control | What it proves | Result |
|---|---|---|
| bill_formula | the code's bill accrual equals CNDR's §3.1 closed form (no accrual on the roll day) | PASS (to 1e-14) |
| hand_stack | three rolls over two tax years, recomputed by explicit scalar arithmetic (a taxed gain, then a carried-back loss), equal the engine | PASS (1e-14) |
| tax_ledger | hand-built ledgers: gains 10/20/30 then −45 (carryback earliest first), and 5/−20/8/10 (carryforward shelters later gains) | PASS |
| roll_calendar | every roll is a third Friday or at most 4 days before one | PASS |
| design_floor | no CNDR roll return below −11 %. Smoke window only in phase 1; `run` halts if any of the 483 breaches it | PASS |
| bill_vs_french | the CNDR-rule bill and French RF agree within 75 bp/yr over the smoke window | PASS |
| metrics_engine_replay | with tax, costs and trading cost at zero, the engine's bootstrap percentiles equal `MetricsEngine.bootstrap_distribution` to 1e-10 | PASS |

- **Reversion tests:** each control **misses** when its target is broken: a different resampler, no carryback, a cost-convention mismatch, a planted floor breach.
- **End to end on synthetic inputs:** a planted premium of 1 %/roll passes every gate; zero fails; −1.2 %/roll breaks N3.
- **Test suite:** `tests/test_t414_o1_stacked_premium.py`, 40 tests.
- **Smoke:** the first 12 rolls (1986-07-18 → 1987-06-19), with smoke-only settings (block 3, 200 draws). Two runs gave the identical md5 `7ec011c82b7a0479c6dfe1a715997453`; never quoted.
- **Refusals:** `run` exits 2 while `FROZEN = False`; any `--out` under a repo `data/` exits 2.

> **CORRECTED 2026-11-24.**
> - **(author) "Each control misses when its target is broken" is false for 3 of the 7.** Reversion tests exist for `metrics_engine_replay`, `tax_ledger`, `hand_stack` and `design_floor`. There is none for `bill_formula`, `roll_calendar` or `bill_vs_french`. The `hand_stack` one changes the control's own cost constant rather than breaking the engine. Commit 051b2f0's message and my hand-off report repeat the false claim.
> - **(author)** `design_floor` cannot miss through the `controls` command, because `build_panel` halts on the same condition first.
> - **(review)** **22 of 34 mutants survived** the test suite; the list is in the review. "40 tests pass" is therefore weak evidence about the code. Not fixed: study closed.

**Proposed pre-freeze control C7 (not run; the director's call).** Reconstruct one roll period from Alpaca's SPX option bars, which start around 2024-03-07 and include expired contracts (verified today). Only the reconstructed-to-index ratio would be printed. It would prove the ten-times collateral scaling on real prints, but it reveals one roll out of 483.

## 11. Before the freeze

1. **Director's rulings on this DRAFT:**
   - m = 1.0 (the census rescaling);
   - adding N2;
   - the bill rule;
   - the symmetric cost rule;
   - τ = 23.6 %;
   - window end 2026-09-18;
   - KNOWN_ROLL_HOLES;
   - whether C7 runs.
2. **The cost census** of §5.3, or an explicit ruling to freeze the planning schedule.
3. **κ re-set** from that census (tier analysis only).
4. **Archive the inputs** (§4.5) and point `--inputs` at the archive.
5. **The freeze commit:**
   - set `FROZEN = True` and the cost constants;
   - record the trial: `python -m scripts.honest_n_trials record --trial-id T-414 --task-id T-414 --n-trials 1 …`;
   - check both lints (`doc_lint` and `honest_n_trials check`).
6. **The measurement:** `run --tag A` and `run --tag B` must give identical md5s, then a fresh-eyes review by execution.

**Proposed count: +1** (the decision cell). The sensitivities, robustness indices and tiers decide nothing and count 0. The controls and the smoke count 0.

## 12. Unverified items [R / UNVERIFIED]

- Whether Schwab's robo (SIP) can hold options at all. Assumed no: it is a managed program [R].
- Schwab's options approval level for spreads, the margin-account requirement for spreads, any minimum equity, and its index-option fees [UNVERIFIED]. The $0.65 commission is [R] (T-402).
- That the core's Reg-T loan value covers a defined-risk spread requirement with no debit [R].
- The settlement style of the standard monthly XSP (AM or PM). The Cboe page lists PM, standard, weekly and daily expirations [UNVERIFIED].
- Retail fill quality on four-leg complex orders [unknown]. The taker rule assumes the quoted half-spread, per Muravyev–Pearson 2020's caution that timed fills may be better.
- The section 1092 straddle treatment against an S&P 500 fund core [UNVERIFIED, material, §3.5].
- What Cboe's 1986–2015 backfill used for the bill rate and for historical SPX quotes [unknown; disclaimer only].

## 13. Reproduce

```bash
python -m scripts.t414_o1_stacked_premium census   --inputs <archive>/inputs --out <dir>   # outcome-free
python -m scripts.t414_o1_stacked_premium controls --inputs <archive>/inputs --out <dir>   # exit 2 on a miss
python -m scripts.t414_o1_stacked_premium smoke    --inputs <archive>/inputs --out <dir>   # first 12 rolls; never quoted
python -m scripts.t414_o1_stacked_premium run      --inputs <archive>/inputs --out <dir> --tag A   # refuses until FROZEN
python -m pytest tests/test_t414_o1_stacked_premium.py -q
```

## 14. Provenance

- **Read:**
  - CLAUDE.md;
  - the T-410 census (§1, §2.1, §4, §5 O-1, §7.2);
  - the T-279 verdict and the T-261 screen;
  - the T-174 row;
  - the T-409 DRAFT (§4.3 tax engine, §4.7 data);
  - T-398's harness (structure only), B-5's H.15 parser;
  - `MetricsEngine.bootstrap_distribution`;
  - the edge-analyst memory.
- **Fetched**, with User-Agent `ArchonDEX-research/1.0` and no personal details:
  - the Cboe CDN CSVs (via the cdn-api redirect);
  - the Cboe CNDR, BFLY, WPUT and PutWrite methodology PDFs;
  - Cboe's XSP product page;
  - Ken French's daily factors zip;
  - IRS Form 6781 (2025).
- **Alpaca** (paper key read from `.env`, never printed): two option-chain snapshots and one bars-availability probe.
- **Scratch code and data** live under the session scratchpad `t414/`: probes, the condor σ model and the cost census.
- **No engine, `live_trader/`, `paper_trader/` or `docs/State` file was touched.**

## 15. Review (2026-11-24)

Verdict: NOT READY, CLOSE UNRUN. The reviewer reproduced the engine to 1e-15. The findings come from the independent reviewer's execution review, relayed by the director. The first version of this section lacked the text of R1, R2, R4–R8 and the minors; the director then supplied it. Its three unnumbered rows are R1 (the cash buffer), R2 (§1092) and R4 (the mutants).

The figures are the reviewer's. The author checked only what is marked **[author checked]**, by reading the code at `b66b5a2` or by arithmetic; nothing was run.

| # | Finding | Resolution |
|---|---|---|
| B1 | Pass probability mis-specified: the endpoint pins the mean, so t has an sd of 0.10–0.3, not 1 | Text corrected in §0.3, §0.4, §7. Code not fixed: study closed |
| B2 | The falsifier claims more than the form tested | Text corrected in §0.4, §8. Not fixed: study closed |
| R1 | The primary silently drops the census's bill buffer. T-410 §7.2 charges a worst-month cash buffer; the prereg made F2 (no buffer) primary and F1 a sensitivity (§3.4), missing from the §2 deviation list and the §11 rulings. F1 costs ≈ 0.5–0.8 %/yr and the planning after-tax D at c_high is +0.5 to +0.6 %/yr, so the choice sets the sign. Also unlisted: block 12 instead of Politis–White | Covered in the text by the §2 and §3.4 corrections (buffer) and the §2 R1 correction (block 12). §3.4 quotes the author's own grid for D (0.4–0.8 %/yr). Not fixed: study closed |
| R2 | §1092 straddle risk flagged but unsized, and it can flip the sign: 26 CFR 1.246-5(c)(1)(iii)(B) (≥ 70 % overlap) and (e)(2)(ii) (fund shares mimicking an index) make an S&P core plus S&P options a likely straddle; IRS CCA 20131902F treated S&P stocks with index puts and calls as a straddle (search excerpt only). Also unmentioned: lost holding period and qualified-dividend status on new core lots. The fix would have been to label the decision cell "best-case tax" and add a gains-only tax cell | Covered in the text by the §3.5 correction, with the deferral sizes. The gains-only cell was not added. Not fixed: study closed |
| R3 | κ is measured on ATM IV but used on VIX; on VIX it is 1.29–1.33 | Text corrected in §0.1, §5.2, §9. Code not fixed: study closed |
| R4 | Tests much weaker than claimed. 40/40 pass, but 22 of 34 mutations survived. `test_run_refuses_while_unfrozen` and `test_out_under_data_is_refused` are vacuous: they pass with the check removed, because empty inputs also exit 2 **[author checked]**. `control_tax_ledger` claims "carryback earliest first", yet latest-first survives. Nothing pins the N1/N2 index, the cohort minimum, the 2.5th percentile, t, the year-end flags, the synthetic tax years or the cost scaling. `cmd_run` has no test: "uses cost_low" and "uses NO_TAX" both survive | Partly covered: §10's correction records 22 of 34 and the missing reversion tests. The vacuous tests and the unpinned items are recorded only here. Not fixed: study closed |
| R5 | Fail-closed gaps in `build_panel`. The design check is one-sided (line 366 **[author checked]**): a ×10 rebase passes with a max roll of +893 %. A 15-day off-roll hole, 6 months flat, and 10 missing French days all pass; only `census` sees holes. Ten of CNDR's 61 zero-change days fall on roll Fridays (1986-10-17, 1986-12-19, 1987-05-15, 1987-12-18, 1988-02-19, 1989-02-17, 1989-03-17, 1992-09-18, 1995-08-18, 2002-01-18) and §4.1 does not say so ("present is not usable"). `run` rechecks only the design floor though §10 says every miss halts. The bill tolerance (75 bp/yr, line 736 **[author checked]**) equals the net effect; it should be 10 bp | Not covered elsewhere; this row supersedes §4.1's silence and §10's "any miss halts". The author checked that the ten dates are third Fridays, not the levels. Not fixed: study closed |
| R6 | Output-guard bypasses (lines 823–829 **[author checked]**): `--out <repo>/DATA/x` on case-insensitive macOS; another worktree's `data/`; `--tag "A/../../escaped"` wrote outside `--out`; the guard switches off when FROZEN is True | Not covered elsewhere; this row supersedes §10's "any `--out` under a repo `data/` exits 2". Not fixed: study closed |
| R7 | The gating-cost rule contradicts itself: code line 99 says the freeze "may only RAISE" c_high **[author checked]**; §5.3 says it can be lowered. With the mean known, lowering cost is the one lever toward a pass | The contradiction is recorded in §16 item 4. "The one lever" is recorded only here, and it supersedes §5.3's "does not bias the test toward a pass". Not fixed: study closed |
| R8 | Trial count: the run also produces D, t and CI for BFLY, PUT and WPUT, and §8 uses them. Drop or count them (+4 on a literal `[NN-MBL]` reading) | Not covered elsewhere; this row supersedes §11's "count 0" for the robustness indices. 0 trials were consumed. Not fixed: study closed |

**Minors** (numbered here in the order supplied; the numbers are this file's). Resolution for all: not fixed, study closed.

| # | Finding |
|---|---|
| m1 | MV 1.02 is padding: the correct 1/(1 − credit/10W) is 1.009–1.012, so it is ≈ 0.03 %/yr conservative; §7's μ_x omits it |
| m2 | N2 charges tax inside its window on 8 pre-window 2015 rolls |
| m3 | §1212(c)(4)(B) first nets against the year's other capital gains |
| m4 | Some states allow no carryback, yet refunds use the full τ including 5 % state |
| m5 | τ = 23.6 % lacks NIIT (immaterial: t 1.30 → 1.35 for τ 0 → 34.8 % at σ 4 %) |
| m6 | E[max of 372] = 2.946; 2.96 is the approximation |
| m7 | At m = 1 the condor notional is ≈ 0.8–1.9× equity (p10–p90), undisclosed. **[author checked]** That range is κ 1.6; at R3's κ of 1.3 the same arithmetic gives ≈ 1.0–2.3× |
| m8 | A pass should also require pricing the robo-exit tax |
| m9 | A roll-day mark could breach −11 % and halt after the freeze |
| m10 | Stale code references: lines 59 and 82 cite §4.6 (it is §4.5), line 113 cites §6.5, line 122 cites §9.2 **[author checked]**; "12 controls" is 7. The author did not find "12 controls" in the branch's script, tests, prereg or manual entry |
| m11 | The probes' User-Agent carried the project name; it should be a generic one. §14's `ArchonDEX-research/1.0` is that string, so §14's "no personal details" does not mean no project name |

**Verified by the reviewer:** methodology v4.2 re-fetched (md5 identical); m = 1.0 correct; the after-tax engine agrees on 300 random paths to 2e-15; the MDE's 2.29× gross is the 80 %-power figure, and the pass bar needs 1.9×; `run` refuses with the FROZEN message on the real inputs.

## 16. Corrections found by the author (2026-11-24)

These did not come from the review.

1. §2: the disclosure of what was seen was incomplete, the H1 smoke boolean was mis-described, and two departures from the census were not listed.
2. §5.2: two extra URLs were tried after the 403; "single-listed" was from memory.
3. §10: "each control misses when its target is broken" holds for 4 of 7 controls. The same false claim is in commit 051b2f0's message and in the hand-off report.
4. The code's comment on `COST_REQ_HIGH` says the freeze rule "may only RAISE it"; §5.3 says the rule is symmetric. They disagree. Not fixed: study closed.
5. The hand-off report called all 45 suite failures "environmental" after the author had read only a sample of them. Checked today: in the same worktree, on main at `29fd716` with no T-414 code, the 13 files that failed give the **same 45 failures, name for name**. T-414 did not cause them. The cause (the worktree has no `data/`) was read for a sample, not for each.
6. The hand-off report wrote "the 2026-10-16 hole"; the date is **2020-10-16**.
