---
task_id: T-2026-07-02-262
title: Compose T-252 conditional vol-targeting into the T-236 sleeve — verdict (H0)
date: 2026-07-02
worker: Agent B
branch: feature/compose-voltarget-t262
status: DONE — ONE pre-registered trial (N_trials += 1); H0 (mechanism overlap). MEASUREMENT only.
---

# T-262 — compose T-252 vol-targeting into the fair sleeve

## Setup
On D's FAIR harness (T-255): **baseline** = `sleeve_returns_fair` verbatim (EW
SPY/BOND/GOLD long-flat; flat leg earns the short rate; ER + 1.5bps both sides).
**Treatment** = the SAME sleeve with T-252 conditional vol-targeting applied to
the **SPY leg only**, using the **EXACT T-252 spec** (expanding-P80 extreme-vol
gate, target 0.15, 20d realized vol, floor 0.5, ceiling 1.0 — **no re-tuning**).
BOND/GOLD legs unchanged (vol-targeting is a risk-asset lever). Full-cycle
1993-2026 (8274 bars); paired block-bootstrap (21d blocks, 1000 iter).

## Result
| strategy | Sortino | ci_low | Sharpe | CAGR | MaxDD | $10k→ |
|---|---|---|---|---|---|---|
| sleeve_fair (baseline) | 1.098 | 0.665 | 0.866 | 5.1% | −11.8% | 50,485 |
| sleeve_fair + T-252 | 1.094 | 0.659 | 0.869 | 4.9% | −11.8% | 48,511 |

**Paired (T-252 − baseline):** ΔSortino 95% CI **[−0.031, +0.035]** (straddles 0);
ΔMaxDD 95% CI **[−0.009, +0.024]** (straddles 0, `+` = shallower/better);
Δterminal-wealth 95% CI [−0.70, +0.13] ×start; **P(T-252 Sortino > baseline) = 51%**.

**Named windows (MaxDD / cum-ret):**
- COVID-2020: baseline −4.7% / +5.9%  →  +T-252 −4.7% / +5.1%
- bear-2022:  baseline −5.4% / −4.1%  →  +T-252 −5.5% / −4.1%

**Integer-share @ $10K** (T-257 machinery, real SPY/AGG/GLD): tracking error
baseline **0.352%/yr** → +T-252 **0.35%/yr**. Vol-scaling does **NOT** break
whole-share tracking.

## Verdict — H0 (adds nothing), with a clear mechanism
Composing T-252 into the sleeve is a **NULL**: no significant ΔSortino or ΔMaxDD
(both CIs straddle 0), a coin-flip win rate (51%), and a small wealth cost
(CAGR 5.1→4.9%). It did NOT cut the tail in COVID-2020 or 2022.

**Why (mechanism overlap):** the sleeve's trend overlay ALREADY moves SPY to
cash/bonds in sustained downtrends. In extreme-vol storms SPY is therefore
usually **already flat** (`eff_pos = trend_pos · vol_scale = 0`), so the
conditional vol-target has nothing to de-gross. T-252's standalone win (MaxDD
−55%→−47%) was measured against an **always-long SPY (buy-hold)** — the sleeve is
NOT always-long, so the incremental tail-protection collapses. The two mechanisms
protect the same tail; stacking them is redundant.

**Recommendation:** do NOT add T-252 to the trend sleeve — the trend overlay is
already the tail-protector. T-252 remains valuable as the **safe-core risk
component of C's barbell (T-251)**, where the core is a *static* long allocation
(always-on risk exposure) that the conditional vol-target CAN de-gross — that is
the always-long context where the standalone win applies. The distinction is the
deliverable: vol-targeting composes with a *static* long core, not with a
*self-exiting* trend sleeve. Module stays default-OFF; nothing enabled.
