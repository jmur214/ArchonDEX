---
name: project-t408-post-fomc-drift-2026-11-19
description: T-408 post-FOMC Treasury drift (Brooks-Katz-Lustig NBER w25127) for the bond sleeve — closed unrun on power; the surprise it scales with shrank 3x since 2015; direction-only form is rate-cycle timing
metadata:
  type: project
---

T-408 (2026-11-19) delivered a pre-run design note recommending CLOSE.
- File: `docs/Sources/design_note_post_fomc_treasury_drift_t408_2026-11-19.md`, commit df82464 on the worktree branch.
- No prereg, no trial spent, nothing measured.

**Why:** T-407 §6.4 suggested it, under the user's "any research we don't have to pay for".

**Facts worth not re-deriving:**
- **The paper.** The 2019 revision is current; all three PDFs plus the separate appendix are free on nber.org.
  - Unrefereed, partly AQR-funded.
  - Drift scales with the Kuttner fed funds futures SURPRISE on target-change days only. Days 2–50, 10Y: ≈1.84 bp per bp, about 13.7 bp of IEF price per bp. Meetings with no change show none.
  - The April 2019 revision adds that it is almost all hawkish surprises: 10Y 4.32 bp/bp at day 50, ≈32 bp of IEF price per bp. Added post hoc.
  - The paper's own tradeable (ex-day-1) fund-return t is ≈2.7, below the 2.96 bar even in-sample.
  - "Robust to extending to 2018" adds only ~1 bp-surprise events (0.4 % of regression weight).
- **Surprise sd on scheduled change days:** 7.2 bp in 1994–2008, 1.0 in 2015–18, 2.2 in 2018–23. That cuts power and payoff about 3×.
- **Census:** 110 target changes since 1990 (Fed page = FRED). After the paper (2018-04 →): 24 scheduled changes, 17 with a free surprise, 6 hawkish.
- **Pass probability at z 2.96:**
  - out-of-sample surprise regression 0.5 %;
  - hawkish exit 1.2 % (per-event ratio 0.29, but about 1 event a year, so ~165 years to power);
  - full 1994–2026 41 %, but 97 % of its weight is the paper's era plus Dec 2008, so it is a replication.
- **Payoff ceiling:** 5–14 bp/yr of the book.
- **The direction-only form** ("after a hike, shorten") chains: 43 of 59 changes are followed by another same-direction change within 49 days. The effective N is 21 rate cycles since 1994, so it is regime timing.
- **The Fed hiked 25 bp on 2026-09-16** (to 3.75–4.00 %) after three cuts in late 2025.

**How to apply:**
- Don't re-propose FOMC-drift or Fed-direction bond timing for this book unless target-change surprises return to about 5 bp or more, sustained.
- Treat as a separate, unpublished hypothesis (mining risk) any rule keyed on PATH surprises (ED/MPS) rather than the target surprise.

See [[feedback-signal-variance-collapse]], [[feedback-per-event-effect-to-noise]], [[reference-fomc-surprise-sources]], [[project-t407-pm-information-2026-11-19]].
