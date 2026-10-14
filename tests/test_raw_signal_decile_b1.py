"""B-1 harness (scripts/raw_signal_decile_b1.py) — prereg §11.1 steps 4–6 and §11.4.

Synthetic panels with PLANTED signals: each lock states what the harness must find and is
shown to bite by the planted structure, not by re-stating the rule.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts import build_signal_panel_b1 as b1
from scripts import raw_signal_decile_b1 as h

ROOT = Path(__file__).resolve().parents[1]
FWD = h.FWD


# ------------------------------------------------------------------ fixtures
def _spy_root(tmp_path, start="2018-12-01", end="2025-02-28", seed=1):
    days = pd.bdate_range(start, end)
    rng = np.random.RandomState(seed)
    close = 100 * np.cumprod(1 + rng.normal(0.0004, 0.01, len(days)))
    root = tmp_path / "processed"
    root.mkdir()
    pd.DataFrame({"Date": days, "Open": close, "High": close, "Low": close, "Close": close,
                  "Volume": 1e6}).to_csv(root / "SPY_1d.csv", index=False)
    return root, b1.load_ohlcv("SPY", root)


def _panel(spy, start="2019-01", end="2024-12", n=200, seed=0, cols=None):
    """cols: {signal: fn(rng, n, fwd) -> values}. fwd is drawn first so a signal can be
    PLANTED on next month's return (the harness must find it) or be pure noise."""
    mes = b1.month_ends(spy.index, start, end)
    rng = np.random.RandomState(seed)
    frames = []
    for m in mes:
        names = [f"T{i:03d}" for i in range(n)]
        fwd = rng.normal(0.008, 0.06, n)
        d = {s: fn(rng, n, fwd) for s, fn in (cols or {}).items()}
        d[FWD] = fwd
        f = pd.DataFrame(d, index=names)
        f.index = pd.MultiIndex.from_product([[m], names], names=["month_end", "ticker"])
        frames.append(f)
    return pd.concat(frames)


def _census(panel):
    sig = [c for c in panel.columns if c != FWD]
    return {"signals": {s: {"sparse": bool(np.median([b1.modal_share(
        panel.xs(m, level="month_end")[s].to_numpy(dtype=float))
        for m in panel.index.get_level_values("month_end").unique()]) > 0.5)} for s in sig}}


PLANT = {
    "mom_12_1": lambda rng, n, fwd: fwd + rng.normal(0, 0.03, n),          # declared +, planted +
    "reversal_1m": lambda rng, n, fwd: fwd + rng.normal(0, 0.03, n),       # declared −, planted +
    "skew_60d": lambda rng, n, fwd: rng.normal(size=n),                    # declared −, noise
}


def _run(tmp_path, cols=PLANT, iters=200, **kw):
    root, spy = _spy_root(tmp_path)
    panel = _panel(spy, cols=cols)
    return h.run(panel, _census(panel), "2000-01", seed=0, iters=iters, block=6,
                 price_root=root, with_calendar=False, **kw)


# ------------------------------------------------------------------ entry + identity
def test_wrong_env_pins_are_REFUSED_by_the_real_entrypoint_never_re_execd():
    env = {**os.environ, "PYTHONHASHSEED": "1"}
    r = subprocess.run([sys.executable, "-m", "scripts.raw_signal_decile_b1", "--panel", "x",
                        "--out", "y"], cwd=ROOT, env=env, capture_output=True, text=True)
    assert r.returncode == 3, r.stderr
    assert "REFUSING" in r.stderr and "PYTHONHASHSEED" in r.stderr


def test_main_REFUSES_outside_the_worktree_root(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert h.main(["--panel", "x", "--out", str(tmp_path / "o")]) == 5


def test_a_panel_whose_content_is_not_its_name_HALTS(tmp_path):
    root, spy = _spy_root(tmp_path)
    panel = _panel(spy, cols=PLANT)
    digest = b1.canonical_md5(panel)
    good = tmp_path / f"signal_panel_{digest[:12]}.parquet"
    panel.to_parquet(good)
    (tmp_path / f"census_{digest[:12]}.json").write_text(
        json.dumps({**_census(panel), "halt_reasons": [], "panel_canonical_md5": digest}))
    assert h.load_panel_checked(good)[2] == []
    tampered = panel.copy()
    tampered.iloc[0, 0] += 1.0
    tampered.to_parquet(good)                 # same name, different content
    assert any("!= its filename" in x for x in h.load_panel_checked(good)[2])


def test_a_panel_whose_census_HALTED_is_never_consumed(tmp_path):
    root, spy = _spy_root(tmp_path)
    panel = _panel(spy, cols=PLANT)
    digest = b1.canonical_md5(panel)
    p = tmp_path / f"signal_panel_{digest[:12]}.parquet"
    panel.to_parquet(p)
    (tmp_path / f"census_{digest[:12]}.json").write_text(
        json.dumps({"halt_reasons": ["x: unusable"], "panel_canonical_md5": digest}))
    assert any("HALT reasons" in x for x in h.load_panel_checked(p)[2])


# ------------------------------------------------------------------ the science locks
def test_planted_signal_is_found_noise_is_not_and_the_wrong_sign_is_NEVER_flipped(tmp_path):
    res, halts = _run(tmp_path)
    assert halts == [], halts
    rows = {r["signal"]: r for r in res["rows"]}
    assert rows["mom_12_1"]["clears_ic"] is True and rows["mom_12_1"]["ic_t_nw"] > 5
    # reversal_1m is declared − but planted +: BH rejects, the direction is wrong → NOT cleared
    assert rows["reversal_1m"]["ic_t_nw"] < -5
    assert rows["reversal_1m"]["ic_bh_reject"] is True
    assert rows["reversal_1m"]["clears_ic"] is False
    assert rows["reversal_1m"]["wrong_sign_reject"] is True
    assert rows["skew_60d"]["clears_ic"] is False
    assert res["families"]["main"]["m"] == 3


def test_the_planted_signal_beats_spy_AND_the_ew_sleeve_and_meets_h1(tmp_path):
    res, _ = _run(tmp_path)
    r = {x["signal"]: x for x in res["rows"]}["mom_12_1"]
    assert r["dlogw_vs_spy"]["ci_low"] > 0 and r["dlogw_vs_ew"]["ci_low"] > 0
    assert r["meets_h1"] is True and res["h1"]["met"] is True
    assert res["h1"]["signals_meeting"] == ["mom_12_1"]
    assert res["h1"]["n_trials_consumed"] == 4


def test_ew_tilt_is_labelled_and_does_NOT_meet_h1():
    row = {"family": "main", "ic_bh_reject": True, "ic_t_nw": 3.0,
           "dlogw_vs_spy": {"ci_low": 0.05}, "dlogw_vs_ew": {"ci_low": -0.02}}
    h.classify(row)
    assert row["ew_tilt_not_signal"] is True
    assert row["wealth_clears_both"] is False and row["meets_h1"] is False


def test_only_the_MAIN_family_can_meet_h1():
    row = {"family": "short_window", "ic_bh_reject": True, "ic_t_nw": 3.0,
           "dlogw_vs_spy": {"ci_low": 0.05}, "dlogw_vs_ew": {"ci_low": 0.02}}
    h.classify(row)
    assert row["clears_ic"] is True and row["meets_h1"] is False


def test_sensitivity_rows_are_reported_but_never_enter_a_BH_count(tmp_path):
    cols = {**PLANT, "momentum_12_1_v1": lambda rng, n, fwd:
            (fwd > np.quantile(fwd, 0.7)).astype(float)}
    res, halts = _run(tmp_path, cols=cols)
    assert halts == [], halts
    r = {x["signal"]: x for x in res["rows"]}["momentum_12_1_v1"]
    assert r["family"] == "sensitivity" and r["ic_p_bh"] is None
    assert r["clears_ic"] is None and r["meets_h1"] is None
    assert res["families"]["main"]["m"] == 3


# ------------------------------------------------------------------ §4.2 sparse rule
def test_sparse_month_with_under_10_favorable_names_takes_EW_and_is_COUNTED(tmp_path):
    """A 1/0 selection edge that selects 5 names in odd months: those months take the
    EW-universe return and are counted — never silently filled."""
    def sel(rng, n, fwd, _c=[0]):
        _c[0] += 1
        k = 5 if _c[0] % 2 else 20
        v = np.zeros(n)
        v[rng.choice(n, k, replace=False)] = 1.0
        return v
    res, halts = _run(tmp_path, cols={"momentum_12_1_v1": sel, "mom_12_1": PLANT["mom_12_1"]})
    assert halts == [], halts
    r = {x["signal"]: x for x in res["rows"]}["momentum_12_1_v1"]
    assert r["sparse"] is True
    assert r["L_n_fallback_months"] == res["benchmarks"]["main"]["n_months"] // 2


def test_select_legs_deciles_and_the_sparse_legs():
    s = pd.Series(np.arange(100, dtype=float), index=[f"T{i}" for i in range(100)])
    top, bot = h.select_legs(s, sparse=False)
    assert list(top) == [f"T{i}" for i in range(90, 100)]
    assert list(bot) == [f"T{i}" for i in range(10)]
    sp = pd.Series([1.0] * 12 + [0.3] * 3 + [0.0] * 85, index=[f"T{i}" for i in range(100)])
    top, bot = h.select_legs(sp, sparse=True)
    assert len(top) == 15 and len(bot) == 85          # favorable = signed > 0; bottom tie group
    few = pd.Series([1.0] * 4 + [0.0] * 96, index=[f"T{i}" for i in range(100)])
    assert h.select_legs(few, sparse=True)[0] is None


def test_a_TIE_at_the_top_is_never_split_or_dropped_the_drawdown_at_high_shape():
    """drawdown_60d = 0 for every name at its 60-day high. 25 of 100 tie there: under
    average ranks their rank is 88 < 90 and the top decile would be EMPTY (Arm L silently
    the EW sleeve). The whole most-favorable group is the leg."""
    vals = np.r_[np.zeros(25), -np.linspace(0.01, 0.30, 75)]
    s = pd.Series(vals, index=[f"T{i}" for i in range(100)])
    top, bot = h.select_legs(s, sparse=False)
    assert top is not None and len(top) == 25
    assert set(top) == {f"T{i}" for i in range(25)}
    assert len(bot) == 10
    ties_low = pd.Series(np.r_[np.full(30, -1.0), np.linspace(0, 1, 70)],
                         index=[f"T{i}" for i in range(100)])
    assert len(h.select_legs(ties_low, sparse=False)[1]) == 30   # bottom tie kept whole


# ------------------------------------------------------------------ costs + bootstrap
def test_leg_costs_are_10bps_round_trip_on_DRIFTED_weights():
    f1 = pd.Series({"A": 0.10, "B": -0.10, "C": 0.0})
    f2 = pd.Series({"A": 0.0, "B": 0.0, "C": 0.0})
    L = h.leg_series([pd.Index(["A", "B"]), pd.Index(["B", "C"])], [f1, f2])
    assert L["turnover"][0] == pytest.approx(1.0)               # from cash
    assert L["cost"][0] == pytest.approx(0.0005)
    # after month 1: A 0.55, B 0.45 (gross 0.0); target B 0.5, C 0.5 → |0-.55|+|.5-.45|+|.5-0|
    assert L["turnover"][1] == pytest.approx(0.55 + 0.05 + 0.5)
    assert L["cost"][1] == pytest.approx(0.0005 * 1.10)


def test_the_bootstrap_is_PAIRED_identical_series_give_exactly_zero_everywhere():
    x = np.random.RandomState(3).normal(0.01, 0.05, 120)
    out = h.boot(120, h.dlogw(x, x, x), seed=0, iters=300, block=6)
    assert out["ci_low"] == 0.0 and out["ci_high"] == 0.0
    a = h.boot(120, lambda i: float(i.sum()), seed=0, iters=50, block=6)
    b = h.boot(120, lambda i: float(i.sum()), seed=0, iters=50, block=6)
    assert a == b


def test_bh_adjust_matches_the_step_up_and_never_counts_a_nan():
    # m = 4 (the NaN is not counted): thresholds 0.0125 / 0.025 / 0.0375 / 0.05 → only 0.01
    adj, rej = h.bh_adjust([0.01, 0.04, 0.03, 0.20, float("nan")])
    assert rej == [True, False, False, False, False]
    assert adj[0] == pytest.approx(0.04)          # 4 × 0.01 / 1; with m = 5 it would be 0.05
    assert adj[2] == pytest.approx(4 * 0.04 / 3)  # step-up minimum over the larger p's
    assert np.isnan(adj[4])
    adj2, rej2 = h.bh_adjust([0.001, 0.008, 0.039, 0.041, 0.042])
    assert rej2 == [True, True, True, True, True]  # p(5)=0.042 <= 0.05 lifts every rank


# ------------------------------------------------------------------ windows + determinism
def test_a_window_under_24_months_HALTS_but_the_smoke_runs_its_first_12(tmp_path):
    root, spy = _spy_root(tmp_path)
    panel = _panel(spy, start="2019-01", end="2019-12", cols=PLANT)
    _, halts = h.run(panel, _census(panel), "2000-01", 0, 100, 6, root, with_calendar=False)
    assert any("< 24" in x for x in halts), halts
    panel = _panel(spy, cols=PLANT)
    res, halts = h.run(panel, _census(panel), "2000-01", 0, 100, 6, root,
                       with_calendar=False, smoke_months=12)
    assert halts == [] and res["benchmarks"]["main"]["n_months"] == 12


def test_the_2012_style_start_flag_trims_the_main_window(tmp_path):
    root, spy = _spy_root(tmp_path)
    panel = _panel(spy, cols=PLANT)
    res, halts = h.run(panel, _census(panel), "2021-01", 0, 100, 6, root, with_calendar=False)
    assert halts == []
    assert res["benchmarks"]["main"]["start"] == "2021-01"
    assert res["benchmarks"]["main"]["n_months"] == 48


def test_two_runs_give_the_same_canonical_md5_and_a_value_change_moves_it(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    r1, _ = _run(tmp_path / "a", iters=100)
    r2, _ = _run(tmp_path / "b", iters=100)
    assert h.canonical_results_md5(r1) == h.canonical_results_md5(r2)
    r2["rows"][0]["ic_mean"] += 1e-9
    assert h.canonical_results_md5(r1) != h.canonical_results_md5(r2)
    r1["rows"] = list(reversed(r1["rows"]))
    r2["rows"][0]["ic_mean"] -= 1e-9
    assert h.canonical_results_md5(r1) == h.canonical_results_md5(r2)


# ------------------------------------------------------------------ calendar (daily)
def test_the_FOMC_table_shape_HALTS_the_calendar_census():
    """fomc_drift's table starts 2018: constant 0.0 for 2000–2017 — the third spelling."""
    days = pd.bdate_range("2000-01-03", "2025-12-31")
    fomc = np.where((days.year >= 2018) & (days.day == 15), 1.0, 0.0)
    jan = np.where((days.month == 1) & (days.day <= 7), 1.0, 0.0)
    cen, halts = h.calendar_census(pd.DataFrame({"fomc_drift": fomc, "january_effect": jan},
                                                index=days))
    assert any(x.startswith("calendar fomc_drift") for x in halts), halts
    assert cen["fomc_drift"]["unusable_years"] == list(range(2000, 2018))
    assert not any("january_effect" in x for x in halts)


def test_ew_daily_uses_the_last_month_end_BEFORE_the_day_and_needs_both_closes():
    days = pd.bdate_range("2020-01-27", "2020-02-07")
    mes = [pd.Timestamp("2020-01-31")]
    names = [f"T{i:02d}" for i in range(12)]
    panel = pd.DataFrame({"x": 1.0}, index=pd.MultiIndex.from_product(
        [mes, names[:10]], names=["month_end", "ticker"]))
    closes = pd.DataFrame(100.0, index=days, columns=names)
    closes.loc[days > "2020-01-31", "T11"] = 200.0           # a non-member jumps: never counted
    closes.loc["2020-02-03", "T00"] = 110.0                  # a member: +10% on 02-03
    ew = h.ew_daily(panel, closes)
    assert np.isnan(ew.loc["2020-01-31"])                     # no month-end before it
    assert ew.loc["2020-02-03"] == pytest.approx(0.10 / 10)


def test_calendar_regression_reads_the_NEXT_day_return_on_todays_flag():
    days = pd.bdate_range("2010-01-01", "2015-12-31")
    rng = np.random.RandomState(0)
    flag = (rng.rand(len(days)) < 0.05).astype(float)
    ew = pd.Series(rng.normal(0, 0.01, len(days)), index=days)
    ew[np.roll(flag, 1) == 1] += 0.01                         # the day AFTER the flag pays
    rows = h.evaluate_calendar(pd.DataFrame({"fomc_drift": flag}, index=days), ew)
    assert rows[0]["t_nw"] > 5 and rows[0]["nw_lags"] == h.nw_auto_lags(rows[0]["n_days"])
