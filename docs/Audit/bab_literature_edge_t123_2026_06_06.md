---
task_id: T-2026-06-06-123
title: BAB (Betting-Against-Beta) — the decisive cross-sectional alpha referendum
date: 2026-06-06
author: Agent D (alpha/edge lane)
outcome: BAB does NOT clear factor-α t>2. Long-short beta-neutral α=−0.77%, t=−0.13,
  ci[−1.97,+1.72], p(α>0)=0.47 — statistically ZERO. Long-only low-beta α=−2.51%,
  t=−1.00. Book correlation 0.11 (genuinely orthogonal). REFERENDUM READ: strong
  (not airtight) evidence the equity-cross-sectional substrate lacks accessible
  factor-orthogonal alpha — caveated by the documented 2014-2025 low-beta headwind
  (our price data can't reach the pre-2014 era where BAB was strongest). Combined
  with T-117 + T-122, this points to the architecture/mission fork.
status: CURRENT
reproduce: |
  PYTHONHASHSEED=0 python -m scripts.analyze_bab_factor_t123        (determinism PASS)
  PYTHONHASHSEED=0 python -m scripts.run_bab_gauntlet_t123 --start 2014-01-01 --end 2025-12-31
---

# T-123 — Betting-Against-Beta: the cross-sectional alpha referendum

## TL;DR — the referendum result is a MISS (with one honest caveat)

The question this task was built to answer: *can ANY well-constructed, free-data,
FF-orthogonal CROSS-SECTIONAL literature edge clear factor-α t>2 in our harness,
or is the substrate empty of accessible cross-sectional alpha?* BAB is the
friendliest possible test (Frazzini-Pedersen 2014; α known to survive FF5).

**Answer: BAB does not clear t>2.** On the 2014-2025 substrate (695 names, 12-yr
MBL-clearing), with HAC + 1000-iter block-bootstrap CI:

| construction | α ann | α t | α t 95% CI | p(α>0) | clears t>2 | Sharpe (ci_low) |
|---|---|---|---|---|---|---|
| **BAB long-short β-neutral (classic FP)** | **−0.77%** | **−0.13** | [−1.97, +1.72] | 0.47 | **NO** | +0.38 (−0.08) |
| BAB long-only low-beta (deployable) | −2.51% | −1.00 | [−2.89, +0.80] | 0.13 | NO | +0.55 (−0.00) |

The long-short α t-stat is −0.13 with p(α>0)=0.47 — a **coin flip. Decisively zero
alpha**, not merely "below 2."

**The one honest caveat:** 2014-2025 is a well-documented **low-beta headwind**
period — the mega-cap growth bull where high-beta (tech) crushed low-beta, and BAB
underperformed globally (2009-2021). So this miss is consistent with BOTH the
"substrate empty" hypothesis AND BAB's known period-dependence. The truly decisive
test needs the pre-2014 era (esp. 2008, where BAB shined), which our Alpaca-sourced
price panel does not reach. **Strong suggestive evidence, not airtight proof.**

---

## 1. The edge (implemented, candidate-only)

`engines/engine_a_alpha/edges/betting_against_beta_edge.py` — mirrors
`xsec_momentum.py` (cross-sectional ranking + inverse-vol scaling + dollar-neutral
re-centering + vol-targeting + clip). Signal: per-name market-beta (cov/var vs the
equal-weight universe market, trailing 252d) → demeaned tilt `−(β_i − mean β)` =
**long below-average-beta, short above-average-beta**, inverse-vol scaled (FP
beta-neutralization spirit), dollar-neutral, vol-targeted.

Smoke test (2023-06-15, 75-name slice) — correct direction & dollar-neutral:
- top LONGS (low-beta): **AGG** (bond ETF — lowest β), ABBV, ATVI (defensives)
- top SHORTS (high-beta): **APP** (AppLovin), APTV, ARES (high-β growth)
- Σ signals = +0.0000 (dollar-neutral). 75/75 names scored (differentiated,
  unlike VRP's uniform tilt).

Registered `status='candidate'` (auto-register-on-import). **Not promoted; no
edges.yml/edge_weights.json/governor edits committed** (edges.yml gitignored).

---

## 2. Rigorous factor-α (the referendum) — `scripts/analyze_bab_factor_t123.py`

Construction: monthly-rebalanced BAB, beta vs the **cap-weighted market (FF MktRF)**
to avoid the equal-weight artifact that biased T-122; inverse-vol legs; FP
beta-neutralization (lever low-β leg to β=1, de-lever high-β leg to β=1); long-short
self-financing; net of 5bps/turnover. Daily P&L → FF5+Mom HAC regression + residual
moving-block bootstrap CI on the α t-stat (the same `regress_with_hac` +
`compute_alpha_tstat_with_bootstrap_ci` machinery T-117/T-122 used). Determinism: PASS.

**Factor loadings (long-short):** MktRF 0.51, SMB −0.38, HML 0.00, **RMW 0.29,
CMA 0.66**, Mom 0.20, R² 0.20. FF5 **partially spans** BAB on this substrate (the
CMA/RMW loadings — low-beta correlates with conservative-investment + profitable
firms). After controlling for all six factors, the residual α is **zero** (−0.77%,
t −0.13). So the brief's premise that "FF doesn't span the low-beta anomaly" does
NOT hold on our 2014-2025 S&P-large-cap substrate — here FF5's CMA/RMW eat most of
it, and the remainder is noise.

**Orthogonality to the existing book:** correlation +0.11 — BAB IS genuinely
diversifying vs the current 6-edge book (the whole point of picking it). It just
has no alpha to contribute.

---

## 3. Gauntlet — BAB also fails Gate-1 (contribution +0.000), like VRP

`scripts/run_bab_gauntlet_t123.py`, `validate_candidate`, 2014-2025 (655 tickers).
Passed Gate-0 (MBL) but **failed Gate-1: contribution = +0.000**, attribution_sharpe
= 0.0 → Gate-6 short-circuited (factor-α not computed by the engine).

**Notable:** I expected BAB (cross-sectional) to express where VRP (uniform timing)
washed out. It did not — BOTH show *exactly* +0.000 ensemble contribution. Two
readings, can't fully disambiguate from this run alone: (a) the `validate_candidate`
candidate-injection path may not add a hand-written candidate to the with/without
ensembles in this configuration; or (b) the long-equity ensemble's marginal capacity
is saturated and a diversifying-but-zero-α factor adds nothing measurable. Reading
(b) is consistent with the analytical result (BAB α ≈ 0 → nothing to add). Either
way, the **analytical standalone factor-α (§2) is the headline**, independent of the
Gate-1 short-circuit. (This also revises the T-122 inference: "cross-sectional vs
timing" is not the discriminator for Gate-1 contribution; both add ~0 here.)

---

## 4. The referendum verdict + the cumulative arc

Per the brief's pre-registration: *BAB misses t>2 → evidence the substrate lacks
accessible cross-sectional alpha → architecture/mission fork.*

The three findings now line up into a coherent, hard conclusion:

| task | edge type | result |
|---|---|---|
| T-117 | existing 11/13 edges (momentum/value/quality/accruals) | factor-NEGATIVE, closet-beta |
| T-122 | VRP (vol-timing) | equity proxy = beta-timing, α ≈ 0; washes out of ensemble |
| **T-123** | **BAB (cross-sectional, FF-orthogonal, free-data)** | **α ≈ 0 (t −0.13); does not clear t>2** |

**On the equity-cross-sectional S&P-large-cap / 2014-2025 substrate, no edge tested
— existing OR newly-implemented literature — produces factor-orthogonal alpha that
clears t>2.** The friendliest possible cross-sectional literature factor returns a
coin-flip α. This is strong evidence the binding constraint is the *substrate/
instrument set*, not the signal or the aggregator (consistent with the 2026-05-31
external research and the Phase-0 diagnostic).

**Caveat that keeps this honest, not nihilistic:** the 2014-2025 window is a known
low-beta headwind, and the universe is S&P large-caps (where BAB is weaker than in
broad/small-cap universes). So "the substrate is empty" is the leading hypothesis,
but a fair disconfirmation attempt (pre-2014 data, or a small-cap/broad universe)
has not been run because the data isn't on hand.

---

## 5. Forward (proposals for the director — NOT executed)

The referendum triggers the architecture/mission fork. Concrete, ranked:

1. **Get a wider/deeper substrate before concluding "empty."** The cheapest
   disconfirmation: a broad/small-cap universe (where BAB/low-beta is strongest)
   and/or pre-2014 history (2008 era). If BAB clears t>2 there, the constraint is
   our *narrow large-cap universe*, not "no alpha exists" — and the fix is universe
   expansion (the microcap/Norgate discussion), not new instruments. **Run this
   before the heavier fork.**
2. **If alpha is absent across substrates → non-equity instruments** (options/
   variance for the real VRP, futures-trend) — a genuine architecture extension
   (new data + a sleeve outside the cross-sectional edge bus), user-gated.
3. **Or accept the system's mission as a risk-management + falsification platform**
   (its MDD/defensive properties are real; its alpha-generation is not). A
   legitimate, honest end-state given the evidence.
4. **Fix the gauntlet candidate-injection / Gate-1 path** (separate, propose-first):
   two distinct hand-written candidates both yielding *exactly* +0.000 contribution
   warrants a look at whether `validate_candidate` actually loads injected
   candidates — otherwise every future hand-written edge's Gates 1-6 are untestable.

---

## 6. Reproduce + determinism

```
PYTHONHASHSEED=0 python -m scripts.analyze_bab_factor_t123
PYTHONHASHSEED=0 python -m scripts.run_bab_gauntlet_t123 --start 2014-01-01 --end 2025-12-31
```
`bab_factor_analysis.json` bit-identical across two runs (md5 88487e98…); seed=0.

## 7. Files

- `engines/engine_a_alpha/edges/betting_against_beta_edge.py` (NEW — candidate edge)
- `scripts/analyze_bab_factor_t123.py` (NEW — FP BAB factor construction + decomp)
- `scripts/run_bab_gauntlet_t123.py` (NEW — gauntlet runner)
- `data/measurements/bab_gauntlet_t123/{result.json,bab_factor_analysis.json}` (NEW, gitignored)
- This audit: `docs/Audit/bab_literature_edge_t123_2026_06_06.md`
- Builds on: T-117 (`edge_compression_t117`), T-122 (`vrp_literature_edge_t122`)

## 8. NOT included (hard boundaries honored)

- No promotion; BAB stays candidate. No edges.yml/edge_weights.json/governor edits committed.
- No TASK_LEDGER write (T-114 — proposed row in outbox). No cockpit/dashboard edits.
- No universe expansion / new data / architecture change (proposed only, §5). Branch only.
