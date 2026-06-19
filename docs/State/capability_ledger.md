# Capability Ledger — ArchonDEX

> **Purpose:** flat index of every BEHAVIOR-ALTERING capability the code currently ships, on which path, behind which flag, with honest reachability. This is the missing axis the decision-centric docs (CURRENT_STATE / TASK_LEDGER / MEMORY) couldn't carry: those track VERDICTS; this tracks CAPABILITY STATE.
>
> **Role:** when an A/B is REFUTED, the surviving default-off knob becomes nobody's documentation responsibility — until now. A row here for every shipped capability surfaces "what's still on the path even after this verdict."
>
> **Source:** the 2026-06-04 engine-capability-gap audit (`docs/State/health_check.md`, search "engine-auditor 2026-06-04"). T-100 (`docs/Audit/crisis_path_diagnostic_t100_2026_06_04.md`) refined the "Wired-to-live-path?" column for the Engine B Path-A-vs-Path-B sizing fork.
>
> **Authority boundary:** this file owns CAPABILITY STATE. `docs/State/CURRENT_STATE.md` owns verdicts/decisions. A refuted finding that leaves a shipped flag should point HERE for what's still on the path.
>
> **Wired-to-live-path? values:** `yes` (active on the prod-arm0 backtest path), `no` (gated off, orphaned, or on a dead sizing branch), `mode-gated` (reachable only under a specific runtime mode flip), `unknown — needs trace` (honest uncertainty; capacity not bisected).
>
> **CI-gated:** `tests/test_contracts.py::Layer 3a` verifies that every `Source (file:line)` here still resolves (file exists, symbol matches). Line-number drift WARNs; missing file/symbol FAILs. See `docs/Audit/capability_ledger_contract_layer3_t102_2026_06_04.md` for the contract spec.

## Engine A — Alpha (signal forecast)

| Capability | Engine | Source (file:line) | Wired-to-live-path? | Prod-flag-state | Defensive/Path-B relevance | Notes |
|---|---|---|---|---|---|---|
| Engine A consumes `advisory["risk_scalar"]` as a crisis de-gross brake (multiplies edge norms when regime_summary ∈ {stressed, crisis}) | A | `engines/engine_a_alpha/signal_processor.py:543` | yes | `risk_advisory_enabled` defaults True; advisory active in prod | HIGH — second crisis de-gross path in A, double-count with B per charter Matrix | health_check 2026-06-04 HIGH: A double-counts B's risk_scalar; charter says A predictive, B protective |
| Engine A consumes `advisory["learned_edge_affinity"]` (0.3-1.5× per-category multiplier) | A | `engines/engine_a_alpha/signal_processor.py:563` | no | Writer at `backtester/backtest_controller.py:348` is gated by `regime_conditional_enabled=false` in `config/governor_settings.json:13` | HIGH | Consumer reads `.get(..., {})` → silently `{}` in prod; Engine F producer (regime_tracker.py:180) shipped but never injected. Path-B-relevant lever for regime-conditional de-weighting |
| `macro_yield_curve_edge` ACTIVE — uniform -0.3 tilt across universe on 10Y-2Y inversion | A | `engines/engine_a_alpha/edges/macro_yield_curve_edge.py:173` (tilt logic), `:199` (status="active") | unknown — needs trace | Auto-registers active; FIRES only when FRED cache populated. Live `data/governor/edges.yml` status not verified in this dispatch | HIGH — pre-existing crisis-defensive overlay; T-092 Path-B kill-switch must account for this | health_check 2026-06-04 MEDIUM A entry; in charter terms safety-oriented gating belongs in B |
| `macro_credit_spread_edge` retired (status="retired") | A | `engines/engine_a_alpha/edges/macro_credit_spread_edge.py` | no | Auto-register retired (2026-05-02 reclassified as HMM input) | MEDIUM — inert ready-made defensive tilt | sibling of yield-curve edge; re-activates if a future caller loads it |
| `macro_unemployment_momentum_edge` retired | A | `engines/engine_a_alpha/edges/macro_unemployment_momentum_edge.py` | no | Auto-register retired | MEDIUM | same family as credit-spread; inert by default |
| `macro_real_rate_edge` retired | A | `engines/engine_a_alpha/edges/macro_real_rate_edge.py` | no | Auto-register retired | MEDIUM | same family as credit-spread |

## Engine B — Risk / Sizing

| Capability | Engine | Source (file:line) | Wired-to-live-path? | Prod-flag-state | Defensive/Path-B relevance | Notes |
|---|---|---|---|---|---|---|
| Crisis-floor on `suggested_max_positions` (5 in crisis, 7 in stressed) | B | `engines/engine_b_risk/risk_engine.py:729` (consumer); `engines/engine_e_regime/regime_config.py:105-106` (config defaults) | yes | `risk_advisory_enabled` defaults True in prod | HIGH — active de-gross knob | health_check 2026-06-04: motivated this audit, in NO living doc |
| Engine B `risk_scalar` consumption in sizing | B | `engines/engine_b_risk/risk_engine.py:739` | **no (dead Path B)** | Path B (atr_risk) sizing branch — prod uses Path A (target_weight) per T-088 | HIGH | T-100 diagnostic refined the audit's "active" claim: this consumer is on the dead atr-risk branch in prod (Engine C target_weight path actually fires). **Engine A's risk_scalar consumer (signal_processor.py:543) is the live one.** |
| `suggested_exposure_cap` consumption (de-gross) | B | `engines/engine_b_risk/risk_engine.py:736` | yes | `risk_advisory_enabled` defaults True | HIGH | Double-consumed with Engine C policy.py:380 — boundary unclear per audit |
| **`correlation_regime` sector-cap branch — DEAD CONSUMER** | B (reader) / E (producer) | `engines/engine_b_risk/risk_engine.py:744` reader; `engines/engine_e_regime/regime_detector.py:259` writes top-level (NESTED dict, NOT advisory[]) | **no** | Read defaults to "normal"; writer puts `correlation_regime` as nested dict on `output`, NOT into `advisory` | HIGH — charter-documented Matrix entries for "Elevated Correlation" / "Dispersed Correlation" silently dead | **Test/contract Layer 3b surfaces this as FAIL**. Fixing it is propose-first (Engine B/E boundary decision). |
| Regime-conditional vol-target multipliers (cautious 0.85 / stressed 0.60 / crisis 0.40) | B | `engines/engine_b_risk/risk_engine.py:112` (config); `engines/engine_b_risk/vol_target.py:251` (consumer) | no | Gated by BOTH `portfolio_vol_target_enabled=False` AND `portfolio_vol_target_regime_aware=False` | HIGH — Refuted on 12-yr (T-055h) but CAPABILITY still ships | MEMORY recorded the negative VERDICT; the surviving default-off knob has no doc home until this ledger |
| Drawdown-gated kill switch (5/10/15% thresholds) — legacy Path-B-only consumer | B | `engines/engine_b_risk/risk_engine.py:83` (config), `:940` (Path-B consumer) | **no (dead Path B even when flag flipped True)** | `drawdown_kill_switch_enabled=False` default | HIGH | T-106 confirmed: even with flag enabled, halt/degrade lives inside Path-B `else:` (line 867); prod uses Path A so block never executes. T-111 PoC adds a pre-path lift behind `drawdown_kill_switch_apply_on_path_a` (default OFF). |
| T-111 PoC — Path-A lift of drawdown kill-switch (pre-path halt + Path A `target_notional` multiplier) | B | `engines/engine_b_risk/risk_engine.py:88` (flag), `:826` (pre-path block), `:884` (Path A `target_notional *= _drawdown_size_mult`) | mode-gated (PoC) | `drawdown_kill_switch_apply_on_path_a=False` default; only effective with `drawdown_kill_switch_enabled=True` | HIGH — reference implementation of the T-106 1-block lift-out fix | T-111 canon A/B: OFF == `0145c03a6496…` (≡ T-101 baseline); ON == `52202e510d27…` (DIFFERS). Determinism `--runs 3` PASS on default OFF. Director-gated A/B campaign on 16-yr + 26-yr required before any default-flag change. |
| `FactorRiskModel` (factor-neutrality) | B | `engines/engine_b_risk/factor_analysis.py` | **no — orphaned** | Zero importers in the repo | MEDIUM | Audit: archive to `Archive/` if it stays unwired, or document intended consumer |
| Regime-conditional ATR stop-widening (high vol → wider stops) | B | `engines/engine_b_risk/risk_engine.py:59-62` (config), `:875` (consumer block) | **no (dead Path B)** | Lives in Path B (atr_risk); prod uses Path A | LOW — same dead-Path-B caveat as risk_scalar consumer | Charter Design Notes mentions "Regime-based stop widening — Keep"; reality is dead-Path-B |

## Engine C — Portfolio Composition

| Capability | Engine | Source (file:line) | Wired-to-live-path? | Prod-flag-state | Defensive/Path-B relevance | Notes |
|---|---|---|---|---|---|---|
| Regime-aware vol-target upside ceiling (caps leverage to 1.0× in market_turmoil/cautious_decline/stressed/crisis; 1.4× transitional; legacy 2.0× benign) | C | `engines/engine_c_portfolio/policy.py:334` | **mode-gated** | Reachable ONLY in adaptive-mode branch. Prod `config/portfolio_settings.json` sets `mode: mean_variance`. `_apply_regime_overrides` (policy.py:86) can flip mode to "adaptive" per regime via `data/research/allocation_recommendations.json` (which recommends adaptive for every regime). | HIGH | health_check 2026-06-04 Engine C MEDIUM entry — Engine-C sibling to Engine B's 0.40 crisis multiplier |
| Vol-target downside floor (0.3× — keep ≥30% gross even in vol spikes) | C | `engines/engine_c_portfolio/policy.py:340` | mode-gated | Same gate as ceiling above | MEDIUM | charter (line 256) only mentions "0.3-2.0× clamp"; asymmetric/regime-aware shape invisible |
| Engine C `_apply_exposure_cap` (consumes `advisory["suggested_exposure_cap"]`) | C | `engines/engine_c_portfolio/policy.py:380` | mode-gated | adaptive-mode only | HIGH — double-consumed with Engine B `risk_engine.py:736` | Boundary ownership C-vs-B not stated in charter |
| `MultiSleeveAggregator` (sleeve composition framework) | C | `engines/engine_c_portfolio/sleeves/aggregator.py` | **no — never wired** | Default-OFF; no caller in `BacktestController` | HIGH — Path-B Layer 2 may be partly pre-built | CURRENT_STATE Layer 2 entry didn't note this exists |
| `TrendFollowingSleeve` (CTA momentum + inverse-vol) | C | `engines/engine_c_portfolio/sleeves/trend_following_sleeve.py` | no — never wired | Default-OFF | HIGH — pre-built defensive sleeve | same as MultiSleeveAggregator |
| `MoonshotSleeve` (asymmetric-upside) | C | `engines/engine_c_portfolio/sleeves/moonshot_sleeve.py` | no — never wired | Default-OFF | MEDIUM | shipped Phase A; never integrated into controller |
| `EngineCAllocator` (charter + index.md reference) | C | _missing — file does not exist_ | **n/a — file missing** | Charter + index.md refer to `allocator.py` but no such file | LOW | health_check 2026-06-04 Engine C MEDIUM: regenerate auto-ref via `scripts/sync_docs.py` |
| `allocation_recommendation` consumer in policy | C | `engines/engine_c_portfolio/policy.py:62` | unknown — needs trace | Reads `advisory["allocation_recommendation"]`; falls back to disk-load via `AllocationEvaluator.load_recommendations()` | LOW | No engine-layer producer puts `allocation_recommendation` into `advisory`; the disk fallback is the de-facto producer |

## Engine D — Discovery

| Capability | Engine | Source (file:line) | Wired-to-live-path? | Prod-flag-state | Defensive/Path-B relevance | Notes |
|---|---|---|---|---|---|---|
| Gate 0 — MBL pre-flight (`mbl_sr_target=1.0` default) | D | `engines/engine_d_discovery/discovery.py:869` (validate_candidate entry) | yes (`--discover` path) | Default ON | LOW | Charter claims "4-Gate" pipeline; actual code runs 8 gates |
| Gate 5 — Universe-B production-equivalent transfer | D | `engines/engine_d_discovery/discovery.py` (gate 5 block within validate_candidate) | yes (`--discover` path) | Default ON | LOW | Wired live in `orchestration/mode_controller.py:1209` |
| Gate 6 — FF5+Mom factor-alpha (t>2 AND α>2%) | D | `engines/engine_d_discovery/discovery.py` (gate 6 block) | yes (`--discover` path) | Default ON | MEDIUM — already enforces factor-adjusted alpha at promotion (audit's claim docs say only "significance"; reality includes factor-α) | T-043 was a SIBLING gate at retirement; Gate 6 is at promotion |
| Gate 7 — Substrate-transfer drift (historical S&P 500) | D | `engines/engine_d_discovery/discovery.py` (gate 7 block) | yes (`--discover` path) | Default ON | LOW | Path-B-relevant for substrate-honest validation |
| Gate 8 — DSR multiple-testing deflation | D | `engines/engine_d_discovery/discovery.py` (gate 8 block) | yes (`--discover` path) | Default ON | LOW | Project's accumulated-N reflated benchmark applied at promotion |
| Macro genes — `vix_level`, `yield_curve`, `unemployment_delta` (10% emit rate) | D | `engines/engine_d_discovery/discovery.py:496` (`_create_random_gene`) | yes when `--discover` fires | Default ON in GA | HIGH — Engine D ALREADY capable of discovering crisis-aware edges | Resolved by `engines/engine_a_alpha/edges/composite_edge.py:181` macro handler |
| Behavioral genes — `panic_score`, `herding_breadth` (5% emit rate) | D | `engines/engine_d_discovery/discovery.py:496` | yes when `--discover` fires | Default ON in GA | MEDIUM | resolved by composite_edge behavioral handler |
| Regime genes — `is bear` (5% emit rate) | D | `engines/engine_d_discovery/discovery.py:496` | yes when `--discover` fires | Default ON in GA | HIGH | regime-conditional edge discovery, Path-B-relevant |
| Short / market-neutral direction emission (10% / 10% emit rate) | D | `engines/engine_d_discovery/discovery.py:353-357`; `engines/engine_d_discovery/genetic_algorithm.py:157-163` | yes when `--discover` fires | Default ON in GA | HIGH — hedge/short edge discovery is existing capability lever | Resolved by composite_edge sign at line 150 |

## Engine E — Regime Detection / Advisory

| Capability | Engine | Source (file:line) | Wired-to-live-path? | Prod-flag-state | Defensive/Path-B relevance | Notes |
|---|---|---|---|---|---|---|
| Advisory output dict (regime_summary / risk_scalar / suggested_exposure_cap / suggested_max_positions / edge_affinity / caution_note / regime_confidence) | E | `engines/engine_e_regime/advisory.py:242` | yes | `risk_advisory_enabled` defaults True; advisory built every bar | HIGH — primary cross-engine defensive contract surface | Layer 3b test enforces reader⊆writer |
| `regime_transition_warning` advisory extension | E | `engines/engine_e_regime/regime_detector.py:246` | yes | Set when transition warning fires | LOW | Read-only diagnostic; no consumer branches on it |
| Multi-resolution advisory blend (`multires_advisory`) | E | `engines/engine_e_regime/regime_detector.py:244` (`advisory.update(multires_advisory)`) | yes if multi-resolution detector active | mode-dependent | LOW | Surfaced into advisory but consumer-side check is opaque |
| HMM Variant C (minimal_c feature_set; 4 long-history FRED + hyg_ig_oas + copper_gold_ratio + xlp_xly_ratio) | E | `engines/engine_e_regime/regime_config.py:121` (config); model artifact `engines/engine_e_regime/models/hmm_minimal_C_v1.pkl` | no | `hmm_enabled=true` since T-101 (2026-06-04) BUT prod `config/regime_settings.json:99-105` selects `feature_set="legacy"` — minimal_c not selected | HIGH — Path-B HMM kill-switch foundation | T-087 validated AUC 0.887 on 12-yr; T-101 testing |
| HMM Variant A/B (legacy + minimal_a/b feature sets) | E | `engines/engine_e_regime/regime_config.py:121` (enum) | posterior computed every bar; consumed by nothing that sizes a trade (T-101: bitwise-identical trades pre/post flip) | `hmm_enabled=true` since T-101; prod loads `hmm_3state_v1.pkl` (legacy) | MEDIUM | Multiple model artifacts shipped: `hmm_3state_v1.pkl`, `hmm_minimal_A_v1.pkl`, `hmm_minimal_B_v1.pkl`, `hmm_3state_vix_term_v1.pkl`, `hmm_monthly_v1.pkl`, `hmm_weekly_v1.pkl` |
| **Validated crisis HMM (`hmm_3state_crisis_v1.pkl`, T-103/T-105: OOS AUC@5d 0.914-0.919, combined posterior)** | E | model artifact `engines/engine_e_regime/models/hmm_3state_crisis_v1.pkl`; referenced ONLY by `Archive/scripts/train_hmm_crisis_t103.py`, `scripts/validate_hmm_*_t10{3,5}.py`, `scripts/gen_t118_campaign_spec.py` | **no — never loaded by production** (`config/regime_settings.json:101` points at legacy `hmm_3state_v1.pkl`, the AUC-0.49 false-negative model T-087 reversed) | Repoint is propose-first; T-118 drives its overlay with the crisis model; if it wins, production repoint rides along (separate gate) | **HIGH — the project's single validated predictive signal is not the model production runs** | Flagged by 2026-06-11 fresh-view review; previously discoverable only inside the T-118 audit doc |

## Engine F — Governance / Lifecycle

| Capability | Engine | Source (file:line) | Wired-to-live-path? | Prod-flag-state | Defensive/Path-B relevance | Notes |
|---|---|---|---|---|---|---|
| `RegimePerformanceTracker.get_learned_affinity()` → advisory["learned_edge_affinity"] | F | `engines/engine_f_governance/regime_tracker.py:180` (producer); `backtester/backtest_controller.py:348` (injector) | **no** | Injector gated by `regime_conditional_enabled=false` in `config/governor_settings.json:13` | HIGH — Path-B lever for regime-conditional crisis de-weighting | health_check 2026-06-04 HIGH F entry; charter presents as active, code default is inert |
| Factor-α retirement gate (T-043) | F | `engines/engine_f_governance/lifecycle_manager.py:614`; `engines/engine_f_governance/factor_alpha_gate.py` | **no — call-site bug** | `factor_alpha_enabled=True` but production caller `governor.evaluate_lifecycle` doesn't pass `factors=`, so the body short-circuits | HIGH | Charter Invariant 4 ("Edge demotions require statistically significant underperformance") — invisibly inert in autonomous loop |
| `regime_conditional_enabled` regime-conditional weight blending | F | `engines/engine_f_governance/governor.py` (`_rebuild_regime_weights_from_tracker`, `get_edge_weights(regime_meta=)`) | no | `regime_conditional_enabled=false` in prod | HIGH — same flag as learned_edge_affinity above | Path-B lever |
| `RegimePerfAnalytics` module reference | F | _missing_ | n/a | Charter + `engines/engine_f_governance/index.md:15` reference file that does not exist | LOW | Resolved by `scripts/sync_docs.py` regeneration or restoring from Archive |

## Cross-cutting

| Capability | Engine | Source (file:line) | Wired-to-live-path? | Prod-flag-state | Defensive/Path-B relevance | Notes |
|---|---|---|---|---|---|---|
| `enforce_target_allocations=True` makes Engine B Path A (target_weight) live; Path B (atr_risk) is dead in prod | B | `engines/engine_b_risk/risk_engine.py:51` (config), `:817` (Path A); `:867` (Path B) | Path A: yes / Path B: **no** | `enforce_target_allocations=True` default; ALSO `target_weights` always passed by controller in prod | foundational — many "active" capabilities in audit actually sit on Path B and are dead in prod | T-088 found this; T-100 quantified it; affects every Engine B sub-capability whose code lives in lines 867+ |

## How to add a row

1. Identify a behavior-altering capability — code that, when toggled, changes a backtest trade or live order. Pure logging, doc strings, or test scaffolding are NOT capabilities; do not add rows for them.
2. Fill all 7 columns. `Source (file:line)` must resolve — Layer 3a is gated CI.
3. For `Wired-to-live-path?`, do the 3-way join: config-flag × wiring-guard × path-reachability. Use `unknown — needs trace` if any leg is unverified. False precision is the bug this ledger exists to prevent.
4. Cross-link a verdict doc that refutes the capability's lift but leaves the knob alive (e.g., T-055h refuted vol-target but `portfolio_vol_target_crisis_multiplier=0.40` ships).

## Coverage stat

- Rows: ~34 (HIGH-defensive: 11; Path-B-relevant marked).
- Source: 11 engine-auditor 2026-06-04 entries in `docs/State/health_check.md` (each entry expanded into 2-5 capability rows).
- Authority: this file is the canonical CAPABILITY INDEX. Verdicts/decisions remain in CURRENT_STATE.md.
