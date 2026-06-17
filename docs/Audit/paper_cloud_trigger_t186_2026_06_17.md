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
