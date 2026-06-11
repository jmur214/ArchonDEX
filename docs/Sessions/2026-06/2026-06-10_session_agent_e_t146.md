# Session Summary: 2026-06-10 (Agent E — T-146, fourth task)

## What was worked on

- **T-146**: OPG/CLS auction-execution convention in the backtest
  execution simulator (`auction_execution: off|moo|moc|moo_moc`,
  default off = legacy bitwise) + per-fill Δcost accounting on the real
  2024 book + the live-side design one-pager (live_trader untouched).

## What was decided

- **Auction fills = official auction print + adverse safety bps, no
  spread/impact model**; regulatory fees (AlpacaFees SEC+TAF) reused
  unchanged in both conventions. Intrabar stop/TP fills are not auction
  orders — slippage-priced in every mode.
- **moo_moc routes entries→open auction, exits→close auction**, with
  the timing-semantics caveat documented (close-auction fills add a day
  of drift — mode choice is a strategy decision; `moo` is the
  conservative timing-identical default).
- The Δcost headline is reported against BOTH the prod realistic model
  (the honest comparison) and the legacy fixed-10bp scenario — see
  lesson below.

## What was learned

- **The ON smoke caught the silent-mismatch family AGAIN**: the first
  end-to-end smoke returned the baseline canon — `run_backtest` builds
  a LOCAL exec_params dict (not `self.exec_params` from `__init__`),
  so the auction keys never reached the simulator; 36 unit tests
  couldn't see it. The flag-ON-must-change-canon smoke is the only test
  class that catches consuming-site misses — now a standard step
  (lessons_learned addendum).
- **The research "free lunch" partially replicated our own cost model**
  (full entry in lessons_learned.md): the realistic slippage model
  already prices mega-caps at 1bp ≈ auction reality, so the honest
  saving is ~$306/yr ≈ 30bps of equity/yr (mid-bucket + impact), not
  the ~235bps/yr a fixed-10bp baseline suggests. The convention's real
  value is killing the live-vs-backtest fill-mechanism divergence.
- The constraint most likely to bite live: the **9:28 ET OPG submission
  cutoff** — a hard scheduling dependency the current daily loop
  doesn't have, with an explicit degrade path needed (fall back to a
  tagged market-at-open or skip-and-log).
- Auction orders are whole-share-only → OPG/CLS live enablement is
  COUPLED to T-139's dynamic optimization (integer book), and the
  T-141 router makes order batching account-aware with the
  cross-account blackout check at the batch layer.

## Pick up next time

- T-146 done pending director merge (OFF canon proof + ON smoke
  numbers in the audit). Enabling = `auction_execution: "moo"` one-key
  flip (engineering-grounds decision; zero N_trials posture) when live
  goes auction; live-side implementation is an Engine B/live_trader
  propose-first item sequenced with paper trading.
- **T-143 follow-up for the director**: the crisis-replay harness
  constants predate T-118b ADDENDUM v3 (episode list locked by
  enumeration incl. 2010 + 2025-04; sign ≥6/7; ALL-3-OOS-must-improve)
  — a small sync dispatch is needed before the post-relaunch run.

## Files touched

```
backtester/execution_simulator.py     (auction modes + safety + helpers)
backtester/backtest_controller.py     (plumbing)
orchestration/mode_controller.py      (plumbing)
config/backtest_settings.json         (auction_execution off, safety 1.0)
tests/test_auction_execution_t146.py  (new, 36 tests)
scripts/demo_auction_execution_t146.py (new, Δcost accounting)
docs/Audit/auction_execution_t146_2026_06_10.md (new, incl. live one-pager)
docs/Core/execution_manual.md, docs/State/lessons_learned.md
```

## Subagents invoked

- None — single-file simulator change with config plumbing; direct
  implementation was the right altitude.
