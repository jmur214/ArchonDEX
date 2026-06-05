# Task Ledger — ArchonDEX

> **Status:** hand-maintained for now. Auto-generation from audit-doc YAML frontmatter is the future path once the structured `result_emit` schema lands (the parallel workstream's item J). Until then, append a row when an audit doc closes.

Columns:

- **T-ID** — task ID.
- **date** — task close date (audit doc commit, not start).
- **title** — one-phrase task summary.
- **status** — `done` / `refuted` / `superseded` / `in-flight` / `blocked`.
- **cells_attempted** / **cells_succeeded** — cloud campaign cell counts; `—` for local or non-campaign tasks.
- **outcome** — one line; the punch line of the audit.
- **audit doc** — relative path under `docs/Audit/`.

Backfilled from T-035 (cloud era start, 2026-05-12) forward. Use `git log` and `MEMORY.md` for older context.

| T-ID | date | title | status | cells_attempted | cells_succeeded | outcome | audit doc |
|---|---|---|---|---|---|---|---|
| T-035 | 2026-05-12 | Metrics pipeline bug + baseline correction | done | — | — | Peak_equity slot bug bi-directional; baseline corrected 0.270→0.598 | `metrics_report_t069_t035_baseline.md` |
| T-038-CONT | 2026-05-12 | Foundry feature vectorization investigation | done | — | — | Surfaced T-054 production hunt() ticker= dead-letter bug | `dead_letter_pattern_audit_2026_05_12.md` |
| T-041 | 2026-05-17 | Spinoff event-driven edge integration | done | — | — | EDGAR scraper + 150 events indexed; edge registered paused/feature tier | `engine_a_alpha_spinoff_2026_05_17.md` |
| T-041b | 2026-05-22 | Spinoff gauntlet Gate 1 | refuted | — | — | Contribution Sharpe +0.000 vs +0.10 threshold; paused-tier-masking confound documented | `gauntlet_t041b_2026_05_22.md` |
| T-041c | 2026-05-23 | Spinoff paused-tier-masking ruled out | refuted | — | — | Clean 0→1.0× re-run identical FAIL; pattern fails Gate 1 legitimately | `t041c_paused_tier_masking_ruled_out_2026_05_23.md` |
| T-053 | 2026-05-23 | V/Q/A clustering prior | refuted | — | — | Max ρ within V/Q/A +0.316 (below 0.5 gate); no pruning needed | `t053_vqa_clustering_refuted_2026_05_23.md` |
| T-053b | 2026-05-25 | Multi-year window harness + T-057 12-yr re-verify | done | 13 | 13 | Multi-year harness shipped; T-057 REFUTED on 12-yr; first MBL Gate-0 PASS | `multi_year_window_harness_t053b_2026_05_25.md` |
| T-054 | 2026-05-12 | Production hunt() ticker= wiring fix | done | — | — | Engine D foundry_feature dead-letter closed; single-line fix unblocked T-022/23/24/38/52 cascade | `production_hunt_ticker_wiring_postfix_2026_05_12.json` |
| T-055 | 2026-05-22 | Engine B vol-target shipped defense-first | done | — | — | INERT in default; bitwise-identical canon md5 vs T-019 | `engine_b_vol_targeting_2026_05_12.md` |
| T-055c | 2026-05-22 | Vol-target A/B harness 5-yr-Alpaca | refuted | — | — | Marginal +0.256 mean, ci_low -0.140 crosses zero; regime-conditional | `engine_b_vol_targeting_ab_t055c_2026_05_22.md` |
| T-055d | 2026-05-22 | EWMA dominates rolling | done | — | — | 2025 trap eliminated; ci_low -0.046 MARGINAL; additive Engine B change | `engine_b_vol_target_ewma_t055d_2026_05_22.md` |
| T-055e | 2026-05-23 | Vol-target regime+EWMA 5-yr-Alpaca | superseded | — | — | First DEFENSIBLE +0.549 ci_low +0.047; later refuted on extended substrate | `engine_b_vol_target_regime_conditional_t055e_2026_05_23.md` |
| T-055g | 2026-05-24 | Vol-target multiplier sensitivity sweep | refuted | 75 | 75 | Substrate-honest re-run: no arm clears ci_low>0; 2022 sign-flipped | `vol_target_multiplier_sensitivity_t055g_2026_05_24.md` |
| T-055h | 2026-05-29 | Vol-target 12-yr verify | refuted | — | — | Δ Sharpe -0.214; vol-target chapter CLOSED on 12-yr window | `vol_target_12yr_verify_t055h_2026_05_29.md` |
| T-057 | 2026-05-23 | Confidence-gated execution N-threshold A/B | superseded | — | — | Original 5-yr-Alpaca +0.793 "strongest lift" later reversed | `confidence_gated_execution_2026_05_12.md` |
| T-057b | 2026-05-24 | Confidence-gated extended-substrate re-run | refuted | 50 | 50 | Δ -0.075, ci_low -0.532 iid / -1.154 block; regime-dependent floor-raiser | `confidence_gated_flag_flip_t057b_2026_05_24.md` |
| T-057c-det | 2026-05-24 | T-057c determinism root-cause | done | — | — | FP summation-order cross-container fix in signal_collector.py | `confidence_gate_determinism_t057c_det_2026_05_24.md` |
| T-057c-fp-followup | 2026-05-30 | FP determinism sweep | done | — | — | Defensive sort added at the 4 sibling cross-container summation sites | `fp_determinism_sweep_t057c_followup_2026_05_30.md` |
| T-066 | 2026-05-22 | Baseline metrics report (T-035 post-fix) | done | — | — | Per-edge rolling PSR + 5-yr-Alpaca breakdown | `baseline_metrics_report_t066_2026_05_22.md` |
| T-069 | 2026-05-22 | Pairwise conditional alpha analysis | done | — | — | Discovery-relevant pairwise correlations + α conditional on co-trigger | `pairwise_conditional_alpha_2026_05_22.md` |
| T-081 | 2026-05-23 | Stooq substrate extension to 1962/1970 | done | — | — | Extended-survivor window opened; delisted gap pre-2020 caveat documented | `substrate_extension_stooq_t081_2026_05_23.md` |
| T-082 | 2026-05-23 | Substrate merge + dividend-strip | done | — | — | Canonical substrate locked: Stooq + Alpaca dividend-strip merged | `substrate_merge_dividend_strip_t082_2026_05_23.md` |
| T-087 | 2026-05-30 | Engine E regime signal re-diagnosis | done | — | — | HMM p_crisis AUC 0.887 on 12-yr; reversed 2026-05-06 "refuted" verdict | `engine_e_regime_rediagnosis_t087_2026_05_30.md` |
| T-088 | 2026-05-31 | Risk-config key rename + filter hardening | done | — | — | risk_per_trade_pct confirmed DEAD KNOB on prod (Path B never runs); audit HIGH downgraded | `risk_config_keyfix_t088_2026_05_31.md` |
| T-089 | 2026-05-31 | Regime-validator causal-path verification | done | — | — | T-087's AUC 0.887 causal claim verified; 3 sibling validators fixed; lookahead inflation bounded +0.006 | `regime_validator_causal_fix_t089_2026_05_31.md` |
| T-090 | 2026-05-31 | Contract-test suite (silent-mismatch guard) | done | — | — | 10 parametric tests <1s; caught 3 known + surfaced 7 NEW silent-mismatch bugs | `contract_test_suite_t090_2026_05_31.md` |
| T-091 | 2026-05-31 | Contract-suite green-up + CI gate | done | — | — | Suite 10/10 green; PSR + Sortino added to producer; CI workflow shipped | `contract_suite_greenup_t091_2026_05_31.md` |
| T-092 | 2026-05-31 | Deep-substrate baseline 16-yr + 26-yr (Agent A) | done | 9 | 9 | PIVOT SIGNAL: Sharpe inverts with depth (16yr 1.018 ci_low 0.56 / 26yr 0.246 ci_low -0.119, fails every gate); strict ci_low>DSR-benchmark fails on ALL windows; det-drift scales with depth | `deep_substrate_baseline_t092_2026_05_31.md` |
| T-093 | 2026-05-31 | Doc-system overhaul Phase 1 | done | — | — | CURRENT_STATE + TASK_LEDGER + doc_lint + Audit/README index + nav edits | `doc_system_overhaul_phase1_t093_2026_05_31.md` |
| T-095 | 2026-05-31 | Fill-convention diagnostic (H-Convention, Agent B) | done | — | — | RESOLVED-CLEAN: backtest already fills t+1 OPEN; ~0.81 NOT a close-to-close artifact; Lou-Polk-Skouras leak N/A | `fill_convention_diagnostic_t095_2026_05_31.md` |
| T-096 | 2026-05-31 | Doc-system overhaul Phase 2 (hooks + NON_NEGOTIABLES split) | done | — | — | SessionStart/Stop externalized + fail-open; CLAUDE.md restructure; NON_NEGOTIABLES.md expanded copy | `doc_system_overhaul_phase2_t096_2026_05_31.md` |
| T-098 | 2026-05-31 | H-Band no-trade bands (Agent B, Engine C) | refuted | 36 | 36 | ±20/25% no Pareto win (Sharpe ci_low<0, turnover flat, skew mixed); clean default-OFF impl kept for tighter sweep; branch NOT merged | `no_trade_band_h_band_t098_audit_2026_05_31.md` |
| T-099 | 2026-06-04 | Long-window FP-determinism (T-057c-det pass 3) | done | — | — | 5 load-bearing sites fixed (signal_collector outer sort + portfolio_engine snapshot/total_equity + backtest_controller 2 equity-calcs); canonical-value INERT; single-container `--runs 3` PASS bitwise; cross-container cloud verify deferred (image rebuild). 6 new regression tests + 15/15 FP-determinism suite green. MERGED 253a96f | `long_window_determinism_t099_2026_06_04.md` |
| T-100 | 2026-06-04 | Crisis-path diagnostic (kill-switch Phase 0, Agent B) | done | — | — | MASTER FINDING: crisis defenses exist in code but were STARVED in the backtest — HMM not wired (0/1174 advisory calls got hmm_proba; hmm_enabled=false), 5-axis detector MISSED COVID (0 crisis bars May-Dec 2020), regime None pre-2020 (local SPY gap). risk_scalar 46% cut lives on DEAD Path B (confirms T-088, refutes audit static-read). Verdict (c): Phase 0+ (autonomous: hmm_enabled=true) + Phase 0b (cloud 2008/dotcom cell) + Phase 1 (Engine B kill-switch) | `crisis_path_diagnostic_t100_2026_06_04.md` |
| T-104 | 2026-06-05 | Dead advisory consumers diagnose+propose (Agent B, propose-first) | done | — | — | **correlation_regime HIGH** — sector-cap-tightening branch DEAD in 847/1175=72.1% of bars; producer emits nested dict at top level instead of flat string in advisory[]. 1-line proposed fix + canon-md5 A/B (OFF 0145c03a6496… → ON 16f872fe2d99…, DIFFERS); NOT applied (director-gated). **allocation_recommendation LOW** — INTENDED-DISK-SOURCE per `policy.py:62-80` fallback; allowlist comment sharpened (autonomous test-hygiene). Zero engines/ edits in final commit. | `dead_advisory_consumers_t104_2026_06_05.md` |
| T-101 | 2026-06-04 | HMM kill-switch Phase 0+ — wire hmm_enabled=true + verify (Agent B, Engine E config only) | done | — | — | Q1' YES posterior flows (1174/1174 calls); Q2'/Q3' NO change (regime_summary derives from 5-axis, gross delta identical, 2022 default-cell canon BITWISE IDENTICAL pre/post-flip); det 3/3. **CAPABILITY failure not WIRING** — HMM modulates risk_scalar on dead Path B; the -59% MDD is NOT a wiring gap. Phase 1 (Engine B propose-first) IS required. Flag flip kept (no-op for trades, observability win). | `hmm_wire_phase0plus_t101_2026_06_04.md` |
| T-102 | 2026-06-04 | capability_ledger.md + contract Layer 3a/3b (Agent A) | done | — | — | NEW living doc: `docs/State/capability_ledger.md` (34 rows; HIGH-defensive coverage; Path-B-relevant marked). Contract suite Layer 3a (ledger Source(file:line) symbol-resolution) + Layer 3b (cross-engine advisory reader⊆writer) shipped. STRICT layer 3b xfail surfaces 2 OPEN-BUG dead consumers: `correlation_regime` (Engine B reads flat str; E emits nested dict) + `allocation_recommendation` (Engine C reads with disk fallback). Both flagged for propose-first repair; NOT silenced by code edit. Suite 14 passed + 1 xfailed in 1.8s wall. | `capability_ledger_contract_layer3_t102_2026_06_04.md` |
| T-103 | 2026-06-04 | HMM crisis-inclusive retrain + held-out OOS validation (Agent A) | done | — | — | REPOINT JUSTIFIED on combined posterior (p_crisis+p_stressed), NOT on p_crisis alone. New `hmm_3state_crisis_v1.pkl` (train 2006-04→2019-12; existing model PRESERVED). Combined posterior ≥0.5 fires on 3/3 held-out crises with 28-58d lead and max_p=1.000 (COVID 28d, 2022 58d, 2025 43d). OOS AUC@5d=0.914 ci_low 0.880; OOS@10d=0.864 ci_low 0.814. Crisis-trained HMM concentrates "crisis" label into 2008-magnitude tail only (6.1% of train days); state labels are training-distribution-dependent. Binding data floor 2006-04-04 (DTWEXBGS+63d warmup). NO engine logic touched. | `hmm_crisis_retrain_t103_2026_06_04.md` |
| T-105 | 2026-06-05 | HMM repoint window re-validate + dwell-time (Agent A) | done | — | — | **AUC SURVIVES** at LIVE 60-bar window (OOS@5d 0.919 ci_low 0.885 vs T-103@252 0.914/0.880 — marginally HIGHER); per-event TPR identical 7/7 at both windows; **BUT DWELL FAILS** — p_combined≥0.5 frac-above=44-50%, median run 12-19d OK but **p90 198-265d** and **max 348-632d**. Operative horizon = 10d (ci_low 0.815). VERDICT: **DEGRADED-BUT-OK as TRANSITION-TRIGGER; NOT-OK as LEVEL.** Repoint design must shift from threshold-on-level to Δp / decay-after-fire / co-condition. NO engine logic touched. | `hmm_repoint_window_revalidate_t105_2026_06_05.md` |

## Closed-pre-T-035 (digest only)

Older tasks (T-001 to ~T-034) are summarized in `MEMORY.md` and the `docs/Sessions/2026-04/` summaries. Not backfilled here because the audit-doc trail is sparser and the cloud-cells columns don't apply.

## Convention notes

- **`cells_attempted` / `cells_succeeded`**: cloud-campaign cell counts (when AWS Batch submitted N cells; useful for honest-N accounting per the MBL constraint). For local-only or non-campaign work, both columns are `—`.
- **`superseded`**: the task closed with a verdict that has since been overturned by a newer, more rigorous measurement. The audit doc still STANDS as the historical record; do not re-edit it. The supersession is tracked here + in the relevant audit's commit message of the superseding task.
- **`refuted`**: the task closed with a negative verdict (the hypothesis it tested did NOT clear the gate). Distinct from `superseded` (which was originally positive but later overturned).
