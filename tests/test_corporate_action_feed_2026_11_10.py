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


_NO_MARKS = object()


class _World:
    """Account 2 as the 2026-11-05 run found it — the REAL journal and ledger
    (12 VOO / 5 MTUM / 9 SGOV) — with a broker and a state root that PERSIST
    across run days, so a freeze can be followed from one session to the next."""

    def __init__(self, root: Path, *, broker_mtum: int, mtum_px: float = POST_PX,
                 mark=PRE_PX) -> None:
        self.root = Path(root)
        state = self.root / "data/paper_state"
        state.mkdir(parents=True)
        shutil.copy(FIX / "acct2_orders_thru_2026_11_03.jsonl", state / "orders.jsonl")
        shutil.copy(FIX / "acct2_ledger_2026_11_04.jsonl", state / "ledger.jsonl")
        (self.root / "config").mkdir()
        for f in ("deploy_candidate.json", "substantially_identical.json"):
            shutil.copy(Path("config") / f, self.root / "config" / f)
        (self.root / "config/llm_settings.json").write_text(json.dumps(
            {"llm": {"kill_switch": False, "trading_kill_switch": False,
                     "monthly_budget_usd": 30.0, "max_output_tokens": 1500}}))
        self.px = {"VOO": 692.0, "MTUM": mtum_px, "SGOV": 100.45,
                   "SPY": 754.35, "AGG": 95.94, "GLD": 359.26}
        self.positions = {"VOO": 12, "MTUM": broker_mtum, "SGOV": 9}
        self.cash = 89_598.74
        self.marks_path = self.root / MARKS_REL
        if mark is not _NO_MARKS:
            marks = {t: {"px": v, "run_date": "2026-11-04"} for t, v in self.px.items()}
            marks["MTUM"]["px"] = mark
            self.marks_path.parent.mkdir(parents=True, exist_ok=True)
            self.marks_path.write_text(json.dumps({"marks": marks}))

    def marks_file(self) -> dict:
        return json.loads(self.marks_path.read_text())

    def run(self, today: dt.date, feed):
        w, px = self, dict(self.px)
        idx = pd.bdate_range(end=pd.Timestamp(today) - pd.Timedelta(days=1), periods=80)
        series = {t: pd.Series([v] * len(idx), index=idx) for t, v in px.items()}
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
                return {"equity": 100_346.57, "cash": w.cash, "status": "ACTIVE"}

            def list_positions(self):
                return [{"symbol": s, "qty": q} for s, q in w.positions.items() if q]

            def submit_order(self, client_order_id, symbol, qty, side, tif):
                super().submit_order(client_order_id, symbol, qty, side, tif)
                sign = 1 if side == "buy" else -1
                w.positions[symbol] = w.positions.get(symbol, 0) + sign * qty
                w.cash = round(w.cash - sign * qty * px[symbol], 2)
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
        state = self.root / "data/paper_state"
        rc = drv.main(["--allocator", "mean_variance", "--strategy", "deploy_candidate",
                       "--sleeve-notional-cap", "10000"],
                      now=now, client=client, cloud=cloud, root=str(self.root), ca_fetch=feed)
        hb = json.loads((self.root / "data/state/paper_heartbeat.json").read_text())
        led = LedgerStore(str(state / "ledger.jsonl"))
        recon = [r for r in (json.loads(l) for l in
                             (state / "recon.jsonl").read_text().splitlines())
                 if r["trade_date"] == str(today)]
        journal = [json.loads(l) for l in (state / "orders.jsonl").read_text().splitlines()]
        new_orders = [o for o in journal if o["trade_date"] == str(today)]
        return types.SimpleNamespace(rc=rc, client=client, cloud=cloud, hb=hb, led=led,
                                     recon=recon, new_orders=new_orders,
                                     block=hb.get("corporate_actions", {}))


def _replay(tmp_path, *, broker_mtum: int, feed, mtum_px: float = POST_PX,
            mark=PRE_PX, today: dt.date = EX):
    """One run of ``_World`` on the ex-date."""
    w = _World(tmp_path, broker_mtum=broker_mtum, mtum_px=mtum_px, mark=mark)
    r = w.run(today, feed)
    r.world = w
    return r


def D(day: int) -> dt.date:
    return dt.date(2026, 11, day)


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
    assert "reports NO matching split" in r.block["frozen"]["MTUM"]


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
    assert json.loads((tmp_path / "marks.json").read_text())["marks"].get("MTUM") is None, \
        "no mark is laid while nobody can witness the basis"


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
FEED_FILE = FIX / "alpaca_corporate_actions_2026_11_05.json"


def test_repair_restates_the_real_momentum_record(tmp_path, capsys):
    out = tmp_path / "restated.json"
    before = REAL_BOOK.read_bytes()
    rc = repair.main(["--state", str(REAL_BOOK), "--book", "momentum_satellite",
                      "--split", "MTUM:2026-11-05:4", "--closes", str(CLOSES),
                      "--feed-json", str(FEED_FILE), "--out", str(out)])
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
        repair.restate(json.loads(REAL_BOOK.read_text()), MOMENTUM_SAT, [MTUM_4_1], bad,
                       feed_events=[MTUM_4_1])


def test_repair_never_in_place_never_over_an_existing_file_never_live_state(tmp_path):
    copy = tmp_path / "copy.json"
    shutil.copy(REAL_BOOK, copy)
    base = ["--book", "momentum_satellite", "--split", "MTUM:2026-11-05:4",
            "--closes", str(CLOSES), "--feed-json", str(FEED_FILE)]
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


# =========================================================================== #
# 7. the 2026-11-10 independent review of cf7ae05 — one lock per finding.
#    Each scenario was reproduced from the reviewer's scripts before the fix.
# =========================================================================== #
import scripts.corporate_action_ack as ack_tool  # noqa: E402
from paper_trader.clock_census import EXEMPT  # noqa: E402
from paper_trader.corporate_actions import (  # noqa: E402
    UnhandledAction, gate_query_window, price_ratio_bands)
from paper_trader.heartbeat import PaperHeartbeat  # noqa: E402


def _silent(*_a, **_k) -> dict:
    return {}


def _real(*_a, **_k) -> dict:
    return REAL_FEED


def _sub(r) -> list:
    return [(o["symbol"], o["side"], o["qty"]) for o in r.client.submitted]


# ---- finding 1 (BLOCKER): a freeze is persisted and never releases on drift -- #
def test_F1_a_freeze_PERSISTS_and_never_releases_on_price_drift(tmp_path):
    """c_driver C5: frozen 11-05 at 69.14; 11-06 the price is 80.00 — 276.56/80
    = 3.457, outside every band. The old gate re-derived the freeze from that
    day's price, found nothing, and SUBMITTED `MTUM buy 14`."""
    w = _World(tmp_path, broker_mtum=5)
    r5 = w.run(D(5), _raises)
    assert r5.rc == 70 and "UNCONFIRMED" in r5.block["frozen"]["MTUM"]
    fz = w.marks_file()["frozen"]["MTUM"]
    assert (fz["kind"], fz["frozen_on"], fz["ref_px"], fz["ref_date"]) == (
        "unconfirmed", "2026-11-05", PRE_PX, "2026-11-04")
    w.px["MTUM"] = 80.0
    assert price_split_ratio(PRE_PX, 80.0) is None, "today's price alone is NOT split-shaped"
    r6 = w.run(D(6), _raises)
    assert r6.client.submitted == [] and r6.new_orders == [] and r6.rc == 70
    assert _mtum(r6.block["refused_orders"]), "the spurious buy is constructed and REFUSED"
    assert r6.block["frozen"]["MTUM"] == r5.block["frozen"]["MTUM"], "the reason is not rewritten"
    assert w.marks_file()["marks"]["MTUM"] == {"px": PRE_PX, "run_date": "2026-11-04"}


def test_F1a_release_by_a_feed_confirmed_split_whose_RATIO_matches(tmp_path):
    w = _World(tmp_path, broker_mtum=5)
    w.run(D(5), _raises)
    w.positions["MTUM"] = 20                       # the broker applies the split
    r = w.run(D(6), _real)
    assert r.rc == 0 and ("MTUM", "buy", HONEST_TOPUP) in _sub(r), _sub(r)
    assert [x["ticker"] for x in r.block["released"]] == ["MTUM"]
    assert "matches the observed move" in r.block["released"][0]["why"]
    mf = w.marks_file()
    assert mf["frozen"] == {} and mf["marks"]["MTUM"]["px"] == POST_PX
    assert [j["event"] for j in mf["journal"] if j["ticker"] == "MTUM"] == ["freeze", "release"]


def _frozen_file(path: Path) -> Path:
    path.write_text(json.dumps({"marks": {"MTUM": {"px": PRE_PX, "run_date": "2026-11-04"}},
                                "frozen": {"MTUM": {
                                    "kind": "unconfirmed", "reason": "MTUM mark moved …",
                                    "frozen_on": "2026-11-05", "ref_px": PRE_PX,
                                    "ref_date": "2026-11-04", "no_split_streak": 0,
                                    "streak_date": None}}}))
    return path


def test_F1a_a_confirmed_split_of_the_WRONG_ratio_does_not_release(tmp_path):
    mp = _frozen_file(tmp_path / "m.json")
    two = SplitFeedResult.ok([SplitEvent("MTUM", EX, 2.0)], tickers=["MTUM"],
                             start=D(4), end=D(6))
    g = CorporateActionGate(today=D(6), feed=two, marks_path=mp)
    g.check_prices({"MTUM": POST_PX}, held=["MTUM"])
    assert "MTUM" in g.frozen and g.released == [] and g.stand_down


def test_F1b_operator_ack_releases_is_signed_and_is_journaled(tmp_path, capsys):
    w = _World(tmp_path, broker_mtum=5, mtum_px=193.59)          # a genuine −30% session
    assert w.run(D(5), _raises).rc == 70
    m, why = str(w.marks_path), "a real -30% session, checked against the tape"
    assert ack_tool.main(["--marks", m, "--ticker", "MTUM", "--who", "op"]) == 2      # no reason
    assert ack_tool.main(["--marks", m, "--ticker", "MTUM", "--who", "op",
                          "--reason", "ok"]) == 2                                      # not a reason
    assert ack_tool.main(["--marks", m, "--ticker", "MTUM", "--reason", why]) == 2     # unsigned
    assert ack_tool.main(["--marks", m, "--ticker", "VOO", "--who", "op",
                          "--reason", why]) == 2                                       # not frozen
    assert ack_tool.main(["--marks", "S3://bucket/marks.json", "--ticker", "MTUM",
                          "--who", "op", "--reason", why]) == 2                        # never S3
    assert "ack" not in w.marks_file()["frozen"]["MTUM"], "a refusal writes nothing"
    assert ack_tool.main(["--marks", m, "--list"]) == 0 and "MTUM: kind=unconfirmed" in \
        capsys.readouterr().out
    assert ack_tool.main(["--marks", m, "--ticker", "MTUM", "--who", "op", "--reason", why]) == 0
    r6 = w.run(D(6), _raises)
    assert "MTUM" not in r6.block["frozen"] and r6.rc == 0 and r6.client.submitted
    assert "operator acknowledgement by op" in r6.block["released"][0]["why"]
    mf = w.marks_file()
    assert [j["event"] for j in mf["journal"]] == ["freeze", "ack", "release"]
    assert mf["journal"][1]["who"] == "op" and mf["journal"][1]["why"] == why
    assert mf["marks"]["MTUM"] == {"px": 193.59, "run_date": "2026-11-06"}


def test_F1_book_freeze_persists_and_never_releases_on_drift(tmp_path):
    """f_books F6: parked 11-05..11-10, then at 80.00 the book recorded growth
    0.290 as a clean day."""
    lb = _momentum_through_11_04(tmp_path)
    dead = SplitFeedResult.unavailable("403")
    lb.record("2026-11-05", CLOSE_11_05, splits=dead)
    lb.record("2026-11-06", {"MTUM": 80.0, "SPY": 739.87}, splits=dead)
    st = lb._state()
    assert [d["degraded"] for d in st["days"][-2:]] == [True, True]
    assert "book_growth" not in st["days"][-1]
    fz = st["frozen"]["MTUM"]
    assert (fz["kind"], fz["frozen_on"], fz["ref_px"], fz["ref_date"]) == (
        "unconfirmed", "2026-11-05", 276.56, "2026-11-04")
    assert st["side"]["book"]["shares"] == {"MTUM": 333.0} and st["last_px"]["MTUM"] == 276.56


# ---- finding 2: a real move is released by the FEED, never by time alone ---- #
def test_F2_feed_no_split_x3_releases_a_real_move(tmp_path):
    """c_driver C3: a genuine −30% session froze the book for 12 sessions."""
    w = _World(tmp_path, broker_mtum=5, mtum_px=193.59)
    r5 = w.run(D(5), _silent)
    assert w.run(D(5), _silent).rc == 70          # a same-day re-run is not a second session
    assert w.marks_file()["frozen"]["MTUM"]["no_split_streak"] == 1
    r6 = w.run(D(6), _silent)
    assert r5.rc == r6.rc == 70 and r6.client.submitted == []
    assert w.marks_file()["frozen"]["MTUM"]["no_split_streak"] == 2
    r9 = w.run(D(9), _silent)
    assert r9.rc == 0 and r9.client.submitted and r9.block["frozen"] == {}
    assert "feed answered no-split ×3 — treated as a real move" in r9.block["released"][0]["why"]
    assert "RELEASED" in (tmp_path / "data/state/paper_alerts.log").read_text()
    assert w.marks_file()["journal"][-1]["event"] == "release"


def test_F2_with_the_feed_UNAVAILABLE_it_stays_frozen_and_a_gap_resets_the_count(tmp_path):
    w = _World(tmp_path, broker_mtum=5, mtum_px=193.59)
    for d in (5, 6, 9, 10, 11):
        r = w.run(D(d), _raises)
    assert r.rc == 70 and "MTUM" in r.block["frozen"] and r.client.submitted == []
    assert w.marks_file()["frozen"]["MTUM"]["no_split_streak"] == 0
    for d, feed in ((12, _silent), (13, _silent), (16, _raises), (17, _silent), (18, _silent)):
        r = w.run(D(d), feed)
    assert r.rc == 70 and w.marks_file()["frozen"]["MTUM"]["no_split_streak"] == 2, \
        "consecutive means consecutive: silent, silent, DEAD, silent, silent is 2, not 4"
    assert w.run(D(19), _silent).rc == 0


def test_F2_a_mark_older_than_ten_trading_days_is_not_a_witness(tmp_path):
    mp = tmp_path / "m.json"
    mp.write_text(json.dumps({"marks": {"MTUM": {"px": PRE_PX, "run_date": "2026-10-20"}}}))
    g = CorporateActionGate(today=D(5), feed=_feed_ok(), marks_path=mp)    # 12 weekdays on
    g.check_prices({"MTUM": POST_PX}, held=[], traded=["MTUM"])
    assert g.frozen == {} and g.seeding == ["MTUM"] and g.stand_down
    assert any("trading days" in p for p in g.state.problems)
    fresh = tmp_path / "f.json"
    fresh.write_text(json.dumps({"marks": {"MTUM": {"px": PRE_PX, "run_date": "2026-10-22"}}}))
    g2 = CorporateActionGate(today=D(5), feed=_feed_ok(), marks_path=fresh)  # exactly 10
    g2.check_prices({"MTUM": POST_PX}, held=[], traded=["MTUM"])
    assert "MTUM" in g2.frozen and g2.seeding == []


# ---- finding 3: the feed window ------------------------------------------- #
def test_F3_window_includes_an_ex_date_that_is_the_ledgers_last_event():
    one = dt.timedelta(days=1)
    since, capped = gate_query_window(EX, D(12))
    assert since + one <= D(4) and not capped, "first day = the trading day BEFORE the last event"
    since, _ = gate_query_window(dt.date(2026, 11, 9), dt.date(2026, 11, 9))   # a Monday…
    assert since + one == dt.date(2026, 11, 3), "…today−6 is earlier than the Friday before"
    since, _ = gate_query_window(dt.date(2026, 10, 26), D(12))    # a Monday → that Friday
    assert since + one == dt.date(2026, 10, 23)
    since, _ = gate_query_window(D(11), D(12), oldest_reference=dt.date(2026, 10, 20))
    assert since + one == dt.date(2026, 10, 20), "…and back to the oldest frozen mark"
    since, capped = gate_query_window(dt.date(2026, 7, 1), D(12))
    assert capped and since + one == D(12) - dt.timedelta(days=60)


def test_F3_the_split_is_recovered_after_a_feed_outage_longer_than_the_lookback(tmp_path):
    """c_driver C6: feed dead 11-05..11-12, back on 11-13 with a provider that
    answers ONLY for the window it is asked about."""
    w = _World(tmp_path, broker_mtum=5)
    w.run(D(5), _raises)
    w.positions["MTUM"] = 20
    for d in (6, 9, 10, 11, 12):
        r = w.run(D(d), _raises)
    assert r.rc == 70 and r.led.positions()["MTUM"] == 5
    asked: list = []

    def honest(syms, start, end):
        asked.append((start, end))
        return {"forward_splits": [x for x in REAL_FEED["forward_splits"]
                                   if str(start) <= x["ex_date"] <= str(end)]}
    r = w.run(D(13), honest)
    assert asked[0][0] <= D(4), asked
    assert r.block["applied_this_run"] == ["MTUM:2026-11-05"] and r.block["frozen"] == {}
    assert r.rc == 0 and r.led.positions()["MTUM"] >= 20


# ---- finding 4 / 10: no mark is a seeding day; a bad file is not a crash ---- #
def test_F4_a_first_run_without_marks_is_a_SEEDING_day(tmp_path):
    """a_replay A4b: no marks file, feed alive and silent → `MTUM buy 17`
    submitted, rc 0."""
    w = _World(tmp_path, broker_mtum=5, mark=_NO_MARKS)
    r = w.run(D(5), _silent)
    assert r.rc == 70 and r.client.submitted == [] and r.new_orders == []
    assert r.block["seeding"] == ["MTUM", "SGOV", "VOO"] and r.block["frozen"] == {}
    assert _mtum(r.block["refused_orders"])
    assert "seeding price-basis marks (first run)" in r.hb["last_run"]["reason"]
    assert r.block["marks_age_sessions"] == 0, "the seeding day is flagged weakly witnessed"
    mf = w.marks_file()
    assert mf["_schema"] == "price_basis_marks/v2" and mf["marks"]["MTUM"]["px"] == POST_PX
    assert not list(w.marks_path.parent.glob("*.tmp")), "the temp file is renamed, not left"


def test_F4_no_mark_plus_a_confirmed_split_in_the_window_is_FROZEN(tmp_path):
    """e_edges E3b: broker 20, vendor price not adjusted, no marks → `MTUM sell 15`."""
    w = _World(tmp_path, broker_mtum=20, mtum_px=PRE_PX, mark=_NO_MARKS)
    r = w.run(D(5), _real)
    assert r.rc == 70 and r.client.submitted == []
    assert w.marks_file()["frozen"]["MTUM"]["kind"] == "blind_split"
    assert "MTUM" not in w.marks_file()["marks"]
    r6 = w.run(D(6), _real)
    assert r6.rc == 70 and r6.client.submitted == [] and "acknowledge" in r6.block["frozen"]["MTUM"]


@pytest.mark.parametrize("raw", ['{"marks": {"MTUM": {"px": 276.56}}}',
                                 '{"marks": {"VOO": {"px": null, "run_date": "2026-11-04"}}}',
                                 '{"marks": {"VOO": {"px": 0, "run_date": "2026-11-04"}}}',
                                 '{"marks": {"VOO": {"px": NaN, "run_date": "2026-11-04"}}}'],
                         ids=["no-run_date", "px-null", "px-zero", "px-nan"])
def test_F4_F10_an_invalid_marks_file_is_degraded_and_seeds_never_crashes(tmp_path, raw):
    """c_driver C4: KeyError / AttributeError / TypeError out of main(), no
    heartbeat, no metric, every day. A PARSEABLE file with invalid entries: each
    bad entry is "no mark" for that ticker. (A file that cannot be parsed at all
    is a different case — see the round-3 lock below.)"""
    w = _World(tmp_path, broker_mtum=5, mtum_px=PRE_PX)
    w.marks_path.write_text(raw)
    r = w.run(D(5), _silent)
    assert r.rc == 70 and r.cloud.metrics == [(True, False)] and r.client.submitted == []
    assert r.block["marks_problems"] and r.block["seeding"] and r.block["degraded"] is True
    assert r.hb["last_run"]["run_date"] == "2026-11-05"
    assert set(w.marks_file()["marks"]) >= {"MTUM", "SGOV", "VOO"}
    assert w.run(D(6), _silent).rc == 0


# ---- finding 5: matched by ratio, not by which date the mark carries -------- #
def test_F5_a_mark_laid_ON_the_ex_date_in_the_pre_split_basis_is_not_a_false_freeze(tmp_path):
    """e_edges E4: ex-date run sees the UNADJUSTED price with the feed dead; the
    next day everything is right — and the old gate froze forever."""
    w = _World(tmp_path, broker_mtum=5, mtum_px=PRE_PX)
    r5 = w.run(D(5), _raises)
    assert r5.rc == 0 and w.marks_file()["marks"]["MTUM"] == {"px": PRE_PX,
                                                              "run_date": "2026-11-05"}
    w.positions["MTUM"], w.px["MTUM"] = 20, POST_PX
    r6 = w.run(D(6), _real)
    assert r6.block["frozen"] == {} and r6.rc == 0
    assert ("MTUM", "buy", HONEST_TOPUP) in _sub(r6) and w.run(D(9), _real).rc == 0


def test_F5_vendor_not_adjusted_yet_is_frozen_until_the_price_arrives(tmp_path):
    """e_edges E3: feed confirms, broker already 20, price still 276.56."""
    w = _World(tmp_path, broker_mtum=20, mtum_px=PRE_PX)
    r5 = w.run(D(5), _real)
    assert r5.rc == 70 and r5.client.submitted == []
    assert "vendor has not adjusted" in r5.block["frozen"]["MTUM"]
    assert w.marks_file()["frozen"]["MTUM"]["kind"] == "basis_lag"
    w.px["MTUM"] = 150.0                                       # neither basis: stays frozen
    assert w.run(D(6), _real).rc == 70
    w.px["MTUM"] = POST_PX
    r9 = w.run(D(9), _real)
    assert r9.rc == 0 and "now in the confirmed split's basis" in r9.block["released"][0]["why"]


def test_F5_a_confirmed_ratio_explains_a_move_whatever_date_the_mark_carries(tmp_path):
    """The old test was `ex_date > mark date`: a mark laid ON the ex-date in the
    pre-split basis could never be explained. Matched by RATIO instead — and a
    confirmed split of a different ratio explains nothing."""
    for name, ratio, frozen in (("match", 4.0, False), ("mismatch", 2.0, True)):
        mp = tmp_path / f"{name}.json"
        mp.write_text(json.dumps({"marks": {"MTUM": {"px": PRE_PX, "run_date": "2026-11-05"}}}))
        feed = SplitFeedResult.ok([SplitEvent("MTUM", EX, ratio)], tickers=["MTUM"],
                                  start=D(1), end=D(6))
        g = CorporateActionGate(today=D(6), feed=feed, marks_path=mp)
        g.check_prices({"MTUM": POST_PX}, held=[], traded=["MTUM"])
        assert ("MTUM" in g.frozen) is frozen, name
        if not frozen:      # explained outright — never frozen-then-released
            assert g.released == [] and g.state.journal == []
            assert g.state.marks["MTUM"] == {"px": POST_PX, "run_date": "2026-11-06"}


# ---- finding 6: the heartbeat FILE carries the gate's verdict --------------- #
def test_F6_the_heartbeat_file_itself_says_non_canonical_on_a_stand_down(tmp_path):
    """d_misc D2: rc 70 while last_run.canonical True / reason clean / alert False."""
    r = _replay(tmp_path, broker_mtum=5, feed=_raises)
    hb = json.loads((tmp_path / "data/state/paper_heartbeat.json").read_text())
    assert hb["last_run"]["canonical"] is False
    assert hb["last_run"]["reason"].startswith("corporate actions: FROZEN MTUM")
    assert hb["alert"] is True and "NON-CANONICAL" in hb["alert_reason"]
    v = PaperHeartbeat(root=str(tmp_path)).check(EX, is_trading_day=True)
    assert v.alert and not v.alive and r.rc == 70
    assert "book STOOD DOWN" in (tmp_path / "data/state/paper_alerts.log").read_text()


# ---- finding 7: a dead feed alarms; the ratio set ---------------------------- #
def test_F7_a_feed_unavailable_three_runs_running_is_NON_CANONICAL(tmp_path):
    w = _World(tmp_path, broker_mtum=5, mtum_px=PRE_PX)            # ordinary days throughout
    r5, r6 = w.run(D(5), _raises), w.run(D(6), _raises)
    assert r5.rc == r6.rc == 0 and r6.block["feed_unavailable_streak"] == 2
    assert w.run(D(6), _raises).block["feed_unavailable_streak"] == 2, "per run DATE"
    r9 = w.run(D(9), _raises)
    assert r9.rc == 70 and r9.block["stand_down"] is False
    assert "split feed UNAVAILABLE on 3 consecutive runs" in r9.hb["last_run"]["reason"]
    assert r9.hb["last_run"]["canonical"] is False and r9.hb["alert"] is True
    r10 = w.run(D(10), _silent)
    assert r10.rc == 0 and r10.block["feed_unavailable_streak"] == 0


def test_F7_the_ratio_set_and_its_false_positive_bands():
    for prev, px, want in ((100, 80, 1.25), (100, 40, 2.5), (100, 4, 25.0), (100, 2, 50.0),
                           (100, 3.3, 30.0), (100, 2.5, 40.0), (80, 100, 0.8), (2, 100, 0.02)):
        assert price_split_ratio(prev, px) == pytest.approx(want), (prev, px)
    for px in (92, 88, 86, 108, 115):                 # ordinary sessions, −14%..+15%
        assert price_split_ratio(100, px) is None, px
    bands = price_ratio_bands()
    assert all(b["ret_hi"] < -0.148 or b["ret_lo"] > 0.178 for b in bands), bands
    gaps = [(round(a["ret_hi"], 3), round(b["ret_lo"], 3)) for a, b in zip(bands, bands[1:])]
    assert (-0.245, -0.371) not in gaps and (-0.291, -0.245) in gaps, gaps


# ---- finding 9 / 12: the repair script -------------------------------------- #
@pytest.mark.parametrize("split", ["MTUM:2026-11-05:2", "MTUM:2026-11-06:4", "SPY:2026-11-05:4"],
                         ids=["wrong-ratio", "wrong-ex-date", "wrong-ticker"])
def test_F9_repair_refuses_a_split_the_feed_does_not_corroborate(tmp_path, capsys, split):
    """g_repair: all three were written, rc 0, labelled `verified`."""
    out = tmp_path / "o.json"
    rc = repair.main(["--state", str(REAL_BOOK), "--book", "momentum_satellite", "--split",
                      split, "--closes", str(CLOSES), "--feed-json", str(FEED_FILE),
                      "--out", str(out)])
    assert rc == 2 and not out.exists()
    assert "NOT in the feed payload" in capsys.readouterr().err


def test_F9_repair_refuses_without_a_feed_an_unheld_ticker_and_a_split_shaped_result():
    real, closes = json.loads(REAL_BOOK.read_text()), json.loads(CLOSES.read_text())
    with pytest.raises(repair.RepairRefused, match="no feed payload"):
        repair.restate(real, MOMENTUM_SAT, [MTUM_4_1], closes)
    qual = SplitEvent("QUAL", EX, 4.0)
    with pytest.raises(repair.RepairRefused, match="not held on either side"):
        repair.restate(real, MOMENTUM_SAT, [qual], closes, feed_events=[qual])
    two = SplitEvent("MTUM", EX, 2.0)       # even a (wrongly) corroborated 2:1 …
    with pytest.raises(repair.RepairRefused, match="split-shaped day"):
        repair.restate(real, MOMENTUM_SAT, [two], closes, feed_events=[two])


def test_F12_repair_forbids_every_repo_data_root_and_any_spelling_of_s3(tmp_path):
    copy = tmp_path / "copy.json"
    shutil.copy(REAL_BOOK, copy)
    roots = repair.forbidden_data_roots()
    assert repair.REPO_DATA in roots
    for root in roots:                       # this checkout, the main repo, every worktree
        with pytest.raises(repair.RepairRefused, match="data/ root"):
            repair._guard_paths(copy, root / "state" / "zz_restated.json")
    with pytest.raises(repair.RepairRefused, match="data/ root"):      # an unregistered one
        repair._guard_paths(copy, Path("/x/repo/.claude/worktrees/other/data/state/z.json"))
    for bad in ("S3://bucket/x.json", "s3://bucket/x.json", " S3:/bucket/x.json"):
        with pytest.raises(repair.RepairRefused, match="S3 paths"):
            repair._guard_paths(copy, Path(bad))
    repair._guard_paths(copy, tmp_path / "fine.json")                  # positive control


# ---- finding 11: the small ones --------------------------------------------- #
def _pre_split_fill() -> list:
    return [OrderRecord("a", "2026-09-15", "MTUM", "buy", 5, "day", "filled",
                        filled_qty=5, filled_at="2026-09-15T13:52:00+00:00")]


def test_F11_duplicate_rows_future_dates_partial_pages_and_in_play_lists(tmp_path):
    dup = {"forward_splits": REAL_FEED["forward_splits"][:1] * 2}
    assert len(fetch_splits(lambda *a: dup, ["MTUM"], D(4), D(5)).events) == 1
    led = _ledger(tmp_path / "a")
    g = CorporateActionGate(today=EX, feed=SplitFeedResult(True, (MTUM_4_1, MTUM_4_1)))
    g.apply_to_ledger(led, _pre_split_fill())
    assert g.applied == ["MTUM:2026-11-05"] and led.positions()["MTUM"] == 20
    assert g.in_play["MTUM"] == [MTUM_4_1], "a LIST per ticker"
    led2 = _ledger(tmp_path / "b")
    g2 = CorporateActionGate(today=EX, feed=SplitFeedResult(True, (SplitEvent("MTUM", D(12), 4.0),)))
    g2.apply_to_ledger(led2, _pre_split_fill())
    assert led2.positions()["MTUM"] == 5 and g2.future_events == ["MTUM:2026-11-12"]
    paged = fetch_splits(lambda *a: {"forward_splits": [], "next_page_token": "abc"},
                         ["MTUM"], D(4), D(5))
    assert paged.available is False and "paginated" in paged.reason


def test_F11_an_unmodelled_action_stays_frozen_after_it_leaves_the_feed_window(tmp_path):
    mp = tmp_path / "m.json"
    led = _ledger(tmp_path / "a")
    feed = SplitFeedResult.ok([], [UnhandledAction("MTUM", "stock_dividends", EX)])
    g = CorporateActionGate(today=EX, feed=feed, marks_path=mp)
    g.apply_to_ledger(led, [])
    g.save()
    later = SplitFeedResult.ok(tickers=["MTUM"], start=D(13), end=D(20))   # it has aged out
    g2 = CorporateActionGate(today=D(20), feed=later, marks_path=mp)
    assert "unmodelled corporate action" in g2.frozen["MTUM"] and g2.stand_down
    g2.check_prices({"MTUM": 276.0}, held=["MTUM"])
    for _ in range(3):
        assert "MTUM" in CorporateActionGate(today=D(20), feed=later, marks_path=mp).frozen


def test_F2_book_a_real_move_is_released_by_the_feed_answering_no_split_x3(tmp_path):
    """f_books F6b: a genuine −30% session parked the book until the price
    happened to drift out of the band. Now: three sessions of a feed that
    ANSWERS (and covers the frozen date), then the real move is recorded."""
    lb = _momentum_through_11_04(tmp_path)

    def answered(day: str) -> SplitFeedResult:
        return SplitFeedResult.ok(tickers=["MTUM"], start=D(1), end=dt.date.fromisoformat(day))
    for day, px in (("2026-11-05", 193.6), ("2026-11-06", 195.0)):
        lb.record(day, {"MTUM": px, "SPY": 756.61}, splits=answered(day))
        assert lb._state()["days"][-1]["degraded"] is True
    lb.record("2026-11-09", {"MTUM": 190.0, "SPY": 756.61}, splits=answered("2026-11-09"))
    st = lb._state()
    assert st["days"][-1]["degraded"] is False and st["frozen"] == {}
    assert st["days"][-1]["book_growth"] == pytest.approx(0.6344, abs=1e-3)   # 333 × 190 + cash
    assert "treated as a real move" in st["freeze_journal"][-1]["released"][0]


# ---- finding 13: the census exemption says what the code does ---------------- #
def test_F13_the_marks_file_is_written_on_a_clean_run_and_the_exemption_says_so(tmp_path):
    r = _replay(tmp_path, broker_mtum=5, feed=_silent, mtum_px=254.44)   # nothing frozen
    assert r.rc == 0 and r.world.marks_file()["_schema"] == "price_basis_marks/v2"
    text = EXEMPT[MARKS_REL]
    assert "SEEDING" in text and "PERSISTED freezes" in text and "exit 70" in text


# =========================================================================== #
# 8. round 3 — two rulings corrected on the evidence
# =========================================================================== #
TEN_SESSIONS = (5, 6, 9, 10, 11, 12, 13, 16, 17, 18)


# ---- A: feed silence releases ONLY a sub-2:1 move ---------------------------- #
def test_RA_a_4_to_1_shaped_move_with_a_SILENT_feed_is_still_frozen_on_session_10(tmp_path):
    """The round-2 rule ("feed answered no-split ×3 → a real move") reopened the
    original defect: a feed that simply never reports a real split released the
    freeze on session 3 and the spurious buy was staged. A −30% move still
    releases that way (test_F2_feed_no_split_x3_releases_a_real_move); a move of
    2:1 or more never does."""
    w = _World(tmp_path, broker_mtum=5)                      # mark 276.56 → 69.14
    for d in TEN_SESSIONS:
        r = w.run(D(d), _silent)
        assert r.rc == 70 and r.client.submitted == [] and r.new_orders == [], d
        assert _mtum(r.block["refused_orders"]), d
    fz = w.marks_file()["frozen"]["MTUM"]
    assert (fz["kind"], fz["ratio"], fz["frozen_on"], fz["no_split_streak"]) == (
        "unconfirmed", 4.0, "2026-11-05", 0)
    assert "never on feed silence" in fz["reason"]
    assert w.marks_file()["marks"]["MTUM"] == {"px": PRE_PX, "run_date": "2026-11-04"}
    # …and it is still releasable the right way: the feed confirms a matching split
    w.positions["MTUM"] = 20
    r = w.run(D(19), _real)
    topup = [q for t, side, q in _sub(r) if t == "MTUM" and side == "buy"]
    assert r.rc == 0 and len(topup) == 1 and topup[0] < 6, _sub(r)   # the honest one, vs 20
    assert "matches the observed move" in r.block["released"][0]["why"]


def test_RA_book_a_4_to_1_shaped_move_with_a_silent_feed_stays_parked(tmp_path):
    lb = _momentum_through_11_04(tmp_path)
    for d in TEN_SESSIONS:
        day = D(d).isoformat()
        lb.record(day, {"MTUM": 65.59, "SPY": 756.61},
                  splits=SplitFeedResult.ok(tickers=["MTUM"], start=D(1), end=D(d)))
        st = lb._state()
        assert st["days"][-1]["degraded"] is True and "book_growth" not in st["days"][-1], day
    fz = st["frozen"]["MTUM"]
    assert (fz["ratio"], fz["no_split_streak"], fz["frozen_on"]) == (4.0, 0, "2026-11-05")
    assert "OPERATOR must repair this state file" in st["days"][-1]["reason"]
    assert st["side"]["book"]["shares"] == {"MTUM": 333.0} and st["last_px"]["MTUM"] == 276.56


# ---- B: an unreadable marks file is never "seed and trade tomorrow" ---------- #
@pytest.mark.parametrize("raw", ["[1]", "{not json"], ids=["top-level-list", "not-json"])
def test_RB_an_unreadable_marks_file_stands_down_EVERY_run_until_an_operator_resets_it(
        tmp_path, raw):
    """A file that exists but cannot be parsed may have held freezes. Round 2
    treated it as a first run: seed today, trade tomorrow — the freezes gone."""
    w = _World(tmp_path, broker_mtum=5, mtum_px=254.44)     # the positive control's day
    w.marks_path.write_text(raw)
    for d in (5, 6, 9):
        r = w.run(D(d), _silent)
        assert r.rc == 70 and r.client.submitted == [] and r.new_orders == [], d
        assert r.cloud.metrics == [(True, False)]
        assert ("price-basis marks unreadable — operator must restore or acknowledge"
                in r.hb["last_run"]["reason"])
        assert r.block["marks_unreadable"] is True and r.block["seeding"] == []
        assert r.block["stand_down"] is True and r.block["refused_orders"], \
            "an order WAS constructed (an ordinary −8% day) and the stand-down refused it"
        assert w.marks_path.read_text() == raw, "the bad file is left exactly as it is"
    m, why = str(w.marks_path), "file truncated by a failed sync; no freezes were open"
    assert ack_tool.main(["--marks", m, "--reset-unreadable", "--who", "op"]) == 2
    assert ack_tool.main(["--marks", m, "--reset-unreadable", "--reason", why]) == 2
    assert ack_tool.main(["--marks", "s3://b/marks.json", "--reset-unreadable", "--who", "op",
                          "--reason", why]) == 2
    assert w.marks_path.read_text() == raw, "a refusal moves nothing"
    assert ack_tool.main(["--marks", m, "--reset-unreadable", "--who", "op", "--reason", why]) == 0
    kept = list(w.marks_path.parent.glob("price_basis_marks.json.unreadable-*"))
    assert len(kept) == 1 and kept[0].read_text() == raw, "moved aside, not deleted"
    j = w.marks_file()["journal"]
    assert [(x["event"], x["who"], x["why"]) for x in j] == [("reset_unreadable", "op", why)]
    assert ack_tool.main(["--marks", m, "--reset-unreadable", "--who", "op",
                          "--reason", why]) == 2, "a READABLE file is not reset"
    # the next run is an ordinary seeding day; then the account trades
    r10 = w.run(D(10), _silent)
    assert r10.rc == 70 and r10.block["seeding"] == ["MTUM", "SGOV", "VOO"]
    assert r10.block["marks_unreadable"] is False and r10.block["marks_age_sessions"] == 0
    r11 = w.run(D(11), _silent)
    assert r11.rc == 0 and r11.block["marks_age_sessions"] == 1, "weakly witnessed: flagged"
    assert w.run(D(12), _silent).block["marks_age_sessions"] is None


def test_RB_an_ABSENT_marks_file_is_still_an_ordinary_seeding_day(tmp_path):
    w = _World(tmp_path, broker_mtum=5, mtum_px=PRE_PX, mark=_NO_MARKS)
    r = w.run(D(5), _silent)
    assert r.rc == 70 and r.block["marks_unreadable"] is False and r.block["seeding"]
    assert w.run(D(6), _silent).rc == 0
