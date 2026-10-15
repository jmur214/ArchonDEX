"""The writer's LEVEL rail (adopted 2026-10-15; R's four conditions): the cache's last bar must equal
the provider's TRUE PRINT — unadjusted close × splits after it — up to the dividends the cache's own
adjustment applied; a level change outside it needs a matching declaration; a declared reused ticker
is never written. Fake providers only (no network)."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.data_manager import tr_writer as w

IDX = pd.bdate_range("2023-01-02", "2025-12-31")
CACHE_END = pd.Timestamp("2025-09-30")
TODAY = IDX[-1]


def _raw(price0: float = 100.0) -> pd.Series:
    return pd.Series(price0 * (1.0004 ** np.arange(len(IDX))), index=IDX)


def _ohlcv(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                         "Volume": 1e6}, index=close.index)


def _seed(cache_dir: Path, close: pd.Series, ticker: str = "ABC") -> None:
    w.write_pair_atomically(w.with_derived_columns(_ohlcv(close)), cache_dir / "parquet" / f"{ticker}_1d.parquet",
                            cache_dir / f"{ticker}_1d.csv")


def _provider(adjusted: pd.Series, unadjusted: pd.Series):
    def p(symbol, start, end, adj):
        s = adjusted if adj else unadjusted
        return _ohlcv(s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))])
    return p


def _actions(splits=None, dividends=None):
    idx = sorted(set((splits or {}).keys()) | set((dividends or {}).keys()))
    df = pd.DataFrame({"Dividends": [float((dividends or {}).get(d, 0.0)) for d in idx],
                       "Stock Splits": [float((splits or {}).get(d, 0.0)) for d in idx]},
                      index=pd.DatetimeIndex(idx))

    def a(symbol):
        return df
    return a


NONE = _actions()
NO_DECL: dict = {}


def _bytes(d: Path, t: str = "ABC") -> tuple:
    return ((d / f"{t}_1d.csv").read_bytes(), (d / "parquet" / f"{t}_1d.parquet").read_bytes())


# ── the identity holds: a correct level is written, and the record says so ──────

def test_a_correct_level_is_written_with_the_identity_in_the_record(tmp_path):
    raw = _raw()
    _seed(tmp_path, raw[raw.index <= CACHE_END])
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _provider(raw, raw)}, today=TODAY,
                         actions=NONE, declarations=NO_DECL)
    assert rec.level["log_residual"] == pytest.approx(0.0, abs=1e-12) and rec.level_declared is None
    pinned = json.loads((tmp_path / w.WRITE_RECORDS_DIR / "ABC.json").read_text())
    assert pinned["adjusted_as_of"] == str(TODAY.date()) and pinned["level"]["identity"] == pytest.approx(1.0)


# ── a ÷10 cache: refused without a declaration; written under a matching one ────

def test_a_div10_cache_is_REFUSED_by_the_level_identity(tmp_path):
    """The reproduction: AZO/MTD/NVR's shape. The overlap reads it RESCALED (constant ratio 10), so
    the merged writer wrote it; the identity reads 0.1 and refuses."""
    raw = _raw()
    _seed(tmp_path, raw[raw.index <= CACHE_END] / 10.0)
    before = _bytes(tmp_path)
    with pytest.raises(w.WriterRefusal, match="LEVEL IDENTITY") as refused:
        w.full_refetch("ABC", tmp_path, {"yfinance": _provider(raw, raw)}, today=TODAY,
                       actions=NONE, declarations=NO_DECL)
    assert refused.value.detail["level"]["identity"] == pytest.approx(0.1)
    assert _bytes(tmp_path) == before


def test_a_div10_cache_under_a_MATCHING_scale_defect_declaration_is_written_at_the_true_level(tmp_path):
    raw = _raw()
    _seed(tmp_path, raw[raw.index <= CACHE_END] / 10.0)
    decl = {"ABC": {"kind": "scale_defect", "declared_ratio": 10.0, "source": "test"}}
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _provider(raw, raw)}, today=TODAY,
                         actions=NONE, declarations=decl)
    assert rec.level_declared["kind"] == "scale_defect"
    written = pd.read_parquet(tmp_path / "parquet" / "ABC_1d.parquet")["Close"]
    assert written.loc[CACHE_END] == pytest.approx(raw.loc[CACHE_END]), "restored to the true level"
    census = w.substrate_level_declarations(tmp_path)
    assert census["records_dir_present"] and census["declared"]["ABC"]["declared_ratio"] == 10.0


def test_a_declared_ratio_that_does_NOT_explain_the_residual_is_refused(tmp_path):
    raw = _raw()
    _seed(tmp_path, raw[raw.index <= CACHE_END] / 10.0)
    with pytest.raises(w.WriterRefusal, match="does not explain"):
        w.full_refetch("ABC", tmp_path, {"yfinance": _provider(raw, raw)}, today=TODAY, actions=NONE,
                       declarations={"ABC": {"kind": "scale_defect", "declared_ratio": 5.0}})


def test_a_declared_scale_defect_whose_identity_HOLDS_is_refused_as_a_mismatch(tmp_path):
    """The DAL pattern: a declaration that no longer matches the data stops the write until re-ruled."""
    raw = _raw()
    _seed(tmp_path, raw[raw.index <= CACHE_END])
    with pytest.raises(w.WriterRefusal, match="no longer matches"):
        w.full_refetch("ABC", tmp_path, {"yfinance": _provider(raw, raw)}, today=TODAY, actions=NONE,
                       declarations={"ABC": {"kind": "scale_defect", "declared_ratio": 10.0}})


def test_a_declared_REUSED_TICKER_is_never_written_even_when_the_identity_holds(tmp_path):
    """POM's shape: the cached file IS the reused entity, so every rail passes; only the declaration
    refuses, and it does so before any provider call."""
    raw = _raw()
    _seed(tmp_path, raw[raw.index <= CACHE_END])
    calls = []

    def counting(symbol, start, end, adj):
        calls.append(adj)
        return _provider(raw, raw)(symbol, start, end, adj)
    with pytest.raises(w.WriterRefusal, match="REUSED TICKER"):
        w.full_refetch("ABC", tmp_path, {"yfinance": counting}, today=TODAY, actions=NONE,
                       declarations={"ABC": {"kind": "reused_ticker", "source": "test"}})
    assert calls == [], "refused before any provider call"


# ── corporate actions after the cache's last bar are EXPLAINED, not declared ────

def test_a_split_after_the_cache_is_explained_by_the_providers_split_record(tmp_path):
    """KLAC/CTVA/CVNA's shape: a 4:1 split after the cache's last bar. The provider's series are
    split-adjusted (÷4 before the split); the cache holds the true pre-split print."""
    raw = _raw()
    split = pd.Timestamp("2025-11-03")
    adj_basis = raw.where(raw.index >= split, raw / 4.0)
    _seed(tmp_path, raw[raw.index <= CACHE_END])
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adj_basis, adj_basis)}, today=TODAY,
                         actions=_actions(splits={split: 4.0}), declarations=NO_DECL)
    assert rec.level["splits_after"] == 4.0 and rec.level["log_residual"] == pytest.approx(0.0, abs=1e-12)
    assert rec.level_declared is None


def test_without_the_split_record_the_same_split_is_REFUSED(tmp_path):
    raw = _raw()
    split = pd.Timestamp("2025-11-03")
    adj_basis = raw.where(raw.index >= split, raw / 4.0)
    _seed(tmp_path, raw[raw.index <= CACHE_END])
    with pytest.raises(w.WriterRefusal, match="LEVEL IDENTITY"):
        w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adj_basis, adj_basis)}, today=TODAY,
                       actions=NONE, declarations=NO_DECL)


# ── a stale file: the dividends after its last bar are explained exactly ────────

def _stale_case(tmp_path: Path, special: float = 0.05):
    """The cache's last bar is CACHE_END, but its total-return adjustment is as of a later date (a
    prior write record says so), and a special dividend fell in between: the cached last bar is the
    true print × (1 − D/P). APH's shape (0.9947 → residual 1.0000)."""
    raw = _raw()
    ex = pd.Timestamp("2025-10-15")
    as_of = pd.Timestamp("2025-11-28")
    p_prev = float(raw.loc[:ex - pd.Timedelta(days=1)].iloc[-1])
    _seed(tmp_path, raw[raw.index <= CACHE_END] * (1.0 - special))
    (tmp_path / w.WRITE_RECORDS_DIR).mkdir(parents=True, exist_ok=True)
    (tmp_path / w.WRITE_RECORDS_DIR / "ABC.json").write_text(json.dumps(
        {"ticker": "ABC", "adjusted_as_of": str(as_of.date())}))
    adjusted = raw.where(raw.index >= ex, raw * (1.0 - special))
    return raw, adjusted, ex, special * p_prev


def test_a_stale_file_whose_dividend_is_in_the_record_is_written(tmp_path):
    raw, adjusted, ex, d = _stale_case(tmp_path)
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adjusted, raw)}, today=TODAY,
                         actions=_actions(dividends={ex: d}), declarations=NO_DECL)
    assert rec.level["identity"] == pytest.approx(0.95, rel=1e-9)
    assert rec.level["dividend_factor"] == pytest.approx(0.95, rel=1e-9)
    assert rec.level["log_residual"] == pytest.approx(0.0, abs=1e-9)
    assert rec.level["adjusted_as_of"] == "2025-11-28", "the prior record's date, not the legacy one"


def test_a_stale_file_whose_dividend_is_MISSING_from_the_record_is_refused(tmp_path):
    raw, adjusted, ex, d = _stale_case(tmp_path)
    with pytest.raises(w.WriterRefusal, match="LEVEL IDENTITY"):
        w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adjusted, raw)}, today=TODAY,
                       actions=NONE, declarations=NO_DECL)


# ── fail-closed inputs and the census reader ────────────────────────────────────

def test_a_cache_without_an_actions_record_is_REFUSED(tmp_path):
    raw = _raw()
    _seed(tmp_path, raw[raw.index <= CACHE_END])
    with pytest.raises(w.WriterRefusal, match="no corporate-actions record"):
        w.full_refetch("ABC", tmp_path, {"yfinance": _provider(raw, raw)}, today=TODAY,
                       declarations=NO_DECL)


def test_a_new_ticker_needs_no_identity(tmp_path):
    raw = _raw()
    rec = w.full_refetch("NEW", tmp_path, {"yfinance": _provider(raw, raw)}, today=TODAY,
                         new_ticker_start=IDX[0], declarations=NO_DECL)
    assert rec.level is None and (tmp_path / w.WRITE_RECORDS_DIR / "NEW.json").exists()


def test_the_census_reader_REPORTS_an_absent_records_dir_rather_than_a_clean_zero(tmp_path):
    assert w.substrate_level_declarations(tmp_path) == {"records_dir_present": False, "declared": {}}


def test_the_shipped_declarations_are_the_four_div10_restorations_and_the_two_reused_tickers():
    d = w.load_level_declarations()
    assert {t for t, v in d.items() if v["kind"] == "scale_defect"} == {"AZO", "MTD", "NVR"}
    assert {t for t, v in d.items() if v["kind"] == "reused_ticker"} == {"SLE", "POM"}
    assert all(v["declared_ratio"] == 10.0 for v in d.values() if v["kind"] == "scale_defect")


def test_an_ERRORED_level_declarations_record_fails_the_census():
    from core.census import assert_census
    v = assert_census({"census": {"n_resolved": 3, "n_in_panel": 3,
                                  "level_declarations": {"error": "RuntimeError('boom')"}}})
    assert any("level_declarations record errored" in f for f in v.failures)
