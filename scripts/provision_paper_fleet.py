#!/usr/bin/env python
"""T-288 — provision the paper FLEET accounts 2 & 3 (offense_sso, sleeve_btc).

IDEMPOTENT: every step create-or-updates. Reuses the shared IAM roles, SNS topic,
Batch queue, and results bucket from the account-1 deploy (scripts/
deploy_paper_cloud_trigger.sh) — this ONLY adds the per-account jobdef +
schedule (DISABLED) + dead-man's-switch alarms, and extends the exec role's
secret-read policy to the two new secrets.

Per-account isolation:
  * own Secrets-Manager secret        (creds injected by the jobdef `secrets`)
  * own S3 state prefix               (ARCHONDEX_PAPER_STATE_PREFIX)
  * own strategy                      (ARCHONDEX_PAPER_STRATEGY)
  * own CloudWatch metric DIMENSION   (ARCHONDEX_PAPER_ACCOUNT — explicit, never
                                       a default, so the 3 alarms can't collide)
  * own schedule (staggered, DISABLED) + own alarms

Schedules are created DISABLED — each is enabled only AFTER a clean armed run,
by the user's word (same gate as account 1). PAPER only.

Usage:  python scripts/provision_paper_fleet.py --image <ecr-ref>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

PROFILE, REGION = "archondex", "us-east-1"
ACCOUNT = "407539788432"
BUCKET = f"archondex-results-{ACCOUNT}"
QUEUE = "archondex-backtest-queue"
EXEC_ROLE = "archondex-paper-exec-role"
JOB_ROLE = "archondex-paper-job-role"
SCHED_ROLE = "archondex-paper-scheduler-role"
TOPIC = f"arn:aws:sns:{REGION}:{ACCOUNT}:archondex-paper-alerts"
SECRET_BASE = "archondex/alpaca-paper"

# (account key, strategy, secret suffix, schedule minute, metric-dimension value)
FLEET = [
    # T-298 flip: offense-sso runs the DAMPED spec (damp re-entry, never de-risk)
    # now that its undamped armed run is clean + the real SSO slippage (2.2 bps)
    # is measured. btc-sleeve carries no damping (default symmetric).
    dict(key="offense-sso", strategy="offense_sso", minute=50, damping="asymmetric"),
    dict(key="btc-sleeve",  strategy="sleeve_btc",  minute=55),
]


def aws(*args, capture=True):
    cmd = ["aws", *args, "--profile", PROFILE, "--region", REGION]
    r = subprocess.run(cmd, capture_output=capture, text=True)
    if r.returncode != 0 and capture:
        raise RuntimeError(f"aws {' '.join(args[:2])} failed: {r.stderr.strip()[:300]}")
    return r.stdout.strip() if capture else ""


def secret_arn(suffix: str) -> str:
    return aws("secretsmanager", "describe-secret", "--secret-id",
               f"{SECRET_BASE}-{suffix}", "--query", "ARN", "--output", "text")


def role_arn(name: str) -> str:
    return aws("iam", "get-role", "--role-name", name, "--query", "Role.Arn", "--output", "text")


def extend_exec_secret_policy(new_arns):
    """Grant the exec role GetSecretValue on the account-1 secret + the new ones."""
    base = aws("secretsmanager", "describe-secret", "--secret-id", SECRET_BASE,
               "--query", "ARN", "--output", "text")
    doc = {"Version": "2012-10-17", "Statement": [{
        "Sid": "ReadAlpacaPaperSecrets", "Effect": "Allow",
        "Action": "secretsmanager:GetSecretValue",
        "Resource": [base] + list(new_arns)}]}
    aws("iam", "put-role-policy", "--role-name", EXEC_ROLE,
        "--policy-name", "read-alpaca-paper-secret",
        "--policy-document", json.dumps(doc))
    print(f"  exec-role policy → {1 + len(new_arns)} secret ARNs")


def register_jobdef(acct, image, exec_arn, job_arn, sec_arn) -> str:
    name = f"archondex-paper-{acct['key']}"
    jd = {
        "jobDefinitionName": name, "type": "container",
        "platformCapabilities": ["FARGATE"],
        "containerProperties": {
            "image": image, "command": ["scripts/paper_cloud_entrypoint.sh"],
            "executionRoleArn": exec_arn, "jobRoleArn": job_arn,
            "runtimePlatform": {"cpuArchitecture": "ARM64", "operatingSystemFamily": "LINUX"},
            "resourceRequirements": [{"type": "VCPU", "value": "1"},
                                     {"type": "MEMORY", "value": "2048"}],
            "networkConfiguration": {"assignPublicIp": "ENABLED"},
            "environment": [
                {"name": "AWS_DEFAULT_REGION", "value": REGION},
                {"name": "ARCHONDEX_PAPER_STATE_BUCKET", "value": BUCKET},
                {"name": "ARCHONDEX_PAPER_STATE_PREFIX",
                 "value": f"paper_state_{acct['key'].replace('-', '_')}"},
                {"name": "ARCHONDEX_PAPER_ALLOCATOR", "value": "mean_variance"},
                {"name": "ARCHONDEX_PAPER_STRATEGY", "value": acct["strategy"]},
                {"name": "ARCHONDEX_SLEEVE_NOTIONAL_CAP", "value": "10000"},
                {"name": "ARCHONDEX_SLEEVE_TIF", "value": "day"},
                {"name": "ARCHONDEX_PAPER_ACCOUNT", "value": acct["key"]},
            ] + ([{"name": "ARCHONDEX_OFFENSE_DAMPING", "value": acct["damping"]}]
                 if acct.get("damping") else []),
            "secrets": [
                {"name": "ALPACA_API_KEY", "valueFrom": f"{sec_arn}:ALPACA_API_KEY::"},
                {"name": "ALPACA_SECRET_KEY", "valueFrom": f"{sec_arn}:ALPACA_SECRET_KEY::"}],
            "logConfiguration": {"logDriver": "awslogs", "options": {
                "awslogs-group": "/aws/batch/job", "awslogs-region": REGION,
                "awslogs-stream-prefix": f"paper-{acct['key']}"}},
        },
        "retryStrategy": {"attempts": 1}, "timeout": {"attemptDurationSeconds": 1800},
    }
    rev = aws("batch", "register-job-definition", "--cli-input-json", json.dumps(jd),
              "--query", "revision", "--output", "text")
    print(f"  jobdef {name} rev {rev}")
    return name


def create_schedule(acct, jobdef_name, sched_role_arn):
    name = f"archondex-paper-{acct['key']}-daily"
    jd_arn = aws("batch", "describe-job-definitions", "--job-definition-name", jobdef_name,
                 "--status", "ACTIVE", "--query",
                 "reverse(sort_by(jobDefinitions,&revision))[0].jobDefinitionArn",
                 "--output", "text")
    q_arn = aws("batch", "describe-job-queues", "--job-queues", QUEUE,
                "--query", "jobQueues[0].jobQueueArn", "--output", "text")
    target = {"Arn": "arn:aws:scheduler:::aws-sdk:batch:submitJob",
              "RoleArn": sched_role_arn,
              "Input": json.dumps({"JobName": f"paper-{acct['key']}-day",
                                   "JobQueue": q_arn, "JobDefinition": jd_arn})}
    cron = f"cron({acct['minute']} 9 ? * MON-FRI *)"
    exists = subprocess.run(["aws", "scheduler", "get-schedule", "--name", name,
                             "--profile", PROFILE, "--region", REGION],
                            capture_output=True).returncode == 0
    verb = "update-schedule" if exists else "create-schedule"
    aws("scheduler", verb, "--name", name, "--state", "DISABLED",
        "--schedule-expression", cron,
        "--schedule-expression-timezone", "America/New_York",
        "--flexible-time-window", '{"Mode":"OFF"}', "--target", json.dumps(target))
    print(f"  schedule {name} @ {cron} America/New_York — DISABLED")


def create_alarms(acct):
    dim = [{"Name": "Account", "Value": acct["key"]}]
    aws("cloudwatch", "put-metric-alarm",
        "--alarm-name", f"archondex-paper-{acct['key']}-silent-stop",
        "--alarm-description", f"Paper account {acct['key']} did not run today (dead-man's-switch).",
        "--namespace", "ArchonDEX/PaperLoop", "--metric-name", "PaperRunHappened",
        "--dimensions", json.dumps(dim), "--statistic", "Maximum", "--period", "86400",
        "--evaluation-periods", "1", "--threshold", "1", "--comparison-operator",
        "LessThanThreshold", "--treat-missing-data", "breaching",
        "--alarm-actions", TOPIC, "--ok-actions", TOPIC)
    aws("cloudwatch", "put-metric-alarm",
        "--alarm-name", f"archondex-paper-{acct['key']}-non-canonical",
        "--alarm-description", f"Paper account {acct['key']} ran but was NON-CANONICAL.",
        "--namespace", "ArchonDEX/PaperLoop", "--metric-name", "PaperRunCanonical",
        "--dimensions", json.dumps(dim), "--statistic", "Minimum", "--period", "86400",
        "--evaluation-periods", "1", "--threshold", "1", "--comparison-operator",
        "LessThanThreshold", "--treat-missing-data", "notBreaching",
        "--alarm-actions", TOPIC, "--ok-actions", TOPIC)
    print(f"  alarms archondex-paper-{acct['key']}-{{silent-stop,non-canonical}} (dim Account={acct['key']})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True, help="the rev14 ECR image ref")
    args = ap.parse_args()
    exec_arn, job_arn, sched_arn = role_arn(EXEC_ROLE), role_arn(JOB_ROLE), role_arn(SCHED_ROLE)
    sec = {a["key"]: secret_arn(a["key"]) for a in FLEET}
    print("== extend exec-role secret policy ==")
    extend_exec_secret_policy(sec.values())
    sched_gap = []
    for acct in FLEET:
        print(f"== provision {acct['key']} (strategy={acct['strategy']}) ==")
        jn = register_jobdef(acct, args.image, exec_arn, job_arn, sec[acct["key"]])
        try:
            create_schedule(acct, jn, sched_arn)
        except RuntimeError as e:
            if "AccessDenied" in str(e):
                sched_gap.append(acct["key"])
                print(f"  ⚠ schedule SKIPPED — scheduler:CreateSchedule denied for "
                      f"this IAM user (not needed for the manual armed run).")
            else:
                raise
        create_alarms(acct)
    print("\nDONE. Jobdefs + alarms provisioned; secret policy extended.")
    if sched_gap:
        print(f"⚠ SCHEDULES NOT CREATED for {sched_gap} — the IAM user lacks "
              f"scheduler:CreateSchedule. They are NOT needed for the manual armed "
              f"runs; create them (DISABLED) before per-account enable. Armed run: "
              f"aws batch submit-job --job-definition archondex-paper-<acct> ...")


if __name__ == "__main__":
    sys.exit(main())
