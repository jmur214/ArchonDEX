"""Survival for the autonomy ledger — the guard that makes a backup safe.

D's T-356 Finding 1: the record on which autonomous authority is granted and demoted
was one copy on one machine. The danger a naive mirror introduces is subtler than the
gap it closes — `aws s3 cp local remote` is a REWRITE PATH wearing a backup's clothes.
These tests pin the rule that makes the difference.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ledger_backup import (
    KEY_CANON, KEY_DAILY_FMT, OK_EXTEND, OK_FIRST, OK_SAME, REFUSE, classify_push,
)

A = b'{"ts":"1"}\n'
B = b'{"ts":"2"}\n'
C = b'{"ts":"3"}\n'


# ---- the appends, allowed ----------------------------------------------------

def test_first_push_when_no_remote_exists():
    v = classify_push(A + B, None)
    assert v.status == OK_FIRST and v.ok and v.needs_push


def test_identical_content_is_a_no_op_not_a_push():
    v = classify_push(A + B, A + B)
    assert v.status == OK_SAME and v.ok and not v.needs_push


def test_a_strict_append_is_allowed_and_counts_the_rows():
    v = classify_push(A + B + C, A + B)
    assert v.status == OK_EXTEND and v.needs_push
    assert "2 -> 3 rows" in v.detail


# ---- the losses, refused -----------------------------------------------------

def test_a_TRUNCATED_local_is_REFUSED_rather_than_mirrored():
    """The night the local file is truncated, a naive mirror faithfully destroys the
    good remote copy — the backup becomes the delivery mechanism for the loss."""
    v = classify_push(A, A + B + C)
    assert v.status == REFUSE and not v.ok
    assert "SHORTER" in v.detail and "history this machine has lost" in v.detail


def test_an_EMPTY_local_is_REFUSED():
    assert classify_push(b"", A + B).status == REFUSE
    assert classify_push(b"", None).status == REFUSE, "an empty first push is still empty"


def test_a_REWRITTEN_history_is_REFUSED_even_at_equal_length():
    """The 2026-09-14 reconciliation RE-SORTED the ledger to merge stranded rows —
    same rows, different bytes. That is a legitimate event and precisely the one that
    deserves a human, not an automatic overwrite."""
    v = classify_push(B + A, A + B)
    assert v.status == REFUSE
    assert "DIVERGES" in v.detail and "rewritten, not appended" in v.detail


def test_a_reordering_is_not_mistaken_for_an_append():
    v = classify_push(A + B + C, A + C)      # C inserted mid-history
    assert v.status == REFUSE


# ---- properties of the scheme ------------------------------------------------

def test_the_nightly_path_can_never_pass_allow_rewrite(monkeypatch):
    """A scheduled job must be able to EXTEND history and never to overwrite it.

    Driven by EXECUTION (2026-10-13): the first form grepped `main()`'s source for the
    call, so moving the call into `survival_syncs` broke a lock that had certified
    only where the text sat. Now the nightly entry point is run against recording
    stubs, and every survival push must arrive with allow_rewrite False."""
    import inspect
    from scripts import janitor_nightly as jn
    from scripts import ledger_backup as lb
    seen = []

    def rec(path, allow_rewrite=False, as_of=None):
        seen.append(allow_rewrite)
        return lb.PushVerdict(lb.OK_SAME, "stub")

    monkeypatch.setattr(lb, "sync", rec)
    monkeypatch.setattr(lb, "sync_observability", rec)
    jn.survival_syncs("2026-10-13")
    assert seen == [False, False], "every nightly survival push must forbid a rewrite"
    assert "survival_syncs(as_of)" in inspect.getsource(jn.main), "main() must run the pushes"


class _Proc:
    """A stand-in for subprocess.CompletedProcess as `_aws` returns it."""
    def __init__(self, rc: int = 0, out: bytes = b"", err: bytes = b""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def test_a_DATED_key_is_written_alongside_the_canonical_one(tmp_path, monkeypatch):
    """Bucket versioning could not be verified (s3:GetBucketVersioning is denied to
    this IAM user), so the design must not depend on it: a bad overwrite of the
    canonical object cannot erase what previous days recorded.

    EXECUTED (2026-10-13; was a getsource lock): sync() is driven and the destinations
    it actually copies to are observed — on a first push and on an extension."""
    from scripts import ledger_backup as lb
    assert KEY_DAILY_FMT.format(date="2026-09-16") != KEY_CANON
    ledger = tmp_path / "autonomy_ledger.jsonl"
    remote = {"bytes": None}
    copied = []

    def fake_aws(args, **kw):
        if args[-1] == "-":                                   # read_remote
            return (_Proc(0, remote["bytes"]) if remote["bytes"] is not None
                    else _Proc(1, err=b"An error occurred (404) when calling HeadObject: Not Found"))
        copied.append(args[-1])                               # s3 cp <local> <dest>
        return _Proc(0)

    monkeypatch.setattr(lb, "_aws", fake_aws)
    canon = f"s3://{lb.BUCKET}/{KEY_CANON}"
    for date, content in (("2026-09-16", A), ("2026-09-17", A + B)):
        ledger.write_bytes(content)
        copied.clear()
        v = lb.sync(ledger, as_of=date)
        assert v.needs_push, v.detail
        assert copied == [canon, f"s3://{lb.BUCKET}/{KEY_DAILY_FMT.format(date=date)}"]
        remote["bytes"] = content
    copied.clear()
    assert lb.sync(ledger, as_of="2026-09-18").status == OK_SAME and copied == []


@pytest.mark.parametrize("rc, err, expect", [
    (1, b"fatal error: An error occurred (NoSuchKey) when calling the GetObject operation", "absent"),
    (1, b"An error occurred (404) when calling the HeadObject operation: Not Found", "absent"),
    (1, b"Could not connect to the endpoint URL: \"https://s3.amazonaws.com/\"", "unreachable"),
    (127, b"aws CLI not found on PATH", "unreachable"),        # a missing CLI is NOT an empty remote
])
def test_missing_and_unreachable_remotes_are_DIFFERENT_facts(monkeypatch, rc, err, expect):
    """'The object is not there' and 'I could not look' license different actions;
    collapsing them is how a backup reports success while writing nothing.

    EXECUTED (2026-10-13; was a getsource lock): read_remote is fed the CLI's real
    failure shapes and its classification is observed."""
    from scripts import ledger_backup as lb
    monkeypatch.setattr(lb, "_aws", lambda args, **kw: _Proc(rc, err=err))
    body, why = lb.read_remote()
    assert body is None and why.split(":")[0] == expect, why
    monkeypatch.setattr(lb, "_aws", lambda args, **kw: _Proc(0, out=A))
    assert lb.read_remote() == (A, "ok")


def test_the_janitor_verifies_at_the_START_so_a_failed_push_surfaces_within_24h():
    import inspect
    from scripts import janitor_nightly as jn
    assert "check_ledger_backup()" in inspect.getsource(jn.run_checks)
    assert "verify" in inspect.getsource(jn.check_ledger_backup)


# ---- the scheduled path's binary resolution ----------------------------------

def test_the_aws_cli_is_resolved_ABSOLUTELY_never_by_bare_name(monkeypatch):
    """launchd runs with PATH=/usr/bin:/bin:/usr/sbin:/sbin and the CLI lives in
    /opt/homebrew/bin. A bare `aws` therefore works perfectly from an interactive
    shell and resolves to NOTHING at 03:00 — the backup would have reported failure
    every scheduled night while succeeding in every test. Same class as the
    2026-07-08 bare-`python` bug and the 2026-09-10 wrapper bootstrap: it fails only
    on the path nobody watches.

    EXECUTED (2026-10-13; was a getsource lock): the argv `_aws` actually spawns is
    observed, and resolution is driven under launchd's PATH."""
    import shutil
    import subprocess
    from scripts import ledger_backup as lb
    exe = lb._aws_binary()
    assert exe is None or Path(exe).is_absolute()

    spawned = []
    monkeypatch.setattr(subprocess, "run", lambda argv, **kw: spawned.append(argv) or _Proc(0))
    monkeypatch.setattr(lb, "_aws_binary", lambda: "/opt/homebrew/bin/aws")
    lb._aws(["s3", "ls"])
    assert spawned[0][0] == "/opt/homebrew/bin/aws", "the resolved absolute path is what runs"
    monkeypatch.undo()

    # launchd's PATH: `which` finds nothing; only a fallback candidate exists.
    monkeypatch.setattr(shutil, "which", lambda name: None)
    monkeypatch.setattr(lb.os.path, "exists", lambda p: p == "/usr/local/bin/aws")
    monkeypatch.setattr(lb.os, "access", lambda p, mode: p == "/usr/local/bin/aws")
    assert lb._aws_binary() == "/usr/local/bin/aws"
    monkeypatch.setattr(lb.os.path, "exists", lambda p: False)
    assert lb._aws_binary() is None, "nothing found -> None, never a bare 'aws'"


def test_a_missing_aws_cli_is_a_LOUD_nonzero_not_a_silent_skip(monkeypatch):
    """`[NN-FAIL-CLOSED]`: if the CLI cannot be found, say so with a non-zero rc
    rather than returning something that reads like an empty remote.

    EXECUTED (2026-10-13; was a getsource lock): with no CLI, `_aws` is called and
    nothing may be spawned; the result must be loud, and must not read as absent."""
    import subprocess
    from scripts import ledger_backup as lb

    def must_not_spawn(*a, **kw):
        raise AssertionError("spawned a process with no CLI resolved")

    monkeypatch.setattr(subprocess, "run", must_not_spawn)
    monkeypatch.setattr(lb, "_aws_binary", lambda: None)
    r = lb._aws(["s3", "ls"])
    assert r.returncode == 127 and b"not found" in r.stderr
    assert lb.read_remote()[1].startswith("unreachable"), "a missing CLI must never read as absent"


def test_the_wrapper_resolves_aws_for_the_ALARM_path_too():
    """The loud-failure channel had never been exercised under launchd — it fires
    only on rc!=0, and the single recorded failure was a MANUAL run whose shell had
    homebrew on PATH. An alarm that cannot run is not an alarm."""
    sh = (Path(__file__).resolve().parent.parent / "scripts/run_janitor_nightly.sh").read_text()
    assert 'AWS="$(command -v aws' in sh
    assert '/opt/homebrew/bin/aws' in sh
    assert '"$AWS" sns publish' in sh, "the alarm must use the resolved binary"
