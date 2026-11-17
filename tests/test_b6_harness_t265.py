"""B-6 T-265 arm harness — identity (AMENDMENT 4's holder rule, frozen in A9), deaths and costs (B-2
by reference), the §7.7 floors after the band, the freeze manifest, and the composite the review
found unguarded: H_OOS's sign and pass rule, the short-leg sign, the signal date rule, the tercile
cuts, the death penalties, the gate's 1.25th-percentile ci_low, the satellite weight, the Newey-West
lags and the ADV high edge. Synthetic inputs only; no network, no real price."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from scripts.lazy_prices import b6_harness_t265 as T


def _panel(n_days: int = 70, closes: dict | None = None, deaths: dict | None = None,
           adv: dict | None = None, holders: dict | None = None, cik2t: dict | None = None,
           segs: dict | None = None, ambiguous: set | None = None) -> T.Panel:
    cal = pd.bdate_range("2016-01-04", periods=n_days)
    closes = closes or {}
    ids = list(closes)
    C = np.column_stack([closes[s] for s in ids]) if ids else np.empty((n_days, 0))
    FF = np.array(pd.DataFrame(C).ffill().to_numpy(), dtype=float, copy=True)
    death_pos = np.array([(deaths or {}).get(s, -1) for s in ids])
    for j, d in enumerate(death_pos):
        if d >= 0:
            FF[d + 1:, j] = np.nan
    A = np.column_stack([np.full(n_days, (adv or {}).get(s, 5e6)) for s in ids]) if ids else C
    seg_by_ticker = segs or {s.split("#")[0]: [(cal[0], cal[-1], s)] for s in ids}
    bil = pd.Series(np.linspace(1.0, 1.01, n_days), index=cal)
    spy = pd.Series(np.linspace(1.0, 1.05, n_days), index=cal)
    return T.Panel(cal, C, FF, A, ids, {s: j for j, s in enumerate(ids)}, death_pos,
                   np.array([d < 0 for d in death_pos]), seg_by_ticker,
                   cik2t or {i + 1: s.split("#")[0] for i, s in enumerate(ids)}, ambiguous or set(),
                   holders or {}, spy, spy, bil, {})


def test_alive_name_is_carried_at_its_last_traded_close():
    c = np.linspace(10, 20, 70)
    c[30:35] = np.nan                                   # a short halt: priced at the stale trade
    P = _panel(closes={"AAA#0": c})
    bil = P.bil.to_numpy()
    V, died = T.name_values(P, ["AAA#0"], 0, [20, 33, 60], -0.30, bil)
    assert not died.any()
    assert V[0, 1] == pytest.approx(c[29] / c[0])
    assert V[0, 2] == pytest.approx(c[60] / c[0])


def test_death_inside_the_quarter_takes_D_then_bil():
    c = np.linspace(10, 20, 70)
    c[41:] = np.nan
    P = _panel(closes={"DED#0": c}, deaths={"DED#0": 40})
    bil = P.bil.to_numpy()
    V, died = T.name_values(P, ["DED#0"], 5, [20, 50, 60], -0.30, bil)
    assert died.all()
    assert V[0, 0] == pytest.approx(c[20] / c[5])
    assert V[0, 1] == pytest.approx(c[40] / c[5] * 0.70 * bil[50] / bil[40])
    V0, _ = T.name_values(P, ["DED#0"], 5, [20, 50, 60], 0.0, bil)
    assert V0[0, 2] == pytest.approx(c[40] / c[5] * bil[60] / bil[40])


def test_death_on_the_formation_day_takes_D_from_that_close():
    c = np.linspace(10, 20, 70)
    c[21:] = np.nan
    P = _panel(closes={"LST#0": c}, deaths={"LST#0": 20})
    bil = P.bil.to_numpy()
    V, died = T.name_values(P, ["LST#0"], 20, [30, 40], -1.0, bil)
    assert died.all() and np.allclose(V, 0.0)


def test_nan_without_a_death_halts():
    c = np.linspace(10, 20, 70)
    c[45:] = np.nan                                     # bars end, but no death recorded
    P = _panel(closes={"BAD#0": c})
    P.FF[45:, 0] = np.nan
    with pytest.raises(T.Halt):
        T.name_values(P, ["BAD#0"], 0, [20, 50], -0.30, P.bil.to_numpy())


def test_costs_by_adv_bucket_and_dead_proceeds_sell_free():
    c = np.full(70, 10.0)
    P = _panel(closes={"SML#0": c, "MIC#0": c, "OLD#0": c, "DED#0": c},
               adv={"SML#0": 5e7, "MIC#0": 5e6, "OLD#0": 3e7})
    bil = P.bil.to_numpy()
    advs = {"SML#0": 5e7, "MIC#0": 5e6}
    prev = {"OLD#0": 0.5, "DED#0": 0.5}
    r, w_end, dead, cost, turn, nd = T.leg_quarter(P, ["SML#0", "MIC#0"], advs, 10, [20, 30], 0.0, bil,
                                                   prev, {"DED#0"}, "gate")
    # buys: 0.5 at 35 bps + 0.5 at 75 bps; sell OLD 0.5 at its bucket ($30M -> 35 bps); DED free
    assert cost == pytest.approx(0.5 * 0.0035 + 0.5 * 0.0075 + 0.5 * 0.0035)
    assert turn == pytest.approx(1.5)
    assert r[0] == pytest.approx(-cost)
    _, _, _, gross, _, _ = T.leg_quarter(P, ["SML#0", "MIC#0"], advs, 10, [20, 30], 0.0, bil, prev,
                                         {"DED#0"}, "none")
    assert gross == 0.0
    _, _, _, flat, _, _ = T.leg_quarter(P, ["SML#0", "MIC#0"], advs, 10, [20, 30], 0.0, bil, prev,
                                        {"DED#0"}, "flat75")
    assert flat == pytest.approx(1.5 * 0.00375)


def test_a_name_leaving_the_leg_is_charged_even_if_still_ranked_elsewhere():
    c = np.full(70, 10.0)
    P = _panel(closes={"KEEP#0": c, "LEFT#0": c}, adv={"KEEP#0": 5e6, "LEFT#0": 5e6})
    bil = P.bil.to_numpy()
    _, _, _, cost, _, _ = T.leg_quarter(P, ["KEEP#0"], {"KEEP#0": 5e6, "LEFT#0": 5e6}, 10, [20], 0.0,
                                        bil, {"KEEP#0": 0.5, "LEFT#0": 0.5}, set(), "gate")
    assert cost == pytest.approx(0.5 * 0.0075 + 0.5 * 0.0075)


def test_identity_ambiguous_ticker_needs_a_unique_date_aware_holder():
    c = np.full(70, 10.0)
    P = _panel(closes={"SHR#0": c}, cik2t={1: "SHR", 2: "SHR"}, ambiguous={"SHR"},
               holders={"SHR": [(1, pd.Timestamp("2015-01-01"), pd.Timestamp("2016-01-20")),
                                (2, pd.Timestamp("2016-06-01"), pd.Timestamp("2026-01-01"))]})
    t_early, t_late = P.cal[2], P.cal[60]
    assert P.resolve(1, t_early) == ("SHR#0", "ok")
    assert P.resolve(2, t_early) == (None, "identity_unresolved")    # 2 is not yet a holder
    assert P.resolve(1, t_late) == (None, "identity_unresolved")     # both within the padding
    P.holders["SHR"] = [(2, pd.Timestamp("2016-06-01"), pd.Timestamp("2026-01-01"))]
    assert P.resolve(2, t_late) == ("SHR#0", "ok")
    P.holders = {}
    assert P.resolve(2, t_late) == (None, "identity_unresolved")     # no record -> not attributable


def test_identity_reused_ticker_uses_the_segment_alive_at_t():
    c = np.full(70, 10.0)
    cal = pd.bdate_range("2016-01-04", periods=70)
    segs = {"RUS": [(cal[0], cal[20], "RUS#0"), (cal[40], cal[69], "RUS#1")]}
    P = _panel(closes={"RUS#0": c, "RUS#1": c}, segs=segs, cik2t={7: "RUS"}, ambiguous={"RUS"},
               holders={"RUS": [(7, cal[0], cal[69])]})
    assert P.resolve(7, cal[10]) == ("RUS#0", "ok")
    assert P.resolve(7, cal[30]) == (None, "no_live_segment")
    assert P.resolve(7, cal[50]) == ("RUS#1", "ok")
    assert P.resolve(8, cal[50]) == (None, "no_price_file")


def test_floors_are_checked_after_the_band_and_halt():
    ok = pd.DataFrame([{"rebalance": "2016-03-31", "ranked": 300, "long": 100, "short": 100}])
    assert T.check_census(ok) == []
    thin = pd.DataFrame([{"rebalance": "2016-03-31", "ranked": 299, "long": 100, "short": 100},
                         {"rebalance": "2016-06-30", "ranked": 900, "long": 39, "short": 300}])
    bad = T.check_census(thin)
    assert len(bad) == 2 and "299" in bad[0] and "39" in bad[1]


def test_eligibility_band_trade_and_survivor_filters():
    c = np.full(70, 10.0)
    c_no = c.copy()
    c_no[50] = np.nan
    P = _panel(closes={"INB#0": c, "LOW#0": c, "HIG#0": c, "NOT#0": c_no, "DIE#0": c},
               adv={"INB#0": 5e6, "LOW#0": 5e5, "HIG#0": 3e8, "NOT#0": 5e6, "DIE#0": 5e6},
               cik2t={1: "INB", 2: "LOW", 3: "HIG", 4: "NOT", 5: "DIE"})
    P.survivor[P.col["DIE#0"]] = False
    t = P.cal[50]
    sig = pd.DataFrame({"cik": [1, 2, 3, 4, 5], "form": ["10-Q"] * 5, "accession": list("abcde"),
                        "yoy_mda_cos": [0.9] * 5, "yoy_mda_why": ["ok"] * 5,
                        "yoy_combo_cos": [np.nan] * 5, "yoy_combo_why": ["x"] * 5,
                        "floor": [t - pd.Timedelta(days=10)] * 5, "acc": [t - pd.Timedelta(days=11)] * 5,
                        "acceptance_dt": ["x"] * 5})
    df, cause = T.eligible_at(T.SPECS["gate_similarity"], sig, P, t)
    assert sorted(df.cik) == [1, 5]
    assert cause["adv_lt_1M"] == 1 and cause["adv_ge_200M"] == 1 and cause["no_trade_at_t"] == 1
    df2, cause2 = T.eligible_at(T.SPECS["survivor_similarity"], sig, P, t)
    assert sorted(df2.cik) == [1] and cause2["not_survivor"] == 1


def test_hoos_spec_is_the_sp_q10_adjacent_construction_gross():
    from scripts.lazy_prices import b6_harness_sp as H
    h, s = T.SPECS["hoos_adjacent"], H.SPECS["q10_adjacent"]
    assert (h.col_10k, h.col_10q, h.why_10k, h.why_10q) == (s.col_10k, s.col_10q, s.why_10k, s.why_10q)
    assert h.cost == "none" and h.death == "base" and h.forms == ("10-K", "10-Q") and not h.gate
    g = T.SPECS["gate_similarity"]
    assert (g.cost, g.death) == ("gate", "base") and T.HOOS_T == -2.0


def test_manifest_halts_on_an_added_or_changed_file(tmp_path, monkeypatch):
    d = tmp_path / "sig"
    d.mkdir()
    pd.DataFrame({"cik": [1, 2]}).to_parquet(d / "signals_a.parquet", index=False)
    sp = tmp_path / "sp.parquet"
    pd.DataFrame({"cik": [3]}).to_parquet(sp, index=False)
    monkeypatch.setattr(T, "T265_SIG_DIR", d)
    monkeypatch.setattr(T, "SP_V2_SIGNALS", sp)
    from scripts.lazy_prices import b6_signals as S
    monkeypatch.setattr(S, "lm_md5", lambda: T.LM_MD5)
    monkeypatch.setattr(S, "load_lm", lambda: {})
    man = tmp_path / "m.json"
    man.write_text(json.dumps(T.manifest_now()))
    assert T.verify_manifest(man)["n_files"] == 1
    pd.DataFrame({"cik": [9]}).to_parquet(d / "signals_b.parquet", index=False)
    with pytest.raises(T.Halt):
        T.verify_manifest(man)
    (d / "signals_b.parquet").rename(tmp_path / "moved.parquet")
    pd.DataFrame({"cik": [1, 2, 3]}).to_parquet(d / "signals_a.parquet", index=False)
    with pytest.raises(T.Halt):
        T.verify_manifest(man)
    with pytest.raises(T.Halt):
        T.verify_manifest(tmp_path / "absent.json")


def _synthetic_world(seed: int = 3, mix: bool = True):
    """A small end-to-end world: 30 names over three years, one death, random walks."""
    rng = np.random.default_rng(seed)
    cal = pd.bdate_range("2016-01-04", "2018-12-31")
    n = len(cal)
    closes, deaths = {}, {}
    for k in range(30):
        c = 10.0 * np.exp(np.cumsum(rng.normal(0.0003, 0.02, n)))
        sid = f"N{k:02d}#0"
        if k == 0:
            c[400:] = np.nan
            deaths[sid] = 399
        closes[sid] = c
    P = _panel(n_days=n, closes=closes, deaths=deaths,
               adv={s: 5e6 if i % 2 else 5e7 for i, s in enumerate(closes)})
    P.cal = cal
    P.spy = pd.Series(np.exp(np.cumsum(rng.normal(0.0004, 0.01, n))), index=cal)
    P.iwm = pd.Series(np.exp(np.cumsum(rng.normal(0.0003, 0.012, n))), index=cal)
    P.bil = pd.Series(np.linspace(1.0, 1.03, n), index=cal)
    P.seg_by_ticker = {s.split("#")[0]: [(cal[0], cal[deaths.get(s, n - 1)], s)] for s in closes}
    rows = []
    for k in range(30):
        for q, d in enumerate(pd.date_range("2016-02-01", "2018-11-15", freq="QS-FEB")):
            form = "10-K" if ((q + k) if mix else q) % 4 == 0 else "10-Q"
            v = float(rng.uniform(0.5, 1.0))
            rows.append({"cik": k + 1, "form": form, "accession": f"{k}-{q}", "acceptance_dt": str(d.date()),
                         "floor": d + pd.Timedelta(days=1), "acc": d,
                         "yoy_combo_cos": v, "yoy_combo_why": "ok", "yoy_mda_cos": v, "yoy_mda_why": "ok",
                         "qoq_mda_cos": 1 - v, "qoq_mda_why": "ok", "yoy_combo_dtone": v - 0.75,
                         "yoy_mda_dtone": v - 0.75})
    return P, pd.DataFrame(rows).sort_values(["floor", "acceptance_dt"]).reset_index(drop=True)


def test_end_to_end_synthetic_run_is_deterministic_and_complete(monkeypatch):
    monkeypatch.setattr(T, "MIN_RANKED", 5)
    monkeypatch.setattr(T, "MIN_TERCILE", 2)
    from scripts.lazy_prices import b6_harness_sp as H
    P, sig = _synthetic_world()
    grid = H.rebalance_dates(P.cal, "2016-03-31", "2018-09-30")
    hold_end = P.cal[P.cal <= pd.Timestamp("2018-12-31")].max()
    outs = []
    for _ in range(2):
        for name in ("gate_similarity", "hoos_adjacent", "stress_similarity"):
            spec = T.SPECS[name]
            panel, census = T.build_panel(spec, sig, P, grid)
            assert T.check_census(census) == []
            res = T.run_returns(spec, panel, P, P.cal, hold_end)
            assert len(res["months"]) == 33 and np.all(np.isfinite(res["blend"]))
            s = T.summarize(res, spec)
            outs.append(T._json({name: s}))
            if spec.hoos:
                assert set(s["hoos"]) >= {"t_hac", "passes", "changers_minus_universe_mean_ann"}
                assert res["universe"].shape == res["q10_universe"].shape
                assert s["hoos"]["q10_only_companion_empty_quarters"] == 0
                assert isinstance(s["hoos"]["q10_only_companion_t_hac"], float)
    assert outs[:3] == outs[3:]
    stress, base = json.loads(outs[2])["stress_similarity"], json.loads(outs[0])["gate_similarity"]
    assert stress["deaths"] == base["deaths"]


def test_hoos_companion_that_cannot_be_formed_reads_not_evaluable_and_hoos_still_runs(monkeypatch):
    monkeypatch.setattr(T, "MIN_RANKED", 5)
    monkeypatch.setattr(T, "MIN_TERCILE", 2)
    from scripts.lazy_prices import b6_harness_sp as H
    P, sig = _synthetic_world(mix=False)          # every name's first-quarter filing is a 10-K
    grid = H.rebalance_dates(P.cal, "2016-03-31", "2018-09-30")
    spec = T.SPECS["hoos_adjacent"]
    panel, census = T.build_panel(spec, sig, P, grid)
    res = T.run_returns(spec, panel, P, P.cal, P.cal[-1])
    s = T.summarize(res, spec)
    assert s["hoos"]["q10_only_companion_t_hac"] == "NOT-EVALUABLE"
    assert s["hoos"]["q10_only_companion_empty_quarters"] >= 1
    assert isinstance(s["hoos"]["t_hac"], float) and np.isfinite(s["hoos"]["t_hac"])


# --------------------------------------------------------------------------- #
# review locks (2026-11-17): the composite the mutation run found unguarded
# --------------------------------------------------------------------------- #
def _res(n: int = 36, seed: int = 1, short_shift: float = -0.003) -> dict:
    """A synthetic monthly result: changers (short) lag the universe by `short_shift` a month."""
    rng = np.random.default_rng(seed)
    spy = rng.normal(0.008, 0.04, n)
    universe = rng.normal(0.007, 0.05, n)
    short = universe + short_shift + rng.normal(0.0, 0.004, n)
    long = universe + rng.normal(0.001, 0.01, n)
    iwm = rng.normal(0.006, 0.05, n)
    months = [d.date().isoformat() for d in pd.date_range("2016-04-30", periods=n, freq="ME")]
    return {"months": months, "long": long, "short": short, "universe": universe, "spy": spy, "iwm": iwm,
            "blend": 0.25 * long + 0.75 * spy, "iwm_blend": 0.25 * iwm + 0.75 * spy, "exits": [],
            "turnover": {"long": 0.5, "short": 0.5, "universe": 0.3},
            "cost_per_rebalance": {"long": 0.001, "short": 0.001, "universe": 0.0005},
            "deaths": {"long": 0, "short": 0, "universe": 0}, "long_new_name_share": 0.3,
            "q10_short": short, "q10_universe": universe, "q10_empty_quarters": 0}


def _bartlett_t(x: np.ndarray, lags: int) -> float:
    x = np.asarray(x, dtype=float)
    n = len(x)
    e = x - x.mean()
    s = e @ e / n
    for k in range(1, lags + 1):
        s += 2.0 * (1.0 - k / (lags + 1.0)) * (e[k:] @ e[:-k]) / n
    return float(x.mean() / np.sqrt(s / n))


def test_hoos_statistic_is_changers_minus_universe():
    res = _res()
    s = T.summarize(res, T.SPECS["hoos_adjacent"])
    want = float(np.mean(res["short"] - res["universe"]) * 12)
    assert s["hoos"]["changers_minus_universe_mean_ann"] == pytest.approx(want)
    assert want < 0
    assert s["hoos"]["t_hac"] == pytest.approx(_bartlett_t(res["short"] - res["universe"], 3))


@pytest.mark.parametrize("t, mean_negative, passes", [(-2.1, True, True), (2.5, True, False),
                                                     (-2.1, False, False), (-1.9, True, False)])
def test_hoos_pass_rule_is_negative_mean_and_t_at_most_minus_two(monkeypatch, t, mean_negative, passes):
    from scripts.lazy_prices import b6_harness_sp as H
    res = _res(short_shift=-0.003 if mean_negative else 0.003)
    monkeypatch.setattr(H, "newey_west_t", lambda x, lags=3: t)
    assert T.summarize(res, T.SPECS["hoos_adjacent"])["hoos"]["passes"] is passes


def test_short_leg_diagnostic_is_universe_minus_changers():
    from scripts.lazy_prices import b6_harness_sp as H
    res = _res()
    s = H.summarize(res)
    assert s["short_leg_mean_ann"] == pytest.approx(float(np.mean(res["universe"] - res["short"]) * 12))
    assert s["short_leg_mean_ann"] > 0 and s["short_leg_t_hac"] > 0


def _sig_rows(rows: list[tuple]) -> pd.DataFrame:
    """(cik, accession, acceptance date, form, value)"""
    out = []
    for cik, acc, d, form, v in rows:
        a = pd.Timestamp(d)
        out.append({"cik": cik, "accession": acc, "form": form, "acceptance_dt": f"{d}T21:00:00.000Z",
                    "acc": a, "floor": a + pd.Timedelta(days=1), "yoy_combo_cos": v, "yoy_combo_why": "ok",
                    "yoy_mda_cos": v, "yoy_mda_why": "ok"})
    return pd.DataFrame(out).sort_values(["floor", "acceptance_dt"]).reset_index(drop=True)


def test_signals_at_date_rule_floor_at_most_t_fresh_six_months_latest_wins():
    from scripts.lazy_prices import b6_harness_sp as H
    t = pd.Timestamp("2020-06-30")
    sig = _sig_rows([
        (1, "acc_on_t", "2020-06-30", "10-Q", 0.5),        # accepted ON t -> floor t+1: NOT usable
        (2, "floor_is_t", "2020-06-29", "10-Q", 0.5),      # floor == t: usable
        (3, "old", "2020-02-01", "10-Q", 0.1),             # two usable filings: the LATEST wins
        (3, "new", "2020-05-01", "10-Q", 0.9),
        (4, "stale", "2019-12-15", "10-Q", 0.5),           # accepted > 6 months before t: NOT usable
    ])
    got = H.signals_at(sig, t, T.SPECS["gate_similarity"], {1, 2, 3, 4})
    assert sorted(got.cik) == [2, 3]
    assert got.set_index("cik").loc[3, "accession"] == "new"


def test_rank_terciles_cut_constants_and_within_form_ranking():
    from scripts.lazy_prices import b6_harness_sp as H
    nine = H.rank_terciles(pd.DataFrame({"cik": range(9), "form": "10-Q", "value": np.arange(9.0)}))
    assert (nine.leg == "long").sum() == 3 and (nine.leg == "short").sum() == 3
    twelve = H.rank_terciles(pd.DataFrame({"cik": range(12), "form": "10-Q", "value": np.arange(12.0)}))
    assert (twelve.leg == "long").sum() == 4 and (twelve.leg == "short").sum() == 4   # 2/3 and 1/3, inclusive short
    two = H.rank_terciles(pd.DataFrame({"cik": range(6), "form": ["10-K"] * 3 + ["10-Q"] * 3,
                                        "value": [0.90, 0.95, 0.99, 0.10, 0.15, 0.20]}))
    assert two.groupby("form").leg.apply(lambda s: sorted(s)).to_dict() == {
        "10-K": ["long", "mid", "short"], "10-Q": ["long", "mid", "short"]}             # within form


def test_death_penalties_are_b2s():
    from scripts import smallcap_t265_b2_common as cm
    assert cm.DEATH_D == {"base": -0.30, "stress": -1.0, "lastprice": 0.0}


def test_gate_ci_low_is_the_1p25th_percentile_of_the_paired_bootstrap():
    from core.metrics_engine import MetricsEngine
    from scripts.lazy_prices import b6_harness_sp as H
    res = _res()
    s = H.summarize(res)
    blend, spy = res["blend"], res["spy"]

    def dlogw(i):
        return float(np.sum(np.log1p(blend[i])) - np.sum(np.log1p(spy[i])))

    idx = pd.Series(np.arange(len(blend), dtype=float))
    want = MetricsEngine.bootstrap_distribution(idx, lambda x: dlogw(x.to_numpy().astype(int)),
                                                n_iterations=1000, seed=0, confidence=0.975)["ci_low"]
    assert s["dlogw_ci_low_1p25"] == pytest.approx(want)
    assert s["dlogw_ci_low_1p25"] < s["dlogw_ci_low_2p5"]


def test_satellite_weight_and_newey_west_lags():
    from scripts.lazy_prices import b6_harness_sp as H
    assert H.SATELLITE == 0.25 and H.NW_LAGS == 3
    x = np.array([0.01, -0.02, 0.03, 0.00, 0.02, -0.01, 0.04, -0.03, 0.01, 0.02, -0.02, 0.03])
    assert H.newey_west_t(x) == pytest.approx(_bartlett_t(x, 3))
    assert H.newey_west_t(x) != pytest.approx(_bartlett_t(x, 0))


def test_adv_high_edge_excludes_exactly_200m():
    c = np.full(70, 10.0)
    P = _panel(closes={"EDG#0": c, "JUS#0": c}, adv={"EDG#0": 2e8, "JUS#0": 2e8 - 1.0},
               cik2t={1: "EDG", 2: "JUS"})
    t = P.cal[50]
    sig = pd.DataFrame({"cik": [1, 2], "form": ["10-Q"] * 2, "accession": ["a", "b"],
                        "yoy_mda_cos": [0.9] * 2, "yoy_mda_why": ["ok"] * 2,
                        "yoy_combo_cos": [np.nan] * 2, "yoy_combo_why": ["x"] * 2,
                        "floor": [t] * 2, "acc": [t - pd.Timedelta(days=1)] * 2, "acceptance_dt": ["x"] * 2})
    df, cause = T.eligible_at(T.SPECS["gate_similarity"], sig, P, t)
    assert list(df.cik) == [2] and cause["adv_ge_200M"] == 1
