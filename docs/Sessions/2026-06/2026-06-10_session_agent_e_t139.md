# Session Summary: 2026-06-10 (Agent E — T-139)

## What was worked on

- **Agent E bootstrap** (first session of the 5th worker, deployment-
  engineering lane) + **T-139**: Carver dynamic optimization — the
  integer-position layer for small accounts, implemented as an Engine C
  post-processor behind `dynamic_optimization_enabled=False`.
- Studied the pysystemtrade source (`systems/provided/
  dynamic_small_system_optimise/` — it moved from `sysquant/optimisation/`
  exactly as the brief warned), ported the concept (greedy TE-std
  minimizer + shadow-cost penalty + TE buffer/speed control), wired it
  into `PortfolioEngine.compute_target_allocations`, tested it (258 new
  tests), proved OFF-inertness, and ran the $5K/$50K fixture
  demonstration.

## What was decided

- **Engine-C-side integerization, zero Engine B edits**: the optimizer
  emits integer-feasible weights `(n_i ± 1e-6 shares)·p_i/equity`; the
  directional nudge makes Engine B Path A's `int(delta/price)`
  truncation land exactly on the chosen integers (property-tested).
- **Two robustness extensions over the source, both documented**:
  multi-start (zero + feasible naive book → dominance over production
  naive rounding is by-construction) and a bidirectional ±1-share
  sign-preserving polish (escapes toward-target-only stalls in
  correlated books). Zero-start-only greedy — the faithful port — LOST
  to naive truncation on 14/20 random books; see lessons_learned.
- **TE as std, not variance**: the brief's spec said `(w−w*)'Σ(w−w*)`;
  the source uses `sqrt(·)` + linear costs. Source is the authority per
  the brief — ported the std form.
- **Covariance reuse**: `HRPOptimizer._estimate_cov` (Ledoit-Wolf,
  sample fallback) — no new estimator.
- **Demo uses buffer=0**: the TE buffer is live trade-pacing, not part
  of the expressibility question the fixture answers.

## What was learned

- **Zero-start greedy loses to naive truncation under common-factor
  correlation** (full entry in `docs/State/lessons_learned.md`):
  reference heuristics encode their asset class's geometry; when a
  property must hold vs a production baseline, make the baseline a
  search start so the guarantee is structural.
- **Share count is the wrong cost metric** across a 5–500 price range —
  the cost penalty suppresses traded weight, not trade count; the
  monotonicity property only holds (and only should hold) in weight.
- 5 full-suite test failures are **pre-existing on origin/main**
  (verified by `git stash` re-run): `test_cockpit_metrics_alignment`,
  `test_discovery_gate1_caching`, `test_oos_validation_isolation_default`,
  `test_validate_candidate_v2` ×2. Flagged to director.

## Pick up next time

- T-139 is DONE pending director merge. The user-gated enabling path is
  in the audit doc (`docs/Audit/dynamic_optimization_t139_2026_06_10.md`):
  one config key + a deployment-tier-capital A/B (cloud cells at
  `--override-capital 5000`-class, image rebuild via
  `scripts/build_backtest_image.sh` after merge).
- If dyn-opt heads to prod: Engine B `rebalance_tolerance` composition
  (it double-suppresses small optimizer trades) is a propose-first
  follow-up; non-unit Path A multipliers (vol scalar, kill switch,
  regime overlay) rescale the integer-feasible weights — re-run the
  optimizer post-multiplier if those features arm together.

## Files touched

```
config/portfolio_settings.json
docs/Audit/dynamic_optimization_t139_2026_06_10.md
docs/Core/execution_manual.md
docs/State/lessons_learned.md
engines/engine_c_portfolio/dynamic_optimizer.py        (new)
engines/engine_c_portfolio/policy.py
engines/engine_c_portfolio/portfolio_engine.py
engines/*/index.md + orchestration/scripts/data_manager index.md (sync_docs regen)
scripts/demo_dynamic_optimization_t139.py              (new)
scripts/t139_fixture_data.py                           (new)
tests/test_engine_c_dynamic_optimizer.py               (new)
```

## Subagents invoked

- `Explore` (very thorough) — Engine C wiring map. Mostly excellent
  (found the insertion point, config filter pattern, HRP estimator,
  T-111/T-118 canon procedure); one fabrication caught: it asserted
  `compute_target_allocations` call sites/line numbers in a
  "BacktestController" flow without a path — the real call site was
  verified by hand grep (`backtester/backtest_controller.py:539`).
  Lesson: treat agent file:line claims as leads, verify load-bearing
  ones directly.
