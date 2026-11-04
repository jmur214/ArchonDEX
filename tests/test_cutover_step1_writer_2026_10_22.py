"""Cutover step 1 (the user's OPTION (a) ruling, 2026-10-22): the writer's SEAM-preserving write,
the seam-ratio rail, the declared cache-convention defects, the class (i) declarations and the
BK -> BNY entry. Every lock DRIVES `full_refetch` on planted files with fake providers (no
network); each is reversion-proven (the record is in docs/Audit/cutover_step1_record_2026_10_22.md).

The planted world: a quarterly payer. The PROVIDER is total return as of TODAY; the CACHE's
post-seam span is total return as of its write date W (= its last bar), and its pre-seam span is a
DIFFERENT series (the T-082b drip stands in for it: the same bars at +2% level) — so a lock can tell
"the cached pre-seam bars were KEPT" from "the provider's were taken"."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.data_manager import tr_writer as w
from engines.data_manager.yahoo_symbols import RENAME, yahoo_symbol

IDX = pd.bdate_range("2015-01-02", "2025-12-31")
SEAM = pd.Timestamp("2018-01-02")
CACHE_END = pd.Timestamp("2025-09-30")          # W: the cache's write date = its last bar
TODAY = IDX[-1]
Q = 0.009                                        # the quarterly dividend, as a fraction of price
EXDATES = pd.DatetimeIndex(sorted({IDX[(IDX.year == y) & (IDX.month == m) & (IDX.day >= 10)][0]
                                   for y in range(2015, 2026) for m in (2, 5, 8, 11)}))
RAW = pd.Series(100.0 * (1.0004 ** np.arange(len(IDX))), index=IDX)
TICKER = "ABC"


def tr_as_of(as_of: pd.Timestamp, raw: pd.Series = RAW, skip=()) -> pd.Series:
    """Total return back-adjusted as of `as_of`: every ex-date in (t, as_of] scales bar t down —
    except the `skip` ex-dates (a cache that MISSED them)."""
    f = pd.Series(1.0, index=raw.index)
    for ex in EXDATES:
        if ex <= as_of and ex not in skip:
            f[f.index < ex] *= (1.0 - Q)
    return raw * f


def _ohlcv(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"Open": close, "High": close * 1.01, "Low": close * 0.99, "Close": close,
                         "Volume": 1e6}, index=close.index)


def _seed(cache_dir: Path, close: pd.Series, ticker: str = TICKER) -> None:
    w.write_pair_atomically(w.with_derived_columns(_ohlcv(close)),
                            cache_dir / "parquet" / f"{ticker}_1d.parquet", cache_dir / f"{ticker}_1d.csv")


def _meta(cache_dir: Path, ticker: str = TICKER, *, both: bool = True, n_pre: int = 1,
          seam: str = str(SEAM.date())) -> None:
    (cache_dir / w.MERGE_META_NAME).write_text(json.dumps({"per_ticker": {ticker: {
        "ticker": ticker, "merge_case": "both" if both else "alpaca_only",
        "seam_date": seam if both else None, "n_stooq_pre_seam": n_pre if both else 0,
        "first_bar_date": str(IDX[0].date()), "last_bar_date": str(CACHE_END.date())}}}))


def drip_cache(post_skip=(), pre_level: float = 1.02) -> pd.Series:
    """The planted cache: post-seam = total return as of W; pre-seam = the same bars at +2% (the
    stand-in for the drip: a series the provider does NOT hold)."""
    c = tr_as_of(CACHE_END, skip=post_skip)
    c = c[c.index <= CACHE_END].copy()
    c[c.index < SEAM] *= pre_level
    return c


def _provider(adjusted: pd.Series, unadjusted: pd.Series, provider_start=IDX[0], calls=None):
    def p(symbol, start, end, adj):
        if calls is not None:
            calls.append((symbol, str(pd.Timestamp(start).date()), adj))
        s = adjusted if adj else unadjusted
        return _ohlcv(s[(s.index >= max(pd.Timestamp(start), pd.Timestamp(provider_start)))
                        & (s.index <= pd.Timestamp(end))])
    return p


def _actions(symbol):
    return pd.DataFrame(columns=["Dividends", "Stock Splits"])


NO_DECL: dict = {}
NO_CONV = {s: {} for s in w.CONVENTION_SECTIONS}
PROVIDER = _provider(tr_as_of(TODAY), RAW)


def _run(cache_dir, provider=PROVIDER, **kw):
    kw.setdefault("declarations", NO_DECL)
    kw.setdefault("conventions", NO_CONV)
    return w.full_refetch(TICKER, cache_dir, {"yfinance": provider}, today=TODAY, actions=_actions, **kw)


def _written(cache_dir: Path, ticker: str = TICKER) -> pd.Series:
    return pd.read_parquet(cache_dir / "parquet" / f"{ticker}_1d.parquet")["Close"]


# ── the seam-preserving write (option (a)) ──────────────────────────────────────

def test_a_both_file_KEEPS_its_cached_pre_seam_bars_and_takes_the_provider_post_seam(tmp_path):
    cache = drip_cache()
    _seed(tmp_path, cache)
    _meta(tmp_path)
    rec = _run(tmp_path)
    got = _written(tmp_path)
    r = rec.seam["seam_ratio"]["ratio"]
    assert rec.overlap["verdict"] == "RESCALED" and r == pytest.approx(1.0 - Q, rel=1e-9)
    pre, post = got[got.index < SEAM], got[got.index >= SEAM]
    # the kept bars are the CACHE's (at +2%), scaled by the seam ratio — never the provider's
    np.testing.assert_allclose(pre.values, (cache[cache.index < SEAM] * r).values, rtol=1e-12)
    assert not np.allclose(pre.values, tr_as_of(TODAY)[pre.index].values, rtol=1e-3)
    np.testing.assert_allclose(post.values, tr_as_of(TODAY)[post.index].values, rtol=1e-12)
    assert got.index.max() == TODAY and len(got) == len(IDX)
    # the seam-day return is unchanged by the write
    i = cache.index.get_loc(SEAM)
    assert got[SEAM] / got.iloc[i - 1] == pytest.approx(cache[SEAM] / cache.iloc[i - 1], rel=1e-12)
    assert rec.convention == {"pre_seam": w.DRIP, "seam_date": "2018-01-02", "post_seam": w.EXACT_TR}
    assert rec.seam["source"] == "merge_meta" and rec.seam["n_pre_seam_bars_kept"] == int((IDX < SEAM).sum())
    pinned = json.loads((tmp_path / w.WRITE_RECORDS_DIR / f"{TICKER}.json").read_text())
    assert pinned["convention"] == rec.convention and pinned["seam"]["seam_ratio"]["ratio"] == r


def test_the_provider_need_only_cover_the_POST_seam_span_the_class_iii_iv_shape(tmp_path):
    """yfinance starts after the cached start (C: 1977 vs 1970; CHTR: 34 days late): with a seam the
    deep Stooq history is kept and the provider covers the seam onward. Whole-file (seam=None) is
    still refused on the span — the ruling admits these names through the seam, not by slack."""
    _seed(tmp_path, drip_cache())
    _meta(tmp_path)
    late = _provider(tr_as_of(TODAY), RAW, provider_start=SEAM)
    before = (tmp_path / f"{TICKER}_1d.csv").read_bytes()
    with pytest.raises(w.WriterRefusal, match="cannot replace the file"):
        _run(tmp_path, late, seam=None)
    assert (tmp_path / f"{TICKER}_1d.csv").read_bytes() == before
    rec = _run(tmp_path, late)
    assert rec.seam is not None and _written(tmp_path).index.min() == IDX[0]


def test_without_a_merge_record_there_is_NO_seam_to_keep_and_a_short_provider_is_refused(tmp_path):
    """Fail closed: a cache with no `_merge_meta.json` has no seams the writer can keep — the write
    is whole-file, and a provider that does not cover the cached start is refused."""
    _seed(tmp_path, drip_cache())
    assert w.seam_for(tmp_path, TICKER, NO_CONV) is None
    with pytest.raises(w.WriterRefusal, match="cannot replace the file"):
        _run(tmp_path, _provider(tr_as_of(TODAY), RAW, provider_start=SEAM))


def test_a_both_file_with_NO_pre_seam_bars_is_replaced_whole(tmp_path):
    """AMCR's shape in the merge record: `both`, seam 2018-01-02, n_stooq_pre_seam 0."""
    c = tr_as_of(CACHE_END)
    _seed(tmp_path, c[(c.index >= SEAM) & (c.index <= CACHE_END)])
    _meta(tmp_path, n_pre=0)
    rec = _run(tmp_path)
    assert rec.seam is None and rec.convention == {"whole": w.EXACT_TR}


def test_a_seam_not_inside_the_cached_span_is_refused(tmp_path):
    c = tr_as_of(CACHE_END)
    _seed(tmp_path, c[(c.index >= SEAM) & (c.index <= CACHE_END)])     # starts AT the seam
    _meta(tmp_path, n_pre=5)                                           # the record claims pre-seam bars
    with pytest.raises(w.WriterRefusal, match="not inside the cached span"):
        _run(tmp_path)


# ── the seam-ratio rail ───────────────────────────────────────────────────────────

def test_a_cache_that_missed_an_ex_date_OLDER_than_the_tail_is_caught_at_the_seam(tmp_path):
    """The tail (last 252 bars) reads a clean RESCALE; the seam ratio does not match it — the cache
    changed convention between the seam and the tail. Refused unless declared."""
    missed = EXDATES[(EXDATES > pd.Timestamp("2021-01-01")) & (EXDATES < pd.Timestamp("2021-12-31"))][0]
    _seed(tmp_path, drip_cache(post_skip=(missed,)))
    _meta(tmp_path)
    before = (tmp_path / f"{TICKER}_1d.csv").read_bytes()
    with pytest.raises(w.WriterRefusal, match="undeclared mid-span step") as e:
        _run(tmp_path)
    assert e.value.detail["overlap"]["verdict"] == "RESCALED"
    assert (tmp_path / f"{TICKER}_1d.csv").read_bytes() == before


def test_the_same_missed_ex_date_DECLARED_as_a_mixed_convention_is_verified_and_written(tmp_path):
    missed = EXDATES[(EXDATES > pd.Timestamp("2021-01-01")) & (EXDATES < pd.Timestamp("2021-12-31"))][0]
    _seed(tmp_path, drip_cache(post_skip=(missed,)))
    _meta(tmp_path)
    conv = {**NO_CONV, "cache_convention_defects": {TICKER: {
        "kind": "mixed_convention_cache", "declared_steps": [str(missed.date())]}}}
    rec = _run(tmp_path, conventions=conv)
    assert rec.convention_declared["kind"] == "mixed_convention_cache"
    # the cache never scaled its past down for the missed ex-date, so provider/cache steps UP there
    assert rec.convention_declared["steps_found"] == {str(missed.date()): pytest.approx(-np.log(1 - Q), rel=1e-6)}
    assert rec.seam["gap_explained_by_declaration"] is True
    # declaring the WRONG date, or a date with no step, is refused
    other = EXDATES[(EXDATES > pd.Timestamp("2022-01-01"))][0]
    bad = {**NO_CONV, "cache_convention_defects": {TICKER: {
        "kind": "mixed_convention_cache", "declared_steps": [str(other.date())]}}}
    with pytest.raises(w.WriterRefusal, match="does not match the data"):
        _run(tmp_path, conventions=bad)


def test_a_mixed_declaration_on_a_CLEAN_cache_is_refused(tmp_path):
    _seed(tmp_path, drip_cache())
    _meta(tmp_path)
    conv = {**NO_CONV, "cache_convention_defects": {TICKER: {
        "kind": "mixed_convention_cache", "declared_steps": [str(EXDATES[-8].date())]}}}
    with pytest.raises(w.WriterRefusal, match="declared steps absent"):
        _run(tmp_path, conventions=conv)


# ── the declared SPLIT-ONLY cache (the backfill_t052 trio) ──────────────────────

def _split_only_cache() -> pd.Series:
    return RAW[RAW.index <= CACHE_END]


def test_a_split_only_cache_is_still_REFUSED_without_a_declaration(tmp_path):
    _seed(tmp_path, _split_only_cache())
    with pytest.raises(w.WriterRefusal, match="DIFFERENT_CONVENTION"):
        _run(tmp_path)


def test_a_DECLARED_split_only_cache_is_verified_against_the_split_only_mode_and_rewritten_as_TR(tmp_path):
    _seed(tmp_path, _split_only_cache())
    calls = []
    conv = {**NO_CONV, "cache_convention_defects": {TICKER: {"kind": "split_only_cache"}}}
    rec = _run(tmp_path, _provider(tr_as_of(TODAY), RAW, calls=calls), conventions=conv)
    assert rec.convention_declared["kind"] == "split_only_cache"
    assert rec.convention_declared["against_split_only"]["verdict"] == "APPEND"
    assert rec.convention_declared["against_total_return"]["verdict"] == "DIFFERENT_CONVENTION"
    assert [c[2] for c in calls].count(False) == 4, \
        "the basis tail, the declared split-only check, the level rail, the close_unadj span"
    np.testing.assert_allclose(_written(tmp_path).values, tr_as_of(TODAY).values, rtol=1e-12)


# ── the split-only close as a second column (close_unadj; ruled 2026-10-15) ──────

def test_every_written_file_carries_the_providers_split_only_close_as_close_unadj(tmp_path):
    """The dollar-ADV, slippage and borrow buckets and the Engine B share-sizing unit read the
    column named EXACTLY `close_unadj`: the provider's unadjusted mode over the file's whole span,
    NaN only on bars the provider does not hold, never derived from the total-return close."""
    _seed(tmp_path, drip_cache())
    _meta(tmp_path)
    rec = _run(tmp_path)
    got = pd.read_parquet(tmp_path / "parquet" / f"{TICKER}_1d.parquet")
    assert w.CLOSE_UNADJ == "close_unadj" and w.CLOSE_UNADJ in got.columns
    assert got[w.CLOSE_UNADJ].notna().all()
    np.testing.assert_allclose(got[w.CLOSE_UNADJ].values, RAW[got.index].values, rtol=1e-12)
    assert not np.allclose(got[w.CLOSE_UNADJ].values, got["Close"].values), "split-only, not the TR close"
    assert rec.close_unadj == {"column": "close_unadj", "mode": rec.close_unadj["mode"], "n_bars": len(got),
                               "n_missing": 0, "span": [str(IDX[0].date()), str(TODAY.date())]}
    csv = pd.read_csv(tmp_path / f"{TICKER}_1d.csv")
    assert w.CLOSE_UNADJ in csv.columns, "the csv pair carries it too"


def test_close_unadj_is_NaN_before_a_class_iii_iv_providers_first_bar_never_derived(tmp_path):
    _seed(tmp_path, drip_cache())
    _meta(tmp_path)
    late = _provider(tr_as_of(TODAY), RAW, provider_start=SEAM)
    rec = _run(tmp_path, late)
    got = pd.read_parquet(tmp_path / "parquet" / f"{TICKER}_1d.parquet")
    assert got.loc[got.index < SEAM, w.CLOSE_UNADJ].isna().all()
    assert got.loc[got.index >= SEAM, w.CLOSE_UNADJ].notna().all()
    assert rec.close_unadj["n_missing"] == int((IDX < SEAM).sum()) and rec.close_unadj["span"][0] == str(SEAM.date())


def test_a_split_only_declaration_on_a_TOTAL_RETURN_cache_is_refused_as_no_longer_matching(tmp_path):
    _seed(tmp_path, drip_cache())
    _meta(tmp_path)
    conv = {**NO_CONV, "cache_convention_defects": {TICKER: {"kind": "split_only_cache"}}}
    with pytest.raises(w.WriterRefusal, match="no longer matches the data; re-rule it"):
        _run(tmp_path, conventions=conv)


def test_a_split_only_declaration_whose_cache_matches_NEITHER_mode_is_refused(tmp_path):
    _seed(tmp_path, _split_only_cache() * np.linspace(1.0, 1.3, int((IDX <= CACHE_END).sum())))
    conv = {**NO_CONV, "cache_convention_defects": {TICKER: {"kind": "split_only_cache"}}}
    with pytest.raises(w.WriterRefusal, match="SPLIT-ONLY mode too"):
        _run(tmp_path, conventions=conv)


# ── class (i) by declaration; BK -> BNY ───────────────────────────────────────────

CLASS_I = ["SLE", "POM", "ABS", "BMC", "CCE", "CFC", "GR", "HAR", "MHS", "NCC", "TEG", "TIE"]


@pytest.mark.parametrize("ticker", CLASS_I)
def test_the_twelve_class_i_names_are_refused_BEFORE_any_provider_call(tmp_path, ticker):
    _seed(tmp_path, drip_cache(), ticker=ticker)
    calls = []
    before = (tmp_path / f"{ticker}_1d.csv").read_bytes()
    with pytest.raises(w.WriterRefusal, match="REUSED TICKER"):
        w.full_refetch(ticker, tmp_path, {"yfinance": _provider(tr_as_of(TODAY), RAW, calls=calls)},
                       today=TODAY, actions=_actions)             # the SHIPPED declarations
    assert calls == [] and (tmp_path / f"{ticker}_1d.csv").read_bytes() == before


RELISTED = ["AVB", "EA", "EQR", "LEG", "QRVO", "SATS", "WBD"]


@pytest.mark.parametrize("ticker", RELISTED)
def test_the_seven_symbols_reused_by_a_later_entity_are_KEPT_and_never_refetched(tmp_path, ticker):
    """RULED 2026-10-23: the cached file IS the PIT entity; the provider's series under the symbol
    (from 2026-08..10) is another company. Refused BEFORE any provider call — the refusal no longer
    rests on the provider's start date, which could move — and the file is untouched."""
    _seed(tmp_path, drip_cache(), ticker=ticker)
    calls = []
    before = (tmp_path / f"{ticker}_1d.csv").read_bytes()
    with pytest.raises(w.WriterRefusal, match="SYMBOL REUSED BY A LATER ENTITY") as e:
        w.full_refetch(ticker, tmp_path, {"yfinance": _provider(tr_as_of(TODAY), RAW, calls=calls)},
                       today=TODAY, actions=_actions)             # the SHIPPED declarations
    assert calls == [] and (tmp_path / f"{ticker}_1d.csv").read_bytes() == before
    assert e.value.detail["level_declared"]["provider_series_start"].startswith("2026-")


def test_BK_is_fetched_as_BNY_under_the_rename_kind_and_the_record_names_the_claim(tmp_path):
    assert yahoo_symbol("BK") == ("BNY", RENAME)
    _seed(tmp_path, drip_cache(), ticker="BK")
    calls = []
    rec = w.full_refetch("BK", tmp_path, {"yfinance": _provider(tr_as_of(TODAY), RAW, calls=calls)},
                         today=TODAY, actions=_actions, declarations=NO_DECL, conventions=NO_CONV, seam=None)
    assert {c[0] for c in calls} == {"BNY"} and rec.symbol_mapped == "BK -> BNY (rename)"


# ── the shipped declarations (data locks on the canonical cache) ──────────────────

SEAM_NAMES = ["C", "INTC", "JPM", "ELV", "MAR", "PLD", "AXP", "WMT", "CHTR", "KDP", "TDC", "UAL", "WU"]


def test_the_shipped_convention_declarations_load_and_name_the_ruled_sets():
    c = w.load_convention_declarations()
    assert sorted(c["seams"]) == sorted(SEAM_NAMES)
    assert all(v["pre_seam"] == w.DRIP and v["post_seam"] == w.EXACT_TR for v in c["seams"].values())
    assert set(c["whole_file_overrides"]) == {"SPY"} and c["whole_file_overrides"]["SPY"]["convention"] == w.EXACT_TR
    assert {t: v["kind"] for t, v in c["cache_convention_defects"].items()} == {
        "AGG": "split_only_cache", "EFA": "split_only_cache", "VNQ": "split_only_cache",
        "AMCR": "mixed_convention_cache"}
    assert c["cache_convention_defects"]["AMCR"]["declared_steps"] == ["2025-09-05", "2025-11-28"]


@pytest.mark.parametrize("ticker", SEAM_NAMES)
def test_each_declared_seam_equals_the_canonical_merge_records_seam(ticker):
    meta = w.load_merge_meta(w.CANONICAL_CACHE_DIR)
    assert meta is not None, "the canonical cache has no merge record"
    decl = w.load_convention_declarations()["seams"][ticker]
    assert meta[ticker]["seam_date"] == decl["seam_date"] and meta[ticker]["merge_case"] == "both"
    assert meta[ticker]["first_bar_date"] == decl["cached_first_bar"]
    spec = w.seam_for(w.CANONICAL_CACHE_DIR, ticker)
    assert spec["source"] == "declared" and spec["date"] == pd.Timestamp(decl["seam_date"])


def test_a_declared_seam_that_disagrees_with_the_merge_record_is_refused(tmp_path):
    _seed(tmp_path, drip_cache())
    _meta(tmp_path)
    conv = {**NO_CONV, "seams": {TICKER: {"seam_date": "2019-01-02", "pre_seam": w.DRIP, "post_seam": w.EXACT_TR}}}
    with pytest.raises(w.WriterRefusal, match="disagrees with the merge record"):
        _run(tmp_path, conventions=conv)


@pytest.mark.parametrize("bad", [
    {"seams": {"X": {"seam_date": "2018-01-02", "pre_seam": "guess", "post_seam": "exact_tr"}}},
    {"whole_file_overrides": {"X": {"convention": "maybe"}}},
    {"cache_convention_defects": {"X": {"kind": "something_else"}}},
    {"cache_convention_defects": {"X": {"kind": "mixed_convention_cache"}}},
])
def test_a_malformed_convention_declaration_file_RAISES(tmp_path, bad):
    p = tmp_path / "conv.json"
    p.write_text(json.dumps(bad))
    with pytest.raises(ValueError):
        w.load_convention_declarations(p)
