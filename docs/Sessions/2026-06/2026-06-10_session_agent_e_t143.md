# Session Summary: 2026-06-10 (Agent E — T-143, third task)

## What was worked on

- **T-143**: the locked T-118b crisis-replay pre-registration
  (v1 + addendum v2) implemented as tested code —
  `scripts/crisis_replay_t118b.py` + 23 fixture tests. Fixture-only;
  zero contact with real campaign artifacts (the campaign is still
  blind; first real run is director-executed post-relaunch).

## What was decided

- **Gate date-fixing = month-anchored day-pinning** (peak = TR max in
  the locked peak month, trough = TR min in the locked trough month):
  the only rule-ambiguity-free mechanical reading, and it's licensed by
  the registration's own §1 (SET locked; exact days fixed at analysis
  time). Both derivation rules (all-time-high, local-peak) ship as the
  honest-derivation CHECKER, never the gate.
- **PARTIAL vs FAIL operationalized** per the brief's own adjudication
  (v1-hole must FAIL): PARTIAL requires (i)+(iii) AND all v2 co-equal
  criteria — only trigger-tunable (ii)/(iv) failures earn "iterate
  parameters"; any v2 failure is structural → FAIL.
- Other registration silences resolved per §6 (less favorable to the
  overlay) and tabled in the audit: ratio-test units (return-pp,
  episode-frequency-annualized), single-episode share over the NET
  benefit (fails outright when net ≤ 0), calm days = complement of ALL
  reported episode windows, CI-excludes = lower bound above −80bps.

## What was learned

- **THE FINDING (STOP-reported, director must adjudicate
  PRE-unblinding):** the locked episode list is not mechanically
  derivable from the locked rule on real S&P 500 TR data under any
  consistent reading — 2011 needs local-peak, local-peak admits the
  omitted 2010 (−15.6%) and fragments dotcom/GFC/2022, strict re-dates
  dotcom's peak to 2000-09, and **2025-02→04 (−18.7% TR) clears every
  reading, is on no list, and predates the registration** so the
  auto-append clause doesn't cover it. Verified on Stooq SPY (proxy)
  AND ^SP500TR (full 1999→2026 fetch, /tmp only). Full entry in
  lessons_learned.md: writing the verification code IS the audit.
- No on-disk S&P TR series covers 1999→present (longest TR-flavored
  proxy starts 2005-02) — flagged; caching ^SP500TR is a deliberate,
  manifest-pinned substrate decision for the director.
- Fixture-geometry insight (committed as a test comment): the v1-hole
  is only constructible when recoveries are sharp — within a window the
  bleed budget is bounded by the ΔMaxDD margin, so the forgone
  V-recovery is what makes MaxDD-passing-but-net-negative possible. My
  first construction accidentally IMPROVED terminal wealth (halving a
  355-day decline dominates any 20-day bleed).

## Pick up next time

- T-143 done pending director merge + adjudication of the episode-list
  findings (amend the registration to "curated set + month-pinned
  dates" and decide 2025/2010 status — legitimate only while the
  campaign stays blind).
- Post-relaunch: director runs the one command (in execution_manual)
  on the PRIMARY config's on/off 26-yr artifacts.

## Files touched

```
scripts/crisis_replay_t118b.py            (new — harness, importable + CLI)
tests/test_crisis_replay_t143.py          (new — 23 fixture tests)
docs/Audit/crisis_replay_harness_t143_2026_06_10.md (new)
docs/Core/execution_manual.md, docs/State/lessons_learned.md
```

## Subagents invoked

- None — the locked registration demanded line-by-line fidelity;
  direct implementation with targeted data checks was the right
  altitude.
