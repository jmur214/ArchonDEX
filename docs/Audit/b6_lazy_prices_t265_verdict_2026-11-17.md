---
task_id: T-383 (B-6)
title: B-6 Lazy Prices — T-265 small-cap arm verdict (the gate and H_OOS)
date: 2026-11-17
author: ml-architect subagent (director-dispatched)
outcome: "T-265 ARM: H1 NOT MET for either signal — similarity Δ log wealth −0.093 (family ci_low −0.262), Δtone −0.125 (ci_low −0.317); short-leg t_HAC +1.09 / +1.33 on net legs (gross +0.39 / −0.18). H_OOS FAILS (changers − universe +0.49%/yr, t_HAC +0.50, wrong sign): the S&P adjacent-pairing finding is CLOSED as a one-window artifact. With the S&P arm, the brief's refutation holds in both arms: Lazy Prices is H0 on free data for this operator — for YoY similarity and LM tone change of the R6 text (10-K Items 1A + 7, 10-Q MD&A), quarterly, on these windows; not for other sections, paid full text or other horizons (§10)."
status: "T-265 arm DONE; reviewed (APPROVE WITH REQUIRED FIXES, 2026-11-17), fixes applied; the reviewer's delta check precedes any merge. N_trials +2 (gate family +1, H_OOS +1) — the director records it on main against AMENDMENT 9 (6b98883)."
reproduce: "python -m scripts.lazy_prices.b6_harness_t265 --all --out data/b6_local/harness_t265/run1  # results md5 886b6b0c791fd705b1361a70f6efcd0a (run1, run2; the reviewer's run3, run4; run5 after the review fixes)"
---

# B-6 Lazy Prices — T-265 small-cap arm verdict

**Power, stated first (A5.5, A6.3).**
- **H_OOS could confirm only an effect about twice the S&P one.**
  - t = −2 is reached at a gap of −3.8%/yr; 80% power needs −5.4%/yr.
  - At the S&P estimate (−1.96%/yr), H_OOS would pass about one time in six.
  - So a refutation is weak evidence against a small effect. It closes only the adjacent-pairing finding as a certifiable claim.
- **The long-leg gate detects only a long leg that beats SPY TR by about 12%/yr.** That is a central MDE80 of +0.31 Δ log wealth (§8). The realised MDE80 from the bootstrap sd is +0.22, or **+0.244 at the family level** (×3.08, §8).
  - A gate FAIL is therefore weak evidence too.
  - The short-leg diagnostic is the more informative statistic, but on the net legs it is inflated by the changers' higher cost (§4, the gross-vs-net disclosure).

**Pre-registration:** `docs/Sources/prereg_b6_lazy_prices_2026-11-11.md`. The T-265 arm's terms are §5–§8, A1.7, A1.10, A5–A6 (H_OOS) and A7 (the gap fill and the grid). A8 is the population-controlled fill check, with its erratum. It passed, with the forking path disclosed in §7. A9 is the FREEZE, `6b98883`. Each amendment was committed alone, before any T-265 price was read.

**Harness:** `scripts/lazy_prices/b6_harness_t265.py`, standalone, never `BacktestController`. It reaches B-2's frozen segment, death and ADV rules by reference through `scripts/smallcap_t265_b2_common.py`, which is byte-identical to main.

**S&P-arm verdict:** `docs/Audit/b6_lazy_prices_verdict_2026-11-12.md`.

## 1. Verdict

| | similarity (PRIMARY) | Δtone |
|---|---|---|
| **Gate**: 25% long-leg satellite, Δ log wealth vs 100% SPY TR, 120 months | **−0.093** | **−0.125** |
| `ci_low`, 1.25th percentile (family level, Bonferroni) | **−0.262** | **−0.317** |
| 95% interval (2.5th / 97.5th percentiles) | −0.244 / +0.071 | −0.299 / +0.073 |
| H1 met? | **no** | **no** |
| short-leg diagnostic: universe − changers, mean, %/yr, NET legs¹ | +2.04 | +1.44 |
| short-leg t_HAC (Newey-West, 3 lags), NET legs¹ | **+1.09** | **+1.33** |
| long − short, %/yr (t_HAC) | +1.60 (+0.49) | −0.09 (−0.05) |
| long leg − SPY TR, %/yr | −3.34 | −4.43 |

¹ **The frozen short-leg diagnostic is computed on NET legs (A9.3).** The changers' leg turns over about 3× the universe, so it is charged about 3× the cost: 51.0–58.5 bp per rebalance against 18.0 bp. That makes "universe − changers" larger by construction. The gross mechanism check (§4) gives +0.72%/yr with t +0.39 for similarity, and −0.19%/yr with t −0.18 for Δtone. The refutation reads the frozen net statistic, and that statistic is already below 2.

- **H1 (T-265): NOT MET for either signal.** Both point estimates are negative and below the central MDE80. Under §8's labelling rule they read as **"not demonstrable at this length"**.
- **H_OOS (A5.2/A6.1): FAILS, with the wrong sign.**
  - Changers minus universe, gross, is **+0.49%/yr** with **t_HAC +0.50**. Changers slightly *out*performed. The threshold was t_HAC ≤ −2.0.
  - Under A5.3, **the S&P adjacent-pairing short-leg finding (t +2.23) is closed permanently as a one-window artifact.** No re-slicing follows: no other pairing, window, tercile cut, form subset or universe.
  - The 10-Q-names-only companion: +0.53%/yr, t_HAC +0.43. It is formed in all 40 quarters and cannot meet H_OOS.
- **The brief's refutation sentence holds in BOTH arms.**
  - **Wording (verbatim):** "both ≤ 0 AND short-leg t_HAC < 2 ⇒ Lazy Prices is H0 on free data for this operator."
  - **S&P (window (c), corrected run):** `ci_low` −0.117 / −0.122; short-leg t_HAC −0.72 / −0.89 under R2's same-quarter pairing.
  - **T-265 (2016-Q1 → 2025-Q4):** `ci_low` −0.262 / −0.317; short-leg t_HAC +1.09 / +1.33.
  - The only S&P statistic that had cut against this sentence was the adjacent pairing's +2.23. H_OOS has now failed to reproduce it out of sample.
  - **Scope of the H0 (§10):**
    - YoY filing-text similarity and LM tone change on the R6 text: 10-K Items 1A + 7; 10-Q MD&A.
    - Quarterly holding, free EDGAR text, the two windows.
    - **Not** other sections, paid full text or other horizons.
    - B-2's survivorship caveat applies to the T-265 panel: it is survivorship-corrected, not complete, and the deaths it does carry are mostly takeovers.

## 2. Standalone statistics and the honest-N line (`[NN-SHARPE-CI]`, `[NN-MBL]`)
Monthly data, rf = 0, ×√12. Each `ci_low` is the 2.5th percentile of the same paired month-index block bootstrap (1,000 iterations, seed 0, auto block length 5).

| long leg | Sharpe (ci_low) | Sortino (ci_low) | turnover per quarter | cost drag, bps/yr |
|---|---|---|---|---|
| similarity | 0.56 (0.07) | 0.86 (0.10) | 76% | 175 |
| Δtone | 0.47 (−0.02) | 0.71 (−0.03) | 102% | 236 |

**MinBTL line: the SR a 10.0-year window requires, exact form.**
- **0.68** at the prereg's N_eff of 36.92 (§9).
- **0.94** at the current correlation-aware honest N of about 372 (CLAUDE.md `[NN-MBL]`, ruling 9.2).

Neither long leg's point estimate clears either line. Their ci_lows sit near zero.

**The long leg behaved like the IWM sleeve.**
- **IWM-TR sleeve** (75% SPY + 25% IWM) vs SPY: Δ log wealth −0.085, 95% CI low −0.266.
- **Similarity blend minus that sleeve:** −0.009 (point). No beta was estimated.
- §12 predicted this (a long leg "dominated by the size factor"). It is a description of the paths, not a factor regression.

## 3. Census (every fail-closed block passed; nothing below is a return)
**Prices.** B-2's census was recomputed and matched exactly:
- 4,674 files, of which 44 have fewer than 60 bars;
- 151 phantom zero-volume tails;
- 141 reused-ticker splices;
- 4,830 segments, 734 segment deaths;
- the full §3.3 count set.

**Price sources.** T-265 bars only (`data/research/t265/prices/`), plus the SPY / IWM / BIL TR twins (`data/processed/tr_reconciled/`, to 2026-05-22). There was no `data/processed` fill and no source switch.

**Text.** 1,317 files, verified against the A9 manifest (md5 `ea078498…`). The LM md5 equals the frozen one.

**Identity and price inputs.** The holder table, `cik_ticker_final.parquet`, the 4,674 price files and the twins were not pinned by the A9 manifest. They are now recorded in a manifest ADDENDUM: `docs/Sources/prereg_b6_t265_freeze_manifest_addendum_2026-11-17.json` (§7).

**Identity.**
- 4,699 of the 4,743 T-265 priced CIKs carry a price segment. The other 44 sit behind files with fewer than 60 bars.
- 205 tickers are ambiguous: 66 shared plus 141 reused, the two sets overlapping. 203 of them have a Form 3/4/5 holder record.

**Per rebalance, gate similarity.** 40 rebalances, 2016-03-31 → 2025-12-31, on the S&P harness's grid, with holdings to 2026-03-31. The same panel serves Δtone.

| count | min | median | max |
|---|---|---|---|
| **ranked** (§7.7 floor 300) | **1,416** | 1,984 | 2,339 |
| long / short tercile (floor 40) | 473 / 471 | 662 / 660 | 780 / 779 |
| usable signal before price | 2,396 | 3,132 | 3,800 |
| left out: identity not attributable | 23 | 34 | 47 |
| left out: no live segment at t | 79 | 204 | 290 |
| left out: no trade on t | 5 | 13 | 43 |
| left out: ADV < $1M | 445 | 722 | 1,156 |
| left out: ADV ≥ $200M | 91 | 244 | 429 |

- **Mix:** 10-Q-latest names are 17% of the ranked set in March quarters and up to 97% in the other quarters. Names with $1M–$20M ADV make up 52–61% of the ranked set.
- **H_OOS panel:** ranked 1,450–2,412; terciles at least 483.
- **Deaths in the universe:** 235 over 40 quarters (long 65, short 90).
- **Two diagnostics HALTED on their own floors and carry no number,** following the S&P harness's precedent:
  - `tenk_only`: as few as 63 ranked in non-March quarters;
  - `tenq_only`: 257 in 2016-03 and 296 in 2017-03.

## 4. Pre-named diagnostics (§7.5; none can meet H1)

| spec | Δ log W (ci_low 1.25%) | short-leg %/yr, net (t_HAC) | long−short t_HAC | short / universe deaths |
|---|---|---|---|---|
| flat 75 bps RT | −0.079 (−0.247) | +1.56 (+0.84) | +0.45 | 90 / 235 |
| STRESS, deaths −100% | −0.111 (−0.282) | +2.12 (+1.13) | +0.55 | 90 / 235 |
| LAST-PRICE, deaths 0 | −0.086 (−0.253) | +2.01 (+1.08) | +0.46 | 90 / 235 |
| SURVIVOR-ONLY | −0.082 (−0.248) | +1.04 (+0.56) | +0.06 | 0 / 0 |
| Jaccard | −0.114 (−0.284) | +1.41 (+0.83) | +0.07 | 85 / 235 |
| TF-IDF | −0.103 (−0.266) | +1.90 (+0.98) | +0.35 | 86 / 235 |
| MD&A only | −0.107 (−0.286) | +1.64 (+0.82) | +0.18 | 79 / 236 |
| risk factors only | −0.141 (−0.353) | +3.96 (+4.76) | +1.09 | 111 / 233 |
| 10-Q on the combo | −0.069 (−0.254) | +3.71 (+2.90) | +2.09 | 105 / 231 |
| 10-Q adjacent (net of cost) | −0.134 (−0.326) | +1.09 (+1.09) | −0.38 | 97 / 238 |
| 10-K only / 10-Q only | HALTED (floors) | — | — | — |

**Mechanism disclosure: gross vs net.** This is a check of how the net statistic is built, run after the review with `run_returns(..., cost="none")` on the frozen panels (the reviewer's `diag.py`). It is not a new test and has no N.

| spec | short leg NET, %/yr (t_HAC) | short leg GROSS, %/yr (t_HAC) | cost differential, %/yr | turnover per rebalance, short / universe | cost per rebalance, short / universe |
|---|---|---|---|---|---|
| similarity (gate) | +2.04 (+1.09) | +0.72 (+0.39) | 1.32 | 0.87 / 0.30 | 51.0 / 18.0 bp |
| Δtone (gate) | +1.44 (+1.33) | −0.19 (−0.18) | 1.62 | 1.02 / 0.30 | 58.5 / 18.0 bp |
| risk factors only | +3.96 (+4.76) | +2.33 (+2.80) | 1.63 | 1.04 / 0.33 | 60.5 / 19.8 bp |
| 10-Q on the combo | +3.71 (+2.90) | +2.46 (+1.93) | 1.25 | 0.88 / 0.34 | 51.5 / 20.2 bp |

**Read plainly.** On the frozen NET construction, two diagnostics show changers underperforming with a large t: risk-factors-only similarity (+4.76) and the 10-Q combo (+2.90).
- **Multiplicity:** ten diagnostics were evaluated. Bonferroni over ten at two-sided 5% needs |t| > 2.8.
  - Only the NET risk-only t exceeds that line.
  - **Gross, the risk-only t is +2.80, right at the line, and the 10-Q combo's is +1.93.**
  - The net construction charges changers about 3× the universe's cost, about 1.6%/yr of the risk-only spread.
  - Neither statistic has an S&P counterpart: both S&P versions halted on the 80%-of-members floor.
- **Where the risk-only spread comes from:**
  - **Cost:** about **1.6%/yr** of the net +4.0%/yr spread is cost differential (net − gross = 1.63%/yr).
  - **Deaths:** about **0.2%/yr** comes from the −30% death assumption. The short leg had 111 deaths against about 78 expected at one third of the universe's 233. At −30% each, the excess is worth roughly 0.2%/yr (arithmetic on the counts and the median leg size of 619).
- **Confound:** about **75% of risk-only name-quarters (74.8%) are 10-Q-latest names ranked on Part II Item 1A.** That is the text R6 excluded from 10-Q ranking because it flips between a one-line "no material changes" and the full list — "a formatting change, not a language change" (§13 R6). The risk-only spread may therefore measure that formatting flip, not a change of language.
- **These are data-suggested slices of this very sample.**
  - Under the same logic as A5.1 they **cannot be certified here**. They meet nothing, and nothing is licensed by them.
  - Testing one would need its own pre-registration on data not yet seen, and the T-265 window 2016–2025 is now spent.
- **On deployment:** a short leg is never deployable in a Roth (§2.6). The only route A5.3 licenses is a pre-registered 24-month forward paper book of a NEGATIVE SCREEN (a long book that excludes recent changers), and only if H_OOS had passed. It did not pass, so that route is **not earned here**. Nothing in this section earns it either.
- **The death assumption does not move the gate:** BASE −0.093, LAST-PRICE −0.086, STRESS −0.111.

**Per-year Δ log wealth, similarity** (descriptive):

| 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 Q1 |
|---|---|---|---|---|---|---|---|---|---|---|
| +0.022 | −0.016 | −0.010 | −0.011 | +0.009 | −0.003 | −0.010 | −0.022 | −0.029 | −0.029 | +0.005 |

## 5. Predictions (§12) vs the result
- **T-265 long-leg satellite, `ci_low` ≤ 0, dominated by the size factor: CONFIRMED** in the sense of §2. The blend minus the IWM sleeve is −0.009; no beta was estimated.
- **T-265 short-leg t_HAC +1.5 to +3.0: MISSED LOW.** The net statistic was +1.09 (similarity) and +1.33 (Δtone); gross it was +0.39 and −0.18.
- **Tone weaker than similarity: MIXED.** On the gate Δtone is weaker (−0.125 vs −0.093). On the net short leg it is slightly stronger (+1.33 vs +1.09).
- **Expected verdict, "the refutation sentence does NOT fully hold (≈45%)": WRONG.** It holds in both arms.
- **Honest prior** (T-265 10%; P(short-leg t ≥ 2) 30%): the outcome sits inside the 70% branch.

## 6. Determinism, smoke, independent recomputation
- **Smoke:** the first 12 months (four rebalances), checked by eye: months 2016-04 → 2017-03, no NaN, ranked 1,416–1,602. No number from it is quoted. md5 `778049e0…`.
- **Results md5 `886b6b0c791fd705b1361a70f6efcd0a`, identical every time:**
  - two full runs;
  - the reviewer's run3, and run4 from a holder table regenerated from source;
  - run5, after the review's code fix to `b6_cik_map.py`.
  - The monthly series and census CSVs are identical too: `monthly_gate_similarity.csv` `6871c182…`, `census_gate_similarity.csv` `b3f03737…`.
- **Independent recomputation:** the headlines were recomputed from the monthly CSVs with a hand-rolled Bartlett estimator, not the harness code. Δ log wealth −0.093482 / −0.125196, short-leg t +1.0933 / +1.3268, and H_OOS +0.00492/yr with t +0.4960 all match. The reviewer reproduced every headline to ≤ 1e-14.
- **Tests:** the review's 28-mutation table is now caught in full by the T-265 suite (`tests/test_b6_harness_t265.py`, `tests/test_b6_t265_fill.py`).

## 7. Disclosures (A7.5, A9.5, and the review of 2026-11-17)

**Inputs and data handling**
- 3.1% of small-cap 10-Ks omit Item 1A, as smaller reporting companies may. They have no combo pair and cannot be gate-ranked on 10-K quarters. They are the smallest firms.
- One out-of-window fetch failure: HTTP 503, CIK 1837254, 10-Q accepted 2026-05-15.
- The census's text counts were upper bounds before the ADV band. Section 3 gives the after-band counts.
- **Census correction:** co-registrant filings are keyed on (cik, accession). The `6e52752` census had dropped 67.

**The fill and the forking path in A8**
- The overlap gap was filled under A7: 252 firms, 11,195 filings, 5,510 gap accessions. A7.1's two-sided check failed on the high side.
- **A8 is not a clean pass.** A8's single population-controlled check passed (conditioned pair rates within 0.1–0.7 pp), but the path to it forked:
  - A8.2's committed count table already fixed two of the four conditioned rates exactly. Both MD&A pair rates are ok ÷ (total − no prior) from that table: 10-K 98.1 vs 98.3, 10-Q 99.3 vs 98.9.
  - With exclusion (a) alone, the combo rates were also arithmetic from that table. 10-Q combo would FAIL (88.1 vs 92.0, +3.9). 10-K combo would sit at the edge (93.8 vs 96.8, +3.0).
  - The director chose exclusion (b) (Item 1A not covered) knowing my hand-back's narrative of the two population differences (Item 1A omission 3.1% vs 0.0%).
  - So the deciding exclusion was chosen with the pass-relevant counts on the table.
  - No price or return was involved at any step, so H1 and H_OOS are not biased by it. But the fill's admission rests on a check chosen after its inputs were seen.
- **A8 erratum provenance.** The erratum header says "before the check's result was computed". It should read "before the result was SEEN".
  - The pre-erratum code built the conditioned table in memory, then halted on the count assertion before printing or writing it. That code was never committed.
  - The committed `fill_population_check` also builds the table before the assertion.
  - The implemented `seven` list names `("10-Q", "risk_ok_excl_not_covered_pct")` twice, so it checks six distinct rates. That is consistent with the reading.
  - The director ratified the erratum (quoted in the prereg's appended review note).

**Identity inputs (`[NN-FAIL-CLOSED]`)**
- The Form 3/4/5 holder table (`t265_ambiguous_ticker_users.parquet`) was built AFTER the freeze, by the first census run. That was 41 s after `6b98883`.
- The reviewer regenerated it from source byte-identical (md5 `6b9901eb…`), and the results md5 was unchanged.
- Its md5, `cik_ticker_final.parquet`'s, the 4,674 price files' and the twins' are now in the manifest ADDENDUM. The frozen manifest is unedited.
- `b6_cik_map.symbol_users` now halts when there are no insider zips, instead of returning an empty table. It is not part of the frozen harness, and the results md5 after the change is unchanged.
- **Latent defect, no effect in this run:** an overlap CIK with no S&P-panel rows would drop out silently (`b6_harness_t265.py:173` filters the S&P signals to the overlap set without counting a CIK that has none). All 392 overlap CIKs have rows, so nothing was dropped here. A future reuse must count or halt on it.

**Departures from A9, all immaterial or conservative**
- An H_OOS census failure halts the whole run, rather than reading H_OOS NOT EVALUABLE as A9.3(5) says. That is conservative, and it did not fire.
- **Deaths on rebalance boundaries:**
  - A death exactly on the next rebalance bar escapes the −30% when the name is not re-selected. It is sold at its last close. This happened once (one short / universe name in gate similarity). Where the name was re-selected, the formation-day rule applied D (17 universe cases).
  - A death on the hold-end bar is never penalised.
  - Both effects are immaterial.
- The frozen harness's docstrings say "AMENDMENT 8 (the freeze)" and "identity rule (A8)". They mean A9 and A4. They are left unfixed to keep the frozen md5.
- B-2's `ENV_PINS` are not enforced by this harness. Determinism was reproduced five times regardless.

**Survivorship**
- **B-2's survivorship caveat applies verbatim.** A PASS here would have been an UPPER BOUND.
- The panel misses most failure deaths, so a short-leg statistic is biased toward zero for genuine failures. The deaths it does carry are mostly takeovers.

## 8. N_trials
**+2 at this run:** the gate family {similarity, Δtone} +1, and H_OOS +1 as its own family (A6.2, A9.4). The director records them on main against AMENDMENT 9 (`6b98883`). This worktree does not touch `config/honest_n_trials.json`.

## Reproduce
```bash
python -m scripts.lazy_prices.b6_census --t265                      # text census (counts only)
python -m scripts.lazy_prices.b6_census --t265-fill-pop             # AMENDMENT 8's one check (PASS)
python -m scripts.lazy_prices.b6_harness_t265 --census-only --all --out data/b6_local/harness_t265/census
python -m scripts.lazy_prices.b6_harness_t265 --smoke --out data/b6_local/harness_t265/smoke
python -m scripts.lazy_prices.b6_harness_t265 --all --out data/b6_local/harness_t265/run1   # md5 886b6b0c…
```
