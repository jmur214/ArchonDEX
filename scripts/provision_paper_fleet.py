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

# (account key, strategy, schedule minute, metric-dimension value = key)
# `secret` defaults to the key; set it explicitly when an account INHERITS another
# slot's secret (see ai-trader below).
FLEET = [
    # T-298 flip: offense-sso runs the DAMPED spec (damp re-entry, never de-risk)
    # now that its undamped armed run is clean + the real SSO slippage (2.2 bps)
    # is measured.
    dict(key="offense-sso", strategy="offense_sso", minute=50, damping="asymmetric"),
    # --- T-329 ACCOUNT 3 = the stage-2 AI trader (the constrained analyst's
    # validated note → real paper orders). It INHERITS the dormant btc-sleeve slot:
    #
    #   * the SECRET keeps its historical name `archondex/alpaca-paper-btc-sleeve`.
    #     It is ALIASED here, never renamed — a rename touches IAM ARNs and the
    #     jobdef binding, which is the deploy-drift class that produced the July
    #     outage. Cosmetics are not worth a live-resource edit.
    #   * the physical Alpaca sub-account was verified FLAT from the broker before
    #     ignition (positions=0, open_orders=0), never from dashboard memory.
    #   * the STATE PREFIX is NEW (`paper_state_ai_trader`), not inherited. The
    #     btc-sleeve prefix holds the 2026-07-08 armed-run journal/ledger/tracker;
    #     reusing it would open the AI trader's book with somebody else's page,
    #     which is the opposite of what a forward record certifies. The old prefix
    #     is left intact in S3 as the archive ([NN-ARCHIVE]).
    #   * 9:55 ET — after account-1's 9:45 pulse, whose push completes the notes
    #     prefix this account cross-reads. (Correctness does not depend on it: the
    #     constructor consumes YESTERDAY's note by construction.)
    dict(key="ai-trader", strategy="llm_analyst", minute=55,
         secret="btc-sleeve", state_prefix="paper_state_ai_trader"),
    # RETIRED — btc-sleeve. Its science moved to the VIRTUAL btc_shadow book (which
    # keeps accruing, unaffected) and the user's 3-account cap reserved this slot for
    # stage 2. The jobdef + its DISABLED schedule are left inert rather than deleted
    # ([NN-ARCHIVE]); they are deliberately absent from this list so a re-run of this
    # provisioner can never resurrect a second strategy pointed at the SAME Alpaca
    # account the AI trader now trades.
    #   dict(key="btc-sleeve", strategy="sleeve_btc", minute=55),
]

# The live schedule shape, matching account-1's `archondex-paper-daily`. These were
# added to the LIVE schedules by hand and never written back here — so the checked-in
# provisioner used to render a schedule with NO DLQ and AWS's 185-retry default, and
# re-running it would have silently reverted both. Written back now; every deploy
# still diffs rendered-vs-live first.
DLQ_ARN = f"arn:aws:sqs:{REGION}:{ACCOUNT}:archondex-scheduler-dlq"
RETRY_POLICY = {"MaximumEventAgeInSeconds": 3600, "MaximumRetryAttempts": 3}


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


def _live_secret_arns() -> list:
    """Every ARN the LIVE exec-role policy already grants. Absent policy → []."""
    r = subprocess.run(
        ["aws", "iam", "get-role-policy", "--role-name", EXEC_ROLE,
         "--policy-name", "read-alpaca-paper-secret", "--query", "PolicyDocument",
         "--output", "json", "--profile", PROFILE, "--region", REGION],
        capture_output=True, text=True)
    if r.returncode != 0:
        return []
    out = []
    for st in json.loads(r.stdout).get("Statement", []):
        res = st.get("Resource", [])
        out += [res] if isinstance(res, str) else list(res)
    return out


def extend_exec_secret_policy(new_arns):
    """Grant the exec role GetSecretValue on the account-1 secret + the new ones —
    as a UNION with whatever the live policy already grants, never a blind overwrite.

    This is the fix for a real near-miss. The live policy carries grants this script
    does not know about (notably `archondex/anthropic-api`, added out-of-band when the
    analyst was wired). Rendering the document from FLEET alone and PUT-ing it would
    have silently REVOKED them — a fleet-wide LLM blackout while every run still
    reported canonical. Read-modify-write plus a readback is the only safe shape for
    an IAM document whose live contents can legitimately exceed the template's."""
    base = aws("secretsmanager", "describe-secret", "--secret-id", SECRET_BASE,
               "--query", "ARN", "--output", "text")
    live = _live_secret_arns()
    want = sorted(set(live) | {base} | set(new_arns))
    dropped = sorted(set(live) - set(want))
    assert not dropped, f"REFUSING to revoke live grants: {dropped}"
    doc = {"Version": "2012-10-17", "Statement": [{
        "Sid": "ReadPaperSecrets", "Effect": "Allow",
        "Action": "secretsmanager:GetSecretValue",
        "Resource": want}]}
    aws("iam", "put-role-policy", "--role-name", EXEC_ROLE,
        "--policy-name", "read-alpaca-paper-secret",
        "--policy-document", json.dumps(doc))
    readback = sorted(_live_secret_arns())          # verify the WRITE, not the intent
    assert readback == want, f"readback mismatch: {readback} != {want}"
    print(f"  exec-role policy → {len(want)} secret ARNs "
          f"({len(want) - len(live)} added, 0 revoked, readback verified)")


def extend_scheduler_submit_policy(jobdef_names):
    """Grant the SCHEDULER role batch:SubmitJob on every fleet jobdef — as a UNION
    with whatever the live policy already grants, never a blind overwrite.

    This closes the T-329d ignition miss (2026-08-25): this script registered the
    ai-trader jobdef and created its schedule, but the scheduler role's submit
    policy still listed only the three older jobdefs — so every scheduled submit
    AccessDenied'd straight to the DLQ, with zero FAILED Batch jobs to notice.
    Same class as the July outage, one IAM layer over: IAM patterns and their
    consumers change together, so the script that adds a consumer must extend the
    pattern in the same run. Read-modify-write + readback, per the exec-role fix."""
    role, pol = SCHED_ROLE, "submit-paper-job"

    def _live():
        r = subprocess.run(
            ["aws", "iam", "get-role-policy", "--role-name", role,
             "--policy-name", pol, "--query", "PolicyDocument", "--output", "json",
             "--profile", PROFILE, "--region", REGION], capture_output=True, text=True)
        if r.returncode != 0:
            return []
        out = []
        for st in json.loads(r.stdout).get("Statement", []):
            res = st.get("Resource", [])
            out += [res] if isinstance(res, str) else list(res)
        return out

    live = _live()
    want = sorted(set(live) | {
        f"arn:aws:batch:{REGION}:{ACCOUNT}:job-definition/{n}:*" for n in jobdef_names})
    dropped = sorted(set(live) - set(want))
    assert not dropped, f"REFUSING to revoke live grants: {dropped}"
    if want == sorted(live):
        print(f"  scheduler-role submit policy already covers all {len(jobdef_names)} jobdefs")
        return
    doc = {"Version": "2012-10-17", "Statement": [{
        "Sid": "SubmitPaperJob", "Effect": "Allow",
        "Action": "batch:SubmitJob", "Resource": want}]}
    aws("iam", "put-role-policy", "--role-name", role, "--policy-name", pol,
        "--policy-document", json.dumps(doc))
    readback = sorted(_live())
    assert readback == want, f"readback mismatch: {readback} != {want}"
    print(f"  scheduler-role submit policy → {len(want)} resources "
          f"({len(want) - len(live)} added, 0 revoked, readback verified)")


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
                 "value": acct.get("state_prefix")
                 or f"paper_state_{acct['key'].replace('-', '_')}"},
                {"name": "ARCHONDEX_PAPER_ALLOCATOR", "value": "mean_variance"},
                {"name": "ARCHONDEX_PAPER_STRATEGY", "value": acct["strategy"]},
                {"name": "ARCHONDEX_SLEEVE_NOTIONAL_CAP", "value": "10000"},
                {"name": "ARCHONDEX_SLEEVE_TIF", "value": "day"},
                {"name": "ARCHONDEX_PAPER_ACCOUNT", "value": acct["key"]},
            ] + ([{"name": "ARCHONDEX_OFFENSE_DAMPING", "value": acct["damping"]}]
                 if acct.get("damping") else [])
              + ([  # T-329 account-3: where to cross-read the analyst notes from
                  # (intel_pulse runs on the account-1 branch only), and the
                  # trading kill switch's no-image-rebuild surface. Present and
                  # EXPLICITLY "0" so the control is visible in the jobdef rather
                  # than being an undocumented env name someone has to know.
                  {"name": "ARCHONDEX_NOTES_SOURCE_PREFIX", "value": "paper_state"},
                  {"name": "ARCHONDEX_TRADING_KILL_SWITCH", "value": "0"},
              ] if acct["strategy"] == "llm_analyst" else []),
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
    # jd_arn is the REVISION-PINNED ARN (…/name:N). A bare, revisionless ARN is what
    # caused the 2026-07-13→24 silent outage: it failed the scheduler role's `:*` IAM
    # pattern, every scheduled submit AccessDenied'd, and the retries drained with no
    # DLQ. Both halves of that lesson are pinned here — the revision and the DLQ.
    assert ":" in jd_arn.rsplit("/", 1)[-1], f"jobdef ARN is not revision-pinned: {jd_arn}"
    target = {"Arn": "arn:aws:scheduler:::aws-sdk:batch:submitJob",
              "RoleArn": sched_role_arn,
              "Input": json.dumps({"JobName": f"paper-{acct['key']}-day",
                                   "JobQueue": q_arn, "JobDefinition": jd_arn}),
              "DeadLetterConfig": {"Arn": DLQ_ARN},
              # FAST-FAIL. AWS's default is 185 attempts over 24h, which turns a
              # broken submit into a day-long silent retry storm instead of a prompt,
              # visible failure in the DLQ.
              "RetryPolicy": dict(RETRY_POLICY)}
    cron = f"cron({acct['minute']} 9 ? * MON-FRI *)"
    probe = subprocess.run(["aws", "scheduler", "get-schedule", "--name", name,
                            "--output", "json",
                            "--profile", PROFILE, "--region", REGION],
                           capture_output=True, text=True)
    exists = probe.returncode == 0
    # T-329d lesson: a re-run must never revert a live enable. A NEW schedule is
    # born DISABLED (enable is its own deliberate act, possibly StartDate-armed —
    # see the execution manual); an EXISTING schedule keeps its LIVE state and this
    # update only repoints the jobdef pin + re-asserts DLQ/fast-fail. (StartDate is
    # deliberately not carried: it is an arming-time control, and a past StartDate
    # is rejected by the API anyway.)
    state = json.loads(probe.stdout).get("State", "DISABLED") if exists else "DISABLED"
    verb = "update-schedule" if exists else "create-schedule"
    aws("scheduler", verb, "--name", name, "--state", state,
        "--schedule-expression", cron,
        "--schedule-expression-timezone", "America/New_York",
        "--flexible-time-window", '{"Mode":"OFF"}', "--target", json.dumps(target))
    print(f"  schedule {name} @ {cron} America/New_York — {state}"
          f"{' (live state preserved)' if exists else ''}")


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
    # `secret` defaults to the account key; ai-trader INHERITS btc-sleeve's secret
    # (aliased, never renamed — a rename touches IAM ARNs and the jobdef binding).
    sec = {a["key"]: secret_arn(a.get("secret", a["key"])) for a in FLEET}
    print("== extend exec-role secret policy ==")
    extend_exec_secret_policy(sec.values())
    print("== extend scheduler-role submit policy ==")
    extend_scheduler_submit_policy([f"archondex-paper-{a['key']}" for a in FLEET])
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
