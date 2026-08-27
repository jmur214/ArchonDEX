"""tests/test_expiry_warning_t347.py — T-347.

Two units from the director's rulings on the T-343/T-346 wave:
  * the APPROACHING-EXPIRY warning — the recovery window gets a voice BEFORE it acts.
    Receipt: the machine's first two theses opened at age 7 of a 10-day window. Three
    days of margin, and nothing warned. A bound that only speaks at the moment it
    destroys something is a trapdoor, not a guard.
  * the ADVISOR-SURFACE clock — the cadence lint's first catch, given a CONSUMER
    instead of an exemption.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.clock_census import (  # noqa: E402
    ADVANCED, ADVISOR_BUDGET_DAYS, CADENCE_CLAIMS, MISS, NOT_DUE, REGISTRY,
    _advisor_surface_rendered, _md_header_date, unregistered_cadences)
from paper_trader.heartbeat import PaperHeartbeat  # noqa: E402
from paper_trader.thesis_book import (  # noqa: E402
    EXPIRY_WARN_FRACTION, MACHINE_DESK, RECOVERY_WINDOW_DAYS, ThesisBook,
    _expiry_warnings)


def _th(tid="T1", as_of="2026-08-19", reason="awaiting price for FN"):
    return {"thesis_id": tid, "as_of": as_of, "_pending_reason": reason,
            "instruments": [{"symbol": "FN", "role": "primary", "weight_hint": 1.0,
                             "mapping_reason": "r"}]}


# ---------- the warning fires on the clock that actually expires ----------
def test_warns_once_half_the_window_is_burned():
    w = _expiry_warnings([_th(as_of="2026-08-19")], "2026-08-24")     # age 5 of 10
    assert len(w) == 1 and w[0]["days_to_expiry"] == 5 and w[0]["age_days"] == 5


def test_silent_before_the_halfway_mark():
    assert _expiry_warnings([_th(as_of="2026-08-19")], "2026-08-23") == []   # age 4


def test_the_real_near_miss_would_have_warned():
    """The receipt: filed 08-19, opened 08-26 at age 7 of 10. Under this guard it would
    have spoken on 08-24, three days before it was in danger of being thrown away."""
    w = _expiry_warnings([_th(as_of="2026-08-19")], "2026-08-26")
    assert w and w[0]["days_to_expiry"] == 3


def test_the_warning_runs_on_FILING_age_not_queue_time():
    """These are different clocks: a thesis parked on its first due day has queue-age
    filed+1. A guard measured on a different clock than the bound it guards fires at the
    wrong time — expiry is decided on filing age, so the warning must be too."""
    th = _th(as_of="2026-08-19")
    th["_pending_since"] = "2026-08-25"          # only just queued...
    w = _expiry_warnings([th], "2026-08-26")     # ...but 7 days old since FILING
    assert w and w[0]["age_days"] == 7


def test_the_warning_names_what_it_is_blocked_on():
    """A countdown without the blocker is an alarm nobody can act on."""
    w = _expiry_warnings([_th(reason="awaiting price for AMTM")], "2026-08-26")
    assert "AMTM" in w[0]["blocked_on"]


def test_a_thesis_with_no_recorded_reason_still_warns_and_says_so():
    th = _th(); th.pop("_pending_reason")
    w = _expiry_warnings([th], "2026-08-26")
    assert w and "not recorded" in w[0]["blocked_on"]


def test_most_urgent_first():
    w = _expiry_warnings([_th("late", as_of="2026-08-21"), _th("urgent", as_of="2026-08-18")],
                         "2026-08-26")
    assert [x["thesis_id"] for x in w] == ["urgent", "late"]


def test_threshold_is_half_the_window_by_construction():
    """If the window is retuned the warning must follow it — never a second hard-coded
    number to drift out of step."""
    assert EXPIRY_WARN_FRACTION == 0.5
    w = _expiry_warnings([_th(as_of="2026-08-19")],
                         str((__import__("pandas").Timestamp("2026-08-19")
                              + __import__("pandas").Timedelta(
                                  days=int(RECOVERY_WINDOW_DAYS * EXPIRY_WARN_FRACTION))).date()))
    assert w, "the warning must fire exactly at the halfway mark"


# ---------- it reaches the record and the notify path ----------
def test_the_warning_reaches_the_book_summary_not_just_state(tmp_path):
    """A warning buried in state is the silence it exists to end — the pulse reads the
    SUMMARY, so that is where it has to appear."""
    b = ThesisBook(root=str(tmp_path))
    src = tmp_path / "data/intel/thesis_calls.jsonl"
    src.parent.mkdir(parents=True, exist_ok=True)
    src.write_text(json.dumps({"schema_version": "thesis_call/v1", "thesis_id": "TX",
                               "as_of": "2026-08-19", "origin": "machine",
                               "theme_class": "t", "conviction": 0.8, "horizon_days": 60,
                               "instruments": [{"symbol": "FN", "role": "primary",
                                                "weight_hint": 1.0, "mapping_reason": "r"}],
                               "falsifiers": [{"kind": "qualitative", "statement": "s",
                                               "check_by": "2027-01-01"}]}) + "\n")
    st = b.record("2026-08-26", closes={"SPY": 600.0})      # FN unpriced -> pending
    assert st["n_pending"] == 1
    assert st["expiring"] and st["expiring"][0]["days_to_expiry"] == 3
    assert any("from EXPIRY" in r for r in b._state()["days"][-1]["reasons"])


def test_an_open_thesis_is_not_warned_about(tmp_path):
    """Only the PENDING queue can expire. Warning about an open position would be noise
    that trains the alarm away."""
    b = ThesisBook(root=str(tmp_path))
    b.record("2026-08-26", closes={"FN": 10.0, "SPY": 600.0},
             theses=[{"schema_version": "thesis_call/v1", "thesis_id": "TY",
                      "as_of": "2026-08-19", "origin": "machine", "theme_class": "t",
                      "conviction": 0.8, "horizon_days": 60,
                      "instruments": [{"symbol": "FN", "role": "primary",
                                       "weight_hint": 1.0, "mapping_reason": "r"}],
                      "falsifiers": [{"kind": "qualitative", "statement": "s",
                                      "check_by": "2027-01-01"}]}])
    assert b._summary(b._state())["expiring"] == []


def test_notify_fires_and_names_the_thesis_and_the_blocker(tmp_path):
    hb = PaperHeartbeat(root=str(tmp_path))
    hb.record_thesis_expiry("thesis_machine", [
        {"thesis_id": "m-2026-08-19-geopolitical", "filed_date": "2026-08-19",
         "age_days": 7, "days_to_expiry": 3, "blocked_on": "awaiting price for AMTM",
         "window_days": 10}])
    log = (tmp_path / "data/state/paper_alerts.log").read_text()
    assert "THESIS-EXPIRY" in log and "geopolitical" in log and "AMTM" in log


def test_no_pending_theses_fires_nothing(tmp_path):
    hb = PaperHeartbeat(root=str(tmp_path))
    hb.record_thesis_expiry("thesis_machine", [])
    assert not (tmp_path / "data/state/paper_alerts.log").exists()


def test_expiry_block_is_orthogonal_to_the_trading_verdict(tmp_path):
    """A research book's stalled thesis must never flip canonical and fail the Batch job."""
    hb = PaperHeartbeat(root=str(tmp_path))
    hb.record_thesis_expiry("thesis_machine", [
        {"thesis_id": "T1", "filed_date": "2026-08-19", "age_days": 7,
         "days_to_expiry": 3, "blocked_on": "x", "window_days": 10}])
    st = json.loads((tmp_path / "data/state/paper_heartbeat.json").read_text())
    assert "thesis_expiry" in st
    assert st.get("canonical") is not False or "canonical" not in st


def test_two_desks_do_not_overwrite_each_other(tmp_path):
    hb = PaperHeartbeat(root=str(tmp_path))
    w = [{"thesis_id": "T1", "filed_date": "2026-08-19", "age_days": 7,
          "days_to_expiry": 3, "blocked_on": "x", "window_days": 10}]
    hb.record_thesis_expiry("thesis_machine", w)
    hb.record_thesis_expiry("thesis_user_seeded", w)
    st = json.loads((tmp_path / "data/state/paper_heartbeat.json").read_text())
    assert set(st["thesis_expiry"]) == {"thesis_machine", "thesis_user_seeded"}


# ---------- the advisor-surface clock ----------
def _surface(tmp_path, stamp):
    d = tmp_path / "docs/State"
    d.mkdir(parents=True, exist_ok=True)
    (d / "advisor_surface.md").write_text(f"# Advisor surface — {stamp}\n\nbody\n")
    return tmp_path


def test_advisor_clock_is_registered_and_the_lint_entry_now_points_at_it():
    assert "advisor_surface_rendered" in {c.name for c in REGISTRY}
    assert CADENCE_CLAIMS["intelligence/analyst/advisor_surface.py"] == \
        "clock:advisor_surface_rendered"
    assert not unregistered_cadences()


def test_advisor_clock_parses_As_real_header_format(tmp_path):
    """It must read A's ACTUAL rendered header, not one I imagined — same `# Title — date`
    shape the digest uses, which is why both share one parser."""
    stamp, why = _md_header_date(_surface(tmp_path, "2026-08-26") /
                                 "docs/State/advisor_surface.md")
    assert stamp == "2026-08-26" and why == "ok"


def test_advisor_within_monthly_budget_is_not_due(tmp_path):
    r = _advisor_surface_rendered(_surface(tmp_path, "2026-08-01"), "2026-08-26")
    assert r.status == NOT_DUE


def test_advisor_written_today_advances(tmp_path):
    assert _advisor_surface_rendered(_surface(tmp_path, "2026-08-26"),
                                     "2026-08-26").status == ADVANCED


def test_advisor_never_rendered_reports_the_honest_state(tmp_path):
    """Until A's generator lands this is a TRUE finding, not a broken clock."""
    r = _advisor_surface_rendered(tmp_path, "2026-08-26")
    assert r.status == MISS and "never rendered" in r.detail


def test_advisor_budget_is_monthly_plus_grace():
    assert 31 <= ADVISOR_BUDGET_DAYS <= 40


def test_advisor_date_comes_from_the_header_not_mtime(tmp_path):
    root = _surface(tmp_path, "2026-06-01")        # written now, stamped long ago
    assert _advisor_surface_rendered(root, "2026-08-26").status == MISS
