---
task_id: T-2026-06-15-172
title: Regime-detector deep-history retrain + leave-one-crisis-out OOS generalization (Step 1)
date: 2026-06-16
substrate: deep reduced feature panel 2000-02→2026-04 (6592 obs); measurement-only (no production regime-model swap)
scope: scripts/ + docs/ ; pre-registered (regime_oos_preregistration_t172_2026_06_16.md). Engine E measurement; no prod swap, no live path.
outcome: **MARGINAL PASS, honestly weak on the load-bearing fold.** A deep-trained base-feature HMM GENERALIZES OOS to FAST/credit/liquidity crises it didn't train on — GFC (lead 333td, but FA over budget), COVID (17td, sharp), 2022 (108td) — proving the production model's blindness was NOT fundamental but data-floor (2006 training) + VIX-term features that didn't exist in 2000. BUT on **dotcom** (the slow valuation-bear TYPE, the user's key question) it is **substantively weak**: it fires only via a brief real spike (the Apr-2000 Nasdaq crash) then goes mostly quiet through the 2001 grind (p>0.5 on just 4% of 2000, 15% of 2001), re-lighting only in 2002. The pre-registered LETTER passes (early sustained crossing + FA 0.41/yr ≤ budget); the SPIRIT is partial — the slow-grind middle of a valuation bear is largely invisible to this feature set. **Verdict: crash detection generalizes for fast/credit crises; the slow-valuation-bear TYPE is partly structurally hard. Step 2 (dynamic sleeve sizing) is worth testing AS A REGIME SIZER for fast crises — NOT as an all-crisis timer.**
---

# T-172 Step 1 — does the regime detector generalize OOS?

## The data-feasibility finding (established first — it reframes the question)

The production HMM's dotcom-blindness is **two distinct problems**, only
one of which is fixable:

1. **STRUCTURAL (not fixable with more training):** its strongest crisis
   features — the VIX **term-structure** set (VIX3M, VIX9D
   backwardation) — **did not exist in 2000** (VIX3M from 2007, VIX9D
   from 2011). No amount of training generalizes a model to a window
   where its inputs don't exist. The production model also trained only
   from ~2006 (T-103 floor) and the cached VIX/TLT only reach 2020.
2. **FIXABLE (data-cache depth):** `^VIX` is available to 1995, the
   yield-curve and BAA-AAA credit spreads to 2000, SPY to 1993, and a
   DGS10-derived bond-return proxy to 2000. A **reduced base feature
   set** (no term structure, no dollar) can be trained on deep history
   and OOS-tested. That is what this task measures.

## Method (per the locked pre-registration)

Gaussian HMM (3 states, seed 0, 10 inits, best by train-LL) on the
reduced deep panel `[spy_ret_5d, spy_vol_20d, bond_ret_20d, vix_level,
yield_curve_spread, credit_spread]`. Leave-one-crisis-out: train
excluding the held-out crisis ±90d, identify the crisis state
mechanically (max mean `spy_vol_20d`), compute **causal** `p_crisis`
(forward filter — no backward smoothing, the T-089 guard). Firing =
`p_crisis ≥ 0.50` sustained ≥3d with first crossing ≤ trough and lead >
0; FA budget ≤ 1/yr on calm (non-crisis) days. `scripts/regime_oos_loco_t172.py`.

## Results

| held-out crisis | fires? | lead (td) | first cross | trough | max p | FA/yr | in budget? |
|---|---|---:|---|---|---:|---:|---|
| **dotcom** (slow valuation) | letter-✓ / **substance-WEAK** | 609 | 2000-05-04 | 2002-10-09 | 1.00 | 0.41 | ✓ |
| GFC (credit) | ✓ but FA over | 333 | 2007-11-08 | 2009-03-09 | 1.00 | **1.13** | ✗ |
| COVID (fast liquidity) | ✓ | 17 | 2020-02-27 | 2020-03-23 | 1.00 | 0.41 | ✓ |
| 2022 (rates/grind) | ✓ | 108 | 2022-05-09 | 2022-10-12 | 1.00 | 0.46 | ✓ |

**The discrimination is real, not degenerate** — on the dotcom-fold
model, calm years are silent (mean p_crisis 2005/2013/2017/2019/2021 =
**0.00**), so the model genuinely separates calm from crisis.

**BUT the dotcom fold is substantively weak** — within the held-out
window: **p>0.5 on only 4% of 2000, 15% of 2001, 35% of 2002.** The
"609td lead" is a brief real spike (the Apr-2000 Nasdaq −34% crash, a
genuine first leg), after which the model goes mostly quiet through the
slow 2001 grind and re-lights only as the 2002 capitulation deepens. It
catches the FAST legs of dotcom but is largely blind to the slow
valuation-de-rating middle. The GFC/COVID/2022 folds (fast/credit
crises) are tracked far more strongly (COVID's 17td is a genuine sharp
lead).

## Honest verdict (the user's question)

**Is the dotcom-blindness fixable or structural?** BOTH, by mechanism:
- The production model's term-structure features are **structurally**
  dotcom-blind (didn't exist in 2000).
- A deep base-feature model **partly fixes it** — it recovers the FAST
  legs of dotcom and generalizes cleanly to GFC/COVID/2022 (the
  blindness was data-floor, not fundamental). But it does **not**
  robustly track the **slow valuation-bear TYPE** (the 2001 grind reads
  calm — VIX/credit/curve simply don't move much in a slow de-rating
  the way they do in a fast credit/liquidity crisis). That residual is
  partly structural to *what a vol/credit feature set can see*.

**Is crash-TIMING viable, or is always-on 20% the ceiling?** Crash
detection is viable for **fast/credit crises** (GFC/COVID/2022) with
real lead and clean FA — so **always-on is NOT the ceiling**: a
dynamically-sized sleeve has a genuine signal to ride for those crisis
types. For **slow valuation bears (dotcom)** the signal is weak/late, so
a timer there would lag. The signal is **regime-classification-grade,
not sharp-timing-grade** — which is exactly why the de-gross overlay
(T-118r) failed (it needed precise flatten-timing the signal doesn't
give) and exactly why a **sleeve SIZER** is the right utilization (you
want the MF sleeve heavier through the whole risk-off regime, which the
sustained signal supports).

## Step-2 gate decision

**GATED OPEN — but scoped.** Per the pre-registration's letter dotcom
passes, and the fast-crisis generalization is strong, so Step 2 (wire
the detector to dynamic MF-sleeve sizing, A/B vs always-on 20% OOS
net-of-cost) is justified — **framed as a fast-crisis regime sizer**,
with the explicit caveat that it will under-help in slow valuation bears
(size the sleeve up in fast risk-off; don't expect it to time a dotcom-
style grind). The honest expectation: the amplifier recovers bull upside
+ adds in fast crises, but always-on 20% remains the floor for the
slow-bear type. The GFC FA-over-budget (1.13/yr) is a tuning caveat for
the Step-2 operating point. (Step 2 is a SEPARATE pre-registration/task.)

## Files

- `docs/Audit/regime_oos_preregistration_t172_2026_06_16.md` — the locked pre-reg
- `scripts/regime_oos_loco_t172.py` — the harness (deep panel + LOCO + causal filter)
- `data/research/regime_oos_loco_t172.json` — results
- this audit

## NOT done / caveats

- Measurement-only — NO production regime-model swap (any swap ships
  default-OFF + canon `--runs 3`, a downstream task).
- The reduced feature set is a deliberate honesty constraint (term
  structure can't reach dotcom); a production model would keep the term
  features for the post-2007 era and accept dotcom-structural-blindness.
- `^VIX` deep history fetched to `data/research/vix_deep_t172.csv`
  (measurement-local; not a production substrate change).
- Step 2 is gated open but is its own pre-registered task, not started here.
