"""Check sched_state.py on a SYNTHETIC schedule JSON shaped like `aws scheduler get-schedule`
for archondex-paper-offense-sso-daily (AWS account id replaced by the placeholder 000000000000).
usage: python3 check_sched_state.py        (exit 0 = all cases behave)
"""
import copy
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACCT = "000000000000"                      # placeholder, never a real account id
LIVE = {
    "ActionAfterCompletion": "NONE",
    "Arn": f"arn:aws:scheduler:us-east-1:{ACCT}:schedule/default/archondex-paper-offense-sso-daily",
    "CreationDate": "2026-07-09T13:07:52.609000-05:00",
    "FlexibleTimeWindow": {"Mode": "OFF"},
    "GroupName": "default",
    "LastModificationDate": "2026-11-13T23:54:12.139000-06:00",
    "Name": "archondex-paper-offense-sso-daily",
    "ScheduleExpression": "cron(50 9 ? * MON-FRI *)",
    "ScheduleExpressionTimezone": "America/New_York",
    "State": "ENABLED",
    "Target": {
        "Arn": "arn:aws:scheduler:::aws-sdk:batch:submitJob",
        "DeadLetterConfig": {"Arn": f"arn:aws:sqs:us-east-1:{ACCT}:archondex-scheduler-dlq"},
        "Input": json.dumps({"JobName": "paper-offense-sso-day",
                             "JobQueue": f"arn:aws:batch:us-east-1:{ACCT}:job-queue/archondex-backtest-queue",
                             "JobDefinition": f"arn:aws:batch:us-east-1:{ACCT}:job-definition/archondex-paper-offense-sso:21"}),
        "RetryPolicy": {"MaximumEventAgeInSeconds": 3600, "MaximumRetryAttempts": 3},
        "RoleArn": f"arn:aws:iam::{ACCT}:role/archondex-paper-scheduler-role",
    },
}
fails = 0


def case(name, live, state, expect, want_rc):
    global fails
    with tempfile.TemporaryDirectory() as d:
        lp, op = Path(d) / "live.json", Path(d) / "out.json"
        lp.write_text(json.dumps(live))
        r = subprocess.run([sys.executable, "-I", str(HERE / "sched_state.py"), str(lp), state, expect, str(op)],
                           capture_output=True, text=True)
        ok = (r.returncode == 0) == (want_rc == 0)
        if ok and want_rc == 0:
            out = json.loads(op.read_text())
            base = {k: v for k, v in live.items() if k not in ("Arn", "CreationDate", "LastModificationDate")}
            diff = sorted(k for k in set(base) | set(out) if base.get(k) != out.get(k))
            want = ["State"] if live["State"] != state else []      # nothing but State may move
            ok = diff == want and out["State"] == state and out["Target"] == live["Target"]
        print(("PASS " if ok else "FAIL ") + name + f" (rc={r.returncode}: {(r.stdout or r.stderr).strip()[:110]})")
        fails += 0 if ok else 1


case("disable at the live pin: only State changes", LIVE, "DISABLED", "archondex-paper-offense-sso:21", 0)
case("enable at the live pin (already ENABLED): output identical but for the dropped keys", LIVE, "ENABLED",
     "archondex-paper-offense-sso:21", 0)
off = copy.deepcopy(LIVE); off["State"] = "DISABLED"
case("re-enable a DISABLED schedule: only State changes", off, "ENABLED", "archondex-paper-offense-sso:21", 0)
case("expected :22 vs live :21 refuses (finding 1)", LIVE, "ENABLED", "archondex-paper-offense-sso:22", 1)
nodlq = copy.deepcopy(LIVE); del nodlq["Target"]["DeadLetterConfig"]
case("no DLQ refuses", nodlq, "DISABLED", "archondex-paper-offense-sso:21", 1)
slow = copy.deepcopy(LIVE); slow["Target"]["RetryPolicy"] = {"MaximumEventAgeInSeconds": 86400, "MaximumRetryAttempts": 185}
case("non-fast-fail retry refuses", slow, "DISABLED", "archondex-paper-offense-sso:21", 1)
unpinned = copy.deepcopy(LIVE)
unpinned["Target"]["Input"] = unpinned["Target"]["Input"].replace("archondex-paper-offense-sso:21", "archondex-paper-offense-sso")
case("revisionless target refuses", unpinned, "DISABLED", "archondex-paper-offense-sso", 1)
print("ALL PASS" if not fails else f"{fails} FAIL(S)")
sys.exit(1 if fails else 0)
