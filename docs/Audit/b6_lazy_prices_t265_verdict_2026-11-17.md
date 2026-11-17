---
task_id: T-383 (B-6)
title: B-6 Lazy Prices — T-265 small-cap arm verdict (the gate and H_OOS)
date: 2026-11-17
author: ml-architect subagent (director-dispatched)
outcome: "T-265 ARM: H1 NOT MET for either signal — similarity Δ log wealth −0.094 (family ci_low −0.262), Δtone −0.125 (ci_low −0.317); short-leg t_HAC +1.09 / +1.33. H_OOS FAILS (changers − universe +0.49%/yr, t_HAC +0.50, wrong sign): the S&P adjacent-pairing finding is CLOSED as a one-window artifact. With the S&P arm, the brief's refutation holds in both arms: Lazy Prices is H0 on free data for this operator."
status: "T-265 arm DONE; awaiting independent review before any merge. N_trials +2 (gate family +1, H_OOS +1) — the director records it on main against AMENDMENT 9 (6b98883)."
reproduce: "python -m scripts.lazy_prices.b6_harness_t265 --all --out data/b6_local/harness_t265/run1  # results md5 886b6b0c791fd705b1361a70f6efcd0a (x2: run1, run2)"
---

# B-6 Lazy Prices — T-265 small-cap arm verdict

**Power, stated first (A5.5, A6.3).**
- **H_OOS could confirm only an effect about twice the S&P one.**
  - t = −2 is reached at a gap of −3.8%/yr; 80% power needs −5.4%/yr.
  - At the S&P estimate (−1.96%/yr), H_OOS would pass about one time in six.
  - So a refutation is weak evidence against a small effect. It closes only the adjacent-pairing finding as a certifiable claim.
- **The long-leg gate detects only a long leg that beats SPY TR by about 12%/yr.** That is a central MDE80 of +0.31 Δ log wealth (§8); the realised MDE80 from the bootstrap sd is +0.22.
  - A gate FAIL is therefore weak evidence too.
  - The short-leg diagnostic is the informative statistic.

**Pre-registration:** `docs/Sources/prereg_b6_lazy_prices_2026-11-11.md`. The T-265 arm's terms are §5–§8, A1.7, A1.10, A5–A6 (H_OOS) and A7 (the gap fill and the grid). A8 holds the population-controlled fill check, its erratum included, and passed. A9 is the FREEZE, `6b98883`. Each amendment was committed alone, before any T-265 price was read.

**Harness:** `scripts/lazy_prices/b6_harness_t265.py`, standalone, never `BacktestController`. It reaches B-2's frozen segment, death and ADV rules by reference through `scripts/smallcap_t265_b2_common.py`, which is byte-identical to main.

**S&P-arm verdict:** `docs/Audit/b6_lazy_prices_verdict_2026-11-12.md`.

## 1. Verdict

| | similarity (PRIMARY) | Δtone |
|---|---|---|
| **Gate**: 25% long-leg satellite, Δ log wealth vs 100% SPY TR, 120 months | **−0.094** | **−0.125** |
| `ci_low`, 1.25th percentile (family level, Bonferroni) | **−0.262** | **−0.317** |
| 95% interval (2.5th / 97.5th percentiles) | −0.244 / +0.071 | −0.299 / +0.073 |
| H1 met? | **no** | **no** |
| short-leg diagnostic: universe − changers, mean, %/yr | +2.04 | +1.44 |
| short-leg t_HAC (Newey-West, 3 lags) | **+1.09** | **+1.33** |
| long − short, %/yr (t_HAC) | +1.60 (+0.49) | −0.09 (−0.05) |
| long leg − SPY TR, %/yr | −3.34 | −4.43 |

- **H1 (T-265): NOT MET for either signal.** Both point estimates are negative and below the central MDE80. Under §8's labelling rule they read as **"not demonstrable at this length"**.
- **H_OOS (A5.2/A6.1): FAILS, with the wrong sign.**
  - Changers minus universe, gross, is **+0.49%/yr** with **t_HAC +0.50**.
  - So changers slightly *out*performed. The threshold was t_HAC ≤ −2.0.
  - Under A5.3, **the S&P adjacent-pairing short-leg finding (t +2.23) is closed permanently as a one-window artifact.** No re-slicing follows: no other pairing, window, tercile cut, form subset or universe.
  - The 10-Q-names-only companion was +0.53%/yr, t_HAC +0.43. It is formed in all 40 quarters and cannot meet H_OOS.
- **The brief's refutation sentence holds in BOTH arms.**
  - **Wording (verbatim):** "both ≤ 0 AND short-leg t_HAC < 2 ⇒ Lazy Prices is H0 on free data for this operator."
  - **S&P (window (c), corrected run):** `ci_low` −0.117 / −0.122; short-leg t_HAC −0.72 / −0.89 under R2's same-quarter pairing.
  - **T-265 (2016-Q1 → 2025-Q4):** `ci_low` −0.262 / −0.317; short-leg t_HAC +1.09 / +1.33.
  - The only S&P statistic that had cut against this sentence was the adjacent pairing's +2.23. H_OOS has now failed to reproduce it out of sample.
  - **Scope of the H0:** YoY filing-text similarity and LM tone change; the R6 ranking text; quarterly holding; free EDGAR text; the two windows. B-2's survivorship caveat applies to the T-265 panel: it is survivorship-corrected, not complete, and the deaths it does carry are mostly takeovers.

## 2. Standalone statistics and the honest-N line (`[NN-SHARPE-CI]`, `[NN-MBL]`)
Monthly data, rf = 0, ×√12. Each `ci_low` is the 2.5th percentile of the same paired month-index block bootstrap: 1,000 iterations, seed 0, auto block length 5.

| long leg | Sharpe (ci_low) | Sortino (ci_low) | turnover per quarter | cost drag, bps/yr |
|---|---|---|---|---|
| similarity | 0.56 (0.08) | 0.86 (0.10) | 76% | 175 |
| Δtone | 0.47 (−0.02) | 0.71 (−0.03) | 102% | 236 |

**MinBTL line, with the required SR for a 10.0-year window under the exact form:**
- **0.68** at the prereg's N_eff of 36.92 (§9).
- **0.94** at the current correlation-aware honest N of about 372 (CLAUDE.md `[NN-MBL]`, ruling 9.2).

Neither long leg's point estimate clears either line. Their ci_lows sit near zero.

**The size factor explains the long leg.**
- **IWM-TR sleeve** (75% SPY + 25% IWM) vs SPY: Δ log wealth −0.085, 95% CI low −0.266.
- **Similarity blend vs that IWM sleeve:** −0.009 (point).
- **Conclusion:** the long tercile behaved like small caps in general, which lagged SPY over this decade. §12 predicted exactly this.

## 3. Census (every fail-closed block passed; nothing below is a return)
**Prices:** B-2's census was recomputed and matched exactly:
- 4,674 files, of which 44 have fewer than 60 bars;
- 151 phantom zero-volume tails;
- 141 reused-ticker splices;
- 4,830 segments, 734 segment deaths;
- the full §3.3 count set.

The sources are T-265 bars only (`data/research/t265/prices/`) and the SPY / IWM / BIL TR twins (`data/processed/tr_reconciled/`, to 2026-05-22). There was no `data/processed` fill and no source switch.

**Text:** 1,317 files, verified against the A9 manifest (md5 `ea078498…`). The LM md5 equals the frozen one.

**Identity:**
- 4,699 of the 4,743 T-265 priced CIKs carry a price segment; the other 44 sit behind files with fewer than 60 bars.
- 205 tickers are ambiguous (66 shared plus 141 reused, the two sets overlapping). 203 of them have a Form 3/4/5 holder record.

**Per rebalance, gate similarity:** 40 rebalances, 2016-03-31 → 2025-12-31 on the S&P harness's grid, holdings to 2026-03-31. The same panel serves Δtone.

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

- **Mix:** 10-Q-latest names are 17% of the ranked set in March quarters and up to 97% in other quarters. Names with $1M–$20M ADV are 52–61% of the ranked set.
- **H_OOS panel:** ranked 1,450–2,412, terciles of at least 483.
- **Deaths in the universe:** 235 over 40 quarters (long 65, short 90).
- **Two diagnostics HALTED on their own floors and carry no number:** `tenk_only` (as few as 63 ranked in non-March quarters) and `tenq_only` (257 in 2016-03, 296 in 2017-03). This follows the S&P harness's precedent.

## 4. Pre-named diagnostics (§7.5; none can meet H1)

| spec | Δ log W (ci_low 1.25%) | short-leg %/yr (t_HAC) | long−short t_HAC | short / universe deaths |
|---|---|---|---|---|
| flat 75 bps RT | −0.079 (−0.247) | +1.56 (+0.84) | +0.45 | 90 / 235 |
| STRESS, deaths −100% | −0.111 (−0.282) | +2.12 (+1.13) | +0.55 | 90 / 235 |
| LAST-PRICE, deaths 0 | −0.086 (−0.253) | +2.01 (+1.08) | +0.46 | 90 / 235 |
| SURVIVOR-ONLY | −0.082 (−0.248) | +1.04 (+0.56) | +0.06 | 0 / 0 |
| Jaccard | −0.115 (−0.284) | +1.41 (+0.83) | +0.07 | 85 / 235 |
| TF-IDF | −0.103 (−0.266) | +1.90 (+0.99) | +0.35 | 86 / 235 |
| MD&A only | −0.107 (−0.286) | +1.64 (+0.82) | +0.18 | 79 / 236 |
| **risk factors only** | −0.142 (−0.354) | **+3.96 (+4.76)** | +1.09 | 111 / 233 |
| **10-Q on the combo** | −0.069 (−0.254) | **+3.71 (+2.90)** | **+2.09** | 105 / 231 |
| 10-Q adjacent (net of cost) | −0.134 (−0.326) | +1.09 (+1.09) | −0.38 | 97 / 238 |
| 10-K only / 10-Q only | HALTED (floors) | — | — | — |

**Read plainly.** Two diagnostics show changers underperforming with a large t: risk-factors-only similarity (t +4.76) and the 10-Q combo (t +2.90).
- **Multiplicity:** ten diagnostics were evaluated. Bonferroni over ten at two-sided 5% needs |t| > 2.8.
  - The risk-only t survives that; the 10-Q combo t is at the edge.
  - Neither statistic has an S&P counterpart: both S&P versions halted on the 80%-of-members floor.
- **Deaths do not drive the risk-only result.** Its short leg had 111 deaths against about 78 expected at one third of the universe's 233.
  - At −30% each, the excess is worth roughly 0.2%/yr of the 4.0%/yr spread (arithmetic on the counts and the median leg size of 619).
  - This is consistent with CMN locating much of the effect in the risk-factor section.
- **These are data-suggested slices of this very sample.**
  - Under the same logic as A5.1 they **cannot be certified here**. They meet nothing, and nothing is licensed by them.
  - Testing one would need its own pre-registration on data not yet seen, and the T-265 window 2016–2025 is now spent.
  - Even a confirmed short-leg effect is undeployable in a Roth (§2.6). The verdict above does not change.
- **The death assumption does not move the gate:** BASE −0.094, LAST-PRICE −0.086, STRESS −0.111.

**Per-year Δ log wealth, similarity** (descriptive): 2016 +0.022 · 2017 −0.016 · 2018 −0.011 · 2019 −0.011 · 2020 +0.009 · 2021 −0.003 · 2022 −0.010 · 2023 −0.022 · 2024 −0.029 · 2025 −0.029 · 2026 Q1 +0.005.

## 5. Predictions (§12) vs the result
- **T-265 long-leg satellite, `ci_low` ≤ 0, dominated by the size factor: CONFIRMED.** The blend minus the IWM sleeve is −0.009.
- **T-265 short-leg t_HAC +1.5 to +3.0: MISSED LOW.** The result was +1.09 for similarity and +1.33 for Δtone.
- **Tone weaker than similarity: MIXED.** On the gate Δtone is weaker (−0.125 vs −0.094). On the short leg it is slightly stronger (+1.33 vs +1.09).
- **Expected verdict, "the refutation sentence does NOT fully hold (≈45%)": WRONG.** It holds in both arms.
- **Honest prior** (T-265 10%; P(short-leg t ≥ 2) 30%): the outcome sits inside the 70% branch.

## 6. Determinism, smoke, independent recomputation
- **Smoke:** the first 12 months (four rebalances), checked by eye: months 2016-04 → 2017-03, no NaN, ranked 1,416–1,602. No number from it is quoted. md5 `778049e0…`.
- **Two full runs** gave the identical results md5 `886b6b0c791fd705b1361a70f6efcd0a`. The monthly series and census CSVs are identical too: `monthly_gate_similarity.csv` `6871c182…`, `census_gate_similarity.csv` `b3f03737…`.
- **Independent recomputation:** I recomputed the headlines from the monthly CSVs with a hand-rolled Bartlett estimator, not the harness code. Δ log wealth −0.093482 / −0.125196, short-leg t +1.0933 / +1.3268, and H_OOS +0.00492/yr with t +0.4960 all match.

## 7. Disclosures (A7.5, A9.5)
- 3.1% of small-cap 10-Ks omit Item 1A, as smaller reporting companies may. They have no combo pair and cannot be gate-ranked on 10-K quarters. They are the smallest firms.
- One out-of-window fetch failure: HTTP 503, CIK 1837254, 10-Q accepted 2026-05-15.
- The census's text counts were upper bounds before the ADV band. Section 3 gives the after-band counts.
- **Census correction:** co-registrant filings are keyed on (cik, accession). The `6e52752` census had dropped 67.
- **The overlap gap was filled** under A7: 252 firms, 11,195 filings, 5,510 gap accessions. A7.1's two-sided check failed on the high side. A8's single population-controlled check passed: conditioned pair rates within 0.1–0.7 pp.
- **B-2's survivorship caveat applies verbatim.** A PASS here would have been an UPPER BOUND. The panel misses most failure deaths, so a short-leg statistic is biased toward zero for genuine failures. The deaths it does carry are mostly takeovers.

## 8. N_trials
**+2 at this run:** the gate family {similarity, Δtone} +1, and H_OOS +1 as its own family (A6.2, A9.4). The director records them on main against AMENDMENT 9 (`6b98883`). This worktree does not touch `config/honest_n_trials.json`.

## Reproduce
```bash
python -m scripts.lazy_prices.b6_census --t265                      # text census (counts only)
python -m scripts.lazy_prices.b6_census --t265-fill-pop             # AMENDMENT 8's one check (PASS)
python -m scripts.lazy_prices.b6_harness_t265 --census-only --all --out data/b6_local/harness_t265/census
python -m scripts.lazy_prices.b6_harness_t265 --smoke --out data/b6_local/harness_t265/smoke
python -m scripts.lazy_prices.b6_harness_t265 --all --out data/b6_local/harness_t265/run1   # md5 886b6b0c… (x2)
```
