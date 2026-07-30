# T-337 — the dividend-strip audit: PRE-REGISTRATION (DRAFT for director freeze)

**Date:** 2026-07-30 · **Agent:** C · Branch `feature/dividend-strip-audit-t337` · **0 N_trials until frozen** (N+=1 at run)
**NOTHING RUN ON REAL DATA.** Per the freeze protocol (and the T-333 lesson): premise verification + synthetic pipeline validation only; the closures' measurements are untouched until this doc is frozen.

---

## ⚠ PREMISE CORRECTION — BOTH stated premises are imprecise (measured before drafting)
This is the part the director must see before freezing, because it changes the effect size and therefore the gate.

**The dispatch states:** *"the T-082 deep-panel splice deliberately strips dividends (price-return)"* and *"data/raw/stooq daily bundles are split+dividend."*
**My own T-256 memory line states:** *"Stooq is split-ONLY."*
**Measured today, neither is right — the truth is in between:**

| name | canonical panel | split-adj PRICE | true TR (Adj Close) | verdict |
|---|--:|--:|--:|---|
| T | +5.71%/yr | +0.96% | +8.47% | panel is **partially** div-adjusted |
| VZ | +5.75%/yr | +2.71% | +8.19% | same |

Stooq (and hence the panel) **captures part of the dividend and misses the rest.** It is neither a clean price series nor a clean TR series. My T-256 *tooling* already measured this three-way split correctly (`stooq_div_capture_pct_yr` / `tr_gap_pct_yr` / `full_div_yield_pct_yr`); the lossy part was the one-line memory summary, which I will correct.

**The residual gap on the CANONICAL panel the closures actually consumed** (2010+, `data/processed/<T>_1d.csv`, 730 equities available):

| cohort | panel-vs-TR gap | range |
|---|--:|---|
| **high-yield / value-income** (T, VZ, MO, XOM, KO, PFE, IBM) | **−1.61%/yr** | [−2.88, −0.74] |
| **low/no-yield growth** (NVDA, AMZN, GOOGL, ADBE) | **−0.02%/yr** | [−0.07, +0.00] |
| **DIFFERENTIAL** | **−1.59%/yr** | — |

**So the claim's MECHANISM is CONFIRMED and is genuinely differential** — the understatement lands almost entirely on the high-yield/value-income cohort, exactly the class the challenge names. **But the claim's MAGNITUDE is ~1.6%/yr on high-yield names, not a full dividend strip (~7%).** The audit remains worth running; its expected effect is ~4× smaller than the claim implies.

---

## Pre-registered hypothesis (as dispatched, with the corrected effect size)
**H:** restoring TR does **NOT** flip the value/accruals sub-verdict (T-180-v2 "neutral-to-negative") **AND** moves the T-215 honest base by **< +0.15 Sharpe**.

**Why H is likely on the measured numbers (stated in advance, so a pass isn't post-hoc rationalized):** a diversified long-only book holding ~25% in high-yield names picks up ≈ 0.25 × 1.61% ≈ **+0.40%/yr**, which at ~16% annual vol is ≈ **+0.025 Sharpe**. A *value-tilted sub-book* at ~60-80% high-yield weight picks up ≈ **+1.0-1.3%/yr ≈ +0.06-0.08 Sharpe**. Both sit inside the gate — **but the value sub-verdict is where the risk concentrates, and it is the one that could plausibly move from "negative" toward "neutral."** That is the honest exposure of this audit and I flag it now rather than after.

## Method (frozen; unchanged otherwise)
1. Select the **~150 highest-yield PIT names** on the deep panel (yield measured PIT, never with hindsight — selection uses only data available as of each formation date).
2. TR-reconcile each with the **proven T-256 machinery** (`reconcile_stooq_tr_t256.py`), which already reports the three-way split per ticker. **Correction to the dispatched method:** because the Stooq bundle is only *partially* dividend-adjusted, the TR source is **yfinance `Adj Close`** (as T-256 used), **not** the raw Stooq bundle. Using the bundle as if it were TR would leave the ~1.6%/yr residual in place and produce a null by construction.
3. Re-run **T-180-v2** (value/accruals contribution) and the **T-215 honest-base** measurement with *everything else unchanged* — same windows, same costs, same PIT membership, same N-accounting.
4. Report per-cohort so the differential is visible, not just the pooled number.

## Pre-stated gate
- **PASS (both closures stamped TR-VERIFIED):** `Δci_low < +0.10` **AND** value/accruals contribution stays **≤ 0**.
- **FAIL (either condition breaks):** `[NN-SUBSTRATE-REVERIFY]` cascade on the affected verdicts, with the scope enumerated in the report (which downstream conclusions inherit the substrate and must be re-checked).
- **Fail-closed on measurement:** any ticker whose TR cannot be validated is **excluded and named**, never silently left price-basis — a partial reconciliation reported as complete is the exact failure this audit exists to catch.

## What this audit can and cannot settle
- **CAN:** give the program's central negative result its receipt — quantify how much of the "equity book is H0" conclusion was substrate artifact vs signal.
- **CANNOT:** revive the equity book on its own. Even the upper end (+0.08 Sharpe on a value sub-book) leaves the honest base far below the deployable bar; a pass means "the closure was not a dividend artifact," not "the book works."
- **N_trials += 1** at run. A null teaches: the largest unexamined assumption under the central negative result gets checked.

**Awaiting director freeze. No real-data closure re-run has occurred.**
