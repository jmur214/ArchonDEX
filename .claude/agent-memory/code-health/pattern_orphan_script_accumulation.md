---
name: pattern-orphan-script-accumulation
description: scripts/ is the #1 debt sink — one-off T-xxx harnesses are never archived despite the "archive never delete" rule; ~132/170 imported by nothing; self-contained import webs archive as a unit
metadata:
  type: project
---

`scripts/` is this project's largest debt accumulator: 171 .py files, ~42K LOC,
larger than all engines combined. The dominant form is the **one-off `T-xxx`
harness** — a script written to answer one measurement/campaign question, run once,
then left in place (the "archive never delete" rule is consistently violated for
research scripts specifically; engines/core/backtester stay clean).

**Why:** every task in TASK_LEDGER that needs a backtest/sweep/analysis spawns a
`scripts/<verb>_<thing>_tNNN.py`. They are entrypoints (run via `python -m`), so
nothing imports them → orphan-by-construction → invisible to import-based dead-code
tools → never cleaned. As of 2026-06-18: 67 T-pattern scripts = ~14K LOC, 64 of them
imported-by-nothing-live.

**How to apply:** (1) The T-xxx naming convention makes them trivially enumerable:
`ls scripts/*t[0-9]*.py`. (2) They form **self-contained import webs** (e.g. the
managed-futures/sleeve cluster: `sleeve_phase0_verdict` ← `managed_futures_*`,
`run_diversified_futures_trend`, etc.) — these archive together as a unit, not file
by file. (3) Cross-check status against TASK_LEDGER: a CLOSED/refuted/H0 task's
scripts are safe; a `dispatched`/in-flight task's scripts (and the director's
current operational tools) are KEEP even if orphaned. (4) The legitimate KEEP carve-
outs are small: scripts documented as current CLI in execution_manual.md, scripts
that build a data panel live engine code depends on the OUTPUT of, and this-week
operational tools. See [[pattern-archive-verification-string-vs-import]] and the
duplicate-orchestrator pattern [[pattern_duplicate_orchestrators]] (same root cause:
build-next-to rather than refactor/retire).
