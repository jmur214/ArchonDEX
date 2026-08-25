#!/usr/bin/env python
"""Diff the CHECKED-IN paper-fleet templates against the LIVE AWS resources.

READ-ONLY. Run this BEFORE any provisioning/redeploy touch.

Why it exists (the rule it mechanises — `feedback_deploy_template_vs_live_drift_2026_07_28`):
a fix applied by hand to a live resource and never written back is invisible to the
template, so the next "just re-run the provisioner" SILENTLY REVERTS it while every
log line still reads success. This has now bitten three separate resources:

  * the exec-role secret policy   — a live `archondex/anthropic-api` grant the
    template did not render (a blind PUT = a fleet-wide LLM blackout)
  * the fleet schedules           — live DeadLetterConfig + fast-fail RetryPolicy
    the template did not render (a blind write = no DLQ, and AWS's 185-retry
    default restored, which is the shape of the July silent outage)
  * the job-role S3 policy        — each new state prefix must be granted
    EXPLICITLY or every push is silently AccessDenied

Memory is not a control. This is.

Usage:  python scripts/diff_live_paper_infra.py
Exit:   0 = no drift, 1 = drift found (each difference printed).
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROFILE, REGION = "archondex", "us-east-1"
ACCOUNT = "407539788432"
BUCKET = f"archondex-results-{ACCOUNT}"
EXEC_ROLE, JOB_ROLE = "archondex-paper-exec-role", "archondex-paper-job-role"
ROOT = Path(__file__).resolve().parents[1]

# Every schedule that must carry the July lessons: revision-PINNED jobdef ARN,
# a DLQ, and a fast-fail retry policy.
SCHEDULES = ["archondex-paper-daily", "archondex-paper-offense-sso-daily",
             "archondex-paper-btc-sleeve-daily", "archondex-paper-ai-trader-daily"]
FAST_FAIL = {"MaximumEventAgeInSeconds": 3600, "MaximumRetryAttempts": 3}


def aws(*args):
    r = subprocess.run(["aws", *args, "--profile", PROFILE, "--region", REGION],
                       capture_output=True, text=True)
    return (r.returncode, r.stdout.strip(), r.stderr.strip())


def _report(findings, what, detail):
    findings.append(f"{what}: {detail}")
    print(f"  DRIFT  {what}\n         {detail}")


def check_job_role(findings) -> None:
    print("== job-role S3 policy (template vs live) ==")
    tmpl = json.loads(
        (ROOT / "infra/paper_cloud/iam_job_role_policy.json").read_text()
        .replace("__RESULTS_BUCKET__", BUCKET))
    names = aws("iam", "list-role-policies", "--role-name", JOB_ROLE,
                "--query", "PolicyNames[0]", "--output", "text")[1]
    rc, out, err = aws("iam", "get-role-policy", "--role-name", JOB_ROLE,
                       "--policy-name", names, "--query", "PolicyDocument",
                       "--output", "json")
    if rc != 0:
        return _report(findings, "job-role policy", f"unreadable: {err[:160]}")
    live = json.loads(out)
    t = {s["Sid"]: s for s in tmpl["Statement"] if "Sid" in s}
    lv = {s["Sid"]: s for s in live.get("Statement", []) if "Sid" in s}
    for sid in sorted(set(t) | set(lv)):
        if sid not in lv:
            _report(findings, f"job-role/{sid}", "in template, ABSENT live")
        elif sid not in t:
            _report(findings, f"job-role/{sid}", "LIVE ONLY — a hand-fix never written back")
        elif json.dumps(t[sid], sort_keys=True) != json.dumps(lv[sid], sort_keys=True):
            _report(findings, f"job-role/{sid}",
                    f"differs\n           template={json.dumps(t[sid], sort_keys=True)[:400]}"
                    f"\n           live    ={json.dumps(lv[sid], sort_keys=True)[:400]}")
    if not findings:
        print("  ok — template matches live")


def check_exec_role(findings) -> None:
    """The exec-role policy is legitimately a SUPERSET of what any one script
    renders, so the check is one-directional: nothing may be MISSING, and the
    provisioner must never PUT a document that drops a live grant."""
    print("== exec-role secret grants (live inventory) ==")
    rc, out, _ = aws("iam", "get-role-policy", "--role-name", EXEC_ROLE,
                     "--policy-name", "read-alpaca-paper-secret",
                     "--query", "PolicyDocument", "--output", "json")
    if rc != 0:
        return _report(findings, "exec-role policy", "unreadable")
    arns = []
    for st in json.loads(out).get("Statement", []):
        res = st.get("Resource", [])
        arns += [res] if isinstance(res, str) else list(res)
    for a in sorted(arns):
        print(f"  grant  {a.split(':secret:')[-1]}")
    required = ["archondex/alpaca-paper-", "archondex/anthropic-api"]
    for need in required:
        if not any(need in a for a in arns):
            _report(findings, "exec-role policy", f"MISSING a grant matching {need!r}")


def check_schedules(findings) -> None:
    print("== schedules (July lessons: pinned revision + DLQ + fast-fail) ==")
    for name in SCHEDULES:
        rc, out, _ = aws("scheduler", "get-schedule", "--name", name, "--output", "json")
        if rc != 0:
            print(f"  --     {name}: does not exist yet")
            continue
        s = json.loads(out)
        tgt = s.get("Target", {})
        jd = json.loads(tgt.get("Input", "{}")).get("JobDefinition", "")
        pinned = ":" in jd.rsplit("/", 1)[-1]
        dlq = (tgt.get("DeadLetterConfig") or {}).get("Arn")
        retry = tgt.get("RetryPolicy") or {}
        print(f"  {s.get('State'):8s} {name} @ {s.get('ScheduleExpression')} "
              f"pinned={pinned} dlq={bool(dlq)} retry={retry.get('MaximumRetryAttempts')}")
        if not pinned:
            _report(findings, name, f"jobdef ARN NOT revision-pinned ({jd}) — the "
                                    f"2026-07-13 silent-outage shape")
        if not dlq:
            _report(findings, name, "no DeadLetterConfig — a failed submit vanishes")
        if retry != FAST_FAIL:
            _report(findings, name, f"retry policy {retry} != fast-fail {FAST_FAIL}")


def check_scheduler_submit_policy(findings) -> None:
    """Every EXISTING schedule's target jobdef must be covered by the scheduler
    role's batch:SubmitJob resource list. The gap this catches is the T-329d
    ignition miss (found 2026-08-25): a NEW jobdef + schedule provisioned without
    the scheduler role ever learning the new ARN → every scheduled submit
    AccessDenied → straight to the DLQ, with zero FAILED Batch jobs to see.
    Same class as July 2026, one IAM layer over. IAM patterns and their
    consumers change together — this check makes that rule mechanical."""
    print("== scheduler-role submit policy covers every scheduled jobdef ==")
    rc, out, _ = aws("iam", "get-role-policy", "--role-name",
                     "archondex-paper-scheduler-role",
                     "--policy-name", "submit-paper-job",
                     "--query", "PolicyDocument", "--output", "json")
    if rc != 0:
        return _report(findings, "scheduler-role policy", "unreadable")
    resources: list = []
    for st in json.loads(out).get("Statement", []):
        res = st.get("Resource", [])
        resources += [res] if isinstance(res, str) else list(res)
    covered = {r.rsplit("/", 1)[-1].split(":")[0]
               for r in resources if ":job-definition/" in r}
    for name in SCHEDULES:
        rc, out, _ = aws("scheduler", "get-schedule", "--name", name, "--output", "json")
        if rc != 0:
            continue
        jd_arn = json.loads(json.loads(out).get("Target", {}).get("Input", "{}")) \
            .get("JobDefinition", "")
        jd_name = jd_arn.rsplit("/", 1)[-1].split(":")[0]
        if jd_name and jd_name not in covered:
            _report(findings, name,
                    f"target jobdef {jd_name!r} NOT in the scheduler role's "
                    f"batch:SubmitJob resources — every scheduled submit will "
                    f"AccessDenied straight to the DLQ (the T-329d ignition miss)")
        else:
            print(f"  ok     {name} → {jd_name}")


def main() -> int:
    findings: list = []
    check_job_role(findings)
    check_exec_role(findings)
    check_schedules(findings)
    check_scheduler_submit_policy(findings)
    print()
    if findings:
        print(f"DRIFT: {len(findings)} finding(s). Reconcile the TEMPLATE to live "
              f"(or fix live deliberately) BEFORE provisioning — never let a "
              f"re-run silently revert a live hand-fix.")
        return 1
    print("No drift. Safe to provision.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
