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

def _pin_adjusted_as_of(cache_dir: Path, date: str, ticker: str = "ABC") -> None:
    """A prior write record: the date the cached file's adjustment is as of."""
    (cache_dir / w.WRITE_RECORDS_DIR).mkdir(parents=True, exist_ok=True)
    (cache_dir / w.WRITE_RECORDS_DIR / f"{ticker}.json").write_text(
        json.dumps({"ticker": ticker, "adjusted_as_of": date}))


def test_a_split_after_the_caches_adjustment_is_explained_by_the_providers_split_record(tmp_path):
    """KLAC/CTVA/CVNA's shape: a 4:1 split AFTER the cache was written. The provider's series are
    split-adjusted (÷4 before the split); the cache, written before it, holds the pre-split level."""
    raw = _raw()
    split = pd.Timestamp("2025-11-03")
    adj_basis = raw.where(raw.index >= split, raw / 4.0)
    _seed(tmp_path, raw[raw.index <= CACHE_END])
    _pin_adjusted_as_of(tmp_path, str(CACHE_END.date()))        # written before the split
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adj_basis, adj_basis)}, today=TODAY,
                         actions=_actions(splits={split: 4.0}), declarations=NO_DECL)
    assert rec.level["splits_after_adjusted_as_of"] == 4.0
    assert rec.level["log_residual"] == pytest.approx(0.0, abs=1e-12) and rec.level_declared is None


def test_without_the_split_record_the_same_split_is_REFUSED(tmp_path):
    raw = _raw()
    split = pd.Timestamp("2025-11-03")
    adj_basis = raw.where(raw.index >= split, raw / 4.0)
    _seed(tmp_path, raw[raw.index <= CACHE_END])
    _pin_adjusted_as_of(tmp_path, str(CACHE_END.date()))
    with pytest.raises(w.WriterRefusal, match="LEVEL IDENTITY"):
        w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adj_basis, adj_basis)}, today=TODAY,
                       actions=NONE, declarations=NO_DECL)


def test_a_STALE_file_split_adjusted_by_its_writer_is_NOT_read_as_a_scale_defect(tmp_path):
    """NVDA's shape (found by the 652-file sweep): the file ENDS 2025-09-30, a 4:1 split came on
    2025-11-03, and the file was written AFTER it (adjusted as of 2025-12-31) — so its writer already
    split-adjusted every bar, and its last bar holds the split-adjusted level, correctly. The split
    falls in (d, W], so it is NOT multiplied back in. On the first rail (splits after d) this read 0.25
    and was refused as a level defect."""
    raw = _raw()
    split = pd.Timestamp("2025-11-03")
    adj_basis = raw.where(raw.index >= split, raw / 4.0)
    _seed(tmp_path, adj_basis[adj_basis.index <= CACHE_END])     # split-adjusted by its writer
    _pin_adjusted_as_of(tmp_path, "2025-12-31")                  # written after the split
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adj_basis, adj_basis)}, today=TODAY,
                         actions=_actions(splits={split: 4.0}), declarations=NO_DECL)
    assert rec.level["splits_after_adjusted_as_of"] == 1.0
    assert rec.level["log_residual"] == pytest.approx(0.0, abs=1e-12) and rec.level_declared is None


def test_the_NVDA_shape_through_the_LEGACY_path_with_no_pinned_record(tmp_path):
    """R: the legacy files have no record — W is LEGACY_ADJUSTED_AS_OF (2026-04-25). The split
    (2025-11-03) falls in (d, W_legacy], the cache is post-split: identity 1 with no record at all."""
    raw = _raw()
    split = pd.Timestamp("2025-11-03")
    assert CACHE_END < split <= w.LEGACY_ADJUSTED_AS_OF
    adj_basis = raw.where(raw.index >= split, raw / 4.0)
    _seed(tmp_path, adj_basis[adj_basis.index <= CACHE_END])
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adj_basis, adj_basis)}, today=TODAY,
                         actions=_actions(splits={split: 4.0}), declarations=NO_DECL)
    assert rec.level["adjusted_as_of"] == str(w.LEGACY_ADJUSTED_AS_OF.date())
    assert rec.level["splits_after_adjusted_as_of"] == 1.0
    assert rec.level["log_residual"] == pytest.approx(0.0, abs=1e-12)


def test_a_split_BEFORE_the_caches_last_bar_has_no_effect(tmp_path):
    """R's third interval: a split before d is in every basis already (the cache's and the
    provider's); it is multiplied in by neither formula."""
    raw = _raw()
    split = pd.Timestamp("2024-06-03")
    assert split < CACHE_END
    adj_basis = raw.where(raw.index >= split, raw / 4.0)
    _seed(tmp_path, adj_basis[adj_basis.index <= CACHE_END])
    _pin_adjusted_as_of(tmp_path, str(CACHE_END.date()))
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adj_basis, adj_basis)}, today=TODAY,
                         actions=_actions(splits={split: 4.0}), declarations=NO_DECL)
    assert rec.level["splits_after_adjusted_as_of"] == 1.0
    assert rec.level["log_residual"] == pytest.approx(0.0, abs=1e-12)


def test_a_dividend_AND_a_split_both_in_d_to_W_read_in_one_basis(tmp_path):
    """R: with a split and a dividend both in (d, W], the dividend factor's prior close must be in
    the same (split-adjusted) basis as the dividend amount, or the factor is off by the split. The
    provider quotes both split-adjusted; the cache (written at W) is split-adjusted AND scaled by
    the dividend: identity = 1 − y, factor = 1 − y, residual 1."""
    raw = _raw()
    split, ex = pd.Timestamp("2025-10-20"), pd.Timestamp("2025-11-17")
    W = pd.Timestamp("2025-12-15")
    y = 0.03
    adj_basis = raw.where(raw.index >= split, raw / 4.0)                 # split-adjusted, unadjusted for divs
    p_prev = float(adj_basis.loc[:ex - pd.Timedelta(days=1)].iloc[-1])   # in the split-adjusted basis
    _seed(tmp_path, adj_basis[adj_basis.index <= CACHE_END] * (1.0 - y))
    _pin_adjusted_as_of(tmp_path, str(W.date()))
    adjusted = adj_basis.where(adj_basis.index >= ex, adj_basis * (1.0 - y))
    rec = w.full_refetch("ABC", tmp_path, {"yfinance": _provider(adjusted, adj_basis)}, today=TODAY,
                         actions=_actions(splits={split: 4.0}, dividends={ex: y * p_prev}),
                         declarations=NO_DECL)
    assert rec.level["splits_after_adjusted_as_of"] == 1.0
    assert rec.level["dividend_factor"] == pytest.approx(1.0 - y, rel=1e-9)
    assert rec.level["log_residual"] == pytest.approx(0.0, abs=1e-9)


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
    assert w.substrate_level_declarations(tmp_path) == {"cache_dir": str(tmp_path),
                                                        "records_dir_present": False, "declared": {}}


def test_the_census_block_NAMES_the_directory_it_read(tmp_path):
    """R: on a proof-on-a-copy run the producers read the canonical cache; the block says which."""
    assert w.substrate_level_declarations(tmp_path)["cache_dir"] == str(tmp_path)


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
