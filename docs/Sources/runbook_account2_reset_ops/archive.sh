#!/usr/bin/env bash
# Archive account-2 epoch-1 state: per key, prove the LIVE object is still the step-1
# snapshot, copy it to the dated archive prefix, prove the copy, then move the original
# aside. Never deletes. Any failure exits non-zero BEFORE the next key is touched.
# Required env: B PFX ARCH ASIDE OPS RELS (and P R for the aws profile/region).
set -uo pipefail
AWS="${AWS:-aws}"
EMPTY=d41d8cd98f00b204e9800998ecf8427e
die() { echo "STOP: $*" >&2; exit 1; }
for REL in $RELS; do
  SNAP="$OPS/snapshot/$REL"
  [ -s "$SNAP" ] || die "no non-empty step-1 snapshot for $REL"
  S=$(md5 -q "$SNAP") || die "md5 of snapshot $REL"
  [ "$S" != "$EMPTY" ] || die "snapshot md5 is the empty-file md5 for $REL"
  L=$($AWS s3 cp "s3://$B/$PFX/$REL" - --profile "$P" --region "$R" | md5 -q) || die "read live $REL"
  [ "$L" = "$S" ] || die "live $REL ($L) differs from the step-1 snapshot ($S) — something wrote it"
  $AWS s3 cp "s3://$B/$PFX/$REL" "s3://$B/$ARCH/$REL" --profile "$P" --region "$R" --no-progress \
    || die "archive copy $REL"
  A=$($AWS s3 cp "s3://$B/$ARCH/$REL" - --profile "$P" --region "$R" | md5 -q) || die "read archive $REL"
  [ "$A" = "$S" ] || die "archive copy of $REL ($A) != snapshot ($S)"
  E=$($AWS s3api head-object --bucket "$B" --key "$ARCH/$REL" --query ETag --output text \
        --profile "$P" --region "$R" | tr -d '"') || die "head-object archive $REL"
  [ "$E" = "$S" ] || die "archive ETag of $REL ($E) != snapshot md5 ($S)"
  BYTES=$(wc -c < "$SNAP" | tr -d ' ')
  $AWS s3 mv "s3://$B/$PFX/$REL" "s3://$B/$ASIDE/$REL" --profile "$P" --region "$R" --no-progress \
    || die "move-aside $REL (archive copy exists; live key untouched or partially moved — check both)"
  echo "$REL $BYTES $S" >> "$OPS/MANIFEST_md5.txt"
  echo "archived+aside $REL $BYTES $S"
done
echo "DONE: all keys archived and moved aside"
