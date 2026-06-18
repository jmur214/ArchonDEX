# Cloud trigger for the paper loop (T-186)

**Date:** 2026-06-17 · **Branch:** `feature/paper-cloud-trigger-t186` ·
**Agent:** E (deployment) · **Endpoint:** Alpaca **PAPER** only.

## Mandate

User chose **cloud** (2026-06-17) over Mac+launchd for the paper-loop
host: a sleeping laptop is itself a silent-stop mode. T-185 shipped every
host-independent piece; T-186 wires the trigger + the cloud-context
persistence and alarms.

## What shipped (this branch)

### Code (host-agnostic, non-destructive)
- **`paper_trader/cloud_state.py`** — durable S3 state. Fargate disk is
  ephemeral, so the order journal / ledger / heartbeat / alert-log (the
  loop's memory between days) live in `s3://<bucket>/paper_state/...`.
  `pull()` on start (missing keys = clean first run, not an error),
  `push()` on exit (best-effort per file so the heartbeat lands even if a
  journal stalls), `emit_metrics()` for the dead-man's-switch. **No-ops
  off-cloud** so the identical driver runs on a laptop.
- **`scripts/run_paper_cloud_day.py`** — the daily cloud driver: pull ->
  T-185 `run_trading_day` (self-skips non-trading days, DEFERs
  out-of-window auctions, reconciles vs broker truth, records the
  heartbeat) -> push -> `emit_metrics(happened, canonical)` -> **exit
  non-zero iff non-canonical** (Batch marks the job FAILED).
- **`scripts/paper_cloud_entrypoint.sh`** — thin container entrypoint;
  Alpaca creds arrive as env via the job-def Secrets Manager binding and
  are never read or logged here.
- **`scripts/first_real_fill_t186.py`** — bootstraps the FIRST real fill:
  one in-window OPG, **left queued** (fills at the next open), durably
  journaled to S3. Refuses outside the OPG window (same gate the scheduler
  enforces) and on a non-trading day.

### IaC (reviewable; applied by the deploy script)
- **`scripts/deploy_paper_cloud_trigger.sh`** — idempotent. Provisions:
  Secrets Manager secret `archondex/alpaca-paper` (creds read from `.env`,
  never echoed); IAM exec/job/scheduler roles (least privilege, below);
  the Batch job def `archondex-paper-cloud-day` (Fargate ARM64, reusing
  the existing `archondex-backtest-queue`); the SNS topic
  `archondex-paper-alerts`; two CloudWatch alarms; the EventBridge daily
  schedule -> `batch:SubmitJob`. Flags: `--no-secret`, `--no-schedule`,
  `--schedule-disabled`.
- **`infra/paper_cloud/*.json`** — job-def + IAM policy templates.

### The dead-man's-switch in the cloud — three independent signals
1. **`archondex-paper-silent-stop`** — alarm on `PaperRunHappened`, 1-day
   period, `treat-missing-data=breaching`. Fires on the ABSENCE of a pulse
   (schedule didn't fire / job never started). This is the real switch.
2. **`archondex-paper-non-canonical`** — alarm on `PaperRunCanonical < 1`
   (ran but drifted/halted/census-failed).
3. **Batch FAILED** — the non-zero exit marks the job FAILED.
All route to SNS `archondex-paper-alerts`; the heartbeat status file is
also pushed to S3 for C's dashboard.

## Verification

- **`tests/test_paper_cloud_t186.py` — 7 passed**: off-cloud no-op;
  `from_env` bucket precedence; `pull()` syncs every durable path; missing
  keys = clean start (no raise); `push()` uploads only existing files;
  metric emission `{Happened:1, Canonical:1}` on a clean run and
  `{Happened:1, Canonical:0}` on a non-canonical run (the exact
  silent-stop-quiet / non-canonical-fires signal).
- Deploy script + entrypoint **bash-lint clean**; all five infra JSON
  templates parse.
- **Driver dry-run, live against the paper account** (2026-06-17 18:04
  ET): clean-start pull, 3/3 reconcile cycles clean vs broker truth,
  heartbeat canonical/alive, would-emit `Happened=1 Canonical=1`, exit 0.
- **First-fill window gate proven**: at 18:07 ET (pre-window) the
  first-fill script refuses with the exact reason (code-40310000 would
  reject) — the gate works before any real order is sent.

## T-186-exec — PROVISIONED LIVE + VERIFIED (2026-06-17, rec-C: schedule DISABLED)

Director chose rec-C. The IAM provisioner delta
(`infra/paper_cloud/iam_policy_provisioner_delta.json`) was granted to
`claude-code-cli` and the deploy ran clean. Two deploy-script bugs were
found + fixed in the process: IAM rejects the `_comment` field in policy +
trust docs (MalformedPolicyDocument) — `render()` and `ensure_role` now
strip it.

**Image — lean variant required.** The full `Dockerfile.backtest` image
won't build on the available disk (~4-9GB free): the ~3GB data-substrate
stage + the full `requirements.lock` install exhaust it (pip died at 0
bytes). The paper loop reads NONE of the substrate, so a lean variant was
built: **`Dockerfile.paper`** (pinned `python:3.14-slim` + `awscli` + just
`pandas==3.0.1` + `alpaca-py==0.43.2`, ~130MB compressed) via the
sanctioned git-archive wrapper **`scripts/build_paper_image.sh`**. Pushed
as `archondex-backtest:paper-sha-0b9d8b3`; job def rev 3 points at it.

**Provisioned (all live, schedule DISABLED):** secret
`archondex/alpaca-paper`; IAM roles `archondex-paper-exec-role` /
`-job-role` / `-scheduler-role`; Batch job def `archondex-paper-cloud-day`
(rev 3); SNS `archondex-paper-alerts`; CloudWatch alarms
`archondex-paper-silent-stop` (PaperRunHappened, treat-missing=breaching)
+ `archondex-paper-non-canonical` (PaperRunCanonical<1); EventBridge
schedule `archondex-paper-daily` `cron(0 13 * * ? *)` UTC, **state
DISABLED**.

**Verify — cloud cycle PASSED end-to-end** (manual Fargate job
`d6b16d45`): container fetched creds from Secrets Manager, `state=S3:...`,
`pulled-from-s3=False` (clean first run), interlock fired (runtime ==
designated), **reconcile 3/3 clean** vs the real paper account from inside
Fargate, heartbeat canonical, **pushed state to S3** (`paper_heartbeat.json`
confirmed in `s3://archondex-results-407539788432/paper_state/...`),
emitted `PaperRunHappened=1 PaperRunCanonical=1`, exit 0. A second run
(`22697123`) showed `pulled-from-s3=True` — **cross-run S3 persistence
proven**.

**Dead-man's-switch — PROVEN via a real failure path** (not a synthetic
set-alarm-state): a job submitted with a mismatched allocator
(`adaptive` ≠ designated `mean_variance`) → the interlock REFUSED →
driver emitted `PaperRunCanonical=0` → **exit 66 → Batch FAILED**
(signal #3) → the `archondex-paper-non-canonical` alarm transitioned
**OK → ALARM in ~90s** (*"1 datapoint [0.0] was less than the threshold
(1.0)"*) → fired to SNS (signal #2). The `silent-stop` alarm
(missing-data) is config-proven (treat-missing=breaching, observed
tracking the pulse: OK because `PaperRunHappened=1` arrived) and shares
the identical SNS wiring; forcing it live needs `cloudwatch:SetAlarmState`
(not in the scoped role) or a 24h missed day. The non-canonical alarm
self-heals once the forced `0` ages out of the 1-day window (well before
the schedule is enabled).

**Remaining (flagged):** (1) the SNS topic has an email subscription
PENDING the user's confirmation click — until confirmed, alarms fire to
SNS but reach no human. (2) The EventBridge schedule stays DISABLED until
the director enables it on confirmation that verify + first-fill are clean
(both are). Enable with:
`aws scheduler update-schedule --name archondex-paper-daily --state ENABLED ...`
(or re-run the deploy without `--schedule-disabled`).

## Least privilege (the three roles)

- exec role: ECR pull + Logs (managed policy) + read the ONE paper secret.
- job role: S3 rw under `paper_state/*` + `PutMetricData` to
  `ArchonDEX/PaperLoop` only.
- scheduler role: `batch:SubmitJob` to the one job def + queue.

No role touches a live-money surface; the secret holds PAPER creds only.

## What is NOT done here (honest status)

- **LIVE AWS provisioning is GATED** on the director's scope decision
  (A: provision+prove / B: IaC-only / C: provision schedule-DISABLED). No
  live resources were created in this branch. The deploy script is ready;
  once the director answers, provisioning is one command + a manual
  one-shot to prove the path + a forced non-canonical run to prove the
  alarm.
- **The first REAL fill is armed, pending the OPG window.** At submit time
  it was 18:0x ET (pre-window). An OPG fills at the next open regardless
  of where in the 7pm-9:28am window it is submitted, so the fill lands at
  the 6/18 open once the in-window submit fires.
- **Order CONTENT** (engine-driven A->C->B order set) is the separate next
  layer; the trigger runs the daily pulse (reconcile + heartbeat) flat by
  default.
- **Schedule timezone:** `cron(0 13 * * ? *)` UTC = 08:00 EST / 09:00 EDT,
  inside the OPG window year-round. (If the US ever drops DST the margin to
  the 9:28 cutoff shrinks but stays positive.)
