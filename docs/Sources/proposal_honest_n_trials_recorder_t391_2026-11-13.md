# Proposal: the honest-N count includes standalone-harness trials (T-391)

**For:** the director, then **the USER**. This changes the referee: what Gate 0 (MBL), Gate 8 (DSR) and every
verdict's honest-N line compute N from. The referee is never modified autonomously. **Status:** PROPOSAL, built on
branch `referee/honest-n-trials-recorder-t391`, NOT merged, NOT pushed. **N_trials: 0** (a correction to the
referee, not a hypothesis).

**The defect:** `docs/State/health_check.md` MEDIUM (main `573fc62`), "The honest-N gate's registry never sees a
standalone-harness trial". `core/measurement/mbl_gate.py` `compute_n_effective_correlated` reads
`data/observability/run_registry.sqlite`, which ingests only `data/trade_logs/<uuid>/performance_summary.json`
(`core/observability/run_registry.py`). The frontier program requires standalone harnesses, so their trials never
enter the count, and the count lives in prose.

---

## §1. Design — PRE-DECLARED (committed alone, before any code)

### 1.1 What the 231 and the 267 actually contain (read-only, 2026-11-12)

Read from a scratch COPY of the registry (sha256 `b3df6a15…` = the pinned value), never the live file:

| population | rows | what it is |
|---|---|---|
| registry run rows | 125 | `source` NULL; 116 with no `snapshot_at`, 9 dated 2026-05-07/08. Evidence for none survives (RR-3B §0). All May-era controller runs. |
| registry ledger rows | 106 | `source = ledger:<task>`, written 2026-08-06 by `scripts/backfill_run_registry_t336.py` from the `N_trials += k` / `N += k` lines in `TASK_LEDGER.md`: **26 tasks** (listed in §1.2 A). |
| **the gate's N_raw** | **231** | the two above. N_eff 36.92 (conservative; ρ̄ ci_low 0.4325, ONC 0.1598, pinned 2026-10-13). |

**The 267 is not a raw count.** It is ruling 9.2's N_eff on the RR-3B Option-B data pass
(`docs/Sources/referee_repair_proposal_RR-3B_2026-10-13.md:52, :258`): **36.5** (258 curve-bearing controller-harness
trials, correlation-compressed) **+ 231** (the registry's curve-less rows at raw, no borrowed credit) = **267.5**. So the
267 covers standalone trials **only through the 106 ledger rows**. A standalone trial whose task is not one of those 26
is in neither the 231 nor the 267.

This settles the question every B-series prereg left open ("≈ 288/290 if the July T-306 series is outside the 267",
`docs/Sources/prereg_b10_gold_leg_2026-11-11.md:281-283`): **T-260, T-311, T-312, T-314, T-315, T-318, T-320 and T-333
are INSIDE** (registry rows `ledger:T-260:0` … `ledger:T-333:0`). The series' own counter ("→78",
`docs/Audit/adaptation_rule_t314_2026_07_27.md:96`; "76 → 81") is a separate family tally, not the honest N.

**And it finds a gap the hand count never saw:** 29 standalone entries from 2026-06-18 to 2026-08-28, 37 trials,
whose N is stated in their own verdict or result docs but never reached the registry. Some lack a ledger row
(T-221…T-254 and T-273…T-288 are absent from the ledger). Others have one that states no N (the 2026-07-02 batch).
Others were added after the 08-06 backfill ran (T-337: the ledger says "registry: 232", and the registry holds 231).
**So the hand count "≥ 283" is itself short by at least 37.**

### 1.2 Inventory (every standalone-harness trial on record)

Sources searched: every `docs/Audit/*.md`, `docs/Sources/*.md` and `docs/Measurements/*/*.md` line matching an N
statement (`N_trials += k`, `N += k`, `N_trials +k`, `n_trials_consumed`, `N_trials consumed`, zero forms), and every
`TASK_LEDGER.md` row. Line numbers are as of `6c24913`. "Ledger" is the `TASK_LEDGER.md` line. Substrate: the record says
`unclassified` for every backfilled row. Only the RR-3B §2D audit-cited table can tag substrate, and tagging from memory
is what §2D forbids. An unclassified trial counts in every family it could belong to, so all of them count in the single pool.

**A — covered by the 231 AND the 267 (registry ledger rows; 26 tasks, 106 trials).** Each row's count equals the
registry's `ledger:<task>` count. The record carries them as `counted_in = registry_ledger` and **never sums them
again**:

| task | date | n | ledger | verdict / doc |
|---|---|---|---|---|
| T-135 | 2026-06-10 | 1 | :80 | overnight_intraday_edge_t135_2026_06_10.md |
| T-137 | 2026-06-10 | 24 | :82 | 8k_event_edge_t137_2026_06_10.md |
| T-144 | 2026-06-10 | 8 | :87 | form4_insider_gauntlet_t144_2026_06_10.md |
| T-145 | 2026-06-11 | 4 | :91 | 13f_crowding_t145_2026_06_10.md |
| T-149 | 2026-06-11 | 3 | :92 | metalearner_falsification_t149_2026_06_11.md |
| T-170 | 2026-06-15 | 1 | :118 | bought_mf_sleeve_t170_2026_06_15.md |
| T-171 | 2026-06-15 | 1 | :119 | mf_sleeve_deep_crisis_t171_2026_06_15.md |
| T-174 | 2026-06-16 | 1 | :122 | vrp_edge_t174_2026_06_16.md |
| T-196 | 2026-06-18 | 35 | :143 | foundry_alpha_test_prereg_t196_2026_06_17.md (Discovery candidates, curve-less) |
| T-204 | 2026-06-18 | 9 | :150 | trend_overlay_validation_t204_2026_06_18.md |
| T-289 | 2026-07-08 | 4 | :193 | news_frozen_tests_t289c_2026_07_07.md |
| T-291 | 2026-07-07 | 1 | :194 | event_interaction_verdict_t291_2026_07_07.md |
| T-294 | 2026-07-08 | 1 | :198 | vehicle_bakeoff_t294_2026_07_08.md |
| T-297 | 2026-07-08 | 1 | :199 | turnover_reduction_t297_2026_07_08.md |
| T-294b | 2026-07-08 | 1 | :200 | taxable_futures_vehicle_t294b_2026_07_08.md |
| T-298 | 2026-07-08 | 1 | :201 | asymmetric_damping_t298_2026_07_08.md |
| T-311 | 2026-07-27 | 1 | :202 | deep_reverify_sleeve_t311_2026_07_27.md |
| T-312 | 2026-07-27 | 1 | :205 | deep_reverify_offense_t312_2026_07_27.md |
| T-315 | 2026-07-27 | 1 | :206 | static_leverage_t315_2026_07_27.md |
| T-299 | 2026-07-09 | 1 | :209 | docs/Sources/prereg_contribution_rule_t299.md |
| T-296 | 2026-07-08 | 1 | :221 | return_stack_arm_verdict_t296_2026_07_08.md |
| T-318 | 2026-07-27 | 1 | :222 | tilt_decision_verdicts_t318_t320_2026_07_27.md |
| T-320 | 2026-07-27 | 1 | :223 | tilt_decision_verdicts_t318_t320_2026_07_27.md |
| T-260 (07-27) | 2026-07-27 | 1 | :224 | deep_reverify_speeds_t260_2026_07_27.md |
| T-314 | 2026-07-27 | 1 | :225 | adaptation_rule_t314_2026_07_27.md |
| T-333 | 2026-07-29 | 1 | :236 | excess_of_cash_attribution_t333_2026_07_28.md |

**B — after the 267 (2026-10-13 onward): 8 tasks, 16 trials.** This is the hand count's increment (267 + 16 = 283):

| task | date | n | ledger | source line (the count) |
|---|---|---|---|---|
| T-365 (B-1) | 2026-10-14 | **6** | :266 | b1_raw_signal_decile_verdict_2026-10-14.md:17 ("+4 at the run; +2 … 6 in all"). **The ledger row says 4: stale.** |
| T-379 | 2026-11-10 | 2 | :280 | cef_wide_lagged_verdict_t379_2026-11-10.md:3 |
| T-380 (B-9) | 2026-11-11 | 2 | :281 | b9_combo_tilts_verdict_2026-11-11.md:257, :281 |
| T-381 (B-2) | 2026-11-11 | 2 | :282 | b2_smallcap_t265_verdict_2026-11-11.md:12, :319 |
| T-382 (B-5) | 2026-11-11 | 1 | :283 | b5_levered_diversified_verdict_2026-11-11.md:7 |
| T-383 (B-6) | 2026-11-12 | 1 | :284 | b6_lazy_prices_verdict_2026-11-12.md:7 (S&P arm; the T-265 arm's +1 lands at its own run) |
| T-385 (B-10) | 2026-11-11 | 2 | :286 | b10_gold_leg_verdict_2026-11-11.md:308 |
| T-386 (B-8) | 2026-11-11 | 0 | :287 | prereg_b8_execution_timing_2026-11-11.md:596 (closed without running) |

**C — before the 267, in NEITHER the 231 nor the 267 (newly found): 29 entries, 37 trials.** Every count is the doc's
own stated N. Every run is evidenced by a verdict or result section, or by a ledger `refuted`/`done` row:

| task | date | n | ledger | source line | flag |
|---|---|---|---|---|---|
| T-213 | 2026-06-18 | 1 | :160 | industry_momentum_t213_2026_06_18.md:47 | |
| T-214 | 2026-06-18 | 6 | :161 | trend_wider_breadth_validation_t214_2026_06_18.md:5 | the ledger row still reads `dispatched` |
| T-216 | 2026-06-18 | 1 | :163 | conditional_selector_build_t216_2026_06_18.md:67 | its §3 re-measure is U3 |
| T-220 | 2026-06-19 | 2 | :167 | regime_conditional_overlay_t220_2026_06_19.md:58 | the ledger row still reads `dispatched` |
| T-241 | 2026-06-26 | 1 | — | moonshot_c1_verdict_t241_2026_06_26.md:41 | |
| T-248 | 2026-06-26 | 1 | — | strategy_riskparity_verdict_t248_2026_06_26.md:36 | |
| T-251 | 2026-06-26 | 1 | — | barbell_prereg_t251_2026_06_26.md:29 (verdict barbell_verdict_t251_2026_06_26.md) | count from the prereg; the verdict states none |
| T-253 | 2026-06-27 | 1 | — | mf_etf_satellite_t253_2026_06_27.md:73-75 ("counts as 1 structural comparison") | |
| T-259 | 2026-07-02 | 1 | :179 | offleg_ab_preregistration_t258_2026_07_02.md:88 | off-leg family trial 1 of 2 (offleg_rescue_preregistration_t266_2026_07_02.md:9) |
| T-260 (07-02) | 2026-07-02 | 1 | :180 | multispeed_robustness_t260_2026_07_02.md:6 | a different trial from the 07-27 T-260 in A |
| T-262 | 2026-07-02 | 1 | :182 | compose_voltarget_verdict_t262_2026_07_02.md:7 | |
| T-265 | 2026-07-02 | 1 | :185 | smallcap_pead_pilot_t265_2026_07_02.md:171 | |
| T-266 | 2026-07-02 | 1 | :186 | offleg_rescue_preregistration_t266_2026_07_02.md:12 | count from the prereg; the ledger reads `refuted` |
| T-267 | 2026-07-02 | 1 | :187 | cef_lowerbound_probe_verdict_t267_2026_07_02.md:3 | |
| T-268 | 2026-07-02 | 1 | :188 | evenweek_sleeve_t268_2026_07_02.md:95 | |
| T-269 | 2026-07-02 | 1 | :189 | asymmetric_exits_verdict_t269_2026_07_02.md:7 | |
| T-270 | 2026-07-02 | 1 | :190 | intraday_probe_preregistration_t270_2026_07_02.md:9 | count from the prereg; the ledger reads `refuted` |
| T-271 | 2026-07-02 | 1 | :191 | index_deletion_t271_2026_07_02.md:119 | |
| T-272 | 2026-07-02 | 1 | :192 | btc_arm_verdict_t272_2026_07_02.md:40 | |
| T-273 | 2026-07-02 | 1 | — | breadth_tilt_t273_2026_07_02.md:106 | |
| T-274 | 2026-07-02 | 1 | — | vixterm_tilt_verdict_t274_2026_07_02.md:7 | |
| T-279 | 2026-07-02 | 1 | — | premium_tier_verdict_t279_2026_07_02.md:3 | |
| T-282 | 2026-07-06 | 1 | — | trend_gated_leverage_t282_2026_07_06.md:62 | |
| T-284 | 2026-07-06 | 2 | — | fullequity_gated_leverage_t284_2026_07_06.md:59 | |
| T-337 | 2026-08-06 | 1 | :241 | dividend_strip_audit_verdict_t337_2026_08_06.md:65 | the ledger says "registry: 232"; the registry holds 231 |
| T-339 | 2026-08-20 | 1 | :244 | anonymized_historical_eval_VERDICT_t339_2026_08_20.md:72 | ledger id `T-339/b` |
| T-339b | 2026-08-28 | 1 | :244 | anonymized_historical_eval_VERDICT_t339b_2026_08_28.md:24 | ledger id `T-339/b` |
| T-340-6 | 2026-08-26 | 2 | :245 | ledger "N+=2 frozen pending run" = volterm_conditioner_prereg_t342_2026_08_15.md:178 | **stated, maybe unrun**: counted as stated, the T-336 parse precedent (raises N); if T-342 ever runs, it must NOT add again |
| T-341 | 2026-08-15 | 1 | — | exec_timing_verdict_t341_2026_08_15.md:39 | |

**Totals:** A 106 (in the 231 and the 267) · B 16 (after the 267) · C 37 (in neither) · **standalone outside the
registry: S = B + C = 53.**

**D — ambiguous: listed in the record's `unresolved` block, NOT counted, each awaiting a ruling (never a guessed
count):**

| id | item | why it is not counted |
|---|---|---|
| U1 | T-193, phase0b_local_discover_t193_2026_06_17.md:95, "consumed 35 trials … VOID (degenerate baseline)" | It may be the same 35 foundry candidates T-196 re-ran a day later on a fixed baseline: 35 or 0. |
| U2 | T-217, regime_gate_t217_2026_06_18.md:77, "N_trials += 1" | This reserves the +1 for an "OOS robo measurement [that] is the director's composition step". No record shows that it ran. |
| U3 | T-216 §3, the 3-way re-measure after the `g_regime` fix (conditional_selector_build_t216_2026_06_18.md:6) | A second trial or a correction of the first: 1 or 0. |
| U4 | T-250, calendar_flow_probe_t250_2026_06_26.md (results present) | No N stated. :36 argues "effective-N ≈ 2-3". |
| U5 | T-254, factor_momentum_t254_2026_06_26.md (results present) | No N stated. |
| U6 | T-263, multi-asset carry (ledger :183 `refuted`) | A branch only, with no doc on main. |
| U7 | T-148, position_buffering_t148_2026_06_11.md:101, "N_trials consumed: 2 primary" | Contradicts its own :5 and ledger :173 ("zero N_trials"). |
| U8 | T-157, lps_reprice_auction_t157_2026_06_11.md:114, :123 | N+=0 per policy; the stricter +1 was "flagged for the merge decision", and no ruling is found. |
| U9 | T-178, regime_sleeve_sizer_preregistration_t178_2026_06_16.md:85, "1 primary A/B" | The result doc states no N, and it may be a controller run (Option B's population). |
| U10 | T-349, buyhold_spread_prereg_t349_2026_08_31.md:147, "N += 1" | A draft. No record shows Arm U ran. |
| U11 | the pre-2026-06-10 era | No per-task N is on record. The hand counter read "~80 N_trials accumulated" (confidence_gated_execution_2026_05_12.md:119). Those were mostly controller runs: the 125 lost rows or the executed universe. |
| U12 | parallel hand counters | "cumulative ~295" (ledger :143, T-196) and "~295 equity-book trials" (calendar_flow_probe_t250_2026_06_26.md:36). Neither reconciles to the 231/267 lineage. Not used. |

**Out of T-391's scope:** controller-harness trials (T-215/T-211 `t215-beat-robo`, T-128r, T-212, T-153, T-055g/h …).
They write run directories and are in RR-3B's executed universe, Option B's population (258 distinct on 10-13). They
are not in the gate's 231 either. That is RR-3B's open build, not this one.

### 1.3 The record: a committed JSON, not a registry table

`config/honest_n_trials.json`, schema `honest_n_trials/v1`. Rows: `trial_id, task_id, date, n_trials, counted_in
(registry_ledger | standalone), ledger_id, family, substrate, prereg, verdict, source, note`, plus an `unresolved`
block. A `rows_sha256` digest covers both blocks.

**Why not a `trials` table in the registry:**
1. **The registry is pinned by sha256** (`config/honest_n_pin.json`). Every recorder write would change its bytes and
   break the pin, so each verdict merge would need a registry re-pin.
2. **The registry is gitignored data.** `data/observability` is a symlink into the main tree from every worktree, with
   one copy and no diff to review (T-356b). A row written there cannot be reviewed, reproduced by commit, or recovered.
3. **The brief forbids writing it in place.**

**Why a committed JSON:**
1. **Every recorder write is a reviewed commit.** The verdict merge's own commit carries the row. `git show <hash>:config/honest_n_trials.json` reproduces the gate's input at any commit.
2. **It is in the image already:** `Dockerfile.backtest:118` COPYs `config/`.
3. **JSON over CSV:** JSON carries the schema, the activation date and the digest in one file. Rows are written one per line, so a row diff stays one line.

**The digest:** `rows_sha256` (sha256 of the canonical JSON of `rows` + `unresolved`) is written by the recorder and
checked by the gate. A hand edit that bypasses the recorder fails closed.

**ONE writer:** `scripts/honest_n_trials.py record …`. The director runs it at each verdict merge. It appends
`counted_in = standalone` rows only. It never writes a `registry_ledger` row (those are frozen with the backfill). It
refuses a duplicate `trial_id`, a path that does not exist, and a `source` line beyond the end of its file. The
referee module (`mbl_gate.py`) only reads and verifies, the same split as `honest_n_pin.py` (R's note on 9.3).

**Pinning at re-pin #2 (cutover day):**
- `honest_n_pin --pin <artifact> --replace` additionally records `"trials": {file, sha256, standalone_at_pin}`.
- `load_pin` accepts that optional third entry. When the pin names it, the gate verifies the record's sha256 the way it verifies the registry's.
- `honest_n_pin --verify` already runs at image build (`Dockerfile.backtest:168`). It now also loads the record and checks its digest and the registry cross-check (§1.5), and, once pinned, its sha256. A bad record fails the build (exit 3).
- **Until re-pin #2,** the record's integrity is git (it is committed) plus its own digest. The gate counts it from the merge (§1.6).
- **After re-pin #2,** each recorder run is followed by `honest_n_pin --pin … --replace` in the same commit. That is the existing explicit act, and the gate refuses on a mismatch until then.
- The record is NOT added to `gen_substrate_manifest.HONEST_N_FILES`. It is versioned source, pinned by the commit that builds the image, not a `data/` file synced by prefix.

### 1.4 How the gate combines the two sources: candidate rules and the choice

Standalone trials have no return stream in any population the gate measures, so their correlation with the rest
cannot be measured. All numbers below are read-only through the merged gate's own functions on the pinned inputs:
registry md5 `83e47441…`, before = after. MinBTL uses the exact form. SR_req is the Sharpe a window must clear.

S = 53 (the full backfill, B + C):

| rule | N_eff | MinBTL @ SR 1 | SR_req 12 y | SR_req 26 y | SR_req 55 y |
|---|---|---|---|---|---|
| R0 today (registry only) | 36.92 | 4.66 y | 0.623 | 0.423 | 0.291 |
| R1 pooled: N_raw = 231 + S, the measured ρ̄/ONC applied to all | 45.40 | 5.01 y | 0.646 | 0.439 | 0.302 |
| **R2 additive: N_eff(registry) + S at raw** | **89.92** | **6.22 y** | **0.720** | **0.489** | **0.336** |
| R3 ruling 9.2 for every curve-less trial: N_eff(executed 252, pinned 09-30 artifact) 40.28 + 231 + S | 324.28 | 8.53 y | 0.843 | 0.573 | 0.394 |

S = 16 (the hand count's increment only, B): R1 39.48 · R2 52.92 · R3 287.28 (8.31 y; 26 y needs 0.565).

**The choice: R2 is what the gate returns; R3 is reported beside it in every breakdown.**

- **R1 is rejected.** It credits trials with a correlation measured on a population that excludes them. That is
  exactly what ruling 9.2 forbids ("NO BORROWED CREDIT", RR-3B §9.2). It is also the lowest N of the three.
- **R2 is the strictest rule that changes only what T-391 owns.** The standalone source enters at raw. Additive
  combination is what independent groups give; any between- or within-group correlation can only lower the true N_eff,
  so R2 is an upper bound on the true N_eff, the conservative side (the 9.2 argument, applied to this source).
- **R3 also strips the credit the merged gate (Option A) gives the registry's own 231 curve-less rows.** That is 9.2's
  unbuilt half. It is computable from pinned inputs today (the 09-30 artifact's `funnel.after_dedupe = 252` population
  is disjoint from the registry, RR-3B §0), and it is the honest number under the director's own ruling. Making it the
  gated value moves Gate 0 from 37 to 324 by a change to trials T-391 does not own. 9.2 was sequenced with the Option B
  build (whose §2D table may also remove T-306-substrate ledger rows). **So it is the user's decision, not this
  branch's.** It is a one-key change (§1.6), and the breakdown carries the R3 number on every read until then. No
  verdict can quote R2 without R3 beside it.

### 1.5 Fail closed

**The gate (production path, no explicit `artifact_path`):**
- It refuses (`HonestNUnavailableError`) when the record is absent, unreadable, the wrong schema, empty, its digest
  mismatches, or any row is malformed. Malformed means: `n_trials` not an int ≥ 0, `counted_in` unknown, a duplicate
  `trial_id`, or a missing citation field.
- It also refuses when the record's `registry_ledger` rows disagree with the registry's `ledger:<id>` rows, per id and
  count, in either direction. That is the structural lock against double counting (a standalone row that is really a
  registry row) and against silent omission.
- Once the pin names the record, it refuses on a sha256 mismatch.
- An explicit `artifact_path` (tools, tests) bypasses the pins and counts the record only when `trials_path` is also
  passed: the existing convention for explicit caller choices.

**The lint (`python -m scripts.honest_n_trials check`; pytest-locked on the real ledger + record):**
- **Every `TASK_LEDGER.md` row that declares N > 0** (`N_trials += k`, `N += k`, `N_trials +k`, `n_trials_consumed k`,
  `N_trials consumed: k`) must have record rows with that `ledger_id` summing **≥** the declared k. The record may
  exceed the ledger (T-365: 6 vs a stale 4), but never fall short. This applies to all history, and the backfill
  satisfies it.
- **Forward-only from the activation date 2026-11-13:** a ledger row with status `done`/`refuted`/`superseded` whose
  doc column names a verdict or a prereg must state N explicitly (`N_trials 0` counts) and have ≥ 1 record row (an
  `n_trials: 0` row counts).
- **Grandfathered:** rows before 2026-11-13 that state no N (the 2026-07-02 batch). The backfill covers them from their
  own docs (§1.2 C).
- A record row whose `ledger_id` names no ledger row fails (dangling).

### 1.6 What the merge changes, and what it does not

- `compute_n_effective_correlated()`: **36.92 → 89.92** on the merge, the record counted from the merge. Its signature
  and float return are unchanged.
- **New:** `honest_n_breakdown()`, a dict with the registry part, S, R2 (gated) and R3 (reported), the pin state and the
  unresolved count.
- **Unchanged:** the `method` options (conservative / onc / equicorr apply to the registry part only), the N_EFF_FLOOR
  of 2, and the source labels (`registry_correlated`, kept for the Discovery records that store them; the breakdown
  carries the split).
- The alternative, counting from re-pin #2 instead of from the merge, is listed for the user (§3). This branch counts
  from the merge, because a known-short count is exactly what `[NN-FAIL-CLOSED]` forbids.

### 1.7 Pre-declared acceptance tests (each proven by reversion)

1. The real record + the real registry (a COPY) gate to 36.92 + 53 = 89.92, and the breakdown's R3 = 324.28.
2. An absent, empty, wrong-schema or digest-mismatched record raises.
3. A malformed row raises: a negative or bool `n_trials`, an unknown `counted_in`, a duplicate `trial_id`.
4. A `registry_ledger` row count ≠ the registry's (either direction), or a registry ledger id missing from the record, raises.
5. Once the pin names the record, a changed record raises until re-pinned. `honest_n_pin --verify` exits 3 on a planted byte in the record.
6. The recorder appends one row, refuses a duplicate id, a non-existent path, and a source line past EOF. It recomputes the digest, so the gate accepts its output.
7. The lint fails: a ledger row declaring N > 0 with no record row; a record sum below the declared k; a forward verdict row stating no N; a dangling `ledger_id`. It passes on the real ledger + record.
8. Existing honest-N locks stay green with fixtures that supply a record (S = 0 via one `n_trials: 0` row), and their expected values are unchanged.
