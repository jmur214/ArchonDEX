# `docs/Audit/` — Topic index

> **Status:** hand-maintained for now. Auto-generation from each audit's YAML frontmatter is the future path once the parallel workstream's structured `result_emit` schema lands. Until then, append a row when a new audit doc commits.

This index groups audit docs by **topic** so cross-task analysis is fast (`Engine B vol-target`, `confidence-gated execution`, `regime detection`, etc.). Counter-references: chronological order is in [`docs/State/TASK_LEDGER.md`](../State/TASK_LEDGER.md); current-state dashboard is [`docs/State/CURRENT_STATE.md`](../State/CURRENT_STATE.md).

`docs/Audit/` vs `docs/Measurements/`:
- **`docs/Audit/`** holds **analysis docs with a verdict** — one per T-ID or per question. A reader can answer "did X clear the bar?" by reading the audit. The audit doc is FROZEN once committed; supersession is tracked in TASK_LEDGER + this index.
- **`docs/Measurements/<YYYY-MM>/`** holds **raw cell-level results**, run registries, parquet manifests. Source data the audits cite, not narrative. Don't confuse the two.

Columns: `topic | audit doc | date | verdict`.

## Baseline + measurement infrastructure

| Topic | Audit doc | Date | Verdict |
|---|---|---|---|
| Cockpit metrics-pipeline bug (peak_equity slot) | `metrics_report_t069_t035_baseline.md` | 2026-05-12 | FIXED — baseline corrected 0.270 → 0.598 |
| T-035 baseline metrics report | `baseline_metrics_report_t066_2026_05_22.md` | 2026-05-22 | DOCUMENTED — 5-yr-Alpaca per-edge breakdown |
| Multi-year window harness + MBL Gate-0 | `multi_year_window_harness_t053b_2026_05_25.md` | 2026-05-25 | SHIPPED — 12-yr window now project standard |
| Foundational DSR/MBL re-evaluation on 12-yr | `baseline_dsr_mbl_foundational_2026_05_30.md` | 2026-05-30 | BORDERLINE — Sharpe ~0.81 plausibly-real but ci_low ~0.33 doesn't clear DSR |

## Engine A — Alpha / signal contracts

| Topic | Audit doc | Date | Verdict |
|---|---|---|---|
| Production hunt() ticker= wiring | `production_hunt_ticker_wiring_postfix_2026_05_12.json` | 2026-05-12 | FIXED — Engine D foundry_feature dead-letter closed |
| Pairwise conditional α (V/Q/A clustering) | `pairwise_conditional_alpha_2026_05_22.md` | 2026-05-22 | DOCUMENTED — pruning math + per-pair α |
| V/Q/A clustering prior | (refuted via memory entry — no standalone audit) | 2026-05-23 | REFUTED — max ρ +0.316 (below 0.5 gate) |

## Engine B — Risk / vol-targeting

| Topic | Audit doc | Date | Verdict |
|---|---|---|---|
| Vol-target shipped defense-first | `engine_b_vol_targeting_2026_05_12.md` | 2026-05-12 | INERT default; canon md5 identical |
| Vol-target A/B 5-yr-Alpaca (T-055c) | `engine_b_vol_targeting_ab_t055c_2026_05_22.md` | 2026-05-22 | MARGINAL — +0.256, ci_low -0.140 crosses zero |
| Vol-target EWMA (T-055d) | `engine_b_vol_target_ewma_t055d_2026_05_22.md` | 2026-05-22 | MARGINAL — ci_low -0.046 |
| Vol-target regime+EWMA (T-055e) | `engine_b_vol_target_regime_conditional_t055e_2026_05_23.md` | 2026-05-23 | SUPERSEDED — first DEFENSIBLE +0.549 5-yr; later refuted |
| Vol-target multiplier sweep (T-055g) | `vol_target_multiplier_sensitivity_t055g_2026_05_24.md` | 2026-05-24 | REFUTED — 75 cells; no arm clears ci_low > 0 |
| Vol-target 12-yr verify (T-055h) | `vol_target_12yr_verify_t055h_2026_05_29.md` | 2026-05-29 | REFUTED — Δ -0.214; chapter CLOSED |
| Risk-config key rename (T-088) | `risk_config_keyfix_t088_2026_05_31.md` | 2026-05-31 | FIXED — risk_per_trade_pct DEAD KNOB confirmed on prod (Path B) |

## Engine A → B/C — Confidence-gated execution

| Topic | Audit doc | Date | Verdict |
|---|---|---|---|
| Confidence-gated execution proof of concept | `confidence_gated_execution_2026_05_12.md` | 2026-05-12 | SHIPPED — initial N-threshold A/B harness |
| Confidence-gated 5-yr substrate (T-057) | (in `confidence_gated_execution_2026_05_12.md`) | 2026-05-23 | SUPERSEDED — original 5-yr-Alpaca +0.793 "strongest lift" |
| Confidence-gated extended substrate (T-057b) | `confidence_gated_flag_flip_t057b_2026_05_24.md` | 2026-05-24 | REFUTED — Δ -0.075, ci_low -0.532 iid / -1.154 block |
| Confidence-gate determinism root-cause (T-057c-det) | `confidence_gate_determinism_t057c_det_2026_05_24.md` | 2026-05-24 | FIXED — FP summation-order cross-container |
| FP determinism sweep follow-up | `fp_determinism_sweep_t057c_followup_2026_05_30.md` | 2026-05-30 | FIXED — defensive sort at sibling sites |
| Confidence-gated 12-yr re-verify (in T-053b) | `multi_year_window_harness_t053b_2026_05_25.md` | 2026-05-25 | REFUTED — Δ -0.128 on 12-yr; first MBL Gate-0 PASS |

## Engine E — Regime detection

| Topic | Audit doc | Date | Verdict |
|---|---|---|---|
| Engine E regime signal re-diagnosis (T-087) | `engine_e_regime_rediagnosis_t087_2026_05_30.md` | 2026-05-30 | REVERSED — HMM p_crisis AUC 0.887 causal on 12-yr |
| Regime-validator causal-path verification (T-089) | `regime_validator_causal_fix_t089_2026_05_31.md` | 2026-05-31 | VERIFIED — T-087 causal claim STANDS; 3 sibling validators fixed; lookahead inflation +0.006 |

## Substrate

| Topic | Audit doc | Date | Verdict |
|---|---|---|---|
| Stooq extension to 1962/1970 (T-081) | `substrate_extension_stooq_t081_2026_05_23.md` | 2026-05-23 | SHIPPED — survivor window opened; delisted gap pre-2020 caveat |
| Substrate merge + dividend strip (T-082) | `substrate_merge_dividend_strip_t082_2026_05_23.md` | 2026-05-23 | LOCKED — canonical substrate is extended Stooq + Alpaca dividend-strip merged |

## Code quality / silent-mismatch family

| Topic | Audit doc | Date | Verdict |
|---|---|---|---|
| Dead-letter pattern audit (T-054 surface) | `dead_letter_pattern_audit_2026_05_12.md` | 2026-05-12 | FIXED — hunt() ticker= + 2 sibling sites |
| Silent-bug systemic audit | `silent_bug_audit_2026_05_31.md` | 2026-05-31 | FOUND — 9 confirmed defects, all silent-mismatch family |
| Contract-test suite (T-090) | `contract_test_suite_t090_2026_05_31.md` | 2026-05-31 | SHIPPED — 10 parametric tests <1s; caught 3 known + 7 NEW bugs |
| Contract-suite green-up + CI (T-091) | `contract_suite_greenup_t091_2026_05_31.md` | 2026-05-31 | SHIPPED — suite 10/10 green; PSR + Sortino producer-add; CI workflow |

## Discovery / Engine D / Engine F lifecycle

| Topic | Audit doc | Date | Verdict |
|---|---|---|---|
| Discovery seed from foundry profile | `discovery_seed_from_foundry_profile_*.json` | 2026-05-12 | DATA — seed snapshots (3 generations) |
| Engine F lifecycle factor-α re-evaluation | `engine_f_lifecycle_factor_alpha_reeval_2026_05_12.json` | 2026-05-12 | RE-EVALUATED post-cockpit-fix |
| Spinoff gauntlet (T-041b) | (audit doc per task) | 2026-05-22 | REFUTED — Gate 1 FAIL +0.000 contribution |
| Spinoff paused-tier-masking ruled out (T-041c) | `t041c_paused_tier_masking_ruled_out_2026_05_23.md` | 2026-05-23 | REFUTED — clean re-run identical FAIL |
| V/Q/A clustering prior (T-053) | `t053_vqa_clustering_refuted_2026_05_23.md` | 2026-05-23 | REFUTED — current actives correlation-clean |

## Documentation system

| Topic | Audit doc | Date | Verdict |
|---|---|---|---|
| Doc-system overhaul Phase 1 (T-093) | `doc_system_overhaul_phase1_t093_2026_05_31.md` | 2026-05-31 | SHIPPED — CURRENT_STATE + TASK_LEDGER + doc_lint + this index + nav edits |

## In-flight (no closed audit yet)

| Topic | Notes |
|---|---|
| T-092 deep-substrate baseline (16-yr + 26-yr) | Agent A in flight; audit will land at close. CURRENT_STATE's next-decision is conditional on this. |
| Phase 2 doc-system (`.claude/settings.json` + `CLAUDE.md`) | Deferred pending coordination with the parallel statistical-discipline-hooks workstream. |

## Conventions

- One row per audit doc. Multi-doc tasks (e.g., T-089 has `.md` + 2 `.json`s) get one row pointing to the `.md`; the JSON aggregations are siblings the audit cites.
- "REFUTED" means the original hypothesis was rejected; "SUPERSEDED" means an earlier positive verdict was later overturned. Both verdicts are visible in TASK_LEDGER's `status` column.
- When a follow-up doc closes a chapter (e.g., T-055h closing the T-055 vol-target arc), the original entries stay as-is and the closer's row carries the punch line.
