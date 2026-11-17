#!/usr/bin/env bash
# Drive restore.sh (after a real archive.sh run) against the LOCAL fake S3. No AWS.
# usage: bash check_restore.sh        (exit 0 = every case behaves as the runbook says)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; . "$HERE/_fake_env.sh"
A1=data/paper_state/ledger.jsonl
archived() { world DISABLED; bash "$HERE/archive.sh" >/dev/null 2>&1 || { echo "FAIL setup: archive.sh"; FAILS=$((FAILS+1)); }; }
restore() { OUT=$(RELS="$(cut -d' ' -f1 "$OPS/MANIFEST_md5.txt")" bash "$HERE/restore.sh" 2>&1); RC=$?; }
same_as_snapshot() {  # every manifest key back live with its snapshot bytes
  local bad=0; for REL in $(cut -d' ' -f1 "$OPS/MANIFEST_md5.txt"); do
    cmp -s "$FAKE_S3/$PFX/$REL" "$OPS/snapshot/$REL" || bad=$((bad+1)); done; echo "$bad"; }

archived; restore
expect "$RC/$(live_n)/$(aside_n)/$(arch_n)/$(same_as_snapshot)" "0/10/0/9/0" \
  "1 happy path: all 9 back live with their snapshot bytes; aside empty; the archive keeps 9"
archived; echo '{"stray": true}' > "$FAKE_S3/$PFX/$A1"; restore
expect "$RC/$(cat "$FAKE_S3/$PFX/$A1")/$(aside_n)/$(has "$OUT" "is occupied")" '1/{"stray": true}/9/yes' \
  "2 occupied destination (a stray wrote it): STOP, the stray untouched, nothing moved back"
archived; echo tampered >> "$FAKE_S3/$ASIDE/$A1"; restore
expect "$RC/$(live_n)/$(has "$OUT" "!= archive copy")" "1/1/yes" "3 aside differs from its archive copy: STOP, nothing moved back"
archived; python3 -I - "$FAKE_SCHED" <<'PY'
import json, sys; s = json.load(open(sys.argv[1])); s["State"] = "ENABLED"; json.dump(s, open(sys.argv[1], "w"))
PY
restore
expect "$RC/$(live_n)/$(has "$OUT" "not DISABLED")" "1/1/yes" "4 schedule ENABLED: STOP, nothing moved back"
archived; mkdir -p "$W/held"; mv "$FAKE_S3/$ARCH/$A1" "$W/held/"; restore
expect "$RC/$(live_n)/$(echo "$OUT" | tail -1)" "1/1/STOP: read archive $A1" \
  "5 archive copy unreadable: STOP on the read (pipefail), nothing moved back"
world DISABLED; RELS="data/paper_state/ledger.jsonl data/paper_state/orders.jsonl data/paper_state/recon.jsonl" \
  bash "$HERE/archive.sh" >/dev/null 2>&1; restore
expect "$RC/$(live_n)/$(aside_n)/$(same_as_snapshot)" "0/10/0/0" \
  "6 partial archive (3 keys): the manifest-driven restore puts back exactly those 3"
archived; OUT=$(RELS="" bash "$HERE/restore.sh" 2>&1); RC=$?
expect "$RC/$(has "$OUT" "RELS is empty")" "1/yes" "7 empty RELS: STOP"
archived; FAKE_FAIL=corrupt_mv restore
expect "$RC/$(has "$OUT" "restored $A1 (")" "1/yes" "8 the move back lands different bytes: STOP on the post-move compare"
archived; FAKE_FAIL=head_denied restore
expect "$RC/$(aside_n)/$(has "$OUT" "cannot prove")" "1/9/yes" "9 head-object denied (absence unprovable): STOP, nothing moved back"
archived; : > "$FAKE_S3/$ARCH/$A1"; : > "$FAKE_S3/$ASIDE/$A1"; restore
expect "$RC/$(live_n)/$(has "$OUT" "archive copy of $A1 is empty")" "1/1/yes" \
  "10 archive AND aside copies both empty: STOP (equal-but-empty is not a restore)"
finish
