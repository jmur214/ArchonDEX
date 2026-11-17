#!/usr/bin/env bash
# The stray-run gate (runbook steps 7, 9.5 and 12). Passes ONLY when the schedule is
# DISABLED and the live prefix holds exactly data/state/exec_cost_ledger.jsonl. Anything
# else means a run wrote state after the archive (a stray): a stray before the liquidation
# seeds the new ledger from the PRE-liquidation cash and wedges the account on CASH_DRIFT.
# Required env: B PFX SCHED (and P R for the aws profile/region).
set -uo pipefail
AWS="${AWS:-aws}"
die() { echo "STOP: $*" >&2; exit 1; }
ST=$($AWS scheduler get-schedule --name "$SCHED" --query State --output text --profile "$P" --region "$R") \
  || die "cannot read the schedule State"
[ "$ST" = "DISABLED" ] || die "schedule $SCHED is '$ST', not DISABLED"
LIST=$($AWS s3 ls --recursive "s3://$B/$PFX/data/" --profile "$P" --region "$R") \
  || die "cannot list s3://$B/$PFX/data/ (an empty prefix also fails: exec_cost_ledger.jsonl must be there)"
KEYS=$(echo "$LIST" | awk '{print $4}' | sort)
[ "$KEYS" = "$PFX/data/state/exec_cost_ledger.jsonl" ] \
  || die "live prefix is not clean — it holds: $(echo "$KEYS" | tr '\n' ' ')(a stray run? see runbook §7.6)"
echo "GATE OK: schedule DISABLED; live prefix holds only data/state/exec_cost_ledger.jsonl"
