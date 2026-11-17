"""Mutation harness (adapted from the delta reviewer's run_mut.py, 2026-11-17): copy THIS folder to
a fresh temp dir per mutant, apply one textual mutation, run the check that guards that file.
A mutant is CAUGHT when the check exits non-zero. EQUIVALENT mutants are declared below with the
reason they cannot be caught; every other mutant must be CAUGHT.
usage: python3 mutate.py        (exit 0 = every non-equivalent mutant caught; prints the table)
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SRC = Path(__file__).resolve().parent
PY = sys.executable
CHECK = {"archive.sh": ["bash", "check_archive.sh"], "restore.sh": ["bash", "check_restore.sh"],
         "gate_live_clean.sh": ["bash", "check_gate.sh"], "step2_snapshot.sh": ["bash", "check_step2.sh"],
         "sched_state.py": [PY, "-I", "check_sched_state.py"], "reset_a2.tmpl.py": [PY, "-I", "check_reset_a2.py"],
         "render.py": [PY, "-I", "check_reset_a2.py"], "postcheck_a2.tmpl.py": [PY, "-I", "check_postcheck.py"]}
OFF = ("true || die", )  # what a dropped refusal is replaced by
M = [  # (name, file, [(old, new), ...]) — the first 31 are the reviewer's list (texts updated where the file changed)
 ("archive: drop pipefail", "archive.sh", [("set -uo pipefail", "set -u")]),
 ("archive: drop live==snapshot compare", "archive.sh", [('  [ "$L" = "$S" ] || die', '  true || die')]),
 ("archive: drop archive==snapshot compare", "archive.sh", [('  [ "$A" = "$S" ] || die', '  true || die')]),
 ("archive: drop ETag compare", "archive.sh", [('  [ "$E" = "$S" ] || die', '  true || die')]),
 ("archive: drop BOTH archive compares (A and ETag)", "archive.sh", [('  [ "$A" = "$S" ] || die', '  true || die'), ('  [ "$E" = "$S" ] || die', '  true || die')]),
 ("archive: drop empty-md5 refusal", "archive.sh", [('  [ "$S" != "$EMPTY" ] || die', '  true || die')]),
 ("archive: drop empty-md5 refusal AND -s check", "archive.sh", [('  [ "$S" != "$EMPTY" ] || die', '  true || die'), ('  [ -s "$SNAP" ] || die', '  true || die')]),
 ("archive: drop pipefail AND live compare", "archive.sh", [("set -uo pipefail", "set -u"), ('  [ "$L" = "$S" ] || die', '  true || die')]),
 ("archive: mv before verification (move first)", "archive.sh", "MOVE_FIRST"),
 ("reset: 30-min -> 20-min", "reset_a2.tmpl.py", [("if mins_left < 30:", "if mins_left < 20:")]),
 ("reset: drop 30-min refusal", "reset_a2.tmpl.py", [("if mins_left < 30:", "if False:")]),
 ("reset: drop 2026-11-27 exclusion", "reset_a2.tmpl.py", [('NO_TRADE_DATES = {"2026-11-26", "2026-11-27"}', 'NO_TRADE_DATES = {"2026-11-26"}')]),
 ("reset: drop 2026-11-26 exclusion", "reset_a2.tmpl.py", [('NO_TRADE_DATES = {"2026-11-26", "2026-11-27"}', 'NO_TRADE_DATES = {"2026-11-27"}')]),
 ("reset: drop broker-date==D check", "reset_a2.tmpl.py", [("if et_now.date().isoformat() != D:", "if False:")]),
 ("reset: coid without attempt suffix", "reset_a2.tmpl.py", [('-sell-a{ATTEMPT}"', '-sell"')]),
 ("reset: attempt suffix hard-coded a1", "reset_a2.tmpl.py", [('-sell-a{ATTEMPT}"', '-sell-a1"')]),
 ("reset: per-order failure not recorded", "reset_a2.tmpl.py", [("        failed.append(t)\n", "        pass\n")]),
 ("reset: no per-order try/except (stop on first)", "reset_a2.tmpl.py", [("    try:\n        inspect", "    if True:\n        inspect"), ("    except Exception as exc:                          # one failure never hides the others\n        failed.append(t)\n        print(f\"RESET-A2 FAILED {t}: {type(exc).__name__}: {str(exc)[:200]}\")\n", "")]),
 ("reset: drop EXPECT compare", "reset_a2.tmpl.py", [("if pos != EXPECT:", "if False:")]),
 ("reset: drop open-order refusal", "reset_a2.tmpl.py", [("if open_o:", "if False:")]),
 ("reset: drop market-closed refusal", "reset_a2.tmpl.py", [("if not clock.is_open:", "if False:")]),
 ("reset: EXECUTE ignored (always submit)", "reset_a2.tmpl.py", [("        if EXECUTE:", "        if True:")]),
 ("postcheck: coid without attempt suffix", "postcheck_a2.tmpl.py", [('-sell-a{ATTEMPT}"', '-sell"')]),
 ("postcheck: FLAT ignores open orders", "postcheck_a2.tmpl.py", [('print("FLAT=%s" % (not pos and not op))', 'print("FLAT=%s" % (not pos))')]),
 ("sched: drop pin check", "sched_state.py", [("if jd != expect:", "if False:")]),
 ("sched: drop revision-pinned check", "sched_state.py", [('if ":" not in jd:', "if False:")]),
 ("sched: drop DLQ check", "sched_state.py", [('if not (tgt.get("DeadLetterConfig") or {}).get("Arn"):', "if False:")]),
 ("sched: drop retry check", "sched_state.py", [('if tgt.get("RetryPolicy") != {"MaximumEventAgeInSeconds": 3600, "MaximumRetryAttempts": 3}:', "if False:")]),
 ("sched: also rewrite Target pin to expect", "sched_state.py", [('s["State"] = state', 's["State"] = state; tgt["Input"] = tgt["Input"].replace(jd, expect)')]),
 ("sched: keep read-only keys", "sched_state.py", [('for k in ("Arn", "CreationDate", "LastModificationDate", "Version"):\n    s.pop(k, None)', 'pass')]),
 ("sched: also drop FlexibleTimeWindow", "sched_state.py", [('s["State"] = state', 's["State"] = state; s.pop("FlexibleTimeWindow", None)')]),
 # --- added for the delta review's N1–N5 ------------------------------------------------- #
 ("archive: drop schedule-DISABLED refusal", "archive.sh", [('[ "$ST" = "DISABLED" ] || die', 'true || die')]),
 ("archive: drop existing-manifest refusal", "archive.sh", [('[ ! -e "$OPS/MANIFEST_md5.txt" ] || die', 'true || die')]),
 ("archive: drop archive-key-occupied refusal", "archive.sh", [('  absent "$ARCH/$REL" || die', '  true || die')]),
 ("archive: drop aside-key-occupied refusal", "archive.sh", [('  absent "$ASIDE/$REL" || die', '  true || die')]),
 ("archive: any head-object error counts as absent", "archive.sh", [('*) die "cannot prove $1 absent: ${err:-no error text}" ;;', '*) return 0 ;;')]),
 ("archive: drop the -s snapshot check alone", "archive.sh", [('  [ -s "$SNAP" ] || die', '  true || die')]),
 ("restore: drop pipefail", "restore.sh", [("set -uo pipefail", "set -u")]),
 ("restore: drop schedule-DISABLED refusal", "restore.sh", [('[ "$ST" = "DISABLED" ] || die', 'true || die')]),
 ("restore: drop occupied-destination refusal", "restore.sh", [('  absent "$PFX/$REL" || die', '  true || die')]),
 ("restore: drop aside==archive compare", "restore.sh", [('  [ "$X" = "$A" ] || die', '  true || die')]),
 ("restore: drop post-move compare", "restore.sh", [('  [ "$L" = "$A" ] || die', '  true || die')]),
 ("restore: drop empty-archive refusal", "restore.sh", [('  [ "$A" != "$EMPTY" ] || die', '  true || die')]),
 ("restore: drop empty-RELS refusal", "restore.sh", [('[ -n "$RELS" ] || die', 'true || die')]),
 ("restore: any head-object error counts as absent", "restore.sh", [('*) die "cannot prove $1 absent: ${err:-no error text}" ;;', '*) return 0 ;;')]),
 ("gate: drop schedule-DISABLED refusal", "gate_live_clean.sh", [('[ "$ST" = "DISABLED" ] || die', 'true || die')]),
 ("gate: drop the clean-prefix compare", "gate_live_clean.sh", [('[ "$KEYS" = "$PFX/data/state/exec_cost_ledger.jsonl" ] \\\n  || die', 'true \\\n  || die')]),
 ("gate: accept any listing that CONTAINS exec_cost", "gate_live_clean.sh", [('[ "$KEYS" = "$PFX/data/state/exec_cost_ledger.jsonl" ]', '[[ "$KEYS" == *exec_cost_ledger.jsonl* ]]')]),
 # --- added for the final check's minor 1 (a stray still RUNNING) ------------------------ #
 ("gate: drop the in-flight-job refusal", "gate_live_clean.sh", [('[ -z "$INFLIGHT" ] || die', 'true || die')]),
 ("gate: ignore a list-jobs error", "gate_live_clean.sh", [('|| die "cannot list the jobs on $JDNAME', '|| true "cannot list the jobs on $JDNAME')]),
 ("gate: filter by job NAME instead of jobdef", "gate_live_clean.sh", [('"name=JOB_DEFINITION,values=$JDNAME"', '"name=JOB_NAME,values=$JDNAME"')]),
 ("gate: only RUNNING counts as in flight", "gate_live_clean.sh", [("awk 'NF && $2 != \"SUCCEEDED\" && $2 != \"FAILED\"'", "awk 'NF && $2 == \"RUNNING\"'")]),
 ("gate: allow-list the 5 statuses (unknown passes)", "gate_live_clean.sh", [("awk 'NF && $2 != \"SUCCEEDED\" && $2 != \"FAILED\"'", "awk 'NF && $2 ~ /^(SUBMITTED|PENDING|RUNNABLE|STARTING|RUNNING)$/'")]),
 ("step2: drop fresh-OPS refusal", "step2_snapshot.sh", [('[ ! -e "$OPS/snapshot" ] || die', 'true || die')]),
 ("step2: drop pin==latest-revision check", "step2_snapshot.sh", [('[ "$JD" = "$JDNAME:$REV" ] || die', 'true || die')]),
 ("step2: drop image check", "step2_snapshot.sh", [('*) die "latest ACTIVE image $IMG is not $EXPECT_IMAGE" ;;', '*) true ;;')]),
 ("step2: ignore a failed snapshot copy", "step2_snapshot.sh", [('--no-progress > /dev/null || die "snapshot copy', '--no-progress > /dev/null || true "snapshot copy')]),
 ("reset: drop the 10:00 ET refusal", "reset_a2.tmpl.py", [("if (et_now.hour, et_now.minute) < (10, 0):", "if False:")]),
 ("reset: 10:00 ET -> 09:30 ET", "reset_a2.tmpl.py", [("< (10, 0):", "< (9, 30):")]),
 ("reset: read the broker clock without converting to ET", "reset_a2.tmpl.py", [("et_now = clock.timestamp.astimezone(ET)", "et_now = clock.timestamp")]),
 ("postcheck: attempt suffix hard-coded a1", "postcheck_a2.tmpl.py", [('-sell-a{ATTEMPT}"', '-sell-a1"')]),
 ("postcheck: drop the CLOCK line", "postcheck_a2.tmpl.py", [('print("CLOCK " + json.dumps(', 'print("NOCLOCK " + json.dumps(')]),
 ("render: drop the unfilled-placeholder refusal", "render.py", [("assert not left,", "assert True,")]),
 ("render: drop value validation", "render.py", [("assert k in checks and checks[k](v),", "assert True,")]),
]
EQUIVALENT = {
    "archive: drop empty-md5 refusal":
        "the `[ -s \"$SNAP\" ]` line above it already refuses an empty snapshot; a NON-empty file whose md5 "
        "is the empty-file md5 is an md5 preimage — unreachable. Kept as defence in depth.",
    "sched: also rewrite Target pin to expect":
        "the line runs only after `if jd != expect: sys.exit(...)`, so jd == expect there and "
        "`replace(jd, expect)` is the identity — the output is byte-identical.",
}


def apply(text, subs):
    if subs == "MOVE_FIRST":   # move the 2-line mv right after the live compare (the reviewer's mutant)
        lines = text.split("\n")
        i = [j for j, l in enumerate(lines) if l.startswith("  $AWS s3 mv")][0]
        block = lines[i:i + 2]; del lines[i:i + 2]
        k = [j for j, l in enumerate(lines) if l.startswith('  [ "$L" = "$S" ]')][0] + 1
        lines[k:k] = block
        return "\n".join(lines)
    for old, new in subs:
        if old not in text:
            return None
        text = text.replace(old, new, 1)
    return text


def main():
    base = Path(tempfile.mkdtemp(prefix="acct2_mutants."))
    env = dict(os.environ, TMPDIR=str(base / "tmp") + "/", PYTHONDONTWRITEBYTECODE="1")
    (base / "tmp").mkdir()
    rows, bad = [], 0
    for i, (name, f, subs) in enumerate(M):
        d = base / f"m{i:02d}"
        shutil.copytree(SRC, d)
        src = (d / f).read_text()
        mutated = apply(src, subs)
        if mutated is None or mutated == src:
            rows.append((name, "NOT-APPLIED", "")); bad += 1; continue
        (d / f).write_text(mutated)
        r = subprocess.run(CHECK[f], cwd=d, env=env, capture_output=True, text=True, timeout=600)
        first = next((l for l in (r.stdout + r.stderr).splitlines() if l.startswith("FAIL")), "")
        if name in EQUIVALENT:
            verdict = "EQUIVALENT" + (" (but caught)" if r.returncode else "")
        else:
            verdict = "CAUGHT" if r.returncode else "NOT CAUGHT"
            bad += 0 if r.returncode else 1
        rows.append((name, verdict, first[:100]))
    for name, verdict, why in rows:
        print(f"{verdict:<12} | {name}" + (f"  — {why}" if why else ""))
    for name, reason in EQUIVALENT.items():
        print(f"EQUIVALENT: {name}: {reason}")
    n_eq = sum(1 for n, *_ in M if n in EQUIVALENT)
    print(f"{len(M)} mutants: {sum(v == 'CAUGHT' for _, v, _ in rows)} caught, {n_eq} declared equivalent, "
          f"{bad} not caught / not applied   (work under {base})")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
