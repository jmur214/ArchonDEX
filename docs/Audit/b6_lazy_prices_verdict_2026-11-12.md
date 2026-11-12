---
task_id: T-383 (B-6)
title: B-6 Lazy Prices — verdict (S&P arm; T-265 arm pending its census and freeze)
date: 2026-11-12
author: ml-architect subagent (director-dispatched)
outcome: "S&P ARM, gate window (c) 2020-Q2→2025-Q4: H1 NOT MET for either signal — similarity Δ log wealth −0.027 (ci_low −0.116 at the family level), Δtone −0.041 (ci_low −0.128); short-leg t_HAC −0.77 / −1.29 (wrong sign). The S&P half of the refutation holds; the refutation itself needs the T-265 arm. Window (d) NOT EVALUABLE (census halt)."
status: "S&P arm DONE on (c) (prereg AMENDMENT 2); N_trials +1 consumed. T-265 arm: stream running, not frozen. Determinism x2: results md5 2ec68e5a9248af3a5138eb940960aa6f."
reproduce: "python -m scripts.lazy_prices.b6_harness_sp --all --out data/b6_local/harness_sp/run1  # md5 2ec68e5a9248af3a5138eb940960aa6f (x2); (d) census: --census-only --spec d_similarity  # exit 2, md5 c3effa85be82e4f5941051cd97dac980"
---

# B-6 Lazy Prices — verdict

Pre-registration: `docs/Sources/prereg_b6_lazy_prices_2026-11-11.md` — the draft, AMENDMENT 1 (rulings
R1–R9, committed alone at `fc28a7d` before any return) and AMENDMENT 2 (the gate window after the (d)
census halted, committed alone at `2a90763` before any return). Harness:
`scripts/lazy_prices/b6_harness_sp.py` (standalone, never `BacktestController`; locks
`tests/test_b6_harness_sp.py`). All outputs worktree-local under `data/b6_local/harness_sp/`.

## 1. S&P arm, window (d) 2016-Q1 → 2025-Q4 — NOT EVALUABLE (census halt, no return)
The frozen census (§7.7, §11) halted the (d) gate (exit 2) before any return: **13 of 40 rebalances below
the 80%-of-members floor, worst 2016-03-31 at 67.9%**; bit-identical twice (census CSV md5
`c3effa85be82e4f5941051cd97dac980`, HALT list `8f80dc57c89739fbae9ea976c86fe1e2`; reproduced again under
the renamed spec `d_similarity`). Cause: T-265 holds no bars for 14–20% of 2016–2019 members (acquired or
failed names — the B-2 §3.1 survivorship hole), not text coverage. Per AMENDMENT 2 (director, B-1
precedent; lowering the floor rejected), (d) re-runs as its own pre-registered trial once the price hole
closes.

| rebalance | share | | rebalance | share |
|---|---|---|---|---|
| 2016-03-31 | **0.679** | | 2017-12-29 | 0.778 |
| 2016-06-30 | 0.741 | | 2018-03-29 | 0.742 |
| 2016-09-30 | 0.747 | | 2018-09-28 | 0.792 |
| 2016-12-30 | 0.753 | | 2018-12-31 | 0.795 |
| 2017-03-31 | 0.724 | | 2019-03-29 | 0.761 |
| 2017-06-30 | 0.767 | | 2020-03-31 | 0.782 |
| 2017-09-29 | 0.772 | | | |

## 2. S&P arm, gate window (c) 2020-Q2 → 2025-Q4 — H1 NOT MET

**Setup (frozen; AMENDMENT 2).** 23 quarterly rebalances 2020-06-30 → 2025-12-31, holdings to 2026-03-31:
**69 months (5.75 years)**. Prices: `data/processed` closes (exact TR after 2020-04-09). Universe: PIT S&P
500 members with a CIK and a usable signal (R6: 10-K combo, 10-Q MD&A; latest filing with
`decision_floor_date` ≤ t, within 6 months) and a bar at t. Census PASS every quarter (ranked 416–474,
83.4–94.8% of members; terciles ≥ 138). Costs 10 bps RT. Exits: 58 over the window (last close → BIL TR).
Bootstrap: paired month-index moving blocks, 1,000 iterations, seed 0, block 5. **Determinism: two full
runs, identical results md5 `2ec68e5a9248af3a5138eb940960aa6f`.** Smoke (the first 12 months) passed
first: no NaN, 5 exits, SPY TR +2.98%/month mean (≈ +42% over the year, matching the period).

### 2.1 The gate — long-leg 25% satellite, Δ log wealth vs 100% SPY TR (family level, Bonferroni)
| signal | Δ log wealth (69 m) | ci_low **1.25th pct (gate)** | ci_low 2.5th | ci_high 97.5th | realized MDE80 | H1 |
|---|---|---|---|---|---|---|
| **similarity** (non-changers long) | **−0.027** | **−0.116** | −0.107 | +0.053 | 0.114 | **NOT MET** |
| **Δtone** (tone improved long) | **−0.041** | **−0.128** | −0.115 | +0.028 | 0.106 | **NOT MET** |

**Label (B-2's binding rule, §8):** both point estimates are below the pre-data central MDE80 (+0.101
total) → **"not demonstrable at this length"**, and the brief's refutation sentence is evaluated beside it
(§2.3).

### 2.2 The short-changers diagnostic (the most informative statistic, §8 / A2.2)
Monthly s_t = r(EW universe) − r(EW bottom tercile); positive = changers underperform. Newey-West, 3 lags.
| signal | mean s, ann. | **t_HAC** | long − short, ann. | t_HAC |
|---|---|---|---|---|
| similarity | **−0.77%** | **−0.77** | −1.19% | −0.59 |
| Δtone | **−1.27%** | **−1.29** | −2.69% | −1.44 |

**The changers did NOT underperform in this window — both point estimates have the wrong sign**, and
neither is distinguishable from zero.

### 2.3 The brief's refutation sentence, evaluated literally
*"Refutation: both ≤ 0 AND short-leg t_HAC < 2 ⇒ Lazy Prices is H0 on free data for this operator."*
- "both ≤ 0" refers to the two arms' H1 statistics (S&P and T-265). **S&P: ci_low ≤ 0 — TRUE** (−0.116
  similarity; −0.128 Δtone). **T-265: NOT YET EVALUATED** (its stream is running; its arm is not frozen).
- "short-leg t_HAC < 2": **S&P — TRUE** (−0.77; −1.29). T-265 — not yet evaluated.
- **Literal result: the S&P half of the refutation HOLDS; the refutation as a whole CANNOT be recorded
  until the T-265 arm runs.** If T-265 also returns ci_low ≤ 0 and short-leg t_HAC < 2, the verdict is
  "Lazy Prices is H0 on free data for this operator" — the first verdict doc T-237 never got.

### 2.4 Where the long leg's shortfall comes from (arithmetic on the reported means; not a new test)
Long − SPY = **−1.99%/yr** = (long − EW universe ≈ −0.42%/yr) + (EW universe − SPY ≈ −1.57%/yr). Most of
the satellite's shortfall is the **equal-weight vs cap-weight tilt** over 2023–2025 (mega-cap
concentration; per-year Δ log wealth +0.005 / +0.010 / +0.015 in 2020–22, −0.026 / −0.020 / −0.014 in
2023–25), not the text signal; the signal's own contribution (long vs its universe) is small and
negative. The prereg named no EW-universe benchmark for the S&P gate (B-1's §3.7 lesson), so this is
reported, not gated.

### 2.5 Standalone statistics (with ci_low, `[NN-SHARPE-CI]`) and the MBL line
Long leg (similarity): Sharpe **0.84, ci_low 0.21**; Sortino 1.46, ci_low 0.31 — against SPY TR's 1.01 over
the same months. **MBL line:** at N_eff 36.92 a 5.75-year window needs SR ≥ ≈ 0.90 to clear MinBTL; the
long leg's 0.84 does not, and it does not beat SPY. Turnover: the long leg replaces ≈ 72% of its names per
quarter (similarity) and ≈ 94% (Δtone) — the ranks are unstable quarter to quarter.

### 2.6 Pre-named diagnostics (§7.5; on the gate's window per A2.2; none can meet H1)
| diagnostic | Δ log wealth | ci_low 2.5th | short-leg mean | short-leg t_HAC |
|---|---|---|---|---|
| 20 bps cost | −0.029 | −0.109 | −0.66% | −0.66 |
| exits at D = −30% | −0.036 | −0.117 | −0.69% | −0.68 |
| Jaccard | −0.034 | −0.105 | −1.13% | −0.85 |
| T-237's TF-IDF cosine | −0.018 | −0.094 | −0.66% | −0.55 |
| MD&A-only (both forms) | −0.028 | −0.106 | −0.76% | −0.68 |
| **10-Q adjacent-quarter pairing** | −0.001 | −0.104 | **+2.10%** | **+2.27** |
| Risk-Factors-only | HALTED at its census (2020-06-30 share 0.726) | | | |
| 10-Q combo | HALTED (3 quarters < 80%) | | | |
| 10-K-only / 10-Q-only rankings | HALTED (a single form cannot fill a quarter: 20–98 names) | | | |

**On the one diagnostic with t_HAC > 2.** Ranking 10-Qs against the ADJACENT prior quarter (the A1.2
diagnostic — "the closest reading of 'quarter-to-quarter'") gives changers underperforming by 2.1%/yr,
t_HAC +2.27, while the satellite stays flat (−0.001, ci_low −0.10). It is **one of 8 diagnostics that ran;
under the null, one t above 2 among 8 is unsurprising** (Bonferroni across 8 needs |t| ≈ 2.7). It cannot
meet H1 and does not enter the refutation clause, which reads the gate construction. It is recorded as a
**nomination**: if the T-265 arm's adjacent-quarter diagnostic points the same way, the adjacent pairing
is the candidate for its OWN pre-registered test — never a re-reading of this one.

### 2.7 Predictions (§12) vs outcome (they were written for the 10-year window (d))
| prediction | outcome |
|---|---|
| similarity satellite point in [−0.05, +0.10]; ci_low ≤ 0; "not demonstrable" | **as predicted** (−0.027; −0.116; label applies) |
| S&P short-leg t_HAC +1.0 to +2.5 | **wrong** — −0.77 (wrong sign) |
| tone weaker than similarity | **as predicted** (−0.041 vs −0.027) |

## 3. N_trials
**+1 consumed (the S&P arm, run on (c)).** The (d) census halt consumed none (no return). The T-265
arm's +1 is consumed at its run. Honest N context: registry N_eff 36.92 (it omits standalone-harness
trials, health_check MEDIUM `573fc62`); the hand count rises by this trial.

## 4. T-265 arm — pending
The signals-only stream (restarted 2026-11-12 19:48 UTC) is running; its census and freeze follow its
completion. Nothing has been run on it.
