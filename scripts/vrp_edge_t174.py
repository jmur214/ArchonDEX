"""T-174: VRP (variance risk premium) equity-implementable edge backtest.

Reproducible from the repo: fetches ^VIX + ^GSPC via yfinance, pulls the
canonical base curve from S3, builds VRP = VIX - RV21(GSPC), and tests a
VRP exposure-timing overlay on the base book net of cost. Gate (pre-
registered, see docs/Audit/vrp_edge_t174_2026_06_16.md): dSharpe ci_low > 0
net-of-cost on the 26yr base substrate.

  python scripts/vrp_edge_t174.py

Honest scope: the pure VRP harvest is short-options (NOT implementable);
this tests only VRP's return-prediction content as an equity exposure overlay.
Data gitignored under data/external/{vrp,base_curve}/.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
VRP_DIR = ROOT / "data/external/vrp"
BASE_LOCAL = ROOT / "data/external/base_curve/t118r_v1_26yr_arm0_3b403882.csv"
BASE_S3 = ("s3://archondex-results-407539788432/t118r-v1-26yr/arm0_v1/26yr/"
           "rep1/3b403882-8ad5-4aba-a4c1-d1b15c8bce6f/portfolio_snapshots.csv")
TD = 252
SEED = 42
NIT = 1000
BLK = 10
COST_PER_DW = 0.0010  # 10 bps round-trip per unit |delta-weight|


def _ensure_market():
    VRP_DIR.mkdir(parents=True, exist_ok=True)
    if not (VRP_DIR / "vix.csv").exists() or not (VRP_DIR / "gspc.csv").exists():
        import yfinance as yf
        for tk, fn in [("^VIX", "vix"), ("^GSPC", "gspc")]:
            c = yf.Ticker(tk).history(start="1995-01-01", end="2026-01-01",
                                      auto_adjust=True)["Close"].dropna()
            c.index = pd.to_datetime(c.index).tz_localize(None)
            c.to_csv(VRP_DIR / f"{fn}.csv")
    if not BASE_LOCAL.exists():
        BASE_LOCAL.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["aws", "s3", "cp", BASE_S3, str(BASE_LOCAL),
                        "--profile", "archondex", "--quiet"], check=True)


def sharpe(r):
    sd = r.std(ddof=1)
    return 0.0 if sd < 1e-12 else float(r.mean() / sd * np.sqrt(TD))


def mdd(r):
    eq = (1 + r).cumprod()
    return float(((eq - eq.cummax()) / eq.cummax()).min())


def boot_diff(a, b):
    rng = np.random.default_rng(SEED)
    n = len(a); nb = int(np.ceil(n / BLK)); av = a.values; bv = b.values; s = []
    for _ in range(NIT):
        st = rng.integers(0, n - BLK + 1, size=nb)
        sel = np.concatenate([np.arange(i, i + BLK) for i in st])[:n]
        sa, sb = av[sel], bv[sel]
        da, db = sa.std(ddof=1), sb.std(ddof=1)
        sha = 0.0 if da < 1e-12 else sa.mean() / da * np.sqrt(TD)
        shb = 0.0 if db < 1e-12 else sb.mean() / db * np.sqrt(TD)
        s.append(sha - shb)
    return float(np.percentile(s, 2.5)), float(np.percentile(s, 97.5))


def main() -> int:
    _ensure_market()
    vix = pd.read_csv(VRP_DIR / "vix.csv", index_col=0, parse_dates=True).iloc[:, 0]
    gspc = pd.read_csv(VRP_DIR / "gspc.csv", index_col=0, parse_dates=True).iloc[:, 0]
    vix.index = pd.to_datetime(vix.index).tz_localize(None)
    gspc.index = pd.to_datetime(gspc.index).tz_localize(None)
    rv21 = np.log(gspc / gspc.shift(1)).rolling(21).std() * np.sqrt(252) * 100
    vrp = (vix - rv21).dropna()

    b = pd.read_csv(BASE_LOCAL); b["timestamp"] = pd.to_datetime(b["timestamp"])
    br = (b.sort_values("timestamp").set_index("timestamp")["equity"].astype(float)
          .pct_change().dropna())
    idx = br.index.intersection(vrp.index)
    br = br.loc[idx]; vrp = vrp.loc[idx]
    exp_med = vrp.expanding(min_periods=252).median()

    def overlay(wlow, trigger):
        sig = (vrp >= exp_med) if trigger == "median" else (vrp >= 0)
        w = pd.Series(np.where(sig, 1.0, wlow), index=idx).shift(1).fillna(1.0)
        cost = COST_PER_DW * w.diff().abs().fillna(0.0)
        return (w * br - cost).dropna()

    print(f"days {len(idx)} ({idx[0].date()}->{idx[-1].date()})  "
          f"base Sharpe {sharpe(br):.3f} MDD {mdd(br)*100:.1f}%")
    print(f"{'arm':24s} {'Sharpe':>7} {'dSharpe':>8} {'ci_low':>8} {'ci_hi':>7} {'MDD':>7} pass")
    for lbl, wlow, trig in [("PRIMARY median w=0.5", 0.5, "median"),
                            ("median w=0.0", 0.0, "median"),
                            ("VRP<0 w=0.5", 0.5, "sign"),
                            ("VRP<0 w=0.0", 0.0, "sign")]:
        ov = overlay(wlow, trig); c = ov.index.intersection(br.index)
        d = sharpe(ov) - sharpe(br.loc[c]); lo, hi = boot_diff(ov.loc[c], br.loc[c])
        print(f"{lbl:24s} {sharpe(ov):7.3f} {d:+8.3f} {lo:+8.3f} {hi:+7.3f} "
              f"{mdd(ov)*100:6.1f}% {'PASS' if lo > 0 else 'fail'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
