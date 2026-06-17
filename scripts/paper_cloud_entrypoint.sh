#!/usr/bin/env bash
# scripts/paper_cloud_entrypoint.sh
#
# Container entrypoint for the daily CLOUD paper loop (T-186).
# EventBridge Scheduler → AWS Batch (Fargate) → this script.
#
# Thin by design: the heavy lifting (pull durable state from S3, run the
# T-185 calendar-aware cycle, push state back, emit the CloudWatch
# dead-man's-switch metrics, set the exit code) lives in
# scripts/run_paper_cloud_day.py so it is unit-testable. This wrapper only
# fixes the environment and forwards the exit code.
#
# Creds: ALPACA_API_KEY / ALPACA_SECRET_KEY are injected as env vars by
# the Batch job definition's `secrets` block (valueFrom an AWS Secrets
# Manager ARN). This script NEVER reads, prints, or persists them.
#
# Required env (set by the job definition):
#   ARCHONDEX_PAPER_STATE_BUCKET   durable-state S3 bucket (journal/ledger/heartbeat)
#   AWS_DEFAULT_REGION             us-east-1
# Optional:
#   ARCHONDEX_PAPER_STATE_PREFIX   default "paper_state"
#   ARCHONDEX_PAPER_ALLOCATOR      default "mean_variance"
set -uo pipefail

export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ALLOC="${ARCHONDEX_PAPER_ALLOCATOR:-mean_variance}"

if [ -z "${ALPACA_API_KEY:-}" ] || [ -z "${ALPACA_SECRET_KEY:-}" ]; then
    echo "FATAL: Alpaca paper creds not present in env (expected from the job "\
         "definition's Secrets Manager binding)." >&2
    exit 64
fi

echo "[paper-cloud] $(date -u +%Y-%m-%dT%H:%M:%SZ) starting daily paper cycle (alloc=$ALLOC)"

# Forward the driver's exit code verbatim: 0 = canonical; non-zero =
# non-canonical/failed → Batch marks the job FAILED → the failure alarm
# fires (defence-in-depth with the metric + the heartbeat status file).
python -m scripts.run_paper_cloud_day --allocator "$ALLOC"
RC=$?

echo "[paper-cloud] $(date -u +%Y-%m-%dT%H:%M:%SZ) cycle exit rc=$RC"
exit $RC
