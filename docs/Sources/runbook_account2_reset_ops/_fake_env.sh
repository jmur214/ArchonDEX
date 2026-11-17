# Sourced by the check_*.sh harnesses (never run directly): a SYNTHETIC world for fake_aws.sh.
# No AWS, no real state: every object is a one-line synthetic file; the AWS account id in the
# schedule and image is the placeholder 000000000000.
HERE="${HERE:?set HERE before sourcing}"
export P=placeholder-profile R=us-east-1 B=fakebucket PFX=paper_state_offense_sso D=2026-11-18
export SCHED=archondex-paper-offense-sso-daily JDNAME=archondex-paper-offense-sso
export EXPECT_IMAGE=paper-sha-716ca04
export ARCH=$PFX/archive_deploy_candidate_epoch1_$D ASIDE=$PFX/reset_aside_$D
export RELS="data/paper_state/ledger.jsonl data/paper_state/orders.jsonl data/paper_state/recon.jsonl data/state/deploy_candidate_tracking.json data/state/fleet_mirror_slice.json data/state/paper_alerts.log data/state/paper_heartbeat.json data/state/price_basis_marks.json data/state/tax_lots.jsonl"
export AWS="$HERE/fake_aws.sh"
ROOT="$(mktemp -d "${TMPDIR:-/tmp}/acct2_ops_check.XXXXXX")"
FAILS=0

content() {  # synthetic bytes for a key (the slice carries the positions step 2 reads)
  case "$1" in
    data/state/fleet_mirror_slice.json)
      echo '{"positions": [{"ticker": "MTUM", "qty": 92}, {"ticker": "SGOV", "qty": 6}, {"ticker": "VOO", "qty": 12}]}' ;;
    *) echo "{\"synthetic\": \"$1\"}" ;;
  esac
}

world() {  # world <schedule State> [nosnap] — a fresh fake S3 (+ the step-2 snapshot unless nosnap)
  W="$(mktemp -d "$ROOT/case.XXXX")"
  export OPS="$W/ops" FAKE_S3="$W/s3" FAKE_SCHED="$W/sched.json" FAKE_FAIL=none
  export FAKE_REV=21 FAKE_IMAGE="000000000000.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:paper-sha-716ca04"
  python3 -I - "$FAKE_SCHED" "$1" <<'PY'
import json, sys
acct = "000000000000"
json.dump({"Name": "archondex-paper-offense-sso-daily", "State": sys.argv[2],
           "ScheduleExpression": "cron(50 9 ? * MON-FRI *)", "ScheduleExpressionTimezone": "America/New_York",
           "FlexibleTimeWindow": {"Mode": "OFF"},
           "Target": {"Arn": "arn:aws:scheduler:::aws-sdk:batch:submitJob",
                      "DeadLetterConfig": {"Arn": f"arn:aws:sqs:us-east-1:{acct}:archondex-scheduler-dlq"},
                      "RetryPolicy": {"MaximumEventAgeInSeconds": 3600, "MaximumRetryAttempts": 3},
                      "Input": json.dumps({"JobDefinition": f"arn:aws:batch:us-east-1:{acct}:job-definition/archondex-paper-offense-sso:21"})}},
          open(sys.argv[1], "w"))
PY
  for REL in $RELS data/state/exec_cost_ledger.jsonl; do
    mkdir -p "$(dirname "$FAKE_S3/$PFX/$REL")"; content "$REL" > "$FAKE_S3/$PFX/$REL"
    if [ "${2:-}" != nosnap ]; then
      mkdir -p "$(dirname "$OPS/snapshot/$REL")"; content "$REL" > "$OPS/snapshot/$REL"
    fi
  done
}

n_files() { [ -d "$1" ] && find "$1" -type f | wc -l | tr -d ' ' || echo 0; }
live_n() { n_files "$FAKE_S3/$PFX/data"; }
arch_n() { n_files "$FAKE_S3/$ARCH"; }
aside_n() { n_files "$FAKE_S3/$ASIDE"; }
has() { case "$1" in *"$2"*) echo yes ;; *) echo no ;; esac; }
expect() { if [ "$1" = "$2" ]; then echo "PASS $3"; else echo "FAIL $3 (got '$1', want '$2')"; FAILS=$((FAILS+1)); fi; }
finish() { echo "fixtures under $ROOT (synthetic; left in place)"; [ "$FAILS" = 0 ] && echo "ALL PASS" || echo "$FAILS FAIL(S)"; exit "$FAILS"; }
