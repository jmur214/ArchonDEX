---
task_id: T-409
title: DRAFT pre-registration — where should the owner's retirement money sit? A decision study (Schwab robo, VOO, 85/15, a target-date fund, lifecycle leverage)
date: 2026-11-19
worker: edge-analyst (worktree agent-ac300c3d5f4eba52f)
status: DRAFT — NOT FROZEN. PHASE 1 only: synthesis of the record, a draft design, and a read-only data census. No arm's return, wealth path or terminal value was computed on any sample. The census read file spans, column names and row counts only. This file states NO trial count; §4.10 lists what each arm would add, for the director's ruling at freeze.
design_inputs: docs/Sources/design_note_lifecycle_leverage_t396_2026-11-14.md (T-396, cherry-picked onto this branch from research/lifecycle-leverage-note-t396 @ 1703827, author and message unchanged)
---

> **SUPERSEDED IN PART by revision 2** (`docs/Sources/prereg_real_money_home_t409_DRAFT_2026-11-19.md`,
> 2026-11-19), after the owner's answers. The robo account is **taxable**, not the Roth, and the
> robo profile is **aggressive**. Revision 2 §0 lists which parts below are moot or wrong.
>
> Everything below this banner is revision 1 verbatim (commit `d0616ae`), kept because revision 2 cites
> its sections. The census (§5), data layers (§4.5), precision method (§4.6) and contradictions 1–9 (§6)
> still apply.

# T-409 DRAFT — where the real money should sit, with lifecycle leverage as one candidate

## For the owner, in plain words

**What this is.** A plan for one study, plus a summary of what the project already knows. Nothing has been
run, so no number below is new.

**What the project already knows.**

1. **The biggest unknown is a fact only you have: what risk setting your Schwab robo uses.**
   - Schwab's own brochure (dated 2026-10-15, read today) says the robo keeps **6 % to 30 %** of the
     account in cash, depending on that setting. That cash currently earns 3.51 %.
   - The project's stand-in for the robo is a middle setting: 45 % stocks, 30 % bonds, 5 % gold, 20 % cash.
   - **If your robo looks like that,** the record already answers the question. A plain S&P 500 or
     total-market fund is expected to leave you with much more money after 40 years, provided you really
     never sell. In the project's 2000–2026 replay at $7,000 a year, plain stocks reached about $929k and
     the robo stand-in about $495k. A worse future for stocks shrinks that gap but does not close it. No
     new test is needed.
   - **If your robo is on its most aggressive setting** (at most about 94 % stocks, since at least 6 %
     is cash), the gap is much smaller. About 0.2–0.5 % a year can be counted (the cash and the fund fees). The rest is a bet on
     U.S. stocks against foreign stocks, and no test can settle that.
2. **Putting more money in beats almost every other option.** Each extra $1,000 a year is worth about
   $196,000 in today's dollars at year 40, at historical returns, with no bet attached.
3. **Leverage is a bet, not a discovery.** Here leverage means buying 2× funds while young and stepping
   down later. It pays only if stocks beat cash by enough over the next 40 years. Expected result
   against plain stocks, by how the next 40 years compare with the last century:
   - as well as the last century: **+22 %**;
   - 1 point a year worse: **+10 %**;
   - 2 points worse: **about zero**;
   - 3 points worse: **−12 %**.

   Even where it pays on average, there is about a **3-in-10 to 2-in-3 chance** of ending behind
   plain stocks. A 1929-style crash at a steady 2× turns $10,000 into about **$158**. No backtest can prove
   leverage right or wrong for you; the record says so, and this study is designed knowing it.
4. **Tilts are small.** Adding 15 % momentum (the 85/15 mix) is worth a few percent of final wealth on
   history, and that number is not statistically distinguishable from zero.

**What the study would add.**
- It puts every candidate home on one table, in today's dollars, under your own plan: three years of
  no contributions for law school, 40 years, never selling.
- It uses 100 years of U.S. data and 15 other countries.
- It shows four rows, one per belief about future stock returns: as good as the last century, or 1, 2
  or 3 points a year worse. **You pick the row you believe.** In that row, the table shows which home
  leaves the most money while staying inside a worst case you set in advance.

**What it needs from you before it runs** (a default is used if you skip one):
1. The robo's stock / bond / cash percentages, from the Schwab app.
2. Whether that account is your Roth IRA.
3. Its current balance.
4. When law school starts.
5. The worst outcome you would accept. Default: never below two-thirds of plain stocks in any
   historical 40-year run.
6. Would you buy *more* of a 2× fund right after a crash? The leverage plans require it.

**What it will not do.** It will not tell you the future, and it will not certify any choice as proven.
The honest expected verdict on leverage, tilts and the target-date fund is "cannot certify". The choice
is yours.

**One thing worth knowing now.** `docs/State/GOAL.md` keeps the money in the robo until *this trading
system* passes paper validation. A plain index fund is not this system: it is one or two manual trades.
Whether that rule is meant to cover a move to a plain fund is your ruling, not a research question.

---

## 1. What is already settled (with the numbers the record reported)

| Question | What the record says | Firmness | Source |
|---|---|---|---|
| **Moderate robo vs 1× equity, won't-sell, 40 years** | $7k/yr, 2000–2026, one path: buy-hold SPY TR **$929,498** (worst $ drawdown −$157,610) vs `schwab_like` proxy **$494,701** (−$55,604) vs 60/40 $594,554. 64 years lump sum: buy-hold $5.73M vs `schwab_like` $1.35M. | **Settled on point; no interval on record.** Neither T-287 nor T-311 put a CI on buy-hold minus the robo. The size of the gap is the equity premium on the ~55 % the proxy does not hold: t ≈ 3.4–4.2 over 58–99 years for the premium itself. My arithmetic (§2.1) has 1× ahead in expectation in every belief row offered. | `docs/Audit/dividend_reconcile_verdict_t287_2026_07_07.md:41-53`; `docs/Audit/deep_reverify_sleeve_t311_2026_07_27.md:76-81`; T-396 §2.0 |
| **What the robo proxy is** | 45 % SPY / 30 % ten-year Treasury TR synthetic / 5 % gold / 20 % cash at the bill rate. It is one middle profile. | A modelling choice, not the owner's account. The real robo holds **6–30 %** cash by profile (brochure p.13, read today) at the SWGXX seven-day yield (3.51 % APY from 2026-11-02, read today), and charges no advisory fee (pp.8–9). | `core/combined_candidate_scorecard.py:26-35,68-71`; `scripts/accumulation_model_t283.py:134-135`; §5 census |
| **Trend sleeve as a wealth home** | Loses to buy-hold on wealth at depth: $1.96M vs $5.73M over 64 years. Its timing is significantly value-destroying net of cash, −5.16 pp/yr (CI excludes 0). | **Settled** (CI-significant). It is a drawdown tool, not a wealth tool. | T-311; T-333 (ledger row) |
| **Growth/tech tilt** | Wins 7–10 % of 40-year windows; QQQ −81.1 %, 14.6 years underwater. | **Refuted** | `docs/Audit/tilt_decision_verdicts_t318_t320_2026_07_27.md:31-33,43` |
| **85/15 VOO/MTUM vs VOO** | 2000–2026: +0.079 log terminal wealth (+0.30 %/yr), ci_low −0.066 (block 7), −0.038 (block 60). T-320, 1927+, 80/20 long-only momentum: [+0.139, +0.565]; the post-1993 decayed variant [−0.118, +0.307] straddles. | **The prior, not a finding.** The point estimate is positive and small. Significance rests on pre-publication data. | `docs/Audit/b9_combo_tilts_verdict_2026-11-11.md:46-52,215-237`; T-320 table |
| **Static leverage (SSO synthetic, T-399-corrected)** | D-B 1968+: 2× +1.66 %/yr [−2.76, +5.83], 1.25× +0.15 [−0.95, +1.17]. No static arm CI-beats or CI-loses in any window. At −2 % premium every arm is behind on point (0.81–0.91× of 1×); at −3 % 0.46–0.70×. 1929 path: 2× takes $10,000 to $158, 19.0 years to recover. | **Neither supported nor refuted.** A belief decision. | `docs/Audit/static_leverage_t315_2026_07_27.md:332-430,594-623` |
| **Gated (trend-switched) leverage** | Execution-bound: the gate's turnover at measured slippage exceeds the edge. | **Refuted** for this vehicle | T-294, T-294b, T-312 (ledger rows) |
| **Lifecycle leverage** | **Never run.** Arithmetic only (normal approximation, independent annual returns, $5k/yr). Expected gain at year 40 vs 1×, real dollars: **+$250k (+22 %) / +$86k (+10 %) / −$8k (−1 %) / −$59k (−12 %)** at the realized premium / −1 / −2 / −3 pp. P(below 1×) **29 / 39 / 51 / 64 %**. A flat 1.25× has about the same expected gain with about half the dispersion against 1×. | **Open as a measurement; closed as a gate question.** The best possible t for untimed leverage is 2.04 (1968+) or 2.63 (1926+), against 2.96. | T-396 §0, §2d, §4 |
| **Kelly** | On the arithmetic mean, before costs: 2.55 → 1.83 → 1.48 at 0 / −2 / −3 pp (T-399). With SSO-blend costs: 2.05 / 1.69 / 1.33 / 1.00 at 0 / −1 / −2 / −3 (T-396). Half-Kelly ≈ 1× with any real vehicle. | Arithmetic | T-399 R.3; T-396 §2b |
| **Levered stock/bond stacks; gold leg; multi-factor tilts; small-value** | +0.21 %/yr [−1.91, +2.30]; +0.042 [−0.341, +0.441]; 60/20/20 ci_low −0.241; [−0.066, +0.735] with ⅔ of the premium decayed. | **Refuted or straddling** | B-5/T-382; B-10/T-385; B-9/T-380; T-318 |
| **Certain-sign items** | +$1,000/yr of contributions ≈ +$196k real at year 40 (1×, realized premium). An HSA, if the plan qualifies. A broker incentive of $45–675 in year 1 (none at Alpaca). | Certain sign; size depends on owner facts | T-396 §5; `docs/State/advisor_surface.md`; T-402 §1 |

**Robo vs a plain index fund — the plain answer.**
- **For a moderate-profile robo (≈ 45–60 % equity), it is settled.** For a won't-sell 40-year holder, 1×
  equity has the higher expected terminal wealth under every belief row this study offers. The study
  does not need to re-test that. It only needs to price it in the same frame as the other candidates.
- **For an aggressive-profile robo (≈ 94 % equity, 6 % cash), it is not settled, and cannot be.**
  - The known-sign part is small: cash drag plus fees, about 0.2–0.5 %/yr (§2.1).
  - The rest is the robo's international and fundamental-index share. That is a US-vs-world bet with
    tracking error far above the premium being chased.
- **The owner's profile is not in the repo.** Neither is whether that account is the Roth (T-402 §7).
  Those two facts decide which of the two cases applies. Both are on the owner's statement.

## 2. What is genuinely open

1. **Owner facts** (no study needed): the robo profile, whether the robo is the Roth, the balance, when
   school starts, the loss bound, and whether the owner would re-lever after a crash.
2. **The owner's forward equity-premium belief.** It is a belief and stays one. The study reports every
   row, and the owner picks.
3. **Lifecycle vs flat vs 1× under the owner's actual schedule** (open measurement).
   - What is missing: full distributions, the worst cohort, dollar drawdowns and P(below 1×), under real
     blend costs, in real dollars, with the law-school pause.
   - T-396 is a normal approximation. Nothing has been simulated or cohort-run.
4. **Robustness outside the United States** (never tested here, for any arm). The US equity premium
   is the survivor's premium. JST gives 15 other markets (Japan, Germany, Italy, France, …) where the
   lower-premium rows actually happened.
5. **One frame for the dull candidates.** The robo (at the owner's profile), a target-date fund and
   85/15 are mostly known by arithmetic. They have never been priced with path metrics under this
   schedule.

### 2.1 Pre-run arithmetic for the robo and the target-date fund

Arithmetic only, so these numbers can be checked against the run. Inputs are the T-396 moments for
1926–2025: arithmetic equity excess μ 7.75 %, σ 17.14 %, σ² 2.94 %. The bond inputs are **my
assumptions**: excess return 1.5 %/yr, σ 7 %, ρ(stocks, bonds) ≈ 0. Gold excess return is taken as 0.

| Comparison | Δ arithmetic mean | ½·Δσ² | Δ log growth, %/yr | Tracking error | IR | t at 58 / 99.5 yr |
|---|---|---|---|---|---|---|
| 1× minus moderate robo (45/30/5/20), realized premium | 0.55·7.75 − 0.30·1.5 + 0.20·0.30 ≈ 3.87 | ½(2.94 − 0.64) ≈ 1.15 | **≈ +2.7** | ≈ 9.6 % | ≈ 0.28 | ≈ 2.1 / 2.8 |
| same, −3 pp premium | 3.87 − 0.55·3 ≈ 2.22 | 1.15 | **≈ +1.1** | ≈ 9.6 % | ≈ 0.11 | ≈ 0.8 / 1.1 |
| 1× minus aggressive robo (94 % US-equity proxy, 6 % cash at bill − 0.30), realized | 0.06·(7.75 + 0.30) ≈ 0.48 | ½(1 − 0.94²)·2.94 ≈ 0.17 | **≈ +0.31**, plus a 0.07–0.17 fee gap | ≈ 1.0 % | ≈ 0.3 before fees, 0.37–0.47 with them | ≈ 2.3 / 3.0 before fees; 2.8–3.6 / 3.7–4.7 with them |
| same, −3 pp | 0.06·5.05 ≈ 0.30 | 0.17 | **≈ +0.13**, plus the fee gap | ≈ 1.0 % | | |

- **Dollar-weighted, the moderate gap is large.** About 20 effective years at +2.7 %/yr is ≈ +0.54 log,
  or ×1.7 of terminal wealth. T-287's single 2000–2026 path printed ×1.88. At −3 pp it is still about
  ×1.2.
- **The aggressive case's known-sign gap is 4–10 % of terminal wealth.**
  - The fee gap assumes a 0.10–0.20 % blended robo ETF expense ratio [R] against VOO's 0.03 % [R].
    Both are verified at freeze.
  - With a US-only equity proxy the tracking error is tiny, and a fee is a deterministic drag, so the
    t is high for a trivial claim. With the robo's real ~40 % international share the tracking error
    is ~5.7 %/yr and the IR collapses to ≈ 0.05–0.08 (t ≈ 0.5–0.8 over a century).
- **Target-date fund (90 % equity for 15 years, then linear to 50 % at year 40).** Over the last 25
  years it averages ≈ 70 % equity: 0.30·7.75 − ½(1 − 0.49)·2.94 ≈ +1.6 %/yr in favour of 1×. That lands
  on the largest balances. My expectation: 1× ends 10–30 % ahead at the realized premium and still ahead
  at −3 pp.

## 3. Owner inputs at freeze (each with the default used if unanswered)

| # | Input | Default | Why it matters |
|---|---|---|---|
| O1 | Robo allocation (equity incl. US/intl split, bonds, cash, other) from the Schwab statement | Run both bounds: **A1-agg** (94 % equity / 6 % cash) and **A1-mod** (repo proxy 45/30/5/20) | Decides which half of §1's answer applies |
| O2 | Is the robo account the Roth? | Yes | If taxable, a sale is taxed; move it in kind (T-402 §3) |
| O3 | Current balance B0 | $10,000 (the records' labelled assumption); $20,000 as a sensitivity | Sets the account ÷ PV of contributions still to come (after the year-1 contribution, schedule S1): 8.0 % at $10k, 12.5 % at $20k |
| O4 | School years with no contribution | Years 2–4 of 40 | Moves the leverage cap's binding window |
| O5 | Loss bound | The arm's worst historical 40-year cohort ≥ 0.67× A0, **and** bootstrap P(W_arm < 0.5·W_A0) ≤ 5 % in the chosen belief row | Fixes the bound before the table is seen |
| O6 | Would you re-lever after a crash? (the G-arms buy more 2× fund each January after a fall) | Not assumed. If "no", A4/A5 are ineligible and reported only | A rule the owner will not follow is not a candidate |
| O7 | Belief row | **Not needed before the run.** The owner reads all four rows and picks one | Nothing is selected for a gate, so picking afterwards selects nothing |

## 4. The pre-registration (DRAFT)

### 4.1 Framing — a decision study, not an alpha claim

- **Run once, as an estimate.** No arm, weight, schedule or threshold may be revised after any output is
  read. A change is a new pre-registration.
- **Verdict vocabulary: DESCRIPTIVE.** The program's gate is computed and reported (§4.8). It decides
  nothing. Its expected reading is "cannot certify" for every arm that would move money toward risk.
- **The decision is the owner's.** The study supplies one mechanical rule, stated here so it cannot be
  tuned later. In the owner's belief row, among arms that satisfy the loss bound O5, the highest
  `E[log W_T]` wins. A difference smaller than the larger of (Monte Carlo error × 2) and (the spread
  across the three bootstrap block lengths) counts as a tie, and a tie goes to the simpler arm, A0. The
  machine recommends nothing beyond that table.
- **Licenses nothing in the system.** No edge promotion, no Engine A–F change, no paper or live book.
  Any leverage book on paper is a separate propose-first unit (`paper_trader/`).

### 4.2 Arms (frozen at freeze; costs by calendar time, never 1/252 per bar)

**Common to every arm**
- **Equity gross leg.** Ken French daily (and monthly) `Mkt-RF + RF`: CRSP value-weighted total market,
  dividends included, gross of fund fees, CRSP vintage 202609.
  - It is used for the full span, with no splice to SPY adjusted close. That removes by construction
    the T-306 post-1993 SPY splice and its fee add-back convention (T-399 R.8(b)).
  - It also removes the pre-seam DRIP issue of the processed SPY file.
  - This is the broad market, not the S&P 500 (T-306: daily ρ 0.9785 after 1993).
- **Cash leg:** French daily RF.
- **Fees, financing and haircuts accrue by calendar days.** 1927–1951 had six-day weeks (~294 bars a
  year), so per-bar accrual would over-charge by ~17 % (T-399 R.9).
- **Contributions** on the first trading day of each January; the account rebalances to target on the
  same day.
- **Trading cost:** 0.51 bp per traded dollar on rebalance days only, located by a positional
  year-change mask (the T-399 fix). The account never sells to cash.

| Arm | Construction | Engine |
|---|---|---|
| **A0 — VOO / total market (the bar)** | Equity gross − 0.03 %/yr [R: VOO ER, verify]. | daily and monthly (must agree, §4.9) |
| **A1 — the Schwab robo at the owner's profile** | Weights from O1. Intl equity, REITs and fundamental-index equity map to the US equity leg ("US-only proxy"; §4.4 explains why). Bonds use the ten-year TR leg. Gold uses the T-306 LBMA/GC leg from 1968; before 1968 its weight is spread pro rata over the other legs (labelled). Cash earns the bill rate − 0.30 %/yr (the SWGXX-linked sweep; bill-rate sensitivity reported). Blended ETF ER from the owner's funds (default 0.15 %/yr [R]). Monthly rebalance. Without O1, **A1-agg** (94/0/6) and **A1-mod** (45/30/5/20) both run. | monthly |
| **A2 — target-date fund proxy** (Vanguard Target Retirement 2065-class) | Equity 90 % for years 1–15, then linear to 50 % at year 40 [R: Vanguard's published glide; verify from the prospectus at freeze]. The remainder is the ten-year TR leg. The fund's ~40 % international equity maps to US equity (labelled). ER 0.08 % [R]. Monthly rebalance. | monthly |
| **A3 — 85/15 VOO/MTUM** | 85 % A0 leg + 15 % momentum leg, annual rebalance at 5 bp. **Momentum leg:** French **monthly** `BIG HiPRIOR` (2×3 ME×Prior 12-2, value-weighted, monthly rebalanced), 1927-01 → 2013-04, less **50 % of its alpha vs Mkt over that span as a constant shift** (the B-9 convention), less 0.15 % ER [R]. From 2013-05: actual MTUM adjusted close. Not the daily-constructed French file (it rebalances daily; §5). | monthly |
| **A4 — lifecycle, cap 2×** | Each January after the contribution: `L = clip((W + PV)/W, 1, 2)`. PV = scheduled future contributions at 1 % real (T-396). Hold `w_SSO = L − 1`, `w_VOO = 2 − L` and let them drift until next January. **SSO synthetic, daily:** `2·r_gross − (f + s)·d/360 − ER_SSO·d/365.25` (d = calendar days). f = French RF before 1954, FRED DTB3 1954-01 → 2018-04-02, SOFR from 2018-04-03 (B-5's base). **s = 57 bp** (B-5 measured, CI [18, 96]); ER 0.89 %. Before 2006-06 the fund did not exist (labelled synthetic). | daily |
| **A5 — lifecycle, cap 1.5×** | As A4 with cap 1.5. | daily |
| **A6 — static 1.25× (reference form)** | `w_SSO = 0.25`, `w_VOO = 0.75`, reset each January. T-396 §2d: same expected gain as A4 with about half the dispersion against 1×. | daily |
| **Vehicle sensitivity V2 (A4–A6)** | UPRO blend: `w_UPRO = (L − 1)/2`; UPRO = `3·r_gross − 2·(f + s_U)·d/360 − ER_U·d/365.25`; s_U = 56 bp [35, 81]; ER 0.90 % (B-5; verify; issuer may now say 0.91 %). | daily |

This is the T-399-corrected cost model in its blended form (T-399's labelled sensitivity S1), made
primary here because each arm *is* a blend. Its direction is known beforehand: it is cheaper for low
leverage than T-315's whole-balance fee model. It is stated, not chosen after seeing a result.

### 4.3 The owner's schedule

- **S1 (primary), real 2026 dollars:** B0 per O3. $7,500 in January of year 1. **$0 in years 2–4**
  (school, O4; a Roth contribution needs earned income). $7,500 each January in years 5–40. Total
  contributed $277,500. Terminal value at the end of year 40.
  - PV at t = 0 of the contributions still to come (years 5–40) at 1 % real: **$219.2k**. After the
    year-1 contribution the account ($17.5k at B0 = $10k) is 8.0 % of that, inside the records'
    "5–10 %"; at the first reset the rule wants (17.5 + 219.2)/17.5 ≈ 13.5× and the cap binds.
- **Indexing.** Contributions are indexed to CPI: FRED CPIAUCNS from 1913, Shiller CPI 1871–1912. In
  bootstrap paths they are indexed to the path's own drawn CPI. The IRA limit moves in $500 steps with
  inflation, so a constant real $7,500 is the honest approximation.
- **Reported sensitivities** (same arms; not trials; labelled):
  1. no school pause;
  2. B0 = $20,000;
  3. household PV for A4/A5 only: add $5,000 a year in years 5–40 to PV (the extra capacity, assumed
     to sit in a separate 1× account).

### 4.4 Belief rows

- **Equity premium rows.** h ∈ {0, −1, −2, −3} pp/yr is subtracted from the **arithmetic** equity
  return by calendar time. It applies to every equity leg, including the momentum leg, and leaves
  cash, bonds and gold unchanged. The realized arithmetic excess on L1 is about 7.75 % (T-396, 1926–2025),
  so the rows read ≈ 7.75 / 6.75 / 5.75 / 4.75 %.
- **Parameter-uncertainty row** (reported beside h = 0 and h = −2). Each bootstrap path draws its own
  δ ~ N(0, SE), with SE the Newey–West standard error of the L1 mean (≈ 1.83 pp, T-396). The path uses
  h + δ. This shows what not knowing the mean to ±2 pp adds; the plain bootstrap treats the realized
  mean as known.
- **Tilt rows (A3 only):** the momentum alpha kept at 50 % (primary), 100 % and 0 %. At 0 %, A3 is
  VOO + MTUM fee + rebalance cost.
- **Not adjusted, and stated.**
  - Bond history: 1940–1981 rising yields penalize the bond-holding arms (A1, A2); 1982–2020 falling
    yields flatter them.
  - The US-vs-world question. A1 and A2 use a US-only equity proxy, so they differ from A0 only in
    equity share, cash, glide and fees. Whether foreign stocks beat US stocks over the next 40 years is
    a separate belief. The study reports a JST descriptive table (§4.5, L3) of US vs GDP-weighted
    world-ex-US 40-year relative returns since 1900, so the owner can see its historical range. No
    test of it can reach significance.
- **Context the owner may use to pick a row** (context, not a signal): Shiller's CAPE reads 39.4 for
  2026-11 in the file read today. High valuations have historically preceded lower long-horizon
  returns. That argues the lower rows deserve weight; it does not say which one.

### 4.5 Data layers (all free; md5 pinned at freeze; read-only for repo files)

| Layer | Content | Span | Used for |
|---|---|---|---|
| **L1 (daily)** | French `F-F_Research_Data_Factors_daily` (Mkt-RF, RF); FRED DTB3, SOFR (API) | 1926-07-01 → 2026-09-30 | A0, A4–A6 |
| **L1m (monthly)** | Equity and RF = the L1 daily series compounded to calendar months (so A0 is the same object in both engines); French monthly `6_Portfolios_ME_Prior_12_2`; Shiller monthly bond TR (ten-year, from GS10); T-306 gold (1968+); actual MTUM / VOO adjusted close (yfinance snapshot). The French monthly factor file is used only as a check | 1926-07 → 2026-09 (momentum 1927-01+) | A0–A3 |
| **L2 (monthly, extension)** | Shiller `ie_data.xls`: S&P composite P, D, CPI, GS10, monthly bond TR. Cash = JST USA annual bill rate, pro rata by month (labelled) | 1871-01 → 1926-06, spliced to L1m at 1926-07 | Cohort table only: A0, A1, A2. **No levered arm**: Shiller's P is a monthly average of daily closes, which understates σ and adds autocorrelation, so it would understate the variance drag |
| **L3 (annual, international)** | JST Macrohistory R6: `eq_tr`, `bond_tr`, `bill_rate`, `cpi`, `gdp`, `xrusd`; 16 countries with equity and bills (CAN and IRL carry neither) | each country's first full year → 2020 | A0-analog (1× own market), A1m-analog (45/30/25 own equity/bonds/bills), A4–A6 at annual reset. Local real terms. The annual-reset gap is measured on US L1 cohorts (annual-reset vs daily-reset on the same years) and **printed beside, not applied**. Reported at h = 0 only: the non-US markets are themselves realized lower-premium worlds. US-vs-world table in USD |
| **Cross-checks** | T-306 `data/research/substrate_multidecade/` (read-only); B-5 inputs (`data/research/b5/inputs/`, H.15 SDMX and SOFR); actual SSO/UPRO adjusted close | — | Reproduction and tracking checks, §4.9 |

### 4.6 Forty-year windows: how precision is kept honest

- **Historical cohorts** (descriptive):
  - L1/L1m: January starts 1927 → 1986, which is 60 cohorts.
  - L2: adds starts 1871 → 1926.
  - L3: every country-start with 40 years of data.
  - Every cohort table prints its **effective number of independent windows**: span ÷ 40, i.e. ≈ 2.5
    for L1 and ≈ 3.9 for L1+L2. **A share of overlapping cohorts is never quoted as a probability**
    (T-318's lesson: 100 % of windows won while the CI straddled zero).
- **Stationary block bootstrap** (Politis–Romano) over the 1,203 L1 months:
  - mean block length **60 months** (primary), with 12 and 120 reported;
  - 10,000 paths of 480 months, with a fixed seed;
  - each drawn month carries its full daily vector (equity, RF, financing base) for the daily arms, and
    its monthly bond, momentum, gold and CPI returns for the monthly arms (a drawn pre-1968 month has
    no gold, and A1's gold weight is spread pro rata for that month, as in the cohorts);
  - **the same draws feed every arm** (paired);
  - the generator is study code, reviewed by execution before freeze.
  - `MetricsEngine.bootstrap_distribution` is a fixed-length moving-block bootstrap; it is used for
    the Sortino CIs (§4.7), not for path generation.
- **What the bootstrap is and is not.** It models sequence risk *given* the century's realized mean.
  It is not evidence about the next forty years' mean. That uncertainty lives in the belief rows and the
  parameter-uncertainty row. **No bootstrap percentile is quoted without the belief row it was computed
  under.**
- **Terminal-wealth intervals over decades are numerically degenerate** (T-311). Every gate statistic
  is therefore a Δ log growth rate or a Δ log terminal wealth, never a Δ dollar.

### 4.7 Metrics (per arm × belief row × layer)

| # | Metric | Notes |
|---|---|---|
| M1 / M2 | Median and mean real terminal wealth | Bootstrap; Monte Carlo SE printed |
| M3 | P(W_arm < W_A0) | Paired draws; also the share of historical cohorts, labelled with the effective N |
| M4 | 5th / 50th / 95th percentile of W_arm ÷ W_A0 | |
| M5 | E[log W_T]; certainty equivalent at relative risk aversion 2 | The decision rule's input (§4.1); γ = 2 is half-Kelly |
| M6 | Worst historical cohort: start year, W_arm, W_A0, shortfall in $ and in years of contributions | L1+L2 and per country in L3 |
| M7 | Maximum real-dollar drawdown: historical worst (date, cohort, year of cohort); bootstrap median and 95th percentile | The owner asked for "worst path in dollars" |
| M8 | Maximum relative drawdown vs A0 (regret) and time to recover | T-318 convention |
| M9 | P(balance < cumulative contributions at year 20) | The ruin-type event, defined now (T-396 §4) |
| M10 | Sortino ratio, target 0, on **monthly** returns annualized with **12 periods**, never 252. A0, A1, A3 and A6 on the full-sample lump-sum path, with a block-bootstrap CI (`MetricsEngine.bootstrap_distribution`; block n^(1/3) and 12 months, both printed). A2, A4 and A5 exist only inside a cohort: their per-cohort Sortino distribution, no CI, labelled | `[NN-SHARPE-CI]`; the periods trap (×4.58) is on record |
| M11 | A4/A5: years at the cap, and leverage by cohort year | |

### 4.8 The program's gate — computed, reported, never deciding

- **Static arms** (A1, A3, A6, and V2's 1.25×), full-sample lump sum on L1 / L1m:
  - Statistic: Δ annualized log growth vs A0, block bootstrap.
  - "Clears undeflated": ci_low > 0.
  - "Clears deflated": t ≥ E[max_N] at the ruled N_eff (≈ 2.96 at 372).
  - For A1 the claim is the reverse, A0 − A1 > 0: "the plain fund beats the robo".
- **Cohort-defined arms** (A2's glide and the lifecycle arms A4, A5 exist only on a cohort clock): the
  mean over the 60 L1 cohorts of Δ log terminal wealth vs A0. Its SE comes from re-running the cohort
  table on 1,000 stationary block resamples of the months. For A2 the claim is A0 − A2 > 0.
- **Pre-run pass probabilities** (my estimates, from T-396 §4, T-399 and §2.1):

| Claim | Expected t | P(clears undeflated) | P(clears deflated, 2.96) | What a pass would mean |
|---|---|---|---|---|
| A0 beats A1-mod (moderate robo) | 2.1 (58 yr) – 2.8 (99.5 yr) | ≈ 85 % | **30–50 %** | Only that equities beat bonds and cash over a century, which is already known |
| A0 beats A1-agg (US-only proxy) | ≈ 3.0 on 99.5 yr before the fee gap; 3.7–4.7 with it | > 90 % | **60–90 %** | Only that a 6 % cash sleeve and higher fees cost money, both certain-sign; with the robo's real international share t ≈ 0.5–0.8 and P ≈ 0 |
| A0 beats A2 (target-date) | ≈ 1.5 per cohort, ≈ 2–2.5 over the century | ≈ 60 % | 10–20 % | The equity premium again |
| A3 beats A0 (50 % tilt kept) | ≈ 1.9–2.0 (B-9 1963+ boot z 1.90) | ≈ 50 % | **2–5 %** | At 100 % kept a pass is plausible, but it would certify only the pre-1993 momentum premium (Jegadeesh–Titman 1993) |
| A6 beats A0 (SSO blend) | ≈ 1.76 (T-399 S1, ~99 yr) | ≈ 25 % | **≈ 0** (ceiling 2.63) | — |
| A6 beats A0 (UPRO blend) | ≈ 2.0 (T-396) | ≈ 50 % | **≈ 0** | — |
| A4 / A5 beat A0 | ≈ 0.9–1.1 over the century (T-396) | < 5 % | **0 by construction** | — |

- **At realistic sizes the deflated bar is out of reach.** MinBTL at t = 2.96:
  - SSO-blend 1.25× needs ≈ 367 years and UPRO-blend 1.25× ≈ 275 (T-396 §4, 1968 moments);
  - one 40-year cohort's expected t is 0.56–0.68.
- **Every pass the gate can produce here certifies the equity premium or a certain-sign cost, not a
  choice.**

### 4.9 Pre-run checks (fail closed, `[NN-FAIL-CLOSED]`; any failure HALTS and nothing is quoted)

1. **Pins.** md5 of every input matches the freeze manifest. Any French `-99.99` / `-999` sentinel, any
   NaN, any non-monotone date, or any calendar hole > 15 days (`core/calendar_guard.py`) halts the run.
2. **A0 identity.** The daily and monthly engines' A0 terminal values agree to 1e-9 relative on every
   cohort. Both read the same daily series, and buy-and-hold with January contributions is
   engine-invariant. Separately, the French monthly factor file is compared with the compounded daily
   series; the gap is reported, and the run halts if it exceeds 0.10 %/yr in any decade.
3. **Reproduction.** French daily 1926-07 → 1993-01 against the T-306 equity leg: correlation ≥ 0.999
   and level ratio drift ≤ 0.5 %. The CRSP vintages differ, so small revisions are expected and reported.
4. **Vehicle tracking.** Synthetic SSO / UPRO vs actual adjusted close since inception: the annualized
   tracking difference must sit inside B-5's spread CI ([18, 96] / [35, 81] bp). Otherwise HALT and
   re-price; the vehicle is never silently swapped.
5. **Schedule.** Contributions sum to $277,500 real under S1. PV at t = 0 is $219.2k ± $0.1k at B0 =
   $10k. A unit test plants a 3-year toy schedule.
6. **Guards.** Every std/var guard uses `std < 1e-12 or not np.isfinite`. The <4-observation zero-return
   path of `MetricsEngine.bootstrap_distribution` must be unreachable; the study asserts its length
   before calling it. Sortino is called with `periods=12` on monthly data (a lock test plants a series
   whose 252- and 12-period values differ).
7. **Smoke the edges.** The first 12 months of each layer (1926-07, 1871-01, each JST country's first
   year) and the last 12 are hand-checked before the full run.
8. **Determinism ×2.** The results JSON is md5-identical over two runs.
9. **Census block** in the output: cohorts per layer; paths; block lengths; per-arm rebalance count;
   financing-base source shares by date; years at the cap; months mapped to each proxy leg; count of
   legs renormalized pre-1968.

### 4.10 Trial count (a proposal for the director's ruling; this draft states none)

| Unit | Would add | Basis |
|---|---|---|
| A1 at the owner's profile (or A1-agg) | 1 | a configuration that could be quoted against the bar |
| A1-mod, if run in addition to A1 | 1 | the same, raw |
| A2 | 1 | |
| A3 | 1 | duplicates T-320 / B-9 on the same French data; counted anyway |
| A4, A5, A6 on SSO | 3 | |
| A4, A5, A6 on UPRO (V2) | 0 under the T-315 sensitivity convention; 3 if counted raw | the director's ruling |
| L3 (JST) — four arm analogs on a new substrate | 0 on the US substrate; 4 raw | the director's ruling |
| Belief rows, tilt rows, parameter-uncertainty row, block lengths, schedule sensitivities | 0 | reported sensitivities of the same configurations (T-315 convention) |

- **Range:** 7 (primary only) to 14 (everything raw).
- **Effect on the gate:** at 14, N_eff 372 → ~386 and E[max] 2.96 → ~2.97. That is immaterial to every
  pass probability above, so my recommendation is to **count raw**.

### 4.11 Pre-stated expectations (so the result cannot be rationalized)

These are my priors from T-396, T-399 and §2.1, h = 0 unless stated.

| # | Expectation |
|---|---|
| E1 | A1-mod trails A0 in median terminal wealth in every belief row. P(A1-mod > A0) ≤ 25 % at h = 0 and ≤ 35 % at h = −3. |
| E2 | A1-agg (US-only proxy) trails A0 by 0.2–0.5 %/yr. P(A1-agg > A0) 25–45 %. |
| E3 | A2 trails A0 in every row; median shortfall 10–30 % at h = 0 and smaller at −3. |
| E4 | A3's median is within ±8 % of A0 (50 % tilt kept); P(A3 > A0) 55–70 %. |
| E5 | A4's median ratio to A0 is about +15–25 % at h = 0 and −5 % to +5 % at −2. P(below A0) 25–35 % / 45–55 %. The worst cohorts are those that meet 1929–32, 1973–74 or 2008 in cohort years 8–20, at 30–50 % behind. |
| E6 | A6 has about A4's mean with about half its dispersion against A0. On the decision rule at γ = 2, A6 or A0 beats A4 in every row. |
| E7 | In L3, the leverage arms trail 1× in the median cohort in a material share of non-US markets (expected: Japan, Italy, Germany, Belgium, Portugal). The ranking 1× > balanced holds in most markets but not all. |
| E8 | The gate certifies nothing that moves money toward risk. Only the A0-beats-A1 contrasts have a real chance of a deflated pass: A1-mod would certify the equity premium, and A1-agg (US-only proxy) would certify that cash and fees cost money. Both are already known. |

If the run contradicts an expectation, the report says so in its first paragraph.

### 4.12 What the output may and may not be used for

**May:** the owner's decision table; a corrected `real_money_decision_package_2026_09.md` menu (director,
propose-first); the advisor surface.

**May not:**
- be quoted as an edge, a proof, or a "validated" allocation;
- promote anything;
- set a deployment date;
- move money (that is the owner's act);
- justify a leverage book on paper or live without its own propose-first unit.

## 5. Census of the free data actually reachable (read-only probes, 2026-11-19)

- **Method.** Generic User-Agent `ArchonDEX-research/1.0`. Downloads went to their own empty
  directories under the session scratchpad. Each file was opened with `python -I` from a separate
  script directory. Spans, columns and row counts only; no returns or statistics.

| Source | Status today | Span read | Note | md5 of today's file |
|---|---|---|---|---|
| French `F-F_Research_Data_Factors_daily_CSV.zip` | 200 | 1926-07-01 → 2026-09-30, 26,338 rows; CRSP 202609 | RF: Ibbotson to 2024-05, ICE BofA 1-month bill after | `98fad1a66fe8c9e792fcd013b979b962` |
| French `6_Portfolios_ME_Prior_12_2_Daily_CSV.zip` | 200 | 1926-11-03 → 2026-09-30; VW and EW sections | **Constructed daily** (prior return −250 to −21 days), so it rebalances daily and is not MTUM-like. A3 uses the monthly file. Missing = −99.99 / −999 | `99fa07c708296719bcf902d94017874a` |
| French `6_Portfolios_ME_Prior_12_2_CSV.zip` (monthly) | on disk (B-9 inputs) | B-9 used 1963+ / 2000+ | Monthly rebalanced; the A3 proxy | B-9 manifest `471e5887…` |
| French `F-F_Research_Data_Factors_CSV.zip` (monthly) | on disk (B-9) | | | `a2867511…` |
| French `Developed_3_Factors_CSV.zip`; `Developed_ex_US_3_Factors_CSV.zip` | 200 / 200 (HEAD) | 1990-07 → (Bloomberg 202609) | Less than one 40-year window; descriptive only | `0186d585db22d30058635c66352f0b4f` (Developed) |
| Shiller `ie_data.xls` (shillerdata.com via img1.wsimg.com) | 200 | **1871-01 → 2026-11**; dividends to 2026-09 | Columns P, D, E, CPI, GS10, real TR price, monthly total bond returns, CAPE. **The repo copy `data/macro/shiller_ie_data.csv` lacks CPI and GS10 and ends 2024-09, so it is insufficient.** Recent CPI months are provisional | `2fd4f34013378aeb1a9b96c794a3346c` |
| JST Macrohistory R6 (`macrohistory.net`) | 200 | 1870 → **2020**, annual, 18 countries | 16 have `eq_tr` and `bill_rate` (CAN and IRL have neither); CHE, ESP and NLD equity from 1900; JPN from 1886. Ends 2020. Citation required (Jordà, Knoll, Kuvshinov, Schularick, Taylor 2019) | `76884a335991ece55366255bd629d312` |
| FRED keyless CSV (`fredgraph.csv`) | **FAILED** (HTTP/2 INTERNAL_ERROR) | — | Same outage as recorded 11-19 | — |
| FRED API (key from `.env`, never printed) | OK | CPIAUCNS 1913-01 → 2026-10; TB3MS 1934-01 →; DTB3 1954-01-04 → 2026-11-18; GS10 1953-04 →; DGS10 1962-01-02 →; DFII10 2003-01 →; SOFR 2018-04-03 → | | — |
| yfinance 1.2.0 (monthly census) | OK | VOO 2010-09; VTI 2001-06; MTUM 2013-04; SSO 2006-06; UPRO 2009-06; VLXVX 2017-07; VFFVX 2010-08; VTTSX 2012-01; SWYNX 2016-08; SCHB/SCHF 2009-11; SCHE 2010-01; FNDX 2013-08; SGOV 2020-06 | Snapshot; pin at freeze. Actual target-date NAVs cover less than one 40-year window, so they check the A2 proxy only | — |
| Schwab Intelligent Portfolios brochure (2026-10-15) | 200 | 18 pages | **Cash 6–30 % "depending on the investment strategy"** (p.13). No advisory fee (pp.8–9). Cash above 10 % earns Schwab more (p.9). Asset classes: stocks, fixed income, real estate, commodities; cap-weighted and fundamental ETFs (pp.7, 9). **No per-profile weights** | `c7e84a84a6ee19dab600c5d8827e256d` |
| Schwab sweep-rate page | 200 | — | Rate = SWGXX seven-day yield (with waivers); **3.51 % APY effective 2026-11-02** | — |
| Vanguard target-date page | 200 | — | Glide-path numbers are rendered by script and could not be read. **Verify the glide from the prospectus before freeze** | — |
| Repo, read-only | present | T-306 equity 1926-07-01 → 2026-04-17 (FF → SPY splice 1993-02-01), bond 1962 →, gold 1968 → 2025-12-31, cash 1926 → 2026-05-29; B-5 H.15 SDMX + SOFR; B-9 FF + yfinance snapshots; `data/macro/` DGS10, DGS3MO, CPIAUCSL | | provenance.json |

**Not reachable for free:** the robo's per-profile model weights and their history; daily international
equity before 1990; any option or LEAPS price history (T-396 §3); the owner's own robo performance
(the owner can export it, and that would be the definitive robo series from enrollment on).

**Disk.** The host shows ~4 GiB free. The Phase-2 run should keep inputs (~5 MB) and outputs (one JSON,
tables) small and write under `data/research/t409/`, never `data/processed/`.

## 6. Where the record contradicts itself (for the director)

1. **"Stay in the robo — Dominated"** (`docs/State/real_money_decision_package_2026_09.md:32`, "Beaten
   on every axis (T-311)").
   - T-311 tested the **trend sleeve** against the `schwab_like` proxy: Sortino and MaxDD
     CI-significant; wealth on point only, $1.96M vs $1.35M, the CI "leaning positive"
     (`deep_reverify_sleeve_t311_2026_07_27.md:80-81,100-102`).
   - Buy-hold vs the robo never had an interval.
   - The proxy is one moderate profile. The brochure's 6–30 % cash range means an aggressive profile
     is a different object.
   - "Dominated" holds on point for a moderate robo. It is unestablished for an aggressive one.
2. **The package's default row** says 1× is "wealth-maximizing under ANY forward-ERP haircut (T-315)"
   (`:24`). This is superseded by T-399 ([NN-SUPERSEDED]): on point, 1× trails every static arm at
   1.35× and above at the realized premium. The row was written 07-27 and not updated.
3. **The fresh-eyes audit's "≈ 4 pp/yr" robo cost** (§2A) converts T-287's $929K vs $495K. That
   conversion holds only if the owner's robo resembles the 45 %-equity proxy, which nobody has checked.
4. **The fresh-eyes audit §2B** quotes "the 2×→1× glide at $86.5M against $35.0M" and "Kelly 2.20 /
   1.49 / 1.13". Both are withdrawn by T-399: static 2× $130.7M and 1.75× $98.5M finish ahead of the
   glide, and Kelly is 2.55 / 1.83 / 1.48 on the arithmetic mean.
5. **Contribution size differs across records.**
   - T-396 models $5,000 a year.
   - `advisor_surface.md` says the Roth is maxed at "~$7,000/yr" plus $5,000 of extra capacity.
   - The 2026–2027 limit is $7,500 (T-402 §4).
   - T-396 therefore under-states the Roth stream by a third and is neither the Roth-only nor the
     household figure. This draft uses $7,500.
6. **`GOAL.md:19` ties the real money to *this system's* paper validation.** A move to a plain index
   fund does not deploy the system. The package (`:24`, "machine-executed") and the fresh-eyes audit
   ("manually, decoupled from the fleet") read the rule differently. Owner ruling.
7. **`MetricsEngine.bootstrap_distribution`** (`core/metrics_engine.py:864-972`) does not match its
   description.
   - Its docstring says "stationary block-bootstrap"; it implements a fixed-length moving-block
     bootstrap.
   - Its "Politis–White" auto block is the n^(1/3) rule of thumb, while `CLAUDE.md` `[NN-SHARPE-CI]`
     names Politis–White automatic selection.
   - Below 4 observations it returns all-zero results, a fail-open path under `[NN-FAIL-CLOSED]`.
   - Referee code: reported, not touched.
8. **The repo's Shiller copy** (`data/macro/shiller_ie_data.csv`) has no CPI or GS10 and stops at
   2024-09. Anything that needs real returns or the long bond from it cannot use that copy.
9. **Smaller, consistent with the record but worth one line.** The processed-SPY pre-seam DRIP error
   sits inside T-306's post-1993 equity leg, which T-315/T-399 and T-396 used. It shifts levels for 1×
   and the levered arms alike. This draft avoids it by using French throughout.

## 7. Before freeze (checklist)

- [ ] Owner inputs O1–O6, or explicit "use defaults".
- [ ] Verify from issuers: VOO, MTUM, SSO, UPRO and the target-date ERs; Vanguard's glide path (prospectus).
- [ ] The director rules: the trial count (§4.10); the h grid; γ = 2; the default loss bound; whether
      A1-mod runs if O1 arrives.
- [ ] Study code written and reviewed by execution (stationary bootstrap, synthetic vehicles, schedule,
      checks 1–9), including the lock tests.
- [ ] Freeze manifest: input md5s, code hash, this file's SHA-256 in the ledger row.
- [ ] Only then run once.

## References

- T-396 design note (`docs/Sources/design_note_lifecycle_leverage_t396_2026-11-14.md`, on this branch).
- T-315 / T-399: `docs/Audit/static_leverage_t315_2026_07_27.md`.
- T-283, T-283b, T-283c, T-287: `docs/Audit/accumulation_model_verdict_t283_2026_07_06.md`,
  `accumulation_levered_t283b_2026_07_06.md`, `accumulation_t284_reconcile_t283c_2026_07_06.md`,
  `dividend_reconcile_verdict_t287_2026_07_07.md`.
- T-311: `docs/Audit/deep_reverify_sleeve_t311_2026_07_27.md`.
- T-318 / T-320: `docs/Audit/tilt_decision_verdicts_t318_t320_2026_07_27.md`.
- B-9 / T-380: `docs/Audit/b9_combo_tilts_verdict_2026-11-11.md`.
- B-5 / T-382: `docs/Audit/b5_levered_diversified_verdict_2026-11-11.md`.
- T-400: `docs/Sources/design_study_two_account_household_t400_2026-11-14.md`.
- T-402: `docs/Sources/design_study_real_money_venue_t402_2026-11-17.md`.
- Fresh-eyes and salvage audits: `docs/Audit/fresh_eyes_and_salvage_audits_2026-11-14.md`.
- Jordà, Knoll, Kuvshinov, Schularick & Taylor (2019), "The Rate of Return on Everything, 1870–2015",
  QJE (the JST data).
- Shiller, *Irrational Exuberance* data (`ie_data.xls`).
- Fama–French data library (K. French).
- Ayres & Nalebuff (2010), *Lifecycle Investing* (the λ rule's source, as summarized in T-396).
