---
name: project-b5-route-c-closed-correlation-regime-bet-2026-11-11
description: B-5 (T-382) verdict — levered stock+bond stacks are a stock-bond CORRELATION-REGIME bet that nets to ~0 over 58y; financing is not binding; measured embedded spreads (swaps ~50bp, futures ~0bp); RP SR 0.46 on T-306
metadata:
  type: project
---

**The verdict.** B-5 (T-382) ran 2026-11-11 on the T-306 substrate. Verdict doc:
`docs/Audit/b5_levered_diversified_verdict_2026-11-11.md`.
- **H1 NOT MET:** RSSB-class 100/100 vs 1× equity, 1968–2025, Δ log wealth +0.21 %/yr, CI
  [−1.91, +2.30] (IR 0.03).
- **Route C is closed** for a levered-ETF Roth holder.
- **Financing is NOT binding:** ci_low is −1.41 %/yr already at zero spread.

**Regime lessons (the durable part).**
- **Bond-levered stacks are a ρ(stock, bond) regime bet.**
  - ρ ≤ 0 years (deflationary): +3.3–3.5 %/yr vs equity, ci_low > 0.
  - ρ > 0 years (inflationary: 1968–97, 2022–24): −1.8 to −6.4 %/yr.
  - Deeper than equity in every inflationary rate shock: 1973–74 −56 % vs −48 %, 1980–82 −39 % vs
    −20 %, 2022 −37 % vs −25 %.
  - Shallower in the deflationary crashes (2000–02, GFC, COVID).
  - The classification is EX POST (same-year correlation). An ex-ante ρ forecast is UNTESTED, and a
    trailing-ρ switch would be a lagging indicator that flips only after 2022-type damage.
- **1.9× inverse-vol RP (equity/bond/gold):** realized unlevered SR 0.46 over 1972–2025 on T-306, not
  the literature's ~0.6.
  - The 1980–82 gold-plus-rates crash gives a −49 % drawdown, so the long window loses −1.9 %/yr.
  - 2000–25 is a point win that straddles zero.
- **Measured embedded financing** (validation of the frozen simulator against live funds):
  - swap-financed LETFs ≈ bill/SOFR + 49–57 bp (SSO, UPRO, TMF);
  - futures-stacked NTSX ≈ +0 bp;
  - UBT −38 bp.
  - The brief's frozen 50 bp is right for swaps and conservative by ~50 bp for futures stacks.
- **The brief's no-variance break-even formula** understates arm (i)'s break-even. Adding
  (σ_e² − σ_p²)/2 matches the simulator within ~6 bp.

**Why:** the macro-lens question "when do signals and levers matter" has a concrete answer here. The
lever pays only in the negative-correlation regime.

**How to apply:**
- Never re-propose static levered stock/bond stacks as a structural edge.
- Any revival must be a pre-registered EX-ANTE correlation-regime switch, judged on lag.
- The trend overlay stays UNTESTED: AQR over-captures, and DBMF has only 6.6 years.

Related: [[project-b5-financing-inputs-census-2026-11-11]],
[[project-macro-signal-lead-coincident-classification-2026-05-06]].
