"""T-321 — tests for the agentic analyst's read-only store-readers.

Proves the four invariants the tool surface relies on:
  (a) fail-closed to [] when a store is absent (root = empty tmp dir);
  (b) PIT guard — a record dated on-or-after as_of is excluded;
  (c) the factory returns exactly the six expected reader keys;
  (d) row caps hold (a store with > MAX_ROWS PIT-valid rows is capped).
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd
import pytest

from intelligence.analyst.agentic_readers import MAX_ROWS, build_readers

AS_OF = "2024-01-10"
EXPECTED_KEYS = {
    "query_news", "query_prices", "query_rate_path",
    "query_events", "query_own_notes", "query_resolved_predictions",
}


# ── fixtures: tiny on-disk stores under a tmp root ──────────────────────────────
def _write_news(root: Path, rows: list[dict]) -> None:
    d = root / "data" / "intel" / "news_panel"
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(d / "news_202401.parquet", index=False)


def _write_prices(root: Path, ticker: str, rows: list[dict]) -> None:
    d = root / "data" / "processed" / "tr_reconciled"
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(d / f"{ticker}_1d.csv", index=False)


def _write_rate_path(root: Path, rows: list[dict]) -> None:
    d = root / "data" / "macro_data" / "alt"
    d.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(d / "fred_rate_path.parquet", index=False)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


# ── (c) factory returns exactly the six keys ────────────────────────────────────
def test_factory_returns_exactly_six_keys(tmp_path: Path) -> None:
    readers = build_readers(tmp_path, AS_OF)
    assert set(readers) == EXPECTED_KEYS
    assert all(callable(fn) for fn in readers.values())


# ── (a) fail-closed to [] when every store is absent ────────────────────────────
def test_all_readers_fail_closed_on_empty_root(tmp_path: Path) -> None:
    readers = build_readers(tmp_path, AS_OF)
    assert readers["query_news"]({"ticker": "AAPL"}) == []
    assert readers["query_prices"]({"ticker": "SPY"}) == []
    assert readers["query_rate_path"]({}) == []
    assert readers["query_events"]({}) == []
    assert readers["query_own_notes"]({}) == []
    assert readers["query_resolved_predictions"]({}) == []


def test_readers_never_raise_on_garbage_input(tmp_path: Path) -> None:
    readers = build_readers(tmp_path, AS_OF)
    # missing/blank required args and unparseable dates must not raise
    assert readers["query_news"]({}) == []
    assert readers["query_prices"]({"ticker": ""}) == []
    assert readers["query_news"]({"ticker": "AAPL", "date_from": "not-a-date"}) == []


# ── (b) PIT guard: news (created_at strictly < as_of) ───────────────────────────
def test_query_news_pit_excludes_on_or_after_as_of(tmp_path: Path) -> None:
    _write_news(tmp_path, [
        {"created_at": pd.Timestamp("2024-01-05T14:00:00Z"),
         "symbols": ["AAPL"], "headline": "before", "content": "past article"},
        {"created_at": pd.Timestamp("2024-01-15T14:00:00Z"),
         "symbols": ["AAPL"], "headline": "after", "content": "future leak"},
        # exactly at midnight of as_of — must be excluded (strict <)
        {"created_at": pd.Timestamp("2024-01-10T00:00:00Z"),
         "symbols": ["AAPL"], "headline": "boundary", "content": "same day"},
    ])
    out = build_readers(tmp_path, AS_OF)["query_news"]({"ticker": "AAPL"})
    heads = {r["headline"] for r in out}
    assert heads == {"before"}


def test_query_news_ticker_and_date_filters(tmp_path: Path) -> None:
    _write_news(tmp_path, [
        {"created_at": pd.Timestamp("2024-01-03T10:00:00Z"),
         "symbols": ["AAPL"], "headline": "aapl-jan3", "content": "x"},
        {"created_at": pd.Timestamp("2024-01-06T10:00:00Z"),
         "symbols": ["MSFT"], "headline": "msft-jan6", "content": "x"},
        {"created_at": pd.Timestamp("2024-01-08T10:00:00Z"),
         "symbols": ["AAPL", "MSFT"], "headline": "aapl-jan8", "content": "x"},
    ])
    readers = build_readers(tmp_path, AS_OF)
    aapl = {r["headline"] for r in readers["query_news"]({"ticker": "aapl"})}
    assert aapl == {"aapl-jan3", "aapl-jan8"}
    ranged = {r["headline"] for r in
              readers["query_news"]({"ticker": "AAPL", "date_from": "2024-01-05"})}
    assert ranged == {"aapl-jan8"}


# ── (b) PIT guard: prices (date ≤ as_of) ────────────────────────────────────────
def test_query_prices_pit_and_shape(tmp_path: Path) -> None:
    _write_prices(tmp_path, "SPY", [
        {"Date": "2024-01-08", "Close": 470.5},
        {"Date": "2024-01-10", "Close": 472.0},   # == as_of: allowed (≤)
        {"Date": "2024-01-12", "Close": 999.0},   # > as_of: excluded
    ])
    out = build_readers(tmp_path, AS_OF)["query_prices"]({"ticker": "SPY"})
    dates = [r["date"] for r in out]
    assert dates == ["2024-01-08", "2024-01-10"]
    assert out[-1] == {"date": "2024-01-10", "close": 472.0}


# ── (b) PIT guard + wide pivot: rate path ───────────────────────────────────────
def test_query_rate_path_pivot_and_pit(tmp_path: Path) -> None:
    _write_rate_path(tmp_path, [
        {"series": "DFEDTARL", "observation_date": "2024-01-05", "value": 5.25},
        {"series": "DFEDTARU", "observation_date": "2024-01-05", "value": 5.50},
        {"series": "EFFR", "observation_date": "2024-01-05", "value": 5.33},
        {"series": "EFFR", "observation_date": "2024-01-20", "value": 9.99},  # future
    ])
    out = build_readers(tmp_path, AS_OF)["query_rate_path"]({})
    assert len(out) == 1
    assert out[0] == {"date": "2024-01-05", "DFEDTARL": 5.25,
                      "DFEDTARU": 5.50, "EFFR": 5.33}


# ── (b) PIT + symbol filter: events ─────────────────────────────────────────────
def test_query_events_pit_and_symbol_filter(tmp_path: Path) -> None:
    ledger = tmp_path / "data" / "intel" / "event_calls.jsonl"
    _write_jsonl(ledger, [
        {"note_date": "2024-01-04", "symbol": "AAPL",
         "event_call": {"event_type": "buyback", "materiality": "high",
                        "direction": "up", "document_ref": "d1"}},
        {"note_date": "2024-01-06", "symbol": "MSFT",
         "event_call": {"event_type": "8-K", "direction": "down", "document_ref": "d2"}},
        {"note_date": "2024-01-20", "symbol": "AAPL",
         "event_call": {"event_type": "future", "document_ref": "d3"}},  # > as_of
    ])
    readers = build_readers(tmp_path, AS_OF)
    allev = readers["query_events"]({})
    assert {e["document_ref"] for e in allev} == {"d1", "d2"}
    aapl = readers["query_events"]({"symbol": "AAPL"})
    assert {e["document_ref"] for e in aapl} == {"d1"}


# ── (b) PIT: own notes ──────────────────────────────────────────────────────────
def test_query_own_notes_pit(tmp_path: Path) -> None:
    d = tmp_path / "data" / "intel" / "analyst_notes_agentic"
    d.mkdir(parents=True, exist_ok=True)
    (d / "note_a.json").write_text(json.dumps({
        "as_of": "2024-01-07", "market_assessment": "cautious",
        "predictions": [{"statement": "SPY up", "probability": 0.6, "horizon": "5d"}]}))
    (d / "note_b.json").write_text(json.dumps({
        "as_of": "2024-01-20", "market_assessment": "future note", "predictions": []}))
    out = build_readers(tmp_path, AS_OF)["query_own_notes"]({})
    assert [n["as_of"] for n in out] == ["2024-01-07"]
    assert out[0]["predictions"][0]["statement"] == "SPY up"


# ── (b) PIT + brier: resolved predictions ───────────────────────────────────────
def test_query_resolved_predictions_pit_and_brier(tmp_path: Path) -> None:
    log = tmp_path / "data" / "intel" / "analyst_predictions.jsonl"
    _write_jsonl(log, [
        {"statement": "SPY above 470", "probability": 0.75, "outcome": 1,
         "resolvable": True, "resolved_at": "2024-01-08", "resolve_date": "2024-01-08"},
        {"statement": "unresolvable", "probability": 0.5, "outcome": None,
         "resolvable": False, "resolved_at": "2024-01-08"},   # not scored
        {"statement": "future", "probability": 0.5, "outcome": 0,
         "resolvable": True, "resolved_at": "2024-01-20"},     # > as_of
    ])
    out = build_readers(tmp_path, AS_OF)["query_resolved_predictions"]({})
    assert len(out) == 1
    assert out[0]["statement"] == "SPY above 470"
    assert out[0]["brier"] == pytest.approx(0.0625)   # (0.75 - 1)^2


# ── (d) row caps hold ───────────────────────────────────────────────────────────
def test_query_news_row_cap(tmp_path: Path) -> None:
    base = dt.date(2023, 6, 1)
    rows = [{"created_at": pd.Timestamp(base + dt.timedelta(days=i), tz="UTC"),
             "symbols": ["AAPL"], "headline": f"h{i}", "content": "x"}
            for i in range(MAX_ROWS + 20)]
    _write_news(tmp_path, rows)
    out = build_readers(tmp_path, AS_OF)["query_news"]({"ticker": "AAPL"})
    assert len(out) == MAX_ROWS


def test_query_events_row_cap_and_limit_clamp(tmp_path: Path) -> None:
    ledger = tmp_path / "data" / "intel" / "event_calls.jsonl"
    _write_jsonl(ledger, [
        {"note_date": "2023-06-01", "symbol": "AAPL",
         "event_call": {"event_type": "e", "document_ref": f"d{i}"}}
        for i in range(MAX_ROWS + 20)
    ])
    readers = build_readers(tmp_path, AS_OF)
    assert len(readers["query_events"]({})) == MAX_ROWS
    # a model-supplied limit above the cap is clamped to MAX_ROWS
    assert len(readers["query_events"]({"limit": 9999})) == MAX_ROWS
    assert len(readers["query_events"]({"limit": 5})) == 5
