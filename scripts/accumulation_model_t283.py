"""
scripts/accumulation_model_t283.py
==================================
T-2026-07-06-283 — the ACCUMULATION model: which validated config maxes terminal
wealth for a CONTRIBUTING investor ($7K/yr Roth, ~40yr horizon, won't-sell).

Lump-sum backtests miss the accumulator's reality: drawdowns during accumulation
are PURCHASES (DCA buys the dip). This re-analyzes the validated fair-harness
configs under a frozen $7K/yr annual contribution over 2000-2026 (the available
fair window; the longest honest proxy for the 40yr path) + 5 staggered starts.

Configs (fair T-255 conventions; SPY TR = price + a frozen 1.8%/yr dividend
add-back applied CONSISTENTLY to ALL SPY exposure so the comparison is fair —
the fair harness's SPY legs are otherwise price-only):
  (a) SPY buy-hold TR   (b) plain trend sleeve   (c) 60_40   (d) schwab_like
  (e) D/T-282 trend-gated-2x — ADDED when it lands (run a-d now).

0 new N_trials — a re-analysis of validated configs, not a new hypothesis.
Output: data/research/t283/accumulation.json + tables.
Usage: python -m scripts.accumulation_model_t283
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.trend_overlay import TrendOverlay  # noqa: E402

TD = 252
ER = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040}
TXN = 0.00015
SPY_DIV_ANN = 0.018            # FROZEN ~S&P 500 dividend yield 2000-2026 (approx; applied to ALL SPY exposure)
CONTRIB = 7000.0               # $/yr, FROZEN annual (Roth-style, contributed each Jan)
OUT = ROOT / "data" / "research" / "t283" / "accumulation.json"


def _spy():
    r = list(csv.DictReader(open(ROOT / "data/processed/SPY_1d.csv")))
    return pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in r}).sort_index()


def _csv_ser(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index)
    return d.iloc[:, 0].astype(float).sort_index()


SPY = _spy()
BOND = _csv_ser(ROOT / "data/research/bond_synth_dgs10_t255.csv")
GOLD = _csv_ser(ROOT / "data/research/gold_gcf_t255.csv")
CLOSES = {"SPY": SPY, "BOND": BOND, "GOLD": GOLD}
_dgs3 = pd.read_parquet(ROOT / "data/macro/DGS3MO.parquet")["value"].astype(float)
_dgs3.index = pd.to_datetime(_dgs3.index)
_cash = (_dgs3.dropna().sort_index() / 100.0 / TD)
_cash = _cash.reindex(pd.date_range(_cash.index[0], _cash.index[-1], freq="D")).ffill()
DIV_D = SPY_DIV_ANN / TD


def _cash_on(idx): return _cash.reindex(idx).ffill().fillna(0.0)
def _spy_tr_ret(idx): return SPY.reindex(idx).pct_change() + DIV_D          # SPY total return (price + div)


def spy_buyhold():
    idx = SPY.index
    return (_spy_tr_ret(idx) - ER["SPY"] / TD).dropna()


def sleeve(lookback=105):
    parts = []
    for k, c in CLOSES.items():
        c = c.astype(float); ar = c.pct_change()
        if k == "SPY": ar = ar + DIV_D                                     # SPY leg gets dividends (TR)
        pos = TrendOverlay(lookback, enabled=True).exposure(c).shift(1)
        ch = _cash_on(ar.index)
        r = pos * (ar - ER[k] / TD) + (1 - pos) * ch
        r = r - pos.diff().abs().fillna(0.0) * (1.0 / 3.0) * TXN
        parts.append((r * (1.0 / 3.0)).rename(k))
    return pd.concat(parts, axis=1, sort=True).dropna(how="all").sum(axis=1, min_count=1).dropna()


def robo(w):
    etfs = [k for k in w if k != "_cash"]; cw = w.get("_cash", 0.0)
    def aret(k):
        a = CLOSES[k].pct_change() - ER[k] / TD
        return (a + DIV_D) if k == "SPY" else a
    rets = pd.concat({k: aret(k) for k in etfs}, axis=1, sort=True).dropna()
    cr = _cash_on(rets.index); hold = {k: w[k] for k in etfs}; cash = cw; out = {}; pm = None
    for dt, row in rets.iterrows():
        m = (dt.year, dt.month); rc = 0.0
        if pm is not None and m != pm:
            tot = sum(hold.values()) + cash; nh = {k: tot * w[k] for k in etfs}; nc = tot * cw
            rc = sum(abs(nh[k] - hold[k]) for k in etfs) / max(tot, 1e-9) * TXN; hold = nh; cash = nc
        prev = sum(hold.values()) + cash
        for k in etfs: hold[k] *= (1 + row[k])
        cash *= (1 + cr.loc[dt]); out[dt] = (sum(hold.values()) + cash) / prev - 1 - rc; pm = m
    return pd.Series(out)


def accumulate(r: pd.Series, start: str, contrib=CONTRIB):
    """DCA: contribute `contrib` each Jan (first trading day of the year); compound
    daily. Returns (wealth path, total_contributed, worst_$_drawdown, frac_underwater)."""
    r = r[r.index >= pd.Timestamp(start)].dropna()
    if len(r) < 252:
        return None
    years = sorted(set(r.index.year))
    contrib_days = {}
    for y in years:
        yd = r.index[r.index.year == y]
        if len(yd): contrib_days[yd[0]] = contrib
    W = 0.0; contributed = 0.0; path = []; cum_contrib = []
    for d in r.index:
        if d in contrib_days:
            W += contrib_days[d]; contributed += contrib_days[d]
        W *= (1.0 + r.loc[d])
        path.append(W); cum_contrib.append(contributed)
    wp = pd.Series(path, index=r.index); cc = pd.Series(cum_contrib, index=r.index)
    worst_dd = float((wp - wp.cummax()).min())                 # worst $ drawdown
    underwater = float((wp < cc).mean())                       # frac of days wealth < $ contributed
    return {"terminal": float(wp.iloc[-1]), "contributed": float(contributed),
            "mult_on_contrib": round(float(wp.iloc[-1] / contributed), 3),
            "worst_dollar_dd": round(worst_dd, 0), "frac_underwater": round(underwater, 3),
            "years": round((r.index[-1] - r.index[0]).days / 365.25, 1)}, wp


def main() -> int:
    configs = {"SPY_buyhold_TR": spy_buyhold(), "trend_sleeve": sleeve(),
               "60_40": robo({"SPY": 0.6, "BOND": 0.4}),
               "schwab_like": robo({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20})}
    lo = max(c.index[0] for c in configs.values())
    starts = [str(lo.date())] + [s for s in ["2003-01-01", "2006-01-01", "2009-01-01", "2012-01-01"]
                                 if pd.Timestamp(s) >= lo]

    report = {"task": "T-2026-07-06-283 accumulation model", "contrib_per_yr": CONTRIB,
              "spy_div_ann_assumed": SPY_DIV_ANN, "data_window": [str(lo.date()), str(min(c.index[-1] for c in configs.values()).date())],
              "note": "40yr horizon requested; fair data is 2000-2026 (26yr) — the longest honest proxy; staggered starts show sequence sensitivity. T-282 2x arm added when it lands.",
              "full_2000": {}, "start_sensitivity": {}}

    # primary: full window from the earliest start
    for nm, r in configs.items():
        m, _ = accumulate(r, starts[0])
        report["full_2000"][nm] = m

    # lump-sum vs DCA: does accumulation WIDEN or NARROW buy-hold's edge over the sleeve?
    def lump(r, start):
        r = r[r.index >= pd.Timestamp(start)].dropna()
        return float((1 + r).prod())      # terminal per $1 invested day-1
    ls = {nm: lump(r, starts[0]) for nm, r in configs.items()}
    dca_ratio = report["full_2000"]["SPY_buyhold_TR"]["mult_on_contrib"] / report["full_2000"]["trend_sleeve"]["mult_on_contrib"]
    ls_ratio = ls["SPY_buyhold_TR"] / ls["trend_sleeve"]
    report["lump_vs_dca"] = {"lumpsum_BH_over_sleeve": round(ls_ratio, 3),
                             "dca_BH_over_sleeve": round(dca_ratio, 3),
                             "dca_widens_edge": bool(dca_ratio > ls_ratio)}
    # start sensitivity: terminal mult-on-contributions per start, + BH/sleeve ratio
    for s in starts:
        row = {}
        for nm, r in configs.items():
            res = accumulate(r, s)
            if res: row[nm] = res[0]["mult_on_contrib"]
        if "SPY_buyhold_TR" in row and "trend_sleeve" in row:
            row["BH_over_sleeve_ratio"] = round(row["SPY_buyhold_TR"] / row["trend_sleeve"], 3)
        report["start_sensitivity"][s[:4]] = row

    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(report, indent=2))

    f = report["full_2000"]
    print(f"\nT-283 ACCUMULATION — ${CONTRIB:,.0f}/yr DCA, {report['data_window'][0]}..{report['data_window'][1]} "
          f"(~{f['SPY_buyhold_TR']['years']:.0f}yr, SPY TR +{SPY_DIV_ANN:.1%} div)")
    print(f"{'config':18}{'terminal$':>12}{'×contrib':>10}{'worst $DD':>12}{'%underwater':>12}")
    for nm, m in f.items():
        print(f"{nm:18}{m['terminal']:>12,.0f}{m['mult_on_contrib']:>10.2f}{m['worst_dollar_dd']:>12,.0f}{m['frac_underwater']*100:>11.1f}%")
    print(f"\nSTART-DATE SENSITIVITY (terminal × contributions; BH/sleeve ratio):")
    print(f"{'start':>7}" + "".join(f"{k[:12]:>13}" for k in ['SPY_buyhold_TR', 'trend_sleeve', '60_40', 'schwab_like', 'BH_over_sleeve_ratio']))
    for s, row in report["start_sensitivity"].items():
        print(f"{s:>7}" + "".join(f"{row.get(k, float('nan')):>13.2f}" for k in ['SPY_buyhold_TR', 'trend_sleeve', '60_40', 'schwab_like', 'BH_over_sleeve_ratio']))
    lvd = report["lump_vs_dca"]
    print(f"\nLUMP-SUM vs DCA (does accumulation widen BH's edge over the sleeve?): "
          f"lumpsum {lvd['lumpsum_BH_over_sleeve']}× → DCA {lvd['dca_BH_over_sleeve']}× "
          f"⇒ DCA {'WIDENS' if lvd['dca_widens_edge'] else 'NARROWS'} the buy-hold edge")
    print(f"\n[T283] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
