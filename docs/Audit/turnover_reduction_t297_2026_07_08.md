---
task_id: T-2026-07-08-297
title: Turnover reduction on the offense config — the execution-bound lever
date: 2026-07-08
author: Agent D (fair-harness lane)
type: PRE-REGISTERED comparison (1 family, jointly reported; N_trials += 1)
status: DONE — both arms CUT turnover ~4x and beat SPY at 5bps on points, but BOTH FAIL the frozen crash-exit gate. Neither earns the offense row. + a correction to T-294's magnitudes. Branch feature/turnover-reduction-t297
---

# T-297 — turnover reduction on the offense config

T-294 established the offense config is **execution-bound, not vehicle-bound**: it turns **23.93
exposure-units/yr** (SSO leg 14.62), its edge over buy-hold SPY is **+0.45%/yr**, and at E's measured **≥5 bps**
SSO slippage it **loses to buy-hold SPY** ($58,709 vs $64,421). Turnover reduction is therefore the highest-value
lever. It is **mechanical, not alpha** — the only question is how much signal it costs.

## Substrate + signal (unchanged, not re-litigated)
Fair harness, full-cycle 2000-08→2026-04. Signal = the T-284 PRIMARY gate: `e_target = min(2·ensemble_frac(SPY), 2)`
from the causal `.shift(1)` {2,5,10}mo ensemble. Vehicle = the basis-checked SSO synthetic (T-282/T-294). The
SPY(1×)+SSO(2×) blend structure of T-284 PRIMARY is retained exactly; **only the exposure path is damped.**

## A measured fact that determines the band (established before choosing it)
`e_target` is **quantized**: it takes values **{0, ⅔, 1, 4/3, 2}** and its nonzero moves are **{⅔, 1, 4/3, 2}**.
The minimum possible move is **⅔ of an exposure unit** (one speed flipping among the three). Therefore **any
deadband < ⅔ suppresses nothing** — the band must be ≥ ⅔ to bind at all. This is a property of the signal, not
a tuning choice, and it fixes the only defensible band without a sweep.

## Arm 1 — Carver deadband, band **B = ⅔** (FROZEN; the "≥2-of-3 speed confirmation" band)
Reuses the T-148 buffering logic (built as a tax lever; this is its execution-cost encore):
```
e_held[t] = e_held[t-1]           if |e_target[t] − e_held[t-1]| ≤ B      (hold, do not trade)
          = e_target[t]           otherwise                                (re-trade to target)
B = 2/3  (compared with a 1e-9 tolerance — the values are floats)
```
**Rationale (priced, not tuned):** one speed flipping moves exposure ⅔ of a unit. A flip-and-revert round trip
therefore costs ≈ `2 × ⅔ × 5 bps ≈ 6.7 bps` of NAV at E's measured SSO slippage floor, while a lone fast-speed
(2mo) flip that whipsaws contributes ≈ 0 expected return. `B = ⅔` prices exactly that trade away: **re-trade only
when at least two of the three speeds agree the exposure should change.** Anything smaller cannot bind (see
above); anything larger (≥ 4/3) would suppress the full de-gross and is a different, riskier animal.
_If a second width is ever needed it is a NAMED SECONDARY and family-N increments._

## Arm 2 — monthly-held `e2` (the classic turnover floor)
Decisions monthly: sample `e_target` on the first trading day of each month and **hold that exposure for the
month**. No intra-month trading. This is the lower bound on gate turnover for a monthly-speed signal.

## Baselines
- **V1 (undamped)** — the T-284 PRIMARY / T-294 incumbent, at 23.93 exposure-units/yr.
- **Buy-and-hold SPY TR** — the north-star bar ($64,421 / 7.54% on this window).

## Reported per arm (all three, jointly)
1. **Exposure-units/yr turned** (total and SSO-leg) vs the 23.93 / 14.62 baseline.
2. **Terminal wealth on the SAME slippage grid as T-294 — 0 / 5 / 10 bps** — charged the same *fair* way
   (extra bps on the **SSO leg only**; the SPY leg keeps its measured **0.51 bps**), so the verdict reads
   directly against the T-294 table.
3. **Signal-fidelity cost = crash-window exit-lag**, in trading days, vs the undamped gate, for **2008, 2020,
   2022**. Measured at two thresholds: first day exposure falls to **≤ 1.0** (de-levered) and to **0.0** (fully
   out). A damper that delays the crash exit is buying execution savings with tail risk — that must be visible.

## Gate (FROZEN)
An arm earns the offense row **iff**:
- **(a)** it **beats buy-hold SPY at the 5 bps grid point** (E's measured floor), **and**
- **(b)** its **crash-window exit-lag ≤ 5 trading days** vs the undamped gate (at both thresholds, all three crises).

Failing (b) disqualifies regardless of wealth: the offense config's survivability rests on the gate exiting
crashes before leverage compounds them (T-284's whole mechanism).

## Honest prior — MEDIUM-HIGH (~50-60%)
Turnover reduction is mechanical; the ⅔ band suppresses only single-speed flips, which are precisely the
whipsaw trades. I expect Arm 1 to cut turnover substantially at small signal cost and to clear (a). The risk is
(b): a band that holds exposure through the first leg of a crash. Arm 2 (monthly hold) should cut turnover
hardest but has a structural exit-lag of up to ~21 trading days — **I expect Arm 2 to FAIL gate (b)**, and that
failure is the point of running it. N_trials += 1 (one family, jointly reported).

**Note:** when E's measured SSO slippage lands it becomes the harness's central estimate; **the 0/5/10 grid
stays** — the grid is what makes the verdict robust to the estimate.

---
## RESULTS (fair harness, 2000-08-30 → 2026-04-17, full SPY trading calendar; buy-hold SPY TR = **$74,104 / 8.13% / −55.2%**)

### ⚠️ FIRST — a correction to T-294 (already merged). Its verdict stands; its magnitudes were understated.
T-294's `common` index was the **intersection with the bond synth** (required by its NTSX/RSSB arms), which is
missing **48 SPY trading days**. Every T-294 series — arms *and* the buy-hold-SPY bar — was silently reindexed
onto that holey calendar. Restricting SPY TR to bond-synth days reproduces T-294's `$64,421` **exactly**; the
true full-calendar bar is **$74,104**. Because a 2×-levered arm loses ~2× the return on each dropped up-day, the
*relative* comparison was distorted too:

| quantity | T-294 (holey index) | corrected (full calendar) |
|---|---|---|
| buy-hold SPY TR | $64,421 | **$74,104** |
| V1 @ 0 bps | $71,658 | **$78,534** |
| V1 @ 5 bps | $58,709 | **$65,088** |
| **V1's zero-slippage edge over SPY** | +0.45%/yr | **+0.25%/yr** |
| V1 @ 5 bps vs SPY | loses by 9% | **loses by 12%** |

**T-294's verdict is unchanged and in fact STRENGTHENED:** the offense config's edge over buy-and-hold is even
thinner (+0.25%/yr, not +0.45%), so it is *more* execution-bound, and at E's 5 bps floor it loses to SPY by more.
**Recommended fix (not run here):** reindex the bond synth onto the SPY trading calendar (ffill) so bond-dependent
arms cannot shrink the calendar for SPY-only arms. T-294's V4−V1 vehicle gap (+0.86%/yr) should be re-run on the
full calendar for magnitude; its direction is not in question (V1 and V4 shared the same holey index).

### The arms
| arm | units/yr | SSO-leg | $10k @0bps | @5bps | @10bps | Sortino | MaxDD |
|---|---|---|---|---|---|---|---|
| V1 undamped (T-284 PRIMARY) | 23.98 | 14.67 | 78,534 | 65,088 | 53,940 | 0.587 | −43.5% |
| **Arm1 Carver deadband B=⅔** | **6.19** | 3.43 | 125,479 | **120,083** | 114,917 | 0.763 | −41.0% |
| **Arm2 monthly-held e2** | **5.90** | 3.54 | 110,596 | **105,714** | 101,045 | 0.633 | −39.6% |

**Both arms cut turnover ~4×** (23.98 → 6.19 / 5.90 exposure-units/yr) and both **beat buy-hold SPY at the 5 bps
grid point on point estimates** — where V1 *loses*. But:

**Paired Δwealth 95% CIs (block bootstrap, @5 bps) all STRADDLE ZERO:** Arm1 − SPY `[−8.89, +37.18]`; Arm1 − V1
`[−3.08, +25.37]`; Arm2 − SPY `[−11.34, +54.31]`. Point-large, **not CI-significant** — levered paths carry huge
bootstrap variance (same caveat as T-284). The wealth gain is directional.

**The wealth gain is NOT cost savings.** At 0 bps the cost difference is only ~0.3%/yr of turnover charge (≈ +8%
over 25.6 yr), yet Arm1 gains +60%. Arm1's **mean exposure is LOWER** (1.250 vs 1.400) — so the gain comes from
**avoided whipsaw** (it sits at 4/3 for 45% of days vs V1's 14%, and at 2.0 for 26% vs 57%). The damper is a
*different exposure path*, not "the same strategy, cheaper." That is a real mechanism, but it must not be sold as
a free lunch.

### Gate (b) — crash-window exit-lag: **BOTH ARMS FAIL**
| arm | 2008 GFC | 2020 COVID | 2022 bear | worst |
|---|---|---|---|---|
| Arm1 (deadband ⅔) | de-lever 15d, full-exit 0d | 2d / 0d | 0d / **225d** | **225d** |
| Arm2 (monthly hold) | **29d / 34d** | 3d / 1d | 8d / 23d | **34d** |

**Arm1's failure is STRUCTURAL, and I mis-specified the band.** `e_target` is quantized in steps of ⅔. With
`B = ⅔` and a strict `>` test, a **single-increment move can never execute** — which is what I intended
("≥2-of-3 speed confirmation"). But the final de-risking step, **⅔ → 0, is itself a single increment**, so from ⅔
the arm **can never fully exit**. Verified: Arm1's executed move sizes are only `{1.333, 2.0}`. In a *gradual*
decline (2 → 4/3 → ⅔ → 0) it gets **pinned at ⅔ equity exposure and rides the bear** — exactly 2022's 225-day
lag. In 2008 the drop was fast enough (≥2 increments in one day) that full-exit lag was 0d, which is why the flaw
hid there. **The band buys its whipsaw savings partly with un-exited tail risk** — precisely what gate (b) exists
to catch.

Arm2's failure is the expected structural one (pre-registered): a monthly hold cannot exit faster than its
rebalance, giving a 29-34 day lag in 2008.

## VERDICT — neither arm earns the offense row (frozen gate (b) fails for both)
| arm | gate (a): beats SPY @5bps | gate (b): exit-lag ≤5d | earns offense row |
|---|---|---|---|
| Arm1 Carver deadband ⅔ | **PASS** ($120,083 vs $74,104) | **FAIL** (225d) | **NO** |
| Arm2 monthly-held e2 | **PASS** ($105,714) | **FAIL** (34d) | **NO** |

Turnover reduction is confirmed as the right lever — it converts a config that *loses* to buy-hold SPY at E's
measured slippage into one that beats it by a wide margin on points. **But both frozen implementations buy that
by delaying the crash exit, which is the one thing the offense config cannot trade away** (T-284's entire
survivability — −43% MaxDD instead of naked-2×'s −89% — rests on the gate exiting before leverage compounds).

**The diagnosis names the fix, and it is NOT a post-hoc tweak to this frozen set:** the damping should be
**asymmetric** — damp exposure *increases* (re-entry, where whipsaw costs are paid) and **never damp exposure
*decreases*** (de-risking). That preserves exit-lag ≡ 0 by construction while capturing the whipsaw savings. It is
a different mechanism, not a second band width, so it requires a **fresh pre-registration** (proposed as T-298),
not a rescue run here. Honest note: the asymmetric variant's wealth gain will be *smaller* than Arm1's, because a
material part of Arm1's +60% came from riding declines it should have exited.

N_trials += 1 (one family, jointly reported; no arm added after seeing results). Reproducible:
`scripts/turnover_reduction_t297.py`.
