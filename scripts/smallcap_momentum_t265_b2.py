"""scripts/smallcap_momentum_t265_b2.py — B-2 (T-381) small-cap 12-1 momentum on the T-265 panel.

Implements the FROZEN pre-registration `docs/Sources/prereg_b2_smallcap_t265_2026-11-11.md`
§4.1/§4.3/§4.4 + AMENDMENT 1. Standalone harness (never `BacktestController`).

    PYTHONHASHSEED=0 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    OMP_DYNAMIC=FALSE python -m scripts.smallcap_momentum_t265_b2 [--smoke] [--out DIR]

Exit codes: 0 ok · 2 HALT (`[NN-FAIL-CLOSED]`) · 3 determinism env pins wrong (refused).

Construction (frozen): month-end formation on the SPY-TR calendar; a security is a price-file
SEGMENT (common module); eligible = 12-1 return defined from the last traded closes of months
t-12 and t-1, a traded bar ON t, 20-day median dollar ADV at t in [$1M, $200M); top decile
k = max(10, floor(n/10)) by signal (ties by segment id), equal weight, held to the next
month-end; deaths at the last traded bar with D (BASE -30% / STRESS -100% / LAST-PRICE 0),
proceeds in BIL TR; costs |Δw| x per-side rate by ADV bucket (GATE 70/150 bps RT, sensitivity
35/75 RT); 2% ADV cap at a $250k sleeve (excess to BIL). Gate: 25%-satellite Δ log wealth vs
SPY TR, paired block-bootstrap ci_low.
"""
from __future__ import annotations

import sys

from scripts.smallcap_t265_b2_common import env_pin_violations  # noqa: E402

if __name__ == "__main__":
    _bad = env_pin_violations()
    if _bad:
        print("[B2-MOM] REFUSING: determinism env pins wrong — " + "; ".join(_bad) +
              ". Export them BEFORE python starts. Never re-exec'd.", file=sys.stderr)
        sys.exit(3)

import argparse  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Dict, List, Optional  # noqa: E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from scripts import smallcap_t265_b2_common as cm  # noqa: E402

FIRST_FORMATION = pd.Timestamp("2017-01-31")
LAST_HOLD_END = pd.Timestamp("2026-04-30")
SLEEVE_NOTIONAL = 250_000.0
ADV_CAP = 0.02
MIN_ELIGIBLE, MIN_DECILE, MIN_MONTHS = 500, 50, 100
SMOKE_FORMATIONS = 12
T249_PUBLISHED = {
    "source": "docs/Audit/smallcap_momentum_gauntlet_t249_2026_06_26.md (RESULTS table)",
    "universe": "Stooq US, 100% survivors; ADV tier from the FULL-WINDOW median (look-ahead)",
    "window": "2006-2025", "cost": "35/75 bps PER SIDE on Σ|Δw| (= 70/150 RT)",
    "gross": {"sortino": 4.907, "sortino_ci_low": 1.523, "sharpe": 3.210, "cagr": 0.151,
              "max_dd": -0.597},
    "net_tier": {"sortino": 3.709, "sortino_ci_low": 0.491, "sharpe": 2.467, "cagr": 0.108,
                 "max_dd": -0.617},
}


# ============================================================ selection
def formation_frame(MC: pd.DataFrame, C: pd.DataFrame, A: pd.DataFrame, me: pd.DatetimeIndex,
                    i: int, universe: pd.Series) -> pd.DataFrame:
    """Every segment's signal / ADV / tradability at formation month-end me[i]."""
    t = me[i]
    sig = MC.iloc[i - 1] / MC.iloc[i - 12] - 1.0
    traded = C.loc[t].notna()
    adv = A.loc[t]
    return pd.DataFrame({"sig": sig, "traded": traded, "adv": adv, "univ": universe})


def select_decile(fr: pd.DataFrame) -> Dict[str, object]:
    base_ok = fr["sig"].notna() & fr["traded"] & fr["univ"]
    in_band = (fr["adv"] >= cm.ADV_LO) & (fr["adv"] < cm.ADV_HI)
    elig = fr[base_ok & in_band]
    n = len(elig)
    k = max(10, n // 10)
    order = elig.assign(_neg=-elig["sig"], _id=elig.index).sort_values(["_neg", "_id"])
    sel = list(order.index[:k])
    return {"sel": sel, "n_eligible": n, "k": k,
            "n_ge200M": int((base_ok & (fr["adv"] >= cm.ADV_HI)).sum()),
            "n_small": int((elig["adv"] >= cm.ADV_MID).sum()),
            "n_micro": int((elig["adv"] < cm.ADV_MID).sum())}


def holding_returns(sel: List[str], i: int, me: pd.DatetimeIndex, C: pd.DataFrame,
                    MC: pd.DataFrame, closes: Dict[str, pd.Series],
                    deaths: Dict[str, Optional[pd.Timestamp]], bil: pd.Series,
                    D: float) -> pd.DataFrame:
    """Per-name return over (me[i], me[i+1]]; a death inside the month takes D at its last
    traded close and earns BIL TR to me[i+1]. A whole-month halt (no trade, not dead) is 0."""
    t0, t1 = me[i], me[i + 1]
    p0 = C.loc[t0, sel].astype(float)
    p1 = MC.iloc[i + 1][sel].astype(float)
    r = (p1 / p0 - 1.0).where(p1.notna(), 0.0)
    dead = pd.Series(False, index=sel)
    for s in sel:
        d = deaths.get(s)
        if d is not None and t0 <= d < t1:
            pd_ = float(closes[s].loc[d])
            r[s] = (pd_ / p0[s]) * (1.0 + D) * (bil.loc[t1] / bil.asof(d)) - 1.0
            dead[s] = True
    if r.isna().any():
        raise cm.Halt(f"NaN holding return without a death classification at {t0.date()}: "
                      f"{list(r[r.isna()].index)[:5]}")
    return pd.DataFrame({"r": r, "dead": dead})


def run_arm(forms: List[dict], me: pd.DatetimeIndex, C: pd.DataFrame, MC: pd.DataFrame,
            closes, deaths, bil: pd.Series, D: float, basis: str) -> Dict[str, object]:
    """Monthly net returns of one arm over the formation list (drifted-weight turnover)."""
    out_r, out_cost, out_turn, out_deaths = [], [], [], []
    prev: Dict[str, float] = {}
    prev_dead: Dict[str, bool] = {}
    for f in forms:
        i, sel, adv = f["i"], f["sel"], f["adv"]
        w = 1.0 / len(sel)
        cap = (ADV_CAP * adv[sel] / SLEEVE_NOTIONAL).clip(upper=w)
        w_eff = pd.Series(w, index=sel).where(cap >= w, cap)
        cash = 1.0 - float(w_eff.sum())
        # cost at this rebalance: buys/sells vs the drifted book (dead proceeds sell free)
        cost, turn = 0.0, 0.0
        for s in sel:
            dw = abs(w_eff[s] - (prev.get(s, 0.0) if not prev_dead.get(s, False) else 0.0))
            cost += dw * cm.side_cost(adv[s], basis)
            turn += dw
        for s, pw in prev.items():
            if s in w_eff.index or prev_dead.get(s, False):
                continue
            a = f["adv_all"].get(s, np.nan)
            cost += pw * cm.side_cost(a, basis)
            turn += pw
        hr = holding_returns(sel, i, me, C, MC, closes, deaths, bil, D)
        bil_m = float(bil.loc[me[i + 1]] / bil.loc[me[i]] - 1.0)
        gross = float((w_eff * hr["r"]).sum() + cash * bil_m)
        net = (1.0 - cost) * (1.0 + gross) - 1.0
        val = w_eff * (1.0 + hr["r"])
        prev = (val / (1.0 + gross)).to_dict()
        prev_dead = hr["dead"].to_dict()
        out_r.append(net)
        out_cost.append(cost)
        out_turn.append(turn)
        out_deaths.append(int(hr["dead"].sum()))
    return {"r": np.asarray(out_r), "cost": np.asarray(out_cost),
            "turnover": np.asarray(out_turn), "deaths": out_deaths}


def build_formations(me, C, A, MC, universe: pd.Series, n_forms: Optional[int]) -> List[dict]:
    idx = [i for i in range(12, len(me) - 1)
           if me[i] >= FIRST_FORMATION and me[i + 1] <= LAST_HOLD_END]
    if n_forms is not None:
        idx = idx[:n_forms]
    forms = []
    for i in idx:
        fr = formation_frame(MC, C, A, me, i, universe)
        s = select_decile(fr)
        if s["n_eligible"] < MIN_ELIGIBLE or s["k"] < MIN_DECILE:
            raise cm.Halt(f"formation {me[i].date()}: eligible {s['n_eligible']} / decile {s['k']} "
                          f"below {MIN_ELIGIBLE}/{MIN_DECILE}")
        held_prev = forms[-1]["sel"] if forms else []
        adv_all = {x: float(fr["adv"].get(x, np.nan)) for x in held_prev}
        forms.append(dict(i=i, date=me[i], fr=fr[["sig", "adv"]].loc[s["sel"]],
                          adv=fr["adv"][s["sel"]], adv_all=adv_all, **s))
    return forms


def per_year(dates: pd.DatetimeIndex, cols: Dict[str, np.ndarray]) -> Dict[str, dict]:
    df = pd.DataFrame(cols, index=dates)
    g = (1.0 + df).groupby(df.index.year).prod() - 1.0
    return {str(y): {k: float(v) for k, v in row.items()} for y, row in g.iterrows()}


# ============================================================ main
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--smoke", action="store_true", help="first 12 formations only; no bootstrap")
    ap.add_argument("--out", default=None)
    a = ap.parse_args(argv)
    t_start = time.time()
    out_dir = Path(a.out) if a.out else (cm.OUT / ("smoke" if a.smoke else "run"))
    try:
        cal = cm.market_calendar()
        tw = cm.twins_on(cal)
        segs, ucensus, fcen = cm.load_universe(cal)
        census_rec = {"price": cm.enforce_census(cm.price_census_observed(fcen),
                                                 cm.EXPECTED_PRICE_CENSUS)}
        C, A = cm.price_matrices(segs, cal)
        closes = {s.seg_id: s.close for s in segs}
        deaths = {s.seg_id: s.death for s in segs}
        MC = C.groupby(C.index.to_period("M")).last()
        me = cm.month_ends(cal)
        if len(MC) != len(me):
            raise cm.Halt("monthly close matrix and month-end list disagree")
        bil = tw["BIL"]
        n_forms = SMOKE_FORMATIONS if a.smoke else None
        all_u = pd.Series(True, index=C.columns)
        surv_u = pd.Series({s.seg_id: (s.death is None or s.death > cm.TWIN_END) for s in segs})
        forms = build_formations(me, C, A, MC, all_u, n_forms)
        if not a.smoke and len(forms) < MIN_MONTHS:
            raise cm.Halt(f"{len(forms)} holding months < {MIN_MONTHS}")
        if not a.smoke:      # prereg §3.6 window, recomputed (§4.5)
            census_rec["window"] = cm.enforce_census(
                {"formations": len(forms), "first_formation": forms[0]["date"].strftime("%Y-%m-%d"),
                 "last_formation": forms[-1]["date"].strftime("%Y-%m-%d"),
                 "last_hold_end": me[forms[-1]["i"] + 1].strftime("%Y-%m-%d")},
                {"formations": 111, "first_formation": "2017-01-31",
                 "last_formation": "2026-03-31", "last_hold_end": "2026-04-30"})
        hold_end = pd.DatetimeIndex([me[f["i"] + 1] for f in forms])
        twm = tw.loc[[me[forms[0]["i"]]] + list(hold_end)].pct_change().iloc[1:]
        spy, iwm, bilm = (twm[c].to_numpy() for c in ("SPY", "IWM", "BIL"))
        arms = {
            "base": run_arm(forms, me, C, MC, closes, deaths, bil, cm.DEATH_D["base"], "gate"),
            "stress": run_arm(forms, me, C, MC, closes, deaths, bil, cm.DEATH_D["stress"], "gate"),
            "lastprice": run_arm(forms, me, C, MC, closes, deaths, bil, cm.DEATH_D["lastprice"],
                                 "gate"),
            "cost_brief": run_arm(forms, me, C, MC, closes, deaths, bil, cm.DEATH_D["base"],
                                  "brief"),
        }
        sforms = build_formations(me, C, A, MC, surv_u, n_forms)
        arms["survivor_only"] = run_arm(sforms, me, C, MC, closes, deaths, bil,
                                        cm.DEATH_D["base"], "gate")
    except cm.Halt as e:
        print(f"[B2-MOM] HALT: {e}", file=sys.stderr)
        return 2

    try:
        return _report(a, out_dir, t_start, forms, arms, hold_end, spy, iwm, bilm, ucensus,
                       census_rec)
    except cm.Halt as e:
        print(f"[B2-MOM] HALT: {e}", file=sys.stderr)
        return 2


def _report(a, out_dir, t_start, forms, arms, hold_end, spy, iwm, bilm, ucensus, census_rec) -> int:
    fcensus = pd.DataFrame([{"formation": f["date"].strftime("%Y-%m-%d"),
                             "n_eligible": f["n_eligible"], "k": f["k"], "n_small": f["n_small"],
                             "n_micro": f["n_micro"], "n_ge200M": f["n_ge200M"],
                             "deaths_in_decile_month": arms["base"]["deaths"][j],
                             "capacity_sleeve_aum": float(ADV_CAP * f["adv"].min() * f["k"]),
                             "turnover": float(arms["base"]["turnover"][j])}
                            for j, f in enumerate(forms)])
    out_dir.mkdir(parents=True, exist_ok=True)
    fcensus.to_csv(out_dir / "momentum_formation_census.csv", index=False)
    monthly = pd.DataFrame({k: v["r"] for k, v in arms.items() if k != "survivor_only"},
                           index=hold_end)
    monthly["survivor_only"] = arms["survivor_only"]["r"]
    monthly["SPY"], monthly["IWM"], monthly["BIL"] = spy, iwm, bilm
    monthly.to_csv(out_dir / "momentum_monthly.csv")

    census = {"universe": ucensus,
              "formations": len(forms), "first_formation": forms[0]["date"],
              "last_formation": forms[-1]["date"], "first_hold_end": hold_end[0],
              "last_hold_end": hold_end[-1],
              "n_eligible": {"min": int(fcensus.n_eligible.min()),
                             "median": float(fcensus.n_eligible.median()),
                             "max": int(fcensus.n_eligible.max())},
              "k": {"min": int(fcensus.k.min()), "median": float(fcensus.k.median()),
                    "max": int(fcensus.k.max())},
              "n_ge200M_excluded": {"min": int(fcensus.n_ge200M.min()),
                                    "max": int(fcensus.n_ge200M.max())},
              "micro_share_of_decile_mean": float((fcensus.n_micro / (fcensus.n_micro + fcensus.n_small)).mean()),
              "deaths_in_decile_total": int(fcensus.deaths_in_decile_month.sum()),
              "survivor_only_deaths_total": int(sum(arms["survivor_only"]["deaths"])),
              "capacity_sleeve_aum_median": float(fcensus.capacity_sleeve_aum.median()),
              "adv_cap_binding_formations": int((fcensus.capacity_sleeve_aum < SLEEVE_NOTIONAL).sum())}
    results = {"task": "T-381 (B-2) momentum", "smoke": a.smoke,
               "prereg": "docs/Sources/prereg_b2_smallcap_t265_2026-11-11.md (+ AMENDMENT 1)",
               "census": census,
               "first_formations": [
                   {"date": f["date"], "k": f["k"], "n_eligible": f["n_eligible"],
                    "top10": [{"seg": s, "sig": float(f["fr"].loc[s, "sig"]),
                               "adv": float(f["fr"].loc[s, "adv"])} for s in f["sel"][:10]]}
                   for f in forms[:3]],
               "turnover_ann": float(arms["base"]["turnover"].mean() * 12),
               "cost_drag_bps_yr": {k: float(arms[k]["cost"].mean() * 12 * 1e4)
                                    for k in ("base", "cost_brief")},
               "per_year": per_year(hold_end, {"base": arms["base"]["r"], "SPY": spy,
                                               "IWM": iwm, "BIL": bilm}),
               "t249_published": T249_PUBLISHED}
    if a.smoke:
        results["smoke_monthly"] = {d.strftime("%Y-%m"): {k: float(v) for k, v in row.items()}
                                    for d, row in monthly.iterrows()}
    else:
        mde = cm.MDE80["momentum_satellite"]
        results["arms"] = {k: cm.arm_block(v["r"], spy, iwm, mde) for k, v in arms.items()}
        results["twins"] = {"SPY": {"cagr": cm.cagr(spy), "max_dd": cm.max_dd(spy),
                                    "sharpe": cm.boot(len(spy), cm.sharpe_fn(spy))},
                            "IWM": {"cagr": cm.cagr(iwm), "max_dd": cm.max_dd(iwm),
                                    "sharpe": cm.boot(len(iwm), cm.sharpe_fn(iwm))},
                            "iwm_sleeve_dlogw_vs_spy": cm.boot(len(spy), cm.dlogw(iwm, spy))}
        base, surv = results["arms"]["base"], results["arms"]["survivor_only"]
        results["haircut_within_panel"] = {
            "cagr_survivor_minus_base": surv["cagr"] - base["cagr"],
            "dlogw_point_survivor_minus_base": (surv["dlogw_vs_spy"]["point"]
                                                - base["dlogw_vs_spy"]["point"]),
            "note": "a LOWER bound on the true haircut: the base panel itself lacks most deaths"}
        yb = arms["base"]["r"] - bilm
        results["alpha_diagnostics"] = {"vs_IWM": cm.nw_alpha(yb, iwm - bilm),
                                        "vs_SPY": cm.nw_alpha(yb, spy - bilm)}
        results["dsr_line"] = {"sr_required_at_neff_36.9": 0.709, "sr_required_at_n_260": 0.937,
                               "years": len(spy) / 12}
        sat = base["dlogw_vs_spy"]
        results["h1"] = {"met": bool(sat["ci_low"] > 0), "ci_low": sat["ci_low"],
                         "point": sat["point"], "label": base["label"]}
        results["stop_trigger"] = {
            "h1_met": results["h1"]["met"],
            "alpha_t_gt_2": {k: bool(v["alpha_t_hac"] > 2.0)
                             for k, v in results["alpha_diagnostics"].items()}}
    results["run_meta"] = {"wall_seconds": round(time.time() - t_start, 1)}
    cm.write_census_check(census_rec, out_dir, "momentum")
    md5 = cm.write_results(results, out_dir, "momentum_results")
    print(f"[B2-MOM] wrote {out_dir}/momentum_results.json  canonical_md5={md5}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
