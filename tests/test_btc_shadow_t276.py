"""T-276 — BtcShadowTracker: report-only forward validation of the +5% BTC arm.

Verifies the frozen construction (variant = 0.95*sleeve + 0.05*btc_leg), fail-closed
degradation, idempotency, and the pre-registered forward-gate reporting. Report-only —
these tests never touch trading.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from paper_trader.btc_shadow import (  # noqa: E402
    BtcShadowTracker, BTC_W, WARMUP_DAYS, _btc_leg_today)


def _btc_series(n=260, seed=0, trend=1.0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2026-01-01", periods=n, freq="B")
    steps = rng.normal(0.001 * trend, 0.03, n)
    return pd.Series(1000 * np.exp(np.cumsum(steps)), index=idx)


def test_variant_is_95_sleeve_plus_5_btc_leg(tmp_path):
    b = _btc_series()
    date = b.index[-1].strftime("%Y-%m-%d")
    t = BtcShadowTracker(root=str(tmp_path))
    s = t.record(date, 0.001, cash_daily_rate=0.0, btc_hist=b, ibit_close=35.0, btc_close=float(b.iloc[-1]))
    pt = t._load()[-1]
    assert pt["degraded"] is False
    leg = _btc_leg_today(b, pd.Timestamp(date), 0.0)[0]
    assert pt["variant_ret"] == pytest.approx((1 - BTC_W) * 0.001 + BTC_W * leg, abs=1e-6)
    assert s["n_clean"] == 1


def test_fail_closed_when_history_too_short(tmp_path):
    short = _btc_series(n=WARMUP_DAYS - 20)          # below the 210d warmup
    date = short.index[-1].strftime("%Y-%m-%d")
    t = BtcShadowTracker(root=str(tmp_path))
    t.record(date, 0.002, cash_daily_rate=0.0001, btc_hist=short)
    pt = t._load()[-1]
    assert pt["degraded"] is True
    # BTC leg parked in cash — NOT a fabricated exposure
    assert pt["btc_exposure"] is None
    assert pt["btc_leg_ret"] == pytest.approx(0.0001)
    assert pt["variant_ret"] == pytest.approx((1 - BTC_W) * 0.002 + BTC_W * 0.0001, abs=1e-9)


def test_idempotent_on_trade_date(tmp_path):
    b = _btc_series()
    date = b.index[-1].strftime("%Y-%m-%d")
    t = BtcShadowTracker(root=str(tmp_path))
    t.record(date, 0.001, btc_hist=b)
    t.record(date, 0.001, btc_hist=b)            # same day twice
    assert len([p for p in t._load() if p["date"] == date]) == 1


def test_nav_compounds_forward(tmp_path):
    b = _btc_series(n=260)
    t = BtcShadowTracker(root=str(tmp_path))
    navs = []
    for i in range(215, 240):
        d = b.index[i].strftime("%Y-%m-%d")
        t.record(d, 0.0005, cash_daily_rate=0.0, btc_hist=b.iloc[:i + 1])
        navs.append(t._load()[-1]["variant_nav"])
    assert len(navs) == 25
    assert navs[-1] != navs[0]                   # NAV moves forward
    assert t._load()[-1]["variant_nav"] > 0


def test_forward_gates_report_only_structure(tmp_path):
    b = _btc_series(n=260)
    t = BtcShadowTracker(root=str(tmp_path))
    for i in range(215, 235):
        t.record(b.index[i].strftime("%Y-%m-%d"), 0.0005, cash_daily_rate=0.0, btc_hist=b.iloc[:i + 1])
    g = t.forward_gates()
    assert "gate_A_oos_winter" in g and "gate_B_directional" in g and "gate_C_ibit_basis" in g
    assert "promote_to_paper_leg" in g
    # 20 days ≪ 18 months → gate B must be accruing, never a premature PASS
    assert g["gate_B_directional"]["status"] == "accruing"
    assert g["promote_to_paper_leg"] is False


def test_would_be_trade_is_report_only_notional(tmp_path):
    b = _btc_series()
    date = b.index[-1].strftime("%Y-%m-%d")
    t = BtcShadowTracker(root=str(tmp_path))
    t.record(date, 0.001, btc_hist=b)
    pt = t._load()[-1]
    assert "btc_would_be_trade" in pt and pt["btc_would_be_trade"] >= 0.0


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
