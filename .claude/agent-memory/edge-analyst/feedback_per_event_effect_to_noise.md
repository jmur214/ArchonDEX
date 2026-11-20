---
name: feedback-per-event-effect-to-noise
description: A "per-event" design only beats the honest-N bar when effect/σ per event is large (≳0.3); release-day timing rules sit at ~0.1 and need 600+ events; persistent conditioning variables turn event rules into regime timing
metadata:
  type: feedback
---

Before calling anything a "per-event niche" (the fresh-eyes audit's passable class), compute the per-event ratio effect/σ. The number of events needed for 80 % power at z_c ≈ 2.96 is N ≈ (3.8 / ratio)².
- A ratio of 0.5 (odd-lot tenders: 3–8 % against ~8 %) needs ~60 events.
- A ratio of 0.1 (macro-release-day SPY timing: 0.1–0.2 % against 1.3 %) needs 600–2,400 events, i.e. decades at ~45 releases a year.

The second case is a time-series timing rule that happens to fire on event days.

A second trap: if the conditioning variable is persistent, the event split is really a regime split. Examples are implied uncertainty, a consensus gap, or a recession probability. The effective N is then the number of regimes, not events. It belongs on the stay-dead "regime-timing of anything" list.

**Why:** found in T-407 (2026-11-19). The brief hoped prediction-market prices would give per-event evidence for directing the held Roth book. Every tradeable form had a ratio of about 0.1, and the uncertainty-scaled form sorted 2022 against 2024.

**How to apply:**
- Put the ratio and the implied N/years in the first paragraph of any per-event design.
- Check the autocorrelation of the conditioning signal across events before counting events as independent.

See [[project-t407-pm-information-2026-11-19]], [[feedback-held-book-timing-trap]].
