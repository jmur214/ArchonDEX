---
task_id: T-409
title: DRAFT pre-registration (revision 3) — where should the owner's money sit? An after-tax household decision study of ordinary manual choices at Schwab (keep the robo; leave the program without selling; a broad index fund; a 2x index ETF in the Roth)
date: 2026-11-20
worker: edge-analyst (worktree agent-ac300c3d5f4eba52f)
revision: 3 (2026-11-20). It supersedes revision 2 (commit bd3e2c7, merged at c308078) after the owner's 2026-11-20 answers. Revision 2 is preserved verbatim at docs/Sources/prereg_real_money_home_t409_DRAFT_rev2_2026-11-19.md and revision 1 at docs/Sources/prereg_real_money_home_t409_DRAFT_rev1_2026-11-19.md; "rev. 2 §x" and "rev. 1 §x" point there.
status: DRAFT — NOT FROZEN. The study code exists (scripts/t409_real_money_home.py, tests/test_t409_real_money_home.py). Only its tests, its two positive controls and its --smoke mode were run. The smoke read real data, used 10-year cohorts on 1985-2026 and 16 bootstrap paths, and checked plumbing only. No parameter, arm or expectation in this file was changed after it. The full study has NOT been run. This file states NO trial count; §8 gives my recommendation for the director's ruling.
design_inputs: T-396 lifecycle-leverage note; T-399 corrected static leverage; T-400 household study; T-402 venue study; revisions 1 and 2 of this prereg
---

> **SUPERSEDED IN PART by revision 4** (`docs/Sources/prereg_real_money_home_t409_DRAFT_2026-11-19.md`,
> 2026-11-20), after the independent review by execution: 1 blocker, 10 required items, 6 minor. Revision 4
> §0 lists every change. Everything below this banner is revision 3 verbatim (commit `f6f5787`).

# T-409 DRAFT (rev. 3) — where the real money should sit, after tax

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
- **Your taxable robo holds under $50,000, so its tax-loss harvesting cannot switch on today.**
  - The robo's one advantage in a taxable account is therefore absent for now.
  - Its costs (6 % in cash, fund fees, taxable rebalancing trades) are not.
  - The default this study tests is **leaving the program without selling**: no tax is due, the cash gets
    invested, and new automatic contributions go to a plain index fund.
  - If you keep contributing, the account will pass $50,000 within a few years. The study also prices
    staying in the robo with harvesting switched on from that point.
- **Your unrealized gain matters only if you sell.** Leaving the program sells nothing, so the gain cannot
  change that default. The study reports selling options at three gain levels (0 %, 15 %, 30 % of the
  balance) for completeness.
- **Law school is more than a year away.** Selling inside the 0 % tax years is kept as a later-year option;
  its start year is a parameter.
- **Your Roth holds $10–25k.** That limits how much leverage the household can hold tax-free: a 2× fund in
  the Roth lifts the whole household only to about 1.2–1.5×. Futures in the Roth need $25,000 and are
  dropped.

**What the study will show you.**
- One table per belief about future stock returns: as good as the last century, or 1, 2 or 3 points a
  year worse. You pick the row you believe.
- Each option is shown after tax, in today's dollars, over 60 historical 40-year runs since 1927 and 2,000
  simulated ones.
- It reports which options never fall below half of the S&P 500 outcome in any historical run (your
  limit), and which one leaves the most money in your row.

**What it will not do.** It will not certify any choice as proven: the evidence cannot do that (§7). The
choice stays yours.

---

## 0. What changed from revision 2

| Revision 2 | Revision 3 |
|---|---|
| Owner facts mostly defaults | **Owner, 2026-11-20:** taxable robo < $50k; embedded gain not given (now a parameter, g ∈ {0, 0.15, 0.30}); law school more than a year away; Roth $10–25k (share r ≈ 0.2–0.5); every arm must be an ordinary manual choice at an institutional broker |
| Decision A: K0, K1, S0, S1 as arms | **K0 and K1 primary**; S0 and S1 are sensitivities only. S1's school start year is a parameter (default year 3; year 6 reported) |
| B5 Roth futures (conditional) | **Dropped:** Schwab requires $25,000 NLV for IRA futures; the Roth holds $10–25k |
| B6 box spread (conditional) | **Dropped:** Schwab's Reg-T treatment of short-box proceeds could not be verified at this size; T-315/T-400 place box financing at the portfolio-margin tier ($110–125k); the taxable balance is under $50k |
| B4 taxable-carried 2× lifecycle | **Sensitivity only.** Buying a 2× fund in a taxable account is an ordinary choice, but it is outside the owner's four options. It is kept to price the tax cost of leverage in taxable |
| L2 (Shiller pre-1926 cohorts) | **Dropped.** Shiller's prices are monthly averages, which distort the variance; the decision-A contrasts are near-deterministic tax arithmetic; and reading the .xls needs `xlrd`, which is not a declared dependency |
| Implementation unstated | §4 states the code's exact mechanics, including simplifications, each labelled |
| No positive controls | Two controls reproduce published numbers before any arm runs; the run halts otherwise (§6) |

## 1. Arms

Every arm is a manual choice at Schwab. The taxable account is the robo account (or the same account
after leaving the program). The Roth is separate. All arms receive the same contributions.

| Arm | Role | What the owner would do |
|---|---|---|
| **REF** | Reference for the loss bound and Δ (never chosen) | VOO in both accounts, the legacy robo balance switched to VOO **at zero tax** (frictionless) |
| **K0** | Decision A, primary | Keep the robo (aggressive: 94 % ETFs / 6 % cash). New money into the robo. Tax-loss harvesting requested; it is active only while the account is ≥ $50,000 |
| **K1** | Decision A, primary; **the simple default** (the tie-break) | Leave the program without selling. Keep the legacy ETFs, invest the 6 % cash in VOO, send new automatic contributions to VOO. Never sell. Roth in VOO |
| K0_noTLH | sensitivity | K0 without ever requesting harvesting |
| S0 | sensitivity | Sell the legacy ETFs now (long-term lots) and buy VOO |
| S1 | sensitivity | K1, then in each school year sell legacy lots up to the 0 % long-term-gain room and harvest VOO gains with any room left |
| **B1** | Decision B, primary | K1 in taxable. **SSO (2× S&P 500) in the Roth**, sized each January so the household follows the lifecycle rule (cap 2×), bounded by what the Roth can carry |
| **B2** | Decision B, primary | As B1, cap 1.5× |
| **B3** | Decision B, primary | As B1 at a fixed household 1.25× |
| B4 | sensitivity | The B1 rule implemented with SSO in the **taxable** account (de-lever by contributions first; sales taxed) |
| B1_upro, B2_upro, B3_upro | sensitivity | B1–B3 with UPRO (3×) in the Roth |
| Dropped | — | B5 Roth futures; B6 box spread; margin loans (lose in every belief row, rev. 2 §3.6); LEAPS (T-396); taxable futures (granularity); target-date fund and 85/15 (rev. 2 §0) |

## 2. Owner inputs, defaults and the reported grid

| Input | Primary value | Reported sensitivities |
|---|---|---|
| Taxable robo balance B | $25,000 (owner: under $50k) | $10,000; $45,000 |
| Embedded gain fraction g (unrealized gain ÷ balance) | 0.15 | 0.0 and 0.30 (decision-A arms at every g; decision-B arms at 0.15) |
| Roth balance | $15,000 (owner: $10–25k), share r = 0.375 | $10,000 (r 0.29); $25,000 (r 0.5) |
| Automatic taxable contribution | $500 a month, real, every month, through every fall (owner) | $250; $1,000 |
| Roth contribution | $7,500 each January of an earned-income year; none in school years | — |
| School years | years 3–5 (owner: more than a year away) | starting year 6 |
| Wages (real, single filer) | pre-school $60,000; school $8,000; post-school $160,000 | — |
| State tax on investment income | 5 % flat [assumption] | — |
| Year-40 liquidation | (15 % + state) × the taxable account's embedded gain | hold for step-up (no tax) |
| Robo harvest threshold θ (undisclosed) | 5 % below basis | 3 %; 10 % |
| Robo's realised rebalancing sales ρ | 2 % of equity a year | 0 %; 5 % |

The grid runs at h = 0 and h = −2 pp with all 60 cohorts and 500 bootstrap paths per cell.

## 3. Belief rows, the loss bound, and the owner's choice rule

- **Belief rows:** h ∈ {0, −1, −2, −3} pp a year on the arithmetic equity return (rev. 2 §4.6), plus the
  parameter-uncertainty row (each path draws δ ~ N(0, 1.83 pp)) at h = 0 and h = −2.
- **Loss bound (owner):** an arm is eligible only if its after-tax household wealth is ≥ **0.5 × REF** in
  **every** US historical 40-year cohort (January starts 1927–1986, 60 cohorts).
- **Behaviour (owner):** contributions continue monthly through every fall; no arm sells to cash. The
  January leverage reset is a mechanical rebalance inside the Roth.
- **Choice rule.**
  - In the owner's belief row, among eligible arms, choose the highest E[log after-tax household wealth]
    over the bootstrap paths.
  - Candidates are K0 and K1 for decision A, and K1, B1, B2 and B3 for decision B.
  - A lead smaller than max(2 × the Monte Carlo SE of the paired Δ log, the spread across block lengths
    12 / 60 / 120 at h = 0) is a tie. A tie goes to **K1**.
- JST (non-US) results are reported but do not enter eligibility. The owner's limit is stated against the
  S&P 500.

## 4. The model as implemented (`scripts/t409_real_money_home.py`)

**Time step.** Monthly. Daily-reset funds are built from French daily returns and compounded within each
month. Contributions arrive at the start of each month. Leverage resets happen each January after the
contribution. Distributions are reinvested monthly. Taxes are computed each December.

**Funds (per year):**
- **VOO:** market (French Mkt-RF + RF, CRSP value-weighted, gross) − 0.03 %.
- **Robo equity:** market − 0.15 %.
- **SSO:** 2 × market − (bill + 0.57 % + 0.29 %) − 0.89 %.
- **UPRO:** 3 × market − 2 × (bill + 0.56 % + 0.29 %) − 0.90 %.
- The 0.29 pp is B-5's financing base over the French bill (T-399 R.6).
- Fees accrue by calendar days (/365.25), financing by /360.

**Belief shift.** Each fund's monthly return is multiplied by exp(k·h·Δt), with k its equity exposure (1,
1, 2, 3). This equals subtracting h from the daily arithmetic return to within 2 × 10⁻⁴ a month (test
`test_monthly_belief_shift_matches_the_daily_arithmetic_shift`).

**Distributions:**
- VOO pays Shiller's monthly D/P, fully qualified.
- The robo pays D/P + 0.6 pp, 80 % qualified [assumption].
- SSO pays 0.6 % a year and UPRO 0.5 %, as ordinary income (census, rev. 2 §6).

**Robo (K0):**
- 6 % cash at the bill rate − 0.30 % (floored at 0), interest taxed as ordinary income.
- Cash is rebalanced to 6 % each December.
- ρ of equity is sold and rebought each December.
- Harvesting is checked **monthly** while the account is ≥ $50,000 nominal. Schwab checks daily, so the
  model understates harvesting, which favours K1 [labelled].
- No wash sales are modelled between the robo and the Roth. The location rule (rev. 2 §4.5) keeps the
  Roth in SSO/VOO, which differ from the robo's ETFs.†

**Lots:**
- One lot per fund per month.
- Sales take the highest basis per share first.†
- A lot counts as long-term once 12 months have passed since its purchase month.
- The legacy balance is one long-term lot with gain g of the whole balance; the cash slice carries basis
  1:1.

**Tax, each December.** The incremental federal tax the taxable account causes:
- **Brackets and thresholds:** 2026 single brackets (Rev. Proc. 2025-32, table 3: 24 % to $201,775, 32 % to
  $256,225, 35 % to $640,600), the $16,100 standard deduction, and the 0 % / 15 % long-term rates to $49,450
  / $545,500. All are CPI-indexed along the path.
- **Losses:** short- and long-term netting, the $3,000 offset, and carryforwards by character.
- **NIIT:** 3.8 % above $200,000 MAGI.
- **Nominal-fixed items:** the $3,000 and the $200,000 are fixed in nominal dollars and deflated along the
  path.
- **State:** the flat rate on net investment income.
- **Payment:** the bill is paid by highest-basis-first sales, whose gains fall into the next tax year. A
  negative bill (the $3,000 offset) is reinvested. If the account could not pay, the run halts.

**S1.** Each school-year December, realise legacy long-term gains (largest gain per dollar first) up to the
0 % room left that year, then harvest VOO long-term gains with the rest.

**Household leverage (B1–B3).**
- Each January: target L = min(cap, (W + PV)/W). W is real household wealth; PV is the present value at 1 %
  real of every scheduled contribution after this month. B3 uses L = 1.25.
- Roth leverage = (L·W − taxable)/Roth, bounded to [1, 2] (SSO) or [1, 3] (UPRO).
- The Roth's SSO share is set and then drifts until the next January.

**B4.** The taxable account targets (L·W − Roth)/taxable ≤ 2 in SSO. It buys with the January contribution
first, then sells VOO loss lots. It de-levers by sending new money to VOO first, then by selling SSO,
which is taxed.

**Terminal.**
- After-tax household wealth = Roth + taxable − (15 % + state) × (embedded gain − carryforwards).
- It is reported in real 2026 dollars; the step-up sensitivity drops the liquidation tax.

**Not modelled, and stated:**
- international diversification (a belief, rev. 2 §4.6);
- the kiddie tax (the owner did not report dependency status; S1 is a sensitivity);
- state tax relief on losses;
- AMT;
- the sweep yield's lag;
- daily harvesting.

## 5. Data (all free; md5 pinned at freeze)

| Input | Source | md5 (fetched 2026-11-20) | Note |
|---|---|---|---|
| French daily factors | `F-F_Research_Data_Factors_daily_CSV.zip`, CRSP 202609 | `98fad1a66fe8c9e792fcd013b979b962` | 1926-07-01 → 2026-09-30; −99.99/−999 sentinels halt |
| CPI-U NSA | FRED `CPIAUCNS` via the API (key from `.env`, never printed) | `74ac80ebee616f81dd98d5ec2a5934e1` | **October 2025 was never published** (federal shutdown). It is the one declared gap, filled by the geometric mean of its neighbours; any other gap halts |
| Dividend yield | repo `data/macro/shiller_ie_data.csv` (read-only copy) | `6e1e19fa864401cf66f8b022619efec1` | Dividends end 2024-06; the last D/P is carried 27 months (cap 30, else halt) |
| JST Macrohistory R6 | `macrohistory.net` | `76884a335991ece55366255bd629d312` | L3, pre-tax, annual reset; 16 countries |
| Control inputs | repo `data/` files, read-only, md5-pinned in the code | see `CONTROL_FILES` | T-306 substrate; T-287's SPY / bond / gold / DGS3MO / T-284 curves |

Commands (also added to `docs/Core/execution_manual.md`):

```
python -m scripts.t409_real_money_home fetch --inputs DIR --shiller-csv <repo>/data/macro/shiller_ie_data.csv --env-file <repo>/.env --jst
python -m scripts.t409_real_money_home run --inputs DIR --out DIR --control-root <repo> --jst [--smoke]
```

`run` refuses an output directory under `<repo>/data/`.

## 6. Positive controls (run before any arm; the run halts if either misses by more than $1)

| Control | Published | Reproduced | Pass |
|---|---|---|---|
| T-399 corrected, D-B 1968-01-02 → 2026-04-17, $10k: the 1× bar | $3,363,893 | $3,363,892.93 | yes |
| T-399 corrected static 2× | $8,864,568 | $8,864,568.00 | yes |
| T-287 buy-hold SPY TR, $7k each January from 2000-10-30 | $929,498 | $929,498.35 | yes |
| T-287 `schwab_like` proxy, same schedule | $494,701 | $494,701.10 | yes |

- **The controls prove the shared primitives**: the levered-fund formula, the positional year mask,
  monthly robo rebalancing, January contributions and input alignment. **The tax engine is proven
  separately** by hand-computed cases and the Rev. Proc. bracket table (tests).
- **A defect the second control exposed.** It is reported as a diagnostic, never gating:
  - **T-287's published figures drop 64 SPY trading days.** These are bond-market holidays such as
    Columbus Day, Veterans Day and Christmas Eve, lost because T-284's curves and T-287's inner join sit on
    the bond synthetic's calendar. This is the T-297 defect class.
  - Calendar-complete, buy-hold is **$1,009,638** (not $929,498) and the robo proxy **$515,736** (not
    $494,701): a ratio of 1.96 rather than 1.88.
  - Every place that quotes "$929k vs $495k" understates both. This needs a health_check row (the
    director's).

## 7. The program's gate (reported, never deciding)

- **Static mixes, pre-tax, full L1 sample.** VOO, the robo mix and a 1.25× SSO blend: Δ log growth vs VOO
  and Sortino (monthly, 12 periods), each with a block-bootstrap CI (`MetricsEngine.bootstrap_distribution`,
  12-month blocks, 1,000 draws).
- **Cohort arms.** The distribution of Δ log terminal across the 60 cohorts.
- **Pass probabilities (rev. 2 §4.9 stands):**
  - leverage arms ≈ 0 by construction;
  - A0-style contrasts (VOO beats the robo mix) likely "pass" but certify a certain-sign cost: cash drag
    and fees.

## 8. Trial count — my recommendation (the director rules at freeze)

**Recommend 15, counted raw per ruling 9.2:**

| Unit | Count |
|---|---|
| Primary arms quotable against the bar: K0, K1, B1, B2, B3 | 5 |
| Sensitivity *arms*, each a distinct configuration: K0_noTLH, S0, S1, B4, B1_upro, B2_upro, B3_upro | 7 |
| JST pre-tax analogs (lifecycle cap 2, cap 1.5, static 1.25) on a new substrate | 3 |
| Belief rows, g levels, owner-grid cells, block lengths, θ / ρ / step-up variants | 0 |

The zero line covers sensitivities of the same configurations, per the T-315/T-399 convention. REF is a
reference and is not counted.

**Why raw:**
- Any of the 15 could be quoted against the bar. Ruling 9.2 grants no correlation credit.
- At 15, N_eff 372 → ≈ 387 and E[max] 2.96 → ≈ 2.97. That changes no pass probability here.

The lower defensible count is **5**, if the director rules the sensitivity arms and the JST analogs at 0 as
reported sensitivities. I do not recommend it: S0, S1 and B4 are different actions, not parameter values.

## 9. Run plan

1. Freeze: this file's SHA-256, the input manifest md5s and the code commit in the ledger row.
2. `fetch` into a fresh directory; the manifest must equal the frozen md5s.
3. `run` once (2,000 paths; measured 2–5 ms per 40-year arm-path, about 15–20 minutes on one core).
4. Run it a second time; the results md5 must match.
5. Independent review by execution.

**Smoke (plumbing only, not evidence).** Two runs on 2026-11-20 gave identical results md5
`838fb3a7db294e971efa8e9931b428c4`. The arms differ as built:
- S0 at g = 0 equals REF exactly;
- B1 and B2 coincide where Roth capacity binds;
- every control passed.

## 10. Pre-stated expectations (from rev. 2 §3 arithmetic; not from the smoke)

| # | Expectation |
|---|---|
| E1 | K1 ≥ K0 at every g and row. In household terms the gap is ≈ 0.05–0.3 %/yr (the robo is part of the household). K0_noTLH < K0 once the account passes $50k |
| E2 | S0 ≥ K1 when g ≤ 0.15, or in a year with 0 % room (pre-school $60k wages leave $5,550). S1 ≥ S0 at g = 0.30 |
| E3 | The spread across decision-A arms is under 5 % of terminal wealth: 40 years of new money dominates the legacy balance |
| E4 | At r = 0.375, B1 ≈ B2 (SSO capacity 1.375× binds under both caps) |
| E5 | B arms lead K1 in E[log W] at h = 0 and −1, are within noise at −2, and trail at −3. The leads are smaller than T-396's household-uncapped +22 % because Roth capacity binds |
| E6 | Every primary arm meets the 0.5× bound in all 60 US cohorts. B1_upro comes closest |
| E7 | In JST, uncapped household leverage (cap 2) falls below 0.5× of 1× in at least one country's worst cohort, so a world reading of the owner's limit would be stricter than the US one |

## 11. What remains open with the owner

- **The belief row:** after the run.
- **Nothing else blocks the run;** the grid covers the owner's ranges.
- **One fact would sharpen it:** the exact taxable balance and the monthly contribution. Both decide when
  the robo would cross $50k and switch harvesting on. That matters only if the owner would stay in the
  robo, and E1 says staying loses.
- **One Schwab check before acting on K1:** does leaving the program keep the positions untouched in the
  same account? (T-402 §3: probably yes, not stated in words.)

## 12. Before freeze

- [ ] Independent code review by execution, including the tests, the controls and a re-derivation of the
      tax cases.
- [ ] The director rules the trial count (§8) and the default wage path.
- [ ] Verify the expense ratios (VOO, SSO, UPRO, the robo's ETFs) and ProShares' distribution character.
- [ ] The † items to a professional before any real-money act (not before the run).
- [ ] Freeze, fetch, run once, determinism ×2.
