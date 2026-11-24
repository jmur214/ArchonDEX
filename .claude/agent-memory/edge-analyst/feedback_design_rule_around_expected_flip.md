---
name: feedback-design-rule-around-expected-flip
description: A decision rule built around an expected sign flip between belief rows silently becomes a pass-through when the flip does not occur; bracket the break-even with rows, and store per-unit dollars
metadata:
  type: feedback
---

When a decision rule's safety comes from two belief rows disagreeing, check before the freeze that the rows bracket the break-even.

**Why:** in T-409 the pair rule (h = 0 and h = -2) was written expecting leverage to flip to the default at -2. It did not flip at -2 or at -3 (linear zero near -4.7, outside every row run), so the "does it survive pessimism" check never bit and the rule returned the leverage arm. My hand arithmetic for the expectation was too pessimistic and I could not diagnose why from frozen output.

**How to apply:**
- Before freezing, derive the break-even shift analytically or from a control, and include a row beyond it.
- Write expectations as numbers with a stated derivation, so a miss can be traced.
- Have the frozen output store every quantity the report will be asked for (worst cohort in dollars, per-cell bands); after the freeze the code cannot change.

See [[project-t409-real-money-home-2026-11-19]].
