#!/usr/bin/env python3
"""T-196 foundry-eval cloud submit. Runs D's BAKED run_foundry_eval_t195.py
in-cloud via a command-override (no rebuild); uploads the per-cell jsonl + log.

  python3 foundry_submit.py probe     # 1 candidate (mom_12_1) — measure wall-time
  python3 foundry_submit.py n5        # N=5 full-35-candidate sweeps (the real run)
"""
import json, subprocess, sys

PROFILE, REGION, QUEUE = "archondex", "us-east-1", "archondex-backtest-queue"
JOBDEF = "archondex-backtest-foundry-t196:1"

CMD = r"""
set -euo pipefail
export T195_OUT=/tmp/t195_foundry_eval.jsonl
echo "[cell] $ARCHONDEX_CELL_ID measured=$ARCHONDEX_MEASURED features=${T195_FEATURES:-ALL}"
python -m scripts.run_foundry_eval_t195 2>&1 | tee /tmp/t195.log
P="s3://$ARCHONDEX_RESULTS_BUCKET/$ARCHONDEX_CELL_ID"
aws s3 cp /tmp/t195_foundry_eval.jsonl "$P/t195_foundry_eval.jsonl" --only-show-errors || true
aws s3 cp /tmp/t195.log "$P/t195.log" --only-show-errors
echo "FOUNDRY-CELL-DONE $ARCHONDEX_CELL_ID"
"""


def submit(cell_id, extra_env=None):
    env = [
        {"name": "ARCHONDEX_CELL_ID", "value": cell_id},
        {"name": "ARCHONDEX_MEASURED", "value": "1"},
        {"name": "ARCHONDEX_HERMETIC", "value": "1"},
    ] + (extra_env or [])
    overrides = {"command": ["bash", "-lc", CMD], "environment": env}
    out = subprocess.run(
        ["aws", "batch", "submit-job", "--job-name", cell_id.replace("/", "-"),
         "--job-queue", QUEUE, "--job-definition", JOBDEF,
         "--region", REGION, "--profile", PROFILE,
         "--container-overrides", json.dumps(overrides),
         "--query", "jobId", "--output", "text"],
        capture_output=True, text=True)
    if out.returncode != 0:
        print("SUBMIT FAILED:", out.stderr[:400]); sys.exit(1)
    return out.stdout.strip()


mode = sys.argv[1] if len(sys.argv) > 1 else ""
if mode == "probe":
    jid = submit("foundry-t196/probe", [{"name": "T195_FEATURES", "value": "mom_12_1"}])
    open("/tmp/foundry_probe_jid.txt", "w").write(jid + "\n")
    print("probe:", jid)
elif mode == "n5":
    lines = []
    for rep in range(1, 6):
        jid = submit(f"foundry-t196/rep{rep}")
        lines.append(f"rep{rep}: {jid}")
        print(lines[-1])
    open("/tmp/foundry_n5_jobs.txt", "w").write("\n".join(lines) + "\n")
else:
    print("usage: foundry_submit.py probe|n5"); sys.exit(2)
