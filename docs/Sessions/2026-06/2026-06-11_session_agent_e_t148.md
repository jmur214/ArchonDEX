# Session Summary: 2026-06-11 (Agent E — T-148, sixth task)

## What was worked on

- **T-148**: Carver position buffering (10% inertia, trade-to-edge) as
  an Engine C post-processor composing after T-139 dynamic
  optimization; default-OFF; the coupled turnover→cost→tax accounting
  via T-141's after-tax module.

## What was decided

- Trade-to-edge semantics with whole-share-aware edge rounding (edge
  rounds INTO the band; no-integer bands fall back to nearest-integer;
  zero target closes fully); output weights reuse the T-139 Engine-B
  truncation nudge.
- Composition order locked + tested: allocate → dyn-opt → buffering.
- The demo deliberately quotes NO Sharpe (single-cell); the
  pre-registered enable-A/B spec is in the audit (12/26-yr, primary
  f=0.10, ci_low-aware non-degradation + after-tax improvement + TE
  ceiling; Roth may rationally stay unbuffered).

## What was learned

- **Turnover levers are tax levers first** (lessons_learned.md):
  turnover ↓11% ⇒ cost ↓4.5 bps/yr but tax ↓130 bps/yr — the tax
  channel is ~29× the cost channel at our ST-heavy posture. Every
  execution proposal should be valued through the after-tax module
  before prioritization; the lever's value is account-dependent
  (router input).
- **T-098's failure mechanism partially carries even under
  trade-to-edge**: turnover fell 11%, not the research's 60-70% —
  daily vol-target moves still dominate dollar turnover; the
  edge-haircut takes only band/move off each. Stated plainly in the
  audit's differentiation table.

## Pick up next time

- T-148 done pending director merge. The enable decision rides the
  pre-registered A/B spec'd in the audit §"What a pre-registered
  enable-A/B would test" — needs director pre-registration before any
  cells.

## Files touched

```
engines/engine_c_portfolio/position_buffering.py   (new)
engines/engine_c_portfolio/policy.py               (2 fields)
engines/engine_c_portfolio/portfolio_engine.py     (branch + helper)
config/portfolio_settings.json                     (keys false/0.10)
tests/test_position_buffering_t148.py              (new, 43 tests)
scripts/demo_position_buffering_t148.py            (new)
docs/Audit/position_buffering_t148_2026_06_11.md   (new)
docs/Core/execution_manual.md, docs/State/lessons_learned.md
```

## Subagents invoked

- None — the T-139/T-141/T-146 patterns made this a composition task;
  direct implementation.
