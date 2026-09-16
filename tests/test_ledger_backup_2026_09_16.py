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

def test_the_nightly_path_can_never_pass_allow_rewrite():
    """A scheduled job must be able to EXTEND history and never to overwrite it."""
    import inspect
    from scripts import janitor_nightly as jn
    src = inspect.getsource(jn.main)
    assert "ledger_backup.sync(LEDGER, as_of=as_of)" in src
    # Strip comments: the code EXPLAINS why it never allows a rewrite, and a naive
    # grep flags the explanation as the offence. (Second time this bit me; the rule
    # is check the CALL, never the prose.)
    code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
    assert "allow_rewrite" not in code


def test_a_DATED_key_is_written_alongside_the_canonical_one():
    """Bucket versioning could not be verified (s3:GetBucketVersioning is denied to
    this IAM user), so the design must not depend on it: a bad overwrite of the
    canonical object cannot erase what previous days recorded."""
    import inspect
    from scripts import ledger_backup as lb
    src = inspect.getsource(lb.sync)
    assert "KEY_CANON" in src and "KEY_DAILY_FMT" in src
    assert KEY_DAILY_FMT.format(date="2026-09-16") != KEY_CANON


def test_missing_and_unreachable_remotes_are_DIFFERENT_facts():
    """'The object is not there' and 'I could not look' license different actions;
    collapsing them is how a backup reports success while writing nothing."""
    import inspect
    from scripts import ledger_backup as lb
    src = inspect.getsource(lb.read_remote)
    assert "absent" in src and "unreachable" in src


def test_the_janitor_verifies_at_the_START_so_a_failed_push_surfaces_within_24h():
    import inspect
    from scripts import janitor_nightly as jn
    assert "check_ledger_backup()" in inspect.getsource(jn.run_checks)
    assert "verify" in inspect.getsource(jn.check_ledger_backup)


# ---- the scheduled path's binary resolution ----------------------------------

def test_the_aws_cli_is_resolved_ABSOLUTELY_never_by_bare_name():
    """launchd runs with PATH=/usr/bin:/bin:/usr/sbin:/sbin and the CLI lives in
    /opt/homebrew/bin. A bare `aws` therefore works perfectly from an interactive
    shell and resolves to NOTHING at 03:00 — the backup would have reported failure
    every scheduled night while succeeding in every test. Same class as the
    2026-07-08 bare-`python` bug and the 2026-09-10 wrapper bootstrap: it fails only
    on the path nobody watches."""
    from scripts import ledger_backup as lb
    exe = lb._aws_binary()
    assert exe is None or Path(exe).is_absolute()
    src = __import__("inspect").getsource(lb._aws)
    assert '"aws"' not in src.split("_aws_binary")[-1], "no bare-name invocation may return"


def test_a_missing_aws_cli_is_a_LOUD_nonzero_not_a_silent_skip():
    """`[NN-FAIL-CLOSED]`: if the CLI cannot be found, say so with a non-zero rc
    rather than returning something that reads like an empty remote."""
    from scripts import ledger_backup as lb
    src = __import__("inspect").getsource(lb._aws)
    assert "127" in src and "not found" in src


def test_the_wrapper_resolves_aws_for_the_ALARM_path_too():
    """The loud-failure channel had never been exercised under launchd — it fires
    only on rc!=0, and the single recorded failure was a MANUAL run whose shell had
    homebrew on PATH. An alarm that cannot run is not an alarm."""
    sh = (Path(__file__).resolve().parent.parent / "scripts/run_janitor_nightly.sh").read_text()
    assert 'AWS="$(command -v aws' in sh
    assert '/opt/homebrew/bin/aws' in sh
    assert '"$AWS" sns publish' in sh, "the alarm must use the resolved binary"
