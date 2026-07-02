# tests/test_paper_day_orders_t238.py
"""T-238 Option A — the PAPER sleeve trades market DAY orders (Alpaca paper
FILLS DAY orders but EXPIRES OPG auction orders unfilled). Covers the new
`is_market_open` gate, the scheduler's `submit_day` path (submit when the
regular session is open; DEFER — and survive — when closed), and the
env-gated TIF flowing to the constructed orders.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from paper_trader import (FakePaperClient, OrderManager, OrderState,
                          PaperConfig, PaperScheduler, ReconcileInputs)
from paper_trader.market_calendar import MarketCalendar
from paper_trader.sleeve_constructor import SleeveOrderConstructor

ET = ZoneInfo("America/New_York")
CFG = "cfg-t238-day"


def _et(h, mi=0, day=18):
    return datetime(2026, 6, day, h, mi, tzinfo=ET)   # Jun 18 = a Thursday


def _armed(tmp_path, now):
    client = FakePaperClient()
    om = OrderManager(client, journal_path=str(tmp_path / "o.jsonl"))
    sched = PaperScheduler(
        om, reconcile_log_path=str(tmp_path / "r.jsonl"),
        dry_run=False, armed=True,
        paper_config=PaperConfig(allocator="mean_variance"),
        designated_allocator="mean_variance",
        calendar=MarketCalendar(), now_fn=lambda: now)
    return sched, om, client


def _inputs(_step):
    return ReconcileInputs({}, 5000.0, {}, 5000.0)


class TestIsMarketOpen:
    def test_open_during_regular_session(self):
        assert MarketCalendar().is_market_open(_et(9, 45)) is True
        assert MarketCalendar().is_market_open(_et(15, 59)) is True

    def test_closed_pre_open_and_post_close(self):
        assert MarketCalendar().is_market_open(_et(9, 0)) is False     # pre-open
        assert MarketCalendar().is_market_open(_et(16, 1)) is False    # post-close

    def test_closed_weekend_and_holiday(self):
        assert MarketCalendar().is_market_open(_et(11, 0, day=20)) is False   # Saturday
        assert MarketCalendar().is_market_open(                              # Jul 3 holiday
            datetime(2026, 7, 3, 11, 0, tzinfo=ET)) is False

    def test_day_routes_through_auction_window_open(self):
        cal = MarketCalendar()
        assert cal.auction_window_open("day", _et(9, 45)) is True
        assert cal.auction_window_open("day", _et(9, 0)) is False


class TestSubmitDay:
    def test_day_submitted_when_session_open(self, tmp_path):
        sched, om, client = _armed(tmp_path, _et(9, 45))
        o = om.stage("2026-06-18", "SPY", "buy", 1, "day", CFG)
        client.script_submit(o.client_order_id, status="accepted")
        summary = sched.run_day("2026-06-18", [o], _inputs)
        assert summary.submitted_count == 1
        assert o.state != OrderState.STAGED.value
        step = next(s for s in summary.steps if s.step == "submit_day")
        assert step.would_submit == 1 and "ARMED" in step.note

    def test_day_deferred_and_survives_when_session_closed(self, tmp_path):
        # pre-open: a DAY order can't fill → DEFER, stays STAGED for the
        # in-window run, and the EOD must NOT expire a never-submitted order.
        sched, om, client = _armed(tmp_path, _et(9, 0))
        o = om.stage("2026-06-18", "SPY", "buy", 1, "day", CFG)
        client.script_submit(o.client_order_id, status="accepted")
        summary = sched.run_day("2026-06-18", [o], _inputs)
        assert summary.submitted_count == 0
        assert o.state == OrderState.STAGED.value
        step = next(s for s in summary.steps if s.step == "submit_day")
        assert "DEFERRED" in step.note

    def test_submitted_day_not_expired_midsession(self, tmp_path):
        sched, om, client = _armed(tmp_path, _et(9, 45))
        o = om.stage("2026-06-18", "SPY", "buy", 1, "day", CFG)
        client.script_submit(o.client_order_id, status="accepted")
        sched.run_day("2026-06-18", [o], _inputs)
        assert o.state != OrderState.EXPIRED.value


class TestEnvTif:
    def test_constructor_tif_flows_to_orders(self):
        idx = pd.date_range("2020-01-01", periods=60, freq="B")
        up = pd.Series(np.linspace(100, 200, 60), index=idx)
        c = SleeveOrderConstructor(speeds=(5, 10, 20), tif="day")
        plan = c.construct(30000.0, {}, {"SPY": up, "AGG": up, "GLD": up})
        assert plan.orders and all(o.tif == "day" for o in plan.orders)
