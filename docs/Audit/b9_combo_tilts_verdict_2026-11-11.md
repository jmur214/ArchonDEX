---
task_id: T-380 (B-9)
title: "B-9 multi-factor combination tilts at deployable weights (VOO / MTUM / AVUV) — VERDICT"
date: 2026-11-11
author: regime-analyst subagent (dispatched by the director)
outcome: "H1 NOT MET — arm (i) 60/20/20 Δ log TW vs 1× SPY-TR +0.279 (terminal wealth ×1.32), block-bootstrap ci_low −0.241 (block 7; −0.477 at block 60). REFUTED per the prereg: multi-factor closed, momentum stays at 15%. No arm clears ci_low > 0. The power premise failed on both inputs: measured t 1.24 against a predicted 2.2; realized ρ of the two tilts' active returns −0.07, not −0.3; the AVUV leg's tracking error 19.9%/yr, not 8%."
status: "FINAL pending director review. Pre-cutover substrate: re-verify required after cutover ([NN-SUBSTRATE-REVERIFY]). N_trials consumed: 1."
reproduce: "python -m scripts.tilt_decision_measure_t318_t320 --b9 (reads only the md5-manifested snapshot data/research/b9/inputs/); results md5 6368f5c6e901d600dd889e5a3fc06d3f must reproduce (bit-identical ×2 on 2026-11-11)"
---

# B-9: two factor tilts together do not beat 1× SPY at deployable weights. H1 NOT MET.

**Pre-registration:** `docs/Sources/prereg_b9_combo_tilts_2026-11-11.md`. It was drafted at `16432da`
and frozen there by the director on 2026-11-11 with Option A. Amendment 1 (`60e51a5`, input check (d))
was committed before the data fetch.
**Script:** `scripts/tilt_decision_measure_t318_t320.py`, which this work extends rather than forks (`--b9`).
**Outputs:** `data/research/b9/b9_results.json` and `data/research/b9/inputs/` (the snapshot and its
manifest).
**Window:** 2000-01 → 2026-06, 318 months, 26.5 years.
**Benchmark:** buy-and-hold 1× SPY total return (yfinance `Adj Close`).
**Bootstrap:** moving block (`MetricsEngine.bootstrap_distribution`), 1,000 iterations, seed 0, the
project-standard block of 7 months. A 60-month block is reported beside it.

## 1. The answer

**H1 (arm (i) ci_low > 0) is NOT MET.**
- **Arm (i) 60/20/20:** Δ log terminal wealth vs SPY-TR is **+0.279**, which multiplies terminal wealth
  by 1.32. The 95% CI is **[−0.241, +0.732]**; with 60-month blocks it is [−0.477, +0.726].
- **Measured t:** 1.24 against the predicted 2.2.
- **The prereg's refutation applies verbatim:** *multi-factor closed, momentum stays at 15%.*
- **No arm clears,** including the REF row and every secondary line.

The point estimate is positive and its CI is wide. The result is a failure to reach significance, not
evidence that the tilts hurt. Two facts make it decisive for deployment anyway:
- **The gain was earned in 2000–2013, when both tilts are haircut French proxies.** Arm (i) gained
  +0.30 in 2000–06 and +0.16 in 2007–13, then lost −0.23 in 2014–19 and gained +0.05 in 2020–26H1
  (descriptive split, not pre-registered).
- **Arm (i)'s wealth relative to SPY has been below its June-2014 high for 12 years.** The ratio was
  1.61× at that high, fell to a 1.20× trough in March 2020, and ended at 1.32×.

## 2. The four arms and the deployed reference (main window)

| arm | Δ log TW | /yr | ci_low (blk 7) | ci_high | ci_low (blk 60) | t (iid) | α/yr | TE/yr | TW ratio |
|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| **(i) 60/20/20 — DECISION** | **+0.279** | +1.05% | **−0.241** | +0.732 | −0.477 | **1.24** | +1.05% | 4.36% | 1.322 |
| (ii) 70/15/15 | +0.220 | +0.83% | −0.173 | +0.561 | −0.352 | 1.30 | +0.83% | 3.29% | 1.246 |
| (iii) 80/20/0 (top of the approved envelope) | +0.101 | +0.38% | −0.093 | +0.221 | −0.055 | 1.12 | +0.38% | 1.74% | 1.106 |
| (iv) 80/0/20 | +0.188 | +0.71% | −0.297 | +0.692 | −0.591 | 0.89 | +0.71% | 4.12% | 1.207 |
| *REF 85/15/0 — deployed mix, no N* | *+0.079* | *+0.30%* | *−0.066* | *+0.169* | *−0.038* | *1.17* | *+0.30%* | *1.31%* | *1.082* |

**Column definitions.**
- α and TE are the annualized mean and standard deviation of the monthly log active return.
- Δ log TW per year = Δ log TW ÷ 26.5.

**Costs are immaterial.** Annual rebalancing at 5 bp per rebalanced dollar cost 0.02–0.09% of wealth
over the whole window (26 rebalances).

**Secondary line (§3.1), arm (i) paired against the deployed 85/15:** Δ log TW +0.200, CI
[−0.283, +0.690] (60-month block [−0.555, +0.688]), t 0.95. Adding AVUV and five more points of MTUM on
top of the deployed mix is not distinguishable from zero.

## 3. Predicted vs measured t: why the power argument failed

| quantity | brief's prior | measured |
|---|--:|--:|
| arm (i) α | 0.8%/yr | **1.05%/yr** |
| arm (i) TE | 1.9%/yr | **4.36%/yr** |
| **t** | **≈ 2.2** | **1.24** |
| ρ of the two tilts' active returns | −0.3 | **−0.07** |
| MTUM-leg TE vs SPY | 8% | 8.6% |
| AVUV-leg TE vs SPY | 8% | **19.9%** |

**The alpha was larger than the prior assumed. The noise was 2.3× larger.** Both inputs to the "twice
the power" arithmetic failed:
1. **The value leg is far noisier than the prior assumed.**
   - Before 2019 it is the French `SMALL HiBM HiOP` cell. The French file's own counts show it holds
     44–55 firms in 2000–2010 and 22–24 since 2020. Its calendar-year returns include −12% (2000),
     +66% (2001) and +104% (2009).
   - From 2019-10 it is actual AVUV, small-cap value against a mega-cap S&P. Its tracking error is
     structurally far above 8%.
   - The prereg named the narrow cell as a known risk (§3.3) and froze it. It turned out to be
     load-bearing.
2. **The value × momentum diversification did not carry over.**
   - The −0.3 is the correlation of the long-short factors (Asness-Moskowitz-Pedersen).
   - Long-only legs measured against SPY carry their own size and beta deviations, and those
     dominate their active returns. The realized correlation was −0.07.

## 4. Regret table (as in T-318): worst rolling 15-year relative drawdown vs SPY-TR

| arm | regret DD | $ per $10k | time to recover the relative high |
|---|--:|--:|---|
| (i) 60/20/20 | −25.0% | $2,500 | **NEVER (≥ 12.0 y)**: peak 2014-06, trough 2020-03 |
| (ii) 70/15/15 | −19.3% | $1,932 | NEVER (≥ 12.0 y) |
| (iii) 80/20/0 | −5.9% | $589 | 5.4 y; ends 2026-06 at its relative high |
| (iv) 80/0/20 | −28.5% | $2,852 | NEVER (≥ 12.0 y): peak 2014-06, trough 2020-03 |
| *REF 85/15/0* | *−4.4%* | *$440* | *5.4 y; ends 2026-06 at its relative high* |

win40y is n/a on a 26.5-year window. It is not computed here and not fabricated.

## 5. Descriptive sub-windows (pre-declared, underpowered, never gating)

Each cell is Δ log TW with its CI.

| sub-window | (i) | (ii) | (iii) | (iv) | REF |
|---|---|---|---|---|---|
| 2013-05 → 2026-06 (MTUM actual) | −0.165 [−0.492, +0.061] | −0.120 [−0.365, +0.048] | +0.068 [−0.066, +0.147] | −0.233 [−0.528, +0.013] | +0.053 [−0.049, +0.112] |
| 2019-10 → 2026-06 (both actual) | +0.039 [−0.171, +0.201] | +0.031 [−0.127, +0.152] | +0.033 [−0.095, +0.119] | +0.010 [−0.173, +0.190] | +0.027 [−0.070, +0.091] |

**Across 2013-05 → 2026-06, every arm that holds the value leg is behind SPY.** Most of that
stretch's value leg is still the French proxy: actual AVUV starts only in 2019-10. The losses
therefore come from 2014–2019 French-proxy months. **In the both-actual era (2019-10 →) every arm is
slightly ahead, and none significantly** (+0.01 to +0.04). Over 2013+, the two arms whose only tilt is
real MTUM are ahead: (iii) +0.068 and REF +0.053, neither significant.

## 6. Secondary: French-only sign test, 1963-07 → 2026-06 (756 months, block 9)

| arm | sign | Δ log TW | CI (blk 9) | ci_low (blk 60) | t (iid) | regret | recover | win40y |
|---|:-:|--:|---|--:|--:|--:|---|--:|
| (i) 60/20/20 | **+** | +0.744 | [−0.142, +1.580] | −0.530 | 2.06 | −33.2% | NEVER (≥ 12.0 y) | 100% |
| (ii) 70/15/15 | + | +0.589 | [−0.072, +1.224] | −0.376 | 2.16 | −25.8% | NEVER (≥ 12.0 y) | 100% |
| (iii) 80/20/0 | + | +0.182 | [−0.021, +0.365] | −0.003 | 1.74 | −6.9% | NEVER (≥ 18.0 y) | 100% |
| (iv) 80/0/20 | + | +0.602 | [−0.221, +1.461] | −0.619 | 1.72 | −31.4% | NEVER (≥ 12.0 y) | 98% |
| *REF 85/15/0* | *+* | *+0.147* | *[−0.005, +0.285]* | *+0.009* | *1.88* | *−5.0%* | *NEVER (≥ 18.0 y)* | *100%* |

**The sign test passes for every arm:** all point estimates are positive over 63 years.
- The block-bootstrap CI still straddles zero for every arm on the standard block, even where the iid t
  passes 2 (arm (i) 2.06, (ii) 2.16). Serial dependence in factor returns makes the iid t overstate
  the evidence.
- The 1963 test therefore does not contradict the main window. It shows a real long-run sign, not
  significance.
- The 100% win40y figures sit on about 1.6 independent 40-year windows. As in T-318, they are not
  evidence.
- The French-only haircut was applied over the whole window: MTUM-proxy α̂ +2.57%/yr and AVUV-proxy α̂
  +9.14%/yr (gross), each halved by a constant shift.

## 7. DSR and MBL (arm (i), the decision arm)

| N | definition | DSR |
|---|---|--:|
| 37.08 | N_eff at the pinned registry count + this trial (conservative correlated; the CLAUDE.md `[NN-MBL]` N) | 0.178 |
| 232 | the raw registry count + this trial | 0.057 |
| 264 | the brief's figure (no derivation given in the brief) | 0.053 |

**MinBTL** at N_eff 37.08 for arm (i)'s realized annualized IR of 0.24 is **79.9 years**, against a
26.5-year window. The prereg showed that even a perfect hit of the predicted t would sit at the margin
(25.5 years).

**The honest-N inputs were read, never written.**
- Both pins were hash-verified (`config/honest_n_pin.json`) and the registry was opened read-only.
- N_raw = 231 and N_eff = 36.92 before this trial.
- The registry is a stale snapshot, last modified 2026-08-05; it lacks B-1's and T-379's trials.
  Recording trials is the director's job.

## 8. Census and input validation (all PASS; the run would have HALTed otherwise)

**Snapshot.** Taken 2026-11-12T00:10:03Z, after amendment 1 was committed (2026-11-11 18:04 CST).
yfinance 1.2.0; French CRSP vintage 202609.

| file | md5 |
|---|---|
| `ff/F-F_Research_Data_Factors_CSV.zip` | `a2867511e56041fd98b57b51793c7f04` |
| `ff/6_Portfolios_ME_Prior_12_2_CSV.zip` | `471e58876606c396e7e865b8042aaa77` |
| `ff/32_Portfolios_ME_BEME_OP_2x4x4_CSV.zip` | `55fc6f25b5f734a092db6d1054620a6c` |
| `yf/SPY.csv` | `4bede6e4f25a57ea7e87c762546825fe` |
| `yf/VOO.csv` | `bc16c3ac98fe46bddd866238ee3832a2` |
| `yf/MTUM.csv` | `1c2254fb03b2adb1a58c93caf9166980` |
| `yf/AVUV.csv` | `4ea6c8bc65f7e8f657304bb7c595a9cd` |

**Input checks (a)–(d).**

| check | result |
|---|---|
| **(a)** split-jump: maximum daily return divergence between the yfinance `Close` and the Stooq close (tolerance 0.20) | SPY 0.020, VOO 0.006, MTUM 0.008, AVUV 0.006 |
| **(b)** fetched SPY TR year-end level ratio | vs `tr_reconciled` (2005–25): constant to 3.9e-7. vs `data/processed` (2000–25): constant to 7.1e-7. Tolerance 5e-3 |
| **(c)** maximum monthly \|return\| (tolerance 0.50) | SPY 0.165, VOO 0.128, MTUM 0.183, AVUV 0.289 |
| **(d)** dividends present: Adj Close CAGR − Close CAGR over the actual-ETF months (band 0.3–4.0%/yr) | VOO 2.01%, MTUM 1.37%, AVUV 1.87%/yr |

**Splice months.** VOO 2010-10, MTUM 2013-05, AVUV 2019-10, exactly as declared. yfinance's first bars
were 2010-09-09, 2013-04-18 and 2019-09-26.

**Months by source.**
- VOO: 129 proxy (SPY-TR + 0.0645%/yr) and 189 actual.
- MTUM: 160 French and 158 actual.
- AVUV: 237 French and 81 actual.

**Main-window haircuts.**
- MTUM proxy (`BIG HiPRIOR`, 2000-01 → 2013-04): α̂ = +0.71%/yr, shift −0.36%/yr.
- AVUV proxy (`SMALL HiBM HiOP`, 2000-01 → 2019-09): α̂ = +7.49%/yr, shift −3.74%/yr.

**Smoke.**
- Ran on the window's first 12 months (2000-01 → 2000-12). Legs were checked by eye: SPY Jan-2000
  −4.98%; VOO = SPY + 0.0054%/mo; FF market −4.33%; each French leg = raw − shift − ER/12.
- The 2000-12 rebalance cost matched a hand computation (arm (i) turnover 3.2% of gross → cost
  1.6e-5 of gross).
- The SVP proxy's 2000 path (≈ −15% after the haircut) was cross-checked against the French file's
  own annual table (−12.0% raw).
- A synthetic unit check passed: identical legs reproduce SPY to 3e-16, and a two-asset hand case
  matches to 1e-17.

**Headline recomputed independently.** Computed from terminal wealth (arm 10.727 vs SPY 8.114 per $1),
it agrees with Σd to within 1e-9 (asserted in the code).

**Determinism ×2.** `b9_results.json` md5 is `6368f5c6e901d600dd889e5a3fc06d3f` on both runs, and the
printed tables were byte-identical.

## 9. What this means for the deployed 85/15

**Keep it exactly as it is. B-9 gives no reason to add a value leg or to move momentum to 20%.**
- **Adding AVUV at 15–20%** would have more than tripled tracking error against SPY (1.3% → 4.1–4.4%/yr).
  It would have produced a 25–29% relative drawdown that is still unrecovered after 12 years, with no
  significant gain to show for it. In the only stretch where both tilts are real ETFs (2019-10 →),
  the gain is +0.01 to +0.04 log and indistinguishable from zero.
- **The deployed 85/15 under B-9's conventions** (annual rebalance, fully invested; not the live
  share-quantum bands or the SGOV residue):
  - +0.30%/yr log over 26.5 years, terminal wealth ×1.08 against SPY;
  - the smallest regret of any arm: −4.4%, recovered in 5.4 years, and it ends at its relative high;
  - **not statistically significant:** ci_low −0.066 (block 7) / −0.038 (block 60);
  - in the actual-MTUM era: +0.053 [−0.049, +0.112].
- **Momentum stays at 15% because nothing here argues for moving it, not because B-9 re-proved it.**
  On this window, with a 50% haircut on the French-era alpha, momentum alone (arm (iii) and REF) is
  "positive, not significant". This differs from T-320's "CI excludes 0", which came from a different
  construction:
  - 1927+ data, 40-year windows, monthly rebalance;
  - small and big winners averaged;
  - no haircut.

  Do not quote B-9 as confirming T-320's significance.

## 10. Caveats that travel with this verdict

1. **Pre-cutover substrate.** The validation references `data/processed/SPY_1d.csv` and
   `tr_reconciled/SPY_1d.csv` are pre-cutover, so the verdict carries "re-verify required after cutover"
   (`[NN-SUBSTRATE-REVERIFY]`). The legs themselves come from the French library and the yfinance
   snapshot, so the expected sensitivity is small.
2. **The decision rests mostly on modelled months.** 237 of 318 AVUV months and 160 of 318 MTUM months
   are haircut French proxies. The 50% haircut is a convention from Novy-Marx-Velikov, not a
   measurement.
3. **The AVUV proxy is a 22–55-firm cell.** The prereg froze it. A broader small-value cell might have
   lower tracking error. Testing that now would be a post-hoc re-spec, which the prereg forbids. It
   needs its own pre-registered trial if anyone wants it.
4. **The ETFs are survivors chosen in 2026.** MTUM and AVUV exist and are well known today. The bias
   from that selection would run toward the arms, which strengthens rather than weakens the null.
5. **Pre-tax and lump sum.** Annual rebalancing in a taxable account would realize gains. Contributions
   are not modelled.

**N_trials consumed: 1** (one family; arms (i)–(iv) are reported jointly). The REF row, the arm (i) vs
REF line, the sensitivity block, the sub-windows and the French-only test are pre-declared secondary
reporting and consume no N.
