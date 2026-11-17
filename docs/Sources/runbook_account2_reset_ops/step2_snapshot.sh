#!/usr/bin/env bash
# Runbook step 2 (after step 1 confirmed D's run terminal): snapshot the live state and read
# the live revision. Writes $OPS/snapshot/, $OPS/snapshot_md5.txt, $OPS/sched_live.json and
# $OPS/step2.env (JD, EXPECT). Refuses an OPS dir that already holds a snapshot, a schedule
# pin that is not the latest ACTIVE revision, and an image that is not $EXPECT_IMAGE.
# Required env: B PFX OPS SCHED JDNAME EXPECT_IMAGE (and P R for the aws profile/region).
set -uo pipefail
AWS="${AWS:-aws}"
die() { echo "STOP: $*" >&2; exit 1; }
[ ! -e "$OPS/snapshot" ] || die "$OPS/snapshot exists — use a fresh OPS dir"
mkdir -p "$OPS/snapshot/data" || die "mkdir"
$AWS s3 cp --recursive "s3://$B/$PFX/data/" "$OPS/snapshot/data/" --profile "$P" --region "$R" \
  --no-progress > /dev/null || die "snapshot copy of s3://$B/$PFX/data/"
(cd "$OPS/snapshot" && find data -type f -exec md5 -r {} \; | sort -k2) > "$OPS/snapshot_md5.txt" \
  || die "md5 list"
[ -s "$OPS/snapshot_md5.txt" ] || die "the snapshot is empty"
$AWS scheduler get-schedule --name "$SCHED" --profile "$P" --region "$R" --output json \
  > "$OPS/sched_live.json" || die "get-schedule $SCHED"
JD=$(python3 -I -c 'import json,sys;print(json.loads(json.load(open(sys.argv[1]))["Target"]["Input"])["JobDefinition"].rsplit("/",1)[-1])' \
  "$OPS/sched_live.json") || die "cannot parse the schedule pin"
REV_IMG=$($AWS batch describe-job-definitions --job-definition-name "$JDNAME" --status ACTIVE \
  --profile "$P" --region "$R" \
  --query 'reverse(sort_by(jobDefinitions,&revision))[0].[revision,containerProperties.image]' \
  --output text) || die "describe-job-definitions $JDNAME"
REV=$(echo "$REV_IMG" | awk '{print $1}'); IMG=$(echo "$REV_IMG" | awk '{print $2}')
[ "$JD" = "$JDNAME:$REV" ] || die "schedule pin $JD is not the latest ACTIVE revision $JDNAME:$REV"
case "$IMG" in *":$EXPECT_IMAGE") ;; *) die "latest ACTIVE image $IMG is not $EXPECT_IMAGE" ;; esac
EXPECT=$(python3 -I -c 'import json,sys;print(json.dumps({p["ticker"]:p["qty"] for p in json.load(open(sys.argv[1]))["positions"]},sort_keys=True))' \
  "$OPS/snapshot/data/state/fleet_mirror_slice.json") || die "cannot read EXPECT from the snapshot slice"
printf "JD=%s\nEXPECT='%s'\n" "$JD" "$EXPECT" > "$OPS/step2.env"
echo "STEP2 OK: JD=$JD image=$IMG EXPECT=$EXPECT ($(wc -l < "$OPS/snapshot_md5.txt" | tr -d ' ') files)"
