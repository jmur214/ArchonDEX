"""T-241 C1 concentration gauntlet — base vs C1 vs robos on a cached-equity window.

No new backtest: reads the BASE and C1 portfolio_snapshots.csv (already produced by
two run_isolated runs) + builds the two robos from cached stooq ETF data + the
analytic trend sleeve (core.trend_overlay). Reports Sortino+ci_low, MaxDD, CAGR,
up/down-capture, monthly skew for base / C1 / C1+trend-sleeve vs both robos.

Usage: python -m scripts.c1_concentration_gauntlet_t241 <base_run_id> <c1_run_id>
"""
import csv
import sys
import os
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME  # noqa: E402
from core.trend_overlay import sleeve_returns          # noqa: E402

TD = 252
RAW = {
    'SPY': 'data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt',
    'AGG': 'data/raw/stooq/daily/us/nyse etfs/1/agg.us.txt',
    'GLD': 'data/raw/stooq/daily/us/nyse etfs/1/gld.us.txt',
}
ER = {'SPY': 0.0009, 'AGG': 0.0003, 'GLD': 0.0040}


def load_close(t):
    rows = []
    for ln in open(os.path.join(ROOT, RAW[t])):
        if ln.startswith('<'):
            continue
        p = ln.split(',')
        rows.append((datetime.strptime(p[2], '%Y%m%d'), float(p[7])))
    return pd.Series({d: c for d, c in rows}).sort_index()


def etf_rets():
    px = {t: load_close(t) for t in RAW}
    df = pd.DataFrame(px).sort_index()
    r = df.pct_change()
    for t in r:
        r[t] = r[t] - ER[t] / TD
    return r.dropna(how='all')


def robo_returns(weights, rets):
    etfs = [t for t in weights if t != '_cash']
    sub = rets[etfs].dropna()
    cash_w = weights.get('_cash', 0.0)
    hold = {t: weights[t] for t in etfs}
    cash = cash_w
    out = {}
    pm = None
    for dt, row in sub.iterrows():
        m = (dt.year, dt.month)
        if pm is not None and m != pm:
            tot = sum(hold.values()) + cash
            for t in etfs:
                hold[t] = tot * weights[t]
            cash = tot * cash_w
        prev = sum(hold.values()) + cash
        for t in etfs:
            hold[t] *= (1 + row[t])
        cur = sum(hold.values()) + cash
        out[dt] = cur / prev - 1
        pm = m
    return pd.Series(out).sort_index()


def equity_returns(rid):
    f = os.path.join(ROOT, 'data', 'trade_logs', rid, 'portfolio_snapshots.csv')
    rows = list(csv.DictReader(open(f)))
    s = pd.Series({datetime.strptime(r['timestamp'][:10], '%Y-%m-%d'): float(r['equity'])
                   for r in rows}).sort_index()
    return s.pct_change().dropna(), s


def maxdd(eq):
    return (eq / eq.cummax() - 1.0).min()


def cagr(eq):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else 0


def sortino_ci(r):
    s = ME.sortino_ratio(r, 0.0, TD)
    try:
        bd = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD),
                                       n_iterations=1000, seed=0)
        ci = bd.get('ci_low')
    except Exception:
        ci = float('nan')
    return s, ci


def updown(strat, ref):
    j = pd.concat({'s': strat, 'r': ref}, axis=1).dropna()
    up = j[j.r > 0]
    dn = j[j.r < 0]
    uc = (up.s.mean() / up.r.mean()) if len(up) and up.r.mean() else float('nan')
    dc = (dn.s.mean() / dn.r.mean()) if len(dn) and dn.r.mean() else float('nan')
    return uc, dc


def mskew(r):
    return ((1 + r).resample('ME').prod() - 1).skew()


def main():
    base_rid, c1_rid = sys.argv[1], sys.argv[2]
    base_r, base_eq = equity_returns(base_rid)
    c1_r, c1_eq = equity_returns(c1_rid)
    rets = etf_rets()
    r6040 = robo_returns({'SPY': 0.60, 'AGG': 0.40}, rets)
    rschwab = robo_returns({'SPY': 0.45, 'AGG': 0.30, 'GLD': 0.05, '_cash': 0.20}, rets)

    # window = intersection of all series
    start = max(base_r.index[0], c1_r.index[0], r6040.index[0])
    end = min(base_r.index[-1], c1_r.index[-1], r6040.index[-1])

    def win(s):
        return s[(s.index >= start) & (s.index <= end)].dropna()

    # trend sleeve (analytic) for the pairing test
    closes = {'SPY': load_close('SPY'), 'AGG': load_close('AGG'), 'GLD': load_close('GLD')}
    try:
        sleeve = sleeve_returns(closes, 105)
        c1w = win(c1_r)
        sl = win(sleeve).reindex(c1w.index).fillna(0.0)
        pair_r = 0.5 * c1w + 0.5 * sl       # 50/50 C1 + trend sleeve
    except Exception as e:
        pair_r = None
        print(f"[warn] sleeve/pair unavailable: {e}")

    series = {
        '60_40': win(r6040), 'schwab_like': win(rschwab),
        'BASE (diversified-MVO)': win(base_r), 'C1 (top-K concentration)': win(c1_r),
    }
    if pair_r is not None:
        series['C1 + trend sleeve (PAIR)'] = pair_r

    ref = win(r6040)
    print(f"\nWINDOW {start.date()} → {end.date()}  ({(end-start).days/365.25:.2f}y)\n")
    print(f"{'series':<28}{'Sortino':>9}{'ci_low':>9}{'MaxDD':>9}{'CAGR':>9}"
          f"{'upCap':>8}{'dnCap':>8}{'mSkew':>8}")
    print("-" * 96)
    for nm, r in series.items():
        eq = (1 + r).cumprod()
        so, ci = sortino_ci(r)
        uc, dc = updown(r, ref)
        print(f"{nm:<28}{so:>9.3f}{ci:>9.3f}{maxdd(eq):>9.1%}{cagr(eq):>9.1%}"
              f"{uc:>8.2f}{dc:>8.2f}{mskew(r):>8.2f}")

    # the PRIZE: does C1+sleeve beat BOTH robos on BOTH terminal wealth AND MaxDD?
    if pair_r is not None:
        pe = (1 + pair_r).cumprod()
        ptw, pmd = pe.iloc[-1], maxdd(pe)
        print("\nPRIZE — C1+sleeve vs BOTH robos (terminal wealth AND MaxDD):")
        for nm, rr in [('60_40', win(r6040)), ('schwab_like', win(rschwab))]:
            re_ = (1 + rr.reindex(pair_r.index).fillna(0.0)).cumprod()
            tw_win = ptw > re_.iloc[-1]
            dd_win = pmd > maxdd(re_)   # less negative = better
            print(f"  vs {nm:<12}: TW {ptw:.3f} vs {re_.iloc[-1]:.3f} "
                  f"[{'WIN' if tw_win else 'LOSS'}] | "
                  f"MaxDD {pmd:.1%} vs {maxdd(re_):.1%} [{'WIN' if dd_win else 'LOSS'}]")


if __name__ == '__main__':
    main()
