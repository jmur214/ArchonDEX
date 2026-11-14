---
name: feedback-held-book-timing-trap
description: Execution-timing effects on a held book scale with the TRADED fraction, not the book; full-notional framings (T-341 Arm B, the B-8 brief's 20 bps/yr) overstate by ~100x; a same-index proxy for a not-yet-listed satellite makes the pre-listing window carry zero information
metadata:
  type: feedback
---

A book that is held continuously earns every overnight leg whatever time it trades. Execution timing touches only the dollars that move: the monthly drift trade plus any new money. For the 85/15 VOO/MTUM at TE ~9%/yr, the drift trade is ~0.27% of the book per leg per month. That puts the plausible effect at ≤ 0.3 bps/yr and even a perfect-hindsight oracle at ~2–5 bps/yr. Any prior or brief that prices timing on the full notional (T-341 Arm B's +6.8 bps per event; the B-8 brief's "≤ 20 bps/yr") is off by about two orders of magnitude.

**Why:** found while pre-registering B-8 (T-386, 2026-11-11, prereg `54d0104`). The brief's 15% prior rested on the full-notional framing.

**How to apply:**
- For any execution, calendar or rebalance-timing hypothesis, first compute turnover × σ(interval) to get the MDE and the oracle ceiling. Do this before accepting the brief's prior.
- New money (contributions) is the only flow large enough to matter. Its timing Δ is mostly time-in-market, which has a known sign (earlier wins). Never let a contribution arm meet a timing H1.
- **Proxy trap:** proxying a satellite with the core's own index before the satellite listed (MTUM before 2013-05 → SPY) makes the book degenerate. Δ is then identically 0 pre-listing. A "2000–2025" window adds zeros, not evidence. Gate on the native window, and use the degenerate stretch as an identity lock.

Related: [[project-b8-execution-timing-2026-11-11]], [[feedback-satellite-gate-low-power]]
