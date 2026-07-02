"""T-272 — the BTC 4th-asset ARM (completeness-critic hole #8; the last uncovered asset).

PRE-REGISTERED (frozen before running), N_trials += 1, EXPLORATORY (2015+ ≈ 11yr < MBL
bar — scoping read, NOT deployment evidence per [NN-MBL]):
  A (base) = the DEPLOYING ensemble sleeve: SPY/BOND/GOLD EW (1/3 each), multi-speed
             {42,105,210}d long/flat fractional trend (exactly T-260 multi([42,105,210])).
  B (arm)  = A scaled to 95% + a 5% BTC leg under the SAME multi-speed long/flat rule.
BTC size FROZEN at 5% (at ~70% ann vol a 5% sleeve already ≈ half the portfolio risk;
10% would let BTC dominate). BTC on the weekday calendar (≈ the IBIT wrapper a Roth
holder trades; 24/7-vs-market-hours basis caveat noted). Fair T-255 harness: flat leg
earns DGS3MO, ER charged when exposed, txn on Δexposure (BTC 7.5bps/flip vs ETF 1.5bps).
Gates: paired ΔSortino + Δwealth + ΔMaxDD 95% CI (B−A); winters 2018 + 2022 + COVID
(does the trend rule exit in time?).
"""
import csv
import os
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME              # noqa: E402
from core.trend_overlay import TrendOverlay                      # noqa: E402

TD = 252
ER = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040, "BTC": 0.0025}   # BTC ER = IBIT 0.25%
TXN = {"SPY": 0.00015, "BOND": 0.00015, "GOLD": 0.00015, "BTC": 0.00075}  # BTC 7.5bps/flip
SPEEDS = [42, 105, 210]
BTC_W = 0.05   # FROZEN pre-registration


def spy_close():
    r = list(csv.DictReader(open(os.path.join(ROOT, "data/processed/SPY_1d.csv"))))
    return pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in r}).sort_index()


def cser(f):
    d = pd.read_csv(os.path.join(ROOT, f), index_col=0)
    d.index = pd.to_datetime(d.index)
    return d.iloc[:, 0].astype(float).sort_index()


def btc_close(calendar):
    import yfinance as yf
    b = yf.Ticker("BTC-USD").history(period="max")["Close"]
    b.index = pd.to_datetime(b.index).tz_localize(None).normalize()
    b = b[~b.index.duplicated()]
    return b.reindex(calendar).ffill()   # weekday calendar (≈ IBIT capture; Mon incl weekend)


def dgs3_cash():
    d = pd.read_parquet(os.path.join(ROOT, "data/macro/DGS3MO.parquet"))["value"].astype(float)
    d.index = pd.to_datetime(d.index)
    daily = (d.dropna() / 100.0 / TD)
    return daily.reindex(pd.date_range(daily.index[0], daily.index[-1], freq="D")).ffill()


CLOSES = {"SPY": spy_close(), "BOND": cser("data/research/bond_synth_dgs10_t255.csv"),
          "GOLD": cser("data/research/gold_gcf_t255.csv")}
CLOSES["BTC"] = btc_close(CLOSES["SPY"].index)
CASH = dgs3_cash()


def multi_expo(c):
    return pd.concat([TrendOverlay(s, enabled=True).exposure(c) for s in SPEEDS], axis=1).mean(axis=1)


def sleeve(weights, start):
    """weighted multi-speed long/flat sleeve; flat earns cash; ER when exposed; txn on Δexpo."""
    parts = []
    for k, w in weights.items():
        c = CLOSES[k].astype(float)
        aret = c.pct_change()
        pos = multi_expo(c).shift(1)
        ch = CASH.reindex(aret.index).ffill().fillna(0.0)
        r = pos * (aret - ER[k] / TD) + (1 - pos) * ch - pos.diff().abs().fillna(0) * w * TXN[k]
        parts.append((r * w).rename(k))
    s = pd.concat(parts, axis=1)
    return s[s.index >= start].dropna(how="any").sum(axis=1).dropna()


def stats(r):
    r = r.dropna()
    eq = (1 + r).cumprod()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    so = ME.sortino_ratio(r, 0.0, TD)
    try:
        ci = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD),
                                       n_iterations=800, seed=0).get("ci_low")
    except Exception:
        ci = float("nan")
    return so, ci, (eq / eq.cummax() - 1).min(), (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1, 10000 * eq.iloc[-1] / eq.iloc[0]


def ddwin(r, a, b):
    s = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    if len(s) < 2:
        return float("nan")
    eq = (1 + s).cumprod()
    return (eq / eq.cummax() - 1).min()


def paired(a, b, L=21, n=800):
    j = pd.concat({"a": a, "b": b}, axis=1).dropna()
    A, B = j["a"].values, j["b"].values
    N = len(A)
    rng = np.random.default_rng(0)
    dso, dmd, dw = [], [], []

    def so_(x):
        d = x[x < 0]
        return (x.mean() / (np.sqrt((d ** 2).mean()) if len(d) else 1e-9)) * np.sqrt(TD)

    def md_(x):
        eq = np.cumprod(1 + x)
        return (eq / np.maximum.accumulate(eq) - 1).min()
    nb = int(np.ceil(N / L))
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb)
        ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
        aa, bb = A[ix], B[ix]
        dso.append(so_(aa) - so_(bb))
        dmd.append(md_(aa) - md_(bb))
        dw.append(np.prod(1 + aa) - np.prod(1 + bb))
    return ((np.percentile(dso, 2.5), np.percentile(dso, 97.5)),
            (np.percentile(dmd, 2.5), np.percentile(dmd, 97.5)),
            (np.percentile(dw, 2.5), np.percentile(dw, 97.5)))


def main():
    start = CLOSES["BTC"].dropna().index[0] + pd.Timedelta(days=220)  # 210d trend warmup
    A = sleeve({"SPY": 1/3, "BOND": 1/3, "GOLD": 1/3}, start)
    w = (1 - BTC_W) / 3
    B = sleeve({"SPY": w, "BOND": w, "GOLD": w, "BTC": BTC_W}, start)
    # align to common window
    idx = A.index.intersection(B.index)
    A, B = A.reindex(idx).dropna(), B.reindex(idx).dropna()

    print(f"=== T-272 BTC ARM (EXPLORATORY, {A.index[0].date()}→{A.index[-1].date()}, "
          f"{(A.index[-1]-A.index[0]).days/365.25:.1f}y < MBL bar — scoping only) ===")
    print(f"{'sleeve':28}{'Sortino':>9}{'ci_low':>8}{'MaxDD':>8}{'CAGR':>7}{'$10k→':>10}")
    for nm, r in [("A: base ensemble (no BTC)", A), (f"B: + {int(BTC_W*100)}% BTC leg", B)]:
        so, ci, md, cg, tw = stats(r)
        print(f"{nm:28}{so:>9.3f}{ci:>8.3f}{md*100:>7.1f}%{cg*100:>6.1f}%{tw:>10,.0f}")

    (dslo, dshi), (dmlo, dmhi), (dwlo, dwhi) = paired(B, A)
    print(f"\npaired Δ(B − A):  ΔSortino 95%CI [{dslo:+.3f},{dshi:+.3f}]  "
          f"ΔMaxDD 95%CI [{dmlo*100:+.1f}%,{dmhi*100:+.1f}%]  "
          f"Δwealth-mult 95%CI [{dwlo:+.3f},{dwhi:+.3f}]")
    sig_so = "SIG+" if dslo > 0 else ("SIG−" if dshi < 0 else "straddle-0")
    print(f"  → ΔSortino {sig_so}; {'BTC helps DD' if dmlo>0 else ('BTC worsens DD' if dmhi<0 else 'DD unchanged')}")

    print("\n=== winter windows — does the long/flat trend rule exit in time? (in-window MaxDD) ===")
    print(f"{'window':22}{'A (no BTC)':>12}{'B (+BTC)':>12}   BTC-USD buy&hold")
    for nm, a, b in [("2018 crypto winter", "2018-01-01", "2018-12-31"),
                     ("2022 crypto winter", "2021-11-10", "2022-11-21"),
                     ("COVID-2020", "2020-02-19", "2020-03-23")]:
        bh = CLOSES["BTC"][(CLOSES["BTC"].index >= a) & (CLOSES["BTC"].index <= b)]
        bhdd = (bh / bh.cummax() - 1).min() if len(bh) > 1 else float("nan")
        print(f"{nm:22}{ddwin(A,a,b)*100:>11.1f}%{ddwin(B,a,b)*100:>11.1f}%   {bhdd*100:>7.1f}%")

    print("\n*** EXPLORATORY per [NN-MBL] — 11yr BTC history (one bull era) cannot be deployment "
          "evidence; scoping read only. Wrapper caveat: BTC-USD 24/7 daily corr to IBIT 0.82 "
          "(timing, not tracking); monthly-signal sleeve robust to it. ***")


if __name__ == "__main__":
    main()
