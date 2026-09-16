#!/usr/bin/env python3
"""Redeploy ONE paper account to a new image, touching nothing else.

`provision_paper_fleet.py --image REF` moves the WHOLE fleet. That is right when
the fleet should move together and wrong when a fix is account-specific, or when
another account is mid-observation and must not gain a variable it did not need.

Two failures this script exists to make impossible, both of which have already
cost this program real days:

* **The stranded fix** (2026-07-28). Re-rendering a jobdef from a template
  silently reverts hand-fixes that were never written back. So the new revision
  is CLONED from the LIVE one and the script refuses to register if anything but
  the image differs.
* **The revisionless ARN** (the 2026-07-13→24 two-week silent outage). A bare
  jobdef ARN fails the scheduler role's ``:*`` IAM pattern; every scheduled
  submit AccessDenies and the retries drain with nothing surfaced. So the
  schedule is always repointed at a revision-PINNED ARN, asserted here.

The schedule's ``State`` is never written: a redeploy must not arm a disabled
account or disarm a live one as a side effect.

Verification belongs to the NEXT SCHEDULED FIRING, not to a manual submit — a
manual run proves the image, never the wiring that invokes it ([NN-FIRST-ARTIFACT]).
"""
from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
from typing import Any, Dict, List

PROFILE = "archondex"
REGION = "us-east-1"
# Everything the register call cannot echo back, plus the fields AWS adds.
_VOLATILE = ("revision", "status", "jobDefinitionArn", "revisionNumber",
             "containerOrchestrationType")
# Top-level jobdef keys that must survive the clone (retryStrategy above all:
# losing it silently re-exposes the account to the single-ECR-hiccup class).
_CARRY = ("retryStrategy", "timeout", "propagateTags", "platformCapabilities",
          "parameters", "tags")


def aws(*args: str) -> Any:
    r = subprocess.run(["aws", *args, "--profile", PROFILE, "--region", REGION],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"FATAL: aws {' '.join(args[:3])} failed — {r.stderr.strip()[:500]}")
    out = r.stdout.strip()
    return json.loads(out) if out.startswith(("{", "[", '"')) else out


def live_jobdef(name: str) -> Dict[str, Any]:
    defs: List[dict] = aws("batch", "describe-job-definitions",
                           "--job-definition-name", name, "--status", "ACTIVE",
                           "--output", "json")["jobDefinitions"]
    if not defs:
        sys.exit(f"FATAL: no ACTIVE revision of {name} — refusing to guess one")
    return sorted(defs, key=lambda d: d["revision"])[-1]


def clone_with_image(live: Dict[str, Any], image: str) -> Dict[str, Any]:
    # DEEP copy, and the depth is load-bearing: a shallow dict() leaves the
    # clone sharing `environment`, `retryStrategy.evaluateOnExit` etc. with
    # LIVE, so a drift in any nested value would be present in BOTH sides of
    # assert_image_only() and compare equal. The guard would then pass on
    # exactly the mutation it exists to catch.
    cp = copy.deepcopy(live["containerProperties"])
    cp["image"] = image
    reg = {"jobDefinitionName": live["jobDefinitionName"], "type": live["type"],
           "containerProperties": cp}
    for k in _CARRY:
        if k in live:
            reg[k] = copy.deepcopy(live[k])
    return reg


def assert_image_only(live: Dict[str, Any], reg: Dict[str, Any], image: str) -> None:
    """The clone must differ from LIVE in the image and in NOTHING else."""
    a, b = copy.deepcopy(live), copy.deepcopy(reg)
    for d in (a, b):
        for k in _VOLATILE:
            d.pop(k, None)
    a["containerProperties"]["image"] = image      # neutralise the intended delta
    if json.dumps(a, sort_keys=True) != json.dumps(b, sort_keys=True):
        sys.exit("FATAL: the clone differs from LIVE beyond the image — refusing "
                 "to register. Something in the live revision is not being "
                 "carried forward; fix the carry-list, do not deploy past this.")
    print("  diff-vs-LIVE: image ONLY  ✓")


def repoint(schedule: str, jd_arn: str, execute: bool) -> None:
    if ":" not in jd_arn.rsplit("/", 1)[-1]:
        sys.exit(f"FATAL: jobdef ARN is not revision-pinned: {jd_arn}")
    s = aws("scheduler", "get-schedule", "--name", schedule, "--output", "json")
    inp = json.loads(s["Target"]["Input"])
    prev = inp["JobDefinition"].rsplit("/", 1)[-1]
    inp["JobDefinition"] = jd_arn
    s["Target"]["Input"] = json.dumps(inp)
    print(f"  schedule {schedule}: {prev} -> {jd_arn.rsplit('/', 1)[-1]}")
    print(f"  State PRESERVED as {s['State']} (never written by this script)")
    for k in ("Arn", "CreationDate", "LastModificationDate", "Version"):
        s.pop(k, None)
    if not execute:
        print("  (dry run — schedule NOT updated; pass --execute)")
        return
    with open("/tmp/_redeploy_sched.json", "w") as fh:
        json.dump(s, fh)
    aws("scheduler", "update-schedule", "--cli-input-json",
        "file:///tmp/_redeploy_sched.json")
    print("  schedule updated")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--account", required=True,
                    help="fleet key, e.g. offense-sso (jobdef archondex-paper-<key>)")
    ap.add_argument("--image", required=True, help="full ECR image ref")
    ap.add_argument("--execute", action="store_true",
                    help="without this, nothing is registered or repointed")
    a = ap.parse_args(argv)

    jd_name = f"archondex-paper-{a.account}"
    sched = f"archondex-paper-{a.account}-daily"
    live = live_jobdef(jd_name)
    print(f"  LIVE {jd_name}:{live['revision']} "
          f"image={live['containerProperties']['image'].rsplit(':', 1)[-1]}")
    reg = clone_with_image(live, a.image)
    assert_image_only(live, reg, a.image)

    if not a.execute:
        print("  (dry run — jobdef NOT registered; pass --execute)")
        repoint(sched, live["jobDefinitionArn"], execute=False)
        return 0

    with open("/tmp/_redeploy_jd.json", "w") as fh:
        json.dump(reg, fh)
    rev = aws("batch", "register-job-definition", "--cli-input-json",
              "file:///tmp/_redeploy_jd.json", "--query", "revision",
              "--output", "json")
    print(f"  registered {jd_name}:{rev}")
    repoint(sched, live_jobdef(jd_name)["jobDefinitionArn"], execute=True)
    print("  NOW: python scripts/diff_live_paper_infra.py  (must print 'No drift.')")
    print("  Verification is the next SCHEDULED firing, not a manual submit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
