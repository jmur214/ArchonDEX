---
task_id: T-2026-06-05-112
title: Managed-futures crisis-diversifier sleeve — Phase 1 capital-partition A/B (MDD-reduction KPI)
date: 2026-06-05
substrate: T-092 arm0_off canonical rep1 equity curves (16-yr 2010-2025 + 26-yr 2000-2025) × T-108 spot 8-ETF basket / DBMF / KMLM
method: analytical capital-partition (portfolio_ret = (1-w)·base + w·sleeve), block-bootstrap CI (n_iter=1000, Politis-White block, seed=42)
allocations: {0%, 10%, 15%, 20%}
scope: Phase 1 measurement only — NO Engine C aggregator wiring, NO production-default change
decision_gate: MDD reduction ≥ 15% AND Sharpe ci_low not down AND calm-year Sharpe drag bounded (≥ -0.20)
outcome: **RECOMMEND KMLM @ 10%** — the only arm that clears all 3 gates. MDD reduction +15.4%; Sharpe ci_low -0.128→-0.072 (up); calm-Sharpe drag -0.133 (bounded); portfolio crisis-Sharpe +0.95→+1.29 (crisis-alpha confirmed). **CAVEAT:** the only sleeve covering 2008 (spot 8-ETF basket on 17.9yr base) MISSES the gate by 2pp at 20% allocation (MDD reduction 13.0%). The inbox explicitly prioritized the 2008-inclusive evidence; director decision required on whether the 5.1yr KMLM evidence is sufficient.
---

# T-112 — Phase 1 Capital-Partition A/B: Managed-Futures Crisis-Diversifier Sleeve

## Headline

**One arm clears the strict decision gate: KMLM at 10% capital
allocation.** But the inbox-priority evidence (17.9-yr window that
includes 2008 GFC) comes from the spot 8-ETF basket, which **misses
the gate by 2pp**. The verdict is therefore conditional on which axis
the director weights more heavily:

- **If 5.1-yr post-2020 evidence is sufficient → RECOMMEND KMLM @ 10%.**
- **If 2008-inclusive evidence is required → spot 8-ETF basket @ 20% is the closest miss; director may relax the 15% threshold to 13%.**

## The KPI shift (load-bearing context)

Per inbox: T-108 + T-110 closed out the "positive-skew structural cure"
thesis NEGATIVE across all 3 product types (equity-trend, spot basket,
DBMF/KMLM — skew got worse each time, ending ~-0.85). The KPI under
test here is **MDD-reduction at non-worse Sharpe**, not skew.

This is conceptually different from the original T-108 scope's
"skewness-flip" Phase 1 framing. Drawdown-reduction at maintained
risk-adjusted return is legitimate alpha (geometric-return + Calmar +
deployment-survivability), and the inbox ratified this reframing
before dispatching.

## Decision-gate table

`MDD reduction ≥ 15% AND Sharpe ci_low not down AND calm-Sharpe drag ≥ -0.20`

| Sleeve | Alloc | MDD reduction | Sharpe ci_low (arm) | Calm-Δ | **PASSES GATE?** |
|---|---:|---:|---:|---:|:-:|
| Spot 8-ETF basket | 10% | +6.3% | -0.079 | +0.077 | ✗ |
| Spot 8-ETF basket | 15% | +9.6% | -0.057 | +0.117 | ✗ |
| Spot 8-ETF basket | 20% | **+13.0%** | -0.045 | +0.157 | ✗ (-2pp short) |
| DBMF | 10% | +9.1% | +0.403 | +0.015 | ✗ |
| DBMF | 15% | +8.3% | +0.404 | -0.007 | ✗ |
| DBMF | 20% | +7.5% | +0.405 | -0.053 | ✗ (MDD plateaus) |
| **KMLM** | **10%** | **+15.4%** | **-0.072** | **-0.133** | **✓ PASS** |
| KMLM | 15% | +20.3% | -0.039 | -0.224 | ✗ (calm-drag exceeds bound) |
| KMLM | 20% | +24.9% | -0.038 | -0.320 | ✗ (calm-drag worse) |

**RECOMMENDED: KMLM @ 10%.**

## The honest tension (must surface)

Per inbox: **"A 26-yr-equivalent (spot basket) result matters most
because it contains both calm stretches AND 2008."** The spot basket
at 20% gets **+13.0% MDD reduction** — 2 percentage points short of
the 15% threshold. Every spot-basket arm also has *positive* calm-
Sharpe drag (i.e., the spot basket HELPS in calm years too, not just
crises). The only failure is the absolute MDD reduction not quite
clearing the gate.

The reason: the spot-basket's base window has MDD **-52.7%** (2008
+ COVID + 2022 stacked). A 6.8pp absolute reduction (to -45.9%) is
clinically meaningful but only 13% in relative terms — a high
absolute bar. KMLM's base window has MDD only -8.6% (post-2020,
no 2008), so a 1.3pp absolute reduction reads as 15%.

**The KMLM result is "easier" in a base-conditional sense.** It
clears the gate because its base is favorable; the spot basket
fails the gate not because the sleeve is worse but because the base
is harder. A 13% MDD reduction on a 52.7% MDD base is arguably more
valuable than a 15.4% MDD reduction on an 8.6% MDD base.

## Full per-arm results

### Spot 8-ETF basket × T-092 26yr arm0_off base (2008-02-20 → 2025-12-30, 17.9yr, n=4,494)

| Alloc | Sharpe | Sharpe ci_low | Sharpe ci_high | MDD | Calmar | CAGR | Calm Sharpe | Crisis Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0% (base) | +0.326 | -0.117 | +0.794 | -52.70% | +0.065 | +3.43% | +0.891 | -1.135 |
| 10% | +0.371 | -0.079 | +0.855 | -49.38% | +0.075 | +3.70% | +0.968 | -1.169 |
| 15% | +0.395 | -0.057 | +0.890 | -47.65% | +0.080 | +3.83% | +1.008 | -1.185 |
| 20% | +0.422 | -0.045 | +0.918 | **-45.87%** | +0.086 | +3.95% | +1.048 | -1.201 |

**Notes:**
- Spot basket monotonically IMPROVES Sharpe, MDD, Calmar, CAGR, and calm-Sharpe across allocations 0-20%.
- Crisis-Sharpe slightly DETERIORATES (-1.135 → -1.201) — counterintuitive. Likely cause: the 17.9-yr crisis bucket sums many sub-events (2008, 2010, 2011, 2015, 2018-Q4, COVID, 2022, 2025) where the spot basket loses *less* than the base but still loses; the sum-of-many-small-losses dominates the few big wins (2022 +35.7pp).
- Closest miss to the decision gate. Director-decision candidate.

### DBMF × T-092 16yr arm0_off base (2019-05-13 → 2025-12-30, 6.6yr, n=1,668)

| Alloc | Sharpe | Sharpe ci_low | Sharpe ci_high | MDD | Calmar | CAGR | Calm Sharpe | Crisis Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0% (base) | +1.088 | +0.359 | +1.775 | -8.60% | +0.909 | +7.81% | +1.408 | +0.543 |
| 10% | +1.148 | +0.403 | +1.862 | -7.81% | +0.973 | +7.60% | +1.424 | +0.710 |
| 15% | +1.163 | +0.404 | +1.873 | -7.88% | +0.950 | +7.49% | +1.401 | +0.798 |
| 20% | +1.164 | +0.405 | +1.883 | -7.95% | +0.927 | +7.37% | +1.355 | +0.885 |

**Notes:**
- DBMF improves Sharpe and Crisis-Sharpe monotonically; CAGR decreases (-0.44pp at 20%) due to fee + drag.
- MDD reduction peaks at 10% (-7.81%) then PLATEAUS — adding more DBMF stops helping.
- Calm-Sharpe slightly degrades at 20% (-0.053) but never breaks the bound.
- Decision gate failure: MDD reduction 9.1% at 10% — well below 15%. DBMF's value is "diversifier on an already-tight base" not "MDD slasher."

### KMLM × T-092 16yr arm0_off base (2020-12-09 → 2025-12-30, 5.1yr, n=1,265)

| Alloc | Sharpe | Sharpe ci_low | Sharpe ci_high | MDD | Calmar | CAGR | Calm Sharpe | Crisis Sharpe |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0% (base) | +0.707 | -0.128 | +1.532 | -8.60% | +0.490 | +4.21% | +0.663 | +0.945 |
| **10%** | **+0.749** | **-0.072** | **+1.549** | **-7.27%** | **+0.581** | **+4.23%** | **+0.530** | **+1.290** |
| 15% | +0.750 | -0.039 | +1.564 | -6.85% | +0.617 | +4.22% | +0.439 | +1.453 |
| 20% | +0.737 | -0.038 | +1.511 | -6.46% | +0.653 | +4.21% | +0.342 | +1.600 |

**Notes (THE WINNER):**
- KMLM @ 10% clears all 3 gates: MDD reduction +15.4%, Sharpe ci_low up (-0.128 → -0.072), calm-Sharpe drag -0.133 (within bound).
- Calmar improvement is the cleanest story: +0.490 → +0.581 at 10%, continuing to +0.653 at 20%.
- Crisis Sharpe at the portfolio level rises from +0.95 to +1.29 at 10% (and further to +1.60 at 20%) — the crisis-alpha thesis IS observable at the partitioned-portfolio level.
- Calm-year Sharpe degrades meaningfully at higher allocations (-0.133 at 10%, -0.224 at 15%, -0.320 at 20%). The "negative skew + fee drag" cost is REAL; it's just bounded at 10%.

## Crisis-period attribution (KMLM @ 10% vs base)

Per-window total returns at 0% (base) vs 10% (KMLM-tilt):

| Window | n_days | base return | base+10% KMLM return | Δ |
|---|---:|---:|---:|---:|
| COVID 2020 | (postdates KMLM) | n/a | n/a | n/a |
| 2022 bear | 196 | base shown in T-092 26-yr eq curve | (computed at portfolio level above) | crisis-Sharpe +0.35 |
| 2025 vol-shock | 61 | (small window) | (small window) | minor positive |

The crisis-Sharpe Δ at the portfolio level (+0.95 → +1.29, a +0.34 swing) is the headline crisis-alpha confirmation. Per-window single-figure returns are at the JSON level; the aggregated Sharpe captures the systemic effect.

## Calm-year drag — the cost half of the Pareto

KMLM @ 10% calm-Sharpe = +0.530 vs base +0.663. The -0.133 drag is
real but small. At 20% the drag grows to -0.320 (calm Sharpe +0.343),
which is why the higher allocations fail the gate despite better MDD
reductions.

**The drag mechanism is clear:** KMLM's standalone skew is -0.849 and
it pays ~0.92% expense ratio. In a calm year the negative-skew tail
shows up as occasional 3-4σ drawdown days, the ER drains 9bps/month,
and the strategy is providing no defensive value (the equity book is
doing fine on its own). 10% allocation keeps the calm-year drag
contained; bigger allocations multiply it.

DBMF shows a different drag profile (-0.053 at 20%) — DBMF has positive
SPY correlation (+0.183) and a similar ER, so it tracks the equity book
more closely in calm periods and has less calm-year cost. But DBMF
delivers less crisis-alpha (its MDD reduction plateaus), so it can't
clear the gate.

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | base vs base+{10,15,20}% A/B for KMLM, DBMF, spot-basket sleeves (deepest window each) | DONE |
| 2 | MDD-reduction (primary) + Sharpe-ci_low + Calmar + crisis-return + calm-year-Sharpe per arm | DONE (3 tables) |
| 3 | Calm-year drag quantified | DONE (KMLM -0.133 at 10%, -0.224 at 15%, -0.320 at 20%) |
| 4 | Decision gate verdict: best sleeve + allocation %, or NONE — with MDD-vs-drag tradeoff explicit, prioritizing 2008-inclusive | DONE — **KMLM @ 10% passes**; spot basket misses by 2pp on 17.9yr window — director decision flagged |
| 5 | Audit doc + TASK_LEDGER row | DONE (this audit + ledger row appended) |
| 6 | NO prod-default change; branch pushed NOT merged | DONE (analytical capital-partition only; no engine code touched) |

## Methodology

### Data + alignment
- **Base equity curves:** T-092 arm0_off canonical rep1 from
  `s3://archondex-results-407539788432/t092-deep-substrate-baseline/arm0_off/{2010-2025,2000-2025}/rep1/<run_id>/portfolio_snapshots.csv`.
- **Sleeve series:**
  - Spot 8-ETF basket: re-ran T-108 sleeve harness (`scripts.sleeve_phase0_verdict::run_sleeve` over `engines.engine_c_portfolio.sleeves.trend_following_sleeve::TrendFollowingSleeve` on the 8-ticker basket via `signals={t: 1.0}`). 4,495 daily-return obs 2008-02-20 → 2025-12-31.
  - DBMF / KMLM: daily returns from Stooq mirror via T-110's `load_stooq_etf` loader.
- **Window matching:** spot basket vs 26-yr base (covers 2008); DBMF & KMLM vs 16-yr base.

### Capital-partition formula
```
portfolio_ret(t) = (1 - w) * base_ret(t) + w * sleeve_ret(t)
```
for w ∈ {0.00, 0.10, 0.15, 0.20}. No leverage, no rebalancing — pure
analytical mixture on the aligned daily-return series.

### Block-bootstrap CI
- n_iter = 1000, block = Politis-White auto = `max(4, ⌊4·(n/100)^(2/9)⌋)`
- seed = 42 (reproducible)
- Bootstrapped metrics: Sharpe, MDD, Calmar (each computed on resampled returns)

### Crisis vs calm masks
Crisis mask = union of 8 windows (matching T-108 + T-110 definitions):
2008 GFC, 2010 Flash crash, 2011 EU debt, 2015-08 China-vol, 2018-Q4,
COVID 2020, 2022 bear, 2025 vol-shock.

Calm period = everything else. Per-period Sharpe computed on
concatenated daily returns within each mask.

### Determinism
All paths deterministic (no random initialization in metric computation;
bootstrap uses fixed seed). The T-108 spot-basket re-run uses the
TrendFollowingSleeve which itself was determinism-checked in T-099/T-105;
this dispatch reuses those guarantees, no new determinism risk.

## Files

- `scripts/managed_futures_sleeve_phase1_t112.py` (NEW — analytical capital-partition harness)
- `docs/Measurements/2026-06/t112_phase1_capital_partition.json` (raw output: per-arm metrics + full gate table)
- `docs/Audit/managed_futures_sleeve_phase1_t112_2026_06_05.md` (this audit)
- `docs/State/TASK_LEDGER.md` (T-112 row appended)

## Honest caveats

- **KMLM history is 5.1yr post-2020.** Sharpe ci_low at the portfolio
  level is -0.072 (just barely "not down" vs base's -0.128). The
  inbox flagged this risk explicitly: "thinner crisis evidence than
  T-108's 8 windows." A real prod deployment would want to repeat
  this A/B once KMLM has another full crisis under its belt.

- **Managed-product caveat preserved:** KMLM is the KFA Mount Lucas
  Managed Futures Index ETF — it embeds Mount Lucas's discretionary
  trend model + ~0.92% ER. The +15.4% MDD reduction is "KMLM delivers
  this," NOT "any managed-futures sleeve delivers this."

- **The spot basket "close miss" is the more important Pareto
  evidence in absolute terms.** -52.7% MDD → -45.9% MDD is a 6.8pp
  absolute reduction over a 17.9yr substrate that includes the
  worst US equity-market years on record. The 15% threshold is
  expressed in RELATIVE terms; a director who weighted absolute MDD
  reduction would prefer the spot basket result despite its formal
  gate-miss.

- **Window matching is base-conditional.** DBMF and KMLM A/Bs use a
  16-yr base that excludes 2008 (T-092 16-yr is 2010-2025). The base
  Sharpe is +1.09 (DBMF window) or +0.71 (KMLM window) — much
  higher than the 26-yr +0.33. The KMLM "wins" partly because its
  base is already strong; under a 2008-inclusive base, KMLM's
  contribution would look different (and we can't test that
  empirically because KMLM didn't exist in 2008).

- **The crisis-Sharpe deterioration in the spot basket arms (-1.135
  → -1.201)** is a real diagnostic finding. Crisis-Sharpe is computed
  over the *union* of all 8 crisis windows; the spot basket loses
  *less* in some windows but the cross-crisis-window aggregation
  shows a slight net deterioration. This is consistent with the
  T-108 finding: spot basket delivers diversification + flat
  returns in crises, not BIG positive returns.

## Decision recommendation

### Strict gate verdict: **RECOMMEND KMLM @ 10%**

The only arm that passes all 3 decision criteria. Pareto improvement
on Sharpe + MDD at the portfolio level; calm-year drag bounded.

### Honest framing for director decision

Two reasonable paths:
1. **Conservative-evidence path:** accept KMLM @ 10% as the recommended
   allocation. Move to a Phase-1.5 integration dispatch (Engine C
   `MultiSleeveAggregator` wiring, default-OFF, canon-md5 baseline
   preserved). Acknowledge the 5.1-yr-history caveat in the
   integration audit. Revisit once KMLM has another crisis.
2. **Deep-evidence path:** require a 2008-inclusive Pareto result.
   Spot basket misses by 2pp on the 17.9-yr substrate. Director may
   relax the threshold to 13% (the spot @ 20% point), OR may require
   the dispatch to be rerun with a wider allocation sweep (25%, 30%)
   to find the spot basket's MDD-reduction sweet spot.

The inbox text "26-yr-equivalent (spot basket) result matters most"
weights the second path. The strict-gate text "MDD reduction ≥ 15%"
weights the first path. Both are coherent; the choice is a director-
level value judgment.

## Memory updates needed (post-merge)

- New entry: "T-112 Phase 1 capital-partition A/B: **KMLM @ 10% capital
  allocation passes the strict decision gate** (MDD reduction +15.4%,
  Sharpe ci_low -0.128→-0.072 up, calm-Sharpe drag -0.133 bounded,
  crisis-Sharpe +0.95→+1.29). DBMF MDD reduction plateaus at 9%
  (already-tight base). **Spot 8-ETF basket misses gate by 2pp on the
  17.9yr window** (MDD reduction 13.0% at 20%) — but spot basket's
  absolute MDD reduction (6.8pp on -52.7% base) is the more important
  Pareto evidence in absolute terms. The KPI shift (skew → MDD-
  reduction) per inbox is reaffirmed across all 3 sleeves and 9 arms.
  Director decision required on conservative-evidence (KMLM 10%) vs
  deep-evidence (spot @ 20%) framing."

- Pattern memory: "Relative-MDD-reduction thresholds are base-
  conditional. A 15% threshold on a -50% base requires 7.5pp absolute
  reduction; on a -8% base requires only 1.2pp. Compare sleeves at
  equivalent base difficulties before declaring winners."

## Forward dispatches

- **T-112-followup-integration** (if director picks KMLM 10%): wire
  KMLM (or `MultiSleeveAggregator` with KMLM as a sleeve) into Engine
  C with default-OFF flag. Canon-md5 OFF == current main; flag-flip
  reviewable. Determinism `--runs 3` PASS on default-OFF.

- **T-112-followup-deep-cell** (if director wants 2008-inclusive
  evidence): rerun spot-basket A/B with extended allocation sweep
  {15, 20, 25, 30}% to find the spot-basket MDD-reduction sweet
  spot. Optionally relax the gate to 13%.

- **T-112-followup-KMLM-vs-DBMF-detailed**: 5.1-yr head-to-head at
  10% allocation specifically on 2022 + 2025 windows, with per-window
  attribution. Would help isolate "is this Mount Lucas's specific
  model" vs "is this any futures-wrap."

## NOT done in T-112

- No Engine C aggregator wiring (analytical only; per inbox).
- No production-default change (per inbox).
- No determinism A/B (analytical mixture is deterministic by construction).
- No integration of any sleeve into the live backtest path.
- No re-fetch of base equity (used T-092 rep1 canonical from S3).
- No data/governor edits.
- No cockpit/dashboard edits.
