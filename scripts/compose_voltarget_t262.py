"""
scripts/compose_voltarget_t262.py
=================================
T-2026-07-02-262 — compose T-252 conditional vol-targeting into the T-236 sleeve
on D's FAIR harness (T-255). ONE pre-registered trial (N_trials += 1).

Baseline = D's `sleeve_returns_fair` verbatim (EW SPY/BOND/GOLD long-flat; flat
leg earns the short rate; ER when long; 1.5bps on flips). Treatment = the SAME,
with T-252 conditional vol-targeting applied to the SPY LEG ONLY, EXACTLY the
T-252 spec (expanding-P80 extreme-vol gate, target 0.15, 20d vol, floor 0.5,
ceiling 1.0 — no re-tuning). BOND/GOLD legs unchanged (vol-targeting is a
risk-asset lever). The vol-scaled portion of the SPY leg earns cash (like the
flat leg); the extra scale-turnover is charged at the same 1.5bps.

Gates: paired block-bootstrap ΔSortino + ΔMaxDD + Δterminal-wealth (treatment −
baseline) CIs; named windows COVID-2020 + 2022; integer-share interaction at
$10K (does vol-scaling break whole-share tracking?). MEASUREMENT only — the
module stays default-OFF, nothing enabled.

Output: data/research/t262/compose.json + table.
Usage: python -m scripts.compose_voltarget_t262
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from core.trend_overlay import TrendOverlay  # noqa: E402
from engines.engine_b_risk.sleeve_vol_target import (  # noqa: E402
    SleeveVolTargetConfig, vol_scale_series, realized_vol,
)

TD = 252
ER = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040}
TXN = 0.00015
OUT = ROOT / "data" / "research" / "t262" / "compose.json"

# EXACT T-252 spec — no re-tuning.
VT_CFG = SleeveVolTargetConfig(enabled=True, conditional=True, target_vol=0.15,
                               vol_window=20, floor=0.5, ceiling=1.0,
                               extreme_percentile=0.80, min_history=252)


def _spy_close():
    r = list(csv.DictReader(open(ROOT / "data/processed/SPY_1d.csv")))
    return pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in r}).sort_index()


def _csv_ser(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index)
    return d.iloc[:, 0].astype(float).sort_index()


def _macro(s):
    d = pd.read_parquet(ROOT / f"data/macro/{s}.parquet")["value"].astype(float)
    d.index = pd.to_datetime(d.index)
    return d.dropna().sort_index()


SPY = _spy_close()
BOND = _csv_ser(ROOT / "data/research/bond_synth_dgs10_t255.csv")
GOLD = _csv_ser(ROOT / "data/research/gold_gcf_t255.csv")
CLOSES = {"SPY": SPY, "BOND": BOND, "GOLD": GOLD}
_dgs3 = _macro("DGS3MO")
_cash_daily = (_dgs3 / 100.0 / TD).reindex(pd.date_range(_dgs3.index[0], _dgs3.index[-1], freq="D")).ffill()


def _cash_on(idx):
    return _cash_daily.reindex(idx).ffill().fillna(0.0)


def _spy_vt_scale(spy_close: pd.Series) -> pd.Series:
    """The EXACT T-252 conditional vol-target scale on SPY, lagged 1 day
    (causal: the scale used for day t is computed from realized vol ≤ t-1)."""
    aret = spy_close.pct_change()
    rv = realized_vol(aret, VT_CFG.vol_window)
    scale = vol_scale_series(rv, VT_CFG)     # ∈[0.5,1.0], =1.0 outside extreme states
    return scale.shift(1).reindex(aret.index).fillna(1.0)


def sleeve_fair(lookback=105, voltarget=False):
    """D's fair sleeve; when voltarget=True, the SPY leg's long exposure is
    additionally scaled by the T-252 conditional vol-target (SPY leg only)."""
    parts = []
    spy_scale = _spy_vt_scale(CLOSES["SPY"]) if voltarget else None
    for k, c in CLOSES.items():
        c = c.astype(float); aret = c.pct_change()
        sig = TrendOverlay(lookback, enabled=True).exposure(c); pos = sig.shift(1)
        ch = _cash_on(aret.index)
        if voltarget and k == "SPY":
            eff = (pos * spy_scale.reindex(pos.index).fillna(1.0)).clip(0.0, 1.0)
        else:
            eff = pos
        r = eff * (aret - ER[k] / TD) + (1 - eff) * ch          # long(scaled): asset−ER; rest: cash
        turn = eff.diff().abs().fillna(0.0)                     # trend flip + (SPY) vol-scale change
        r = r - turn * (1.0 / 3.0) * TXN
        parts.append((r * (1.0 / 3.0)).rename(k))
    return pd.concat(parts, axis=1, sort=True).dropna(how="all").sum(axis=1, min_count=1).dropna()


def _maxdd(r):
    eq = (1 + r).cumprod(); return float((eq / eq.cummax() - 1).min())


def _cagr(r):
    eq = (1 + r).cumprod()
    return float((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (eq.index[-1] - eq.index[0]).days) - 1)


def _so(r):
    return float(ME.sortino_ratio(r, 0.0, TD))


def _so_ci(r):
    try:
        return float(ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD),
                                                n_iterations=1000, seed=0).get("ci_low"))
    except Exception:
        return float("nan")


def _paired(treat, base, L=21, n=1000):
    """Paired block-bootstrap (treatment − baseline): ΔSortino, ΔMaxDD,
    Δterminal-wealth CIs + P(treatment Sortino > baseline)."""
    j = pd.concat({"t": treat, "b": base}, axis=1).dropna()
    t, b = j["t"].values, j["b"].values
    N = len(t); rng = np.random.default_rng(0); nb = int(np.ceil(N / L))
    dso, dmdd, dtw = [], [], []

    def sortino(x):
        d = x[x < 0]; dd = np.sqrt((d ** 2).mean()) if len(d) else 1e-9
        return (x.mean() / dd) * np.sqrt(TD)

    def mdd(x):
        eq = np.cumprod(1 + x); return float((eq / np.maximum.accumulate(eq) - 1).min())

    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb)
        ix = np.concatenate([np.arange(s, s + L) for s in st])[:N]
        tt, bb = t[ix], b[ix]
        dso.append(sortino(tt) - sortino(bb))
        dmdd.append(mdd(tt) - mdd(bb))              # +ve = treatment shallower DD (better)
        dtw.append(np.prod(1 + tt) - np.prod(1 + bb))
    q = lambda a, p: float(np.percentile(a, p))
    return {"dSortino_ci": [round(q(dso, 2.5), 4), round(q(dso, 97.5), 4)],
            "dMaxDD_ci": [round(q(dmdd, 2.5), 4), round(q(dmdd, 97.5), 4)],
            "dWealth_ci_x_start": [round(q(dtw, 2.5), 4), round(q(dtw, 97.5), 4)],
            "P_treat_sortino_gt_base": round(float(np.mean(np.array(dso) > 0)), 3)}


def _win(r, a, b):
    return r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))].dropna()


def _integer_te(voltarget: bool, capital=10_000.0, start="2020-01-01"):
    """T-257 machinery: does vol-scaling break whole-share tracking? Uses REAL
    tradeable ETF prices (SPY/AGG/GLD, data/processed) at $capital. Returns the
    annualized tracking error of the integer book vs its own continuous target."""
    px = {}
    for etf, key in [("SPY", "SPY"), ("AGG", "BOND"), ("GLD", "GOLD")]:
        p = pd.read_csv(ROOT / f"data/processed/{etf}_1d.csv", index_col=0, parse_dates=True)["Close"].astype(float)
        px[etf] = p.loc[start:]
    idx = None
    for p in px.values():
        idx = p.index if idx is None else idx.intersection(p.index)
    idx = idx.sort_values()
    spy_scale = _spy_vt_scale(px["SPY"]) if voltarget else None
    # per-asset target weight (1/3 long/flat; SPY scaled if voltarget)
    W = {}
    for etf, src in [("SPY", "SPY"), ("AGG", "AGG"), ("GLD", "GLD")]:
        c = px[etf]; sig = TrendOverlay(105, enabled=True).exposure(c).shift(1).reindex(idx).fillna(0.0)
        w = sig * (1.0 / 3.0)
        if voltarget and etf == "SPY":
            w = (w * spy_scale.reindex(idx).fillna(1.0)).clip(0.0, 1.0 / 3.0)
        W[etf] = w
    weights = pd.DataFrame(W).reindex(idx).dropna()
    pxdf = pd.DataFrame({e: px[e].reindex(weights.index).ffill() for e in px})
    # continuous vs integer books
    aret = pxdf.pct_change()
    cont = (weights.shift(1) * aret).sum(axis=1).dropna()
    equity = float(capital); shares = {e: 0 for e in px}; cash = equity; rets = []; prev = None
    for d in weights.index:
        if prev is not None:
            mv = sum(shares[e] * pxdf.at[d, e] for e in px); ne = mv + cash
            rets.append((d, ne / equity - 1.0 if equity > 0 else 0.0)); equity = ne
        tgt = {e: int(np.floor(equity * weights.at[d, e] / pxdf.at[d, e])) if pxdf.at[d, e] > 0 else 0 for e in px}
        turn = sum(abs(tgt[e] - shares[e]) * pxdf.at[d, e] for e in px)
        equity -= turn * (TXN); shares = tgt; cash = equity - sum(shares[e] * pxdf.at[d, e] for e in px); prev = d
    ib = pd.Series({d: r for d, r in rets})
    j = pd.concat([cont.rename("c"), ib.rename("i")], axis=1).dropna()
    return round(float((j["i"] - j["c"]).std() * np.sqrt(TD)) * 100.0, 3)


def main() -> int:
    base = sleeve_fair(voltarget=False)
    vt = sleeve_fair(voltarget=True)
    start = max(base.index[0], vt.index[0]); end = min(base.index[-1], vt.index[-1])
    base, vt = base[start:end], vt[start:end]

    report = {"task": "T-2026-07-02-262 compose T-252 vol-target into the fair sleeve",
              "window": [str(start.date()), str(end.date())], "n_obs": int(len(base)),
              "t252_spec": {"conditional": True, "target_vol": 0.15, "vol_window": 20,
                            "floor": 0.5, "ceiling": 1.0, "extreme_percentile": 0.80},
              "full": {}, "named_windows": {}, "paired": {}, "integer_share_10k": {}}

    for nm, r in [("sleeve_fair (baseline)", base), ("sleeve_fair + T-252", vt)]:
        report["full"][nm] = {"sortino": round(_so(r), 3), "sortino_ci_low": round(_so_ci(r), 3),
                              "sharpe": round(float(ME.sharpe_ratio(r, 0.0, TD)), 3),
                              "cagr_pct": round(_cagr(r) * 100, 2), "maxdd_pct": round(_maxdd(r) * 100, 2),
                              "wealth_10k": round(10000 * float((1 + r).prod()), 0)}

    for wnm, a, b in [("COVID_2020", "2020-02-01", "2020-06-30"), ("bear_2022", "2022-01-01", "2022-12-31")]:
        rb, rv = _win(base, a, b), _win(vt, a, b)
        report["named_windows"][wnm] = {
            "baseline": {"maxdd_pct": round(_maxdd(rb) * 100, 2), "sortino": round(_so(rb), 3),
                         "cum_ret_pct": round(float((1 + rb).prod() - 1) * 100, 2)},
            "with_t252": {"maxdd_pct": round(_maxdd(rv) * 100, 2), "sortino": round(_so(rv), 3),
                          "cum_ret_pct": round(float((1 + rv).prod() - 1) * 100, 2)}}

    report["paired"] = _paired(vt, base)
    report["integer_share_10k"] = {
        "baseline_te_pct": _integer_te(voltarget=False),
        "with_t252_te_pct": _integer_te(voltarget=True)}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"\nT-262 — compose T-252 into the fair sleeve  {report['window'][0]}..{report['window'][1]} ({report['n_obs']} bars)")
    print(f"{'strategy':26}{'Sortino':>9}{'ci_low':>8}{'Sharpe':>8}{'CAGR':>7}{'MaxDD':>8}{'$10k→':>10}")
    for nm, m in report["full"].items():
        print(f"{nm:26}{m['sortino']:>9.3f}{m['sortino_ci_low']:>8.3f}{m['sharpe']:>8.3f}"
              f"{m['cagr_pct']:>6.1f}%{m['maxdd_pct']:>7.1f}%{m['wealth_10k']:>10,.0f}")
    p = report["paired"]
    print(f"\nPAIRED (T-252 − baseline, 21d block, 1000 iter):")
    print(f"  ΔSortino 95%CI {p['dSortino_ci']}  ΔMaxDD 95%CI {p['dMaxDD_ci']} (+=shallower/better)  "
          f"Δwealth(×start) 95%CI {p['dWealth_ci_x_start']}  P(T-252 Sortino>base)={p['P_treat_sortino_gt_base']:.0%}")
    print("\nNamed windows (MaxDD / cum-ret):")
    for wnm, w in report["named_windows"].items():
        print(f"  {wnm:12}: baseline MaxDD {w['baseline']['maxdd_pct']:>6.1f}% ret {w['baseline']['cum_ret_pct']:+.1f}%  |  "
              f"+T-252 MaxDD {w['with_t252']['maxdd_pct']:>6.1f}% ret {w['with_t252']['cum_ret_pct']:+.1f}%")
    isr = report["integer_share_10k"]
    print(f"\nInteger-share @ $10K (TE vs own continuous): baseline {isr['baseline_te_pct']}%/yr  |  "
          f"+T-252 {isr['with_t252_te_pct']}%/yr  (does vol-scaling break whole-share tracking?)")
    print(f"\n[T262] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
