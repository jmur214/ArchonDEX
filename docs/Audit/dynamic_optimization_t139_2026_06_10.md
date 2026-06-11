---
task_id: T-2026-06-10-139
title: Carver dynamic optimization for small accounts — the integer-position layer (Engine C, default-OFF)
date: 2026-06-10
substrate: n/a (engineering wiring + frozen-fixture verification; no backtest measurement)
scope: Engine C post-processor behind a default-OFF flag — NO prod-default change; enabling is a separate user-gated step
outcome: **Delivered.** (1) Greedy integer-position optimizer (pysystemtrade concept port + 2 documented robustness extensions) wired as an Engine C post-processing stage behind `dynamic_optimization_enabled=False`. (2) OFF canon-md5 BITWISE-identical to same-worktree pre-change baseline (`5d88e1a0…`), determinism 3/3. (3) 258 new tests green (greedy units + property batteries + fail-open + wiring inertness). (4) Fixture headline: **at $5K, naive rounding leaves 2.87% annualized tracking error vs the ideal book; dynamic optimization cuts it to 1.01% — 64.7% of the rounding-induced TE recovered for 3 extra shares.** No N_trials consumed.
---

# T-139 — Carver Dynamic Optimization (integer-position layer)

## Headline

At $5K capital the production book cannot be expressed in whole shares:
naive truncation (what Engine B's Path A does today) leaves **2.87%
annualized tracking error** against the unrounded target and deploys
only **82.2%** of intended gross (truncation always rounds toward
zero). The dynamic optimizer cuts that to **1.01% TE / 96.2% gross** —
**64.7% of the rounding-induced tracking error recovered** — by
spending 3 extra one-share trades where they best close the joint
(covariance-weighted) gap. At $50K the same comparison is 0.31% → 0.08%
(75.3%): the naive penalty at $5K is **~9× the $50K penalty**, which is
exactly the small-account bind two independent external research passes
ranked as our single highest-EV missing technique (system research Q3;
blind-spots §4).

**This is an engineering verification on a frozen fixture, NOT a
performance claim. No backtest was run; no N_trials were consumed.**
The flag ships OFF; production behavior is bitwise-unchanged.

## What was built

### The algorithm (`engines/engine_c_portfolio/dynamic_optimizer.py`)

Concept port of pysystemtrade's dynamic optimization
(`systems/provided/dynamic_small_system_optimise/` — the module moved
from `sysquant/optimisation/` as our notes anticipated; source tree
grepped per the brief, AFTS book tables NOT relied on). Faithful core,
verified against source:

- **Weight-space formulation**: per-share value `price/equity` plays
  pysystemtrade's per-contract value.
- **Objective** (`objectiveFunctionForGreedy.evaluate`):
  `sqrt((w−w*)' Σ (w−w*)) + shadow_cost · Σ c_i·|w_i − w_prior_i|` —
  tracking error as an annualized **std** (NOT the variance form in the
  brief's spec — the source is the authority per the brief), costs
  linear in the weight-space trade gap vs the prior book.
- **Greedy walk** (`greedy_algo_across_integer_values`): step one share
  at a time, only in the direction of the unrounded optimal, accept the
  single best objective-reducing step per round, stop when none
  improves; per-asset min/max bounds with `at_limit` bookkeeping.
- **Speed control** (`buffering.py`): if TE(prior vs optimal) <
  `tracking_error_buffer` → no trades; otherwise the trade is scaled by
  `(TE−buffer)/TE` and re-rounded in share space.
- **Defaults**: `shadow_cost=10`, `tracking_error_buffer=0.02` (the
  source's production values; its dataclass literals are accidental
  1-tuples `(10,)` that never bind — noted for the record).

**Deviations from source (each deliberate, all in the module docstring):**

1. **Multi-start**: the walk runs from zero (source-faithful) AND from
   the production naive-truncation book when feasible; better final
   objective wins. Found empirically necessary: zero-start greedy
   LOSES to naive truncation on 14/20 seeded random books under strong
   common-factor correlation (single steps stall in the factor valley).
   With multi-start, dominance over the production baseline is
   guaranteed by construction whenever naive is feasible.
2. **Bidirectional ±1-share polish** after each walk (sign-preserving,
   bounds-respecting, strict-improvement): escapes toward-target-only
   stalls — e.g. overweighting one name to compensate an unreachable
   underweight in a correlated sibling, which is precisely the
   diversification-recovery behavior wanted at $5K.
3. **Flat per-trade cost** (`cost_per_trade_bps`, default 10 = the
   existing `turnover_flat_cost_bps` convention) instead of
   per-instrument cost estimates — liquid US equities at sub-ADV size.
4. **Hard gross buying-power bound** `Σ|w| ≤ buying_power_fraction`
   (default 1.0) as step feasibility, replacing the source's optional
   constraint-function machinery.
5. **Fail-open, not fail-loud**: negative TE variance (non-PSD Σ corner)
   or any unoptimizable input degrades to pass-through / keep-prior
   (no-trade is the conservative direction; engines must degrade
   gracefully). The source raises. Tolerance guards per the T-061/T-065
   discipline (`< -1e-10` fails open; tiny negatives clamp to 0).

### The wiring (Engine C only)

`PortfolioEngine.compute_target_allocations`
(`engines/engine_c_portfolio/portfolio_engine.py`) post-processes the
allocator's weights when the flag is ON:

```
weights = policy.allocate(...)                      # unchanged
if cfg.dynamic_optimization_enabled and weights:    # default False
    weights = self._apply_dynamic_optimization(weights, price_data, equity)
self.current_target_weights = weights               # unchanged
```

- Runs AFTER all policy overlays (vol target, exposure cap) — the last
  Engine C stage before Engine B consumes `target_weights`.
- **Covariance reuses `HRPOptimizer._estimate_cov`** (Ledoit-Wolf with
  sample-cov fallback, 60-bar lookback) — the existing portfolio-level
  estimator, as the brief required. No new estimator introduced.
- Prices = last Close of the same `price_data` slice Engine B sizes
  from (verified: `risk_engine.py:855` uses the bar's Close).
- Current integer positions from `self.positions`; equity = the same
  value Engine B receives this bar.
- The optimizer module is **lazy-imported inside the ON branch** — the
  OFF path never imports it (asserted in tests).

**Engine B contract (zero Engine B edits).** Output weights are
integer-feasible: `w_i = (n_i ± 1e-6 shares)·p_i/equity`. Engine B
Path A computes `add_qty = int(delta_notional/price)`, truncation
toward zero; the directional nudge keeps the FP quotient strictly on
the far side of the intended integer, so Path A lands exactly on
`n_i − cur_i`. Property-tested across seeded books
(`test_engine_b_truncation_parity`).

### Flag + config

`PortfolioPolicyConfig` (`engines/engine_c_portfolio/policy.py`):
`dynamic_optimization_enabled: bool = False` + 7 `dynopt_*` tunables
(shadow cost, cost bps, TE buffer, buying-power fraction, per-asset
cap, cov lookback, Ledoit-Wolf toggle). Mirrored as explicit `false` /
defaults in `config/portfolio_settings.json` (both construction sites —
`mode_controller.py:584` and `run_backtest_pure.py:456` — filter JSON
keys to dataclass fields, so the flag flows everywhere from one place).

## Proofs

### Proof 1 — OFF inertness (canon bitwise + determinism)

Same worktree, same 2024 cell (`PYTHONHASHSEED=0 python -m
scripts.run_isolated --runs 3 --year 2024`), T-120-precedent procedure:

| State | Sharpe | trades canon md5 | Determinism |
|---|---:|---|---|
| Pre-change baseline (origin/main 56bb693) | 0.991 | `5d88e1a0f70f0cd052a7813a6e40b1a9` | 3/3 bitwise |
| Post-change, flag OFF (default) | 0.991 | `5d88e1a0f70f0cd052a7813a6e40b1a9` | 3/3 bitwise |

(The T-099/T-120-era reference `b6137649…`/0.86 belongs to an older
main; the valid comparison is same-worktree pre/post, run fresh both
sides.)

### Proof 2 — ON path fires (functional smoke)

Flag flipped ON in `portfolio_settings.json` for one 2024-cell run,
then reverted (config diff vs HEAD verified zero afterward):

| State | Sharpe | trades canon md5 |
|---|---:|---|
| OFF (default) | 0.991 | `5d88e1a0f70f0cd052a7813a6e40b1a9` |
| ON (2024 cell, $100K default capital) | 1.188 | `4c097deb4f476e56a1d11c5d64436493` |

The ON canon **differs** — the flag actually changes trades — and the
run completes end-to-end without errors. **The single-cell Sharpe delta
(0.991 → 1.188) is NOT improvement evidence**: one year, one cell, no
bootstrap CI, $100K capital where integer effects are incidental
(T-120's ON smoke showed the same class of meaningless single-cell
delta). Functional proof only; the A/B that could justify enabling is
the user-gated step described below.

### Proof 3 — test suite

- **258 new tests green** (`tests/test_engine_c_dynamic_optimizer.py`):
  hand-computable greedy cases; property batteries over seeded random
  books — scale invariance (2× capital ⇒ TE non-increasing, 40/40),
  cost-penalty monotonicity in traded WEIGHT (share counts are the
  wrong metric when prices span 5–500; adjacent levels get a
  one-max-share path-dependence tolerance, endpoints strict),
  never-exceeds-buying-power (80/80 across fractions), Engine-B
  truncation parity (40/40), determinism (repeat calls + input-dict-
  order invariance), fail-open battery, wiring inertness (flag OFF ⇒
  identical weights AND optimizer module never imported).
- Full suite: **2124 passed**; 5 failures verified PRE-EXISTING on
  origin/main via `git stash` re-run (`test_cockpit_metrics_alignment`,
  `test_discovery_gate1_caching`, `test_oos_validation_isolation_default`,
  `test_validate_candidate_v2` ×2) — flagged to director, not T-139
  scope.

### Proof 4 — the fixture demonstration

`python -m scripts.demo_dynamic_optimization_t139` — frozen 8-name
fixture (real closes from the canonical cache, pinned 2024-05-10,
EMBEDDED in `scripts/t139_fixture_data.py` so the demo reproduces
bitwise with zero data dependency). Target weights from the production
adaptive formula (inverse-vol, 0.30 cap); Σ from the reused Ledoit-Wolf
estimator; naive baseline = production truncation semantics.

| capital | TE naive | TE dyn-opt | TE recovered | trades naive | trades dyn-opt | gross naive | gross dyn-opt |
|---|---|---|---|---|---|---|---|
| $5,000 | 2.8696% | 1.0136% | **64.7%** | 26 | 29 | 82.2% | 96.2% |
| $50,000 | 0.3131% | 0.0774% | **75.3%** | 297 | 301 | 98.2% | 99.8% |

Position-level view at $5K (ideal → naive → dyn-opt): AAPL 2.85 → 2 →
**3**, MSFT 1.83 → 1 → **2**, XOM 8.89 → 8 → **9**, others unchanged —
the optimizer spends its 3 extra shares on the under-deployed names
that most reduce the covariance-weighted gap, instead of uniformly
flooring.

`tracking_error_buffer=0` in the demo (from-flat construction
comparison; the buffer is a live trade-pacing feature, not part of the
expressibility question).

## What enabling would require (the user-gate path)

1. **Decision gate (user/director):** flip
   `dynamic_optimization_enabled: true` in
   `config/portfolio_settings.json` — one key; everything else ships.
2. **Before any prod flip, run the integrated A/B** the T-120 pattern
   requires: OFF vs ON on the multi-year window under bootstrap CI
   (cloud campaign; the cloud image needs this branch — rebuild via
   `scripts/build_backtest_image.sh` ONLY). NOTE: at the backtest's
   default $100K capital the integer effect is small by construction;
   the A/B that matters is `--override-capital 5000`-class cells
   (deployment-tier capital), or the flip decision can be made on
   engineering grounds (the fixture evidence + inertness) for the
   paper-trading tier first.
3. **Known composition caveats (documented, acceptable, all
   trade-reducing):**
   - Engine B's `rebalance_tolerance` (5%) may skip optimizer
     adjustments smaller than 5% of a position's target — a final
     trade-suppressor on top of the optimizer's own buffer. If dyn-opt
     becomes the prod path, consider (separate, propose-first Engine B
     change) lowering it, since the optimizer already nets cost-vs-TE.
   - Path A multiplier chain (optimizer_weight, vol scalar, kill-switch
     de-gross, advisory scalar, regime overlay) is 1.0 under default
     config; a non-unit multiplier rescales the integer-feasible
     weights (Engine B then truncates to a *different* integer book —
     still safe, no longer the optimizer's exact choice). If any
     multiplier feature is armed together with dyn-opt, the optimizer
     should be re-run on the post-multiplier targets (future wiring
     decision, Engine B coordination required).
   - Fractional-share execution would obviate this layer at the $5K
     tier, but the OPG/CLS auction-order execution path (the
     research-recommended default for daily signals) is whole-share
     only — dynamic optimization is what makes OPG/CLS usable at $5K.

## Files

- `engines/engine_c_portfolio/dynamic_optimizer.py` — NEW; the optimizer
- `engines/engine_c_portfolio/policy.py` — flag + 7 dynopt_* fields (default OFF)
- `engines/engine_c_portfolio/portfolio_engine.py` — post-processing branch + `_apply_dynamic_optimization`
- `config/portfolio_settings.json` — flag block (false) + tunables
- `tests/test_engine_c_dynamic_optimizer.py` — NEW; 258 tests
- `scripts/demo_dynamic_optimization_t139.py` + `scripts/t139_fixture_data.py` — NEW; the fixture demonstration
- this audit

## NOT done (out of T-139 scope)

- Production-default flag flip (user-gated; see path above)
- Integrated multi-year ON A/B (cloud campaign; needs image rebuild)
- Engine B `rebalance_tolerance` composition change (propose-first)
- Per-instrument cost estimates (flat bps is the project standard)
- ON-path determinism beyond the single-cell smoke (verify on longer
  cells before any prod consideration — T-120 precedent)
