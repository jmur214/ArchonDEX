---
name: project-b10-gold-leg-prereg-2026-11-11
description: B-10 (T-385) permanent 10% gold leg REFUTED on wealth; its 5.2pp MDD cut is mostly de-equitization (10% cash gives 3.95pp); gold-specific cushion clear only in 1973-74, worse than cash in real-rate shocks; T-306 gold-leg realities, T-311 flat-tail, pandas[us] guard trap
metadata:
  type: project
---

**B-10 verdict (2026-11-11, `docs/Audit/b10_gold_leg_verdict_2026-11-11.md`; review APPROVE): REFUTED as pre-registered. N_trials +2.** 90/10 equity/gold (IAUM 0.09%) monthly vs 1x SPY:
- 1971–2025: Δ log TW +0.042, CI [−0.341, +0.441].
- 2000–2025: Δ +0.124, CI [−0.105, +0.367].
- MDD −55.25% → −50.02% (5.22 pp).

**The reviewer's cash control changed the reading.** 90% equity / 10% zero-return cash gives MDD −51.30%, a 3.95 pp cut with no gold, but costs ≈0.5 log TW over 55 years.
- Gold's own cushion at the GFC is ≈1.3 pp.
- In 2022 gold was worse than the cash mattress (−22.89% vs −22.25%).
- Gold = a de-risking leg that costs no wealth, NOT a distinctive hedge.
- I initially wrote "the drawdown benefit is real and robust". That was wrong because I never had a cash control.

**How gold behaves across regimes:**
- **1973–74:** gold-specific, clearly. The 9.5 pp cut is about 2× the ~0.1·D cash bound.
- **GFC:** about 1.3 pp beyond cash.
- **1987, 1990, dotcom, COVID:** within ~0.5 pp of the cash bound.
- **1980–82 Volcker and 2022:** worse than cash. Both were real-rate shocks.
- So gold hedges only inflation shocks with falling or negative real rates.
- The wealth Δ comes from re-pricing decades: the 1970s +0.25 and 2000s +0.17, offset by the 1980s and 1990s at −0.33.

Durable substrate facts (verify before reuse):
- T-306 gold is the LBMA AM fix, then COMEX front-month from 2000-08-30. That is spot; there is no GLD or IAUM segment.
  - Local GLD_1d.csv starts 2020-04-09, inside the April 2020 EFP dislocation (+3.1% ratio jump). From 2020-06-30, GLD − substrate = −0.34%/yr, which is GLD's ER.
- Gold ends 2025-12-31 and equity 2026-04-17.
- **T-311 `load_substrate` forward-fills gold FLAT for 73 rows past its native end.**
- **pandas 3.0.1 parses dates as datetime64[us].** `asi8 // ns_per_day` makes gap guards vacuous. Use `TimedeltaIndex.days`.
- A frozen-value tail with an intact index evades native-gap guards. Only an external-price check catches it.

**Why:** gold and crisis-hedge legs keep coming back: the sleeve's GLD timing, [[project-crisis-defense-both-levers-refuted-2026-06-15]], and [[project-b5-route-c-closed-correlation-regime-bet-2026-11-11]].

**How to apply:**
- Score any static hedge leg's drawdown benefit against a SAME-WEIGHT CASH leg, never against 100% equity alone. Pre-register the cash control.
- Don't re-propose static gold as a wealth tool or as a distinctive crash hedge.
- Any gold-hedge timing idea must condition on the real-rate direction.
