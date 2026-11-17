# ACCOUNT 2 RESET RUNBOOK — PROPOSED (risk lens, 2026-11-17; propose-first)

**Status:** PROPOSED. Nothing in this document has been run. Every command below is text for a later,
explicitly approved session. This draft changed no state: no S3 or AWS writes, no broker calls. The
evidence came from read-only `aws s3 ls`/`s3 cp` to a local scratch copy, `describe-*`/`get-*` reads,
the code at `fc7254b`, and Alpaca's public docs.

**The ruling this executes:** on 2026-11-17 the user ruled that account 2 is RESET, not repaired by a
journaled basis adjustment.

**Tags.** Each claim carries `[VERIFIED: source]` (a file:line, an S3 key listed or read on 2026-11-17,
an AWS read-only response, or a public doc URL read on 2026-11-17) or `[UNVERIFIED]`.

**Naming correction.** The brief calls the account's strategy `offense_sso`. It is not. Account 2 runs
`deploy_candidate`: the jobdef env has `ARCHONDEX_PAPER_STRATEGY=deploy_candidate` [VERIFIED: `aws batch
describe-job-definitions` archondex-paper-offense-sso:21, read 2026-11-17]. The `offense-sso` /
`offense_sso` names survive only as identifiers: the S3 prefix, the jobdef family, the alarm names, the
metric dimension `Account=offense-sso` and the secret. They were kept on purpose at the T-350 repurpose
because a rename touches IAM ARNs [VERIFIED: `scripts/provision_paper_fleet.py:47-50`;
`scripts/run_paper_cloud_day.py:841-844`].

---

## 0. Findings that change the plan (read these first)

| # | Finding | Consequence |
|---|---|---|
| F1 | **Alpaca no longer resets paper accounts in place.** Its docs say: "We've updated the dashboard to allow you to create and delete paper accounts, rather than resetting them … Don't forget to generate new API keys for any newly created account", and "You cannot change the account balance after it is created" [VERIFIED: https://docs.alpaca.markets/us/docs/paper-trading.md, "Reset Your Paper Trading Account" and "Rules and Assumptions", read 2026-11-17]. | A broker "reset" now means a NEW paper account, with a new account number and a new key pair. Account 2's existing balance cannot be set to $10,000. |
| F2 | **The user has a 3-paper-account cap**, and all three slots are in use: secrets `archondex/alpaca-paper`, `…-offense-sso` and `…-btc-sleeve` (the last now account 3) [VERIFIED: `scripts/provision_paper_fleet.py:86-89` "the user's 3-account cap"; `docs/Core/execution_manual.md:1084`]. Whether Alpaca itself enforces 3 is [UNVERIFIED]; the docs page does not state a limit. | A new paper account probably means DELETING old account 2 first. Deletion is irreversible and loses the broker-side history. |
| F3 | **The broker does not hold ~$13,500.** It holds about **$103,515 equity**: 12 VOO + 92 MTUM + 6 SGOV = $14,811.92 at the 2026-11-16 closes, plus roughly $88.7k of cash [VERIFIED: S3 `paper_state_offense_sso/data/state/deploy_candidate_tracking.json` last point 2026-11-17 `sleeve_equity` 103,514.78; `…/fleet_mirror_slice.json` positions]. The $10k tier was never a broker balance. It is the notional cap [VERIFIED: `scripts/transition_acct2_to_deploy_candidate_t350.py:21-24`]. | A clean TIER restart is possible in place. Sizing is `min(broker equity, cap)` [VERIFIED: `scripts/run_paper_cloud_day.py:165-166, 941-942`], so the windfall becomes idle cash that the cap keeps out of sizing. It is fenced off, not removed. |
| F4 | **The tier at the new arrival is $11,166, not $10,000.** Rule-B contributions grow the cap by $583 per whole month since `start_date` 2026-09-11 [VERIFIED: `config/deploy_candidate.json` `contributions`; `paper_trader/deploy_candidate_constructor.py:271-316`]. From 2026-11-11 to 2026-12-10 that is 2 months, so 10,000 + 1,166. | Getting exactly $10,000 needs `start_date` re-based to the arrival date. The config is baked into the image, so that means a rebuild plus a surgical redeploy (decision U2). The default is to keep it and state $11,166. |
| F5 | **A state-only reset on a non-flat broker reproduces the halt.** With an empty journal, 12 VOO / 92 MTUM / 6 SGOV at the broker are UNEXPLAINED and are never adopted [VERIFIED: `paper_trader/held_reconcile.py:55-70, 97-119`]. | The broker must be flat (option B) or be a new account (option A) BEFORE the first run on archived state. |
| F6 | **The first run after the reset is a SEEDING day by design.** No price-basis marks means a stand-down: nothing is staged and the job exits 70 [VERIFIED: `paper_trader/corporate_actions.py:953-967, 725-741`; `scripts/run_paper_cloud_day.py:1005-1012, 1774-1777`]. | The arrival buy happens on the SECOND scheduled run. Day 1 pages as non-canonical, and that is expected. |
| F7 | **"36 clean sessions" counts the defect day.** The tracker's `d_clean_days` is 36, but 2026-11-05 (the spurious 18-MTUM buy) is recorded `canonical: True, order_errors: 0`. Only 35 tracked points fall on or before 2026-11-04 [VERIFIED: tracker points read 2026-11-17; `paper_trader/sleeve_tracker.py:219`]. | The valid epoch-1 record is 35 tracked clean sessions (2026-09-17 → 2026-11-04), plus the 2026-09-15/16 arrival sessions, which were never tracked [VERIFIED: `docs/Archive/state_history/CURRENT_STATE_full_history_to_2026_09_17.md:13` "deploy tracker was ephemeral until 09-17"]. 2026-11-05 is VOID even though the tracker calls it clean. |
| F8 | **The laptop `.env` holds ACCOUNT 1's keys.** `.env` has exactly one `ALPACA_API_KEY` name [VERIFIED: names-only read of `.env`, no values]. The deploy script writes it to `archondex/alpaca-paper`, which is account 1's secret [VERIFIED: `scripts/deploy_paper_cloud_trigger.sh:37, 56-75`]. `AlpacaPaperClient` loads `.env` [VERIFIED: `paper_trader/paper_client.py:170-177`]. | Any broker command run from the laptop reaches ACCOUNT 1. Every broker action in this runbook goes through account 2's own jobdef. |
| F9 | **The fleet mirror reads the BASE cap.** The driver passes `tier_cap=args.sleeve_notional_cap` (10,000) while sizing uses the contributed cap [VERIFIED: `scripts/run_paper_cloud_day.py:1592` vs `:861-862, 941-942`]. | On arrival day the new epoch's mirror `total_change` would read about +$1,166 (contributions, not performance). This defect pre-dates the reset; a fix is proposed in §8 R8. |

---

## 1. Every piece of account-2 state (item 1)

Bucket `archondex-results-407539788432` [VERIFIED: `scripts/ledger_backup.py:39`; jobdef :21 env
`ARCHONDEX_PAPER_STATE_BUCKET`], prefix `paper_state_offense_sso` [VERIFIED: jobdef :21 env
`ARCHONDEX_PAPER_STATE_PREFIX`]. Full listing as of 2026-11-17, all live objects written by the
14:51 UTC run [VERIFIED: `aws s3 ls --recursive`, 2026-11-17]:

| Key under the prefix | Bytes | Written by | Read by | Reset action |
|---|---|---|---|---|
| `data/paper_state/ledger.jsonl` | 41,602 | `LedgerStore` snapshots; `adopt_explained_broker_truth` [VERIFIED: `scripts/run_paper_cloud_day.py:592-593`; `paper_trader/held_reconcile.py:117-118`] | the next run (resumes its last valid snapshot) [VERIFIED: `paper_trader/ledger_store.py:77-87`]; the gate's query window via `last_event_date` [VERIFIED: `scripts/run_paper_cloud_day.py:639-640`] | **ARCHIVE + MOVE ASIDE.** It holds the mixed-basis 23 MTUM (last snapshot seq 151: MTUM 23, SGOV 6, VOO 12, cash 88,725.41) [VERIFIED: S3 object read 2026-11-17]. Never re-seed from it. |
| `data/paper_state/orders.jsonl` | 33,463 | `OrderManager` journal [VERIFIED: `scripts/run_paper_cloud_day.py:585-588`] | the next run's reconcile (`journal_net_positions`), the split gate's fill dating, the mirror's basis [VERIFIED: `paper_trader/held_reconcile.py:28-52`; `paper_trader/corporate_actions.py:778-799`; `scripts/run_paper_cloud_day.py:1568-1574`] | **ARCHIVE + MOVE ASIDE.** 27 orders: 12 filled; 15 STAGED and never submitted (2026-11-06 → 11-13, blocked by the halt) [VERIFIED: S3 object read]. The journal is the only record of the epoch-1 fills; the archive preserves it. |
| `data/paper_state/recon.jsonl` | 41,400 | `PaperScheduler` reconcile log [VERIFIED: `scripts/run_paper_cloud_day.py:596-597`] | nothing in the run reads it back [VERIFIED: grep, `paper_trader/clock_census.py:523` "written by reconcile"] | **ARCHIVE + MOVE ASIDE** (clean epoch). |
| `data/state/deploy_candidate_tracking.json` | 24,524 | `SleeveTracker` via `_record_family_tracker` [VERIFIED: `scripts/run_paper_cloud_day.py:1479-1495`] | the next run (appends a point; the summary is recomputed over ALL points, canonical or not) [VERIFIED: `paper_trader/sleeve_tracker.py:265-283`] | **ARCHIVE + MOVE ASIDE + LABEL VOID.** 44 points 2026-09-17 → 11-17; the summary currently reads CAGR 0.1983, Sharpe 1.651 (the windfall) [VERIFIED: S3 object read]. |
| `data/state/fleet_mirror_slice.json` | 650 | the T-357 mirror block [VERIFIED: `scripts/run_paper_cloud_day.py:1563-1598`] | the next run as `prev_tier_equity` (today a swallowed `json` NameError makes `day_change` always null) [VERIFIED: `scripts/run_paper_cloud_day.py:1575-1581`, no module-level `import json`; `docs/State/health_check.md:63`]; the serving layer, which is not live (it is at the user's gate) [VERIFIED: `docs/State/CURRENT_STATE.md:142`] | **ARCHIVE + MOVE ASIDE.** `tier_equity` 14,811.92 includes the windfall [VERIFIED: S3 object read]. |
| `data/state/paper_alerts.log` | 14,166 | `PaperHeartbeat._notify` (append-on-alert) [VERIFIED: `paper_trader/heartbeat.py:32`; `paper_trader/clock_census.py:521`] | no gate reads it | **ARCHIVE + MOVE ASIDE** (clean epoch). |
| `data/state/paper_heartbeat.json` | 5,375 | `PaperHeartbeat` (record_run + blocks) [VERIFIED: `scripts/run_paper_cloud_day.py:976-996`] | `scripts/fleet_health.py` and the janitor's `fleet_health` check [VERIFIED: `scripts/fleet_health.py:26-30, 135-141`]; `hb.check()` reads only TODAY's `last_run`, which the run itself writes [VERIFIED: `paper_trader/heartbeat.py:344-371`] | **ARCHIVE + MOVE ASIDE.** Between the move and the next run, `fleet_health` reports account 2 UNKNOWN (expected; it fails closed) [VERIFIED: `scripts/fleet_health.py:136-139`]. |
| `data/state/price_basis_marks.json` | 1,154 | `CorporateActionGate.save` [VERIFIED: `paper_trader/corporate_actions.py:1002-1007, 553-570`] | the next run's gate (marks, persisted freezes, `account` stamp) [VERIFIED: `scripts/run_paper_cloud_day.py:638-653`] | **ARCHIVE + MOVE ASIDE.** It holds the MTUM `kind: ledger` freeze (frozen_on 2026-11-16), which can only be released by an ack [VERIFIED: S3 object read; `paper_trader/corporate_actions.py:453, 695`]. Its stamp is `account: paper_state_offense_sso`; the new file gets the same stamp on its first save [VERIFIED: `paper_trader/corporate_actions.py:641-643`]. |
| `data/state/tax_lots.jsonl` | 3,935 | the wash guard's `TaxLotLedger` (ENFORCING on `deploy_candidate`) [VERIFIED: `scripts/run_paper_cloud_day.py:74, 536-547`] | the wash guard at every submit [VERIFIED: `engines/engine_b_risk/cross_account_wash_guard.py:109-129`] | **ARCHIVE + MOVE ASIDE.** Its 12 lots include 5 MTUM @ 300.28 (pre-split) and 18 @ 65.26 [VERIFIED: S3 object read]. A missing file is an empty ledger, not an error [VERIFIED: `engines/engine_b_risk/cross_account_wash_guard.py:117-119`]. This is Engine B's INPUT; no Engine B code changes. |
| `data/state/exec_cost_ledger.jsonl` | 4,006 | `ExecCostLedger` (append-only, per proven-fresh fill) [VERIFIED: `scripts/run_paper_cloud_day.py:1610-1626`] | the heartbeat `exec_cost` aggregate; T-301b cost models | **SNAPSHOT-COPY, KEEP LIVE.** 12 rows of real paper fills; execution cost is mechanics and stays valid whatever the void [VERIFIED: S3 object read; heartbeat `exec_cost` block]. The 2026-11-05 MTUM row is a real fill of a spurious order; the archive label notes it. |
| `archive_offense_2026-09-11/*` (6 objects) | — | the T-350 transition [VERIFIED: `scripts/transition_acct2_to_deploy_candidate_t350.py:119-134`] | nobody | **LEAVE untouched.** |
| `data/state/TRADING_HALT` | absent | operator kill switch [VERIFIED: `paper_trader/trading_halt.py:51`] | `check_trading_halt` [VERIFIED: `scripts/run_paper_cloud_day.py:478-489`] | **Absent; leave absent** [VERIFIED: listing]. The jobdef has no `ARCHONDEX_TRADING_KILL_SWITCH` either [VERIFIED: jobdef :21 env]. |
| `DURABLE_DIRS` (analyst notes, llm_raw) | absent | account 1 only | — | nothing to do [VERIFIED: listing; `paper_trader/cloud_state.py:191-202`]. |

**Outside the prefix:**
- **CloudWatch:** `archondex-paper-offense-sso-non-canonical` and `…-silent-stop` (§4).
- **The schedule:** `archondex-paper-offense-sso-daily`.
- **The jobdef:** `archondex-paper-offense-sso:21`.
- **The secret:** `archondex/alpaca-paper-offense-sso` [VERIFIED: read-only `get-schedule`, `describe-alarms`, `describe-job-definitions`, `describe-secret` metadata, 2026-11-17].
- **The dashboard** (`cockpit/dashboard_v2`) reads only the local `data/paper_state/`, never this prefix [VERIFIED: `cockpit/dashboard_v2/utils/paper_loader.py:41`].
- **The digest** has an unwired deploy-candidate row builder that reads tax lots with a `start_date` [VERIFIED: `intelligence/analyst/performance_digest.py:292-324`; no production caller, grep]. If it is ever wired, its `start_date` must be the epoch-2 arrival date.

**How the runner treats a missing key:** benign. `pull()` treats a missing key as a first run and only a
denial as a failure [VERIFIED: `paper_trader/cloud_state.py:295-304`]. `push()` uploads only files that
exist and never deletes [VERIFIED: `paper_trader/cloud_state.py:330-340`]. So a moved-aside key stays
absent until a run recreates it. **Bucket versioning is not available as a safety net:**
`s3:GetBucketVersioning` is denied to the CLI user [VERIFIED: `scripts/ledger_backup.py:22`]. The
byte-verified archive copy is therefore the only protection.

---

## 2. How the runner starts from nothing (item 2)

What a scheduled run does on an empty prefix (`scripts/run_paper_cloud_day.py`):

1. **Pull.** Every key is missing, so it reads as a clean start [VERIFIED: `:433-445`; `paper_trader/cloud_state.py:302-304`].
2. **The ledger is seeded from BROKER CASH, never from broker positions.**
   `LedgerStore(..., starting_cash=acct["cash"])` writes one `init` snapshot with `positions={}`
   [VERIFIED: `:592-593`; `paper_trader/ledger_store.py:83-87`]. Positions enter the ledger ONLY by
   `adopt_explained_broker_truth`, and ONLY when the journal's fills explain the broker exactly
   [VERIFIED: `paper_trader/held_reconcile.py:97-119`].
3. **The tier comes from config, not from the broker.**
   - `deploy_candidate` refuses to run without `--sleeve-notional-cap` [VERIFIED: `:855-860`]. The entrypoint passes `ARCHONDEX_SLEEVE_NOTIONAL_CAP=10000` [VERIFIED: `scripts/paper_cloud_entrypoint.sh:31`; jobdef :21 env].
   - `deploy_cap = contributed_cap(10000, today)` [VERIFIED: `:861-862`].
   - `sizing_equity = min(broker equity, deploy_cap)` [VERIFIED: `:165-166, 941-942`].
4. **Split gate.** A new ledger has no dated event, so the feed window is the last 7 days [VERIFIED: `paper_trader/ledger_store.py:209-221`; `paper_trader/corporate_actions.py:597-604`]. MTUM's ex-date 2026-11-05 is outside that window for any run on or after 2026-11-13, so the MTUM split does not re-enter. With nothing held, a confirmed split cannot freeze anyway; that path applies only to held names [VERIFIED: `paper_trader/corporate_actions.py:953-967`].
5. **Price-basis marks.** No marks file means every traded ticker without a mark (VOO, MTUM, SGOV) goes on the seeding list, so `stand_down=True`. The plan is constructed and every order is REFUSED and recorded. The run is non-canonical with the reason "seeding price-basis marks (first run) for …" and exits **70** [VERIFIED: `paper_trader/corporate_actions.py:725-741, 965-967, 998-1000`; `scripts/run_paper_cloud_day.py:1005-1012, 1774-1777`]. Benchmarks (SPY, AGG, GLD) are just marked [VERIFIED: `paper_trader/corporate_actions.py:947-949`].
6. **Second run:** marks exist, `marks_age_sessions` is 1, there is no stand-down, and the constructor buys to target at the cap. Market DAY orders fill in-cycle and are adopted before each reconcile [VERIFIED: `scripts/run_paper_cloud_day.py:682-704`]. This is the arrival event. The T-350 arrival on 2026-09-15 was canonical on the same path: 12 VOO / 5 MTUM / 1 SGOV, $9,978.42 [VERIFIED: S3 journal; `docs/State/CURRENT_STATE.md:142`].

**Can a fresh $10,000-tier start work while the broker holds ~$103.5k and 92 MTUM? No.** The
positions are unexplained, so every run would HALT on `position_drift`, the same failure as today
with an emptier ledger [VERIFIED: `paper_trader/held_reconcile.py:55-70`]. Once the broker is FLAT,
**yes, at the TIER level**: sizing is bounded by the cap however large broker equity is. The tier will be
**$11,166** (F4) unless `start_date` is re-based. The broker BALANCE cannot be brought back to $10,000
in place (F1).

**What "`sleeve_equity` is BROKER equity, never tier equity" implies** [VERIFIED:
`paper_trader/fleet_mirror.py:78-81`; the user's memory index entry for
`project_account3_stage2_integration_2026_08_13.md`]:
- The tracker's record is denominated in the ~$100k broker account, so its CAGR and Sharpe were never tier performance in either epoch. Tier P&L is diluted about 10× by idle cash: 3.5k on 100k is the "CAGR 20 %" now on file.
- Under option B, epoch 2's tracker starts at about $103.5k. The windfall is in that starting LEVEL, not in any epoch-2 RETURN.
- The tier-honest surfaces are the fleet mirror (`tier_equity`, F9 aside) and the digest's lot-based row (unwired).
- If this account ever rehearses a tier of about $100k or more, the fence fails: the windfall becomes sizable, and that rehearsal needs a new paper account.

---

## 3. The broker side (item 3)

**Alpaca facts** [VERIFIED: https://docs.alpaca.markets/us/docs/paper-trading.md, read 2026-11-17 with a
generic client, no login]:
- A "reset" is now "Open New Paper Account" (dashboard) plus "generate new API keys". The account number and the key pair both CHANGE.
- An existing account's balance cannot be changed.
- New accounts default to $100k.
- Old account: "Delete Account" in Account Settings.
- Paper does NOT simulate dividends.

[UNVERIFIED]:
- whether the "Open New Paper Account" dialog accepts a custom starting balance (the page's older line "reset … with arbitrary amount" pre-dates the change);
- whether any API exists for this (the page describes dashboard steps only);
- whether Alpaca itself caps paper accounts at 3.

**Where account 2's keys live, by NAME:**
- Secrets Manager secret `archondex/alpaca-paper-offense-sso`, JSON keys `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`.
- jobdef :21 binds them as env vars `ALPACA_API_KEY` / `ALPACA_SECRET_KEY` through `secrets[].valueFrom` with no version stage.
- Created 2026-07-07, never changed (1 version), last accessed 2026-11-16 [VERIFIED: jobdef :21 `secrets`; `describe-secret` metadata only].
- [UNVERIFIED]: that an empty version stage resolves to AWSCURRENT, so a new value takes effect at the next container start with no jobdef revision. AWS docs were not re-read this session.
- The CLI user has no `GetSecretValue` by design [VERIFIED: `docs/Core/execution_manual.md:1015`]. Whether it holds `PutSecretValue` on `archondex/alpaca-paper*` is [UNVERIFIED]. A template grants it [VERIFIED: `infra/paper_cloud/iam_policy_provisioner_delta.json:9-14`]; whether that template is attached to the CLI user is not known, and `iam:SimulatePrincipalPolicy` is denied.

### Option B — LIQUIDATE IN PLACE (recommended default)

One explicitly approved one-shot Batch job on account 2's OWN jobdef sells exactly the broker's
positions. It uses the T-350 pattern: dry-run binds the signature, then execute [VERIFIED:
`scripts/transition_acct2_to_deploy_candidate_t350.py:74-116`; `docs/Core/execution_manual.md:1013-1035`].
The account is then all cash, about $103.5k, and the TIER is fenced by the cap (§2).

- **For:**
  - same account id, same keys, same secret, same jobdef, same IAM; no live-resource rename (the July class);
  - the broker history is preserved;
  - fully DIRECTOR-executable on the user's word;
  - rollback is trivial: a halted account is a safe resting state.
- **Against:**
  - the ~$3.5k windfall stays in broker cash for good, fenced but not removed;
  - the liquidation realizes paper P&L outside the OrderManager, so the lot ledger never sees it (R9);
  - the tracker's absolute level carries the windfall (§2).

### Option A — NEW ALPACA PAPER ACCOUNT

The user opens a new paper account (USER: dashboard login) and generates keys (USER). The keys go into
`archondex/alpaca-paper-offense-sso` (USER, in the AWS console). Keys never pass through chat, never go
into `.env` (F8), never go into a file inside the repo.

- **For:** the windfall is gone from the broker, and no sale is needed.
- **Against:**
  - (a) under the 3-account cap (F2) the OLD account 2 must probably be DELETED first, which irreversibly loses its broker history and any chance of rolling back;
  - (b) key rotation, in a secret last changed in July;
  - (c) a starting balance of **$10,000** would silently break the Rule-B rehearsal: after the first contribution, cap > equity, so `min(equity, cap)` binds on equity, the "+$583/mo" is printed and never deployed (the silent-wrongness shape). Avoiding that needs contributions disabled or re-designed, which means an image change;
  - (d) at the $100k default, A buys nothing B does not, at much higher cost.
- **If A anyway:**
  - Before deleting: our S3 journal plus the archive keep every epoch-1 fill (§1). Exporting the old account's activity from the dashboard is the USER's call; whether that export is available is [UNVERIFIED].
  - After the epoch-2 first artifact: the user REVOKES the old key pair (assume it leaked).
  - Verify the secret now reaches the NEW account with the FLAT-CHECK job: `FLAT=True` and `equity` exactly equal to the chosen starting balance. If it shows account 1 or account 3 positions, the wrong pair was pasted: STOP.

**Recommendation: B.** It is the smallest change to a live path, it keeps every identifier, and it
achieves the user's requirement ("start at a clean tier basis") through the mechanism already in force
since T-350. A only becomes necessary if the user wants broker equity itself to equal the tier. Under
contributions, that is a design change, not a reset.

---

## 4. Halt, freeze and alarms (item 4)

- **The halt.** `halted` is recomputed every run from the reconcile; it is not persisted [VERIFIED: `paper_trader/scheduler.py:320-325, 405-412`]. It clears on the first run where the journal explains the broker: an empty journal plus a flat broker counts as explained [VERIFIED: `paper_trader/held_reconcile.py:63-70`]. There is no `TRADING_HALT` object and no kill-switch env to clear (§1).
- **The MTUM freeze.**
  - It is a PERSISTED `kind: ledger` freeze in `price_basis_marks.json` [VERIFIED: S3 object; heartbeat `corporate_actions.frozen_persisted`]. It can only be released by an ack [VERIFIED: `paper_trader/corporate_actions.py:453, 695`].
  - An ack cannot release it while the mixed basis remains: the next run re-freezes [VERIFIED: `scripts/corporate_action_ack.py:13-16` (header)].
  - **The reset does not use the ack tool at all.** It removes the mixed basis (ledger, journal and lots archived; broker flat), then moves the marks file aside, so the freeze has nothing to persist in.
  - R3-1 therefore cannot bite here. The current freeze reason does not contain "supersedes the earlier" [VERIFIED: heartbeat 2026-11-17].
  - **Standing rule for D+1/D+2:** if ANY freeze appears, do not ack it, and above all not one whose reason contains "supersedes the earlier" [VERIFIED: `docs/State/health_check.md:63` R3-1]. STOP and review.
- **The CloudWatch alarm:** `archondex-paper-offense-sso-non-canonical` [VERIFIED: `describe-alarms`, 2026-11-17].
  - State ALARM since 2026-11-06T08:52:07-06:00 (14:52 UTC).
  - Metric `ArchonDEX/PaperLoop` `PaperRunCanonical`, dimension `Account=offense-sso`, Minimum over 86,400 s, 1 evaluation period, `< 1`, missing data `notBreaching`, actions ENABLED.
  - **How it re-arms:** it returns to OK on its own, sending the SNS OK notification, at the first evaluation whose 24 h window holds only canonical datapoints. Expect this after the arrival run (D+2), not after the seeding run (D+1 emits 0). If D+1's 0 still falls inside the window at D+2's evaluation, OK comes later; the exact timing is [UNVERIFIED].
  - While it sits in ALARM, a NEW failure sends nothing (no state change). That is why the reset must get it back to OK quickly.
  - Per the arming protocol, trust needs a proven ALARM→OK→ALARM [VERIFIED: `scripts/provision_paper_fleet.py:54-65`]. The reset supplies ALARM→OK. The →ALARM leg is an optional DIRECTOR drill on the user's word (§6 step 15).
- **The silent-stop alarm:** `archondex-paper-offense-sso-silent-stop` [VERIFIED: `describe-alarms`]. OK since 2026-11-02; `PaperRunHappened` Maximum, missing data = BREACHING.
  - A missed scheduled run is configured to page.
  - [UNVERIFIED]: in practice it stayed OK through the 11-07/08 and 11-14/15 weekends, so its evaluation does not behave as the config literally reads.
  - Plan as if one missed firing WILL page, and announce it beforehand.

---

## 5. The record (item 5)

**Epoch 1, archived and labelled:**
- 2026-09-15 → 2026-11-04 is VALID as MECHANICS evidence, not performance: 35 tracked clean sessions 2026-09-17 → 11-04, plus the untracked 09-15/16 arrival sessions (F7).
- 2026-11-05 → reset day is **VOID**, including 2026-11-05 itself, which the tracker records as clean.
- The archive gets two small text objects written by the director: `README_VOID.txt` (below) and `MANIFEST_md5.txt` (rel path, bytes, md5 of every archived object).

`README_VOID.txt` text:

> ACCOUNT 2 (deploy candidate, prefix paper_state_offense_sso) — EPOCH 1 ARCHIVE, reset on <D> by the
> user's ruling of 2026-11-17. VALID as mechanics evidence only: 2026-09-15..2026-11-04 (35 tracked clean
> sessions 2026-09-17..2026-11-04; 09-15/16 untracked). VOID: 2026-11-05..<D> — MTUM 4:1 split
> ex 2026-11-05 unhandled; a spurious buy of 18 @ 65.26; the paper broker scaled all 23 shares to 92
> (true 38; 54 phantom shares ≈ $3.5k). The tracker summary's CAGR/Sharpe (0.20/1.65 on 2026-11-17;
> 0.24/1.87 on 2026-11-10) is the windfall, NOT the strategy — never quote it. `sleeve_equity` is BROKER
> equity (~$100k), never tier equity. exec_cost_ledger rows stay live (real fills; the 2026-11-05 MTUM
> row is a spurious order's real fill). Evidence: docs/Sources/runbook_account2_reset_2026-11-17.md.

**Epoch 2:**
- It starts at the first run after the reset (D+1, the seeding point: flat, non-canonical). The first CLEAN point is the arrival (D+2). The 60-clean-day gate restarts from zero [VERIFIED: `paper_trader/sleeve_tracker.py:54, 239-241`].
- Its basis is the CONTRIBUTED CAP at arrival: $11,166 under U2-default, $10,000 if re-based. The epoch's write-up states this as "$10,000 arrival + 2 simulated Rule-B months".

**No surface can show the windfall-era numbers as performance after this:**
- the tracker restarts;
- the mirror restarts its basis from epoch-2 fills only;
- `fleet_health` reads only the new heartbeat;
- the digest has no account-2 row (unwired, §1);
- the dashboard never read this prefix (§1).

The remaining places that quote CAGR 24 % / Sharpe 1.87 are `docs/State/health_check.md:62` and
`docs/State/CURRENT_STATE.md`, and both already label them the windfall [VERIFIED: the files]. After the
first artifact, append (do not rewrite) an epoch line to those two files and a TASK_LEDGER row.

---

## 6. Sequence and roles (item 6)

**Roles:**
- **USER:** needs the user's login, hands, or explicit word.
- **DIRECTOR:** can run it on the user's word given once for the whole procedure (U3).
- **READ:** read-only, no word needed.

**Operator variables** (run from a dated ops directory OUTSIDE the repo, e.g. `~/archondex_ops/acct2_reset_<D>/`):

```bash
P=archondex; R=us-east-1; B=archondex-results-407539788432
PFX=paper_state_offense_sso; D=<YYYY-MM-DD>; OPS=~/archondex_ops/acct2_reset_$D
ARCH=$PFX/archive_deploy_candidate_epoch1_$D; ASIDE=$PFX/reset_aside_$D
SCHED=archondex-paper-offense-sso-daily; JD=archondex-paper-offense-sso:21; Q=archondex-backtest-queue
RELS="data/paper_state/ledger.jsonl data/paper_state/orders.jsonl data/paper_state/recon.jsonl \
data/state/deploy_candidate_tracking.json data/state/fleet_mirror_slice.json data/state/paper_alerts.log \
data/state/paper_heartbeat.json data/state/price_basis_marks.json data/state/tax_lots.jsonl"
```

**Choose D:** a full regular session from 2026-11-18 onward. Avoid letting D+1/D+2 straddle Thanksgiving
(markets closed Thu 2026-11-26; early close Fri 11-27) [UNVERIFIED against `paper_trader/market_calendar.py`].
Work starts only after D's 09:50 ET run has finished, and steps 2–11 must be complete before D+1 09:40 ET.

| # | Who | Step (command of record) | Artifact that proves it | Rollback |
|---|---|---|---|---|
| U1–U3 | USER | One batched decision. **U1:** broker path B (default) or A. **U2:** keep contributions `start_date` 2026-09-11, so arrival at $11,166 (default); or re-base, so $10,000 (this needs a config change, an image build, and `redeploy_one_account.py` with image-only diff and a new pinned revision, all BEFORE step 11). **U3:** the word for steps 3–11 and 15. | the user's message | — |
| 0 | READ | `python -m scripts.fleet_health`; read account 2's heartbeat [VERIFIED command: `docs/Core/execution_manual.md:1342`] | account 2 still reads "reconcile 0/3; halted; UNEXPLAINED … FROZEN MTUM". **Anything else: STOP.** | — |
| 1 | READ | `aws s3 cp --recursive s3://$B/$PFX/ $OPS/snapshot/ --profile $P --region $R --no-progress`; `md5 -r` every file to `$OPS/snapshot_md5.txt`; save `aws scheduler get-schedule --name $SCHED … --output json > $OPS/sched_live.json` and `aws cloudwatch describe-alarms --alarm-name-prefix archondex-paper-offense-sso …` output | snapshot on disk; `sched_live.json` Target.Input names `archondex-paper-offense-sso:21` | — |
| 2 | READ | in-flight check: `aws batch list-jobs --job-queue $Q --filters name=JOB_NAME,values=paper-offense-sso-day --profile $P --region $R --query 'jobSummaryList[0:3].[status,createdAt,container.exitCode]' --output text` [VERIFIED syntax: run 2026-11-17; `--job-status` cannot be combined with `--filters`] | newest D job is SUCCEEDED or FAILED (not SUBMITTED/PENDING/RUNNABLE/STARTING/RUNNING); heartbeat `run_date` = D | — |
| 3 | DIRECTOR | **Disable the schedule** (fail-safe; preserve the pinned ARN): `python3` strips `Arn, CreationDate, LastModificationDate, Version` from `sched_live.json`, asserts `Target.Input` JobDefinition ends `:21`, and writes `sched_disable.json` (State=DISABLED) and `sched_enable.json` (State=ENABLED) with everything else verbatim [VERIFIED pattern: `scripts/redeploy_one_account.py:94-124`; `docs/Core/execution_manual.md:1114-1124`]. Then `aws scheduler update-schedule --cli-input-json file://$OPS/sched_disable.json --profile $P --region $R` | readback `get-schedule --query '[State,Target.Input]'`: `DISABLED` and an Input byte-identical to `sched_live.json` | `update-schedule --cli-input-json file://$OPS/sched_enable.json`; readback |
| 4 | DIRECTOR | (B) **Liquidation DRY RUN** on account 2's own jobdef. Body in §6.1 with `EXECUTE=False`. `python3 -c "import json;print(json.dumps({'command':['python','-c',open('$OPS/reset_a2.py').read()]}))" > $OPS/ov.json`; `aws batch submit-job --job-name reset-a2-dryrun-$D --job-queue $Q --job-definition $JD --container-overrides file://$OPS/ov.json --profile $P --region $R` [VERIFIED pattern: `docs/Core/execution_manual.md:1013-1035`] | log (`/aws/batch/job`, stream prefix `paper-offense-sso` [VERIFIED: jobdef :21 logConfiguration]): `positions_before={"MTUM": 92, "SGOV": 6, "VOO": 12}`, `open_orders=0`, `market_open=True`, three `DRY-RUN would sell` lines, exit 0. **A REFUSED line or any other exit: STOP.** | none needed (read-only to the broker) |
| 5 | DIRECTOR | (B) **Liquidation EXECUTE**: the same body with `EXECUTE=True`, job name `reset-a2-execute-$D`; in regular hours, ≥ 10:00 ET | log: three `submitted` lines with coids `reset-a2-<D>-<TICKER>-sell` | none to the broker state. A partial fill or refusal leaves the account halted: a safe resting state. **Do not re-buy.** Re-run step 6, then decide. |
| 4A–5A | USER | (A instead of 4–5) Open the new paper account; generate keys; paste them into `archondex/alpaca-paper-offense-sso` in the AWS console. **Do not delete or revoke the old account yet** unless the cap forces it (then the deletion IS the point of no return) | the secret's `LastChangedDate` moves (`describe-secret`, metadata only) | restore the old pair only if the old account and its keys still exist |
| 6 | DIRECTOR | **FLAT-CHECK** job (execution manual's body, verbatim) on `$JD` [VERIFIED: `docs/Core/execution_manual.md:1020-1033`] | `FLAT=True`, `n_open_orders 0`; equity ≈ $103.5k (B) or EXACTLY the new starting balance (A). **Anything else: STOP; schedule stays disabled.** | — |
| 7 | DIRECTOR | **Archive copy + verify + move aside**, per key in `$RELS` (§6.2) | for every key: archive md5 = live md5; live key absent; aside key present | `aws s3 mv s3://$B/$ASIDE/<rel> s3://$B/$PFX/<rel>` per key (only valid BEFORE any run writes those keys) |
| 8 | DIRECTOR | **Snapshot** `exec_cost_ledger.jsonl` (copy only): `aws s3 cp s3://$B/$PFX/data/state/exec_cost_ledger.jsonl s3://$B/$ARCH/data/state/exec_cost_ledger.jsonl` | md5 match | — |
| 9 | DIRECTOR | **Label:** write `README_VOID.txt` (§5 text, `<D>` filled) and `MANIFEST_md5.txt` locally, then `aws s3 cp $OPS/README_VOID.txt s3://$B/$ARCH/README_VOID.txt` (same for the manifest) | both objects listed | — |
| 10 | READ | `aws s3 ls --recursive s3://$B/$PFX/` | live keys = ONLY `data/state/exec_cost_ledger.jsonl`, plus `archive_offense_2026-09-11/`, `$ARCH/` and `$ASIDE/` | step 7 rollback |
| 11 | DIRECTOR | **Re-enable:** `aws scheduler update-schedule --cli-input-json file://$OPS/sched_enable.json …`; readback; `python scripts/diff_live_paper_infra.py` [VERIFIED: `docs/Core/execution_manual.md:1010, 1064`] | `ENABLED`; Input byte-identical to `sched_live.json` (`…offense-sso:21`); drift gate prints `No drift.` | `sched_disable.json` |
| 12 | READ | **D+1 09:50 ET firing: the SEEDING run** (§7 artifact 1) | §7 | if any freeze or UNEXPLAINED appears: re-disable (step 3), STOP, review. **Do not ack.** |
| 13 | READ | **D+2 09:50 ET firing: the ARRIVAL** (§7 artifact 2) | §7 | as row 12 |
| 14 | READ | the non-canonical alarm goes to OK (SNS OK mail); `fleet_health` has no account-2 problem | `describe-alarms` StateValue `OK` | — |
| 15 | DIRECTOR (optional) | →ALARM drill: `aws cloudwatch set-alarm-state --alarm-name archondex-paper-offense-sso-non-canonical --state-value ALARM --state-reason "arming drill <D+2>" …` | SNS ALARM mail received; the alarm returns to OK at its next evaluation | the alarm self-corrects at the next evaluation [UNVERIFIED timing] |
| 16 | DIRECTOR | docs: append the epoch line to `CURRENT_STATE.md` and `health_check.md:62-63` (account-2 recovery DONE on its artifact), plus a `TASK_LEDGER.md` row; add every NEW CLI used to `docs/Core/execution_manual.md` in the same turn | the commit | — |
| 17 | USER (A only) | revoke the OLD key pair; decide on the old account (delete under the cap) | — | — |

**NEW CLI, not in the execution manual** ([NN-NO-GUESS-CLI]; add each in the turn it is first executed):
`aws s3 mv`, `aws s3api head-object`, `aws logs get-log-events`, `aws cloudwatch set-alarm-state`,
`aws batch list-jobs --filters`. Only the last was run in this session, and its syntax is VERIFIED.
**`aws s3 mv` needs `s3:DeleteObject` for the CLI user** [UNVERIFIED today]. The T-350 transition ran
`aws s3 rm` on this prefix on 2026-09-11 [VERIFIED: `scripts/transition_acct2_to_deploy_candidate_t350.py:132`;
the originals are absent from the 2026-11-17 listing]. **If the move is denied: STOP.** The archive copies
exist, and nothing has been removed.

### 6.1 Liquidation body (`$OPS/reset_a2.py`; runs ONLY inside account 2's container)

```python
import inspect, json, sys
from paper_trader.paper_client import AlpacaPaperClient
D = "<YYYY-MM-DD>"; EXECUTE = False          # the execute job changes ONLY this flag
EXPECT = {"MTUM": 92, "SGOV": 6, "VOO": 12}  # re-read from step 0/6 on the day; never from the ledger
c = AlpacaPaperClient()
clock = c._client.get_clock()                # read-only; [UNVERIFIED: alpaca-py Clock.is_open]
pos = {p["symbol"]: int(p["qty"]) for p in c.list_positions()}
TERM = {"filled", "canceled", "expired", "rejected", "done_for_day", "replaced"}
open_o = [o for o in c.list_orders() if str(o.get("status", "")).lower() not in TERM]
print("RESET-A2 positions_before=" + json.dumps(pos, sort_keys=True))
print("RESET-A2 equity_before=%s open_orders=%d market_open=%s"
      % (c.get_account().get("equity"), len(open_o), clock.is_open))
if pos != EXPECT or open_o or not clock.is_open:
    print("RESET-A2 REFUSED — broker state/market not as expected; stop and review"); sys.exit(70)
for t, q in sorted(pos.items()):
    kw = dict(client_order_id=f"reset-a2-{D}-{t}-sell", symbol=t, qty=q, side="sell", tif="day")
    inspect.signature(c.submit_order).bind(**kw)
    if EXECUTE:
        print("RESET-A2 submitted " + json.dumps(c.submit_order(**kw), default=str)[:300])
    else:
        print(f"RESET-A2 DRY-RUN would sell {q} {t} (signature binds)")
```

Sell exactly what the BROKER reports, never what the ledger says. The coid prefix `reset-a2-` cannot
collide with the stream token `deploycand-a2` [VERIFIED: `scripts/run_paper_cloud_day.py:70`].
`submit_order(client_order_id, symbol, qty, side, tif)` is the real signature [VERIFIED:
`paper_trader/paper_client.py:206-217`].

### 6.2 Archive loop (step 7)

```bash
for REL in $RELS; do
  aws s3 cp "s3://$B/$PFX/$REL" "s3://$B/$ARCH/$REL" --profile $P --region $R --no-progress || { echo "STOP copy $REL"; break; }
  L=$(aws s3 cp "s3://$B/$PFX/$REL" - --profile $P --region $R | md5)
  A=$(aws s3 cp "s3://$B/$ARCH/$REL" - --profile $P --region $R | md5)
  [ "$L" = "$A" ] || { echo "STOP md5 mismatch $REL"; break; }
  aws s3 mv "s3://$B/$PFX/$REL" "s3://$B/$ASIDE/$REL" --profile $P --region $R --no-progress || { echo "STOP mv $REL"; break; }
  echo "$REL $L" >> $OPS/MANIFEST_md5.txt
done
```

Each key is copied to the dated archive prefix, proven byte-identical, and only then moved aside. Nothing
is deleted ([NN-ARCHIVE]). `aws s3 cp <s3> -` is the codebase's own read form [VERIFIED:
`scripts/ledger_backup.py:136`]. A `STOP` leaves every untouched key live. Re-run from the failed key
after review.

---

## 7. First artifacts (`[NN-FIRST-ARTIFACT]` — the scheduled firings, never a manual submit)

The verification is the NEXT SCHEDULED FIRING [VERIFIED: `docs/Core/execution_manual.md:1067-1068`].
Read `s3://$B/$PFX/data/state/paper_heartbeat.json`, the Batch job and `python -m scripts.fleet_health`.

**Artifact 1 — D+1 09:50 ET (`paper-offense-sso-day`), the seeding run.** Expected:
- the Batch job **FAILED with exit 70**, by design;
- `last_run.run_date` = D+1, `canonical` false;
- `reconcile_clean_cycles` 3 of 3, `halted` false, `account_explained` true, `submitted` 0, `fills` 0;
- `reason` contains "seeding price-basis marks (first run)" and NOT "UNEXPLAINED", "FROZEN" or "drift";
- `corporate_actions`: `feed.available` true; `frozen` {} and `frozen_persisted` {}; `seeding` ⊇ [MTUM, SGOV, VOO]; `marks_age_sessions` 0; `stand_down` true; `refused_orders` = the arrival buys;
- new objects: `price_basis_marks.json` (`account` "paper_state_offense_sso", `seed_sessions` 0); `ledger.jsonl` with ONE `init` row whose cash equals broker cash and `positions` {}; tracker with 1 point.

The non-canonical alarm stays ALARM and `fleet_health` names account 2 non-canonical (seeding). Both are
expected; announce them.

**Artifact 2 — D+2 09:50 ET, the arrival.** Expected:
- the Batch job **SUCCEEDED (exit 0)**;
- `canonical` true, `reconcile_clean_cycles` 3/3, `halted` false, `account_explained` true;
- `submitted` 3 (VOO, MTUM, SGOV buys) with `fills` 3;
- `corporate_actions`: `frozen` {}, `seeding` [], `stand_down` false, `marks_age_sessions` 1, `refused_orders` [];
- `fleet_mirror_slice.json`: `tier_equity` ≈ the cap ($11,166 or $10,000), positions ≈ 13 VOO / 25 MTUM / ~6 SGOV at current prices (the share counts are an estimate);
- `tax_lots.jsonl` holds exactly 3 buy lots; the tracker has 2 points, the second `exec.canonical` true and `order_errors` 0;
- the job's stdout prints the `DEPLOY-CAND contributions: +$… ` line naming the cap actually used.

Then artifact 3: the non-canonical alarm moves to OK (§4).

---

## 8. Open risks (item 7)

- **R1 — seeding from the windfall.** Under B the new ledger's starting cash includes the ~$3.5k windfall (as cash). This is harmless to sizing while the cap is below broker equity (§2). It becomes material at any tier of roughly $100k or more on this account: use a new paper account for such a rehearsal.
- **R2 — the scheduler firing mid-reset.** A run between step 5 and step 10 would PUSH a fresh ledger, tracker, marks and heartbeat into the half-archived prefix (`push()` uploads whatever exists) [VERIFIED: `paper_trader/cloud_state.py:330-340`].
  - Steps 3/11 close the window. The disable is done the July-safe way: GET, change State only, `--cli-input-json`, a byte-identical Target readback with the `:21` pin, and the drift gate.
  - Not chosen: `StartDate`. It auto-resumes even if the reset stalls; DISABLED fails safe.
  - A DISABLED schedule left across 09:50 ET is a silent stop. The silent-stop alarm is configured to page but its weekend behaviour is [UNVERIFIED] (§4), so steps 11–12 are explicit.
- **R3 — the wrong account's keys.**
  - Laptop `.env` = account 1 (F8): never run a broker command locally.
  - Under A, a mis-pasted pair is caught by the step-6 equity identity check.
  - Keys never pass through chat.
- **R4 — irreversible deletion.** Under A with the cap, deleting old account 2 is the only non-recoverable act in this runbook. Do it last, only after artifact 2, and only if a new account is truly needed.
- **R5 — A at $10,000 breaks Rule-B silently** (§3). Not a reset problem; a design one.
- **R6 — seeding is weakly witnessed.** D+1 and D+2 have no price reference, or only a one-day-old one [VERIFIED: `paper_trader/corporate_actions.py:39-45`]. A split in VOO, MTUM or SGOV unreported by the feed just before D+1 would be invisible. Check the corporate-action calendar for those three for D..D+2 before choosing D [UNVERIFIED: none known].
- **R7 — the paper broker's own split handling is defective.** It multiplied the 18 shares bought ON the ex-date at the post-split price (true 38, broker 92) [VERIFIED: journal + broker positions]. Epoch 2 will meet the next split with the gate in force (it froze MTUM correctly on 2026-11-16 [VERIFIED: `price_basis_marks.json` journal]), but the broker's share counts on split days cannot be trusted.
- **R8 — the mirror's base cap (F9).** Proposed fix, propose-first and NOT part of this reset: pass `deploy_cap if deploy_cap is not None else args.sleeve_notional_cap` as `tier_cap` at `scripts/run_paper_cloud_day.py:1592`. Also add the missing `json` import that nulls `day_change` [VERIFIED: `docs/State/health_check.md:63`]. It belongs on a branch with its own lock; it changes a display surface on the live path.
- **R9 — the liquidation is invisible to the wash guard.** The sales go outside the OrderManager and the lot ledger is archived. VOO was bought at 698.04 and is about 680 now, a realized loss [VERIFIED: journal; mirror price], so a VOO re-buy on D+2 inside 61 days would be refusable in a guarded real account. This is a paper-reset artifact with no real-money analogue; state it in the epoch-2 record. Option A has no sale.
- **R10 — dividends.** Alpaca paper does not simulate dividends [VERIFIED: Alpaca doc], so SGOV, whose return is almost entirely distributions, earns about 0 in the paper record in both epochs. Read the cash leg accordingly.
- **R11 — no versioning net.** A wrong `mv` is recoverable only from the archive copy, hence verify-before-move (§6.2) [VERIFIED: `scripts/ledger_backup.py:22`].
- **R12 — the new prefix alternative was rejected.** Pointing the jobdef at a fresh prefix (the account-3 precedent [VERIFIED: `scripts/provision_paper_fleet.py:76-80`]) would move no S3 object. But it changes jobdef env (non-image diff: `redeploy_one_account.py` refuses), needs a job-role grant [VERIFIED: `docs/Core/execution_manual.md:1009`], needs a `fleet_health.py` mapping edit, and runs into R3-2 (no re-stamp tool) [VERIFIED: `docs/State/health_check.md:63`]. That is far more live-path change than an in-place archive.

---

## 9. Every [UNVERIFIED] item, in one place

1. Whether "Open New Paper Account" accepts a custom starting balance, and whether any API exists for it (§3).
2. Whether Alpaca itself limits paper accounts to 3. The cap is the user's, per a code comment (F2).
3. Whether exporting a deleted paper account's activity is possible (§3 A).
4. That an empty version stage in `valueFrom` resolves to AWSCURRENT, so a secret change needs no new jobdef revision (§3).
5. Whether the CLI user holds `secretsmanager:PutSecretValue` and `s3:DeleteObject` today (`iam:SimulatePrincipalPolicy` is denied) (§3, §6).
6. The exact time the non-canonical alarm reaches OK after D+2, and when a `set-alarm-state` drill self-corrects (§4, step 15).
7. Whether the silent-stop alarm pages on one missed firing, given that it stayed OK across two weekends (§4).
8. `alpaca-py` `TradingClient.get_clock().is_open` as used in §6.1 (not executed).
9. Syntax of `aws s3 mv`, `aws s3api head-object`, `aws logs get-log-events`, `aws cloudwatch set-alarm-state` as written (not executed).
10. The Thanksgiving dates against `paper_trader/market_calendar.py`, and any corporate actions in VOO/MTUM/SGOV for D..D+2 (§6, R6).
11. The estimated arrival share counts in §7 artifact 2 (13 / 25 / ~6), which depend on prices on D+2.
