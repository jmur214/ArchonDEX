---
name: check-supersession-before-quoting-frontier
description: A frontier/idea map is a snapshot; the lane may have tested+closed its items days later. Always follow the supersession chain before treating a category as "open."
metadata:
  type: feedback
---

A "frontier map" or "untested categories" doc is a point-in-time snapshot, not
current truth. In this codebase the alpha lane moves fast: the T-132 frontier
map (2026-06-10) listed 16 "untested" categories, and within 48 hours T-135 /
T-136 / T-137 / T-144 / T-145 / T-149 / T-150 tested and closed almost all of
them. A brief that says "X mapped untested categories Y" can be stale even when
X is only days old.

**Why:** quoting a closed category as "open, high-EV" wastes a director N-trial
on a dead lane and inflates the MBL bar for everything else. The honest-N
discipline in this project makes a false "open" claim actively costly, not just
wrong.

**How to apply:** when asked to assess the EV of categories from any map/idea
doc, grep docs/Audit for that task's sibling/successor task-ids FIRST (e.g.
T-132 → T-135..T-150) and read the outcome: lines before treating any category
as open. Only categories with NO closing audit are genuinely open. State the
closing audit for every category you mark closed. Same rule applies to
CURRENT_STATE / MEMORY entries tagged SUPERSEDED (CLAUDE.md non-negotiable).
