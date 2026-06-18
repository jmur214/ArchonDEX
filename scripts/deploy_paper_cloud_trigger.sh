#!/usr/bin/env bash
# scripts/deploy_paper_cloud_trigger.sh
#
# T-186 — provision the daily CLOUD paper-loop trigger. IDEMPOTENT: every
# step create-or-updates, so re-running is safe. Reuses the existing Batch
# queue + ECR repo + results bucket (it does NOT touch the backtest infra).
#
# Architecture:
#   EventBridge Scheduler (daily 13:00 UTC = 08:00-09:00 ET, inside the
#   7pm-9:28am OPG window year-round)
#     -> batch:SubmitJob (job def archondex-paper-cloud-day, queue
#        archondex-backtest-queue, Fargate ARM64)
#       -> container runs scripts/paper_cloud_entrypoint.sh
#          (PULL state from S3 -> T-185 cycle -> PUSH state -> emit metrics)
#   Dead-man's-switch:
#     - CloudWatch alarm on PaperRunHappened (missing>1day = breaching) -> SNS
#     - CloudWatch alarm on PaperRunCanonical (<1) -> SNS
#     - Batch job FAILED (non-canonical exits non-zero) is the third signal
#
# PAPER creds: read from .env (this Mac) and stored in Secrets Manager; the
# container reads them via the job-def `secrets` binding. NEVER echoed.
#
# Usage:
#   scripts/deploy_paper_cloud_trigger.sh --image <ecr-ref> [--alert-email you@x] \
#       [--no-secret] [--no-schedule] [--schedule-disabled]
#
#   --no-secret          skip the Secrets Manager write (it already exists)
#   --no-schedule        provision everything EXCEPT the EventBridge schedule
#   --schedule-disabled  create the schedule in DISABLED state (director flips on)
set -euo pipefail

PROFILE="${AWS_PROFILE:-archondex}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
ACCOUNT="$(aws sts get-caller-identity --profile "$PROFILE" --query Account --output text)"
RESULTS_BUCKET="archondex-results-${ACCOUNT}"
QUEUE="archondex-backtest-queue"
SECRET_NAME="archondex/alpaca-paper"
TOPIC_NAME="archondex-paper-alerts"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INFRA="$HERE/infra/paper_cloud"

IMAGE=""; ALERT_EMAIL=""; DO_SECRET=1; DO_SCHEDULE=1; SCHED_STATE="ENABLED"
while [ $# -gt 0 ]; do
  case "$1" in
    --image) IMAGE="$2"; shift 2;;
    --alert-email) ALERT_EMAIL="$2"; shift 2;;
    --no-secret) DO_SECRET=0; shift;;
    --no-schedule) DO_SCHEDULE=0; shift;;
    --schedule-disabled) SCHED_STATE="DISABLED"; shift;;
    *) echo "unknown arg: $1" >&2; exit 2;;
  esac
done
_aws() { aws "$@" --profile "$PROFILE" --region "$REGION"; }
log() { echo "[deploy] $*"; }

# --- 1. Secrets Manager: Alpaca PAPER creds (read from .env, never echoed) -- #
if [ "$DO_SECRET" = "1" ]; then
  ENV_FILE="${ARCHONDEX_ENV_FILE:-$HERE/.env}"
  [ -f "$ENV_FILE" ] || ENV_FILE="/Users/jacksonmurphy/Dev/trading_machine-2/.env"
  [ -f "$ENV_FILE" ] || { echo "[deploy] FATAL: no .env to read paper creds from" >&2; exit 64; }
  # Extract by NAME only; values go straight into a JSON doc, never to stdout.
  AK="$(grep -E '^ALPACA_API_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
  SK="$(grep -E '^ALPACA_SECRET_KEY=' "$ENV_FILE" | head -1 | cut -d= -f2-)"
  [ -n "$AK" ] && [ -n "$SK" ] || { echo "[deploy] FATAL: ALPACA_* not in .env" >&2; exit 64; }
  SECRET_JSON="$(python3 -c 'import json,sys; print(json.dumps({"ALPACA_API_KEY":sys.argv[1],"ALPACA_SECRET_KEY":sys.argv[2]}))' "$AK" "$SK")"
  if _aws secretsmanager describe-secret --secret-id "$SECRET_NAME" >/dev/null 2>&1; then
    log "secret $SECRET_NAME exists -> put-secret-value"
    _aws secretsmanager put-secret-value --secret-id "$SECRET_NAME" \
      --secret-string "$SECRET_JSON" >/dev/null
  else
    log "creating secret $SECRET_NAME"
    _aws secretsmanager create-secret --name "$SECRET_NAME" \
      --description "Alpaca PAPER API creds for the cloud paper loop (T-186). PAPER ONLY." \
      --secret-string "$SECRET_JSON" >/dev/null
  fi
  unset AK SK SECRET_JSON
fi
SECRET_ARN="$(_aws secretsmanager describe-secret --secret-id "$SECRET_NAME" --query ARN --output text)"
log "secret ARN: ${SECRET_ARN%%-??????}<redacted-suffix>"

# --- 2. IAM: execution role (read secret + ECR/logs), job role (S3+metrics) - #
ensure_role() {  # name trust-file
  local name="$1" trust="$2"
  if ! _aws iam get-role --role-name "$name" >/dev/null 2>&1; then
    log "creating role $name"
    # strip any _comment field — IAM rejects unknown fields in policy docs
    local clean="/tmp/trust_$name.json"
    python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); d.pop("_comment",None); json.dump(d,open(sys.argv[2],"w"))' "$trust" "$clean"
    _aws iam create-role --role-name "$name" \
      --assume-role-policy-document "file://$clean" >/dev/null
  fi
}
render() { sed -e "s|__SECRET_ARN__|$SECRET_ARN|g" -e "s|__RESULTS_BUCKET__|$RESULTS_BUCKET|g" \
              -e "s|__ACCOUNT__|$ACCOUNT|g" -e "s|__REGION__|$REGION|g" "$1" \
            | python3 -c 'import json,sys; d=json.load(sys.stdin); d.pop("_comment",None); print(json.dumps(d))'; }

EXEC_ROLE="archondex-paper-exec-role"
JOB_ROLE="archondex-paper-job-role"
SCHED_ROLE="archondex-paper-scheduler-role"

# ECS task execution role: trust = ecs-tasks; managed exec policy + secret read.
cat > /tmp/ecs_tasks_trust.json <<'EOF'
{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"ecs-tasks.amazonaws.com"},"Action":"sts:AssumeRole"}]}
EOF
ensure_role "$EXEC_ROLE" /tmp/ecs_tasks_trust.json
_aws iam attach-role-policy --role-name "$EXEC_ROLE" \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy >/dev/null 2>&1 || true
render "$INFRA/iam_exec_secret_policy.json" > /tmp/exec_secret.json
_aws iam put-role-policy --role-name "$EXEC_ROLE" --policy-name read-alpaca-paper-secret \
  --policy-document file:///tmp/exec_secret.json >/dev/null

ensure_role "$JOB_ROLE" /tmp/ecs_tasks_trust.json
render "$INFRA/iam_job_role_policy.json" > /tmp/job_role.json
_aws iam put-role-policy --role-name "$JOB_ROLE" --policy-name paper-state-and-metrics \
  --policy-document file:///tmp/job_role.json >/dev/null

EXEC_ROLE_ARN="$(_aws iam get-role --role-name "$EXEC_ROLE" --query Role.Arn --output text)"
JOB_ROLE_ARN="$(_aws iam get-role --role-name "$JOB_ROLE" --query Role.Arn --output text)"

# --- 3. Batch job definition (rendered) ----------------------------------- #
[ -n "$IMAGE" ] || { echo "[deploy] FATAL: --image <ecr-ref> required to register the job def" >&2; exit 65; }
log "registering job def archondex-paper-cloud-day (image $IMAGE)"
sed -e "s|__IMAGE__|$IMAGE|g" -e "s|__EXEC_ROLE_ARN__|$EXEC_ROLE_ARN|g" \
    -e "s|__JOB_ROLE_ARN__|$JOB_ROLE_ARN|g" -e "s|__SECRET_ARN__|$SECRET_ARN|g" \
    -e "s|__RESULTS_BUCKET__|$RESULTS_BUCKET|g" "$INFRA/job_definition.json" \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); d.pop("_comment",None); print(json.dumps(d))' \
  > /tmp/paper_job_def.json
_aws batch register-job-definition --cli-input-json file:///tmp/paper_job_def.json \
  --query '{name:jobDefinitionName,rev:revision}' --output json

# --- 4. SNS alert topic (the notification path) --------------------------- #
TOPIC_ARN="$(_aws sns create-topic --name "$TOPIC_NAME" --query TopicArn --output text)"
log "alert topic: $TOPIC_ARN"
if [ -n "$ALERT_EMAIL" ]; then
  _aws sns subscribe --topic-arn "$TOPIC_ARN" --protocol email --notification-endpoint "$ALERT_EMAIL" >/dev/null
  log "subscribed $ALERT_EMAIL (CONFIRM the email link to receive alerts)"
fi

# --- 5. CloudWatch dead-man's-switch alarms ------------------------------- #
# (a) silent stop: no PaperRunHappened datapoint in >1 day. treat-missing=breaching.
_aws cloudwatch put-metric-alarm --alarm-name archondex-paper-silent-stop \
  --alarm-description "Paper loop did not run today (EventBridge missed / job never started). Dead-man's-switch." \
  --namespace ArchonDEX/PaperLoop --metric-name PaperRunHappened \
  --statistic Maximum --period 86400 --evaluation-periods 1 --threshold 1 \
  --comparison-operator LessThanThreshold --treat-missing-data breaching \
  --alarm-actions "$TOPIC_ARN" --ok-actions "$TOPIC_ARN"
# (b) non-canonical run: PaperRunCanonical reported 0.
_aws cloudwatch put-metric-alarm --alarm-name archondex-paper-non-canonical \
  --alarm-description "Paper loop ran but was NON-CANONICAL (reconcile drift / halt / census fail)." \
  --namespace ArchonDEX/PaperLoop --metric-name PaperRunCanonical \
  --statistic Minimum --period 86400 --evaluation-periods 1 --threshold 1 \
  --comparison-operator LessThanThreshold --treat-missing-data notBreaching \
  --alarm-actions "$TOPIC_ARN" --ok-actions "$TOPIC_ARN"
log "alarms: archondex-paper-silent-stop + archondex-paper-non-canonical -> SNS"

# --- 6. EventBridge Scheduler -> Batch SubmitJob -------------------------- #
if [ "$DO_SCHEDULE" = "1" ]; then
  ensure_role "$SCHED_ROLE" "$INFRA/iam_scheduler_trust.json"
  render "$INFRA/iam_scheduler_submit_policy.json" > /tmp/sched_submit.json
  _aws iam put-role-policy --role-name "$SCHED_ROLE" --policy-name submit-paper-job \
    --policy-document file:///tmp/sched_submit.json >/dev/null
  SCHED_ROLE_ARN="$(_aws iam get-role --role-name "$SCHED_ROLE" --query Role.Arn --output text)"
  JOBDEF_ARN="$(_aws batch describe-job-definitions --job-definition-name archondex-paper-cloud-day \
     --status ACTIVE --query 'reverse(sort_by(jobDefinitions,&revision))[0].jobDefinitionArn' --output text)"
  QUEUE_ARN="$(_aws batch describe-job-queues --job-queues "$QUEUE" --query 'jobQueues[0].jobQueueArn' --output text)"
  TARGET="$(python3 -c 'import json,sys; print(json.dumps({"Arn":"arn:aws:scheduler:::aws-sdk:batch:submitJob","RoleArn":sys.argv[1],"Input":json.dumps({"JobName":"paper-cloud-day","JobQueue":sys.argv[2],"JobDefinition":sys.argv[3]})}))' "$SCHED_ROLE_ARN" "$QUEUE_ARN" "$JOBDEF_ARN")"
  # daily 13:00 UTC; OPG window 7pm-9:28am ET => 08:00 EST / 09:00 EDT, in-window year-round.
  if _aws scheduler get-schedule --name archondex-paper-daily >/dev/null 2>&1; then
    log "updating schedule archondex-paper-daily (state=$SCHED_STATE)"
    _aws scheduler update-schedule --name archondex-paper-daily --state "$SCHED_STATE" \
      --schedule-expression "cron(0 13 * * ? *)" --schedule-expression-timezone "UTC" \
      --flexible-time-window '{"Mode":"OFF"}' --target "$TARGET" >/dev/null
  else
    log "creating schedule archondex-paper-daily (state=$SCHED_STATE)"
    _aws scheduler create-schedule --name archondex-paper-daily --state "$SCHED_STATE" \
      --schedule-expression "cron(0 13 * * ? *)" --schedule-expression-timezone "UTC" \
      --flexible-time-window '{"Mode":"OFF"}' --target "$TARGET" >/dev/null
  fi
else
  log "skipping schedule (--no-schedule)"
fi

log "DONE. Manual one-shot to prove the path:"
log "  aws batch submit-job --profile $PROFILE --region $REGION \\"
log "    --job-name paper-cloud-manual --job-queue $QUEUE \\"
log "    --job-definition archondex-paper-cloud-day"
