#!/usr/bin/env bash
# The stray-run gate (runbook steps 7, 9.5 and 12). Passes ONLY when (1) the schedule is
# DISABLED, (2) NO job on account 2's jobdef (any revision) is still in flight, and (3) the live
# prefix holds exactly data/state/exec_cost_ledger.jsonl. Anything else means a run wrote, or may
# still write, state after the archive (a stray): a stray before the liquidation seeds the new
# ledger from the PRE-liquidation cash and wedges the account on CASH_DRIFT.
# Terminal = SUCCEEDED or FAILED; every other status (SUBMITTED, PENDING, RUNNABLE, STARTING,
# RUNNING, or anything unknown) refuses. Our own one-shot jobs count too: wait until they finish.
# Required env: B PFX SCHED Q JDNAME (and P R for the aws profile/region).
set -uo pipefail
AWS="${AWS:-aws}"
die() { echo "STOP: $*" >&2; exit 1; }
ST=$($AWS scheduler get-schedule --name "$SCHED" --query State --output text --profile "$P" --region "$R") \
  || die "cannot read the schedule State"
[ "$ST" = "DISABLED" ] || die "schedule $SCHED is '$ST', not DISABLED"
JOBS=$($AWS batch list-jobs --job-queue "$Q" --filters "name=JOB_DEFINITION,values=$JDNAME" \
  --query 'jobSummaryList[].[jobName,status]' --output text --profile "$P" --region "$R") \
  || die "cannot list the jobs on $JDNAME — a job in flight cannot be ruled out"
INFLIGHT=$(echo "$JOBS" | awk 'NF && $2 != "SUCCEEDED" && $2 != "FAILED"')
[ -z "$INFLIGHT" ] || die "job(s) on $JDNAME not yet terminal — wait, then re-run the gate: $(echo "$INFLIGHT" | tr '\t\n' ': ')"
LIST=$($AWS s3 ls --recursive "s3://$B/$PFX/data/" --profile "$P" --region "$R") \
  || die "cannot list s3://$B/$PFX/data/ (an empty prefix also fails: exec_cost_ledger.jsonl must be there)"
KEYS=$(echo "$LIST" | awk '{print $4}' | sort)
[ "$KEYS" = "$PFX/data/state/exec_cost_ledger.jsonl" ] \
  || die "live prefix is not clean — it holds: $(echo "$KEYS" | tr '\n' ' ')(a stray run? see runbook §7.6)"
echo "GATE OK: schedule DISABLED; no job in flight on $JDNAME; live prefix holds only data/state/exec_cost_ledger.jsonl"
