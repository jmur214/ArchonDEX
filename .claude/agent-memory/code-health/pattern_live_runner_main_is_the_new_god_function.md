---
name: live-runner-main-is-the-new-god-function
description: As of 2026-09-17 the debt hotspot has migrated from engines/* orchestrators to the live paper path — scripts/run_paper_cloud_day.py main() is 1157 lines of T-numbered step sections, and wiring is locked by tests that read that file as TEXT
metadata:
  type: project
---

Scan 2026-09-17: `scripts/run_paper_cloud_day.py::main` = 1157 lines (file 1464), grown by appending
`# --- T-xxx:` step sections (13 of them) rather than extracting steps. This is the ACCOUNT-1/2/3
production entrypoint, so it is the highest-blast-radius god function in the repo. The engines/*
hotspots from the 2026-04 memory (discovery.validate_candidate 910 lines, risk_engine.prepare_order
777) are still there but are NOT on the live paper path anymore — the paper machine bypasses them.

**Why:** every T-task that needs "run at the tail of the day" appends a block to main() because
ordering-at-the-tail is load-bearing (T-329d3) and there is no step registry to hang it on.

**How to apply:** when scanning, rank by live-path membership (transitive imports from
run_paper_cloud_day.py + paper_trader/intel_pulse.py, ~79 files) before ranking by size.
Companion smell: 6+ test files (`test_rev31_wiring_*`, `test_acct2_repurpose_wiring_*`,
`test_fleet_halt_*`, `test_census_runs_at_tail_*`, `test_digest_friday_wiring_*`,
`test_artifact_paths_*`) lock main()'s wiring by `.read_text()` substring asserts — the exact
class the 2026-09-14 NameError lesson says cannot catch undefined names. Extracting main() into
callable steps would ALSO let those tests drive real code. Recommend the two together.

paper_trader/ broad-excepts (~110) are mostly deliberate fail-safe/fail-closed (order_manager,
trading_halt, clock_census return MISS/UNVERIFIABLE) — do NOT bulk-flag them. The real ones are
the silent-empty/default class: `sleeve_tracker._load → []`, `intel_pulse.py:189 pass → empty
news/events`, `intel_pulse.py:120 → hardcoded model id`, `market_calendar.py:65 → weekday
heuristic`, `heartbeat.py:363 alert-log write swallowed`, `combined_candidate_scorecard.py:327 →
default TaxRates()`. Same family as the T-342 always-empty-channel finding.
