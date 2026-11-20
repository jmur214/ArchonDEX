---
task_id: T-409
title: DRAFT pre-registration (revision 4) — where should the owner's money sit? An after-tax household decision study of ordinary manual choices at Schwab (keep the robo; leave the program without selling; a broad index fund; a 2x index ETF in the Roth)
date: 2026-11-20
worker: edge-analyst (worktree agent-ac300c3d5f4eba52f)
revision: 4 (2026-11-20). It supersedes revision 3 (commit f6f5787) after the independent review by execution of 23f6286. Revisions 1-3 are preserved verbatim at docs/Sources/prereg_real_money_home_t409_DRAFT_rev{1,2}_2026-11-19.md and _rev3_2026-11-20.md; "rev. N §x" points there.
status: DRAFT — NOT FROZEN. The full study has NOT been run. Only the tests (41), the five positive controls and --smoke were run. The smoke read real data (10-year cohorts on 1985-2026, 16 paths) for plumbing only; no parameter, arm or expectation was set from it. The owner's decision row is NOT YET recorded (§3); the freeze requires it. This file states NO trial count; §8 gives my recommendation.
design_inputs: T-396; T-399; T-400; T-402; revisions 1-3 of this prereg; the reviewer's findings (2026-11-20)
---

# T-409 DRAFT (rev. 4) — where the real money should sit, after tax

> † marks a tax or broker rule this study models but a professional or the broker should confirm before
> anyone acts. This is the owner's own research platform; it is not tax advice.

## For the owner, in plain words

**Every option in this study is an ordinary choice you would make yourself at Schwab:**
- keep the robo;
- leave the robo program without selling;
- buy a plain index fund;
- hold a 2× index fund in your Roth.

**Nothing here involves this project's trading machine, its paper accounts or its strategies.**

**What your answers settle** (unchanged from revision 3):
- **Harvesting cannot switch on today.** Your taxable robo holds under $50,000. The default being tested
  is leaving the program without selling: no tax, the cash gets invested, new money goes to an index fund.
- **Your unrealized gain matters only if you sell.**
- **Law school is more than a year away.** Selling in the 0 % tax years is kept as a later option.
- **Your $10–25k Roth limits household leverage to about 1.2–1.5×.**

**One thing we need from you before the run: which belief row you will decide on.**
- The rows are future stock returns as good as the last century, or 1, 2 or 3 points a year worse.
- There is also an "uncertain" version of the first and third: the same average, plus the honest
  uncertainty about it.
- Fixing the row *before* the results exist is what keeps the answer honest. It is written into the
  frozen plan, and the run refuses to start without it.

**What the study will show.** For your row, it shows:
- each option after tax, in today's dollars;
- which options never fell below half of the S&P 500 outcome in any of 60 real historical 40-year runs;
- which option leaves the most money.

It will not certify any choice as proven. The choice stays yours.

---

## 0. What changed from revision 3 (the review, 2026-11-20)

| # | Finding | Revision 4 |
|---|---|---|
| 1 (blocker) | The tie band took the largest block spread over **every** arm, sensitivity arms included; it ran only at h = 0 on 500-path block runs; its "paired SE" was the larger of two SEs vs REF; a top arm that tied returned K1 even when a lower arm clearly led | §3.4: the band is **per decision and per contrast**: max(2 × the paired MC SE of (arm − K1), the range of (arm − K1) across block lengths 12 / 60 / 120). Block runs use **2,000 paths** each (seeds 409 + block), at **every** decision row. Arms are scanned in descending E[log W]; the first whose lead exceeds its band is chosen, otherwise K1 |
| 2 | The decision row was chosen after the run | §3.1: `--decision-row` is required for the full run and recorded in the frozen file |
| 3 | The parameter-uncertainty row had no choice and no K0 | It runs every arm and has a full choice (§3.4) |
| 4 | Overlapping cohorts carried SEs and probabilities | Cohort rows carry `share_of_cohorts_below_ref` and `effective_independent_windows` (≈ 2.48), and no SE |
| 5 | Input md5s not pinned; a regenerated manifest accepted a tampered file | `INPUT_MD5` in code; `run` halts on any difference. Durable archive (§5): proposal only |
| 6 | The year-40 sale ignored NIIT and the 20 % bracket | It goes through `annual_tax` at the liquidation year's wages (default $160k real); step-up is the sensitivity |
| 7 | The robo's sell-and-rebuy harvested losses for free | Sold-and-rebought lots realise **gains only**: a loss on an immediate rebuy is a wash sale |
| 8 | Roth income phase-out ignored; school-year rule contradicted rev. 2 §4.4 | †Backdoor Roth after school (2026 single phase-out $153,000–$168,000, IR-2025-111, read 2026-11-20); sensitivity: no Roth after school. School years follow rev. 2 §4.4 (contribute iff wages ≥ the contribution; $8,000 ≥ $7,500, so yes); sensitivity: none in school |
| 9 | The controls did not exercise the study path | A fifth control: the study's own path vs an independent recurrence (§6) |
| 10 | Wages below the standard deduction mis-taxed; carryover and QDCG worksheet gaps; NIIT ignored the $3,000 offset | Form 1040 order (§4), locked by hand cases and a 3,000-case fuzz against an independently written 1040 path |
| 11 | The loss bound was read on belief-shifted cohorts | §3.3: eligibility on the **unshifted** history; each row's shifted cohort minima are reported beside |
| 12 | Wash sales between the accounts were ignored | A taxable VOO or robo-ETF loss is disallowed when that fund is bought within 30 days. New money buys VOO (or the robo's ETFs, for K0) every month, so every such loss qualifies; the basis moves to the replacement lot |
| 13 | B4's text said "VOO loss lots" | §1: B4 sells VOO lots highest-basis-first; any loss is wash-disallowed, per item 12 |
| 14 | The data/ guard could be bypassed by a symlink | Checked against `<control-root>/data` and the script's own `data/`, literal and resolved |
| 15 | The T-287 diagnostic was not like for like | Calendar-complete buy-hold, fee-free like the published curve: **$1,025,316** (ratio 1.99 vs 1.88) |
| 16 | Silent cohort skip; `--jst` optional; "the only exception" | Each of the 60 starts must fit or the run halts; `--jst` is mandatory on the full run; two declared fills (§5) |
| 17 | Gate mixes uncounted | They are quoted with a CI and a t, so they count (§8) |

## 1. Arms (unchanged except B4's wording)

| Arm | Role | What the owner would do |
|---|---|---|
| REF | Reference for the bound and every Δ (never chosen) | VOO in both accounts; the legacy balance switched at zero tax |
| **K0** | decision A | Keep the robo (94 % ETFs / 6 % cash); new money into it; harvesting requested, active ≥ $50,000 |
| **K1** | decision A and B; **the default** | Leave the program without selling; the cash and all new money to VOO; never sell |
| K0_noTLH, S0, S1 | sensitivities | Never harvest; sell now; sell inside school-year 0 % room |
| **B1 / B2 / B3** | decision B | K1, plus SSO in the Roth: household lifecycle cap 2× / cap 1.5× / static 1.25×, bounded by Roth capacity |
| B4 | sensitivity | The B1 rule with SSO in taxable. It sells VOO lots highest-basis-first to re-lever, and any loss there is wash-disallowed. It de-levers by contributions first, then taxed SSO sales |
| B1–B3_upro | sensitivities | UPRO in the Roth |
| Dropped | — | Roth futures; box spread; margin; LEAPS; taxable futures; target-date fund; 85/15 (rev. 3 §1) |

## 2. Owner inputs and the reported grid

As rev. 3 §2, with these changes:
- the Roth rules of §0 item 8;
- year-40 liquidation through `annual_tax` at $160k real wages;
- two added grid cells: no Roth after school, and no Roth in school.

## 3. Rows, the decision row, the loss bound and the choice rule

**3.1 The decision row.** One of:
- `h=+0.00`, `h=-0.01`, `h=-0.02`, `h=-0.03`;
- `param:h=+0.00`, `param:h=-0.02` (the same h, each path also drawing δ ~ N(0, 1.83 pp)).

The owner states it before the freeze. **It is recorded here at freeze: DECISION ROW = ____ (pending the
owner, asked 2026-11-20).** The full run refuses to start without `--decision-row`. The output's
`decision` block is the choice in that row; every other row is reported, not decided on.

**3.2 Behaviour.** Contributions continue monthly through every fall. No arm sells to cash. January
leverage resets are mechanical.

**3.3 The loss bound.**
- An arm is eligible only if its after-tax household wealth is ≥ 0.5 × REF in **every one of the 60
  unshifted US historical cohorts**: the history as it happened, January starts 1927–1986.
- Each row's belief-shifted cohort minima are reported beside, and do not gate.
- JST results are reported and do not gate.

**3.4 The choice, per decision.** The candidates are K0 and K1 for decision A, and K1, B1, B2 and B3 for
decision B.
1. Keep the eligible candidates.
2. If K1 is not eligible, choose the highest E[log W] among the eligible and say so.
3. Otherwise, scan the eligible non-default arms in descending E[log W].
   - For each, compute its **paired** lead over K1 on the decision row's 2,000 bootstrap paths:
     mean of log W_arm − log W_K1.
   - Its band is max(2 × the paired MC SE of that difference, the range of the lead across the
     block-length runs 12, 60 and 120). Each block run uses 2,000 paths: seed 409 for 60, 409 + b for the
     others. The parameter-uncertainty rows reuse the same δ draws in every block run.
   - The first arm whose lead exceeds its band is chosen.
4. If none does, choose **K1**.

So a top arm whose lead is inside its own noise does not block a lower arm whose lead is clearly outside
its own. The output records every contrast: lead, paired SE, block leads, band, distinct.

## 4. The model as implemented

As rev. 3 §4, with these changes.

**Tax engine (Form 1040 order).**
- **Taxable income:** wages + ordinary + qualified + the Schedule D line − the standard deduction.
  - It may go negative before its zero floor, so wages under the deduction shelter investment income.
  - Netting follows Schedule D lines 7 / 15 / 16 / 21.
- **Carryovers:** the Capital Loss Carryover Worksheet. A year with negative taxable income does not use
  up the $3,000.
- **Preferential income:** the Qualified Dividends and Capital Gain Tax Worksheet, lines 4–17, including
  its "smaller of" steps.
- **NIIT:** Form 8960, counting the capped $3,000 loss.
- **School-year 0 % room:** found by bisection on `annual_tax` itself.

**Year 40.** Every taxable lot is sold through `annual_tax` in a liquidation year with $160k real wages,
so NIIT and the 20 % bracket apply.

**Wash sales (†).** A taxable loss on VOO, or on the robo's ETFs for K0, is disallowed when the same fund
is bought within 30 days. Monthly contributions make that every such loss. The disallowed amount joins
the replacement's basis.
- The robo's December sell-and-rebuy realises the gain of each gain lot pro rata and leaves loss lots
  untouched.
- The robo's own harvesting (into a different-index replacement) is allowed.
- SSO is treated as not substantially identical to VOO.

**Roth.** As §0 item 8.

**Disclosed generosities.** The sweep yield (bill − 0.30 %) is generous to K0: the real sweep follows a
money fund's net yield with a lag. Monthly harvest checks understate Schwab's daily checks, which favours
K1.

## 5. Data (pinned in code; two declared fills)

- **Pinned files.** `INPUT_MD5` holds the four inputs fetched 2026-11-20 (rev. 3 §5); `run` halts on any
  other bytes.
- **Two declared fills.**
  - October 2025 CPI, never published: the geometric mean of its neighbours.
  - Shiller's last dividend yield, carried 27 months (cap 30).
  - Any other gap halts.
- **A re-fetch will not reproduce the inputs.** French updates monthly and FRED adds a CPI month each
  month. The frozen files are the only reproducible inputs.
- **Durable archive (proposal, for the director).** Copy the four files and their `manifest.json`:
  - to `/Users/jacksonmurphy/Dev/_research_snapshots/t409_real_money_home_2026-11-20/inputs/`, outside
    the repo, following T-398's precedent;
  - **and** to an S3 prefix under the project bucket;
  - before freeze, recording both md5 lists in the ledger row.
  - The fetch step and the run read any `--inputs` directory, and tests never write there. I did not
    write outside the scratchpad.

## 6. Positive controls (all halt the run; tolerance $1, the study-path control $0.01)

| Control | Target | Reproduced |
|---|---|---|
| T-399 bar, D-B 1968-01-02 → 2026-04-17, $10k | $3,363,893 | $3,363,892.93 |
| T-399 corrected static 2× | $8,864,568 | $8,864,568.00 |
| T-287 buy-hold (as published) | $929,498 | $929,498.35 |
| T-287 `schwab_like` (as published) | $494,701 | $494,701.10 |
| **Study path:** REF via `simulate`, 1990-01 for 120 months (see below) | independent recurrence | **$486,231.4866 = $486,231.4866** |

**How the study-path control is built.**
- **What `simulate` runs:** French daily loader → monthly panel → lot book → `annual_tax` at the final
  sale, on the pinned inputs, with dividends zeroed and state tax 0.
- **What the recurrence uses instead:** separate code, its own Roth schedule, its own lot ages, and
  Rev. Proc. 2025-32's published "$X plus Y %" bracket form.
- **Check against the reviewer's value:** the reviewer's $450,662.8196 is reproduced exactly by the new
  code under revision 3's rules (no Roth in school, no year-40 tax).

**Diagnostics, never gating.** T-287's published inputs drop 64 SPY days. Like for like, calendar-complete
buy-hold is **$1,025,316** and the robo proxy $515,736 (ratio 1.99).

## 7. The program's gate (reported, never deciding)

As rev. 3 §7. The two pre-tax gate mixes (the robo mix and the 1.25× SSO blend vs VOO) are quoted with a
block-bootstrap CI and a t, so they are counted (§8).

## 8. Trial count — recommendation (the director rules at freeze)

**Recommend 17, raw per ruling 9.2:**

| Unit | Count |
|---|---|
| Primary arms: K0, K1, B1, B2, B3 | 5 |
| Sensitivity arms: K0_noTLH, S0, S1, B4, B1–B3_upro | 7 |
| JST analogs | 3 |
| §7 gate mixes | 2 |
| Rows, g levels, grid cells, block lengths | 0 |

The effect is N_eff 372 → ≈ 389, which changes no pass probability.

## 9. Run plan

1. Owner's decision row recorded here; archive the inputs (§5); freeze (SHA-256 of this file, input
   md5s, code commit).
2. `run --jst --decision-row <row>` once; then a second run must match the results md5.
3. Estimated runtime 35–45 minutes on one core (2,000-path block runs now at every row).
4. Independent delta review by execution.

**Smoke (plumbing only).** Results md5 `82f77f1f74edb4ac869478d7cd8ac524`, identical over two runs. It
changed from rev. 3's `838fb3a7…` because the review fixes change every after-tax number:
- the Roth school-year rule;
- the year-40 sale through `annual_tax`;
- wash sales;
- the robo's gains-only rebalancing;
- the tax engine;
- the new output fields and the study-path control.

## 10. Pre-stated expectations

Rev. 3 §10 E1–E7 stand. One revision is made before any full run, because of review fix 6: **E1's K1 − K0
gap may narrow slightly**. The year-40 sale now charges deferred gains NIIT and the 20 % bracket, which
were previously missing to the benefit of the arms that defer gains (K1, REF).

## 11. Before freeze

- [ ] The owner's decision row (§3.1).
- [ ] Inputs archived durably (§5); md5s in the ledger row.
- [ ] Delta review by execution of the fixes and their reversion proofs.
- [ ] The director rules the trial count (§8).
- [ ] Verify expense ratios and ProShares' distribution character; the † items to a professional before any
      real-money act.
- [ ] Freeze, run once, determinism ×2.
