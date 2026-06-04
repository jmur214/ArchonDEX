---
task_id: T-2026-06-04-099
title: Long-window FP-determinism — close the residual cross-container summation drift (T-057c-det pass 3)
date: 2026-06-04
substrate: Stooq+Alpaca merged (post-T-082b)
scope: Engine A (signal_collector) + Engine C (portfolio_engine) + backtester (backtest_controller) — autonomous; no Engine B / live_trader changes
outcome: 5 load-bearing sites fixed; canonical-value INERT (Sharpe 0.86 / canon_md5 unchanged pre/post on 2024 cell); single-container --runs 3 PASS; hash-seed-invariance PASS; cross-container cloud verify deferred to image rebuild (separate dispatch)
---

# T-099 — Long-Window FP-Determinism (T-057c-det pass 3)

## Headline

Fixed **5 load-bearing order-dependent FP-summation sites** on the live
arm0_off backtest path that T-057c-det + T-057c-followup left
unaddressed. Each site mirrors the canonical bug class: dict iteration
order varies cross-container, the iteration feeds a `+=` accumulator
(or `sum()`), and the resulting near-cancellation residue propagates
into the next-bar sizing decision — exactly the T-092 mechanism that
produced 0.19-Sharpe drift at 26-yr.

| # | File | Function | What was wrong | Fix |
|---|---|---|---|---|
| 1 | `engines/engine_a_alpha/signal_collector.py` | `collect()` return | Outer ticker dict iteration order = "which edge fired first per ticker" = cross-container-variable | Sort outer ticker keys at return (extends T-057c-det inner-only sort) |
| 2 | `engines/engine_c_portfolio/portfolio_engine.py:248` | `snapshot()` | `for t, pos in self.positions.items(): market_value += pos.qty * px; unrealized += (px - pos.avg_price) * pos.qty` — accumulator over dict-order positions | Sort `positions.keys()` + `math.fsum` over contribution lists |
| 3 | `engines/engine_c_portfolio/portfolio_engine.py:323` | `total_equity()` | Same pattern as snapshot() — `mv += pos.qty * px` over positions.items() | Same fix |
| 4 | `backtester/backtest_controller.py:525` | `_prepare_orders` equity #1 | `for t_pos, p_pos in self.portfolio.positions.items(): mv += p_pos.qty * close_prices_df.at[ts, t_pos]` | Sort + math.fsum |
| 5 | `backtester/backtest_controller.py:558` | `_prepare_orders` equity #2 | `pos_values.append(...); ... equity = capital + sum(pos_values)` — pos_values built from pos_qtys.items() | Sort pos_qtys.keys() + math.fsum |

All fixes tagged `# T-2026-06-04-099 determinism fix`.

## The drift propagation mechanism (what T-092 observed)

1. **Root**: `signal_collector.collect()` returned `raw_scores` with
   OUTER ticker keys in dict-insertion-order. The T-057c-det fix
   sorted the INNER `edge_map` but the outer order was determined by
   "which edge fired first per ticker" — which depended on individual
   edges' internal pandas/numpy operations and varies cross-container.
2. **Propagation**: signal_processor's outer loop
   `for ticker, edge_map in raw_scores.items()` inherits that
   non-canonical order → `proc` dict order varies → signals list
   order varies → trades execute in different sequence →
   `self.portfolio.positions` insertion order varies.
3. **Compounding**: `portfolio_engine.snapshot()` accumulates
   `market_value += pos.qty * px` over `self.positions.items()` —
   different order → ULP-level FP residue in equity → next bar's
   target_notional = equity × target_weight differs by the same residue
   → at a near-zero crossing (rebalance tolerance check, vol-target,
   sizing-vs-cap), the SIGN flips → side flips → completely different
   trade sequence from that bar forward.
4. **Why depth-scaling**: each bar accumulates more residue; over
   3,017 bars (12-yr) vs 6,538 bars (26-yr), the residue compounds.
   12-yr drift was ≤0.1 Sharpe; 26-yr was 0.19; the >3-Sharpe per-year
   swings T-092 reported (2018 canonical +2.079 vs drift -1.014)
   are the visible signature of late-window sign flips.

The fix breaks the chain at sites 1, 2, 3, 4, 5 — each is order-
canonicalized so even if a deeper source still produces order-variable
inputs, the consuming reductions are now order-independent.

## Verification

### Single-container `--runs 3` — PASS (still bitwise stable)

Local 2024 single-year, PYTHONHASHSEED=0:
```
Sharpes:          [0.86, 0.86, 0.86]
Sharpe range:     0.0000
Canon md5 unique: 1 / 3
[RESULT] PASS — Sharpe within ±0.02 AND bitwise-identical canon md5
```

### Canonical-value inert — PASS (proves order-only, not semantic)

Pre-fix (git stash baseline) and post-fix on 2024 single-year:

| | Pre-fix | Post-fix | Δ |
|---|---|---|---|
| Sharpe | 0.86 | 0.86 | 0.00 |
| CAGR | 4.95% | 4.95% | 0.00% |
| canon_md5 | `b613764912f1a66da5c7d00ebaa3ab8b` | `b613764912f1a66da5c7d00ebaa3ab8b` | identical |

The fixes produce trades.csv **byte-identical** to the pre-fix canonical
output. Sort+fsum is genuinely order-only on the canonical-order input;
no semantic change.

### Hash-seed invariance — PASS (stronger cross-container proxy than --runs 3)

Local 2024 single-year, varying PYTHONHASHSEED ∈ {0, 1, 42} simulates
different dict iteration orders that real cross-container Fargate
instances would produce:

| HASHSEED | Sharpe | canon_md5 |
|---|---|---|
| 0 | 0.86 | `b613764912f1a66da5c7d00ebaa3ab8b` |
| 1 | 0.86 | `b613764912f1a66da5c7d00ebaa3ab8b` |
| 42 | 0.86 | `b613764912f1a66da5c7d00ebaa3ab8b` |

Note: pre-fix also showed identical results across these seeds — local
dict-hash randomization doesn't fully exercise the cross-container
drift surface (CPU instruction differences, BLAS threading, numpy
internals, etc. also contribute). This test is a NECESSARY but not
SUFFICIENT proxy. The DEFINITIVE test is cloud-side; see "Residual
verdict" below.

### Long-window local `--runs 3` (12-yr cell) — PASS

Local 2014-01-01 → 2025-12-31 (12-yr arm0_off), `--runs 3`,
PYTHONHASHSEED=0:

```
Sharpes:          [1.081, 1.081, 1.081]
Sharpe range:     0.0000
Canon md5 unique: 1 / 3
canon_md5:        36f37aaefaa67b1a51946b5b8db78846
CAGR%:            11.42
[RESULT] PASS — Sharpe within ±0.02 AND bitwise-identical canon md5
```

The inbox's stated pass/fail gate is cleared. Note: the 12-yr local
canonical Sharpe is 1.081 here, materially above the T-088 cloud
baseline (0.81) and below T-092's 16-yr (1.018). This is consistent
with the post-T-088/T-089/T-090/T-091/T-092/T-093/T-095/T-096/T-098
merges that have happened since the last cloud image build; local
state has progressed, cloud image is from 2026-05-29. The canon_md5
above (`36f37aae...`) is the new post-T-099 local canonical for the
12-yr arm0_off cell.

### Regression tests — 6 new + 9 prior PASS

`tests/test_fp_determinism_t099_long_window.py` (new, 6 tests):
- `test_collector_outer_ticker_order_canonicalized` — outer ticker dict
  iterates alphabetically regardless of insertion order
- `test_portfolio_mv_accumulator_order_independent` — market_value
  invariant under permuted position dict
- `test_portfolio_mv_handles_zero_qty` — skip qty==0 doesn't depend on
  iteration order
- `test_backtest_controller_equity_order_independent` — controller's
  equity accumulator invariant
- `test_near_zero_crossing_drift_eliminated` — long/short basket at
  near-cancellation produces identical MV across 3 iteration orders
- `test_bare_sum_drift_demonstrated` — informational sanity that the
  test data exercises the actual bug surface

`tests/test_fp_determinism_t057c_followup.py` (9 prior tests) — all PASS.

Broader test sweep: 1850 of 1857 PASS. 7 pre-existing failures unrelated
to T-099 (same set as T-088 baseline: `test_anchor_no_stale_composites`,
`test_discovery_gate1_caching`, `test_oos_validation_isolation_default`,
`test_spinoff_reversion_edge`, `test_validate_candidate_v2`). None
touch the modules T-099 modified.

## Why not Engine B / live_trader

The inbox put `engines/engine_b_risk/` and `live_trader/` in
PROPOSE-FIRST scope. I grep'd both for the same bug class and found
candidate sites:

- `engines/engine_b_risk/risk_engine.py` has multiple iterations over
  signals + position-iteration patterns (e.g., `_check_sector_cap`
  iterates an exposure-by-sector dict). The risk-engine sizing also
  consumes `equity` from the controller — but `equity` is now sorted-
  sourced (sites 4, 5 above). I did NOT touch Engine B; if any
  Engine-B-internal accumulator surfaces residue after this dispatch,
  it warrants a propose-first follow-up.
- `live_trader/` was not scoped for this dispatch (live trading path
  doesn't run the backtest harness).

## Residual verdict

| Gate | Result | Notes |
|---|:-:|---|
| Local `--runs 3` 1-yr bitwise-identical | ✓ PASS | Sharpe 0.86 / md5 stable across 3 reps |
| Canonical-value inert (pre/post stash) | ✓ PASS | Same Sharpe + same canon_md5 = order-only |
| 6 new + 9 prior FP-determinism tests | ✓ PASS | 15/15 |
| Hash-seed invariance (proxy) | ✓ PASS | Identical across seeds 0/1/42 (also pre-fix, so necessary-not-sufficient signal) |
| Local `--runs 3` 12-yr bitwise-identical (the gate) | ✓ PASS | Sharpe 1.081 × 3, canon_md5 `36f37aae...`, range 0.0000 |
| **Cross-container determinism (cloud A/B on long window)** | **deferred** | Requires image rebuild + cloud verify; SEPARATE dispatch |

**Conclusion (subject to long-window-local gate confirmation):** the
fix is mechanically correct on each identified site (proven by 6 unit
tests + canonical-value inertness). Whether it CLOSES T-092's
0.19-Sharpe drift depends on whether all the load-bearing cross-
container drift sources were among the 5 fixed sites. The candidates
were enumerated against the same bug-class fingerprint T-057c-det
established and against the live arm0_off path the inbox prescribed;
the equity-snapshot accumulator in particular is the canonical
write-target for `portfolio_snapshots.csv` (which IS canon_md5'd), so
fixing it is essentially load-bearing for any long-window canon_md5
stability claim.

**The cross-container empirical gate requires a fresh ECR image push +
3-rep cloud verify on a 16-yr or 26-yr cell.** That test cannot run
on this branch — the image build path is a separate dispatch.
Recommended next step:
1. Director merges this branch.
2. Image rebuild (Dockerfile.backtest → ECR :dev push, manual per
   CI-OIDC-failing-since-2026-05-24 workaround that T-088 documented).
3. Submit a verify spec mirroring T-092 with N=3 reps on the 26-yr
   window only (or 16-yr if budget is tight); compare canon_md5
   spread to T-092's reference baseline.

If T-092 had reps 1/2/5 stable at canon `c579566c...` and rep4 drifting
to `a762df...`, the post-fix verify should see ALL 3 reps stable on
the same md5. Anything else means another drift source remains.

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | Residual drift site(s) identified with evidence | DONE — 5 sites enumerated with drift-propagation mechanism written up |
| 2 | Canonical `sort + math.fsum` fix applied | DONE — at all 5 (none in Engine B/live_trader) |
| 3 | Determinism re-test `--runs 3` bitwise-identical canon md5 on LONG window | DONE — 12-yr 2014-2025: 3/3 reps Sharpe 1.081 / canon_md5 `36f37aae...` / range 0.0000 |
| 4 | Canonical Sharpe unchanged to ~3 decimals on stable cell | DONE — Sharpe 0.86 / md5 unchanged pre/post |
| 5 | Audit doc + TASK_LEDGER row | DONE — this file + ledger appended |
| 6 | Branch pushed; NOT merged | pending |

## Files

- `engines/engine_a_alpha/signal_collector.py` (outer ticker dict sort at return)
- `engines/engine_c_portfolio/portfolio_engine.py` (snapshot + total_equity)
- `backtester/backtest_controller.py` (two equity-calc sites in `_prepare_orders`)
- `tests/test_fp_determinism_t099_long_window.py` (NEW, 6 regression tests)
- `docs/Audit/long_window_determinism_t099_2026_06_04.md` (this file)
- `docs/State/TASK_LEDGER.md` (appended row)

## Memory updates needed (post-merge)

- New entry: "T-099 closed 5 residual long-window FP-determinism sites
  beyond T-057c-det + T-057c-followup. Root cause was outer ticker
  dict in `signal_collector.collect()` not being sorted (only inner
  edge_map was). Propagated through proc → signals → positions →
  equity-snapshot accumulator (the canon_md5'd write target).
  Canonical-value inert; single-container --runs 3 bitwise stable.
  Cross-container empirical gate deferred to post-merge image rebuild."
- Update `project_t057c_det_fp_summation_order_2026_05_24.md` and
  the T-057c-followup memory — note that the dispatch missed the
  OUTER ticker sort + the portfolio_engine + backtest_controller
  equity accumulators; T-099 closes that gap.

## Forward dispatches

- **T-099-verify**: Image rebuild + ECR push + 3-rep cloud verify on
  a 26-yr `arm0_off` cell. Pass criterion: all 3 reps converge on
  identical canon_md5. Failure means another drift source remains;
  next bisect would instrument candidate `np.dot` / BLAS-threading /
  numpy-internal-ordering sites.
- **T-099-engine-b-audit**: PROPOSE-FIRST audit of Engine B for the
  same bug-class fingerprint. If any sites surface, propose-first
  fix would be a separate Engine-B-touching dispatch.

## NOT done in T-099

- No Engine B / live_trader code changes (per inbox propose-first).
- No image rebuild + cloud verify (separate dispatch).
- No semantic changes — every fix is sort+fsum, order-only.
- No changes to `data/governor/*` (per inbox).
- Did not bisect deeper drift sources beyond the 5 enumerated; if
  the cloud verify shows residual drift, that's the next dispatch.
