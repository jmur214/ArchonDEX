---
task_id: T-2026-07-08-294
title: Leverage-vehicle bake-off — is the offense config's edge leaking through SSO?
date: 2026-07-08
author: Agent D (fair-harness lane)
type: PRE-REGISTERED comparison set (1 family, jointly reported; N_trials += 1)
status: DONE — vehicle leak REAL (0.86%/yr) but EXECUTION is the binding leak: at E's measured >5bps SSO slippage the offense config LOSES to buy-hold SPY. Branch feature/vehicle-bakeoff-t294
---

# T-294 — the leverage-vehicle bake-off

The T-284 offense config (100% SPY, 2× when the {2,5,10}mo ensemble trend is ON) was validated on the
SIGNAL. The vehicle was never stress-tested. The external research run (Q7) argues daily-reset SSO decays in
chop (ER 0.90% + embedded financing + path-dependency), while Roth-holdable capital-efficient stacked ETFs
have historically cost LESS than the financing they replace (independent 2025 analysis: NTSX excess cost
≈ −0.50%). **This must be settled before real money routes to the offense config.**

## ⚠️ A structural fact that reframes the question (from the research doc itself)
**NTSX/RSSB cannot deliver 2× equity.** NTSX is 90% equity + 60% treasury-futures (1.5× *notional*, but only
**0.9× equity**); RSSB is 100% equity + 100% bond-futures (2.0× notional, **1.0× equity**). Both "cap at 100%
equity (no pure 2x equity)" — and in a Roth (no margin) you cannot hold >100% of either. **So they are NOT
drop-in cheaper 2× vehicles; they are different portfolios (lower equity + a bond overlay).** Comparing them
to gated-SSO on terminal wealth therefore conflates *vehicle cost* with *asset allocation*. This
pre-registration separates the two questions:

- **Q-A (the real vehicle question): V1 vs V4** — same 2× equity exposure, different vehicle. `V4 − V1` IS
  the SSO vehicle gap (ER + financing spread + daily-reset chop decay). This is the test of "is the edge
  leaking through SSO."
- **Q-B (the portfolio question): V2 / V3 vs V1** — different exposure profiles. Reported honestly as an
  allocation comparison, never as "a cheaper 2×."
- **Q-C (exposure-matched vehicle cost): V2m vs V2** — a gated SSO+cash blend sized to NTSX's 0.9× equity
  (the research doc's own suggested control). Isolates vehicle cost at MATCHED equity exposure.

## Collateral-aware construction (C/T-296 rule — the lessons_learned standard, binding)
The stacked fund's base asset is the **collateral**; the overlay leg enters as **excess-over-cash**, NOT as
two funds added (the naive form over-stated real RSST by a measured **+9.1%/yr**). With `rf` = DGS3MO daily:
```
NTSX_syn = 0.90·spy_tr + 0.10·rf + 0.60·(bond_tr − rf) − 0.0020/252     # 90/60, ER 0.20%
RSSB_syn = 1.00·spy_tr        + 1.00·(bond_tr − rf) − 0.0036/252        # 100/100, ER 0.36%
SSO_syn  = 2·spy_tr_gross − (rf + 0.0060)/252 − 0.0089/252              # daily-reset 2x (T-282, validated)
FUT_syn  = 2·spy_tr_gross − (rf + 0.0030)/252                           # ideal 2x, NO daily reset (V4)
```
`bond_tr` = the DGS10 constant-maturity TR synth (D≈7, matches NTSX's ~7yr overlay duration); `spy_tr` = the
dividend-adjusted SPY series (verified TR, T-286). RSSB's global equity/bond are approximated by SPY/DGS10 —
the real-fund basis check quantifies that approximation.

## The frozen arms (same signal everywhere: the {2,5,10}mo ensemble trend gate on SPY, causal `.shift(1)`)
| arm | vehicle | equity exposure when trend ON | note |
|---|---|---|---|
| **V1** | gated synthetic-SSO, **exactly T-284 PRIMARY** | 2.0× | the validated incumbent baseline row |
| **V2** | gated NTSX-synthetic | 0.9× (+0.6× bond) | native; cannot reach 2× |
| **V3** | gated RSSB-synthetic | 1.0× (+1.0× bond) | native; short real-fund window |
| **V4** | gated ideal-2× futures financing (rf+30bps, **no daily reset** → monthly reset at the gate) | 2.0× | the "vehicle were free" ceiling |
| **V2m** | gated SSO+cash blend sized to 0.9× equity (0.45·SSO + 0.55·cash) | 0.9× | exposure-matched control vs V2 |

Off-leg = cash at the short rate in every arm. Costs: 1.5 bps/side on gate flips, charged identically.

## Basis checks (T-285 discipline — a synthetic is untrusted until checked vs its real fund)
- **SSO_syn vs real SSO** (2006+) — re-confirm the T-282 basis (+0.23%/yr).
- **NTSX_syn vs real NTSX** (2018-08+) — report TE, CAGR gap, terminal ratio.
- **RSSB_syn vs real RSSB** (2023-11+) — **short window (~2.5yr); state honestly, treat as weak evidence.**
- Any arm whose synthetic shows > ~1%/yr unexplained basis is QUARANTINED (not quoted as a verdict).

## Required decomposition (the research demanded it) — per arm
1. **Realized financing cost per year** (the borrow/futures-basis drag actually paid).
2. **Chop-decay drag**: isolate via the **daily-reset vs monthly-reset counterfactual** on the same 2×
   synthetic (`SSO_syn` daily-compounded vs a monthly-reset 2×). The difference IS the decay.
3. **Tracking error vs the ideal exposure** (2× for V1/V4/V2m-scaled, 1.5×-notional for V2, 2.0×-notional V3).

## Named windows
- **Chop clusters (where daily-reset decay bites hardest):** 2011, 2015-16, 2018.
- **Sustained rising-rate stress:** 2022 full year. **Blind-spot #2 fold-in:** report V2/V3's **bond-leg
  behaviour in joint drawdown explicitly** — the stacked funds embed a bond leg the pure-SSO arm does not
  have, and in 2022 both legs fell together. That is part of the vehicle choice, not a footnote.

## Gates + honest prior
Reported jointly as ONE family (N_trials += 1); **no arm added after seeing results.** PRIMARY metric =
terminal WEALTH (the user's north star), with Sortino/MaxDD/Calmar as scorecard. The vehicle-gap statistic is
`V4 − V1` (wealth and CAGR), decomposed into ER + financing + decay.

**Honest prior:** the research doc's own point cuts both ways — a *gated* weeks-to-months hold is exactly the
regime where daily-reset decay is LEAST harmful (the gate exits the worst chop), so I expect the SSO vehicle
gap to be **real but modest** (~0.3-0.8%/yr), not the headline leak. I expect **V2/V3 to LOSE on wealth**
(they carry ~half the equity of V1) while possibly winning risk-adjusted — which would be an allocation
result, not a vehicle result. The Gayed critique (curve-fit MA, chop whipsaw) is acknowledged; V1 inherits it.

**Pending measured input:** E's fleet reports the first genuine SSO fill **FAILED exec-gate b (>5 bps vs
SPY/AGG's 0.51)**. The magnitude lands after the redo. Pre-registered handling: V1 is reported at **0 extra
slippage** plus a **sensitivity band at 5 and 10 bps per gate flip**; when E's measured number lands it is
substituted into V1's cost model without re-freezing anything else.

---
## RESULTS (fair harness, 2000-08 → 2026-04; buy-hold SPY TR on the same window = **$64,421 / 7.54% / −59.2%**)

### Basis checks — collateral-aware synthetics validated; C/T-296's rule independently confirmed
| synthetic | vs real | window | CAGR gap | term ratio | verdict |
|---|---|---|---|---|---|
| SSO (2× daily) | SSO | 2006-2026 | **+0.23%/yr** | 1.040 | ✅ (re-confirms T-282) |
| NTSX (90/60) | NTSX | 2018-2026 | **+0.63%/yr** | 1.044 | ✅ under the 1%/yr bar |
| RSSB (100/100) | RSSB | 2023-2026 | **−0.02%/yr** | 1.000 | ✅ near-exact — but **588 days, weak evidence** |
| _NTSX **naive** (non-collateral-aware)_ | NTSX | 2018-2026 | **+2.19%/yr** | 1.160 | ❌ |
| _RSSB **naive**_ | RSSB | 2023-2026 | **+5.61%/yr** | 1.113 | ❌ |

**C/T-296's collateral-aware rule is independently validated with magnitudes:** treating the overlay leg as
excess-over-cash cuts the NTSX error 2.19% → 0.63%/yr and eliminates RSSB's 5.61% → −0.02%/yr. The naive
"two funds added" form would have overstated RSSB by **+5.6%/yr**.

### The arms
| arm | $10k→ | CAGR | Sortino | MaxDD | Calmar |
|---|---|---|---|---|---|
| **V1 gated SSO 2× (incumbent, T-284 PRIMARY)** | 71,658 | 8.0% | 0.568 | −42.8% | 0.19 |
| **V4 gated ideal-2× futures (no daily reset)** | **87,740** | **8.8%** | 0.619 | −42.2% | 0.21 |
| V2 gated NTSX 90/60 (0.9× eq) | 39,868 | 5.5% | **0.791** | **−19.1%** | 0.29 |
| V3 gated RSSB 100/100 (1.0× eq) | 43,808 | 5.9% | 0.761 | −21.1% | 0.28 |
| V2m gated SSO+cash @0.9× eq (matched) | 35,071 | 5.0% | 0.692 | −20.2% | 0.25 |

### Q-A — the vehicle gap is REAL: **V4 − V1 = +0.86%/yr (+$16,082)** at identical 2× equity exposure
Decomposition on the standalone levered leg (integrity-checked: monthly-reset min NAV 0.13 → no wipeout, the
clamp never binds, so the decay number is real):
| component | annualized |
|---|---|
| chop/path **decay avoided** (daily vs monthly reset, *same costs*) | **+1.97%/yr** |
| fund ER avoided | +0.89%/yr |
| financing spread avoided (60→30 bps on the 1× borrowed) | +0.30%/yr |
| _sum of parts_ | +3.16%/yr |
| **measured total (standalone levered leg)** | **+2.35%/yr** _(parts don't sum exactly — compounding)_ |

The **decay is the dominant term**, and it bites exactly where predicted — chop: **2011 +4.01%/yr**, 2015-16
+1.73%/yr, 2018 +1.21%/yr. Arm-level the gap is smaller (0.86%/yr) because the levered vehicle is held only
when the gate is ON and only for the `(e−1)` fraction of NAV (avg 0.61×); the rest is plain SPY/cash.
Realized financing paid: V1 1.46%/yr vs V4 1.28%/yr.

**Honest nuance:** V4's advantage comes precisely from *not* maintaining constant exposure. TE vs the ideal
constant-2× path is V1 **0.17%/yr** vs V4 **0.46%/yr** — daily reset buys exposure fidelity and pays decay for
it. V4 is a **ceiling, not an alternative**: futures need margin/approval (box-spread financing needs
portfolio margin, ~$125K+), so it is **not Roth-implementable** at this account size.

### Q-B — NTSX/RSSB are NOT cheaper 2× vehicles. They are a different portfolio.
They cap at 100% equity (NTSX delivers **0.9× equity**, RSSB **1.0×**), and in a Roth you cannot hold >100% of
either. Gated, they make **$39.9k / $43.8k vs V1's $71.7k** — ~40% less wealth, and **both lose to buy-hold SPY
($64.4k)**. They *are* far better risk-adjusted (Sortino 0.79/0.76 vs 0.57; MaxDD −19%/−21% vs −43%). That is
an **allocation** result, not a vehicle result. This refutes the research doc's framing of NTSX/RSSB as
"a stronger gated-2× vehicle than SSO" — for a max-terminal-wealth north star they are not competitive.

### Q-C + blind-spot #2 — the stacked bond leg is a liability in a rate shock
At matched 0.9× equity, NTSX ($39.9k, Sortino 0.791) beats the SSO+cash blend V2m ($35.1k, 0.692) — but
**most of that is the bond leg's 40-year bull, not vehicle efficiency.** In 2022 it reversed: the bond leg
(DGS10 TR) returned **−13.1%** *alongside* equity's **−18.2%**. V2 (with the bond overlay) lost **−14.0%** vs the
equity-matched, bond-free V2m at **−11.7%**. **The overlay is not a diversifier in a rate shock; it amplified
the loss.** Named windows (CAGR / in-window MaxDD):
| window | V1 | V4 | V2 | V3 | V2m |
|---|---|---|---|---|---|
| CHOP 2011 | −13.1% / −27.4% | −11.7% / −26.7% | +0.0% / −8.9% | +3.0% / −8.1% | −5.6% / −13.1% |
| CHOP 2015-16 | −2.8% / −19.9% | −2.1% / −19.4% | −0.7% / −8.8% | −1.0% / −9.8% | −0.8% / −9.2% |
| CHOP 2018 | −3.8% / −20.8% | −3.4% / −20.6% | −2.2% / −10.4% | −4.0% / −12.1% | −0.3% / −9.5% |
| RATE-STRESS 2022 | −26.5% / −27.2% | −26.3% / −27.0% | −14.0% / −14.0% | −16.9% / −17.3% | −11.7% / −12.2% |

## ⚠️ THE HEADLINE — the binding leak is EXECUTION, not the vehicle
The gate turns over **23.93 exposure-units/yr** (SSO leg **14.62**, SPY leg 9.31). E's fleet measured the first
genuine SSO fill **FAILING exec-gate b at >5 bps** (vs SPY/AGG's 0.51 bps). Charging that **fairly** — the extra
slippage on the **SSO leg only**, SPY leg at its measured 0.51 bps:

| V1 under slippage | $10k→ | CAGR | vs buy-hold SPY ($64,421) |
|---|---|---|---|
| 0 bps (the T-284 number) | 71,658 | 7.99% | **BEATS** (+11%) |
| **SSO leg +5 bps** (E's measured floor) | **58,709** | **7.15%** | **LOSES** |
| SSO leg +10 bps | 48,686 | 6.37% | LOSES badly |

**The offense config's entire edge over buy-and-hold SPY is +0.45%/yr (7.99% vs 7.54%). Its slippage exposure
at E's measured floor is ~0.84%/yr. The edge is thinner than the execution cost.** (Charging the slippage on
all turnover — the upper bound — gives $52,742 / 6.70%.) This dwarfs the 0.86%/yr vehicle gap.

## VERDICT
1. **Yes, the edge leaks through the vehicle — 0.86%/yr**, dominated by daily-reset chop decay (+1.97%/yr on
   the levered leg; +4.01%/yr in 2011), not by ER or financing. The research run's mechanism is confirmed.
2. **But no Roth-holdable vehicle recovers it.** V4 (futures) needs margin; NTSX/RSSB cannot reach 2× equity
   and lose ~40% of terminal wealth (and lose to plain SPY). **SSO remains the vehicle of record** for the
   offense config — with the decay now measured and disclosed, not assumed away.
3. **The decision-relevant finding is EXECUTION.** At E's measured >5 bps SSO slippage the offense config
   **loses to buy-and-hold SPY on terminal wealth.** **Recommendation: do NOT route real money to the offense
   config until SSO execution slippage is measured and controlled.** The highest-leverage fix is **turnover
   reduction** (~24 exposure-units/yr is a lot): a deadband/Carver buffer (T-148) on the ensemble fraction, or
   holding `e2` monthly rather than letting it flip daily. That is a SEPARATE pre-registered arm, not a
   post-hoc tweak to this one.
4. C/T-296's collateral-aware rule is independently validated (naive error +2.19%/yr NTSX, +5.61%/yr RSSB).
   RSSB's near-exact basis rests on only 588 days — weak evidence, flagged.

N_trials += 1 (one family, jointly reported; no arm added after seeing results). Reproducible:
`scripts/vehicle_bakeoff_t294.py`.
