"""Turn a LIVE `aws scheduler get-schedule` JSON into an update-schedule input that
changes ONLY State, refusing unless the target is pinned to the expected revision.

usage: python3 sched_state.py <live.json> <ENABLED|DISABLED> <expected_jobdef_tail> <out.json>
  expected_jobdef_tail e.g. archondex-paper-offense-sso:21
"""
import json
import sys

live_p, state, expect, out_p = sys.argv[1:5]
assert state in ("ENABLED", "DISABLED"), f"bad state {state!r}"
s = json.load(open(live_p))
tgt = s["Target"]
jd = json.loads(tgt["Input"])["JobDefinition"].rsplit("/", 1)[-1]
if jd != expect:
    sys.exit(f"REFUSE: live target is {jd}, expected {expect} — someone repointed it; re-read and decide")
if ":" not in jd:
    sys.exit(f"REFUSE: target {jd} is not revision-pinned")
if not (tgt.get("DeadLetterConfig") or {}).get("Arn"):
    sys.exit("REFUSE: no DeadLetterConfig on the live target")
if tgt.get("RetryPolicy") != {"MaximumEventAgeInSeconds": 3600, "MaximumRetryAttempts": 3}:
    sys.exit(f"REFUSE: retry policy is {tgt.get('RetryPolicy')}, not fast-fail")
for k in ("Arn", "CreationDate", "LastModificationDate", "Version"):
    s.pop(k, None)
s["State"] = state
json.dump(s, open(out_p, "w"), indent=1)
print(f"wrote {out_p}: State={state} target={jd} (everything else verbatim from the live GET)")
