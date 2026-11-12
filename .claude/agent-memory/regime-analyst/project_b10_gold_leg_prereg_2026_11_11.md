---
name: project-b10-gold-leg-prereg-2026-11-11
description: B-10 (T-385) permanent 10% gold leg REFUTED on wealth (ci_low<0 both windows), MDD −5.2pp real; gold hedge is real-rate-regime-conditional; T-306 gold-leg realities + T-311 flat-tail ffill + pandas[us] guard trap
metadata:
  type: project
---

**B-10 verdict (2026-11-11, `docs/Audit/b10_gold_leg_verdict_2026-11-11.md`): REFUTED as pre-registered.** 90/10 equity/gold (IAUM 0.09%) monthly vs 1x SPY:
- 1971–2025: Δ log TW +0.042 (+0.08%/yr), CI [−0.341, +0.441].
- 2000–2025: Δ +0.124 (+0.48%/yr), CI [−0.105, +0.367].
- MDD −55.25% → −50.02% (5.22 pp). The ΔMDD bootstrap CI excludes zero; the recovery came 18 months sooner.
- TE 2.7%/yr; IR 0.03 / 0.18, against an MBL need of 0.29 / 0.42.
- Every prereg prediction hit except one: the 252-day block CI was only 1.16× wider, not ≥1.5×.

**How gold behaves across regimes:** the hedge depends on the real-rate regime.

| crisis | MDD change from the gold leg |
|---|---|
| 1973–74 | −9.6 pp |
| GFC | −5.2 pp |
| dotcom | −4.5 pp |
| 1987 | −3.5 pp |
| COVID | −2.9 pp |
| 1980–82 Volcker | **+2.6 pp (worse)** |
| 2022 | −1.7 pp only |

- The wealth Δ comes from re-pricing decades: the 1970s +0.25 and 2000s +0.17 are offset by the 1980s and 1990s at −0.33.
- The monthly equity-gold correlation is −0.13 to +0.18 by decade; it was positive in the 1980s and 2020s.

Durable substrate facts (verify before reuse):
- T-306 gold is the LBMA AM fix to 2000-08-29, then COMEX front-month `gold_gcf_t255`. That is spot; there is no GLD or IAUM segment.
  - Local GLD_1d.csv starts 2020-04-09. GLD − substrate is +0.04%/yr from 04-09, because of the April 2020 EFP dislocation (+3.1% ratio jump), and −0.34%/yr from 2020-06-30, which is GLD's ER.
- Gold ends 2025-12-31 and equity 2026-04-17, so any equity+gold window ends 2025-12-31.
- **T-311 `load_substrate` forward-fills gold FLAT for 73 rows past its native end.** T-311's 3-asset arm is affected (the director is logging it).
- **pandas 3.0.1 parses dates as datetime64[us].** `asi8 // ns_per_day` makes gap guards 1000× too small, so they are vacuous. Use `TimedeltaIndex.days`. A planted-hole lock caught it.
- The 18-day 1968 gold gap is the real London market closure.

**Why:** gold and crisis-hedge legs keep coming back: the sleeve's GLD timing, [[project-crisis-defense-both-levers-refuted-2026-06-15]], and [[project-b5-route-c-closed-correlation-regime-bet-2026-11-11]].

**How to apply:**
- A static ≤20% diversifier vs 1x equity on T-306 leaves wealth within noise. Value shows only in MDD and time under water.
- Don't re-propose static gold as a wealth tool.
- Any gold-hedge timing idea must condition on the real-rate direction, not on a "crisis" flag.
- The forward-twin proposal (verdict §9) tests the drawdown cushion only.
