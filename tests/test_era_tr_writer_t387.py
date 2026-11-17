"""T-387 — option (a′) in the CUTOVER WRITE PATH (USER RULING 2026-11-12: the cutover adopts the
T-384 (a′) v4 drip fix, amending the 2026-10-22 option (a)).

The writer's (a′) mode is `tr_writer.era_tr_rewrite`; the (a′) logic is ONE shared module,
`engines/data_manager/era_tr.py`, also called by `scripts/drip_fix_candidate_t384.py`. Every series
here is SYNTHETIC and lives under pytest's tmp_path; nothing reads or writes the real cache.

The planted world is the T-384 one, driven through the cutover's real order:
  * the CACHE as T-082b merged it — a "Stooq" series that misses every dividend in the measured
    missed eras (2003-04-01 → 2011-02-21, and from 2022-12-19) and captures the rest, merged with a
    total-return "Alpaca" leg by the merge's OWN functions (`fit_ratio_loglinear`,
    `apply_dividend_strip`, `_recompute_derived`), so the cache carries the real drip defect;
  * cutover step 1 — option (a)'s seam write (`full_refetch` with a fake provider: the pre-seam drip
    KEPT, the post-seam span the provider's, `close_unadj` added) — a copy-format file;
  * then the (a′) rewrite.
The known-good names are a non-payer and a payer whose Stooq is total return in every era (b = 0).
Each lock is reversion-proven (the record is in the T-387 commit message)."""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from engines.data_manager import era_tr as et
from engines.data_manager import tr_writer as w
from engines.data_manager.convention import pre_seam_spans, substrate_convention_record
from engines.data_manager.coverage import PRE_SEAM_DRIP_GAP, stale_files_record

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


merge = _load("_merge_t082b_for_t387", "scripts/merge_stooq_alpaca_substrate.py")
cs = _load("_cutover_step1_pass_for_t387", "scripts/cutover_step1_pass.py")

TICKER = "PLNT"
SEAM = pd.Timestamp("2018-01-02")
DATES = pd.bdate_range("2001-01-02", "2025-06-30")
CACHE_END = pd.Timestamp("2025-03-31")       # the merged cache's last bar; the provider runs to TODAY
TODAY = DATES[-1]
TRUE_MISSED = ((pd.Timestamp("2003-04-01"), pd.Timestamp("2011-02-21")),
               (pd.Timestamp("2022-12-19"), pd.Timestamp("2262-01-01")))
NO_CONV = {s: {} for s in w.CONVENTION_SECTIONS}


# ── the planted world ──────────────────────────────────────────────────────────

def _price_path(seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    return pd.Series(50.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.012, len(DATES)))), index=DATES)


def _dividends(close: pd.Series, quarterly_yield: float) -> pd.Series:
    if quarterly_yield <= 0:
        return pd.Series(dtype=float, name="dividend")
    m = DATES.month.isin([2, 5, 8, 11]) & (DATES.day <= 7)
    ex = pd.DatetimeIndex(pd.Series(DATES[m], index=DATES[m]).groupby([DATES[m].year, DATES[m].month]).first().values)
    return pd.Series(np.round(quarterly_yield * close.shift(1).reindex(ex).to_numpy(), 4), index=ex,
                     name="dividend").dropna()


def _back_adjust(close: pd.Series, divs: pd.Series, include: np.ndarray) -> pd.Series:
    """close × Π_{e > t, include[e]} (1 − D_e / P_{e−1})."""
    if not len(divs):
        return close.copy()
    pos = close.index.searchsorted(divs.index)
    log_f = np.where(include, np.log1p(-divs.to_numpy() / close.to_numpy()[pos - 1]), 0.0)
    acc = np.zeros(len(close) + 1)
    np.add.at(acc, pos, log_f)
    return close * np.exp(acc.sum() - np.cumsum(acc)[: len(close)])


def _missed(ex: pd.DatetimeIndex) -> np.ndarray:
    out = np.zeros(len(ex), dtype=bool)
    for lo, hi in TRUE_MISSED:
        out |= (ex >= lo) & (ex < hi)
    return out


def _ohlcv(close: pd.Series) -> pd.DataFrame:
    return pd.DataFrame({"Date": close.index, "Open": close.to_numpy() * 0.999, "High": close.to_numpy() * 1.01,
                         "Low": close.to_numpy() * 0.99, "Close": close.to_numpy(), "Volume": 1_000_000.0}
                        ).reset_index(drop=True)


@dataclass
class Planted:
    close: pd.Series      # the price that traded (the provider's split-only mode)
    divs: pd.Series
    tr: pd.Series         # the TRUE total return as of TODAY (the provider's adjusted mode, the reference)
    stooq: pd.Series      # the raw Stooq bundle
    text: str             # the merged cache file, as T-082b wrote it
    meta: dict            # its merge record


def _plant(seed: int, quarterly_yield: float, stooq_missed: bool, post_seam_block: bool = False) -> Planted:
    close = _price_path(seed)
    divs = _dividends(close, quarterly_yield)
    ex = pd.DatetimeIndex(divs.index)
    tr = _back_adjust(close, divs, np.ones(len(divs), dtype=bool))
    stooq = (_back_adjust(close, divs, ~_missed(ex)) if (len(divs) and stooq_missed) else tr.copy()).round(6)
    if post_seam_block:     # a Stooq block offset inside the merge's first 30 overlap days: the merge's
        i = stooq.index.get_loc(SEAM)          # median intercept sits off the seam-day ratio, so k matters
        stooq.iloc[i + 3:i + 26] *= 1.02
    alpaca_w = _back_adjust(close, divs, np.asarray(ex <= CACHE_END))      # TR as of the merge's write date
    s_df = _ohlcv(stooq[stooq.index <= CACHE_END])
    a_df = _ohlcv(alpaca_w[(alpaca_w.index >= SEAM) & (alpaca_w.index <= CACHE_END)])
    fit = merge.fit_ratio_loglinear(s_df, a_df)
    assert fit is not None
    pre = s_df[s_df["Date"] < SEAM].copy()
    merged = pd.concat([merge.apply_dividend_strip(pre, fit)[["Date", "Open", "High", "Low", "Close", "Volume"]],
                        a_df[["Date", "Open", "High", "Low", "Close", "Volume"]]], ignore_index=True)
    text = merge._recompute_derived(merged).to_csv(index=False, date_format="%Y-%m-%d")
    meta = {"ticker": TICKER, "merge_case": "both", "seam_date": str(SEAM.date()), "n_stooq_pre_seam": int(len(pre)),
            "fit_slope_per_day": fit["b"], "first_bar_date": str(DATES[0].date()),
            "last_bar_date": str(CACHE_END.date())}
    return Planted(close, divs, tr, stooq, text, meta)


@pytest.fixture(scope="module")
def defective() -> Planted:
    return _plant(seed=7, quarterly_yield=0.009, stooq_missed=True)


@pytest.fixture(scope="module")
def defective_blocked() -> Planted:
    return _plant(seed=7, quarterly_yield=0.009, stooq_missed=True, post_seam_block=True)


@pytest.fixture(scope="module")
def good_payer() -> Planted:
    return _plant(seed=13, quarterly_yield=0.009, stooq_missed=False)


@pytest.fixture(scope="module")
def good_nonpayer() -> Planted:
    return _plant(seed=11, quarterly_yield=0.0, stooq_missed=False)


def _seed_merged_cache(cache_dir: Path, p: Planted) -> Path:
    """The cache as merged: the text verbatim + its parquet twin + the merge record."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    w.write_text_pair_atomically(p.text, et.frame_from_text(p.text), cache_dir / "parquet" / f"{TICKER}_1d.parquet",
                                 cache_dir / f"{TICKER}_1d.csv")
    (cache_dir / w.MERGE_META_NAME).write_text(json.dumps({"per_ticker": {TICKER: p.meta}}))
    return cache_dir


def _provider(p: Planted):
    def fetch(symbol, start, end, adjusted):
        s = p.tr if adjusted else p.close
        s = s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
        return pd.DataFrame({"Open": s, "High": s * 1.01, "Low": s * 0.99, "Close": s, "Volume": 1e6}, index=s.index)
    return fetch


def _no_actions(symbol):
    return pd.DataFrame(columns=["Dividends", "Stock Splits"])


def _option_a_write(cache_dir: Path, p: Planted) -> w.WriteRecord:
    """Cutover step 1 (option (a)): the seam write — the drip KEPT, the provider post-seam, close_unadj."""
    return w.full_refetch(TICKER, cache_dir, {"yfinance": _provider(p)}, today=TODAY, actions=_no_actions,
                          declarations={}, conventions=NO_CONV)


def _rewrite(cache_dir: Path, p: Planted, with_reference: bool = True, **kw) -> dict:
    px = pd.DataFrame({"adj_close": p.tr, "close": p.close}) if with_reference else None
    dv = p.divs if with_reference else None
    return w.era_tr_rewrite(TICKER, cache_dir, stooq=p.stooq, reference_px=px, reference_divs=dv,
                            conventions=NO_CONV, **kw)


def _closes(cache_dir: Path) -> pd.Series:
    df = pd.read_csv(cache_dir / f"{TICKER}_1d.csv", usecols=["Date", "Close"], float_precision="round_trip")
    return pd.Series(df["Close"].to_numpy(), index=pd.DatetimeIndex(pd.to_datetime(df["Date"])))


def _yearly(a: pd.Series, b: pd.Series) -> pd.Series:
    """Full-calendar-year log-return differences a − b in pp (year-end to year-end on common dates)."""
    j = pd.concat([a.rename("a"), b.rename("b")], axis=1, join="inner").dropna()
    ends = np.log(j.groupby(j.index.year).tail(1))
    return 100 * ends.diff().dropna().pipe(lambda d: d["a"] - d["b"]).set_axis(ends.index.year[1:])


def _lines(cache_dir: Path) -> list:
    return (cache_dir / f"{TICKER}_1d.csv").read_text().split("\n")[1:-1]


def _record(cache_dir: Path) -> dict:
    return json.loads((cache_dir / w.WRITE_RECORDS_DIR / f"{TICKER}.json").read_text())


def _label(cache_dir: Path) -> dict:
    df = pd.read_csv(cache_dir / f"{TICKER}_1d.csv", usecols=["Date", "Close"], parse_dates=["Date"]).set_index("Date")
    return substrate_convention_record(cache_dir, run_names=[TICKER], data_map={TICKER: df}, conventions=NO_CONV)


# ── 1. the known-DEFECTIVE name, through the cutover's real order ─────────────

def test_a_known_defective_name_is_restored_to_total_return_through_the_cutover_order(tmp_path, defective):
    p = defective
    cache = _seed_merged_cache(tmp_path / "copy", p)
    assert p.meta["fit_slope_per_day"] * 365.25 > 0.01                      # the merge fitted a drip
    step1 = _option_a_write(cache, p)
    assert step1.convention["pre_seam"] == w.DRIP                            # option (a) kept the drip
    drip = _closes(cache)
    y0 = _yearly(drip[drip.index <= SEAM], p.tr[p.tr.index <= SEAM])
    assert (y0.loc[2005:2010] < -1.0).all() and (y0.loc[2012:2017] > 1.0).all()   # the planted defect

    rec = _rewrite(cache, p)
    got = _closes(cache)
    y = _yearly(got[got.index <= SEAM], p.tr[p.tr.index <= SEAM])
    assert y.loc[2002:2017].abs().max() < 1e-3                              # every era, to rounding
    n_missed_era = int(((p.divs.index >= "2003-04-01") & (p.divs.index < "2011-02-21")).sum())
    assert rec["era_tr"]["n_div_added"] == n_missed_era
    assert rec["era_tr"]["added_by_source"] == {"measured": n_missed_era}
    assert rec["convention"] == {"pre_seam": w.ERA_TR, "seam_date": "2018-01-02", "post_seam": w.EXACT_TR}
    assert rec["provider"] == "yfinance" and rec["seam"]["seam_ratio"] == step1.seam["seam_ratio"]  # prior kept
    assert rec["era_tr"]["rails"]["step_audit"]["n_steps_expected"] == n_missed_era
    assert _record(cache) == json.loads(json.dumps(rec, default=str))        # pinned as returned
    lab = _label(cache)
    assert lab["per_name"] == {TICKER: "era_tr<2018-01-02|exact_tr"} and lab["n_pre_seam_era_tr"] == 1
    assert lab["n_pre_seam_drip"] == 0 and lab["unverified"] == {}


# ── 2. the known-GOOD names: the rewrite moves nothing ────────────────────────

@pytest.mark.parametrize("fixture_name", ["good_payer", "good_nonpayer"])
def test_a_known_good_name_is_not_moved(tmp_path, fixture_name, request):
    p = request.getfixturevalue(fixture_name)
    assert abs(p.meta["fit_slope_per_day"]) < 1e-12                         # an exact cache: no drip
    cache = _seed_merged_cache(tmp_path / "cache", p)
    before = _closes(cache)
    rec = _rewrite(cache, p)
    after = _closes(cache)
    assert rec["era_tr"]["n_div_added"] == 0
    assert _yearly(after[after.index <= SEAM], before[before.index <= SEAM]).abs().max() < 1e-6
    assert rec["convention"]["pre_seam"] == w.ERA_TR
    assert rec["provider"].startswith("none") and rec["seam"]["n_pre_seam_bars_kept"] == p.meta["n_stooq_pre_seam"]


# ── 3. the NO-REFERENCE name: raw Stooq, LABELLED UNVERIFIED ──────────────────

def test_a_no_reference_name_stays_raw_stooq_and_its_spans_are_labelled_in_record_and_census(tmp_path, defective):
    p = defective
    cache = _seed_merged_cache(tmp_path / "cache", p)
    rec = _rewrite(cache, p, with_reference=False)
    b = rec["era_tr"]
    assert b["reference"] == "no_prices" and b["n_div_added"] == 0 and b["approx_bars"] == 0
    assert b["unverified_missed_era_spans"] == [["2003-04-01", "2011-02-18"]]
    assert "UNDER-counts" in b["unverified_missed_era_bias"]
    assert b["unverified_pre2003_span"] == ["2001-01-02", "2003-03-31"]
    got = _closes(cache)
    pre = got[got.index < SEAM]
    step = np.diff(np.log(pre.to_numpy() / p.stooq.reindex(pre.index).to_numpy()))
    assert np.abs(step).max() < et.STEP_TOL                                  # every daily return IS raw Stooq's
    lab = _label(cache)
    assert lab["unverified"] == {TICKER: {"missed_era_spans": [["2003-04-01", "2011-02-18"]],
                                          "pre2003_span": ["2001-01-02", "2003-03-31"]}}
    assert lab["n_unverified_missed_era"] == 1 and lab["n_unverified_pre2003"] == 1


# ── 4. the POST-seam span: byte-identical; the seam one constant ──────────────

@pytest.mark.parametrize("fixture_name", ["defective", "defective_blocked"])
def test_the_post_seam_span_and_close_unadj_are_byte_identical_and_the_seam_is_one_constant(tmp_path, fixture_name,
                                                                                            request):
    """`defective_blocked` plants a Stooq block in the merge's first 30 overlap days (T-384's k lock):
    there the seam constant k is far from 1, so removing it fails the writer's SPLICE RAIL, not only
    this test's seam assertion."""
    p = request.getfixturevalue(fixture_name)
    cache = _seed_merged_cache(tmp_path / "copy", p)
    _option_a_write(cache, p)
    before = _lines(cache)
    header = (cache / f"{TICKER}_1d.csv").read_text().split("\n", 1)[0]
    assert header.endswith(f",{w.CLOSE_UNADJ}")                              # the copy's 9-column layout
    rec = _rewrite(cache, p)
    if fixture_name == "defective_blocked":
        assert abs(rec["era_tr"]["k_splice"] - 1.0) > 0.01                    # k matters here (T-384's lock)
    after = _lines(cache)
    n_pre = p.meta["n_stooq_pre_seam"]
    assert len(after) == len(before)
    assert after[n_pre + et.SEAM_TEXT_ROWS:] == before[n_pre + et.SEAM_TEXT_ROWS:]   # whole lines, verbatim
    assert [ln.split(",")[:6] for ln in after[n_pre:]] == [ln.split(",")[:6] for ln in before[n_pre:]]
    assert [ln.rsplit(",", 1)[1] for ln in after] == [ln.rsplit(",", 1)[1] for ln in before]   # close_unadj, every row
    assert after[:n_pre] != before[:n_pre]                                   # and the pre-seam span DID change
    pq = pd.read_parquet(cache / "parquet" / f"{TICKER}_1d.parquet")
    pd.testing.assert_frame_equal(pq, et.frame_from_text((cache / f"{TICKER}_1d.csv").read_text()))
    got = _closes(cache)
    i = got.index.get_loc(SEAM)
    seam_ret = got.iloc[i] / got.iloc[i - 1]
    assert abs(np.log(seam_ret) - np.log(p.stooq.loc[SEAM] / p.stooq.iloc[p.stooq.index.get_loc(SEAM) - 1])) < 1e-9


# ── 5. fail closed ─────────────────────────────────────────────────────────────

def test_the_rewrite_never_runs_twice_and_refuses_a_span_that_is_not_the_drip(tmp_path, defective):
    p = defective
    cache = _seed_merged_cache(tmp_path / "copy", p)
    _option_a_write(cache, p)
    _rewrite(cache, p)
    snap = (cache / f"{TICKER}_1d.csv").read_bytes()
    with pytest.raises(w.WriterRefusal, match="applies to a drip span only"):
        _rewrite(cache, p)
    assert (cache / f"{TICKER}_1d.csv").read_bytes() == snap
    rec = _record(cache)
    rec["convention"] = {"whole": w.EXACT_TR}                                # a file written WHOLE
    (cache / w.WRITE_RECORDS_DIR / f"{TICKER}.json").write_text(json.dumps(rec))
    with pytest.raises(w.WriterRefusal, match="written WHOLE"):
        _rewrite(cache, p)


def test_write_False_measures_and_touches_nothing_and_no_merge_record_refuses(tmp_path, defective):
    p = defective
    cache = _seed_merged_cache(tmp_path / "cache", p)
    snap = {q.name: q.read_bytes() for q in cache.rglob("*") if q.is_file()}
    rec = _rewrite(cache, p, write=False)
    assert rec["convention"]["pre_seam"] == w.ERA_TR
    assert {q.name: q.read_bytes() for q in cache.rglob("*") if q.is_file()} == snap
    assert not (cache / w.WRITE_RECORDS_DIR).exists()
    (cache / w.MERGE_META_NAME).rename(cache / "_merge_meta.moved")
    with pytest.raises(w.WriterRefusal, match="never run on a guess"):
        _rewrite(cache, p)


# ── 6. after the cutover: a refresh KEEPS the era_tr label (never relabels drip) ─

def test_a_refresh_after_the_rewrite_keeps_the_era_tr_label_and_block(tmp_path, defective):
    p = defective
    cache = _seed_merged_cache(tmp_path / "copy", p)
    _option_a_write(cache, p)
    rewritten = _rewrite(cache, p)
    era = _closes(cache)
    rec = _option_a_write(cache, p)                                          # a post-cutover refresh
    assert rec.convention == {"pre_seam": w.ERA_TR, "seam_date": "2018-01-02", "post_seam": w.EXACT_TR}
    assert rec.seam["pre_seam_label_source"] == "write_record"
    assert rec.era_tr == json.loads(json.dumps(rewritten["era_tr"], default=str))
    kept = _closes(cache)
    pre = kept.index < SEAM
    lr = np.log(kept[pre].to_numpy() / era.reindex(kept.index[pre]).to_numpy())
    assert lr.max() - lr.min() < 1e-12                                       # the era_tr bars, one constant
    assert _label(cache)["per_name"] == {TICKER: "era_tr<2018-01-02|exact_tr"}


# ── 7. the census and the guard read era_tr ───────────────────────────────────

def test_the_guard_excuses_an_era_tr_spans_own_pre_seam_holes_and_the_census_requires_the_block(tmp_path):
    days = pd.bdate_range("2017-01-02", "2018-06-29")
    holes = [pd.Timestamp("2017-03-15"), pd.Timestamp("2017-09-20")]
    d = tmp_path / "cache"
    (d / w.WRITE_RECORDS_DIR).mkdir(parents=True)
    dates = days.drop(holes)
    (d / "ERA_1d.csv").write_text("\n".join(["Date,Open,High,Low,Close,Volume"]
                                            + [f"{x.date()},1,1,1,1,1" for x in dates]) + "\n")
    rec = {"ticker": "ERA", "convention": {"pre_seam": w.ERA_TR, "seam_date": "2018-01-02", "post_seam": w.EXACT_TR},
           "seam": {"date": "2018-01-02", "n_pre_seam_bars_kept": int((dates < SEAM).sum())},
           "era_tr": {"unverified_missed_era_spans": [], "unverified_pre2003_span": None}}
    (d / w.WRITE_RECORDS_DIR / "ERA.json").write_text(json.dumps(rec))
    frame = lambda ix: pd.DataFrame({"Close": 1.0}, index=pd.DatetimeIndex(ix))    # noqa: E731
    m = {t: frame(days) for t in ("SPY", "AAA", "BBB")}
    m["ERA"] = frame(dates)
    sf = stale_files_record(m, str(days[0].date()), str(days[-1].date()), declared={}, cache_dir=d)
    assert sf["names"]["ERA"]["pre_seam_drip_gap_days"] == 2 and sf["names"]["ERA"]["declared"] == [PRE_SEAM_DRIP_GAP]
    assert sf["n_holed"] == 0 and sf["pre_seam_drip_gaps"]["per_name"] == {"ERA": 2}
    del rec["era_tr"]                                                        # an era_tr record without its block
    (d / w.WRITE_RECORDS_DIR / "ERA.json").write_text(json.dumps(rec))
    spans = pre_seam_spans(d, ["ERA"], m, conventions=NO_CONV)["ERA"]
    assert "seam_date" not in spans and "no era_tr block" in spans.get("refused", "")
    sc = substrate_convention_record(d, run_names=["ERA"], data_map=m, conventions=NO_CONV)
    assert "ERA" in sc["unlabelled"] and sc["n_labelled"] == 0
    sf2 = stale_files_record(m, str(days[0].date()), str(days[-1].date()), declared={}, cache_dir=d)
    assert sf2["n_holed"] == 1                                               # fail closed: nothing excused


def test_a_declaration_may_name_era_tr_pre_seam_only(tmp_path):
    ok = tmp_path / "ok.json"
    ok.write_text(json.dumps({"seams": {"X": {"seam_date": "2018-01-02", "pre_seam": "era_tr", "post_seam": "exact_tr"}}}))
    assert w.load_convention_declarations(ok)["seams"]["X"]["pre_seam"] == w.ERA_TR
    for bad in ({"seams": {"X": {"seam_date": "2018-01-02", "pre_seam": "drip", "post_seam": "era_tr"}}},
                {"whole_file_overrides": {"X": {"convention": "era_tr"}}}):
        p = tmp_path / "bad.json"
        p.write_text(json.dumps(bad))
        with pytest.raises(ValueError):
            w.load_convention_declarations(p)


# ── 8. the cutover-day driver's reference guard (offline: never reads 'never fetched' as 'none') ─

def test_the_driver_refuses_a_reference_cache_without_its_fetch_log_or_a_name_it_never_fetched(tmp_path):
    with pytest.raises(SystemExit, match="fetch state is unknown"):
        cs.yf_fetch_state(tmp_path)
    (tmp_path / "_fetch_log.jsonl").write_text(
        json.dumps({"ticker": "OK", "prices": "ok"}) + "\n" + json.dumps({"ticker": "GONE", "prices": "no_data"}) + "\n")
    state = cs.yf_fetch_state(tmp_path)
    assert cs.reference_for("NEVER", tmp_path, state)[2].startswith("refused: NEVER has no row")
    assert cs.reference_for("OK", tmp_path, state)[2].startswith("refused: the fetch log says OK's prices were fetched")
    px, dv, status = cs.reference_for("GONE", tmp_path, state)
    assert px is None and dv is None and status == "no_reference (no_data)"


def test_the_driver_refuses_to_rewrite_the_canonical_cache():
    with pytest.raises(SystemExit, match="REFUSED"):
        cs.main(["era-tr", "--copy", str(w.CANONICAL_CACHE_DIR), "--dry-run"])


# ── 9. the T-387 review (2026-11-12): the merge-record drip fallback FAILS CLOSED after (a′) ──────

def _sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _planted_witness(cache_dir: Path, *names: str) -> dict:
    """The frozen drip-cache witness, planted: each name's csv/parquet sha256 AS MERGED (drip)."""
    out = {}
    for t in names:
        pq = cache_dir / "parquet" / f"{t}_1d.parquet"
        out[t] = {"csv": _sha(cache_dir / f"{t}_1d.csv"), **({"parquet": _sha(pq)} if pq.exists() else {})}
    return out


def test_a_rewritten_file_whose_record_is_missing_is_UNLABELLED_never_inferred_drip(tmp_path, defective):
    """The MAJOR: an era_tr file with its record set aside read `drip<…>` from the merge record. Now
    the fallback needs the file's bytes to equal the frozen drip witness; the rewrite changed them."""
    p = defective
    cache = _seed_merged_cache(tmp_path / "copy", p)
    witness = _planted_witness(cache, TICKER)
    df = pd.read_csv(cache / f"{TICKER}_1d.csv", usecols=["Date", "Close"], parse_dates=["Date"]).set_index("Date")
    before = substrate_convention_record(cache, run_names=[TICKER], data_map={TICKER: df}, conventions=NO_CONV,
                                         drip_witness=witness)
    assert before["per_name"] == {TICKER: "drip<2018-01-02|exact_tr"}            # positive control: the drip
    _rewrite(cache, p)
    rec_p = cache / w.WRITE_RECORDS_DIR / f"{TICKER}.json"
    rec_p.rename(tmp_path / "set_aside.json")                                   # the record goes missing
    r = substrate_convention_record(cache, run_names=[TICKER], data_map={TICKER: df}, conventions=NO_CONV,
                                    drip_witness=witness)
    assert r["per_name"] == {} and "NOT the drip re-pin #1 pinned" in r["unlabelled"][TICKER]
    assert "refused" in pre_seam_spans(cache, [TICKER], {TICKER: df}, conventions=NO_CONV, drip_witness=witness)[TICKER]


def test_a_post_a_prime_cache_never_infers_drip_even_for_a_byte_identical_file(tmp_path):
    """PODD/POM: (a′) leaves two files byte-identical to the drip, so the byte rule passes them. A
    cache holding ANY era_tr record is post-(a′): there a seam file without a record is unlabelled.
    And with no witness at all, nothing is labelled drip from the merge record."""
    d = tmp_path / "cache"
    (d / w.WRITE_RECORDS_DIR).mkdir(parents=True)
    entry = {"merge_case": "both", "seam_date": "2018-01-02", "n_stooq_pre_seam": 1, "first_bar_date": "2017-12-29"}
    (d / w.MERGE_META_NAME).write_text(json.dumps({"per_ticker": {"ERA": entry, "SAME": entry}}))
    for t in ("ERA", "SAME"):
        (d / f"{t}_1d.csv").write_text("Date,Open,High,Low,Close,Volume\n2017-12-29,1,1,1,1,1\n2018-01-02,1,1,1,1,1\n")
    witness = _planted_witness(d, "SAME")
    frames = {t: pd.DataFrame({"Close": [1.0]}, index=pd.DatetimeIndex(["2017-12-29"])) for t in ("ERA", "SAME")}
    ok = substrate_convention_record(d, run_names=["SAME"], data_map=frames, conventions=NO_CONV, drip_witness=witness)
    assert ok["per_name"] == {"SAME": "drip<2018-01-02|exact_tr"} and not ok["post_a_prime"]   # positive control
    nowit = substrate_convention_record(d, run_names=["SAME"], data_map=frames, conventions=NO_CONV, drip_witness=None)
    assert "no drip-cache witness" in nowit["unlabelled"]["SAME"]
    (d / w.WRITE_RECORDS_DIR / "ERA.json").write_text(json.dumps({
        "ticker": "ERA", "convention": {"pre_seam": w.ERA_TR, "seam_date": "2018-01-02", "post_seam": w.EXACT_TR},
        "seam": {"n_pre_seam_bars_kept": 1},
        "era_tr": {"unverified_missed_era_spans": [], "unverified_pre2003_span": None}}))
    r = substrate_convention_record(d, run_names=["ERA", "SAME"], data_map=frames, conventions=NO_CONV,
                                    drip_witness=witness)
    assert r["post_a_prime"] and r["per_name"] == {"ERA": "era_tr<2018-01-02|exact_tr"}
    assert "post-(a′)" in r["unlabelled"]["SAME"]


def test_an_era_tr_block_without_its_unverified_keys_is_unlabelled(tmp_path):
    """MINOR-1: a block that cannot say what is unverified is never read as fully verified."""
    d = tmp_path / "cache"
    (d / w.WRITE_RECORDS_DIR).mkdir(parents=True)
    conv = {"pre_seam": w.ERA_TR, "seam_date": "2018-01-02", "post_seam": w.EXACT_TR}
    for t, block in (("NOTE", {"note": "x"}), ("HALF", {"unverified_missed_era_spans": []}),
                     ("FULL", {"unverified_missed_era_spans": [["2005-01-03", "2006-01-03"]],
                               "unverified_pre2003_span": None})):
        (d / w.WRITE_RECORDS_DIR / f"{t}.json").write_text(json.dumps({"ticker": t, "convention": conv,
                                                                          "seam": {}, "era_tr": block}))
    r = substrate_convention_record(d, run_names=["NOTE", "HALF", "FULL"], data_map={}, conventions=NO_CONV,
                                    drip_witness=None)
    assert r["per_name"] == {"FULL": "era_tr<2018-01-02|exact_tr"}
    assert "lacks" in r["unlabelled"]["NOTE"] and "unverified_pre2003_span" in r["unlabelled"]["HALF"]
    assert r["unverified"] == {"FULL": {"missed_era_spans": [["2005-01-03", "2006-01-03"]], "pre2003_span": None}}


def test_a_seam_DECLARED_era_tr_on_a_file_with_no_record_is_refused_before_any_provider_call(tmp_path, defective):
    """MINOR-2: a declaration may name era_tr, but era_tr is only CARRIED from a record with its block."""
    p = defective
    cache = _seed_merged_cache(tmp_path / "cache", p)
    conv = {**NO_CONV, "seams": {TICKER: {"seam_date": "2018-01-02", "pre_seam": w.ERA_TR, "post_seam": w.EXACT_TR}}}
    calls = []

    def counting(symbol, start, end, adjusted):
        calls.append(symbol)
        return _provider(p)(symbol, start, end, adjusted)
    snap = (cache / f"{TICKER}_1d.csv").read_bytes()
    with pytest.raises(w.WriterRefusal, match="declared era_tr but the file has no write record"):
        w.full_refetch(TICKER, cache, {"yfinance": counting}, today=TODAY, actions=_no_actions,
                       declarations={}, conventions=conv)
    assert calls == [] and (cache / f"{TICKER}_1d.csv").read_bytes() == snap


def test_the_driver_pins_the_reference_cache_by_its_per_file_manifest(tmp_path):
    """MINOR-4: the (a′) bytes depend on every price/dividend parquet, not only the fetch log."""
    yf = tmp_path / "yf"
    yf.mkdir()
    (yf / "_fetch_log.jsonl").write_text("{}\n")
    (yf / "A.parquet").write_bytes(b"prices")
    man = tmp_path / "pin.sha256"
    man.write_text(cs.yf_cache_manifest(yf))
    assert len(cs.verify_yf_manifest(yf, man)) == 64
    (yf / "A.parquet").write_bytes(b"prices, restated")                      # a re-fetch drifted a file
    with pytest.raises(SystemExit, match="does not equal its pinned manifest"):
        cs.verify_yf_manifest(yf, man)
    with pytest.raises(SystemExit, match="is absent"):
        cs.verify_yf_manifest(yf, tmp_path / "nope.sha256")


def test_the_shipped_reference_manifest_and_drip_witness_are_the_ones_v4_and_re_pin_1_used():
    """Data locks on the two committed pins: the reference manifest lists 1,147 files (v3's yf/ set,
    which v4 read) and the drip witness names the 575 merged files with pre-seam bars."""
    from engines.data_manager.convention import DRIP_WITNESS_PATH, load_drip_witness
    lines = cs.DEFAULT_YF_MANIFEST.read_text().splitlines()
    assert len(lines) == 1147 and any(ln.endswith("  _fetch_log.jsonl") for ln in lines)
    wit = json.loads(DRIP_WITNESS_PATH.read_text())
    assert wit["n_files"] == 575 == len(load_drip_witness())
    assert wit["source_manifest"] == "config/substrate_manifest.sha256"
    assert all(set(v) == {"csv", "parquet"} and len(v["csv"]) == 64 for v in wit["files"].values())


def test_the_drip_witness_RE_DERIVES_byte_for_byte_from_re_pin_1s_manifest():
    """Round-2 review MINOR: a hand-edited hash must fail. The witness is re-derived from
    `git show 1bb6764:config/substrate_manifest.sha256` and the merge record through THE recipe
    (`convention.derive_drip_witness_text`) and must equal the committed file byte for byte. Where git
    history is unavailable (the image) or the cache has no merge record, the lock SKIPS with the reason —
    it never passes silently."""
    import subprocess
    from engines.data_manager.convention import (DRIP_WITNESS_PATH, DRIP_WITNESS_SOURCE_COMMIT,
                                                  derive_drip_witness_text)
    spec = f"{DRIP_WITNESS_SOURCE_COMMIT}:config/substrate_manifest.sha256"
    try:
        r = subprocess.run(["git", "show", spec], cwd=REPO, capture_output=True, timeout=60)
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        pytest.skip(f"git unavailable here ({e!r}) — the witness cannot be re-derived from {spec}")
    if r.returncode != 0:
        pytest.skip(f"git history unavailable here — `git show {spec}` failed: {r.stderr.decode()[:200]}")
    meta = w.CANONICAL_CACHE_DIR / w.MERGE_META_NAME
    if not meta.exists():
        pytest.skip(f"no merge record at {meta} — the witness's name set cannot be re-derived")
    derived = derive_drip_witness_text(r.stdout, meta.read_bytes())
    assert derived.encode() == DRIP_WITNESS_PATH.read_bytes(), (
        "config/drip_cache_witness_repin1.json is NOT the re-derivation from re-pin #1's manifest — a hash "
        "was edited, or the merge record changed since the witness was frozen")
