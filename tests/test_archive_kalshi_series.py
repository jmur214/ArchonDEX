"""T-405 locks (2026-11-19): the Kalshi archive selects by SERIES, and judges a row priced
only by a REAL quote.

The defect: the snapshot paged the first 2,000 open markets (on the current API almost all
multivariate sports parlays, prefix KXMVE) and kept titles containing a keyword as a
substring ("gold" -> Golden State, "powell" -> Norman Powell). All 21,294 rows ever written
were parlays. The 2026-11-17 fail-closed check counted a non-null field as a price, so the
11-18 parlays (0.0 bid, 0.0 last, 0 volume) read as "364 priced", and the resolver's
_pending() used the same rule.

1. Discovery keeps macro series by a whole-word title keyword or an exact Kalshi tag, and
   drops parlays, combos, KXFED, intraday series, event-minute ladders, state/city series,
   series with no open event, and every category outside the rule set.
2. The snapshot requests only the listed series and stamps series_ticker + selector.
3. It fails closed: no config, an empty config, no market back, or no real quote -> a
   FAILED line and nothing written. It never falls back to paging the open-market list.
4. A real quote is bid > 0, last > 0 or 0 < ask < 1; the resolvers look up nothing else.
5. No request carries a contact address.

The network is stubbed in every test; nothing here touches data/ or the committed config
(except the read-only checks of the committed config at the bottom).
"""
from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


def _serve(monkeypatch: pytest.MonkeyPatch, router) -> list[tuple[str, str]]:
    """Stub urlopen with ``router(url) -> obj | Exception``; record (url, User-Agent)."""
    seen: list[tuple[str, str]] = []
    lock = threading.Lock()

    def fake_urlopen(req, timeout=None):  # noqa: ANN001
        with lock:
            seen.append((req.full_url, req.get_header("User-agent") or ""))
        out = router(req.full_url)
        if isinstance(out, Exception):
            raise out
        return _Resp(json.dumps(out).encode())

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return seen


def _q(url: str) -> dict[str, str]:
    return {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}


def _series(ticker: str, title: str, category: str, frequency: str = "monthly",
            tags: list[str] | None = None) -> dict:
    return {"ticker": ticker, "title": title, "category": category,
            "frequency": frequency, "tags": tags or []}


def _mkt(ticker: str, bid: str | None = "0.4000", ask: str | None = "0.4200",
         last: str | None = "0.4100", **kw: object) -> dict:
    base = {"ticker": ticker, "event_ticker": ticker.rsplit("-", 1)[0],
            "title": f"Will {ticker} be above x?", "yes_sub_title": "Above 0.1%",
            "strike_type": "greater", "floor_strike": 0.1,
            "yes_bid_dollars": bid, "yes_ask_dollars": ask, "last_price_dollars": last,
            "no_bid_dollars": "0.5800", "no_ask_dollars": "0.6000",
            "yes_bid_size_fp": "100.00", "yes_ask_size_fp": "90.00",
            "previous_price_dollars": "0.4000", "volume_fp": "1200.00",
            "volume_24h_fp": "30.00", "open_interest_fp": "800.00", "status": "active",
            "close_time": "2026-12-10T13:30:00Z", "expiration_time": "2026-12-10T13:30:00Z"}
    base.update(kw)
    return base


@pytest.fixture
def sandbox(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(m, "OUT_DIR", tmp_path)
    monkeypatch.setattr(m, "KALSHI_SERIES_CONFIG", tmp_path / "kalshi_macro_series.json")
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    return tmp_path


def _write_config(path: Path, rows: list[dict]) -> None:
    path.write_text(json.dumps({"selector": "series_v1", "series": rows}))


# ---- 1. discovery: what is selected ------------------------------------------------ #
_OPEN_UNIVERSE = [
    _series("KXCPI", "CPI", "Economics", tags=["Inflation"]),
    _series("KXPAYROLLS", "Jobs numbers", "Economics", tags=["Jobs & Economy"]),
    _series("KXGOLDD", "Gold Daily", "Commodities", "daily", ["Gold"]),
    _series("KXTARIFFRATEEU", "EU tariff rate", "Politics", "one_off", ["Trade & tariffs"]),
    _series("KXBTCMAXY", "How high will Bitcoin get this year?", "Crypto", "annual"),
    # rejected — each for one stated reason
    _series("KXNBAGSW", "Golden State Warriors wins", "Sports", "custom", ["Basketball"]),
    _series("KXNBAPTS", "Norman Powell points", "Sports", "custom", ["Basketball"]),
    _series("KXGSWVAL", "Golden State Warriors valuation", "Financials", "annual"),
    _series("KXMVECROSSCATEGORY", "MVE Cross Category CPI and gold", "Economics", "custom"),
    _series("KXFED", "Fed funds rate", "Economics", "custom", ["Fed"]),
    _series("KXINXU", "S&P 500 above/below", "Financials", "hourly", ["S&P 500"]),
    _series("KXGOLD15M", "Gold 15-minute", "Commodities", "fifteen_min", ["Gold"]),
    _series("KX10YRRATEEVENT", "US 10Y Treasury yield after events", "Financials", "custom"),
    _series("KXAAAGASCDNJ", "New Jersey gas price", "Economics", "daily"),
    _series("KXCPICOMBO", "CPI Combo", "Economics", "monthly", ["Inflation"]),
    _series("KXFEDDINNER", "Will the Fed chair attend the dinner?", "Politics", "one_off",
            ["Trump"]),
    _series("KXU3PARTY", "2029 unemployment x 2028 winner", "Elections", "one_off"),
    _series("KXDOGEMINY", "DOGE min yearly", "Crypto", "annual"),
    _series("KXCPIOLD", "CPI (2023)", "Economics", "monthly", ["Inflation"]),   # no open event
]
_OPEN = {s["ticker"]: 1 for s in _OPEN_UNIVERSE if s["ticker"] != "KXCPIOLD"}


def test_discovery_keeps_macro_series_and_rejects_the_parlay_failure_modes():
    picked = m.select_kalshi_series(_OPEN_UNIVERSE, _OPEN)
    assert sorted(picked["ticker"]) == ["KXBTCMAXY", "KXCPI", "KXGOLDD", "KXPAYROLLS",
                                        "KXTARIFFRATEEU"]
    got = picked.set_index("ticker")["matched"]
    assert got["KXCPI"] == "title:cpi" and got["KXGOLDD"] == "title:gold"
    assert got["KXTARIFFRATEEU"] == "tag:trade & tariffs"


@pytest.mark.parametrize("text,hit", [
    ("Gold Daily", "gold"), ("Golden State Warriors", None), ("Goldman CEO leaving", None),
    ("S&P 500 range", "s&p 500"), ("EUR/USD daily range", "eur/usd"),
    ("Federal government employee count", None), ("Fed meeting", "fed"),
    ("Rate cuts this year", "rate cuts"), ("Separate cuts", None),
])
def test_title_keywords_match_whole_words_only(text: str, hit: str | None):
    word = pd.Series([text]).str.extract(m._KALSHI_RULES["Economics"][0],
                                         flags=m.re.IGNORECASE)[0].iloc[0]
    assert (None if pd.isna(word) else word.lower()) == hit


def test_discover_writes_the_reviewed_config_with_the_named_fields(monkeypatch, sandbox):
    series_page = {"series": _OPEN_UNIVERSE}
    events = [{"event_ticker": f"{t}-26DEC", "series_ticker": t} for t in _OPEN]
    pages = {None: {"events": events[:5], "cursor": "c1"}, "c1": {"events": events[5:],
                                                                    "cursor": ""}}

    def router(url: str):
        path = urlparse(url).path
        if path.endswith("/series"):
            return series_page
        if path.endswith("/events"):
            return pages[_q(url).get("cursor")]
        raise AssertionError(f"unexpected request {url}")

    seen = _serve(monkeypatch, router)
    out = sandbox / "cfg.json"
    msg = m.discover_kalshi_series(out)
    assert "wrote 5 series" in msg
    doc = json.loads(out.read_text())
    assert doc["selector"] == "series_v1" and doc["discovered"] == m.SNAP_DATE
    assert sorted(r["ticker"] for r in doc["series"]) == ["KXBTCMAXY", "KXCPI", "KXGOLDD",
                                                           "KXPAYROLLS", "KXTARIFFRATEEU"]
    for r in doc["series"]:
        assert {"ticker", "title", "category", "frequency", "discovered"} <= set(r)
        assert r["discovered"] == m.SNAP_DATE
    assert seen and all("@" not in ua for _, ua in seen)


def test_discover_fails_closed_and_keeps_the_existing_config(monkeypatch, sandbox):
    out = sandbox / "cfg.json"
    out.write_text('{"series": [{"ticker": "KXCPI"}]}')

    def router(url: str):
        if urlparse(url).path.endswith("/series"):
            return {"series": _OPEN_UNIVERSE}
        return {"events": [{"series_ticker": "KXCPI"}], "cursor": "forever"}   # never ends

    seen = _serve(monkeypatch, router)
    monkeypatch.setattr(m, "KALSHI_DISCOVERY_MAX_PAGES", 3)
    msg = m.discover_kalshi_series(out)
    assert "FAILED" in msg and "incomplete" in msg
    assert sum(urlparse(u).path.endswith("/events") for u, _ in seen) == 3
    assert json.loads(out.read_text()) == {"series": [{"ticker": "KXCPI"}]}


# ---- 2. the snapshot pulls only the listed series --------------------------------- #
def _by_series(markets: dict[str, list[dict]]):
    def router(url: str):
        q = _q(url)
        if urlparse(url).path.endswith("/markets") and "series_ticker" in q:
            return {"markets": markets.get(q["series_ticker"], []), "cursor": ""}
        raise AssertionError(f"unlisted or unfiltered request: {url}")
    return router


def test_snapshot_requests_only_listed_series_and_stamps_them(monkeypatch, sandbox):
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": "KXCPI", "category": "Economics"},
                                           {"ticker": "KXGOLDD", "category": "Commodities"}])
    seen = _serve(monkeypatch, _by_series({
        "KXCPI": [_mkt("KXCPI-26NOV-T0.1"), _mkt("KXCPI-26NOV-T0.2")],
        "KXGOLDD": [_mkt("KXGOLDD-26NOV19-T4000")],
        "KXMVECROSSCATEGORY": [_mkt("KXMVECROSSCATEGORY-S1")]}))
    msg = m.snapshot_kalshi()
    assert "snapped 3 markets" in msg and "3 priced" in msg and "2/2 series" in msg
    assert sorted(_q(u)["series_ticker"] for u, _ in seen) == ["KXCPI", "KXGOLDD"]
    assert all(_q(u).get("status") == "open" for u, _ in seen)
    df = pd.read_parquet(sandbox / "kalshi_snapshots.parquet").set_index("ticker")
    assert set(df["selector"]) == {"series_v1"}
    assert df.loc["KXGOLDD-26NOV19-T4000", "series_ticker"] == "KXGOLDD"
    assert df.loc["KXGOLDD-26NOV19-T4000", "category"] == "Commodities"
    assert df.loc["KXCPI-26NOV-T0.1", "yes_bid"] == pytest.approx(0.40)
    assert df.loc["KXCPI-26NOV-T0.1", "floor_strike"] == pytest.approx(0.1)
    assert not df.index.str.startswith("KXMVE").any()
    assert all("@" not in ua for _, ua in seen)


def test_snapshot_keeps_old_rows_and_they_stay_identifiable(monkeypatch, sandbox):
    old = pd.DataFrame([{"snap_date": "2026-11-18", "ticker": "KXMVECROSSCATEGORY-S1",
                         "title": "yes Golden State", "yes_bid": 0.0, "yes_ask": 0.0,
                         "last_price": 0.0, "volume": 0.0}])
    old.to_parquet(sandbox / "kalshi_snapshots.parquet", index=False)
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": "KXCPI", "category": "Economics"}])
    _serve(monkeypatch, _by_series({"KXCPI": [_mkt("KXCPI-26NOV-T0.1")]}))
    m.snapshot_kalshi()
    df = pd.read_parquet(sandbox / "kalshi_snapshots.parquet").set_index("ticker")
    assert len(df) == 2
    assert pd.isna(df.loc["KXMVECROSSCATEGORY-S1", "selector"])
    assert df.loc["KXMVECROSSCATEGORY-S1", "yes_bid"] == 0.0           # untouched
    assert df.loc["KXCPI-26NOV-T0.1", "selector"] == "series_v1"


def test_snapshot_respects_the_request_cap_and_says_partial(monkeypatch, sandbox):
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": t, "category": "Economics"}
                                           for t in ("KXA", "KXB", "KXC")])
    monkeypatch.setattr(m, "KALSHI_MAX_REQUESTS", 2)
    monkeypatch.setattr(m, "KALSHI_WORKERS", 1)
    seen = _serve(monkeypatch, _by_series({t: [_mkt(f"{t}-1")] for t in ("KXA", "KXB", "KXC")}))
    msg = m.snapshot_kalshi()
    assert len(seen) == 2 and "PARTIAL" in msg and "snapped 2 markets" in msg


# ---- 3. fail closed ---------------------------------------------------------------- #
@pytest.mark.parametrize("content", [None, "", "{not json", '{"series": []}',
                                     '{"series": [{"ticker": "KXMVECROSSCATEGORY"}]}',
                                     '{"series": [{"ticker": "KXFED"}]}'])
def test_snapshot_fails_closed_without_a_usable_series_list(monkeypatch, sandbox, content):
    if content is not None:
        m.KALSHI_SERIES_CONFIG.write_text(content)
    seen = _serve(monkeypatch, lambda url: {"markets": [_mkt("KXANY-1")], "cursor": ""})
    msg = m.snapshot_kalshi()
    assert "FAILED" in msg and "nothing written" in msg
    assert seen == []                       # never falls back to paging the open markets
    assert not (sandbox / "kalshi_snapshots.parquet").exists()


def test_snapshot_fails_closed_on_an_all_empty_book_day(monkeypatch, sandbox):
    """The 2026-11-18 shape: 0.0 bid, 0.0 last, 0 volume, a 1.00 or 0.00 ask."""
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": "KXCPI", "category": "Economics"}])
    _serve(monkeypatch, _by_series({"KXCPI": [
        _mkt("KXCPI-1", bid="0.0000", ask="1.0000", last="0.0000", volume_fp="0.00"),
        _mkt("KXCPI-2", bid="0.0000", ask="0.0000", last="0.0000", volume_fp="0.00"),
        _mkt("KXCPI-3", bid=None, ask=None, last=None)]}))
    msg = m.snapshot_kalshi()
    assert "FAILED" in msg and "NONE carries a real quote" in msg
    assert not (sandbox / "kalshi_snapshots.parquet").exists()


def test_snapshot_fails_closed_when_every_series_errors(monkeypatch, sandbox):
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": "KXCPI", "category": "Economics"}])
    _serve(monkeypatch, lambda url: urllib.error.HTTPError(url, 503, "down", {}, None))
    msg = m.snapshot_kalshi()
    assert "FAILED" in msg and "1 errors" in msg
    assert not (sandbox / "kalshi_snapshots.parquet").exists()


def test_snapshot_never_raises_into_the_daily_run(monkeypatch, sandbox):
    """main() evaluates every pull; one exception would skip all the pulls after Kalshi."""
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": "KXCPI", "category": "Economics"}])
    _serve(monkeypatch, _by_series({"KXCPI": [_mkt("KXCPI-1")]}))

    def boom(*a: object, **k: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(m, "_append", boom)
    msg = m.snapshot_kalshi()
    assert msg.startswith("kalshi: FAILED (OSError: disk full)")


def test_a_mixed_day_keeps_every_row_and_counts_only_real_quotes(monkeypatch, sandbox):
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": "KXCPI", "category": "Economics"}])
    _serve(monkeypatch, _by_series({"KXCPI": [
        _mkt("KXCPI-BID"),                                                # bid > 0
        _mkt("KXCPI-LAST", bid="0.0000", ask="1.0000", last="0.0300"),    # last > 0
        _mkt("KXCPI-ASK", bid="0.0000", ask="0.0100", last="0.0000"),     # 0 < ask < 1
        _mkt("KXCPI-EMPTY", bid="0.0000", ask="1.0000", last="0.0000"),
        _mkt("KXCPI-ZERO", bid="0.0000", ask="0.0000", last="0.0000"),
    ]}))
    msg = m.snapshot_kalshi()
    assert "snapped 5 markets" in msg and "(3 priced" in msg
    assert len(pd.read_parquet(sandbox / "kalshi_snapshots.parquet")) == 5


# ---- 4. the real-quote rule and the resolvers ------------------------------------ #
@pytest.mark.parametrize("bid,ask,last,quoted", [
    (0.41, 0.43, 0.42, True), (0.0, 1.0, 0.0, False), (0.0, 0.0, 0.0, False),
    (None, None, None, False), (0.0, 0.001, 0.0, True), (0.0, 1.0, 0.05, True),
    (0.0, 0.99, 0.0, True), (0.0, 1.0, None, False), (0.02, 1.0, 0.0, True),
])
def test_the_real_quote_rule(bid, ask, last, quoted):
    s = lambda v: pd.Series([v], dtype="float64")  # noqa: E731
    assert bool(m._real_quote(s(bid), s(ask), s(last)).iloc[0]) is quoted


def _v1(ticker: str, event: str, close: str = "2026-11-18T21:00:00Z", **kw: object) -> dict:
    row = {"snap_date": "2026-11-18", "ticker": ticker, "event_ticker": event,
           "yes_bid": 0.4, "yes_ask": 0.41, "last_price": 0.4, "close_time": close,
           "series_ticker": event.split("-")[0], "selector": "series_v1"}
    row.update(kw)
    return row


def _settled(ticker: str, event: str, result: str = "no", status: str = "finalized") -> dict:
    return {"ticker": ticker, "event_ticker": event, "status": status, "result": result,
            "settlement_value_dollars": "1.0000" if result == "yes" else "0.0000",
            "expiration_value": "7323.63", "close_time": "2026-11-18T21:00:00Z",
            "settlement_ts": "2026-11-19T00:02:00Z"}


def _event_router(events: dict[str, list[dict] | Exception],
                  markets: dict[str, dict | Exception] | None = None):
    """/events/{ev} -> {"event": ..., "markets": events[ev]}; /markets/{t} -> markets[t]."""
    def router(url: str):
        path = urlparse(url).path
        key = path.rsplit("/", 1)[1]
        if "/events/" in path and key in events:
            out = events[key]
            return out if isinstance(out, Exception) else {"event": {"event_ticker": key},
                                                          "markets": out}
        if "/markets/" in path and markets and key in markets:
            out = markets[key]
            return out if isinstance(out, Exception) else {"market": out}
        raise AssertionError(f"unexpected lookup {url}")
    return router


def _resolutions(sandbox: Path) -> pd.DataFrame:
    return pd.read_parquet(sandbox / "kalshi_resolutions.parquet").set_index("ticker")


def test_kalshi_resolver_never_looks_up_a_pre_t405_row(monkeypatch, sandbox):
    """Old rows are parlays by construction: even one with a real (one-sided) ask is skipped."""
    pd.DataFrame([
        # pre-T-405 rows (no selector), closed, with an ask in (0, 1): never looked up
        {"snap_date": "2026-11-18", "ticker": "KXMVECROSSCATEGORY-S1",
         "event_ticker": "KXMVECROSSCATEGORY-R1", "yes_bid": 0.0, "yes_ask": 0.02,
         "last_price": 0.0, "close_time": "2026-11-18T23:00:00Z"},
        {"snap_date": "2026-11-18", "ticker": "KXMVESPORTSMULTIGAMEEXTENDED-S2",
         "event_ticker": "KXMVESPORTSMULTIGAMEEXTENDED-R2", "yes_bid": 0.0,
         "yes_ask": 0.349, "last_price": 0.0, "close_time": "2026-11-18T23:00:00Z",
         "selector": None},
        # a series_v1 row, an ask-only real quote, closed: looked up
        _v1("KXCPI-26OCT-T0.9", "KXCPI-26OCT", yes_bid=0.0, yes_ask=0.02, last_price=0.0),
    ]).to_parquet(sandbox / "kalshi_snapshots.parquet", index=False)
    seen = _serve(monkeypatch, _event_router(
        {"KXCPI-26OCT": [_settled("KXCPI-26OCT-T0.9", "KXCPI-26OCT")]}))
    msg = m.resolve_kalshi_snapshots()
    assert [urlparse(u).path.rsplit("/", 1)[1] for u, _ in seen] == ["KXCPI-26OCT"]
    assert list(_resolutions(sandbox).index) == ["KXCPI-26OCT-T0.9"]
    assert "1 final" in msg and all("@" not in ua for _, ua in seen)


def test_kalshi_resolver_makes_one_request_per_event(monkeypatch, sandbox):
    pd.DataFrame([_v1(f"KXINX-26NOV18H1600-B{k}", "KXINX-26NOV18H1600") for k in (7300, 7325, 7350)]
                 + [_v1(f"KXWTI-26NOV1814-T{k}", "KXWTI-26NOV1814") for k in (81.99, 82.49)]
                 ).to_parquet(sandbox / "kalshi_snapshots.parquet", index=False)
    inx = [_settled(f"KXINX-26NOV18H1600-B{k}", "KXINX-26NOV18H1600",
                    "yes" if k == 7325 else "no") for k in (7300, 7325, 7350, 7375)]
    wti = [_settled(f"KXWTI-26NOV1814-T{k}", "KXWTI-26NOV1814", "yes") for k in (81.99, 82.49)]
    seen = _serve(monkeypatch, _event_router({"KXINX-26NOV18H1600": inx,
                                              "KXWTI-26NOV1814": wti}))
    msg = m.resolve_kalshi_snapshots()
    assert len(seen) == 2 and all("/events/" in u for u, _ in seen)
    res = _resolutions(sandbox)
    assert len(res) == 5                                   # only the SNAPPED markets
    assert "KXINX-26NOV18H1600-B7375" not in res.index
    assert res["final"].all() and set(res["resolved_via"]) == {"event"}
    assert res.loc["KXINX-26NOV18H1600-B7325", "result"] == "yes"
    assert res.loc["KXINX-26NOV18H1600-B7325", "settlement_value"] == pytest.approx(1.0)
    assert res.loc["KXINX-26NOV18H1600-B7300", "expiration_value"] == pytest.approx(7323.63)
    assert "2/2 due events" in msg and "5 final" in msg

    seen.clear()                                           # all final: nothing re-asked
    assert m.resolve_kalshi_snapshots() == "kalshi_resolve: nothing pending" and not seen


def test_kalshi_resolver_caps_by_events_earliest_close_first(monkeypatch, sandbox):
    rows = [_v1(f"KXGOLDD-26NOV{d:02d}17-T1", f"KXGOLDD-26NOV{d:02d}17",
                close=f"2026-11-{d:02d}T22:00:00Z") for d in (14, 10, 12, 11, 13)]
    pd.DataFrame(rows).to_parquet(sandbox / "kalshi_snapshots.parquet", index=False)
    monkeypatch.setattr(m, "MAX_RESOLVE_EVENTS_PER_RUN", 2)
    events = {f"KXGOLDD-26NOV{d:02d}17": [_settled(f"KXGOLDD-26NOV{d:02d}17-T1",
                                                   f"KXGOLDD-26NOV{d:02d}17")]
              for d in range(10, 15)}
    seen = _serve(monkeypatch, _event_router(events))
    msg = m.resolve_kalshi_snapshots()
    assert [urlparse(u).path.rsplit("/", 1)[1] for u, _ in seen] == ["KXGOLDD-26NOV1017",
                                                                    "KXGOLDD-26NOV1117"]
    assert "2/5 due events" in msg


def test_a_gone_event_records_its_snapped_markets_final_not_found(monkeypatch, sandbox):
    pd.DataFrame([_v1("KXA-1-T1", "KXA-1"), _v1("KXA-1-T2", "KXA-1")]).to_parquet(
        sandbox / "kalshi_snapshots.parquet", index=False)
    gone = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    _serve(monkeypatch, _event_router({"KXA-1": gone}))
    m.resolve_kalshi_snapshots()
    res = _resolutions(sandbox)
    assert set(res["status"]) == {"not_found"} and res["final"].all() and len(res) == 2


def test_a_ticker_absent_from_its_event_is_looked_up_alone_never_assumed(monkeypatch, sandbox):
    pd.DataFrame([_v1("KXB-1-T1", "KXB-1"), _v1("KXB-1-T2", "KXB-1"),
                  _v1("KXB-1-T3", "KXB-1")]).to_parquet(
        sandbox / "kalshi_snapshots.parquet", index=False)
    events = {"KXB-1": [_settled("KXB-1-T1", "KXB-1")]}          # T2, T3 absent
    markets: dict[str, dict | Exception] = {
        "KXB-1-T2": _settled("KXB-1-T2", "KXB-1", "yes"),          # the market answers
        "KXB-1-T3": urllib.error.HTTPError("u", 503, "down", {}, None)}  # it errors
    seen = _serve(monkeypatch, _event_router(events, markets))
    msg = m.resolve_kalshi_snapshots()
    res = _resolutions(sandbox)
    assert sorted(res.index) == ["KXB-1-T1", "KXB-1-T2"]          # T3 NOT recorded
    assert res.loc["KXB-1-T2", "resolved_via"] == "market" and bool(res.loc["KXB-1-T2", "final"])
    assert "2 absent" in msg and "2 single-market lookups" in msg and "1 errors" in msg
    assert sum("/markets/" in u for u, _ in seen) == 2

    # next run: T3 is still pending, so its event is asked again and T3 again alone
    seen.clear()
    markets["KXB-1-T3"] = urllib.error.HTTPError("u", 404, "Not Found", {}, None)
    m.resolve_kalshi_snapshots()
    res = _resolutions(sandbox)
    assert res.loc["KXB-1-T3", "status"] == "not_found" and bool(res.loc["KXB-1-T3", "final"])
    assert [urlparse(u).path.rsplit("/", 1)[1] for u, _ in seen] == ["KXB-1", "KXB-1-T3"]


def test_absent_tickers_beyond_the_fallback_cap_stay_pending(monkeypatch, sandbox):
    pd.DataFrame([_v1(f"KXC-1-T{i}", "KXC-1") for i in range(4)]).to_parquet(
        sandbox / "kalshi_snapshots.parquet", index=False)
    monkeypatch.setattr(m, "MAX_RESOLVE_MARKET_FALLBACKS_PER_RUN", 1)
    markets = {f"KXC-1-T{i}": _settled(f"KXC-1-T{i}", "KXC-1") for i in range(4)}
    _serve(monkeypatch, _event_router({"KXC-1": []}, markets))   # the event lists none
    m.resolve_kalshi_snapshots()
    assert list(_resolutions(sandbox).index) == ["KXC-1-T0"]       # 3 left pending, unrecorded


def test_an_unsettled_market_is_recorded_not_final_and_asked_again(monkeypatch, sandbox):
    pd.DataFrame([_v1("KXD-1-T1", "KXD-1")]).to_parquet(sandbox / "kalshi_snapshots.parquet",
                                                         index=False)
    events: dict[str, list[dict] | Exception] = {
        "KXD-1": [_settled("KXD-1-T1", "KXD-1", result="", status="closed")]}
    seen = _serve(monkeypatch, _event_router(events))
    m.resolve_kalshi_snapshots()
    assert not bool(_resolutions(sandbox).loc["KXD-1-T1", "final"])
    events["KXD-1"] = [_settled("KXD-1-T1", "KXD-1", "yes")]
    m.resolve_kalshi_snapshots()
    assert bool(_resolutions(sandbox).loc["KXD-1-T1", "final"]) and len(seen) == 2


def test_the_kalshi_resolver_never_raises(monkeypatch, sandbox):
    (sandbox / "kalshi_snapshots.parquet").write_bytes(b"not a parquet file")
    assert m.resolve_kalshi_snapshots().startswith("kalshi_resolve: FAILED")


def test_polymarket_resolver_keeps_long_shots_and_skips_empty_books(monkeypatch, sandbox):
    pd.DataFrame([
        # a long shot: bid 0, last 0, ask 0.001 -- a real quote
        {"snap_date": "2026-11-18", "id": "21", "prices": '["0.0005", "0.9995"]',
         "best_bid": 0.0, "best_ask": 0.001, "last_trade_price": 0.0,
         "end_date": "2026-11-18T12:00:00Z"},
        # an empty book (the 2026-11-18 shape): never looked up
        {"snap_date": "2026-11-18", "id": "22", "prices": "None", "best_bid": 0.0,
         "best_ask": 1.0, "last_trade_price": 0.0, "end_date": "2026-11-18T12:00:00Z"},
        # a pre-2026-11-17 row (prices only): still looked up
        {"snap_date": "2026-09-01", "id": "23", "prices": '["0.42", "0.58"]',
         "best_bid": None, "best_ask": None, "last_trade_price": None,
         "end_date": "2026-09-02T00:00:00Z"},
    ]).to_parquet(sandbox / "polymarket_snapshots.parquet", index=False)

    def router(url: str):
        i = url.rsplit("/", 1)[1]
        if i == "22":
            raise AssertionError("looked up an empty book")
        return {"id": i, "closed": True, "umaResolutionStatus": "resolved",
                "outcomePrices": '["0", "1"]'}

    seen = _serve(monkeypatch, router)
    m.resolve_polymarket_snapshots()
    assert sorted(u.rsplit("/", 1)[1] for u, _ in seen) == ["21", "23"]


# ---- 5. the CLI writes where it is told ------------------------------------------- #
def test_cli_kalshi_only_writes_to_the_out_dir(monkeypatch, sandbox, tmp_path):
    cfg = tmp_path / "list.json"
    _write_config(cfg, [{"ticker": "KXCPI", "category": "Economics"}])
    out = tmp_path / "scratch"

    def router(url: str):
        if urlparse(url).path.endswith("/markets"):
            return {"markets": [_mkt("KXCPI-1")], "cursor": ""}
        raise AssertionError(url)

    _serve(monkeypatch, router)
    rc = m.main(["--kalshi-only", "--out-dir", str(out), "--kalshi-config", str(cfg)])
    assert rc == 0 and (out / "kalshi_snapshots.parquet").exists()


# ---- 6. the committed config (read-only) ------------------------------------------ #
def _committed() -> dict:
    return json.loads((m.ROOT / "config" / "kalshi_macro_series.json").read_text())


def test_the_committed_config_is_a_clean_reviewed_list():
    doc = _committed()
    rows = doc["series"]
    assert doc["selector"] == m.KALSHI_SELECTOR and len(rows) >= 50
    tickers = [r["ticker"] for r in rows]
    assert len(tickers) == len(set(tickers))
    assert not any(t.upper().startswith("KXMVE") for t in tickers)
    assert m.KXFED_SERIES not in tickers
    for r in rows:
        assert {"ticker", "title", "category", "frequency", "discovered"} <= set(r)
        assert r["category"] in m._KALSHI_RULES
        assert r["frequency"] not in m.KALSHI_SKIP_FREQUENCIES
    cats = {r["category"] for r in rows}
    assert {"Economics", "Financials", "Commodities"} <= cats
    assert "KXCPI" in tickers and "KXPAYROLLS" in tickers


def test_the_committed_config_is_what_the_rule_selects():
    """Re-running the rule on the committed rows keeps every one of them: a hand-added row
    the rule would reject fails here."""
    rows = _committed()["series"]
    again = m.select_kalshi_series(rows, {r["ticker"]: 1 for r in rows})
    assert sorted(again["ticker"]) == sorted(r["ticker"] for r in rows)
