"""T-213 standalone validation for sector-neutral industry momentum.

DESCRIPTIVE ONLY — L/S momentum Sharpe/MDD/CAGR vs an equal-weight-9
sector benchmark, sector-neutrality confirmation (realized per-sector net
exposure), and orthogonality (corr to the equal-weight benchmark). NOT the
beat-the-robo measurement (post-composition, Engine-C T-211).

  python scripts/industry_momentum_t213.py
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.engine_a_alpha.screens import industry_momentum as im  # noqa: E402

TD = 252
STOOQ = ROOT / "data" / "raw" / "stooq" / "daily" / "us"


def _load(sec: str) -> pd.Series:
    import glob
    hits = glob.glob(str(STOOQ / "**" / f"{sec.lower()}.us.txt"), recursive=True)
    df = pd.read_csv(hits[0])
    df.columns = [c.strip("<>").lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"], format="%Y%m%d")
    return df.set_index("date")["close"].astype(float).sort_index()


def _sharpe(r):
    sd = r.std(ddof=1); return 0.0 if sd < 1e-12 else float(r.mean() / sd * np.sqrt(TD))
def _mdd(r):
    eq = (1 + r).cumprod(); return float(((eq - eq.cummax()) / eq.cummax()).min())
def _cagr(r):
    eq = (1 + r).cumprod(); yrs = (r.index[-1] - r.index[0]).days / 365.25
    return float(eq.iloc[-1] ** (1 / yrs) - 1)
def _boot_lo(r, seed=42, nit=1000, blk=10):
    rng = np.random.default_rng(seed); v = r.values; n = len(v); nb = int(np.ceil(n / blk)); s = []
    for _ in range(nit):
        st = rng.integers(0, n - blk + 1, size=nb)
        sm = np.concatenate([v[i:i + blk] for i in st])[:n]
        sd = sm.std(ddof=1); s.append(0.0 if sd < 1e-12 else sm.mean() / sd * np.sqrt(TD))
    return float(np.percentile(s, 2.5))


def main() -> int:
    closes = {s: _load(s) for s in im.GICS9}
    px = pd.DataFrame(closes).dropna()
    rets = px.pct_change().dropna()
    print(f"[T213] {len(px)} days {px.index[0].date()}->{px.index[-1].date()}, sectors {im.GICS9}")

    # Monthly rebalance: weights as-of last trading day of each month, applied next month.
    rebal_days = rets.index.to_series().groupby([rets.index.year, rets.index.month]).last().tolist()
    w_hist = {}
    for d in rebal_days:
        w = im.sector_momentum_weights({s: px[s] for s in im.GICS9}, d)
        if w:
            w_hist[d] = w
    wdf = pd.DataFrame(w_hist).T.reindex(columns=im.GICS9).fillna(0.0).sort_index()
    # forward-fill weights daily (held until next rebalance), lag 1 day (apply after decision)
    wdaily = wdf.reindex(rets.index, method="ffill").shift(1).fillna(0.0)

    ls_ret = (wdaily * rets).sum(axis=1).loc[wdaily.abs().sum(axis=1) > 0]
    ew_ret = rets.mean(axis=1).loc[ls_ret.index]   # equal-weight-9 benchmark

    print(f"\n[L/S MOMENTUM] (dollar-neutral top-3/bottom-3, monthly, {len(ls_ret)} days)")
    print(f"  Sharpe {_sharpe(ls_ret):.3f} (ci_low {_boot_lo(ls_ret):.3f})  "
          f"MDD {_mdd(ls_ret)*100:.1f}%  CAGR {_cagr(ls_ret)*100:.2f}%")
    print(f"[EQUAL-WEIGHT-9 benchmark]")
    print(f"  Sharpe {_sharpe(ew_ret):.3f}  MDD {_mdd(ew_ret)*100:.1f}%  CAGR {_cagr(ew_ret)*100:.2f}%")

    # Sector-neutrality: time-average net exposure per sector (≈0 if no tilt)
    net = wdaily.loc[ls_ret.index].mean()
    print(f"\n[SECTOR-NEUTRALITY] time-avg net weight per sector (≈0 = no persistent tilt):")
    print("  " + "  ".join(f"{s}:{net[s]:+.3f}" for s in im.GICS9))
    print(f"  max |avg net| = {net.abs().max():.3f}  (sum {net.sum():+.3f})")
    turn = wdaily.diff().abs().sum(axis=1).loc[ls_ret.index].mean() * TD
    print(f"  annualized turnover ~ {turn:.1f}x")

    # Orthogonality
    rho = float(np.corrcoef(ls_ret.values, ew_ret.values)[0, 1])
    print(f"\n[ORTHOGONALITY] corr(L/S, equal-weight-9) = {rho:+.3f} "
          f"({'low → genuine rotation' if abs(rho) < 0.3 else 'beware hidden beta'})")
    print("\n[T213] standalone validation only — NO beat-the-robo measurement (post-composition).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
