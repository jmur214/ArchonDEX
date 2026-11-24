---
task_id: T-409
title: DRAFT pre-registration (revision 5, the freeze candidate) — where should the owner's money sit? An after-tax household decision study of ordinary manual choices at Schwab (keep the robo; leave the program without selling; a broad index fund; a 2x index ETF in the Roth)
date: 2026-11-24
worker: edge-analyst (worktree agent-ac300c3d5f4eba52f)
revision: 5 (2026-11-24). It supersedes revision 4 (commit 09bae94) after the delta review of 4e38476. It is SELF-CONTAINED — every rule below is written out; earlier revisions are provenance only (Appendix A lists them with SHA-256).
status: DRAFT — NOT FROZEN. The full study has NOT been run. Run so far are the tests, the five positive controls, the mutants, and --smoke (real data, 10-year cohorts 1990-96 on 1985-2026, 16 paths, plumbing only). No parameter, arm or expectation was set from a smoke. What the smoke showed was visible before the decision rule in §3.1 was chosen, and §3.1 says so. This file states NO trial count; §8 gives my recommendation.
---

# T-409 DRAFT (rev. 5) — where the real money should sit, after tax

> † marks a tax or broker rule this study models but a professional or the broker should confirm before
> anyone acts. This is the owner's own research platform; it is not tax advice.

## For the owner, in plain words

**Every option in this study is an ordinary choice you would make yourself at Schwab:**
- keep the robo;
- leave the robo program without selling;
- buy a plain index fund;
- hold a 2× index fund in your Roth.

**Nothing here involves this project's trading machine, its paper accounts or its strategies.**

**What your answers settle.**
- **Harvesting cannot switch on today.** Your taxable robo holds under $50,000. The default being tested
  is leaving the program without selling: no tax is due, the cash gets invested, and new automatic
  contributions go to a plain index fund.
- **Your unrealized gain matters only if you sell.** The study reports selling options at 0 %, 15 % and
  30 % gain for completeness.
- **Law school is more than a year away.** Selling in the 0 % tax years is kept as a later option.
- **Your $10–25k Roth limits household leverage to about 1.2–1.5×.**

**You have said you have no view of future returns, so here is how the study decides for you** (§3.1 has
the exact text):
- It reads the answer twice: once assuming stocks do as well as they did in the last century (with honest
  uncertainty about that), and once assuming they do 2 points a year worse.
- If both readings give the same answer, that is the answer. If they disagree, the answer is the simple
  default: leave the program without selling.
- You can overrule this by naming one row before the run. An overrule is written into the frozen plan.

**How the study picks between options.** It picks the option with the best *typical* outcome: the middle of
the range, counted in percentage terms. It does not pick the highest average, because a few very lucky
futures can pull an average up without making the typical outcome better. Where the two differ, the output
shows the highest-average option on its own line, so you can see it.

**What the study will show**, for each belief row:
- each option after tax, in today's dollars;
- which options never fell below half of the S&P 500 outcome in any of 60 real historical 40-year runs;
- which option has the best typical outcome.

It will not certify any choice as proven. The choice stays yours.

---

## 0. What changed from revision 4 (the delta review, 2026-11-24)

| # | Finding | Revision 5 |
|---|---|---|
| 1 | No decision rule for an owner with no stated view | §3.1: the **pair rule**, as code (`--decision-row pair`) and as text |
| 2 | 11 of the reviewer's 45 mutants survived | New tests; all 45 reviewer mutants and 16 new ones re-run (§11). The last worksheet step (below) had been omitted from both the code and the test's reference |
| 3 | The freeze was not self-contained | This file writes out everything; provenance is in Appendix A |
| 4 | Owner summary said "leaves the most money" | The rule picks the best **typical** outcome (highest E[log W]); the highest-mean arm is reported on its own line and never decides |
| 5 | Minors | `--decision-row` is checked before any input is read; the smoke now has two parameter rows and a block run; **the Qualified Dividends worksheet's last "smaller of" step** is applied (below); the output guard also refuses the main tree's `data/` from a worktree; progress reporting; runtime restated (§9) |

**Numerics touched by this revision** (so the director can judge whether another execution review is needed):
- the last worksheet step (≤ $30 a year, in the $49,450–$50,400 band only);
- the default for school-year Roth contributions: **none** (§2);
- a new sensitivity that pauses the taxable contribution in school.

**A correction to revision 4.** It said the tax engine followed the Qualified Dividends worksheet "including
its smaller-of steps". It did not apply the last one (the smaller of the worksheet's tax and the ordinary tax on all taxable
income). The test's independent reference omitted the same step, so the 3,000-case fuzz could not notice. A
hand-computed case from the published brackets (125 = the ordinary tax on 50,450, not 150) now locks it.

## 1. Arms

Every arm is a manual choice at Schwab. The taxable account is the robo account, or that same account after
leaving the program. The Roth is separate. Every arm receives the same contributions.

| Arm | Role | What the owner would do |
|---|---|---|
| **REF** | Reference for the loss bound and every Δ; never chosen | VOO in both accounts; the legacy balance switched to VOO at zero tax (frictionless) |
| **K0** | decision A, primary | Keep the robo (94 % ETFs / 6 % cash). New money into it. Harvesting requested; active only while the account is ≥ $50,000 |
| **K1** | decisions A and B, primary; **the default** (the tie-break) | Leave the program without selling. Keep the legacy ETFs, invest the 6 % cash in VOO, send new money to VOO. Never sell. Roth in VOO |
| K0_noTLH | sensitivity | K0 without ever harvesting |
| S0 | sensitivity | Sell the legacy long-term lots now, buy VOO |
| S1 | sensitivity | K1, then in each school year sell legacy lots up to the 0 % long-term-gain room, and harvest VOO gains with any room left |
| **B1** | decision B, primary | K1 in taxable. SSO (2× S&P 500) in the Roth, sized each January to the household lifecycle rule, cap 2×, bounded by Roth capacity |
| **B2** | decision B, primary | As B1, cap 1.5× |
| **B3** | decision B, primary | As B1 at a fixed household 1.25× |
| B4 | sensitivity | The B1 rule with SSO in the **taxable** account. It sells VOO lots highest-basis-first to re-lever, and any loss there is disallowed (§4). It de-levers by sending new money to VOO first, then by selling SSO, which is taxed |
| B1_upro, B2_upro, B3_upro | sensitivity | B1–B3 with UPRO (3×) in the Roth |

**Dropped, with reason.** None of these is in the study.
- **Roth futures:** Schwab requires $25,000 NLV in an IRA; the Roth holds $10–25k.
- **Box spread:** Schwab's treatment of short-box proceeds under ordinary margin could not be verified at
  this size; T-315/T-400 put it at the portfolio-margin tier ($110–125k).
- **Margin loan:** loses in every belief row at any rate more than 4.4 points above T-bills.
- **LEAPS:** T-396 (not cheaper; expires; a forced sale at the bottom for a never-seller; no price history).
- **Taxable futures:** one contract is about $38k of exposure, more than the 1.5× cap below ~$76k.
- **Target-date fund:** trails 1× by arithmetic and is tax-inefficient in taxable.
- **85/15 momentum:** B-9, not significant.
- **Shiller pre-1926 cohorts:** monthly-average prices; `xlrd` is not a declared dependency.

## 2. Owner inputs, defaults and the reported grid

| Input | Primary value | Reported sensitivities |
|---|---|---|
| Taxable robo balance | $25,000 (owner: under $50k) | $10,000; $45,000 |
| Embedded gain fraction g (unrealized gain ÷ balance) | 0.15 | 0.0 and 0.30 (decision-A arms at every g; decision-B arms at 0.15) |
| Roth balance | $15,000 (owner: $10–25k) | $10,000; $25,000 |
| Automatic taxable contribution | $500 a month, real, every month, through every fall (owner) | $250; $1,000; **none in school years** (`no_contrib_in_school`) |
| Roth contribution | $7,500 each January, pre-school and post-school | none after school (`no_roth_post_school`) |
| Roth in school years | **none (primary)** | the rule "contribute if wages ≥ the contribution" (`roth_in_school`) |
| School years | years 3–5 (owner: more than a year away) | from year 6 |
| Wages (real, single filer) | pre-school $60,000; school $8,000; post-school $160,000 | — |
| Wages in the year-40 liquidation | $160,000 real | — |
| State tax on investment income | 5 % flat [assumption] | — |
| Year-40 liquidation | through `annual_tax` | hold for step-up (no tax) |
| Robo harvest threshold θ (undisclosed) | 5 % below basis | 3 %; 10 % |
| Robo's realised sales per year ρ | 2 % of equity | 0 %; 5 % |

The grid runs at h = 0 and h = −2 pp, all 60 cohorts and 500 bootstrap paths per cell.

**Why no Roth contribution in school, and the open question about the taxable one.** $7,500 to the Roth
plus $6,000 to the taxable account is $13,500 a year on wages modelled at $8,000. No source says the owner
would do that. The project's own advisor memo says capacity "likely falls to ~zero" in school
(`docs/State/advisor_surface.md`). Revision 4 had the Roth contribution continuing under an older rule;
this revision makes **none** the primary and keeps the rule as a sensitivity. The taxable $500 a month
continues in the primary because the owner said the contributions are automatic. That statement was about
market falls, not school, so it is an assumption here. The `no_contrib_in_school` cell shows what dropping
it does.

## 3. Rows, the decision rule, the loss bound and the choice rule

### 3.1 The decision record

**The decision rows.** Single rows: `h=+0.00`, `h=-0.01`, `h=-0.02`, `h=-0.03` (the arithmetic equity return
shifted by h per year). Parameter-uncertainty rows: `param:h=+0.00`, `param:h=-0.02` (the same shift, and
each bootstrap path also draws δ ~ N(0, 1.83 pp) once).

**The decision rule: `pair`.** The owner said on 2026-11-20 that they have no view of future returns and do not
know how to decide. The director's ruling for that case (2026-11-24):

1. Read each decision (A and B) in **both** `param:h=+0.00` and `param:h=-0.02`.
2. If the two choices agree, that is the choice.
3. If they disagree, the choice is **K1**, the tie-break default, and the output flags the disagreement. If
   K1 itself fails the loss bound in that case, there is no choice (§3.3).
4. Both rows' choices are written out beside the resolved answer, for A and for B.

**Why a pair, and not one row.** The `param:h=+0.00` row means "as good as the last century". It tilts toward
leverage, so it is not a neutral default on its own. The second row asks whether the answer survives moving
the premium down two points a year. If it does not, the answer depends on a belief the owner says they do not
hold, and the simple default applies.

**Information order (disclosed).** The smoke run had already been executed and read before this rule was
chosen. On its 10-year cohorts starting 1990–96 with 16 paths, decision B came out **B1 at h = 0 and K1 at
h = −2**: the very flip the pair rule addresses. Those cells are plumbing, not evidence, and the rule
does not pick an answer. A reader should still know the order in which these things were seen. The
widened smoke of this revision (two parameter rows and a block run) ran **after** the rule was fixed. On it,
under the pair rule, decision A came out K1 and decision B came out K1 in both rows (16 paths, 10-year cohorts:
plumbing, not evidence).

**Override.** The owner may name one single row before the run. An override is recorded here:
**OVERRIDE = none as of 2026-11-24.** The run refuses to start without `--decision-row`; the row is checked
against the rows this configuration computes before any input is read.

### 3.2 Behaviour

Contributions continue monthly through every fall. No arm sells to cash. January leverage resets are
mechanical.

### 3.3 The loss bound (the owner's limit)

An arm is eligible only if its after-tax household wealth is ≥ **0.5 × REF** in **every one of the 60
unshifted US historical 40-year cohorts** (January starts 1927–1986): the history as it happened. Each row's
belief-shifted cohort minima are reported beside it and do not gate. JST (non-US) results are reported and
do not gate; the owner's limit is stated against the S&P 500.

### 3.4 The choice, per decision and per row

Candidates: K0 and K1 for decision A; K1, B1, B2 and B3 for decision B.
1. Keep the eligible candidates.
2. If K1 is not eligible, choose the highest E[log W] among the eligible and say so.
3. Otherwise scan the eligible non-default arms in descending E[log W]. For each, compute its **paired** lead
   over K1 on the row's 2,000 bootstrap paths (mean of log W_arm − log W_K1). Its band is max(2 × the
   paired Monte Carlo SE of that difference, the range of the lead across the block-length runs 12, 60 and
   120). The first arm whose lead exceeds its band is chosen.
4. If none does, choose **K1**.

Block runs use 2,000 paths each (seed 409 for the 60-month block; seed 409 + b for b = 12 and 120) and run in
**every** row. The parameter-uncertainty rows reuse the same δ draws in every block run. A top arm whose lead
is inside its own band does not block a lower arm whose lead is clearly outside its own. The output records
every contrast: lead, paired SE, the leads by block, the band, and whether it is distinct.

**The rule picks the best typical outcome.** E[log W] is maximised, which favours the middle of the range.
The arm with the highest **mean** terminal wealth is written on a separate line and never decides.

## 4. The model as implemented (`scripts/t409_real_money_home.py`)

**Time step.** Monthly. Daily-reset funds are built from French daily returns and compounded within each month.
Contributions arrive at the start of each month. Leverage resets happen each January after the contribution.
Distributions are reinvested monthly. Taxes are computed each December.

**Funds (per year), built on the French market (`Mkt-RF + RF`, CRSP value-weighted, gross of fees):**
- **VOO:** market − 0.03 %.
- **Robo ETFs:** market − 0.15 %.
- **SSO:** 2 × market − (bill + 0.57 % + 0.29 %) − 0.89 %.
- **UPRO:** 3 × market − 2 × (bill + 0.56 % + 0.29 %) − 0.90 %.

The bill is the French one-month bill. The 0.57 % and 0.56 % are B-5's measured swap spreads; the 0.29 pp is
B-5's financing base over that bill (T-399 R.6). Fees accrue by calendar days (/365.25); financing by
calendar days /360. Trading cost is 0.51 bp per traded dollar, charged on the Roth's leverage resets and on B4's
SSO trades.

**Belief shift.** Each fund's monthly return becomes (1 + R)·exp(k·h·Δt) − 1, with k its equity exposure
(VOO and robo 1, SSO 2, UPRO 3) and Δt the month's calendar years. This equals subtracting h from the daily
arithmetic return to within 2 × 10⁻⁴ a month.

**Distributions.** VOO pays Shiller's monthly D/P, fully qualified. The robo pays D/P + 0.6 pp, 80 %
qualified [assumption]. SSO pays 0.6 % and UPRO 0.5 % a year as ordinary income [census of 2006–2026
payouts].

**The robo (K0).** 6 % cash at the bill rate − 0.30 % (floored at 0; interest is ordinary income). Cash is
rebalanced to 6 % each December. ρ of equity is sold and rebought each December: gain lots realise the gain
pro rata, and loss lots are untouched (a loss on an immediate rebuy is a wash sale). Harvesting is requested,
active only while the account is ≥ **$50,000 nominal**, checked **monthly**, and uses a replacement on a
different index. Schwab checks daily, so the model understates harvesting, which favours K1.

**Lots.** One lot per fund per month. Sales take the highest basis per share first.† A lot is long-term once
12 months have passed. The legacy balance is one long-term lot with gain g of the whole balance; its cash
slice carries basis 1:1.

**Wash sales †** (Rev. Rul. 2008-5). A taxable loss on VOO, or on the robo's ETFs for K0, is disallowed when the
same fund is bought within 30 days. Monthly contributions make that every such loss; the disallowed amount
joins the replacement's basis. SSO is treated as not substantially identical to VOO. The Roth's purchases
of VOO are assumed not to add to this (taxable contributions already trigger it). Losses in a tax payment's
VOO or robo sale are covered too. A loss on SSO in taxable (B4) is allowed.

**Tax, each December (Form 1040 order).** The incremental federal tax the taxable account causes:
- **Taxable income:** wages + ordinary + qualified + the Schedule D line − the standard deduction. It may go
  negative before its zero floor, so wages under the deduction shelter investment income. Netting follows
  Schedule D (short against long; carryovers included).
- **Carryovers:** the Capital Loss Carryover Worksheet. The $3,000 deduction is not used up by a year whose
  taxable income is negative.
- **Preferential income:** the Qualified Dividends and Capital Gain Tax Worksheet, including its last step:
  the smaller of the worksheet's tax and the ordinary tax on all taxable income.
- **NIIT:** Form 8960, 3.8 % above $200,000 MAGI, counting the capped $3,000 loss.
- **Parameters:** 2026 single brackets (Rev. Proc. 2025-32 Table 3: 10 % to $12,400; 12 % to $50,400; 22 % to
  $105,700; 24 % to $201,775; 32 % to $256,225; 35 % to $640,600; 37 % above), the $16,100 standard
  deduction, and the 0 % / 15 % long-term rates to $49,450 / $545,500. These are CPI-indexed along the path;
  the $3,000 and the $200,000 are nominal-fixed.
- **State:** the flat rate on net investment income; no relief on losses.
- **Payment:** highest-basis-first sales whose gains fall into the next tax year; a negative bill is
  reinvested; if the account could not pay, the run halts.

**The Roth.** January contributions per §2. †The post-school contribution is assumed to be a backdoor Roth: the
2026 single phase-out is $153,000–$168,000 MAGI (IR-2025-111), and the modelled $160,000 sits inside it.

**S1.** Each school-year December, realise long-term gain up to the 0 % room left (found by bisection on
`annual_tax` itself, so it counts the unused deduction and any loss being absorbed): legacy lots first,
largest gain per dollar first, then VOO lots.

**Household leverage (B1–B3).** Each January: target L = min(cap, (W + PV)/W), with W real household wealth
and PV the present value at 1 % real of every scheduled contribution after this month. B3 uses L = 1.25.
Roth leverage = (L·W − taxable)/Roth, bounded to [1, 2] (SSO) or [1, 3] (UPRO). The SSO share is set then
drifts.

**B4.** The taxable account targets (L·W − Roth)/taxable ≤ 2 in SSO. The January contribution buys SSO first;
any remaining need is met by selling VOO lots, highest basis first, losses disallowed. It de-levers by sending
new money to VOO first, then by selling SSO, which is taxed.

**Terminal.** Every taxable lot is sold through `annual_tax` in a year with $160,000 real wages (20 % bracket
and NIIT included), net of carryforwards and of any disallowed loss still waiting for a replacement.
After-tax household wealth = Roth + taxable − that tax, in real 2026 dollars.

**Bootstrap.** Politis–Romano stationary bootstrap over months 1926-07 → 2026-09 (circular), mean block 60
months, 2,000 paths of 480 months, seed 409. The same draws feed every arm.

**Reported per arm × row × g:** median, mean, E[log W], certainty equivalent at risk aversion 2, ratio to REF
(5/50/95 %, minimum), largest real-dollar drawdown (median, 95 %), taxes paid, years of active harvesting,
0 % room used, gains realised de-levering. Bootstrap rows add Monte Carlo SEs, P(below REF) and P(balance
below contributions at year 20). Historical cohorts add shares of cohorts and the effective number of
independent windows, and no SE.

**Not modelled, and stated:** the US-vs-world mix of the robo (a belief); the kiddie tax (S1 is a sensitivity);
state relief on losses; AMT; the sweep's lag; daily harvesting; the phase-in of brackets between years other
than CPI.

**Disclosed generosities.** The sweep yield (bill − 0.30 %) is generous to K0. Monthly harvest checks
understate Schwab's daily checks, which favours K1.

## 5. Data

| Input | Source | md5 (pinned as `INPUT_MD5`) |
|---|---|---|
| French daily factors | Ken French library, CRSP 202609, 1926-07-01 → 2026-09-30 | `98fad1a66fe8c9e792fcd013b979b962` |
| CPI-U NSA | FRED `CPIAUCNS` | `74ac80ebee616f81dd98d5ec2a5934e1` |
| Dividend yield | repo `data/macro/shiller_ie_data.csv` (P, D) | `6e1e19fa864401cf66f8b022619efec1` |
| JST Macrohistory R6 | `macrohistory.net`, annual 1870–2020, 16 countries | `76884a335991ece55366255bd629d312` |

The French file's missing-data sentinels (−99.99 / −999) and any calendar hole over 15 days halt the run. Two
declared fills, and no others: **October 2025 CPI** (never published, geometric mean of its neighbours)
and **Shiller's last dividend yield** (2024-06, carried 27 months; cap 30). A re-fetch will not reproduce
the inputs, since French updates monthly and FRED adds a CPI month each month. The frozen copies are in
`/Users/jacksonmurphy/Dev/_research_snapshots/t409_real_money_home_2026-11-20/inputs/` (verified
2026-11-24: all four files match the pins; `manifest.json` md5 `6256b9d7592afb889af18b174b33ca2d`).

## 6. Positive controls (all halt the run; tolerance $1, the study path $0.01)

| Control | Target | Reproduced |
|---|---|---|
| T-399 bar, D-B 1968-01-02 → 2026-04-17, $10k | $3,363,893 | $3,363,892.93 |
| T-399 corrected static 2× | $8,864,568 | $8,864,568.00 |
| T-287 buy-hold (as published) | $929,498 | $929,498.35 |
| T-287 `schwab_like` (as published) | $494,701 | $494,701.10 |
| **Study path** | independent recurrence | see below |

**The study-path control** runs `simulate` on the 1990-01 window over 120 months with dividends zeroed and
state tax 0 (French loader → monthly panel → lot book → `annual_tax` at the final sale) and compares REF's
after-tax value with a separate recurrence. That recurrence has its own lot ages, its own contribution
schedule and the Rev. Proc. 2025-32 "$X plus Y %" bracket form. The value is **$415,477.1850** under this
revision's defaults, equal to the recurrence to the cent. Under revision 3's rules, pre-tax, the same code
gives $450,662.8196, the first reviewer's number.

**Diagnostics, never gating.** T-287's published inputs drop 64 SPY days (the T-297 class). Like for like,
calendar-complete buy-hold is $1,025,316 and the robo proxy $515,736 (ratio 1.99 vs 1.88).

## 7. The program's gate (reported, never deciding)

- **Static mixes, pre-tax, full L1 sample** (VOO; the robo mix 94 % robo ETFs + 6 % cash; a 1.25× SSO blend,
  0.75 VOO + 0.25 SSO, monthly): Δ log growth vs VOO and Sortino (monthly, 12 periods a year), each with a
  block-bootstrap CI (12-month blocks, 1,000 draws). Quoted with a CI and a t, so counted (§8).
- **Pass probabilities (stated before the run).** Leverage arms ≈ 0 by construction (best possible t for
  untimed leverage 2.63, the deflated bar 2.96 at N_eff 372). VOO beats the robo mix is likely to "pass",
  and would certify a certain-sign cost: cash drag and fees, nothing else.

## 8. Trial count — recommendation (the director rules at freeze)

**17, raw, per ruling 9.2:** 5 primary arms (K0, K1, B1, B2, B3); 7 sensitivity arms (K0_noTLH, S0, S1, B4,
B1–B3_upro); 3 JST analogs (household leverage, pre-tax, annual reset); 2 gate mixes. Rows, g levels, grid
cells, block lengths and θ/ρ/step-up variants are 0. N_eff 372 → ≈ 389, which changes no pass probability.

## 9. Run plan

1. Freeze: the SHA-256 of this file, the code and test blobs, and the input md5s, in the ledger row.
2. `run --jst --decision-row pair --progress` once, from the archived inputs; then a second run whose
   `results.md5` must match.
3. **Runtime.** 668,400 arm-paths (counted by `arm_path_total`). Each 40-year arm-path takes 2–5 ms on a
   synthetic panel; the delta reviewer's estimate is 55–100 minutes a run on real data. Plan for that, twice.

**Smoke (plumbing only; not evidence).** Results md5 **cb5d9ceaf68b3ee5ea4c5acdeb318c1e** (two runs identical). It changed from
revision 4's `82f77f1f…` because this revision changes the school-year Roth default, adds the last
worksheet step, and adds two parameter rows and a block run to the smoke itself.

## 10. Pre-stated expectations

Written before the full run, from the arithmetic in the earlier revisions, and not from any smoke.

| # | Expectation |
|---|---|
| E1 | K1 ≥ K0 at every g and row. In household terms the gap is ≈ 0.05–0.3 %/yr, and the year-40 NIIT and 20 % bracket may narrow it slightly (they fall on the arms that defer gains). K0_noTLH < K0 once the account passes $50k |
| E2 | S0 ≥ K1 when g ≤ 0.15, or in a year with 0 % room (the $60k pre-school wages leave $5,550). S1 ≥ S0 at g = 0.30 |
| E3 | The spread across decision-A arms is under 5 % of terminal wealth: 40 years of new money dominates the legacy balance |
| E4 | At r = 0.375, B1 ≈ B2 (SSO capacity 1.375× binds under both caps) |
| E5 | B arms lead K1 in E[log W] at h = 0 and −1, are within noise at −2, and trail at −3. The leads are smaller than T-396's uncapped +22 % because Roth capacity binds |
| E6 | Every primary arm meets the 0.5× bound in all 60 US cohorts. B1_upro comes closest |
| E7 | In JST, uncapped household leverage (cap 2) falls below 0.5× of 1× in at least one country's worst cohort |

Implied by E5: the pair's two rows may well **disagree** on decision B, in which case the rule returns K1. It
was written before the smoke showed the same shape.

## 11. Verification before freeze (done on this revision)

- **Tests:** 59 in `tests/test_t409_real_money_home.py` (58 without the data-backed control).
- **Mutants:** the delta reviewer's 45, re-run from their definitions, plus 16 new ones for the pair rule, the
  worksheet step, the guard and the early row check: all 45 of the reviewer's are killed (five with the pattern moved by this revision), and 15 of the 16 new ones; the survivor, N15 (the wash flag on SSO's tax payment), cannot be reached, because SSO pays tax only after VOO and the robo lots are exhausted.
- **Full suite** against a `git archive` baseline of the parent: 45 failed / 5,191 passed, exit 1, against 48 / 5,170 on the archive of `4e38476`; no failure appears only in the worktree, and the 3 only in the baseline are location-dependent.
- **Lints:** `doc_lint` and `honest_n_trials check` both exit 0.

## 12. Before freeze

- [ ] The director verifies this diff and rules the trial count (§8).
- [ ] Freeze record: the SHA-256 of this file plus Appendix A's blobs, the code commit, and the input md5s.
- [ ] Verify expense ratios and ProShares' distribution character; the † items to a professional before any
      real-money act.
- [ ] Run once; run again; md5 must match.

## Appendix A. Provenance (not normative) — SHA-256 and blobs

| Document | git blob | SHA-256 |
|---|---|---|
| Revision 1, `..._DRAFT_rev1_2026-11-19.md` | `04bb289c1604e956b806820f38d56c727f7cecff` | `1105eafd11565c09b87ba391c2252e54ccd050d48e13cbb6f066a2fbceebb3ba` |
| Revision 2, `..._DRAFT_rev2_2026-11-19.md` | `1dcaead73fa9600cb96f008d38a98d6ed10d3005` | `e3fe1183a589eed33b371cef634703caf7aef9635e22bc8a2f646ad4a9b44743` |
| Revision 3, `..._DRAFT_rev3_2026-11-20.md` | `85a3514566cf5d8cfb990cb78229efb015c95e62` | `0c3784219ae10fc8f86d39552caa092950e3c4ff6f7121bb77cfbb2271b37a68` |
| Revision 4, `..._DRAFT_rev4_2026-11-20.md` | `294a1e82e5a2e557e0a78c6e68e71c9b38cbab4f` | `5015732f01f51a631fd8e1407fd60895d2b898db8e66f96985b76ebb308f8cfa` |
| Study code, `scripts/t409_real_money_home.py` | `2233a2ed5ea6fc9c1fe4eeac5ed64b19409b6350` (commit da224b7) | `35ad9952140eb0ae9b264f8551e0356bc647548c4a4000c2a31cebbc70ab0e97` |
| Tests, `tests/test_t409_real_money_home.py` | `80332825d293b016d63e9f0593bcf735bba7bfa0` | `988f15191acce72956b26701854d5bb0f55857068f969c599eb091a35f4d42cb` |

The revision 1–4 files carry a supersession banner added after their own commits (revisions 1–3's blobs above
include the banner); their text below the banner is the original.

## References

- T-396 design note (`docs/Sources/design_note_lifecycle_leverage_t396_2026-11-14.md`); T-315/T-399
  (`docs/Audit/static_leverage_t315_2026_07_27.md`); T-287; T-311; T-318/T-320; B-5, B-9, B-10 verdicts;
  T-400, T-402; fresh-eyes audit 2026-11-14.
- IRS Rev. Proc. 2025-32 and 2026-35; IR-2025-111; Rev. Rul. 2008-5 (via T-402); Schwab Intelligent Portfolios
  brochure (2026-10-15).
- Jordà, Knoll, Kuvshinov, Schularick & Taylor (2019), QJE; Ayres & Nalebuff, *Lifecycle Investing*.
