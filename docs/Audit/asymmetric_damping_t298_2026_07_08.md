---
task_id: T-2026-07-08-298
title: Asymmetric damping — damp re-entry, never damp de-risking
date: 2026-07-08
author: Agent D (fair-harness lane)
type: PRE-REGISTRATION DRAFT (awaiting director freeze; N_trials += 1 on run)
status: DRAFT — NOT RUN. Awaiting freeze.
---

# T-298 (DRAFT) — asymmetric damping

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

N_trials += 1 on run. **Not run. Awaiting director freeze.**
