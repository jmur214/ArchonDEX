"""tests/test_cadence_registration_t346.py — T-346.

The census corrections plus THE CLASS FIX: a module that claims a cadence must be
registered or exempted. The weekly digest was built, verified once, and orphaned for a
month while every test passed and no clock complained — because nothing required it to
be registered anywhere. This is the covered-or-exempted tripwire, extended from durable
PATHS to CONSUMERS.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.clock_census import (  # noqa: E402
    ADVANCED, CADENCE_CLAIMS, CLOCK_NOTES, DIGEST_BUDGET_DAYS, MISS, NOT_DUE, REGISTRY,
    _digest_written_weekly, _news_month_pushed, cadence_claimants, run_census,
    unregistered_cadences)

CLOCK_NAMES = {c.name for c in REGISTRY}


# ---------- the tripwire ----------
def test_every_cadence_claiming_module_is_registered_or_exempted():
    """THE CLASS FIX. Built-with-a-cadence-but-unwatched is now a failing test, not a
    discovery for the next external review."""
    missing = unregistered_cadences()
    assert not missing, (
        "these modules claim a cadence in their docstring but appear in no registry "
        f"entry — add a clock: or exempt: line with a REASON: {missing}")


def test_the_scan_actually_finds_claimants_so_the_tripwire_cannot_pass_vacuously():
    """A tripwire that scans nothing passes forever. Assert it has real teeth."""
    found = cadence_claimants()
    assert len(found) >= 20, f"cadence scan collapsed to {len(found)} — it is not scanning"
    assert "intelligence/analyst/performance_digest.py" in found


def test_every_clock_reference_resolves_to_a_real_registered_clock():
    """A mapping that points at a clock which does not exist is WORSE than no mapping —
    it reads as covered while nothing watches."""
    dangling = {m: v for m, v in CADENCE_CLAIMS.items()
                if v.startswith("clock:")
                and not v.split(":", 1)[1].strip().startswith("SELF")
                and v.split(":", 1)[1].strip() not in CLOCK_NAMES}
    assert not dangling, f"cadence entries point at non-existent clocks: {dangling}"


def test_every_registry_entry_states_a_reason_not_just_a_verdict():
    """`exempt:` alone is an assertion; `exempt: <why>` is a claim someone can refute."""
    bare = {m: v for m, v in CADENCE_CLAIMS.items()
            if not v.startswith("clock:") and len(v.split(":", 1)[-1].strip()) < 20}
    assert not bare, f"exemptions without a real reason: {bare}"


def test_any_unwatched_module_is_labelled_as_a_gap_never_quietly_exempted():
    """T-347: advisor_surface — the entry this test was written to lock — has been RULED
    on and now carries `clock:advisor_surface_rendered`, so the specific lock is spent.
    The lock itself is not: it generalises. Any module the lint catches with a cadence
    and no watcher must be filed as UNWATCHED-KNOWN, naming what is missing and who owns
    it, so it can never be quietly downgraded to `exempt:` to make the suite green.

    An empty finding set is the healthy state here and the assertion still has teeth —
    it constrains the SHAPE of any future gap entry, not the existence of one."""
    gaps = {m: v for m, v in CADENCE_CLAIMS.items() if v.startswith("UNWATCHED-KNOWN")}
    for m, v in gaps.items():
        assert "owner" in v.lower(), f"{m}: an unwatched gap must name an owner"
        assert len(v) > 60, f"{m}: an unwatched gap must state what is missing"


def test_the_lint_first_catch_got_a_consumer_not_an_exemption():
    """The director's ruling, locked in the record: advisor_surface was WIRED. If anyone
    later reverts it to `exempt:`, that is a decision that must be made deliberately —
    this test makes it visible rather than silent."""
    v = CADENCE_CLAIMS["intelligence/analyst/advisor_surface.py"]
    assert v == "clock:advisor_surface_rendered", (
        "advisor_surface was ruled WIRED (2026-08-26) — it gets a clock, not an exemption")


# ---------- the digest clock ----------
def _digest(tmp_path, stamp):
    d = tmp_path / "docs/State"
    d.mkdir(parents=True, exist_ok=True)
    (d / "performance_digest.md").write_text(f"# Performance digest — {stamp}\n\nbody\n")
    return tmp_path


def test_digest_written_today_advances(tmp_path):
    r = _digest_written_weekly(_digest(tmp_path, "2026-08-26"), "2026-08-26")
    assert r.status == ADVANCED


def test_digest_inside_its_weekly_budget_is_not_due_not_a_miss(tmp_path):
    """Most days a weekly artifact is correctly silent. NOT_DUE keeps it out of the
    expected-count so it can never dilute the advanced/expected ratio."""
    r = _digest_written_weekly(_digest(tmp_path, "2026-08-21"), "2026-08-26")
    assert r.status == NOT_DUE and "inside cadence" in r.detail


def test_digest_past_budget_misses_and_names_the_date(tmp_path):
    r = _digest_written_weekly(_digest(tmp_path, "2026-07-28"), "2026-08-26")
    assert r.status == MISS and "2026-07-28" in r.detail and "29d" in r.detail


def test_digest_absent_or_undated_is_fail_closed(tmp_path):
    assert _digest_written_weekly(tmp_path, "2026-08-26").status == MISS
    d = tmp_path / "docs/State"
    d.mkdir(parents=True)
    (d / "performance_digest.md").write_text("# Performance digest\n")   # no date
    r = _digest_written_weekly(tmp_path, "2026-08-26")
    assert r.status == MISS and "fail-closed" in r.detail


def test_digest_date_comes_from_the_header_not_the_mtime(tmp_path):
    """A git checkout rewrites mtime and would fake an advance. The artifact's own
    stamp is the only honest source."""
    root = _digest(tmp_path, "2026-07-28")          # written NOW, stamped a month ago
    assert _digest_written_weekly(root, "2026-08-26").status == MISS


# ---------- the news clock: the permanent false miss ----------
def _panel(tmp_path, rows_stamp, name=None):
    # The FILENAME must track the month the clock will ask for — i.e. TODAY's — while
    # `rows_stamp` independently controls the row CONTENT (that separation is the point
    # of the frozen-feed test: current file, stale rows). Hardcoding "news_202608.parquet"
    # silently stopped matching the clock's month key the moment the calendar rolled into
    # September, and all three tests went red on 2026-09-01 for that reason alone — the
    # clock was behaving correctly throughout.
    import datetime as _dt
    name = name or f"news_{_dt.date.today():%Y%m}.parquet"
    pytest.importorskip("pyarrow")
    import pyarrow as pa, pyarrow.parquet as pq
    d = tmp_path / "data/intel/news_panel"
    d.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.table({"ingest_ts": [f"{rows_stamp}T12:00:00Z"],
                             "headline": ["h"]}), d / name)
    return d / name


def test_news_clock_reads_the_FLAT_local_layout(tmp_path):
    """The bug: it built the S3 partitioned key and looked for it locally, so it
    reported 'partition missing' every day of its life — a miss that could not clear."""
    import datetime as dt, os
    today = dt.date.today().isoformat()
    f = _panel(tmp_path, today)
    os.utime(f, None)
    r = _news_month_pushed(tmp_path, today)
    assert r.status == ADVANCED, r.detail
    # and the partitioned path is NOT what it looks at
    assert not (tmp_path / f"data/intel/news_panel/{today[:4]}").exists()


def test_news_clock_catches_a_touched_file_whose_tape_never_moved(tmp_path):
    """The frozen-feed class: mtime alone reads healthy. This program has been bitten
    by it twice."""
    import datetime as dt, os
    today = dt.date.today().isoformat()
    f = _panel(tmp_path, "2026-01-02")            # rows are months old
    os.utime(f, None)                             # but the file was touched today
    r = _news_month_pushed(tmp_path, today)
    assert r.status == MISS and "TAPE DID NOT" in r.detail


def test_news_clock_misses_when_row_freshness_cannot_be_verified(tmp_path):
    """Fail-closed: half a check passed quietly is how a census earns false trust."""
    import datetime as dt, os
    pytest.importorskip("pyarrow")
    import pyarrow as pa, pyarrow.parquet as pq
    today = dt.date.today().isoformat()
    d = tmp_path / "data/intel/news_panel"
    d.mkdir(parents=True)
    fn = f"news_{dt.date.today():%Y%m}.parquet"     # today's month, not a hardcoded one
    pq.write_table(pa.table({"headline": ["h"]}), d / fn)  # no stamp col
    os.utime(d / fn, None)
    r = _news_month_pushed(tmp_path, today)
    assert r.status == MISS and "UNVERIFIED" in r.detail


# ---------- notes travel with the result ----------
def test_clock_notes_are_surfaced_in_the_census_detail(tmp_path):
    c = run_census(root=str(tmp_path), as_of="2026-08-26")
    for name in CLOCK_NOTES:
        assert c["detail"][name].get("note"), f"{name} lost its note in the output"
    assert "T-341" in c["detail"]["similarity_panel_refreshed"]["note"]


def test_a_note_never_converts_a_miss_into_a_pass(tmp_path):
    """An annotation explains a finding; it must never suppress one."""
    c = run_census(root=str(tmp_path), as_of="2026-08-26")
    assert c["detail"]["similarity_panel_refreshed"]["status"] == MISS
    assert c["degraded"] is True


def test_notes_reference_only_registered_clocks():
    assert not (set(CLOCK_NOTES) - CLOCK_NAMES)


def test_digest_budget_is_a_week_plus_grace():
    assert 7 < DIGEST_BUDGET_DAYS <= 10
