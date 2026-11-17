#!/usr/bin/env bash
# Drive archive.sh against the LOCAL fake S3 (fake_aws.sh) on SYNTHETIC fixtures. No AWS.
# usage: bash check_archive.sh        (exit 0 = every case behaves as the runbook says)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; . "$HERE/_fake_env.sh"
A1=data/paper_state/ledger.jsonl
run() { OUT=$(bash "$HERE/archive.sh" 2>&1); RC=$?; }

world DISABLED; run
expect "$RC/$(live_n)/$(wc -l < "$OPS/MANIFEST_md5.txt" | tr -d ' ')/$(aside_n)/$(arch_n)" "0/1/9/9/9" \
  "1 happy path: rc 0, only exec_cost live, 9 manifest rows, 9 aside, 9 archived"
expect "$(awk 'NF!=3' "$OPS/MANIFEST_md5.txt" | wc -l | tr -d ' ')" "0" "1b manifest rows are '<rel> <bytes> <md5>'"
world DISABLED; FAKE_FAIL=read_live run
expect "$RC/$(live_n)/$(echo "$OUT" | tail -1)" "1/10/STOP: read live $A1" "2 live read denied: STOP at the first key, nothing moved"
world DISABLED; FAKE_FAIL=mv run
expect "$RC/$(live_n)/$(arch_n)/$(has "$OUT" "move-aside $A1")" "1/10/1/yes" "3 move denied: STOP, every live key present, one archive copy"
world DISABLED; echo '{"x":1}' >> "$FAKE_S3/$PFX/$A1"; run
expect "$RC/$(live_n)/$(has "$OUT" "differs from the step-2 snapshot")" "1/10/yes" "4 live changed since the snapshot: STOP, nothing moved"
world DISABLED; mkdir -p "$W/held"; mv "$FAKE_S3/$PFX/$A1" "$W/held/"; run
expect "$RC/$(live_n)/$(echo "$OUT" | tail -1)" "1/9/STOP: read live $A1" "5 live key missing (the empty-md5 case): STOP, nothing moved"
world DISABLED; FAKE_FAIL=corrupt_copy run
expect "$RC/$(live_n)/$(has "$OUT" "archive copy of $A1 (")" "1/10/yes" "6 corrupted archive copy: STOP on the md5 compare, nothing moved"
world DISABLED; FAKE_FAIL=etag_wrong run
expect "$RC/$(live_n)/$(has "$OUT" "archive ETag of $A1")" "1/10/yes" "7 wrong archive ETag (bytes fine): STOP on the ETag compare, nothing moved"
world DISABLED; : > "$OPS/snapshot/$A1"; : > "$FAKE_S3/$PFX/$A1"; run
expect "$RC/$(live_n)/$(has "$OUT" "no non-empty step-2 snapshot for $A1")" "1/10/yes" "8 empty snapshot AND empty live: STOP on the -s check"
world ENABLED; run
expect "$RC/$(arch_n)/$(has "$OUT" "not DISABLED")" "1/0/yes" "9 schedule ENABLED: STOP before anything is copied"
world DISABLED; mkdir -p "$OPS"; echo "x 1 y" > "$OPS/MANIFEST_md5.txt"; run
expect "$RC/$(arch_n)/$(has "$OUT" "MANIFEST_md5.txt exists")" "1/0/yes" "10 manifest already present (a re-run): STOP, nothing copied"
world DISABLED; mkdir -p "$(dirname "$FAKE_S3/$ARCH/$A1")"; echo prior > "$FAKE_S3/$ARCH/$A1"; run
expect "$RC/$(cat "$FAKE_S3/$ARCH/$A1")/$(live_n)/$(has "$OUT" "refusing to overwrite an archive")" "1/prior/10/yes" \
  "11 archive key already occupied: STOP, the prior archive object untouched"
world DISABLED; mkdir -p "$(dirname "$FAKE_S3/$ASIDE/$A1")"; echo prior > "$FAKE_S3/$ASIDE/$A1"; run
expect "$RC/$(cat "$FAKE_S3/$ASIDE/$A1")/$(live_n)/$(has "$OUT" "aside key")" "1/prior/10/yes" \
  "12 aside key already occupied: STOP, the prior aside object untouched"
world DISABLED; FAKE_FAIL=head_denied run
expect "$RC/$(arch_n)/$(live_n)/$(has "$OUT" "cannot prove")" "1/0/10/yes" \
  "13 head-object denied (absence unprovable): STOP before any copy"
finish
