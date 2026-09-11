"""Launchd canon — registered jobs map to LIVE tasks or carry an exemption.

The class: `com.archondex.t295-population` fired twice daily for six weeks, printing
"already DONE ... unload the job" into a log nobody read — 88 firings, 60 of them
saying exactly that. A channel that was RIGHT, and unread.
"""
from __future__ import annotations

import pytest

from scripts.launchd_canon import LIVE_JOBS, PREFIX, audit


def test_a_closed_task_still_registered_is_ORPHANED():
    v = audit(list(LIVE_JOBS) + ["com.archondex.t295-population"])
    assert not v.ok
    assert v.orphaned == ["com.archondex.t295-population"]
    assert "ORPHANED" in v.report()


def test_a_job_believed_scheduled_but_NOT_registered_is_MISSING():
    """The dangerous direction, and the reason this check is bidirectional: a
    one-way check catches zombies and misses the 2026-07-13 silent outage."""
    v = audit(["com.archondex.janitor"])
    assert not v.ok
    assert "com.archondex.altdata-archive" in v.missing
    assert "silent-outage" in v.report()


def test_both_directions_are_reported_together():
    v = audit(["com.archondex.janitor", "com.archondex.t999"])
    assert v.orphaned == ["com.archondex.t999"]
    assert v.missing == ["com.archondex.altdata-archive"]
    assert "ORPHANED" in v.report() and "MISSING" in v.report()


def test_exactly_the_live_set_passes():
    v = audit(list(LIVE_JOBS))
    assert v.ok and not v.orphaned and not v.missing
    assert sorted(v.live) == sorted(LIVE_JOBS)


def test_non_archondex_jobs_are_ignored():
    """The machine runs other people's launch agents; this audits OUR namespace."""
    v = audit(list(LIVE_JOBS) + ["com.apple.something", "com.docker.helper"])
    assert v.ok, v.report()


def test_every_live_entry_states_its_CONSUMER_not_just_a_name():
    """An entry here is a claim that something still consumes the job's output.
    'It exists' is what kept t295-population alive for six weeks."""
    for label, why in LIVE_JOBS.items():
        assert label.startswith(PREFIX)
        assert len(why) > 40, f"{label}: say what consumes it"
        assert any(w in why.lower() for w in ("consumed", "consumes", "clock", "gate")), why


def test_the_registry_is_off_limits_to_the_janitor():
    """It decides what may run unattended — an autonomous session may not grant
    itself a job, nor exempt a rogue one."""
    from scripts.janitor_guard import classify
    assert not classify(["scripts/launchd_canon.py"]).ok


def test_the_janitor_actually_runs_this_check():
    """A check nobody calls is the very failure this module exists to close."""
    import inspect
    from scripts import janitor_nightly as jn
    assert "check_launchd_canon()" in inspect.getsource(jn.run_checks)
