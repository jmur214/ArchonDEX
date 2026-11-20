---
name: feedback-signal-variance-collapse
description: For a published effect that scales with a conditioning variable (a surprise or shock size), check whether that variable's DISTRIBUTION shrank after publication — power and payoff scale with sd(signal), not with the coefficient; also check which few events carry the regression weight
metadata:
  type: feedback
---

When a paper's effect is "b per unit of X", the forward edge is b · |X|, and power is about b · sd(X) · √N / σ.

A coefficient can survive perfectly while sd(X) collapses for a structural reason, killing both payoff and testability. Before computing power, census the post-publication distribution of X, using the conditioning variable only, never the outcome. Use that, not the paper's sd.

Also compute each event's share of the regression weight (Σ demeaned X²) by era. Where a few large events dominate, a "full-sample" test is a replication of those events, not evidence about the current regime.

**Why:** T-408 (2026-11-19).
- Brooks-Katz-Lustig post-FOMC drift: the target surprise's sd fell from 7.2 bp (1994–2008) to about 2 bp (2015–2023) because the Fed pre-announces.
- Out-of-sample pass probability fell to ≤ 1 %, and payoff fell about 3×.
- In the full-sample design, Dec 2008 alone carried 19 % of the weight and the post-2015 events 3 %.
- Sanity check that worked: b · sd(X) · √N / σ, with the paper's own sd and N, reproduced its published t (3.3). Do this before trusting the planning values.

**How to apply:**
- Applies to any shock-scaled published effect: Fed or ECB surprises, earnings-surprise drift (consensus dispersion), macro-surprise drift.
- Report sd(X) by era next to the coefficient in the first table of the design note.

See [[feedback-per-event-effect-to-noise]], [[project-t408-post-fomc-drift-2026-11-19]].
