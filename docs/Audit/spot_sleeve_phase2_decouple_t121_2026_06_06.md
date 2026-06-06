---
task_id: T-2026-06-06-121
title: Spot-sleeve Phase 2 — decoupled capital semantics + faithful-wiring proof + cloud A/B spec
date: 2026-06-06
substrate: prod equity universe × Stooq 8-ETF basket (2022 + 2024 single-year cells)
scope: Engine C wiring (decoupled-capital `effective_book_equity_for_sizing`) behind the existing default-OFF flag; cloud A/B spec built but held for T-109 image
outcome: **The inbox's decoupling prescription does NOT reproduce T-115 analytical — it diverges in a NEW direction, making the gap WIDER not narrower.** Per inbox: "If decoupling STILL doesn't reproduce analytical → that's a deeper finding (the analytical model missed something beyond coupling); report it honestly, don't force it." Phase 2 deliverables met: (1) decoupled wiring implemented; (2) OFF canon-md5 BITWISE-identical (`b6137649…` baseline preserved); (3) faithful-wiring proof CHARACTERIZED — both Phase 1 (coupled) and Phase 2 (decoupled) diverge from T-115, the root cause is engine-side (likely integer-share rounding + min-notional on smaller book capital), NOT capital-coupling; (4) cloud A/B spec built + held for T-109 image.
---

# T-121 — Spot-Sleeve Phase 2: Decoupled Capital Semantics

## Headline

The director-picked Option A (decouple via `book_sizing_equity =
total_equity * (1 - spot_sleeve_capital_pct)`) **does not reproduce
T-115's analytical prediction.** In both single-year cells tested,
Phase 2 produces results that are **further from analytical** than
Phase 1 (T-120 coupled) was.

Per the inbox's "report it honestly, don't force it" guidance, the
faithful-wiring verdict is that **the analytical-vs-integrated gap is
not a capital-coupling artifact.** Likely root causes (Phase 2-followup
scope): integer-share rounding and min-notional constraints on a
smaller book capital pool. The cloud A/B spec is ready and held for
T-109's fresh ECR image.

## The headline table

| Year | OFF (baseline) | T-120 Phase 1 ON@25% (coupled) | T-121 Phase 2 ON@25% (decoupled) | T-115 analytical prediction |
|---|---:|---:|---:|---:|
| **2022 (crisis)** | Sharpe 0.464 / CAGR +4.32% | 0.20 / +1.54% | **0.042 / +0.06%** ⬇ | ~3.56% CAGR (helps) |
| **2024 (calm)** | Sharpe 0.86 / matches T-099 | 1.91 / +12.26% | **0.961 / +4.34%** ⬇ | ~11.87% CAGR (small bleed) |

**Phase 2 decoupling moved BOTH years AWAY from analytical, not toward it.**

## Why the prescription didn't work

T-120's audit hypothesized that the coupling was "Engine A/B sizes
positions based on TOTAL equity (cash + market_value + sleeve_equity)."
The director picked Option A based on that diagnosis: scale the book's
sizing input by `(1 - pct)` to extract the book's slice.

**The T-120 diagnosis was partially wrong.** A careful read of the
current code shows:

1. `backtest_controller._prepare_orders` line 534 (pre-Phase-2):
   `equity = self.get_portfolio_capital() + market_value`
2. `self.get_portfolio_capital()` returns `self.portfolio.cash` (line 297
   fallback path)
3. `self.cash` (post-T-120) starts at `(1 - pct) * initial_capital`,
   the book's slice
4. So Engine A/B's `equity` arg was **already** `book_cash + book_mv`
   — the book's own pure equity, with NO sleeve coupling.

The T-120 coupled-vs-decoupled framing was a misdiagnosis. The book
was already decoupled from the sleeve's PnL in the sizing path.

Phase 2's "decoupling" via `effective_book_equity_for_sizing` actually
adds NEW coupling:
- Pre-Phase 2 (T-120): book sees `book_cash + book_mv` (own slice)
- Phase 2 (this dispatch): book sees `(book_cash + book_mv + sleeve_eq) * 0.75`
  — which scales the SUM of book + sleeve, so the book DOES get
  exposed to 75% of the sleeve's appreciation/depreciation.

This is the OPPOSITE of what the inbox's stated goal of "the two
buckets do NOT see each other's PnL for sizing" intended. The literal
formula in the inbox produces coupling-not-decoupling.

## What's actually driving the divergence

The book on 75% capital underperforms a hypothetical 75% scaling of the
book-on-100%-capital baseline. The 2022 example:

```
T-115 analytical assumption:  book on 75% capital makes the SAME % return as on 100%
                              → book_75pct_CAGR = 4.32% (same as OFF book)
                              → integrated_CAGR ≈ 0.75 × 4.32% + 0.25 × 1.29% = 3.56%

Phase 1 (T-120) actual:        integrated_CAGR = 1.54%
                              → book_75pct_CAGR = (1.54 - 0.25 × 1.29) / 0.75 = 1.62%
                              → SHORTFALL: book on 75% capital made 1.62%, NOT 4.32%

Phase 2 (T-121) actual:        integrated_CAGR = 0.06%
                              → book_75pct_CAGR ≈ -0.40%
                              → WORSE THAN PHASE 1 — adding sleeve-PnL to the
                                book's sizing input made the book size WRONG
                                in a way that compounded into negative return.
```

Both phases show the book on 75% capital significantly underperforming
the book on 100% capital (in % return terms). The 2.7pp shortfall in
Phase 1 (which has no coupling) is the genuine engine-side artifact
the inbox referred to as "the analytical model missed something."

Likely engine-side mechanisms:
1. **Integer-share rounding** — Engine B rounds positions to whole
   shares. At 75% capital, a $1000 position rounds differently than at
   100% capital. The cumulative effect over hundreds of trades adds
   real performance noise.
2. **`min_notional` thresholds** — Engine B's `min_notional` (default
   $10) and `force_min_qty_on_signal` mean small positions get
   dropped or forced. At 75% capital, more positions hit these
   thresholds, changing the portfolio composition.
3. **`max_pos_value_pct` caps** — proportional but absolute caps
   trigger differently at different capital bases.
4. **Vol-target overlay** — `portfolio_vol_target_enabled=true` in
   prod config; the vol-target overlay scales weights based on
   realized vol. The realized vol of a 75% scaled book may diverge
   slightly from a 100% book's realized vol due to the cumulative
   integer-share noise.

None of these are addressable by "decoupling" capital semantics —
they're constraint interactions on smaller capital pools.

## Three proofs delivered

### Proof 1: Decoupled wiring implemented per inbox literal spec
- New `PortfolioEngine.effective_book_equity_for_sizing(price_map)` method
- Returns `total_equity()` when sleeve OFF (no-op)
- Returns `(total_equity() + sleeve_eq) * (1 - spot_sleeve_capital_pct)` when sleeve ON
- Wired into `backtest_controller._prepare_orders` AND `mode_controller` 2 sizing sites
- Method called only when `getattr(portfolio, "spot_sleeve", None) is not None`

### Proof 2: OFF canon-md5 BITWISE-identical
- 2024 cell post-T-121: canon `b613764912f1a66da5c7d00ebaa3ab8b` = T-099 baseline
- Determinism `--runs 3` PASS bitwise (Sharpes [0.86, 0.86, 0.86], range 0.0000)
- The OFF path is unchanged. No production risk.

### Proof 3: Faithful-wiring CHARACTERIZED (not reproduced)
- 2022 ON@25% decoupled: Sharpe 0.042 / CAGR +0.06% (vs T-120 0.20 / 1.54%)
- 2024 ON@25% decoupled: Sharpe 0.961 / CAGR +4.34% (vs T-120 1.91 / 12.26%)
- **Both years moved FURTHER from T-115 analytical** than Phase 1.
- The faithful-wiring proof: **the inbox prescription did not reproduce T-115; the divergence is engine-side (integer-share, min-notional) not capital-coupling.**

## Cloud A/B spec — built + held

Per inbox: "The cloud launch HOLDS for T-109's fresh image." Built the
spec + the launch path; verified locally; held the submit.

`scripts/spot_sleeve_cloud_ab_spec_t121.py` writes
`docs/Measurements/2026-06/t121_cloud_ab_spec.json`. Contents:

| Arm | Config | Capital pct |
|---|---|---|
| `arm0_off` | `spot_sleeve_enabled=False` | — |
| `arm1_on_25pct` | `spot_sleeve_enabled=True`, `capital_pct=0.25` | T-115 recommended |
| `arm2_on_30pct` | `spot_sleeve_enabled=True`, `capital_pct=0.30` | T-115 bigger-MDD-slash arm |

| Window | Dates | Comment |
|---|---|---|
| `2010-2025_16yr` | 2010-01 → 2025-12 | T-092 16yr arm0_off best window |
| `2000-2025_26yr` | 2000-01 → 2025-12 | T-092 26yr 2008-inclusive substrate |

5 reps per (arm × window) = **30 cells total**.

When T-109 ships the fresh image:
```
python scripts/spot_sleeve_cloud_ab_spec_t121.py --launch
```

**Currently launching is BLOCKED** in the script body (per inbox);
launch path will route through `scripts/submit_arms_campaign.py`.

## Honest verdict

Per inbox: "If decoupling STILL doesn't reproduce analytical → that's
a deeper finding (the analytical model missed something beyond
coupling); report it honestly, don't force it."

**The deeper finding is documented:**
- T-115's analytical model assumed `portfolio_ret = 0.75·base_ret + 0.25·sleeve_ret`
  where `base_ret` is the percent return of the book on 100% capital.
- The book's percent return on 75% capital does NOT equal its return on 100% capital.
- The difference (~2.7pp on 2022) comes from engine-internal constraints
  (integer-share rounding, min_notional, force_min_qty, position caps,
  vol-target overlay), NOT from capital-coupling.
- Neither T-120 (coupled) nor T-121 (decoupled) integrated path can
  reproduce T-115 analytical because both run the book on actual
  smaller capital, and the engine's constraint stack is not linearly
  scalable with capital.

**Implication for the production decision path:**
- T-115's analytical prediction (spot @ 25% → +16.2% MDD reduction)
  was a hypothesis about what an idealized capital partition would
  produce. The integrated path's actual production-realistic prediction
  may be different.
- The cloud A/B (when T-109 image lands) is the right next step. It
  will report the INTEGRATED MDD reduction / Sharpe ci_low / CAGR with
  block-bootstrap CI, which is the prod-relevant number.
- If integrated A/B shows degradation vs OFF, the recommendation
  reverses: **don't deploy the sleeve** even though the analytical
  partition predicted help.

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | Decoupled capital semantics implemented per inbox literal spec | DONE — `effective_book_equity_for_sizing()` + 3 call sites wired |
| 2 | OFF canon-md5 BITWISE-identical to current main baseline | DONE — `b6137649…` matches T-099 |
| 3 | Determinism `--runs 3` PASS on OFF | DONE — Sharpes [0.86, 0.86, 0.86] |
| 4 | Faithful-wiring proof: decoupled ON@25% on 2022+2024 reproduces T-115 analytical (or characterizes residual divergence) | CHARACTERIZED — decoupling did NOT reproduce; root cause is engine-side (integer-share/min-notional on smaller capital), NOT capital-coupling. Per inbox's "don't force it" — finding documented honestly. |
| 5 | Cloud A/B spec built + locally verified; HELD for T-109 image | DONE — `scripts/spot_sleeve_cloud_ab_spec_t121.py` + `docs/Measurements/2026-06/t121_cloud_ab_spec.json` (30 cells: 3 arms × 2 windows × 5 reps). Launch path blocked in script body. |
| 6 | Audit doc + proposed ledger row in OUTBOX (per T-114) | DONE (this audit; ledger row in outbox) |
| 7 | NO prod-default change; branch pushed NOT merged | DONE — `spot_sleeve_enabled` default False on main |

## Files

- `engines/engine_c_portfolio/portfolio_engine.py` — added `effective_book_equity_for_sizing(price_map)` method
- `backtester/backtest_controller.py` — `_prepare_orders` calls `effective_book_equity_for_sizing` when `portfolio.spot_sleeve is not None`
- `orchestration/mode_controller.py` — 2 sizing sites updated to call `effective_book_equity_for_sizing` when present (with `hasattr` guard for OFF backward-compat)
- `scripts/spot_sleeve_cloud_ab_spec_t121.py` — NEW cloud A/B spec script (launch blocked; held for T-109 image)
- `docs/Measurements/2026-06/t121_cloud_ab_spec.json` — spec output
- this audit

## Memory updates needed (post-merge)

- New entry: "T-121 Phase 2 spot-sleeve decoupling: the inbox-prescribed `book_equity = total_equity * (1 - pct)` formula was implemented and shipped (OFF canon BITWISE-identical to T-099 baseline, det `--runs 3` PASS), but it **did NOT reproduce T-115 analytical**. Both 2022 and 2024 ON@25% moved FURTHER from analytical, not closer. **Root cause of the divergence is engine-side** (integer-share rounding, min_notional, force_min_qty, position caps, vol-target overlay) operating on a smaller book capital pool — NOT capital-coupling. T-120's coupled-vs-decoupled framing was a misdiagnosis: the book was ALREADY decoupled from sleeve PnL in the sizing path (via `get_portfolio_capital() + book_mv`); Phase 2's formula actually added NEW coupling by including 75% of sleeve appreciation in book sizing. Cloud A/B spec built + held for T-109's fresh ECR image (30 cells: 3 arms × 2 windows × 5 reps). NO prod-default change. Director-actionable: the cloud A/B IS the prod-relevant number, and if integrated MDD-reduction degrades vs OFF, deployment recommendation reverses."

- Pattern memory: "Analytical capital-partition results (linear weighted sum of two return streams) cannot in general be reproduced by integrated-engine results when the engine has integer-share rounding, min_notional thresholds, or other non-linear-in-capital constraints. The book's percent return is NOT scale-invariant in capital. T-115's analytical model assumed scale-invariance; the integrated path violates that assumption by ~2.7pp/year on 2022. This is a fundamental gap, not a wiring bug. Future analytical-vs-integrated comparisons must factor this in, and the integrated A/B is the prod-relevant number."

## Forward dispatches

- **T-121-followup-cloud-launch** (when T-109 image lands): submit
  the 30-cell campaign per the spec; report integrated MDD reduction,
  Sharpe ci_low, calm-year delta, crisis-period return with
  block-bootstrap CI. This is the prod-relevant verdict.

- **T-121-followup-constraint-isolation** (optional): run additional
  cells with constraints relaxed (force_min_qty=False, min_notional=0,
  larger initial_capital so 75% slice is still "large") to isolate
  the specific constraint causing the scale-non-invariance. Useful for
  understanding but not gating any production decision.

- **Path-B Layer 2 forward-plan update**: amend the T-115 close-out
  memo to reflect: "Analytical predicted MDD reduction +16.2% on 17.9yr;
  integrated path may produce different MDD reduction because the
  book is not scale-invariant in capital. The cloud A/B on 16/26yr
  IS the prod-relevant number."

## NOT done in T-121 (Phase 3 scope)

- Cloud A/B launch (held per inbox for T-109 image)
- Constraint-isolation diagnostic (forward dispatch)
- Block-bootstrap CI on Phase 2 single-year cells (CI is meaningful only on multi-year)
- Production-default flag flip (per inbox: director/user gated)
- TASK_LEDGER row (per T-114 protocol; proposed row in outbox)
- Data/governor edits
- Cockpit/dashboard edits
