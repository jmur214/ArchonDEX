# Paper Loop in the Cloud — runbook (T-186)

**Status:** code + IaC shipped 2026-06-17 (`feature/paper-cloud-trigger-t186`).
Live provisioning is gated on the director's scope decision.
**Companion:** [`CLOUD_USAGE.md`](CLOUD_USAGE.md) (the backtest infra this reuses),
`docs/State/paper_run_scorecard.md` (the run scorecard), T-185 persistence
(`docs/Audit/paper_persistence_t185_2026_06_17.md`).

## Why cloud (the decision)

The paper loop must run once per trading day, unattended, and the
dead-man's-switch must alert if it doesn't. A Mac + launchd was the
alternative, but **a sleeping laptop is itself a silent-stop mode** the
switch would then have to alert on daily. The user chose cloud
(2026-06-17). Everything host-independent (calendar self-skip,
auction-window DEFER, the heartbeat, reconcile-on-restart) is T-185; T-186
is the cloud trigger + durable state + cloud-context alarms.

## Architecture

```
EventBridge Scheduler  (cron 13:00 UTC daily = 08:00 EST / 09:00 EDT,
        |               inside the OPG window 7pm-9:28am ET year-round)
        v   batch:SubmitJob (scheduler invocation role)
AWS Batch job  archondex-paper-cloud-day   (Fargate, ARM64, reuses the
        |                                    existing archondex-backtest-queue)
        v   container command: scripts/paper_cloud_entrypoint.sh
   creds injected as env from Secrets Manager (job-def `secrets` binding)
        v
scripts/run_paper_cloud_day.py
   1. CloudState.pull()   — S3 -> local: orders journal / ledger /
                            heartbeat / alert log (Fargate disk is ephemeral;
                            this is the loop's memory between days)
   2. T-185 run_trading_day() — self-skips non-trading days; DEFERs
                            out-of-window auctions; reconciles vs broker truth;
                            records the heartbeat in run_day's finally
   3. CloudState.push()   — local -> S3 (so tomorrow's container resumes)
   4. emit_metrics()      — PaperRunHappened=1, PaperRunCanonical=1|0
   5. exit 0 (canonical) | non-zero (non-canonical -> Batch FAILED)
```

### The dead-man's-switch in the cloud — THREE independent signals

A silently-skipped or failed cloud day is the exact failure mode we are
eliminating. Three signals, so no single failure swallows the alarm:

1. **Silent stop** (`archondex-paper-silent-stop`): a CloudWatch alarm on
   `ArchonDEX/PaperLoop / PaperRunHappened`, period 1 day,
   `treat-missing-data=breaching`. If the schedule never fired OR the job
   never started, the metric is ABSENT -> the alarm breaches -> SNS. This
   is the true dead-man's-switch: it fires on the absence of a pulse.
2. **Non-canonical** (`archondex-paper-non-canonical`): an alarm on
   `PaperRunCanonical < 1`. The job ran but reconcile drifted / halted /
   census failed -> the driver emits `PaperRunCanonical=0` and exits
   non-zero.
3. **Batch FAILED state**: the non-zero exit marks the Batch job FAILED —
   visible in the console and to any Batch-state EventBridge rule.

All three route to the SNS topic `archondex-paper-alerts` (subscribe an
email at deploy with `--alert-email`). The heartbeat **status file**
(`data/state/paper_heartbeat.json`, schema `paper_heartbeat/v1`) is also
pushed to S3 so C's dashboard (T-182) surfaces the same `alert` flag.

## Deploy

```bash
# 1. Build + push the paper image (SANCTIONED path only — never raw docker build):
ARCHONDEX_BUILD_PUSH=1 scripts/build_backtest_image.sh HEAD \
    407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:sha-<short>

# 2. Provision (idempotent). Reads paper creds from .env, never echoes them.
#    Full live:
scripts/deploy_paper_cloud_trigger.sh \
    --image 407539788432.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:sha-<short> \
    --alert-email you@example.com
#    Schedule disabled (director flips on later):
scripts/deploy_paper_cloud_trigger.sh --image <ref> --schedule-disabled
#    Creds already in Secrets Manager:
scripts/deploy_paper_cloud_trigger.sh --image <ref> --no-secret

# 3. Prove the path (one manual cloud run, no waiting for the schedule):
aws batch submit-job --profile archondex --region us-east-1 \
    --job-name paper-cloud-manual --job-queue archondex-backtest-queue \
    --job-definition archondex-paper-cloud-day
aws logs tail /aws/batch/job --follow --profile archondex   # watch it
```

The same image as the backtest infra is reused (the paper driver is just a
different container command); the only paper-specific image requirement is
that `paper_trader/` + `scripts/paper_cloud_entrypoint.sh` are present
(they are, on `main` once this merges).

## What the container is allowed to do (least privilege)

- **Execution role** (`archondex-paper-exec-role`): ECR pull + CloudWatch
  Logs (managed `AmazonECSTaskExecutionRolePolicy`) + read the ONE Alpaca
  paper secret. Nothing else.
- **Job role** (`archondex-paper-job-role`): S3 read/write under
  `paper_state/*` only + `cloudwatch:PutMetricData` to the
  `ArchonDEX/PaperLoop` namespace only. No broker creds (those are the
  execution role's job), no live-trading AWS surface.
- **Scheduler role** (`archondex-paper-scheduler-role`): `batch:SubmitJob`
  to the one job def + the one queue. Nothing else.

## Hard boundary

PAPER endpoint only. No live-money path anywhere in this loop. The
deployment boundary (paper-allowed / live-hard-gated on paper-valid AND
beats-Schwab-robo) is unchanged — see `deployment_boundary.md`. The secret
holds PAPER creds only; no real-money credentials exist in this system.

## Cost

The daily job is a ~1-2 min Fargate task (1 vCPU / 2GB): roughly
$0.001-0.002/day (~$0.03-0.06/mo). Trivial against the $20 monthly budget
alarm.

## Order CONTENT (the next layer)

This trigger runs the daily PULSE — reconcile broker truth + record the
heartbeat — with NO staged orders by default, so the account stays flat
and the loop's liveness is proven without accumulating positions. The
engine-driven order set (`PaperOrderConstructor`, A->C->B; PR-3) is the
content layer wired separately; it slots into `run_paper_cloud_day.py`'s
`run_trading_day([...], ...)` call once the in-container data pipeline is
confirmed. The first REAL fill is bootstrapped manually in-window via
`scripts/first_real_fill_t186.py`.
