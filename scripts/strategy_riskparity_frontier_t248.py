"""T-248 strategy-level risk-parity frontier — naive vs HRP over {base, trend} vs robos.

No new backtest: base sleeve = a cached base-equity portfolio_snapshots.csv; trend
sleeve = analytic core.trend_overlay.sleeve_returns; robos from cached stooq ETF
data. Composes the two sleeves naive (equal-weight) vs HRP (StrategyRiskParityComposer)
and reports Sortino+ci_low / MaxDD / CAGR / up-down-capture for each vs both robos.

Usage: python -m scripts.strategy_riskparity_frontier_t248 <base_run_id>
"""
import csv
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME          # noqa: E402
from core.trend_overlay import sleeve_returns                # noqa: E402
from engines.engine_c_portfolio.strategy_composer import (   # noqa: E402
    StrategyCompositionConfig, StrategyRiskParityComposer)

TD = 252
RAW = {'SPY': 'data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt',
       'AGG': 'data/raw/stooq/daily/us/nyse etfs/1/agg.us.txt',
       'GLD': 'data/raw/stooq/daily/us/nyse etfs/1/gld.us.txt'}
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
    df = pd.DataFrame({t: load_close(t) for t in RAW}).sort_index().pct_change()
    for t in df:
        df[t] = df[t] - ER[t] / TD
    return df.dropna(how='all')


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
        out[dt] = (sum(hold.values()) + cash) / prev - 1
        pm = m
    return pd.Series(out).sort_index()


def base_returns(rid):
    f = os.path.join(ROOT, 'data', 'trade_logs', rid, 'portfolio_snapshots.csv')
    rows = list(csv.DictReader(open(f)))
    s = pd.Series({datetime.strptime(r['timestamp'][:10], '%Y-%m-%d'): float(r['equity'])
                   for r in rows}).sort_index()
    return s.pct_change().dropna()


def maxdd(eq):
    return (eq / eq.cummax() - 1.0).min()


def cagr(eq):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else 0


def sortino_ci(r):
    s = ME.sortino_ratio(r, 0.0, TD)
    try:
        ci = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD),
                                       n_iterations=1000, seed=0).get('ci_low')
    except Exception:
        ci = float('nan')
    return s, ci


def updown(strat, ref):
    j = pd.concat({'s': strat, 'r': ref}, axis=1).dropna()
    up, dn = j[j.r > 0], j[j.r < 0]
    uc = up.s.mean() / up.r.mean() if len(up) and up.r.mean() else float('nan')
    dc = dn.s.mean() / dn.r.mean() if len(dn) and dn.r.mean() else float('nan')
    return uc, dc


def main():
    base_rid = sys.argv[1]
    base = base_returns(base_rid)
    closes = {'SPY': load_close('SPY'), 'AGG': load_close('AGG'), 'GLD': load_close('GLD')}
    trend = sleeve_returns(closes, 105)
    rets = etf_rets()
    r6040 = robo_returns({'SPY': 0.60, 'AGG': 0.40}, rets)
    rschwab = robo_returns({'SPY': 0.45, 'AGG': 0.30, 'GLD': 0.05, '_cash': 0.20}, rets)

    sleeves = pd.concat({'base': base, 'trend': trend}, axis=1).dropna()
    start, end = sleeves.index[0], sleeves.index[-1]

    def win(s):
        return s[(s.index >= start) & (s.index <= end)].dropna()

    naive = StrategyRiskParityComposer(StrategyCompositionConfig(risk_parity_enabled=False))
    hrp = StrategyRiskParityComposer(StrategyCompositionConfig(risk_parity_enabled=True))
    w_naive = naive.risk_budget_weights(sleeves)
    w_hrp = hrp.risk_budget_weights(sleeves)
    comp_naive = naive.compose_returns(sleeves, w_naive)
    comp_hrp = hrp.compose_returns(sleeves, w_hrp)

    print(f"\nWINDOW {start.date()} → {end.date()}  ({(end-start).days/365.25:.2f}y)")
    print(f"sleeve weights — naive: {dict(w_naive.round(3))} | HRP: {dict(w_hrp.round(3))}\n")

    series = {
        '60_40 robo': win(r6040), 'schwab_like robo': win(rschwab),
        'base sleeve': win(base), 'trend sleeve': win(trend),
        'NAIVE comp (base+trend)': comp_naive, 'HRP comp (base+trend)': comp_hrp,
    }
    ref = win(r6040)
    print(f"{'series':<26}{'Sortino':>9}{'ci_low':>9}{'MaxDD':>9}{'CAGR':>9}{'upCap':>8}{'dnCap':>8}")
    print("-" * 78)
    for nm, r in series.items():
        eq = (1 + r).cumprod()
        so, ci = sortino_ci(r)
        uc, dc = updown(r, ref)
        print(f"{nm:<26}{so:>9.3f}{ci:>9.3f}{maxdd(eq):>9.1%}{cagr(eq):>9.1%}{uc:>8.2f}{dc:>8.2f}")

    # frontier verdict: HRP higher Sortino at equal-or-lower MaxDD than naive?
    en, eh = (1 + comp_naive).cumprod(), (1 + comp_hrp).cumprod()
    sn, _ = sortino_ci(comp_naive)
    sh, _ = sortino_ci(comp_hrp)
    print(f"\nFRONTIER: HRP vs NAIVE — Sortino {sh:.3f} vs {sn:.3f} "
          f"[{'HIGHER' if sh > sn else 'not higher'}], "
          f"MaxDD {maxdd(eh):.1%} vs {maxdd(en):.1%} "
          f"[{'<=' if maxdd(eh) >= maxdd(en) else '>'} naive]")


if __name__ == '__main__':
    main()
