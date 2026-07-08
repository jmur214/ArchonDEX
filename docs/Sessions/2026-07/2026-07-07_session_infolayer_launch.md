# Session Summary: 2026-07-07/08 — The Information + Judgment Layer program: launch → build → all lanes landed in ~36 hours

## What was worked on

- **The entire Info-Layer program** (`docs/Sources/info_layer_program_2026_07_07.md`), from user-approved plan
  to substantially-built system: Lane 1 news (probe → PIT panel → frozen tests), Lane 2 event-state (archivers,
  KXFED rate-path, FOMC calendar, EventStateDetector), Lane 3 LLM analyst (evaluation harness at full
  tournament standard; the analyst service itself queued behind the fleet). T-289…T-296 all dispatched;
  T-290/290b/291/293(+b,c)/296 closed, T-289 closing (backfill finishing), T-294/295 in flight.
- **Paper go-live + the 3-account fleet**: account 1 (defensive sleeve) ENABLED and trading autonomously
  (rev12: poll-until-filled + BTC shadow); fleet constructors for accounts 2 (gated-2× SSO) and 3
  (sleeve+IBIT) built and merged; driver generalization in progress; first scheduled self-trigger Wed 9:45 ET.
- **Two external prompt runs** (research agent 16-question v2; fresh-eyes repo audit) — both archived
  verbatim with director triage under the NEW `docs/Sources/External_Prompt_Runs/` convention.

## What was decided

- **Archive-every-prompt-run rule** (user directive): prompt + verbatim findings + model self-report header +
  triage table, permanently, in `docs/Sources/External_Prompt_Runs/`. Codified in SESSION_PROCEDURES.md.
- **G1 promotion gate amended TWICE**: (1) beat the market-implied prior per category, skill-score ci_low>0,
  discrimination requirement, gimme exclusion (A's adversarial review — base-rate hedger was a pass);
  (2) block-bootstrap CI on the Brier differential + pre-registered question sets + walk-forward isotonic
  recalibration (external research convergence). Now ENFORCED in code (`g1_skill` block), test-proven.
- **T-294 vehicle bake-off BLOCKS real money to the offense config** (research finding #1: SSO daily-reset
  decay vs NTSX/RSSB negative-cost stacking — the vehicle, not the signal, may be leaking edge).
- **Cross-account wash-sale guard = BLOCKING requirement before the taxable wrapper opens** (Rev. Rul.
  2008-5; advisor spec §9), plus after-tax account-specific benchmarking for the taxable column.
- **Kill-switch semantics codified**: halt = stop new automated actions, NEVER liquidate.
- **launchd archivers are PERMANENT** (18:30 ET EOD series) alongside the pulse's 09:45 ET pre-open series —
  the fresh-eyes time-of-day-discontinuity finding; no retirement.
- **T-296 freeze discipline**: proxy fallback order pre-committed; ±4-5%/yr basis accepted EXPLORATORY-only
  with the consequence rule pre-stated (PASS = a real-RSST shadow slot only; FAIL = door closes, CTA untouched).
- **Fleet accounts**: default $100k values (the $10k software cap governs sizing — min(equity, cap) is
  deterministic), names `archondex-offense-sso` / `archondex-btc-sleeve`.

## What was learned

- **Trend layers don't stack, they interfere** (T-296 H0, the session's headline null): the gate reads the
  combined price → RSST's internal MF up-trend masked SPY's 2022 decline → LESS protection (−7.5% vs −5.2%).
  Internally-overlaid funds are always-long-core candidates, never the gated leg. Plus: return-stack
  synthetics must be collateral-aware (naive form measured +9.1%/yr wrong). Both in lessons_learned.md.
- **The even-week premium is NOT FOMC-concentrated** (T-291 H0; FOMC-calendar family now 3/3 null).
- **The news corpus is deep and survivorship-CLEAN** (T-289a: Benzinga floor 2015-01, ~11yr; SIVB/FRC/TWTR/
  BBBY covered through delisting) — the user's named concern resolved at the probe level.
- **Kalshi is genuinely well-calibrated on Fed path** (FEDS 2026-010) and B's KXFED catch mattered: the
  generic snapshot was blind to the Fed market (prices moved to `*_dollars`/`*_fp` fields).
- **The fresh-eyes audit caught a real hole in the director's own day-1 work**: archivers exit 0
  unconditionally → the launchd failure token was unreachable. Fixed same day (verify_altdata_snapshot.py +
  SNS/notification alarm). Also: no per-account pulse exists (fleet = net-new refactor), CloudState is a
  small-file sync (T-290b date-partitioned the panel prefix).
- **Honest behavior gap ≈ 1.2%/yr** (Morningstar), not DALBAR's 848bps — the system's automation edge
  claimed accordingly.
- **Stooq is bot-walled** (health_check MEDIUM): on-disk data fine, all future refresh paths dead.
- Operational: interactive-session background jobs die at turn boundaries → launchd one-shots for >30min
  unattended work (D's backfill); macOS ephemeral-port exhaustion (OSError 49) can kill sustained API pulls —
  resumable design absorbed it.

## State at session end

- **LIVE**: account-1 sleeve trading autonomously (rev12); launchd archivers captured their first fully
  scheduled run CLEAN (altdata=0 positioning=0 verify=0); KXFED + FRED rate-path accruing daily.
- **IN FLIGHT**: D's backfill (~121/139 months, restarted after a transient network error; tests auto-run on
  completion → the a1/a2/a3/b1 interaction table); E's fleet driver generalization (constructors merged);
  B's T-295 finalization (one clean unthrottled ZQ run; Fargate = the fresh-IP shortcut) + the one-time
  panel backfill upload (waits on D's completion signal).
- **QUEUED**: D→T-294 vehicle bake-off (collateral-aware synthetics); E→T-292 analyst stage-0 (LAST, after
  the fleet); rev13 carries B's step-8 news wiring + E's fleet driver together.
- **USER items open**: `sns:Publish` IAM grant for `claude-code-cli` on `archondex-paper-alerts` (archiver
  alarms are local-notification-only until then); dashboard-v2 verdict (redesign sits uncommitted).
- **Next session first checks**: the 9:45 ET self-trigger (single-run adopt + first gate-b sample + btc-shadow
  accruing); D's interaction table (or the F1 >30% HALT); E's armed runs.
