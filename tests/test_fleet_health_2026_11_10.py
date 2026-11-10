"""Fleet health (2026-11-10) — the janitor reads the paper fleet's own record.

Fixtures are the REAL objects read from S3 on 2026-11-10: account 2 halted since
2026-11-06 on an unhandled MTUM 4-for-1 split, two virtual books carrying a corrupt
2026-11-05 day marked clean, one book parked 74 sessions, the rest healthy."""
from __future__ import annotations

import inspect
import json
from datetime import date
from pathlib import Path
from typing import Dict, Optional, Tuple

import pytest

from scripts import fleet_health as fh
from scripts import janitor_nightly as jn

FIX = Path(__file__).parent / "fixtures" / "fleet_health_2026_11_10"
TODAY = date(2026, 11, 10)
HB = {"paper_state": "hb_account1_clean.json", "paper_state_offense_sso": "hb_account2_halted.json",
      "paper_state_ai_trader": "hb_account3_clean.json"}


def _real_store() -> Dict[str, bytes]:
    store = {f"{p}/data/state/paper_heartbeat.json": (FIX / f).read_bytes() for p, f in HB.items()}
    for b in fh.BOOKS:
        store[f"{fh.BOOK_PREFIX}/data/state/{b}"] = (FIX / b).read_bytes()
    return store


def _reader(store: Dict[str, bytes]):
    def read(key: str) -> Tuple[Optional[bytes], str]:
        return (store[key], "ok") if key in store else (None, "missing: no such key")
    return read


def _healthy_store() -> Dict[str, bytes]:
    """The real store with every known defect replaced by a healthy real object."""
    s = _real_store()
    s["paper_state_offense_sso/data/state/paper_heartbeat.json"] = (FIX / "hb_account1_clean.json").read_bytes()
    clean = (FIX / "book_spy_null.json").read_bytes()
    for b in ("book_damped_offense.json", "book_quality_satellite.json", "book_momentum_satellite.json"):
        s[f"{fh.BOOK_PREFIX}/data/state/{b}"] = clean
    return s


def test_the_REAL_fleet_of_2026_11_10_is_NOT_healthy_and_every_defect_is_named():
    v = fh.evaluate(_reader(_real_store()), today=TODAY)
    assert not v.ok and not v.unknown and v.checked == 8
    text = v.detail
    assert "account-2 deploy candidate: NON-CANONICAL on 2026-11-10" in text and "UNEXPLAINED position" in text
    assert "momentum_satellite: implausible one-day gap" in text and "2026-11-05" in text
    assert "quality_satellite: implausible one-day gap" in text
    assert "damped_offense_t298: parked 74 consecutive session(s)" in text
    assert "account-1" not in text and "account-3" not in text and "spy_null" not in text


def test_POSITIVE_CONTROL_a_fleet_with_no_defect_passes():
    v = fh.evaluate(_reader(_healthy_store()), today=TODAY)
    assert v.ok, v.detail


def test_an_unreadable_object_FAILS_it_is_never_healthy_by_absence():
    s = _healthy_store()
    del s["paper_state_ai_trader/data/state/paper_heartbeat.json"]
    v = fh.evaluate(_reader(s), today=TODAY)
    assert not v.ok and "UNKNOWN account-3 ai trader" in v.detail
    s = _healthy_store()
    s["paper_state/data/state/book_spy_null.json"] = b"{not json"
    v = fh.evaluate(_reader(s), today=TODAY)
    assert not v.ok and "unparseable" in v.detail


def test_a_SILENT_account_is_named_with_its_age():
    v = fh.evaluate(_reader(_healthy_store()), today=date(2026, 11, 20))
    assert not v.ok and v.detail.count("SILENT — last run 2026-11-10 (10 days ago)") == 3


def test_a_weekend_is_not_a_silent_stop():
    assert fh.evaluate(_reader(_healthy_store()), today=date(2026, 11, 14)).ok


def test_an_ordinary_bad_day_is_not_a_defect_and_a_degraded_day_is_skipped():
    book = json.loads((FIX / "book_spy_null.json").read_text())
    days = [{"date": "d1", "degraded": False, "book_growth": 1.0, "twin_growth": 1.0},
            {"date": "d2", "degraded": False, "book_growth": 0.92, "twin_growth": 0.99}]
    assert fh.judge_book("b", {**book, "days": days}) == []           # −7 pp: a real market gap
    days[1]["book_growth"] = 0.25
    assert "implausible one-day gap" in fh.judge_book("b", {**book, "days": days})[0]
    days[1]["degraded"] = True
    assert fh.judge_book("b", {**book, "days": days}) == []           # parked days are not marks


def test_a_heartbeat_missing_its_fields_is_a_problem_not_a_pass():
    assert fh.judge_heartbeat("a", {}, TODAY) == ["a: heartbeat has no last_run"]
    assert "unreadable run_date" in fh.judge_heartbeat("a", {"last_run": {"canonical": True}}, TODAY)[0]
    hb = {"last_run": {"run_date": "2026-11-10"}}                      # canonical absent
    assert "NON-CANONICAL" in fh.judge_heartbeat("a", hb, TODAY)[0]


def test_the_book_roster_equals_the_live_books_registered_state_paths():
    from paper_trader import live_books
    src = inspect.getsource(live_books)
    import re
    registered = sorted(Path(p).name for p in re.findall(r'state_path="(data/state/book_[a-z0-9_]+\.json)"', src))
    assert registered == sorted(fh.BOOKS), "a live book was added or removed — update fleet_health.BOOKS"


def test_the_janitor_RUNS_the_check_and_reports_a_reader_crash(monkeypatch):
    assert "check_fleet_health()" in inspect.getsource(jn.run_checks)
    monkeypatch.setattr(jn.ledger_backup, "read_remote", _reader(_real_store()))
    c = jn.check_fleet_health()
    assert c.name == "fleet_health" and c.ok is False and "account-2 deploy candidate" in c.detail

    def boom(key):
        raise RuntimeError("reader broke")
    monkeypatch.setattr(jn.ledger_backup, "read_remote", boom)
    c = jn.check_fleet_health()
    assert c.ok is False and "evaluate raised RuntimeError" in c.detail
