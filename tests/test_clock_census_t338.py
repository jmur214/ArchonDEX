"""T-338 — the clock census: every forward-accruing record must be asserted to advance.

The disease: a clock BELIEVED to be accruing that wasn't. These tests lock the properties
that make silence trustworthy — fail-closed on unreadable artifacts, artifact-derived
due-ness, read-only observation, and the registration tripwire that stops a new clock from
being added silently.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.clock_census import (  # noqa: E402
    ADVANCED, EXEMPT, MISS, NOT_DUE, REGISTRY, census_line, run_census)
from paper_trader.cloud_state import DURABLE_DIRS, DURABLE_PATHS  # noqa: E402

AS_OF = "2026-08-06"


def _book(tmp, rel, last_date):
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"days": [{"date": last_date}]}))
    return p


# ---------- THE TRIPWIRE: nothing may be added silently ----------
def test_every_durable_path_is_registered_or_explicitly_exempted():
    """The B pattern: a new durable artifact must either be censused or exempted WITH A
    REASON. This test is the thing that stops a future clock from being added silently."""
    covered = {c for clock in REGISTRY for c in clock.covers}
    unclassified = [p for p in DURABLE_PATHS if p not in covered and p not in EXEMPT]
    assert not unclassified, (
        "Unclassified durable artifacts — register a clock or add an EXEMPT reason:\n  "
        + "\n  ".join(unclassified))


def test_every_exemption_carries_a_nonempty_reason():
    for path, reason in EXEMPT.items():
        assert reason and len(reason) > 20, f"{path} exemption needs a real reason"


def test_durable_dirs_are_covered_by_the_analyst_clock():
    """Same rule as the paths tripwire: covered-by-a-clock OR exempted-with-a-reason.

    (Widened 2026-08-15/T-329: it previously demanded a CLOCK for every durable dir,
    which left no honest home for a diagnostic archive whose healthy state is 'no new
    file today' — `data/intel/llm_raw`, added by the T-325 token-truncation fix, sat
    unclassified and this tripwire was RED on main. Exemption is the same discipline,
    not an escape hatch: `test_every_exemption_carries_a_nonempty_reason` still applies,
    so a dir can only leave the census by SAYING WHY.)"""
    covered = {c for clock in REGISTRY for c in clock.covers}
    for d in DURABLE_DIRS:
        assert d in covered or d in EXEMPT, (
            f"{d} not covered by any clock and not exempted with a reason")


# ---------- FAIL-CLOSED: unverifiable is a MISS, never a skip ----------
def test_missing_artifact_is_a_MISS_not_a_skip(tmp_path):
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    assert c["degraded"] is True
    assert c["n_missed"] > 0
    # and nothing silently passed
    assert c["n_advanced"] == 0


def test_unparseable_artifact_is_a_MISS(tmp_path):
    p = tmp_path / "data/state/btc_shadow_tracking.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{ this is not json")
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    d = c["detail"]["btc_shadow_rolled"]
    assert d["status"] == MISS and "unparseable" in d["detail"]


def test_a_raising_check_becomes_a_MISS_never_disappears(tmp_path, monkeypatch):
    import paper_trader.clock_census as cc

    def boom(root, as_of):
        raise RuntimeError("boom")
    monkeypatch.setattr(cc.REGISTRY[0], "check", boom)
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    assert any("raised" in m["detail"] for m in c["missed"])


# ---------- clock 4: rolled means last date == as_of ----------
def test_book_that_rolled_is_ADVANCED(tmp_path):
    _book(tmp_path, "data/state/book_spy_null.json", AS_OF)
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    assert c["detail"]["book_spy_null_rolled"]["status"] == ADVANCED


def test_STALE_book_is_a_MISS_and_is_NAMED(tmp_path):
    """The core disease: the file exists and looks healthy, but the clock froze."""
    _book(tmp_path, "data/state/book_spy_null.json", "2026-07-01")
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    d = c["detail"]["book_spy_null_rolled"]
    assert d["status"] == MISS and "did not roll" in d["detail"]
    assert "book_spy_null_rolled" in census_line(c)      # NAMED, not just counted


# ---------- due-ness must be artifact-derived ----------
def test_eval_not_due_when_nothing_matured(tmp_path):
    p = tmp_path / "data/intel/analyst_predictions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"resolve_by": "2027-01-01", "brier": None}) + "\n")
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    assert c["detail"]["eval_scored_when_due"]["status"] == NOT_DUE


def test_eval_MISS_when_matured_but_unscored(tmp_path):
    """T-331's disease: predictions matured and nothing scored them."""
    p = tmp_path / "data/intel/analyst_predictions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"resolve_by": "2026-07-01", "brier": None}) + "\n")
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    d = c["detail"]["eval_scored_when_due"]
    assert d["status"] == MISS and "UNSCORED" in d["detail"]


def test_eval_ADVANCED_when_scored_today(tmp_path):
    p = tmp_path / "data/intel/analyst_predictions.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join([
        json.dumps({"resolve_by": "2026-07-01", "brier": None}),
        json.dumps({"resolve_by": "2026-07-01", "brier": 0.2, "scored_at": AS_OF})]))
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    assert c["detail"]["eval_scored_when_due"]["status"] == ADVANCED


def test_unknowable_dueness_is_a_MISS_not_a_NOT_DUE(tmp_path):
    """'Probably not due' is the same silence the census exists to eliminate."""
    c = run_census(root=str(tmp_path), as_of=AS_OF)   # no scan state at all
    d = c["detail"]["scan_filed_when_due"]
    assert d["status"] == MISS and "due-ness unknown" in d["detail"]


# ---------- clock 5: a self-explained zero IS an advance ----------
def test_scan_self_explained_zero_counts_as_ADVANCED(tmp_path):
    (tmp_path / "data/intel").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data/intel/thesis_scan_state.json").write_text(json.dumps({"due": True}))
    (tmp_path / "data/intel/thesis_scan_provenance.jsonl").write_text(
        json.dumps({"as_of": AS_OF, "filed": 0, "reason": "no_qualifying_events"}) + "\n")
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    d = c["detail"]["scan_filed_when_due"]
    assert d["status"] == ADVANCED and "self-explained zero" in d["detail"]


def test_scan_due_but_silent_is_a_MISS(tmp_path):
    (tmp_path / "data/intel").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data/intel/thesis_scan_state.json").write_text(json.dumps({"due": True}))
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    assert c["detail"]["scan_filed_when_due"]["status"] == MISS


# ---------- clock 8: due-ness from the orders artifact ----------
def test_exec_ledger_not_due_without_fills(tmp_path):
    p = tmp_path / "data/paper_state/orders.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"trade_date": AS_OF, "state": "QUEUED"}) + "\n")
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    assert c["detail"]["exec_ledger_on_fill_days"]["status"] == NOT_DUE


def test_exec_ledger_MISS_when_filled_but_no_ledger_row(tmp_path):
    p = tmp_path / "data/paper_state/orders.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"trade_date": AS_OF, "state": "FILLED"}) + "\n")
    c = run_census(root=str(tmp_path), as_of=AS_OF)
    d = c["detail"]["exec_ledger_on_fill_days"]
    assert d["status"] == MISS and "fill(s) today but ledger" in d["detail"]


# ---------- READ-ONLY: the census never repairs what it measures ----------
def test_census_is_read_only(tmp_path):
    p = _book(tmp_path, "data/state/book_spy_null.json", "2026-07-01")
    before = p.read_bytes()
    listing_before = sorted(x.name for x in (tmp_path / "data/state").iterdir())
    run_census(root=str(tmp_path), as_of=AS_OF)
    assert p.read_bytes() == before                  # the stale artifact is NOT repaired
    assert sorted(x.name for x in (tmp_path / "data/state").iterdir()) == listing_before


# ---------- the headline line ----------
def test_clean_census_says_all_clocks_running(tmp_path):
    import paper_trader.clock_census as cc
    monkey = [cc.ClockResult("a", ADVANCED, "ok"), cc.ClockResult("b", NOT_DUE, "n/a")]
    line = census_line({"degraded": False, "clocks_advanced": "1/1", "n_not_due": 1,
                        "missed": []})
    assert "all clocks running" in line


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


# ---------- THE INTEGRATION BAR: a REAL injected miss, end-to-end ----------
def test_INTEGRATION_injected_freeze_flows_artifact_to_flag_to_notify(tmp_path):
    """The dispatch's integration bar, locked as a regression: freeze ONE clock in a
    realistic full-artifact day and assert it is (a) isolated as the ONLY new miss,
    (b) stamped on the heartbeat under the agreed `clock_census` key, and (c) NAMED in a
    same-day notify. Asserted on the DELTA, because a synthetic root legitimately lacks
    alt-data feeds — the census flagging that too is it being correct, not broken."""
    from paper_trader.heartbeat import PaperHeartbeat

    def _seed(day):
        (tmp_path / "data/state").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data/intel").mkdir(parents=True, exist_ok=True)
        (tmp_path / "data/paper_state").mkdir(parents=True, exist_ok=True)
        for n in ("sleeve_tracking", "btc_shadow_tracking", "dbmf_shadow_tracking",
                  "event_shadow_book", "analyst_desk_book", "thesis_book_machine",
                  "thesis_book_user_seeded", "book_spy_null", "book_damped_offense",
                  "book_quality_satellite", "book_sleeve_tier50k", "llm_shadow_book"):
            (tmp_path / f"data/state/{n}.json").write_text(json.dumps({"days": [{"date": day}]}))
        for d in ("analyst_notes", "analyst_notes_agentic"):
            (tmp_path / f"data/intel/{d}").mkdir(parents=True, exist_ok=True)
            (tmp_path / f"data/intel/{d}/{day}.json").write_text("{}")
        (tmp_path / "data/intel/analyst_predictions.jsonl").write_text(
            json.dumps({"resolve_by": "2027-01-01"}) + "\n")
        (tmp_path / "data/intel/thesis_scan_state.json").write_text(json.dumps({"due": False}))
        (tmp_path / "data/intel/thesis_scan_provenance.jsonl").write_text(
            json.dumps({"as_of": day}) + "\n")
        (tmp_path / "data/state/stage2_clock.jsonl").write_text(json.dumps({"date": day}) + "\n")
        (tmp_path / "data/paper_state/orders.jsonl").write_text(
            json.dumps({"trade_date": day, "state": "QUEUED"}) + "\n")
        p = tmp_path / f"data/intel/news_panel/{day[:4]}/{day[5:7]}"
        p.mkdir(parents=True, exist_ok=True)
        (p / f"news_{day[:7].replace('-', '')}.parquet").write_text("x")

    import datetime as _dt
    day = _dt.date.today().isoformat()          # news mtime must be TODAY by construction
    _seed(day)
    before = {m["clock"] for m in run_census(root=str(tmp_path), as_of=day)["missed"]}

    # INJECT: a book that silently stopped rolling weeks ago (the exact disease)
    (tmp_path / "data/state/book_quality_satellite.json").write_text(
        json.dumps({"days": [{"date": "2026-07-15"}]}))
    after = run_census(root=str(tmp_path), as_of=day)
    delta = {m["clock"] for m in after["missed"]} - before
    assert delta == {"book_quality_sat_rolled"}          # isolated as the ONLY new miss

    fired = []
    hb = PaperHeartbeat(status_path=str(tmp_path / "data/state/paper_heartbeat.json"),
                        root=str(tmp_path))
    hb._notify = lambda m: fired.append(m)
    hb.record_clock_census(after)
    st = json.loads((tmp_path / "data/state/paper_heartbeat.json").read_text())
    assert "clock_census" in st and st["clock_census"]["degraded"] is True   # E's drill key
    assert "book_quality_sat_rolled" in [m["clock"] for m in st["clock_census"]["missed"]]
    assert len(fired) == 1 and "book_quality_sat_rolled" in fired[0]         # NAMED, same-day
