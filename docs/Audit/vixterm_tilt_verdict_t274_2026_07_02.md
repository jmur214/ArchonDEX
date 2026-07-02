---
task_id: T-2026-07-02-274
title: VIX-term / VVIX implied-vol sizing tilt — VERDICT (H0; closes the vol-conditioning family)
date: 2026-07-02
worker: Agent B
branch: feature/vixterm-tilt-t274
status: DONE — ONE frozen trial (N_trials += 1). VERDICT: H0. Implied vol does NOT beat realized, and neither beats the null.
---

# T-274 — VIX-term / VVIX implied-vol tilt: VERDICT (H0)

FROZEN mapping (a priori, no sweep): implied-vol stress → continuous 0.5–1.0×
SPY tilt. `bw = VIX/VIX3M`; `s1 = clip((pctl_exp(bw)−0.5)·2,0,1)`;
`s2 = clip((pctl_exp(VVIX)−0.7)/0.3,0,1)`; `stress = max(s1,s2)`;
`scale = clip(1−0.5·stress, 0.5, 1.0)`, applied (lagged) to the SPY leg of the
fair T-255 sleeve. Compared vs TWO nulls over the VIX-defined window (2006-07 →
2026, 4982 days).

## Result
| strategy | Sortino | ci_low | Sharpe | CAGR | MaxDD | $10k→ |
|---|---|---|---|---|---|---|
| sleeve (unconditioned) | **1.238** | 0.685 | 0.976 | 6.1% | −11.8% | 32,301 |
| sleeve + T-252 (realized) | 1.226 | 0.675 | 0.969 | 6.0% | −11.8% | 31,344 |
| sleeve + VIX-term (implied) | 1.210 | 0.658 | 0.960 | 5.8% | −11.8% | 30,173 |
| 60_40 | 0.919 | 0.304 | 0.746 | 7.7% | −36.7% | 43,355 |
| schwab_like | 1.043 | 0.441 | 0.842 | 6.7% | −27.8% | 35,478 |

**Paired block-bootstrap (implied − null):**
- vs **unconditioned**: ΔSortino 95% CI **[−0.070, +0.043]**, Δwealth [−0.55, +0.00] ×start, **P(implied > null) = 28%**.
- vs **T-252 realized**: ΔSortino 95% CI **[−0.064, +0.055]**, Δwealth [−0.39, +0.09] ×start, **P(implied > realized) = 39%**.

## Verdict — H0 (as the ~10% prior predicted)
1. **The implied-vol tilt adds NOTHING and slightly HURTS.** It is the worst of
   the three sleeves (Sortino 1.210 < 1.238 unconditioned), with identical MaxDD
   (−11.8% — no tail cut) and a small wealth cost; the paired ΔSortino CI
   straddles 0 (negative-leaning) and P(implied > null) is only 28%.
2. **Implied vol does NOT beat realized vol.** VIX-term vs T-252: ΔSortino CI
   straddles 0, P = 39%. The extra information in options-implied vol / vol-of-vol
   buys nothing over the realized-vol conditional — which was itself redundant
   with the trend rule (T-262).
3. **Same mechanism (redundancy with the trend overlay).** The sleeve's long/flat
   trend rule ALREADY exits SPY to cash/bonds in sustained downtrends, so during
   the exact backwardation/VVIX-spike states the tilt fires, SPY is usually
   already flat — the tilt has nothing to de-gross. This confirms + extends the
   T-262 finding across the WHOLE vol-conditioning family (realized AND implied).

## What this closes
The vol-conditioning family — realized-vol (T-252/T-262) AND implied-vol
(VIX-term/VVIX, this task) sizing tilts on the sleeve — is **CLOSED with evidence:
none of them beat the unconditioned trend sleeve, because the trend rule already
captures the vol-state information (it exits in storms).** Consistent with T-233
(VIX-term trigger-happy as a timer). The realized win remains the plain trend
sleeve; adding vol-state conditioning is redundant. Measurement only; nothing
enabled. (T-252 remains valuable only for a *static* always-long core — C's
barbell T-251 — which has exposure to de-gross; the self-exiting sleeve does not.)
