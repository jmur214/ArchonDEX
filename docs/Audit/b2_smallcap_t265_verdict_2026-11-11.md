---
task_id: T-381 (B-2)
title: B-2 verdict — small-cap 12-1 momentum and insider-buying clusters on the T-265 panel
date: 2026-11-11
author: edge-analyst subagent (in-session, director-dispatched)
outcome: >-
  BOTH H1s NOT MET; both refutations stand, and both gates also fail with no death penalty at all.
  Momentum: 25%-satellite Δ log wealth vs SPY TR −0.111 [ci −0.408, +0.192].
  Insider (clusters ≥ 3): CAR(0,126) t_HAC 0.20 (n = 1,895 events, 118 cohorts);
  satellite −0.141 [ci −0.454, +0.149]. Both satellite nulls are "not demonstrable at this
  length" (point below the pre-data MDE80). No alpha diagnostic has t > 2, so the A1.1 stop
  trigger did not fire and C-1 (PEAD × insider) does not run. N_trials +2.
  Side finding: T-249's Sharpe/Sortino were annualized ×√252 on MONTHLY returns, i.e.
  inflated ×4.58 (its "Sharpe 3.2" is ≈ 0.70).
status: CURRENT — determinism ×2 PASS; re-verify required after cutover ([NN-SUBSTRATE-REVERIFY])
reproduce: |
  export PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_DYNAMIC=FALSE
  python -m scripts.smallcap_momentum_t265_b2 --out data/research/b2/run1   # canonical md5 eb1a1a5cb9d10e872d3b0393a115c960
  python -m scripts.smallcap_insider_t265_b2  --out data/research/b2/run1   # canonical md5 7f9f470635d33cd0f365dd3f16ecb11c
  (smoke: add --smoke; first 12 months of each window, no bootstrap)
---

# B-2 (T-381) — small-cap momentum and insider clusters on the T-265 panel

> **Review correction, 2026-11-11 (a follow-up commit; independent review reproduced every md5 and
> recomputed both headlines exactly; both H1-NOT-MET verdicts stand):**
> - §3.1 no longer calls the survivor-only − base gap a "measured haircut" or a "lower bound". The
>   panel's in-decile deaths are takeovers, and the death arms price an assumption.
> - §6.3 makes the sub-$1M number descriptive and untested.
> - §7 re-scores the event-count prediction on EVENTS, not names.
> - §3.1 marks the corrected T-249 Sharpes as point estimates without a CI.

## In plain English

Neither idea pays well enough to show up, at this length, in the measure the brief made the gate. This
holds even with no penalty at all on the panel's exits. The panel is missing most failure deaths,
which would push the results down further (§3.1).

**Small-cap momentum.** Buy the top tenth of $1M–$200M-ADV names by 12-1 return each month, after
honest small-cap trading costs.
- From 2017 to 2026 it compounded 8.3% a year, against 15.1% for SPY and 9.5% for IWM.
- It behaved almost exactly like IWM with a beta of 1.1, with no alpha (−0.9%/yr, t −0.25).
- Trading costs alone ate 4.8% a year.
- As a 25% satellite it lowered terminal log wealth by 0.11 against holding all SPY. The 95% CI
  [−0.41, +0.19] spans zero.

**Insider buying clusters** (three or more insiders buying within 30 days).
- Across 1,895 tradable small-cap events, they beat IWM by a statistically invisible amount over the
  next six months: a mean CAR of +2.0%, but t_HAC 0.20 across the monthly cohorts. Most of the +2.0%
  is one month, the March 2020 crash bottom.
- A 40-name book of them compounded 7.8% a year and as a satellite cost 0.14 of log wealth.
- Sub-$1M-ADV names show a mean summed CAR of +8.8%, but that measure is inflated by bid-ask bounce
  and its buy-and-hold median is −3.8%. It is descriptive and untested (§6.3).

The brief's refutations apply verbatim.
- Momentum: **"T-249's kill stands, now measured."**
- Insider: **"insider clusters are priced in small caps too — close the region."**

Both satellite nulls also carry the pre-registered label **"not demonstrable at this length"**. The
gate can detect only an arm that beats SPY by roughly 18–22% a year (A1.6), so it cannot exclude a
small edge. What the more powerful instruments show (the event-study t of 0.20; the IWM alphas of
−0.9 and −4.3%/yr) is no edge at all.

## 1. Pre-registration and order of operations
- Prereg `docs/Sources/prereg_b2_smallcap_t265_2026-11-11.md`: FROZEN at `780a49b` (18:15:11).
- AMENDMENT 1 (director rulings R1–R9) and the nine census scripts: `7e6562b` (18:23:10). The frozen
  prefix md5 `d369e628…` is unchanged.
- The first output file under `data/research/b2/` is the momentum smoke at 18:31:28. Every number here
  postdates the frozen rules, and no rule was changed after any output.
- **Smoke** (first 12 months of each window) was read by eye:
  - The 2017-01-31 formation's top names (CRBP, CC, CLF, NAV, CDE, LNTH) are 2016's real small-cap
    multi-baggers.
  - SD (SandRidge) was correctly excluded: its file splices the pre- and post-bankruptcy equity.
  - An independent re-derivation from the raw files (no harness code) reproduced the first month's
    net return to every digit (−0.0013812894488294).
  - Insider events were checked against the raw zip. HBAN 2016-02-01 had four filers; the CEO is
    CMP-routine (April buys in 2009, 2012 and 2013), so the PIT size is 3. Entry is the 2016-02-02
    close.
  - One smoke-found defect was fixed before the full run. A REPORTING field (`first_events.size`)
    read pandas' `Series.size`; it touched no statistic.
- **Determinism ×2:** momentum canonical md5 `eb1a1a5cb9d10e872d3b0393a115c960` (run1 = run2;
  monthly CSV `3818bf4d…`, census CSV `c6e9c178…` identical). Insider canonical md5
  `7f9f470635d33cd0f365dd3f16ecb11c` (run1 = run2; monthly `0937e0c9…`, events `107e4bd7…` identical).
  After the full suite, the processed-globbers lock required a bypass comment on the twin read, the
  only code change after the runs. A third run (`run3`) on the COMMITTED code reproduced both
  canonical md5s.
- **Full suite:** 4,690 passed, 56 skipped, 11 xfailed, and 1 failed. The failure is the known
  environmental `test_layer3a_capability_ledger_source_files_exist` (`data/governor/edges.yml` is
  absent in the safe worktree layout).
- **Post-review hardening re-run (`run4`, on `e699286`, 2026-11-11, on the director's go).**
  - This is the code with strict TSV reads, no coercion, a NOT-EVALUABLE gate and full §4.5 census
    enforcement.
  - Both canonical md5s are UNCHANGED (momentum `eb1a1a5cb9d10e872d3b0393a115c960`, insider
    `7f9f470635d33cd0f365dd3f16ecb11c`), and all four output CSVs are byte-identical to run1.
  - `momentum_census_check.json`: 23/23 checks ok (19 price, 4 window). `insider_census_check.json`:
    31/31 ok (19 price, 12 Form 4 / join / window).
  - Full suite after the re-run: 4,705 passed, 56 skipped, 11 xfailed, and 1 failed (the same known
    `edges.yml` contract test). The data-write guard flagged nothing.
- **Review round 2 notes (2026-11-11):**
  - **`main()` census wiring is now tested.**
    - Six tests drive each script's `main()` on a tiny synthetic fixture: a positive control per
      script that passes its census, and four refusals (momentum price, momentum window, insider
      price, insider Form 4), each with one declared count off by one, asserting exit 2 and the
      census-halt message.
    - Each refusal was proven in a SCRATCH COPY, never the worktree: disconnecting exactly that one
      `enforce_census` call made its test fail (main ran to exit 0), and the unmodified copy passed
      6/6.
  - **pandas' default NA tokens** ("NA", "N/A", "null", …) still become NaN without a halt.
    `strict_parse` only refuses a NON-empty value that fails to parse.
    - A scan of all 81 zips with NA-detection off found **17** such values in the fields the
      harness reads. All 17 are in `SECURITY_TITLE`, across every transaction code.
    - That field feeds only the "prefer" test. The literal string and the NaN it becomes (filled to
      "") fail that test identically, so no event or number changes.
    - Every date, number, CIK, code and accession field has **0**.
  - **The census scripts' byte-identity to the pre-freeze scratch copies is established by the
    author but NOT independently verifiable.**
    - The scratch copies still exist in the author's session scratchpad, last modified 18:00:09 →
      18:06:11, before the 18:15:11 freeze. Their git blob hashes equal all nine blobs committed at
      `7e6562b` (e.g. `census_prices.py` `ccfa2496…`, `census_form4.py` `9cd7bcb0…`).
    - That scratchpad lies outside the repo and is session-scoped, so a reviewer cannot read it.
      Treat the identity as the author's attestation, not as a reproduced fact.
- **Headlines recomputed independently** from the output CSVs: momentum Δ log wealth −0.111334,
  insider −0.141058, insider NW t 0.19980 (a hand-rolled Bartlett estimator) all match.

## 2. Census (every fail-closed block passed)
| check | value | rule |
|---|---|---|
| price files / files < 60 bars | 4,674 / 44 | — |
| phantom zero-volume tails (≥ 5 bars) / any | **151** / 170 | A1.2 recount = 151 ✓ |
| reused-ticker files (gap ≥ 63 days) → segments | **141** files → 341 segments | A1.2 recount = 141 ✓ |
| segments / segment deaths | 4,830 / 734 | — |
| momentum formations | 111 (2017-01-31 → 2026-03-31; holds 2017-02 → 2026-04) | ≥ 100 ✓ |
| eligible per formation | 1,707–2,412 (median 2,126) | ≥ 500 ✓ |
| decile size k | 170–241 (median 212) | ≥ 50 ✓ |
| names with ADV ≥ $200M excluded | 110–559 a month | R5 |
| micro ($1M–$20M) share of the eligible set | 57% | — |
| deaths inside a held decile month | 59 over 111 months | — |
| 2% ADV cap | never binds at the $250k sleeve; median capacity ≈ $4.3M of sleeve AUM | — |
| P/A original Form 4 rows (2006–2026q1) | 808,146 | 81 zips ✓ |
| CIK-join row coverage, 2016–2025 | **64.43%** | ≥ 63.0% ✓ |
| rows: after size/price/preferred → after 10b5-1 → after CMP | 786,912 → 718,186 → 615,387 | — |
| routine (owner, issuer) pairs | 5,752 | R9 |
| clusters/yr, all issuers (2016–2025) | 606, 550, 672, 676, 887, 626, 647, 582, 434, 503 | — |
| in-band event names/yr (2016–2025) | 110, 108, 169, 178, 310, 169, 212, 202, 144, 224 | — |
| event drops (in-window and out) | pre-window/post-data 9,279 · no ticker 1,797 · no price file 288 · multi-CIK ticker 95 · splice ticker 100 · no ADV 594 · ADV ≥ $200M 112 · no trade within 5 days 5 | counted |
| events in-band / study set / sub-$1M | 1,988 / 1,895 / 1,254 (study window) | > 0 ✓ |
| share of the priced universe with any Form 4 | 90.6–92.2% a year | — |
| footnote 10b5-1 rate among P/A rows (2016→2025) | 9.6, 5.9, **39.9, 31.7**, 6.2, 7.2, 7.2, 4.1, 6.2, 7.2% | R8 (i) |
| `AFF10B5ONE` rate (2023 / 2024 / 2025) | 3.5 / 7.3 / 7.7% | R8 (i) |
| book days / days the cap binds / events skipped at the cap | 2,577 / **607** / 1,184 | — |

## 3. Momentum — the table (111 monthly holds, 2017-02 → 2026-04; bootstrap 1,000 iterations, block 5, paired)
| arm | CAGR | vol | MaxDD | Sharpe [95% CI] | Sortino (ci_low) | **25%-sat Δ log W vs SPY [95% CI]** | vs the IWM sleeve (point) |
|---|---|---|---|---|---|---|---|
| **BASE (gate): −30% deaths, 70/150 bps RT** | **8.29%** | 26.8% | −46.3% | 0.43 [−0.24, 1.06] | 0.71 (−0.38) | **−0.111 [−0.408, +0.192]** | −0.006 |
| STRESS: −100% deaths | 5.97% | 27.0% | −53.2% | 0.35 [−0.35, 0.99] | 0.56 (−0.53) | −0.161 [−0.460, +0.141] | −0.056 |
| LAST-PRICE: deaths at 0 | 9.29% | 26.7% | −43.1% | 0.46 [−0.20, 1.08] | 0.78 (−0.31) | −0.090 [−0.377, +0.213] | +0.015 |
| cost sensitivity: the brief's 35/75 bps RT | 10.92% | 26.9% | −43.0% | 0.52 [−0.15, 1.14] | 0.90 (−0.26) | −0.056 [−0.353, +0.248] | +0.049 |
| **SURVIVOR-ONLY** (segments still alive at the window end) | **11.00%** | 27.2% | −42.8% | 0.52 [−0.14, 1.13] | 0.89 (−0.23) | −0.054 [−0.338, +0.263] | +0.051 |
| SPY TR | 15.05% | — | −23.9% | 0.97 [0.40, 1.69] | — | — | — |
| IWM TR | 9.47% | — | −32.3% | 0.53 [−0.08, 1.17] | — | IWM sleeve vs SPY: −0.105 [−0.271, +0.055] | — |

- **Alpha diagnostics** (A1.6, no N): vs IWM **−0.86%/yr, t_HAC −0.25** (β 1.11); vs SPY −6.96%/yr,
  t_HAC −1.15 (β 1.24).
- **Turnover:** 815%/yr. **Cost drag:** 477 bps/yr at the gate, 239 at the brief's rate.
- **DSR line:** standalone Sharpe 0.43 (ci_low −0.24), below the 0.71 required at N_eff 36.9 and the
  0.94 required at N ≈ 260 over 9.25 years.
- **Realized MDE80** of the satellite gate: 0.424, against 0.43 pre-data. The power assumption held.
- **Per calendar year (base / SPY / IWM):** 2017 +16.9 / +19.6 / +14.3; 2018 −11.9 / −4.6 / −11.1;
  2019 +21.3 / +31.2 / +25.4; **2020 +49.3 / +18.3 / +20.0**; 2021 +15.4 / +28.7 / +14.5; 2022 −22.8 /
  −18.2 / −20.5; 2023 +5.4 / +26.2 / +16.8; 2024 +2.3 / +24.9 / +11.4; 2025 +2.5 / +17.7 / +12.7;
  2026 Jan–Apr +13.9 / +5.7 / +13.1 (%). One year (2020) carries the arm.

### 3.1 The survivor-only gap, decomposed (not a measured haircut) — and T-249 corrected
| | window / universe | cost | CAGR | Sharpe | Sortino (ci_low) |
|---|---|---|---|---|---|
| T-249 **as published** (gross / net tier) | 2006-02 → 2026-05 (244 months; the audit says "2006–2025"), Stooq, 100% survivors, ADV tier from the FULL-window median (look-ahead) | 0 / 35+75 bps per side | 15.1% / 10.8% | 3.21 / 2.47 (no CI published) | 4.91 (1.52) / 3.71 (0.49) |
| **T-249 corrected** (÷ √21, see §6.1) | same | same | 15.1% / 10.8% | 0.70 / 0.54: **point estimates only; T-249 never bootstrapped its Sharpe, so these are not measurements under `[NN-SHARPE-CI]`** | **1.07 (0.33) / 0.81 (0.11)**: the CI-carrying figures (the reviewer's re-run with periods = 12 reproduced gross 1.071, ci_low 0.332) |
| B-2 survivor-only | 2017-02 → 2026-04, T-265 survivors, PIT ADV | 70/150 RT (the same basis as T-249's net tier) | 11.0% | 0.52 | 0.89 (−0.23) |
| **B-2 base** | the same, with the panel's deaths at −30% | 70/150 RT | **8.3%** | **0.43** | **0.71 (−0.38)** |

**Within-panel survivor-only − base: +2.7 pp/yr CAGR and +0.058 Δ log wealth.** The Sharpes are 0.52
(ci_low −0.14) against 0.43 (ci_low −0.24); the CIs overlap almost entirely, so no Sharpe difference
is established. **This gap is NOT a measured survivorship haircut, and it is not established as a
lower bound** (corrected after independent review, 2026-11-11):
- **The deaths this panel does carry are takeovers, not failures.** The reviewer measured all 59
  in-decile deaths over each name's last 20 traded days: median annualized vol 6.1%, median return
  +0.5%, none below $1, and only 1 of 59 down more than 30% (ISLE, ONCE, ARQL, TECD, MNTA, XEC, SAIL,
  ACC …). Their true delisting return is ≈ 0 (the deal price).
- **About 1.0 pp/yr of the 2.7 is the ASSUMED −30% charged on those takeover exits** (LAST-PRICE CAGR
  9.29% vs base 8.29%). The STRESS arm's further −2.3 pp/yr is the same assumption at −100%, not
  evidence that failures drive returns.
- **The other ~1.7 pp/yr is ex-post selection.** Survivor-only drops, with hindsight, names that later
  exit, mostly parked flat at a deal price for their final months.
- **Two biases pull in opposite directions.** The panel misses most FAILURE deaths (prereg §3.1),
  which pushes the true complete-panel number down. The −30% on takeover exits over-charges, which
  pushes it up. The net direction is not established.
- **The gate is unaffected.** With no death penalty at all, the LAST-PRICE satellite is −0.090 (ci_low
  −0.377). Charging −30% on takeover exits is conservative, so it biases AGAINST H1, and the
  refutation is robust to it.
- **Notes.**
  - 12 of the 59 deaths fall on the formation day: the name is bought on its last trading day and
    charged −30%. That is prereg-compliant (§4.3) and costs about 0.2 pp/yr.
  - The universe is an ADV band, not a market-cap band. For example, HBAN at a ~$7B market cap is
    in-band.

Once T-249's annualization is corrected, its net-tier point estimates (Sharpe 0.54, CAGR 10.8%,
2006-02 → 2026-05) sit close to B-2's survivor-only arm (0.52, 11.0%) on a different window.

## 4. Insider clusters — the event study (entries 2016-02-02 → 2025-11-19; CAR(0,126) vs IWM TR; NW 6 lags on the entry-month cohort means)
| set | n events | cohorts | mean CAR | median | % > 0 | winsorized 1/99 mean | cohort mean of means | **t_HAC** |
|---|---|---|---|---|---|---|---|---|
| **clusters ≥ 3 (gate)** | **1,895** | 118 | +1.97% | +1.61% | 52.6% | +1.91% | +0.33% | **0.20** |
| size 3 | 1,393 | 115 | +1.87% | +1.46% | 52.3% | +1.87% | +0.73% | 0.37 |
| size 4 | 288 | 95 | +1.86% | +0.99% | 52.4% | +1.60% | −0.30% | −0.12 |
| size 5+ | 214 | 86 | +2.74% | +4.10% | 55.1% | +3.02% | +1.89% | 0.66 |
| STRESS (−100% deaths) | 1,895 | 118 | +1.86% | — | — | — | +0.23% | 0.14 |
| LAST-PRICE | 1,895 | 118 | +2.02% | — | — | — | +0.38% | 0.23 |
| R8 sensitivity (no 10b5-1 exclusion before 2023) | 1,905 | 118 | +2.05% | +1.77% | 52.8% | +1.99% | +0.52% | 0.32 |
| sub-$1M-ADV events (descriptive, UNTESTED; summed daily returns on illiquid closes carry an upward bid-ask-bounce bias; the reviewer's BHAR median is −3.8%) | 1,254 | — | +8.82% | — | — | — | — | not computed (prereg: mean only) |

- Deaths inside a study window: 3.
- **Realized SE** of the gate statistic: 1.68% (0.33% / 0.20), so the realized MDE80 is 4.7%, against
  5.7% pre-data. The event study had the power to see a 4–6% effect, and the cohort-weighted effect
  is 0.3%.
- The gap between the pooled mean (+2.0%) and the cohort mean (+0.3%) is one month. **March 2020
  alone holds 186 events (10% of the set) with a cohort-mean CAR of +15.5%**: insiders bought the
  COVID low, and the whole small-cap complex rebounded. The next-largest cohorts hold 39–55 events
  each, with mixed signs (May 2022 −5.4%, Dec 2021 −24.7%). Once each month counts once, the drift is
  +0.3%. A single crash-bottom month is a regime bet, not a repeatable event signal.

### 4.1 The insider book (40-name cap; daily EW; 123 months, 2016-02 → 2026-04)
| arm | CAGR | vol | MaxDD | Sharpe (ci_low) | Sortino (ci_low) | **25%-sat Δ log W vs SPY [95% CI]** | vs the IWM sleeve (point) |
|---|---|---|---|---|---|---|---|
| **BASE (gate): −30% deaths, 70/150 bps RT** | **7.84%** | 27.9% | −52.0% | 0.41 (−0.17) | 0.67 (−0.28) | **−0.141 [−0.454, +0.149]** | −0.063 |
| STRESS | 7.46% | 28.0% | −52.9% | 0.40 (−0.18) | 0.65 (−0.30) | −0.150 [−0.460, +0.145] | −0.072 |
| LAST-PRICE | 8.00% | 27.9% | −51.7% | 0.42 (−0.17) | 0.68 (−0.27) | −0.137 [−0.452, +0.156] | −0.060 |
| cost sensitivity: flat 75 bps RT (brief) | 8.95% | 28.0% | −51.3% | 0.45 (−0.14) | 0.74 (−0.22) | −0.115 [−0.429, +0.176] | −0.037 |
| R8 sensitivity | 8.70% | 27.3% | −49.2% | 0.44 (−0.13) | 0.75 (−0.21) | −0.123 [−0.419, +0.155] | −0.045 |
| SPY TR / IWM TR | 15.52% / 11.60% | — | — | — | — | IWM sleeve vs SPY: −0.078 [−0.248, +0.090] | — |

- **Alpha diagnostic** vs IWM: **−4.32%/yr, t_HAC −1.09** (β 1.23).
- **DSR line:** Sharpe 0.41, below 0.67 at N_eff 36.9 and below 0.89 at N ≈ 260 over 10.25 years.
- The 40-name cap bound on 607 of 2,577 book days, and 1,184 events were skipped (first-come). The
  event study above covers every in-band event, so the skips cannot hide an effect.

## 5. H1 assessment (as pre-registered + A1)
| family | H1 | result | label (A1.6) | refutation (verbatim) |
|---|---|---|---|---|
| **momentum** | 25%-sat Δ log wealth ci_low > 0 vs SPY TR | **NOT MET**: point −0.111, ci_low **−0.408** | "not demonstrable at this length" (point < MDE80 0.43) | **"ci_low ≤ 0 in the base arm ⇒ T-249's kill stands, now measured."** |
| **insider** | CAR t_HAC > 2.0 (≥ 3) AND satellite ci_low > 0 | **NOT MET** on both legs: t_HAC **0.20**; satellite ci_low **−0.454** | satellite: "not demonstrable at this length" (point < MDE80 0.56) | **"t_HAC < 2 ⇒ insider clusters are priced in small caps too — close the region."** |

- **The A1.1 stop trigger did not fire.** No H1 is met, and no alpha diagnostic has t > 2 (momentum
  vs IWM −0.25, vs SPY −1.15; insider vs IWM −1.09). The ~2,000-symbol SIP fetch is therefore not
  needed for this verdict.
- Under the asymmetric rule (§2.7), both FAILs stand. The missing FAILURE deaths would push both
  results down, and both gates fail even at LAST-PRICE (no death penalty), so the refutations do not
  rest on the death assumption.
- **C-1 (PEAD × insider) does not run.** Its trigger, t_HAC > 2, failed.

## 6. Findings the director should see
1. **T-249's Sharpe and Sortino were annualized with `periods=252` on MONTHLY returns**
   (`scripts/smallcap_momentum_gauntlet_t249.py:7` sets `TD=252`; `:81` and `:86` pass it to
   `MetricsEngine.sortino_ratio`/`sharpe_ratio` on the month-end series, and `:82` passes it into the
   bootstrap, so the published ci_low is inflated by the same factor). That inflates every Sharpe,
   Sortino and bootstrap bound by √(252/12) = 4.58×. The audit's reasoning, "Sharpe 3.2 for a
   diversified momentum decile is not real — it's the survivorship bias", rests partly on this
   arithmetic error: the corrected gross Sharpe is 0.70, which is unremarkable. Its CAGRs and MaxDDs
   are unaffected. The T-249 verdict text should carry an erratum.
2. **Cost is the largest single drag on momentum.** Its gross alpha vs IWM is roughly +3.9%/yr (the
   net alpha of −0.9% plus the 4.8% drag; an estimate, not a tested quantity), and 815% annual
   turnover hands it to the spread. At half the measured cost (the brief's 35/75), the satellite point
   is still negative (−0.056), so cost alone does not explain the null.
3. **Sub-$1M-ADV clusters: descriptive and UNTESTED.** Their mean summed-daily CAR is +8.8% (n =
   1,254; no t was pre-registered and none was computed). That number cannot be read as alpha:
   - **Summing daily returns on illiquid closes carries an upward bid-ask-bounce bias.**
   - The reviewer's buy-and-hold (BHAR) check gives a median of **−3.8%** against a mean of +7.7%: a
     few large winners in a negative-median set.
   - Whether any of it is real, and whether a retail account could capture it, is unknown. A test
     would need a bounce-robust return measure and a sub-$1M cost model, neither of which exists here.
4. **The R9 CMP filter is aggressive.** 5,752 (owner, issuer) pairs are routine, and 14% of the
   counted rows were dropped. Any insider who bought in the same calendar month in three earlier years
   is excluded for life, including active CEOs (HBAN's Steinour). The R8 sensitivity moved t from 0.20
   to 0.32. Nothing here suggests the filter hid a result, but it is stricter than CMP 2012.
5. The 2018–2019 footnote 10b5-1 rate among P/A rows is 40% / 32%, against about 6–10% in other years.
   A few issuers' plan purchases are reported as code P. They are correctly excluded in the base and
   restored in the R8 sensitivity, which changes nothing.

## 7. Predictions (prereg §8) vs results
| prediction | result | hit? |
|---|---|---|
| momentum H1 NOT met (≈ 93%) | NOT met | ✓ |
| momentum satellite point < 0 | −0.111 | ✓ |
| momentum standalone net Sharpe 0.3–0.7 | 0.43 | ✓ |
| within-panel haircut +1 to +3%/yr | +2.7%/yr survivor-only − base | ✓ on the number; ✗ on the reading (§3.1: not a survivorship haircut) |
| STRESS lowers the base by < 1%/yr | −2.3%/yr | ✗. 59 exits × the assumed charge; the exits are takeovers (§3.1), so this is not evidence that failures matter |
| LAST-PRICE raises the base by < 0.5%/yr | +1.0%/yr | ✗ |
| insider mean CAR +2% to +4% | +1.97% (pooled) / +0.33% (cohort) | ≈ (pooled at the floor) |
| insider t_HAC 1.5–2.5; P(t > 2) ≈ 40% | 0.20 | ✗ (weaker than predicted) |
| size buckets weakly increasing | 5+ highest (+2.7%); 3 ≈ 4 (+1.9%) | partial |
| insider satellite ci_low < 0; H1 NOT met | −0.454; NOT met | ✓ |
| sub-$1M events show a larger CAR | +8.8% vs +2.0% mean summed CAR; BHAR median −3.8% | untested (§6.3: bid-ask bounce) |
| 150–400 in-band EVENTS/yr | 116, 113, 179, 186, 324, 177, 229, 211, 151, 241 (2016–2025) | partial: 2016–17 fall below the range |
| … fewest in 2024–25 (prereg §8.2 sub-prediction) | the fewest were 2016–17 (116, 113); 2024–25 had 151 and 241 | ✗ MISSED |
| the 40-name cap binds on < 10% of book-days | 24% | ✗ |

## 8. What this does NOT show
- It says nothing about small-cap momentum or insider buying on a SURVIVORSHIP-COMPLETE panel. The
  missing failure deaths would push both results down (§2.7, prereg §3.1); the over-charged takeover
  exits push the momentum base the other way (§3.1). Both gates fail even with no death penalty.
- It does not show "no small-cap momentum premium exists". The satellite gate detects only a large
  edge (A1.6). The IWM alpha (t −0.25) is the cleaner statement: no edge beyond IWM-with-beta, net of
  measured cost.
- It does not cover sub-$1M insider events (untradeable here), 6-1 or 3-1 momentum, value-weighting,
  role filters, dollar-value thresholds, or K ≠ 3 cluster definitions (scope exclusions, prereg §10).
- Nothing is deployed, and nothing is promoted.

## 9. N_trials, honest N, substrate
- **N_trials +2** (momentum family; insider family; R7). The director records it; the run registry is
  not written.
- Honest N at run time: N_raw 231, N_eff 36.9 (conservative).
- **Substrate:** the T-265 stages (agent-d vintage, 2026-07-02; SIP `adjustment='all'`, total return)
  and the T-256 `tr_reconciled` SPY/IWM/BIL twins (ending 2026-05-22). **Re-verify required after
  cutover**, per `[NN-SUBSTRATE-REVERIFY]`.

## 10. Files
- Harnesses: `scripts/smallcap_momentum_t265_b2.py`, `scripts/smallcap_insider_t265_b2.py`, shared
  `scripts/smallcap_t265_b2_common.py`. Hermetic locks: `tests/test_smallcap_t265_b2.py`.
- Census scripts: `scripts/b2_census_t381/` (committed unchanged at `7e6562b`).
- Outputs (gitignored, under the main tree's `data/research/b2/`):
  - `run1/` and `run2/` (identical): `momentum_results.json`, `momentum_monthly.csv`,
    `momentum_formation_census.csv`, `insider_results.json`, `insider_monthly.csv`,
    `insider_events.csv`;
  - `smoke/`.
