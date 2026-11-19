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
    # Politics by a narrow title phrase (these carry only a Trump/Congress tag)
    _series("KXFEDCHAIRNOM", "Fed Chair nominee", "Politics", "custom", ["Trump"]),
    _series("KXGOVSHUT", "Government shutdown", "Politics", "custom", ["Congress"]),
    # the national University of Michigan survey despite the state name; a plural keyword
    _series("KXUMICHOVR", "Michigan consumer sentiment above X in [year]?", "Economics",
            "one_off", ["Jobs & Economy"]),
    _series("KXWRECSS", "World recessions", "Economics", "custom", ["Growth"]),
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
    # The original 2026-11-19 fixture text. It was REJECTED by the tag-only Politics rule,
    # MATCHED once the "fed chair" title phrase was added (6050d1d), and is rejected again
    # by the Politics novelty rule (visit/attend/dinner): the intended outcome is rejection.
    _series("KXFEDDINNER", "Will the Fed chair attend the dinner?", "Politics", "one_off",
            ["Trump"]),
    _series("KXTRUMPVISITFED", "Will Trump visit the Federal Reserve?", "Politics", "one_off",
            ["Travel & meetings", "Trump"]),              # novelty, despite "federal reserve"
    _series("KXFEDLAWYER", "Will the Fed's lawyer resign?", "Politics", "one_off",
            ["Trump"]),                                   # "fed" alone: not a policy phrase
    _series("KXAIKILLSWITCH", "Federal AI model shutdown authority", "Politics", "one_off",
            ["AI", "Congress"]),                          # bare "shutdown": not a policy phrase
    _series("KXSENOH", "Who will win the 2028 Senate race?", "Politics", "one_off",
            ["Senate"]),                                  # a candidate race
    _series("KXMIMFGEMP", "Michigan manufacturing employment", "Economics", "annual",
            ["Jobs & Economy"]),                          # a state series
    _series("KXAAAGASDTX", "TX gas price", "Economics", "daily",
            ["Oil and energy"]),                          # a state series by postal code
    _series("KXAAAGASM", "US gas price", "Economics", "monthly"),   # ...but US is national
    _series("KXU3PARTY", "2029 unemployment x 2028 winner", "Elections", "one_off"),
    _series("KXDOGEMINY", "DOGE min yearly", "Crypto", "annual"),
    _series("KXCPIOLD", "CPI (2023)", "Economics", "monthly", ["Inflation"]),   # no open event
]
_OPEN = {s["ticker"]: 1 for s in _OPEN_UNIVERSE if s["ticker"] != "KXCPIOLD"}
_KEPT = ["KXAAAGASM", "KXBTCMAXY", "KXCPI", "KXFEDCHAIRNOM", "KXGOLDD", "KXGOVSHUT",
         "KXPAYROLLS", "KXTARIFFRATEEU", "KXUMICHOVR", "KXWRECSS"]


def test_discovery_keeps_macro_series_and_rejects_the_parlay_failure_modes():
    picked = m.select_kalshi_series(_OPEN_UNIVERSE, _OPEN)
    assert sorted(picked["ticker"]) == _KEPT
    got = picked.set_index("ticker")["matched"]
    assert got["KXCPI"] == "title:cpi" and got["KXGOLDD"] == "title:gold"
    assert got["KXTARIFFRATEEU"] == "tag:trade & tariffs"
    assert got["KXFEDCHAIRNOM"] == "title:fed chair" and got["KXGOVSHUT"].startswith("title:")
    assert got["KXWRECSS"] == "title:recessions"


def test_politics_novelty_markets_are_rejected_even_with_a_policy_phrase():
    cls = m._classify_series([s for s in _OPEN_UNIVERSE
                              if s["ticker"] in ("KXFEDDINNER", "KXTRUMPVISITFED")], {})
    assert list(cls["matched"].str.startswith("title:")) == [True, True]   # the phrase matches
    assert cls["excluded"].all()                                          # novelty excludes


@pytest.mark.parametrize("title,category,tags,kept", [
    ("IN CPI", "Economics", ["Inflation"], True),                 # India, not Indiana
    ("DE GDP", "Economics", ["GDP"], True),                       # Germany, not Delaware
    ("CA unemployment", "Economics", ["Jobs & Economy"], True),   # ambiguous: kept
    ("ID rate decision", "Economics", ["Global Central Banks"], True),   # Indonesia
    ("TX gas price", "Economics", ["Oil and energy"], False),      # a state retail price
    ("NY home prices", "Economics", ["Housing"], False),
    ("US gas price", "Economics", ["Oil and energy"], True),       # US is not a state code
])
def test_a_postal_code_prefix_is_regional_only_before_a_local_price(title, category, tags,
                                                                     kept):
    picked = m.select_kalshi_series([_series("KXT", title, category, "monthly", tags)],
                                    {"KXT": 1})
    assert (len(picked) == 1) is kept


_NOW = pd.Timestamp("2026-11-19T16:00:00Z")
_BETWEEN = [
    _series("KXJOBLESSCLAIMS", "Weekly initial jobless claims", "Economics", "weekly"),
    _series("KXGDP", "US GDP growth", "Economics", "quarterly", ["GDP"]),
    _series("KXCPIOLD", "CPI (2023)", "Economics", "monthly", ["Inflation"]),
    _series("KXFEDCUTONCE", "Next Fed rate cut (2025)", "Economics", "one_off", ["Fed"]),
    _series("KXCPI", "CPI", "Economics", "monthly", ["Inflation"]),
]


def test_discovery_keeps_a_recurring_series_between_events_within_the_lookback():
    closes = {"KXJOBLESSCLAIMS": "2026-11-19T13:29:00Z",   # settled today, next not listed
              "KXGDP": "2026-08-01T12:30:00Z",             # 110 days: a quarterly gap
              "KXCPIOLD": "2023-12-12T13:30:00Z",          # dead for years
              "KXFEDCUTONCE": "2026-11-10T19:00:00Z"}      # one_off: never lists again
    picked = m.select_kalshi_series(_BETWEEN, {"KXCPI": 2}, closes, now=_NOW)
    assert sorted(picked["ticker"]) == ["KXCPI", "KXGDP", "KXJOBLESSCLAIMS"]
    row = picked.set_index("ticker").loc["KXJOBLESSCLAIMS"]
    assert row["n_open_events"] == 0 and row["last_close"] == "2026-11-19T13:29:00Z"
    # inside the window it stays, past it it is dropped
    edge = _NOW + pd.Timedelta(days=m.KALSHI_DISCOVERY_LOOKBACK_DAYS - 1)
    late = m.select_kalshi_series(_BETWEEN, {"KXCPI": 2}, closes, now=edge)
    assert "KXJOBLESSCLAIMS" in set(late["ticker"]) and "KXGDP" not in set(late["ticker"])
    gone = m.select_kalshi_series(_BETWEEN, {"KXCPI": 2}, closes,
                                  now=edge + pd.Timedelta(days=2))
    assert sorted(gone["ticker"]) == ["KXCPI"]


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

    recent = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")

    def router(url: str):
        path, q = urlparse(url).path, _q(url)
        if path.endswith("/series"):
            return series_page
        if path.endswith("/events") and "series_ticker" in q:      # the between-events lookup
            assert q["status"] == "settled" and q["series_ticker"] == "KXCPIOLD"
            return {"events": [{"event_ticker": "KXCPIOLD-26NOV", "markets": [
                {"ticker": "KXCPIOLD-26NOV-T0.1", "close_time": recent}]}]}
        if path.endswith("/events"):
            return pages[q.get("cursor")]
        raise AssertionError(f"unexpected request {url}")

    seen = _serve(monkeypatch, router)
    out = sandbox / "cfg.json"
    msg = m.discover_kalshi_series(out)
    assert "wrote 11 series" in msg and "1 kept between events" in msg
    doc = json.loads(out.read_text())
    assert doc["selector"] == "series_v1" and doc["discovered"] == m.SNAP_DATE
    assert sorted(r["ticker"] for r in doc["series"]) == sorted(_KEPT + ["KXCPIOLD"])
    for r in doc["series"]:
        assert {"ticker", "title", "category", "frequency", "discovered"} <= set(r)
        assert r["discovered"] == m.SNAP_DATE
    # exactly one settled-event lookup: only the recurring candidate with no open event
    assert sum("series_ticker" in _q(u) for u, _ in seen) == 1
    assert seen and all("@" not in ua for _, ua in seen)


def test_the_lookback_reads_the_historical_api_when_the_settled_event_lists_nothing(
        monkeypatch, sandbox):
    """An event settled before /historical/cutoff lists 0 nested markets on the live API;
    without the historical read the 120-day lookback acts as ~61 days."""
    def router(url: str):
        path, q = urlparse(url).path, _q(url)
        if path.endswith("/historical/markets"):
            assert q["event_ticker"] == "KXNGDPQ-26Q2"
            return {"markets": [{"ticker": "KXNGDPQ-26Q2-T5", "close_time": "2026-08-28T12:30:00Z"},
                                {"ticker": "KXNGDPQ-26Q2-T6", "close_time": "2026-08-28T12:30:00Z"}],
                    "cursor": ""}
        if path.endswith("/events"):
            return {"events": [{"event_ticker": "KXNGDPQ-26Q2", "markets": []}]}
        raise AssertionError(url)

    seen = _serve(monkeypatch, router)
    budget = m._RequestBudget(10, m.time.monotonic() + 60)
    assert m._last_settled_close("KXNGDPQ", budget) == "2026-08-28T12:30:00Z"
    assert len(seen) == 2 and budget.used == 2
    picked = m.select_kalshi_series(
        [_series("KXNGDPQ", "Nominal GDP growth (quarterly)", "Economics", "quarterly", ["GDP"])],
        {}, {"KXNGDPQ": "2026-08-28T12:30:00Z"}, now=_NOW)          # 83 days: inside 120
    assert list(picked["ticker"]) == ["KXNGDPQ"]


def test_discover_fails_closed_when_the_lookback_lookups_fail(monkeypatch, sandbox):
    out = sandbox / "cfg.json"
    out.write_text('{"series": [{"ticker": "KXCPI"}]}')

    def router(url: str):
        path, q = urlparse(url).path, _q(url)
        if path.endswith("/series"):
            return {"series": _BETWEEN}
        if "series_ticker" in q:
            return urllib.error.HTTPError(url, 503, "down", {}, None)
        return {"events": [{"series_ticker": "KXCPI"}], "cursor": ""}

    _serve(monkeypatch, router)
    msg = m.discover_kalshi_series(out)
    assert "FAILED" in msg and "lookups errored" in msg
    assert json.loads(out.read_text()) == {"series": [{"ticker": "KXCPI"}]}


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
    assert msg.startswith("kalshi: FAILED") and msg.endswith("LOUD")
    assert len(pd.read_parquet(sandbox / "kalshi_snapshots.parquet")) == 2   # hoarded


def _n_series_config(n: int) -> list[str]:
    tickers = [f"KXS{i:02d}" for i in range(n)]
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": t, "category": "Economics"}
                                           for t in tickers])
    return tickers


def test_a_mass_error_day_keeps_its_rows_but_fails_loud(monkeypatch, sandbox):
    """The reviewer's case: 49 of 50 series answer 503 -> FAILED, the 1 real row is kept."""
    tickers = _n_series_config(50)

    def router(url: str):
        t = _q(url)["series_ticker"]
        if t == tickers[0]:
            return {"markets": [_mkt(f"{t}-1")], "cursor": ""}
        return urllib.error.HTTPError(url, 503, "down", {}, None)

    _serve(monkeypatch, router)
    msg = m.snapshot_kalshi()
    assert msg.startswith("kalshi: FAILED — PARTIAL day") and "1/50 series" in msg
    assert "49 errors" in msg and msg.endswith("LOUD")
    assert len(pd.read_parquet(sandbox / "kalshi_snapshots.parquet")) == 1
    assert m._daily_rc([msg]) == 1


@pytest.mark.parametrize("n_ok,failed", [(10, False), (9, False), (8, True)])
def test_the_completion_threshold_is_ninety_percent(monkeypatch, sandbox, n_ok, failed):
    tickers = _n_series_config(10)

    def router(url: str):
        t = _q(url)["series_ticker"]
        if tickers.index(t) < n_ok:
            return {"markets": [_mkt(f"{t}-1")], "cursor": ""}
        return urllib.error.HTTPError(url, 503, "down", {}, None)

    _serve(monkeypatch, router)
    assert ("FAILED" in m.snapshot_kalshi()) is failed


def test_a_listed_series_with_no_open_market_is_a_successful_empty_pull(monkeypatch, sandbox):
    tickers = _n_series_config(3)
    _serve(monkeypatch, _by_series({tickers[0]: [_mkt(f"{tickers[0]}-1")]}))  # 2 empty
    msg = m.snapshot_kalshi()
    assert msg.startswith("kalshi: snapped 1 markets") and "3/3 series, 0 errors" in msg


def test_markets_without_a_ticker_are_dropped_and_counted(monkeypatch, sandbox):
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": "KXCPI", "category": "Economics"}])
    no_id, blank = _mkt("KXCPI-2"), _mkt("KXCPI-3")
    no_id["ticker"], blank["ticker"] = None, "  "
    _serve(monkeypatch, _by_series({"KXCPI": [_mkt("KXCPI-1"), no_id, blank]}))
    msg = m.snapshot_kalshi()
    assert "snapped 1 markets" in msg and "'no ticker': 2" in msg
    df = pd.read_parquet(sandbox / "kalshi_snapshots.parquet")
    assert list(df["ticker"]) == ["KXCPI-1"]


def test_one_endless_cursor_cannot_spend_the_request_budget(monkeypatch, sandbox):
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": t, "category": "Economics"}
                                           for t in ("KXLOOP", "KXCPI")])
    monkeypatch.setattr(m, "KALSHI_WORKERS", 1)

    def router(url: str):
        t = _q(url)["series_ticker"]
        if t == "KXLOOP":
            n = int(_q(url).get("cursor", "0"))
            return {"markets": [_mkt(f"KXLOOP-{n}")], "cursor": str(n + 1)}     # never ends
        return {"markets": [_mkt("KXCPI-1")], "cursor": ""}

    seen = _serve(monkeypatch, router)
    msg = m.snapshot_kalshi()
    assert sum(_q(u)["series_ticker"] == "KXLOOP" for u, _ in seen) == m.KALSHI_MAX_PAGES_PER_SERIES
    assert any(_q(u)["series_ticker"] == "KXCPI" for u, _ in seen)
    assert "'page cap': 1" in msg


@pytest.mark.parametrize("field,value", [("yes_bid_dollars", "41.0000"),
                                         ("yes_ask_dollars", "43.0000"),
                                         ("last_price_dollars", "-0.0100")])
def test_a_price_outside_zero_one_fails_the_day_closed(monkeypatch, sandbox, field, value):
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": "KXCPI", "category": "Economics"}])
    _serve(monkeypatch, _by_series({"KXCPI": [_mkt("KXCPI-1"), _mkt("KXCPI-2", **{field: value})]}))
    msg = m.snapshot_kalshi()
    assert "FAILED" in msg and "outside [0, 1]" in msg and "nothing written" in msg
    assert not (sandbox / "kalshi_snapshots.parquet").exists()


def test_a_mostly_unquoted_day_fails_closed(monkeypatch, sandbox):
    _write_config(m.KALSHI_SERIES_CONFIG, [{"ticker": "KXCPI", "category": "Economics"}])
    empty = {"bid": "0.0000", "ask": "1.0000", "last": "0.0000"}
    _serve(monkeypatch, _by_series({"KXCPI": [_mkt("KXCPI-1"), _mkt("KXCPI-2", **empty),
                                              _mkt("KXCPI-3", **empty)]}))
    msg = m.snapshot_kalshi()
    assert "FAILED" in msg and "only 1 of 3" in msg and "nothing written" in msg
    assert not (sandbox / "kalshi_snapshots.parquet").exists()


@pytest.mark.parametrize("age_days,warn", [(0, False), (60, False), (61, True)])
def test_the_line_names_the_list_date_and_warns_when_stale(monkeypatch, sandbox, age_days,
                                                           warn):
    discovered = (pd.Timestamp(m.SNAP_DATE) - pd.Timedelta(days=age_days)).strftime("%Y-%m-%d")
    m.KALSHI_SERIES_CONFIG.write_text(json.dumps({
        "discovered": discovered, "series": [{"ticker": "KXCPI", "category": "Economics"}]}))
    _serve(monkeypatch, _by_series({"KXCPI": [_mkt("KXCPI-1")]}))
    msg = m.snapshot_kalshi()
    assert f"series list discovered {discovered}" in msg and ("WARN" in msg) is warn
    assert msg.startswith("kalshi: snapped")                 # a WARN is not a FAILED


def test_main_exits_nonzero_only_on_the_gated_failed_lines(monkeypatch, sandbox):
    pulls = ("pull_gpr", "pull_epu", "snapshot_polymarket", "snapshot_kalshi",
             "resolve_polymarket_snapshots", "resolve_kalshi_snapshots", "snapshot_kxfed",
             "pull_fred_rate_path", "snapshot_cef", "pull_form4_index", "pull_usaspending",
             "pull_credit_spread_oas")
    for name in pulls:
        monkeypatch.setattr(m, name, lambda n=name: f"{n}: ok")
    assert m.main(["--out-dir", str(sandbox)]) == 0
    monkeypatch.setattr(m, "pull_gpr", lambda: "gpr: gpr_daily FAILED (no variant reachable)")
    assert m.main(["--out-dir", str(sandbox)]) == 0       # verifier/cadence-gated feeds: rc 0
    for name, line in [("snapshot_kalshi", "kalshi: FAILED — PARTIAL day, x — LOUD"),
                       ("resolve_kalshi_snapshots", "kalshi_resolve: FAILED (OSError: x) — LOUD"),
                       ("resolve_polymarket_snapshots",
                        "polymarket_resolve: FAILED (ArrowInvalid: x) — LOUD")]:
        monkeypatch.setattr(m, name, lambda line=line: line)
        assert m.main(["--out-dir", str(sandbox)]) == 1, name
        monkeypatch.setattr(m, name, lambda n=name: f"{n}: ok")


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


def _not_found(url: str = "u") -> urllib.error.HTTPError:
    return urllib.error.HTTPError(url, 404, "Not Found", {}, None)


def _event_router(events: dict[str, list[dict] | Exception],
                  markets: dict[str, dict | Exception] | None = None,
                  hist_events: dict[str, list[dict] | Exception] | None = None,
                  hist_markets: dict[str, dict | Exception] | None = None):
    """Live: /events/{ev} -> events[ev]; /markets/{t} -> markets[t].
    Historical (as the real API behaves): /historical/markets?event_ticker=E -> hist_events[E]
    or an EMPTY 200; /historical/markets/{t} -> hist_markets[t] or a 404."""
    def router(url: str):
        path, q = urlparse(url).path, _q(url)
        key = path.rsplit("/", 1)[1]
        if "/historical/markets" in path:
            if path.endswith("/historical/markets"):
                out = (hist_events or {}).get(q.get("event_ticker", ""), [])
                return out if isinstance(out, Exception) else {"markets": out, "cursor": ""}
            out = (hist_markets or {}).get(key, _not_found(url))
            return out if isinstance(out, Exception) else {"market": out}
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


def _live_market_calls(seen: list[tuple[str, str]]) -> int:
    return sum("/markets/" in u and "/historical/" not in u for u, _ in seen)


def test_an_event_404_sends_its_tickers_to_the_single_market_lookup(monkeypatch, sandbox):
    """One 404 on /events/{ev} is not authoritative per market; only a 404 from the live
    AND the historical single-market endpoints is."""
    pd.DataFrame([_v1("KXA-1-T1", "KXA-1"), _v1("KXA-1-T2", "KXA-1"),
                  _v1("KXA-1-T3", "KXA-1")]).to_parquet(
        sandbox / "kalshi_snapshots.parquet", index=False)
    gone = _not_found()
    markets: dict[str, dict | Exception] = {
        "KXA-1-T1": gone, "KXA-1-T2": _settled("KXA-1-T2", "KXA-1", "yes"),
        "KXA-1-T3": urllib.error.HTTPError("u", 503, "down", {}, None)}
    seen = _serve(monkeypatch, _event_router({"KXA-1": gone}, markets))
    m.resolve_kalshi_snapshots()
    res = _resolutions(sandbox)
    assert sorted(res.index) == ["KXA-1-T1", "KXA-1-T2"]        # T3 errored: still pending
    assert res.loc["KXA-1-T1", "status"] == "not_found" and bool(res.loc["KXA-1-T1", "final"])
    assert res.loc["KXA-1-T1", "resolved_via"] == "market+historical"
    assert res.loc["KXA-1-T2", "result"] == "yes" and res.loc["KXA-1-T2", "resolved_via"] == "market"
    assert _live_market_calls(seen) == 3


def test_a_market_moved_to_the_historical_api_is_resolved_not_called_gone(monkeypatch, sandbox):
    """The reviewer's case: KXCPI-26AUG settled before /historical/cutoff. The live event
    lists 0 markets and /markets/{t} 404s; /historical/markets has the outcome."""
    pd.DataFrame([_v1("KXCPI-26AUG-T-0.4", "KXCPI-26AUG", close="2026-09-11T12:25:00Z"),
                  _v1("KXCPI-26AUG-T0.5", "KXCPI-26AUG", close="2026-09-11T12:25:00Z")]
                 ).to_parquet(sandbox / "kalshi_snapshots.parquet", index=False)
    hist = [dict(_settled("KXCPI-26AUG-T-0.4", "KXCPI-26AUG", "yes"), expiration_value="0.4"),
            dict(_settled("KXCPI-26AUG-T0.5", "KXCPI-26AUG", "no"), expiration_value="0.4")]
    seen = _serve(monkeypatch, _event_router(
        {"KXCPI-26AUG": []}, {"KXCPI-26AUG-T-0.4": _not_found(), "KXCPI-26AUG-T0.5": _not_found()},
        hist_events={"KXCPI-26AUG": hist}))
    msg = m.resolve_kalshi_snapshots()
    res = _resolutions(sandbox)
    assert set(res["resolved_via"]) == {"historical"} and res["final"].all()
    assert res.loc["KXCPI-26AUG-T-0.4", "result"] == "yes"
    assert res.loc["KXCPI-26AUG-T-0.4", "settlement_value"] == pytest.approx(1.0)
    assert res.loc["KXCPI-26AUG-T-0.4", "expiration_value"] == pytest.approx(0.4)
    assert "not_found" not in set(res["status"])
    assert len(seen) == 2 and _live_market_calls(seen) == 0       # 1 live + 1 historical GET
    assert "2 from the historical API" in msg


def test_a_live_404_market_is_looked_up_in_the_historical_api_before_gone(monkeypatch, sandbox):
    pd.DataFrame([_v1("KXE-1-T1", "KXE-1"), _v1("KXE-1-T2", "KXE-1"), _v1("KXE-1-T3", "KXE-1")]
                 ).to_parquet(sandbox / "kalshi_snapshots.parquet", index=False)
    seen = _serve(monkeypatch, _event_router(
        {"KXE-1": []},                                     # live listing: none of ours
        {t: _not_found() for t in ("KXE-1-T1", "KXE-1-T2", "KXE-1-T3")},
        hist_events={},                                    # the historical event listing too
        hist_markets={"KXE-1-T1": _settled("KXE-1-T1", "KXE-1", "yes"),   # but by ticker: yes
                      "KXE-1-T3": urllib.error.HTTPError("u", 503, "down", {}, None)}))
    m.resolve_kalshi_snapshots()
    res = _resolutions(sandbox)
    assert res.loc["KXE-1-T1", "resolved_via"] == "historical" and bool(res.loc["KXE-1-T1", "final"])
    assert res.loc["KXE-1-T2", "status"] == "not_found"          # both APIs 404: gone
    assert res.loc["KXE-1-T2", "resolved_via"] == "market+historical"
    assert "KXE-1-T3" not in res.index                            # historical errored: pending
    assert sum("/historical/markets/" in u for u, _ in seen) == 3


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
    assert "2 missing from their live event" in msg and "2 single-market lookups" in msg
    assert "1 errors" in msg and _live_market_calls(seen) == 2

    # next run: T3 is still pending, so its event is asked again and T3 again alone; live and
    # historical both 404 now, so it is gone
    seen.clear()
    markets["KXB-1-T3"] = _not_found()
    m.resolve_kalshi_snapshots()
    res = _resolutions(sandbox)
    assert res.loc["KXB-1-T3", "status"] == "not_found" and bool(res.loc["KXB-1-T3", "final"])
    assert [urlparse(u).path.split("/v2", 1)[1] for u, _ in seen] == [
        "/events/KXB-1", "/historical/markets", "/markets/KXB-1-T3",
        "/historical/markets/KXB-1-T3"]


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


def test_the_polymarket_resolver_never_raises(monkeypatch, sandbox):
    (sandbox / "polymarket_snapshots.parquet").write_bytes(b"not a parquet file")
    msg = m.resolve_polymarket_snapshots()
    assert msg.startswith("polymarket_resolve: FAILED") and m._daily_rc([msg]) == 1


def _write_resolutions(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_parquet(path, index=False)


def test_new_events_go_before_re_asks_so_re_asks_cannot_starve_them(monkeypatch, sandbox):
    pd.DataFrame([_v1("KXOLD-1-T1", "KXOLD-1", close="2026-11-10T21:00:00Z"),
                  _v1("KXNEW-1-T1", "KXNEW-1", close="2026-11-18T21:00:00Z")]).to_parquet(
        sandbox / "kalshi_snapshots.parquet", index=False)
    yesterday = (pd.Timestamp(m.SNAP_DATE) - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    _write_resolutions(sandbox / "kalshi_resolutions.parquet", [
        {"ticker": "KXOLD-1-T1", "status": "closed", "result": "", "final": False,
         "looked_up": yesterday}])
    monkeypatch.setattr(m, "MAX_RESOLVE_EVENTS_PER_RUN", 1)
    seen = _serve(monkeypatch, _event_router({
        "KXNEW-1": [_settled("KXNEW-1-T1", "KXNEW-1")],
        "KXOLD-1": [_settled("KXOLD-1-T1", "KXOLD-1", result="", status="closed")]}))
    m.resolve_kalshi_snapshots()
    assert [urlparse(u).path.rsplit("/", 1)[1] for u, _ in seen] == ["KXNEW-1"]


@pytest.mark.parametrize("asked_days_ago,asked", [(2, False), (8, True)])
def test_a_stale_non_final_event_is_re_asked_only_weekly(monkeypatch, sandbox, asked_days_ago,
                                                         asked):
    close = (pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=m.KALSHI_STALE_REASK_DAYS + 5))
    pd.DataFrame([_v1("KXSTALE-1-T1", "KXSTALE-1", close=close.strftime("%Y-%m-%dT%H:%M:%SZ"))]
                 ).to_parquet(sandbox / "kalshi_snapshots.parquet", index=False)
    last = (pd.Timestamp(m.SNAP_DATE) - pd.Timedelta(days=asked_days_ago)).strftime("%Y-%m-%d")
    _write_resolutions(sandbox / "kalshi_resolutions.parquet", [
        {"ticker": "KXSTALE-1-T1", "status": "closed", "result": "", "final": False,
         "looked_up": last}])
    seen = _serve(monkeypatch, _event_router({
        "KXSTALE-1": [_settled("KXSTALE-1-T1", "KXSTALE-1", result="", status="closed")]}))
    msg = m.resolve_kalshi_snapshots()
    assert bool(seen) is asked
    if not asked:
        assert "held to a weekly re-ask" in msg
    res = pd.read_parquet(sandbox / "kalshi_resolutions.parquet")
    assert not res["final"].any()                         # never marked final when it is not


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
