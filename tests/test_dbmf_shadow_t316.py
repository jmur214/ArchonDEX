"""T-316 — DbmfShadowBook: report-only forward shadow of a 5% managed-futures leg.

Modeled on test_btc_shadow_t276.py. Verifies the frozen construction, fail-open
degradation, idempotency, and the pre-registered forward-gate reporting.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.dbmf_shadow import (  # noqa: E402
    DBMF_W, GATE_A_CORR_MAX, GATE_B_MIN_FORWARD_MONTHS, DbmfShadowBook)


def test_variant_is_95_sleeve_plus_5_dbmf(tmp_path):
    b = DbmfShadowBook(root=str(tmp_path))
    b.record("2026-07-27", 0.001, dbmf_close=30.00)          # day 1: price only, no return yet
    b.record("2026-07-28", 0.002, dbmf_close=30.60)          # DBMF +2%
    pt = b._load()[-1]
    assert pt["degraded"] is False
    assert pt["dbmf_ret"] == pytest.approx(0.02, abs=1e-9)
    assert pt["variant_ret"] == pytest.approx((1 - DBMF_W) * 0.002 + DBMF_W * 0.02, abs=1e-9)


def test_fail_open_when_no_price(tmp_path):
    b = DbmfShadowBook(root=str(tmp_path))
    b.record("2026-07-27", 0.001, dbmf_close=None)
    pt = b._load()[-1]
    assert pt["degraded"] is True
    assert pt["dbmf_ret"] == 0.0                              # parked, never fabricated
    assert pt["variant_ret"] == pytest.approx((1 - DBMF_W) * 0.001, abs=1e-9)


def test_idempotent_on_trade_date(tmp_path):
    b = DbmfShadowBook(root=str(tmp_path))
    b.record("2026-07-27", 0.001, dbmf_close=30.0)
    b.record("2026-07-27", 0.001, dbmf_close=30.0)
    assert len([p for p in b._load() if p["date"] == "2026-07-27"]) == 1


def test_navs_compound_and_twin_diverges(tmp_path):
    b = DbmfShadowBook(root=str(tmp_path))
    px = 30.0
    for i in range(10):
        px *= 1.001
        s = b.record(f"2026-07-{10+i:02d}", 0.002, dbmf_close=px)
    assert s["n_clean"] == 10
    assert s["base_nav"] > 1.0 and s["variant_nav"] > 1.0
    # sleeve (+0.2%/day) outruns the 5% MF leg (+0.1%/day) → variant trails base
    assert s["variant_nav"] < s["base_nav"]


def test_forward_gates_report_only_and_never_premature(tmp_path):
    b = DbmfShadowBook(root=str(tmp_path))
    px = 30.0
    for i in range(25):
        px *= 1.0005
        b.record(f"2026-07-{1+i:02d}" if i < 30 else "x", 0.001, dbmf_close=px)
    g = b.forward_gates()
    assert "gate_A_crisis_independence" in g and "gate_B_carry_drag" in g
    assert g["gate_A_crisis_independence"]["status"].startswith("no crisis")   # no -10% DD yet
    assert g["gate_B_carry_drag"]["status"] == "accruing"                      # « 24 months
    assert g["promote_to_paper_leg"] is False
    assert g["thresholds"]["A_corr_max"] == GATE_A_CORR_MAX
    assert g["thresholds"]["B_min_months"] == GATE_B_MIN_FORWARD_MONTHS


def test_gate_a_fires_and_measures_crisis_corr(tmp_path):
    """A ≥10% sleeve drawdown with DBMF moving OPPOSITE → gate A can PASS (corr ≤ 0.30)."""
    b = DbmfShadowBook(root=str(tmp_path))
    px = 30.0
    for i in range(30):                       # sleeve falls ~12%, DBMF rises (the hedge case)
        px *= 1.004
        b.record(f"2026-08-{1+i:02d}", -0.004, dbmf_close=px)
    g = b.forward_gates()
    a = g["gate_A_crisis_independence"]
    assert a["status"] in ("PASS", "FAIL")           # fired (a real crisis window found)
    assert a["sleeve_dd"] <= -0.10
    assert a["crisis_corr"] is not None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
