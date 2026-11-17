---
task_id: T-400
title: The two-account household as one portfolio
date: 2026-11-14
type: DESIGN STUDY (reading, arithmetic, public-web checks)
status: PROPOSAL. Nothing built or run. N_trials 0.
---

# T-400 — one household, two (or three) accounts, one controller

**Summary.** Running a Roth and a taxable account as one portfolio is worth doing, for dull reasons and
less money than the question hopes. The sign-certain gains are under ~$250/yr at today's size, about
0.1–0.6 %/yr of the household at $50–100k and 0.1–0.4 %/yr at $500k: a tenth to a half of the 1 %/yr
alpha the program hunts, with a known sign. The deployed 85/15 book is two tax-efficient equity funds, so
asset location is worth nothing until a tax-inefficient leg exists; that leg goes in the Roth. The
taxable account should be the boring one: broad equity bought with new money, no gain sold to rebalance,
losses harvested once the owner is in a high bracket. The largest certain item is an HSA, if
the plan qualifies. Two findings correct the record: futures can sit inside a Roth at some brokers, so
"futures belong in taxable" (T-281, T-294b) is wrong on tax; and T-294b's "tax consumed the edge" reverses
at school brackets but is unusable at this size. One mistake costs more than a year of benefit: a loss
sold in taxable while the Roth buys the same thing.

**I am not a tax adviser.** Every line marked † needs a professional before anyone acts on it.
**[W n]** = read on the web today, source n. **[R]** = recalled, unchecked. **[REPO]** = repo.

## 0. The record, checked

- Investor facts: `docs/State/advisor_surface.md`. It says "school" ("law school" is in no doc), labels
  the $10k balance an assumption, and gives no age. Robo: `docs/State/GOAL.md:19`, silent on whether that
  account is the Roth.
- T-294b's rate: ST 24 % / LT 15 % → blended **18.6 %** (high: 26.8 %); no NIIT, no state
  (`docs/Audit/taxable_futures_vehicle_t294b_2026_07_08.md:44-45`). T-141 used 34.95 % short-term: the
  repo's config assumes Illinois.
- Wash guard: `engines/engine_b_risk/cross_account_wash_guard.py`, single-account in practice (ledger
  T-358). `LotEvent.qty` is an `int`: fractional buys and DRIPs cannot be recorded.
- "household": zero docs, confirmed. N_eff ≈ 371: ledger T-391 (unmerged). The three-classes audit:
  **not found**.

## 1. Asset location

Assumed throughout (mine): taxable share 25 % at $20k, 35 % at $50k, 40 % above.

| Leg | Home | Why |
|---|---|---|
| Broad equity core, bought and held | **Taxable** (and Roth overflow) | qualified dividends only; gains deferred; the only leg with harvestable lots |
| Momentum satellite | Roth | the leg that is trimmed and topped up; selling is free there |
| Trend overlay (fund), levered fund, options | Roth | ordinary-income distributions; every rebalance is a realization |
| Futures | **Roth if the broker permits**, else taxable | §2 |
| Odd-lot tenders (T-395) | Roth | every gain is short-term; two accounts may not mean two allotments (offers test beneficial ownership [R]) |

Value: for 85 % VOO / 15 % MTUM, about **zero**. Location pays the tax-inefficient sleeve's distribution
× the tax rate. With a 15 % sleeve distributing 4 %/yr as ordinary income (my assumption): 0.07 %/yr at a
12 % bracket, 0.14–0.19 % at 24–32 %; Vanguard's range is 5–30 bp [W 9]. Dollars at the four sizes:
**≤ $15, $95, $190, $960**, and $0 until such a sleeve is adopted.

## 2. The school window (about three years)

2026, single [W 1, 2]: standard deduction $16,100; 10 % to $12,400, 12 % to $50,400; long-term gains taxed
0 % while taxable income ≤ $49,450. 2027 [W 3, 4]: $16,600; $12,800 / $52,025; $51,050. Total income to
**$65,550 (2026) / $67,650 (2027)** leaves long-term gains at 0 % federal.†

- **Tax-gain harvesting** (sell a lot held > 1 year [W 5], rebuy at once; wash sales bind losses only).
  Value = gain × the later rate (15 %; 18.8 % with NIIT above $200k MAGI [W 6]). There is almost nothing
  to harvest: the taxable account does not exist yet and gets little during school. $1–3k of gain is worth
  $150–450 **once**, and nothing if the lot is never sold. It fails outright under the **kiddie tax** —
  under 24 at year-end, full-time student, earned income not over half of support: unearned income above
  $2,700 is taxed at the parents' rate [W 7; R]. It also costs state tax now, raises AGI for aid and
  insurance subsidies [R], and breaks if a summer job overshoots.†
- **Never harvest gains and losses in the same year**: they net. A loss in a zero-tax year is worth more
  carried to a 24–35 % year ($3,000/yr against ordinary income, the rest carried forward [W 5]).†
- **Ordering.** HSA and Roth before taxable, always. A Roth contribution needs taxable compensation;
  taxable non-tuition stipends count [W 8]; a no-income year allows none.† "Low-bracket Roth conversions"
  has no object: no pre-tax balance is on record.
- **§1256 recomputed.** T-294b's drag is ≈ 0.098 pp per point of blended rate (1.81 at 18.6; 2.66 at
  26.8); scaling it linearly is my approximation. The 60/40 rule [R; REPO] at this investor's brackets:

| Bracket (ST / LT) | Blended | Drag | Taxable futures 2× vs Roth buy-hold 8.13 % |
|---|---|---|---|
| School 12 / 0 | 4.8 % | −0.47 %/yr | **+0.79 %/yr** |
| 24 / 15 (T-294b base) | 18.6 % | −1.81 | −0.55 |
| 32 / 15 | 21.8 % | −2.14 | −0.88 |
| 35 / 15 + NIIT | 26.8 % | −2.63 | −1.37 |

  The verdict **reverses in the window and worsens after it**, and is still unusable: one micro S&P
  contract is $5 × index, about $34–36k [W 15; REPO], against a taxable balance of $5–15k; the window is
  three years; the gated-2× config failed at depth (T-312); state tax is omitted. And the comparison was
  mis-framed: **futures are permitted in a Roth** — IBKR at about twice the overnight margin, Schwab with
  $25k and 125 % of initial margin [W 12; excerpts only, both pages refused a direct read] — where the tax
  is zero at every bracket. An IRA margin call cannot be met beyond the contribution limit [R].

## 3. After school (24–35 % brackets)

- **Loss harvesting.** Literature: 1.08 %/yr, 0.82 % under the wash-sale rule, for a 500-stock direct
  index with monthly contributions at 35 % / 15 % rates [W 10]; Vanguard's press range is 0.5–4 %, about
  1 % typical [W 11, secondary]. Those assume short-term gains to offset. This investor never sells, so the
  usable amount is **$3,000/yr × the marginal rate = $720–1,050/yr, a dollar ceiling at any size**.† It
  decays because old lots rise out of reach; only new contributions make harvestable lots. It is deferral
  unless the lot is never sold (step-up at death, current law [R]). The repo's 0.1–0.3 %/yr (T-317) is the
  right order.
- **Direct indexing** generates more loss than $3,000/yr can absorb; pointless until a taxable sleeve
  produces gains.
- **Across accounts.** Rev. Rul. 2008-5, read today [W 13]: "The loss on the Sale of stock is disallowed
  under § 1091. A's basis in the individual retirement account or Roth IRA is not increased by virtue of
  § 1091(d)." The loss is gone, not deferred. HSAs, a spouse and a 401(k) are not addressed; treat them as
  covered.†
- **What the guard must enforce:** (1) one lot ledger over every household account, including ones the
  system does not trade; (2) 30 days both sides, counting contributions and DRIPs as buys; (3) **class
  segregation** — the Roth never buys a class the taxable account holds or harvests into, which needs a
  third equity class in `config/substantially_identical.json`; (4) fractional quantities; (5) proof it has
  seen a second account's lot (`[NN-FIRST-ARTIFACT]`) before any harvest.

## 4. "Different times, different ways"

- One household target; per-account holdings are derived from it.
- **Roth/HSA: all selling**, monthly, every strategy with turnover.
- **Taxable: buys on contribution days only**, into the most-underweight sleeve. Sells are a loss harvest
  on a threshold, or a December gain harvest decided by a person once the year's income is known.
- Class segregation removes the timing coupling; without it every Roth buy blocks taxable harvests for
  61 days.
- The controller needs: lots (date, fractional quantity, basis, account), holding period, class,
  year-to-date realized gains and losses, the carryforward, an owner-supplied tax profile (status, income,
  state, kiddie-tax status), contribution room, and the broker's cost basis set to specific-lot, or the
  1099-B disagrees with it [R].

## 5. What taxable unlocks, by household size

- **$35k:** margin borrowing ($2,000 minimum [R]); the $25k day-trade rule is being retired [W 14].
  Cheapest trend or leverage: a stacked or levered fund, 0.96–1.37 %/yr per borrowed
  dollar (T-396), in the Roth.
- **$100k:** one micro contract ≈ +0.35× exposure at ~1 bp round trip (T-294b); in the Roth if permitted.
- **$250k:** micros in 14 % steps. Portfolio margin needs $110–125k in the account itself [W 16];
  box-spread financing from $125k (T-315). Roth for the futures; taxable only to borrow.

T-281's triage stands: one family reopens (micro-futures trend, $65k in one account); short legs, levered
vol-targeting and risk parity stay closed. Base rate: the 2021–26 ETF trend sleeve was falsified; DBMF's
Sharpe interval is [−0.18, +1.19]; B-5's trend overlay is "neither opened nor closed"; at N_eff ≈ 371
nothing untimed clears (T-396). Trend and leverage are class (2): the owner's belief.

## 6. Automation

- **Alpaca: yes.** Roth and Traditional IRAs for Trading API users, equities and options; funding is
  dashboard-only; no futures [W 17, updated 2026-07-06].
- **Schwab:** the API trades equities and options, not futures; **IRA coverage unconfirmed** (third-party
  pages only [W 12]); a robo account is not self-directed [R].
- **IBKR:** API; futures in IRAs; IRA-by-API unconfirmed [W 12]. **Tradier:** one login, margin account
  plus Roth (weak source [W 18]).

Manual for good: contributions and their tax year, transfers, the cost-basis election, DRIP off,
margin/futures approvals, payroll HSA elections, the return itself (Forms 8949, 6781).

## 7. What it is worth

School brackets at $20k; 24–32 % after; $/yr.

| Mechanism | $20k | $50k | $100k | $500k | Standing |
|---|---|---|---|---|---|
| HSA before taxable, if eligible ($4,400, 2026 [W 19]) | 0–530 | 1,060–1,410 | same | same | CERTAIN, conditional |
| Asset location | 0–15 | 0–95 | 0–190 | 0–960 | LIKELY; $0 on today's book |
| Rebalance in the Roth | 0 | ~15 | ~35 | ~180 | CERTAIN |
| Gain harvesting (window) | 0–200 | 0–450 once | — | — | CERTAIN if eligible |
| Loss harvesting | ≤ 20, banked | 40–170 | 95–385 | 480–960 | LIKELY |
| Leverage, trend, tenders | — | — | — | — | BELIEF-DEPENDENT / per-event; not summed |
| **Total without HSA** | **0–35** | **55–280** | **130–610** | **660–2,100** | |
| 1 %/yr alpha | 200 | 500 | 1,000 | 5,000 | not evidenced |

Assumed (mine, unmeasured): 1–3 % of the taxable balance harvested a year. Totals exclude the gain-harvest
row at every size (director's correction, 2026-11-14: the $20k total had included it; the summary's
"under ~$250/yr at today's size" is that row plus the rest).

**Risks.** One disallowed $1,500 loss costs $360–480, a year of harvesting at $50–100k. A $2,000 gain
taken short-term costs $340 more than long-term. The 0 % bracket, step-up, 60/40 and the wash-sale
perimeter are recurring legislative targets [R]. This fleet has run silently wrong before (the split,
a two-week outage); a silently wrong tax engine is discovered at filing. Unlocked leverage tempts.

## 8. Build plan

**No code (owner):** (1) settle HDHP status; if eligible, fund and invest the HSA. (2) Answer the questions
below. (3) If a taxable account is opened: a broker where both wrappers trade by API, specific-lot basis,
DRIP off, a broad-equity class the Roth does not buy, contributions only, no sales — most of the table.
(4) Each December of school, with a professional†: harvest gains or not.

**Code, report-only:** a household ledger reading every account; a location and tax-budget report; a
shadow controller.

**Propose-first (Engine B, live path):** guard phase 2 (§3, items 1–5); a contribution router and
Roth-side rebalancer on two paper accounts; the harvest loop only above ~$40k taxable AND a ≥ 22 %
bracket, after the T-317 simulation. Futures or leverage: only on the owner's stated belief, in the Roth,
above ~$100k.

**Owner questions:** age and dependency status; state; filing status; how school is funded (the advisor
memo's standing question); expected income per school year; any existing taxable holdings; whether the
robo account is the Roth.

## Sources (accessed 2026-11-14; "excerpt" = search-result excerpt only)

1. IRS IR-2025-103 (Rev. Proc. 2025-32): irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2026-including-amendments-from-the-one-big-beautiful-bill
2. Secondary: currentfederaltaxdevelopments.com/blog/2025/10/9/2026-inflation-adjustments-for-tax-professionals-revenue-procedure-2025-32-analysis
3. IRS IR-2026-133 (Rev. Proc. 2026-35): irs.gov/newsroom/irs-releases-tax-inflation-adjustments-for-tax-year-2027-taxpayers-continue-to-benefit-from-the-working-families-tax-cuts
4. Secondary: currentfederaltaxdevelopments.com/blog/2026/11/5/2027-inflation-adjusted-tax-provisions-technical-analysis-and-legal-index-for-tax-practitioners
5. IRS Topic 409: irs.gov/taxtopics/tc409
6. IRS Topic 559: irs.gov/taxtopics/tc559
7. IRS Topic 553: irs.gov/taxtopics/tc553
8. Pub. 590-A, excerpt: irs.gov/forms-pubs/revised-2021-publication-590-a
9. Vanguard, excerpt: corporate.vanguard.com/content/dam/corp/research/pdf/revisiting_conventional_wisdom_regarding_asset_location.pdf
10. Chaudhuri-Burnham-Lo 2020, excerpt: rpc.cfainstitute.org/research/financial-analysts-journal/2020/empirical-evaluation-tax-loss-harvesting-alpha
11. Secondary: financial-planning.com/news/vanguard-advisors-alpha-study-cites-tax-loss-harvesting
12. Excerpts: schwab.com/futures/faqs; interactivebrokers.com/en/trading/ira-information.php; blog.traderspost.io/article/thinkorswim-api
13. Rev. Rul. 2008-5, text read: irs.gov/pub/irs-drop/rr-08-05.pdf
14. FINRA Notice 26-10, excerpt: finra.org/sites/default/files/2026-04/Regulatory-Notice-26-10.pdf
15. Excerpt: help.metrotrade.com/kb/micro-e-mini-sp-500-futures-mes-contract-specifications
16. Excerpts: schwab.com/margin/portfolio-margin; ibkb.interactivebrokers.com/article/3560
17. alpaca.markets/blog/alpaca-introduces-individual-retirement-accounts-for-trading-api-users/
18. Third-party, excerpt: rithmic-html-css.pages.dev/broker-faq/tradier-faq/
19. HSA limits, excerpt: plansponsor.com/irs-announces-higher-hsa-limits-updated-health-plan-thresholds-for-2027/
