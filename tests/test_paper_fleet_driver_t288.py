# tests/test_paper_fleet_driver_t288.py
"""T-288 fleet — the shared sleeve-FAMILY driver pipeline (Accounts 2/3):
_run_family_strategy (fetch → drop today-bar → stale HALT → construct → stage)
and _record_family_tracker (exec-gate record). Account-1 (trend_sleeve) stays
inline + untouched.
"""
from __future__ import annotations

import datetime as dt
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from paper_trader import FakePaperClient, OrderManager, PaperConfig
from paper_trader.offense_sso_constructor import OffenseSSOConstructor
from paper_trader.sleeve_btc_constructor import SleeveBtcConstructor
from scripts.run_paper_cloud_day import (_FailClosed, _record_family_tracker,
                                         _run_family_strategy)


def _closes(rising=True, n=260):
    idx = pd.date_range("2024-01-01", periods=n, freq="B")

    def s(a, b):
        return pd.Series(np.linspace(a, b, n) if rising else np.linspace(b, a, n), index=idx)
    return {"SPY": s(300, 500), "SSO": s(50, 90), "AGG": s(95, 99),
            "GLD": s(160, 180), "IBIT": s(40, 60)}, idx[-1].date() + dt.timedelta(days=1)


class _FakeData:
    def __init__(self, closes, equity=100000.0):
        self._c, self._eq = closes, equity

    def fetch_daily_closes(self, tickers, lookback_days=400):
        return {t: self._c[t] for t in tickers if t in self._c}

    def get_account(self):
        return {"equity": self._eq, "cash": self._eq}

    def fetch_latest_prices(self, tickers):
        return {t: float(self._c[t].iloc[-1]) for t in tickers if t in self._c}


def _om_cfg(tmp_path):
    return (OrderManager(FakePaperClient(), journal_path=str(tmp_path / "o.jsonl")),
            PaperConfig(allocator="mean_variance"))


class TestFamilyConstruction:
    def test_offense_constructs_and_stages_sso(self, tmp_path):
        closes, today = _closes(rising=True)
        om, cfg = _om_cfg(tmp_path)
        plan, latest, staged, arrival, arrival_ts, sizing, eq = _run_family_strategy(
            constructor=OffenseSSOConstructor(tif="day"),
            fetch_universe=("SPY", "SSO", "AGG", "GLD"),
            tracking_universe=("SPY", "SSO", "AGG", "GLD"),
            client=_FakeData(closes), om=om, cfg=cfg, today=today,
            broker_positions={}, cap=10000.0)
        assert plan.signals["SPY"] == 1.0 and plan.targets["SSO"] == 1.0
        assert sizing == 10000.0 and eq == 100000.0
        assert any(o.ticker == "SSO" and o.side == "buy" for o in staged)
        assert set(latest) == {"SPY", "SSO", "AGG", "GLD"}

    def test_sleeve_btc_constructs_all_four_legs(self, tmp_path):
        closes, today = _closes(rising=True)
        om, cfg = _om_cfg(tmp_path)
        plan, latest, staged, arrival, arrival_ts, sizing, eq = _run_family_strategy(
            constructor=SleeveBtcConstructor(tif="day"),
            fetch_universe=("SPY", "AGG", "GLD", "IBIT"),
            tracking_universe=("SPY", "AGG", "GLD", "IBIT"),
            client=_FakeData(closes), om=om, cfg=cfg, today=today,
            broker_positions={}, cap=10000.0)
        assert plan.targets["IBIT"] == pytest.approx(0.05, abs=1e-3)
        assert len(staged) == 4

    def test_fail_closed_on_stale_bar(self, tmp_path):
        closes, _ = _closes(rising=True)
        om, cfg = _om_cfg(tmp_path)
        far_future = dt.date(2030, 1, 1)                  # every bar is > 5 days stale
        with pytest.raises(_FailClosed) as e:
            _run_family_strategy(
                constructor=OffenseSSOConstructor(tif="day"),
                fetch_universe=("SPY", "SSO", "AGG", "GLD"),
                tracking_universe=("SPY", "SSO", "AGG", "GLD"),
                client=_FakeData(closes), om=om, cfg=cfg, today=far_future,
                broker_positions={}, cap=10000.0)
        assert e.value.code == 68

    def test_fail_closed_on_fetch_failure(self, tmp_path):
        om, cfg = _om_cfg(tmp_path)

        class _Boom(_FakeData):
            def fetch_daily_closes(self, *a, **k):
                raise RuntimeError("net down")
        with pytest.raises(_FailClosed) as e:
            _run_family_strategy(
                constructor=OffenseSSOConstructor(tif="day"),
                fetch_universe=("SPY", "SSO"), tracking_universe=("SPY", "SSO"),
                client=_Boom({}), om=om, cfg=cfg, today=dt.date(2024, 6, 1),
                broker_positions={}, cap=10000.0)
        assert e.value.code == 67


class TestFamilyTracker:
    def test_offense_tracker_records_exec_gates(self, tmp_path):
        closes, today = _closes(rising=True)
        om, cfg = _om_cfg(tmp_path)
        plan, latest, staged, arrival, arrival_ts, sizing, eq = _run_family_strategy(
            constructor=OffenseSSOConstructor(tif="day"),
            fetch_universe=("SPY", "SSO", "AGG", "GLD"),
            tracking_universe=("SPY", "SSO", "AGG", "GLD"),
            client=_FakeData(closes), om=om, cfg=cfg, today=today,
            broker_positions={}, cap=10000.0)
        summary = SimpleNamespace(trade_date=str(today), reconcile_total_cycles=3,
                                  reconcile_clean_cycles=3, halted=False)
        tsum = _record_family_tracker(
            tracker_path=str(tmp_path / "offense_tracking.json"),
            plan=plan, closes_latest=latest, equity=eq, sizing_equity=sizing,
            broker_positions={}, staged=staged, arrival_px={}, arrival_ts=arrival_ts,
            summary=summary,
            canonical=True, root=tmp_path,
            robo_closes={t: latest[t] for t in ("SPY", "AGG", "GLD")})
        eg = tsum.get("execution_gates", {})
        assert eg.get("gates", {}).get("c_order_errors", {}).get("status") == "pass"
