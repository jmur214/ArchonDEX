---
task_id: T-2026-06-05-110
title: DBMF + KMLM managed-futures ETFs Phase 0 diagnostic (T-108 RECONSIDER follow-up)
date: 2026-06-05
substrate: Stooq mirror; DBMF (2019-05-13 → 2026-05-22, 7.0yr), KMLM (2020-12-09 → 2026-05-22, 5.4yr); SPY reference
products: iMGP DBi Managed Futures Strategy (DBMF) + KFA Mount Lucas Managed Futures Index (KMLM)
scope: Phase 0 diagnostic only — NO integration, NO engine touches
outcome: **MIXED — crisis-alpha diversifier, NOT a skew cure.** DBMF skew -0.749 ci [-1.026, -0.425]; KMLM skew -0.849 ci [-1.302, -0.424]. The futures-wrapper hypothesis is REFUTED: wrappers make skew WORSE, not better than T-108's spot basket (-0.408). BUT crisis-alpha is MORE extreme — DBMF +57pp in 2022, KMLM +73pp in 2022, KMLM also negatively correlated to SPY (-0.139, beta -0.12). Path-B Layer 2 "structural skew cure" thesis closes-out NEGATIVE; the secondary "crisis-alpha diversifier" thesis is REINFORCED.
---

# T-110 — DBMF / KMLM Managed-Futures ETFs (Phase 0)

## Headline

**The futures-wrapper hypothesis from T-108 is REFUTED, but the practical
value of these products is even GREATER than the spot-ETF basket.**

T-108 closed RECONSIDER with the hypothesis: "self-built spot-ETF trend
fails skew (-0.41) because spot ETFs lack futures carry/roll/leverage;
real managed-futures ETFs (futures-wrapped) may flip skew positive
while keeping the crisis-alpha." T-110 tests that hypothesis on DBMF
+ KMLM — the two main managed-futures ETFs the inbox flagged.

**The hypothesis fails.** Both ETFs have skew MORE negative than the
spot basket, not less:

| Product | Skew (point) | Skew ci_low | Skew ci_high |
|---|---:|---:|---:|
| equity-trend reference (T-007 falsified) | -0.133 | n/a | n/a |
| T-108 spot 8-ETF basket | -0.408 | -0.754 | -0.039 |
| **DBMF (this dispatch)** | **-0.749** | **-1.026** | **-0.425** |
| **KMLM (this dispatch)** | **-0.849** | **-1.302** | **-0.424** |

The "real futures contracts deliver positive skew" claim does not
survive the empirical test. **Wrappers concentrate the negative skew,
they don't dilute it.** Likely mechanism: managed-futures funds use
leverage on futures contracts; leveraged short positions in bear
trends create amplified left-tail losses on short-squeeze days, even
while the strategy is profitable on the trend itself.

**BUT — the crisis-alpha is far more extreme than T-108's spot basket:**

| Crisis window | T-108 spot basket | DBMF | KMLM | SPY |
|---|---:|---:|---:|---:|
| COVID 2020 | -2.65% (+11.0pp vs SPY) | -2.43% (+11.2pp) | n/a (postdates) | -13.63% |
| **2022 bear** | **+11.18% (+35.7pp)** | **+32.73% (+57.2pp)** | **+48.79% (+73.3pp)** | **-24.50%** |
| 2025 vol-shock | +0.72% (+7.7pp) | -4.57% (+2.4pp) | -4.26% (+2.7pp) | -6.95% |

In 2022 — the single most predictive crisis window in our data — KMLM
made **+48.8% while SPY lost 24.5%**. That's a 73-percentage-point
divergence. DBMF was close behind at +57pp. Both materially more
extreme than the spot basket's +36pp.

**And KMLM is NEGATIVELY correlated to SPY**: -0.139 correlation,
beta -0.12. The first product in this Path-B exploration that's
actively anti-correlated, not just low-correlation.

## The verdict — per inbox decision tree

Per inbox:
- **PROCEED-TO-INTEGRATE**: skew positive AND crisis-alpha AND low base-corr → **FAIL** on skew for both
- **MIXED**: crisis-alpha yes, skew still flat/negative → **FITS BOTH**
- **DEAD**: no skew AND no crisis-alpha → **does NOT fit** (crisis-alpha + diversification are clear)

**Combined verdict: MIXED (crisis-alpha diversifier with negative-skew
profile).** The Path-B Layer 2 thesis as originally conceived
("structural skew cure for the strategy's bull-conditional negative
skew") closes out NEGATIVE — managed-futures ETFs do not deliver this
property. The secondary thesis ("Pareto-improvement diversifier") is
REINFORCED by both products.

## Per-product detail

### DBMF (iMGP DBi Managed Futures Strategy)

7.0-year history (2019-05 → 2026-05) — covers COVID, 2022, 2025.

| Metric | Point | ci_low | ci_high | Pass strict CLAUDE.md #6? |
|---|---:|---:|---:|:-:|
| Sharpe | +0.517 | -0.175 | +1.188 | ✗ ci_low < 0 |
| Sortino | +0.458 | -0.149 | +1.069 | ✗ ci_low < 0 |
| **Skewness** | **-0.749** | **-1.026** | -0.425 | ✗ FAIL — make-or-break |
| Max drawdown | -23.7% | n/a | n/a | (n/a; SPY same-window -33.9%) |
| Annualized return | +5.96%/yr | n/a | n/a | (n/a) |
| SPY correlation | +0.183 | n/a | n/a | ✓ below 0.5 threshold |
| SPY beta | +0.118 | n/a | n/a | (n/a) |

Note the Sharpe + Sortino ci_lows go negative — the 7-year history is
too short to firmly conclude positive Sharpe via block-bootstrap.
Point estimates are clearly positive but the CIs are wide. (T-108's
17.4-year spot-basket Sharpe ci_low was +0.085, much tighter.)

Per-crisis returns:
- COVID 2020 (51d): DBMF -2.43% vs SPY -13.63% → **+11.21pp outperformance**
- 2022 bear (196d): DBMF **+32.73%** vs SPY -24.50% → **+57.23pp**
- 2025 vol-shock (61d): DBMF -4.57% vs SPY -6.95% → +2.38pp

### KMLM (KFA Mount Lucas Managed Futures Index)

5.4-year history (2020-12 → 2026-05) — POSTDATES COVID; covers 2022 + 2025 only.

| Metric | Point | ci_low | ci_high | Pass strict CLAUDE.md #6? |
|---|---:|---:|---:|:-:|
| Sharpe | +0.409 | -0.346 | +1.249 | ✗ ci_low < 0 (5.4yr too thin) |
| Sortino | +0.371 | -0.311 | +1.164 | ✗ ci_low < 0 |
| **Skewness** | **-0.849** | **-1.302** | -0.424 | ✗ FAIL — make-or-break (WORST of all 3) |
| Max drawdown | -28.1% | n/a | n/a | (n/a) |
| Annualized return | +5.17%/yr | n/a | n/a | (n/a) |
| **SPY correlation** | **-0.139** | n/a | n/a | ✓ **NEGATIVE — anti-correlated** |
| SPY beta | -0.124 | n/a | n/a | (n/a) |

Per-crisis returns:
- 2022 bear (196d): KMLM **+48.79%** vs SPY -24.50% → **+73.29pp** (largest single-window outperformance in any Path-B test)
- 2025 vol-shock (61d): KMLM -4.26% vs SPY -6.95% → +2.70pp

**KMLM's negative correlation is the most striking single number from
this dispatch.** It is the first product in any Path-B test that's
actively anti-correlated to SPY, not just decorrelated. Beta -0.12
means the product reliably moves OPPOSITE to equities at the margin
— exactly the property a defensive sleeve should have.

## Hypothesis post-mortem

### What T-108 hypothesized
"Self-built spot-ETF trend fails skew because spot ETFs lack the
carry/roll/leverage of futures contracts. Real managed-futures ETFs
(DBMF/KMLM) should flip the skew positive because they hold actual
futures contracts."

### What we found
**Wrappers make skew WORSE, not better.** DBMF -0.749 and KMLM -0.849
are both substantially more negative than the spot basket's -0.408
and the equity-trend reference's -0.133.

### Likely mechanism
Leveraged futures positions (the inbox's expected source of
convexity) appear to produce concentrated left-tail losses when:
- A short bet is forced to cover (short squeeze days = single-day -5%+ losses)
- Multiple long positions correlate-and-crash simultaneously (Sept 2008-style)
- Leverage amplifies BOTH directions; if the strategy is right ~60% of the
  time the losing 40% concentrates leverage losses

The "positive skew" property of trend-following often cited in academic
literature is measured at MONTHLY or longer horizons in IDEAL trend
environments; in DAILY returns over real history, the right-tail
trend continuations are spread over many small days while the
left-tail flash losses concentrate into single large drops.

### What this changes about the Layer 2 plan
- **Stop hunting for positive-skew via this asset class.** Neither
  the spot basket (T-108), the futures wrappers (T-110), nor the
  equity-trend baseline (T-007) deliver it. The "structural skew
  cure" framing of Layer 2 should be retired.
- **The "crisis-alpha diversifier" framing should REPLACE it.** Both
  T-108 and T-110 give us robust evidence that managed-futures-style
  products deliver large positive returns in crisis windows, low (or
  negative) correlation to equities, and meaningful MDD reduction
  vs SPY alone. THAT is the actual lever.
- **The KPI for Phase 1 must shift from "skewness flip" to "MDD
  reduction at non-worse Sharpe at the portfolio level."** A
  capital-partitioned A/B with 10-20% allocation to one of these
  products would test the Pareto improvement claim directly.

## What Phase 1 would look like NOW (revised from T-108 scope §Phase 1)

Per the original T-108 scope, Phase 1 was "capital-partitioned A/B
with skewness-flip as primary KPI." T-110's evidence forces a KPI
revision:

- **Primary KPI:** MDD reduction at non-worse Sharpe (Pareto check)
- **Secondary KPI:** crisis-period combined-portfolio return (2008/COVID/2022)
- **Tertiary KPI:** portfolio-level skewness — the standalone-negative-skew
  product might still flip the combined book positive via decorrelation, but
  this is a secondary check, not the gate
- **Allocation:** sweep {5%, 10%, 15%, 20%} — smaller increments than the
  T-108-scope {10%, 20%, 30%} because the negative skew + leveraged
  drawdowns argue against large allocations
- **Product choice:** DBMF preferred (7yr history vs KMLM's 5.4yr), but
  KMLM is the cleaner anti-correlator (negative beta). Could A/B both as
  separate arms.
- **Substrate:** 5yr 2020-2025 (shared coverage with DBMF) is the realistic
  window; KMLM-arms limited to 4.5yr 2021-2025. Cloud campaign with
  block-bootstrap CI.

NOT initiated this dispatch (Phase 0 only per inbox).

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | DBMF + KMLM returns fetched; data floors + covered-crisis list reported | DONE — DBMF 2019-05-13 covers all 3; KMLM 2020-12-09 covers 2022 + 2025 only |
| 2 | SKEW + ci for each (the make-or-break) | DONE — DBMF -0.749 ci [-1.026, -0.425]; KMLM -0.849 ci [-1.302, -0.424]; BOTH worse than T-108's -0.408 |
| 3 | 2022/2025 (+COVID for DBMF) vs SPY crisis-alpha; Sharpe/Sortino/MDD + CI; base-correlation | DONE — DBMF 2022 +57.2pp; KMLM 2022 +73.3pp; KMLM SPY corr -0.139 |
| 4 | VERDICT: PROCEED-INTEGRATE / MIXED / DEAD with skew + caveats | DONE — **MIXED (crisis-alpha diversifier)** for both; managed-product + short-history caveats below |
| 5 | Audit doc + TASK_LEDGER row | DONE |
| 6 | NO integration, NO engine edits; branch pushed NOT merged | DONE |

## Files

- `scripts/dbmf_kmlm_phase0_t110.py` (NEW; Phase 0 diagnostic)
- `docs/Measurements/2026-06/t110_dbmf_kmlm_phase0.json` (raw output)
- `docs/Audit/dbmf_kmlm_managed_futures_t110_2026_06_05.md` (this audit)
- `docs/State/TASK_LEDGER.md` (T-110 row appended)

## Honest caveats (per inbox)

- **Managed product + fees**: DBMF (~0.85% ER) and KMLM (~0.92% ER) embed a manager's discretionary trend model. A positive crisis return here is "this fund delivers it via futures contract trading," not "any futures-trend strategy would." Returns shown are POST-fee total returns.
- **Short history**: DBMF 7yr, KMLM 5.4yr. Block-bootstrap Sharpe ci_low went negative on both — the point estimates are clearly positive but the bands are wide. We cannot strictly clear CLAUDE.md #6 on Sharpe alone with this much data. The crisis-alpha findings rest on 2-3 specific window observations, not a multi-year baseline.
- **KMLM postdates COVID**: only 2 testable crises (2022, 2025). The 2022 +73pp result is genuinely extreme but rests on a single 196-day window.
- **The negative skew at -0.75/-0.85 IS large.** A standalone allocation would expose the book to chunky single-day losses (a 4-sigma left-tail day on a -0.85-skew distribution is much more likely than on a -0.41 distribution). This is a real risk that the crisis-alpha doesn't offset for a large allocation.
- **DBMF and KMLM are not interchangeable.** DBMF tracks an academic-replication index, KMLM tracks Mount Lucas's proprietary methodology. They have different beta signatures (DBMF +0.12, KMLM -0.12) and the 2022 results differed dramatically (DBMF +32.7% vs KMLM +48.8%). Product selection matters; cherry-picking the winning year is a real overfit risk in a 5-7 year window.

## Memory updates needed (post-merge)

- New entry: "T-110 DBMF + KMLM Phase 0: the futures-wrapper hypothesis from T-108 REFUTED — both ETFs have MORE negative skew than the spot basket (DBMF -0.749, KMLM -0.849 vs T-108 -0.408 vs equity-trend -0.133). Managed-futures wrappers concentrate negative skew via leveraged single-day losses, they don't dilute it. **BUT crisis-alpha is MORE extreme**: DBMF +57.2pp in 2022, KMLM +73.3pp in 2022; KMLM SPY correlation -0.139 (anti-correlated). **Verdict MIXED**: crisis-alpha diversifier, NOT skew cure. **Path-B Layer 2 'structural skew cure' thesis CLOSED-OUT NEGATIVE across 3 distinct product types** (equity-trend T-007, spot 8-ETF T-108, managed-futures ETFs T-110). The crisis-alpha diversifier thesis is REINFORCED and should be the Phase 1 KPI."
- Pattern memory: "The 'positive skew of trend-following' often cited in academic literature is a monthly/longer horizon property in ideal trend environments; daily returns over realistic histories have the right-tail trend continuations spread over many small days while left-tail flash losses concentrate into single large drops. Don't chase positive daily skew in actively-managed trend products."

## Forward dispatches

- **T-110-followup-Phase1-Pareto-A/B** (RECOMMENDED next IF director wants the diversifier): cloud or local A/B of base vs base + {5/10/15/20}% DBMF (or KMLM, or both as separate arms). Primary KPI = MDD reduction at non-worse Sharpe on shared 2020-2025 window with block-bootstrap CI; portfolio-level skewness as secondary. NOT a skew-cure dispatch; a Pareto-frontier dispatch.
- **T-110-product-choice-cell** (small optional): if Phase 1 fires, decide DBMF vs KMLM via a focused A/B on the 2 shared years (2022-2025). KMLM's -0.14 beta is the cleaner diversifier; DBMF's wider history reduces overfit risk; the right pick depends on Phase 1's allocation magnitude.
- **Path-B Layer 2 thesis close-out memo**: the original Layer 2 framing ("structural skew cure for the bull-conditional negative skew") should be formally retired in `docs/State/forward_plan.md`. The replacement framing ("crisis-alpha defensive diversifier sleeve") is well-supported.

## NOT done in T-110

- Phase 1 integration (per inbox: only if Phase 0 clears PROCEED; verdict is MIXED, which routes to director-decision, NOT auto-Phase-1)
- DBMF vs KMLM head-to-head A/B (separate forward dispatch)
- Full equity-book base correlation (used SPY as proxy)
- No engine code changes (per inbox)
- No production-default changes (per inbox)
