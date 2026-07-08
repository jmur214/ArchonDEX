# Code Health Tracker

Living document tracking the current quality state of the codebase. 
Maintained by the `engine-auditor` and `code-health` subagents — they 
append findings as they discover them. Resolved items move to the 
"Resolved" section with a date.

This is the source of truth for SESSION_PROCEDURES.md Path 2 
("Critical findings"). When the user asks what's next, this file is 
checked before the roadmap.

If this file appears empty or stale, run the engine-auditor against 
recently-touched engines or the code-health subagent across the 
codebase to populate it.

---

## Active Issues

Findings are listed in priority order: HIGH first, then MEDIUM, 
then LOW. Within each severity, list newest at the top.

### HIGH

### [HIGH] Info-Layer fresh-eyes audit findings (external read-only review, 2026-07-08)
- Engine: cross-cutting (ingest layer / paper_trader / info-layer program)
- First flagged: 2026-07-08 (fresh-eyes agent, zero-prior-context repo review). Full report: `data/coordination/fresh_eyes_report_2026_07.md` (gitignored relay copy — findings itemized here so they persist in git).
- Status: **#1 and #3 RESOLVED same-day**; #2 folded into T-288/program-doc amendments; #4 partially resolved by the T-289/290/291/293 merge wave; #5 is by-design (Lane 3 not yet built).
  - **[HIGH → RESOLVED 2026-07-08] Archivers cannot fail loudly on the launchd path.** `archive_altdata_t136.py` and `archive_positioning_t136.py` return 0 unconditionally (failures are strings) → the wrapper's failure token was structurally unreachable; silent capture loss possible. FIX: `scripts/verify_altdata_snapshot.py` (reuses the pulse orchestrator's `_SNAPSHOT_FRESHNESS`/`_fresh_rows` so the two paths can't drift) now runs after every launchd capture; any failure alarms via SNS + local macOS notification fallback. RESIDUAL: `sns:Publish` IAM grant for `claude-code-cli` on `archondex-paper-alerts` pending user action — until then the alarm is local-notification-only.
  - **[HIGH — OPEN, owned by E/T-288] No per-account pulse pattern exists.** `run_paper_cloud_day.py` is hardwired single-account; the fleet (accounts 2/3) and the Stage-2 LLM account require a NET-NEW multi-account generalization, not a clone. Program doc amended. Also `CloudState` is a small-file sync, not an archive layer — growing stores (news panel, analyst notes) need a sizing check before routing through it (D asked for panel GB estimate).
  - **[MEDIUM → RESOLVED 2026-07-08 by amendment] Phase A (18:30 ET) vs Phase B (09:45 ET) capture-time discontinuity.** Resolution: launchd is PERMANENT (canonical local EOD series); the pulse capture is a separate pre-open series on S3. Neither retires into the other.
  - **[MEDIUM — LARGELY RESOLVED by the merge wave] Zero tests on the new senses at review time.** Now: `test_altdata_archive_t290.py` (9), `test_macro_calendar_t290.py` (5), `test_event_state_detector_t291.py` (7), `test_analyst_eval_t293.py` + panel tests. RESIDUAL: the T-136 archiver scripts themselves remain untested (string-status legacy design) — acceptable while the verifier gates their output; revisit if they grow.
  - **[NOTE — by design] Lane 3 safety is unbuilt** (`intelligence/analyst/` firewall/governor/injection suite are greenfield until E/T-292). The authority ladder is doc-policy until then; `btc_shadow.py`'s signal-t/fill-t+1 template is the confirmed-good containment pattern to generalize.

### [HIGH] Documentation-system integrity findings (external fresh-eyes audit 2026-06-19)
- Engine: docs/knowledge-system (cross-cutting)
- First flagged: 2026-06-19 (external reviewer, read-only audit; commissioned via commit `3717210`)
- Status: not started — itemized below. Full write-up: `docs/Sessions/Other-dev-opinion/06-19-26_doc-system-audit.md`.
- Description: cold-onboarding + verification audit of the doc system found the self-correction layer is partly dead and the always-loaded constitution carries stale headline numbers. Items (severity in brackets; **PROPOSE-FIRST** = touches the doc system itself per CLAUDE.md "Changes to the documentation system itself", so user-gated, NOT autonomous):
  - **[HIGH] `doc_lint.py` runs, prints `[FAIL]`, and exits `0`.** Live `python scripts/doc_lint.py --pre-commit`: `[FAIL] TASK_LEDGER rows complete: 11 issue(s)` + 3× `[WARN]` because `MEMORY_DIR` is hardcoded to `/root/.claude/projects/-Users-jacksonmurphy-Dev-trading-machine-2/memory/` (macOS/old-repo path, absent) → `EXIT: 0`. `--no-verify`-skippable; no CI backstop (`feature_ablation.yml` only backs the Foundry gate). The one automated guard for memory/supersession hygiene protects nothing here. **[PROPOSE-FIRST]**
  - **[HIGH] "MEMORY.md" is a phantom file.** CLAUDE.md (supersession non-negotiable) + CURRENT_STATE.md reference a single "MEMORY.md" that does not exist; only 6 per-agent `.claude/agent-memory/<agent>/MEMORY.md` exist. `SESSION_PROCEDURES.md:463` adds a third dead path. "Follow the supersession pointer" is unresolvable. **[PROPOSE-FIRST]**
  - **[HIGH] Constitution carries stale numbers that "win".** `CLAUDE.md:131`/`NON_NEGOTIABLES.md:116` baseline `0.598` (+ `~75` N_trials, `CLAUDE.md:129`) vs live `0.751`/`~0.81` and `125`/`~260+` (`CURRENT_STATE.md:13,73,74`). `health_check.md` (this file, ~L689) already says "Do not quote 0.598 as current," yet CLAUDE.md (auto-loaded, precedence) still does → wrong DSR/MBL bar seeded every session. **[PROPOSE-FIRST]**
  - **[HIGH] "Archive, never delete" data-loss path.** `.gitignore:44` bare `Archive/` also matches `docs/Archive/` (`git check-ignore` confirmed) → any *newly*-archived doc is silently un-committable and lost on ephemeral-container reclaim. **[PROPOSE-FIRST]**
  - **[MEDIUM] Generated `index.md` systemically stale.** `sync_docs.py` output staged/committed in only ~2/22 engine-code commits; e.g. `engine_b_risk/index.md` missing the T-209 `decompose()` backbone. Fix = doc_lint check that `index.md` matches a fresh regen. **[PROPOSE-FIRST]**
  - **[MEDIUM] Second, contradictory instruction system at root.** `.agent/` + `.aider.conf.yml` (GPT-4.1-mini): broken charter path (`.agent/rules.md:7` → `docs/Audit/engine_charters.md`, absent), looser approval rules than CLAUDE.md (`.agent/rules/terminal-commands.md`), stale governor filenames. Archive or reconcile. **[PROPOSE-FIRST]**
  - **[MEDIUM] CURRENT_STATE.md internal contradiction + uncapped header.** 26yr ci_low printed as both `0.371` (`:13` table) and `0.382` (`:17,37`); ~1,100-word header exempt from the §`:27` hard caps. **[PROPOSE-FIRST]**
  - **[MEDIUM] SessionStart surfacing grep is brittle.** `grep -E "^### \[(HIGH|MEDIUM)\]"` misses live findings titled `### [MEDIUM 2026-06-04 by engine-auditor] …`; 4 are never surfaced. **[PROPOSE-FIRST]**
  - **[LOW → RESOLVED 2026-06-18 (doc-overhaul sweep)] Content drift.** Product-name sweep done (`GOAL.md` title+`:4`, `PROJECT_CONTEXT.md` headings/prose → ArchonDEX; absolute-path and meta uses of `trading_machine-2` left intact). `docs/Core/README.md` "Beyond docs/Core/" table fixed (`health_check.md`/`lessons_learned.md`/`high_level_engine_function.md` mislocations, `forward_plan_<DATE>` → `State/forward_plan.md`, `docs/Archive/` no-longer-gitignored, root `DOCUMENTATION_SYSTEM.md` → `docs/Archive/DOCUMENTATION_SYSTEM_legacy.md`). `PROJECT_CONTEXT.md:18,101-102` re-tagged `[INTENDED — NEVER-BUILT … see DESIGN_FIDELITY/T-208/T-216]` (the conjunctive selector); `:86` Live-Trading status corrected to paper-only-on-cloud + stub-archived. `:79` (Engine C "allocation wall not yet enforced") left as-is — consistent with the "Planned" sleeves note at `:27`, no DESIGN_FIDELITY contradiction. `deployment_boundary.md:85` ("A3 in trading_machine-2") left as borderline path/name. Frozen Sessions/Measurements relative-path breaks left for review (see doc-overhaul report).
- Recommended next step: triage the [PROPOSE-FIRST] items with the user (they touch CLAUDE.md/hooks/linter/gitignore). The [LOW] content-drift sweep is within autonomous doc-authority and can be done without a gate. AI-memory rot + the director-invisible "is the autonomous vehicle even right?" objection (`architect/strategic_frame_..._2026_06_15.md:41`) are captured in the full note §3-I.

### [RESOLVED] `brokers/alpaca_broker.py` reads a non-existent env var name → can never authenticate (dead stub)
- Engine: execution / live_trader (broker layer)
- First flagged: 2026-06-13 (Agent E, during T-160)
- Status: **RESOLVED 2026-06-15 (T-169 PR-4)** — `brokers/alpaca_broker.py`, `live_trader/`, and `storage/state_manager.py` archived to `Archive/pr4_dead_live_stub_t169/`; its only consumer (the never-constructed, fill-fabricating `AlpacaExecutionAdapter` in `mode_controller`) is deprecated (raises). The real order path is `paper_trader/`.
- Description: `brokers/alpaca_broker.py` reads the env var **`ALPACA_API_SECRET`**, a name that does not exist in `.env` (which defines `ALPACA_SECRET_KEY`). So this broker stub could never have authenticated — it is dead on its own terms, independently of also being superseded by the T-160 `paper_trader/` package. Sibling of the silent-mismatch family (config/env key name ≠ the consuming reader's expected name). Doubly-dead: wrong env name AND superseded.
- Resolution path: **PR-4 (hard-gated)** of the paper-trading build archives `brokers/alpaca_broker.py` + the `live_trader/` stub + `storage/state_manager.py` to `Archive/` and moves the deployment boundary. Until then leave it (don't repair a stub slated for archival) — flagged here so nobody mistakes it for a working broker path.
- Cross-ref: `docs/Core/paper_trading_readiness_design_t159.md` §1 (stub-archival decision, user-ratified 2026-06-12); T-160 audit.

### [HIGH] Engine F learned-affinity producer is DEAD on production path (regime_conditional_enabled=false)
- Engine: F
- First flagged: 2026-06-04
- Status: not started
- Description: `RegimePerformanceTracker.get_learned_affinity()` (regime_tracker.py:180) produces the `advisory["learned_edge_affinity"]` key that `engine_a_alpha/signal_processor.py:563` consumes (0.3-1.5x per-category multiplier on edge norms). The ONLY caller in the repo is `backtester/backtest_controller.py:346-348`, gated behind `regime_conditional_enabled`. In `config/governor_settings.json:13` that flag is `false`. So in production the multiplier is never injected, the consumer always sees `{}`, and the whole regime-conditional-weight chain (`_rebuild_regime_weights_from_tracker`, `get_edge_weights(regime_meta=...)` blending) is also disabled (same flag). Capability is shipped + wired end-to-end but switched OFF; NONE of CURRENT_STATE.md/MEMORY.md/index reflect the default-OFF state.
- Charter reference: engine_charters.md §F Design Notes "Learned edge affinity | F computes per-category affinity via `get_learned_affinity(regime_label)` ... Injected into `regime_meta["advisory"]["learned_edge_affinity"]`". Charter presents as active; code default is inert.
- Recommended next step: Document default-OFF in CURRENT_STATE/charters. For Path B this is the existing lever for regime-conditional crisis de-weighting (kills edges whose per-regime Sharpe <= 0 via `get_regime_weight`). Re-verify lift on canonical substrate before flag-flip (CLAUDE.md `[NN-SUBSTRATE-REVERIFY]`).

### [HIGH] Engine F factor-α retirement gate (T-043) is inert on every live/backtest lifecycle call
- Engine: F
- First flagged: 2026-06-04
- Status: not started
- Description: `LifecycleConfig.factor_alpha_enabled` defaults `True` (lifecycle_manager.py:224); a full FF5+Mom HAC bootstrap retirement gate exists (factor_alpha_gate.py). But the gate body requires `factors is not None` (lifecycle_manager.py:614), and the production entry `StrategyGovernor.evaluate_lifecycle` (governor.py:607-610) calls `lcm.evaluate(...)` WITHOUT `factors=`. The only caller supplying factors is `scripts/lifecycle_factor_alpha_reeval_t043.py`. So in the autonomous loop the gate is a permanent no-op despite its enable-flag reading True. Flag-vs-path hazard, same family as T-088.
- Charter reference: engine_charters.md §F Invariant 4 ("Edge demotions require statistically significant underperformance"). Not discoverable as inert from any living doc.
- Recommended next step: USER-GATED, not autonomous (re-scoped 2026-06-11 fresh-view review). Wiring `factors=` is mechanically one argument (`load_factor_data(auto_download=False)` fail-soft → `lcm.evaluate(..., factors=factors)`), BUT with prod `lifecycle_enabled=true` + `lifecycle_readonly=false` + `journal=None` on the `update_from_trades` path (governor.py:554), transitions DIRECT-MUTATE edges.yml, and T-043 measured 6 of 7 active edges firing. That would shift arm0 canon mid-T-140-re-baseline and under the held T-118 campaign. Sequence: after T-140 lands and the T-118 wave closes, surface "retire the factor-negative book" as the user decision it is (fresh-view review P1 #3), then wire with journal routing on every call path.

### [HIGH] Engine E: production loads the legacy HMM, not the validated crisis model
- Engine: E
- First flagged: 2026-06-11 (fresh-view review; previously discoverable only inside the T-118 audit doc)
- Status: not started (repoint is propose-first; sequenced behind T-118 verdict)
- Description: `config/regime_settings.json:101` points at `engines/engine_e_regime/models/hmm_3state_v1.pkl` — the original model that scored OOS AUC 0.49 (false-negative) before T-087 reversed the verdict via the crisis retrain. The validated artifact `hmm_3state_crisis_v1.pkl` (T-103/T-105: OOS AUC@5d 0.914–0.919 on the combined posterior, 7/7 per-event TPR at the live 60-bar window) is referenced ONLY by T-103/T-105 scripts and the T-118 campaign-spec generator. CURRENT_STATE leans on "hmm_p_crisis is VALIDATED-predictive" as load-bearing for the Path-B kill-switch decision, but the production system never computes that signal.
- Charter reference: engine_charters.md §E (regime detection is E's job; the model artifact choice is config, not code).
- Recommended next step: T-118 drives its overlay with the crisis model; if the overlay wins its pre-registered gate, the production repoint rides along as a separate propose-first gate. Until then this row exists so the mismatch is discoverable from a living doc. capability_ledger.md Engine E section updated 2026-06-11 with the same facts.

### [MEDIUM] Yahoo Finance is unusable from ANY cloud/AWS context (policy 429 on first request)
- Engine: data lanes (cross-cutting)
- First flagged: 2026-07-08 (Agent B, T-295 cloud population attempt — measured, not assumed: a Fargate task's FIRST-EVER request got 429'd while Alpaca/Minneapolis egress was healthy)
- Status: open — a standing constraint, not a bug to fix.
- Description: Yahoo throttles AWS IP ranges by policy. Affects anything yfinance-based if ever run in
  Batch/Fargate: `earnings_data`'s `yf.Ticker`, the CEF NAV path (`X<TKR>X`), and T-295-style ZQ pulls.
  Rule: yfinance work runs from residential contexts (the dev Mac) only; cloud jobs must not assume it.
  Dev-box note: aggressive retries reset the per-IP ban — after a ban, wait a genuine quiet window before
  ONE polite run. (T-295's script is proven correct — 10yr ZQ=F pulled pre-ban, corr 0.9989 vs FRED — and
  fail-closed exactly as designed when the fetch came back empty.)

### [MEDIUM] Stooq is now bot-walled — future refreshes of every Stooq-sourced dataset will fail
- Engine: data lanes (cross-cutting)
- First flagged: 2026-07-08 (Agent B, during T-295 recon)
- Status: open — no immediate breakage, but the refresh path is dead.
- Description: the Stooq CSV endpoint now returns a JavaScript proof-of-work challenge instead of data.
  Everything Stooq-sourced ON DISK is unaffected (the T-256 tr_reconciled bundle, the deep-ETF history),
  but any future refresh via `scripts/ingest_stooq_us_daily.py` — or any new lane assuming Stooq as a free
  source — will fail. B's T-295 already substituted Yahoo `ZQ=F` for its ZQ needs (director-approved,
  method validated live: 100−96.3675 = 3.63% = actual EFFR). Next lane that needs a Stooq-class refresh
  should plan a substitute source up front; if the wall persists, mark the Stooq ingest script deprecated
  in the execution manual.

### [MEDIUM] Engine F: `regime_analytics.RegimePerfAnalytics` referenced by charter + index.md but file does not exist
- Engine: F
- First flagged: 2026-06-04
- Status: not started
- Description: engine_charters.md §F Modules and `engines/engine_f_governance/index.md:15`/:99-101 document `regime_analytics.py`, but a whole-repo search (excl. Archive) finds no such file. The auto-generated index block is built by `scripts/sync_docs.py` from real code → file archived/deleted without regenerating, or sync_docs read a stale source. Role overlaps the existing `regime_tracker.RegimePerformanceTracker`.
- Charter reference: engine_charters.md §F Modules table, row `regime_analytics.py`.
- Recommended next step: Run `scripts/sync_docs.py`; confirm consolidation into RegimePerformanceTracker; update charter + index or restore from Archive.

### [MEDIUM 2026-06-22 by engine-auditor] Engine F — behavior-altering governance capabilities are UNTRACKED in `capability_ledger.md` (the buried-capability blind spot, F edition)
- Engine: F
- First flagged: 2026-06-22 (capability-registry audit after the T-204/211/216/217/220-227 + T-212/T-218 merge wave)
- Status: not started
- Description: The `capability_ledger.md` Engine F section (4 rows) tracks only the three OFF/inert/missing items (learned_edge_affinity, factor-α gate, regime-conditional weighting) + RegimePerfAnalytics. It has NO row for the F capabilities that are actually behavior-altering and reachable — the exact blind spot the ledger exists to close. Verified against code 2026-06-22:
  1. **Autonomous lifecycle transitions — ACTIVE in prod, UNTRACKED.** `lifecycle_enabled=true` AND `lifecycle_readonly=false` in `config/governor_settings.json:19,23`; `governor.evaluate_lifecycle` (governor.py:602) → `LifecycleManager.evaluate` (lifecycle_manager.py:352) is reached on the prod backtest post-run path (`orchestration/mode_controller.py:1045`) and the paper/live `update_from_trade_log` path (governor.py:600). It DIRECT-MUTATES `edges.yml` status (active→paused→retired→revive) and `lifecycle_history.csv` — the single most consequential F behavior, and it is ON. Tracked at the system-level in DESIGN_FIDELITY (row "Autonomous discovery + lifecycle + self-learning loop = ACTIVE") but with no capability_ledger row, no flag-state, no wired-to-live-path verification.
  2. **MDD-25% kill-switch / pause gate — UNTRACKED.** Charter §F Design Notes ("Kill-switch: Edges exceeding MDD threshold (-25%) immediately paused") + lifecycle pause gates (lifecycle_manager.py:35 "MDD spike", config `disable_mdd_threshold=-0.25` governor.py:36 and lifecycle pause thresholds). Same `lifecycle_enabled` gate (True) → reachable. No ledger row.
  3. **Allocation evaluation orchestration — ACTIVE, UNTRACKED.** `allocation_evaluation_enabled=true` (config:17); `update_from_trade_log` (governor.py:558-576) constructs `AllocationEvaluator`, evaluates 384 param combos, and writes `data/research/allocation_recommendations.json` every cycle. `auto_apply_allocation=false` (config:18) so it does NOT write portfolio_policy.json, but the recommendations file IS the de-facto producer that Engine C `policy.py:62` falls back to (cross-referenced in the ledger's Engine C `allocation_recommendation` row). The producer side is untracked in F.
  4. **Tier reclassification hook — DORMANT, UNTRACKED.** `tier_reclassification_enabled=false` (config absent → default False, governor.py:78); `governor.evaluate_tiers` (governor.py:665) re-runs FF5+Mom decomp and mutates `tier`/`combination_role` in edges.yml when ON. Reached from mode_controller.py:1056. Default-OFF (correctly noted), but a behavior-altering capability with zero registry presence.
  5. **T-227 runtime dead-gate assert — UNTRACKED (borderline).** `governor._assert_regime_weight_keys_reachable` (governor.py:189) HALTs in measured mode if `_regime_weights` carries a key no `macro_regime` label emits. Defensive/observability, but it CAN abort a measured run → arguably behavior-altering on the measurement path. No-op in prod (gate empty when `regime_conditional_enabled=false`). Not in capability_ledger or DESIGN_FIDELITY.
- Charter reference: engine_charters.md §F Design Notes ("Autonomous reweighing", "Kill-switch", "Allocation evaluation"); Invariants 1 (versioned audit trail) and 7 (fully autonomous). The capability_ledger "How to add a row" rule (line 95) requires a row for every behavior-altering capability — lifecycle/MDD-kill/allocation-eval qualify and are missing.
- Recommended next step: Add capability_ledger.md Engine F rows for (1) autonomous lifecycle transitions [wired: yes, flag: lifecycle_enabled=true, HIGH], (2) MDD-25% kill-switch [wired: yes via lifecycle, HIGH], (3) allocation-evaluation producer [wired: yes, flag: allocation_evaluation_enabled=true; auto-apply OFF, MEDIUM], (4) tier reclassification [wired: yes-when-flagged, flag: tier_reclassification_enabled=false default, LOW]. Decide whether the T-227 measured-mode HALT warrants a row. This is autonomous doc-authority (updating a state doc to reflect what the code does) — no user gate needed for the ledger additions themselves.

### [LOW 2026-06-22 by engine-auditor] Engine F — `capability_ledger.md` learned_edge_affinity row states the WRONG gate (injector is gated by `learned_affinity_enabled`, not `regime_conditional_enabled`)
- Engine: F
- First flagged: 2026-06-22 (capability-registry audit)
- Status: not started
- Description: `capability_ledger.md` Engine F row 1 says the `learned_edge_affinity` injector is "gated by `regime_conditional_enabled=false`" and wired-to-live-path "no". The NET verdict (inert in prod) is correct, but the stated GATE is imprecise: the injector at `backtester/backtest_controller.py:368` is gated by `learned_affinity_enabled` (default True, `config/governor_settings.json:16` = true) — NOT `regime_conditional_enabled`. The reason it is still inert is one level deeper: `RegimePerformanceTracker.get_learned_affinity` (regime_tracker.py:180) returns `{}` because the tracker is never FED — `record_trade` only fires inside `update_from_trades` when `regime_conditional_enabled=true` (governor.py:421-422, config:13 = false), so `if learned:` (backtest_controller.py:379) is False and nothing is injected. This is the "empty-plumbing trap" from DESIGN_FIDELITY (line 36): the consumer path is ON but fed empty data. The existing health_check HIGH entry describes the empty-`{}` mechanism correctly; only the ledger's one-line gate attribution is wrong.
- Charter reference: engine_charters.md §F Design Notes "Learned edge affinity".
- Recommended next step: Correct the capability_ledger F row 1 Prod-flag-state to "`learned_affinity_enabled=true` (injector ON) but `regime_conditional_enabled=false` starves the producer → tracker empty → `get_learned_affinity` returns `{}` → no injection." Add a "Fed-real-data? = no" note (the DESIGN_FIDELITY-proposed canary column). Autonomous doc-authority.

### [MEDIUM 2026-06-04 by engine-auditor] Engine C — shipped crisis/defensive capabilities are NOT discoverable from living docs (Path-B-relevant doc gap)
- Engine: C
- First flagged: 2026-06-04
- Status: not started
- Description: An Engine-C audit for Path B (crisis-regime robustness) found multiple SHIPPED capabilities that are absent from `docs/State/CURRENT_STATE.md` and only thinly described (or wrong) in `docs/Core/engine_charters.md` + `engines/engine_c_portfolio/index.md`. The most Path-B-relevant:
  1. **Regime-aware vol-target upside ceiling (crisis de-gross)** — `policy.py:334-352` `_apply_vol_target` caps leverage to 1.0× in `market_turmoil`/`cautious_decline`/`stressed`/`crisis` (1.4× transitional, legacy 2.0× benign). This is an Engine-C SIBLING to the already-surfaced Engine B/E `portfolio_vol_target_crisis_multiplier=0.40` path. No living doc mentions Engine C has its own regime-conditional de-gross. Charter (line 256) only says "scale weights to match target_volatility (clamp 0.3-2.0x)" — the asymmetric/regime-aware ceiling is invisible, and the 0.3 downside FLOOR (keeps ≥30% gross in vol spikes — a de-gross LIMITER) is undocumented.
  2. **Advisory exposure-cap enforcement in Engine C** — `policy.py:370-391` `_apply_exposure_cap` consumes Engine E's `suggested_exposure_cap`. This is DOUBLE-CONSUMED: Engine B (`risk_engine.py:736`) also applies the same `suggested_exposure_cap` to `effective_max_gross`. Potential compounding de-gross; the boundary (who owns exposure-cap enforcement, C or B?) is not stated in any doc.
  3. **Reachability nuance the docs hide:** prod `config/portfolio_settings.json` sets `mode: "mean_variance"`, and both overlays above live ONLY in the adaptive-mode branch (after the mean_variance early-return at `policy.py:200`). BUT `data/research/allocation_recommendations.json` recommends `mode:"adaptive"` for EVERY regime, and `_apply_regime_overrides` (`policy.py:86`) applies "mode" as a known-safe override key — so the crisis overlays can be silently activated at allocation time. No doc captures this mean_variance→adaptive flip.
  4. **Multi-sleeve infrastructure already exists** — `sleeves/` ships `MultiSleeveAggregator`, `TrendFollowingSleeve` (CTA momentum + inverse-vol), `MoonshotSleeve` (asymmetric-upside). CURRENT_STATE.md line 36 names "LAYER 2 — trend/managed-futures positive-skew sleeve (the STRUCTURAL skew fix)" as future near-term work WITHOUT noting a TrendFollowingSleeve + aggregator already exist (default-OFF, never wired into `BacktestController`). Path B Layer 2 may be partly pre-built.
- Charter reference: `engine_charters.md` §Engine C C.2 Allocation (lines 249-277) lists "Portfolio-level vol targeting (scale weights to match target_volatility via w@cov@w)" and "Advisory exposure cap enforcement" but omits the regime-conditional ceiling, the double-consumption with B, the mean_variance/adaptive reachability flip, and all sleeve infrastructure.
- Recommended next step: (a) Add the regime-aware vol-target ceiling + downside floor and the C-vs-B exposure-cap double-consumption to CURRENT_STATE.md as a Path-B-relevant existing defensive primitive (it answers "what de-gross does C already do?"). (b) Resolve the exposure-cap ownership boundary B-vs-C in the charter. (c) Document sleeve infra status (built, default-OFF, unwired) before Path-B Layer 2 work re-builds it. (d) Regenerate `index.md` auto-ref via `scripts/sync_docs.py` — it currently lists a non-existent `allocator.py` (`EngineCAllocator`).

### [MEDIUM 2026-06-04 by engine-auditor] Engine D charter + index.md claim "4-Gate Validation" but code runs an 8-gate pipeline (Gates 0,5,6,7,8 undocumented; Gates 1,3 descriptions stale)
- Engine: D
- First flagged: 2026-06-04
- Status: not started
- Description: `docs/Core/engine_charters.md` (Engine D output contract + Invariant #4) and `engines/engine_d_discovery/index.md` (line 10, 18) both describe a 4-gate validation pipeline: "backtest → PBO → WFO → significance." The actual `DiscoveryEngine.validate_candidate` (discovery.py:869-1673) runs **Gate 0 (MBL pre-flight, default ON, mbl_sr_target=1.0)**, Gate 1 (now a *contribution-lift* gate `with−baseline > 0.10`, NOT the documented standalone "Sharpe > 0"), Gate 2 (PBO), Gate 3 (rolling-window consistency on the attribution stream — NOT the documented OOS/IS hyperparameter WFO degradation), Gate 4 (permutation), **Gate 5 (Universe-B production-equivalent transfer)**, **Gate 6 (FF5+Mom factor-alpha, t>2 AND α>2%)**, **Gate 7 (substrate-transfer drift, historical-S&P 500)**, **Gate 8 (DSR multiple-testing correction)**. Gates 7 and 8 are wired LIVE in the production `--discover` path (`orchestration/mode_controller.py:1209-1318`), so they are not dead code. A reader of the living docs would not know the gauntlet enforces factor-adjusted alpha, substrate transfer, or multiple-testing deflation.
- Charter reference: engine_charters.md Engine D Invariant #4: "Every candidate must pass 4-gate validation (backtest → PBO → WFO → significance) before promotion"; output contract comments label only Gates 2/3/4.
- Recommended next step: Update the Engine D charter output contract + Invariant #4 and index.md design-notes to describe the 8-gate (Gate 0-8) pipeline as implemented, including which gates are default-ON vs gated, and correct the Gate 1 (contribution-lift) and Gate 3 (consistency) semantics.

### [MEDIUM 2026-06-04 by engine-auditor] Engine D GA can emit crisis/defensive gene types (macro VIX/yield-curve, regime=bear, short/market_neutral direction) that no living doc surfaces — Path-B relevant
- Engine: D
- First flagged: 2026-06-04
- Status: not started
- Description: `DiscoveryEngine._create_random_gene` (discovery.py:496-538) emits a **macro (10%)** bucket — `vix_level` (thresholds 15/20/25/30, "panic" at >30), `yield_curve` (T10Y2Y inversion-as-stress), `unemployment_delta` — plus a **behavioral (5%)** bucket (`panic_score`, `herding_breadth`) and a **regime (5%)** bucket (`is bear`). The GA also emits `direction: short` (10%) and `market_neutral` (10%) genomes (discovery.py:353-357, genetic_algorithm.py:157-163, 288-289). These resolve to real signal behavior in `engines/engine_a_alpha/edges/composite_edge.py` (macro handler line 181/496-531; regime handler line 160; short/market_neutral sign at line 150). This means Engine D is *already capable* of discovering crisis-aware, VIX-gated, and short/hedge edges — directly relevant to the T-092 Path B crisis-robustness pivot — yet MEMORY records Engine D only as "GA emits only rsi_bounce_v1 mutations" (the pre-T-022 state, now superseded by the foundry/macro vocabulary). No living doc tells a Path-B planner that the edge-discovery vocabulary already spans crisis/defensive primitives.
- Charter reference: engine_charters.md Engine D Design Notes: "GA gene vocabulary spans 7 types (technical, fundamental, regime, calendar, microstructure, intermarket, behavioral)" — omits the macro (FRED VIX/yield-curve/unemployment) and foundry_feature buckets, and does not mention short/market_neutral direction emission.
- Recommended next step: Document the full gene vocabulary (incl. macro + foundry_feature buckets and short/market_neutral directions) in the Engine D charter Design Notes, and flag for the Path-B work that crisis/VIX/short edge discovery is an existing capability lever (not new infrastructure).

### [HIGH 2026-06-22 by engine-auditor] capability_ledger.md + DESIGN_FIDELITY.md are STALE for Engine B after the T-204/211/212/216/218 merge wave — 5 real wired capabilities are UNTRACKED, 1 row is STALE-as-dead, line numbers drifted across the whole B section
- Engine: B
- First flagged: 2026-06-22
- Status: not started
- Description: A registry-vs-code audit of Engine B (`engines/engine_b_risk/`) against `docs/State/capability_ledger.md` (Engine B section) + `docs/State/DESIGN_FIDELITY.md` found the registry has not been reconciled since the recent merge wave. The exact "buried-capability" blind spot the registry exists to prevent. Findings:
  1. **UNTRACKED — `regime_transition_overlay` (T-118), a real wired Path-A crisis de-gross.** `RiskConfig.regime_transition_overlay_enabled` (`risk_engine.py:188`, default False) gates `RegimeTransitionOverlay` (`engines/engine_b_risk/regime_transition_overlay.py`), constructed in `__init__` (`risk_engine.py:286`), advanced per-bar in `manage_positions` (`risk_engine.py:392`) and in `prepare_order` (`risk_engine.py:1041-1048`), and applied to Path A `target_notional` (`risk_engine.py:1080` via `_regime_overlay_mult`). Default-OFF but fully wired and reachable on the LIVE Path A. Has tests (`tests/test_regime_transition_overlay_t118.py`). It is the TRANSITION-trigger form of the de-gross lever (consumes the validated combined HMM posterior). NOT in capability_ledger or DESIGN_FIDELITY at all.
  2. **UNTRACKED — Path-A advisory `risk_scalar` de-gross lift (T-116 PoC).** `advisory_risk_scalar_apply_on_path_a` (`risk_engine.py:119`, default False) lifts the dead-Path-B HMM-modulated `advisory.risk_scalar` onto Path A `target_notional` (`risk_engine.py:1023-1031, 1080` via `_advisory_risk_scalar_mult`). Sibling of the tracked T-111 drawdown Path-A lift, but the T-116 lift has no ledger row.
  3. **UNTRACKED — tax-aware order gates `WashSaleAvoidance` + `LTHoldPreference`.** Both wired in `prepare_order`: wash-sale block (`risk_engine.py:836-842`, `should_block_buy`), LT-hold exit-defer (`risk_engine.py:724-748`, `should_defer_exit`), configured via `config/portfolio_settings.json:38,43` (both `enabled:false`). Behavior-altering Engine B capabilities (they BLOCK/DEFER orders) with zero registry rows.
  4. **UNTRACKED (branch-only, but TASK_LEDGER-tracked) — T-218 factor-neutrality SIZING + T-212 vol-target re-enablement.** `factor_neutrality.py` + `factor_neutrality_enabled` (+ 6 per-factor caps) is BUILT on `feature/factor-neutrality-sizing-t218` (NOT on main; `engines/engine_b_risk/factor_neutrality.py` does not exist on main; zero factor-neutrality wiring in main's `risk_engine.py`). T-212 vol-target build is on `feature/voltarget-build-t212` (part-1 sigma-floor fail-loud hardening branch-only; T-153's non-fail-loud floor IS on main). Both are in `TASK_LEDGER.md` as `dispatched`/branch-held, but neither capability_ledger nor DESIGN_FIDELITY has a row — so a planner reading those two registries would not know factor-neutrality sizing was ever built. (Per the registry's own "Fed-real-data?/branch-status" proposal, these should be DORMANT/branch-held rows, not absent.)
  5. **STALE — `correlation_regime` sector-cap branch listed as "DEAD CONSUMER (no producer)".** The ledger (line 33) says the consumer (`risk_engine.py:876`) is dead because "writer puts correlation_regime as nested dict on output, NOT into advisory." That is now outdated: T-107 added a GATED producer (`engines/engine_e_regime/advisory.py:259-260`, flag `correlation_regime_in_advisory_enabled`, default False, `regime_config.py:125`). The consumer is reachable the moment that flag flips; the row should read "gated-off producer (T-107)", not "no producer / dead".
  6. **STALE — `FactorRiskModel` row says "zero importers in the repo / orphaned".** T-209 added a `decompose()` measurement diagnostic to `factor_analysis.py` (`:98-149`) imported by `tests/test_factor_risk_model.py`. The SIZING relevance is still correctly "no — not wired into risk path" (the sizing-integration hook at `factor_analysis.py:151-163` is explicitly propose-first/not-implemented), but "zero importers" is now wrong and the diagnostic capability is untracked.
  7. **STALE (mechanical) — line numbers across the entire Engine B section have drifted** after the merge wave. Spot-checks: crisis-floor consumer ledger`:729`→actual `risk_engine.py:861`; `suggested_exposure_cap` `:736`→`:866`; `risk_scalar` Path-B `:739`→`:1163`; correlation `:744`→`:876`; vol-target consumer `:251`→`_compute_portfolio_vol_scalar` at `:525` + applied at `:940/1079`; drawdown Path-B `:940`→`:1188`; ATR stop-widening `:875`→`:1129`. The capabilities themselves are intact and correctly classified (Path-A-live vs dead-Path-B); only the `Source (file:line)` anchors are stale (Layer 3a WARN-class, not a phantom).
- Charter reference: capability_ledger.md header — "flat index of every BEHAVIOR-ALTERING capability the code currently ships, on which path, behind which flag, with honest reachability"; DESIGN_FIDELITY.md — "code-grounded so a NEVER-BUILT row can't be silently asserted-as-built" and proposes a "Fed-real-data?" + branch-status column. The wash-sale/LT-hold/overlay/risk-scalar-lift/factor-neutrality capabilities are exactly the behavior-altering shipped surface both registries claim to index.
- Recommended next step: (a) Add ledger rows for the 5 untracked B capabilities (regime_transition_overlay T-118, advisory risk_scalar Path-A lift T-116, WashSaleAvoidance, LTHoldPreference, and branch-held T-218 factor-neutrality / T-212 vol-target as DORMANT/branch-held). (b) Re-tag the `correlation_regime` row to "gated-off producer (T-107)". (c) Re-tag the `FactorRiskModel` row: diagnostic `decompose()` is test-imported (T-209), sizing hook still unwired/propose-first. (d) Re-run the Layer 3a source-anchor reconciliation to refresh the drifted line numbers. (e) Add a DESIGN_FIDELITY row for factor-neutrality sizing (intended risk-control, BUILT-on-branch, not merged) so it cannot fall through the net like the conjunctive selector did.

### [MEDIUM → ELEVATED 2026-05-12] Worth a broader codebase audit for other dead-letter / unreachable-code patterns (post-T-054 discovery)
- Category: code hygiene / structural plumbing
- Status: needs-verification (triaged 2026-06-11; partially addressed by the T-090/T-102/T-104/T-111 contract-test + wiring sweeps, but no TASK_LEDGER row closes out the codebase-wide dead-letter audit as such)
- The T-054 production-hunt() ticker= wiring bug is the second "registered but unreachable" bug class discovered (after the cockpit metrics-pipeline bug which was schema-mismatch, not unreachable code per se). Per the user 2026-05-12 directive "bones must be PERFECT before LLM," a deliberate dead-letter audit is overdue.
- Candidates to search for:
  - Functions defined but never invoked in production code paths (especially in engines/)
  - Class methods that exist on a class but are only called from tests
  - Config flags that gate code paths nothing else references
  - Feature classes registered in a factory but never instantiated downstream
  - CLI scripts that import functionality not actually exercised by `__main__`
- Recommended dispatch: `code-health` subagent against engines/engine_d_discovery/ + engines/engine_a_alpha/edges/ as Phase 1 (where T-022/T-024 worked and the gap was). Then engines/engine_b_risk/ + engines/engine_c_portfolio/ as Phase 2.
- Director-side analysis of `engines/engine_d_discovery/` already started (separate audit forthcoming).

### [HIGH] Gate 1 (Sharpe-contribution-to-ensemble) wall-time makes Discovery cycles intractable at cap=30
- Category: Engine D performance / Discovery-cycle feasibility
- First flagged: 2026-05-11 by T-2026-05-10-021. Per-candidate wall-time 3,240-6,689 sec (Gate 1 runs full ModeController backtest). Cap=30 candidates → 37+ hr. **Cap=30 is infeasible without Gate 1 caching.**
- Status: needs-verification (triaged 2026-06-11; `gate1_signal_cache.py` shipped on the T-023 lane, but no ledger/audit row confirms cap=30 Discovery-cycle wall-time is now tractable)
- Forward action: cached signal-collector replay (compute active-ensemble signal stream ONCE per (universe, window), then replay candidate contributions layered on top) — B's estimate: 10-50× speedup. Makes cap=30+ Discovery runs tractable in 6-8 hr.
- T-013's vectorization doesn't help here — different code path (Discovery Gate 1 vs Foundry feature loop).

### [HIGH] 0/11 edges clear FF5+Mom t > 2 gate on substrate-honest — universal pattern, not edge-specific
- Category: alpha mechanism / threshold calibration question
- First flagged: 2026-05-09 by T-004 (0/6 active edges). Confirmed 2026-05-10 by T-020 (0/5 new paused edges either, despite 5/5 generating trades at full isolation). Max α t-stat across all 11 edges: 1.76 on short_term_reversal_v1.
- Status: not started (triaged 2026-06-11)
- Implication: raw Sharpe in this system is Mkt + Mom factor exposure, not idiosyncratic alpha. EITHER (a) the t > 2 threshold is inherently incompatible with retail-scale substrate-honest universes, OR (b) the project genuinely has no factor-adjusted alpha. Per the discipline framework, we don't relax thresholds after data lands — but the threshold-calibration question is worth ~2-3 hr director analysis (comparison against SPY's own factor-adjusted alpha on the same window; original calibration context).
- Closest-miss watchlist: short_term_reversal_v1 (t=1.76, 2022 zero-Sharpe cell suspicious), pairs_trading_MA_V_v1 (α point +18%, t=1.41 limited by n=167 trades).
- Forward action: keep all 5 new paused edges at paused/feature (no manual promotion). Optional follow-ups: STR re-measurement (~2 hr) + pairs inventory expansion (~4 hr) to tighten the t-stats on the closest-miss edges.

### [HIGH → 2026-05-12 EVENING UPDATE BY T-036] All 6 active edges are UNIFORMLY NEGATIVE on factor-adjusted α (re-confirmed at stronger level)
- Category: alpha integrity / factor-vs-idiosyncratic decomposition
- Status: not started (triaged 2026-06-11)
- 2026-05-12 evening update post-T-036 Part B (per-regime factor decomp on cockpit-fixed trade logs): the cockpit-bug-correction strengthened, not weakened, the T-004/T-029 "no idiosyncratic alpha" finding. **`volume_anomaly_v1` and `gap_fill_v1` — labeled as "5-year dollar PnL winners" in the morning 2024 attribution audit (commit d1ed01f) — are UNIFORMLY NEGATIVE on factor-adjusted α** (volume_anomaly emerging_expansion t = -2.06, robust_expansion t = -2.27; gap_fill robust_expansion t = -2.77). Their positive dollar PnL is Mkt+Mom factor beta exposure, NOT idiosyncratic alpha.
- Implication: the 0.598 corrected Sharpe baseline IS REAL (the strategy makes money) but it's **beta-driven, not alpha-driven**. After factor exposure subtraction, the residual α is uniformly negative or noisy across all 11 edges in the T-029/T-036 panel.
- Bucket counts (11 edges, post-T-036): UNIFORMLY NEGATIVE 7 (+2 from T-029) | UNIFORMLY NOISY 1 (STR — equity-level Sharpe 0.999 but factor-explained) | UNIFORMLY POSITIVE 1 (dividend_initiation_drift_v1 — currently inert/paused per T-019) | INSUFFICIENT DATA 1 (pairs_MA_V).
- Forward action: T-043 spec needs to incorporate factor-adjusted α inputs alongside raw Sharpe for the Engine F lifecycle re-evaluation. T-041 (spin-offs, structurally non-factor) becomes more important. Discovery's Gate 6 (FF5+Mom t > 2) becomes the highest-leverage filter for finding idiosyncratic α.

### [HIGH → RESOLVED 2026-05-08] Missing-CSV upper-bound caveat — 36 delisted S&P 500 names absent from `data/processed/` (substrate-honest measurements were upper-bounds only)
- Category: data substrate completeness
- First flagged: 2026-05-09 in `universe_aware_verdict_2026_05_09.md` ("0.507 is an upper bound — 26-54 names per year were silently dropped because their CSV files don't exist locally") and the 36-name target list at `missing_csvs_substrate_completion_2026_05_09.md`.
- Status: RESOLVED. `scripts/fetch_missing_delisted.py` ships a 3-source pipeline (Alpaca v2 historical bars → yfinance → Stooq) with provenance tracking. 48/48 = 100% of legitimately-missing 2021-2025 S&P 500 names sourced (all 36 from the original target list, plus 12 edge cases including BF.B/BRK.B share-class variants and AMD). 7 still-"missing" tickers per the membership union (HRS, JEC, JOYG, KORS, LUK, TSO, WLP) are confirmed parser false-positives — pre-2021 ticker renames whose successor symbols (LHX, J, CPRI, JEF, MPC, ELV) are already on disk. Validation: no zero/negative closes, no spurious >50% jumps, no calendar gaps; spot-checks confirm FRC truncates at 2023-04-28, SIVB at 2023-03-09, ATVI at 2023-10-13, TWTR at 2022-10-27, PXD at 2024-05-02 — all match public record. Provenance per ticker in `data/processed/_data_provenance_delisted.json`. Runbook in `docs/Core/execution_manual.md` §"Sourcing delisted / share-class names". Full report at `docs/Measurements/2026-05/missing_csv_closure_2026_05_08.md`.
- Note: the substrate-honest **re-measurement** that quantifies the post-closure Sharpe delta is BLOCKED on the new HIGH item above (zero-trade regression since 2026-05-07 evening). The data side is closed; running the measurement through it is the unblock.

### [HIGH → RESOLVED 2026-05-07] F11 backtest-vs-live divergence — backtests mutated edges.yml mid-run while live can't snapshot/restore
- Category: architectural drift / measurement fidelity
- Files: `engines/engine_f_governance/journal.py` (NEW), `scripts/journal_apply.py` (NEW), `engines/engine_f_governance/lifecycle_manager.py:298`, `engines/engine_f_governance/governor.py:557+620`, `orchestration/mode_controller.py:1007`
- First flagged: 2026-05-06 (R1 audit). Phase 1 shipped 2026-05-07 morning; Phase 2 shipped 2026-05-07 evening.
- Status: RESOLVED.
  - Phase 1: `LifecycleJournal` append-only writer + `journal_apply` CLI + 36 tests + architecture doc.
  - Phase 2: `LifecycleManager.evaluate`, `governor.evaluate_lifecycle`, `governor.evaluate_tiers` all gain `journal: Optional[Any] = None` kwargs. When supplied, decisions append as `make_status_change` / `make_tier_change` entries instead of mutating `edges.yml`. Default `None` preserves legacy bit-for-bit. `mode_controller.run_backtest` gains `apply_journal_at_end: bool = False` kwarg. 8 wire tests verify the journal-mode-doesn't-mutate AND the legacy-mode-does-mutate invariants.
- Backtest-vs-live fidelity: when `apply_journal_at_end=True`, no edges.yml mutation happens during the run, mirroring the future live-trading shape (decisions journal, apply at configured cadence).

### [HIGH → RESOLVED 2026-05-07] WFO geometry was gapless — every Sharpe in the falsification record was measured under no-embargo conditions
- Category: validation geometry / leakage
- Files: `engines/engine_d_discovery/wfo.py:98`
- First flagged: 2026-05-07 (R1 audit-week-of)
- Status: RESOLVED — `run_optimization` now takes `embargo_days: int = 21`
  and gaps test_start from train_end_idx by that many trading days. The
  default ≈1 trading month clears the lookback of every active edge except
  multi-month windows (mom_252d, realized_vol_60d are still partial-leak;
  edge-aware embargo is future work). Setting embargo_days=0 reverts to
  legacy behavior for backwards-compat sanity only. Commit `c449179`.

### [HIGH → RESOLVED 2026-05-07] Discovery Gates 7 (substrate-transfer) and 8 (DSR) were dead code in production
- Category: missing call-site wire
- Files: `orchestration/mode_controller.py::_run_discovery_cycle:1149`
- First flagged: 2026-05-07 (R1 audit-week-of)
- Status: RESOLVED — Gate 7 receives a per-cycle `data_map_substrate_b`
  built once via `universe_resolver` (the *complement* of the static
  universe so Gate 7 measures genuine transfer rather than near-identity
  overlap; falls back to skipped when the membership parquet is missing).
  Gate 8 receives `n_trials_for_dsr = max(1, len(batch))` so every
  candidate competes against the expected-max-of-N null. Commit `b46dd30`.

### [HIGH → RESOLVED 2026-05-07] Symmetric vol-target clamp leveraged into calm regimes (Minsky setup)
- Category: risk geometry
- Files: `engines/engine_c_portfolio/policy.py:321`
- First flagged: 2026-05-07 (R1 audit-week-of)
- Status: RESOLVED — vol-target ceiling is now regime-aware. Adverse
  regimes (`market_turmoil`, `cautious_decline`, `stressed`, `crisis`)
  cap the upside scalar at 1.0 (no leverage). Transitional regime caps
  at 1.4. Benign or unknown regime keeps the legacy 2.0 ceiling. Downside
  floor 0.3 unchanged. When `regime_meta is None`, behavior is identical
  to legacy. 6 unit tests cover all 4 regime classes. Commit `c4fb913`.

### [HIGH → RESOLVED 2026-05-02] Gauntlet geometry-mismatch — gates 1–6 consumed a standalone single-edge equity curve incompatible with ensemble-deployed strategies
- Engine: D (Discovery — `engines/engine_d_discovery/discovery.py::validate_candidate`, gates 1–6) + orchestration (the production-equivalent backtest invocation that didn't exist)
- First flagged: cumulatively across 2026-04-29 → 2026-05-01 — Q3 gauntlet revalidation (`docs/Audit/gauntlet_revalidation_2026_04.md`), Phase 2.10c per-edge attribution (`oos_2025_decomposition_2026_04.md`), discovery diagnostic (`docs/Audit/discovery_diagnostic_2026_05.md`), gates-2-through-6 audit (`docs/Audit/gates_2_to_6_audit_2026_05.md`). Memory: `project_gauntlet_consolidated_fix_2026_05_01.md`.
- **Status: RESOLVED 2026-05-02.** Consolidated architectural fix shipped on `gauntlet-architectural-fix` branch, merged to main as commits `2451076` (gauntlet fix) and `36d9072` (merge). Agent 1's audit `docs/Audit/gauntlet_architectural_fix_2026_05.md` documents the design rationale, threshold calibration, and falsifiable-spec verification. Path A's foundation work landed alongside the Feature Foundry merge `9ea6c17`.
- Description: `validate_candidate` ran a single-edge **standalone** backtest (one edge at full risk-per-trade, no ensemble context) and used its equity curve as the input to all six downstream gates. Two structural problems followed: (a) Gate 1's standalone Sharpe is incommensurable with ensemble-deployed Sharpe — full risk-per-trade per fill crossed the Almgren-Chriss impact knee on `volume_anomaly_v1` and `herding_v1` (Q3 produced 0.32 / -0.26 standalone vs +ensemble contribution; the very edges that contribute positively in production were architecturally falsified by the gate); (b) gates 2–6 inherited the standalone artifact and tested the wrong object (a strawman strategy, not the candidate's actual ensemble effect). All 6 gates were not 6 independent bugs — they were one architectural mismatch between measurement geometry and deployment geometry, which violates the foundation rule "Geometry of measurement matches deployment. No standalone tests for ensemble-deployed strategies." (`docs/Sessions/Other-dev-opinion/05-1-26_1-percent.md`).
- Fix: `validate_candidate` rewritten to run two production-equivalent backtests per candidate via the new `orchestration/run_backtest_pure.py::run_backtest_pure` (pure callable, no governor/CSV/perf-summary side effects, with `PureBacktestCache` so a Discovery cycle of N candidates costs N+1 backtests instead of 2N). Baseline = (active ∪ paused) **minus** the candidate at production weights (active at config weight, paused at `min(config_weight × 0.25, 0.5)` matching `ModeController`'s soft-pause logic). With-candidate = baseline ∪ {candidate at default weight}. Treatment-effect attribution stream = `with_candidate_returns − baseline_returns`. Gate 1 = contribution Sharpe > θ (default 0.10). Gates 2–6 consume the attribution stream rather than the standalone equity curve. Gate 5 (Universe-B) and Gate 6 (FF5) operate on the same attribution-stream geometry. WFO stitching at `wfo.py:112` switched to RETURNS-based concatenation (eliminates phantom −4.76% returns at every window boundary). Robustness module gains `generate_cross_section_bootstrap` (synchronized block-pick preserves cross-sectional correlation) and `bootstrap_returns_stream` for 1-D attribution streams.
- Verification — falsifiable spec (`docs/Audit/falsifiable_spec_results.json`, captured by `scripts/run_falsifiable_spec.py`, 30-ticker × 2024H1):
  - `volume_anomaly_v1`: contribution +0.113 Sharpe → Gate 1 PASS, Gate 2 PASS (76.5% PBO survival), Gate 5 PASS. **The architectural fix correctly admits a real ensemble contributor that the standalone-geometry gate had architecturally falsified.**
  - `herding_v1`: contribution -0.422 Sharpe in 2024H1 → Gate 1 FAIL (window-specific result for a contrarian edge in a strong bull window; consistent with prior per-edge attribution audits, NOT an infrastructure bug — see memory `project_ensemble_alpha_paradox_2026_04_30.md`).
- Tests: 32 new unit tests pass (`tests/test_run_backtest_pure.py`, `tests/test_attribution.py`, `tests/test_validate_candidate_v2.py`, `tests/test_pbo_cross_section.py`, `tests/test_wfo_oos_stitching.py`). 24 existing discovery tests still pass.
- Honest scope: this resolution closes the **measurement-geometry** bug class. It does not retroactively re-validate prior Q3-era findings (which are already closed under their own resolved entries); it does mean future Discovery cycles measure ensemble contribution honestly. The narrow gate-3 (WFO interface) and gate-5 (datetime index) findings further down in this file were partial precursors that the consolidated fix supersedes architecturally even though they were already closed under their own entries.

### [HIGH → RESOLVED 2026-05-01] Backtest non-determinism regression — same config produced ±1.4 Sharpe variance across runs
- Engine: F (lifecycle / governor state mutation) + orchestration (run_oos_validation harness)
- First flagged: 2026-05-01 (Phase 2.10d/Path 1 ship-validation block)
- **Status: RESOLVED 2026-05-01.** Agent A's investigation (branch `determinism-floor-restore`, audit `docs/Audit/determinism_floor_restore_2026_05.md`) bisected the drift source to a single file: **`data/governor/edges.yml`**. End-of-run lifecycle (`evaluate_lifecycle`) and tier reclassification (`evaluate_tiers`) writes mutate active-edge status; subsequent `--reset-governor` runs read the mutated file and produce different Sharpes. The other three mutable governor files (edge_weights.json, regime_edge_performance.json, lifecycle_history.csv) mutate too but their content is write-only audit; restoring just edges.yml from clean closes the entire 0.227 Sharpe gap exactly. New harness `scripts/run_isolated.py` snapshots+restores edges.yml + 3 audit files around each run. **3-run verify under harness: Sharpe 0.984 / 0.984 / 0.984, 1 unique canon md5 across 3 runs (bitwise-identical, matching the 04-23 floor).** Use `python -m scripts.run_isolated --runs N --task q1` for any measurement campaign. See memory `project_determinism_floor_2026_05_01.md`.
- Description: Backtest reproducibility has regressed materially since the 2026-04-23 determinism floor (memory `project_determinism_floor_2026_04_23.md` documented bitwise-identical canon md5s under `scripts/run_deterministic.py`). Recent same-config runs produce wildly different Sharpe:
  - cap=0.25 + ML-off: Phase 2.10d task C = 0.315; round-1 Agent A A0 hours later = 0.562 (Δ +0.247)
  - cap=0.20 + ML-off: round-1 A3 = 0.920; round-2 B3 v2 = 1.102 (Δ +0.182)
  - **cap=0.20 + ML-on: Agent C round-1 (cap=0.25 default + ML) = 1.064; Agent A round-3 A3 = -0.378 (Δ -1.442 — opposite-sign Sharpe under nominally compatible config)**
- The ±1.4 variance band makes every Sharpe number from the project from 2026-04-29 onward unreliable as a deployment input. Including Agent D's Path 2 result (Universe-B 0.916 with floors+ML) — could be real or could be favorable governor-state coincidence.
- Leading hypothesis: the autonomous lifecycle (`engines/engine_f_governance/lifecycle_manager.py`) and governor (`engines/engine_f_governance/governor.py`) mutate `data/governor/edges.yml`, `lifecycle_history.csv`, `regime_edge_performance.json`, and `edge_weights.json` at end-of-run. `--reset-governor` resets weights at start but does not isolate end-of-run mutations or roll back lifecycle state. Cross-worktree governor-COPY isolation (per `MULTI_SESSION_ORCHESTRATION.md`) prevents inter-agent races but does NOT fix intra-agent run-to-run drift.
- Why this is HIGH (not MEDIUM): the project cannot proceed past Path 1 ship without reproducible measurement. Every A/B claim is provisional. The 2026-04-23 fix already exists at `scripts/run_deterministic.py`; presumably either (a) the OOS validation harness `scripts/run_oos_validation.py` doesn't use it, (b) it broke since 04-23, or (c) it doesn't cover the lifecycle state mutations introduced in Phase 2.10d.
- Recommended next step: dispatch a focused agent for non-determinism investigation. Reproduce the variance with a controlled experiment (run same config 3-5× under tight isolation), find the source of drift (likely candidates: lifecycle_history.csv accumulation, regime_edge_performance.json mutation, edge_weights.json saves), implement a determinism harness that fully isolates a run from prior governor state. Re-establish the bitwise-identical canon md5 floor from the 04-23 baseline. Until this resolves, every Sharpe number is ±1.4 noise.
- See: `docs/Audit/path1_ship_validation_2026_05.md` (Agent A's blocked ship + ±1.4 evidence), `docs/Audit/path2_adv_floors_2026_05.md` (Agent D's caveat), memory `project_determinism_floor_2026_04_23.md` (the prior fix).

### [HIGH → RESOLVED 2026-05-01] System alpha is real but architecturally wasted — capital rivalry + noise edges drag the ensemble (updated 2026-04-30, resolved 2026-05-01)
- Engine: A (signal_processor capital allocation) + C (portfolio engine slot management) + F (lifecycle — partial; pause decisions vindicated, soft-pause weight policy in question)
- First flagged: 2026-04-29 (as "no validated alpha"); **revised 2026-04-30** after Phase 2.10c per-edge attribution diagnostics resolved the apparent paradox.
- **Status: RESOLVED 2026-05-01** — Phase 2.10d task B shipped the three structural primitives; round-2 cap recalibration found cap=0.20 as the optimum (Sharpe 1.102 OOS / 1.113 IS, full-pass gate cleared). `fill_share_cap: 0.20` is the production cap value. Path 1 deployment-ship state captures cap=0.20 as the validated baseline.
- **Residual:** the ML-stacking variant of Path 1 (cap=0.20 + ML-on) did NOT reproduce in agentA's path1-deployment-ship validation (Sharpe -0.378 vs the expected 1.1+ from stacking on Agent C's 1.064 ML-on baseline). Same nominal config; different governor state at run start. Tracked as a separate ship blocker — see `docs/Audit/path1_ship_validation_2026_05.md`. Resolution path is non-deterministic-state diagnosis, NOT re-investigating the rivalry pathology (which is structurally fixed).
- See `docs/Audit/capital_allocation_fixes_2026_04.md`, `docs/Audit/cap_recalibration_sweep_2026_04.md`, `docs/Audit/cap_bracket_sweep_2026_04.md`, `docs/State/deployment_boundary.md`.

### [HIGH NEW → RESOLVED 2026-05-01 evening] Same-config Sharpe non-determinism across worktrees — lifecycle_history.csv likely culprit (2026-05-01)
- Engine: F (lifecycle history not snapshotted by sweep harness) + orchestration (anchor restore semantics)
- First flagged: 2026-04-30 in `cap_bracket_sweep_2026_04.md`; **escalated to ship-blocker 2026-05-01** by `path1_ship_validation_2026_05.md`.
- **Status: RESOLVED 2026-05-01 evening.** Agent A's `determinism-floor-restore` branch isolated the actual drift source to a different file: **`data/governor/edges.yml`** (not lifecycle_history.csv as initially hypothesized — that file does mutate but its content is write-only audit). End-of-run lifecycle + tier-reclassification writes to edges.yml; subsequent runs read mutated state. The new `scripts/run_isolated.py` harness snapshots+restores 4 governor files (edges.yml + 3 audit files) around each backtest. **3-run verify produces bitwise-identical canon md5 across runs.** Subsequent re-validation under harness confirmed: cap=0.20 + ML-off = 0.984 Sharpe deterministic on 2025 OOS prod-109; ML-on degrades by ~0.58 (the +0.749 lift was governor-drift coincidence). See memory `project_determinism_floor_2026_05_01.md` and `project_metalearner_drift_falsified_2026_05_01.md`. The `path1-revalidation-under-harness` audit table is the canonical post-harness measurement set.

### [HISTORICAL — superseded by entries above 2026-05-01]
- Status: closed.
- Description: per Phase 2.10c attribution work (audit docs `oos_2025_decomposition_2026_04.md` and `per_edge_per_year_attribution_2026_04.md`), the system *does* have real alpha — but it lives in the ensemble's risk-sizing dampening + edge-timing diversification, not in standalone signals. Specifically:
  - **Stable contributors (positive every year 2021-2025):** `volume_anomaly_v1` (+1.93% to +4.94%/yr), `herding_v1` (+0.55% to +2.43%/yr).
  - **Weak-positive diversifiers:** `gap_fill_v1`, `macro_credit_spread_v1`, and 4 others (~+0.5%/yr each).
  - **Noise / sparse / zero-fill dead weight:** ~9-11 edges contributing nothing or near-zero across 5 years.
  - **Lifecycle-paused edges (vindicated):** `atr_breakout_v1` (-5.78% in 2022 alone), `momentum_edge_v1` (-9.17% in 2022), `low_vol_factor_v1`. All 3 pause decisions were correct in retrospect.
- The Q3 standalone-gauntlet failure of `volume_anomaly_v1` and `herding_v1` was a **measurement-vs-test mismatch**, not a falsification: standalone Gate 1 gives full `risk_per_trade_pct` per fill, which crosses the Almgren-Chriss impact knee. In production, risk-per-trade is split across 17 firing signals → sub-knee fills → cost tax stays small → signal survives. See memory `project_ensemble_alpha_paradox_2026_04_30.md`.
- Three concrete defects identified in Phase 2.10c (Agent A audit doc):
  1. **Capital rivalry — no per-edge participation floor.** Bottom-3 edges in 2025 (`low_vol_factor_v1`, `atr_breakout_v1`, `momentum_edge_v1`) consumed 83% of fill share for -$5,645 of realized losses; top-2 best-PnL edges got 4.3% of fill share. Un-pausing momentum edges flipped `volume_anomaly_v1` per-fill from +$10.12 to -$1.17.
  2. **Soft-pause weight leak — `low_vol_factor_v1` fired 1,613 times in 2025** despite being effectively paused (weight 0.5 × regime_gate `{benign:0.15, stressed:1.0, crisis:1.0}`). It contributed -2.53% in 2025 alone, mostly via the regime_gate amplifying it in `market_turmoil`/`crisis` regimes — exactly when it should NOT trade.
  3. **No regime-aware slot reduction.** April-2025 `market_turmoil` triggered -$3,551 of simultaneous correlated loss across 5 edges in one month (122% of full-year loss). The portfolio engine has no primitive to reduce concurrent slot count in stressed regimes.
- Why this is HIGH (not MEDIUM): the system's headline performance (1.063 in-sample, -0.049 OOS, 0.225 universe-B) is gated entirely on these three structural issues. Pruning + fixing them is the path to unblocking Phase 2.11/2.12/2.5; not fixing them means the gauntlet never runs out of failure modes to surface.
- Recommended next step: **Phase 2.10d** (see ROADMAP). Two parallel diagnostics — (A) attribution-based pruning proposal cutting 9-11 noise edges to ~6-7 actives, (B) capital allocation defect investigation with code-change proposals. Then sequential C: re-run 2025 OOS with pruned + structurally-fixed system.
- Original entry kept below for context, dated 2026-04-29:

### [HIGH] (HISTORICAL — superseded by entry above 2026-04-30) In-sample Sharpe 1.063 was a double artifact — system has no validated alpha under honest costs on a representative universe
- Engine: A (signal_processor / edge stack) + D (discovery / lifecycle decisions made on artifact data)
- First flagged: 2026-04-29 (Phase 2.10b OOS Validation Gate result)
- Status: historical/superseded (Status line corrected 2026-06-11 — was stale "active — blocking" contradicting the entry's own HISTORICAL title; superseded by the 2026-04-30 entry above)
- Description: Phase 2.10b ran the three OOS gates for the realistic-cost in-sample Sharpe 1.063 result. **All three failed by wide margins:**
  - **Q1 (2025 OOS, prod 109 universe):** Sharpe **-0.049** vs criterion > 0.5. SPY 2025 was 0.955 — system trailed every benchmark by **>1.0 Sharpe** in a strong bull year. Run UUID `72ec531d-7a82-4c2a-97c0-ffb2bf6ddb34`. Audit: `docs/Audit/oos_validation_2026_04.md`.
  - **Q2 (universe-B held-out 50, in-sample window):** Sharpe **0.225** vs in-sample 1.063 — a **79% Sharpe collapse** on the same window with held-out tickers. Vol nearly doubled (5.7% → 9.95%), MDD nearly doubled (-10.07% → -18.17%). Run UUID `ee21c681-f8de-4cdb-9adb-a102b4063ca1`.
  - **Q3 (`volume_anomaly_v1` + `herding_v1` standalone gauntlet under realistic costs):** Both failed Gate 1. Sharpe 0.32 and **-0.26** respectively (`herding_v1` standalone is capital-destroying under honest costs) vs benchmark threshold ~0.68. The prior factor-decomp t-stats of +4.36 and +4.49 were a cost-model confound — `validate_candidate` hardcoded slippage at 5bps while the integration backtest used realistic Almgren-Chriss. Audit: `docs/Audit/gauntlet_revalidation_2026_04.md`.
- Diagnosis: the 1.063 in-sample headline is a **double artifact** — favorable universe (curated 109 mega/mid caps) AND favorable window (2021-2024). Universe-B at 0.225 is in the same ZIP code as the prior 0.4 baseline noted in `project_lifecycle_vindicated_universe_expansion_2026_04_25.md`. The "two real alphas" claim is falsified.
- What this kills: Phase 2.11 (per-ticker meta-learner), Phase 2.12 (growth-profile config), Phase 2.5 (Moonshot Sleeve) all blocked until Phase 2.10c diagnostic triage determines whether ANY real alpha exists in the active edge stack.
- Adjacent bug fix shipped on `gauntlet-revalidation` branch: `engines/engine_d_discovery/discovery.py::validate_candidate` previously hardcoded `slippage_bps=5.0`; agent added `exec_params` override so candidates can be validated under the same cost model the integration backtest uses. **This is a real bug fix independent of the edge result and should land on main.**
- Recommended next step: Phase 2.10c — full standalone gauntlet on all 13 active edges + TierClassifier rerun with realistic costs + universe-fit decomposition. Single audit doc per diagnostic. **No new features until results are in.**
- See: `docs/State/ROADMAP.md` Phase 2.10b/2.10c sections, `docs/Archive/forward_plans/forward_plan_2026_04_29.md` "Result" section.

### [HIGH → PARTIALLY RESOLVED 2026-05-09] Sharpe-only fitness limits portfolio profile flexibility — multi-metric measurement + config-driven fitness profile needed
- Engine: A (signal_processor / meta-learner) + D (discovery gates) + F (lifecycle)
- First flagged: 2026-04-28
- Status: PARTIAL — measurement layer upgraded 2026-05-09 (commits `82b904d` + `418828c`): `core/metrics_engine.py` now exports PSR, DSR, Information Ratio, Tail Ratio, Skewness, Excess Kurtosis, Ulcer Index alongside Sharpe / Sortino / Calmar. `scripts/run_multi_year.py` reports surface PSR / IR / Calmar / Sortino / Skew / Kurt / Tail / Ulcer / MDD per year + cross-year aggregates with PSR median as headline. Engine D's gauntlet gained Gate 7 (substrate-transfer) + Gate 8 (DSR — multiple-testing correction) at commit `fcd048d`. **Remaining open:** profile-aware optimization (fitness-profile-conditional metric weighting in Discovery + lifecycle), wiring DSR into the Discovery promotion path beyond gauntlet acceptance, MetaLearner training against profile-conditional objectives (Calmar/PSR for core sleeve, Sortino/tail-ratio for Moonshot Sleeve when activated). Design doc still applies for the profile-aware optimization layer.
- Description: The realistic-cost backtest produced Sharpe 1.063 (vs SPY 0.875) with under HALF the volatility and HALF the drawdown — but only **6.06% CAGR vs SPY 13.94%**. The system's apparent excellence on Sharpe is partly because Sharpe is volatility-normalized: a 5.7%-vol system beats a 16.5%-vol system on Sharpe even when its absolute return is half. **What's optimal for a low-vol/retiree profile (low drawdown, high Sharpe) is NOT optimal for a growth profile (high CAGR even at higher vol).** Currently every gate, fitness function, and lifecycle decision in the codebase uses Sharpe as the dominant metric. This hardcodes one profile preference into infrastructure that should support multiple.
- Architectural fix (three-layer separation, per design doc):
  - **Layer 1 (Existence — alive vs retired):** OBJECTIVE / profile-independent. Lifecycle gates use factor-decomp t-stat, BH-FDR, PBO survival, raw Sharpe vs benchmark. An edge gets retired only for objective reasons (consistently destroying value, no real signal, charter-broken). Profile changes do NOT retire edges.
  - **Layer 2 (Tier — alpha/feature/context):** OBJECTIVE / profile-independent. Machine-classified from factor-decomp t-stats by the planned `TierClassifier` module. Self-updating, not hand-set.
  - **Layer 3 (Allocation — how much capital):** SUBJECTIVE / config-driven. The active `FitnessConfig` profile weights Sharpe + Calmar + Sortino + CAGR + MDD into a single fitness score. Profiles in `config/fitness_profiles.yml`: retiree (`0.6 calmar + 0.3 sortino + 0.1 sharpe`), balanced (`0.5 sharpe + 0.3 calmar + 0.2 cagr`), growth (`0.5 cagr + 0.3 sharpe + 0.2 calmar`).
  - The meta-learner trains against the active profile's fitness target, not raw forward returns.
- Why this is HIGH (not MEDIUM): every downstream optimization in the system is currently anchored to Sharpe. Without this fix, the v2 plan's "build edges, autonomously combine" architecture is implicitly committing to one risk profile forever. Switching to a different profile later would require code edits across discovery, lifecycle, and signal_processor.
- Recommended next step: implement during Session N of the meta-learner build (foundation phase). `MetricsEngine.calculate_all` already returns Calmar (commit fb1ba13 era); just add Sortino and Sortino-coverage tests, then add the `FitnessConfig` config layer. The `TierClassifier` rule and Lifecycle objective gates are already designed in the meta-learner design doc.
- See: `docs/Core/phase1_metalearner_design.md` ("Three-layer architecture" section), `docs/Audit/realistic_cost_backtest_result.md` (the empirical observation that triggered this finding).

### [MEDIUM → RESOLVED 2026-05-07] validate_candidate uses full data_map extent instead of configured backtest window — Gate 1 takes ~35 min/candidate
- Engine: D
- First flagged: 2026-04-28
- Status: RESOLVED via two-step fix:
  1. **API-side (commit `2451076`, gauntlet architectural rewrite 2026-05-02):** `discovery.py::validate_candidate` accepts `start_date` / `end_date` kwargs. When provided, the gauntlet runs Gate 1 over the specified window instead of the full data_map extent.
  2. **Call-site (this commit, 2026-05-07):** `orchestration/mode_controller.py::_run_discovery_cycle:1169` now computes a 24-month rolling validation window (`end = data_map.index[-1]`, `start = end - 24 months`) and passes it explicitly to `validate_candidate`. Override via `DISCOVERY_VALIDATION_MONTHS` env var for campaigns that need longer history. Gate 3 (WFO) still does proper multi-window OOS via `train_months` / `test_months` params, so a short Gate 1 window is the correct cheap pass/fail filter.
- Description: `discovery.py::validate_candidate` lines 631-632 derive `start_date` and `end_date` from `data_map[first_ticker].index[0]` and `[-1]`. The data_map fed by `mode_controller._run_discovery_cycle` is the full price-history parquet (2020-04 → 2026-04, ~6 years for current cache) including the 1-year warmup window. So Gate 1's "quick backtest" runs 6 years of data on 109 tickers per candidate — observed empirically at ~30-35 min per Gate 1. Combined with Gates 2-5, each candidate takes ~2 hours. With the cycle cap of 10 candidates this is ~20 hours per discovery run, making the autonomous loop impractical.
- Recommended next step: Have validate_candidate accept (or look up) a "validation window" — e.g. last 12-24 months — for Gate 1's quick filter. Gate 3 (WFO) already does proper multi-window OOS via train_months/test_months params, so a short Gate 1 window is fine for the cheap pass/fail filter. Either honor `cfg_bt["start_date"]`/`end_date` from backtest_settings, or expose `validation_start_date`/`validation_end_date` parameters to the mode_controller call site.

### [HIGH → RESOLVED 2026-05-07] RuleBasedEdge requires FeatureEngineer-computed columns that are absent from validation data_map
- Engine: D (with A as the affected receiver — `RuleBasedEdge.check_signal`)
- First flagged: 2026-04-28
- Status: RESOLVED via option (a) per the audit's recommended next-step. `RuleBasedEdge.compute_signals` now runs `FeatureEngineer.compute_all_features()` on each ticker's OHLCV inline, with a `(ticker, last_bar_index)` cache to amortize the ~100ms-per-call cost across the bar (without caching: 250 × 100 × 6-edges = ~minutes of feature recomputation per backtest). 10 new tests in `tests/test_rule_based_edge_features.py` cover trivial-rule firing on OHLCV-only input, short direction, Vol_ZScore-referencing rule (the original failing case), unsatisfied-condition correctness, cache hit + invalidation behavior, empty-DataFrame edge case, unknown-feature fall-through, and compound AND-rules. The fix unblocks the autonomous Discovery loop's TreeScanner promotion path.
- Description: After commit dda474c added `RuleBasedEdge.compute_signals()`, hunter candidates run through Gate 1 — but they still produce Sharpe=0.00 with zero trades. Root cause: `check_signal()` reads `row[feat]` for features like `RSI_14`, `Vol_ZScore`, `Regime_CorrSpike` etc. These columns are only populated by `FeatureEngineer.compute_*` methods during the hunt phase (assembled into `big_data` at `discovery.py::hunt:106`), and are NOT preserved into the validation `data_map` that `validate_candidate` passes to AlphaEngine. The data_map there has only OHLCV columns. `if feat not in row: return None` triggers on every bar, every ticker. Result: hunter Gate 1 Sharpe = 0.00 → fails benchmark threshold → marked failed. The autonomous discovery loop cannot promote any rule discovered by TreeScanner regardless of how good the rule is.
- Files: `engines/engine_a_alpha/edges/rule_based_edge.py::check_signal`, `engines/engine_d_discovery/discovery.py::validate_candidate` (data_map passed to AlphaEngine without feature engineering), `engines/engine_d_discovery/feature_engineering.py` (where features are computed but only for hunt).
- Recommended next step: Either (a) `RuleBasedEdge.compute_signals` calls `FeatureEngineer` on the per-ticker DataFrame at signal-time to add the columns its conditions reference, OR (b) `validate_candidate` runs `FeatureEngineer.compute_basic_features()` over `data_map` before instantiating the AlphaEngine. Option (a) is cleaner — keeps the edge self-sufficient and matches how rsi_bounce/atr_breakout compute their features inline. Add a unit test asserting hunter validation produces non-zero Sharpe given a contrived dataset where the rule trivially matches.

### [HIGH → RESOLVED 2026-04-28] Engine A alpha_engine references deleted `rsi_mean_reversion` module — bare-except masks 6-month-old broken import
- Engine: A
- First flagged: 2026-04-28
- Status: **resolved 2026-04-28** — dead imports removed, default edge swapped to `rsi_bounce`
- Description: `alpha_engine.py:251` listed `"rsi_mean_reversion"` in `default_edges`, and `alpha_engine.py:422` did `importlib.import_module("engines.engine_a_alpha.edges.rsi_mean_reversion")`. Module was deleted 2025-11-12. Both call sites were wrapped in `except Exception` blocks that only printed under `is_info_enabled()` — failure was invisible under standard logging. AlphaEngine ran with one fewer default edge for ~6 months.
- Fix: Replaced both import sites with `rsi_bounce` (the only existing RSI edge); removed orphan `"rsi_mean_reversion": "mean_reversion"` from `signal_processor.EDGE_AFFINITY_MAP`; updated `config/alpha_settings.dev.json` orphan entry; replaced silent `except Exception` with `except ImportError` that raises with diagnostic context. Future default-edge rename will now fail loudly at startup.

### [HIGH → CLOSED 2026-04-28] (misdiagnosed) Engine D WFO `_quick_backtest` keys edges dict by edge_id, but AlphaEngine looks up weights by edge_name — WFO runs all edges at default weight 1.0
- Engine: D (with A as the receiver of the contract drift)
- First flagged: 2026-04-28
- Status: **misdiagnosed — closed 2026-04-28**
- Description: code-health agent claimed `AlphaEngine.edges` is keyed by edge_name (`"momentum_edge"`) in production, but WFO keys by edge_id (`"momentum_edge_v1"`). Verification on 2026-04-28: `mode_controller._load_edges_via_registry` lines 674-679 actually populate `loaded_edges[edge_id] = ...`, and `config/alpha_settings.prod.json::edge_weights` is keyed by edge_id (`"atr_breakout_v1": 2.5`). Both sides of the lookup use edge_id consistently. WFO's `AlphaEngine(edges={spec["edge_id"]: edge})` matches production convention.
- Real (smaller) issue: WFO does not pass `edge_weights` or `regime_gates` to AlphaEngine, so a single-edge WFO test runs at weight=1.0 with regime_gates bypassed. For a solo WFO test this is the **desired** behavior — there is no other edge to compete with for capital, and you typically want to measure the unconditioned edge. If we ever need to WFO-test a regime-gated edge with its gate active, surface it as a separate finding.

### [HIGH → RESOLVED 2026-04-28] Engine D Gate 3 (WFO) is silently disabled — interface mismatch with WalkForwardOptimizer
- Engine: D
- First flagged: 2026-04-28
- Status: **resolved 2026-04-28** — rewired with correct interface
- Description: `discovery.py::validate_candidate` line 736 called `WalkForwardOptimizer()` with no args, but ctor requires `data_map`. Line 750 called `run_optimization(_WFOWrapper(edge), data_map, n_configs=1)` — wrong signature. Bare `except` swallowed everything; Gate 3 trivially passed for every candidate. No candidate was actually WFO-validated since this code was written.
- Fix: Rewrote Gate 3 block to use the correct interface — `WalkForwardOptimizer(data_map=data_map)`, then `run_optimization(candidate_spec, start_date=..., train_months=12, test_months=3)`. Removed the `_WFOWrapper` shim (candidate_spec already has `module`/`class`/`edge_id` keys, doubles as `strategy_spec`). The bare-except now re-raises `TypeError` and `AttributeError` so future interface drift surfaces immediately. Also fixed `wfo.py::run_optimization` deprecated `get_loc(method='nearest')` → `get_indexer(..., method='nearest')` (separate but related bug masked by another bare-except).

### [HIGH → RESOLVED 2026-04-28] Engine D Gate 5 (Universe-B) crashes silently — same datetime-index bug just fixed at Gate 1
- Engine: D
- First flagged: 2026-04-28
- Status: **resolved 2026-04-28** — datetime index added at line 806
- Description: `discovery.py:806` built the universe-B equity curve as `pd.Series([h["equity"] for h in b_history])` with no datetime index. `MetricsEngine.cagr()` then crashed on `.days` of the integer RangeIndex. Bare-except set `universe_b_sharpe = float("nan")` and reported `Gate 5 skipped`. The Gate-5 logic `universe_b_passed = math.isnan(...) or > 0` gave every candidate a free pass.
- Fix: Same pattern as Gate 1 — `pd.Series([h["equity"] for h in b_history], index=pd.to_datetime([h["timestamp"] for h in b_history]))`. Exception logging now includes `type(e).__name__` so future schema drift is identifiable instead of being swallowed as "Gate 5 skipped".

### [HIGH → RESOLVED 2026-04-28] Engine D feature_engineering reads regime keys that don't exist on RegimeDetector output
- Engine: D
- First flagged: 2026-04-28
- Status: **resolved 2026-04-28** — read from structured `*_regime["state"]` keys
- Description: `feature_engineering.py:347-358` did `regime_meta.get("correlation")`, but RegimeDetector's output only has `"correlation"` nested under `correlation_regime["state"]`. `Regime_CorrSpike` was hardcoded 0 for every bar of every TreeScanner hunt.
- Fix: Read all three regime states from the structured form (`trend_regime["state"]`, `volatility_regime["state"]`, `correlation_regime["state"]`) with fallback to the top-level backward-compat keys (`trend`, `volatility`). 6 new tests in `tests/test_discovery_regime_features.py` cover the fix path AND the legacy fallback path.

### [MEDIUM → DECISION KEPT 2026-05-07] Engine D has duplicate, drifting WFO orchestrators (evolution_controller and validate_candidate)
- Engine: D + F (charter boundary issue — `evolution_controller.py` lives in `engine_f_governance/` but does Engine D work)
- First flagged: 2026-04-28
- Status: **DECISION 2026-05-07: kept active.** During Phase A task A1
  the agent verified `evolution_controller.py` is NOT dead — it has 10+
  tests in `tests/test_evolution_controller.py` and is "Critical-path
  autonomy code rewired in Phase γ" per memory
  `project_lifecycle_phase_abg_shipped_2026_04_24.md`. Excluded from the
  A1 archive. The "duplicate orchestrator" framing in this finding was
  audit-side error — the two paths solve different problems. Charter-
  boundary concern remains valid (E-engine work in F's package); revisit
  if Engine F refactor is on the roadmap.
- Description: `engines/engine_f_governance/evolution_controller.py` implements a complete validate-from-registry-with-WFO pipeline (`run_cycle`, `run_wfo_for_candidate`). Until commit 8ee8289 it was the only WFO orchestrator with a correct interface — `discovery.py::validate_candidate` was broken. After 8ee8289, validate_candidate is canonical and works; evolution_controller.py is unused. Its module location violates the charter (Engine D work in F's package).
- Charter reference: engine_charters.md Engine F Forbidden Inputs: "Edge discovery, parameter optimization, or walk-forward testing (that's D's job)."
- Recommended next step: User decision required — moving the file is a charter-boundary change which CLAUDE.md classifies as propose-first. Recommend archiving to `Archive/engine_f_governance/evolution_controller.py` since validate_candidate is now the canonical path. Alternative: keep evolution_controller as a future migration target if you want a more structured WFO orchestrator separate from validate_candidate.

### [MEDIUM → RESOLVED 2026-05-07] Engine D bare `except Exception` blocks routinely mask interface-drift bugs
- Engine: D
- First flagged: 2026-04-28
- Status: RESOLVED via two-step fix:
  1. **discovery.py gates (Phase A task A3, commit `2513676`):** Gates 2/4/5/outer narrowed to re-raise `(TypeError, AttributeError, NameError, AssertionError, ImportError)`. NaN-passes-Gate-5 fail-closed. Gate 6 default-True-on-exception flipped to False. Gate 4 None-threshold-bypass eliminated.
  2. **tree_scanner.py + wfo.py (this commit, 2026-05-07):** All four `except Exception` blocks in tree_scanner.py (lines 178, 233, 249, 257) and the one in wfo.py:51 narrowed using the same pattern. tree_scanner now propagates programmer errors (TypeError/AttributeError/NameError/AssertionError/ImportError) from sklearn fit/score calls; runtime data errors (ValueError on single-class folds, etc.) still caught + logged. wfo.py:51 narrowed to `(ValueError, KeyError, IndexError)` — the legitimate runtime conditions where `start_idx = 0` is a sensible fallback.
- Description: `discovery.py::validate_candidate` contains 6 bare `except Exception as e: print(...)` blocks at lines 680, 727, 758, 769, 812, 871 — one for each gate plus the outer wrapper. Each catches programmer errors (TypeError, AttributeError, missing-method) on equal footing with legitimate runtime issues (data unavailability, file IO). This pattern is what hid all three bugs the user just fixed in commit dda474c, AND it is hiding the two HIGH findings above (Gate 3 and Gate 5). The print messages do not include exception type or traceback, so the user cannot distinguish "Gate 3 had no data this run" from "Gate 3 has been broken for weeks." `tree_scanner.py:178, 233, 257` and `wfo.py:48-53` (also `try: get_loc(method='nearest') except: start_idx = 0`) follow the same pattern — bare except, default value, silent continuation.
- Charter reference: Charter Invariant 5 (Engine D): "D's research is fully reproducible given the same data and random seeds." Silent gate-skip violates reproducibility — outcome depends on whether the masked exception fires.
- Recommended next step: Replace each bare `except Exception` with `except (RuntimeError, KeyError, FileNotFoundError) as e:` (or a similar narrow set), and add a final `except Exception:` at the top level that logs the traceback. Programmer errors should propagate; data errors should fail the gate explicitly with `result["gate_X_passed"] = False` not silently default to a passing value. Also, `wfo.py:49` uses the deprecated `get_loc(method='nearest')` API which has been removed in pandas ≥1.4 — the bare except masks an `InvalidIndexError` and falls back to `start_idx = 0`, meaning every WFO run starts from bar 0 regardless of `start_date`.

### [MEDIUM → RESOLVED 2026-04-28] Engine D wfo.py uses deprecated `get_loc(method='nearest')` API
- Engine: D
- First flagged: 2026-04-28
- Status: **resolved 2026-04-28** — switched to `get_indexer` (commit 8ee8289 item 4)
- Description: `wfo.py:49` calls `full_timeline.get_loc(start_dt, method='nearest')`. The `method` parameter was deprecated in pandas 1.4 and removed in pandas 2.0+. On any recent pandas, this raises `TypeError: get_loc() got an unexpected keyword argument 'method'`. The bare `except: start_idx = 0` at line 52 catches it, so every WFO call starts at bar 0 of the timeline — `start_date` is silently ignored. Combined with the Gate 3 interface mismatch above, the production discovery path never reaches this line, so the bug has been latent. But `evolution_controller.run_wfo_for_candidate` (the working orchestrator) DOES reach it — meaning when that path is exercised, all WFO runs use full-history training despite the caller specifying a recent start date.
- Charter reference: "Walk-forward optimization, OOS/IS degradation ratio" (engine_charters.md, Engine D Modules table). Walk-forward by definition requires honoring the rolling window start.
- Recommended next step: Replace with `full_timeline.get_indexer([start_dt], method='nearest')[0]` (or `np.argmin(np.abs(full_timeline - start_dt))` for clarity). Remove the bare except — if the date is unparseable, the run should fail loudly.

### [LOW 2026-05-23 by code-health] Unused defs / constants sweep — 6 functions + 13 module constants/dataclass fields with zero non-def references
- Category: dead-code / hygiene
- Files: 6 unused functions/methods (verified: zero same-file refs AND zero outside-file refs, string-grep aware):
  - `core/feature_foundry/ablation.py:114` `load_ablation` — superseded by `latest_ablation` / `latest_ablation_for_feature` (the consumed APIs)
  - `engines/data_manager/data_manager.py:752` `async_prefetch` — async helper, no callers; class is otherwise used
  - `engines/data_manager/fundamentals/loader.py:38` `ingest_fmp_ratios` — only `FundamentalLoader()` instantiated in scripts/run_shadow_paper.py; this method never invoked. Path-C docs reference the LOADER (not this method) as the SimFin-rewire target
  - `engines/data_manager/fundamentals/simfin_adapter.py:211` `load_fundamentals` — consumers (`_fundamentals_helpers.py`) use `load_panel` instead
  - `engines/engine_d_discovery/gate1_signal_cache.py:251` `invalidate_on_universe_change` — wrapper for `clear()`, never invoked
  - `engines/engine_d_discovery/gate1_signal_cache.py:254` `invalidate_on_window_change` — wrapper for `clear()`, never invoked
- Files: 13 module-level constants / dataclass fields with zero reads anywhere:
  - `engines/engine_d_discovery/bayesian_optimizer.py:107` `EARNINGS_INDICATORS`
  - `engines/engine_f_governance/lifecycle_manager.py:93-94` `LifecycleConfig.retirement_recent_window`, `retirement_decay_std` (dataclass fields)
  - `engines/engine_f_governance/governor.py:48` `GovernorConfig.max_turnover_per_month` (comment says "informational, not enforced by default")
  - `engines/engine_c_portfolio/sleeves/moonshot_sleeve.py:37` `DEFAULT_MAX_POSITION_WEIGHT`
  - `engines/engine_a_alpha/edges/leaps_catalyst_edge.py:60` `_Catalyst.expected_move_pct`
  - `core/feature_foundry/feature.py:60` `Feature.registered_at` (auto-timestamp dataclass field never serialized — `asdict` only used on AblationResult)
  - `scripts/factor_decomp_substrate_honest.py:82` `ALPHA_ANNUAL_FLOOR`
  - `scripts/reset_base_edges.py:49` `SKIP_STATUSES`
  - `scripts/path_c_synthetic_compounder.py:251-253` `ST_CAP_GAINS_RATE`, `ANNUAL_REBALANCE_MONTH`, `ANNUAL_REBALANCE_DAY_NOMINAL`
  - `tests/test_anchor_no_stale_composites.py:30` `STALE_STATUSES`
- Files: 1 obsolete one-shot script: `scripts/run_substrate_arm1_t035.py` — only ref is in a frozen measurement doc (`docs/Measurements/2026-05/substrate_honest_arm1_cockpit_fixed_2026_05_12.md`); no active code or script references
- First flagged: 2026-05-23
- Status: **PARTIAL 2026-05-23** — T-079 removed 5 functions (`invalidate_on_universe_change`, `invalidate_on_window_change`, `load_fundamentals`, `load_ablation`, `async_prefetch`), 3 dataclass fields (`Feature.registered_at`, `LifecycleConfig.retirement_{recent_window,decay_std}`, `GovernorConfig.max_turnover_per_month`), and archived `scripts/run_substrate_arm1_t035.py` to `Archive/scripts/`. 69 relevant tests pass. **REMAINING:** `ingest_fmp_ratios` (Medium-risk per agent — Path-C SimFin-rewire template, kept), 13 module-level constants in 8 files (deferred to next sweep).
- Recommended next step: a future sweep can pick up the 13 deferred unused constants in atomic per-file commits. Excludes: pytest fixtures (auto-injected by name) and in-file helper functions (used only inside their own script's main). Out of scope per agent instructions: Engine B, Engine E, signal_processor.py.

### [LOW] Engine D save_candidates uses print() instead of structured logger; conflicts with DiscoveryLogger
- Engine: D
- First flagged: 2026-04-28
- Status: not started
- Description: `discovery.py:475, 492, 513` and the gate-result lines at 678, 685, 728, 759, 770, 813, 852, 854 use `print()` for diagnostic output, while the module already has `DiscoveryLogger` (jsonl audit trail) and a module-level `logger = logging.getLogger("DISCOVERY")`. Inconsistent emission means the gate failures we just diagnosed are visible only as stdout in the discovery cycle log file, not in the structured `discovery_log.jsonl` that downstream tools (and the cockpit) consume. The user's diagnosis of the three bugs in commit dda474c required reading the raw stdout — DiscoveryLogger only sees the final pass/fail, not the gate-skip reason.
- Charter reference: Engine D index.md: "JSONL audit logging of all discovery activity" (`discovery_logger.py` purpose).
- Recommended next step: Route gate-result diagnostics through `DiscoveryLogger.log_validation` (extend the schema with `gate_skipped_reason: Optional[str]`), or at minimum through `logger.warning(...)` so it lands in `evolution.log`. Stop printing.

### [HIGH → SUPERSEDED 2026-05-09] System Sharpe 0.4 on 109-ticker universe vs SPY 0.88 in-sample
- Engine: System-level (Alpha + Risk + Portfolio composition)
- First flagged: 2026-04-25
- Status: **superseded 2026-05-09 by the universe-aware verdict above** — the 109-ticker universe was itself a substrate artifact, so this entry's "SPY benchmark gap" framing is no longer the right lens. The universe-aware substrate produces mean Sharpe 0.507 across 2021-2025 with worst year −0.321; SPY benchmarks shift on the broader universe and the head-to-head needs to be recomputed. Earlier 0.855 / 0.161 / 0.264 figures were all conditioned on the static substrate.
- Description: Universe expansion from 39 to 109 tickers exposed that the system underperforms SPY by ~0.5 Sharpe on a broader equity universe. The previously-reported Sharpe 0.979 was a curated-mega-cap-tech artifact. Existing edges don't generalize beyond the original 39 names; lifecycle correctly paused 2 of 14 (`atr_breakout_v1`, `momentum_edge_v1`) but no replacement alpha was queued.
- 2026-04-27 Phase 2.10 full backtest result: **Sharpe 0.855** (run d134e488) — but this was the run that GENERATED the lifecycle pause decisions. `atr_breakout_v1` (weight 2.5) and `momentum_edge_v1` (weight 1.5) were still at full weight during this run and contributed +$2,694 and +$1,569 respectively. Post-pause, subsequent in-sample runs show Sharpe 0.161–0.677 depending on governor learned-affinity state.
- 2026-04-28 in-sample re-run with paused edges at 0.25x soft-pause: **Sharpe 0.161** (run daf4ad4d). Per-edge breakdown shows `momentum_edge_v1` went from +$1,569 to -$888 at reduced weight; `gap_fill_v1` went from +$151 to -$1,080; "Unknown" exit losses went from -$3,681 to -$11,241. Governor learned-affinity state is a significant contributor to variance between runs.
- **2026-04-28 operational baseline established**: `--no-governor` (0.264) and neutral-governor + weight-cap (0.256) both confirm post-lifecycle Sharpe of **~0.26**. SPY 2021-2024 Sharpe is 0.875 — gap is **-0.619**. This is larger than the pre-Phase-2.10 gap (0.875 - 0.403 = 0.472), because the Phase 2.10 macro edges barely fire in-sample (macro_credit_spread: 0 trades, most others 0-3 trades) and some lose (macro_yield_curve: -$784 from 157 trades). The alpha is concentrated in atr_breakout (soft-paused) and volume_anomaly/herding (unchanged from before Phase 2.10).
- Per-edge breakdown of neutral-governor run (e5055f4e): atr_breakout +$7,988 (2188 trades at 0.5 cap), volume_anomaly +$5,176 (77 trades), herding +$2,119 (49 trades). "Unknown" exit losses: -$14,832 (885 exits, likely atr_breakout stops). All Phase 2.10 macro edges either silent or losing.
- **2026-04-28 (session 3) walk-forward year-by-year results** (`walk_forward_phase210.py`): 0/4 years beat SPY. 2021: sys 0.455 vs SPY 2.133 (delta -1.678); 2022: sys -0.844 vs SPY -0.735 (delta -0.109, worse in bear); 2023: sys 1.167 vs SPY 1.896 (delta -0.729); 2024: sys 1.048 vs SPY 1.882 (delta -0.834). Mean delta: **-0.837**. No year-specific anomaly — uniform structural underperformance. 2022 result is particularly damning: system loses MORE than SPY in the bear year (no defensive value). Paused edges (atr_breakout, momentum_edge) dominate portfolio even at soft-pause weight, with active macro/PEAD edges contributing near-zero.
- **2026-04-28 (session 3) attribution bug fixed**: "Unknown" exit losses (-$14,832) were attribution failures from soft-paused edges where `norm*weight < min_edge_contribution=0.05`. Fixed `_prepare_orders` in `backtest_controller.py` to fall back to signal's top-level `edge` field when `edges_triggered` is empty. Also fixed double version suffix bug in `alpha_engine.py::_edge_meta_from_detail`. Loss is real (momentum_edge_v1 at soft-pause weight); fix only corrects governance metrics reporting, not Sharpe.
- **2026-04-28 (session 3) autonomous discovery cycle launched**: `PYTHONHASHSEED=0 PYTHONPATH=. python -m scripts.run_backtest --discover` running. Discovery phase begins after in-sample backtest completes. Expected: hunt + generate candidates + 5-gate validation with BH-FDR. Prior cycle had 132/133 failures — GA fitness was optimizing for in-sample Sharpe which the gauntlet kills. This run uses same GA fitness (ROADMAP plan item 6B — OOS fitness — not yet implemented). Not expecting promotions.
- Remaining gap: **-0.837 mean Sharpe delta vs SPY (year-by-year)**. The edge pool has no alpha that fires reliably at deployment weights across multiple years. Gap is uniform, not year-specific. Closing it requires new alpha sources, not weight tuning. Autonomous discovery cycle is the next mechanism.
- Recommended next step: (1) Wait for discovery cycle results; (2) implement ROADMAP item 6B (GA fitness = 0.5*OOS_Sharpe + 0.3*(1-PBO) + 0.2*(OOS/IS)) so the next cycle optimizes for what the gauntlet rewards; (3) discovery is generating candidates but the fitness function needs to align with the validation gauntlet.
- See: `docs/Sessions/2026-04-27_session.md`, commits dfb0627, f06afb2-b1928c9, aa1cb65, da196b1, 1600e45, 53d5c07, 7db6625, 45abf0e, efbdf8d. Also `scripts/walk_forward_phase210.py`.

### MEDIUM

### [MEDIUM 2026-06-04 by engine-auditor] Engine B defensive-capability surface is doc-buried — living docs omit ≥4 crisis/de-gross paths that Path B needs to find
- Engine: B
- First flagged: 2026-06-04
- Status: not started
- Description: A targeted audit of `engines/engine_b_risk/` for Path-B (crisis-regime robustness) cross-checked the code surface against the living docs (`CURRENT_STATE.md`, `engine_charters.md`, Engine B `index.md`, `high_level_engine_function.md`). Multiple shipped defensive capabilities are NOT discoverable from those docs:
  - **Crisis-floor on `suggested_max_positions`** (`engine_e_regime/advisory.py:228-235`, fields `AdvisoryConfig.crisis_max_positions=5` / `stressed_max_positions=7` at `regime_config.py:105-106`) → consumed ACTIVE by Engine B (`risk_engine.py:729-731`, `risk_advisory_enabled` defaults True, present in prod). This is the de-gross path that motivated the audit and appears in NO living doc.
  - **Regime-conditional vol-target multiplier incl. `portfolio_vol_target_crisis_multiplier=0.40`** (`risk_engine.py:112-116`; `vol_target.py:90-94,251-275`) → GATED-OFF (needs both `portfolio_vol_target_enabled` + `portfolio_vol_target_regime_aware`) AND refuted on 12-yr (T-055h). The shipped CAPABILITY is invisible because MEMORY recorded only the negative VERDICT.
  - **Drawdown-gated kill switch** (`risk_engine.py:83-87,940-979`, thresholds 5/10/15%) → INERT (default OFF). Only mention is one RESOLVED line in `health_check.md:524`; absent from CURRENT_STATE and charter.
  - **`FactorRiskModel`** (`factor_analysis.py`) → ORPHANED: zero importers anywhere in the repo. Charter never mentions a factor-neutrality capability for B.
- Charter reference: engine_charters.md § Engine B Design Notes lists only "Regime-based stop widening — Keep" and the Double-Counting Matrix rows for exposure cap / max positions / risk scalar. The charter does NOT enumerate the drawdown kill switch, the crisis vol-target multiplier, the advisory crisis-positions floor, or factor analysis — so a Path-B planner reading the charter cannot see the de-gross tools already shipped.
- Recommended next step: add a "Defensive / crisis-regime tools (current state + flag)" subsection to the Engine B `index.md` and to `CURRENT_STATE.md`, listing each capability with its file:line, default state (active / inert / gated / refuted-but-present), and the config flag that engages it. Archive `factor_analysis.py` to `Archive/` if it stays unwired, or document the intended consumer.

### [MEDIUM] Variant C HMM wire shipped (OFF-by-default) — flip `feature_set="minimal_c"` + `model_path=hmm_minimal_C_v1.pkl` to engage
- Category: regime / risk-advisory wire-up
- Files: `engines/engine_e_regime/regime_config.py`, `engines/engine_e_regime/regime_detector.py`, `tests/test_hmm_variant_c_wire.py`
- First flagged: 2026-05-08
- Status: SHIPPED. `HMMConfig.feature_set` enum (`legacy` / `minimal_a` / `minimal_b` / `minimal_c`) selects which feature panel `_init_hmm` builds; `minimal_c` matches the trained Variant C model's 7-feature contract (4 long-history FRED + hyg_ig_oas + copper_gold_ratio + xlp_xly_ratio). The downstream advisory→risk_engine wire was already in place (per the inline comment at `advisory.py:200-201`); this commit just makes the right model loadable. 10 tests cover config defaults, model artifact existence, feature-panel logic, end-to-end load, and the confidence-modulates-risk_scalar contract. INERT until user flips `hmm_enabled=True` + selects minimal_c.

### [MEDIUM] Lifecycle gauntlet hasn't fired on V/Q/A edges because the harness wipes its audit trail
- Category: F11 architectural problem manifesting in edge attribution
- Files: `docs/Measurements/2026-05/lifecycle_gauntlet_investigation_2026_05_08.md`
- First flagged: 2026-05-08
- Status: DIAGNOSED, not acted on. The retirement gate WOULD fire on `value_earnings_yield_v1` in 3 of 5 yearly windows (per-year edge Sharpe −3.99 / −3.65 / +2.16 / −1.89 / +0.50). But `lifecycle_history.csv` has zero 2026 entries — the V/Q/A edges shipped 2026-05-06 and every run since has been through `run_isolated`, which snapshots+restores `lifecycle_history.csv`. F11 Phase 2's `apply_journal_at_end=True` path or a real autonomous-cycle run (outside the harness) is needed to actually persist a decision. Per CLAUDE.md not flipping by hand.

### [MEDIUM] Trend on wider universe (722 tickers) is dramatically WORSE than mega-caps — hypothesis refuted
- Category: design verification result
- Files: `docs/Measurements/2026-05/trend_wider_universe_verdict_2026_05_08.md`, `scripts/run_trend_wider_universe.py`
- First flagged: 2026-05-08
- Status: SHIPPED + VERDICT. The mega-cap diagnosis ("trend needs more dispersion") is empirically refuted. Wider-universe trend gives Sortino +0.456 vs mega-cap +1.467 (Δ −1.01); MDD −43.14% vs −23.30% (kill threshold tripped); skewness still negative (−0.133); Sharpe +0.340 vs +1.013. Trend on the long tail has higher idiosyncratic vol that becomes drawdown-amplified, not skew-amplified. The asymmetric-upside property requires structural convexity (LEAPS / event-driven binary catalysts / disciplined stop-losses), not just more universe. Three documented paths forward: reframe as Sharpe vehicle / add stop-losses / drop sleeve.

### [MEDIUM] `value_earnings_yield_v1` is a net-$1,192 drag on the 6-active ensemble (2021-2025)
- Category: per-edge contribution analysis
- Files: `scripts/per_edge_contribution.py`, `docs/Measurements/2026-05/per_edge_contribution_2026_05_08.md`
- First flagged: 2026-05-08 (per-edge attribution)
- Status: FINDING SHIPPED, not yet acted on. Across 2021-2025: `volume_anomaly_v1` carries 93.8% of ensemble PnL (+$3,002); `gap_fill_v1` adds 33.3%; `accruals_inv_sloan_v1` 11.8%; `value_book_to_market_v1` 1.9%. **Two net-drags: `accruals_inv_asset_growth_v1` (−$111, −3.5%) and `value_earnings_yield_v1` (−$1,192, −37.2%).** value_earnings_yield is doubly bad: substantial $-drag AND highly correlated with the value/accrual cluster (+0.507 unconditional, +0.642 adverse) — pure cost, no diversification. Per CLAUDE.md autonomous-improvement rules I am NOT flipping its status manually; the lifecycle gauntlet should catch this on its next run.

### [MEDIUM] Inter-edge correlation roughly DOUBLES under adverse regimes (mean off-diag ρ +0.154 benign → +0.315 adverse)
- Category: regime-conditional diversification
- Files: `Archive/scripts/inter_edge_correlation_regime.py`, `docs/Measurements/2026-05/inter_edge_correlation_regime_2026_05_08.md`
- First flagged: 2026-05-08
- Status: FINDING SHIPPED. 11 of 15 edge pairs become more correlated under stress; 1 pair decorrelates further; 3 flat. Biggest jumpers: gap_fill × volume_anomaly (−0.092 → +0.273, Δ +0.365), value_b2m × value_earnings_yield (+0.337 → +0.642). The 6-active set's effective independent-edge count drops in stress — exactly when diversification would matter most. **Validates the drawdown-gated kill switch design (commit `3acec41`)**: de-grossing in adverse regimes is doing the right thing because effective diversification halves.

### [MEDIUM → RESOLVED 2026-05-08] F11 Phase 2 acceptance gate — 3-rep determinism passes under journal-mode
- Category: F11 verification gate
- Files: `scripts/run_isolated.py` (--journal-mode flag added 2026-05-08)
- First flagged: 2026-05-07 (F11 Phase 2 ship)
- Status: RESOLVED. Verified empirically: in journal-mode, `edges.yml` POST-RUN hash equals anchor hash (`818330dc05e5e58804fa5cace7973640`) — i.e. edges.yml is NOT mutated during the run. Three reps produce 1 unique canon md5 (PASS). Caveat: zero-trade environment; the full no-mutation property holds for non-trivial workloads only by construction (decisions append to journal instead of edges.yml; nothing else mutates the file). Phase 3 (reduce snapshot scope to remove the redundant edges.yml/edge_weights.json files) is now unblocked.

### [MEDIUM] Trend-following Phase 0 sleeve gauntlet → FAIL (positive Sortino, but symmetric tails on S&P mega-caps)
- Category: design verification result
- Files: `engines/engine_c_portfolio/sleeves/trend_following_sleeve.py`, `docs/Measurements/2026-05/trend_phase0_verdict_2026-05-07.md`
- First flagged: 2026-05-07 (Phase 0 verdict run)
- Status: SHIPPED + VERDICT — sleeve scaffolding works; gauntlet bucket is FAIL (2/4 success criteria). Sortino +1.467, Skew −0.153, Tail-ratio 0.997, Upside-capture 1.082, Sharpe +1.013, MDD −23.30%. Bootstrap Sortino 95% CI [0.189, 2.913] with P(>0)=0.98 — the strategy IS positive-Sortino, just not asymmetric upside. **Diagnosis: trend-following on S&P mega-cap universe is beta-amplified; symmetric tail ratio + weakly negative skew is exactly what one expects.** To get the upside-skew property the sleeve gauntlet rewards, trend needs a more dispersion-rich universe (small-caps, futures, alt-asset classes). Not a defect — verdict is honest.

### [MEDIUM] Moonshot Phase 0 sleeve gauntlet → FAIL (kill-triggered) — synthetic-options stand-in confounds the verdict
- Category: design verification result with explicit Phase 0 caveat
- Files: `engines/engine_c_portfolio/sleeves/moonshot_sleeve.py`, `engines/engine_a_alpha/edges/leaps_catalyst_edge.py`, `docs/Measurements/2026-05/moonshot_phase0_verdict_2026-05-07.md`
- First flagged: 2026-05-07
- Status: SHIPPED + VERDICT — sleeve scaffolding works; gauntlet bucket is FAIL kill-triggered (2/4 success, skew −0.028 ≤ kill-floor 0.0). Sortino +1.599, Tail-ratio 0.996, Upside-capture 0.904, Sharpe +1.158, MDD −21.28%. **Phase 0 caveat is load-bearing: leaps_catalyst_edge_v1 uses synthetic Black-Scholes pricing on the underlying close + IV proxy, NOT real OPRA options PnL. The placeholder catalyst stub flags +90d earnings on every name uniformly — so the moonshot sleeve essentially equal-weights the universe. Real OPRA + real catalyst sources (FDA / federal contracts / M&A) are Phase 1 work that fundamentally changes the signal shape.** Treat this verdict as a SLEEVE-PLUMBING signal, not a real strategy verdict.

### [MEDIUM → RESOLVED 2026-05-07] AlphaEngine auto-registered NewsSentimentEdge as the *class*, not an instance — TypeError on every backtest startup since 2026-01-27
- Category: latent integration bug
- Files: `engines/engine_a_alpha/alpha_engine.py:315`
- First flagged: 2026-05-07 (manifested in test_alpha_pipeline TypeError)
- Status: RESOLVED 2026-05-07 — `setdefault("news_sentiment_edge", ns.NewsSentimentEdge)` → `setdefault("news_sentiment_edge", ns.NewsSentimentEdge())`. SignalCollector calls `compute_signals(data_map, now)` as a bound method; passing the class made the call unbound, `data_map` consumed `self`, and `now` was reported missing. Latent for ~4 months. Commit `bb155f5`.

### [MEDIUM → RESOLVED 2026-05-07] No drawdown-aware sizing brake — peak_equity wasn't tracked
- Category: missing risk control
- Files: `engines/engine_c_portfolio/portfolio_engine.py`, `engines/engine_b_risk/risk_engine.py`
- First flagged: 2026-05-07 (R1 audit-week-of)
- Status: RESOLVED — Engine C now tracks `peak_equity` monotonically and emits `current_drawdown_pct` on every snapshot. Engine B reads it under an OFF-by-default `drawdown_kill_switch_enabled` flag with thresholds at 5% (warn), 10% (de-gross via `risk_scaler ×= 0.5`), 15% (block new entries). Default OFF preserves legacy behavior; flipping the flag is the user's call (Engine B charter requires user approval per CLAUDE.md). Commit `3acec41`.

### [MEDIUM → RESOLVED 2026-05-07] Performance summary lacked distributional CIs around point Sharpe
- Category: measurement quality
- Files: `core/metrics_engine.py`, `backtester/backtest_controller.py`
- First flagged: 2026-05-07 (R1 audit-week-of)
- Status: RESOLVED — `MetricsEngine.bootstrap_distribution(returns, metric_fn, ...)` provides moving-block bootstrap (Künsch 1989) with auto block length per Politis-White n^(1/3). Wired into backtest_controller so every new run's `performance_summary.json` carries `bootstrap_distribution: { sharpe: {...}, sortino: {...}, n_returns }` with point estimate, mean/std/median, 95% CI, p>0, n_iterations, block_length. 8 metrics tests + smoke. Commits `ce4cd2c`, `dab74e4`.

### [MEDIUM → RESOLVED 2026-05-07] No queryable index of historical backtests — cross-run forensics required walking 134 directories by hand
- Category: observability
- Files: `core/observability/run_registry.py`, `data/observability/run_registry.sqlite`
- First flagged: 2026-05-07 (forward-plan item)
- Status: RESOLVED — SQLite registry ingests `data/trade_logs/<uuid>/performance_summary.json` + `engine_versions.json` into a single queryable table. CLI: `python -m core.observability.run_registry --rebuild` and `--query "<SQL>"`. Idempotent (UPSERT). Schema covers run_id, snapshot_at, key metrics, per-engine versions, n_trades, source paths. Indices on snapshot_at, sharpe, engine versions. Smoke-tested: 119/134 runs ingested cleanly (15 skipped — unfinished or pre-engine-versions). 8 tests. Commit `b4b9fd3`.

### [MEDIUM] Inter-edge correlation matrix on 6 active edges — no collapsed pairs, two value-family pairs at moderate ρ ≈ 0.51
- Category: ensemble diagnostic
- Files: `scripts/inter_edge_correlation.py`, `docs/Measurements/2026-05/inter_edge_correlation_2026_05_07.md`
- First flagged: 2026-05-07 (R1 audit-week-of)
- Status: SHIPPED 2026-05-07 — daily realized PnL aggregated across 2021-2025 from 5 deterministic-harness multi-year runs (942 trading days). 6/6 active edges show realized PnL. Zero pairs above |ρ|≥0.7 (no collapse). Two moderate pairs (~0.507) involving `value_earnings_yield_v1`: vs `value_book_to_market_v1` and vs `accruals_inv_asset_growth_v1` — expected for value-family factors. The 2 technical edges (gap_fill, volume_anomaly) are well-decorrelated from the 4 fundamentals. Active set is NOT one-strategy-with-extra-trades. Commit `9a79e67`.

### [MEDIUM → RESOLVED 2026-05-07] Engine F duplicate orchestrator `system_governor.py` (653 lines) archived
- Engine: F
- First flagged: 2026-04-28
- Status: RESOLVED 2026-05-07 — file moved to `Archive/engine_f_governance/system_governor.py`
- Description: `engines/engine_f_governance/system_governor.py` defined a 653-line `SystemGovernor` class that orchestrated the same loop as `StrategyGovernor.update_from_trade_log` — read trades, compute edge metrics, update weights, persist to `data/governor/edge_weights.json`, append history. It had its own CLI entry (`python -m engines.engine_f_governance.system_governor --once / --watch`) and its own dataclass-based config. Grep across the entire repo confirmed: every production caller (`mode_controller`, `alpha_engine`, `analytics.edge_feedback`, `scripts.system_validity_check`) imports `StrategyGovernor` from `governor.py`. Nothing imported `SystemGovernor` — only the file's own `__main__` ran it. Lineage check: `governor.py` and `system_governor.py` were both created in commit a651446 on 2026-04-21 (parallel design competition); `governor.py` was picked as canonical and accumulated 5 subsequent commits of lifecycle work, `system_governor.py` was never touched again. Zero tests, zero CLI invocations in `scripts/` or `execution_manual`, zero production importers.
- Files: `Archive/engine_f_governance/system_governor.py` (archived), `engines/engine_f_governance/governor.py` (the canonical one)
- Resolution note: The `--watch` mode + `system_state.json` dashboard cache features in the archived file are NOT implemented in `governor.py` but aren't currently needed. If a future live-deployment workstream needs continuous file watching, mine the archived file rather than re-deriving it.

### [MEDIUM → RESOLVED 2026-05-07] Engine A signal_collector silently returns `{}` when an edge defines a typo'd method — same failure class as the just-fixed `check_signal` vs `compute_signals` bug
- Engine: A
- First flagged: 2026-04-28
- Status: RESOLVED via commits `30251a0` + `a04f215`. `SignalCollector._call_edge` now raises `AttributeError` with a typo-hint message when no recognized signal method is found (was: silent `return {}`). Outer per-edge wrapper + class-instantiation inner block both narrowed-catch `(TypeError, AttributeError, NameError, AssertionError, ImportError)` and re-raise programmer errors (mirrors the gauntlet remediation pattern). 8 new tests in `tests/test_signal_collector_silent_failure.py` lock in the propagate set + the typo-hint behavior. Note: the `xsec_momentum.py` triple-define is a separate concern not addressed by this fix.
- Description: `SignalCollector._call_edge` (signal_collector.py:23-103) tries four method-name dispatches in order: module-level `compute_signals`, module-level `generate_signals`, class instance with `compute_signals`, class instance with `generate_signals`. Each layer is wrapped in `except Exception as inst_err: …` that only emits a print under `is_debug_enabled("COLLECTOR")` (off in production). If an edge author defines `_compute_signals` (private), or `compute_signal` (singular), or any other typo, the collector falls all the way through and returns `{}` — the edge produces zero signals every bar with no warning. This is exactly the symptom of the `check_signal` vs `compute_signals` bug from the user's recent diagnosis: `RuleBasedEdge` only survives because it explicitly wraps `check_signal()` inside a `compute_signals()` method (rule_based_edge.py:72-89). Any edge that ships with the wrong method name today is invisible. Worse, the dispatch order means a class with both `compute_signals` and `generate_signals` will always use `compute_signals` regardless of what the author intended (edges like `xsec_momentum.py` define both, with subtly different return shapes — class.compute_signals returns a `dict[str, float]`; the module-level `compute_signals` at line 181 returns a `list[dict]`, so the dispatcher's choice silently determines the contract).
- Files: `engines/engine_a_alpha/signal_collector.py:23-103`, `engines/engine_a_alpha/edges/xsec_momentum.py:31, 139, 181` (triple-defined `compute_signals` — module-level convenience function shadows the class method).
- Recommended next step: At AlphaEngine startup, validate every registered edge has exactly one of `compute_signals` or `generate_signals` callable, and log a `WARNING` for any edge that has neither. Make the bare-excepts in `_call_edge` re-raise `AttributeError` and `TypeError` so a typo manifests as a startup failure, not a silent zero-signal day. Separately, resolve the `xsec_momentum.py` triple-define: either delete the module-level `compute_signals` (lines 173-187) or document why it exists.

### [MEDIUM → RESOLVED 2026-05-07] Charter inversion: Engine A signal_processor imports EDGE_CATEGORY_MAP from Engine F's regime_tracker
- Engine: A (with import dependency on F)
- First flagged: 2026-04-28
- Status: resolved (Status line corrected 2026-06-11 — was stale "not started" contradicting the RESOLVED title; code-verified: `engines/engine_a_alpha/edge_taxonomy.py` exists and `signal_processor.py:28` imports from it)
- Description: `engines/engine_a_alpha/signal_processor.py:27` does `from engines.engine_f_governance.regime_tracker import EDGE_CATEGORY_MAP`. EDGE_CATEGORY_MAP is a taxonomy mapping edge name patterns to category labels (`"momentum"`, `"mean_reversion"`, etc.) used by SignalProcessor for the learned-affinity multiplier. Per `engine_charters.md`, Engine A produces signals; Engine F governs lifecycle. A should not depend on F's internal data structures at module-import time — that creates a cycle of intent: SignalProcessor's behaviour now depends on whether F has loaded its tracker module, which means refactoring F's tracker can break A's signal aggregation. The proper layering is for the taxonomy to live in `engines/engine_a_alpha/` (where the edges live) or in `core/` as a shared resource, with F consuming it. Today it lives in F because F was the first to need it for affinity tracking, and A grew an after-the-fact dependency. This is a smaller version of the same charter-inversion that flagged `evolution_controller.py` in F (existing finding above): a piece of the system is in the wrong package, and the dependency direction is reversed from what the charter intends.
- Charter reference: engine_charters.md Engine A: "Generates buy/sell signals." Engine F: "Lifecycle, governance, weight learning." Authority Boundaries imply A precedes F in the data flow — A should not import F.
- Files: `engines/engine_a_alpha/signal_processor.py:27`, `engines/engine_f_governance/regime_tracker.py` (where EDGE_CATEGORY_MAP is defined)
- Recommended next step: Move `EDGE_CATEGORY_MAP` to `engines/engine_a_alpha/edge_taxonomy.py` (new small module), import it from there in both `signal_processor.py` and `regime_tracker.py`. Same content, correct dependency direction. While there, check whether `EDGE_CATEGORY_MAP` is the right shape — it currently has the orphan `"rsi_mean_reversion"` entry referenced in the HIGH finding above.

### [MEDIUM → RESOLVED 2026-04-28] Soft-paused edges with high alpha_settings weights still dominate signal ensemble
- Engine: A (AlphaEngine / SignalProcessor) + F (lifecycle soft-pause design)
- First flagged: 2026-04-28
- Status: **resolved 2026-04-28** — `PAUSED_MAX_WEIGHT = 0.5` cap added (commit 93411be)
- Description: The soft-pause 0.25x multiplier is applied to the edge's pre-pause alpha_settings weight. `atr_breakout_v1` at weight 2.5 → 0.625 after soft-pause, still above most active edges at 0.5-1.0. Caused atr_breakout to generate 2371 trades in the 2026-04-28 in-sample run (vs 51 for volume_anomaly at weight 1.0) and drive "Unknown" exit losses to -$11K. Fix: added `PAUSED_MAX_WEIGHT = 0.5` cap in `mode_controller.py` after the multiplier — paused edges can now be at most `min(weight × 0.25, 0.5)`. For atr_breakout: min(0.625, 0.5) = 0.5, below active edges at 1.0. Does not affect edges whose pre-pause weight was ≤ 2.0 (they stay below 0.5 after multiplier).

### [MEDIUM → RESOLVED 2026-04-28] Governor learned-affinity from OOS runs contaminates subsequent in-sample backtests
- Engine: F (Governor — `data/governor/edge_weights.json` persistence)
- First flagged: 2026-04-28
- Status: **resolved 2026-04-28** — `--reset-governor` flag shipped
- Description: `edge_weights.json` (the governor's learned SR-based affinity per edge) persists across runs. When OOS backtests run first (especially on adversarial windows like 2025 data), the governor downgrades edge weights that underperform in OOS. Loading those downgraded weights into a subsequent in-sample run injects forward-looking signal: the governor "knows" which edges struggled in 2025 and suppresses them in the 2021-2024 window where they were profitable. Observed 2026-04-28: governor-enabled in-sample run got Sharpe 0.161 vs 0.264 with `--no-governor` — the difference is -0.103 Sharpe from stale/wrong affinity. Resetting to neutral (all weights = 1.0) before in-sample runs restores correct behavior.
- Fix: `StrategyGovernor.reset_weights()` clears `_weights` and `_regime_weights` to empty (→ all edges default to 1.0 in `get_edge_weights()`). Does NOT write to disk — persisted production state is unchanged. Exposed as `--reset-governor` flag in `scripts/run_backtest.py` and `reset_governor=True` parameter in `run_backtest_logic()`. 4 tests in `tests/test_governor_reset.py` cover: clears in-memory weights, does not touch disk, clears regime weights, idempotent. Use: `PYTHONHASHSEED=0 python -m scripts.run_backtest --reset-governor` for clean in-sample measurement.

### [MEDIUM → PARTIALLY RESOLVED 2026-04-28] Soft-paused edges at 0.25x are primary driver of 2025 OOS underperformance
- Engine: F (Governance — lifecycle soft-pause weight policy)
- First flagged: 2026-04-28
- Status: **partially resolved 2026-04-28** — paused→retired path added (commit 1dca4a5)
- Description: 2025 OOS backtest (2025-01-01 → 2026-04-17) shows Sharpe 0.173 vs SPY 0.975. Root cause: `atr_breakout_v1` and `momentum_edge_v1` are soft-paused at 0.25x weight, but still generate 3082 + 1642 = 4724 fills and lose -$3,357 + -$1,208 = -$4,565 combined. The positive Phase 2.10 edges generate only +$3,556 total. The paused edges had no lifecycle exit path — they could only revive or stay paused forever.
- 2026-04-28 partial fix: `LifecycleManager` now has a `paused → retired` transition gate. After `paused_retirement_min_days` (default 90 days), if an edge remains benchmark-negative and is not currently reviving, it gets retired rather than accumulating 0.25x losses indefinitely. 4 new tests, 19/19 lifecycle tests pass.
- Remaining gap: The 2025 OOS backtest result won't change until the in-sample run fires the retirement (next run with lifecycle=True against 2021-2024 data). After that run, both edges will retire at the 2024-12-31 evaluation point and won't be loaded in the 2025 OOS at all.

### [MEDIUM] Earnings backend swapped Finnhub → yfinance — PEAD now has training data
- Engine: A (data_manager — `engines/data_manager/earnings_data.py`)
- First flagged: 2026-04-25
- Status: resolved-but-noted — swap done, cache re-bootstrapped
- Description: Finnhub's free tier was confirmed (2026-04-25) to return 0 historical earnings — per-symbol queries return empty regardless of window, and the unfiltered calendar exposes only the last ~30 days. With Finnhub as the backend, `pead_edge.py` had no historical training data and was functionally inert. Swapped backend to yfinance which exposes ~25 quarters per ticker with `EPS Estimate`, `Reported EPS`, and computed surprise %. Re-bootstrapped on 115-ticker universe → 109 with events, 6 empty (ETFs / BRK.B), 0 failed, 2698 total events. PEAD edge confirmed live (NVDA 2024-02-21 +13% surprise → signal 0.127 day +1, decays linearly to 0 at day 90). `FINNHUB_API_KEY` retained in `.env` for possible real-time use during paper trading; no longer consumed by `EarningsDataManager`. Old Finnhub cache archived at `data/Archive_earnings_finnhub_2026_04_25/`.
- Recommended next step: monitor — yfinance scraping has known reliability issues; if it degrades, the manager already falls back to cache so backtests stay reproducible. No further action unless cache rebuilds start failing.
- See: `memory/project_finnhub_free_tier_no_historical_2026_04_25.md`, `tests/test_earnings_data.py`.

### [MEDIUM → RESOLVED 2026-04-27] signal_processor lacks conditional-weight composition for regime-conditional edges
- Engine: A (signal_processor)
- First flagged: 2026-04-25
- Status: **resolved 2026-04-27** — regime_gate primitive shipped (commit aa1cb65)
- Description: Resolved. `SignalProcessor` now accepts `regime_gates: Dict[str, Dict[str, float]]` in its constructor. Per-edge gate maps Engine E `regime_summary` labels ("benign", "stressed", "crisis") to weight multipliers [0,1]. Gate multiplies `w` in the weighted-mean aggregation; missing labels default to 1.0; `regime_meta=None` defaults to "benign". `low_vol_factor_v1` re-enabled at weight 0.5 with gate `{benign:0.15, stressed:1.0, crisis:1.0}`. 8 new tests in `tests/test_signal_processor_regime_gate.py` covering all edge cases.
- See: commit aa1cb65, `tests/test_signal_processor_regime_gate.py`, `data/governor/edges.yml` (low_vol_factor_v1 entry).

### LOW

### [LOW → RESOLVED 2026-04-28] Lifecycle must not modify edge statuses during OOS backtesting
- Engine: F (Governance) + backtesting methodology
- First flagged: 2026-04-28
- Status: **resolved 2026-04-28** — `lifecycle_readonly` mode shipped
- Description: Running lifecycle on the same OOS window multiple times caused a cascade: each run retired more edges that underperformed in that window, making the result non-reproducible. Fixed by adding `LifecycleConfig.readonly: bool = False`. When `True`, all gate evaluations run and events are returned, but `_save_registry()` and `_append_history()` are skipped — the same OOS window always produces the same result regardless of how many times it's run.
- Wire-up: `GovernorConfig.lifecycle_readonly: bool = False` added; `governor_settings.json` carries the key. Set `lifecycle_readonly: true` in governor_settings to enter OOS measurement mode. 2 new tests in `tests/test_lifecycle_manager.py` (21/21 pass): `test_readonly_mode_does_not_write_registry`, `test_readonly_mode_does_not_append_history`.

---

## Resolved (last 90 days)

### [HIGH → RESOLVED 2026-06-11] Engine F: governor.py docstrings mislabel the engine as "Engine D"
- Engine: F
- First flagged: 2026-06-04; Resolved: 2026-06-11
- Description: governor.py:21 and governor.py:89 both attributed the Governor to "Engine D" (stale label from before the D/F split). Both updated to "Engine F". Doc-only change, autonomous-allowed.
- See: `engines/engine_f_governance/governor.py:21,89`; fresh-view review `docs/Audit/fresh_view_full_system_review_2026_06_11.md`.

### [HIGH → RESOLVED 2026-06-10] Worktree anchor divergence — director/A/B have different `_isolated_anchor/edges.yml`, inflating apparent canon-md5 drift
- Category: harness state / cross-worktree measurement comparability
- First flagged: 2026-05-11 by A's T-024 outbox (Q1 canon shifted 182af6a1 → 28cfa38f, Sharpe 0.127 → 0.281). Director-side investigation found root cause: each worktree's `data/governor/_isolated_anchor/edges.yml` has diverged. Director + B have md5 `818330dc...` (size 86,674, mtimes May 7-8); A has md5 `8da9ce85...` (size 88,278, mtime May 10). A's anchor is 1,604 bytes larger — almost certainly the auto-registered T-014/T-016/T-017/T-018 paused edges appended to A's anchor's edges.yml during a recent backtest run (which suggests one or more measurement runs had end-of-run edges.yml mutations NOT gated by journal-mode).
- Implication: T-019's "paused-tier inert" conclusion needs reframing. T-019 measured ~Δ Sharpe 0.0000 vs T-002 on the OLD anchor (without the new paused edges). The new paused edges weren't being loaded at all, NOT producing 0 trades through soft-pause. T-020's per-edge isolation used `exact_edge_ids` so it bypassed this and correctly showed 5/5 generate trades at full weight.
- A's current canon (28cfa38f) IS the production state on the NEW anchor: 5 paused edges loaded, soft-pause applies 0.25× weight, they contribute trades, lifting Q1 Sharpe by +0.154. This is the real measurement going forward.
- Forward action: standardize on A's anchor as the canonical one (it reflects post-T-014/T-016/T-017/T-018 production reality). Re-save anchor in director + B worktrees via `python -m scripts.run_isolated --save-anchor`. Per CLAUDE.md, --save-anchor is propose-first-equivalent since it changes governor state — director executes after explicit user nod.
- Open question: HOW did A's edges.yml get those 1,604 bytes? Auto-register-on-import shouldn't write to edges.yml. Possibly an end-of-run lifecycle mutation in a non-journal-mode run. Worth a brief code audit (~30 min) to find the mutation path.
- Resolved by: T-131 governor hygiene (anchor-vs-live proven canon-irrelevant bitwise; anchors write-protected; manifest policy) + T-133 follow-ups (all worktrees symlinked to the director's write-protected anchors; divergence class closed end-to-end). TASK_LEDGER: both `done` 2026-06-10. (triaged 2026-06-11)

### [HIGH → SUPERSEDED 2026-05-29] T-055e regime-conditional vol-target — CLEARS CLAUDE.md `[NN-SHARPE-CI]` gate; T-055b flag-flip now DEFENSIBLE (user-decision gate)
- Category: engine-completion / first T-055-series result to clear strict ci_low > 0
- 15 fresh arm1 backtests (EWMA + regime_aware) reusing T-055d arm0. 10/10 cells canon-stable.
- **Δ Sharpe = +0.549 with ci_low +0.047 (>0)** — first regime-conditional layer to clear the gate. ALL THREE headline metrics (Sharpe, CAGR, MDD) have ci_low > 0.
- **Progressive improvement T-055c → T-055d → T-055e**:
  - T-055c rolling: Δ +0.256, ci_low -0.140
  - T-055d EWMA: Δ +0.289, ci_low -0.046
  - T-055e regime+EWMA: **Δ +0.549, ci_low +0.047**
- **MDD improves in every single year** (+0.38 to +2.74pp range, +1.11pp mean, ci_low +0.68pp). Harvey-et-al-2018 defensive value finally showing up consistently.
- **2022 outlier (-0.997 Sharpe)** is the only per-year loss — regime-conditional over-degrosses in sustained bear, missing partial recoveries. Worst per-year loss in entire T-055 series. Cost of the policy's 2021/2024 wins.
- **2024 rescue preserved** (+1.564 vs T-055d +1.622) AND **2025 trap-elimination preserved** (-0.198 vs T-055d -0.128) — both T-055d wins survive the regime-conditional layer.
- **T-055b flag-flip is now defensible** per strict CLAUDE.md `[NN-SHARPE-CI]`. NOT autonomously recommended (Engine B propose-first). Director surfaces to user-decision gate with full per-year evidence (2022 -0.997 cost included).
- Branch `feature/engine-b-vol-target-regime-conditional-t055e` pushed.
- Audit: `docs/Audit/engine_b_vol_target_regime_conditional_t055e_2026_05_23.md`.
- Superseded by: T-055g multiplier sweep (refuted on canonical substrate; no arm clears ci_low>0; 2022 sign-flipped) and T-055h 12-yr verify (Δ Sharpe -0.214; vol-target chapter CLOSED, `docs/Audit/vol_target_12yr_verify_t055h_2026_05_29.md`). TASK_LEDGER marks T-055e `superseded`; CURRENT_STATE.md lists the +0.549 "DEFENSIBLE" verdict as retired. Not current truth per the CLAUDE.md supersession rule. (triaged 2026-06-11)

### [MEDIUM → SUPERSEDED 2026-05-29] T-055d EWMA estimator A/B — EWMA strictly dominates rolling but ci_low still touches zero
- Category: engine-completion measurement / Moreira-Muir lift verification — EWMA alternative
- 15 fresh EWMA-arm backtests (arm0 OFF reused from T-055c); 10/10 cells canon-stable.
- **EWMA wins on every metric**: Δ Sharpe point +0.289 (vs rolling +0.256), ci_low -0.046 (vs -0.140; 67 % tighter), Δ MDD -0.03pp (vs rolling -0.62pp).
- **Key wins**: 2024 fragility rescue AMPLIFIED (+1.622 vs rolling +1.303) and **2025 vol-shock trap FIXED** (-0.128 vs rolling -0.942). The catastrophic outlier that drove T-055c's wide CI is gone under EWMA.
- **Trade-offs**: EWMA loses some 2021 bull lever-up (+0.289 vs +0.915) and gets 2022 bear WORSE (-0.594 vs -0.129) because the faster estimator misses partial recoveries.
- Verdict **MARGINAL** per strict CLAUDE.md `[NN-SHARPE-CI]`: ci_low(-0.046) still < 0; T-055b autonomous-recommend NOT cleared. **Director's call**: hold for T-055e (regime-conditional target) layered on EWMA, or surface to user with the +0.094 ci_low improvement evidence.
- Branch `feature/engine-b-vol-target-ewma-t055d` pushed.
- Audit: `docs/Audit/engine_b_vol_target_ewma_t055d_2026_05_22.md`.
- Superseded by: T-055h 12-yr verify closed the vol-target chapter (Δ Sharpe -0.214; `docs/Audit/vol_target_12yr_verify_t055h_2026_05_29.md`); the held T-055e follow-up ran and was itself refuted (T-055g/T-055h). TASK_LEDGER: T-055d `done`, chapter closed. (triaged 2026-06-11)

### [MEDIUM → SUPERSEDED 2026-05-29] T-055c A/B lift verification — MARGINAL verdict, T-055b flag-flip NOT YET recommended
- Category: engine-completion measurement / Moreira-Muir 2017 verification
- 30-backtest grid (3-rep × 5-yr × 2-arm) — 10/10 cells canon-stable.
- **Mean Sharpe lift: +0.256 point estimate (ABOVE Moreira-Muir +0.10-0.20 band) but ci_low = -0.140 (CROSSES ZERO)**. Per CLAUDE.md `[NN-SHARPE-CI]`: gate on ci_low, not point.
- Per-year variance huge: 2024 fragility-year RESCUED (+1.303), 2025 vol-shock TRAP (-0.942). Net MDD slightly worse (-0.62pp) driven by 2025 outlier.
- **Harness bug found mid-campaign**: `run_vol_target_arms_full.py` was patching `config/risk_settings.json` but mode_controller loads `config/risk_settings.{env}.json` → silent vol-target-disabled for first 4 arm1 runs. Diagnosed via offline scalar simulator, fixed, re-ran. Lesson: env-suffixed config files require env-suffixed patches.
- **Recommended follow-up before T-055b**: T-055d (EWMA λ=0.94 estimator) addresses the 2025 vol-shock failure mode. T-055e (regime-conditional target) addresses the late-cycle trap.
- Branch `feature/engine-b-vol-targeting-ab-t055c` pushed; director merges audit doc to main.
- Audit: `docs/Audit/engine_b_vol_targeting_ab_t055c_2026_05_22.md`.
- Superseded by: T-055d/T-055e follow-ups ran; chapter closed by T-055h 12-yr verify (vol-target CLOSED). TASK_LEDGER: T-055c `refuted`. (triaged 2026-06-11)

### [MEDIUM → RESOLVED 2026-05-29] Engine B portfolio-level vol-targeting LANDED (T-055; defense-first OFF, flag-flip gated on T-055b post full A/B)
- Category: engine completion / Moreira-Muir 2017 infrastructure
- `engines/engine_b_risk/vol_target.py` ships VolTargetConfig + compute_vol_scale + composer. Wired into `risk_engine.py` Path A (target_weight) AND Path B (ATR-risk) via the new `_compute_portfolio_vol_scalar()` helper. Reads from existing `self.portfolio.history` (same source as drawdown kill switch — no new state plumbing).
- **Defense-first default**: `portfolio_vol_target_enabled=False` in `config/risk_settings.json`. Determinism gate verified: single-rep Q1 canon md5 = `182af6a1240da35055f716ef9dfcd333` — bitwise identical to T-019 clean-main reference.
- **Hard constraints met**: does NOT override kill-switch / drawdown-halt (those short-circuit before scalar is applied); no look-ahead (realized vol uses snapshots already in history); 12 new tests pass + 25 existing Engine B tests still pass.
- **A/B Q1 smoke (T-055)**: ARM_OFF and ARM_ON both produced canon-identical trades.csv. This is BY DESIGN — Q1 (~62 trading days) is below the 60-day warmup gate; the scalar barely fires. The smoke validates wiring/determinism, NOT Sharpe lift.
- **Sharpe lift validation deferred to T-055c** (full 3-rep × 5-yr × 2-arm = 30-run grid, ~6 hr wall). Expected lift per Moreira-Muir 2017 + dive 2: +0.10-0.20 Sharpe. Bootstrap CI per CLAUDE.md 6th non-negotiable will be required there.
- Branch `feature/engine-b-vol-targeting` pushed; director merges after review per CLAUDE.md Engine B propose-first rule.
- Resolved by: infrastructure shipped (TASK_LEDGER T-055 `done`); the gated T-055b flag-flip question closed NEGATIVE via T-055g/T-055h (vol-target chapter CLOSED on 12-yr; flag stays OFF). (triaged 2026-06-11)

### [HIGH → RESOLVED 2026-05-25] T-057b verification — confidence-gate lift COLLAPSES on extended substrate; flag-flip NOT recommended
- Category: engine-completion verification / substrate-conditional lift falsified
- Cloud campaign: 50/50 cells succeeded (2 arms × 5 yrs × 5 reps). T-057's +0.793 Sharpe lift on Alpaca-only substrate REVERSES to **Δ -0.075** on the extended Stooq+Alpaca substrate.
- ci_low(Δ Sharpe): iid -0.532, block-bootstrap (5-yr) -1.154. **Both fail CLAUDE.md `[NN-SHARPE-CI]` strict gate.**
- **Per-year pattern reveals regime dependency**: gate helps when OFF is weak (2021 +0.72, 2024 +1.43) but HURTS when OFF is strong (2022 -1.79, 2023 -1.13). 3 of 5 years remain consistent-sign vs original T-057; 2 of 5 reverse sign (2022, 2023 — both years where extended substrate's stronger OFF baseline left less room for the gate).
- **MBL Gate-0 also FAILS**: 5-yr window insufficient for SR=1.0 lift claim at N=230 trials (needs 10.88 yr). Maximum clearable SR on this design: 1.475.
- **3 of 10 cells show 1-rep determinism drift** (arm0_off/2021, arm2_n3/2022, arm2_n3/2024). The 5-rep design eliminated T-057's original 2021 arm2_n3 drift but surfaced 3 new cells — within-container module-global drift, worth a T-057c-determinism-investigation follow-up.
- **Recommendation: DO NOT flip `confidence_gate.enabled=True`.** Stays False on main pending: (a) regime-conditional confidence gate (mirror T-055e pattern), (b) 11+ yr backtest window to clear MBL.
- Lessons-learned pattern: SECOND time a positive lift has reversed sign on substrate change (vol-targeting series + confidence-gate series). ANY positive lift must be substrate-verified BEFORE production-recommend.
- Audit: `docs/Audit/confidence_gated_flag_flip_t057b_2026_05_24.md`.
- Resolved by: recommendation adopted — flag stays False; T-053b 12-yr re-verify REFUTED T-057 definitively (TASK_LEDGER T-057b `refuted`, T-053b `done`, `docs/Audit/multi_year_window_harness_t053b_2026_05_25.md`); determinism follow-up closed by T-057c-det + T-057c-fp-followup. CURRENT_STATE.md lists T-057 as refuted. (triaged 2026-06-11)

### [LOW → RESOLVED 2026-05-23] Dead-branches scan came back clean
- Category: dead-code (sentinel)
- Files: engines/ (in-scope), core/, scripts/, tests/
- AST scan for `if False:` / `if 0:` / unreachable-after-return found zero violations across 436 .py files. Good sign; previous cleanup work has held up. No action needed.
- Resolved by: clean-scan sentinel — the entry's own text states "No action needed". (triaged 2026-06-11)

### [HIGH → RESOLVED 2026-05-12] Engine D production `hunt()` does NOT pass `ticker=` to `compute_all_features` — foundry_feature gene type has been a dead-letter office for the entire project arc
- Category: structural plumbing failure / engine integration
- Surfaced 2026-05-12 evening by Agent B during T-038-CONT vectorization investigation. Empirical: production hunt() on 53 tickers × 1yr completes in 20.5 sec emitting 3 candidates; the smoke's 65min silent CPU was in a DIFFERENT, still-unprofiled code path.
- **Cascade impact**: T-022 (gene encoding extension), T-023 (Gate 1 caching), T-024 (seed enrichment), T-038-CONT (vectorization), T-052 (4 regime features) all share this dead-letter destiny until the wiring fix lands. The "Foundry features invisible to GA gene encoding" diagnosis from 2026-05-11 was correct but located in the wrong layer — gene encoding was fine; the FEATURE COMPUTE in production was the gap.
- **Reframes Engine D history**: T-021's "all 3 candidates were rsi_bounce_v1 mutations" was structural plumbing failure, not signal weakness. T-025's 30/30 Gate 1 kill rate was the same dead-letter pattern. T-026 BLOCKED on stale composites masked the wiring issue.
- Forward action: T-054 dispatch in flight (Agent A as of 2026-05-12 LATE). Single likely-1-line fix in `engines/engine_d_discovery/discovery.py` unblocks ~30+ hr of prior agent investment.
- Discipline implication: parallels the cockpit metrics-pipeline bug pattern — silent structural gap masked as functional weakness. **Worth a broader dead-letter audit across the codebase** (any registered-but-never-invoked feature/method/config flag). See newly-flagged MEDIUM entry below.
- Resolved by: T-054 production hunt() ticker= wiring fix (TASK_LEDGER `done` 2026-05-12; audit `production_hunt_ticker_wiring_postfix_2026_05_12.json`), unblocking the T-022/23/24/38/52 cascade. (triaged 2026-06-11)

### [HIGH → RESOLVED 2026-05-12 by T-043 ship + flag-flip] Lifecycle gauntlet was asymmetric — strict on entry (Gate 6 FF5+Mom α t > 2), loose on retirement (raw Sharpe only)
- Category: governance / lifecycle policy
- T-043 (merged 219648b 2026-05-12) added `engines/engine_f_governance/factor_alpha_gate.py` — symmetric retirement gate matching Discovery Gate 6.
- Re-evaluation on T-035/T-036 cockpit-fixed trade logs: **6 of 7 evaluated edges fire** (gap_fill, volume_anomaly, value_book_to_market, accruals_inv_sloan, value_earnings_yield, accruals_inv_asset_growth retire; STR keeps as UNIFORMLY NOISY).
- `factor_alpha_enabled` flag flipped True in commit b45f829 per user explicit approval. Next live discovery cycle writes retirement decisions to lifecycle journal; user applies via journal_apply.
- gap_fill_v1 + volume_anomaly_v1 fire on **ci_low alone** (point -0.93 above -2.0 threshold; ci_low -3.9/-4.0). Textbook CLAUDE.md 6th non-negotiable working as designed.
- Resolved by: T-043 ship (commit 219648b) + `factor_alpha_enabled` flag-flip (commit b45f829), as recorded in-entry. NOTE: a 2026-06-04 engine-auditor finding (active HIGH in this file) later found the gate INERT on the production lifecycle call path (`factors=` never supplied) — that residual is tracked there, not here. (triaged 2026-06-11)

### [MEDIUM → RESOLVED 2026-05-12] Lifecycle gauntlet doesn't check factor-adjusted α — edges with positive raw PnL but significantly negative factor-adjusted α stay active
- Category: Engine F autonomous-decision gap / lifecycle retirement scope
- First flagged: 2026-05-11 by director-side threshold-calibration audit (`docs/Audit/factor_decomp_threshold_calibration_2026_05_11.md`).
- The `lifecycle_manager.py:_check_retirement` gate (line 655+) uses raw Sharpe-vs-benchmark with CI-aware reading (T-010's update). It catches edges with negative raw PnL/Sharpe. But it does NOT check factor-adjusted α.
- Concrete miss: `value_book_to_market_v1` has +$2,082 raw PnL over 5 years but FF5+Mom α = -2.20% / t = -2.60 (significantly negative idiosyncratic α). It's winning ONLY by buying Mkt+Mom factor exposure that factor ETFs sell cheaper. Lifecycle keeps it active despite the structural-evidence retirement case.
- Future T-026-or-similar dispatch: extend the lifecycle gauntlet's retirement gate to ALSO check factor-adjusted α (HAC t < -2 OR α ci_low < some-negative-threshold). Would catch the value/accruals cluster cleanly. Engine F change — propose-first per CLAUDE.md interpretation since it changes autonomous decision logic; spec needed before dispatch.
- Note: lifecycle hasn't fired on substrate-honest data yet (`data/governor/decision_diary.jsonl` only shows measurement_run entries through 2026-05-10, no lifecycle decisions). So the 3 raw-PnL-negative edges (value_earnings_yield, accruals_inv_sloan, accruals_inv_asset_growth) would auto-retire on the next lifecycle cycle that runs on substrate-honest. Value_book_to_market would stay alive without the factor-adjusted gate.
- Resolved by: T-043 shipped `engines/engine_f_governance/factor_alpha_gate.py` (symmetric FF5+Mom retirement gate, commit 219648b; flag flipped b45f829) — exactly the extension this entry requested; value_book_to_market_v1 is among the 6/7 firing edges. NOTE: the gate is currently inert on the production call path (`factors=` never supplied) — tracked as an active HIGH entry (2026-06-04) in this file. (triaged 2026-06-11)

### [HIGH → RESOLVED 2026-05-12] Engine D gene encoding is single-archetype — Discovery cannot emit candidates from expanded Foundry vocabulary
- Category: Engine D structural / autonomous-discovery gap
- First flagged: 2026-05-11 by T-2026-05-10-021 (first-ever Discovery cycle on substrate-honest). All 3 candidates were `rsi_bounce_v1` mutations. The post-T-006 Foundry features + post-T-014 calendar features (mom_12_1, mom_6_1, vol_regime, ma_cross, dist_52w_high, drawdown, hyg_lqd_spread, FOMC drift, sell-in-May, etc.) are NOT REACHABLE by the GA's gene encoding.
- Implication: vocabulary expansion (T-006, T-013, T-014) delivered zero benefit to Discovery's autonomous candidate-search until gene encoding is extended. **This is the primary structural blocker for the engines-first lift path.** Highest-leverage Engine D work going forward.
- Forward action: dispatch Engine D gene-encoding extension (next dispatch, ~6-10 hr Engine D autonomy lane).
- Resolved by: T-022 gene-encoding extension + T-054 production hunt() `ticker=` wiring fix (TASK_LEDGER T-054 `done` — the actual blocking layer). The 2026-06-04 engine-auditor entry in this file documents the now-expanded GA vocabulary (macro/behavioral/regime + short/market_neutral directions). (triaged 2026-06-11)

### [HIGH → SUPERSEDED 2026-05-11] Paused-tier edge expansion is INERT against the active-edge-dominated ensemble — Discovery cycle is the only lift mechanism for new edges
- Category: alpha mechanism / forward-path-bottleneck
- First flagged: 2026-05-10 by T-019 substrate-honest post-edge-expansion measurement. Δ Sharpe = 0.0000 in BOTH arms vs T-002. Bit-identical canon md5s in 15/15 cells per arm. The 5 new paused edges from 2026-05-09 (T-014 calendar features, T-016 momentum × 3, T-017 pairs MA/V, T-018 dividend init) contributed **zero trades** over 5-year substrate-honest — while pre-existing `news_sentiment_edge_v1` at the same 0.25× soft-pause weight produced 451 trades. Infrastructure isn't the filter; signal density at the substrate-honest scale is.
- Implication: today's edge-expansion track delivered zero substrate-honest alpha. Paused parking provides "post-pause revival evidence" capability — NOT a path to alpha contribution while still paused. **The mechanism for converting today's inventory into headline lift is Discovery's substrate-honest gauntlet (Phase 2.10 + Gates 7/8) promoting edges to `status='active'`.**
- Forward action: dispatch a Discovery cycle on substrate-honest data; let the gauntlet validate which (if any) of the new paused edges deserve promotion. Adding MORE paused edges is wasted effort until the existing inventory's gauntlet outcome is known.
- Superseded by: the 2026-05-11 worktree-anchor investigation — T-019 ran against a stale anchor that never loaded the 5 new paused edges (NOT soft-pause producing 0 trades); on the canonical anchor they contribute trades (+0.154 Q1 Sharpe). Anchor-divergence class later closed by T-131/T-133. (triaged 2026-06-11)

### [HIGH → RESOLVED 2026-05-12 (RE-CORRECTED BY T-035)] The substrate-honest baseline is 0.598, not 0.270
- Category: measurement integrity / canonical baseline
- 2026-05-12 update: T-2026-05-12-035 re-measured T-002 Arm 1 with the cockpit metrics-pipeline fix (T-034) applied. **Corrected mean Arm 1 Sharpe = 0.598** (vs T-002 reported 0.270, Δ +0.328). The shift is from bug-correction, not substrate change.
- The cockpit bug was bi-directional: winning years inflated (peak_equity is monotone non-decreasing, lower variance than real equity; the metric reader was reading peak-as-equity, inflating Sharpe) and losing years zeroed (peak stays at starting capital while real equity falls → flat equity read → Sharpe ≈ 0). Director's prediction "barely fires in small-MDD cells" was REFUTED.
- Per-year corrected | T-002 → T-035: 2021 0.413 → **1.791** | 2022 0.116 → **0.294** | 2023 0.261 → **1.221** | 2024 0.236 → **-0.613** | 2025 0.325 → **0.297** | mean 0.270 → **0.598**.
- **No single year clears `ci_low > 0`** even at corrected level. Per CLAUDE.md 6th non-negotiable: 0.598 mean Sharpe is better than 0.270 but the strategy is **bull-conditional with material 2024-style downside** that was previously hidden.
- All prior bear-year Sharpe-bearing audits remain SUSPECT until re-measured: T-002 Arm 2, T-019 paused-tier-inert, T-029 per-regime decomp, T-020 per-edge isolation, F6 multi-year, T-030 STR. T-036 (in flight) takes highest-priority subset (STR + per-regime adverse cells).
- The "0.9154 surviving-6 contaminated" finding (below, retained for history) is still correct: that was the zero-trade-regression bug, NOT the cockpit bug. They are two distinct measurement-integrity issues; both retract their respective headlines.
- Resolved by: T-035 metrics-pipeline fix + re-measurement (TASK_LEDGER `done` 2026-05-12). The 0.598 figure is itself now historical — current baselines per CURRENT_STATE.md: ~0.81 (12-yr, not formally validated) and 0.237 (26-yr clean arm0, canon 529e5520). Do not quote 0.598 as current. (triaged 2026-06-11)

### [HIGH → RESOLVED-AS-CONTAMINATED 2026-05-09 (historical, see entry above for the corrected 0.598 baseline as of 2026-05-12)] The 0.9154 surviving-6 result was contaminated by the zero-trade regression
- Category: measurement integrity / superseded headlines
- First flagged: 2026-05-09 evening by dev review at `docs/Sessions/Other-dev-opinion/05-09-26.md`. The C-collapses-1 surviving-6 mean Sharpe 0.9154 (PARTIAL bucket, basis for the "6-edge surviving set" narrative) was almost certainly measured during the 2026-05-07 zero-trade-regression window before the bug was caught. **It is RETRACTED.**
- The honest baseline going forward is the substrate-honest two-arm result T-002 (May 9): **Arm 1 mean Sharpe 0.2702 with bootstrap 95% CI [-0.383, +0.771] — `ci_low` includes zero.** Arm 2 (HMM ON) at 0.294, Δ +0.024, NEUTRAL bucket per pre-commit. **(SUPERSEDED 2026-05-12 by T-035 corrected 0.598 — see entry above.)**
- Compounding evidence: T-004 factor-decomp on the same trade logs found 0/6 edges have positive factor-adjusted α at t > 2; 4/6 have *significantly negative* factor-adjusted α (t between -2.6 and -5.7). The load-bearing alpha (`volume_anomaly_v1`) is GENUINELY NOISY at t = 0.83, R² = 0.04. (Factor decomp uses real equity returns, not the buggy metric — so this finding is INDEPENDENT of the cockpit bug and remains valid.)
- Implication: the project now operates against the **0.598** baseline (corrected 2026-05-12) as the comparison point for whether engine completion delivers projected lift.
- Forward path: engines-first directive anchored. Three parallel tracks (engine completion, edge expansion, defensive layer), all gated on engine completion before Moonshot/AI evaluation.
- Resolved by: retraction recorded in-entry; superseded chain continues in the T-035 entry above. (triaged 2026-06-11)

### [HIGH → SUPERSEDED 2026-05-12] Foundation Gate baseline (mean Sharpe 1.296) was a substrate artifact — universe-aware rerun lands 0.507 (−0.789, −61%)
- Engine: data_manager (pre-2026-05-09 the survivorship-bias-aware loader was unwired) + orchestration (ModeController defaulted to the static 109-ticker config) + Engine A (edges were tuned and validated against the static-substrate Sharpes)
- First flagged: 2026-05-09 — F6 finding from the dev-opinion consolidated audit (the 115-name static config was identified as a load-bearing assumption hiding under every prior Sharpe headline). The universe loader (`engines/data_manager/universe.py`) was built 2026-04-24 but never wired into ModeController, so every measurement campaign through 2026-05-08 ran on the static substrate.
- Wiring shipped: `f6-universe-loader-wire` branch, commit `69006fb`. New `engines/data_manager/universe_resolver.py::resolve_universe` is opt-in via `use_historical_universe` config flag (default false to preserve prior measurement reproducibility) or `--use-historical-universe` CLI flag on `scripts/run_multi_year`. 15 resolver unit tests pass; 40 existing universe.py tests pass.
- Verdict: COLLAPSES. See full report `docs/Measurements/2026-05/universe_aware_verdict_2026_05_09.md`. Per-year deltas: 2021 1.666→0.862 (−0.804), 2022 0.583→−0.321 (−0.904), 2023 1.387→1.292 (−0.095), 2024 1.890→0.268 (−1.622), 2025 0.954→0.436 (−0.518). 4 of 5 years collapse far outside the noise band; 2023 alone holds together. Mean clears 0.5 by 0.0074 — cosmetic rather than meaningful.
- Implication: Path 1 ship is not viable as previously framed. The kill thesis suspended by the 2026-04-30 Foundation Gate pass is re-engaged on the universe-aware substrate. Engine A edges tuned against the static substrate need re-validation under universe-aware geometry before any per-edge Sharpe number is treated as honest. ~~The 26-54 missing-CSV delisted names per year (FRC, DISCA, ATVI, etc.) remain unincluded — adding them would push deeper into COLLAPSES, so the measured 0.507 is an upper bound.~~ **Update 2026-05-08:** the missing-CSV gap is now closed (48/48 = 100% of legitimate names sourced via Alpaca; see `missing_csv_closure_2026_05_08.md`). The 0.507 figure becomes a re-measurable number, not an upper bound, as soon as the zero-trade regression (new HIGH item above) is fixed.
- Honest scope: the wiring is a clean fix and lands as a Pareto improvement to the substrate (default behavior preserved, opt-in path validated, deterministic). The COLLAPSES verdict is an information win, not a project-breaking finding — it tells us where to focus next: edge-level re-validation, regime-conditional analysis of why 2023 held, and the remaining missing-CSV names.
- Next: (1) default `use_historical_universe: true` for measurement campaigns going forward, (2) re-run the Discovery gauntlet on universe-aware substrate, ~~(3) populate the missing CSVs via `scripts/fetch_universe.py`,~~ **(3) DONE 2026-05-08** — `scripts/fetch_missing_delisted.py` closed the 48-name gap, (4) re-evaluate which alpha generators survive in 2023 vs. the others.
- Superseded by: the zero-trade-regression fix + T-035 cockpit-metrics correction re-based the number (0.507 → 0.598), and the substrate was later canonicalized (T-081/T-082) with deeper-window baselines (12-yr ~0.81, 26-yr 0.237 per CURRENT_STATE.md). The COLLAPSES verdict stands historically; none of this entry's numbers are current truth. (triaged 2026-06-11)

### [HIGH → RESOLVED 2026-05-08] Backtests produce zero trades since 2026-05-07 evening — every isolated run lands trades_canon_md5 = `d41d8cd9...` (empty file)
- **RESOLVED 2026-05-08:** root cause was `EarningsVolEdge` raising `TypeError: Cannot compare tz-naive and tz-aware timestamps` — silently swallowed by `backtest_controller.py:389` bare-except. Fix: tz-strip in yfinance cache (commit `4b7a14e`). The bug class is closed by T-005 narrow-except in `backtest_controller.py:389-405` (commit `129c7ba`, merged `4aa634e`); programmer errors now propagate so the next regression of this shape surfaces immediately. Also swept in T-011 (Engine A, 7 sites) and T-012 (Engine B drawdown-halt). Bonus audit at `docs/Audit/bare_except_audit_2026_05_08.md` flagged 188 broader sites; 7 highest-impact closed today.
- Resolved by: commits 4b7a14e (tz-strip fix) + 129c7ba/4aa634e (T-005 narrow-except), as recorded in-entry. (triaged 2026-06-11)

### [HIGH — historical context only] Original symptom report from 2026-05-08 (pre-fix):
- Category: governor-state regression / measurement gating
- First flagged: 2026-05-08 during the missing-CSV closure work. The closure was complete (48/48 sourced, 100% of legitimate names) but the post-closure substrate-honest re-measurement returned Sharpe 0.0 with zero trades. A static-substrate repro yielded the same result. A code-only rollback to commit `7d54de3` (last commit before the 2026-05-07 evening regression window) also yielded zero trades, ruling out the engine/orchestration trees as the cause.
- Last trade-producing run in `data/trade_logs/`: `35e2f3dd-49e9-45bd-b72f-828efba624a7` at 2026-05-07 01:39 (Sharpe −0.107, 10,581 trade rows). Every subsequent isolated run is empty.
- Bisect: at code-state `7d54de3` (post-F4-merge, pre-F11-phase-2) — 0 trades. At code-state `1085069` (parent of the F4-merge `cae2002`, with composer.py moved aside) — also 0 trades. So the cause is not in any commit since the last good run; it's purely in state restored by `isolated()` from `data/governor/_isolated_anchor/`. Cross-reference: a note in `project_engine_c_f4_closed_2026_05_07.md` at the time of the F4 merge flagged "incomplete worktree governor state" producing zero trades — that state propagated into the parent repo at 2026-05-07 01:49 (the timestamp on `_isolated_anchor/edges.yml`).
- The anchor's `edge_weights.json` (last modified 2026-05-06) lacks weight entries for the 4 active V/Q/A edges (`value_earnings_yield_v1`, `value_book_to_market_v1`, `accruals_inv_sloan_v1`, `accruals_inv_asset_growth_v1`); if any recent governor change started reading missing entries as 0.0 instead of defaulting to 1.0, the V/Q/A edges would silently abstain. This is the most likely root cause and the first thing to check.
- Implication: ALL measurement work done after 2026-05-07 01:39 needs verification — anything claiming a Sharpe number without a trades.csv with >1 line is reading stale results, not measuring current code. The substrate-honest re-measurement closing the 0.5074 upper bound is blocked on this fix.
- Next: (1) check `_isolated_anchor/edge_weights.json` first — restore weights for the 4 V/Q/A active edges. (2) If that doesn't unblock, bisect among the 4 anchor files (`edges.yml`, `edge_weights.json`, `lifecycle_history.csv`, `regime_edge_performance.json`) by restoring each from a pre-2026-05-07 trade_log's `engine_versions.json` snapshot. (3) Verify with a 1-year static-substrate smoke producing ~0.27 Sharpe / ~13k trades. (4) Then re-anchor and re-run the 5-year substrate-honest measurement against the now-closed missing-CSV gap. See `docs/Measurements/2026-05/missing_csv_closure_2026_05_08.md` for the full debug trail (3 forward repros + 2 code-bisect rollbacks all confirming state-side cause).
- Resolved by: the same fix as the entry above; kept as historical context only per its own header. (triaged 2026-06-11)

### [MEDIUM → RESOLVED 2026-04-27] Lifecycle audit-trail / registry-state divergence detection missing (2026-04-25)
- Engine: F (Governance)
- Resolved: 2026-04-27
- Description: `LifecycleManager._audit_registry_divergence_check()` was shipped as part of "Phase α v3" (committed before 2026-04-27 session). At the top of `evaluate()`, it reads `lifecycle_history.csv`, extracts the most recent `new_status` per edge via `groupby("edge_id").last()`, then compares against the current registry status in `edges.yml`. Any disagreement logs a `WARNING` with edge_id, audit_trail value, registry value, and a bug-class label (`status_reverted` or `missing_from_registry`). The check is wrapped in `try/except` so it cannot break the lifecycle loop — observability only, not gating. 6 unit tests in `tests/test_lifecycle_manager.py` cover: no-op on empty history, no-op when audit and registry agree, flags status_reverted, flags missing_from_registry, uses most-recent-event correctly, runs silently when evaluate() is called with divergence present.
- See: `engines/engine_f_governance/lifecycle_manager.py::_audit_registry_divergence_check` (lines 357-449), `tests/test_lifecycle_manager.py` lines 292-420.

### [MEDIUM → RESOLVED 2026-04-27] Engine D's GA gene vocabulary searches a strip-mined space (2026-04-24)
- Engine: D (Discovery)
- Resolved: 2026-04-27
- Description: `CompositeEdge` now evaluates `"macro"` (10% probability — T10Y2Y yield curve, VIX level, UNRATE unemployment delta) and `"earnings"` (5% — EPS surprise % look-back) gene types. Both use lazy instance-level caching. Gene vocabulary weights: technical 40%→35%, regime 10%→5%, fundamental 15%→10%. GA now discovers macro-conditional and earnings-event combinations.
- See: commit 45abf0e, `tests/test_composite_edge_macro_earnings.py`.

### [HIGH → RESOLVED 2026-04-25] EdgeRegistry.ensure() silently overrode lifecycle status (2026-04-25)
- Engine: A (EdgeRegistry, used by F's lifecycle)
- Status: **resolved 2026-04-25** — `ensure()` write-protects `status` per edges.yml Write Contract; `tests/test_edge_registry.py` is the regression check
- Resolved: 2026-04-25
- Description: Auto-register-on-import code (`momentum_edge.py:64`, `momentum_factor_edge.py:113`) called `EdgeRegistry().ensure(EdgeSpec(..., status="active"))`. Pre-fix `ensure()` had `if spec.status: s.status = spec.status` — the comment claimed "keep status as-is unless provided" but `EdgeSpec.status` defaults to `"active"` so callers always provided it. Effect: every backtest startup imported `momentum_edge.py` → reverted any lifecycle-applied pause/retire on `momentum_edge_v1` back to `active`. Visible only as repeated identical pause events in `lifecycle_history.csv` across runs. `atr_breakout_v1` escaped because `atr_breakout.py` has no auto-register block, which is why the "first autonomous pause" finding from 2026-04-24 felt real (it was — for atr_breakout). Discovered today via the methodology rule "bitwise-identical canon md5 when expecting change is diagnostic evidence."
- Fix: `EdgeRegistry.ensure()` now write-protects `status` for existing specs, per the `edges.yml` Write Contract documented in `PROJECT_CONTEXT.md` ("F writes: status field changes — neither engine deletes the other's fields"). Added `tests/test_edge_registry.py` with 12 tests including `test_repro_momentum_edge_import_does_not_revive_paused` as a permanent regression check.
- See: `memory/project_registry_status_stomp_bug_2026_04_25.md`, `docs/State/lessons_learned.md` 2026-04-25 entry, `tests/test_edge_registry.py`.

---

## Archived (older than 90 days)

When resolved items pass 90 days, move them here. Keep this section 
trimmed — if it grows beyond ~50 items, archive the oldest to 
`docs/Archive/audits/health_check_resolved_<year>.md`.

*No archived findings yet.*

---

## Severity guide

- **HIGH**: Actively breaks things or causes silent harm. Examples: 
  broken imports still being called, deprecated paths in active use, 
  bugs that produce wrong outputs, code that bypasses charter 
  boundaries in ways that affect runtime behavior.
- **MEDIUM**: Structural debt that doesn't break the system today 
  but compounds. Examples: god classes (>500 lines), duplicate 
  implementations, oversized functions (>200 lines), missing test 
  coverage on critical paths, charter drift that hasn't yet caused 
  visible problems.
- **LOW**: Hygiene issues. Examples: stale TODOs (>90 days), unused 
  imports, empty test stubs, formatting inconsistencies, outdated 
  comments.

## Format

Findings appended by subagents follow one of two formats:

**From engine-auditor:**
```
### [SEVERITY] <one-line summary>
- Engine: <A/B/C/D/E/F>
- First flagged: <YYYY-MM-DD>
- Status: not started
- Description: <what's wrong>
- Charter reference: <quote or section from engine_charters.md>
- Recommended next step: <specific action>
```

**From code-health:**
```
### [SEVERITY] <one-line summary>
- Category: <duplicate/god-class/dead-code/stale-todo/other>
- Files: <path(s)>
- First flagged: <YYYY-MM-DD>
- Status: not started
- Recommended next step: <specific action>
```

When a finding is resolved, move the entry to the Resolved section 
and add a `- Resolved: <YYYY-MM-DD>` line.
---

## Code-health scan 2026-05-06 — post-V/Q/A merge (code-health subagent)

Scope: Engine A (6 new SimFin V/Q/A edges + signal_processor + fill_share_capper),
Engine E (HMM panel + cross_asset_confirm + transition_warning), Engine C
(HRP + sleeves), Engine D (gauntlet architectural fix), core/feature_foundry,
core/observability (net-new), engines/data_manager/fundamentals/simfin_adapter,
scripts/path_c_synthetic_compounder, scripts/run_multi_year, scripts/run_isolated.
Prior was tilted toward bare-except / silent-cache / dict-iteration patterns
because the past week surfaced 2 Path C bugs in those families.

Severity counts: HIGH 3 | MEDIUM 6 | LOW 4. Top-3 highest-impact below.

### [HIGH → RESOLVED 2026-05-06] Negative-equity ROIC silently zeros the denominator — distressed firms inflate to top-quintile rank
- Category: silent-correctness / signal-quality bug
- Files:
  - `engines/engine_a_alpha/edges/quality_roic_edge.py:87-88` (NEW edge, just shipped)
  - `scripts/path_c_synthetic_compounder.py:663-664` (Path C real-fundamentals composite)
- First flagged: 2026-05-06
- **Status: RESOLVED 2026-05-06.** Branch `vqa-edges-bugfixes` commit `6c9b4af`. Fix mirrors `value_book_to_market_edge`'s explicit `equity <= 0 → return None` in both `quality_roic_edge.compute_signals` and `path_c_synthetic_compounder.compute_composite_score_real`. Regression test `test_quality_roic_drops_negative_equity_ticker` synthesizes a negative-equity firm and asserts it is dropped from the cross-section before quintile selection. See audit `docs/Measurements/2026-05/vqa_edges_bugfix_2026_05_06.md`.
- Description: ROIC denominator is computed as
  `invested_capital = (equity if equity > 0 else 0.0) + (lt_debt if lt_debt > 0 else 0.0)`.
  A firm with negative equity (deeply distressed) thus has its equity component
  silently treated as 0, and ROIC = `NOPAT / lt_debt`. That denominator is small,
  so distressed firms can score a *very high* ROIC and end up in the top
  quintile of the long-only Quality factor — the opposite of what the academic
  factor (Asness-Frazzini-Pedersen "Quality Minus Junk") prescribes. Compare
  to `value_book_to_market_edge.py:76-78` four files away in the same package,
  which correctly drops negative-equity firms with an explicit `return None`
  and the comment "Negative-equity firms produce misleading signs for B/P".
  The same silent-zero pattern is duplicated in the Path C compounder's
  `compute_composite_score_real` at line 663, so any historical Path C
  result that scored a near-bankrupt firm into the top quintile is suspect.
  This was unflagged on the 2024 smoke test (canon `4ae83833f6d5a35a...`)
  because the prod 109-ticker universe is mostly mature mega-caps with
  positive equity — but the next universe expansion (Workstream H, growing
  past 109) increases the probability of a negative-equity name in the panel.
- Recommended next step: In both sites, return `None` (drop the ticker) when
  `equity is None or equity <= 0`. The contract should match
  `value_book_to_market_edge.py`'s explicit comment. Add a regression test in
  `tests/test_fundamentals_edges.py` with a synthetic negative-equity ticker
  asserting it is dropped from `quality_roic_v1`'s top-quintile.

### [HIGH → RESOLVED 2026-05-06] `top_quintile_long_signals` swallows ALL exceptions inside the score function — every new V/Q/A edge inherits the silent-bug pattern
- Category: bare-except / silent failure
- Files: `engines/engine_a_alpha/edges/_fundamentals_helpers.py:205-208`
- First flagged: 2026-05-06
- **Status: RESOLVED 2026-05-06.** Branch `vqa-edges-bugfixes` commit `6c9b4af`. The bare `except Exception` is replaced with two narrowed tuples — `_PROGRAMMER_ERRORS = (AttributeError, NameError, ImportError, SyntaxError, AssertionError)` re-raises so bugs surface, `_DATA_MISSING_ERRORS = (KeyError, IndexError, ValueError, ZeroDivisionError, TypeError)` is suppressed and DEBUG-logged with ticker + edge_id + exception type. Tests `test_helper_reraises_attribute_error_from_score_fn` and `test_helper_suppresses_value_error_from_score_fn` lock the contract. See audit `docs/Measurements/2026-05/vqa_edges_bugfix_2026_05_06.md`.
- Description: The shared helper that all 6 new SimFin V/Q/A edges use has a
  bare `except Exception: raw = None` around the per-ticker score callable.
  Programmer errors in any score function — `TypeError` from a bad pandas
  operation, `AttributeError` from a method-name typo, `KeyError` from a
  panel-column rename, `ImportError` from a moved helper — are caught
  identically to legitimate data-missing cases and quietly turn into "this
  ticker has no signal." All 6 edges (`value_earnings_yield_v1`,
  `value_book_to_market_v1`, `quality_roic_v1`, `quality_gross_profitability_v1`,
  `accruals_inv_sloan_v1`, `accruals_inv_asset_growth_v1`) share this code
  path. The 2024 smoke result showed all 6 firing — that result tells you
  the happy path works; it tells you nothing about whether the gauntlet of
  exception types are being silenced. This is the same failure mode the
  prior memory `project_gauntlet_consolidated_fix_2026_05_01` documents in
  Engine D (gates 1-6 hid 5 distinct bugs behind bare-excepts for weeks).
- Recommended next step: Narrow the catch to `except (KeyError,
  IndexError, ValueError, ZeroDivisionError) as exc:` (the legitimate
  data-shape exceptions a score_fn might raise on a sparse SimFin slice),
  log the exception class+message at DEBUG level when raw is None, and let
  `TypeError` / `AttributeError` / `ImportError` propagate. This is the
  single change that has the largest downside-prevention surface across
  the 6 new edges.

### [HIGH → RESOLVED 2026-05-06] All 6 new V/Q/A edge auto-register blocks swallow EdgeRegistry errors silently
- Category: bare-except / silent-state / status-stomp risk
- Files:
  - `engines/engine_a_alpha/edges/value_earnings_yield_edge.py:101-112`
  - `engines/engine_a_alpha/edges/value_book_to_market_edge.py:94-105`
  - `engines/engine_a_alpha/edges/quality_roic_edge.py:105-116`
  - `engines/engine_a_alpha/edges/quality_gross_profitability_edge.py:84-95`
  - `engines/engine_a_alpha/edges/accruals_inv_sloan_edge.py:100-111`
  - `engines/engine_a_alpha/edges/accruals_inv_asset_growth_edge.py:93-104`
- First flagged: 2026-05-06
- **Status: RESOLVED 2026-05-06.** Branch `vqa-edges-bugfixes` commit `6c9b4af`. All 6 auto-register blocks narrowed to `except (FileNotFoundError, PermissionError, OSError) as exc` with WARNING-level log. A future `EdgeSpec` schema-drift `TypeError` or registry-write `RuntimeError` now propagates so the AlphaEngine never loads an edge whose spec failed to install. Tests `test_auto_register_propagates_programmer_errors` (TypeError raised by mocked `ensure()` propagates on importlib.reload) and `test_auto_register_swallows_io_error` (FileNotFoundError degrades gracefully + WARNING log captured) lock the contract. See audit `docs/Measurements/2026-05/vqa_edges_bugfix_2026_05_06.md`.
- Description: Every new edge ends with the same pattern:
  ```python
  try:
      _reg = EdgeRegistry()
      _reg.ensure(EdgeSpec(... status="active"))
  except Exception:
      pass
  ```
  Memory entry `project_registry_status_stomp_bug_2026_04_25.md` documents that
  the EdgeRegistry's `ensure()` was previously stomping pause/retire decisions
  silently — exactly because callers (every edge module) auto-register at
  import. The 04-25 fix made `ensure()` write-protect status; OK. But the
  bare `except Exception: pass` in the call site means: if the registry file
  is locked (concurrent backtest in another worktree), corrupted, or a future
  schema change to `EdgeSpec` breaks the constructor, the 6 new edges will
  silently fail to register but the import will succeed. AlphaEngine will
  load them as classes, the lifecycle layer won't see the spec, and
  `EdgeRegistry.get_all_specs()` will return a registry that's missing 6
  edges. The lifecycle audit divergence check is the only thing that would
  catch this — and only if it runs on a corrupt-registry scenario.
- Recommended next step: Either narrow the catch to `except (FileNotFoundError,
  PermissionError, yaml.YAMLError) as exc: log.warning(f"... auto-register
  skipped: {type(exc).__name__}: {exc}")` so a missing data dir during test
  runs degrades gracefully but a programmer error fails loudly, OR move the
  auto-register to `EdgeRegistry`'s own scan-on-startup so the duplication
  goes away entirely. Latter is the structurally cleaner fix and aligns
  with the `EdgeRegistry` charter.

### [RESOLVED 2026-05-06] cross_asset_confirm.py archived — disabled-by-default, validation showed it as coincident-noise
- Category: dead-code / archive candidate
- Files (now archived): `Archive/engine_e_regime/cross_asset_confirm.py` (183 lines),
  `Archive/engine_e_regime/run_ws_c_smoke.py`
- First flagged: 2026-05-06
- Status: RESOLVED 2026-05-06 on branch `f1-lite-cac-archive`
- Resolution: Option (a) executed — `cross_asset_confirm.py` and
  `run_ws_c_smoke.py` moved via `git mv` to `Archive/engine_e_regime/`;
  `CrossAssetConfirmConfig` dataclass and call site removed from
  `regime_config.py` and `regime_detector.py`; `tests/test_ws_c_cross_asset.py`
  split — 17 feature tests retained, 12 confirmation-function tests dropped
  (~240 lines). The 3 Foundry features (hyg_lqd_spread, dxy_change_20d,
  vvix_or_proxy) STAY — VVIX-proxy was the lone salvageable signal (AUC 0.64).
  See `docs/Measurements/2026-05/cross_asset_confirm_archive_2026_05_06.md`.
- Verification: pytest passes (17 cross-asset feature tests + 80 broader
  regime tests); `RegimeConfig()` no longer has `cross_asset_confirm` attr;
  no production references remain outside `Archive/` and historical docs.

### [MEDIUM → RESOLVED 2026-05-07] `scripts/run_multi_year.py` per-year report assumes uniform rep counts — silent KeyError on heterogeneous failures
- Category: load-bearing harness fragility
- Files: `scripts/run_multi_year.py:77`, lines 84-106
- First flagged: 2026-05-06
- Status: RESOLVED via commit `7f30022`. `_format_markdown_report` now filters failed runs into a separate `failed` bucket before per-year iteration; uses defensive `.get()` for all rep-record fields; reports heterogeneous rep counts honestly (e.g. `reps=[1, 3] (heterogeneous)`); writes a dedicated `## Failed runs` section listing each failure's error trail; gracefully handles all-runs-failed case (was: `StopIteration` in `next(iter(by_year.values()))`). 6 new tests in `tests/test_run_multi_year_report.py` lock in the heterogeneous + all-failed + uniform paths.
- Description: At line 77 the formatter computes
  `len(next(iter(by_year.values())))` to print "N years × M reps". This
  assumes all years have identical rep counts. If a single (year, rep) pair
  errored out (handled at line 206-213 and skipped via `[r for r in results
  if r.get("ok")]` at line 222), the surviving by_year buckets can have
  different lengths and the printed total is misleading. Worse, if ALL reps
  for a year fail, that year is silently dropped from `by_year` entirely,
  meaning the markdown table would not show any FAIL row for that year —
  the report's per-year coverage decays without alerting the reader.
  Separately, line 96's determinism check `det_pass = (sharpe_range <= 0.02
  and canon_unique == 1)` computes `sharpe_range` over only non-None Sharpes
  but `canon_unique` over all reps — so if rep 2 errored out and produced
  `trades_canon_md5 = "(no run_id)"` while reps 1 and 3 produced identical
  canons, `canon_unique = 2` and the run is wrongly flagged FAIL. This is
  the file the user explicitly called out as "load-bearing" (multi-year
  measurement is currently running). The bug doesn't corrupt measurement,
  but it can silently misreport the determinism floor.
- Recommended next step: (a) include FAILED runs in `_format_markdown_report`
  with explicit "FAIL — error: ..." rows so cross-year coverage is visible;
  (b) compute total by `sum(len(reps) for reps in by_year.values())` instead
  of assuming uniformity; (c) compute canon_unique only over reps where
  `ok=True` and `run_id != "?"`. Add a small unit test with a synthetic
  results list mixing failed and successful runs to lock the expected
  report shape.

### [MEDIUM → RESOLVED 2026-05-07] Engine D Gates 2/4/5/6 still use bare `except Exception` — 5 of 6 gates can silently default to "skipped" or "passing"
- Category: bare-except / silent-failure persistence after a known-fix
- Files: `engines/engine_d_discovery/discovery.py:975-976` (Gate 2),
  `:1006-1009` (Gate 3 — has the partial fix that re-raises TypeError /
  AttributeError, this is the model), `:1026-1027` (Gate 4),
  `:1078-1079` (Gate 5), `:1114` (Gate 6 — same pattern), `:1183` (outer
  catch)
- First flagged: 2026-05-06
- Status: RESOLVED via Phase A task A3 (commit `2513676`). Gates 2, 4, 5,
  and the outer wrapper got the narrowed `(TypeError, AttributeError,
  NameError, AssertionError, ImportError)` re-raise pattern. Gate 5
  NaN-passes-the-gate bug specifically eliminated (NaN now FAILS Gate 5).
  Gate 4 None-threshold-bypass eliminated. Gate 6 default-True-on-
  exception flipped to default-False. 4 new tests in
  `tests/test_discovery_gate_remediation.py` cover the failure modes.
- Description: The gauntlet architectural fix landed 2026-05-02 fixed the
  measurement-geometry but kept the same bare-except shape around each
  gate's body. Gate 3 was retrofitted with `if isinstance(e, (TypeError,
  AttributeError)): raise` (lines 1007-1008) — which is exactly the right
  pattern. Gates 2, 4, 5, 6 did NOT receive the same patch. They still
  catch the broad `Exception`, print the type/name, and fall through to
  default values: Gate 2 leaves `survival_rate=0.0`; Gate 4 leaves
  `sig_p=1.0`; Gate 5 leaves `universe_b_sharpe=NaN`; Gate 6 leaves
  factor-alpha defaults. The downstream gate-pass logic varies — Gate 4
  treats `sig_p=1.0` as failing if a `significance_threshold` is set, but
  Gate 5's `universe_b_passed` logic treats NaN as passing. This means a
  silent crash in Gate 5 currently gives a free-pass to the universe-B
  transfer test — the same bug class that was already documented and
  resolved on 2026-04-28. The previous fix-pattern of "narrow the catch
  to `(KeyError, ValueError, RuntimeError)` and re-raise programmer
  errors" should be replicated to the other 4 gates.
- Recommended next step: Apply the same `if isinstance(e, (TypeError,
  AttributeError, ImportError)): raise` defensive promotion to gates 2,
  4, 5, 6 in discovery.py (plus the outer wrapper at line 1183). Or
  better: refactor each gate body into its own `_run_gate_N()` method
  with consistent error-handling — the 5 gate try-except blocks have
  drifted slightly which is its own reason to factor out the boilerplate.

### [RESOLVED 2026-05-07] Engine A imports Engine C optimizers — charter inversion (A→C)
- Category: charter inversion
- Files: `engines/engine_a_alpha/signal_processor.py` (was :229-231 — those imports no longer exist)
- First flagged: 2026-05-06
- Status: RESOLVED. The lazy `from engines.engine_c_portfolio.optimizers
  import HRPOptimizer, TurnoverPenalty` block in `signal_processor.__init__`
  was lifted as part of the C-engines-1 dispatch (commit `cae2002`). HRP
  composition now lives in `engines/engine_c_portfolio/composer.py` as
  `PortfolioComposer`, instantiated unconditionally in
  `engines/engine_a_alpha/alpha_engine.py:506`. SignalProcessor is pure
  edge-aggregation; the optimizer instantiation no longer crosses the A→C
  charter line.
- Remaining surface: `alpha_engine.py:61` imports `PortfolioComposer` and
  `PortfolioOptimizerSettings` from `engine_c_portfolio.composer`. This is
  the *correct* direction for a portfolio-composition service — A consumes
  a C-owned utility class via an explicit interface (compose / is_active),
  rather than instantiating raw optimizers and wiring them by hand. The
  charter language can be tightened to read "portfolio composers are
  C-owned services that A may consume via the composer.compose interface"
  rather than treating ANY A→C import as inversion.
- Verification (2026-05-07): `grep "engines.engine_c_portfolio" engines/engine_a_alpha/`
  returns only the alpha_engine.py:61 composer import; signal_processor
  has zero engine_c imports.

### [MEDIUM → PARTIALLY RESOLVED 2026-05-07] Engine A signal_processor approaching god-class threshold (715 LOC); fundamentals_helpers global cache adds another mutable singleton
- Category: god-class / mutable singleton
- Files: `engines/engine_a_alpha/signal_processor.py` (715 LOC),
  `engines/engine_a_alpha/edges/_fundamentals_helpers.py:43-44, 47-66`
- First flagged: 2026-05-06
- Status: not started
- Description: signal_processor.py grew from ~600 LOC pre-Phase-2.10d to
  715 LOC after fill_share_capper, HRP/turnover wiring, per-ticker
  metalearner, and tier-classifier integration. Still under the 1000-LOC
  hard threshold but worth flagging — the same accretion pattern documented
  in `pattern_debt_hotspots.md`. Adjacent finding: `_fundamentals_helpers.py`
  uses a module-global `_PANEL_CACHE` + `_PANEL_LOAD_FAILED` singleton with
  reset functions for tests. Per-process caching is reasonable for a
  10MB SimFin parquet, but the pattern is the same one that bit Path C's
  `fetch_prices` SPY-cache (a cache key that didn't include all required
  tickers). The current implementation caches the *whole panel* unconditionally,
  so the SPY-cache shape of bug isn't reproducible here — but the test-helper
  contract (`reset_panel_cache`, `set_panel`) means production code can
  observe a fixture-injected panel if a test forgets to reset, with no
  cache-key isolation. Same semantics as the Path C bug, different surface.
- Recommended next step: (a) For signal_processor.py: extract the HRP / turnover
  branch (lines 220-242) into a separate `_PortfolioCompositionLayer` class.
  Same pattern as the LifecycleManager extraction that "Held" per the
  hotspots memory. (b) For `_fundamentals_helpers.py`: replace the module-
  global with `functools.lru_cache(maxsize=1)` on a no-arg `_load_panel_cached()`
  function and a corresponding `_load_panel_cached.cache_clear()` for tests.
  Same effective behavior, no mutable globals, harder for tests to leak
  state into production.

### [MEDIUM → MITIGATED 2026-05-07] `_LAST_OVERLAY_DIAGS` module-global leaks between calls if `run_compounder_backtest` is invoked outside the wrapper
- Category: mutable global / leakage between runs
- Files: `scripts/path_c_synthetic_compounder.py:799, 967, 1295`
- First flagged: 2026-05-06
- Status: MITIGATED via Phase A task A2 (commit `86527f5` / fix
  `686dbfb`). The determinism harness's `isolated()` context now
  lazy-resets `_LAST_OVERLAY_DIAGS` (and 5 other module-level mutable
  globals) at session start. Measurement-determinism risk is closed.
  The architectural finding stands — the module-global itself remains;
  removing it via the recommended return-tuple refactor is still the
  proper fix.
- Description: `_LAST_OVERLAY_DIAGS` is a module-global list mutated inside
  `run_compounder_backtest` (line 967) whenever vol_overlay_enabled=True.
  The wrapper `_run_with_overlay_diagnostics` is the only function that
  CLEARS the global (lines 1277, 1291). Any caller that invokes
  `run_compounder_backtest(vol_overlay_enabled=True, ...)` directly — twice
  in the same process — will see the diagnostics from run-1 leaked into
  run-2's view of the global, since `.append()` is the only mutation. This
  is the same shape as the SPY-cache bug: a process-wide mutable state
  that an unsuspecting caller can be silently affected by. Currently only
  `main()` calls the wrapper, so it's latent; but path_c is in active
  iteration and a future ablation harness might hit this.
- Recommended next step: Pass diagnostics back through the return tuple
  (already a 3-tuple; making it a 4-tuple is straightforward) and remove
  `_LAST_OVERLAY_DIAGS` entirely. The wrapper exists only to hide the
  signature change — a deliberate workaround per its docstring. With the
  signature change, the wrapper goes away and the global goes away.

### [LOW → RESOLVED 2026-05-07] Stale TODO at robustness.py:303 — open since 2026-01-27 (~99 days)
- Category: stale-todo
- Files: `engines/engine_d_discovery/robustness.py:303`
- First flagged: 2026-05-06
- Status: RESOLVED via Phase A task A3 (commit `2513676`).
  `original_sharpe_percentile` now computes the percentile of actual
  Sharpe within the synthetic null distribution by calling
  `strategy_func({"SYTH": df})` once on historical data; falls back to
  50.0 if strategy_func chokes.
- Description: `# TODO: Compare real result to these distribution` set to
  `"original_sharpe_percentile": 0.0` for every PBO result. Git blame:
  cb61f4f8, 2026-01-27. Older than the 90-day stale threshold. The PBO
  output dict has the placeholder field but no consumer ever reads
  `original_sharpe_percentile` (grep across repo: 0 hits outside this
  line). The TODO is noting that the bootstrapped distribution is
  computed but the actual percentile of the live result against that
  distribution isn't returned. Either implement (1 line:
  `np.mean(self._sharpe_distribution < actual_sharpe)`) or delete the
  field from the dict.
- Recommended next step: One-line fix — either compute the percentile
  inline, or delete the field. Don't leave the TODO open another quarter.

### [LOW] `engines/engine_c_portfolio/sleeves/` is a documented design artifact with zero consumers
- Category: design artifact / disable-on-arrival
- Files: `engines/engine_c_portfolio/sleeves/sleeve_base.py` (151 LOC),
  `engines/engine_c_portfolio/sleeves/__init__.py` (26 LOC)
- First flagged: 2026-05-06
- Status: not started
- Description: Both files document themselves as DESIGN ARTIFACTS — the
  module docstrings explicitly say "DESIGN ARTIFACT, not production code"
  and reference Phases M0-M3 of the path_c_compounder_design_2026_05.md
  migration plan. There are zero non-test imports of the `Sleeve` ABC
  anywhere in the repo (grep across `engines/`, `orchestration/`,
  `scripts/`, `cockpit/`: 0 production consumers). The recent Path C
  decision (defer pending HMM in-production-decision-path + Engine B
  regime-driven de-grossing — see `project_compounder_synthetic_failed_2026_05_02`)
  pushes M1+ further out. This is borderline between "intentional
  forward-looking placeholder" and "dead code that will go stale before
  it ships." The honest framing per
  `pattern_duplicate_orchestrators.md`: a placeholder that ships before
  the migration does often grows two implementations.
- Recommended next step: Either (a) ship a minimal concrete sleeve (e.g.
  CoreSleeve wrapping the existing PortfolioPolicy.allocate() at zero
  semantic change) so the abstraction has at least one real consumer
  beyond tests, OR (b) move sleeves/ to `Archive/engine_c_portfolio/sleeves/`
  with a pointer in the migration plan saying "interface-first design,
  resurrect when M1 unblocks." Per CLAUDE.md, archive-not-delete.
  Path (a) is more useful if Path C unblock happens in next quarter; (b)
  if longer.

### [LOW] `accruals_inv_sloan_edge.py` and `accruals_inv_asset_growth_edge.py` directly negate adapter-precomputed factors — adapter-edge contract is implicit
- Category: implicit contract / future-fragility
- Files: `engines/engine_a_alpha/edges/accruals_inv_sloan_edge.py:88`,
  `engines/engine_a_alpha/edges/accruals_inv_asset_growth_edge.py:81`,
  `engines/data_manager/fundamentals/simfin_adapter.py:131-177`
  (`compute_factors` adds these as derived columns)
- First flagged: 2026-05-06
- Status: not started
- Description: The two accruals edges read `sloan_accruals` and `asset_growth`
  directly from the SimFin panel (precomputed by the adapter at panel-build
  time) and just negate them. The contract — "adapter populates these
  columns, edge consumes them" — is implicit; nothing pins the column
  names or sign convention. If a future adapter rewrite renames
  `sloan_accruals` to `accruals_sloan` (or flips the sign convention), the
  edges fail silently via the bare-except in `top_quintile_long_signals`
  (the previous HIGH finding) — score_fn returns None for every ticker,
  edge abstains, signals drop to zero. No alert fires. Compare to the
  `_INC_KEEP` / `_BAL_KEEP` / `_CF_KEEP` mapping dicts in simfin_adapter.py
  (lines 60-92) which are the canonical column-name registry — these two
  derived columns aren't listed there, just computed inline at line 156-174.
- Recommended next step: Add a `_DERIVED_COLUMNS = {"sloan_accruals", ...}`
  set in simfin_adapter.py and assert the columns exist after `compute_factors`.
  Have edges import that constant rather than the literal string, so a
  rename is enforced by the import. Or: add a `DerivedColumnsContract`
  test that builds a tiny synthetic panel, calls `compute_factors`, and
  asserts the expected columns + sign conventions.

### [LOW] `_LAST_OVERLAY_DIAGS` declared at line 1295 but used at line 799 — forward-reference works only because it's never read in the same module-scope
- Category: code-organization / readability
- Files: `scripts/path_c_synthetic_compounder.py:799, 1295`
- First flagged: 2026-05-06
- Status: not started
- Description: `global _LAST_OVERLAY_DIAGS` at line 799 references a name
  defined at module load time at line 1295 (~500 lines later). This works
  in Python because module loading is top-down and the global is read at
  call-time, not at function-definition-time — but it makes the file
  surprising to read, especially given the global is only mutated inside
  `run_compounder_backtest` and read inside `_run_with_overlay_diagnostics`.
  Same finding as the MEDIUM one above on the global itself, but the
  ordering is independently a readability issue.
- Recommended next step: When the MEDIUM finding above is fixed by
  threading diagnostics through the return tuple, this issue resolves
  automatically. Otherwise, move the `_LAST_OVERLAY_DIAGS: List = []`
  declaration to the top of the module (near other module-level state)
  and add a `# Module-global: see _run_with_overlay_diagnostics docstring`
  comment.

### [HIGH] Engine A independently consumes E's `risk_scalar`/`regime_summary` as a crisis de-gross brake — undocumented + double-count with B
- Engine: A
- First flagged: 2026-06-04
- Status: not started
- Description: `signal_processor.py:543-551` reads
  `regime_meta["advisory"]["regime_summary"]` and, when it is
  `"stressed"` or `"crisis"`, multiplies every edge's normalized score
  by `advisory["risk_scalar"]` — an active, default-ON crisis de-gross
  path that lives INSIDE Engine A's forecast layer. The living docs
  attribute `risk_scalar` consumption EXCLUSIVELY to Engine B:
  `high_level_engine_function.md:35` ("Applies Engine E advisory
  `risk_scalar` to ATR sizing budget") and the charter Double-Counting
  Matrix (`engine_charters.md:551`) gives A a dash for Risk-Off /
  risk_scalar. So the SAME crisis fact (risk_scalar < 1.0) is applied
  in BOTH A (shrinks forecast) AND B (shrinks size) — exactly the
  triple-count failure mode the matrix's WARNING block exists to
  prevent. This is the same buried-defensive-path class as the
  Engine B+E `portfolio_vol_target_crisis_multiplier=0.40` /
  `advisory.py` crisis path that no living doc surfaced. It is HIGHLY
  relevant to T-092 Path B (HMM crisis kill-switch) because the
  kill-switch design must account for A ALREADY de-grossing on the
  crisis posterior, or the de-gross gets double-applied.
- Charter reference: `engine_charters.md:88` ("A should be opinionated
  about direction but NOT protective about risk. ... It's B's job to
  say 'I'm only allowing 0.5% exposure right now.'") and the
  Double-Counting Matrix rule (line 557): "Each regime fact should
  affect at most 2 engines, and only through different mechanisms (A
  as a predictive feature, B as a risk constraint — never both as
  'reduce aggressiveness')." A multiplying its own score by risk_scalar
  is "reduce aggressiveness," not "predictive feature."
- Recommended next step: Decide (propose-first, spans A+B+E boundary)
  whether crisis de-gross belongs in A's score path at all. If kept,
  document it explicitly in `high_level_engine_function.md` Engine A
  section AND update the Double-Counting Matrix to show A consuming
  risk_scalar, with an explicit note on why double-application is
  intended. If not, move it entirely to B. Either way, the T-092 Path B
  kill-switch scoping MUST treat this as a pre-existing de-gross layer.

### [HIGH] Engine B's `correlation_regime` consumer is DEAD — E emits a nested dict, B reads a flat string, so elevated/dispersed sector-limit branches never fire
- Engine: B (consumer) / E (producer) — cross-engine contract mismatch
- First flagged: 2026-06-04
- Status: not started
- Description: `risk_engine.py:744` reads `advisory.get("correlation_regime", "normal")` and branches on `== "dispersed"` / `in ("elevated","spike")` to widen/tighten the sector cap (lines 745-748). But Engine E never puts a flat top-level `correlation_regime` string into the advisory dict — `regime_detector.py:259` emits it as a NESTED object `{"state": ..., "confidence": ...}` on the detector output, and `advisory.py` does not surface a flat `correlation_regime` key at all (grep returns zero hits). So B's read always falls through to the `"normal"` default and the correlation-driven sector-limit adjustment (a charter-documented Engine B control — Double-Counting Matrix "Elevated Correlation" + "Dispersed Correlation" rows) NEVER fires in production. Same silent key-mismatch family as the T-088/T-090/T-091 contract-test work; not caught because the contract suite covers config-key⊆dataclass and perf-summary reader⊆producer, but NOT cross-engine advisory-dict reader⊆producer.
- Charter reference: `engine_charters.md` Double-Counting Matrix "Elevated Correlation" row ("B uses as... Lower gross exposure cap, tighter sector limits (20%)") and "Dispersed Correlation" row ("B uses as... Relaxed sector limits (40%)"). Both rows describe a control that is dead on the production path.
- Recommended next step: Decide whether E should publish a flat `correlation_regime` key into `advisory` (Engine E change) or B should read the nested `correlation_regime.state` (Engine B — PROPOSE-FIRST, risk engine). Add a Layer-3 cross-engine advisory contract test (reader keys ⊆ producer keys) so the next advisory-key drift is structurally unmergeable. Re-measure any sector-cap effect AFTER the fix, since historical backtests ran with this control dead.

### [MEDIUM] Engine A ships 4 active/inert macro de-gross "regime tilt" edges that no living doc surfaces (yield-curve ACTIVE; credit-spread/unemployment/real-rate retired-but-importable)
- Engine: A
- First flagged: 2026-06-04
- Status: not started
- Description: `macro_yield_curve_edge.py` auto-registers
  `status="active"` (line 199) and emits a UNIFORM -0.3 tilt across
  every ticker when the 10Y-2Y Treasury spread inverts (line 173-178)
  — a recession/crisis de-gross overlay baked into the alpha layer.
  Three sibling edges (`macro_credit_spread_edge.py`,
  `macro_unemployment_momentum_edge.py`, `macro_real_rate_edge.py`)
  implement the same uniform-defensive-tilt mechanism but auto-register
  `status="retired"` (reclassified 2026-05-02 as Engine E HMM regime
  inputs) — they are inert by default but remain fully importable and
  would re-activate any defensive tilt if a future caller loads them.
  NONE of these appear in CURRENT_STATE.md, the charter, or
  high_level_engine_function.md. They are directly Path-B relevant:
  the yield-curve edge is a SECOND crisis-de-gross path inside A
  (alongside the risk_scalar brake above), and the retired trio are
  ready-made defensive tilts. Note the yield-curve edge fires only when
  the FRED cache is populated (abstains to zeros on a fresh clone), so
  whether it is actually contributing on the canonical substrate needs
  verification, not assumption.
- Charter reference: `engine_charters.md:75` ("Macro-regime gating | A
  consumes E's regime as a predictive feature ... Safety-oriented
  gating belongs in B.") A uniform across-universe -0.3 tilt on curve
  inversion is safety-oriented gross-bias gating, which the charter
  rules belongs in B, not a per-ticker A edge.
- Recommended next step: Inventory which of these macro/defensive edges
  is actually in the loaded edge set on the canonical substrate (read
  the live `data/governor/edges.yml` status, not the auto-register
  default). Document the active ones in the Engine A section of
  high_level_engine_function.md. For T-092 Path B, treat
  `macro_yield_curve_v1` as a pre-existing crisis-defensive overlay
  when scoping the kill-switch.

### [MEDIUM] Engine E's `regime_gate.py` (T-217) — `hmm_regime_label` is BUILT + WIRED into A's conjunctive selector but is UNTRACKED in capability_ledger.md
- Engine: E
- First flagged: 2026-06-22
- Status: not started
- Description: `engines/engine_e_regime/regime_gate.py` (landed
  2026-06-18, T-217) ships a real, behavior-altering capability that
  has NO row in `docs/State/capability_ledger.md`. `hmm_regime_label()`
  (regime_gate.py:63) maps the validated causal HMM `p_crisis`
  (carried in `regime_meta["hmm_regime"]["probabilities"]["crisis"]`)
  to a 3-state label {calm/cautious/crisis}, and it IS imported and
  called on the live code path by Engine A's conjunctive selector at
  `engines/engine_a_alpha/signal_processor.py:546-548`
  (`g_regime = self._CONJ_REGIME_GATE.get(regime, 1.0)`,
  `{calm:1.0, cautious:0.5, crisis:0.0}`). This is exactly the
  buried-capability blind spot the ledger exists to prevent: a shipped,
  wired E→A defensive gate with no capability-state row. It is
  reachable only under `EnsembleSettings.mode="conjunctive"`
  (signal_processor.py:688), which is default-OFF
  (`mode="weighted_mean"`, signal_processor.py:76; no prod config sets
  `conjunctive`), so it is correctly DORMANT today — but dormancy is a
  Prod-flag-state, not a reason to omit the row. Note the prod HMM
  (`hmm_3state_v1.pkl`, `hmm_enabled=true`) DOES emit a `crisis` state
  key, so the label is functional, not a phantom — if the conjunctive
  mode were flipped on, g_regime would produce real {1.0/0.5/0.0}
  multipliers, not a permanent no-op.
- Charter reference: `engine_charters.md` Engine E "Validated regime
  findings" #5 ("Correct uses of the HMM regime: descriptive
  context/feature for A (`g_regime` per-edge SELECTION gate, T-217 —
  pending composition measure)"). The charter documents this as a
  deliverable; the capability_ledger (the file whose stated purpose is
  "flat index of every BEHAVIOR-ALTERING capability the code currently
  ships") omits it. `DESIGN_FIDELITY.md:19` tracks the conjunctive
  selector as "NEVER-BUILT → BUILDING NOW (A/T-216)" — STALE: it is now
  BUILT (signal_processor.py:510 `_conjunctive_aggregate`) and DORMANT
  (default-OFF), not never-built.
- Recommended next step: Add an Engine E row to capability_ledger.md:
  Capability = "`hmm_regime_label` g_regime label (causal-HMM 3-state)
  consumed by A's conjunctive selector"; Source =
  `engines/engine_e_regime/regime_gate.py:63`; Wired-to-live-path? =
  `mode-gated` (reachable only under `ensemble.mode=conjunctive`);
  Prod-flag-state = default-OFF (`mode=weighted_mean`). Separately
  update DESIGN_FIDELITY.md row 1 from NEVER-BUILT to DORMANT
  (built + wired, default-OFF, composition measure pending).

### [LOW] Engine E's `RegimeGate` class + `build_gates_from_stats`/`gate_from_sharpe`/`from_file` (T-217 per-edge overlay gate) are BUILT but have ZERO production consumers and are UNTRACKED
- Engine: E
- First flagged: 2026-06-22
- Status: not started
- Description: Beyond `hmm_regime_label` (tracked-gap above),
  `regime_gate.py` also ships a per-(edge, regime) overlay-gate
  subsystem: `RegimeGate` dataclass (line 108) with
  `gate(edge, regime_meta)` (line 117), the Sharpe→gate mapper
  `gate_from_sharpe` (line 77), the stats-to-gate builder
  `build_gates_from_stats` (line 87), and JSON persistence
  `to_file`/`from_file` (lines 132/137). Grep across
  engines/backtester/orchestration/core/live_trader finds ZERO
  importers of any of these symbols — only `hmm_regime_label` is
  consumed (by signal_processor.py). No `regime_gate*.json` artifact
  exists on disk, so even `from_file` would always fail-safe to OFF.
  This is a built-but-DORMANT scaffold (the per-edge SELECTION-gate half
  of the conjunctive vision, distinct from the portfolio-level
  g_regime label A actually uses) with no capability-ledger row. Not
  HIGH because it is genuinely inert (no caller, no artifact) and
  default-OFF by construction — but it is real code that alters
  behavior the moment a caller composes a populated gate, which is the
  ledger's inclusion criterion.
- Charter reference: same as above — `engine_charters.md` Engine E
  finding #5 references the g_regime gate as a deliverable; the
  capability_ledger does not carry it.
- Recommended next step: Add a single LOW/DORMANT Engine E ledger row
  for the `RegimeGate` per-edge overlay subsystem (Source
  `engines/engine_e_regime/regime_gate.py:108`; Wired-to-live-path? =
  `no — never wired` / zero importers; Prod-flag-state = N/A inert). If
  it stays unwired past the T-217 composition measure, flag for
  Archive per the orphaned-code policy (sibling of the
  `MultiSleeveAggregator`/`FactorRiskModel` orphan rows).

### [HIGH] Engine D's Gate 6 (FF5+Mom factor-alpha) is DEMOTED to report-only in prod config but `capability_ledger.md` still lists it as an enforcing promotion gate (STALE / REFUTED_LISTED_ACTIVE)
- Engine: D
- First flagged: 2026-06-22
- Status: not started
- Description: `config/discovery_settings.json` sets `factor_gate_mode: "report"` (T-203 re-aim to "beat-the-robo, not academic factor-orthogonality"). At `discovery.py:1552`, `factor_alpha_passed_for_gate = factor_alpha_passed if _fgm=="kill" else True` — so in prod Gate 6 computes the HAC-corrected FF5+Mom t-stat and records it as a diagnostic, but it can NO LONGER KILL a candidate (always passes). The capability_ledger Engine-D row says Gate 6 "already enforces factor-adjusted alpha at promotion (reality includes factor-α)" with Wired=`yes`/Default=ON — which now misrepresents production behavior. A gate the registry presents as load-bearing has been semantically neutered by a config flag the registry doesn't surface.
- Charter reference: `engine_charters.md` Engine D Invariant #4 ("Every candidate must pass 4-gate validation ... before promotion"); capability_ledger Engine-D Gate-6 row.
- Recommended next step: Update the Gate-6 ledger row to Prod-flag-state = `report-only (factor_gate_mode='report')`, note the config knob + `discovery.py:1552` gate-passthrough, tag REFUTED_LISTED_ACTIVE→re-described. Restoring KILL is director-gated.

### [HIGH] `robo_deploy_gate_enabled=true` declares `evaluate_deploy_readiness` the "PRIMARY deploy-readiness gate" but it is NEVER wired into the discovery cycle (config-claims-but-not-wired; PHANTOM-as-described)
- Engine: D
- First flagged: 2026-06-22
- Status: not started
- Description: `config/discovery_settings.json` sets `robo_deploy_gate_enabled: true` and its comment names `core.combined_candidate_scorecard.evaluate_deploy_readiness` as the PRIMARY deploy-readiness gate. Repo-wide grep finds `evaluate_deploy_readiness` called ONLY from `scripts/run_combined_scorecard.py` and its own test; the config key `robo_deploy_gate_enabled` has ZERO python consumers anywhere. It is NOT invoked by `validate_candidate` (discovery.py) or the `--discover` cycle in `mode_controller.py`. The config asserts a primary promotion gate the autonomous discovery path does not run. Not capability_ledger-tracked.
- Charter reference: capability_ledger.md "Wired-to-live-path?" rule (config-flag × wiring-guard × path-reachability); fails leg 2 (wiring) despite leg 1 (flag=true) reading active.
- Recommended next step: Either (a) wire `evaluate_deploy_readiness` into `validate_candidate` behind the flag, or (b) correct the config comment to say it is an offline/manual scorecard — propose first (touches promotion path). Add a ledger row for whichever reality is chosen.

### [MEDIUM] Engine D's Foundry-feature gene bucket (20% emit, T-022) + `foundry_seed_fraction=0.5` + `use_bayesian_opt` are real behavior-altering Discovery capabilities UNTRACKED in capability_ledger.md
- Engine: D
- First flagged: 2026-06-22
- Status: not started
- Description: The capability_ledger Engine-D section tracks the macro/behavioral/regime/short-direction gene buckets but omits the LARGEST one: the 20% Foundry-feature bucket (`discovery.py:657-675`, `_make_random_foundry_gene`), which draws a feature_id uniformly from the live tier-A/B Foundry registry. MEMORY historically called this bucket inert (the T-177 `set_params` bug); it is now resolved by `composite_edge.py:56-71` (set_params re-hydrates `self.genes`/`self.direction`) so it is live. Two untracked config knobs: `foundry_seed_fraction: 0.5` (prod; default 0.0 at `discovery.py:89`) makes half the fresh Gen-0 GA seed single-gene foundry genomes (T-183) — a real change to which candidates get tested first; and `use_bayesian_opt: false` (reachable at `discovery.py:285-293`) — a default-OFF GP+EI candidate search that replaces the GA when flipped.
- Charter reference: `index.md` / `high_level_engine_function.md` describe the Foundry bucket and GA seeding; capability_ledger.md — the anti-build-bias index — carries no rows for them.
- Recommended next step: Add ledger rows for (1) Foundry 20% gene bucket (Wired=yes on `--discover`; resolved by composite_edge), (2) `foundry_seed_fraction` (Wired=yes, prod 0.5), (3) `use_bayesian_opt` (mode-gated, default OFF).

### [LOW] Every Engine-D capability_ledger `file:line` is stale post-merge-wave; the Layer 3a contract only checks file-exists, not symbol-at-line, so the drift passes CI silently
- Engine: D
- First flagged: 2026-06-22
- Status: not started
- Description: `discovery.py` grew to 1784 lines; the ledger's D rows point at pre-growth lines — `validate_candidate` cited :869, actually :943; macro/behavioral/regime genes cited `_create_random_gene:496`, actually :592 (within a def at :499); short/market_neutral direction cited :353-357, actually :401-406. The Layer 3a contract (`tests/test_contracts.py:750`, `test_layer3a_capability_ledger_source_files_exist`) only asserts the FILE exists — it does NOT verify the cited line resolves to the claimed symbol, despite the ledger header claiming "Line-number drift WARNs; missing file/symbol FAILs." The header oversells the contract.
- Charter reference: capability_ledger.md header "CI-gated: tests/test_contracts.py::Layer 3a verifies that every Source (file:line) here still resolves (file exists, symbol matches)."
- Recommended next step: Refresh the D row line numbers, and either strengthen Layer 3a to assert the symbol appears at/near the cited line, or correct the ledger header to state the contract only checks file existence.

### [MEDIUM 2026-06-22 by engine-auditor] capability_ledger STALE-as-dead: `macro_yield_curve_v1` is RETIRED in the live registry, not ACTIVE — the "active -0.3 crisis tilt in A" claim is refuted by edges.yml
- Engine: A
- First flagged: 2026-06-22
- Status: not started
- Description: Direct correction of the open MEDIUM above (the
  "yield-curve ACTIVE" entry) and the capability_ledger row that cites
  `macro_yield_curve_edge.py:199 status="active"` as evidence of an
  active de-gross overlay. Tracing the LIVE registry (the
  recommended-next-step the prior entry deferred): `data/governor/
  edges.yml:1755` sets `macro_yield_curve_v1` `status: retired`. The
  in-code auto-register `status="active"` (macro_yield_curve_edge.py:199)
  is WRITE-PROTECTED by `EdgeRegistry.ensure()` (per the comment at
  macro_yield_curve_edge.py:184-187, ensure() does not revert persisted
  lifecycle status), so the code default never wins over the persisted
  `retired`. Net: the edge does NOT fire in prod — it is
  DORMANT/retired, not an active crisis-de-gross path. The
  capability_ledger's "ACTIVE — uniform -0.3 tilt" / "unknown — needs
  trace" framing is STALE-as-dead. (Same dynamic on `low_vol_factor_v1`:
  code auto-registers `status="active"`, low_vol_factor_edge.py:140;
  live `edges.yml:1778` = `paused` / `retire-eligible` — and it is not
  in the ledger at all.)
- Charter reference: capability_ledger.md header — "honest
  reachability"; the Path-B-relevance column tags macro_yield_curve as
  a "pre-existing crisis-defensive overlay … T-092 Path-B kill-switch
  must account for this." A T-092 scoper trusting that row would
  double-count a retired/inert edge as a live de-gross path.
- Recommended next step: Re-tag the macro_yield_curve_v1 ledger row to
  `Wired-to-live-path? = no (retired in data/governor/edges.yml:1755)`,
  Prod-flag-state = `retired`. Same correction for low_vol_factor
  (`paused`/`retire-eligible`). When the registry's proposed
  "Fed-real-data?" column lands, both are clear "no" cases a code scan
  of the auto-register line would mis-read as active.

### [MEDIUM 2026-06-22 by engine-auditor] UNTRACKED Engine A-alpha capabilities after the merge wave — defensive_tilt screens (T-205) + Phase-1 composition (T-211) + trend overlay, none in capability_ledger or DESIGN_FIDELITY; stale "not on prod path" docstrings
- Engine: A
- First flagged: 2026-06-22
- Status: not started
- Description: The T-204/205/211 merge wave added real, behavior-altering
  Engine A capabilities that neither registry tracks — the same
  buried-capability blind spot that hid the conjunctive selector.
  (1) `engines/engine_a_alpha/screens/defensive_tilt.py` — a cross-
  sectional QUALITY tilt (`quality_tilt_longs`, line 112) + a
  high-IVOL/lottery EXCLUSION screen (`high_ivol_exclusion`, line 163),
  both PIT-correct producers. The module's `__init__.py` docstring AND
  `defensive_tilt.py:18-23` assert "NOT imported by the production
  backtest path … prod canon unchanged" — that is now FALSE:
  `engines/engine_c_portfolio/phase1_composition.py:88-96` imports and
  calls both screens. (Correct boundary placement — A produces the
  screen scores, C applies them as a CONSTRUCTION tilt, not a B
  admission gate — but the capability is real and cross-engine-wired.)
  (2) Phase-1 composition (`apply_phase1_composition`,
  phase1_composition.py:114) applies the defensive tilt + a
  trend-overlay gross scalar (`core.trend_overlay.TrendOverlay`) to the
  book's target weights, reached from
  `engines/engine_c_portfolio/portfolio_engine.py:440` gated by
  `phase1_composition_enabled` (`config/portfolio_settings.json:21`,
  default False) — DORMANT but fully wired and reachable via one flag.
  Grep for trend_overlay / defensive_tilt / phase1 / quality_tilt /
  screens returns NOTHING in either capability_ledger.md or
  DESIGN_FIDELITY.md. (`screens/industry_momentum.py` is genuinely
  inert — called only by `scripts/industry_momentum_t213.py`, no
  engine/controller import — a true orphan, lower priority.)
- Charter reference: capability_ledger.md header — "flat index of EVERY
  behavior-altering capability the code currently ships"; DESIGN_FIDELITY
  exists so a built-but-undocumented capability "can't fall through the
  net like the conjunctive selector did." The defensive screens are the
  alpha-layer half of the Phase-1 crisis-defense lever (the bought-MF-
  sleeve alternative) and belong in both registries.
- Recommended next step: Add capability_ledger rows: (a) Engine A
  "defensive_tilt screens (quality tilt + high-IVOL exclusion)" Source
  `engines/engine_a_alpha/screens/defensive_tilt.py:112,163`,
  Wired-to-live-path? = `mode-gated` (consumed by C's phase1 only when
  `phase1_composition_enabled`), Prod-flag-state = default-OFF; (b)
  Engine C "phase1_composition post-processor (defensive tilt + trend
  overlay scalar)" Source `engines/engine_c_portfolio/phase1_composition.py:114`
  / `portfolio_engine.py:440`, default-OFF. Correct the two "NOT
  imported by production path" docstrings (`screens/__init__.py`,
  `defensive_tilt.py:18-23`) to "consumed by C's phase1 composition,
  default-OFF" — they now under-state the wiring (a sibling of the
  ledger-header-overstates / docstring-understates drift class).

### [MEDIUM] Engine C ships FOUR wired-but-untracked post-processor capabilities (phase1_composition, dynamic_optimizer, position_buffering, SpotETFTrendSleeve) — none in capability_ledger.md or DESIGN_FIDELITY.md
- Engine: C
- First flagged: 2026-06-22
- Status: not started
- Description: The capability_ledger Engine C section (rows 44-51) was written 2026-06-04 and never updated through the T-139/T-148/T-120/T-211 merge wave. Four real, behavior-altering, default-OFF-but-WIRED capabilities now exist with ZERO ledger/DESIGN_FIDELITY coverage: (1) Phase-1 composition (T-211) — `engines/engine_c_portfolio/phase1_composition.py:114` (`apply_phase1_composition`), wired at `portfolio_engine.py:440-441` behind `phase1_composition_enabled` (policy.py:91, default False); applies the A/T-205 defensive quality/IVOL tilt + the E/T-204 trend-overlay exposure scalar to the final book. (2) Carver dynamic optimization (T-139) — `dynamic_optimizer.py:optimize_integer_positions`, wired at `portfolio_engine.py:424-425` behind `dynamic_optimization_enabled` (default False). (3) Carver position buffering (T-148) — `position_buffering.py:apply_position_buffering`, wired at `portfolio_engine.py:433-434` behind `position_buffering_enabled` (default False). (4) SpotETFTrendSleeve (T-120) — `sleeves/spot_etf_trend_sleeve.py`, wired into PortfolioEngine init (`portfolio_engine.py:79-85`) AND snapshot equity (`portfolio_engine.py:322-331`) behind `spot_sleeve_enabled` (policy.py:44, default False). All four are default-OFF (canon bitwise-identical when off), so none is a production risk today — but the ledger's stated purpose is to be the flat index of EVERY shipped behavior-altering capability "behind which flag, with honest reachability," precisely so a default-OFF knob does not become nobody's documentation responsibility. These are exactly the buried-capability class the ledger exists to catch.
- Charter reference: `capability_ledger.md:3` ("flat index of every BEHAVIOR-ALTERING capability the code currently ships, on which path, behind which flag, with honest reachability"). The four above ship, are on the live path (gated), behind named flags — and are absent.
- Recommended next step: Add four Engine C rows (Wired-to-live-path? = mode-gated, reachable when each `*_enabled` flag flips; Prod-flag-state = default OFF). Cross-link verdict docs: T-211->T-215 (composition verdict pending the cloud cell), T-148 (buffering A/B pre-registered), T-128r (SpotETF sleeve crisis-MDD thesis REFUTED — see finding below), T-139 (dyn-opt A/B gated).

### [MEDIUM] Engine C `PortfolioComposer` (HRP + turnover gate) is reachable in prod but UNTRACKED in capability_ledger.md; it is C-owned code dispatched from inside Engine A (design-of-record, not drift)
- Engine: C
- First flagged: 2026-06-22
- Status: not started
- Description: `engines/engine_c_portfolio/composer.py` (`PortfolioComposer.compose`, line 102) is the F4-charter-inversion home for HRP + turnover gating. It is constructed at `engines/engine_a_alpha/alpha_engine.py:571` and called at `alpha_engine.py:799-800` (`if proc and self.composer.is_active: proc = self.composer.compose(...)`). Fully reachable on the live backtest path but a strict no-op under the prod config (`config/portfolio_settings.json` `portfolio_optimizer.method = "weighted_sum"` -> `is_active` False, composer.py:99-100). Gaps: (a) it is NOT in the capability_ledger Engine C section despite being behavior-altering behind the `method` flag (`hrp`/`hrp_composed` activate it); (b) it is C-owned but A-dispatched. (b) is the documented intentional F4-inversion fix (composer.py:8-12 records HRP/turnover moved OUT of Engine A's signal_processor INTO Engine C's composer.py) — the heavy logic lives in the right engine; only the dispatch is cross-engine. Flagging for ledger coverage, NOT as a boundary violation.
- Charter reference: `engine_charters.md:280-293` (Engine C.2 owns "Diversification and correlation-aware weighting"); `capability_ledger.md:3`.
- Recommended next step: Add an Engine C ledger row (Source `composer.py:102`; Wired-to-live-path? = mode-gated, active only when `method` in {hrp, hrp_composed}, prod weighted_sum no-op; Notes: HRP-replacement slice-1 FALSIFIED -0.63, hrp_composed retained).

### [MEDIUM] capability_ledger.md Engine C section is STALE post-merge: all 5 file:line refs drifted, the allocator.py "missing-file" claim no longer matches docs, and vol-target/exposure-cap reachability is overstated
- Engine: C
- First flagged: 2026-06-22
- Status: not started
- Description: Three accuracy defects in the existing Engine C ledger rows (44-51). (1) Line drift (Layer 3a WARN class): every Engine C `policy.py` reference is wrong — vol-target ceiling ledger says :334, actual :440; vol-target floor :340->:445; `_apply_exposure_cap` :380->:463; `_apply_regime_overrides` :86->:115; `allocation_recommendation` consumer :62->:129. Symbols still exist (not phantom) but no ref resolves. (2) The `EngineCAllocator`/`allocator.py` row (50) claims "Charter + index.md refer to `allocator.py` but no such file" — STALE: a grep of both `docs/Core/engine_charters.md` and `engines/engine_c_portfolio/index.md` finds NO `allocator.py`/`EngineCAllocator` reference anymore (only a role-table "Allocator" label and a "portfolio policy allocator" description). The dangling reference the row describes was removed; retire the row. (3) Vol-target/exposure-cap reachability OVERSTATED: rows 44-46 say these are reachable because `_apply_regime_overrides` flips mode to "adaptive" via `data/research/allocation_recommendations.json` "(which recommends adaptive for every regime)". That file is ABSENT on disk -> `_apply_regime_overrides` early-returns (policy.py:146-147) -> mode stays mean_variance -> the regime-aware vol-target ceiling/floor and exposure-cap (at the END of the adaptive branch, after the mean_variance branch already returns at policy.py:292) are NOT reached in prod. CURRENT_STATE confirms "mean_variance is production; the adaptive artifact was archived (T-167)." The file is gitignored/regenerable so it COULD exist live, but the ledger states it as present-fact.
- Charter reference: `capability_ledger.md:11` ("False precision is the bug this ledger exists to prevent"); `:13` (Layer 3a: line drift WARNs, missing symbol FAILs).
- Recommended next step: Refresh all five Engine C line numbers, retire the `allocator.py`-missing-file row, and change the vol-target/exposure-cap reachability to "no (mean_variance prod; adaptive-only, recommendations file absent)" rather than mode-gated.

### [LOW] SpotETFTrendSleeve is captured in DESIGN_FIDELITY only as part of the blanket "sleeve ... REFUTED" row but ships WIRED — the registry conflates "refuted thesis" with "removed capability"
- Engine: C
- First flagged: 2026-06-22
- Status: not started
- Description: `DESIGN_FIDELITY.md:27` marks "Regime vol-target / de-gross overlay / capital-partition sleeve" REFUTED (T-055h/T-118r/T-128r), and :65 says "Do NOT resurrect: ... sleeve (REFUTED)." T-128r (TASK_LEDGER row 116) did refute the spot-sleeve crisis-MDD thesis on the integrated path ("NOT RECOMMEND ... NOT a drawdown hedge"). HOWEVER `SpotETFTrendSleeve` remains BUILT + WIRED into PortfolioEngine (init + snapshot, behind `spot_sleeve_enabled` default OFF) — it was not removed/archived after refutation. That is correct (archive-never-delete; the knob stays default-OFF on the path), but it means a refuted default-OFF capability is again nobody's documentation responsibility: DESIGN_FIDELITY says "REFUTED, do not resurrect" while capability_ledger has no row saying "still wired, default-OFF, on the path." The nuance T-128r itself logged (spot @25% lifts base Sharpe 0.751->0.897 via calm-period return diversification, statistically soft, NOT a crisis hedge) makes it a refuted-as-hedge / marginal-as-diversifier capability still shipping — the refuted-verdict-buries-shipped-capability pattern.
- Charter reference: `DESIGN_FIDELITY.md:51-52` ("On REFUTATION, flip the row to REFUTED so the registry distinguishes wrongly-never-tried from correctly-abandoned"); `capability_ledger.md:5`.
- Recommended next step: Add a capability_ledger Engine C row for `SpotETFTrendSleeve` with Defensive/Path-B relevance = REFUTED-as-hedge (T-128r) and Wired-to-live-path? = mode-gated / still on the path default-OFF, cross-linking T-128r.
