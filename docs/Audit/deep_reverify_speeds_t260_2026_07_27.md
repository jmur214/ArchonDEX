---
task_id: T-2026-07-27-260-deep
title: T-260-deep DONE — the ensemble-speed selection re-verified on 58-64yr
date: 2026-07-27
worker: Agent B
branch: feature/deep-reverify-speeds-t260
status: DONE. N_trials += 1. Ran the frozen spec, no deviation, NO re-selection performed. SUPERSEDES the 2000-2026 T-260.
---

> ⚠️ **CORRECTION (2026-07-28):** the **MBL/DSR "CLEARS" sentence in this doc is RETRACTED.**
> It fed `[NN-MBL]` the sleeve's ABSOLUTE Sharpe (~1.5, overwhelmingly market beta) instead of the
> Sharpe of the CLAIMED EDGE. The active (difference) Sharpe vs buy-hold is **−0.210** — there is no
> positive edge to clear. **All substantive verdicts in this doc STAND** (they rest on paired
> block-bootstrap CIs on differences, the correct test). Canonical:
> `docs/Audit/mbl_framing_correction_t306_arc_2026_07_28.md`.

# T-260-deep — the ensemble lift UPGRADES to significant; spec-dispersion SHRANK (my prior was wrong)

Pre-reg: `docs/Sources/prereg_deep_reverify_speeds_t260.md` (frozen, no amendment).
Script: `scripts/deep_reverify_speeds_t260.py` (reuses the T-311 code path verbatim).
Data: `data/research/t260_deep_reverify.json`.

## PRIMARY — D-A 2-asset, 1962-01-04 → 2026-04-17 (64.3 yr)
| spec | Sortino | ci_low | CAGR | MaxDD | $10k → |
|---|---|---|---|---|---|
| **ENSEMBLE {2,5,10}** ★ | **1.996** | **1.605** | 8.6% | −11.6% | $1,957,667 |
| single 21d | 1.899 | 1.554 | 9.1% | −19.0% | $2,657,769 |
| single 42d | 1.848 | 1.495 | 8.7% | −17.9% | $2,127,275 |
| single 105d | 1.747 | 1.381 | 8.3% | −17.7% | $1,665,269 |
| single 210d | 1.773 | 1.404 | 8.6% | −9.7% | $2,021,510 |
*(full 11-point grid in the JSON)*

## CLAIM 2 — **UPGRADE. The lift is now CI-SIGNIFICANT.**
| window | ΔSortino (ensemble − single 5mo) | verdict |
|---|---|---|
| shallow 2000-2026 | [−0.023, +0.207] | directional, NOT significant |
| **deep 2-asset 64yr** | **[+0.100, +0.252]** | **SIGNIFICANT** |
| **deep 3-asset 58yr** | **[+0.102, +0.274]** | **SIGNIFICANT** |

The shallow window's near-miss **resolved in the ensemble's favour** on both deep
windows — exactly what more independent data is supposed to settle. Against the
individual constituents (2-asset): vs 105d **[+0.100,+0.252]** ✓, vs 210d
**[+0.063,+0.269]** ✓, vs 42d [−0.019,+0.205] (not significant — the fast leg is the
closest competitor). **The T-260 caveat "adopt as a robustness choice, NOT on a claim
of significant lift" is now RETIRED: the lift is real at MBL-cleared N.**
MBL: N=77, 64yr → required Sharpe 0.368 vs ensemble 1.516 → **CLEARS**.

## CLAIM 1 — dispersion **SHRANK**. **My pre-registered prior was WRONG.**
I predicted dispersion would "persist or widen" (the deep window adds the 1970s-80s,
trend-following's most speed-sensitive era). It did the opposite in the core band:

| measure | shallow 2000-2026 | deep 2-asset | deep 3-asset |
|---|---|---|---|
| Sortino range, 4-10mo band | **0.401** | **0.121** | **0.111** |
| Sortino range, full 1-12mo grid | — | 0.197 | 0.332 |
| CAGR spread across grid | "100-350 bps/yr" | **92 bps/yr** | **119 bps/yr** |

**Reading:** across 64 years the *choice among reasonable trend speeds* matters
roughly **3× less** than the shallow window implied. The shallow 0.401 was itself
substantially small-sample noise — a 26-year window over-stated spec-selection risk.
The honest correction: **the shallow "100-350 bps/yr is spec-selection" claim is
revised down to ~90-120 bps/yr at the low end of its range.** Still material, but
not the dominant term it appeared to be. (Dispersion is larger on the *full* grid
than the 4-10mo band — the very fast 21d and very slow 252d ends are where the real
spread lives, which is an argument for the mid-band the deployed spec occupies.)

## Where the deployed spec sits (characterization — NO re-selection)
- **2-asset primary: 100th percentile.** The ensemble beats **every one** of the 11
  single specs on Sortino. Not mid-pack — top.
- **3-asset secondary: 91st percentile.** **One single beats it: 21d (1mo)**, Sortino
  1.973 vs 1.931.

**The pre-commitment held: the spec stays `{42,105,210}`.** And the 21d case is the
best possible demonstration of *why* that pre-commitment exists — **the "best single"
FLIPS between the two windows**: 21d loses to the ensemble on the 2-asset window
(1.899 vs 1.996) and beats it on the 3-asset (1.973 vs 1.931). A spec that wins on
one honest window and loses on another is **spec-luck, not edge** — which is
precisely the failure mode the ensemble exists to average away. Adopting 21d because
it topped one of two windows would have been the free-parameter fit the pre-reg
forbade. `reselection_performed: false` is asserted in the output JSON.

## Verdict
1. **Claim 2 UPGRADED** — ensemble lift significant on both deep windows; the
   "robustness-only" caveat is retired. The deployed spec's status moves from
   *pending* to **settled**, which is what T-314's baseline needed.
2. **Claim 1 REVISED DOWN** — spec-selection risk is real but ~3× smaller in the
   4-10mo band than the shallow window claimed (92-119 bps/yr, not 100-350). My own
   prior was wrong in direction; recorded as such.
3. **Claim 3 SUPERSEDED** — it is no longer merely a robustness choice; it is a
   robustness choice *that also earns a significant lift*.
4. **No change to the deployed configuration.** `{42,105,210}` stands, now on
   stronger evidence than when it was chosen.

## Honest caveats
- Same disclosed substrate caveats as T-311 (anachronistic-but-symmetric ETF ERs on
  the pre-ETF segment; pre-1993 equity is broad-market TR, not S&P-500).
- **No rate-regime slicing** was performed (T-311's cash-rate split is post-hoc;
  conditioning on it here would import that contamination — it belongs to family
  experiment #2, forward/out-of-time).
- The grid is single-speed only; alternative *ensemble shapes* (weightings, >3 legs)
  were excluded by the pre-reg as a search, and remain untested by design.

**N_trials += 1** (arms jointly reported, no selection). **Next: T-314 (#1)** against
this now-settled frozen baseline.
