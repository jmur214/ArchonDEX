"""Prediction-market archive locks (2026-11-17, the T-403 follow-up the user approved).

1. The Kalshi snapshot reads the CURRENT API fields (*_dollars / *_fp). The legacy
   yes_bid / yes_ask / last_price fields are null, and every row from July to November was
   price-less.
2. Both snapshots FAIL CLOSED when every price or quote field is null. They write nothing
   and say so, so the local verifier's zero-fresh-rows gate fires instead of the archive
   silently filling with empty rows.
3. Outcomes: the resolvers look up only markets captured WITH a price whose close or end
   time has passed. They record final outcomes, never re-look-up a final one, and record a
   404 as final.

The network is stubbed in every test; nothing here touches data/.
"""
from __future__ import annotations

import io
import json
import urllib.error
import urllib.request

import pandas as pd
import pytest

import scripts.archive_altdata_t136 as m


class _Resp:
    def __init__(self, body: bytes) -> None:
        self._b = body

    def read(self) -> bytes:
        return self._b

    def __enter__(self) -> "_Resp":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False


def _kalshi_market(ticker: str, title: str = "Fed rate cut in December?", **kw) -> dict:
    base = {"ticker": ticker, "event_ticker": "KXFEDDEC", "title": title, "category": "",
            "yes_bid_dollars": "0.4100", "yes_ask_dollars": "0.4300",
            "no_bid_dollars": "0.5700", "no_ask_dollars": "0.5900",
            "yes_bid_size_fp": "120.00", "yes_ask_size_fp": "80.00",
            "last_price_dollars": "0.4200", "previous_price_dollars": "0.4000",
            "volume_fp": "1500.00", "volume_24h_fp": "90.00", "open_interest_fp": "700.00",
            "status": "active", "close_time": "2026-12-10T19:00:00Z",
            "expiration_time": "2026-12-11T19:00:00Z",
            # the legacy fields the old code read: null on the current API
            "yes_bid": None, "yes_ask": None, "last_price": None, "volume": None}
    base.update(kw)
    return base


@pytest.fixture
def sandbox(monkeypatch, tmp_path):
    monkeypatch.setattr(m, "OUT_DIR", tmp_path)
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    # T-405: the Kalshi snapshot reads a series list; one series, so each stubbed response
    # below is served once (the series-selection locks live in test_archive_kalshi_series.py)
    cfg = tmp_path / "kalshi_macro_series.json"
    cfg.write_text(json.dumps({"series": [{"ticker": "KXCPI", "category": "Economics"}]}))
    monkeypatch.setattr(m, "KALSHI_SERIES_CONFIG", cfg)
    return tmp_path


def _serve(monkeypatch, router):
    seen = []

    def fake_urlopen(req, timeout=None):  # noqa: ANN001
        url = req.full_url
        seen.append(url)
        out = router(url)
        if isinstance(out, Exception):
            raise out
        return _Resp(json.dumps(out).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return seen


# ---- 1 + 2: the Kalshi snapshot ------------------------------------------------ #
def test_kalshi_snapshot_reads_the_dollar_fields(monkeypatch, sandbox):
    _serve(monkeypatch, lambda url: {"markets": [_kalshi_market("KXFED-A")], "cursor": None})
    msg = m.snapshot_kalshi()
    assert "snapped 1" in msg and "1 priced" in msg
    df = pd.read_parquet(sandbox / "kalshi_snapshots.parquet")
    row = df.iloc[0]
    assert row["yes_bid"] == pytest.approx(0.41) and row["yes_ask"] == pytest.approx(0.43)
    assert row["last_price"] == pytest.approx(0.42) and row["volume"] == pytest.approx(1500.0)
    assert row["open_interest"] == pytest.approx(700.0) and row["event_ticker"] == "KXFEDDEC"


def test_kalshi_snapshot_fails_closed_when_every_price_is_null(monkeypatch, sandbox):
    nulls = {k: None for k in ("yes_bid_dollars", "yes_ask_dollars", "last_price_dollars")}
    _serve(monkeypatch, lambda url: {"markets": [_kalshi_market("KXFED-A", **nulls),
                                                 _kalshi_market("KXFED-B", **nulls)],
                                     "cursor": None})
    msg = m.snapshot_kalshi()
    assert "FAILED" in msg and "nothing written" in msg
    assert not (sandbox / "kalshi_snapshots.parquet").exists()


def test_kalshi_snapshot_keeps_a_day_when_some_markets_are_unquoted(monkeypatch, sandbox):
    nulls = {k: None for k in ("yes_bid_dollars", "yes_ask_dollars", "last_price_dollars")}
    _serve(monkeypatch, lambda url: {"markets": [_kalshi_market("KXFED-A"),
                                                 _kalshi_market("KXFED-B", **nulls)],
                                     "cursor": None})
    assert "1 priced" in m.snapshot_kalshi()
    assert len(pd.read_parquet(sandbox / "kalshi_snapshots.parquet")) == 2


# ---- 2: the Polymarket snapshot ---------------------------------------------- #
def _poly(i: int, **kw) -> dict:
    base = {"id": str(i), "question": "Will the Fed cut rates in December?", "category": "",
            "outcomes": '["Yes", "No"]', "outcomePrices": '["0.42", "0.58"]',
            "volume": "1000", "endDate": "2026-12-10T00:00:00Z", "bestBid": 0.41,
            "bestAsk": 0.43, "lastTradePrice": 0.42, "spread": 0.02, "liquidityNum": 5000.0,
            "volume24hr": 120.0, "conditionId": "0xabc"}
    base.update(kw)
    return base


def test_polymarket_snapshot_captures_the_quote(monkeypatch, sandbox):
    pages = {0: [_poly(1)], 100: []}
    _serve(monkeypatch, lambda url: pages[int(url.split("offset=")[1])])
    assert "1 quoted" in m.snapshot_polymarket()
    row = pd.read_parquet(sandbox / "polymarket_snapshots.parquet").iloc[0]
    assert row["best_bid"] == pytest.approx(0.41) and row["best_ask"] == pytest.approx(0.43)
    assert row["last_trade_price"] == pytest.approx(0.42) and row["condition_id"] == "0xabc"


def test_polymarket_snapshot_fails_closed_without_any_quote(monkeypatch, sandbox):
    pages = {0: [_poly(1, bestBid=None, bestAsk=None, lastTradePrice=None)], 100: []}
    _serve(monkeypatch, lambda url: pages[int(url.split("offset=")[1])])
    msg = m.snapshot_polymarket()
    assert "FAILED" in msg and not (sandbox / "polymarket_snapshots.parquet").exists()


# ---- 3: outcomes ------------------------------------------------------------- #
# T-405 follow-up: Kalshi resolves only selector == "series_v1" rows, one GET per EVENT
# (/events/{event_ticker}); the event-level locks are in test_archive_kalshi_series.py.
def _write_kalshi_snaps(path):
    v1 = {"selector": "series_v1"}
    pd.DataFrame([
        # closed, priced -> looked up
        {"snap_date": "2026-11-01", "ticker": "K-DONE", "event_ticker": "EV-DONE",
         "yes_bid": 0.9, "yes_ask": 0.92, "last_price": 0.91,
         "close_time": "2026-11-02T00:00:00Z", **v1},
        # closed, priced, not settled yet -> looked up, not final
        {"snap_date": "2026-11-01", "ticker": "K-WAIT", "event_ticker": "EV-WAIT",
         "yes_bid": 0.5, "yes_ask": 0.52, "last_price": 0.51,
         "close_time": "2026-11-03T00:00:00Z", **v1},
        # closed, priced, event gone -> 404 recorded final
        {"snap_date": "2026-11-01", "ticker": "K-GONE", "event_ticker": "EV-GONE",
         "yes_bid": 0.1, "yes_ask": 0.12, "last_price": 0.11,
         "close_time": "2026-11-04T00:00:00Z", **v1},
        # closed but PRICE-LESS -> never looked up
        {"snap_date": "2026-08-01", "ticker": "K-NULL", "event_ticker": "EV-NULL",
         "yes_bid": None, "yes_ask": None, "last_price": None,
         "close_time": "2026-08-02T00:00:00Z", **v1},
        # still open -> never looked up
        {"snap_date": "2026-11-17", "ticker": "K-OPEN", "event_ticker": "EV-OPEN",
         "yes_bid": 0.3, "yes_ask": 0.32, "last_price": 0.31,
         "close_time": "2099-01-01T00:00:00Z", **v1},
    ]).to_parquet(path, index=False)


def _kalshi_router(url):
    ev = url.rsplit("/", 1)[1]
    if "/events/" not in url:
        raise AssertionError(f"expected one GET per event, got {url}")
    if ev == "EV-DONE":
        return {"event": {"event_ticker": ev}, "markets": [
            {"ticker": "K-DONE", "event_ticker": ev, "status": "finalized", "result": "yes",
             "settlement_value_dollars": "1.0000"}]}
    if ev == "EV-WAIT":
        return {"event": {"event_ticker": ev}, "markets": [
            {"ticker": "K-WAIT", "event_ticker": ev, "status": "closed", "result": ""}]}
    if ev == "EV-GONE":
        return urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b""))
    raise AssertionError(f"looked up an event it must not: {ev}")


def test_kalshi_resolver_records_outcomes_and_skips_what_it_must(monkeypatch, sandbox):
    _write_kalshi_snaps(sandbox / "kalshi_snapshots.parquet")
    seen = _serve(monkeypatch, _kalshi_router)
    msg = m.resolve_kalshi_snapshots()
    assert sorted(u.rsplit("/", 1)[1] for u in seen) == ["EV-DONE", "EV-GONE", "EV-WAIT"]
    res = pd.read_parquet(sandbox / "kalshi_resolutions.parquet").set_index("ticker")
    assert bool(res.loc["K-DONE", "final"]) and res.loc["K-DONE", "result"] == "yes"
    assert res.loc["K-DONE", "settlement_value"] == pytest.approx(1.0)
    assert not bool(res.loc["K-WAIT", "final"])
    assert bool(res.loc["K-GONE", "final"]) and res.loc["K-GONE", "status"] == "not_found"
    assert "2 final" in msg

    # a second run re-asks only the unsettled one's event
    seen.clear()
    m.resolve_kalshi_snapshots()
    assert [u.rsplit("/", 1)[1] for u in seen] == ["EV-WAIT"]


def test_kalshi_resolver_respects_the_per_run_event_cap(monkeypatch, sandbox):
    rows = [{"snap_date": "2026-11-01", "ticker": f"K{i:03d}", "event_ticker": f"EV{i:03d}",
             "yes_bid": 0.5, "yes_ask": 0.5, "last_price": 0.5,
             "close_time": "2026-11-02T00:00:00Z", "selector": "series_v1"} for i in range(7)]
    pd.DataFrame(rows).to_parquet(sandbox / "kalshi_snapshots.parquet", index=False)
    monkeypatch.setattr(m, "MAX_RESOLVE_EVENTS_PER_RUN", 3)
    seen = _serve(monkeypatch, lambda url: {"markets": [
        {"ticker": "K" + url.rsplit("EV", 1)[1], "status": "finalized", "result": "no"}]})
    m.resolve_kalshi_snapshots()
    assert len(seen) == 3


def test_polymarket_resolver_records_final_prices(monkeypatch, sandbox):
    pd.DataFrame([
        {"snap_date": "2026-11-01", "id": "11", "prices": '["0.9","0.1"]',
         "end_date": "2026-11-02T00:00:00Z"},
        {"snap_date": "2026-11-01", "id": "12", "prices": '["0.5","0.5"]',
         "end_date": "2026-11-03T00:00:00Z"},
        {"snap_date": "2026-11-17", "id": "13", "prices": '["0.3","0.7"]',
         "end_date": "2099-01-01T00:00:00Z"},
    ]).to_parquet(sandbox / "polymarket_snapshots.parquet", index=False)

    def router(url):
        i = url.rsplit("/", 1)[1]
        if i == "11":
            return {"id": i, "closed": True, "umaResolutionStatus": "resolved",
                    "outcomePrices": '["1", "0"]', "outcomes": '["Yes", "No"]'}
        if i == "12":
            return {"id": i, "closed": True, "umaResolutionStatus": "proposed"}
        raise AssertionError(f"looked up a market it must not: {i}")

    seen = _serve(monkeypatch, router)
    m.resolve_polymarket_snapshots()
    assert sorted(u.rsplit("/", 1)[1] for u in seen) == ["11", "12"]
    res = pd.read_parquet(sandbox / "polymarket_resolutions.parquet").set_index("id")
    assert bool(res.loc["11", "final"]) and res.loc["11", "final_prices"] == '["1", "0"]'
    assert not bool(res.loc["12", "final"])


def test_resolver_requests_carry_no_contact_address(monkeypatch, sandbox):
    _write_kalshi_snaps(sandbox / "kalshi_snapshots.parquet")
    uas = []

    def fake_urlopen(req, timeout=None):  # noqa: ANN001
        uas.append(req.get_header("User-agent") or "")
        out = _kalshi_router(req.full_url)
        if isinstance(out, Exception):
            raise out
        return _Resp(json.dumps(out).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    m.resolve_kalshi_snapshots()
    assert uas and all("@" not in u for u in uas)
