# T-224 — engine_c_portfolio code-health pass: what was tightened + what I'm proposing

**Date:** 2026-06-19
**Agent:** C. Tightening pass while D/T-215 runs. Autonomous safe fixes done; riskier items PROPOSED below (not done).

---

## DONE (autonomous, all behavior/canon-preserving)
| fix | file:loc | why it's safe |
|---|---|---|
| **Gated 2 ungated debug prints** (the highest-value find — a real bug) | `portfolio_engine.py` apply_fill close-path + open-path | `[DEBUG_PORTFOLIO_STATE]` printed on EVERY fill (12k+ lines on a 26yr cell) — the exact logger-drain the in-file T-142 comment was meant to kill, but these two siblings were missed when line 124's sibling was gated. Now `if is_debug_enabled("PORTFOLIO")`. Stdout-only → trades.csv/canon unaffected. |
| **Removed dead `is_portfolio_debug()`** | `portfolio_engine.py:11-12` | 0 callers repo-wide; also buggy (returned `(bool, function)`, the function never called). Archived. |
| **Consolidated the duplicated price-extraction** into `_last_close_map()` | `portfolio_engine.py` (buffering + dyn-opt) | the `{ticker: last_close}` build was copy-pasted in two OFF-default post-processors; one helper now, dyn-opt keeps its separate returns_map loop. Behavior-identical (330 engine_c tests green incl. the FP-determinism locks). |
| **Removed no-op duplicate dataclass fields / dict keys / re-assignments** | `portfolio_engine.py` (`Position.edge_id` ×2; `_as_dict` `edge_id`/`edge_category` ×2; `apply_fill` flip-path re-assign ×2) | pure no-ops (Python keeps the last; the re-assignment set the same values) → canon-identical. |
| **Removed unused imports** | `moonshot_sleeve.py` (np), `optimizer.py` (List/Optional/Tuple), `allocation_evaluator.py` (field/List/Tuple) | AST-confirmed unused; no runtime effect. |

**LOC:** net ~−2 in the engine, but the value is the de-duplication (one price-extraction source) + the real print-drain bug fix + dead-code removal — "tighter, not larger." Archived removals: `Archive/engine_c_health_t224/removed_dead_code.md`. Canon: 2022 `trades_canon_md5` unchanged (proof in commit); doc_lint green; 330 engine_c tests green.

---

## PROPOSED (NOT done — for director review)

### P1 — Dead public accessors (batch-archive, ~−30 LOC)
Grep-confirmed ZERO callers anywhere (engine_c, tests, backtester, orchestration, paper_trader, scripts): `PortfolioEngine.net_exposure()`, `target_notional_values()`, `get_position_info()`, `get_avg_price()`, `get_qty()`; `PortfolioPolicy.requires_rebalance()`; `PortfolioOptimizer.calculate_metrics()`. They READ as deliberate "downstream-compatibility" API surface (the section header says so) on cross-engine-consumed classes — removing API others might wire to later is a judgment call, not a clean dead-branch. **Recommend:** confirm none are a planned wire, then Archive as a batch. (`positions_map` IS live — consumed by cost_aggregator — keep.)

### P2 — Engine-boundary: vol-target / exposure-cap regime logic lives in Engine C [NN-ENGINE-BOUNDARIES]
`policy.py::_apply_vol_target` + `_apply_exposure_cap` read Engine-E regime labels (`macro_regime`, `forward_stress_regime`, `advisory.suggested_exposure_cap`), and the phase1_composition docstring explicitly calls the vol-target **Engine B's** scope (propose-first, B/T-212). So Engine C currently owns a vol-target overlay a sibling documents as Engine B's. **This is a charter-boundary question for you to route** (it dovetails with B/T-212) — flagging, not fixing.

### P3 — God-functions (canon-sensitive splits — branch + canon-md5 before/after)
- `apply_fill` (~150 LOC) inlines close/reduce, open/add, opposite-flip, SL/TP-direction in one method → split `_apply_close`/`_apply_open`/`_apply_flip`. Touches the core accounting identity (canon-sensitive).
- `policy.allocate` (~170 LOC) runs 3 modes in one method; the `mean_variance` branch (~90 LOC) inlines sector-map load + the COVMVO probe + constraint-building → split `_allocate_mean_variance`/`_allocate_adaptive`/`_allocate_parrondo`. Touches the production allocator.
Both are exactly the kind of change to do behind a bitwise-canon gate; recommend a dedicated branch + before/after md5, not folded into a cleanup pass.

### P4 — Vectorization is a DETERMINISM TRAP here (recommend NOT doing)
`policy.compute_vol_estimates` per-ticker loop and the `snapshot()`/`total_equity()` loops are intentionally scalar + `math.fsum` + sorted-key for the T-099/T-057c cross-container FP-determinism fix (locked by `test_fp_determinism_*`). Vectorizing would change the FP reduction order and risk the exact cross-container lottery those comments fight. In this engine, loop→vector is a risk, not a free win — recommend leaving as-is unless a profiler proves a hotspot, and only behind a canon-md5 gate.
