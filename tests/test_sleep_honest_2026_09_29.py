"""Sleep-honesty for the local rung-0 layer — the host is a laptop.

The design assumed an always-on host. It is not one: launchd cannot run a job while
the machine is asleep or off, so a missing night is usually the HOST being unavailable
rather than the janitor failing — and those need opposite responses. Measured on this
host: 09-24/25/26 fired at 03:07, 03:07, 03:14 (ON TIME, but before Wi-Fi associated),
while 09-27/28/29 produced neither a row nor a log.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pytest

from scripts import janitor_nightly as jn
from scripts.ledger_backup import DEFERRED, REFUSE, PushVerdict

REPO = Path(__file__).resolve().parent.parent


def _ledger(tmp_path, *as_ofs):
    p = tmp_path / "l.jsonl"
    p.write_text("".join(
        json.dumps({"session": "janitor_nightly", "as_of": a, "ts": f"{a}T08:02:00+00:00"}) + "\n"
        for a in as_ofs))
    return p


# ---- the three states a night can be in --------------------------------------

def test_a_run_at_the_scheduled_hour_is_on_time(tmp_path):
    led = _ledger(tmp_path, "2026-09-28")
    h = jn.schedule_health(led, dt.datetime(2026, 9, 29, 3, 0))
    assert h["minutes_late"] == 0 and h["nights_without_row"] == 0


def test_a_late_wake_is_recorded_as_MINUTES_LATE_not_as_a_failure(tmp_path):
    """09-24/25/26 fired 7-14 minutes late — launchd's normal catch-up, not an
    incident. The number belongs in the row; the alarm does not."""
    led = _ledger(tmp_path, "2026-09-28")
    h = jn.schedule_health(led, dt.datetime(2026, 9, 29, 3, 14))
    assert h["minutes_late"] == 14 and h["nights_without_row"] == 0


def test_nights_with_NO_ROW_are_counted_so_a_gap_is_readable_afterwards(tmp_path):
    led = _ledger(tmp_path, "2026-09-26")
    h = jn.schedule_health(led, dt.datetime(2026, 9, 29, 3, 5))
    assert h["nights_without_row"] == 2, "09-27 and 09-28"
    assert h["last_row_as_of"] == "2026-09-26"


def test_schedule_health_survives_a_missing_or_corrupt_ledger(tmp_path):
    """Bookkeeping must never be the thing that breaks the janitor."""
    assert jn.schedule_health(tmp_path / "absent.jsonl")["nights_without_row"] == 0
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not json\n{\"session\": \"janitor_nightly\"}\n")
    assert jn.schedule_health(bad)["last_row_as_of"] is None


def test_the_row_carries_the_schedule_block(tmp_path, monkeypatch):
    monkeypatch.setattr(jn, "LEDGER", tmp_path / "out.jsonl")
    jn.append_ledger("2026-09-29", "nightly_schedule", [jn.Check("suite", True, "ok")],
                     "no changes", "checks_only",
                     schedule={"minutes_late": 14, "nights_without_row": 2})
    row = json.loads((tmp_path / "out.jsonl").read_text().strip())
    assert row["schedule"]["nights_without_row"] == 2


# ---- the network at wake is not a backup failure ------------------------------

def test_an_unreachable_network_DEFERS_rather_than_FAILS():
    """The 03:00 job fires before Wi-Fi associates. An alarm that fires every night
    the laptop wakes slowly is the cry-wolf failure this program keeps closing —
    and the record is not at risk: the local file is intact and append-only."""
    assert PushVerdict(DEFERRED, "x").ok is True
    assert PushVerdict(REFUSE, "x").ok is False


class _OK:
    returncode = 0
    stdout = b""
    stderr = b""


def test_the_backup_retries_before_deferring(tmp_path, monkeypatch):
    """Driven by EXECUTION (2026-10-13). The first form asserted that `sync()`'s SOURCE
    contained 'NET_RETRIES' and 'time.sleep'; it broke when the retry loop moved into a
    helper while the behaviour survived — a text lock certifies only that we said it.
    Now the network is made to fail and the attempts, the backoff, and the verdict are
    observed."""
    from scripts import ledger_backup as lb
    assert lb.NET_RETRIES >= 2
    ledger = tmp_path / "autonomy_ledger.jsonl"
    ledger.write_bytes(b'{"ts":"1"}\n')
    reads, sleeps, pushes = [], [], []

    def unreachable(key=lb.KEY_CANON):
        reads.append(key)
        return None, "unreachable: Could not connect to the endpoint URL"

    monkeypatch.setattr(lb, "read_remote", unreachable)
    monkeypatch.setattr(lb.time, "sleep", sleeps.append)
    monkeypatch.setattr(lb, "_aws", lambda args, **kw: pushes.append(args) or _OK())

    v = lb.sync(ledger, as_of="2026-10-14")
    assert len(reads) == lb.NET_RETRIES, "every attempt must actually be made"
    assert sleeps == [lb.NET_BACKOFF_S] * (lb.NET_RETRIES - 1), "backoff between attempts"
    assert v.status == DEFERRED and v.ok, v.detail
    assert "absent" not in v.detail and pushes == [], "unreachable is never treated as absent"

    # The contrast: an ABSENT object is a fact, not a hiccup — no retries, first push.
    reads.clear(); sleeps.clear()
    monkeypatch.setattr(lb, "read_remote", lambda key=lb.KEY_CANON: (reads.append(key), (None, "absent"))[1])
    v = lb.sync(ledger, as_of="2026-10-14")
    assert len(reads) == 1 and sleeps == [] and v.status == lb.OK_FIRST and len(pushes) == 2


def test_a_REAL_refusal_is_still_a_failure():
    """Deferring on an unreachable network must not soften the guard that matters:
    a truncated or rewritten local file still refuses, loudly."""
    from scripts.ledger_backup import classify_push
    assert classify_push(b"a\n", b"a\nb\n").status == REFUSE
    assert classify_push(b"b\na\n", b"a\nb\n").status == REFUSE


# ---- the clock says what a missing night MEANS --------------------------------

def test_the_clock_explains_that_a_gap_may_be_the_HOST_not_the_janitor():
    from paper_trader.clock_census import CLOCK_NOTES
    note = CLOCK_NOTES.get("janitor_ran_nightly", "")
    assert note, "the clock must carry a note about what a MISS means"
    assert "asleep or off" in note and "NO row and NO log" in note
    assert "log" in note, "the note must say how to TELL the two causes apart"
