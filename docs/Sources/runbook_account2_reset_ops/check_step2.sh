#!/usr/bin/env bash
# Drive step2_snapshot.sh against the LOCAL fake S3 / schedule / jobdef. No AWS.
# usage: bash check_step2.sh        (exit 0 = every case behaves as the runbook says)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; . "$HERE/_fake_env.sh"
step2() { OUT=$(bash "$HERE/step2_snapshot.sh" 2>&1); RC=$?; }

world ENABLED nosnap; step2
expect "$RC/$(wc -l < "$OPS/snapshot_md5.txt" | tr -d ' ')/$(grep -c . "$OPS/step2.env")" "0/10/2" \
  "1 happy path: 10 files snapshotted and hashed, step2.env written"
expect "$(. "$OPS/step2.env"; echo "$JD|$EXPECT")" 'archondex-paper-offense-sso:21|{"MTUM": 92, "SGOV": 6, "VOO": 12}' \
  "1b step2.env carries the live pin and EXPECT from the snapshot slice"
expect "$(cmp -s "$OPS/snapshot/data/paper_state/ledger.jsonl" "$FAKE_S3/$PFX/data/paper_state/ledger.jsonl" && echo same)" "same" \
  "1c the snapshot bytes equal the live bytes"
world ENABLED nosnap; FAKE_REV=22 step2
expect "$RC/$(has "$OUT" "not the latest ACTIVE revision")" "1/yes" "2 a newer ACTIVE revision than the schedule pin: STOP"
world ENABLED nosnap; FAKE_IMAGE="000000000000.dkr.ecr.us-east-1.amazonaws.com/archondex-backtest:paper-sha-0000000" step2
expect "$RC/$(has "$OUT" "is not paper-sha-716ca04")" "1/yes" "3 the latest image is not EXPECT_IMAGE: STOP"
world ENABLED; step2
expect "$RC/$(has "$OUT" "snapshot exists")" "1/yes" "4 an OPS dir that already holds a snapshot: STOP"
world ENABLED nosnap; FAKE_FAIL=read_live; mv "$FAKE_S3/$PFX" "$W/held_prefix"; step2
expect "$RC/$(has "$OUT" "snapshot copy")" "1/yes" "5 the live prefix cannot be copied: STOP"
finish
