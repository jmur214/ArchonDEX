---
task_id: T-409
title: DRAFT pre-registration (revision 2) — where should the owner's money sit? A decision study in after-tax household wealth (taxable Schwab robo, VOO, switching and its tax, the robo's loss harvesting, asset location, leverage routes)
date: 2026-11-19
worker: edge-analyst (worktree agent-ac300c3d5f4eba52f)
revision: 2 (2026-11-19). It supersedes revision 1 (commit d0616ae, merged at a31c63a) after the owner's answers. §0 lists what changed and what in revision 1 is now wrong. Revision 1 is preserved verbatim at docs/Sources/prereg_real_money_home_t409_DRAFT_rev1_2026-11-19.md; every "rev. 1 §x" below points there.
status: DRAFT — NOT FROZEN. Nothing run. No arm's return, wealth path, tax bill or terminal value was computed on any sample. The census read file spans, column names, row counts, public rule text and fund distribution records only. This file states NO trial count; §4.11 lists what each arm would add, for the director's ruling at freeze.
design_inputs: docs/Sources/design_note_lifecycle_leverage_t396_2026-11-14.md (T-396); docs/Sources/design_study_two_account_household_t400_2026-11-14.md (T-400); docs/Sources/design_study_real_money_venue_t402_2026-11-17.md (T-402)
---

> **SUPERSEDED IN PART by revision 3** (`docs/Sources/prereg_real_money_home_t409_DRAFT_2026-11-19.md`,
> 2026-11-20), after the owner's second round of answers:
> - the taxable balance is under $50k;
> - the embedded gain is unknown;
> - law school is more than a year away;
> - the Roth holds $10–25k;
> - every arm must be an ordinary manual choice at Schwab.
>
> Revision 3 §0 lists what changed. Everything below this banner is revision 2 verbatim (commit `bd3e2c7`),
> kept because revision 3 cites its sections.

# T-409 DRAFT (rev. 2) — where the real money should sit, after tax

> † marks a tax or broker rule this study models but a professional or the broker should confirm before
> anyone acts. This is the owner's own research platform; it is not tax advice.

## For the owner, in plain words

**What changed.** You told us four things:
- the robo is on its **aggressive** setting;
- it is a **taxable** account, not your Roth;
- your worst acceptable outcome is **half of what the S&P 500 would have given you**;
- your contributions are **automatic and keep going through crashes**.

The second fact changes the question the most. In a Roth, moving money is free. In a taxable account,
selling realizes gains, and the tax bill is part of the decision.

**What we can already say (arithmetic, not yet a run).**

1. **You can probably leave the robo without selling anything.** Schwab's brochure says you can end the
   program at any time; the account then stays open and is simply not managed.†
   - That alone ends the robo's 6 % cash holding and its rebalancing trades.
   - New automatic contributions can then go into a plain S&P 500 fund.
   - No tax is due, because nothing is sold.
2. **Selling the robo's funds is worth it only if the tax is small.** It is small in either of two cases:
   - **Little of the account is gain.** You can see this in the app as "unrealized gain".
   - **You sell during law school.** The IRS's 2026 table (Rev. Proc. 2025-32) taxes long-term gains at
     **0 %** while taxable income stays under **$49,450**, after the **$16,100** standard deduction. With
     little other income, roughly **$50,000–65,000 of long-term gains a year** could be sold free of
     federal tax. State tax may still apply. If you are under 24 and your parents support you, the
     "kiddie tax" can cancel this.†
3. **The robo's one real advantage in a taxable account is tax-loss harvesting** (selling a fund at a
   loss to cut your taxes, then buying a similar one).
   - Schwab does it **only if you ask, and only once the account holds $50,000** (brochure).
   - It does not look at your tax situation. In law-school years a harvested loss is worth little.
   - Below $50,000 it does nothing for you. Above it, its value is roughly the size of the robo's cash
     and fee cost, so the answer depends on your balance and tax bracket.
4. **If you want leverage, keep it in your Roth, not the taxable account.**
   - In the Roth, stepping leverage down later costs no tax.
   - How much leverage the *whole household* can get that way depends on how big the Roth is compared
     with the taxable account.
   - In the taxable account:
     - **borrowing on margin is a losing trade** at retail rates;
     - **futures** don't fit below about $38,000 per contract;
     - **a "box spread" loan** is cheap but needs broker approvals, a manual roll every year, and Schwab
       confirming how it treats one.
   - Leverage is still a bet on future stock returns, as before.
5. **Your half-of-the-S&P-500 floor is looser than our default.**
   - Modest leverage (1.25×, or a 1.5× cap) very likely passes it.
   - Starting at 2× is borderline.
6. **Your automatic contributions are exactly what the model assumes.** One caution: if law school is
   paid with loans, investing during school means investing borrowed money at the loan's rate. That loses
   on average. Pause contributions in those years.

**What we need from you** (only the answers that can change the decision; §5 says how each one does):
1. The taxable account's balance, and how much of it is unrealized gain.
2. The monthly automatic contribution.
3. When law school starts, and your expected income in school.
4. Your age, and whether a parent claims you as a dependent.
5. Your Roth's balance and which broker holds it.
6. Your state.
7. After the run: which belief row (future stock returns) you believe.

---

## 0. What changed from revision 1, and what in it is now wrong

| Revision 1 | Now |
|---|---|
| The account was assumed to be the Roth: zero tax, $7,500/yr cap, no margin or futures | **The robo is taxable.** Dividends, sweep interest, realized gains, levered-fund distributions and every sell are taxed. Contributions are uncapped (automatic, monthly, amount unknown). Margin, futures and boxes are possible, but **only outside the robo**: "accounts enrolled in the Program are not margin accounts" (brochure p.7). The Roth exists separately. |
| Robo profile unknown; both bounds run | **Aggressive.** Revision 1's "moderate robo: settled on point" is moot. The live case is revision 1's "cannot be settled": 0.2–0.5 %/yr is countable, plus a US-vs-world belief. |
| The leverage arms rebalanced tax-free in one account | Leverage is a **household** quantity. Its natural home is the Roth (tax-free resets), bounded by the Roth's share. In taxable, de-levering sells are charged. |
| λ rule on the Roth alone | λ rule on household wealth plus PV of all future contributions (Roth and taxable) |
| Loss bound default 0.67× VOO | **Owner: never below 0.5× the S&P 500** in any US historical cohort, after tax |
| O6: would you re-lever after a crash? | **Owner: contributions continue automatically through a 40 % fall; no behavioural sell.** The annual reset is mechanical. |
| Arms A2 (target-date fund) and A3 (85/15) | **Dropped as arms.** A2 trails 1× by arithmetic (§2.1 of rev. 1), and a target-date mutual fund is tax-inefficient in taxable. A3's effect is small and settled as "not significant" (B-9); if kept, MTUM lives in the Roth by the location rule (§4.5). |
| Pre-tax terminal wealth | **After-tax household terminal wealth**, liquidated at the retirement-year rate. A hold-for-step-up variant is a sensitivity. |

**The Roth-based framing was wrong in four places.**
1. It priced no switching tax and no robo loss harvesting.
2. It let the leverage glide sell without tax.
3. It assumed the real money could not borrow, when a taxable account can.
4. It treated the $7,500 Roth stream as the whole contribution stream.

Revision 1's census, data layers and precision method still apply. They are kept below.

## 1. What is already settled (carried from revision 1, re-read for a taxable account)

| Question | Settled answer | Source |
|---|---|---|
| Untimed leverage as an *edge* | Cannot pass the gate by construction: best t 2.04 / 2.63 vs 2.96 at N_eff 372 | T-396 §4 |
| Static leverage, pre-tax (T-399-corrected) | No arm CI-beats or CI-loses 1×. 2× +1.66 %/yr [−2.76, +5.83]. At −2 pp every arm is behind on point; the 1929 path takes 2× from $10,000 to $158 | T-315 + T-399 |
| Lifecycle leverage, pre-tax (arithmetic, Roth, $5k/yr) | +22 / +10 / −1 / −12 % of terminal at 0 / −1 / −2 / −3 pp; P(below 1×) 29–64 %. A flat 1.25× has the same mean with half the dispersion | T-396 §2d |
| Trend sleeve, growth tilt, gold leg, levered stacks, multi-factor tilts | Not wealth homes; refuted or straddling | T-311/T-333, T-320, B-10, B-5, B-9 |
| 85/15 vs VOO | +0.30 %/yr on point, ci_low −0.066: the prior, not a finding | B-9 |
| Certain-sign items | +$1,000/yr of contributions ≈ +$196k real at year 40. An HSA if the plan qualifies. Broker incentives $45–675 in year 1 | T-396 §5; T-400; T-402 |
| Asset location for two tax-efficient equity funds | Worth about nothing until a tax-inefficient leg exists; that leg goes in the Roth | T-400 §1 |
| Loss harvesting for a never-sell holder | Usable value is about $3,000/yr × the marginal rate ($720–1,050/yr) plus offsets of realized gains; it decays as old lots rise | T-400 §3 |

## 2. The question now, and what is open

**The question.** For the household (taxable robo account + a separate Roth), what maximizes **expected
log after-tax household wealth at year 40** in the owner's belief row? Three decisions:
- **(A)** the existing robo balance and where new taxable money goes;
- **(B)** whether, how much and where to hold leverage;
- **(C)** which holding lives in which account.

The constraint: after-tax household wealth must never fall below 0.5× the S&P 500 reference in any US
historical cohort, with contributions continuing on schedule.

**Open:**
1. Owner facts (§5).
2. The belief row.
3. Decision (A) under the owner's tax path: switching tax, the school-year 0 % window, the robo's loss
   harvesting. Never priced here.
4. Decision (B) in after-tax household terms, including the Roth-capacity limit and the taxable routes.
   Never priced here.
5. Non-US robustness of the leverage arms. Pre-tax only, as in revision 1, since no tax regime can be
   applied to JST countries.

## 3. Pre-run arithmetic (checkable against the run; assumptions marked)

### 3.1 The cost of switching a taxable position

Selling a position with embedded gain fraction g (unrealized gain ÷ value) at rate τ₀ pays τ₀·g now. That
tax would otherwise be deferred to liquidation, or forgiven at a step-up. The annual drag that switching
must remove to break even over T = 40 years is about `d* = −ln(1 − τ₀·g)/T`. The bracket is the version
that credits the future liquidation tax at τ_T = 20 %.

| τ₀ (federal + state) | g = 0.10 | g = 0.25 | g = 0.50 |
|---|---|---|---|
| 0.05 — a school year: 0 % federal + 5 % state [assumed] | 0.013 (0.010) %/yr | 0.031 (0.025) | 0.063 (0.051) |
| 0.20 — post-school: 15 % + 5 % | 0.051 (0.040) | 0.128 (0.102) | 0.263 (0.208) |
| 0.24 — with the 3.8 % NIIT | 0.061 (0.048) | 0.155 (0.123) | 0.320 (0.252) |

Two readings:
- **In a school year switching is nearly free.** It also resets the basis upward (a gain harvested at 0 %).
- **Post-school, it pays only if the drag removed exceeds 0.1–0.3 %/yr.** After de-enrolling (§3.2) the
  remaining drag on legacy lots is the fee gap of about 0.07–0.12 %/yr, so switching post-school pays only
  at small g.

Short-term lots (held < 1 year) are taxed at ordinary rates and are never sold by any arm.

### 3.2 What the aggressive robo costs in a taxable account, before loss harvesting (post-school bracket)

Assumptions: 24 % ordinary rate, 15 % long-term rate, 5 % state, realized premium.

| Component | %/yr of the account | Basis |
|---|---|---|
| 6 % cash at the sweep yield instead of equity | 0.31 (0.13 at −3 pp) | rev. 1 §2.1 |
| Tax on sweep interest (ordinary) less the dividend tax VOO would pay on that 6 % | ≈ 0.04 | 6 % × ~3.2 % × 29 % − 6 % × 1.2 % × 20 % |
| Fee gap: robo ETFs vs VOO 0.03 % | 0.07–0.17 [R] | owner's statement replaces it |
| Dividend character: REIT and part of international paid as non-qualified | 0.02–0.05 [assumption] | owner's 1099-DIV replaces it |
| Rebalancing sells inside the robo realize gains early | ≈ 0.05 [assumption: 2 %/yr of value sold, g 0.3] | owner's 1099-B replaces it |
| **Total** | **≈ 0.5–0.6** | |

**De-enrolling in place (K1, §4.2) removes all of it except the fee gap on the legacy lots.** It also keeps
the robo's US/international mix, which stays a belief this model does not price.

### 3.3 What the robo's loss harvesting is worth (Schwab brochure, read today)

What the brochure says:
- Opt-in, "with any taxable account", active only at **$50,000** in a single SIP account. A lower,
  undisclosed balance keeps it active.
- A daily check sells at a loss "when the tax-loss harvesting threshold is met" (threshold not disclosed)
  and buys a replacement ETF tracking a different index.
- "CSIM does not monitor the type and amount of capital gains."
- Its wash-sale avoidance covers Program accounts monitored together, **not the owner's Roth elsewhere**.

Value:
- **Ceiling when active post-school.** The usable offset is $3,000/yr against ordinary income plus any
  realized gains (T-400 §3). At 1–3 % of the balance harvested a year (T-400's assumption) and a 29 %
  combined rate: gross ≈ 0.3–0.9 %/yr at $50k, net ≈ 0.2–0.6 %/yr after the later tax on the lowered
  basis. It falls as the balance grows and old lots rise out of reach.
- **In school years ≈ 0 or negative.** Losses offset income taxed at 0–12 %, and harvested losses net
  against the gains the 0 % window would have realized for free.
- **A harvested loss is lost permanently if the Roth buys a substantially identical fund within 30 days**
  (Rev. Rul. 2008-5, T-402 §4). The location rule (§4.5) prevents this.

Read together with §3.2:
- **Below $50k:** K1 beats staying (K0) by ≈ 0.5 %/yr on that balance, at no tax.
- **Above $50k in high-bracket years:** K0 vs K1 is roughly a wash (−0.4 to +0.1 %/yr).
- **K1 plus do-it-yourself harvesting** (VOO ↔ a fund on a different index) beats K0 by the robo's drag,
  if someone executes it.

### 3.4 The school-year 0 % window (IRS, read today)

Rev. Proc. 2025-32 §3.03 (2026) and Rev. Proc. 2026-35 (2027):
- the maximum zero-rate amount for single filers is **$49,450** (2026) and **$51,050** (2027) of taxable
  income;
- the standard deduction is **$16,100** / **$16,600**;
- the 15 % rate runs to $545,500 (2026);
- the kiddie-tax floor is **$2,700** (2026: twice the $1,350 element, Rev. Proc. 2025-32 §3.02) /
  **$2,800** (2027).

| Ordinary gross income in the year | 0 % long-term-gain room, 2026 | 2027 |
|---|---|---|
| $0 | $65,550 | $67,650 |
| $10,000 | $55,550 | $57,650 |
| $25,000 | $40,550 | $42,650 |
| $40,000 | $25,550 | $27,650 |

Caveats†:
- State tax usually still applies.
- The kiddie tax voids the window if the owner is under 24, a full-time student, and earned income does
  not exceed half of support. Unearned income above the floor is then taxed at the parents' rate.
- Realized gains raise AGI, which can reduce need-based aid or premium subsidies.
- Harvested losses in the same year net against these gains (T-400 §2).

### 3.5 Household leverage capacity if the leverage lives in the Roth

With r = Roth ÷ (Roth + taxable), and the taxable account at 1×:

| r | via SSO in the Roth | via UPRO in the Roth |
|---|---|---|
| 0.10 | 1.10× | 1.20× |
| 0.20 | 1.20× | 1.40× |
| 0.33 | 1.33× | 1.66× |
| 0.50 | 1.50× | 2.00× |
| 0.67 | 1.67× | 2.00× (cap) |

The λ rule wants the 2× cap for the first 12–15 years (T-396 §2c). So unless r ≥ 0.5 with UPRO, the Roth
alone cannot deliver the cap-2 lifecycle rule. It can deliver a 1.25× static or a 1.5×-cap rule from
r ≈ 0.25 (UPRO) or 0.5 (SSO).

### 3.6 Leverage routes at the owner's size

Break-even arithmetic premium `μ* = c + ½(L+1)·σ²`, σ² 2.94 %, against the belief rows 7.75 / 6.75 / 5.75 /
4.75 %.

| Route | Where | Cost per borrowed $ over bills, c | Minimum / granularity | Crash behaviour for a non-seller | Tax | Status |
|---|---|---|---|---|---|---|
| SSO + VOO blend | Roth or taxable | 1.37 % (0.89 % ER less 0.09 %, plus 57 bp swap spread [18, 96]) | none | Daily reset; no margin call; keeps a remnant (2008 at 2×: ≈ 15 %) | Taxable: distributions 0.2–0.9 %/yr of NAV since 2009 (dividends only, census §6; character [R] ordinary); sells realize gains | **Feasible** (arms B1–B4) |
| UPRO + VOO blend | Roth or taxable | 0.96 % | none | as SSO, 3× slice | as SSO | **Feasible** (sensitivity V2) |
| Margin loan (Schwab) | taxable, after leaving SIP | rate − bill; Schwab's table is script-rendered and could not be read [R: retail small-balance margin rates ≈ 11–13 % in 2024–25] | $2,000 to borrow (Schwab margin page, read today) | Margin call: at 2× after a 29–33 % fall (25–30 % maintenance); 1.5× after 52–56 %; 1.25× after 71–73 % | Interest deductible only if itemizing, against investment income | **Dropped.** It loses in every belief row at any spread above 4.4 pp over bills (μ* ≥ 7.31 % at 1.25×). Any retail small-balance rate is far above that [R] |
| Short box spread (SPX), cash buys VOO | taxable margin account | ≈ 0.35–0.6 % [R: box rates ≈ Treasuries + ~35 bp in the literature] + about $1.4 per contract per year in commissions and fees [R] | Margin and spreads approval. Whether Schwab lets Reg-T short-box proceeds be used, or locks them as margin, is **unverified**; T-315/T-400 place box financing at the portfolio-margin tier ($110–125k) | Same margin-call arithmetic: realistic only at ≤ 1.3–1.4× | SPX options are §1256: the implied interest is a 60/40 capital loss, usable against gains or $3,000/yr of ordinary income | **Conditional** (B6): only if Schwab confirms usable proceeds below portfolio margin. Manual roll yearly; no options order path in the code (T-396) |
| Micro E-mini S&P (MES) | taxable futures account, or a Roth at ≥ $25k NLV | ≈ 0.1–0.4 % [R] | $1,500 account minimum and margin approval (taxable); **$25,000 NLV plus margin and spreads approval in an IRA, held to 125 % of initial margin** (Schwab futures FAQ, read today). One contract ≈ $5 × 7,619 ≈ **$38k** notional: +1 contract is 2× at $38k, 1.5× at $76k, 1.25× at $152k of equity | Daily variation margin in cash; a 40 % fall costs ≈ $15k per contract, paid by selling other holdings (taxable: realized; Roth: free) or the position is closed | Taxable: §1256 marked to market every year, 60/40 (no deferral; T-294b's 1.81 %/yr drag at an 18.6 % blend; ≈ 0.5 %/yr in school brackets, T-400). Roth: none | **Roth route conditional** (B5: Roth ≥ $25k at a broker that allows IRA futures). **Taxable route dropped below ~$76k** (granularity overshoots the 1.5× cap) |
| Deep-ITM LEAPS | either | 0.8–2.9 % (T-396) | One SPY-class contract ≈ $76k notional; fits 2× above ≈ $38k | Expires; a forced sale at the bottom for a never-sell holder | Rolls realize gains | **Dropped** (T-396 §3: not cheaper, forced-sale instrument, no price history) |

**Reading:** at the owner's likely size, the feasible leverage routes are levered ETFs (Roth first), and
possibly Roth futures from $25k or a box spread if Schwab confirms the margin treatment. All borrowing
routes carry a margin-call ceiling of ≈ 1.3–1.4× for a holder who must not be forced to sell in a 1929-
or 2008-scale fall.

## 4. The pre-registration (DRAFT, revision 2)

### 4.1 Framing and the owner's choice rule

- **Run once, as an estimate; DESCRIPTIVE verdicts only.** The program's gate is computed and reported
  (§4.9) and decides nothing.
- **The owner's choice rule, fixed now.**
  - Take the owner's belief row (chosen after reading the table).
  - Discard every arm whose after-tax household wealth falls **below 0.5 × the S&P 500 reference** in
    **any** US historical 40-year cohort (L1, and L2 where defined).
  - Choose the arm with the highest E[log after-tax household wealth] in the bootstrap.
  - A difference smaller than max(2 × Monte Carlo SE, the spread across the three block lengths) is a
    tie. A tie goes to the simpler arm: K1 in decision A, B0 in decision B.
- **The S&P 500 reference R\*.** The same household and contributions, holding VOO 1× in both accounts
  from t = 0, with the legacy robo balance switched to VOO at **zero** tax. That is frictionless, so the
  bound is slightly strict for every arm.
- **Behaviour, per the owner.** In every arm and every path, contributions continue monthly on schedule
  through every fall. No arm ever sells to cash. Leverage resets are mechanical annual rebalances,
  executed in the path whatever the market did.
- Licenses nothing in the system: no promotion, no engine change, no paper or live book (propose-first).

### 4.2 Arms

**Decision A — the existing taxable robo balance B and new taxable money.** All four arms use the same
equity return (US-only proxy, rev. 1 §4.4). They differ only in fees, cash, taxes, harvesting and the
timing of sales.

| Arm | Construction |
|---|---|
| **K0 — stay** | SIP aggressive as is: 94 % equity / 6 % cash at bill − 0.30 %. Robo ETF fees (owner's statement; default 0.15 % [R]). New contributions go into SIP. **Loss harvesting** is opted in and active while the balance is ≥ $50,000; the maintenance threshold is undisclosed, so the same $50,000 is assumed (labelled). Daily check; harvest a lot whose loss exceeds θ (θ undisclosed: **5 %** primary; 3 % and 10 % reported). The swap goes to a replacement with the same return (tracking difference ignored, labelled); 30-day lockout. Robo rebalancing realizes gains at ρ_r = **2 %/yr** of value sold, highest basis first (0 % and 5 % reported; the owner's 1099-B replaces this) |
| **K1 — leave the program in place** | De-enroll at t = 0† (T-402 §3: "probably yes", confirm by phone). Legacy ETF lots are kept at their basis and fees. The 6 % cash buys VOO. New contributions → VOO. No sales, no harvesting |
| **S0 — switch now** | At t = 0 sell every **long-term** legacy lot at the current year's rates and buy VOO; short-term lots are sold on the day they turn long-term. New contributions → VOO |
| **S1 — switch in the 0 % years** | K1 at t = 0. In each school year, sell legacy lots (highest gain per dollar first) up to that year's 0 % room, then harvest gains on VOO lots (sell and rebuy at once) up to any room left. After school, the remaining legacy lots are held (K1) |
| **Toggle: DIY harvesting** (reported on K1, S0, S1) | The K0 rule applied to VOO lots with a replacement on a different index, executed only in years with a combined ordinary rate ≥ 22 % (T-400's threshold). Requires an executor; reported, never assumed |

**Decision B — household leverage.** In every B arm the taxable account holds VOO (legacy handled as in
K1). The λ rule, cap, floor and vehicle model are revision 1's A4–A6 (T-399-corrected blend: fees on the
levered slice, bills/SOFR + measured spread, calendar-day accrual, annual reset cost charged once). The
ratio is now computed on **household** wealth plus PV of **all** scheduled contributions.

| Arm | Construction |
|---|---|
| **B0 — 1× everywhere** | The bar for decision B |
| **B1 — Roth-carried lifecycle, cap 2×** | The household target L_t is implemented with SSO in the Roth, up to its capacity (§3.5). Excess target is dropped, never moved to taxable. Resets are tax-free |
| **B2 — Roth-carried lifecycle, cap 1.5×** | As B1 |
| **B3 — Roth-carried static 1.25×** | As B1 at a fixed household 1.25× |
| **B4 — taxable-carried lifecycle, cap 2×** | Target as B1, implemented in taxable as VOO + SSO. **De-lever by contributions first:** new money buys VOO, and SSO is sold (highest basis first, gains charged) only if the year-end target cannot otherwise be met. **Re-lever after a fall by contributions first,** then by selling VOO loss lots, which are harvested. SSO distributions are taxed as ordinary income at the census rate (§6). Prices the tax cost of putting leverage in taxable |
| **B5 — Roth futures (conditional)** | Only if the Roth is ≥ $25k at a broker allowing IRA futures. Integer MES contracts (≈ $38k notional each) sized to the nearest contract at or below the B2 target. Collateral in T-bills inside the Roth; variation margin met by tax-free sales of the Roth's VOO. Financing = bills + 0.2 % [R] |
| **B6 — taxable box-financed static 1.25× (conditional)** | Only if Schwab confirms that Reg-T short-box proceeds are usable below portfolio margin. Box rate = bills + 0.45 % [R midpoint]. The implied interest is a §1256 60/40 loss. Margin calls are simulated at 30 % maintenance with forced highest-basis-first sales, and taxed. A manual annual roll |
| **Vehicle sensitivity V2** | UPRO in place of SSO in B1–B4 |
| **Dropped, with reason** | Margin loan (§3.6, loses in every row); LEAPS (T-396); taxable futures below ~$76k of taxable equity (granularity); target-date fund and 85/15 as arms (§0) |

### 4.3 The tax engine (applied to all historical and bootstrap paths; 2026 law held constant, indexed)

- **Lots.** Every contribution is a lot: date, fractional quantity, basis. Sales use specific-lot
  highest-basis-first† (FIFO reported). The holding period sets short vs long term.
- **Each year:**
  - **Qualified dividends** at the long-term schedule (0 / 15 / 20 % by taxable income).
  - **Ordinary income** at the owner's ordinary rate: non-qualified dividends, sweep interest, levered-fund
    distributions.
  - **Realized gains** netted short against long. Up to **$3,000** of net loss offsets ordinary income;
    the rest carries forward.
  - **NIIT** of 3.8 % above **$200,000** MAGI.
  - **State tax** at a flat rate s (owner input; default 5 % [assumption]; `config/` assumes Illinois,
    T-400 §0).
- **Indexing.** The $3,000 offset and the NIIT threshold are fixed in nominal dollars by statute, so
  they are deflated along each path. Brackets and the standard deduction are CPI-indexed.
- **Payment.** Taxes are paid from the taxable account each year-end by highest-basis-first sales; the
  tax on that sale falls into the next year.
- **Dividend yield.** Shiller monthly D/P of the S&P composite splits the French total-market return
  into price and dividend (labelled proxy). The robo's yield is D/P plus an international/REIT uplift
  of 0.6 pp, with a qualified share of 80 % [assumptions; the owner's 1099-DIV replaces them].
- **Owner's income path (inputs; defaults in brackets):**
  - pre-school ordinary taxable income [$50k];
  - school years [$5k], with the kiddie-tax flag [off];
  - post-school [$150k real];
  - retirement-year liquidation rate τ_T [15 % + s];
  - sensitivity: τ_T = 0 (hold for step-up, or a low-income retirement year).
  - The Roth is untaxed throughout.
- **Liquidation.** After-tax household wealth at year 40 = Roth + taxable value − τ_T × the taxable
  account's embedded gain, less any unused loss carryforward credit. Pre-liquidation value and the
  deferred liability are also reported.

### 4.4 Schedule (owner inputs; defaults in brackets)

- **Taxable:** balance B [$20,000], embedded gain fraction g [0.20], short-term share [0].
  - Monthly automatic contribution c_T [$500], continuing through every fall.
  - In school years c_T continues unless the owner says the contributions would be loan-funded; a
    loan-funded variant is reported as a warning case, not an arm.
- **Roth:** balance R [$10,000], $7,500 each January when there is earned income. School years: Roth
  contribution 0 [default], unless school-year earned income ≥ $7,500.
- **Timing:** school years [2–4]; horizon 40 years.
- **Real dollars:** CPI-indexed contributions (rev. 1 §4.3).
- **λ rule PV:** household PV of all scheduled contributions at 1 % real.

### 4.5 The asset-location rule (simple, stated, not an arm)

1. **Roth:** any levered piece (SSO/UPRO or futures), any momentum satellite (MTUM), anything paying
   ordinary-income distributions, and all rebalancing trades.
2. **Taxable:** broad cap-weighted 1× equity bought with new money. Sold only to:
   - harvest losses (in ≥ 22 % years);
   - realize long-term gains inside the 0 % room;
   - de-lever B4 when contributions cannot.
3. **Wash-sale perimeter:** the Roth never buys the taxable account's fund or its harvest partner (Rev.
   Rul. 2008-5).† Example: taxable holds an S&P 500 fund and harvests into a total-market fund; the Roth
   holds SSO/UPRO.
   - Whether SSO is "substantially identical" to an S&P 500 fund is unsettled [R]†. The default treats
     it as not identical, and the test case §4.10(6) runs both readings.

### 4.6 Belief rows

Unchanged from revision 1 §4.4:
- h ∈ {0, −1, −2, −3} pp on the arithmetic equity return, every equity leg;
- the parameter-uncertainty row (SE ≈ 1.83 pp);
- bonds and cash unadjusted;
- the US-vs-world question left as a belief, with the JST descriptive table;
- CAPE 39.4 (2026-11) as context, not a signal.

### 4.7 Data and precision

As revision 1 §4.5–4.6:
- **L1:** French daily 1926-07 → 2026-09, for the equity, RF and financing legs.
- **L1m:** monthly; Shiller bond TR and D/P.
- **L2:** Shiller 1871–1926. Unlevered arms only; dividend yields from Shiller.
- **L3:** JST, 16 countries. Leverage arms **pre-tax only**, labelled.
- **FRED API:** CPIAUCNS, DTB3, SOFR.
- **Historical cohorts:** 60 on L1, more with L2; effective-N printed; never quoted as a probability.
- **Paired stationary block bootstrap:** mean block 60 months; 12 and 120 reported.
  - 10,000 paths for the pre-tax quantities; **2,000 paths for the tax-engine arms** (lot-level
    bookkeeping is the cost), with the Monte Carlo SE printed.
- The bootstrap carries sequence risk only; the belief rows carry the mean.

### 4.8 Metrics (per arm × belief row; after tax unless stated)

- **M1–M2:** median and mean after-tax household terminal wealth.
- **M3:** P(arm < R\*).
- **M4:** 5 / 50 / 95 % of arm ÷ R\*.
- **M5:** E[log W]; CE at γ = 2.
- **M6:** worst US cohort's arm ÷ R\*, which is **the loss-bound test**, plus the start year, the dollar
  shortfall, and the same for JST (reported; eligibility is US-only, per the owner's "S&P 500").
- **M7:** largest real-dollar drawdown (historical worst and bootstrap median / 95 %).
- **M8:** regret vs R\* and time to recover.
- **M9:** P(balance < cumulative contributions at year 20).
- **M10:** pre-tax Sortino on monthly returns (12 periods) with a block-bootstrap CI, for the static
  arms. After-tax Sortino is undefined with annual tax and is not computed.
- **M11, tax-specific:**
  - present value of taxes paid;
  - realized gains by year;
  - 0 % room used;
  - losses harvested and their tax value;
  - years the robo harvesting was active;
  - the carryforward at year 40;
  - the deferred liability at year 40;
  - for B4, the tax charged on de-levering sales;
  - for B6, margin calls and forced sales.

### 4.9 The program's gate (reported, never deciding)

Revision 1 §4.8 applies, with the statistic now Δ log after-tax household terminal wealth across cohorts.
Pass probabilities:
- leverage arms ≈ 0 by construction;
- K-vs-S contrasts are near-deterministic tax arithmetic. A "pass" would certify a fee or tax identity,
  not an edge.

### 4.10 Pre-run checks (fail closed; any failure HALTS)

Revision 1 §4.9's nine checks, plus:
1. **Tax toy.** A 3-year, 4-lot toy reproduces a hand computation to the cent. It contains:
   - a qualified dividend;
   - a 0 % school-year gain;
   - a harvested loss with $3,000 used and a carryforward;
   - a short-term sale;
   - an NIIT crossing.
2. **Brackets.** The 2026 and 2027 parameters equal Rev. Proc. 2025-32 / 2026-35 as read (md5-pinned
   PDFs, §6).
3. **Wash-sale lock.** A Roth purchase of the harvested fund within 30 days disallows the loss, with
   no basis carryover (Rev. Rul. 2008-5). A purchase of the partner fund in taxable defers it.
4. **Nominal-fixed items.** The $3,000 offset and the $200k NIIT threshold deflate along the path.
5. **Lot order.** Highest basis first chooses the right lot; a FIFO variant differs on a planted case.
6. **Both readings of the SSO "substantially identical" question** run on one toy path.
7. **Margin call (B6).** A planted −35 % month at 2× triggers a call; at 1.25× it does not.

### 4.11 Trial count (proposal for the director; this draft states none)

| Unit | Would add |
|---|---|
| Decision A: K0, K1, S0, S1 | 4 (near-deterministic tax arithmetic; counted anyway) |
| Decision B: B1, B2, B3, B4 | 4 |
| B5, B6 (conditional; only if their feasibility condition holds at freeze) | 0–2 |
| V2 (UPRO) on B1–B4 | 0 by the T-315 sensitivity convention, 4 raw |
| JST pre-tax leverage analogs (B1–B3 equivalents) on a new substrate | 0 on the US substrate, 3 raw |
| Toggles and sensitivities (DIY harvesting, θ, ρ_r, τ_T, s, FIFO, income path, belief rows, block lengths) | 0, as reported sensitivities |

- **Range:** 8 to 17.
- **Effect:** at 17, N_eff 372 → ~389 and E[max] ≈ 2.97.
- **Recommendation:** count raw.

### 4.12 Pre-stated expectations

| # | Expectation |
|---|---|
| E1 | Below $50k, K1 beats K0 by 0.4–0.6 %/yr on the legacy balance. Above $50k in high-bracket years the gap is within ±0.3 %/yr. K1 + DIY harvesting beats K0 everywhere by about the robo's drag. |
| E2 | S1 ≥ S0 whenever g ≥ 0.1 and a school year with ≥ B·g of 0 % room exists. S1 ≈ K1 + the basis step-up. Post-school, S0 beats K1 only for g ≲ 0.1. |
| E3 | The decision-A spread (best minus worst) is under 5 % of after-tax household terminal wealth when c_T·12 ≥ B. The new money dominates. |
| E4 | B1 is capped by Roth capacity in most paths unless r ≥ 0.5. B2 and B3 are feasible from r ≈ 0.25–0.5. |
| E5 | B4 keeps 80–95 % of B1-uncapped's expected pre-tax gain. Most de-levering happens through contributions, and the tax on sales is deferral lost, not tax added. |
| E6 | Loss bound (0.5× R\*): B2, B3 and Roth-capped B1 pass in every US cohort. Uncapped 2× (B4) is borderline in the cohorts that meet 1929–32 or 1973–74 in years 8–20. B6 at 1.25× passes. |
| E7 | In E[log W] (log utility) at the realized premium: the leverage arms beat B0 where feasible. At −2 pp: within noise. At −3 pp: B0 wins. The order of A arms does not depend on the belief row. |

## 5. Which remaining owner inputs change the decision, and how

| Input | Default | If high | If low | Size of what's at stake |
|---|---|---|---|---|
| **Taxable balance B** | $20k | ≥ $50k: the robo's harvesting can switch on. K0 vs K1 becomes a close call that depends on the bracket and on whether anyone does DIY harvesting. The run decides | < $50k: harvesting cannot run. **Leave the program in place (K1) now**: no tax, removes ≈ 0.5 %/yr | ≈ 0.5 %/yr × B (≈ $100/yr at $20k; $500/yr at $100k, compounding) |
| **Embedded gain fraction g** (app: unrealized gain ÷ value) and any lots < 1 year old | 0.20; none | ≥ 0.3: **don't sell outside a 0 % year.** K1 now; S1 in school, or hold the legacy for good | ≤ 0.1: selling now (S0) costs ≤ 0.05 %/yr-equivalent. Switch whenever convenient | Switching tax τ₀·g·B: at $20k, g 0.3, τ₀ 0.20 ≈ $1,200 now vs ≈ $60 in a school year (state only) |
| **When school starts; school-year income** | years 2–4; $5k | Starts soon and income ≲ $40k: **S1 dominates** (0 % room $25–65k/yr) | Far off, or high income in school (spouse, stipend): no window. K1 and hold | The whole switching tax, plus a free basis step-up of up to ~$50–65k a year |
| **Age / dependency (kiddie tax)** | not subject | Under 24, full-time student, supported: **the 0 % window is void**; K1 and hold | Not subject: the window stands | As above |
| **Monthly automatic contribution c_T, and whether school-year money is borrowed** | $500, not borrowed | c_T·12 ≫ B: the legacy choice is < 5 % of the outcome (E3). What matters is where new money goes (VOO) | Small c_T: decision A matters more | If school-year contributions are loan-funded at 7–9 %: **pause them.** No belief row pays 7–9 % plus the variance cost (the §3.6 margin arithmetic) |
| **Roth balance R and its broker** | $10k, unknown | r = R/(R+T) ≥ 0.5: Roth-carried leverage reaches the household targets tax-free (B1 with UPRO, B2, B3). R ≥ $25k at a broker allowing IRA futures adds B5 | r ≤ 0.2: Roth-carried leverage ≤ 1.2× (SSO) / 1.4× (UPRO). More needs taxable routes (B4, B6), at a tax and operations cost | The leverage decision's feasible size |
| **Post-school bracket and state** | 24 % / 15 % / 5 % | High (≥ 32 %, NIIT, state ≥ 5 %): harvesting worth more (DIY, or K0 above $50k); selling outside school costs more (S1/K1); taxable leverage costs more (Roth first) | Low: tax differences shrink; K1 ≈ S0 | Tens of basis points a year |
| **Belief row** (after the run) | — | Realized premium: leverage arms lead in E[log W] where feasible | ≤ −2 pp: B0 | T-396's +22 / +10 / −1 / −12 % at the full-household scale; less when Roth capacity binds |
| **Robo tax history** (1099-B realized gains, 1099-DIV qualified share) | assumptions §3.2 | Only matters when B ≥ $50k and K0 vs K1 is close | — | ± 0.1 %/yr |

**Decisions that need no further input.**
- New taxable money goes to a broad 1× index fund, not the robo, unless B ≥ $50k and the owner wants the
  robo's harvesting (E1).
- Leverage, if any, goes in the Roth first.
- Margin loans are out.
- Contributions continue through crashes, but not on borrowed money.

**One owner-side check before anything moves:** ask Schwab whether ending the program leaves the
positions in place, untouched, in the same taxable account (T-402 §3: "probably yes", not stated in words).

## 6. Census (revision 1 §5 stands; additions read 2026-11-19, generic User-Agent, scratch only)

| Source | Status | What was read | md5 |
|---|---|---|---|
| IRS Rev. Proc. 2025-32 (`irs.gov/pub/irs-drop/rp-25-32.pdf`) | 200 | §3.03: 2026 maximum zero-rate amount $49,450 (single) / $98,900 (joint); 15 % to $545,500. Standard deduction $16,100 | `74f4c844423b8c3d651188c9c5f889fd` |
| IRS Rev. Proc. 2026-35 (`rp-26-35.pdf`) | 200 | 2027: $51,050 / $102,100; standard deduction $16,600; kiddie-tax element $1,400 (so $2,800) | `da92f5ce13973722ec03d1592212c07a` |
| Schwab SIP brochure (rev. 1 file) | — | Loss harvesting is opt-in, $50,000 to activate, a lower undisclosed maintenance minimum, a daily check, an undisclosed threshold, replacement on a different index; "does not monitor the type and amount of capital gains" (p.8–9). SIP accounts "are not margin accounts" (p.7). $5,000 to open (p.10) | `c7e84a84…` |
| Schwab margin page (`schwab.com/margin`) | 200 | "at least $2,000 in cash or marginable securities" to borrow. **The rate table (`/margin-rates`) is script-rendered; no rate could be read** | — |
| Schwab futures FAQ | 200 | Taxable: margin approval and a $1,500 account minimum. IRA: $25,000 NLV, margin and options-spreads approval, held to 125 % of initial margin; Roth eligible | — |
| yfinance actions (census of distributions ÷ year-end close) | OK | SSO 2009–2026 dividends 0.2–0.9 %/yr (4.4–5.3 % in 2006–07); UPRO 0.05–0.9 %; VOO 0.9–2.2 %. **No capital-gain distributions recorded** for any of the three (yfinance's capital-gain field is not authoritative: verify from ProShares' distribution history) | — |
| Shiller `ie_data.xls` (rev. 1 file) | — | S&P composite 2026-11 monthly-average level 7,619, so MES ≈ $38k and an SPY-class option ≈ $76k notional | `2fd4f340…` |

## 7. Where the record contradicts itself (revision 1 §6 items 1–9 stand; additions)

10. **`advisor_surface.md`, T-402 and revision 1 all assumed or left open that the robo was the Roth.**
    It is taxable. T-402 §3's two hedged lines are now load-bearing:
    - "convert in place: probably yes" — K1 depends on it;
    - "if taxable, move it in kind".
11. **T-400 §2 says gain harvesting has "almost nothing to harvest: the taxable account does not exist
    yet."** It exists: the robo account, with embedded gains. The school-year window has a real object.
12. **The decision package's mechanics row** (`real_money_decision_package_2026_09.md:37-42`) plans
    "robo-liquidate → ACAT/cash → machine-executed buys" and "the Roth first (zero-tax …)". For a taxable
    robo, liquidation is a taxable event. The plan should be de-enroll or move in kind, then sell only
    inside the 0 % room.
13. **`CURRENT_STATE.md`'s "Wrapper facts (any Roth IRA …)"** describe the account the real money is not
    in. The real money can borrow, but the robo account itself cannot (SIP accounts are not margin
    accounts).
14. **T-315 and T-396 place box-spread financing at $125k+.** That is the portfolio-margin tier. Whether
    Reg-T short-box proceeds are usable at Schwab is unverified (B6's condition), so neither "box from
    $125k" nor "box at any size" is established.

## 8. Before freeze (checklist)

- [ ] Owner inputs in §5, or explicit "use defaults". One Schwab call (de-enroll keeps positions; short-box
      margin treatment; the harvesting maintenance minimum; the current margin rate for the record).
- [ ] A tax professional reviews the † items: lot method, the SSO wash-sale reading, kiddie-tax status,
      state treatment of gains, the §1256 box treatment.
- [ ] Verify expense ratios and ProShares' distribution character and history.
- [ ] The director rules the trial count (§4.11), the default income path, θ, ρ_r and τ_T.
- [ ] Study code (tax engine, lots, harvesting, margin calls, the household λ rule) written and reviewed by
      execution, with the lock tests in §4.10.
- [ ] Freeze manifest with input md5s; only then run once.

## References

Revision 1's list, plus:
- IRS Rev. Proc. 2025-32 and 2026-35; Rev. Rul. 2008-5 (via T-402).
- Schwab Intelligent Portfolios Disclosure Brochure (2026-10-15); Schwab margin page and futures FAQ (read
  2026-11-19).
- T-294b (`docs/Audit/taxable_futures_vehicle_t294b_2026_07_08.md`), for §1256 drag.
- Chaudhuri, Burnham & Lo (2020), "An Empirical Evaluation of Tax-Loss-Harvesting Alpha", FAJ (via T-400).
- van Binsbergen, Diamond & Grotteria (2022), "Risk-Free Interest Rates", JFE, for box-spread rates [R].
