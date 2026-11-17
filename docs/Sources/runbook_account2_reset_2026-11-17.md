# ACCOUNT 2 RESET RUNBOOK — PROPOSED, REVISION 2 (risk lens, 2026-11-17; propose-first)

**Status:** PROPOSED. Nothing in this document has been run. Every command below is text for a later,
explicitly approved session. This revision changed no state: no S3 or AWS writes, no broker calls, no
`.env` read. The evidence comes from four kinds of source:
- read-only AWS reads (`s3 ls`, `s3 cp` to a scratch copy, `describe-*`, `get-*`, `head-object`, `list-jobs`);
- the code at `fc7254b`, unchanged on the paper path through main `f13a1c5` [VERIFIED: `git log fc7254b..main -- scripts/run_paper_cloud_day.py paper_trader config/deploy_candidate.json` is empty];
- Alpaca's public docs, re-read 2026-11-17;
- local simulations, described in the next bullet list.

**The simulations.** All were run locally with no network and no broker:
- the independent reviewer's driver `/tmp/runbook_review_fresh/sim_reset.py`, which runs the REAL `run_paper_cloud_day.main()` for D+1/D+2/D+3 from an empty state against a fake flat broker at the 2026-11-16 closes. It was re-run by me (output matches `/tmp/runbook_review_fresh/sim_out.txt`);
- three variants of it: the $10,000 re-base, and option A at $10,000 with and without the re-base;
- fake-S3 and fake-broker tests of the §7 scripts.

**The ruling this executes:** the user ruled 2026-11-17 that account 2 is RESET, not repaired by a
journaled basis adjustment, as recorded at `docs/State/CURRENT_STATE.md:177` on main: "The broker's own
balance is not a valid seed … so the reset restarts at a clean $10,000 tier with a new record epoch".

**Review verdict (2026-11-17):**
- Option B: READY WITH REQUIRED FIXES (findings 2, 3, 4, 5). If U2 = re-base, B is NOT READY until finding 1 is fixed.
- Option A: NOT READY.

Revision 2 fixes every finding. The map is in §11.

**Tags.** Each claim carries `[VERIFIED: source]` (a file:line, an S3 key or AWS response read on
2026-11-17, a public doc URL read on 2026-11-17, or a named simulation) or `[UNVERIFIED]`.

**Naming.** Account 2 runs `deploy_candidate`, not `offense_sso`: the jobdef env has
`ARCHONDEX_PAPER_STRATEGY=deploy_candidate` [VERIFIED: `describe-job-definitions` :21]. The
`offense-sso` / `offense_sso` names survive only as identifiers: the prefix, the jobdef family, the
alarms, the metric dimension and the secret. They were kept to avoid an IAM rename [VERIFIED:
`scripts/provision_paper_fleet.py:47-50`].

---

## 0. What the user must rule — the departures, stated plainly (finding 5)

The director presents these choices to the user. This section states what each choice does; it does not
recommend.

**U1 — the broker path.**

- **B, liquidate in place.** One approved job sells the 92 MTUM / 6 SGOV / 12 VOO on account 2's own
  Alpaca paper account. Same account id, keys, secret, jobdef and IAM.
  - **Departure from the ruling:** under B the epoch-2 ledger IS seeded from the broker's cash, and that
    cash includes the realized windfall. The run creates the ledger with
    `starting_cash = broker cash` [VERIFIED: `scripts/run_paper_cloud_day.py:592-593`;
    `paper_trader/ledger_store.py:83-87`]. The simulated D+1 init row is `cash 103514.78, positions {}`
    [VERIFIED: re-run of the reviewer's simulation].
  - The windfall is **fenced off from sizing by the cap, not removed**. Sizing is
    `min(broker equity, contributed cap)` [VERIFIED: `scripts/run_paper_cloud_day.py:165-166, 941-942`],
    so the windfall never sizes an order. It does stay in three places for the life of this account: the
    ledger's cash, the Alpaca balance, and the tracker's starting `sleeve_equity`.
  - **The user is asked to rule:** does "fenced off by the cap" satisfy "the broker's own balance is not
    a valid seed"? If it does not, B cannot meet the ruling and only A can.
- **A, a new Alpaca paper account.** This removes the windfall from the broker.
  - **Departures:**
    - (a) Under the user's 3-account cap, old account 2 probably has to be DELETED first. That is
      irreversible, and it loses the broker-side history (§4).
    - (b) At Alpaca's $100k default the broker still shows about $100k, not $10,000.
    - (c) At a $10,000 starting balance, the Rule-B contribution rehearsal breaks ON ARRIVAL DAY: the
      cap at arrival is already $11,166 > $10,000 equity, so the +$1,166 is never deployed (finding 14;
      §4).
  - Whether a new account's balance can even be chosen is [UNVERIFIED].

**U2 — the tier at arrival.**

- **Keep `start_date` 2026-09-11.** The arrival is sized at **$11,166** = $10,000 + 2 Rule-B months of
  $583 [VERIFIED: `config/deploy_candidate.json` `contributions`;
  `paper_trader/deploy_candidate_constructor.py:271-316`; simulated arrival 13 VOO / 25 MTUM / 6 SGOV,
  $11,089.61 invested].
  - **Departure:** the ruling says "a clean $10,000 tier". This is $11,166, and the next +$583 lands on
    2026-12-11.
- **Re-base `start_date` to the arrival date.** The arrival is exactly **$10,000**: the simulated run
  prints `contributions: +$0 = 0 whole month(s)` and buys 12 VOO / 22 MTUM / 3 SGOV, $9,910.48
  [VERIFIED: re-base variant simulation].
  - The cost is a live-path change before day D (step 0.5): a config commit, review and merge, a new
    paper image, and a surgical redeploy to a new jobdef revision.

**U3 — the word** for the director steps in §7.

### 0.1 What the user WILL see on each surface (the question was whether the reset makes "those numbers show correctly")

D+1 is the first scheduled run after the reset (the seeding run), D+2 the arrival, and D+3 the first
settled day.

| Surface | B, liquidate in place | A at the $100k default | A at $10,000 |
|---|---|---|---|
| **Alpaca dashboard balance** | about **$103.5k**, all cash, then the tier book. Never $10,000. The windfall stays as cash. | **$100,000**, then the tier book | **$10,000**, then the tier book; the +$583/mo is never deployed |
| **Tracker `sleeve_equity`** (`deploy_candidate_tracking.json`; BROKER equity by design [VERIFIED: `paper_trader/fleet_mirror.py:78-81`]) | starts about **103,514.78** on D+1 [VERIFIED: simulation]; tier P&L diluted about 10× | starts **100,000** | starts **10,000**: tier-honest, but the contributions break |
| **Fleet-mirror `tier_equity` / `total_change`** (the tier view) | D+1: **10,000.00 / 0** (all tier cash). D+2: **0.00 / −10,000** (defect, finding 2). From D+3: **≈ 11,089.61 / ≈ +1,089.61** under U2-default (about $76 of residual cash is dropped); **≈ 10,000 / ≈ 0** under re-base | same as B | D+2: **≈ 89.52 / ≈ −9,910**; from D+3 **≈ 10,000 / ≈ 0**, under either U2 [VERIFIED: simulations] |
| **Digest** | no account-2 row: the row builder is unwired [VERIFIED: `intelligence/analyst/performance_digest.py:292-324`, no production caller] | same | same |
| **`fleet_health`** | account-2 line: D+1 NON-CANONICAL (seeding); from D+2 nothing about account 2. The overall verdict stays **NOT HEALTHY** because of three book problems (§6) | same | same |

**The tier-honest surface is the mirror, from D+3 onward,** and then only with two caveats:
- `total_change` is measured against the BASE cap of $10,000, so it includes contributions (F9);
- clipped residual cash is dropped.

The tracker is tier-honest only under A at $10,000. The Alpaca balance is never the tier under B.

---

## 1. Findings that change the plan

| # | Finding | Consequence |
|---|---|---|
| F1 | **Alpaca's paper page contradicts itself about "reset".** The section titled "Reset Your Paper Trading Account" says: "We've updated the dashboard to allow you to create and delete paper accounts, rather than resetting them. … Don't forget to generate new API keys for any newly created account." Two older lines on the same page still say: "You can reset the paper trading account at any time later with arbitrary amount as you configure." and "You cannot change the account balance after it is created, unless you reset it." [VERIFIED: https://docs.alpaca.markets/us/docs/paper-trading.md lines 61, 65-73, 80, re-read 2026-11-17] | Whether an in-place reset that sets the balance still exists anywhere is [UNVERIFIED]. The dedicated section describes only create (new account number, new keys) and delete. Plan as if an existing account's balance cannot be set. |
| F2 | **The user has a 3-paper-account cap** and all three slots are in use [VERIFIED: `scripts/provision_paper_fleet.py:86-89`; `docs/Core/execution_manual.md:1084`]. Whether Alpaca enforces it is [UNVERIFIED]. | Option A probably requires deleting old account 2 first, which is irreversible. |
| F3 | **The broker holds about $103.5k, not $13.5k.** That is 12 VOO + 92 MTUM + 6 SGOV = $14,811.92 at the 11-16 closes, plus about $88.7k cash [VERIFIED: S3 tracker last point `sleeve_equity` 103,514.78; slice positions]. The $10k tier is the notional cap [VERIFIED: `scripts/transition_acct2_to_deploy_candidate_t350.py:21-24`]. | A clean TIER restart is possible in place: the windfall is fenced off by the cap, not removed (§0 U1). |
| F4 | **The cap at arrival is $11,166** unless re-based (§0 U2). | — |
| F5 | **A state-only reset on a non-flat broker re-creates the halt.** With an empty journal the broker's positions are UNEXPLAINED and never adopted [VERIFIED: `paper_trader/held_reconcile.py:55-70, 97-119`]. | The broker must be flat (B) or new (A) before the first run on archived state. |
| F6 | **D+1 is a seeding stand-down by design:** exit 70, nothing staged, and the arrival on D+2 [VERIFIED: `paper_trader/corporate_actions.py:725-741, 953-967`; `scripts/run_paper_cloud_day.py:1005-1012, 1774-1777`; simulation D+1 rc=70, D+2 rc=0]. | Day 1 pages as non-canonical, and that is expected. |
| F7 | **The tracker's "36 clean sessions" includes the defect day.** The tracker recorded 2026-11-05 as `canonical: True, order_errors: 0`. Only 35 tracked points fall on or before 11-04 [VERIFIED: tracker read; `paper_trader/sleeve_tracker.py:219`]. The ruling text at `docs/State/CURRENT_STATE.md:177` on main says 36. | Epoch 1 is valid for 35 tracked sessions (2026-09-17 → 11-04), plus the untracked 09-15/16 arrival sessions [VERIFIED: `docs/Archive/state_history/CURRENT_STATE_full_history_to_2026_09_17.md:13`]. Append a correction to the state line; do not rewrite it. |
| F8 | **The laptop `.env` holds ACCOUNT 1's keys:** there is one `ALPACA_API_KEY` name [VERIFIED: names-only read, 2026-11-17]; it is written to `archondex/alpaca-paper` [VERIFIED: `scripts/deploy_paper_cloud_trigger.sh:37, 56-75`]; and the client loads `.env` [VERIFIED: `paper_trader/paper_client.py:170-177`]. | Any broker command run locally hits account 1. Every broker action here goes through account 2's own jobdef. |
| F9 | **Corrected (finding 2).** The mirror is passed the BASE cap of $10,000, not the contributed cap [VERIFIED: `scripts/run_paper_cloud_day.py:1592` vs `:861-862, 941-942`]. So from D+3 its `total_change` reads about **+$1,089.61** under U2-default: the deployed contributions minus about $76 of residual tier cash that is clipped to 0 [VERIFIED: `paper_trader/fleet_mirror.py:113-120`; simulation D+3]. It is NOT the "+$1,166 at arrival" that revision 1 stated. On arrival day it reads −$10,000 (F10). | This is not performance. The director is adding it to T-401. |
| F10 | **The arrival-day mirror is wrong (finding 2).** The mirror takes `positions=broker_positions` [VERIFIED: `scripts/run_paper_cloud_day.py:1585`], captured once BEFORE trading [VERIFIED: `:621`], but takes its basis from the POST-fill journal [VERIFIED: `:1568-1574`]. On D+2 there are no position rows, and `cash = max(10000 − basis, 0)`, so `tier_equity` = 0.00 and `total_change` = −10,000 under U2-default, or about 89.52 / about −9,910 under re-base [VERIFIED: simulations]. It corrects on D+3. | Artifact 2 reads positions from the ledger, journal and lots (§8). The director is adding the stale-positions defect to T-401. The arrival-day mirror has never been observed live: the 09-15 arrival predates both the mirror and the corporate-action gate (deployed 2026-11-14) [VERIFIED: `docs/State/health_check.md:63`; `docs/Archive/state_history/CURRENT_STATE_full_history_to_2026_09_17.md:13`]. |
| F11 | **The split feed asks nothing on D+1 or D+2 (finding 6).** Nothing is held or journaled, so `tickers == []` and `reason "no tickers to ask about"` [VERIFIED: `paper_trader/corporate_actions.py:256-260`; simulation D+1/D+2]. The feed first asks on D+3 (`tickers [MTUM, SGOV, VOO]`) [VERIFIED: simulation D+3]. | The arrival buys go through with no feed query. Only the price-basis guard (seeded D+1) and the manual calendar check (P2) stand. |
| F12 | **The S3 objects are SSE-S3 single-part, and versioning is off for them.** `head-object` returns ETag = md5 and VersionId null [VERIFIED: `head-object` on `…/price_basis_marks.json`, ETag `3671af88…` = md5 of the snapshot copy; `ServerSideEncryption AES256`]. `GetBucketVersioning` is denied to the CLI user [VERIFIED: `scripts/ledger_backup.py:22`]. | The protections are the step-1 local snapshot plus the byte-verified archive copy. There is no versioning safety net. |

---

## 2. Every piece of account-2 state (item 1)

Bucket `archondex-results-407539788432` [VERIFIED: `scripts/ledger_backup.py:39`; jobdef :21 env].
Prefix `paper_state_offense_sso` [VERIFIED: jobdef :21 env]. The listing below is as of 2026-11-17, all
written by the 14:51 UTC run [VERIFIED: `aws s3 ls --recursive`].

| Key under the prefix | Bytes | Written by | Read by | Reset action |
|---|---|---|---|---|
| `data/paper_state/ledger.jsonl` | 41,602 | `LedgerStore` snapshots; adopt [VERIFIED: `scripts/run_paper_cloud_day.py:592-593`; `paper_trader/held_reconcile.py:117-118`] | the next run [VERIFIED: `paper_trader/ledger_store.py:77-87`]; the gate window [VERIFIED: `scripts/run_paper_cloud_day.py:639-640`] | **ARCHIVE + MOVE ASIDE.** It holds the mixed-basis 23 MTUM (seq 151) [VERIFIED: object read]. |
| `data/paper_state/orders.jsonl` | 33,463 | `OrderManager` [VERIFIED: `:585-588`] | reconcile, split-gate fill dating, mirror basis [VERIFIED: `paper_trader/held_reconcile.py:28-52`; `paper_trader/corporate_actions.py:778-799`; `scripts/run_paper_cloud_day.py:1568-1574`] | **ARCHIVE + MOVE ASIDE.** 27 orders: 12 filled, 15 STAGED and never submitted [VERIFIED: object read]. |
| `data/paper_state/recon.jsonl` | 41,400 | `PaperScheduler` [VERIFIED: `:596-597`] | nothing reads it back [VERIFIED: `paper_trader/clock_census.py:523`] | **ARCHIVE + MOVE ASIDE.** |
| `data/state/deploy_candidate_tracking.json` | 24,524 | `SleeveTracker` [VERIFIED: `:1479-1495`] | the next run; the summary covers ALL points [VERIFIED: `paper_trader/sleeve_tracker.py:265-283`] | **ARCHIVE + MOVE ASIDE + LABEL VOID.** The summary shows CAGR 0.1983 / Sharpe 1.651, which is the windfall. |
| `data/state/fleet_mirror_slice.json` | 650 | mirror block [VERIFIED: `:1563-1598`] | the next run as `prev_tier_equity`; `day_change` is always null because of a swallowed NameError (no `import json`) [VERIFIED: `:1575-1581`]. The serving layer is not live. | **ARCHIVE + MOVE ASIDE.** `tier_equity` 14,811.92 includes the windfall. Its `positions` are the step-1 source of EXPECT (§7). |
| `data/state/paper_alerts.log` | 14,166 | `PaperHeartbeat._notify` (`DEFAULT_ALERT_LOG`) [VERIFIED: `paper_trader/heartbeat.py:33`] | no gate | **ARCHIVE + MOVE ASIDE.** |
| `data/state/paper_heartbeat.json` | 5,375 | `PaperHeartbeat` (`DEFAULT_STATUS`) [VERIFIED: `paper_trader/heartbeat.py:32`; `scripts/run_paper_cloud_day.py:976-996`] | `scripts/fleet_health.py` [VERIFIED: `:26-30, 135-141`]; `hb.check()` reads only today's run [VERIFIED: `paper_trader/heartbeat.py:344-371`] | **ARCHIVE + MOVE ASIDE.** Account 2 reads UNKNOWN until D+1's run (§8 step-13 branch). |
| `data/state/price_basis_marks.json` | 1,154 | gate save [VERIFIED: `paper_trader/corporate_actions.py:553-570, 1002-1007`] | the next run's gate [VERIFIED: `scripts/run_paper_cloud_day.py:638-653`] | **ARCHIVE + MOVE ASIDE.** It holds the ack-only MTUM `ledger` freeze [VERIFIED: object read; `paper_trader/corporate_actions.py:453, 695`]. |
| `data/state/tax_lots.jsonl` | 3,935 | wash guard, ENFORCING on `deploy_candidate` [VERIFIED: `scripts/run_paper_cloud_day.py:74, 536-547`] | the guard [VERIFIED: `engines/engine_b_risk/cross_account_wash_guard.py:109-129`]; a missing file is an empty ledger [VERIFIED: `:117-119`] | **ARCHIVE + MOVE ASIDE.** This is Engine B's INPUT; no Engine B code changes. |
| `data/state/exec_cost_ledger.jsonl` | 4,006 | `ExecCostLedger` (append-only) [VERIFIED: `:1610-1626`] | the heartbeat aggregate; T-301b | **SNAPSHOT-COPY, KEEP LIVE.** The rows carry `trade_date` and `account: offense-sso` but **no epoch field** [VERIFIED: object read], so the live file mixes epochs. Epoch-2 rows are those with `trade_date` ≥ the arrival date. The 2026-11-05 MTUM row is a real fill of a spurious order. |
| `archive_offense_2026-09-11/*` (6) | — | T-350 [VERIFIED: `scripts/transition_acct2_to_deploy_candidate_t350.py:119-134`] | nobody | **LEAVE.** |
| `data/state/TRADING_HALT` | absent | operator [VERIFIED: `paper_trader/trading_halt.py:51`] | `check_trading_halt` | **Leave absent** [VERIFIED: listing; jobdef :21 env has no kill switch]. |

**Outside the prefix:**
- the alarms `archondex-paper-offense-sso-non-canonical` / `…-silent-stop`;
- the schedule `archondex-paper-offense-sso-daily`;
- the jobdef `archondex-paper-offense-sso` (live :21, image `paper-sha-716ca04`);
- the secret `archondex/alpaca-paper-offense-sso`;
- [VERIFIED for all four: read-only `describe-alarms`, `get-schedule`, `describe-job-definitions`, `describe-secret` metadata];
- the dashboard reads the local `data/paper_state/` only [VERIFIED: `cockpit/dashboard_v2/utils/paper_loader.py:41`];
- the account-2 attribution book `book_momentum_satellite.json` lives under ACCOUNT 1's prefix and is not touched by this reset (§6).

**How the runner treats missing keys:** a missing key is benign; only a denial fails [VERIFIED:
`paper_trader/cloud_state.py:295-304`]. `push()` uploads only files that exist and never deletes
[VERIFIED: `:330-340`].

---

## 3. How the runner starts from nothing (item 2)

From an empty prefix, on a flat broker [VERIFIED by simulation; code cites as listed]:

1. **Pull:** all keys are missing, which reads as a clean start [VERIFIED: `scripts/run_paper_cloud_day.py:433-445`].
2. **Ledger:** one `init` row, with `cash = broker cash` and `positions {}` [VERIFIED: `:592-593`; `paper_trader/ledger_store.py:83-87`]. Positions enter the ledger only by explained adoption [VERIFIED: `paper_trader/held_reconcile.py:97-119`].
3. **Tier:**
   - the entrypoint passes `--sleeve-notional-cap 10000` [VERIFIED: `scripts/paper_cloud_entrypoint.sh:32`];
   - `deploy_candidate` refuses to run without it [VERIFIED: `scripts/run_paper_cloud_day.py:855-860`];
   - `deploy_cap = contributed_cap(10000, today)` [VERIFIED: `:861-862`];
   - sizing is `min(equity, deploy_cap)` [VERIFIED: `:165-166, 941-942`].
4. **Split feed:** on D+1 and D+2 it asks about no tickers (F11). On D+3 it asks about [MTUM, SGOV, VOO]. MTUM's 11-05 split falls outside any window that starts after 2026-11-12 [VERIFIED: `paper_trader/corporate_actions.py:597-604`].
5. **D+1, seeding.** VOO/MTUM/SGOV have no mark, so the book stands down: the plan is built, every order is refused and recorded, and the job exits 70. Reconcile is 3/3, `halted` false, `account_explained` true [VERIFIED: simulation].
6. **D+2, arrival.** Market DAY buys fill and are adopted before each reconcile [VERIFIED: `:682-704`]; the run is canonical with exit 0 [VERIFIED: simulation]. The T-350 arrival (2026-09-15) was canonical on the pre-gate, pre-mirror version of this path. **D+2 under the current gate and mirror has never been observed live** (F10).

**Can a $10,000 tier start work while the broker holds about $103.5k and 92 MTUM?**
- **No, while positions are held:** they are UNEXPLAINED and every run halts (F5).
- **Yes, at the TIER level, once the broker is flat:** the cap fences off sizing. The tier is $11,166 or
  $10,000 per U2. The broker BALANCE cannot be brought back to $10,000 in place (F1).

**What "`sleeve_equity` is BROKER equity, never tier equity" implies:**
- The tracker was never tier performance in either epoch.
- Under B, epoch 2 starts at about 103,514.78, so the windfall is in the starting LEVEL, not in any
  epoch-2 return.
- At any tier of about $100k or more on this account, the windfall becomes reachable by sizing (R1).

---

## 4. The broker side (item 3)

**Alpaca facts:** see F1 and F2. In addition: paper accounts do NOT simulate dividends [VERIFIED: the
same page, "Rules and Assumptions"].

[UNVERIFIED], still open after the review:
1. whether a new paper account's starting balance can be chosen;
2. whether Alpaca itself caps paper accounts at 3;
3. whether a deleted account's activity can be exported;
4. whether the CLI user holds `secretsmanager:PutSecretValue` on `archondex/alpaca-paper*`. A template
   grants it [VERIFIED: `infra/paper_cloud/iam_policy_provisioner_delta.json:9-14`]; whether it is
   attached to the CLI user is not known, and the `iam` List/Simulate calls are denied.

**Where account 2's keys live, by NAME:**
- Secrets Manager `archondex/alpaca-paper-offense-sso`, JSON keys `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`.
- jobdef :21 binds them through `secrets[].valueFrom` with no version stage. That resolves to AWSCURRENT
  and is picked up at container start, so no jobdef revision is needed after a value change [VERIFIED:
  jobdef :21; RESOLVED-TRUE by the review].
- The secret was created 2026-07-07, has never been changed (1 version), and was last accessed 2026-11-16
  [VERIFIED: `describe-secret` metadata].
- The CLI user has no `GetSecretValue` by design [VERIFIED: `docs/Core/execution_manual.md:1015`].

**Option B — liquidate in place.** Steps 8–11 in §7, using the T-350 pattern: dry-run binds the
signature, then execute [VERIFIED: `scripts/transition_acct2_to_deploy_candidate_t350.py:74-116`].
- **For:** no identifier changes; broker history kept; director-executable on the user's word; until
  step 10 every step is reversible (§7).
- **Against:**
  - the windfall stays as fenced-off cash (§0 U1);
  - the sale is invisible to the wash guard (R9);
  - **finding 15:** if Alpaca later corrects the 54 phantom shares on this account, epoch 2 inherits the
    correction [UNVERIFIED whether Alpaca ever does]:
    - a SHARE correction would read as an UNEXPLAINED position and HALT (visible);
    - **a CASH-only correction would be silently ADOPTED once positions are held.**
      `adopt_explained_broker_truth` copies broker cash into the ledger whenever the held positions are
      explained [VERIFIED: `paper_trader/held_reconcile.py:116-118`], so CASH_DRIFT (tolerance $1
      [VERIFIED: `paper_trader/reconciliation.py:60, 188-190`]) can fire only while the account is flat.
      From D+2 on, the only witness would be a step in broker equity and the tracker.
  - Option A is immune to both.

**Option A — a new paper account.** NOT READY per the review.
- **USER steps:** open the account (dashboard); generate keys; paste them into the secret through the
  console. Never through chat, never into `.env` (F8).
- **Before the swap,** record the OLD account number by running the §7.4 check body with `TICKERS=[]`.
  It prints `account_number`, a field present in `alpaca-py` 0.43.2 `TradeAccount` [VERIFIED: local
  model introspection; `Dockerfile.paper:43` pins 0.43.2].
- **After the swap,** the same check must print a DIFFERENT `account_number`, `FLAT=True`, and `equity`
  exactly equal to the chosen balance. A mis-pasted pair shows account 1's or account 3's number or
  positions: STOP.
- **(c) At $10,000 the Rule-B rehearsal breaks on arrival day (finding 14).** Under U2-default the cap is
  $11,166 > $10,000 equity, so sizing binds on equity, the plan buys 12 / 22 / 3 ($9,910.48), and the
  +$1,166 is printed but never deployed [VERIFIED: option-A-at-$10k simulation]. Under re-base it breaks
  one month later instead, at the first contribution.
- **Delete or revoke the OLD account and keys only after artifact 3**, and delete only if the cap forces
  it.

---

## 5. Halt, freeze and alarms (item 4)

- **Halt.** It is recomputed every run and never persisted [VERIFIED: `paper_trader/scheduler.py:320-325, 405-412`]. It clears when an empty journal meets a flat broker [VERIFIED: `paper_trader/held_reconcile.py:63-70`; simulation D+1 `halted false`].
- **MTUM freeze.** This is a persisted, ack-only `ledger` freeze that the next run re-freezes while the mixed basis remains [VERIFIED: `scripts/corporate_action_ack.py:13-16` (header)].
  - **The reset never uses the ack tool.** The mixed basis is archived, then the marks file is moved aside.
  - R3-1 cannot bite: the current reason contains no "supersedes the earlier" [VERIFIED: heartbeat 2026-11-17].
  - **Rule for D+1 through D+3:** if any freeze appears, do NOT ack it, above all one whose reason contains "supersedes the earlier" [VERIFIED: `docs/State/health_check.md:63` R3-1]. Apply the §8 stop rule.
- **Non-canonical alarm** `archondex-paper-offense-sso-non-canonical` [VERIFIED: `describe-alarms`; `/tmp/runbook_review_fresh/alarms.json`].
  - ALARM since 2026-11-06T08:52:07-06:00.
  - Configuration: `PaperRunCanonical` Minimum, 86,400 s period, 1 evaluation period, `< 1`, missing data `notBreaching`, actions enabled.
  - It returns to OK by itself after a canonical day: expected after D+2 or D+3. The exact timing is [UNVERIFIED].
  - While it sits in ALARM, a new failure sends nothing.
- **Silent-stop alarm** `archondex-paper-offense-sso-silent-stop`: OK; `PaperRunHappened` Maximum, 86,400 s, 1 evaluation period, missing data `breaching` [VERIFIED: same].
  - **One missed firing does NOT page (finding 7).** The review's reading of AWS's missing-data rules: CloudWatch evaluates over an evaluation range wider than one period, and applies `TreatMissingData` only when no real datapoint is in that range. That is why weekends never page. My own observation agrees: it stayed OK through the 11-07/08 and 11-14/15 weekends [VERIFIED: `StateUpdatedTimestamp` 2026-11-02]. I did not re-read the AWS doc myself.
  - **It is not a backstop for a disabled schedule.** Step 12 and the step-13 branch are the controls.
- **Arming drill (optional, finding 10).** `cloudwatch:SetAlarmState` appears in no IAM template in the repo [VERIFIED: grep over `infra/`, `scripts/`, `docs/Core/` finds nothing], so it is **likely denied** to the CLI user.
  - Even if allowed, it proves only that SNS delivers a manually set state, not that the metric path pages.
  - Fallback: the user runs the same command with their own credentials (AWS console CloudShell).

---

## 6. The record (item 5)

**Epoch 1, archived and labelled:**
- VALID as mechanics evidence: 2026-09-15 → 11-04 (35 tracked clean sessions 09-17 → 11-04, plus 09-15/16 untracked).
- VOID: 2026-11-05 → D, including 11-05, which the tracker records as clean.
- **Two copies exist:** the step-1 local snapshot in `$OPS/snapshot/` (finding 12) and the S3 archive `$ARCH`. Plus the moved-aside originals in `$ASIDE`.

**Objects written into the archive** (§7.5 text):
- `README_VOID.txt` — includes the liquidation's realized P&L and the wash-guard bypass;
- `MANIFEST_md5.txt` — rel path, bytes and md5 of every archived object, including the exec-cost snapshot;
- `$ASIDE/README_ASIDE.txt`.

**Epoch 2:**
- It starts at D+1 (a flat, non-canonical seeding point).
- The first clean point is D+2.
- The 60-clean-day gate restarts at 0 [VERIFIED: `paper_trader/sleeve_tracker.py:54, 239-241`].
- Basis: $11,166 under U2-default, $10,000 under re-base.

**Scope of the "no windfall-era numbers" claim (finding 11): ACCOUNT-2 ARTIFACTS ONLY.**
- After the reset:
  - the account-2 tracker, ledger, journal, lots and heartbeat start fresh;
  - the mirror starts its basis from epoch-2 fills;
  - the digest has no account-2 row.
- **Not covered:**
  - (1) **`book_momentum_satellite.json`, account 2's own MTUM attribution book, under ACCOUNT 1's prefix,** still records 2026-11-05 as clean at −74.7% vs its twin. `book_quality_satellite.json` records −14.6% [VERIFIED: `python -m scripts.fleet_health`, 2026-11-17]. Their repair is T-401, not this reset.
  - (2) `fleet_health` therefore stays **NOT HEALTHY** after the reset, also because of `damped_offense_t298`, parked 79 sessions [VERIFIED: same run]. Judge the reset by the account-2 line, never by the exit code.
  - (3) `docs/State/health_check.md:62` and `docs/State/CURRENT_STATE.md` quote CAGR 24 % / Sharpe 1.87 as the windfall, which is correctly labelled.
- After artifact 3, APPEND an epoch line and the 35-session correction (F7) to those state docs, and add a TASK_LEDGER row.

---

## 7. Sequence and roles (item 6) — reordered so everything reversible comes before the broker step (finding 4)

**Roles:**
- **USER:** the user's login, hands or word.
- **DIRECTOR:** on the user's word (U3).
- **READ:** read-only.

**Points of no return:**
- **Option B: step 10, the sells.**
  - Before step 10, every step is reversible: restore the archived state (the step-5 rollback) and
    re-enable the schedule, and the account is back to today's halted state.
  - After step 10, restoring the old state still yields a halted account, which is a safe resting
    state, but the positions are gone.
- **Option A: deleting the old account.**

**Pre-conditions — all must hold before step 1:**
- **P1:** U1–U3 have been given.
- **P2:** D is chosen:
  - a full regular session, on or after 2026-11-18;
  - not 2026-11-26 or 11-27 (Thanksgiving; the 11-27 13:00 ET close) [VERIFIED: RESOLVED-TRUE by the review];
  - D+1 and D+2 are trading days;
  - the operator has checked the corporate-action calendar for VOO / MTUM / SGOV from D to D+2. This is manual because the feed asks nothing on D+1 or D+2 (F11) [UNVERIFIED: no source checked yet].
- **P3 (re-base only):** step 0.5 is complete and its readback is recorded.
- **P4:** the §7.1–7.5 files are in `$OPS`. That is a dated directory OUTSIDE the repo, e.g. `~/archondex_ops/acct2_reset_<D>/`.

```bash
P=archondex; R=us-east-1; B=archondex-results-407539788432
PFX=paper_state_offense_sso; D=<YYYY-MM-DD>; OPS=~/archondex_ops/acct2_reset_$D
ARCH=$PFX/archive_deploy_candidate_epoch1_$D; ASIDE=$PFX/reset_aside_$D
SCHED=archondex-paper-offense-sso-daily; JDNAME=archondex-paper-offense-sso; Q=archondex-backtest-queue
RELS="data/paper_state/ledger.jsonl data/paper_state/orders.jsonl data/paper_state/recon.jsonl \
data/state/deploy_candidate_tracking.json data/state/fleet_mirror_slice.json data/state/paper_alerts.log \
data/state/paper_heartbeat.json data/state/price_basis_marks.json data/state/tax_lots.jsonl"
export P R B PFX D OPS ARCH ASIDE RELS
submit() {  # submit a one-shot body on the LIVE pinned jobdef $JD (never the laptop — F8)
  python3 -c "import json,sys;print(json.dumps({'command':['python','-c',open(sys.argv[1]).read()]}))" "$1" > "$OPS/ov_$2.json"
  aws batch submit-job --job-name "reset-a2-$2-$D" --job-queue $Q --job-definition "$JD" \
    --container-overrides "file://$OPS/ov_$2.json" --profile $P --region $R --query jobId --output text
}   # read the log: describe-jobs → container.logStreamName; group /aws/batch/job [VERIFIED: jobdef logConfiguration]
```

| # | Who | Step (command of record) | Artifact that proves it | Rollback |
|---|---|---|---|---|
| 0 | READ | `python -m scripts.fleet_health` (read the **account-2 line**); `python scripts/diff_live_paper_infra.py` [VERIFIED: `docs/Core/execution_manual.md:1010, 1342`] | Account-2 line still reads "reconcile 0/3; halted; UNEXPLAINED … FROZEN MTUM". Drift: `No drift.` **Anything else: STOP.** | — |
| 0.5 | DIRECTOR on the USER's word — **re-base only**, completed BEFORE step 1 (finding 1) | (a) A branch sets `contributions.start_date` = the planned arrival date D+2 in `config/deploy_candidate.json`; review it and merge it to main (live path; never deploy unmerged code). (b) `git diff --stat 716ca04 <commit> -- paper_trader scripts/run_paper_cloud_day.py scripts/paper_cloud_entrypoint.sh Dockerfile.paper requirements.lock.txt config engines intelligence core`: **any change under `paper_trader/`, the driver, the entrypoint, `Dockerfile.paper` or the lock file → STOP and review.** Today (main `f13a1c5`) the diff is `core/census.py`, `core/measurement/mbl_gate.py`, `engines/data_manager/{convention,era_tr,stooq_tier1,tr_writer}.py` and four research configs. None runs on this path: the only import is `core.census` at `paper_trader/heartbeat.py:90`, reached only when a summary is passed, which the scheduler never does [VERIFIED: `paper_trader/scheduler.py:357, 361-373`]. (c) `scripts/build_paper_image.sh <commit> "$REF"` [VERIFIED: `docs/Core/execution_manual.md:975-976`]. (d) `python scripts/redeploy_one_account.py --account offense-sso --image "$REF"` (dry run), then `--execute` [VERIFIED: `docs/Core/execution_manual.md:1053`]. | Prints `diff-vs-LIVE: image ONLY ✓`. The schedule readback names the NEW `:N`. The drift gate prints `No drift.` | Redeploy the `paper-sha-716ca04` image the same way, which gives yet another new revision. |
| 1 | READ | **Snapshot + live revision.** `aws s3 cp --recursive s3://$B/$PFX/data/ $OPS/snapshot/data/ --profile $P --region $R --no-progress`; `(cd $OPS/snapshot && find data -type f -exec md5 -r {} \; \| sort -k2) > $OPS/snapshot_md5.txt`; `aws scheduler get-schedule --name $SCHED --profile $P --region $R --output json > $OPS/sched_live.json`; `JD=$(python3 -c "import json,sys;print(json.loads(json.load(open(sys.argv[1]))['Target']['Input'])['JobDefinition'].rsplit('/',1)[-1])" $OPS/sched_live.json)`; `aws batch describe-job-definitions --job-definition-name $JDNAME --status ACTIVE --profile $P --region $R --query 'reverse(sort_by(jobDefinitions,&revision))[0].[revision,containerProperties.image]' --output text`; `EXPECT=$(python3 -c "import json,sys;print(json.dumps({p['ticker']:p['qty'] for p in json.load(open(sys.argv[1]))['positions']},sort_keys=True))" $OPS/snapshot/data/state/fleet_mirror_slice.json)` [VERIFIED: every command above run read-only on 2026-11-17, giving `archondex-paper-offense-sso:21`, `21 …:paper-sha-716ca04` and `{"MTUM": 92, "SGOV": 6, "VOO": 12}`] | `$JD` = `$JDNAME:<latest ACTIVE revision>`. Image = `paper-sha-716ca04` (U2-default) or the step-0.5 tag (re-base). `EXPECT` recorded. **A mismatch: STOP.** | — |
| 2 | READ | **In flight / idle:** `aws batch list-jobs --job-queue $Q --filters name=JOB_NAME,values=paper-offense-sso-day --profile $P --region $R --query 'jobSummaryList[0:3].[status,createdAt,container.exitCode]' --output text`; `for s in SUBMITTED PENDING RUNNABLE STARTING RUNNING; do aws batch list-jobs --job-queue $Q --job-status $s --profile $P --region $R --query 'length(jobSummaryList)' --output text; done` [VERIFIED: both forms run 2026-11-17] | D's job is terminal and the heartbeat `run_date` = D. **Every status count is 0:** the queue is shared with backtests, and a busy queue would delay the one-shot jobs past the close. | — |
| 3 | DIRECTOR | **Probe `s3:DeleteObject` first (finding 4):** `echo "account-2 reset probe $D" > $OPS/probe.txt`; `aws s3 cp $OPS/probe.txt s3://$B/$ASIDE/_probe/created.txt --profile $P --region $R`; `aws s3 mv s3://$B/$ASIDE/_probe/created.txt s3://$B/$ASIDE/_probe/moved.txt --profile $P --region $R` | `aws s3 ls s3://$B/$ASIDE/_probe/` shows only `moved.txt`. **Denied: STOP.** Nothing live has changed; the probe sits outside every key a run reads. | — |
| 4 | DIRECTOR | **Disable** from a FRESH GET: `aws scheduler get-schedule … > $OPS/sched_now.json`; `python3 $OPS/sched_state.py $OPS/sched_now.json DISABLED $JD $OPS/sched_off.json`; `aws scheduler update-schedule --cli-input-json file://$OPS/sched_off.json --profile $P --region $R` [VERIFIED pattern: `scripts/redeploy_one_account.py:94-124`; `docs/Core/execution_manual.md:1115-1124`; `sched_state.py` tested on the live JSON] | Readback `--query '[State,Target.Input]'`: `DISABLED`, pin `$JD` | §7.1 with `ENABLED $JD` from a fresh GET |
| 5 | DIRECTOR | **Archive + move aside:** `bash $OPS/archive.sh` (§7.2) | `DONE`; 9 rows in `MANIFEST_md5.txt`; every archive md5 = the snapshot md5 = the live md5 at the move | **Restore:** `for REL in $RELS; do aws s3 mv s3://$B/$ASIDE/$REL s3://$B/$PFX/$REL --profile $P --region $R; done`. Valid until a run writes those keys. The schedule is disabled, so no run can. |
| 6 | DIRECTOR | **Exec-cost snapshot + labels:** `aws s3 cp s3://$B/$PFX/data/state/exec_cost_ledger.jsonl s3://$B/$ARCH/data/state/exec_cost_ledger.jsonl …`; append `<rel> <bytes> <md5>` to the manifest; upload `README_ASIDE.txt` to `$ASIDE/` and the manifest to `$ARCH/`. README_VOID is uploaded at step 11, once the P&L is known. | All three objects are listed; the exec-cost copy's md5 = live | — |
| 7 | READ | `aws s3 ls --recursive s3://$B/$PFX/` | Live keys: ONLY `data/state/exec_cost_ledger.jsonl`, plus `archive_offense_2026-09-11/`, `$ARCH/`, `$ASIDE/` | step-5 restore |
| 8 | DIRECTOR | **Pre-liquidation flat-check:** render §7.4 with `TICKERS=[]` and run `submit $OPS/pc_pre.py pre`. Re-run step 2's idle check. | `FLATCHECK` positions = `$EXPECT`; `n_open_orders` 0; `account_number` recorded. The clock is ≥ 10:00 ET and ≥ 30 min before the close. **Otherwise: STOP**, then step-5 restore and step-12 re-enable. | step-5 restore + re-enable |
| 9 | DIRECTOR | **(B) Dry run:** `python3 $OPS/render.py $OPS/reset_a2.tmpl.py $OPS/r_dry.py D=$D EXPECT="$EXPECT" ATTEMPT=1 EXECUTE=False`; `submit $OPS/r_dry.py dry` | Log: `positions_before` = EXPECT; `broker_avg_entry` printed; three `DRY-RUN would sell` lines; `RESULT ok`; exit 0. **A REFUSED line or a non-zero exit: STOP.** | step-5 restore + re-enable |
| 10 | DIRECTOR — **(B) point of no return** | **Execute:** render with `EXECUTE=True`, then `submit $OPS/r_exec.py exec` | three `submitted` lines (coids `reset-a2-<D>-<T>-sell-a1`); `RESULT ok` | **Partial / FAILED:** never re-buy. Run step 11. Then either re-run with `ATTEMPT=2` and `EXPECT` = the REMAINING positions, before 15:30 ET, or stop with the account halted (restore + re-enable). |
| 11 | DIRECTOR | **Post-check:** render §7.4 with `TICKERS=["MTUM","SGOV","VOO"]`, then `submit $OPS/pc_post.py post`. Fill README_VOID's P&L from the FILL lines and step 9's `broker_avg_entry`, then upload it to `$ARCH/`. | `FLAT=True`; equity ≈ cash ≈ $103.5k; the same `account_number` as step 8 | — |
| 8A–11A | USER, then DIRECTOR (option A instead of 9–11) | The user creates the account, generates keys, and puts them into the secret (console). The director runs `pc_pre.py` again. | A NEW `account_number`; `FLAT=True`; `equity` = the chosen balance exactly | Put the old key pair back; possible only while the old account and its keys exist |
| 12 | DIRECTOR | **Re-enable from a FRESH GET:** `get-schedule … > $OPS/sched_now2.json`; `python3 $OPS/sched_state.py $OPS/sched_now2.json ENABLED $JD $OPS/sched_on.json`; `update-schedule --cli-input-json file://$OPS/sched_on.json …`; repeat step 1's `describe-job-definitions` query; `python scripts/diff_live_paper_infra.py`. **Must finish before D+1 09:40 ET.** | `ENABLED`; pin = `$JD` (the NEW revision under re-base). The latest ACTIVE revision is still `$JD`: if a newer one was registered mid-window, STOP and decide; never write an old pin back (finding 1). `No drift.` | `sched_state.py … DISABLED $JD` |
| 13 | READ | **D+1 09:50 ET: seeding** (§8 artifact 1, with its branches) | §8 | §8 stop rule |
| 14 | READ | **D+2: arrival** (§8 artifact 2) | §8 | §8 stop rule |
| 15 | READ | **D+3: first settled day** (§8 artifact 3) | §8 | §8 stop rule |
| 16 | READ | `aws cloudwatch describe-alarms --alarm-name-prefix archondex-paper-offense-sso …` | non-canonical `OK` (SNS OK mail) | — |
| 17 | optional — likely DENIED (finding 10) | `aws cloudwatch set-alarm-state --alarm-name archondex-paper-offense-sso-non-canonical --state-value ALARM --state-reason "arming drill" …`; on denial, the user runs it from the console's CloudShell | SNS ALARM mail. This proves SNS delivery only. | The alarm self-corrects at its next evaluation [UNVERIFIED timing] |
| 18 | DIRECTOR | Docs: APPEND to `CURRENT_STATE.md`, to `health_check.md:62-63`, and a TASK_LEDGER row (the epoch line, the 35-session correction, R8/T-401 pointers). Add every NEW CLI to `docs/Core/execution_manual.md` in that turn. | the commit | — |
| 19 | USER (A only, after artifact 3) | Revoke the OLD key pair; decide the old account's fate | — | — |

**NEW CLI** ([NN-NO-GUESS-CLI]; add each to the execution manual when first executed):
- `aws s3 mv`, `aws s3api head-object`, `aws logs get-log-events`, `aws cloudwatch set-alarm-state`:
  syntax RESOLVED-TRUE by the review.
- `aws batch list-jobs --filters` and `--job-status`, and the `describe-job-definitions` revision query:
  run by me read-only on 2026-11-17.

### 7.1 `sched_state.py` — State-only, pin-asserting (tested on the live schedule JSON)

```python
"""usage: python3 sched_state.py <live.json> <ENABLED|DISABLED> <expected_jobdef_tail> <out.json>"""
import json, sys
live_p, state, expect, out_p = sys.argv[1:5]
assert state in ("ENABLED", "DISABLED"), f"bad state {state!r}"
s = json.load(open(live_p)); tgt = s["Target"]
jd = json.loads(tgt["Input"])["JobDefinition"].rsplit("/", 1)[-1]
if jd != expect:
    sys.exit(f"REFUSE: live target is {jd}, expected {expect} — someone repointed it; re-read and decide")
if ":" not in jd: sys.exit(f"REFUSE: target {jd} is not revision-pinned")
if not (tgt.get("DeadLetterConfig") or {}).get("Arn"): sys.exit("REFUSE: no DeadLetterConfig")
if tgt.get("RetryPolicy") != {"MaximumEventAgeInSeconds": 3600, "MaximumRetryAttempts": 3}:
    sys.exit(f"REFUSE: retry policy is {tgt.get('RetryPolicy')}, not fast-fail")
for k in ("Arn", "CreationDate", "LastModificationDate", "Version"): s.pop(k, None)
s["State"] = state
json.dump(s, open(out_p, "w"), indent=1)
print(f"wrote {out_p}: State={state} target={jd} (everything else verbatim from the live GET)")
```

Tested on `/tmp/runbook_review_fresh/sched_live.json`:
- the output differs from the input only in `State` and the three dropped read-only keys;
- an expected `:22` against a live `:21` → `REFUSE` [VERIFIED: local run].

### 7.2 `archive.sh` — pipefail, three-way md5, empty-md5 refusal, ETag, then move (finding 3)

```bash
#!/usr/bin/env bash
set -uo pipefail
AWS="${AWS:-aws}"; EMPTY=d41d8cd98f00b204e9800998ecf8427e
die() { echo "STOP: $*" >&2; exit 1; }
for REL in $RELS; do
  SNAP="$OPS/snapshot/$REL"
  [ -s "$SNAP" ] || die "no non-empty step-1 snapshot for $REL"
  S=$(md5 -q "$SNAP") || die "md5 of snapshot $REL"
  [ "$S" != "$EMPTY" ] || die "snapshot md5 is the empty-file md5 for $REL"
  L=$($AWS s3 cp "s3://$B/$PFX/$REL" - --profile "$P" --region "$R" | md5 -q) || die "read live $REL"
  [ "$L" = "$S" ] || die "live $REL ($L) differs from the step-1 snapshot ($S) — something wrote it"
  $AWS s3 cp "s3://$B/$PFX/$REL" "s3://$B/$ARCH/$REL" --profile "$P" --region "$R" --no-progress \
    || die "archive copy $REL"
  A=$($AWS s3 cp "s3://$B/$ARCH/$REL" - --profile "$P" --region "$R" | md5 -q) || die "read archive $REL"
  [ "$A" = "$S" ] || die "archive copy of $REL ($A) != snapshot ($S)"
  E=$($AWS s3api head-object --bucket "$B" --key "$ARCH/$REL" --query ETag --output text \
        --profile "$P" --region "$R" | tr -d '"') || die "head-object archive $REL"
  [ "$E" = "$S" ] || die "archive ETag of $REL ($E) != snapshot md5 ($S)"
  BYTES=$(wc -c < "$SNAP" | tr -d ' ')
  $AWS s3 mv "s3://$B/$PFX/$REL" "s3://$B/$ASIDE/$REL" --profile "$P" --region "$R" --no-progress \
    || die "move-aside $REL (archive copy exists; live key untouched or partially moved — check both)"
  echo "$REL $BYTES $S" >> "$OPS/MANIFEST_md5.txt"
  echo "archived+aside $REL $BYTES $S"
done
echo "DONE: all keys archived and moved aside"
```

**How it was tested:** with a stub `aws` mapping `s3://` to a local directory, on the 2026-11-17
snapshot. The happy path archives 9, moves 9 aside, writes a 9-row manifest, and leaves only
`exec_cost_ledger.jsonl` live. Four failure cases each STOP at the first key, with nothing moved:
- the live read denied;
- the move denied (10 live keys remain, 1 archive copy exists);
- the live key changed since the snapshot;
- the live key missing, which is the reviewer's empty-md5 case.

With `pipefail` a failed `aws … - | md5 -q` assignment now returns non-zero; without it, the same line
yields `d41d8cd9…` and exits 0, as demonstrated [VERIFIED: local runs].

### 7.3 `reset_a2.tmpl.py` — the liquidation body (finding 9; runs ONLY in account 2's container)

```python
import datetime as dt, inspect, json, sys
from paper_trader.paper_client import AlpacaPaperClient
D = "__D__"; ATTEMPT = __ATTEMPT__; EXECUTE = __EXECUTE__      # the execute job changes ONLY EXECUTE
EXPECT = __EXPECT__          # from step 1's slice, re-confirmed at step 8
NO_TRADE_DATES = {"2026-11-26", "2026-11-27"}         # Thanksgiving; the 13:00 ET early close
c = AlpacaPaperClient()
acct = c._client.get_account()                       # read-only
clock = c._client.get_clock()                        # read-only
mins_left = (clock.next_close - clock.timestamp).total_seconds() / 60.0
raw = c.list_positions()
pos = {p["symbol"]: int(p["qty"]) for p in raw}
entry = {p["symbol"]: p.get("avg_entry_price") for p in raw}
TERM = {"filled", "canceled", "expired", "rejected", "done_for_day", "replaced"}
open_o = [o for o in c.list_orders() if str(o.get("status", "")).lower() not in TERM]
print("RESET-A2 account_number=%s equity=%s cash=%s" % (acct.account_number, acct.equity, acct.cash))
print("RESET-A2 positions_before=" + json.dumps(pos, sort_keys=True))
print("RESET-A2 broker_avg_entry=" + json.dumps(entry, sort_keys=True))
print("RESET-A2 open_orders=%d market_open=%s minutes_to_close=%.0f attempt=%d execute=%s"
      % (len(open_o), clock.is_open, mins_left, ATTEMPT, EXECUTE))
why = []
if D in NO_TRADE_DATES: why.append(f"D={D} is excluded")
if clock.timestamp.date().isoformat() != D: why.append(f"broker date {clock.timestamp.date()} != D {D}")
if not clock.is_open: why.append("market closed")
if mins_left < 30: why.append(f"only {mins_left:.0f} min to the close")
if pos != EXPECT: why.append(f"positions {pos} != EXPECT {EXPECT}")
if open_o: why.append(f"{len(open_o)} open order(s)")
if why:
    print("RESET-A2 REFUSED: " + "; ".join(why)); sys.exit(70)
failed = []
for t, q in sorted(pos.items()):
    kw = dict(client_order_id=f"reset-a2-{D}-{t}-sell-a{ATTEMPT}", symbol=t, qty=q,
              side="sell", tif="day")
    try:
        inspect.signature(c.submit_order).bind(**kw)
        if EXECUTE:
            print("RESET-A2 submitted " + json.dumps(c.submit_order(**kw), default=str)[:300])
        else:
            print(f"RESET-A2 DRY-RUN would sell {q} {t} coid={kw['client_order_id']} (signature binds)")
    except Exception as exc:                          # one failure never hides the others
        failed.append(t)
        print(f"RESET-A2 FAILED {t}: {type(exc).__name__}: {str(exc)[:200]}")
print("RESET-A2 RESULT " + ("FAILED " + ",".join(failed) if failed else "ok"))
sys.exit(70 if failed else 0)
```

**Rendering** (refuses any unfilled `__KEY__` and validates each value):
`python3 render.py <template> <out> D=… EXPECT=… ATTEMPT=… EXECUTE=…`, alongside §7.4.

**Tested against a fake broker module.** Results:
- dry run: exit 0, nothing submitted;
- execute: three coids with the `-a1` suffix;
- one order failing: the other two still submit, then `RESULT FAILED SGOV`, exit 70;
- REFUSED with exit 70 for: positions ≠ EXPECT, an open order, 25 min to the close, market closed, D = 2026-11-27, broker date ≠ D [VERIFIED: local runs].

**Field checks:**
- `get_clock().is_open` and `next_close`, and `TradeAccount.account_number`, exist in `alpaca-py` 0.43.2 [VERIFIED: local introspection; review RESOLVED-TRUE].
- Whether `clock.timestamp` carries the ET offset is [UNVERIFIED]. It does not matter before 15:30 ET, because the UTC date and the ET date agree then.
- Sell exactly what the BROKER reports. The coid prefix `reset-a2-` cannot collide with the stream token `deploycand-a2` [VERIFIED: `scripts/run_paper_cloud_day.py:70`]. The `submit_order` signature is [VERIFIED: `paper_trader/paper_client.py:206-217`].

### 7.4 `postcheck_a2.tmpl.py` — flat-check (`TICKERS=[]`) or post-liquidation check

```python
import json
from paper_trader.paper_client import AlpacaPaperClient
D = "__D__"; ATTEMPT = __ATTEMPT__; TICKERS = __TICKERS__   # TICKERS=[] → a plain flat-check
c = AlpacaPaperClient(); a = c._client.get_account(); pos = c.list_positions()
TERM = {"filled", "canceled", "expired", "rejected", "done_for_day", "replaced"}
op = [o for o in c.list_orders() if str(o.get("status", "")).lower() not in TERM]
print("FLATCHECK " + json.dumps({"account_number": a.account_number, "status": str(a.status),
      "equity": str(a.equity), "cash": str(a.cash), "n_positions": len(pos),
      "n_open_orders": len(op), "positions": pos}, default=str))
for t in TICKERS:
    o = c.get_order(f"reset-a2-{D}-{t}-sell-a{ATTEMPT}")
    print("FILL " + t + " " + (json.dumps({k: o.get(k) for k in ("status", "filled_qty",
          "filled_avg_price", "filled_at")}, default=str) if isinstance(o, dict) else repr(o)))
print("FLAT=%s" % (not pos and not op))
```

It derives from the execution manual's FLAT-CHECK [VERIFIED: `docs/Core/execution_manual.md:1020-1033`],
adding `account_number` (finding 15) and the per-order fills. The order fields are as normalized by
`_normalize_order` [VERIFIED: `paper_trader/paper_client.py:144-157`]. Tested against a fake client
[VERIFIED: local run].

### 7.5 Label texts (finding 12)

`$ARCH/README_VOID.txt`:

> ACCOUNT 2 (deploy candidate, prefix paper_state_offense_sso) — EPOCH 1 ARCHIVE, reset on <D> by the
> user's ruling of 2026-11-17. VALID as mechanics evidence only: 2026-09-15..2026-11-04 (35 tracked clean
> sessions 2026-09-17..2026-11-04; 09-15/16 untracked). VOID: 2026-11-05..<D> — MTUM 4:1 split ex
> 2026-11-05 unhandled; a spurious buy of 18 @ 65.26; the paper broker scaled all 23 shares to 92 (true 38;
> 54 phantom shares). The tracker summary's CAGR/Sharpe is the windfall, never the strategy.
> `sleeve_equity` is BROKER equity (~$100k), never tier equity.
> LIQUIDATION on <D> (reset-a2-<D>-*-sell-a<n>): proceeds <Σ fill × qty per ticker>; realized vs the
> journal's own fills <…> of which the 54 phantom MTUM shares contributed <54 × MTUM fill>; broker-reported
> realized vs its avg_entry <…>. [Estimate at the 2026-11-16 closes, for scale only: +$3,155.90 total =
> −$392.44 on the true position (VOO −213.36, MTUM −179.10, SGOV +0.02) + $3,548.34 phantom-share
> proceeds.] WASH-GUARD BYPASS: these sales went outside the OrderManager, so no lot events; the lot
> ledger is archived here; a VOO loss sale followed by the epoch-2 VOO buy inside 61 days would be
> refusable in a guarded real account — a paper-reset artifact with no real-money analogue.
> exec_cost_ledger.jsonl stays live, mixing epochs with no epoch field (epoch 2 = trade_date ≥ <D+2>);
> its 2026-11-05 MTUM row is a real fill of a spurious order. Copies: this archive, the moved-aside
> originals in reset_aside_<D>/, and the operator's local snapshot. Runbook:
> docs/Sources/runbook_account2_reset_2026-11-17.md.

The estimate comes from the journal's filled orders at the slice's 11-16 closes [VERIFIED: computed from
the S3 `orders.jsonl` snapshot].

`$ASIDE/README_ASIDE.txt`:

> The moved-aside ORIGINALS of account 2's epoch-1 live state, moved on <D>; byte-identical to
> archive_deploy_candidate_epoch1_<D>/ (see its MANIFEST_md5.txt). Kept, never deleted ([NN-ARCHIVE]).
> Rollback source until the first post-reset run writes the live keys. _probe/moved.txt is the
> DeleteObject probe of step 3.

`$ARCH/MANIFEST_md5.txt` has one row per archived object, `<rel> <bytes> <md5>`, written by
`archive.sh`, plus the `exec_cost_ledger.jsonl` snapshot row from step 6.

---

## 8. First artifacts (`[NN-FIRST-ARTIFACT]`, from the scheduled firings only) and the stop rule

**Stop rule (findings 2 and 8):** any field that differs from its expected value below, other than the
mirror values marked EXPECTED-WRONG, means:
1. do not ack, do not re-run anything by hand, do not edit state;
2. if the next firing would compound the problem (a freeze, UNEXPLAINED, drift or a refused order), disable
   the schedule with the step-4 procedure;
3. capture the heartbeat, the Batch job log and the `fleet_health` account-2 line;
4. hand them to the director and the user.

**Artifact 1 — D+1 09:50 ET, the seeding run.**
- **Branch A — no job by 10:15 ET.** If no `paper-offense-sso-day` job was created on D+1:
  - check the DLQ count (`aws sqs get-queue-attributes … --attribute-names ApproximateNumberOfMessages`) [VERIFIED: `docs/Core/execution_manual.md:1137-1140`];
  - check the schedule `State` and the queue;
  - STOP.
  - From 10:15 ET, UNKNOWN in `fleet_health` is NOT "expected".
- **Branch B — the job exits anything other than 70.** STOP.
  - Exit 0 means marks existed, or nothing was traded.
  - 64–69 means a fail-closed refusal elsewhere. The next run then becomes the seeding day, and every later expectation shifts by one session.
- **Expected** [VERIFIED: simulation]:
  - job FAILED, exit 70;
  - `last_run`: `canonical` false, `reason` exactly "corporate actions: seeding price-basis marks (first run) for MTUM, SGOV, VOO", reconcile 3/3, `halted` false, `submitted` 0, `fills` 0, `account_explained` true;
  - `corporate_actions`: `feed.available` true, `feed.tickers` **[]** with reason "no tickers to ask about" (F11), `frozen` {}, `frozen_persisted` {}, `seeding` [MTUM, SGOV, VOO], `marks_age_sessions` 0, `stand_down` true;
  - `refused_orders` = the arrival buys: 25 MTUM / 6 SGOV / 13 VOO under U2-default, or 22 / 3 / 12 under re-base, at 11-16 prices;
  - new `ledger.jsonl` with ONE `init` row whose cash = broker cash (about 103,514.78 under B) and `positions` {};
  - the marks file with `account` "paper_state_offense_sso" and `seed_sessions` 0;
  - tracker 1 point; no `tax_lots.jsonl`; no exec-cost rows added;
  - mirror `tier_equity` 10,000.00, `total_change` 0 (all tier cash);
  - the non-canonical alarm stays ALARM.

**Artifact 2 — D+2 09:50 ET, the arrival.** Expected [VERIFIED: simulations]:
- job SUCCEEDED, exit 0;
- `canonical` true, reconcile 3/3, `halted` false, `submitted` 3, `fills` 3, `account_explained` true;
- `corporate_actions`: `feed.tickers` **[]** (F11), `frozen` {}, `seeding` [], `stand_down` false, `marks_age_sessions` 1, `refused_orders` [];
- **the contributions line in the job log:**
  - U2-default: `contributions: +$1,166 = 2 whole month(s)` (or +$1,749 = 3 months if D+2 ≥ 2026-12-11);
  - **re-base: `contributions: +$0 = 0 whole month(s)`. Anything else: STOP (finding 1).**
- **Positions — read them from the ledger, the journal and the lots, NOT the mirror (F10):**
  - `ledger.jsonl` last row `adopt_broker:cloud cycle <D+2> reconcile` with positions 13 VOO / 25 MTUM / 6 SGOV (U2-default) or 12 / 22 / 3 (re-base) at 11-16 prices;
  - `tax_lots.jsonl` holds exactly those 3 buy lots;
  - `orders.jsonl` holds 3 filled orders with coid prefix `archondex-deploycand-a2-<D+2>-`;
  - exec-cost +3 rows.
- **Mirror EXPECTED-WRONG on D+2:** `positions` [], `tier_equity` **0.00**, `total_change` **−10,000.00** (U2-default); or `tier_equity` ≈ **89.52**, `total_change` ≈ **−9,910** (re-base or A at $10k). This is the stale-positions defect (T-401), not a stop.
- tracker 2 points, the second with `exec.canonical` true and `order_errors` 0.

**Artifact 3 — D+3 09:50 ET, the first settled day.** Expected [VERIFIED: simulation]:
- exit 0, `canonical` true, `submitted` 0 when inside the bands;
- **`feed.tickers` [MTUM, SGOV, VOO] with `feed.available` true** (finding 6);
- `marks_age_sessions` null;
- mirror `positions` listed, `tier_equity` ≈ invested: ≈ 11,089.61 / `total_change` ≈ +1,089.61 under U2-default, or ≈ 10,000 / ≈ 0 under re-base, moving with prices;
- the non-canonical alarm `OK`, or OK within about 24 h;
- the `fleet_health` **account-2 line is absent** (the overall verdict stays NOT HEALTHY for the books, §6).

---

## 9. Open risks (item 7)

- **R1 — seeding from the windfall** (§0 U1). Under B the ledger cash and the broker equity carry about $3.5k of windfall for good. It is fenced off from sizing only while the cap is below equity: at a tier of about $100k or more on this account it becomes sizable.
- **R2 — the scheduler firing mid-reset.** Closed by steps 4 and 12:
  - the disable and re-enable are built from FRESH GETs, change State only, and assert the live pin;
  - the re-enable also asserts the latest ACTIVE revision;
  - never write a pin captured earlier back to the schedule (finding 1).
  - The silent-stop alarm is NOT a backstop (finding 7).
- **R3 — the wrong account's keys.** The laptop holds account 1's keys (F8). Under A, the step-8A `account_number` and `equity` check catches a mis-pasted pair.
- **R4 — irreversible deletion under A** (F2). Do it last, after artifact 3, and only if forced.
- **R5 — A at $10,000 breaks Rule-B on arrival day** (§4, finding 14).
- **R6 — D+1 and D+2 are unwitnessed by the feed** (F11). There is no price reference on D+1 and only a one-day-old one on D+2 [VERIFIED: `paper_trader/corporate_actions.py:39-45`]. P2's manual calendar check is the only control. Corporate actions for D..D+2 are [UNVERIFIED].
- **R7 — the paper broker's split handling is defective** [VERIFIED: journal 23 vs broker 92]. The gate in force froze MTUM correctly on 2026-11-16, but broker share counts on split days cannot be trusted.
- **R8 — the mirror** (F9, F10). It reads −$10,000 on D+2, then contributions-inclusive `total_change` with clipped cash from D+3. The fixes are propose-first on a branch, tracked in T-401:
  - pass the contributed cap;
  - pass post-fill positions;
  - add the missing `json` import.
- **R9 — the wash-guard bypass** (README_VOID). Option A has no sale.
- **R10 — no dividends in paper** [VERIFIED: Alpaca page], so SGOV earns about 0 in the record.
- **R11 — no versioning** (F12). The protections are the step-1 local snapshot plus the verified archive copy, and the step-3 probe proves the move works before anything moves.
- **R12 — the new-prefix alternative was rejected.** It changes jobdef env (`redeploy_one_account.py` refuses a non-image diff), needs a job-role grant [VERIFIED: `docs/Core/execution_manual.md:1009`], a `fleet_health.py` edit, and hits R3-2 [VERIFIED: `docs/State/health_check.md:63`].
- **R13 — a later Alpaca correction of the phantom shares under B** (finding 15, §4). A share correction halts visibly. A cash-only correction is adopted silently once positions are held. [UNVERIFIED whether Alpaca ever corrects.]

---

## 10. Every [UNVERIFIED] item, with the review's resolutions

| # | Item | Status |
|---|---|---|
| 1 | Whether a new paper account's starting balance can be chosen, and whether any API exists for it; whether an in-place reset still exists (F1 contradiction) | STILL UNVERIFIED |
| 2 | Whether Alpaca itself caps paper accounts at 3 | STILL UNVERIFIED |
| 3 | Whether a deleted account's activity can be exported | STILL UNVERIFIED |
| 4 | Empty version stage → AWSCURRENT, picked up at container start | RESOLVED-TRUE (review) |
| 5 | CLI user `PutSecretValue` and `s3:DeleteObject` | STILL UNVERIFIED. DeleteObject is now PROVEN by the step-3 probe before any move. The job role has only Get/Put/List [VERIFIED: `/tmp/runbook_review_fresh/jobrole_policy.json`], which is irrelevant because the operator runs the move. |
| 6 | Exact OK time of the non-canonical alarm; drill self-correction timing | STILL UNVERIFIED |
| 7 | Silent-stop pages on one missed firing | RESOLVED-FALSE (review); consistent with the observed weekends |
| 8 | `get_clock().is_open` / `next_close`; `account_number` | RESOLVED-TRUE (alpaca-py 0.43.2, local introspection) |
| 9 | CLI syntax of the NEW commands | RESOLVED-TRUE (review); `list-jobs` and the revision query run by me |
| 10 | Thanksgiving dates; corporate actions VOO/MTUM/SGOV D..D+2 | dates RESOLVED-TRUE; corporate actions STILL UNVERIFIED (P2 manual check) |
| 11 | Arrival share counts | RESOLVED by execution: 13 / 25 / 6 at $11,166, or 12 / 22 / 3 at $10,000, at 11-16 prices |
| 12 | Whether `clock.timestamp` carries the ET offset | UNVERIFIED; harmless before 15:30 ET (§7.3) |
| 13 | Whether Alpaca ever corrects phantom shares later (R13) | UNVERIFIED |

---

## 11. Review findings → where each is fixed (revision 2)

| Finding | Fix |
|---|---|
| 1 BLOCKER (re-base undone by step 11) | Step 0.5 runs before step 1. `$JD` is read live at step 1. `sched_state.py` asserts the live pin at steps 4 and 12, both built from FRESH GETs, and step 12 re-checks the latest ACTIVE revision. Artifact 2 requires `+$0 = 0 whole month(s)` under re-base. The 716ca04 → commit diff rule is in step 0.5. |
| 2 arrival-day mirror | F9 corrected; F10 added; artifact 2 reads positions from the ledger, journal and lots, with the mirror marked EXPECTED-WRONG; artifact 3 added; T-401 noted; §8 stop rule. |
| 3 md5 gate | `archive.sh`: pipefail, three-way md5 against the step-1 snapshot, empty-md5 refusal, ETag check; tested five ways. |
| 4 irreversible before deniable | Reordered: the DeleteObject probe (3) and the archive (5–7) come before the liquidation (8–11). |
| 5 departures | §0 U1/U2 name each departure and ask the user to rule; §0.1 shows the surfaces by option and day; recommendation removed. |
| 6 feed asks nothing D+1/D+2 | F11; artifacts 1 and 2 expect `tickers []`; artifact 3 checks [MTUM, SGOV, VOO]; P2 manual check kept. |
| 7 silent-stop | §5: does not page on one miss; not a backstop. |
| 8 step-12 branches | Artifact 1 branches A and B: no job by 10:15 ET → DLQ, State, queue, STOP; exit ≠ 70 → STOP. |
| 9 liquidation body | EXPECT from the step-1 slice, re-confirmed by the step-8 flat-check; per-order try/except; `-a<ATTEMPT>` coids; < 30 min refusal; 11-26/27 excluded; queue idle (steps 2 and 8); drift gate at step 0. |
| 10 SetAlarmState | Step 17 marked likely-denied; it proves SNS only; CloudShell fallback. |
| 11 fleet_health | §6 scopes the claim to account-2 artifacts; the books remain; judge by the account-2 line. |
| 12 labelling | README_ASIDE; README_VOID with P&L and the wash-guard bypass; the manifest carries bytes and the exec-cost row; the epoch mixing in the live exec-cost ledger is stated; the snapshot is a second copy. |
| 13 cites | F1 full quotes; entrypoint `:32`; heartbeat `:32`/`:33`; the 09-15 arrival predates the gate and the mirror; F12 VersionId null. |
| 14 A at $10,000 | §4 (c) rewritten: it breaks on arrival day (simulated). |
| 15 B Alpaca correction | §4 / R13, with the refinement that a cash-only correction is silently adopted; A's check prints `account_number`. |
