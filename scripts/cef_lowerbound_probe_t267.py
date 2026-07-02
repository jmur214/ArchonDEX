"""T-267 — CEF discount-capture SURVIVOR-ONLY LOWER-BOUND probe (pre-registered, N_trials+=1).

Runs the frozen T-264 pre-registration on the free NAV panel (yfinance X<TKR>X, 1999+):
long-only, monthly, z-score of each fund's discount vs its OWN trailing 12mo mean,
long the cheapest quintile (widest relative discount), EW. TR returns (Adj Close);
discount from RAW price/NAV, month-end (mitigates NAV staleness).

Gauntlet vs both robos on the T-255 FAIR conventions (DGS3MO cash path, ER+txn both
sides, below-market-sweep schwab variant). is_it_beta_or_edge: residual reversion
t_HAC net of equity (SPY) + credit (HYG/LQD) + CEF-universe-average beta. corr-to-sleeve.
Full window + the post-2011 15yr decay half reported separately.

*** SURVIVOR-ONLY = a CONSERVATIVE LOWER BOUND (T-264): the delisting events ARE the
reversion wins, so this UNDERSTATES the edge. PASS = real & bias-defeating;
FAIL = INCONCLUSIVE, NOT a refutation. ***
"""
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
CEF_TXN = 0.0010          # 10 bps/side round-trip 20bps — CEF spreads wider than ETFs (honest)
ER = {"SPY": 0.0009, "AGG": 0.0003, "GLD": 0.0040}
ETF_TXN = 0.00015
CACHE = os.path.join(ROOT, "data/research/cef_panel_t267.parquet")
UNIV = ("RVT GAM GAB USA NUV NAD NEA PTY PCN BLW EVT PHK UTF EOS BME BDJ "
        "ETY NIE PML PFN VKQ VMO DNP PDI BST").split()


def tr_close(t):
    df = pd.read_csv(os.path.join(ROOT, f"data/processed/tr_reconciled/{t}_1d.csv"),
                     parse_dates=["Date"]).set_index("Date")
    return df["Close"].astype(float).sort_index()


def dgs3_cash():
    d = pd.read_parquet(os.path.join(ROOT, "data/macro/DGS3MO.parquet"))["value"].astype(float)
    d.index = pd.to_datetime(d.index)
    daily = (d.dropna() / 100.0 / TD)
    return daily.reindex(pd.date_range(daily.index[0], daily.index[-1], freq="D")).ffill()


def build_panel():
    """price(raw), tr(adj close), nav per CEF → cached. discount = raw price / nav - 1."""
    if os.path.exists(CACHE):
        return pd.read_parquet(CACHE)
    import yfinance as yf
    frames = {}
    for t in UNIV:
        px = yf.download(t, period="max", auto_adjust=False, progress=False, threads=False)
        nav = yf.download(f"X{t}X", period="max", auto_adjust=False, progress=False, threads=False)
        if not len(px) or not len(nav):
            print(f"  drop {t}"); continue
        if isinstance(px.columns, pd.MultiIndex):
            px.columns = px.columns.get_level_values(0)
        if isinstance(nav.columns, pd.MultiIndex):
            nav.columns = nav.columns.get_level_values(0)
        frames[(t, "raw")] = px["Close"]
        frames[(t, "tr")] = px["Adj Close"]
        frames[(t, "nav")] = nav["Close"]
    panel = pd.DataFrame(frames)
    panel.index = pd.to_datetime(panel.index)
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    panel.to_parquet(CACHE)
    return panel


def maxdd(r):
    eq = (1 + r).cumprod()
    return (eq / eq.cummax() - 1).min()


def cagr(r):
    eq = (1 + r).cumprod()
    return (eq.iloc[-1] / eq.iloc[0]) ** (365.25 / (eq.index[-1] - eq.index[0]).days) - 1


def sortino_ci(r):
    s = ME.sortino_ratio(r, 0.0, 12)
    try:
        ci = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, 12),
                                       n_iterations=1000, seed=0).get("ci_low")
    except Exception:
        ci = float("nan")
    return s, ci


def paired_dci(a, b, n=1000, bl=6):
    j = pd.concat({"a": a, "b": b}, axis=1).dropna()
    av, bv = j["a"].values, j["b"].values
    m = len(av)
    rng = np.random.default_rng(0)
    pt = ME.sortino_ratio(pd.Series(av), 0.0, 12) - ME.sortino_ratio(pd.Series(bv), 0.0, 12)
    ds = []
    for _ in range(n):
        idx = np.concatenate([np.arange(s, s + bl) % m for s in rng.integers(0, m, int(np.ceil(m / bl)))])[:m]
        ds.append(ME.sortino_ratio(pd.Series(av[idx]), 0.0, 12) - ME.sortino_ratio(pd.Series(bv[idx]), 0.0, 12))
    return pt, float(np.percentile(ds, 2.5))


def newey_west_t(y, X, lags=6):
    X = np.column_stack([np.ones(len(y)), X])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    n, k = X.shape
    S = (X * resid[:, None]).T @ (X * resid[:, None])
    for L in range(1, lags + 1):
        w = 1 - L / (lags + 1)
        G = (X[L:] * resid[L:, None]).T @ (X[:-L] * resid[:-L, None])
        S += w * (G + G.T)
    XtX_inv = np.linalg.inv(X.T @ X)
    cov = XtX_inv @ S @ XtX_inv
    return beta, beta / np.sqrt(np.diag(cov))


def monthly(r):
    return (1 + r).resample("ME").prod() - 1


def main():
    panel = build_panel()
    cash_daily = dgs3_cash()
    present = sorted({c[0] for c in panel.columns})
    print(f"panel: {len(present)} CEFs, {panel.index[0].date()}→{panel.index[-1].date()}")

    # month-end raw price, tr, nav
    me_raw = pd.DataFrame({t: panel[(t, "raw")] for t in present}).resample("ME").last()
    me_nav = pd.DataFrame({t: panel[(t, "nav")] for t in present}).resample("ME").last()
    tr_m = pd.DataFrame({t: monthly(panel[(t, "tr")].pct_change().dropna()) for t in present})
    disc = me_raw / me_nav - 1.0

    # own trailing-12mo z-score of discount
    z = (disc - disc.rolling(12, min_periods=12).mean()) / disc.rolling(12, min_periods=12).std()

    # each month: long cheapest quintile (lowest z), EW; next-month TR; turnover cost
    dates = z.index
    strat, held_prev = {}, set()
    univ_ret = {}
    for i in range(len(dates) - 1):
        dt, nxt = dates[i], dates[i + 1]
        zi = z.loc[dt].dropna()
        if len(zi) < 10:
            continue
        k = max(2, int(round(len(zi) * 0.20)))
        held = set(zi.nsmallest(k).index)         # widest relative discount
        fwd = tr_m.loc[nxt, list(held)].dropna()
        if not len(fwd):
            continue
        turn = len(held.symmetric_difference(held_prev)) / max(len(held), 1)
        strat[nxt] = fwd.mean() - turn * CEF_TXN
        univ_ret[nxt] = tr_m.loc[nxt, list(zi.index)].dropna().mean()  # CEF-universe avg (beta control)
        held_prev = held
    strat = pd.Series(strat).sort_index()
    univ = pd.Series(univ_ret).sort_index()

    # --- fair robos (T-255 conventions) on tr_reconciled SPY/AGG/GLD, DGS3MO cash ---
    etf = {t: tr_close(t) for t in ["SPY", "AGG", "GLD"]}

    def robo(weights, sweep=0.0):
        etfs = [k for k in weights if k != "_cash"]
        cw = weights.get("_cash", 0.0)
        rets = pd.DataFrame({k: etf[k].pct_change() - ER[k] / TD for k in etfs}).dropna()
        cr = (cash_daily - sweep / TD).clip(lower=0).reindex(rets.index).ffill().fillna(0.0)
        hold = {k: weights[k] for k in etfs}
        cash = cw
        out = {}
        pm = None
        for dt, row in rets.iterrows():
            m = (dt.year, dt.month)
            if pm is not None and m != pm:
                tot = sum(hold.values()) + cash
                cost = sum(abs(hold[k] - tot * weights[k]) for k in etfs) * ETF_TXN
                hold = {k: tot * weights[k] for k in etfs}
                cash = tot * cw - cost
            prev = sum(hold.values()) + cash
            for k in etfs:
                hold[k] *= (1 + row[k])
            cash *= (1 + cr.loc[dt])
            out[dt] = (sum(hold.values()) + cash) / prev - 1
            pm = m
        return monthly(pd.Series(out).sort_index())

    r6040 = robo({"SPY": 0.60, "AGG": 0.40})
    rschwab = robo({"SPY": 0.45, "AGG": 0.30, "GLD": 0.05, "_cash": 0.20}, sweep=0.0125)

    # --- trend sleeve (fair, flat-leg earns cash) for corr ---
    def sleeve():
        parts = []
        for k in ["SPY", "AGG", "GLD"]:
            c = etf[k]
            ar = c.pct_change()
            pos = TrendOverlay(105, enabled=True).exposure(c).shift(1)
            ch = cash_daily.reindex(ar.index).ffill().fillna(0.0)
            r = pos * (ar - ER[k] / TD) + (1 - pos) * ch
            parts.append((r * (1 / 3)).rename(k))
        return monthly(pd.concat(parts, axis=1).dropna(how="all").sum(axis=1, min_count=1).dropna())
    slv = sleeve()

    def report(tag, s):
        s = s.dropna()
        if len(s) < 24:
            print(f"\n[{tag}] too few months ({len(s)})"); return
        so, ci = sortino_ci(s)
        print(f"\n=== {tag}: {s.index[0].date()}→{s.index[-1].date()} ({len(s)}mo) ===")
        print(f"  CEF-quintile : Sortino {so:.2f} (ci {ci:.2f})  Sharpe {ME.sharpe_ratio(s,0,12):.2f}  "
              f"MaxDD {maxdd(s):.1%}  CAGR {cagr(s):.1%}")
        for nm, rb in [("60_40", r6040), ("schwab_like", rschwab)]:
            rr = rb.reindex(s.index).dropna()
            ss = s.reindex(rr.index)
            so2, _ = sortino_ci(rr)
            dpt, dci = paired_dci(ss, rr)
            print(f"  vs {nm:11}: robo Sortino {so2:.2f} MaxDD {maxdd(rr):.1%} CAGR {cagr(rr):.1%} | "
                  f"ΔSortino {dpt:+.2f} [ci_low {dci:+.2f}] {'PASS' if dci>0 else 'not-sig'}")
        # is_it_beta_or_edge
        spy = monthly(etf["SPY"].pct_change().dropna())
        hyg, lqd = tr_close("HYG"), tr_close("LQD")
        credit = monthly((hyg.pct_change() - lqd.pct_change()).dropna())
        reg = pd.concat({"y": s, "spy": spy, "cr": credit, "u": univ}, axis=1).dropna()
        if len(reg) > 30:
            beta, tstat = newey_west_t(reg["y"].values,
                                       reg[["spy", "cr", "u"]].values, lags=6)
            print(f"  is_it_beta_or_edge: alpha {beta[0]*100:+.2f}%/mo t_HAC {tstat[0]:+.2f} "
                  f"(β_spy {beta[1]:.2f} β_credit {beta[2]:.2f} β_cefuniv {beta[3]:.2f}) "
                  f"→ {'EDGE (t≥2)' if abs(tstat[0])>=2 else 'NOT edge (t<2) — reversion NOT proven on top of beta'}")
        c = pd.concat({"s": s, "v": slv}, axis=1).dropna()
        print(f"  corr-to-sleeve: {c['s'].corr(c['v']):+.2f}")

    report("FULL", strat)
    report("POST-2011 (15yr decay read)", strat[strat.index >= "2011-01-01"])
    print("\n*** SURVIVOR-ONLY LOWER BOUND — PASS = real & bias-defeating; "
          "FAIL = INCONCLUSIVE, not a refutation. ***")


if __name__ == "__main__":
    main()
