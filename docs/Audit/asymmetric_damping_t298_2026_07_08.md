---
task_id: T-2026-07-08-298
title: Asymmetric damping — damp re-entry, never damp de-risking
date: 2026-07-08
author: Agent D (fair-harness lane)
type: PRE-REGISTRATION (FROZEN by the director 2026-07-08; N_trials += 1 on run)
status: FROZEN 2026-07-08 — RUN AUTHORIZED as drafted, no amendments.
---

# T-298 (FROZEN 2026-07-08) — asymmetric damping

T-297 proved turnover reduction is the right lever (both damped arms beat buy-hold SPY at 5 bps where the
undamped config loses) but **both bought it by delaying the crash exit** — Arm1 by 225 days, because a symmetric
⅔ band blocks *every* single-increment move, including the final ⅔ → 0 exit. This arm removes that failure by
construction: **damp only exposure-INCREASING moves; execute every de-risking move undamped.**

## Frozen terms (proposed)
1. **De-risking is never damped.** Whenever `e_target < e_held`, set `e_held = e_target` immediately.
2. **Re-entry rule (ONE, pre-registered):** increase exposure only when `e_target − e_held > B`, with **B = ⅔**;
   then move to `e_target`. Compared with a 1e-9 tolerance (floats).
3. Everything else is the T-284 PRIMARY config, SSO vehicle, on the **corrected full SPY calendar**.

### Rationale for B = ⅔ (priced, not tuned — and no sweep)
`e_target` is quantized in **⅔ steps** (values {0, ⅔, 1, 4/3, 2}), so *any band < ⅔ cannot bind* — this fixes the
only meaningful width, exactly as in T-297. On the increase side, `B = ⅔` means **"require at least two of the
three speeds to agree before ADDING leverage."** Whipsaw re-entries are precisely the lone fast-speed (2mo) flips:
**89% of the 415 historical re-entry events are single ⅔ increments.** Unlike T-297's symmetric band, applying it
to increases costs only **missed upside**, never **un-exited tail risk** — the asymmetry is the whole point.

## Exit-lag ≡ 0 — proven by construction, and to be verified empirically anyway
**Invariant: `e_held ≤ e_target` at all times.** Base case `e_held = e_target`. Increases are damped (`e_held`
stays ≤). Decreases execute exactly (`e_held = e_target`). By induction the invariant holds. Therefore for any
threshold `θ`, `e_target ≤ θ ⇒ e_held ≤ θ` on the same day — **the arm reaches every de-risking threshold no later
than the undamped gate, so exit-lag ≤ 0, never positive.** Gate (b) passes definitionally. **It will still be
measured empirically** on 2008 / 2020 / 2022 at both thresholds (≤1.0 and 0.0); a nonzero positive lag would
falsify the implementation, not the theory.

## Expected-turnover math (requested)
Undamped: **23.98 exposure-units/yr = 11.99 increases (50%) + 11.99 decreases (50%)** — 415 increase-events, 424
decrease-events over 25.6yr.

- A ⅔ band on increases suppresses the **89% of re-entry events that are single increments**.
- **Suppressing a re-entry also removes its matching exit** (you cannot de-risk from a position you never entered),
  so the achievable cut exceeds the naive "increase side only" bound of 11.99 units/yr. It is nonetheless **bounded
  above Arm1's 6.19 units/yr**, because every genuine ≥2-increment re-entry still executes and every de-risking
  move still executes.
- Honest expectation: **~9-14 units/yr total.**

### The falsifiable target this implies (derived from the breakeven, before running)
Undamped V1's SSO-leg turnover is **14.67 units/yr** and the **breakeven slippage is 1.55 bps** (below). Slippage
drag ≈ `SSO-leg turnover × bps`. To clear the bar at the 5 bps grid point the arm must reduce the drag by the
0.506%/yr it currently loses, i.e. reach **SSO-leg turnover ≤ ~4.56 units/yr**. Arm1 reached 3.43 (would have
cleared) but failed gate (b). **Asymmetric damping must land ≤ ~4.56 while keeping exit-lag ≡ 0.** That is a tight,
falsifiable bar, and it is why the prior below is not high.

## Breakeven slippage (measured on the frozen undamped arm; stated so E's number reads directly against it)
**Undamped V1 equals the Roth buy-hold SPY bar ($74,104 / 8.13%) at exactly 1.55 bps of SSO-leg slippage.**
- E's first genuine SSO fill measured **> 5 bps** (vs SPY/AGG's 0.51 bps) ⇒ V1 currently **loses**.
- **If E's redo lands below 1.55 bps, the UNDAMPED config beats the bar on its own** and T-298's necessity
  weakens. If it lands above, T-298 (or a better vehicle) is required. The redo number should be read against
  **1.55 bps**, not against 5.

## Gate (unchanged from T-297)
- **(a)** beat **Roth buy-hold SPY ($74,104)** at the **5 bps** grid point, on the corrected calendar.
- **(b)** crash-window exit-lag **≤ 5 trading days** (2008 / 2020 / 2022, thresholds ≤1.0 and 0.0) — expected **0**
  by construction; verified empirically.

Reported: exposure-units/yr (total + SSO-leg) vs 23.98/14.67; terminal wealth on the **0 / 5 / 10 bps** grid;
paired Δwealth CIs vs the bar and vs undamped V1; mean exposure (to show whether any gain is path-shift rather
than cost saving — the T-297 lesson); exit-lag table.

## Honest prior — ~40-50% (genuinely uncertain; below T-297's "medium-high")
Re-entry damping cuts strictly less turnover than T-297's symmetric band, and the derived target (SSO-leg ≤ ~4.56
units/yr) sits between Arm1's 3.43 and roughly half of undamped's 14.67. It is a real coin-flip. **Additionally I
expect the wealth gain to be materially smaller than Arm1's +60%**, because a meaningful part of Arm1's gain came
from *riding declines it should have exited* (its mean exposure was lower, 1.250 vs 1.400 — a path shift, not cost
savings). If this arm passes, it passes honestly; if it fails, the offense row stays unearned and the program's
standing (no implementable gated-2× beats Roth buy-hold SPY at measured slippage + honest taxes) becomes settled
pending only E's number.

N_trials += 1 on run.

## DIRECTOR FREEZE — 2026-07-08 (no amendments; BINDING)
Frozen exactly as drafted: de-risking NEVER damped (immediate execution); re-entry only when
e_target − e_held > ⅔ (quantization-forced band — pre-verified as the only binding width, not tuned);
exit-lag ≡ 0 by the e_held ≤ e_target invariant, verified empirically anyway (a positive lag falsifies the
IMPLEMENTATION); gate = beat Roth buy-hold SPY ($74,104, corrected calendar) at the 5bps grid point; the
pre-derived falsifiable target (SSO-leg turnover ≤ ~4.56 units/yr) and the mean-exposure confound report are
part of the frozen output spec. The pre-registered breakeven — **undamped V1 = the SPY bar at 1.55 bps of
SSO-leg slippage** — is the standing number E's measured redo reads against, whatever this arm's verdict.
Honest prior recorded at ~40-50%. RUN AUTHORIZED. Any deviation = a new pre-registration.

---
## RESULTS (run 2026-07-08, corrected full SPY calendar; BAR = Roth buy-hold SPY **$74,104 / 8.13%**)

### Verdict: **BOTH GATES PASS — the arm earns the offense row.** With three caveats stated below.
| arm | units/yr | SSO-leg | mean exp | @0bps | @1.55bps | @5bps | @10bps | MaxDD |
|---|---|---|---|---|---|---|---|---|
| V1 undamped | 23.98 | 14.67 | 1.400 | 78,534 | 74,093 | 65,088 | 53,940 | −43.5% |
| **T-298 asym damp B=⅔** | **10.66** | 5.59 | **1.101** | **96,320** | 94,208 | **89,672** | **83,482** | **−30.6%** |

- **Gate (a): PASS** — $89,672 vs the $74,104 bar at 5 bps. **And it clears the bar at every grid point (0 / 1.55 /
  5 / 10 bps).** It is therefore **robust to E's measured slippage, whatever the redo returns** — unlike the
  undamped config, whose entire fate hinges on the 1.55 bps breakeven (confirmed here: V1 @1.55bps = $74,093 ≈ the
  $74,104 bar, a $11 check on the pre-registered breakeven).
- **Gate (b): PASS.** Invariant `e_held ≤ e_target` **violated on 0 days**. Empirical crash exit-lag **0d in every
  crisis at both thresholds** (2008, 2020, 2022; de-lever and full-exit). Exit-lag ≡ 0 confirmed, as proven.
- Turnover **23.98 → 10.66 units/yr**, squarely inside the pre-registered 9-14 expectation.

### Caveat 1 — my pre-derived turnover target was MISSED, yet the gate passed. My derivation had a hidden assumption.
I pre-derived that the arm must reach **SSO-leg ≤ 4.56 units/yr** to clear the bar at 5 bps. It reached **5.59 —
a MISS** — and passed anyway. **The derivation assumed path-invariance** (that damping changes only slippage cost,
not the exposure path). The damper violates that assumption: it changes the path materially. The target was a
necessary condition *only under an assumption the arm breaks*. Recorded as a flaw in my own pre-registration
reasoning, in the arm's favour.

### Caveat 2 — the gain is substantially a PATH SHIFT, not cost savings (the pre-registered confound, confirmed)
Mean exposure falls **1.400 → 1.101 (−21%)** and MaxDD improves **−43.5% → −30.6%**, while wealth *rises*. At **0
bps** — where there is no slippage to save — the arm still gains **+23%** ($96,320 vs $78,534). So the bulk of the
advantage is **avoided whipsaw compounding** (each suppressed round trip is a sell-low/buy-high avoided), not
execution-cost reduction. This is a *less-levered, lower-drawdown, different strategy* that happens to compound
better — arguably a superior one, but it must not be sold as "the same config, cheaper."

### Caveat 3 — the wealth advantage is DIRECTIONAL, not CI-significant
Paired Δwealth (block bootstrap, @5 bps): **vs the SPY bar `[−15.98, +22.29]`**, **vs undamped V1 `[−7.51, +9.11]`**
— both **straddle zero**. Point estimates are large; levered paths carry wide bootstrap variance (the same caveat
that qualified T-284 and T-297). The gate is a wealth gate and it passes; the *statistical* claim is directional.

## VERDICT
**T-298 earns the offense row under the frozen gate**: it beats Roth buy-hold SPY at 5 bps (indeed at 0/1.55/5/10
bps), and its crash exit-lag is exactly zero, proven by invariant and confirmed empirically in all three crises. It
is the first offense configuration in the program to clear both gates, and — decisively — **its verdict does not
depend on E's pending slippage number.**

The honest characterisation: **asymmetric damping does not make the levered config cheaper; it makes it a
different, less-levered, less-whipsawed config that compounds better and draws down ~13pp less.** Its wealth edge
over buy-and-hold is not statistically significant on a single 25.6-year path, and its mean exposure of 1.101
means it is closer to a ~1.1× gated strategy than to the 2× the offense program set out to deploy. Recommend the
row be marked **earned-but-directional**, with the real-money decision still gated on (i) E's measured slippage
(read against 1.55 bps for the *undamped* comparison) and (ii) a forward paper record, given the CI.

N_trials += 1. Reproducible: `scripts/asymmetric_damping_t298.py`.
