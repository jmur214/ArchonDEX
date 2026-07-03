"""
scripts/capital_tier_gauntlet_t278.py
=====================================
T-2026-07-02-278 — CAPITAL-TIER GAUNTLET: validate the deploying trend sleeve in
WHOLE shares at every tier ($5K..$250K). Extends the T-257 integer-share machinery
to 6 tiers × 2 instrument sets, with fair T-255 conventions (flat leg @ short rate,
ER, txn). 0 new N_trials — per-tier validation of the already-validated config.

Deploying sleeve = 105d long/flat absolute momentum on SPY/AGG/GLD, EW (T-236).
Continuous baseline (fair conventions) is the tracking target; the integer book
holds floor(equity·w/px) shares, residual + flat legs @ short rate, ER on holdings,
3bps/side. Instrument sets: {SPY,AGG,GLD} vs {SPLG≈SPY/9, AGG, GLDM≈GLD/5} — same
index, finer share granularity at the low tiers.

Data caveat (from T-257): data/processed GLD starts 2020-04, so the window is
2020-2026 — the HIGH-PRICE regime, i.e. the conservative "deploy today" test.

Output: data/research/t278/capital_tiers.json + the per-tier config table.
Usage: python -m scripts.capital_tier_gauntlet_t278
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.trend_overlay import TrendOverlay, LOOKBACK_DAYS  # noqa: E402
from core.metrics_engine import MetricsEngine as ME  # noqa: E402

PROC = ROOT / "data" / "processed"
OUT = ROOT / "data" / "research" / "t278" / "capital_tiers.json"
TD = 252
LOOKBACK = LOOKBACK_DAYS[5]              # 105d
COST = 0.0003                           # 3 bps/side (liquid ETF)
ER = {"SPY": 0.0009, "AGG": 0.0003, "GLD": 0.0040, "SPLG": 0.0002, "GLDM": 0.0010}
TIERS = [5_000, 10_000, 25_000, 65_000, 100_000, 250_000]
SET_STD = {"SPY": "SPY", "AGG": "AGG", "GLD": "GLD"}                 # leg -> ticker
SET_CHEAP = {"SPY": "SPLG", "AGG": "AGG", "GLD": "GLDM"}
DIVISOR = {"SPLG": 9.0, "GLDM": 5.0}    # synth cheap class = real price / divisor (same index/returns)


def _px(tkr_real: str) -> pd.Series:
    return pd.read_csv(PROC / f"{tkr_real}_1d.csv", index_col=0, parse_dates=True)["Close"].astype(float)


def _load_set(inst: dict, start: str):
    """Return {leg: (price_series, ER)} for the instrument set, from `start`.
    Cheap classes synthesized by price/divisor (identical returns, finer shares)."""
    out = {}
    for leg, tkr in inst.items():
        real = "SPY" if leg == "SPY" else ("GLD" if leg == "GLD" else "AGG")
        p = _px(real).loc[start:]
        if tkr in DIVISOR:
            p = p / DIVISOR[tkr]
        out[leg] = (p, ER[tkr])
    return out


def _cash_rate():
    d = pd.read_parquet(ROOT / "data/macro/DGS3MO.parquet")["value"].astype(float)
    d.index = pd.to_datetime(d.index)
    cd = (d.dropna().sort_index() / 100.0 / TD)
    return cd.reindex(pd.date_range(cd.index[0], cd.index[-1], freq="D")).ffill()


CASH = _cash_rate()


def _weights(legs: dict) -> pd.DataFrame:
    """Per-leg target weight (1/3 long/flat; act on yesterday's signal)."""
    w = 1.0 / len(legs)
    cols = {}
    idx = None
    for leg, (p, _) in legs.items():
        sig = TrendOverlay(LOOKBACK, enabled=True).exposure(p).shift(1)
        cols[leg] = sig * w
        idx = sig.index if idx is None else idx.intersection(sig.index)
    return pd.DataFrame(cols).dropna()


def _continuous(legs: dict, W: pd.DataFrame) -> pd.Series:
    """Fair continuous sleeve: long legs earn asset−ER, flat capital earns short
    rate; txn on weight flips."""
    idx = W.index
    cash = CASH.reindex(idx).ffill().fillna(0.0)
    parts = []
    for leg, (p, er) in legs.items():
        ar = p.reindex(idx).pct_change()
        pos = (W[leg] * len(legs))               # 0/1 long-flat (un-weighted)
        r = pos * (ar - er / TD) + (1 - pos) * cash
        r = r - pos.diff().abs().fillna(0.0) * COST
        parts.append(r * (1.0 / len(legs)))
    return pd.concat(parts, axis=1).sum(axis=1, min_count=1).dropna()


def _integer(legs: dict, W: pd.DataFrame, capital: float, deadband: float = 0.05) -> pd.Series:
    """Whole-share book, fair conventions: residual + flat capital earn the short
    rate; ER on holdings; 3bps/side on share turnover. Carver deadband (T-148 /
    paper sleeve_constructor): a leg only rebalances to its new integer target
    when its long/flat state FLIPS or its weight has drifted ≥ `deadband`
    (deadband=0 ⇒ daily re-floor, the churn baseline)."""
    idx = W.index
    cash_r = CASH.reindex(idx).ffill().fillna(0.0)
    px = {leg: p.reindex(idx).ffill() for leg, (p, _) in legs.items()}
    er = {leg: e for leg, (_, e) in legs.items()}
    equity = float(capital); shares = {leg: 0 for leg in legs}; cash = equity
    rets, prev = [], None
    for d in idx:
        if prev is None:
            prev = d; continue
        # (1) rebalance to W[d] using YESTERDAY's price (set the position FOR day d)
        new_shares = dict(shares)
        for leg in legs:
            pp = px[leg].at[prev]
            if pp <= 0:
                continue
            tgt_w = float(W.at[d, leg]); held_w = shares[leg] * pp / equity if equity > 0 else 0.0
            flip = (tgt_w > 0) != (shares[leg] > 0)
            if flip or abs(tgt_w - held_w) >= deadband:
                new_shares[leg] = int(np.floor(equity * tgt_w / pp))
        turn = sum(abs(new_shares[leg] - shares[leg]) * px[leg].at[prev] for leg in legs)
        equity -= turn * COST
        shares = new_shares
        cash = equity - sum(shares[leg] * px[leg].at[prev] for leg in legs)
        # (2) earn day d's return on the shares held over day d
        mv = sum(shares[leg] * px[leg].at[d] for leg in legs)
        er_charge = sum(shares[leg] * px[leg].at[prev] * er[leg] / TD for leg in legs)
        ne = mv + cash * (1 + cash_r.at[d]) - er_charge
        rets.append((d, ne / equity - 1.0 if equity > 0 else 0.0)); equity = ne
        prev = d
    return pd.Series({d: r for d, r in rets})


def _m(r):
    eq = (1 + r).cumprod()
    return {"sortino": round(float(ME.sortino_ratio(r, 0.0, TD)), 3),
            "maxdd_pct": round(float((eq / eq.cummax() - 1).min()) * 100, 2),
            "cagr_pct": round(float((eq.iloc[-1] ** (252.0 / max(len(r), 1)) - 1)) * 100, 2)}


def main() -> int:
    for t in ["SPY", "AGG", "GLD"]:
        if not (PROC / f"{t}_1d.csv").exists():
            print(f"[T278] FATAL {t} absent"); return 2
    start = "2020-01-01"
    report = {"task": "T-2026-07-02-278 capital-tier gauntlet", "lookback": LOOKBACK,
              "cost_bps": 3, "adv_note": "SPY ADV ~$56B, GLD ~$5.3B, AGG ~$825M; a $250K rebalance trades ~$83K/name = <0.02% of the thinnest (AGG) ADV -> zero market-impact through $250K and well beyond.",
              "window": None, "tiers": {}}
    sets = {"SPY/AGG/GLD": SET_STD, "SPLG/AGG/GLDM": SET_CHEAP}
    cont_cache = {}
    for sname, inst in sets.items():
        legs = _load_set(inst, start)
        W = _weights(legs)
        cont = _continuous(legs, W).dropna()
        cont_cache[sname] = (legs, W, cont)
    report["window"] = [str(cont_cache["SPY/AGG/GLD"][2].index.min().date()),
                        str(cont_cache["SPY/AGG/GLD"][2].index.max().date())]

    for cap in TIERS:
        row = {}
        for sname, (legs, W, cont) in cont_cache.items():
            ib = _integer(legs, W, float(cap), deadband=0.05).dropna()      # DEPLOYING config
            ib_nd = _integer(legs, W, float(cap), deadband=0.0).dropna()    # no-deadband (churn baseline)
            j = pd.concat([cont.rename("c"), ib.rename("i")], axis=1).dropna()
            jn = pd.concat([cont.rename("c"), ib_nd.rename("i")], axis=1).dropna()
            te = float((j["i"] - j["c"]).std() * np.sqrt(TD)) * 100.0
            te_nd = float((jn["i"] - jn["c"]).std() * np.sqrt(TD)) * 100.0
            cm, im = _m(j["c"]), _m(ib.reindex(j.index).dropna())
            row[sname] = {"tracking_error_pct": round(te, 3),
                          "tracking_error_no_deadband_pct": round(te_nd, 3),
                          "cagr_drift_pp": round(im["cagr_pct"] - cm["cagr_pct"], 2),
                          "sortino_drift": round(im["sortino"] - cm["sortino"], 3),
                          "maxdd_drift_pp": round(im["maxdd_pct"] - cm["maxdd_pct"], 2)}
        rec = min(row, key=lambda s: row[s]["tracking_error_pct"])          # lowest deploying TE (granularity)
        row["recommended"] = rec
        report["tiers"][f"${cap//1000}K"] = row

    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(report, indent=2))
    print(f"\nT-278 CAPITAL-TIER GAUNTLET — sleeve in whole shares (Carver deadband 0.05), "
          f"{report['window'][0]}..{report['window'][1]} (3bps, fair conv.)")
    print(f"{'tier':>7} | {'SET':16} {'TE%/yr':>7} {'TE(noDB)':>9} {'CAGRdrift':>10} {'MDDdrift':>9} | rec")
    for tier, row in report["tiers"].items():
        for sname in ["SPY/AGG/GLD", "SPLG/AGG/GLDM"]:
            m = row[sname]
            star = " *" if row["recommended"] == sname else ""
            print(f"{tier:>7} | {sname:16} {m['tracking_error_pct']:>7.2f} {m['tracking_error_no_deadband_pct']:>9.2f} "
                  f"{m['cagr_drift_pp']:>+9.2f}pp {m['maxdd_drift_pp']:>+8.2f}pp |{star}")
    print(f"\n[T278] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
