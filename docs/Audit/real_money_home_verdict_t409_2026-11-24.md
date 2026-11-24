---
task_id: T-409
title: Where the owner's real retirement money should sit — the frozen study's result
date: 2026-11-24
author: edge-analyst (quantitative lens)
outcome: The pre-registered rule returns K1 for decision A (leave the robo program without selling) and B1 for decision B (SSO in the Roth, lifecycle rule, cap 2x). Both pair rows agree. The program's gate cannot certify the leverage choice (t 1.50 against a bar of 2.96). Three of the prereg's own expectations were wrong, E5 most of all.
---

# T-409 verdict — where the real money should sit (2026-11-24)

**This is a decision aid for ordinary manual choices at a broker. It is not financial advice, and it is not a
deployment of this project's trading machine. Nothing here involves the machine, its paper accounts or its
strategies. The choice stays the owner's.**

Frozen by `docs/Sources/freeze_real_money_home_t409_2026-11-24.md` (main `d109f84`). Prereg:
`docs/Sources/prereg_real_money_home_t409_DRAFT_2026-11-19.md` (revision 5). Decision rule: `pair`. Owner
override: none. Trials recorded: 17.

## For the owner, in plain words

The study asked two questions and answered each one twice: once assuming stocks do as well as in the last
century, and once assuming they do 2 points a year worse. Both readings gave the same answer to both questions.

**Question A: keep the robo, or leave the program without selling? Answer: leave without selling.**
- Leaving means: no sale, no tax bill, the 6 % cash gets invested, and new automatic contributions go to a plain
  S&P 500 index fund.
- After 40 years the typical outcome is about **4.4 % higher** than keeping the robo if stocks do as well as
  before (about $2.93 million against $2.81 million, in today's dollars, after tax), and about **2.8 % higher**
  if they do 2 points worse ($1.70 million against $1.66 million).
- The size of that gap is uncertain by about a quarter of a point either way. Its direction is not in doubt in
  this model: it is fees and idle cash, which are costs with a known sign. The robo finished behind the plain
  S&P 500 reference in all 60 historical 40-year runs.
- The dollar totals themselves are very uncertain. They move by more than a million dollars between the two
  readings. Only the comparison between options is firm.

**Question B: plain index fund in the Roth, or a 2x S&P 500 fund (SSO) in the Roth? Answer by the rule: the 2x
fund, sized by the lifecycle rule with a 2x cap (option B1).**
- Typical outcome: about **43 % higher** than the plain default if stocks do as well as before ($4.27 million
  against $2.93 million), and about **23 % higher** if they do 2 points worse ($2.12 million against $1.70
  million).
- **This is a bet, not a sure thing.** In the simulated futures the 2x option ended *below* the plain S&P 500
  outcome about 1 time in 9 in the first reading and about 1 time in 4 in the second. In the worst simulated
  futures it ended with about 62–66 % of the plain outcome. It never fell below half, which was your limit.
- In all 60 real historical 40-year runs in the United States it finished ahead of the plain S&P 500. That is
  one country's history, and those 60 runs overlap so heavily that they are worth about two and a half
  independent tries.
- Other countries were less kind. A household-level version of the same rule, tested on 16 countries, finished
  behind plain stocks in the typical case in France, Italy, Norway and Portugal, and at about 53 % of plain
  stocks in France's worst run.
- **The study cannot certify this choice as proven.** The project's own evidence bar asks for far more data than
  a century holds. The rule picks the option with the best typical outcome among those that kept your loss
  limit; it does not say the future will resemble the past.
- The ride is rougher. The typical largest dollar fall along the way is about $1.85 million with the 2x fund
  against $1.25 million without it, and the chance of being behind your own contributions at year 20 is about
  10 % against 6 % (20 % against 14 % in the weaker reading).

**What was wrong in the plan's own expectations.** Before the run, the plan expected the two readings to
*disagree* on question B, which would have returned the simple default. They agreed. The plan also expected the
2x option to be no better than a coin flip at 2 points worse, and to lose at 3 points worse. It led clearly in
both. Read §6 before relying on the answer.

## 1. Controls and determinism

Two full runs from a clean `git archive` of main `d109f84`; the three frozen SHA-256s were verified before the
start. Both exited 0. Run A took 58 minutes, run B 54.

| Item | Value |
|---|---|
| `results.md5`, run A and run B | `3552302266143a77f9cb340ccbaecdcd` (identical; the two `results.json` are byte-identical) |
| Control `t399_bar` | target 3,363,893; reproduced 3,363,892.93; pass |
| Control `t399_static_2x` | target 8,864,568; reproduced 8,864,568.00; pass |
| Control `t287_bh_spy` | target 929,498; reproduced 929,498.35; pass |
| Control `t287_schwab_like` | target 494,701; reproduced 494,701.10; pass |
| Control `study_path_REF` | independent 415,477.1850; simulate 415,477.1850; pass |
| Census | panel 1926-07 to 2026-09 (1,203 months); 60 cohorts (1927–1986 starts); 2,000 bootstrap paths per cell (500 in the owner grid); 2,000 per block run; dividend yield carried 27 months; input md5s equal the pins |
| Effective independent windows | 2.475 (60 overlapping 40-year cohorts) |

Durable copies: `/Users/jacksonmurphy/Dev/_research_snapshots/t409_real_money_home_2026-11-20/runs/` (`run_A`,
`run_B`, both logs).

## 2. The decision record

| Decision | `param:h=+0.00` | `param:h=-0.02` | Agree | Resolved |
|---|---|---|---|---|
| A (keep the robo or leave) | K1 | K1 | yes | **K1** |
| B (leverage in the Roth) | B1 | B1 | yes | **B1** |

Contrasts: the paired lead over K1 in E[log W], with its band (the larger of 2 × the paired Monte Carlo SE and
the range across block lengths 12 / 60 / 120). The band covers simulation and block-length noise only. It does
not cover uncertainty about the future equity premium; the rows do that.

| Row | Arm | Lead over K1 | Paired MC SE | Leads by block (60 / 12 / 120) | Band | Distinct |
|---|---|---|---|---|---|---|
| `param:h=+0.00` | K0 | −0.0446 | 0.0007 | −0.0446 / −0.0456 / −0.0434 | 0.0022 | no (it trails) |
| `param:h=+0.00` | B1 | +0.3577 | 0.0062 | +0.3577 / +0.3497 / +0.3498 | 0.0124 | yes |
| `param:h=+0.00` | B2 | +0.3498 | 0.0059 | +0.3498 / +0.3423 / +0.3419 | 0.0118 | yes |
| `param:h=+0.00` | B3 | +0.3542 | 0.0068 | +0.3542 / +0.3634 / +0.3459 | 0.0175 | yes |
| `param:h=-0.02` | K0 | −0.0284 | 0.0006 | −0.0284 / −0.0296 / −0.0273 | 0.0023 | no (it trails) |
| `param:h=-0.02` | B1 | +0.2092 | 0.0060 | +0.2092 / +0.2055 / +0.2017 | 0.0121 | yes |
| `param:h=-0.02` | B2 | +0.2051 | 0.0058 | +0.2051 / +0.2020 / +0.1979 | 0.0116 | yes |
| `param:h=-0.02` | B3 | +0.1796 | 0.0059 | +0.1796 / +0.1920 / +0.1719 | 0.0201 | yes |

- Eligible under the 0.5× bound: K0 and K1 (decision A); K1, B1, B2 and B3 (decision B).
- **B1 and B2 are not distinguishable from each other**: their leads differ by 0.008 and 0.004, inside either
  band. The rule takes the first distinct arm in E[log W] order, which is B1.
- Highest **mean** arm (reported, never decides): K1 for A in both rows; **B3** for B in both rows
  ($8.65 million against B1's $7.67 million at `param:h=+0.00`; $3.82 million against $3.66 million at
  `param:h=-0.02`).
- The four single rows give the same choices: A → K1 and B → B1 at h = 0, −1, −2 and −3. B1's lead over K1 is
  +0.356, +0.280, +0.204 and +0.128 (bands 0.010–0.011, all distinct). K0's is −0.044, −0.036, −0.028 and
  −0.020.

## 3. Every arm

Real dollars, after tax, household (taxable + Roth), year 40. Δlog is the mean of log(W / W_REF) with ± 2
Monte Carlo SE. "P below REF" is the share of bootstrap paths ending below the reference.

### 3.1 Bootstrap, the two decision rows (g = 0.15)

| Row | Arm | Median | Mean | Δlog vs REF (± 2 SE) | P below REF | Ratio to REF: 5th pct / worst path |
|---|---|---|---|---|---|---|
| `param:h=+0.00` | REF | 2,957,381 | 4,474,575 | 0 | — | 1 / 1 |
| | K0 | 2,811,482 | 4,129,233 | −0.0545 ± 0.0015 | 0.956 | 0.896 / 0.852 |
| | K0_noTLH | 2,770,985 | 4,085,131 | −0.0683 ± 0.0012 | 0.997 | 0.890 / 0.850 |
| | K1 | 2,927,467 | 4,421,062 | −0.0099 ± 0.0002 | 1.000 | 0.984 / 0.975 |
| | S0 | 2,955,750 | 4,471,690 | −0.0005 ± 0.0000 | 0.966 | 0.999 / 0.997 |
| | S1 | 2,947,402 | 4,453,639 | −0.0033 ± 0.0001 | 0.971 | 0.992 / 0.986 |
| | B1 | 4,270,058 | 7,671,612 | +0.3478 ± 0.0122 | 0.114 | 0.891 / 0.656 |
| | B2 | 4,265,102 | 7,542,673 | +0.3400 ± 0.0117 | 0.111 | 0.895 / 0.657 |
| | B3 | 4,068,133 | 8,652,919 | +0.3444 ± 0.0136 | 0.125 | 0.876 / 0.603 |
| | B4 | 3,538,838 | 5,696,693 | +0.1603 ± 0.0063 | 0.133 | 0.920 / 0.778 |
| | B1_upro | 5,142,277 | 9,895,978 | +0.5493 ± 0.0159 | 0.071 | 0.937 / 0.622 |
| | B2_upro | 4,671,016 | 8,235,114 | +0.4304 ± 0.0116 | 0.055 | 0.992 / 0.686 |
| | B3_upro | 4,529,111 | 9,625,178 | +0.4349 ± 0.0142 | 0.079 | 0.942 / 0.653 |
| `param:h=-0.02` | REF | 1,718,474 | 2,470,959 | 0 | — | 1 / 1 |
| | K0 | 1,656,062 | 2,328,809 | −0.0365 ± 0.0014 | 0.898 | 0.915 / 0.870 |
| | K0_noTLH | 1,630,068 | 2,299,158 | −0.0526 ± 0.0011 | 0.990 | 0.907 / 0.867 |
| | K1 | 1,702,997 | 2,446,811 | −0.0080 ± 0.0002 | 1.000 | 0.986 / 0.977 |
| | S0 | 1,718,139 | 2,469,739 | −0.0004 ± 0.0000 | 0.915 | 0.999 / 0.998 |
| | S1 | 1,717,029 | 2,462,550 | −0.0024 ± 0.0001 | 0.938 | 0.994 / 0.988 |
| | B1 | 2,117,463 | 3,656,785 | +0.2011 ± 0.0120 | 0.243 | 0.791 / 0.619 |
| | B2 | 2,113,059 | 3,616,684 | +0.1971 ± 0.0115 | 0.238 | 0.793 / 0.620 |
| | B3 | 1,971,644 | 3,818,928 | +0.1716 ± 0.0118 | 0.280 | 0.801 / 0.576 |
| | B4 | 1,907,443 | 2,947,514 | +0.0900 ± 0.0063 | 0.278 | 0.868 / 0.753 |
| | B1_upro | 2,497,285 | 4,535,968 | +0.3574 ± 0.0159 | 0.177 | 0.794 / 0.586 |
| | B2_upro | 2,318,537 | 3,928,108 | +0.2806 ± 0.0117 | 0.152 | 0.854 / 0.617 |
| | B3_upro | 2,145,586 | 4,162,312 | +0.2467 ± 0.0123 | 0.194 | 0.853 / 0.619 |

The Monte Carlo SE of each arm's own E[log W] is 0.018–0.026, so a median dollar figure carries roughly ± 4–5 %
of simulation noise (2 SE) on top of the much larger difference between rows. The decision-A arms at g = 0 and
g = 0.30 differ from the g = 0.15 figures by under 0.2 % (the full grid is in `results.json`).

### 3.2 Bootstrap, the single rows (g = 0.15; median, Δlog vs REF, P below REF)

| Arm | h = 0 | h = −1 | h = −2 | h = −3 |
|---|---|---|---|---|
| REF | 2,889,194 | 2,177,405 | 1,658,648 | 1,284,770 |
| K0 | 2,730,466; −0.054; 0.97 | 2,081,164; −0.044; 0.95 | 1,602,041; −0.035; 0.92 | 1,250,793; −0.027; 0.87 |
| K0_noTLH | 2,701,976; −0.067; 1.00 | 2,055,401; −0.059; 1.00 | 1,575,679; −0.052; 1.00 | 1,229,273; −0.044; 0.99 |
| K1 | 2,860,728; −0.010; 1.00 | 2,157,740; −0.009; 1.00 | 1,646,417; −0.008; 1.00 | 1,276,726; −0.007; 1.00 |
| S0 | 2,887,539; −0.001; 0.98 | 2,176,494; −0.000; 0.96 | 1,658,168; −0.000; 0.93 | 1,284,628; −0.000; 0.89 |
| S1 | 2,880,315; −0.003; 0.98 | 2,173,181; −0.003; 0.96 | 1,656,413; −0.002; 0.94 | 1,283,773; −0.002; 0.91 |
| B1 | 4,138,202; +0.346; 0.09 | 2,915,014; +0.271; 0.14 | 2,050,288; +0.196; 0.21 | 1,458,091; +0.121; 0.32 |
| B2 | 4,132,425; +0.338; 0.08 | 2,892,031; +0.266; 0.14 | 2,041,345; +0.193; 0.20 | 1,457,011; +0.119; 0.31 |
| B3 | 4,021,542; +0.329; 0.10 | 2,742,890; +0.239; 0.16 | 1,915,350; +0.155; 0.25 | 1,375,404; +0.079; 0.37 |
| B4 | 3,444,425; +0.162; 0.10 | 2,505,148; +0.127; 0.17 | 1,836,257; +0.090; 0.25 | 1,377,813; +0.051; 0.35 |
| B1_upro | 4,996,547; +0.548; 0.05 | 3,417,713; +0.450; 0.08 | 2,371,085; +0.351; 0.14 | 1,678,873; +0.251; 0.22 |
| B2_upro | 4,485,354; +0.430; 0.04 | 3,171,460; +0.354; 0.07 | 2,224,051; +0.277; 0.12 | 1,576,204; +0.199; 0.19 |
| B3_upro | 4,377,061; +0.418; 0.04 | 2,985,472; +0.319; 0.09 | 2,072,022; +0.228; 0.15 | 1,465,094; +0.146; 0.25 |

The ± 2 SE on Δlog is 0.009–0.014 for the leverage arms and at most 0.0013 for the others. The worst
bootstrap path of any primary arm in any row is 0.576 of REF (B3, h = −3 and `param:h=-0.02`).

### 3.3 The 60 historical cohorts (g = 0.15)

These are shares of overlapping cohorts, not probabilities: about 2.48 independent windows. The loss bound reads
the **unshifted** column.

| Arm | Median, unshifted | Mean, unshifted | Δlog vs REF | Worst ratio to REF: unshifted | h = −1 | h = −2 | h = −3 | Share of cohorts below REF: unshifted / −2 / −3 | Meets 0.5× |
|---|---|---|---|---|---|---|---|---|---|
| REF | 2,559,977 | 2,695,514 | 0 | 1.000 | 1.000 | 1.000 | 1.000 | — | — |
| K0 | 2,468,052 | 2,553,187 | −0.053 | 0.923 | 0.934 | 0.945 | 0.956 | 1.00 / 1.00 / 1.00 | yes |
| K0_noTLH | 2,432,922 | 2,522,670 | −0.065 | 0.915 | 0.926 | 0.936 | 0.947 | 1.00 / 1.00 / 1.00 | yes |
| K1 | 2,546,145 | 2,671,229 | −0.009 | 0.986 | 0.988 | 0.988 | 0.990 | 1.00 / 1.00 / 1.00 | yes |
| S0 | 2,559,208 | 2,694,170 | −0.001 | 0.999 | 0.999 | 0.999 | 0.999 | 1.00 / 1.00 / 0.95 | yes |
| S1 | 2,556,511 | 2,686,746 | −0.003 | 0.992 | 0.993 | 0.994 | 0.995 | 1.00 / 1.00 / 1.00 | yes |
| B1 | 3,880,262 | 3,974,216 | +0.386 | 1.034 | 0.954 | 0.896 | 0.852 | 0.00 / 0.15 / 0.25 | yes |
| B2 | 3,665,819 | 3,923,956 | +0.373 | 1.045 | 0.967 | 0.900 | 0.854 | 0.00 / 0.15 / 0.25 | yes |
| B3 | 3,134,372 | 3,743,869 | +0.304 | 1.057 | 0.977 | 0.910 | 0.853 | 0.00 / 0.12 / 0.40 | yes |
| B4 | 2,900,887 | 3,271,722 | +0.196 | 1.010 | 0.975 | 0.948 | 0.922 | 0.00 / 0.20 / 0.30 | yes |
| B1_upro | 4,723,807 | 4,847,174 | +0.581 | 1.095 | 0.978 | 0.891 | 0.815 | 0.00 / 0.15 / 0.22 | yes |
| B2_upro | 4,080,962 | 4,269,735 | +0.459 | 1.163 | 1.080 | 1.002 | 0.932 | 0.00 / 0.00 / 0.13 | yes |
| B3_upro | 3,428,955 | 4,061,639 | +0.386 | 1.132 | 1.042 | 0.968 | 0.905 | 0.00 / 0.03 / 0.13 | yes |

**Not in the frozen output:** the worst cohort in dollars. The output stores the worst cohort as a ratio to the
reference, not as a dollar level, and the code was not changed to add it. Every arm meets the 0.5× bound with
wide room: the closest is K0_noTLH at 0.915, and among the primary arms K0 at 0.923.

## 4. Sensitivities and the owner grid

**No cell changes either decision's direction.** The grid runs at h = 0 and h = −2 with 500 paths and no block
runs, so the pre-registered band cannot be computed there. The figures below are the lead over K1 in E[log W],
with an unpaired 2 SE that overstates the noise (± 0.002–0.004 for K0, ± 0.019–0.023 for B arms).

| Cell | K0 − K1 (h = 0 / −2) | B1 − K1 (h = 0 / −2) | Top of K1, B1, B2, B3 by E[log W] (h = 0 / −2) |
|---|---|---|---|
| Roth $10,000 | −0.046 / −0.029 | +0.353 / +0.200 | B1 / B1 |
| Roth $25,000 | −0.042 / −0.027 | +0.374 / +0.215 | B1 / B1 |
| Taxable $10,000 | −0.042 / −0.028 | +0.378 / +0.215 | B1 / B1 |
| Taxable $45,000 | −0.048 / −0.029 | +0.342 / +0.196 | **B3** / B1 |
| School from year 6 | −0.044 / −0.029 | +0.369 / +0.210 | B1 / B1 |
| Contribution $250 a month | −0.030 / −0.017 | +0.380 / +0.224 | B1 / B1 |
| Contribution $1,000 a month | −0.066 / −0.045 | +0.325 / +0.176 | **B3** / B1 |
| No taxable contribution in school | −0.038 / −0.024 | +0.378 / +0.215 | B1 / B1 |
| Roth contribution in school | −0.040 / −0.026 | +0.372 / +0.217 | B1 / B1 |
| No Roth contribution after school | −0.077 / −0.051 | +0.302 / +0.156 | **B3** / **B2** |
| Harvest threshold 3 % | −0.044 / −0.028 | +0.362 / +0.206 | B1 / B1 |
| Harvest threshold 10 % | −0.046 / −0.029 | +0.362 / +0.206 | B1 / B1 |
| Robo sales 0 % a year | −0.037 / −0.023 | +0.362 / +0.206 | B1 / B1 |
| Robo sales 5 % a year | −0.054 / −0.035 | +0.362 / +0.206 | B1 / B1 |
| Hold for step-up at year 40 | −0.061 / −0.039 | +0.341 / +0.196 | B1 / B1 |
| Embedded gain g = 0 and 0.30 (decision A) | −0.043 to −0.045 / −0.027 to −0.028 | — | — |

- **What does not change:** K1 leads K0 in every cell and row, and a leverage arm leads K1 by 0.16–0.38 in every
  cell and row. Every primary arm meets the 0.5× bound in every cell (the lowest unshifted worst ratio is K0's
  0.881 with no Roth contributions after school).
- **What changes is which leverage arm is on top**, in three cells: B3 at h = 0 with $45,000 taxable, $1,000 a
  month, or no Roth contributions after school; B2 at h = −2 in the last. The top arm's margin over B1 is
  0.013, 0.023 and 0.059 at h = 0 and 0.0004 at h = −2, against an unpaired 2 SE of about 0.02 that overstates
  the noise. The no-Roth-after-school cell at h = 0 (B3 by 0.059) is clearly outside it; the $1,000 cell may be;
  the grid's output cannot settle it. That cell is the owner with two Roth contributions ever, where Roth capacity
  binds hardest.
- **Sensitivity arms.** S0 (sell the legacy lots now) leads K1 by 0.005–0.010 at every g and row, and S1 leads
  K1 by 0.005–0.007. B4 (SSO in taxable) leads K1 by about half of B1's lead and pays about twice the lifetime
  tax (median $660,547 against $331,772 in the unshifted cohorts). B1_upro and B2_upro lead B1 by 0.08–0.20 in
  every row and B3_upro by 0.02–0.09; they are sensitivities and were never candidates.

## 5. The gate, the JST analogs and the reset calibration

**Gate (reported, never deciding): cannot certify the leverage choice, as stated before the run.** Pre-tax
static mixes on the full sample, block bootstrap.

| Mix | Δ log growth vs VOO, per year | Bootstrap CI | t | Sortino (point; CI low – high) |
|---|---|---|---|---|
| VOO | — | — | — | 0.839; 0.500 – 1.256 |
| Robo mix (94 % ETFs, 6 % cash) | −0.42 % | −0.66 % to −0.17 % | −3.33 | 0.844; 0.505 – 1.263 |
| 1.25× SSO blend | +0.79 % | −0.26 % to +1.75 % | +1.50 | 0.790; 0.455 – 1.194 |

- The deflated bar is 2.96. The leverage blend's t is 1.50 and its interval includes zero.
- The robo mix trails VOO with |t| 3.33, above the bar: a cost with a certain sign (cash drag and fees), as
  expected.
- The three Sortino intervals overlap almost entirely. Leverage raised growth and did not raise Sortino.

**JST analogs (pre-tax, household-level, annual reset, not bounded by Roth capacity; they do not gate).** Ratio
of terminal wealth to 1× over every 40-year window.

| Country (windows) | Lifecycle cap 2×: worst / median | Lifecycle cap 1.5×: worst / median | Static 1.25×: worst / median |
|---|---|---|---|
| AUS (69) | 0.884 / 1.304 | 0.935 / 1.188 | 0.885 / 1.238 |
| BEL (68) | 0.754 / 1.036 | 0.836 / 1.037 | 0.742 / 0.960 |
| CHE (82) | 0.809 / 1.148 | 0.895 / 1.132 | 0.835 / 1.082 |
| DEU (45) | 0.796 / 1.191 | 0.925 / 1.104 | 0.795 / 1.001 |
| DNK (107) | 0.757 / 1.022 | 0.850 / 1.029 | 0.833 / 0.986 |
| ESP (40) | 0.980 / 1.278 | 1.008 / 1.125 | 0.860 / 1.042 |
| FIN (86) | 0.938 / 1.427 | 1.060 / 1.295 | 0.774 / 1.204 |
| FRA (65) | **0.530** / 0.942 | 0.662 / 0.950 | 0.711 / 0.881 |
| GBR (111) | 0.600 / 1.169 | 0.770 / 1.129 | 0.766 / 1.052 |
| ITA (60) | 0.680 / 0.980 | 0.770 / 0.887 | 0.679 / 0.823 |
| JPN (55) | 0.958 / 1.192 | 0.819 / 1.096 | 0.770 / 0.978 |
| NLD (82) | 0.599 / 1.336 | 0.721 / 1.232 | 0.840 / 1.120 |
| NOR (101) | 0.625 / 0.955 | 0.749 / 0.987 | 0.768 / 0.986 |
| PRT (102) | 0.643 / 0.891 | 0.653 / 0.911 | 0.543 / 0.917 |
| SWE (111) | 0.615 / 1.169 | 0.732 / 1.153 | 0.671 / 1.144 |
| USA (110) | 0.798 / 1.187 | 0.901 / 1.095 | 0.819 / 1.128 |

No analog falls below 0.5× in any country. The lowest is France at 0.530 (cap 2×). The cap-2× median is below 1
in France, Italy, Norway and Portugal.

**`us_reset_calibration`** (the same household rule on the 60 US cohorts, both ways):

| Rule | Annual reset: median / worst | Daily reset (SSO): median / worst |
|---|---|---|
| Lifecycle cap 2× | 1.499 / 0.900 | 1.533 / 1.031 |
| Lifecycle cap 1.5× | 1.365 / 0.979 | 1.367 / 1.066 |
| Static 1.25× | 1.233 / 1.018 | 1.300 / 1.056 |

On US data the annual-reset approximation is the more pessimistic of the two, by 0.04–0.13 at the worst cohort.

## 6. Surprises, and where the output contradicts the prereg's expectations

| # | Expectation | Result |
|---|---|---|
| E1 | K1 ≥ K0 at every g and row; K0_noTLH < K0 | **Held.** K1 leads K0 by 0.020–0.045 in E[log W] (about 0.05–0.11 % a year) |
| E2 | S0 ≥ K1 when g ≤ 0.15; S1 ≥ S0 at g = 0.30 | **First half held; second half wrong.** S0 leads K1 at every g including 0.30. S1 trails S0 at g = 0.30 in every row, by 0.0001–0.0011 |
| E3 | Decision-A spread under 5 % of terminal wealth | **Wrong at h = 0, by a little.** K0 trails REF by 5.2–5.4 % at h = 0 and by under 5 % at h = −1 to −3. K0_noTLH trails by 6.5 %, 5.8 % and 5.0 % at h = 0, −1 and −2 |
| E4 | B1 ≈ B2 | **Held.** They differ by 0.004–0.008 |
| E5 | B arms lead K1 at h = 0 and −1, are within noise at −2, and trail at −3 | **Wrong at −2 and −3.** B1 leads K1 by +0.204 at −2 and +0.128 at −3, both far outside the band (0.010–0.011). The implied disagreement of the pair's rows did not happen |
| E6 | Every primary arm meets 0.5× in all 60 cohorts; B1_upro closest | **First half held; second half wrong.** No leverage arm came near the bound in US history (every one finished above REF in all 60 unshifted cohorts). The closest arms are the robo arms (0.915, 0.923) |
| E7 | In JST, cap-2 household leverage falls below 0.5× in at least one country's worst cohort | **Wrong.** The lowest is 0.530 (France) |

**What E5 means for how much weight the answer can bear.** The pair rule was designed around an expected flip
between the two rows. The flip did not occur at −2, nor at −3 in the single rows. The lead falls by about 0.075
per point of h, so the straight-line zero is near −4.7 points a year; that is an extrapolation outside the rows
that were run, not a result. The pre-run arithmetic behind E5 was therefore too pessimistic about leverage in
this model, and I have not found the reason inside the frozen output. Two candidates, neither tested: the
earlier arithmetic may have under-weighted that the lifecycle rule levers mainly while the Roth is small and
contributions are still ahead; and the financing cost is a fixed 0.86 points over bills in every row, so a
lower equity premium is not accompanied by a higher borrowing spread. A reader should treat the size of the
leverage lead with more caution than its sign.

Other things that surprised me:
- **Every leverage arm beat the reference in all 60 unshifted US cohorts**, B4 included (worst 1.010). That is a
  statement about one country's century, with about 2.5 independent windows.
- **The highest-mean arm differs from the chosen arm in both pair rows** (B3 against B1). B3's mean is 4–13 %
  above B1's while its median is 5–7 % below: a few very good paths pull its average up.
- **Harvesting was active in a median of 38 of 40 years** for K0, and K0 still trails K1 in every row and cell.
- **The UPRO sensitivity arms lead the SSO arms in every row** and also met the bound. They were never
  candidates, and nothing here chooses them.
- **Leverage did not improve risk-adjusted return** in the gate's static mixes: Sortino 0.790 (CI low 0.455) for
  the 1.25× blend against 0.839 (CI low 0.500) for VOO.

## 7. What this result is, and is not

- **It is** the output of a rule fixed before the run: for an owner with no view of returns, a 40-year horizon,
  contributions that continue through every fall, and a stated loss limit of half the S&P 500 outcome.
- **It is not certified.** The gate's t for leverage is 1.50 against a bar of 2.96, and a century of one
  country's data cannot clear that bar for untimed leverage (best possible t 2.63). The evidence cannot decide
  whether the next 40 years will pay for leverage; the rule only says which option had the best typical outcome
  under two stated beliefs while keeping the loss limit.
- **Not modelled:** a closure or redesign of SSO; a change in its fees or financing spread; Roth rule changes; a
  change in the owner's behaviour in a deep fall (the model assumes none); any country but the United States in
  the decision itself.
- **Decision A rests on firmer ground than decision B.** It is a cost difference with a certain sign, and the
  gate's robo-mix contrast clears the bar. Decision B is a risk choice.
- Every option is a manual choice at a broker. None involves this project's machine.


---

## Addendum 2026-11-24 — independent reconciliation with the T-396 note (director)

The T-396 design note gave the lifecycle rule +22 / +10 / −1 / −12 % at 0 / −1 / −2 / −3 pp. This study gives about +0.36 / +0.28 / +0.20 / +0.13 in E[log W] over K1. An independent reviewer reconciled the two by execution, read-only, on the frozen code and inputs. **No defect in the frozen T-409 code changes a decision. The gap is mostly an error in T-396's arithmetic.**

The ladder at h = −2 pp (B1 − K1, mean Δ log terminal wealth; 300 of the run's own paths, noise about ±0.016):

| Step | B1 − K1 | Moves |
|---|---|---|
| 0 Frozen T-409 | +0.189 | — (full run: +0.204) |
| 1 All money in the Roth, no tax | +0.243 | +0.054 |
| 2 T-396's money ($10k, $5k a year) | +0.244 | 0 |
| 3 T-396's premium base (7.10 % not 8.25 %) | +0.142 | −0.102 |
| 4 T-396's vehicle cost | +0.174 | +0.032 |
| 5 Independent daily normal returns | +0.148 | −0.026 |
| 6 T-396's expected-path arithmetic | −0.013 | −0.161 |

- **The T-396 error (step 6).** It valued each contributed dollar at its median growth path and summed. That is exact for a lump sum and biased toward 1× for a contribution stream. The reviewer's own independent simulation gives +0.153 at −2 pp where the recurrence gives −0.013.
- **The premium base (step 3).** T-409 starts from the 1926–2026 premium, T-396 from 1968–2025.
- **Checks on T-409, all passing.** The belief shift reaches the levered fund. The modelled 2× fund tracks the real SSO from 2006 (CAGR 15.02 % vs 15.30 %; 2008 −67.5 % vs −67.9 %; worst drawdown −84.5 % vs −84.7 %). Financing is charged daily on the bill rate. There is no look-ahead. The bootstrap's bad 20-year stretches are harsher than US history, but far milder than the 16-country JST record.
- **What the result turns on.** The forward equity premium over bills: the lead shrinks about 0.076 log per point and reaches zero near h ≈ −4.7 pp (an arithmetic premium of about 3.5 %/yr). A world-like future is the real risk.
- **Decision A stands.** K1 − K0 is +0.027 to +0.039 across sweep-yield assumptions.

The gate still cannot certify the leverage choice (t 1.50 against 2.96). It remains a belief decision, the owner's.
