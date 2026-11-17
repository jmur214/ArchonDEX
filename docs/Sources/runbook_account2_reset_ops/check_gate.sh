#!/usr/bin/env bash
# Drive gate_live_clean.sh against the LOCAL fake S3. No AWS.
# usage: bash check_gate.sh        (exit 0 = every case behaves as the runbook says)
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"; . "$HERE/_fake_env.sh"
gate() { OUT=$(bash "$HERE/gate_live_clean.sh" 2>&1); RC=$?; }
archived() { world "${1:-DISABLED}"; bash "$HERE/archive.sh" >/dev/null 2>&1 || true; }

archived; gate
expect "$RC/$(has "$OUT" "GATE OK")" "0/yes" "1 after a clean archive: GATE OK"
archived; python3 -I - "$FAKE_SCHED" <<'PY'
import json, sys; s = json.load(open(sys.argv[1])); s["State"] = "ENABLED"; json.dump(s, open(sys.argv[1], "w"))
PY
gate
expect "$RC/$(has "$OUT" "not DISABLED")" "1/yes" "2 schedule re-enabled after the archive: STOP"
archived; echo '{"event": "init"}' > "$FAKE_S3/$PFX/data/paper_state/ledger.jsonl"; gate
expect "$RC/$(has "$OUT" "not clean")" "1/yes" "3 a stray run wrote a ledger after the archive: STOP"
archived; mkdir -p "$W/held"; mv "$FAKE_S3/$PFX/data/state/exec_cost_ledger.jsonl" "$W/held/"; gate
expect "$RC" "1" "4 empty live prefix (exec_cost missing too): STOP"
world DISABLED; gate
expect "$RC/$(has "$OUT" "not clean")" "1/yes" "5 nothing archived yet (all 10 keys live): STOP"

# 6 — runbook §7.6 end to end, "found BEFORE step 10": archive, a stray writes, R1, restore epoch 1.
archived
for k in data/paper_state/ledger.jsonl data/state/paper_heartbeat.json data/state/price_basis_marks.json; do
  echo "{\"stray\": \"$k\"}" > "$FAKE_S3/$PFX/$k"; done
gate; pre="$RC"
OPS1="$OPS"; OPS2="$OPS1/stray1"; mkdir -p "$OPS2/snapshot/data"
$AWS s3 cp --recursive "s3://$B/$PFX/data/" "$OPS2/snapshot/data/" --profile "$P" --region "$R" --no-progress
STRAY_RELS="$(cd "$OPS2/snapshot" && find data -type f ! -path data/state/exec_cost_ledger.jsonl | sort)"
OPS=$OPS2 RELS="$STRAY_RELS" ARCH=$PFX/archive_stray_${D}_1 ASIDE=$PFX/stray_aside_${D}_1 bash "$HERE/archive.sh" >/dev/null 2>&1; r1="$?"
gate; post="$RC"
OPS="$OPS1" RELS="$(cut -d' ' -f1 "$OPS1/MANIFEST_md5.txt")" bash "$HERE/restore.sh" >/dev/null 2>&1; rr="$?"
bad=0; for REL in $RELS; do cmp -s "$FAKE_S3/$PFX/$REL" "$OPS1/snapshot/$REL" || bad=$((bad+1)); done
expect "$pre/$(echo "$STRAY_RELS" | wc -l | tr -d ' ')/$r1/$post/$rr/$bad/$(n_files "$FAKE_S3/$PFX/stray_aside_${D}_1")" "1/3/0/0/0/0/3" \
  "6 stray before step 10: gate STOPs; R1 archives the 3 stray keys; gate OK; restore puts epoch 1 back byte-exact"

# 7–10 — a stray STILL RUNNING has written nothing yet: only the jobs list can see it.
refused=""
for st in SUBMITTED PENDING RUNNABLE STARTING RUNNING; do
  archived; printf "paper-offense-sso-day\tFAILED\npaper-offense-sso-day\t%s\n" "$st" > "$FAKE_JOBS"; gate
  [ "$RC/$(has "$OUT" "not yet terminal")" = "1/yes" ] && refused="$refused $st"
done
expect "$refused" " SUBMITTED PENDING RUNNABLE STARTING RUNNING" \
  "7 a job in flight on the jobdef (each of the 5 non-terminal statuses), live prefix still clean: STOP"
archived; printf "reset-a2-exec-2026-11-18\tSOMETHING_NEW\n" > "$FAKE_JOBS"; gate
expect "$RC/$(has "$OUT" "not yet terminal")" "1/yes" "8 an unknown job status: STOP (fail closed)"
archived; FAKE_FAIL=list_denied gate
expect "$RC/$(has "$OUT" "cannot list the jobs")" "1/yes" "9 list-jobs denied: STOP (a job in flight cannot be ruled out)"
archived; : > "$FAKE_JOBS"; gate
expect "$RC/$(has "$OUT" "GATE OK")" "0/yes" "10 no jobs at all on the jobdef: GATE OK"
finish
