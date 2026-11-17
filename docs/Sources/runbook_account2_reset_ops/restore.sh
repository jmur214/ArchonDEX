#!/usr/bin/env bash
# Roll back archive.sh: move each original from $ASIDE back to its live key. Per key: the
# live key must be provably ABSENT (an occupied destination is refused — never overwritten);
# the aside object's md5 must equal the archive copy's; after the move the live md5 must
# equal the archive's. Refuses unless the schedule is DISABLED. Never deletes.
# Use RELS from the manifest so a partial archive restores exactly what was moved:
#   RELS="$(cut -d' ' -f1 "$OPS/MANIFEST_md5.txt")" bash restore.sh
# A PARTLY finished restore is re-run with RELS = the manifest keys still under $ASIDE (the
# already-restored keys are now occupied live keys and would be refused) — runbook §7.6.
# Required env: B PFX ARCH ASIDE RELS SCHED (and P R for the aws profile/region).
set -uo pipefail
AWS="${AWS:-aws}"
EMPTY=d41d8cd98f00b204e9800998ecf8427e
die() { echo "STOP: $*" >&2; exit 1; }
absent() {  # 0 iff head-object proves the key absent (a 404); any other error is not proof
  local err
  err=$($AWS s3api head-object --bucket "$B" --key "$1" --profile "$P" --region "$R" 2>&1 >/dev/null) && return 1
  case "$err" in *"(404)"*) return 0 ;; *) die "cannot prove $1 absent: ${err:-no error text}" ;; esac
}
ST=$($AWS scheduler get-schedule --name "$SCHED" --query State --output text --profile "$P" --region "$R") \
  || die "cannot read the schedule State"
[ "$ST" = "DISABLED" ] || die "schedule $SCHED is '$ST', not DISABLED — a run could write mid-restore"
[ -n "$RELS" ] || die "RELS is empty — nothing to restore"
for REL in $RELS; do
  absent "$PFX/$REL" || die "live key $PFX/$REL is occupied — a run wrote it; archive that stray first"
  A=$($AWS s3 cp "s3://$B/$ARCH/$REL" - --profile "$P" --region "$R" | md5 -q) || die "read archive $REL"
  [ "$A" != "$EMPTY" ] || die "archive copy of $REL is empty"
  X=$($AWS s3 cp "s3://$B/$ASIDE/$REL" - --profile "$P" --region "$R" | md5 -q) || die "read aside $REL"
  [ "$X" = "$A" ] || die "aside $REL ($X) != archive copy ($A)"
  $AWS s3 mv "s3://$B/$ASIDE/$REL" "s3://$B/$PFX/$REL" --profile "$P" --region "$R" --no-progress \
    || die "move back $REL"
  L=$($AWS s3 cp "s3://$B/$PFX/$REL" - --profile "$P" --region "$R" | md5 -q) || die "read restored $REL"
  [ "$L" = "$A" ] || die "restored $REL ($L) != archive copy ($A)"
  echo "restored $REL $A"
done
echo "DONE: all keys restored"
