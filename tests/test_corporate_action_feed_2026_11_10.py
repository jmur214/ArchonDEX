# tests/test_corporate_action_feed_2026_11_10.py
"""The corporate-action (split) feed, the ledger event, the order gate and the
live-book treatment — locked against the event that produced them.

2026-11-05, account 2: MTUM split 4-for-1. The vendor's split-ADJUSTED price
series read ~1/4 of the day before while the ledger and the paper broker still
showed 5 pre-split shares. The run bought 18 MTUM it did not need; the virtual
momentum book printed −76% with ``degraded: False``. The designed feed
(``ReconcileInputs.corporate_action_tickers``) had never been fed.

Fixtures under tests/fixtures/corporate_actions/ are cut from the real state:
  * alpaca_corporate_actions_2026_11_05.json — the REAL data-API response
    (captured 2026-11-10 with one read-only call);
  * acct2_orders_thru_2026_11_03.jsonl / acct2_ledger_2026_11_04.jsonl — account
    2's real journal and ledger as the 2026-11-05 run found them;
  * book_momentum_satellite_real_2026_11_10.json — the real book file;
  * momentum_closes_derived_from_recorded_navs.json — DERIVED, not fetched: the
    closes implied by that file's own recorded navs (see the repair test).

The driver tests EXECUTE ``main()``; nothing here reads production code as text.
"""
from __future__ import annotations

import datetime as dt
import json
import shutil
import types
from pathlib import Path

import pandas as pd
import pytest

import scripts.repair_live_book_split_2026_11_05 as repair
import scripts.run_paper_cloud_day as drv
from paper_trader.corporate_actions import (
    MARKS_REL, CorporateActionGate, SplitEvent, SplitFeedResult, fetch_splits,
    parse_alpaca_corporate_actions, price_split_ratio, split_adjusted_journal_net)
from paper_trader.ledger_store import LedgerStore
from paper_trader.live_books import MOMENTUM_SAT, LiveBook
from paper_trader.order_manager import OrderRecord
from paper_trader.paper_client import FakePaperClient
from paper_trader.reconciliation import (CLASS_CORPORATE_ACTION,
                                         CLASS_POSITION_DRIFT)

FIX = Path(__file__).parent / "fixtures" / "corporate_actions"
REAL_FEED = json.loads((FIX / "alpaca_corporate_actions_2026_11_05.json").read_text())["response"]
EX = dt.date(2026, 11, 5)
MTUM_4_1 = SplitEvent("MTUM", EX, 4.0)
# the mark account 2 saw on 11-04 (pre-split basis) and the same bar as the
# vendor served it on 11-05 (adjusted): 276.56 / 4.
PRE_PX, POST_PX = 276.56, 69.14
# deploy_candidate at the $10,583 contributed cap: target int(10583 × 0.15 /
# 69.14) = 22 MTUM. Against the split-adjusted 20 that is a 2-share top-up;
# against the broker's stale 5 it is the spurious buy (18 in the real run, at
# the real close; 17 at this fixture's).
HONEST_TOPUP, SPURIOUS_BUY = 2, 17


def _feed_ok(*events: SplitEvent) -> SplitFeedResult:
    return SplitFeedResult.ok(events, tickers=["MTUM"], start=EX, end=EX)


def _raises(*_a, **_k):
    raise ConnectionError("data API unreachable")


# =========================================================================== #
# 1. the feed: OK-and-empty is a different fact from UNAVAILABLE
# =========================================================================== #
def test_real_alpaca_response_parses_to_the_two_4_for_1_splits():
    events, unhandled = parse_alpaca_corporate_actions(REAL_FEED)
    assert sorted(e.to_dict()["ticker"] for e in events) == ["MTUM", "QUAL"]
    assert all(e.ex_date == EX and e.ratio == 4.0 for e in events)
    # SGOV's cash dividend is in the same real payload and is NOT a share action
    assert "cash_dividends" in REAL_FEED and unhandled == []


def test_a_failed_ask_is_UNAVAILABLE_with_a_reason_never_an_empty_ok():
    since, today = dt.date(2026, 11, 4), EX
    dead = fetch_splits(_raises, ["MTUM"], since, today)
    assert dead.available is False and "ConnectionError" in dead.reason
    assert fetch_splits(None, ["MTUM"], since, today).available is False
    assert fetch_splits(lambda *a: ["not", "a", "mapping"], ["MTUM"], since,
                        today).available is False
    assert fetch_splits(lambda *a: {"forward_splits": [{"symbol": "MTUM"}]},
                        ["MTUM"], since, today).available is False
    quiet = fetch_splits(lambda *a: {}, ["MTUM"], since, today)
    assert quiet.available is True and quiet.events == ()
    live = fetch_splits(lambda *a: REAL_FEED, ["MTUM", "VOO", "SGOV"], since, today)
    assert live.available and [e.key for e in live.events] == ["MTUM:2026-11-05"]


def test_the_result_type_refuses_to_blur_the_two():
    with pytest.raises(ValueError):
        SplitFeedResult(False, (MTUM_4_1,), (), "boom")
    with pytest.raises(ValueError):
        SplitFeedResult(False)                       # unavailable without a reason


def test_an_unmodelled_share_action_is_surfaced_not_dropped():
    events, unhandled = parse_alpaca_corporate_actions(
        {"stock_dividends": [{"symbol": "MTUM", "rate": 0.05, "ex_date": "2026-11-05"}]})
    assert events == [] and [(u.ticker, u.kind) for u in unhandled] == [
        ("MTUM", "stock_dividends")]


# =========================================================================== #
# 2. the price-basis guard
# =========================================================================== #
def test_price_ratio_flags_splits_and_not_an_ordinary_bad_day():
    assert price_split_ratio(PRE_PX, POST_PX) == 4.0
    assert price_split_ratio(PRE_PX, 65.59) == 4.0          # split AND a −5% session
    assert price_split_ratio(10.0, 100.0) == pytest.approx(0.1)   # 1-for-10 reverse
    assert price_split_ratio(100.0, 50.0) == 2.0
    assert price_split_ratio(100.0, 92.0) is None           # POSITIVE CONTROL: −8%
    assert price_split_ratio(100.0, 108.0) is None
    assert price_split_ratio(None, 50.0) is None and price_split_ratio(0.0, 5.0) is None


# =========================================================================== #
# 3. the ledger event: explicit, journaled, exactly once
# =========================================================================== #
def _ledger(tmp_path) -> LedgerStore:
    led = LedgerStore(str(tmp_path / "ledger.jsonl"), starting_cash=1000.0)
    led.adopt_broker_truth({"MTUM": 5, "VOO": 12}, cash=1000.0, reason="cloud cycle 2026-11-04")
    led.state.positions["MTUM"]["avg_price"] = 240.0
    return led


def test_ledger_split_is_an_explicit_journaled_event(tmp_path):
    led = _ledger(tmp_path)
    assert led.apply_split("MTUM", 4.0, EX) is True
    pos = led.position("MTUM")
    assert (pos.qty, pos.avg_price) == (20, 60.0)
    assert led.cash() == 1000.0 and led.positions()["VOO"] == 12
    last = led.store.read_all()[-1]
    assert last["event"] == "split:MTUM:2026-11-05:ratio=4"
    assert last["positions"]["MTUM"]["qty"] == 20


def test_ledger_split_is_idempotent_across_reruns_and_cloud_cycles(tmp_path):
    led = _ledger(tmp_path)
    assert led.apply_split("MTUM", 4.0, EX) is True
    assert led.apply_split("MTUM", 4.0, EX) is False            # same process
    # tomorrow's container: a NEW store resumed from the durable file
    resumed = LedgerStore(str(tmp_path / "ledger.jsonl"))
    assert resumed.apply_split("MTUM", 4.0, EX) is False
    assert resumed.positions()["MTUM"] == 20
    assert [s.key for s in resumed.applied_splits()] == ["MTUM:2026-11-05"]
    assert sum(1 for r in resumed.store.read_all()
               if r["event"].startswith("split:")) == 1


def test_ledger_reverse_split_and_the_fraction_it_refuses(tmp_path):
    led = LedgerStore(str(tmp_path / "ledger.jsonl"), starting_cash=0.0)
    led.adopt_broker_truth({"XYZ": 20, "ODD": 5}, reason="cloud cycle 2026-11-04")
    assert led.apply_split("XYZ", 0.1, EX) is True               # 1-for-10
    assert led.positions()["XYZ"] == 2
    with pytest.raises(ValueError, match="whole shares"):
        led.apply_split("ODD", 0.1, EX)                          # 0.5 share: cash-in-lieu
    assert led.positions()["ODD"] == 5


def test_journal_net_scales_pre_split_fills_only():
    def fill(day: str, side: str, qty: int) -> OrderRecord:
        return OrderRecord(client_order_id=f"c-{day}-{side}-{qty}", trade_date=day,
                           ticker="MTUM", side=side, qty=qty, tif="day", state="filled",
                           filled_qty=qty, filled_at=f"{day}T14:51:00+00:00")
    assert split_adjusted_journal_net([fill("2026-09-15", "buy", 5)], [MTUM_4_1]) == {"MTUM": 20}
    # a fill ON the ex-date is already in the new basis
    assert split_adjusted_journal_net(
        [fill("2026-09-15", "buy", 5), fill("2026-11-05", "buy", 18)], [MTUM_4_1]) == {"MTUM": 38}


def test_a_mixed_basis_position_is_never_auto_scaled(tmp_path):
    """The state account 2 is ACTUALLY in today: 5 pre-split + the spurious 18
    bought on the ex-date = ledger 23, broker 92. 23 × 4 = 92 looks like an
    explanation and is not one — 18 of those shares were never pre-split."""
    led = LedgerStore(str(tmp_path / "ledger.jsonl"), starting_cash=0.0)
    led.adopt_broker_truth({"MTUM": 23}, reason="cloud cycle 2026-11-05 reconcile")
    orders = [OrderRecord("a", "2026-09-15", "MTUM", "buy", 5, "day", "filled",
                          filled_qty=5, filled_at="2026-09-15T13:52:00+00:00"),
              OrderRecord("b", "2026-11-05", "MTUM", "buy", 18, "day", "filled",
                          filled_qty=18, filled_at="2026-11-05T14:51:33+00:00")]
    gate = CorporateActionGate(today=dt.date(2026, 11, 10), feed=_feed_ok(MTUM_4_1))
    gate.apply_to_ledger(led, orders)
    assert led.positions()["MTUM"] == 23 and gate.applied == []
    assert "mix pre- and post-split" in gate.frozen["MTUM"] and gate.stand_down
    gate.assess_broker(led.positions(), {"MTUM": 92})
    assert gate.reconcile_tickers == {"MTUM"}        # classified by the feed, still manual


# =========================================================================== #
# 4. the driver, replaying account 2 on 2026-11-05
# =========================================================================== #
class _Cloud:
    def __init__(self) -> None:
        self.metrics: list = []
        self.cfg = types.SimpleNamespace(enabled=False, s3_root="LOCAL", prefix="x")

    def pull(self) -> bool:
        return False

    def push(self) -> bool:
        return True

    def emit_metrics(self, *, happened: bool, canonical: bool) -> None:
        self.metrics.append((happened, canonical))

    def pull_readonly_from(self, source_prefix, rels) -> None:
        return None


def _replay(tmp_path, *, broker_mtum: int, feed, mtum_px: float = POST_PX,
            mark: float = PRE_PX, today: dt.date = EX):
    """Account 2 as the 2026-11-05 run found it: the REAL journal and ledger
    (12 VOO / 5 MTUM / 9 SGOV), yesterday's MTUM mark, today's close, and a
    broker showing ``broker_mtum`` shares."""
    state = tmp_path / "data/paper_state"
    state.mkdir(parents=True)
    shutil.copy(FIX / "acct2_orders_thru_2026_11_03.jsonl", state / "orders.jsonl")
    shutil.copy(FIX / "acct2_ledger_2026_11_04.jsonl", state / "ledger.jsonl")
    (tmp_path / "config").mkdir()
    for f in ("deploy_candidate.json", "substantially_identical.json"):
        shutil.copy(Path("config") / f, tmp_path / "config" / f)
    (tmp_path / "config/llm_settings.json").write_text(json.dumps(
        {"llm": {"kill_switch": False, "trading_kill_switch": False,
                 "monthly_budget_usd": 30.0, "max_output_tokens": 1500}}))
    px = {"VOO": 692.0, "MTUM": mtum_px, "SGOV": 100.45,
          "SPY": 754.35, "AGG": 95.94, "GLD": 359.26}
    marks = {t: {"px": v, "run_date": "2026-11-04"} for t, v in px.items()}
    marks["MTUM"]["px"] = mark
    mp = tmp_path / MARKS_REL
    mp.parent.mkdir(parents=True, exist_ok=True)
    mp.write_text(json.dumps({"_schema": "price_basis_marks/v1", "marks": marks}))
    idx = pd.bdate_range(end=pd.Timestamp(today) - pd.Timedelta(days=1), periods=80)
    series = {t: pd.Series([v] * len(idx), index=idx) for t, v in px.items()}
    positions = {"VOO": 12, "MTUM": broker_mtum, "SGOV": 9}

    acct = {"cash": 89_598.74}
    now = dt.datetime(today.year, today.month, today.day, 14, 51, tzinfo=dt.timezone.utc)

    class _C(FakePaperClient):
        """A paper broker that FILLS a market DAY order at the quoted price, so
        a staged order runs the whole submit → fill → adopt → reconcile path."""
        def __init__(self) -> None:
            super().__init__()
            self.filled: dict = {}

        def get_clock(self):
            return types.SimpleNamespace(is_open=True)     # the regular session

        def get_account(self):
            return {"equity": 100_346.57, "cash": acct["cash"], "status": "ACTIVE"}

        def list_positions(self):
            return [{"symbol": s, "qty": q} for s, q in positions.items() if q]

        def submit_order(self, client_order_id, symbol, qty, side, tif):
            super().submit_order(client_order_id, symbol, qty, side, tif)
            sign = 1 if side == "buy" else -1
            positions[symbol] = positions.get(symbol, 0) + sign * qty
            acct["cash"] = round(acct["cash"] - sign * qty * px[symbol], 2)
            self.filled[client_order_id] = {
                "broker_order_id": f"bkr-{client_order_id[-8:]}",
                "client_order_id": client_order_id, "status": "filled",
                "symbol": symbol, "qty": qty, "filled_qty": qty,
                "filled_avg_price": px[symbol], "filled_at": now.isoformat(),
                "side": side, "tif": tif}
            return dict(self.filled[client_order_id])

        def get_order(self, client_order_id):
            if client_order_id in self.filled:
                return dict(self.filled[client_order_id])
            return super().get_order(client_order_id)

        def fetch_daily_closes(self, tickers, lookback_days=400):
            return {t: series[t] for t in tickers if t in series}

        def fetch_latest_prices(self, tickers):
            return {t: px[t] for t in tickers if t in px}

        def trading_days(self, start, end):
            return {today}

    client, cloud = _C(), _Cloud()
    rc = drv.main(["--allocator", "mean_variance", "--strategy", "deploy_candidate",
                   "--sleeve-notional-cap", "10000"],
                  now=now, client=client, cloud=cloud, root=str(tmp_path), ca_fetch=feed)
    hb = json.loads((tmp_path / "data/state/paper_heartbeat.json").read_text())
    led = LedgerStore(str(state / "ledger.jsonl"))
    recon = [json.loads(l) for l in (state / "recon.jsonl").read_text().splitlines()]
    journal = [json.loads(l) for l in (state / "orders.jsonl").read_text().splitlines()]
    new_orders = [o for o in journal if o["trade_date"] == str(today)]
    return types.SimpleNamespace(rc=rc, client=client, cloud=cloud, hb=hb, led=led,
                                 recon=recon, new_orders=new_orders,
                                 block=hb.get("corporate_actions", {}))


def _mtum(orders) -> list:
    return [o for o in orders if o.get("ticker") == "MTUM" or o.get("symbol") == "MTUM"]


def test_replay_split_confirmed_and_broker_has_applied_it(tmp_path):
    """Feed = 4-for-1, broker shows 20. The SPURIOUS order is not constructed;
    the ledger becomes 20 through the journaled event; reconcile is CLEAN.

    What IS constructed is the honest one. The bands are in SHARE QUANTA, and
    the split made MTUM's quantum 4× smaller, so the same 13% weight that was
    inside the buy band at $276 is outside it at $69: target int(10583 × 0.15 /
    69.14) = 22, held 20 → BUY 2. On 2026-11-05 the run sized against 5 and
    bought 18; sized against 20 it buys TARGET_QTY − 20."""
    r = _replay(tmp_path, broker_mtum=20, feed=lambda *a: REAL_FEED)
    sub = _mtum(r.client.submitted)
    assert [(o["side"], o["qty"]) for o in sub] == [("buy", HONEST_TOPUP)], sub
    assert HONEST_TOPUP == 2 and SPURIOUS_BUY == 17
    assert r.block["refused_orders"] == [] and r.block["frozen"] == {}
    assert r.led.positions()["MTUM"] == 20 + HONEST_TOPUP
    events = [x["event"] for x in r.led.store.read_all()]
    assert events.count("split:MTUM:2026-11-05:ratio=4") == 1
    assert events.index("split:MTUM:2026-11-05:ratio=4") < events.index(
        "adopt_broker:cloud cycle 2026-11-05"), "journaled BEFORE the ledger converges"
    split_line = [x for x in r.led.store.read_all() if x["event"].startswith("split:")][0]
    assert split_line["positions"]["MTUM"]["qty"] == 20, "5 → 20, by the event itself"
    assert r.block["applied_this_run"] == ["MTUM:2026-11-05"]
    assert r.recon and all(c["clean"] for c in r.recon), r.recon
    assert r.recon[0]["step"] == "preflight", "…and clean vs broker 20 BEFORE any order"
    assert r.hb["last_run"]["canonical"] is True and r.rc == 0
    assert r.cloud.metrics[-1] == (True, True)


def test_replay_split_confirmed_but_broker_still_pre_split_is_FROZEN(tmp_path):
    """THE STATE THAT OCCURRED: feed says split, the price is post-split, the
    broker still shows 5. Nothing may be ordered in MTUM — and (the documented
    decision) nothing is staged at all; the run is non-canonical, by name."""
    r = _replay(tmp_path, broker_mtum=5, feed=lambda *a: REAL_FEED)
    assert r.new_orders == [] and r.client.submitted == []
    refused = _mtum(r.block["refused_orders"])
    assert [(o["side"], o["qty"]) for o in refused] == [("buy", HONEST_TOPUP)], \
        "sized on the split-adjusted 20, the plan holds the honest top-up, not the 17"
    assert r.led.positions()["MTUM"] == 20, "the ledger keeps the split; it is not re-adopted to 5"
    assert "broker has not applied it yet" in r.block["frozen"]["MTUM"]
    assert r.block["stand_down"] is True and r.block["reconcile_tickers"] == ["MTUM"]
    klasses = {f["klass"] for c in r.recon for f in c["findings"] if f["ticker"] == "MTUM"}
    assert klasses == {CLASS_CORPORATE_ACTION}, klasses    # the T-163 path, fed at last
    assert not any(c["halt"] for c in r.recon)
    assert r.rc == 70 and r.cloud.metrics[-1] == (True, False)


def test_replay_feed_UNAVAILABLE_the_price_guard_refuses_the_MTUM_buy(tmp_path):
    """The guard that would have stopped the 18-share buy with a dead feed:
    yesterday's mark 276.56, today's 69.14, nobody to confirm a split."""
    r = _replay(tmp_path, broker_mtum=5, feed=_raises)
    assert r.block["feed"]["available"] is False
    refused = _mtum(r.block["refused_orders"])
    assert [(o["side"], o["qty"]) for o in refused] == [("buy", SPURIOUS_BUY)], \
        "the spurious MTUM buy WAS constructed — and must be recorded as refused"
    assert r.new_orders == [] and r.client.submitted == []
    assert "UNCONFIRMED" in r.block["frozen"]["MTUM"] and "UNAVAILABLE" in r.block["frozen"]["MTUM"]
    assert r.led.positions()["MTUM"] == 5, "no split is applied on a price hunch"
    assert r.rc == 70 and r.cloud.metrics[-1] == (True, False)
    marks = json.loads((tmp_path / MARKS_REL).read_text())["marks"]
    assert marks["MTUM"]["px"] == PRE_PX, "a frozen ticker's mark must not advance"


def test_replay_feed_answers_NO_split_the_price_guard_still_refuses(tmp_path):
    r = _replay(tmp_path, broker_mtum=5, feed=lambda *a: {})
    assert r.block["feed"]["available"] is True and r.block["feed"]["events"] == []
    assert _mtum(r.block["refused_orders"]) and r.client.submitted == [] and r.rc == 70
    assert "reports NO split" in r.block["frozen"]["MTUM"]


def test_POSITIVE_CONTROL_an_ordinary_minus_8pct_day_trades_normally(tmp_path):
    """Not a clean ratio → not a split → the book trades. MTUM −8% (276.56 →
    254.44) with 5 shares held; the constructor's own orders are staged and
    submitted, with the feed alive OR dead."""
    for sub, feed in (("ok", lambda *a: {}), ("dead", _raises)):
        r = _replay(tmp_path / sub, broker_mtum=5, feed=feed, mtum_px=254.44)
        assert r.block["frozen"] == {} and r.block["stand_down"] is False
        assert r.block["refused_orders"] == []
        assert r.client.submitted, "the positive control must actually trade"
        assert {o["symbol"] for o in r.client.submitted} == {o["ticker"] for o in r.new_orders}
        assert r.led.positions()["MTUM"] == 5 and r.rc == 0, (sub, r.hb["last_run"])
        marks = json.loads((tmp_path / sub / MARKS_REL).read_text())["marks"]
        assert marks["MTUM"] == {"px": 254.44, "run_date": "2026-11-05"}


def test_blind_no_mark_and_no_feed_freezes_a_held_ticker(tmp_path):
    gate = CorporateActionGate(today=EX, feed=fetch_splits(_raises, ["MTUM"], EX, EX + dt.timedelta(1)),
                               marks_path=tmp_path / "marks.json")
    gate.check_prices({"MTUM": POST_PX, "SPY": 754.0}, held=["MTUM"])
    assert "UNVERIFIABLE" in gate.frozen["MTUM"] and "SPY" not in gate.frozen
    # with a feed that ANSWERED, a first-ever mark is simply recorded
    ok = CorporateActionGate(today=EX, feed=_feed_ok(), marks_path=tmp_path / "m2.json")
    ok.check_prices({"MTUM": POST_PX}, held=["MTUM"])
    assert ok.frozen == {}


# =========================================================================== #
# 5. live books: shares must follow the price basis
# =========================================================================== #
def _momentum_through_11_04(tmp_path, *, with_marks: bool = True) -> LiveBook:
    """The REAL momentum_satellite record through 2026-11-04. The file keeps only
    its latest side, so the 11-04 side is the one the repair script DERIVES and
    proves (333 MTUM + $168.2775; 131 SPY + $487.9554)."""
    real = json.loads((FIX / "book_momentum_satellite_real_2026_11_10.json").read_text())
    st = {"_schema": "live_book/v1", "book": "momentum_satellite",
          "side": {"book": {"shares": {"MTUM": 333.0}, "cash": 168.2775, "nav": 92262.7575},
                   "twin": {"shares": {"SPY": 131.0}, "cash": 487.9554, "nav": 101025.2154}},
          "days": [d for d in real["days"] if d["date"] <= "2026-11-04"]}
    if with_marks:
        st["last_px"] = {"MTUM": 276.56, "SPY": 767.46}
    lb = LiveBook(MOMENTUM_SAT, root=str(tmp_path))
    lb._write(st)
    return lb


CLOSE_11_05 = {"MTUM": 65.59, "SPY": 756.61}


def test_live_book_with_the_feed_is_continuous_across_the_split(tmp_path):
    lb = _momentum_through_11_04(tmp_path)
    feed = fetch_splits(lambda *a: REAL_FEED, ["MTUM", "SPY"], dt.date(2026, 10, 6), EX)
    lb.record("2026-11-05", CLOSE_11_05, splits=feed)
    st = lb._state()
    day = st["days"][-1]
    assert day["degraded"] is False and day["splits_applied"] == [MTUM_4_1.to_dict()]
    prev = st["days"][-2]["book_growth"]
    assert prev == 0.922628
    assert day["book_growth"] == pytest.approx(0.875341, abs=1e-6)      # NOT 0.220097
    assert day["book_growth"] / prev - 1 > -0.06, "MTUM's own day, not a −76% artifact"
    assert st["side"]["book"]["shares"]["MTUM"] >= 1332.0
    assert st["side"]["twin"]["shares"] == {"SPY": 131.0}
    assert st["splits_applied"] == ["MTUM:2026-11-05"]
    # exactly once: the next session, same feed window, does not scale again
    lb.record("2026-11-06", {"MTUM": 64.75, "SPY": 739.87}, splits=feed)
    st2 = lb._state()
    assert st2["days"][-1]["book_growth"] == pytest.approx(0.864136, abs=1e-6)
    assert "splits_applied" not in st2["days"][-1]


@pytest.mark.parametrize("feed", [None,
                                  SplitFeedResult.unavailable("fetch raised ConnectionError"),
                                  SplitFeedResult.ok()],
                         ids=["none-supplied", "unavailable", "answered-no-split"])
def test_live_book_without_confirmation_PARKS_instead_of_marking_minus_76(tmp_path, feed):
    lb = _momentum_through_11_04(tmp_path)
    lb.record("2026-11-05", CLOSE_11_05, splits=feed)
    st = lb._state()
    day = st["days"][-1]
    assert day["degraded"] is True and "split-shaped" in day["reason"]
    assert "book_growth" not in day and day["book_nav"] == 92262.7575
    assert st["side"]["book"]["shares"] == {"MTUM": 333.0}, "a parked book holds, untouched"
    assert st["last_px"]["MTUM"] == 276.56
    # …and is RELEASED, continuous, the day the feed confirms
    lb.record("2026-11-06", {"MTUM": 64.75, "SPY": 739.87},
              splits=fetch_splits(lambda *a: REAL_FEED, ["MTUM"], dt.date(2026, 10, 7),
                                  dt.date(2026, 11, 6)))
    rel = lb._state()["days"][-1]
    assert rel["degraded"] is False and rel["book_growth"] > 0.85


def test_live_book_legacy_state_without_marks(tmp_path):
    """The live files have no ``last_px`` yet. With a feed that answers, the day
    is marked and the mark is laid down; with none, the book parks (blind)."""
    a = _momentum_through_11_04(tmp_path / "a", with_marks=False)
    a.record("2026-11-05", {"MTUM": 276.0, "SPY": 756.61}, splits=SplitFeedResult.ok())
    assert a._state()["days"][-1]["degraded"] is False
    assert a._state()["last_px"]["MTUM"] == 276.0
    b = _momentum_through_11_04(tmp_path / "b", with_marks=False)
    b.record("2026-11-05", {"MTUM": 276.0, "SPY": 756.61}, splits=None)
    assert b._state()["days"][-1]["degraded"] is True
    assert "no prior mark" in b._state()["days"][-1]["reason"]


def test_live_book_ordinary_day_is_untouched_by_the_guard(tmp_path):
    lb = _momentum_through_11_04(tmp_path)
    lb.record("2026-11-05", {"MTUM": 254.44, "SPY": 756.61}, splits=None)   # −8%, no feed
    day = lb._state()["days"][-1]
    assert day["degraded"] is False and day["book_growth"] == pytest.approx(0.848963, abs=1e-4)


# =========================================================================== #
# 6. the repair script (pure function + CLI guards; scratch paths only)
# =========================================================================== #
REAL_BOOK = FIX / "book_momentum_satellite_real_2026_11_10.json"
CLOSES = FIX / "momentum_closes_derived_from_recorded_navs.json"


def test_repair_restates_the_real_momentum_record(tmp_path, capsys):
    out = tmp_path / "restated.json"
    before = REAL_BOOK.read_bytes()
    rc = repair.main(["--state", str(REAL_BOOK), "--book", "momentum_satellite",
                      "--split", "MTUM:2026-11-05:4", "--closes", str(CLOSES),
                      "--out", str(out)])
    assert rc == 0 and REAL_BOOK.read_bytes() == before, "the input is never modified"
    new, old = json.loads(out.read_text()), json.loads(before)
    by = {d["date"]: d for d in new["days"]}
    assert [d for d in new["days"] if d["date"] < "2026-11-05"] == \
           [d for d in old["days"] if d["date"] < "2026-11-05"]
    assert by["2026-11-05"]["book_growth"] == pytest.approx(0.875341, abs=1e-6)
    assert by["2026-11-05"]["recorded"]["book_growth"] == 0.220097
    assert all(by[d]["restated"] is True for d in by if d >= "2026-11-05")
    assert by["2026-11-10"]["twin_growth"] == 0.98527             # the twin never split
    assert new["side"]["book"]["shares"]["MTUM"] > 1300
    assert new["restatement"]["pre_split_state"]["book"]["shares"] == {"MTUM": 333.0}
    table = capsys.readouterr().out
    assert "0.220097" in table and "0.875341" in table


def test_repair_REFUSES_closes_that_do_not_reproduce_the_record(tmp_path):
    bad = json.loads(CLOSES.read_text())
    bad["2026-11-06"]["MTUM"] = 66.00                             # not what the run saw
    with pytest.raises(repair.RepairRefused, match="verification FAILED on 2026-11-06"):
        repair.restate(json.loads(REAL_BOOK.read_text()), MOMENTUM_SAT, [MTUM_4_1], bad)


def test_repair_never_in_place_never_over_an_existing_file_never_live_state(tmp_path):
    copy = tmp_path / "copy.json"
    shutil.copy(REAL_BOOK, copy)
    base = ["--book", "momentum_satellite", "--split", "MTUM:2026-11-05:4",
            "--closes", str(CLOSES)]
    assert repair.main(["--state", str(copy), "--out", str(copy)] + base) == 2
    exists = tmp_path / "exists.json"
    exists.write_text("{}")
    assert repair.main(["--state", str(copy), "--out", str(exists)] + base) == 2
    assert exists.read_text() == "{}"
    live = repair.REPO_DATA / "state" / "book_momentum_satellite.restated.json"
    assert repair.main(["--state", str(copy), "--out", str(live)] + base) == 2
    assert not live.exists()
    assert repair.main(["--state", "s3://bucket/x.json", "--out", str(tmp_path / "o.json")]
                       + base) == 2
    assert copy.read_bytes() == REAL_BOOK.read_bytes()
