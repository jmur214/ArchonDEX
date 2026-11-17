#!/usr/bin/env bash
# Drive archive.sh against a LOCAL fake S3 (fake_aws.sh) in five scenarios. No AWS.
# Fixtures are SYNTHETIC one-line files, one per key — no real account state is used.
# usage: bash check_archive.sh        (exit 0 = all five scenarios behave as the runbook says)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
export P=placeholder-profile R=us-east-1 B=fakebucket PFX=paper_state_offense_sso D=2026-11-18
export ARCH=$PFX/archive_deploy_candidate_epoch1_$D ASIDE=$PFX/reset_aside_$D
export RELS="data/paper_state/ledger.jsonl data/paper_state/orders.jsonl data/paper_state/recon.jsonl data/state/deploy_candidate_tracking.json data/state/fleet_mirror_slice.json data/state/paper_alerts.log data/state/paper_heartbeat.json data/state/price_basis_marks.json data/state/tax_lots.jsonl"
export AWS="$HERE/fake_aws.sh"
ROOT="$(mktemp -d "${TMPDIR:-/tmp}/acct2_archive_check.XXXXXX")"
FAILS=0
setup() {
  W="$(mktemp -d "$ROOT/case.XXXX")"; export OPS="$W/ops" FAKE_S3="$W/s3"
  for REL in $RELS data/state/exec_cost_ledger.jsonl; do
    for base in "$OPS/snapshot" "$FAKE_S3/$PFX"; do
      mkdir -p "$(dirname "$base/$REL")"; echo "{\"synthetic\": \"$REL\"}" > "$base/$REL"
    done
  done
}
live_count() { find "$FAKE_S3/$PFX/data" -type f | wc -l | tr -d ' '; }
expect() { if [ "$1" = "$2" ]; then echo "PASS $3"; else echo "FAIL $3 (got '$1', want '$2')"; FAILS=$((FAILS+1)); fi; }

setup; FAKE_FAIL=none bash "$HERE/archive.sh" >/dev/null 2>&1; rc=$?
expect "$rc/$(live_count)/$(wc -l < "$OPS/MANIFEST_md5.txt" | tr -d ' ')/$(find "$FAKE_S3/$ASIDE" -type f | wc -l | tr -d ' ')/$(find "$FAKE_S3/$ARCH" -type f | wc -l | tr -d ' ')" \
       "0/1/9/9/9" "1 happy path: rc 0, only exec_cost live, 9 manifest rows, 9 aside, 9 archived"

setup; out=$(FAKE_FAIL=read_live bash "$HERE/archive.sh" 2>&1); rc=$?
expect "$rc/$(live_count)/$(echo "$out" | tail -1)" "1/10/STOP: read live data/paper_state/ledger.jsonl" \
       "2 live read denied: STOP at the first key, nothing moved"

setup; out=$(FAKE_FAIL=mv bash "$HERE/archive.sh" 2>&1); rc=$?
expect "$rc/$(live_count)/$(find "$FAKE_S3/$ARCH" -type f | wc -l | tr -d ' ')" "1/10/1" \
       "3 move denied: STOP, every live key still present, one archive copy"

setup; echo '{"x":1}' >> "$FAKE_S3/$PFX/data/paper_state/ledger.jsonl"
out=$(FAKE_FAIL=none bash "$HERE/archive.sh" 2>&1); rc=$?
case "$out" in *"differs from the step-1 snapshot"*) m=yes;; *) m=no;; esac
expect "$rc/$(live_count)/$m" "1/10/yes" "4 live changed since the snapshot: STOP, nothing moved"

setup; mv "$FAKE_S3/$PFX/data/paper_state/ledger.jsonl" "$W/ledger.held_outside_fake_s3"
out=$(FAKE_FAIL=none bash "$HERE/archive.sh" 2>&1); rc=$?
expect "$rc/$(live_count)/$(echo "$out" | tail -1)" "1/9/STOP: read live data/paper_state/ledger.jsonl" \
       "5 live key missing (the reviewer's empty-md5 case): STOP, nothing moved"

echo "fixtures under $ROOT (synthetic; left in place)"
[ "$FAILS" = 0 ] && echo "ALL PASS" || echo "$FAILS FAIL(S)"
exit "$FAILS"
