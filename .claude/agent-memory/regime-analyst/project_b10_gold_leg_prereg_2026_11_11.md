---
name: project-b10-gold-leg-prereg-2026-11-11
description: B-10 (T-385) permanent 10% gold leg prereg (0cc3f56, Phase 1 STOP) — T-306 gold-leg realities, T-311 loader flat-tail hazard, pre-data power arithmetic for any static gold weight vs 1x equity
metadata:
  type: project
---

B-10 prereg committed 0cc3f56 on `research/gold-leg-b10` (DRAFT, Phase-1 STOP, five rulings requested). Predicted outcome: REFUTED (CI spans zero, positive points), MDD clause met. Prior P(H1) 7% vs brief 25%.

Durable facts learned (verify before reuse):
- **T-306 gold leg is LBMA AM fix (1968→2000-08-29) → COMEX front-month `gold_gcf_t255` (2000-08-30→2025-12-31)**, i.e. SPOT. No GLD/IAUM segment despite briefs saying "LBMA → GLD → IAUM". ER must be applied synthetically. Local GLD_1d.csv only starts 2020-04-09.
- **gold ends 2025-12-31, equity 2026-04-17** — any T-306 equity+gold window ends 2025-12-31.
- **T-311 `load_substrate` forward-fills gold FLAT 73 rows past its native end** (to 2026-04-17) — besides the known vacuous hole guard. T-311's 3-asset arm ran its last ~3.5 months on flat gold. Refuse window end > min(native ends).
- The 18-day gold gap is 1968-03-15→04-01, the real London gold-market closure (gold crisis), not a data hole.
- Static-gold power arithmetic (literature σ: gold 19.5, eq 16.5, ρ≈0): TE of 10% gold ≈ 2.55%/yr; MDE ≈ 0.97%/yr over 55y, 1.40%/yr over 26y. Expected Δ ≈ 0.1·(g_gold−g_eq) + 0.29%/yr rebalancing bonus ≈ +0.1 (1971+) / +0.6 (2000+) %/yr — far under MDE.
- Both brief windows start at gold-favorable points (1971 pre-repricing; 2000 near secular low) — a pass is weaker than it looks.

**Why:** gold/defensive-leg questions recur (sleeve GLD timing, crisis hedges [[project-crisis-defense-both-levers-refuted-2026-06-15]], B-5 correlation-regime [[project-b5-route-c-closed-correlation-regime-bet-2026-11-11]]).
**How to apply:** for any static-hedge-leg test vs 1x equity on T-306, expect wealth CIs to span zero at ≤20% weight; the only plausible win is MDD. Check verdict `docs/Audit/b10_gold_leg_verdict_2026-11-11.md` (if it exists) for realized numbers before quoting these predictions.
