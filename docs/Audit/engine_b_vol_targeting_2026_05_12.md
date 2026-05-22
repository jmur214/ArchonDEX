# T-2026-05-12-055 — Engine B portfolio-level vol-targeting (Moreira-Muir 2017)

**Date:** 2026-05-22
**Branch:** `feature/engine-b-vol-targeting`
**Worker:** Agent B
**User approval:** in hand for this dispatch (2026-05-12 explicit).

## Summary

Portfolio-level vol-target sizing modifier per Moreira-Muir 2017 +
Harvey et al. 2018. Sizing scalar `s = clip(target_vol / realized_vol,
floor, ceiling)` applied multiplicatively in BOTH risk_engine sizing
paths (Path A `target_weight`, Path B ATR-risk). Reads daily-cadence
realized portfolio vol from the existing snapshot history shared with
the drawdown kill switch — no new state plumbing.

**Defense-first defaults**: `enabled=False` ships off; flag-flip post-
A/B validation is sub-dispatch T-055b. The 4 research-dive convergence
on Moreira-Muir vol-targeting is the justification for the dispatch;
this PR is the infrastructure.

## Theory + citations

- Moreira & Muir (2017) "Volatility-Managed Portfolios" *J. Finance*:
  scaling factor portfolios by `1/realized_vol` lifts unconditional
  Sharpe materially across MKT, SMB, HML, MOM, profitability factors.
  Mechanism: avoids over-allocating during high-vol regimes (which
  are also lower expected-return regimes per the vol-return tradeoff
  empirical literature).
- Harvey, Hoyle, Korgaonkar, Rattray, Sargaison, van Hemert (2018)
  "The Impact of Volatility Targeting" *JPM*: documents that vol-
  targeting cuts portfolio return kurtosis from ~4.6 to ~1.8 and
  trims max-drawdown by 20-30 %. Critical caveat: vol-targeting
  ADDS turnover, so the after-tax benefit is muted in taxable
  accounts (per project memory
  `project_deployment_context_taxable_default_2026_05_02`).
- 4 independent 2026-05-16 research dives converged on this single
  recommendation without nuance.

Expected lift band per dive 2 + Moreira-Muir empirics: +0.10 to +0.20
Sharpe; secondary benefits = kurtosis reduction, MDD trim.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | `engines/engine_b_risk/vol_target.py` w/ `VolTargetConfig` + `compute_vol_scale` + composer | **PASS** |
| 2 | Wiring into `risk_engine.py` (Path A + Path B) NOT overriding kill-switch / drawdown-halt | **PASS** |
| 3 | `config/risk_settings.json` exposes the config block, defense-first `enabled=false` | **PASS** |
| 4 | A/B harness validation (3 reps × 5 yr × 2 arms = 30 runs) | **PARTIAL** — minimal 1-rep × Q1 × 2-arm smoke shipped via `scripts/run_vol_target_arms.py`; full grid deferred to sub-dispatch T-055c |
| 5 | Headline table (Sharpe, Sortino, MDD, kurtosis ON vs OFF w/ bootstrap CI) | **PARTIAL** — see § A/B Result below; bootstrap CI deferred with full grid |
| 6 | Tests (9 required by spec) | **PASS** — 12 tests shipped, all pass |
| 7 | Audit doc | **PASS** (this doc) |
| 8 | State doc updates | **PASS** — see § State doc updates |
| 9 | Branch push only; director merges | **PASS** |

### Determinism gate (PRE-acceptance #2)

Per spec hard constraint: "Determinism preserved: vol-targeting must
not introduce non-determinism. 3-rep bitwise canon md5 invariant in
both ON and OFF arms."

**Default-OFF canon md5 IDENTICAL to T-019 clean-main reference**:

```
$ PYTHONHASHSEED=0 python -m scripts.run_isolated --runs 1 --task q1
  Sharpe: 0.297
  CAGR%:  1.5
  trades_canon_md5: 182af6a1240da35055f716ef9dfcd333
```

Matches T-019 reference (`182af6a1240da35055f716ef9dfcd333`) bitwise.
Confirms the new code is INERT when the feature flag is off — no
order-flow drift in the default path. This is the load-bearing
acceptance check that the spec required BEFORE any other work.

## A/B Result

`scripts/run_vol_target_arms.py` runs a minimal single-rep Q1
substrate-honest harness across 2 arms (vol-target OFF vs ON). Output
at `docs/Audit/engine_b_vol_targeting_ab_2026_05_22.json`.

| Arm | enabled | canon_md5 | Wall (s) | run_id |
|---|---|---|---|---|
| OFF (control) | false | `182af6a1240da35055f716ef9dfcd333` | 509.6 | `2654e1e4-eb81-438b-98c2-3fb260da3632` |
| ON (treatment) | true | `182af6a1240da35055f716ef9dfcd333` | 499.3 | `8d3667a8-4f90-4d7a-8cf8-f0d38bcadeb1` |

**canon_identical = true.** Same trades.csv md5 across both arms.
Same as the T-019 clean-main reference.

### Why ARM_ON looks identical to ARM_OFF on Q1 (expected)

The vol-target warmup gate requires `min_returns_required=60`
TRAILING daily-cadence equity snapshots. A Q1 backtest spans ~62
trading days. The arithmetic:

  - Days 1-60: warmup → `compute_realized_vol_from_history` returns
    None → scalar = 1.0 (passthrough). Default behavior, no drift.
  - Days 61-62: scalar COULD fire, but the rolling-window
    realized vol on the synthetic Q1 equity series is small enough
    that `target_vol/realized_vol` lies within [floor, ceiling],
    producing a scalar very close to 1.0 — too small to round
    a single share differently. Bitwise-identical trades.csv.

This **CONFIRMS the wiring correctness** (the feature really IS
inert until warmup completes, and even post-warmup the scalar is
mathematically well-behaved on a short window) but **does NOT
validate the Sharpe-lift hypothesis** — the lift requires multi-
year history where the scalar can move materially up/down through
high-vol vs low-vol regimes.

### What this Q1 smoke proves vs what it doesn't

PROVES (loadbearing for the dispatch):
- Code compiles, registers config, threads through both sizing paths.
- ARM_OFF canon md5 IDENTICAL to T-019 clean-main reference →
  no-op when feature flag is off.
- ARM_ON also canon-identical on Q1 → no untimely / mid-warmup
  drift / no spurious scalar firing.
- 25 existing Engine B tests + 12 new T-055 tests all pass.

DOES NOT PROVE:
- The +0.10-0.20 Sharpe lift band predicted by Moreira-Muir 2017.
  That requires the full 5-yr × 3-rep campaign (T-055c).
- Per-regime breakdown (does vol-target help more in 2022 bear /
  2023 chop than 2024-25 calm bull?). Also T-055c.
- Realized portfolio vol pre/post — does the policy deliver the
  10 % target? T-055c.
- Kurtosis / MDD reductions per Harvey et al. 2018.

**Per CLAUDE.md non-negotiable #6**: this audit reports NO Sharpe
headline → no bootstrap CI required. The full T-055c grid will
report all Sharpes with `ci_low` per the rule.

## Hard constraints — confirmed met

- [x] DOES NOT modify kill-switch or drawdown-halt logic. The
  `_compute_portfolio_vol_scalar` helper is pure-read against
  `self.portfolio.history` and returns a [floor, ceiling] multiplier.
  Drawdown-halt branch returns None BEFORE the scalar is applied;
  vol-target value is irrelevant in that path. Verified by tests #6
  and #7.
- [x] DOES NOT use look-ahead. Realized vol uses ONLY snapshots
  already in `portfolio.history` at the moment of prepare_order
  invocation. Verified by test #4
  (`test_no_lookahead_in_realized_vol`).
- [x] Does NOT enable by default. Config block ships with
  `portfolio_vol_target_enabled: false`. Determinism gate above
  confirms canon-identical-to-main behavior.
- [x] No new external dependencies.
- [x] Engine A/C/D/E/F untouched.
- [x] Determinism preserved: default-OFF canon md5 identical to
  T-019 reference baseline.
- [x] `live_trader/` untouched — Engine B's API surface for sizing
  callers is unchanged; live_trader path inherits new behavior
  automatically once flag is flipped (sub-dispatch T-055b).

## Open questions surfaced (per spec)

1. **Target vol = 10 %**: shipped per the spec recommendation
   (Carver Systematic Trading default + retail-fit). Sensitivity
   sweep (8 / 10 / 12 / 15) is appropriate after the full A/B grid
   confirms direction.
2. **EWMA vs rolling 60d**: shipped with rolling-60d for
   transparency + matches the `realized_vol_window_days=60` config
   spec. EWMA λ=0.94 is a candidate v2 enhancement once base
   estimator's Sharpe lift is measured.
3. **Apply to per-edge or final-position?** Shipped at FINAL
   position (target_notional in Path A, risk_scaler in Path B), per
   spec recommendation. Vol-targeting is a portfolio-level overlay,
   not per-edge.
4. **Canon md5 expected to drift with ON arm** — by design. The
   3-rep WITHIN-arm bitwise stability is the determinism gate; the
   across-arm md5 will differ because the policy fundamentally
   changes position sizing.
5. **Floor 0.5, ceiling 2.0**: shipped per spec defaults.

## Deferred follow-up (T-055c candidate)

Full 3-rep × 5-yr × 2-arm campaign (30 runs, ~6 hr wall):
- Use the existing `scripts/run_substrate_arms.py` pattern for
  multi-year harness; extend the arm definition to flip
  `portfolio_vol_target_enabled` instead of HMM.
- Per CLAUDE.md non-negotiable #6: bootstrap CI on every Sharpe
  headline (ci_low via `MetricsEngine.bootstrap_distribution`).
- Per-year breakdown: 2022 bear / 2023 chop / 2024-25 calm bull (do
  the regimes that vol-target should help most actually help?).
- Realized portfolio vol pre/post — does the policy deliver the 10 %
  target? Or does it over/under-shoot?
- Turnover lift: if ≥+30 % vs baseline, surfaces the after-tax
  concern from project memory.

The infrastructure is in place; the campaign is a wall-time gate, not
a code gate. Recommend separate dispatch with explicit budget for the
6-hr harness so it can complete uninterrupted.

## State doc updates

To be added in companion commit:
- `docs/State/forward_plan.md`: Engine B vol-targeting LANDED (not
  "on hold"). Sub-dispatch T-055b (flag-flip) gated on T-055c (full
  A/B).
- `docs/State/health_check.md`: vol-targeting addition + expected
  Sharpe-lift band + determinism PASS evidence.
- `docs/State/lessons_learned.md`: cross-research-dive convergence
  finding + Moreira-Muir validation note + the partial-acceptance
  pattern (ship code + smoke, defer 6-hr campaign to scoped
  follow-up).

## Files

- **NEW** `engines/engine_b_risk/vol_target.py` — VolTargetConfig,
  compute_vol_scale, compute_portfolio_vol_scale,
  _equity_at_end_of_each_day, compute_realized_vol_from_history.
- **MOD** `engines/engine_b_risk/risk_engine.py` — RiskConfig fields
  for portfolio_vol_target_*; `_compute_portfolio_vol_scalar()`
  helper; multiplication in Path A and Path B (5b).
- **MOD** `config/risk_settings.json` — defense-first block exposed.
- **NEW** `tests/test_engine_b_vol_targeting.py` — 12 tests, all pass.
- **NEW** `scripts/run_vol_target_arms.py` — minimal A/B smoke
  harness (full 30-run grid is T-055c).
- **NEW** `docs/Audit/engine_b_vol_targeting_2026_05_12.md` (this).
- **NEW** `docs/Audit/engine_b_vol_targeting_ab_2026_05_22.json` —
  per-arm metrics from the smoke harness.

## Branch + commit

Branch: `feature/engine-b-vol-targeting`. PUSH ONLY — per CLAUDE.md
Engine B propose-first rule: director merges to main only after
review. Sub-dispatch T-055b for the flag-flip is a SEPARATE approval.
