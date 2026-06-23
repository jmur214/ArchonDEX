# T-229 — Code self-honesty sweep: "code that lies about itself"

**Date:** 2026-06-19 · **Agent:** A · **Branch:** `feature/code-self-honesty-sweep-t229`
**Lane:** integrity (engine-agnostic; comment/docstring-only — autonomous-OK).
**Status:** SHIPPED — 10 edge-status contradictions clarified (comment-only, proven non-executable); all reachability/wiring docstring claims in the load-bearing paths verified ACCURATE; no logic-fix-required lie found. doc_lint exit 0, tests green.

## 1. Scope

Find + fix the class where code **misrepresents itself** — falsifiable
"this code isn't used / active / reachable" self-claims that mislead the
audits and agents we rely on (the class that helped bury the conjunctive
selector; T-228 surfaced two: `defensive_tilt` docstring + `macro_yield_curve_v1`
status). Two parts: (1) docstring/comment reachability+status claims;
(2) in-code edge `status=` defaults vs the `edges.yml` authority. **Comment-only
— no logic/default/`edges.yml` change**; a lie fixable only by logic change is
PROPOSED, not done.

## 2. Part 1 — reachability/wiring self-claims (engines/ + core/): ALL ACCURATE

Swept for load-bearing phrasings ("not imported", "never called", "not on the
production/live/backtest path", "OFF by construction", "unreachable", "stub",
"not wired", "inert", "no consumers"). Each verified against the actual
importers/callers/flags. **Every surviving claim is TRUE** — the one real lie of
this class (`defensive_tilt` "NOT imported" → it IS imported by
`phase1_composition`) was already fixed on main by T-228.

| Claim site | Self-claim | Verdict |
|---|---|---|
| `screens/industry_momentum.py:8` | "NOT imported by the production backtest path" | TRUE — only `scripts/industry_momentum_t213.py` (research) imports it |
| `engine_b_risk/regime_transition_overlay.py:60` | "Default OFF → `observe` is never called by Engine B" | TRUE — `risk_engine` call sites are gated on `regime_transition_overlay_enabled` (default False); claim is correctly scoped to "Default OFF" |
| `screens/__init__.py:4` | "NOT wired into Engine-B admission or sizing" | TRUE — and it self-corrects, explicitly naming the Engine-C `phase1_composition` import behind `phase1_composition_enabled` (default False) |
| `engine_b_risk/factor_analysis.py:152` | "SIZING-INTEGRATION HOOK — NOT WIRED" | TRUE — no caller of `decompose`/`compute_exposures` in `risk_engine` or Engine C |
| `engine_c_portfolio/sleeves/trend_following_sleeve.py:22` | "not wired into `PortfolioEngine.allocate`" | TRUE — `TrendFollowingSleeve` is absent from `portfolio_engine.py`/`composer.py` |
| `engine_b_risk/risk_engine.py:82` | "this scaffold ships INERT" | TRUE — `drawdown_kill_switch_enabled` default False |
| `core/account_router.py:8` | "backtest-time checker stub… does NOT place or block real" orders | TRUE — zero importers, no broker/order-submit APIs |

No comment changes needed in Part 1.

## 3. Part 2 — in-code edge `status="active"` vs `edges.yml`: 10 contradictions, all clarified

`edges.yml` (`data/governor/edges.yml`) is the write-protected lifecycle
authority: `EdgeRegistry.ensure()` write-protects an existing spec's `status`
(verified: `edge_registry.py:294` + `tests/test_edge_registry.py::test_ensure_does_not_overwrite_{paused,retired,failed}_status`).
So an edge's auto-register `status="active"` is a **first-registration default
that never wins** for an already-persisted edge — but it actively misleads any
agent/audit grepping the edge file (reads "active" when the live status is
paused/retired/failed). This is the exact `macro_yield_curve_v1` class.

Cross-referencing every in-code `status="active"` against `edges.yml`:

| Edge file | EDGE_ID | edges.yml status |
|---|---|---|
| `momentum_edge.py` | momentum_edge_v1 | paused |
| `momentum_factor_edge.py` | momentum_factor_v1 | failed |
| `pead_edge.py` | pead_v1 | paused |
| `pead_predrift_edge.py` | pead_predrift_v1 | paused |
| `pead_short_edge.py` | pead_short_v1 | paused |
| `quality_gross_profitability_edge.py` | quality_gross_profitability_v1 | failed |
| `quality_roic_edge.py` | quality_roic_v1 | failed |
| `insider_cluster_edge.py` | insider_cluster_v1 | paused |
| `low_vol_factor_edge.py` | low_vol_factor_v1 | paused |
| `macro_yield_curve_edge.py` | macro_yield_curve_v1 | retired |

(For reference, the non-contradicting `status="active"` edges —
`value_book_to_market_v1`, `value_earnings_yield_v1`, `accruals_inv_asset_growth_v1`,
`accruals_inv_sloan_v1` — match `edges.yml=active` and were left untouched.)

**Fix (comment-only, uniform, non-staling).** Each contradicting `status="active"`
line gets a trailing clarifier:

```python
status="active",  # non-authoritative default — edges.yml is the live status (EdgeRegistry.ensure write-protects existing specs); do not read this literal as the edge's lifecycle state. [NN-NO-MANUAL-EDGES]
```

It does NOT hardcode the current `edges.yml` status (which F's lifecycle mutates)
→ truthful and drift-proof. The `status="active"` literal itself is unchanged
(changing it would be a logic/default change, and is harmless anyway since
write-protected).

## 4. Canon-safety / comment-only proof

Strict check: every changed line equals `old_line + clarifier` exactly — **zero
executable change** (10/10, mechanically verified). All 10 files `py_compile`
clean; `tests/test_edge_registry.py` 12 passed; `tests/test_contracts.py` green;
doc_lint exit 0. `git diff` touches only the 10 edge files (+ this audit).

## 5. Logic-fix-required lies: NONE found (nothing to propose)

No self-claim required a logic change to make honest; all were fixable in-comment
or already true. Nothing is proposed back.

## 6. Compliance

- Comment/docstring-only; no logic/default/`edges.yml` change. ✓
- Each `.py` change proven non-executable (old_line + comment). ✓
- Bounded to falsifiable "not used/active/reachable" claims (not every comment). ✓
- `[NN-NO-MANUAL-EDGES]` cited (edges.yml authority); doc_lint green. ✓
- Branch push; director merges. ✓
