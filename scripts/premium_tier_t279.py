"""T-279 — the $65-70K+ TIER test: DIRECT premium harvesting (N_trials += 1, tier-labeled).

Capital-adaptive: the income gauntlet was skipped at $5-15K on IMPLEMENTABILITY (the WTPI
wrapper divergence, T-261). At $65K+ a real XSP cash-secured put IS the CBOE PUT-index
mechanic (monthly ATM CSP, T-bill collateral) → the wrapper-transfer objection disappears,
so the backtest is implementation-faithful AT THIS TIER.

PRE-REGISTERED (frozen before running): the $65K+ config = 70% deploying trend sleeve
(SPY/BOND/GOLD EW, multi-speed {42,105,210}d long/flat) + 30% CBOE PUT index, monthly
rebalanced. Fair T-255 harness (DGS3MO cash, ER, txn). PUT roll cost 7.5 bps/mo (XSP
bid/ask on the monthly roll — the index assumes perfect rolling). Gates: paired ΔSortino
+ Δwealth + ΔMaxDD 95% CI vs the sleeve ALONE and vs BOTH robos; named gap windows 1987 /
2008-GFC / COVID (put-write crashes exactly where the sleeve is weakest — the combination
must survive those better than the robo, or it FAILS). Prior LOW-MEDIUM (~25-30%).
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
from scripts.income_leg_screener_t261 import put_returns         # noqa: E402  (reuse the splice)

TD = 252
ER = {"SPY": 0.0009, "BOND": 0.0003, "GOLD": 0.0040}
TXN = 0.00015
SPEEDS = [42, 105, 210]
PREMIUM_W = 0.30           # FROZEN split: 70% sleeve / 30% premium
PUT_ROLL_MO = 0.00075      # 7.5 bps/mo XSP roll implementation drag


def _spy():
    r = list(csv.DictReader(open(os.path.join(ROOT, "data/processed/SPY_1d.csv"))))
    return pd.Series({datetime.strptime(x["Date"][:10], "%Y-%m-%d"): float(x["Close"]) for x in r}).sort_index()


def _cser(f):
    d = pd.read_csv(os.path.join(ROOT, f), index_col=0)
    d.index = pd.to_datetime(d.index)
    return d.iloc[:, 0].astype(float).sort_index()


CLOSES = {"SPY": _spy(), "BOND": _cser("data/research/bond_synth_dgs10_t255.csv"),
          "GOLD": _cser("data/research/gold_gcf_t255.csv")}
_d = pd.read_parquet(os.path.join(ROOT, "data/macro/DGS3MO.parquet"))["value"].astype(float)
_d.index = pd.to_datetime(_d.index)
CASH = (_d.dropna() / 100.0 / TD).reindex(pd.date_range(_d.index[0], _d.index[-1], freq="D")).ffill()


def sleeve():
    parts = []
    for k, c in CLOSES.items():
        c = c.astype(float)
        aret = c.pct_change()
        pos = pd.concat([TrendOverlay(s, enabled=True).exposure(c) for s in SPEEDS], axis=1).mean(axis=1).shift(1)
        ch = CASH.reindex(aret.index).ffill().fillna(0.0)
        r = pos * (aret - ER[k] / TD) + (1 - pos) * ch - pos.diff().abs().fillna(0) * (1/3) * TXN
        parts.append((r * (1/3)).rename(k))
    return pd.concat(parts, axis=1).dropna(how="any").sum(axis=1).dropna()


def put_leg():
    p = put_returns()
    # apply the monthly XSP roll drag (index assumes perfect rolling): 7.5bps on roll days
    roll = pd.Series(0.0, index=p.index)
    m = pd.Series(p.index.to_period("M"), index=p.index)
    roll[m != m.shift(1)] = PUT_ROLL_MO
    return (p - roll).dropna()


def robo(weights, sweep=0.0):
    etfs = [k for k in weights if k != "_cash"]
    cw = weights.get("_cash", 0.0)
    rets = pd.DataFrame({k: CLOSES[k].pct_change() - ER[k] / TD for k in etfs}).dropna()
    cr = (CASH - sweep / TD).clip(lower=0).reindex(rets.index).ffill().fillna(0.0)
    hold = {k: weights[k] for k in etfs}
    cash = cw
    out = {}
    pm = None
    for dt, row in rets.iterrows():
        mo = (dt.year, dt.month)
        if pm is not None and mo != pm:
            tot = sum(hold.values()) + cash
            cost = sum(abs(hold[k] - tot * weights[k]) for k in etfs) * TXN
            hold = {k: tot * weights[k] for k in etfs}
            cash = tot * cw - cost
        prev = sum(hold.values()) + cash
        for k in etfs:
            hold[k] *= (1 + row[k])
        cash *= (1 + cr.loc[dt])
        out[dt] = (sum(hold.values()) + cash) / prev - 1
        pm = mo
    return pd.Series(out).sort_index()


def combine(sl, pt, w_prem):
    """monthly-rebalanced (1-w) sleeve + w premium."""
    j = pd.concat({"s": sl, "p": pt}, axis=1).dropna()
    out = {}
    hs, hp = (1 - w_prem), w_prem
    pm = None
    for dt, row in j.iterrows():
        mo = (dt.year, dt.month)
        if pm is not None and mo != pm:
            tot = hs + hp
            hs, hp = tot * (1 - w_prem), tot * w_prem
        prev = hs + hp
        hs *= (1 + row["s"])
        hp *= (1 + row["p"])
        out[dt] = (hs + hp) / prev - 1
        pm = mo
    return pd.Series(out).sort_index()


def maxdd(r):
    eq = (1 + r).cumprod()
    return (eq / eq.cummax() - 1).min()


def cagr(r):
    eq = (1 + r).cumprod()
    return (eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (eq.index[-1] - eq.index[0]).days) - 1


def sortino_ci(r):
    s = ME.sortino_ratio(r, 0.0, TD)
    try:
        ci = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=800, seed=0).get("ci_low")
    except Exception:
        ci = float("nan")
    return s, ci


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


def ddwin(r, a, b):
    s = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    if len(s) < 2:
        return float("nan")
    eq = (1 + s).cumprod()
    return (eq / eq.cummax() - 1).min()


def main():
    sl = sleeve()
    pt = put_leg()
    r6040 = robo({"SPY": 0.60, "BOND": 0.40})
    rschwab = robo({"SPY": 0.45, "BOND": 0.30, "GOLD": 0.05, "_cash": 0.20}, sweep=0.0125)
    combo = combine(sl, pt, PREMIUM_W)

    start = max(sl.index[0], pt.index[0], r6040.index[0])
    end = min(sl.index[-1], pt.index[-1], r6040.index[-1])

    def win(s):
        return s[(s.index >= start) & (s.index <= end)].dropna()

    print(f"=== T-279 $65K+ TIER: 70% sleeve + 30% PUT-index, {start.date()}→{end.date()} "
          f"({(end-start).days/365.25:.1f}y, fair conventions) ===")
    print(f"{'strategy':28}{'Sortino':>9}{'ci_low':>8}{'MaxDD':>8}{'CAGR':>7}{'$10k→':>10}")
    series = {"trend sleeve alone": win(sl), "CBOE PUT alone (net roll)": win(pt),
              "60_40 robo": win(r6040), "schwab_like robo": win(rschwab),
              "COMBO 70/30 (the arm)": win(combo)}
    for nm, r in series.items():
        so, ci = sortino_ci(r)
        print(f"{nm:28}{so:>9.3f}{ci:>8.3f}{maxdd(r)*100:>7.1f}%{cagr(r)*100:>6.1f}%{10000*(1+r).prod()/(1+r).iloc[0]:>10,.0f}")

    print("\n=== PRE-REGISTERED GATES — paired Δ(COMBO − X) 95% CI ===")
    for nm, r in [("sleeve alone", win(sl)), ("60_40", win(r6040)), ("schwab_like", win(rschwab))]:
        (dslo, dshi), (dmlo, dmhi), (dwlo, dwhi) = paired(win(combo), r)
        so_sig = "SIG+" if dslo > 0 else ("SIG−" if dshi < 0 else "straddle-0")
        print(f"  vs {nm:13}: ΔSortino[{dslo:+.2f},{dshi:+.2f}] {so_sig} | "
              f"ΔMaxDD[{dmlo*100:+.1f}%,{dmhi*100:+.1f}%] | Δwealth[{dwlo:+.2f},{dwhi:+.2f}]")

    print("\n=== NAMED GAP WINDOWS (put-write's worst = the sleeve's weakest; must beat the robo) ===")
    print(f"{'window':20}{'sleeve':>9}{'COMBO':>9}{'60_40':>9}{'schwab':>9}{'PUT-alone':>11}")
    for nm, a, b in [("1987 crash", "1987-10-01", "1987-12-31"),
                     ("2008 GFC", "2008-09-01", "2009-03-09"),
                     ("COVID-2020", "2020-02-19", "2020-03-23")]:
        print(f"{nm:20}{ddwin(win(sl),a,b)*100:>8.1f}%{ddwin(win(combo),a,b)*100:>8.1f}%"
              f"{ddwin(win(r6040),a,b)*100:>8.1f}%{ddwin(win(rschwab),a,b)*100:>8.1f}%{ddwin(pt,a,b)*100:>10.1f}%")

    print("\n=== CONTRACT GRANULARITY (honest discretization; 1 XSP CSP ≈ SPX/10 × 100 collateral) ===")
    spx_now = 6000
    coll = spx_now / 10 * 100
    print(f"  today SPX~{spx_now}: 1 XSP CSP ≈ ${coll:,.0f} collateral. Clean 70/30 (30%≥1 contract) "
          f"needs ~${coll/0.30:,.0f}. $65-70K holds ~1 contract = PREMIUM-DOMINANT, not 70/30.")
    print(f"  granularity is TIME-VARYING: at SPX~1500 (2000) 1 XSP≈$15k → $65k held ~4 contracts (finer).")


if __name__ == "__main__":
    main()
