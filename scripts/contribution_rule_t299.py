"""T-2026-07-09-299 — the contribution-vs-gate rule (FROZEN pre-reg run).

Pre-registration: docs/Sources/prereg_contribution_rule_t299.md (director-frozen
2026-07-09, no amendments). N_trials += 1, ONE family jointly reported.

Question: a $7K/yr accumulator DCAs into a trend-GATED leveraged-SPY arm whose
exposure e[t] swings 0..2. When a contribution lands with the gate partially/
fully OFF, should it (A) sit in cash till the gate re-engages, or (B) buy in and
let the gate manage it?

Configs (from the FROZEN T-298 construction, re-derived verbatim here with a
repo-relative ROOT; the price-based arm is dividend-blind, but the A-vs-B verdict
is dividend-basis-invariant since both rules ride the SAME arm):
  C1 = e_asym  (T-298 asymmetric-damped, ~1.1x)  -- PRIMARY (decision config)
  C2 = e_target(undamped)                         -- secondary
  C0 = e==1 buy-hold SPY (price)                  -- contributing baseline

Rules (both: $7K on the first trading day of each year, add-then-grow, matching
accumulation_model_t283.accumulate):
  B: full contribution -> arm; rides r_arm thereafter  == accumulate(arm(e))
  A: contribution splits e[t]/e_max into the arm, remainder into external cash
     (short rate); external cash re-deploys into the arm as the gate re-engages
     (headroom-proportional on rising e). e_max = 2.0.

Frozen decision gate (on C1): higher MEDIAN terminal wealth across 5 starts wins
IFF its worst-$-DD <= 110% of the other's (else the DD-safer rule wins); winner
must hold >=3/5 starts, else H0 -> default Rule B.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path
from statistics import median

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.accumulation_model_t283 import accumulate, CONTRIB  # noqa: E402

# ---- FROZEN T-298 primitives (verbatim formulas; repo-relative ROOT) -------- #
TD = 252
TXN = 0.00015
SPY_ER = 0.000945
SSO_ER = 0.0089
SSO_SPREAD = 0.0060
SPY_SLIP = 0.51 / 1e4
B_BAND = 2.0 / 3.0
TOL = 1e-9
E_MAX = 2.0
START = pd.Timestamp("2000-08-30")
STARTS = ["2000", "2003", "2006", "2009", "2012"]


def _spy_close() -> pd.Series:
    rows = list(csv.DictReader(open(ROOT / "data/processed/SPY_1d.csv")))
    return pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"])
                      for x in rows}).sort_index()


def _macro(s: str) -> pd.Series:
    d = pd.read_parquet(ROOT / f"data/macro/{s}.parquet")["value"].astype(float)
    d.index = pd.to_datetime(d.index)
    return d.dropna().sort_index()


from core.trend_overlay import TrendOverlay  # noqa: E402

_spy = _spy_close()
_spy_tr = _spy.pct_change()
IDX = _spy_tr.index
_dgs3 = _macro("DGS3MO")
RF = ((_dgs3 / 100.0 / TD)
      .reindex(pd.date_range(_dgs3.index[0], _dgs3.index[-1], freq="D")).ffill()
      .reindex(IDX).ffill().fillna(0.0))
_spy_gross = _spy_tr + SPY_ER / TD
_sso_syn = 2 * _spy_gross - (RF + SSO_SPREAD / TD) - SSO_ER / TD
_ens = pd.concat([TrendOverlay(s, enabled=True).exposure(_spy.astype(float))
                  for s in [42, 105, 210]], axis=1).mean(axis=1)
E_TARGET = (2.0 * _ens.shift(1)).clip(upper=2.0)


def _asym(tgt: pd.Series, band: float = B_BAND) -> pd.Series:
    out, held = [], np.nan
    for v in tgt.values:
        if np.isnan(v):
            out.append(np.nan); continue
        if np.isnan(held):
            held = v
        elif v < held - TOL:
            held = v                              # de-risk: undamped, immediate
        elif v - held > band + TOL:
            held = v                              # re-entry: only on >= 2 increments
        out.append(held)
    return pd.Series(out, index=tgt.index)


E_ASYM = _asym(E_TARGET)


def arm(e: pd.Series, slip_bps: float = 0.51) -> pd.Series:
    """Net daily return of holding exposure e (verbatim T-298). At e=0 -> RF."""
    e = e.reindex(IDX)
    lo = e * (_spy_tr - SPY_ER / TD) + (1 - e) * RF
    hi = (2 - e) * (_spy_tr - SPY_ER / TD) + (e - 1) * _sso_syn
    r = lo.where(e <= 1, hi)
    ta = e.diff().abs().fillna(0)
    ssow = (e - 1).clip(lower=0)
    ts = ssow.diff().abs().fillna(0)
    tsp = (ta - ts).clip(lower=0)
    return (r - ta * TXN - ts * (slip_bps / 1e4) - tsp * SPY_SLIP)[IDX >= START].dropna()


# ---- Rule A: two-bucket DCA (arm + external cash, re-deploy on rising gate) -- #
def accumulate_rule_a(e: pd.Series, r_arm: pd.Series, start: str,
                      contrib: float = CONTRIB, e_max: float = E_MAX) -> dict:
    r_arm = r_arm[r_arm.index >= pd.Timestamp(start)].dropna()
    if len(r_arm) < 252:
        return None
    idx = r_arm.index
    e = e.reindex(idx)
    rf = RF.reindex(idx).fillna(0.0)
    contrib_days = {idx[idx.year == y][0]: contrib for y in sorted(set(idx.year))
                    if len(idx[idx.year == y])}
    arm_val = ext = contributed = 0.0
    e_prev = np.nan
    path, cc = [], []
    ext_daydollars = 0.0                          # sum of external cash across days
    offgate_deferred = 0.0                        # $ that entered cash on off-gate contrib days
    for d in idx:
        ed = e.loc[d]
        if d in contrib_days:
            f = 0.0 if np.isnan(ed) else float(np.clip(ed / e_max, 0.0, 1.0))
            arm_val += contrib * f
            ext += contrib * (1.0 - f)
            contributed += contrib
            if f < 0.5:                           # contributed while gate largely off
                offgate_deferred += contrib * (1.0 - f)
        arm_val *= (1.0 + r_arm.loc[d])
        ext *= (1.0 + rf.loc[d])
        if (not np.isnan(ed)) and (not np.isnan(e_prev)) and ed > e_prev and ext > 0:
            headroom = e_max - e_prev
            if headroom > 1e-9:
                deploy = ext * min(1.0, (ed - e_prev) / headroom)
                arm_val += deploy
                ext -= deploy
        if not np.isnan(ed):
            e_prev = ed
        ext_daydollars += ext
        path.append(arm_val + ext)
        cc.append(contributed)
    wp = pd.Series(path, index=idx)
    cc = pd.Series(cc, index=idx)
    worst_dd = float((wp - wp.cummax()).min())
    return {
        "terminal": float(wp.iloc[-1]),
        "contributed": float(contributed),
        "mult_on_contrib": round(float(wp.iloc[-1] / contributed), 3),
        "worst_dollar_dd": round(worst_dd, 0),
        "frac_underwater": round(float((wp < cc).mean()), 3),
        "years": round((idx[-1] - idx[0]).days / 365.25, 1),
        # cash-drag decomposition
        "cash_drag_dollar_years": round(ext_daydollars / TD, 0),
        "offgate_deferred_total": round(offgate_deferred, 0),
    }


def run_config(name: str, e: pd.Series | None, is_baseline: bool = False) -> dict:
    r_arm = arm(pd.Series(1.0, index=IDX)) if is_baseline else arm(e)
    out = {"config": name, "A": {}, "B": {}}
    for s in STARTS:
        b = accumulate(r_arm, f"{s}-01-01")
        out["B"][s] = b[0] if b else None
        if is_baseline:
            out["A"][s] = out["B"][s]             # no gate -> A == B
        else:
            out["A"][s] = accumulate_rule_a(e, r_arm, f"{s}-01-01")
    return out


def _verdict(c1: dict) -> dict:
    """Frozen decision gate on C1."""
    starts = [s for s in STARTS if c1["A"].get(s) and c1["B"].get(s)]
    a_term = {s: c1["A"][s]["terminal"] for s in starts}
    b_term = {s: c1["B"][s]["terminal"] for s in starts}
    a_wins = sum(a_term[s] > b_term[s] for s in starts)
    b_wins = sum(b_term[s] > a_term[s] for s in starts)
    med_a, med_b = median(a_term.values()), median(b_term.values())
    wealth_winner = "A" if med_a > med_b else "B"
    # deepest worst-$-DD across starts (most negative)
    dd_a = min(c1["A"][s]["worst_dollar_dd"] for s in starts)
    dd_b = min(c1["B"][s]["worst_dollar_dd"] for s in starts)
    winner_dd = dd_a if wealth_winner == "A" else dd_b
    other_dd = dd_b if wealth_winner == "A" else dd_a
    # "<=110% deeper": |winner_dd| <= 1.10*|other_dd|
    dd_ok = abs(winner_dd) <= 1.10 * abs(other_dd) + 1e-9
    winner_starts = a_wins if wealth_winner == "A" else b_wins
    if not dd_ok:
        adopted, why = ("B" if wealth_winner == "A" else "A"), \
            f"defense override: {wealth_winner} wins wealth but worsens worst-$-DD >10% (|{winner_dd:,.0f}| vs |{other_dd:,.0f}|)"
    elif winner_starts >= 3:
        adopted, why = wealth_winner, f"{wealth_winner} wins median wealth (dd within tolerance) and holds {winner_starts}/5 starts"
    else:
        adopted, why = "B", f"H0: no >=3/5 robust winner (A {a_wins} / B {b_wins}) -> default Rule B"
    return {"median_terminal": {"A": round(med_a), "B": round(med_b)},
            "start_wins": {"A": a_wins, "B": b_wins},
            "deepest_worst_dd": {"A": dd_a, "B": dd_b},
            "wealth_winner": wealth_winner, "dd_within_10pct": dd_ok,
            "ADOPTED_RULE": adopted, "reason": why}


def main() -> int:
    # self-check: faithful reproduction of the frozen T-298 construction
    mean_asym = float(E_ASYM[IDX >= START].mean())
    mean_tgt = float(E_TARGET[IDX >= START].mean())
    lag = int(((E_ASYM - E_TARGET)[IDX >= START].dropna() > 1e-9).sum())
    print(f"[self-check] mean e_asym={mean_asym:.3f} e_target={mean_tgt:.3f} | "
          f"de-risk invariant e_asym<=e_target violations={lag} (expect 0)")
    assert lag == 0, "T-298 invariant violated — re-derivation drifted"

    configs = {
        "C1_e_asym (T-298 damped, PRIMARY)": run_config("C1_e_asym", E_ASYM),
        "C2_e_target (undamped)": run_config("C2_e_target", E_TARGET),
        "C0_buyhold_SPY (baseline)": run_config("C0_buyhold", None, is_baseline=True),
    }
    verdict = _verdict(configs["C1_e_asym (T-298 damped, PRIMARY)"])

    # ---- print the joint table ---- #
    print(f"\n=== T-299 contribution-vs-gate | ${CONTRIB:,.0f}/yr | starts {STARTS} ===")
    for cname, c in configs.items():
        print(f"\n--- {cname} ---")
        print(f"{'start':6}{'rule':5}{'terminal$':>13}{'xcontrib':>10}"
              f"{'worst$DD':>13}{'%uw':>7}{'cashDrag$yr':>13}")
        for s in STARTS:
            for rule in ("A", "B"):
                m = c[rule].get(s)
                if not m:
                    continue
                cd = m.get("cash_drag_dollar_years", 0)
                print(f"{s:6}{rule:5}{m['terminal']:>13,.0f}{m['mult_on_contrib']:>10.2f}"
                      f"{m['worst_dollar_dd']:>13,.0f}{m['frac_underwater']*100:>6.0f}%"
                      f"{cd:>13,.0f}")
    print("\n=== FROZEN VERDICT (on C1) ===")
    print(json.dumps(verdict, indent=2))

    out = {"contrib_per_yr": CONTRIB, "starts": STARTS, "e_max": E_MAX,
           "configs": configs, "verdict": verdict,
           "self_check": {"mean_e_asym": round(mean_asym, 3),
                          "mean_e_target": round(mean_tgt, 3), "invariant_violations": lag}}
    OUT = ROOT / "data/research/t299_contribution_rule.json"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
