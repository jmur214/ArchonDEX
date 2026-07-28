"""T-322 — EventShadowBook: the report-only virtual event desk.

Modeled on test_btc_shadow_t276 / test_dbmf_shadow_t316. Verifies the frozen construction
(materiality floor, direction gate, size ∝ materiality, firewall caps), signal-t/fill-t+1,
own-horizon holding, the SPY twin, fail-closed parking, idempotency, the shared D/T-304
promotion bar, and that the SECOND desk is a parameterization (not a fork).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.event_shadow_book import (  # noqa: E402
    ANALYST_DESK, EVENT_DESK, GATE_MIN_CLOSED_PER_TYPE, MATERIALITY_FLOOR, MAX_WEIGHT,
    EventShadowBook, parse_horizon_days)


def _call(sym="ACME", direction="bullish", mat=0.8, horizon="5 trading days",
          etype="going_concern", as_of="2026-07-27"):
    return {"schema_version": "event_call/v1", "as_of": as_of, "symbol": sym,
            "event_type": etype, "materiality": mat, "direction": direction,
            "predictions": [{"statement": "s", "probability": 0.6, "horizon": horizon,
                             "resolver": {}}]}


# ---------- horizon parsing is FAIL-CLOSED ----------
@pytest.mark.parametrize("h,exp", [
    ("5 trading days", 5), ("3 days", 3), ("2 weeks", 10), ("1 month", 21),
    ("next day", 1), ("", None), ("soon", None), ("whenever the market realizes", None),
    ("900 days", None),                      # beyond MAX_HORIZON_DAYS → park
])
def test_parse_horizon_fail_closed(h, exp):
    assert parse_horizon_days(h, "2026-07-27") == exp


def test_unparseable_horizon_parks_never_guesses(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"ACME": 10.0, "SPY": 600.0},
             calls=[_call(horizon="when the dust settles")])
    st = b._state()
    assert st["open"] == []                                   # nothing opened
    assert any("horizon unparseable" in r for r in st["days"][-1]["reasons"])


# ---------- the qualification gate ----------
def test_neutral_and_low_materiality_never_open(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"ACME": 10.0, "SPY": 600.0},
             calls=[_call(direction="neutral"), _call(direction="uncertain"),
                    _call(sym="LOWM", mat=MATERIALITY_FLOOR - 0.01)])
    assert b._state()["open"] == []


def test_size_scales_with_materiality_and_signs_by_direction(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"BULL": 10.0, "BEAR": 20.0, "SPY": 600.0},
             calls=[_call(sym="BULL", mat=1.0, direction="bullish"),
                    _call(sym="BEAR", mat=0.5, direction="bearish")])
    pos = {p["symbol"]: p for p in b._state()["open"]}
    assert pos["BULL"]["weight"] == pytest.approx(MAX_WEIGHT * 1.0)
    assert pos["BULL"]["sign"] == 1
    assert pos["BEAR"]["weight"] == pytest.approx(MAX_WEIGHT * 0.5)
    assert pos["BEAR"]["sign"] == -1


def test_gross_cap_rejects_and_logs_never_clamps(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    calls = [_call(sym=f"S{i}", mat=1.0) for i in range(15)]     # 15 × 0.20 = 3.0 > 2.0
    closes = {f"S{i}": 10.0 for i in range(15)}
    closes["SPY"] = 600.0
    b.record("2026-07-28", closes=closes, calls=calls)
    st = b._state()
    gross = sum(abs(p["weight"]) for p in st["open"])
    assert gross <= 2.0 + 1e-9
    assert any("gross" in r and "REJECTED" in r for r in st["days"][-1]["reasons"])
    # rejected, not silently clamped: every OPEN position keeps its full intended weight
    assert all(p["weight"] == pytest.approx(MAX_WEIGHT) for p in st["open"])


# ---------- the desk mechanics ----------
def test_position_closes_at_its_own_horizon_with_costs_and_twin(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"ACME": 100.0, "SPY": 600.0},
             calls=[_call(horizon="2 trading days")])
    b.record("2026-07-29", closes={"ACME": 105.0, "SPY": 606.0})     # held=1, still open
    assert len(b._state()["open"]) == 1
    b.record("2026-07-30", closes={"ACME": 110.0, "SPY": 612.0})     # held=2 → CLOSE
    st = b._state()
    assert st["open"] == [] and len(st["closed"]) == 1
    c = st["closed"][0]
    assert c["gross_ret"] == pytest.approx(0.10)                     # +10% long
    assert c["net_ret"] == pytest.approx(0.10 - 2 * 0.0025)          # both sides costed
    assert c["twin_ret"] == pytest.approx(0.02)                      # SPY over the SAME window
    assert c["excess_vs_twin"] == pytest.approx(0.10 - 0.005 - 0.02)


def test_bearish_position_profits_when_name_falls(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"ACME": 100.0, "SPY": 600.0},
             calls=[_call(direction="bearish", horizon="1 trading day")])
    b.record("2026-07-29", closes={"ACME": 90.0, "SPY": 600.0})
    c = b._state()["closed"][0]
    assert c["gross_ret"] == pytest.approx(0.10)                     # short gained 10%


def test_missing_price_at_horizon_holds_degraded_not_fabricated(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"ACME": 100.0, "SPY": 600.0},
             calls=[_call(horizon="1 trading day")])
    b.record("2026-07-29", closes={"SPY": 600.0})                    # ACME price missing
    st = b._state()
    assert len(st["open"]) == 1 and st["closed"] == []               # held, not closed
    assert st["days"][-1]["degraded"] is True


def test_idempotent_per_date(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    b.record("2026-07-28", closes={"ACME": 10.0, "SPY": 600.0}, calls=[_call()])
    b.record("2026-07-28", closes={"ACME": 10.0, "SPY": 600.0}, calls=[_call()])
    assert len(b._state()["open"]) == 1 and len(b._state()["days"]) == 1


# ---------- dormancy + the second desk is a PARAMETERIZATION ----------
def test_dormant_but_armed_when_no_source(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    s = b.record("2026-07-28", closes={"SPY": 600.0})                # no calls injected
    assert s["armed"] is True and s["n_open"] == 0
    assert any("dormant-but-armed" in r for r in b._state()["days"][-1]["reasons"])


def test_second_desk_is_same_machinery_different_state(tmp_path):
    ev = EventShadowBook(cfg=EVENT_DESK, root=str(tmp_path))
    an = EventShadowBook(cfg=ANALYST_DESK, root=str(tmp_path))
    assert type(ev) is type(an)                                      # no fork
    assert ev._file() != an._file()                                  # separate books
    ev.record("2026-07-28", closes={"ACME": 10.0, "SPY": 600.0}, calls=[_call()])
    assert len(ev._state()["open"]) == 1
    assert an._state()["open"] == []                                 # independent state


# ---------- the SHARED D/T-304 gate ----------
def test_promotion_gate_uses_D_bar_and_never_passes_prematurely(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    st = b._state()
    st["closed"] = [{"event_type": "going_concern", "excess_vs_twin": 0.02, "net_ret": 0.02}
                    for _ in range(GATE_MIN_CLOSED_PER_TYPE - 1)]    # one short of the bar
    b._write(st)
    g = b.promotion_gates()
    assert g["per_event_type"]["going_concern"]["status"].startswith("accruing")
    assert g["promote_to_paper_leg"] is False
    assert "D/T-304" in g["standard"]                                 # ONE shared standard


def test_promotion_gate_can_pass_on_consistent_positive_excess(tmp_path):
    b = EventShadowBook(root=str(tmp_path))
    st = b._state()
    st["closed"] = [{"event_type": "tender_offer", "excess_vs_twin": 0.03, "net_ret": 0.03}
                    for _ in range(GATE_MIN_CLOSED_PER_TYPE + 5)]
    b._write(st)
    g = b.promotion_gates()
    row = g["per_event_type"]["tender_offer"]
    assert row["status"] == "PASS" and row["ci_low"] > 0
    assert g["promote_to_paper_leg"] is True


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
