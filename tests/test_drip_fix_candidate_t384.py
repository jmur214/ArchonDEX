"""T-384 — option (a′), the era-aware drip repair: planted known-good and known-defective names.

Every series here is SYNTHETIC and built in memory; nothing reads or writes the real cache.

The defective name is built exactly the way the real defect arose:
  * a dividend payer whose "Stooq" series misses every dividend with an ex-date in
    [2003-04-01, 2011-02-21) and from 2022-12-19 (the measured eras), and captures the rest;
  * a total-return "Alpaca" leg from the seam on;
  * the cache made by the T-082b merge's OWN functions (`fit_ratio_loglinear`,
    `apply_dividend_strip`, `_recompute_derived`) — so the planted cache carries the real
    over-count (2011-Q2 → seam) and under-count (2003-Q2 → 2011-Q1).
The known-good names are a non-payer and a payer whose Stooq series is total return in every era
(with b = 0): the repair must leave both exactly where they were.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fix = _load("_drip_fix_t384", "scripts/drip_fix_candidate_t384.py")
merge = _load("_merge_t082b_for_t384", "scripts/merge_stooq_alpaca_substrate.py")

SEAM = pd.Timestamp("2018-01-02")
DATES = pd.bdate_range("2001-01-02", "2025-06-30")
TRUE_MISSED = ((pd.Timestamp("2003-04-01"), pd.Timestamp("2011-02-21")),
               (pd.Timestamp("2022-12-19"), pd.Timestamp("2262-01-01")))


def _price_path(seed: int) -> pd.Series:
    rng = np.random.default_rng(seed)
    r = rng.normal(0.0003, 0.012, len(DATES))
    return pd.Series(50.0 * np.exp(np.cumsum(r)), index=DATES)


def _dividends(close: pd.Series, quarterly_yield: float) -> pd.Series:
    months = (DATES.month.isin([2, 5, 8, 11])) & (DATES.day <= 7)
    first = pd.Series(DATES[months], index=DATES[months]).groupby([DATES[months].year, DATES[months].month]).first()
    ex = pd.DatetimeIndex(first.values)
    prev = close.shift(1).reindex(ex)
    return pd.Series(np.round(quarterly_yield * prev.to_numpy(), 4), index=ex, name="dividend").dropna()


def _back_adjust(close: pd.Series, divs: pd.Series, include: np.ndarray) -> pd.Series:
    """close × Π_{e > t, include[e]} (1 − D_e / P_{e−1})."""
    pos = close.index.searchsorted(divs.index)
    prev = close.to_numpy()[pos - 1]
    log_f = np.where(include, np.log1p(-divs.to_numpy() / prev), 0.0)
    acc = np.zeros(len(close) + 1)
    np.add.at(acc, pos, log_f)
    log_m = acc.sum() - np.cumsum(acc)[: len(close)]
    return close * np.exp(log_m)


def _missed(ex: pd.DatetimeIndex) -> np.ndarray:
    out = np.zeros(len(ex), dtype=bool)
    for lo, hi in TRUE_MISSED:
        out |= (ex >= lo) & (ex < hi)
    return out


def _ohlcv(close: pd.Series) -> pd.DataFrame:
    df = pd.DataFrame({"Date": close.index, "Open": close.to_numpy() * 0.999,
                       "High": close.to_numpy() * 1.01, "Low": close.to_numpy() * 0.99,
                       "Close": close.to_numpy(), "Volume": 1_000_000.0})
    return df.reset_index(drop=True)


def _merge_cache(stooq: pd.Series, alpaca_tr: pd.Series) -> tuple[str, dict]:
    """The planted cache, made by the T-082b merge's own functions."""
    s_df, a_df = _ohlcv(stooq), _ohlcv(alpaca_tr[alpaca_tr.index >= SEAM])
    fit = merge.fit_ratio_loglinear(s_df, a_df)
    assert fit is not None
    pre = s_df[s_df["Date"] < SEAM].copy()
    corrected = merge.apply_dividend_strip(pre, fit)
    merged = pd.concat([corrected[["Date", "Open", "High", "Low", "Close", "Volume"]],
                        a_df[["Date", "Open", "High", "Low", "Close", "Volume"]]], ignore_index=True)
    merged = merge._recompute_derived(merged)
    text = merged.to_csv(index=False, date_format="%Y-%m-%d")
    meta = {"merge_case": "both", "seam_date": str(SEAM.date()), "n_stooq_pre_seam": int(len(pre)),
            "fit_slope_per_day": fit["b"]}
    return text, meta


def _split_text(text: str) -> tuple[str, list[str]]:
    lines = text.split("\n")
    if lines[-1] == "":
        lines = lines[:-1]
    return lines[0], lines[1:]


def _frame(text: str) -> pd.DataFrame:
    import io
    df = pd.read_csv(io.StringIO(text), float_precision="round_trip")
    df["Date"] = pd.to_datetime(df["Date"])
    return df


def _name(seed: int, quarterly_yield: float, stooq_missed: bool):
    """(true TR, yf close, dividends, raw Stooq, cache text, meta) for one planted name."""
    close = _price_path(seed)
    divs = _dividends(close, quarterly_yield) if quarterly_yield > 0 else pd.Series(dtype=float, name="dividend")
    tr = _back_adjust(close, divs, np.ones(len(divs), dtype=bool)) if len(divs) else close.copy()
    if len(divs) and stooq_missed:
        stooq = _back_adjust(close, divs, ~_missed(pd.DatetimeIndex(divs.index)))
    else:
        stooq = tr.copy()
    stooq = stooq.round(6)
    text, meta = _merge_cache(stooq, tr * 1.0)
    return tr, close, divs, stooq, text, meta


def _build(tr, close, divs, stooq, text, meta, with_reference: bool = True):
    px = pd.DataFrame({"adj_close": tr, "close": close}) if with_reference else None
    dv = divs if with_reference else None
    ref = fix.analyse_reference("PLANT", stooq, px, dv, SEAM)
    yields = pd.Series(0.02, index=range(1995, 2027))
    header, lines = _split_text(text)
    res = fix.build_file("PLANT", meta, header, lines, _frame(text), stooq, ref, yields)
    return res, ref


def _yearly(a: pd.Series, b: pd.Series) -> pd.DataFrame:
    p = fix.yearly_periods(a, b)
    return p[p["full_year"]].set_index("year")


def _closes(text: str) -> pd.Series:
    df = _frame(text)
    return pd.Series(df["Close"].to_numpy(), index=pd.DatetimeIndex(df["Date"]))


# ── the planted pair ──────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def defective():
    return _name(seed=7, quarterly_yield=0.009, stooq_missed=True)


@pytest.fixture(scope="module")
def good_nonpayer():
    return _name(seed=11, quarterly_yield=0.0, stooq_missed=False)


@pytest.fixture(scope="module")
def good_payer():
    return _name(seed=13, quarterly_yield=0.009, stooq_missed=False)


def test_the_planted_cache_carries_the_real_defect(defective):
    tr, _, _, _, text, meta = defective
    assert meta["fit_slope_per_day"] * 365.25 > 0.01          # the merge fitted a drip of > 1 %/yr
    pre = _closes(text)
    y = _yearly(pre[pre.index < SEAM], tr[tr.index < SEAM])
    assert (y.loc[2005:2010, "x_pp"] < -1.0).all()            # under-count in the missed era
    assert (y.loc[2012:2017, "x_pp"] > 1.0).all()             # over-count where Stooq was already TR


def test_the_repair_moves_the_defective_name_onto_total_return(defective):
    tr, close, divs, stooq, text, meta = defective
    res, ref = _build(tr, close, divs, stooq, text, meta)
    cand = _closes(res.text)
    y = _yearly(cand[cand.index <= SEAM], tr[tr.index <= SEAM])
    assert y.loc[2002:2017, "x_pp"].abs().max() < 1e-3       # every era, exact to rounding
    # the missed era was found by measurement, not by the global rule
    lab = ref.labels
    in_era = (pd.DatetimeIndex(lab["day"]) >= "2003-04-01") & (pd.DatetimeIndex(lab["day"]) < "2011-02-21")
    assert lab.loc[in_era, "missed"].all() and not lab.loc[~in_era & (pd.DatetimeIndex(lab["day"]) < SEAM), "missed"].any()
    assert (lab["label_source"] == "measured").all()
    assert res.record["n_div_added"] == int(in_era.sum())
    # the seam-day return is Stooq's own (which equals the true TR here)
    assert abs(res.record["seam_ret_candidate"] - (tr.loc[SEAM] / tr.shift(1).loc[SEAM] - 1)) < 1e-6


@pytest.mark.parametrize("fixture_name", ["good_nonpayer", "good_payer"])
def test_the_repair_does_not_move_a_known_good_name(fixture_name, request):
    tr, close, divs, stooq, text, meta = request.getfixturevalue(fixture_name)
    assert abs(meta["fit_slope_per_day"]) < 1e-12           # an exact cache: the merge fitted no drip
    res, _ = _build(tr, close, divs, stooq, text, meta)
    assert res.record["n_div_added"] == 0
    old, new = _closes(text), _closes(res.text)
    y = _yearly(new[new.index <= SEAM], old[old.index <= SEAM])
    assert y["x_pp"].abs().max() < 1e-6                       # identical returns, every year (float floor)


def test_post_seam_text_is_byte_identical(defective):
    tr, close, divs, stooq, text, meta = defective
    res, _ = _build(tr, close, divs, stooq, text, meta)
    _, old_lines = _split_text(text)
    _, new_lines = _split_text(res.text)
    n_pre = meta["n_stooq_pre_seam"]
    assert fix.check_post_seam_bytes(new_lines, old_lines, n_pre) == []
    assert new_lines[n_pre + fix.SEAM_TEXT_ROWS:] == old_lines[n_pre + fix.SEAM_TEXT_ROWS:]
    # and the check is not vacuous: a one-digit change in a post-seam close is caught
    tampered = list(new_lines)
    f = tampered[n_pre + 100].split(",")
    f[4] = f[4][:-1] + ("1" if f[4][-1] != "1" else "2")
    tampered[n_pre + 100] = ",".join(f)
    assert fix.check_post_seam_bytes(tampered, old_lines, n_pre)


def test_a_captured_spin_off_inside_the_missed_era_is_not_added(defective):
    """MO/Kraft 2007 class: a large distribution Stooq DID apply, inside the missed era."""
    tr, close, divs, stooq, text, meta = defective
    spin_day = pd.Timestamp("2007-04-02")
    pos = close.index.searchsorted(spin_day)
    spin = pd.Series([round(0.25 * close.iloc[pos - 1], 4)], index=[close.index[pos]])
    divs2 = pd.concat([divs, spin]).sort_index()
    inc_tr = np.ones(len(divs2), dtype=bool)
    tr2 = _back_adjust(close, divs2, inc_tr)
    inc_st = ~_missed(pd.DatetimeIndex(divs2.index)) | (divs2.index == close.index[pos])
    stooq2 = _back_adjust(close, divs2, inc_st).round(6)
    text2, meta2 = _merge_cache(stooq2, tr2)
    res, ref = _build(tr2, close, divs2, stooq2, text2, meta2)
    row = ref.labels[pd.DatetimeIndex(ref.labels["day"]) == close.index[pos]]
    assert len(row) == 1 and not bool(row["missed"].iloc[0])
    cand = _closes(res.text)
    y = _yearly(cand[cand.index <= SEAM], tr2[tr2.index <= SEAM])
    assert abs(y.loc[2007, "x_pp"]) < 1e-3


def test_no_reference_uses_the_labelled_approximation_in_the_missed_era_only(defective):
    tr, close, divs, stooq, text, meta = defective
    res, ref = _build(tr, close, divs, stooq, text, meta, with_reference=False)
    assert ref.status == "no_prices"
    rec = res.record
    assert rec["n_div_added"] == 0
    assert rec["approx_years"] == list(range(2003, 2012))
    assert rec["unverified_pre2003_bars"] > 0
    cand = _closes(res.text)
    raw_y = _yearly(stooq[stooq.index < SEAM], stooq[stooq.index < SEAM])
    cy = _yearly(cand[cand.index < SEAM], stooq[stooq.index < SEAM])
    assert raw_y["x_pp"].abs().max() == 0.0
    assert abs(cy.loc[2006, "x_pp"] - 2.0) < 0.01              # the declared 2 % median drift
    assert cy.loc[2012:2016, "x_pp"].abs().max() < 1e-9        # nothing outside the missed era


def test_refuses_a_cache_that_is_not_the_raw_stooq_series(defective):
    tr, close, divs, stooq, text, meta = defective
    other = stooq.copy()
    other.iloc[500] *= 1.01                                    # one bar of a different series
    ref = fix.analyse_reference("PLANT", other, pd.DataFrame({"adj_close": tr, "close": close}), divs, SEAM)
    header, lines = _split_text(text)
    with pytest.raises(fix.CandidateRefusal, match="not proportional"):
        fix.build_file("PLANT", meta, header, lines, _frame(text), other, ref, pd.Series(0.02, index=range(1995, 2027)))


def test_label_rule_neighbours_and_blocks():
    days = pd.DatetimeIndex(["1998-02-02", "1998-05-01", "1998-08-03", "2004-02-02", "2004-05-03",
                             "2004-08-02"])
    probe = pd.DataFrame({"day": days, "m": [1.0, np.nan, 1.0, np.nan, 0.0, np.nan],
                          "sm": [0.01, 9.0, 0.01, 9.0, 0.01, 9.0],
                          "confident": [True, False, True, False, True, False]})
    lab = fix.label_exdates(probe)
    # 1998-05: both neighbours measured missed → missed (a pre-2003 per-name missed era, BA class)
    # 2004-02: neighbours disagree → the global rule (missed era) decides
    # 2004-08: one neighbour, measured captured, in the same block → captured (a measured exception)
    assert lab["missed"].tolist() == [True, True, True, True, False, False]
    assert lab["label_source"].tolist() == ["measured", "neighbours", "measured", "global", "measured",
                                            "neighbour_same_block"]
    # a one-sided neighbour in ANOTHER block does not lend its label: the global rule decides
    probe2 = pd.DataFrame({"day": pd.DatetimeIndex(["2004-02-02", "2012-02-01"]), "m": [np.nan, 0.0],
                           "sm": [9.0, 0.01], "confident": [False, True]})
    lab2 = fix.label_exdates(probe2)
    assert lab2["missed"].tolist() == [True, False]
    assert lab2["label_source"].tolist() == ["global", "measured"]


def test_missed_log_factor_back_adjusts_bars_before_the_ex_date():
    dates = pd.bdate_range("2020-01-01", periods=6)
    lm = fix.missed_log_factor(dates, pd.DatetimeIndex([dates[3]]), np.array([np.log(0.98)]))
    assert np.allclose(lm, [np.log(0.98)] * 3 + [0.0] * 3)
    # an ex-date after the last bar (the seam day) scales every bar
    lm2 = fix.missed_log_factor(dates, pd.DatetimeIndex([dates[-1] + pd.Timedelta(days=3)]), np.array([np.log(0.99)]))
    assert np.allclose(lm2, np.log(0.99))


def test_refuses_to_write_inside_the_repository_data_tree(tmp_path):
    with pytest.raises(SystemExit, match="REFUSED"):
        fix.assert_outside_canon(fix.CACHE_DIR)
    with pytest.raises(SystemExit, match="REFUSED"):
        fix.assert_outside_canon(fix.REPO / "data" / "processed" / "tr_reconciled")
    assert fix.assert_outside_canon(tmp_path) == Path(str(tmp_path)).resolve()
