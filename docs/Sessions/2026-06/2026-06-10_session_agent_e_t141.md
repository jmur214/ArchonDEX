# Session Summary: 2026-06-10 (Agent E — T-141, second task)

## What was worked on

- **T-141**: after-tax Sharpe gate (reporting, not enforcement) +
  Roth/taxable account router. Same-day follow-on to T-139 in the
  deployment-engineering lane.

## What was decided

- **Repoint over rebuild**: `backtester/tax_drag_model.py` already held
  the complete after-tax engine (FIFO/ST-LT/wash-sale/carry-forward),
  unwired into any metric since 2026-05-02. T-141 added state rates +
  a report-only composition module + producer fields instead of a new
  tax engine.
- **Report-only contract**: the new fields compute from a LOCAL
  enabled copy; `tax_drag_model.enabled` stays the canon-changing
  equity-mutation switch and is never consulted by reporting. Canon
  untouched.
- **Single-producer extension**: both `performance_summary.json`
  writers flow through `PerformanceMetrics.summary()`, so the fields
  were added once in `_compute_summary` + `PRODUCER_SUMMARY_KEYS`
  atomically (T-091 pattern).
- **CI-aware routing rule**: RULE A clears on `ci_low > 0`; a bare
  point estimate only downgrades the violation to a warning — the
  CLAUDE.md kill-threshold discipline applied to account routing.
- **Kept the ≥365-day LT boundary** (pre-existing, technically
  optimistic vs the IRS "more than one year") — changing it would alter
  enabled=True results beyond an additive task's scope; documented.

## What was learned

- **Wash-sale scan blindness** (full entry in lessons_learned.md): the
  model indexed re-opens from realized lots only — repurchases still
  held at run end were invisible, understating drag against the
  module's documented conservative intent. Fixed via an open-event log;
  dormant since May because nothing ever read the model's output. A
  default-OFF capability nothing reads is unaudited code.
- The demonstration number is decisive: 2024 6-edge book pre-tax
  Sharpe 0.991 / CAGR +5.66% → after-tax (taxable-IL) **−0.658 /
  −13.34%** — the $18.9K tax bill exceeds the $5.7K profit (845 lots,
  100% ST, $27.7K wash-sale-disallowed). Confirms the 2026-05-02
  finding on the current substrate; the taxable-vs-Roth routing
  decision is now a measured quantity, not a vibe.

## Pick up next time

- T-141 done pending director merge. Later user-gated steps (in the
  audit doc): gate ENFORCEMENT in the deploy-decision path (needs the
  multi-year after-tax number — re-run `python -m
  scripts.demo_after_tax_t141 <run_dir>` on a 12/26-yr run dir when one
  is on disk); router enforcement wiring at the paper-trading milestone
  (Engine B / live_trader, propose-first).

## Files touched

```
backtester/tax_drag_model.py          (state rates + wash-sale fix)
backtester/after_tax_metrics.py       (new)
cockpit/metrics.py                    (producer fields)
config/backtest_settings.json         (IL state rates)
core/account_router.py                (new)
config/account_routing.json           (new)
tests/test_after_tax_t141.py          (new, 36 tests)
tests/test_contracts.py               (PRODUCER_SUMMARY_KEYS)
scripts/demo_after_tax_t141.py        (new)
docs/Audit/after_tax_gate_t141_2026_06_10.md (new)
docs/Core/execution_manual.md, docs/State/lessons_learned.md
```

## Subagents invoked

- None this task — recon was a handful of targeted greps (the T-139
  lesson about verifying load-bearing claims directly made direct recon
  cheaper than delegation for this scope).
