# Session Summary: 2026-06-11 (Agent E — T-152, eighth task)

## What was worked on

- **T-152**: CUSUM + Page-Hinkley divergence monitors — built,
  CALIBRATED on our own history (the actual deliverable), shadow-wired
  into summaries. The pre-registered live kill metrics, tuned before
  paper trading exists.

## What was decided

- Operating points locked at ≤1 false alarm/yr on 200 block-bootstrap
  null replicas: CUSUM-mean k=1.0/h=5.0 (0.91/yr), CUSUM-var
  k=2.0/h=12.0 (0.95/yr), PH δ=0.05/λ=20σ (0.64/yr). Documented
  choices, revisitable pre-paper under fresh registration.
- **A variance channel was ADDED mid-task** when calibration showed the
  mean channel near-blind to the scenarios that matter — with its own
  χ²-scaled grid (the N(0,1)-scale cells over-alarm on zv).
- Operating-point selection fails LOUD when no grid cell meets the
  target (it fired correctly twice during calibration).
- Alarm action semantics documented for the paper hook: REDUCE/FLATTEN
  only, points frozen unless re-registered before go-live.

## What was learned

- **Research PH params were mis-scaled ~80×** for standardized inputs
  (λ=0.25σ ⇒ ~104 alarms/yr) — re-derive detector parameter SCALE
  against the statistic actually fed (lessons_learned.md).
- **The structural finding: daily mean-shift monitors cannot see
  realistic alpha decay** (50% edge cut ≈ 0.04σ/day at our SNR — no
  detect inside a quarter); vol-scale breaks detect in ~13-16td. Kill
  stack = mean+var channels (fast/regime) + safe-f/CAR25 + deep-window
  cadence (slow/alpha).
- **Face validity**: the calibrated monitors fired on 2024-08-05
  (yen-carry unwind) and the US-election week, unprompted.
- The suite is FULLY GREEN (2316 passed) — the five long-standing
  pre-existing failures were fixed on main between T-151 and T-152.

## Pick up next time

- T-152 done pending director merge. Calibration refresh on a 26-yr
  run dir when available (one command). Paper-loop wiring =
  paper-trading milestone, propose-first (the streaming update()
  contract is the integration surface).

## Files touched

```
backtester/divergence_monitors.py                 (new)
scripts/calibrate_divergence_monitors_t152.py     (new)
cockpit/metrics.py                                (_divergence_report + 2 keys)
tests/test_contracts.py                           (keys)
tests/test_divergence_monitors_t152.py            (new, 15 tests)
docs/Audit/divergence_monitors_t152_2026_06_11.md (new)
docs/Core/execution_manual.md, docs/State/lessons_learned.md
```

## Subagents invoked

- None.
