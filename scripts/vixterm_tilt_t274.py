"""
scripts/vixterm_tilt_t274.py
============================
T-2026-07-02-274 — VIX-term / VVIX IMPLIED-vol sizing tilt on the sleeve's SPY leg.
ONE frozen pre-registered arm (N_trials += 1). No sweep.

FROZEN mapping (a priori — implied-vol state → continuous 0.5-1.0× SPY tilt):
  bw    = VIX / VIX3M                       (term structure; >1 = backwardation/stress)
  s1    = clip((pctl_expanding(bw) − 0.5)·2, 0, 1)     (0 at/below median, 1 at max backwardation)
  s2    = clip((pctl_expanding(VVIX) − 0.7)/0.3, 0, 1)  (VVIX vol-of-vol stress; 0 if VVIX absent)
  stress= max(s1, s2)                        (de-risk when EITHER implied signal is elevated — weight-free)
  scale = clip(1.0 − 0.5·stress, 0.5, 1.0)   (continuous band); applied to the SPY leg (lagged, cash off-leg)

Fair T-255 harness (flat leg @ short rate; ER + 1.5bps both sides). Gates: paired
block-bootstrap ΔSortino + Δwealth vs TWO nulls — (1) the UNCONDITIONED sleeve and
(2) the T-252 REALIZED-vol conditional (the incremental question: does IMPLIED vol
beat REALIZED vol, which was itself redundant with the trend rule, T-262?).
Comparison window = where the VIX tilt is defined (VIX3M from 2006-07).

Prior: LOW (~10%) — T-252's redundancy (the trend overlay already exits in storms)
likely applies to any vol-state input; T-233 found VIX-term trigger-happy.

Output: data/research/t274/vixterm.json + table. Read-only measurement.
Usage: python -m scripts.vixterm_tilt_t274
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
OUT = ROOT / "data" / "research" / "t274" / "vixterm.json"
VT_CFG = SleeveVolTargetConfig(enabled=True, conditional=True, target_vol=0.15, vol_window=20,
                               floor=0.5, ceiling=1.0, extreme_percentile=0.80, min_history=252)


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
VIX, VIX3M, VVIX = _macro("VIX"), _macro("VIX3M"), _macro("VVIX")


def _cash_on(idx):
    return _cash_daily.reindex(idx).ffill().fillna(0.0)


def _expanding_pctl(s: pd.Series, min_history=252) -> pd.Series:
    """Causal expanding percentile-rank of the latest value within its history."""
    return s.expanding(min_periods=min_history).apply(
        lambda w: (w <= w[-1]).mean(), raw=True)


def _vixterm_scale(idx: pd.DatetimeIndex) -> pd.Series:
    """The FROZEN implied-vol tilt scale (SPY), lagged 1 day (causal)."""
    common = VIX.index.intersection(VIX3M.index)
    bw = (VIX.reindex(common) / VIX3M.reindex(common)).dropna()
    s1 = ((_expanding_pctl(bw) - 0.5) * 2).clip(0.0, 1.0)
    s2 = ((_expanding_pctl(VVIX) - 0.7) / 0.3).clip(0.0, 1.0)
    s2 = s2.reindex(bw.index)                              # VVIX may start later
    stress = pd.concat([s1, s2], axis=1).max(axis=1).fillna(s1)   # max(s1, s2); s2 absent → s1
    scale = (1.0 - 0.5 * stress).clip(0.5, 1.0)
    return scale.reindex(idx).ffill().shift(1)             # ffill to trading days, lag 1 (causal)


def _t252_scale(idx: pd.DatetimeIndex) -> pd.Series:
    aret = CLOSES["SPY"].pct_change()
    scale = vol_scale_series(realized_vol(aret, VT_CFG.vol_window), VT_CFG)
    return scale.shift(1).reindex(idx).fillna(1.0)


def sleeve(mode="none", lookback=105):
    """Fair sleeve; SPY leg optionally tilted by mode ∈ {none, t252, vixterm}."""
    spy_scale = None
    if mode == "t252":
        spy_scale = _t252_scale(CLOSES["SPY"].index)
    elif mode == "vixterm":
        spy_scale = _vixterm_scale(CLOSES["SPY"].pct_change().index)
    parts = []
    for k, c in CLOSES.items():
        c = c.astype(float); aret = c.pct_change()
        pos = TrendOverlay(lookback, enabled=True).exposure(c).shift(1)
        ch = _cash_on(aret.index)
        if spy_scale is not None and k == "SPY":
            eff = (pos * spy_scale.reindex(pos.index).fillna(1.0)).clip(0.0, 1.0)
        else:
            eff = pos
        r = eff * (aret - ER[k] / TD) + (1 - eff) * ch
        r = r - eff.diff().abs().fillna(0.0) * (1.0 / 3.0) * TXN
        parts.append((r * (1.0 / 3.0)).rename(k))
    return pd.concat(parts, axis=1, sort=True).dropna(how="all").sum(axis=1, min_count=1).dropna()


def _robo(w):
    etfs = [k for k in w if k != "_cash"]; cw = w.get("_cash", 0.0)
    rets = pd.concat({k: CLOSES[k].pct_change() - ER[k] / TD for k in etfs}, axis=1, sort=True).dropna()
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


def _mdd(r): eq = (1 + r).cumprod(); return float((eq / eq.cummax() - 1).min())
def _so(r): return float(ME.sortino_ratio(r, 0.0, TD))
def _so_ci(r):
    try: return float(ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0).get("ci_low"))
    except Exception: return float("nan")


def _paired(treat, base, L=21, n=1000):
    j = pd.concat({"t": treat, "b": base}, axis=1, sort=True).dropna()
    t, b = j["t"].values, j["b"].values; N = len(t); rng = np.random.default_rng(0); nb = int(np.ceil(N / L))
    dso, dtw = [], []
    def sortino(x): d = x[x < 0]; dd = np.sqrt((d ** 2).mean()) if len(d) else 1e-9; return x.mean() / dd * np.sqrt(TD)
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb); ix = np.concatenate([np.arange(s, s + L) for s in st])[:N]
        dso.append(sortino(t[ix]) - sortino(b[ix])); dtw.append(np.prod(1 + t[ix]) - np.prod(1 + b[ix]))
    q = lambda a, p: round(float(np.percentile(a, p)), 4)
    return {"dSortino_ci": [q(dso, 2.5), q(dso, 97.5)], "dWealth_ci_x_start": [q(dtw, 2.5), q(dtw, 97.5)],
            "P_treat_gt": round(float(np.mean(np.array(dso) > 0)), 3), "n_obs": int(N)}


def main() -> int:
    none, t252, vix = sleeve("none"), sleeve("t252"), sleeve("vixterm")
    r6040 = _robo({"SPY": 0.6, "BOND": 0.4})
    rsch = _robo({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20})
    # comparison window: where the VIX tilt actually acts (VIX3M from 2006-07)
    lo = max(pd.Timestamp("2006-07-17"), none.index[0]); hi = min(none.index[-1], r6040.index[-1])
    W = lambda s: s[(s.index >= lo) & (s.index <= hi)].dropna()

    report = {"task": "T-2026-07-02-274 VIX-term/VVIX implied-vol tilt",
              "window": [str(lo.date()), str(hi.date())], "n_days": int(len(W(none))),
              "frozen_mapping": "scale=clip(1-0.5*max(s1,s2),0.5,1); s1=(pctl(VIX/VIX3M)-0.5)*2; s2=(pctl(VVIX)-0.7)/0.3",
              "strategies": {}, "paired_vs_nulls": {}}
    for nm, r in [("sleeve (unconditioned)", none), ("sleeve + T-252 (realized)", t252),
                  ("sleeve + VIX-term (implied)", vix), ("60_40", r6040), ("schwab_like", rsch)]:
        rw = W(r); eq = (1 + rw).cumprod()
        report["strategies"][nm] = {"sortino": round(_so(rw), 3), "sortino_ci_low": round(_so_ci(rw), 3),
                                    "sharpe": round(float(ME.sharpe_ratio(rw, 0.0, TD)), 3),
                                    "cagr_pct": round((eq.iloc[-1] ** (365.25 / (rw.index[-1] - rw.index[0]).days) - 1) * 100, 2),
                                    "maxdd_pct": round(_mdd(rw) * 100, 2), "wealth_10k": round(10000 * float((1 + rw).prod()), 0)}
    report["paired_vs_nulls"] = {
        "vixterm_vs_unconditioned": _paired(W(vix), W(none)),
        "vixterm_vs_t252_realized": _paired(W(vix), W(t252))}

    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(report, indent=2))
    print(f"\nT-274 VIX-term/VVIX implied-vol tilt — {report['window'][0]}..{report['window'][1]} ({report['n_days']}d)")
    print(f"{'strategy':30}{'Sortino':>9}{'ci_low':>8}{'Sharpe':>8}{'CAGR':>7}{'MaxDD':>8}{'$10k→':>10}")
    for nm, m in report["strategies"].items():
        print(f"{nm:30}{m['sortino']:>9.3f}{m['sortino_ci_low']:>8.3f}{m['sharpe']:>8.3f}{m['cagr_pct']:>6.1f}%{m['maxdd_pct']:>7.1f}%{m['wealth_10k']:>10,.0f}")
    print("\nPAIRED (implied VIX-term − null; 21d block, 1000 iter):")
    for k, p in report["paired_vs_nulls"].items():
        print(f"  {k:28}: ΔSortino 95%CI {p['dSortino_ci']}  Δwealth 95%CI {p['dWealth_ci_x_start']}  P(implied>null)={p['P_treat_gt']:.0%}")
    print(f"[T274] wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
