"""B-6 T-265 arm harness — identity (A8), deaths and costs (B-2 by reference), the §7.7 floors after
the band, H_OOS's sign, and the freeze manifest. Synthetic inputs only; no network, no real price."""
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
