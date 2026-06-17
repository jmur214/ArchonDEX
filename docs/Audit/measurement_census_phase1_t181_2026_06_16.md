# T-181 — Measurement-integrity hardening, PHASE 1: the execution-census layer

**Date:** 2026-06-16
**Agent:** C (branch `feature/measurement-census-phase1-t181`)
**Status:** DONE pending the additivity proof + director merge. Pure ADD-and-OBSERVE + mechanical guard fixes. NO change to any allocator / sizing / signal logic. (Phase 2 — cross-engine HALT semantics, Engine B, fundamentals bake — is propose-first, NOT this task.)

Implements the Phase-1 rollout of `docs/Audit/measurement_integrity_audit_2026_06_16.md`: make every backtest **self-announcing** so the recurring "degrade to a plausible number instead of halting" defect (T-088 / T-167 / T-171 / T-175 / T-177) becomes observable and, at the publish boundary, blocking.

---

## 1. The census block (pure-add to performance_summary.json)
`backtester/backtest_controller.py:_build_census()` assembles a `census` block at summary time (observation only — it reads run state + artifacts, never mutates trades; the canon is over trades.csv, not the summary). Producers wired:

| census field | source | invariant / past bug |
|---|---|---|
| `edges_blind`, `edge_signal_counts`, `bars_collected`, `n_active_edges`, `edges_paused` | `signal_collector.py` — per-edge non-zero tally accumulated across the run (seeded with every loaded edge so a never-firing edge shows as 0) | #1 — T-177 (genes inert), T-175 (value edges blind) |
| `n_resolved`, `n_in_panel` | controller `__init__` — tickers handed in vs surviving normalization | #2 — T-167 universe shrink |
| `regime_unknown_bars`, `regime_total_bars`, `regime_unknown_frac`, `macro_panel_complete` | `_detect_regime` per-bar tally | #4 — T-164 GAP-2 (regime silently OFF) |
| `fundamentals_blind`, `fundamentals_edges_active` | `_fundamentals_helpers.panel_is_blind()` × active value/quality edge | #1/#4 — T-175 simfin-blind |
| `n_trades`, `trades_canon_md5`, `trades_empty` | trades.csv (canon reuses the `run_isolated._trades_canon_md5` recipe) | #3 — T-175/T-164 zero-trade-as-0.0 |
| `config_provenance` (path / exists / n_keys / md5 / degraded) | reads the prod config files | #6 — T-088 risk-key mismatch / one-key fallback |

One operator line prints per run (`[BACKTEST][CENSUS] trades=… panel=…/… regime_unknown=… edges_blind=… fund_blind=…`).

## 2. The shared gate — `core/census.py:assert_census`
ONE helper; local and cloud call it so the canonical/non-canonical verdict cannot diverge. A run is **NON-CANONICAL** (no publish / upload / certify / quote) if ANY invariant fails: edges_blind non-empty (minus an `expected_dormant` allowlist), `n_in_panel < n_resolved − allowlist`, zero-trade / EMPTY_MD5, `fundamentals_blind > 0`, regime 100% unknown, or degraded config. A missing census fails closed. CI-absence is a WARN (CLAUDE.md ci_low rule), not a hard block. Strict defaults are env-overridable (`CENSUS_EXPECTED_DORMANT`, `CENSUS_PANEL_ALLOWLIST`) so a legitimate edge case is acknowledged explicitly, never silently tolerated.

Wired at the three publish boundaries:
- **`scripts/run_isolated.py`** — PASS-gate: a NON-CANONICAL run cannot PASS even if perfectly deterministic ("a deterministic clouded number is still a clouded number").
- **`scripts/run_substrate_arms.py`** — extends the existing EMPTY_MD5 smoke kill with the full census.
- **`scripts/cloud_entrypoint.sh`** — runs `python -m core.census` before declaring success; a non-canonical cell still uploads its artifacts (forensics) but exits non-zero and is marked `census_canonical=false` in the manifest + S3 metadata, so the launcher never certifies it.

## 3. Mechanical guard fixes (CLAUDE.md-mandated, single-line each)
- **Bare `.std() == 0` → tolerance guard** (`not np.isfinite(s) or s < 1e-12`, CLAUDE.md #8). The audit named 4 sites; the new AST guard (below) forced completeness — **11 sites across 8 files** were the same latent ~1e15-explosion bug: `cost_aggregator.py`, `run_backtest_pure.py` (×2, incl. the `downside.std()>0` sortino guard), `multiple_testing.py`, `benchmark.py` (×2), `wfo.py` (×2 — only one was named), `volatility_risk_premium_edge.py`, `low_vol_factor_edge.py`, `governor.py`. All same one-line mechanical fix; each changes ONLY the degenerate near-constant branch.
- **Bootstrap-CI broad-except** (`backtest_controller.py`) → every non-CI outcome now sets an explicit `bootstrap_ci_skip_reason` + an **unconditional** WARN (was debug-gated → a CI failure silently shipped a summary with no CI, violating the ci_low rule). The success path is byte-identical.
- **`_normalize_df` band-drop logging** (`data_manager.py`) → counts and WARNs per-ticker when the 20× median band drops rows (the T-167 silent-shrink site). The filter itself is unchanged; `ticker` threaded as an advisory (default "") param through all four call sites.

## 4. CI tiers (extend tests/test_contracts.py + test_forbidden_patterns.py + contract_tests.yml)
- **Layer 1c** — `RegimeConfig` added to the Layer-1 config-key⊆dataclass matrix; `test_layer1c_required_risk_keys_present_in_prod_json` asserts the live risk knobs are PRESENT in the prod JSON (the inverse of Layer 1 — catches the T-088 missing-key→silent-default class).
- **Layer 2d** — census producer/consumer contract: every key `assert_census` reads must be emitted by `_build_census` (static source scan, same idiom as Layer 2a).
- **AST guard** (`test_forbidden_patterns.py`) — pure-AST test that no bare `.std()/.var() == 0` exists under backtester/orchestration/core/engines. This is what forced the 11-site completeness.
- **`tests/test_census.py`** — 14 behavioural tests: each of the 6 invariants flips NON-CANONICAL, clean passes, missing fails closed, allowlists work.
- Workflow now triggers on core/backtester/orchestration and runs `test_census.py`.

Test status: contract suite + census + forbidden-patterns all green locally (see §6).

## 5. Additivity proof (the hard constraint)
The census is observation-only and the std-guards change only the degenerate branch, so trades must be bitwise-identical. Verified by canon-md5 across the change on a 2021 backtest (`run_isolated --runs 3` my-branch vs `git stash` baseline): **<RESULTS PENDING — filled on completion>**. `--runs 3` determinism: **<PENDING>**.

## 6. Scope honesty / non-goals
- **Phase 1 does NOT halt inside loaders.** A degraded run still completes and emits its census; the GATE acts only at the publish boundaries. Missing-input→HALT in data_manager/simfin/macro/universe_resolver, Engine-B-adjacent guards, the fundamentals bake, and the policy.py allocator census are **Phase 2 (propose-first)**.
- `config_provenance` observes the **prod**-suffixed config files, not an arbitrary env-resolved override — a Phase-1 best-effort sufficient to catch an empty/one-key config.
- The `set_params`-hydration test (T-177) is **D's T-179**; this task wires only the census contract tier.
- No prod change, no flag flips, no Engine-B/live_trader edits, no allocator/sizing/signal change.

## 7. Files
Producers: `backtester/backtest_controller.py`, `engines/engine_a_alpha/signal_collector.py`, `engines/engine_a_alpha/edges/_fundamentals_helpers.py`, `engines/data_manager/data_manager.py`.
Gate: `core/census.py` (new).
Callers: `scripts/run_isolated.py`, `scripts/run_substrate_arms.py`, `scripts/cloud_entrypoint.sh`.
Guards: `backtester/cost_aggregator.py`, `orchestration/run_backtest_pure.py`, `core/multiple_testing.py`, `core/benchmark.py`, `engines/engine_d_discovery/wfo.py`, `engines/engine_a_alpha/edges/volatility_risk_premium_edge.py`, `engines/engine_a_alpha/edges/low_vol_factor_edge.py`, `engines/engine_f_governance/governor.py`.
CI: `tests/test_contracts.py`, `tests/test_forbidden_patterns.py`, `tests/test_census.py` (new), `.github/workflows/contract_tests.yml`.
