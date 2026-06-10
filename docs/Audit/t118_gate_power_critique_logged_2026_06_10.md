# Director note — T-118 decision-gate power critique, logged BEFORE results (2026-06-10)

**Status:** timestamped pre-unblinding note. C's T-118 52-cell overlay campaign is IN
FLIGHT; no results have been seen by anyone as of this note.

## The critique (external research, 2026-06-10 system-improvements pass, Q1b)

> "You're validating a crisis-defense overlay with an A/B that can't have power —
> crises are too rare for [the Sharpe-difference CI] to resolve... Replace the A/B
> framing with historical crisis-replay evaluation (2008, 2011, 2015, 2018Q4, 2020,
> 2022 windows) + pre-registered cost ceiling in calm regimes. The decision rule is
> 'cheap insurance with bounded calm-period drag,' not 'statistically significant
> Sharpe improvement.'"

Applied to T-118's frozen gate (`ci_low > 0 on the full-window Sharpe DIFFERENCE
AND 26-yr MDD reduction ≥ 25% AND no single-event dependence`): an overlay that acts
only at rare regime transitions moves full-window Sharpe little even when it works;
the Sharpe-difference CI will plausibly straddle zero **even for a genuinely good
overlay**. The first gate clause may therefore be structurally near-unpassable —
a designed-to-fail criterion, in the same family as our CLAUDE.md concern about
implicit goalpost-moving, but in the opposite direction (goalposts set
unreachably, which invites post-hoc loosening — the thing this note exists to
prevent).

## The ruling (made now, before unblinding)

1. **The frozen T-118 gate STANDS for the running campaign.** No mid-flight
   amendment. C reports against the pre-registered gate exactly as written.
2. **This note pre-registers the interpretation discipline for one specific
   outcome:** if the result lands as *MDD reduction large + crisis-window
   performance strong + calm-period drag small + Sharpe-difference CI straddling
   zero*, the verdict is recorded as **FAILS the frozen gate** — and a SEPARATE,
   freshly pre-registered T-118b may then be designed on the crisis-replay +
   calm-drag-ceiling framing (per-crisis-window performance + a hard calm-regime
   cost ceiling as the decision rule). Because this note predates unblinding, that
   redesign is a legitimate power correction, not goalpost-moving.
3. If the result passes the frozen gate outright, this note is moot (and the gate
   was conservative — fine).
4. If the result shows no MDD benefit either, the overlay fails on substance and
   no power argument applies.

## Why this is being filed now
The integrity of (2) depends entirely on its timestamp relative to the results.
Filed while the cells are still running; committed to main immediately.
