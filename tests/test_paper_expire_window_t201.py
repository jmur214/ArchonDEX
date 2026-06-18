# tests/test_paper_expire_window_t201.py
"""T-201 — the EOD expire must NOT cancel an order whose auction window is
still OPEN (the bug that canceled the first real OPG at 01:14 ET, in the
OPG window, before its 09:30 auction). Expire only once the window has
closed and the order can no longer fill.
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from paper_trader import (
    FakePaperClient,
    OrderManager,
    OrderState,
    PaperConfig,
    PaperScheduler,
    ReconcileInputs,
    TimeInForce,
)
from paper_trader.market_calendar import MarketCalendar

ET = ZoneInfo("America/New_York")
CFG = "cfg-t201"


def _et(h, mi=0):
    return datetime(2026, 6, 18, h, mi, tzinfo=ET)   # a Thursday (trading day)


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


def _pending(om, client, tif):
    o = om.stage("2026-06-18", "SPY", "buy", 1, tif, CFG)
    client.script_submit(o.client_order_id, status="accepted")
    return om.submit(o)          # -> ACKED, open at the broker


def _inputs(_step):
    return ReconcileInputs({}, 5000.0, {}, 5000.0)


class TestAuctionWindowExpiry:
    def test_opg_NOT_expired_while_window_open(self, tmp_path):
        # 01:14 ET — inside the OPG window (7pm-9:28am); the open is UPCOMING.
        sched, om, client = _armed(tmp_path, _et(1, 14))
        o = _pending(om, client, TimeInForce.OPG)
        sched.run_day("2026-06-18", [], _inputs)
        assert o.state == OrderState.ACKED.value         # left to fill
        assert o.broker_order_id not in client.canceled  # NOT canceled

    def test_opg_expired_after_window_closed(self, tmp_path):
        # 13:00 ET — past the 9:28 cutoff + the open; an unfilled OPG is stale.
        sched, om, client = _armed(tmp_path, _et(13, 0))
        o = _pending(om, client, TimeInForce.OPG)
        sched.run_day("2026-06-18", [], _inputs)
        assert o.state == OrderState.EXPIRED.value
        assert o.broker_order_id in client.canceled

    def test_cls_NOT_expired_while_window_open(self, tmp_path):
        # 09:00 ET — before the 15:50 MOC cutoff; the close is UPCOMING.
        sched, om, client = _armed(tmp_path, _et(9, 0))
        o = _pending(om, client, TimeInForce.CLS)
        sched.run_day("2026-06-18", [], _inputs)
        assert o.state == OrderState.ACKED.value
        assert o.broker_order_id not in client.canceled

    def test_cls_expired_after_close(self, tmp_path):
        # 16:30 ET — past the close; an unfilled CLS is stale.
        sched, om, client = _armed(tmp_path, _et(16, 30))
        o = _pending(om, client, TimeInForce.CLS)
        sched.run_day("2026-06-18", [], _inputs)
        assert o.state == OrderState.EXPIRED.value
        assert o.broker_order_id in client.canceled
