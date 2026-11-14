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

---

## §2. Built: results (branch `referee/honest-n-trials-recorder-t391`)

**Commits:**
- `edc103a`: §1 alone, before code.
- `080aff1`: the gate, the recorder and lint, the pin's v2 support, the backfill record, and the existing fixtures.
- `2bbff22`: the 42 T-391 locks.

**Files:**
- `core/measurement/mbl_gate.py`: `load_trials_record`, `reconcile_trials_with_registry`, `honest_n_breakdown`, and the combined `compute_n_effective_correlated`.
- `scripts/honest_n_trials.py`: `record` (the ONE writer), `check` (the lint), `show`.
- `scripts/honest_n_pin.py`: `--verify` loads and reconciles the record; `--pin` writes v2.
- `config/honest_n_trials.json`: 63 rows (26 `registry_ledger`, 106 trials; 37 `standalone`, 53 trials) and 12 unresolved, digest `3bedde97…`. Every citation was checked to exist (path, and line ≤ EOF) by the recorder's own checks when the backfill was built.
- `tests/_honest_n_trials_fixture.py`
- `tests/test_honest_n_trials_t391.py`

**One deviation from §1, stated:** §1.6 says the signature of `compute_n_effective_correlated` is unchanged. As
built, it gains one optional keyword, `trials_path` (default `None`, which means the record beside the pin). This is
backward-compatible: every existing call is unchanged, and the float return is unchanged. `resolve_cycle_n_trials`
gains the same optional keyword, plus a `breakdown` key in its returned dict.

### 2.1 Before and after, on the real inputs, read-only

The registry is opened `mode=ro`. Its md5 is `83e474412a37075db16d419ad3dea414` before and after (`md5 -q`). The
pin verifies.

| | before (main) | after (this branch) |
|---|---|---|
| N_raw | 231 (registry) | 231 registry + 53 standalone = **284** |
| N_eff, gated | **36.92** | **89.92** (R2) |
| N_eff, reported | — | R3 **324.28** (40.28 executed-252 + 231 + 53) |
| MinBTL @ SR 1 (exact) | 4.66 y | 6.22 y (R3 8.53 y) |
| SR required: 5 y / 12 y / 26 y | 0.965 / 0.623 / 0.423 | 1.115 / 0.720 / 0.489 (R3 1.306 / 0.843 / 0.573) |
| `honest_n_pin --verify` | PIN OK (2 files) | PIN OK (2 files), and the trials record's "digest OK, NOT YET PINNED by sha256 (re-pin #2 adds it), reconciled with the registry, standalone S = 53" |
| `honest_n_trials check` | — | TRIALS CHECK OK: 63 rows, S = 53, 12 unresolved, 0 findings. The registry cross-check is OK on its 106 ledger rows. |

The lint's ledger parse, checked by hand, totals 125 declared trials:
- the 26 T-336 tasks (106);
- T-337 1, T-339/b 2, T-340-6 2, T-365 4, T-379 2, T-380 2, T-381 2, T-382 1, T-383 1, T-385 2 (19).

**So 19 trials the ledger itself declared after the 08-06 backfill never reached the registry.** The other 34 of S
(53 = 19 + T-365's +2 + 32) are stated only in their verdict and result docs.

### 2.2 Tests and the reversion proof

- **`tests/test_honest_n_trials_t391.py`:** 42 pass. This covers §1.7 (1)–(7), the production no-argument call, `check_mbl_gate`, `resolve_cycle_n_trials`, every `method`, and the explicit-artifact bypass.
- **The existing honest-N locks** (`test_honest_n_pin`, `test_honest_n_rr3`, `test_referee_repairs_proposed`, `test_repin1_code_2026_11_05`, `test_mbl_gate`, `test_oos_lock_activation_t336`): 102 pass and 8 xfail. Their expected values are unchanged (the fixture's S = 0), per §1.7 (8).
- **The reversion harness** mutates one exact string in the code (asserting it occurs exactly once), runs only the locking tests, restores the bytes, and asserts the md5 matches. **All 20 modes CAUGHT**, each with its first `E` line:

| mode | first failing line |
|---|---|
| M1 the digest check off | DID NOT RAISE (hand edit) |
| M2 empty record accepted | DID NOT RAISE |
| M3 n_trials type/sign check loosened | DID NOT RAISE |
| M4 duplicate trial_id accepted | DID NOT RAISE |
| M5 registry reconcile off | DID NOT RAISE (both directions) |
| M6 S not added to the gated N | `assert 36.92397058823529 == 89.924 ± 0.001` |
| M7 pinned-record sha verify off | DID NOT RAISE |
| M8 production path returns the registry part | `assert 20.4534… == 27.4534…` |
| M9 schema check off | DID NOT RAISE |
| M10 `--verify` skips the reconcile | `assert (0 == 3)` |
| M11 `--verify` skips the pinned sha | `assert 0 == 3` |
| M12 `write_pin` skips the reconcile | DID NOT RAISE |
| M13 the recorder's duplicate check off | `HonestNUnavailableError` raised **by the write path's own load-validation, not the recorder's `RecordError`**. The duplicate is still refused, one rail deeper. The test failed on the exception type. |
| M14 the recorder's path-exists check off | DID NOT RAISE `RecordError` |
| M15 the recorder's source-line bound off | DID NOT RAISE `RecordError` |
| M16 lint: declared-N check off | `assert False` |
| M17 lint: forward states-N off | `assert False` |
| M18 lint: forward record-row off | `assert False` |
| M19 lint: dangling ledger_id off | `assert False` |
| M20 lint: the B-series `N_trials +k` form dropped | the real ledger and the clean fixture both fail |

The harness lives in the session scratchpad. It is reproducible from this table: one string per mode, `count == 1`,
and `pytest -q -p no:cacheprovider -x <ids>`.

## §3. Impact, and what the user decides

### 3.1 Live gates that read N

| gate | reads | what changes on merge |
|---|---|---|
| **MBL Gate-0** (Discovery `validate_candidate`, `engines/engine_d_discovery/discovery.py:1281` → `check_mbl_gate`; the cycle's `orchestration/mode_controller.py:1320` → `resolve_cycle_n_trials`) | `compute_n_effective_correlated()` | N_eff 36.92 → 89.92. At `mbl_sr_target` 1.0 (`discovery.py:1158`) MinBTL goes 4.66 → 6.22 y, so a candidate window of 4.66–6.22 y that passed now fails Gate 0. The cycle's log carries the breakdown (`_n_info["breakdown"]`). |
| **DSR / Discovery Gate 8** (`discovery.py:2009` → `deflated_sharpe_ratio`, `:2028`) | the same | The selection benchmark E[max_N] goes 2.158 → 2.493 (×1.155; R3 would be 2.920, ×1.353), so DSR falls for every candidate. Cloud `--discover` stays halted by ruling RR-3B regardless. |
| **DSR in `core/measurement_reporter.py:99`** | an explicit `n_trials_for_dsr` (default 1) | Unchanged. Aside, not acted on: a default of 1 is a vacuous DSR, the RR-6a class. |
| **The submit gate** (`scripts/submit_arms_campaign.py` `enforce_substrate_gate`) | the anchors and the substrate manifest; it reads no N | Unchanged. The record is committed source, not a `HONEST_N_FILES` data file, so the manifest digest does not move. The image build's `honest_n_pin --verify` (`Dockerfile.backtest:168`) now also fails the build on a bad record. |
| Verdict scripts that read the gate (`scripts/tilt_decision_measure_t318_t320.py:678-679`, `scripts/b5_levered_diversified.py:778-782`) | the no-argument call | A re-run would read 89.92. |

### 3.2 Recorded verdicts whose MBL or DSR line would move

All are lines quoting the gate's N or a hand N. A higher N only raises a bar, so no refutation can flip to a pass. A
"CLEARS" line can only lose margin. The numbers are not recomputed here.

- **Quoting the gate's 36.92 / 37.08:**
  - B-10 `docs/Audit/b10_gold_leg_verdict_2026-11-11.md:74, :315, :317`
  - B-9 `b9_combo_tilts_verdict_2026-11-11.md:149, :153, :159`
  - B-5 `b5_levered_diversified_verdict_2026-11-11.md:193-194`
  - B-2 `b2_smallcap_t265_verdict_2026-11-11.md:166, :243, :321`
  - B-1 `b1_raw_signal_decile_verdict_2026-10-14.md:389`
  - B-8 `docs/Sources/prereg_b8_execution_timing_2026-11-11.md:598` (closed)
- **Quoting the 267 or a hand count:**
  - B-5 `:194` (0.375 at 267)
  - B-10 `:317` (≥ 282, ≈ 289): resolved here to **inside** for the T-306 series, and **≥ 283 + 37** for the rest
  - B-2 `:243` (N ≈ 260)
  - B-6 `b6_lazy_prices_verdict_2026-11-12.md:132` (a 5.75 y MinBTL bar)
- **The T-306 arc, quoting N = 76–78 at 64 y** (already re-framed by `mbl_framing_correction_t306_arc_2026_07_28.md:19-21`):
  - T-311 `deep_reverify_sleeve_t311_2026_07_27.md:41`
  - T-260 `deep_reverify_speeds_t260_2026_07_27.md:46`
  - T-314 `adaptation_rule_t314_2026_07_27.md:97`
  - At 64 y the exact form needs SR 0.312 at R2 and 0.365 at R3.
- **Older lines quoting a family or hand N:**
  - T-269 `asymmetric_exits_verdict_t269_2026_07_02.md:29` (N_eff 16)
  - T-255 `fair_t236_rerun_t255_2026_07_02.md:43` (N = 16)
  - T-265 `smallcap_pead_pilot_t265_2026_07_02.md:45` (~1.05 at honest N)
  - T-270 `intraday_probe_preregistration_t270_2026_07_02.md:51` (~263)
  - T-342 `volterm_conditioner_prereg_t342_2026_08_15.md:121` (≈ 260+)
  - T-336 `honest_n_plumbing_t336_part1_2026_08_05.md:34, :51` (N = 231)
- **The doctrine text:** CLAUDE.md `[NN-MBL]` ("N_eff ≈ 37 … 5 y ≥ 0.97, 12 y ≥ 0.62, 26 y ≥ 0.42") and the `CURRENT_STATE.md` honest-N lines become stale on merge. Under R2 they read 1.115 / 0.720 / 0.489. CLAUDE.md is the user's.

### 3.3 For the user to approve or rule

1. **The merge itself.** It is a referee change, so the gate moves 36.92 → 89.92 from the merge.
   - The alternative is to count the record only from re-pin #2 (cutover day). It needs a small code change (count only when the pin names the record). It leaves the gate knowingly short until then, which is why the branch does not do it.
2. **R2 gated vs R3 gated.** R3 = 324.28 is ruling 9.2 applied to the registry's own 231 curve-less rows, and it is computable from pinned inputs today.
   - Adopting it changes one key in `honest_n_breakdown` (`n_eff` ← `n_eff_ruling_9_2_all`) plus one test expectation.
   - The branch gates R2 and reports R3, because stripping the registry's credit belongs with the Option B build.
3. **The 12 unresolved items** (§1.2 D). Each needs a count ruling. The largest is U1 (T-193's 35, VOID).
4. **Re-pin #2:** `honest_n_pin --pin <artifact> --replace` will write v2 with the record's sha256. On that day:
   - `test_honest_n_pin.py::test_the_committed_pin_is_well_formed` (which asserts `honest_n_pin/v1`) is updated in the same act;
   - after it, every `honest_n_trials record` is followed by a re-pin in the same commit.
5. **The ledger** (the director's): T-365's row says 4 where its verdict says 6. T-214 and T-220 still read `dispatched`. T-391's own row is the director's to add at merge.
6. **Not built (proposed):** wiring `honest_n_trials check` into the nightly janitor. Today the enforcement is the pytest lock `test_the_lint_passes_on_the_REAL_ledger_and_the_REAL_record` in the full suite.

---

## §4. Review round 1 (2026-11-13): NOT READY, addressed in follow-up commits

**§1.2's totals, §2.1's numbers and §3's "89.92" are superseded by this section.** They are left as written. The
review found the inventory short and the forward lint bypassable. Both were true.

### 4.1 The inventory was short: the re-sweep

**Why the first sweep missed them.** It searched only `docs/Audit`, `docs/Sources` and `docs/Measurements`, and only
the `+=` / `+k` / `consumed` forms. It missed `N_trials = k`, lineage tallies, counts stated in `scripts/*_tNNN.py`
docstrings, and results that live only in `docs/State/conditional_shelf.md`.

**The re-sweep, reproducible.** Two passes over `git ls-files` (`.md` and `.py`; `Archive` and `Sessions` excluded):

1. **Every line in `docs/`, `scripts/`, `core/`, `engines/`, `orchestration/`, `config/` and root `*.md`** matching
   any of:
   `N_trials\s*\+=\s*\d` · `N_trials\s*\+\s*\d` · `N_trials\s*=\s*\d` · `N_trials\s*:\s*\**\s*\+?\d` ·
   `\bN\s*\+=\s*\d` · `n_trials_consumed` · `N_trials[ _]consumed` · `N_TRIALS\w*\s*=\s*\d` · `n_trials\s*[:=]\s*\d` ·
   `trials? consumed` · `consumes? \w+ (?:N_)?trials?` · `N_trials\s*(?:→|->)\s*\d` · `\(→\s*\d+\)` ·
   `N_trials\s+\d` · `\d+\s+N_trials` · `honest[- ]N\s*(?:\+=|→|->)\s*\d` · `\+\d+\s+(?:N_)?trials?\b` ·
   `family[- ]N\s*=\s*\d`
2. **Every file in `docs/` and `scripts/` whose NAME carries a task id not yet in the record**, searched with a wide
   net:
   `N_trials|n_trials|N_TRIALS|N_trial\b|honest[- ]N|N_eff|\bN\s*\+=|family[- ]N|\bN\s*[=≈~]\s*\d|\+\s*1 trial|ONE (?:pre-registered )?(?:config|trial)`,
   plus "trial(s)" within 40 characters of `consum`, `pre-regist` or `count`.
   This returned 130 files across 97 task ids. Each was read and classified.
3. **The State files** (`conditional_shelf.md`, `forward_plan.md`, `ROADMAP.md`, `lessons_learned.md`,
   `capability_ledger.md`) with `N_trials|n_trials|family N|N ?\+=|honest-N ≈|\+1 trial`.

**Limit, stated:** pass 2 keys on a task id in the file NAME. A trial recorded only inside a file with no task id in
its name, in a form pass 1 does not match, would still be missed.

**Added to the record: 5 entries, 7 trials (firm):**

| task | date | n | source |
|---|---|---|---|
| T-236 | 2026-06-25 | 1 | `docs/Audit/trend_sleeve_gauntlet_t236_2026_06_25.md:35-36` (a lineage tally: T-204 9 + T-214 6 + T-234 0 + T-236 1 = 16) |
| T-247 | 2026-06-30 | 1 | `scripts/carry_sleeve_gauntlet_t247.py:22`; the result is at `docs/State/conditional_shelf.md:340-348` |
| T-249 | 2026-06-26 | 1 | `docs/Audit/smallcap_momentum_gauntlet_t249_2026_06_26.md:47` ("N_trials = 1") |
| T-252 | 2026-06-26 | 3 | `docs/Audit/conditional_voltarget_gauntlet_t252_2026_06_26.md:26` ("N_trials = 3 treatment configs") |
| T-263 | 2026-07-02 | 1 | `scripts/multiasset_carry_gauntlet_t263.py:10` (merged `091e0f7`; ledger :183 `refuted`). **My U6 reason ("branch only, no doc on main, no stated N") was false**: the script is on main and states the count. |

**Counted pending the user's ruling: 2 entries, 36 trials** (`pending_ruling: true` in the record). The rule is now
one rule: a trial that ran counts until a ruling says otherwise, which is how T-339, T-339b and T-337 (all VOID or
blocked) were already counted.

| task | n | source | the open question |
|---|---|---|---|
| T-193 | 35 | `docs/Audit/phase0b_local_discover_t193_2026_06_17.md:95` ("consumed 35 trials … VOID") | It may be the same 35 foundry candidates T-196 re-ran on a fixed baseline. |
| T-237 | 1 | `scripts/lazy_prices/backtest_lazy_prices_t237.py:25` | The run is evidenced only second-hand (`TASK_LEDGER.md:284`: "the T-237 'leaning H0' had no valid panel behind it"). |

**Unresolved, not counted: now 11.** U1 (T-193) and U6 (T-263) left the list because they are counted. One was added:
**T-205** (`defensive_tilt_screens_t205_2026_06_18.md:45`): 9 arms ran descriptively, and its own pre-registration says
"N is consumed at the eventual beat-the-robo gate measurement, NOT here". That later measurement is not on record, so
it is 9 or 0. The rest stay unresolved because no count is stated for a run (T-216 §3, T-250, T-254), no run is
evidenced (T-217, T-349), the doc contradicts itself (T-148), or its own pre-registered policy says 0 (T-157).

**Found and deliberately NOT in the record: controller-harness runs.** They wrote run directories, so they belong to
the executed universe (the 252 / 258 that R3 already counts). Adding them to S would double-count under R3:
- T-055g, 4 (`vol_target_multiplier_sensitivity_t055g_2026_05_24.md:169`)
- T-057, 3 (`confidence_gated_execution_2026_05_12.md:118`)
- T-092, 10 (`deep_substrate_baseline_t092_2026_05_31.md:33`)
- T-118, 36 (`hmm_transition_trigger_overlay_t118_2026_06_06.md:86`)
- T-128r, 1 (`spot_sleeve_closeout_clean_t128r_2026_06_14.md:96`)
- T-154, 1 pit arm (`scripts/measure_pit_strategy_t154.py:35`)
- T-215, 1 (`phase1_cloud_run_t215_2026_06_19.md:200`)
- T-153, 10 cells (`vol_estimator_fix_t153_2026_06_11.md:81`)

T-154 and T-153 are classified as controller runs from their own text (a canon md5 of the trade log; campaign
cells). I did not verify that their run directories are among the 252.

### 4.2 The new totals and N

**S = 96:** 60 firm (16 after the 267, 44 before it) + 36 pending a ruling. The record holds 70 rows, digest
`378e6ac7…`. The registry md5 is `83e47441…`, unchanged. `honest_n_pin --verify` prints PIN OK with S = 96.

| rule | with T-193 (S = 96) | without T-193 (S = 61) | firm only (S = 60) |
|---|---|---|---|
| R0 today | 36.92 | 36.92 | 36.92 |
| R1 pooled (rejected) | 52.27 | 46.67 | 46.51 |
| **R2 gated** | **132.92** | 97.92 | 96.92 |
| R3 reported | 367.28 | 332.28 | 331.28 |

At R2 = 132.92: MinBTL at SR 1 is 6.91 y, and the SR required at 12 y / 26 y is 0.759 / 0.516. Without T-193 it is
6.37 y and 0.728 / 0.495. At R3 = 367.28 it is 8.75 y and 0.854 / 0.580. `honest_n_breakdown` now also returns
`n_standalone_pending_ruling` (36) and `n_eff_excluding_pending` (96.92), so both readings travel with every quote.

### 4.3 The code findings

- **F3, the forward lint could be bypassed.** It bound only rows whose doc cell said `verdict` or `prereg` AND whose
  status was closed. Now, for any row dated on or after activation (a range reads by its first date; a row with no
  parseable date is treated as forward), a record row is required when the row states a trial count, OR its status is
  closed, OR its doc cell names an existing file under `docs/Audit`, `docs/Sources`, `docs/State`, `docs/Core`,
  `docs/Measurements/*` or `scripts`, whatever the status. A closed row must also state N.
  - **Consequence for the director:** from 2026-11-13 every closed ledger row needs a record row, infra included
    (`--n-trials 0`).
- **F4, `activation_date` was outside the digest.** It is now inside it. Setting it to 2099 fails the digest check.
- **F5a, citations were checked for presence, not existence.** `verify_trials_citations` now checks that each
  `source` path exists and its line is within the file, and that `prereg` / `verdict` exist. It runs in the gate, in
  `check`, and in the backfill build.
  - **Limit:** the backtest image ships no `docs/` (`.dockerignore:77`). An unconditional check at load would refuse
    every cloud gate call. So the gate checks wherever `<root>/docs` exists and returns `citations_checked: false`
    where it does not. `honest_n_pin --verify` (which runs in the image build) does not check citations.
- **F5b, the `== 53` asserts.** They now read S from the record and assert a floor (`BACKFILL_FLOOR = 96`). The
  workflow: a `record` raises S and no test moves. Only a ruling lowers S, and the floor is lowered in that same
  commit.
- **F5c, a registry task re-added as a standalone row was accepted.** It is now refused by task id or ledger id,
  unless the row names the registry trial it is distinct from (`also_in_registry_as`). T-260's 2026-07-02 trial is the
  one legitimate case. The recorder cannot set that field.
- **F6, T-365.** The record's note reads "the verdict says 6, the ledger row says 4 (the record follows the verdict)".
  The ledger is untouched.

**Tests:** `tests/test_honest_n_trials_t391.py` is now 50 tests, including the three planted lint bypasses, the
undated row, the activation-date tamper, the both-classes refusal and the citation checks. The honest-N and MBL
modules together: 152 pass, 8 xfail. The reversion harness: **28 modes, all caught** (the original 20 plus N1
activation date out of the digest, N2 both-classes check off, N3 gate citation check off, N4 / N4b / N4c the forward
trigger narrowed three ways, N5 undated rows skipped, N6 `check` skipping citations). M13 still fails one rail
deeper than targeted, as in §2.2.
