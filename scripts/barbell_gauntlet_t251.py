"""T-251 barbell gauntlet — inverse-vol SAFE CORE + convex trend SATELLITE vs both robos.

Liquid-ETF substrate (stooq SPY/AGG/GLD, ~2005-2026), fully analytic. Costs: ER on
every holding + 1.5bps one-way on trend-satellite turnover; robo cash earns RF.
Reports Sortino+ci_low AND Sharpe+ci_low (Sortino = scorecard, not target), MaxDD,
CAGR, Calmar, up/down-capture. ONE pre-registered config (satellite_weight=0.15).

Usage: python -m scripts.barbell_gauntlet_t251
"""
import os
import sys
from datetime import datetime

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME                 # noqa: E402
from core.trend_overlay import sleeve_returns, TrendOverlay         # noqa: E402
from engines.engine_c_portfolio.strategy_composer import (          # noqa: E402
    BarbellConfig, BarbellComposer)

TD = 252
RF = 0.04
TC = 0.00015   # 1.5 bps one-way trading cost
ER = {'SPY': 0.000945, 'AGG': 0.0003, 'GLD': 0.0040}   # annual expense ratios
RAW = {'SPY': 'data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt',
       'AGG': 'data/raw/stooq/daily/us/nyse etfs/1/agg.us.txt',
       'GLD': 'data/raw/stooq/daily/us/nyse etfs/1/gld.us.txt'}


def load_close(t):
    rows = []
    for ln in open(os.path.join(ROOT, RAW[t])):
        if ln.startswith('<'):
            continue
        p = ln.split(',')
        rows.append((datetime.strptime(p[2], '%Y%m%d'), float(p[7])))
    return pd.Series({d: c for d, c in rows}).sort_index()


def net_asset_rets(closes):
    """Per-asset daily returns net of expense ratio."""
    df = pd.DataFrame({t: closes[t].pct_change() for t in closes}).sort_index()
    for t in df:
        df[t] = df[t] - ER[t] / TD
    return df


def robo(weights, closes):
    etfs = [k for k in weights if k != '_cash']
    cw = weights.get('_cash', 0.0)
    rets = net_asset_rets({k: closes[k] for k in etfs}).dropna()
    hold = {k: weights[k] for k in etfs}
    cash = cw
    out = {}
    pm = None
    for dt, row in rets.iterrows():
        m = (dt.year, dt.month)
        if pm is not None and m != pm:                 # monthly rebalance
            tot = sum(hold.values()) + cash
            turn = sum(abs(hold[k] - tot * weights[k]) for k in etfs) + abs(cash - tot * cw)
            for k in etfs:
                hold[k] = tot * weights[k]
            cash = tot * cw - turn * TC                 # rebalance cost
        prev = sum(hold.values()) + cash
        for k in etfs:
            hold[k] *= (1 + row[k])
        cash *= (1 + RF / TD)                            # cash earns RF (fair to robo)
        out[dt] = (sum(hold.values()) + cash) / prev - 1
        pm = m
    return pd.Series(out).sort_index()


def satellite_with_cost(closes, lookback=105):
    """Trend overlay sleeve net of turnover trading cost (the active leg)."""
    sat = sleeve_returns(closes, lookback)
    # turnover from the long/flat signal per asset (equal-weight sleeve → 1/N each)
    n = len(closes)
    cost = pd.Series(0.0, index=sat.index)
    for k in closes:
        pos = TrendOverlay(lookback, enabled=True).exposure(closes[k]).shift(1)
        turn = pos.diff().abs().reindex(sat.index).fillna(0.0)
        cost = cost.add((turn / n) * TC, fill_value=0.0)
    return (sat - cost).dropna()


def maxdd(eq):
    return (eq / eq.cummax() - 1.0).min()


def cagr(eq):
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1 if yrs > 0 else 0


def metric_ci(r, fn):
    pt = fn(r)
    try:
        ci = ME.bootstrap_distribution(r, fn, n_iterations=1000, seed=0).get('ci_low')
    except Exception:
        ci = float('nan')
    return pt, ci


def updown(strat, ref):
    sm = (1 + strat).resample('ME').prod() - 1
    rm = (1 + ref).resample('ME').prod() - 1
    j = pd.concat({'s': sm, 'r': rm}, axis=1, sort=True).dropna()
    up, dn = j[j.r > 0], j[j.r < 0]
    return (up.s.mean() / up.r.mean()), (dn.s.mean() / dn.r.mean())


def main():
    closes = {t: load_close(t) for t in RAW}
    core_rets = net_asset_rets(closes)

    bar = BarbellComposer(BarbellConfig(satellite_weight=0.15))
    sat = satellite_with_cost(closes)
    barbell = bar.compose_returns(core_rets, sat)
    core_only = bar.core_returns(core_rets)

    r6040 = robo({'SPY': 0.60, 'AGG': 0.40}, closes)
    rschwab = robo({'SPY': 0.45, 'AGG': 0.30, 'GLD': 0.05, '_cash': 0.20}, closes)

    series = {'60_40 robo': r6040, 'schwab_like robo': rschwab,
              'inverse-vol CORE only': core_only, 'trend SATELLITE only': sat,
              'BARBELL (85c+15s)': barbell}
    start = max(s.index[0] for s in series.values())
    end = min(s.index[-1] for s in series.values())

    def win(s):
        return s[(s.index >= start) & (s.index <= end)].dropna()

    ref = win(r6040)
    print(f"\n=== BARBELL GAUNTLET  {start.date()} → {end.date()} "
          f"({(end-start).days/365.25:.1f}y, liquid-ETF, net ER+TC, robo cash@RF={RF}) ===")
    print(f"{'strategy':<24}{'Sortino':>8}{'so_ci':>8}{'Sharpe':>8}{'sh_ci':>8}"
          f"{'MaxDD':>8}{'CAGR':>8}{'Calmar':>8}{'up':>6}{'dn':>6}")
    print("-" * 94)
    out = {}
    for nm, r in series.items():
        rw = win(r)
        eq = (1 + rw).cumprod()
        so, soc = metric_ci(rw, lambda x: ME.sortino_ratio(x, 0.0, TD))
        sh, shc = metric_ci(rw, lambda x: ME.sharpe_ratio(x, 0.0, TD))
        md, cg = maxdd(eq), cagr(eq)
        uc, dc = updown(rw, ref)
        out[nm] = dict(so=so, soc=soc, sh=sh, shc=shc, md=md, cg=cg)
        print(f"{nm:<24}{so:>8.3f}{soc:>8.3f}{sh:>8.3f}{shc:>8.3f}"
              f"{md:>8.1%}{cg:>8.1%}{cg/abs(md):>8.2f}{uc:>6.2f}{dc:>6.2f}")

    b, r1, r2 = out['BARBELL (85c+15s)'], out['60_40 robo'], out['schwab_like robo']
    print("\n=== PRE-REGISTERED VERDICT ===")
    for nm, rb in [('60_40', r1), ('schwab_like', r2)]:
        wealth = b['cg'] > rb['cg']
        dd = b['md'] >= rb['md']   # less negative = lower DD
        dom = (b['so'] > rb['so']) and (b['sh'] > rb['sh']) and (b['md'] >= rb['md'])
        print(f"vs {nm:12}: wealth {'WIN' if wealth else 'lose'} (CAGR {b['cg']:.1%} vs {rb['cg']:.1%}) | "
              f"DD {'WIN' if dd else 'lose'} ({b['md']:.1%} vs {rb['md']:.1%}) | "
              f"shape-dominate {'YES' if dom else 'no'} "
              f"(So {b['so']:.2f}/{rb['so']:.2f}, Sh {b['sh']:.2f}/{rb['sh']:.2f})")
    g1 = (b['cg'] > r1['cg'] and b['md'] >= r1['md']) or \
         (b['so'] > r1['so'] and b['sh'] > r1['sh'] and b['md'] >= r1['md'])
    g2 = (b['cg'] > r2['cg'] and b['md'] >= r2['md']) or \
         (b['so'] > r2['so'] and b['sh'] > r2['sh'] and b['md'] >= r2['md'])
    print(f"\nPASS (beats BOTH robos on wealth+DD OR shape-dominates both): {'YES' if (g1 and g2) else 'NO'}")

    # --- IS THE SHAPE-DOMINATION SIGNIFICANT? paired block-bootstrap on the DIFFERENCE ---
    # per-series CIs overlap; the honest test is the CI on the DIFFERENCE (barbell - robo),
    # resampling the SAME blocks of row positions across both series (paired).
    import numpy as _np
    print("\n=== paired difference-CI (barbell - robo), block-bootstrap 1000x seed 0, block=20 ===")
    bw = win(barbell)
    BL = 20

    def paired_ci(b, r, fn):
        j = pd.concat({'b': b, 'r': r}, axis=1, sort=True).dropna()
        bv, rv = j['b'].values, j['r'].values
        n = len(bv)
        nblk = int(_np.ceil(n / BL))
        rng = _np.random.default_rng(0)
        point = fn(pd.Series(bv)) - fn(pd.Series(rv))
        diffs = []
        for _ in range(1000):
            starts = rng.integers(0, n, nblk)
            idx = _np.concatenate([_np.arange(s, s + BL) % n for s in starts])[:n]
            diffs.append(fn(pd.Series(bv[idx])) - fn(pd.Series(rv[idx])))
        return point, float(_np.percentile(diffs, 2.5))

    for nm, rr in [('60_40', win(r6040)), ('schwab_like', win(rschwab))]:
        psh, csh = paired_ci(bw, rr, lambda x: ME.sharpe_ratio(x, 0.0, TD))
        pso, cso = paired_ci(bw, rr, lambda x: ME.sortino_ratio(x, 0.0, TD))
        print(f"vs {nm:12}: ΔSharpe {psh:+.3f} [ci_low {csh:+.3f}]  "
              f"ΔSortino {pso:+.3f} [ci_low {cso:+.3f}]  "
              f"→ {'SIGNIFICANT (ci_low>0)' if csh > 0 else 'NOT sig (Sharpe ci straddles 0)'}")


if __name__ == '__main__':
    main()
