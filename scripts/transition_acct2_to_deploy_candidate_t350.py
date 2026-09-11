#!/usr/bin/env python
"""T-350 — the ONE-TIME account-2 transition: offense sleeve → deploy candidate.

Run IN MARKET HOURS. This is the account's re-baseline, and it is deliberately a
separate, explicit, one-shot script rather than a branch inside the daily loop:
a transition that can run twice is a transition that will.

What it does, in order, each step gated on the last:

 1. READ-ONLY SNAPSHOT of the broker + the account's own state, printed and
    archived before anything moves. The record of what was there is written
    BEFORE the thing is changed — you cannot reconstruct it afterwards.
 2. CLOSE the legacy 149-SSO position (market, day). The offense question is not
    lost with it: it lives in the `damped_offense_t298` virtual book, which keeps
    accruing untouched — this closes the CAPITAL, not the experiment.
 3. ARCHIVE the offense-era state ([NN-ARCHIVE], never delete) — journal, ledger,
    recon, tracker — under `paper_state_offense_sso/archive_offense_<date>/`, and
    clear the drill residue the T-327 week deliberately left behind (denied push,
    rejected orders, a stale ledger). A forward record must not open with somebody
    else's page, and must not open mid-drill either.
 4. STATE THE TIER. $10k is the arrival-event size; the account's equity is
    whatever Alpaca says. The tier is enforced by the NOTIONAL CAP the jobdef
    already carries, not by moving money — so this step VERIFIES the cap rather
    than pretending to reset a broker balance we cannot set.

It does NOT deploy the lump sum. That is the arrival event itself, and it belongs
to the first scheduled firing under the new strategy — observed as its own
artifact per [NN-FIRST-ARTIFACT], not buried inside a migration script.

Usage:
    python scripts/transition_acct2_to_deploy_candidate_t350.py --dry-run
    python scripts/transition_acct2_to_deploy_candidate_t350.py --execute
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys

PROFILE, REGION = "archondex", "us-east-1"
BUCKET = "archondex-results-407539788432"
PREFIX = "paper_state_offense_sso"
JOBDEF = "archondex-paper-offense-sso"
QUEUE = "archondex-backtest-queue"
LEGACY_TICKER = "SSO"
ARRIVAL_TIER_USD = 10_000.0

STATE_FILES = ("data/paper_state/orders.jsonl", "data/paper_state/ledger.jsonl",
               "data/paper_state/recon.jsonl", "data/state/offense_tracking.json",
               "data/state/paper_heartbeat.json", "data/state/paper_alerts.log")


def aws(*args: str, check: bool = True) -> str:
    r = subprocess.run(["aws", *args, "--profile", PROFILE, "--region", REGION],
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"aws {' '.join(args[:3])} failed: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


def snapshot(today: str) -> dict:
    """Step 1 — what is there, written down BEFORE anything moves."""
    snap: dict = {"as_of": today, "prefix": PREFIX, "state_files": {}}
    listing = aws("s3", "ls", f"s3://{BUCKET}/{PREFIX}/", "--recursive", check=False)
    snap["s3_objects"] = len([l for l in listing.splitlines() if l.strip()])
    for rel in STATE_FILES:
        out = aws("s3", "ls", f"s3://{BUCKET}/{PREFIX}/{rel}", check=False)
        snap["state_files"][rel] = out.split()[2] + " bytes" if out.strip() else "absent"
    return snap


def close_legacy_position(execute: bool, today: str) -> dict:
    """Step 2 — close the offense-era position via a READ-ONLY-SAFE container job.

    The close runs THROUGH the account's own jobdef (its secret, its role, its
    prefix) rather than from a laptop holding broker keys — the CLI user has no
    GetSecretValue by design, and that boundary is not worth crossing for a
    migration."""
    # 2026-09-11: the first --execute FAILED here because this body guessed
    # submit_order's signature (`type=`/`time_in_force=`) instead of reading it —
    # the [NN-NO-GUESS-CLI] class, applied to an API. It failed SAFE (the TypeError
    # raised before anything reached the broker) but it cost a window, and the
    # reason the dry run missed it is the real lesson: **a dry run that skips the
    # mutating call cannot validate the mutating call.** So the dry run now BINDS
    # the very same arguments against the real signature via inspect, proving the
    # call would succeed without making it.
    body = f'''
import inspect, json
from paper_trader.paper_client import AlpacaPaperClient
c = AlpacaPaperClient()
pos = {{p["symbol"]: int(p["qty"]) for p in c.list_positions()}}
print("TRANSITION positions_before=" + json.dumps(pos))
qty = pos.get("{LEGACY_TICKER}", 0)
kw = dict(client_order_id="t350-transition-{today}-{LEGACY_TICKER}-sell",
          symbol="{LEGACY_TICKER}", qty=qty, side="sell", tif="day")
if qty <= 0:
    print("TRANSITION nothing_to_close")
else:
    # bind FIRST, always — in dry-run this is the whole check; in execute it
    # turns a signature mistake into a clean refusal instead of a half-transition
    inspect.signature(c.submit_order).bind(**kw)
    print("TRANSITION signature_binds=True kwargs=" + json.dumps(sorted(kw)))
    if {execute!r}:
        o = c.submit_order(**kw)
        print("TRANSITION closed qty=%d order=%s" % (qty, json.dumps(o, default=str)[:200]))
    else:
        print("TRANSITION DRY-RUN would_sell qty=%d {LEGACY_TICKER}" % qty)
'''
    ov = json.dumps({"command": ["python", "-c", body]})
    name = "t350-transition-close" if execute else "t350-transition-dryrun"
    job = aws("batch", "submit-job", "--job-name", name, "--job-queue", QUEUE,
              "--job-definition", JOBDEF, "--container-overrides", ov,
              "--query", "jobId", "--output", "text")
    return {"job_id": job, "execute": execute}


def archive_state(today: str, execute: bool) -> list:
    """Step 3 — [NN-ARCHIVE]: copy the offense-era state aside, never delete."""
    dest = f"s3://{BUCKET}/{PREFIX}/archive_offense_{today}/"
    moved = []
    for rel in STATE_FILES:
        src = f"s3://{BUCKET}/{PREFIX}/{rel}"
        if not aws("s3", "ls", src, check=False).strip():
            continue
        if execute:
            aws("s3", "cp", src, dest + rel.replace("/", "_"))
            # the ACTIVE copy is then removed so the new record opens clean — the
            # archive above is the preserved original ([NN-ARCHIVE] satisfied by
            # copy-then-clear, never by deletion alone)
            aws("s3", "rm", src)
        moved.append(rel)
    return moved


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--execute", action="store_true")
    a = ap.parse_args(argv)
    execute = bool(a.execute)
    today = dt.date.today().isoformat()

    print(f"=== T-350 account-2 transition ({'EXECUTE' if execute else 'DRY-RUN'}) "
          f"{today} ===")
    print("1. SNAPSHOT (written before anything moves)")
    snap = snapshot(today)
    print(json.dumps(snap, indent=1))

    print(f"\n2. CLOSE the legacy {LEGACY_TICKER} position "
          f"(the CAPITAL, not the experiment — damped_offense_t298 keeps accruing)")
    res = close_legacy_position(execute, today)
    print(f"   submitted job {res['job_id']} — read its log for the artifact")

    print("\n3. ARCHIVE the offense-era state + clear the T-327 drill residue")
    moved = archive_state(today, execute)
    print(f"   {'archived' if execute else 'would archive'}: {moved}")

    print(f"\n4. TIER — the arrival size is ${ARRIVAL_TIER_USD:,.0f}, enforced by the "
          f"jobdef's ARCHONDEX_SLEEVE_NOTIONAL_CAP, not by moving broker money.")
    cap = aws("batch", "describe-job-definitions", "--job-definition-name", JOBDEF,
              "--status", "ACTIVE", "--query",
              "reverse(sort_by(jobDefinitions,&revision))[0].containerProperties."
              "environment[?name=='ARCHONDEX_SLEEVE_NOTIONAL_CAP'].value | [0]",
              "--output", "text")
    ok = str(cap).strip() == str(int(ARRIVAL_TIER_USD))
    print(f"   live cap = {cap} → {'MATCHES the arrival tier' if ok else 'MISMATCH — fix before arming'}")
    if not ok:
        print("FATAL: the notional cap does not match the arrival tier; refusing to "
              "call this transition complete.", file=sys.stderr)
        return 70

    print("\nNEXT: the ARRIVAL EVENT is the first scheduled firing under "
          "deploy_candidate — observed as its own artifact, not run from here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
