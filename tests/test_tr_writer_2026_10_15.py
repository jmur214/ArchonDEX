"""The total-return writer and the guard primitives (Agent R's §5 locks 1, 3, 4, 5, 6; C-1..C-4).

Fake providers only — no network. Lock 2 (a real XOM re-fetch on a COPY reproduces the ex-date
steps) and lock 7 (the data lock + B-1 panel md5 after the first full pass) are proof runs on a
copy, reported separately: they need the provider and the real cache, and must never write it.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.data_manager import tr_writer as w

IDX = pd.bdate_range("2018-01-02", "2025-12-31")
QUARTERLY_EXDATES = pd.DatetimeIndex([d for d in IDX if d.month in (2, 5, 8, 11) and d.day >= 10]
                                      ).to_series().groupby(lambda d: (d.year, d.month)).first().values


def _raw(price0: float = 100.0, idx=IDX) -> pd.Series:
    """Split-adjusted, dividend-UNadjusted closes (price-only)."""
    return pd.Series(price0 * (1.0002 ** np.arange(len(idx))), index=idx)


def _tr(raw: pd.Series, div_yield_q: float = 0.009, exdates=QUARTERLY_EXDATES) -> pd.Series:
    """Total-return back-adjustment: every bar BEFORE an ex-date is scaled down by (1 - d/P)."""
    factor = pd.Series(1.0, index=raw.index)
    for d in pd.DatetimeIndex(exdates):
        factor[raw.index < d] *= (1.0 - div_yield_q)
    return raw * factor


def _ohlcv(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99,
                         "Close": close, "Volume": 1e6}, index=close.index)


def _seed_cache(cache_dir: Path, ohlcv: pd.DataFrame, ticker: str = "ABC") -> None:
    w.write_pair_atomically(w.with_derived_columns(ohlcv), cache_dir / "parquet" / f"{ticker}_1d.parquet",
                            cache_dir / f"{ticker}_1d.csv")


CACHE_END = pd.Timestamp("2025-09-30")


def NO_ACTIONS(symbol):
    """An empty corporate-actions record: no splits or dividends after the cache's last bar."""
    return pd.DataFrame(columns=["Dividends", "Stock Splits"], dtype=float)


def _tr_cache_as_of(end: pd.Timestamp = CACHE_END, exdates=QUARTERLY_EXDATES) -> pd.DataFrame:
    """The cache as a total-return fetch made on `end` wrote it: only the ex-dates up to `end` are
    applied. A re-fetch after a later ex-date reads it as a constant RESCALE — the steady state."""
    raw = _raw()
    raw = raw[raw.index <= end]
    return _ohlcv(_tr(raw, exdates=[d for d in pd.DatetimeIndex(exdates) if d <= end]))


# ── one provider for the universe, and the span (lock 3) ────────────────────────

def test_ONE_provider_for_the_whole_universe_even_for_a_post_2016_file(tmp_path):
    """The per-span rule sent 2016+ files to Alpaca, whose IEX history starts 2020-07-27: 69 of the
    103 that returned could not cover the cache. A 2018-start file comes from the universe provider."""
    _seed_cache(tmp_path, _tr_cache_as_of())

    def per_file_alpaca(*a):
        raise AssertionError("the writer consulted a per-file provider")
    calls = []
    rec = w.full_refetch("ABC", tmp_path, {"alpaca": per_file_alpaca, "yfinance": _fake(IDX[0], calls)},
                         today=IDX[-1], write=False, actions=NO_ACTIONS)
    assert rec.provider == "yfinance" and calls


def test_a_providers_map_without_the_universe_provider_is_REFUSED(tmp_path):
    _seed_cache(tmp_path, _tr_cache_as_of())
    with pytest.raises(w.WriterRefusal, match="no yfinance provider"):
        w.full_refetch("ABC", tmp_path, {"alpaca": _fake(IDX[0], [])}, today=IDX[-1], write=False, actions=NO_ACTIONS)


def test_the_default_providers_name_only_the_universe_provider():
    assert w.UNIVERSE_PROVIDER == "yfinance"
    assert set(w.DEFAULT_PROVIDERS) == {w.UNIVERSE_PROVIDER}


def test_a_deep_file_refetched_from_a_2016_provider_is_REFUSED():
    cached = _ohlcv(_raw(idx=pd.bdate_range("1970-01-02", "2025-12-31")))
    from_2016 = _ohlcv(_raw(idx=pd.bdate_range("2016-01-04", "2025-12-31")))
    ok, why = w.covers_span(from_2016, cached)
    assert not ok and "cannot replace the file" in why


def test_covering_and_short_refetches():
    cached = _ohlcv(_raw())
    assert w.covers_span(_ohlcv(_raw()), cached)[0]
    short = _ohlcv(_raw(idx=IDX[:-10]))
    assert not w.covers_span(short, cached)[0]


# ── basis measured, not recorded (lock 5) ───────────────────────────────────────

def test_a_dividend_payer_measures_as_total_return():
    raw = _raw()
    win = raw.index >= raw.index[-63]
    b = w.measure_basis(_tr(raw)[win], raw[win])
    assert b["basis"] == "measured_tr" and b["n_steps"] >= 1


def test_no_ex_date_in_the_window_is_UNVERIFIED_not_assumed():
    raw = _raw()
    b = w.measure_basis(raw, raw)
    assert b["basis"] == "unverified: no ex-date in window"


def test_a_falling_ratio_is_anomalous():
    raw = _raw()
    bad = raw.copy()
    bad[bad.index >= raw.index[-30]] *= 0.95      # adjusted DROPS relative to unadjusted
    assert w.measure_basis(bad[-60:], raw[-60:])["basis"].startswith("anomalous")


# ── the overlap test at the rounding floor (locks 2-signature, 4) ───────────────

def test_same_convention_appends():
    tr = _tr(_raw())
    assert w.classify_overlap(tr[-40:], tr[-40:])["verdict"] == "APPEND"


def test_a_new_ex_date_after_the_window_reads_as_a_constant_RESCALE():
    """XOM's signature (R §2.1): a constant 0.9907 across the overlap."""
    tr = _tr(_raw())
    v = w.classify_overlap(tr[-40:], tr[-40:] * 0.9907)
    assert v["verdict"] == "RESCALED" and v["ratio"] == pytest.approx(0.9907, rel=1e-6)


def test_split_only_against_total_return_is_a_DIFFERENT_convention():
    raw = _raw()
    v = w.classify_overlap(raw[-120:], _tr(raw)[-120:])   # window spans an ex-date step
    assert v["verdict"] == "DIFFERENT_CONVENTION"


@pytest.mark.parametrize("price, step, expected", [
    (5.0, 0.000125, "APPEND"),                   # 0.0125% at $5: below the cent floor — accepted
    (170.0, 0.0013, "DIFFERENT_CONVENTION"),     # AAPL's 0.13% at $170: above it — refused
])
def test_tolerance_comes_from_the_rounding_floor(price, step, expected):
    idx = pd.bdate_range("2025-06-02", periods=40)
    cached = pd.Series(price, index=idx)
    fetched = cached.copy()
    fetched[idx >= idx[20]] *= (1 + step)
    assert w.classify_overlap(cached, fetched)["verdict"] == expected


# ── the seam rail catches what the overlap test cannot (lock 1) ─────────────────

def test_an_unadjusted_provider_across_a_split_passes_the_overlap_but_FAILS_the_seam():
    idx = pd.bdate_range("2025-01-02", periods=60)
    pre = pd.Series(150.0, index=idx[:40])
    overlap = w.classify_overlap(pre[-20:], pre[-20:])          # raw provider: pre-split matches
    assert overlap["verdict"] == "APPEND", "the overlap test is BLIND to this case, by design"
    ok, r = w.seam_return_ok(last_cached_close=150.0, first_new_close=50.0,
                             rescaled=overlap["verdict"] == "RESCALED")
    assert not ok and r == pytest.approx(-2 / 3)
    assert w.seam_return_ok(150.0, 50.0, rescaled=True)[0], "a reported rescale licenses the jump"


# ── atomic pair (lock 6) ────────────────────────────────────────────────────────

def test_a_failed_csv_write_leaves_BOTH_originals_untouched(tmp_path, monkeypatch):
    pq, csv = tmp_path / "parquet" / "X_1d.parquet", tmp_path / "X_1d.csv"
    w.write_pair_atomically(w.with_derived_columns(_ohlcv(_raw())), pq, csv)
    before = (pq.read_bytes(), csv.read_bytes())

    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr(pd.DataFrame, "to_csv", boom)
    with pytest.raises(OSError):
        w.write_pair_atomically(w.with_derived_columns(_ohlcv(_raw(200.0))), pq, csv)
    assert (pq.read_bytes(), csv.read_bytes()) == before
    assert not list(tmp_path.rglob("*.writing")), "no temp file may survive a failed write"


def test_the_derived_columns_match_the_project_convention():
    from scripts.merge_stooq_alpaca_substrate import _recompute_derived
    o = _ohlcv(_raw())
    mine = w.with_derived_columns(o)
    theirs = _recompute_derived(o.rename_axis("Date").reset_index()).set_index("Date")
    pd.testing.assert_frame_equal(mine[["ATR", "PrevClose"]], theirs[["ATR", "PrevClose"]],
                                  check_names=False, check_freq=False)


# ── the writer end to end, on a temp copy ───────────────────────────────────────

def _fake(provider_start: pd.Timestamp, calls: list):
    raw = _raw()

    def provider(ticker, start, end, adjusted):
        calls.append((ticker, str(pd.Timestamp(start).date()), adjusted))
        s = (_tr(raw) if adjusted else raw)
        s = s[(s.index >= max(pd.Timestamp(start), provider_start)) & (s.index <= end)]
        return _ohlcv(s)
    return provider


def test_full_refetch_writes_a_measured_total_return_pair_and_logs_the_mode(tmp_path):
    """The steady state: an ex-date (2025-11-10) since the cache was written rescales its past."""
    _seed_cache(tmp_path, _tr_cache_as_of())
    calls, log = [], tmp_path / "write_log.jsonl"
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _fake(IDX[0], calls)},
                         today=IDX[-1], log_path=log, actions=NO_ACTIONS)
    assert rec.provider == "yfinance" and rec.mode == "adjusted" and rec.basis == "measured_tr"
    assert rec.overlap["verdict"] == "RESCALED" and rec.overlap["ratio"] == pytest.approx(1 - 0.009, rel=1e-6)
    written = pd.read_parquet(tmp_path / "parquet" / "ABC_1d.parquet")
    assert written["Close"].iloc[0] < _raw().iloc[0], "total return: the past is scaled down"
    assert '"mode": "adjusted"' in log.read_text() and '"verdict": "RESCALED"' in log.read_text()
    assert [c[2] for c in calls] == [True, False, False], \
        "adjusted span + the two-mode basis tail + the LEVEL rail's unadjusted read at the cache's last bar"


def test_full_refetch_REFUSES_a_provider_that_cannot_cover_the_span(tmp_path):
    _seed_cache(tmp_path, _tr_cache_as_of())
    before = (tmp_path / "ABC_1d.csv").read_bytes()
    late = _fake(pd.Timestamp("2020-01-02"), [])
    with pytest.raises(w.WriterRefusal, match="cannot replace the file"):
        w.full_refetch("ABC", tmp_path, {"yfinance": late}, today=IDX[-1], actions=NO_ACTIONS)
    assert (tmp_path / "ABC_1d.csv").read_bytes() == before


def test_measure_only_mode_writes_nothing(tmp_path):
    _seed_cache(tmp_path, _tr_cache_as_of())
    before = (tmp_path / "ABC_1d.csv").read_bytes()
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _fake(IDX[0], [])},
                         today=IDX[-1], write=False, actions=NO_ACTIONS)
    assert rec.basis == "measured_tr" and (tmp_path / "ABC_1d.csv").read_bytes() == before


def test_a_new_ticker_has_no_cache_to_agree_with_and_is_written(tmp_path):
    rec = w.full_refetch("NEW", tmp_path, {"yfinance": _fake(IDX[0], [])}, today=IDX[-1],
                         new_ticker_start=IDX[0], actions=NO_ACTIONS)
    assert rec.overlap is None and (tmp_path / "parquet" / "NEW_1d.parquet").exists()


# ── the re-fetch must agree with the cache up to a rescale (Agent R's planted mismatch) ──

SEMIANNUAL_EXDATES = [pd.Timestamp(f"{y}-{m:02d}-16") for y in range(2018, 2026) for m in (6, 12)]


def _nominal_provider():
    """A provider on the OTHER convention: split-only — both modes return the nominal path."""
    raw = _raw()

    def provider(ticker, start, end, adjusted):
        return _ohlcv(raw[(raw.index >= pd.Timestamp(start)) & (raw.index <= end)])
    return provider


def _pair_bytes(cache_dir: Path, ticker: str = "ABC") -> tuple:
    return ((cache_dir / f"{ticker}_1d.csv").read_bytes(),
            (cache_dir / "parquet" / f"{ticker}_1d.parquet").read_bytes())


def test_a_split_only_provider_does_NOT_replace_a_total_return_cache(tmp_path):
    """R's planted mismatch: the span is covered and the basis measure is BLIND (two identical
    modes read 'unverified', exactly like a non-payer) — only the overlap sees it. Unguarded, the
    writer wrote the nominal series over the total-return cache under a clean write record."""
    _seed_cache(tmp_path, _tr_cache_as_of())
    before = _pair_bytes(tmp_path)
    with pytest.raises(w.WriterRefusal, match="DIFFERENT_CONVENTION") as refused:
        w.full_refetch("ABC", tmp_path, {"yfinance": _nominal_provider()}, today=IDX[-1], actions=NO_ACTIONS)
    assert refused.value.detail["basis"]["basis"] == "unverified: no ex-date in window", \
        "the basis measure cannot see this case — the overlap is the only rail"
    assert refused.value.detail["overlap"]["verdict"] == "DIFFERENT_CONVENTION"
    assert _pair_bytes(tmp_path) == before


def test_a_payer_whose_last_ex_date_is_older_than_a_short_tail_is_still_REFUSED(tmp_path):
    """EFA and VNQ on the real cache: inside a window with no ex-date a total-return tail and a
    split-only tail are IDENTICAL, so a 40-bar tail reads the other convention as agreement. The
    writer compares a trading year (OVERLAP_TAIL_BARS)."""
    end = pd.Timestamp("2025-11-03")            # the last ex-date, 2025-06-16, is ~100 bars back
    cache = _tr_cache_as_of(end, exdates=SEMIANNUAL_EXDATES)
    _seed_cache(tmp_path, cache)
    nominal = _raw()[_raw().index <= end]
    assert w.classify_overlap(cache["Close"].iloc[-40:], nominal)["verdict"] == "APPEND", \
        "a 40-bar tail is blind to this payer — the reason the window is a year"
    before = _pair_bytes(tmp_path)
    with pytest.raises(w.WriterRefusal, match="DIFFERENT_CONVENTION"):
        w.full_refetch("ABC", tmp_path, {"yfinance": _nominal_provider()}, today=end, actions=NO_ACTIONS)
    assert _pair_bytes(tmp_path) == before


def test_an_overlap_too_short_to_measure_is_REFUSED_when_a_cache_exists(tmp_path):
    """The span check reads only the first and last bars; a provider whose bars never meet the
    cached tail leaves nothing to compare — an unmeasured overlap is not agreement."""
    _seed_cache(tmp_path, _tr_cache_as_of())
    full = _fake(IDX[0], [])

    def gappy(ticker, start, end, adjusted):
        df = full(ticker, start, end, adjusted)
        return df[~((df.index > pd.Timestamp("2024-06-01")) & (df.index < CACHE_END))]
    before = _pair_bytes(tmp_path)
    with pytest.raises(w.WriterRefusal, match="INSUFFICIENT"):
        w.full_refetch("ABC", tmp_path, {"yfinance": gappy}, today=IDX[-1], actions=NO_ACTIONS)
    assert _pair_bytes(tmp_path) == before


# ── the Yahoo symbol: ONE table, recorded, never guessed ────────────────────────

def _symbol_bound(answers_to: str, calls: list, series=None):
    """A provider that answers ONLY to `answers_to` (empty for any other symbol) and logs every symbol."""
    raw = _raw()

    def provider(symbol, start, end, adjusted):
        calls.append(symbol)
        if symbol != answers_to:
            return pd.DataFrame(columns=w.COLUMNS)
        s = series if series is not None else (_tr(raw) if adjusted else raw)
        return _ohlcv(s[(s.index >= pd.Timestamp(start)) & (s.index <= end)])
    return provider


def test_a_share_class_is_fetched_under_its_yahoo_spelling_and_the_record_says_so(tmp_path):
    """BRK.B and BF.B read 'no bars' under the merged writer: Yahoo spells a class with a dash."""
    _seed_cache(tmp_path, _tr_cache_as_of(), ticker="BRK.B")
    calls, log = [], tmp_path / "write_log.jsonl"
    rec = w.full_refetch("BRK.B", tmp_path, {"yfinance": _symbol_bound("BRK-B", calls)},
                         today=IDX[-1], log_path=log, actions=NO_ACTIONS)
    assert rec.symbol_mapped == "BRK.B -> BRK-B (share class)"
    assert set(calls) == {"BRK-B"}, "fetched under the Yahoo spelling only"
    assert (tmp_path / "parquet" / "BRK.B_1d.parquet").exists(), "the file keeps the cache's name"
    assert '"symbol_mapped": "BRK.B -> BRK-B (share class)"' in log.read_text()


def test_an_unmapped_ticker_records_no_mapping(tmp_path):
    _seed_cache(tmp_path, _tr_cache_as_of())
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _symbol_bound("ABC", [])}, today=IDX[-1],
                         write=False, actions=NO_ACTIONS)
    assert rec.symbol_mapped is None


def test_a_RENAME_is_an_identity_claim_held_to_the_overlap_rail_and_its_refusal_names_the_claim(tmp_path):
    """FRC -> FRCB: if the symbol's history is another security's, the overlap refuses it."""
    _seed_cache(tmp_path, _tr_cache_as_of(), ticker="FRC")
    other_security = _raw(37.0) * np.exp(0.002 * np.sin(np.arange(len(IDX)) / 5.0))
    before = _pair_bytes(tmp_path, "FRC")
    with pytest.raises(w.WriterRefusal, match=r"symbol mapped: FRC -> FRCB \(rename\)") as refused:
        w.full_refetch("FRC", tmp_path, {"yfinance": _symbol_bound("FRCB", [], series=other_security)},
                       today=IDX[-1], actions=NO_ACTIONS)
    assert refused.value.detail["symbol_mapped"] == "FRC -> FRCB (rename)"
    assert refused.value.detail["overlap"]["verdict"] == "DIFFERENT_CONVENTION"
    assert _pair_bytes(tmp_path, "FRC") == before


def test_NO_fallback_symbol_is_ever_tried(tmp_path):
    """The script's 'most rows wins' tries FRCB then FRC; the writer tries the table's symbol ONLY,
    and an empty answer is a refusal, not a cue to guess."""
    _seed_cache(tmp_path, _tr_cache_as_of(), ticker="FRC")
    calls = []
    with pytest.raises(w.WriterRefusal, match="returned no bars"):
        w.full_refetch("FRC", tmp_path, {"yfinance": _symbol_bound("FRC", calls)}, today=IDX[-1], actions=NO_ACTIONS)
    assert calls == ["FRCB"], f"the writer tried {calls}"
