"""T-302 — LlmShadowBook: report-only virtual book of the analyst's hypothetical actions.

Generalizes the T-276 btc_shadow discipline. Verifies signal-t/fill-t+1 (no look-ahead),
firewall RE-enforcement (reject + log, never clamp), the 60/40 benchmark twin, degraded
parking, and idempotency. Report-only — these tests never touch trading.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.llm_shadow_book import (  # noqa: E402
    LlmShadowBook, MAX_WEIGHT, MAX_GROSS, MAX_TURNOVER, HAIRCUT)


def _note(as_of, actions):
    return {"as_of": as_of, "schema_version": "analyst_note/v1",
            "hypothetical_actions": [
                {"account": "shadow", "symbol": s, "set_weight": w, "target_weight": w}
                for s, w in actions]}


def _book(tmp_path):
    return LlmShadowBook(root=str(tmp_path))


def test_fill_at_next_close_and_nav_moves(tmp_path):
    b = _book(tmp_path)
    # day 1: yesterday's note sets XYZ 10%; book fills at today's close (no return yet)
    b.record("2026-07-10", closes={"SPY": 100.0, "AGG": 100.0, "XYZ": 50.0},
             note=_note("2026-07-09", [("XYZ", 0.10)]))
    pt1 = b._state()["points"][-1]
    assert pt1["action"] == "applied" and pt1["positions"] == {"XYZ": 0.1}
    # day 2: XYZ +10% → book earns 0.10*0.10 = +1.0% (minus day-1 haircut)
    hb = b.record("2026-07-11", closes={"SPY": 110.0, "AGG": 100.0, "XYZ": 55.0},
                  note=_note("2026-07-10", [("XYZ", 0.10)]))
    pt2 = b._state()["points"][-1]
    assert pt2["book_ret"] == pytest.approx(0.01, abs=1e-6)   # 10% weight * 10% move
    assert hb["book_nav"] > 1.0 and hb["armed"] is True


def test_twin_is_60_40_spy_agg(tmp_path):
    b = _book(tmp_path)
    b.record("2026-07-10", closes={"SPY": 100.0, "AGG": 100.0}, note=_note("2026-07-09", []))
    b.record("2026-07-11", closes={"SPY": 110.0, "AGG": 105.0}, note=_note("2026-07-10", []))
    pt = b._state()["points"][-1]
    # 0.6*(+10%) + 0.4*(+5%) = +8%
    assert pt["twin_ret"] == pytest.approx(0.6 * 0.10 + 0.4 * 0.05, abs=1e-6)


def test_idempotent_per_date(tmp_path):
    b = _book(tmp_path)
    n = _note("2026-07-09", [("XYZ", 0.1)])
    b.record("2026-07-10", closes={"SPY": 100.0, "AGG": 100.0, "XYZ": 50.0}, note=n)
    b.record("2026-07-10", closes={"SPY": 100.0, "AGG": 100.0, "XYZ": 50.0}, note=n)
    assert len([p for p in b._state()["points"] if p["date"] == "2026-07-10"]) == 1


def test_degraded_no_prices_holds(tmp_path):
    b = _book(tmp_path)
    b.record("2026-07-10", closes={"SPY": 100.0, "AGG": 100.0, "XYZ": 50.0}, note=_note("2026-07-09", [("XYZ", 0.1)]))
    hb = b.record("2026-07-11", closes=None, note=_note("2026-07-10", [("XYZ", 0.2)]))
    pt = b._state()["points"][-1]
    assert pt["degraded"] is True
    assert pt["positions"] == {"XYZ": 0.1}      # HELD — not rebalanced to the new note
    assert hb["n_degraded"] == 1


def test_degraded_when_held_name_has_no_price(tmp_path):
    b = _book(tmp_path)
    b.record("2026-07-10", closes={"SPY": 100.0, "AGG": 100.0, "XYZ": 50.0}, note=_note("2026-07-09", [("XYZ", 0.1)]))
    # XYZ missing from closes on day 2 → degraded, hold
    b.record("2026-07-11", closes={"SPY": 110.0, "AGG": 100.0}, note=_note("2026-07-10", [("XYZ", 0.1)]))
    assert b._state()["points"][-1]["degraded"] is True


def test_no_note_holds_positions(tmp_path):
    b = _book(tmp_path)
    b.record("2026-07-10", closes={"SPY": 100.0, "AGG": 100.0, "XYZ": 50.0}, note=_note("2026-07-09", [("XYZ", 0.1)]))
    b.record("2026-07-11", closes={"SPY": 100.0, "AGG": 100.0, "XYZ": 50.0}, note=None, note_reason="none yet")
    pt = b._state()["points"][-1]
    assert pt["action"].startswith("no_note") and pt["positions"] == {"XYZ": 0.1}


def test_firewall_rejects_gross_over_2(tmp_path):
    b = _book(tmp_path)
    # 11 names at 20% = gross 2.2 > 2.0 → REJECT (never clamp)
    actions = [(f"N{i}", MAX_WEIGHT) for i in range(11)]
    closes = {"SPY": 100.0, "AGG": 100.0, **{f"N{i}": 10.0 for i in range(11)}}
    b.record("2026-07-10", closes=closes, note=_note("2026-07-09", actions))
    pt = b._state()["points"][-1]
    assert pt["action"].startswith("REJECTED") and "gross" in pt["action"]
    assert pt["positions"] == {}                # book untouched, not clamped to 2.0


def test_firewall_rejects_per_name_over_20pct(tmp_path):
    b = _book(tmp_path)
    b.record("2026-07-10", closes={"SPY": 100.0, "AGG": 100.0, "XYZ": 50.0},
             note=_note("2026-07-09", [("XYZ", 0.25)]))     # bypasses schema; C-layer must catch
    assert b._state()["points"][-1]["action"].startswith("REJECTED")


def test_firewall_rejects_turnover_over_50pct(tmp_path):
    b = _book(tmp_path)
    # from empty book: 3 names at 20% = turnover 0.60 > 0.50 → reject
    actions = [("A", 0.2), ("B", 0.2), ("C", 0.2)]
    closes = {"SPY": 100.0, "AGG": 100.0, "A": 10.0, "B": 10.0, "C": 10.0}
    b.record("2026-07-10", closes=closes, note=_note("2026-07-09", actions))
    assert "turnover" in b._state()["points"][-1]["action"]


def test_ships_dormant_but_armed(tmp_path):
    # no notes dir → loads no note → degraded/no-note, but records + persists (armed on prices)
    b = _book(tmp_path)
    hb = b.record("2026-07-10", closes={"SPY": 100.0, "AGG": 100.0})
    assert hb["armed"] is True and b._state()["points"][-1]["action"].startswith("no_note")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
