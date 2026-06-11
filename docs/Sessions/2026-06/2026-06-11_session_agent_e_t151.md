# Session Summary: 2026-06-11 (Agent E — T-151, seventh task)

## What was worked on

- **T-151**: Bandy safe-f / CAR25 sizing governor, reporting-first —
  seed-deterministic block-MC module, additive summary fields (T-141
  pattern), per-account demonstration via the tax model.

## What was decided

- Bisection on a SINGLE pinned resample matrix (exceedance is monotone
  in f on fixed paths) — exact to f_tol, zero MC noise between
  iterations, and it makes the half-vol ⇒ 2× safe_f identity an EXACT
  test rather than a statistical one.
- All defaults documented as reconstructions (research flagged Bandy's
  exact parameters unverified); configurable via optional
  `safef_car25` config block.
- Reporting only; the sizing-enable path (deep-window number →
  pre-registered Engine B/C scalar policy → live-ops kill metric) is
  spec'd in the audit for the user gate.

## What was learned

- **The guard's own blind spot** (lessons_learned.md): the layer-2a
  contract scraper's non-greedy regex stopped at the first nested `}`
  — every producer key added after T-141's nested detail dict was
  invisible to the guard. Fixed with balanced-brace extraction.
  When a guard fails "backwards," suspect the guard's parser.
- **The per-account split is the demonstration**: Roth/pre-tax
  safe_f = 1.602 (+60% headroom) vs taxable-IL safe_f = 0.273
  (OVERSIZED 73%, CAR25 −5.47%/yr at the safe fraction) — the third
  independent indictment of taxable deployment at current turnover.
  Two caveats stated loudly: benign-single-year record (pre-tax number
  generous; 26-yr would bind far lower) and the year-end tax-lump ×
  resampling interaction (taxable magnitude conservative-side).

## Pick up next time

- T-151 done pending director merge. The deep-window safe_f needs a
  multi-decade run dir on disk (one command then). Quarterly tax
  cadence in the T-141 model is the noted tightening if this metric
  ever gates.

## Files touched

```
backtester/safef_car25.py             (new)
cockpit/metrics.py                    (_safef_report + 3 keys)
tests/test_contracts.py               (keys + scraper fix)
tests/test_safef_car25_t151.py        (new, 13 tests)
scripts/demo_safef_car25_t151.py      (new)
docs/Audit/safef_car25_t151_2026_06_11.md (new)
docs/Core/execution_manual.md, docs/State/lessons_learned.md
```

## Subagents invoked

- None.
