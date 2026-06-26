"""T-234 tail re-score — robos (monthly-rebal) vs T-215 base/composition. No new backtest."""
import csv, math
from datetime import datetime
import pandas as pd, numpy as np
import sys
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.metrics_engine import MetricsEngine as ME

RAW = {
 'SPY':'data/raw/stooq/daily/us/nyse etfs/2/spy.us.txt',
 'AGG':'data/raw/stooq/daily/us/nyse etfs/1/agg.us.txt',
 'GLD':'data/raw/stooq/daily/us/nyse etfs/1/gld.us.txt',
}
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))+'/'
ER={'SPY':0.0009,'AGG':0.0003,'GLD':0.0040}  # annual expense ratios
RF=0.04; TD=252

def load_close(t):
    rows=[]
    for ln in open(ROOT+RAW[t]):
        if ln.startswith('<'): continue
        p=ln.split(',')
        rows.append((datetime.strptime(p[2],'%Y%m%d'), float(p[7])))
    s=pd.Series({d:c for d,c in rows}).sort_index()
    return s

def etf_daily_returns():
    px={t:load_close(t) for t in RAW}
    df=pd.DataFrame(px).sort_index()
    rets=df.pct_change()
    for t in rets: rets[t]=rets[t]-ER[t]/TD   # ER drag
    return rets.dropna(how='all')

def robo_returns(weights, rets):
    """monthly-rebal robo daily returns. weights: {SPY:..,AGG:..,GLD:..,_cash:..}"""
    etfs=[t for t in weights if t!='_cash']
    sub=rets[etfs].dropna()
    cash_w=weights.get('_cash',0.0)
    nav=1.0; hold={t:weights[t] for t in etfs}; cash=cash_w
    out={}
    prev_month=None
    for dt,row in sub.iterrows():
        m=(dt.year,dt.month)
        if prev_month is not None and m!=prev_month:  # rebalance at month change
            tot=sum(hold.values())+cash
            for t in etfs: hold[t]=tot*weights[t]
            cash=tot*cash_w
        prev=sum(hold.values())+cash
        for t in etfs: hold[t]*= (1+row[t])
        cash*= (1+RF/TD)
        cur=sum(hold.values())+cash
        out[dt]=cur/prev-1
        prev_month=m
    return pd.Series(out)

def equity_returns(f):
    rows=list(csv.DictReader(open(f)))
    s=pd.Series({datetime.strptime(r['timestamp'][:10],'%Y-%m-%d'):float(r['equity']) for r in rows}).sort_index()
    return s.pct_change().dropna(), s

def maxdd(equity):
    peak=equity.cummax(); dd=(equity/peak-1.0); return dd.min()

def cagr(equity):
    yrs=(equity.index[-1]-equity.index[0]).days/365.25
    return (equity.iloc[-1]/equity.iloc[0])**(1/yrs)-1 if yrs>0 else 0

def sortino_ci(rets):
    s=ME.sortino_ratio(rets, 0.0, TD)
    try:
        bd=ME.bootstrap_distribution(rets, lambda r: ME.sortino_ratio(r,0.0,TD), n_iterations=1000, seed=0)
        return s, bd.get('ci_low')
    except Exception as e:
        return s, None

def updown_capture(strat, robo):
    """monthly up/down capture vs robo."""
    sm=(1+strat).resample('ME').prod()-1
    rm=(1+robo).resample('ME').prod()-1
    j=pd.concat({'s':sm,'r':rm},axis=1).dropna()
    up=j[j.r>0]; dn=j[j.r<0]
    uc=(up.s.mean()/up.r.mean()) if len(up) and up.r.mean()!=0 else float('nan')
    dc=(dn.s.mean()/dn.r.mean()) if len(dn) and dn.r.mean()!=0 else float('nan')
    return uc, dc

# ---- build ----
rets=etf_daily_returns()
robo6040=robo_returns({'SPY':0.60,'AGG':0.40}, rets)
roboschwab=robo_returns({'SPY':0.45,'AGG':0.30,'GLD':0.05,'_cash':0.20}, rets)
base_r, base_eq = equity_returns('/tmp/t234/arm0_base_snap.csv')
comp_r, comp_eq = equity_returns('/tmp/t234/arm1_composition_snap.csv')

print('=== data windows ===')
for nm,s in [('60_40',robo6040),('schwab_like',roboschwab),('BASE',base_r),('COMP',comp_r)]:
    print(f'  {nm:12} {s.index[0].date()} -> {s.index[-1].date()} ({len(s)} bars)')

# common window for vs-robo (base ∩ robo) — robos start ~2005
start=max(robo6040.index[0], base_r.index[0]); end=min(robo6040.index[-1], base_r.index[-1])
print(f'\n=== TAIL METRICS over common vs-robo window {start.date()}..{end.date()} ===')
def win(s): return s[(s.index>=start)&(s.index<=end)]
strats={'60_40':robo6040,'schwab_like':roboschwab,'BASE(lev)':base_r,'COMP(lev)':comp_r}
print(f'{"strategy":14}{"Sortino":>10}{"ci_low":>9}{"MaxDD":>9}{"Calmar":>8}{"CAGR":>8}  up/down-cap vs 60_40')
for nm,r in strats.items():
    rw=win(r); eq=(1+rw).cumprod()
    so,ci=sortino_ci(rw); md=maxdd(eq); cg=cagr(eq)
    cal=cg/abs(md) if md else 0
    uc,dc=updown_capture(rw, win(robo6040)) if 'robo' not in nm else (float('nan'),float('nan'))
    capstr= f'{uc:.2f}/{dc:.2f}' if not (math.isnan(uc)) else '—'
    print(f'{nm:14}{so:>10.3f}{(ci if ci is not None else float("nan")):>9.3f}{md*100:>8.1f}%{cal:>8.3f}{cg*100:>7.2f}%  {capstr}')

# ---- PER-CRISIS relative drawdown (THE key tail comparison) ----
import pandas as pd
def dd_in_window(eq_rets, a, b):
    s=eq_rets[(eq_rets.index>=pd.Timestamp(a))&(eq_rets.index<=pd.Timestamp(b))]
    if len(s)<2: return None,None
    eq=(1+s).cumprod(); peak=eq.cummax(); dd=(eq/peak-1).min()
    ret=eq.iloc[-1]/eq.iloc[0]-1
    return dd, ret
crises=[('dotcom','2000-03-24','2002-10-09'),('GFC','2007-10-09','2009-03-09'),
        ('COVID','2020-02-19','2020-03-23'),('2022 bear','2022-01-03','2022-10-12')]
print('\n=== PER-CRISIS MAX DRAWDOWN (in-window) — does comp lose LESS than the robo? ===')
print(f'{"crisis":12}{"60_40":>9}{"schwab":>9}{"BASE(lev)":>11}{"COMP(lev)":>11}   comp vs 60_40')
lines={'60_40':robo6040,'schwab_like':roboschwab,'BASE':base_r,'COMP':comp_r}
for nm,a,b in crises:
    row={}
    for k,r in lines.items():
        dd,ret=dd_in_window(r,a,b); row[k]=dd
    def f(x): return f'{x*100:.1f}%' if x is not None else '  n/a'
    vs = (f'comp {f(row["COMP"])} vs robo {f(row["60_40"])}' if row['60_40'] is not None else 'robo: ETFs predate (no data)')
    print(f'{nm:12}{f(row["60_40"]):>9}{f(row["schwab_like"]):>9}{f(row["BASE"]):>11}{f(row["COMP"]):>11}   {vs}')

print('\n=== BASE/COMP FULL-WINDOW 2000-2025 (standalone, incl. dotcom) ===')
for nm,r in [('BASE',base_r),('COMP',comp_r)]:
    eq=(1+r).cumprod(); so,ci=sortino_ci(r)
    print(f'  {nm}: Sortino={so:.3f} (ci_low={ci:.3f}) MaxDD={maxdd(eq)*100:.1f}% CAGR={cagr(eq)*100:.2f}%')

# ---- T-204 overlay SLEEVE (clean defensive sleeve, AS-IS; flag: SPY/AGG/GLD EW, NOT the 26yr PIT base) ----
from core.trend_overlay import sleeve_returns
closes={t:load_close(t) for t in ('SPY','AGG','GLD')}
sleeve=sleeve_returns(closes, 105)
sl=win(sleeve)
eq=(1+sl).cumprod(); so,ci=sortino_ci(sl); md=maxdd(eq); cg=cagr(eq)
uc,dc=updown_capture(sl, win(robo6040))
print('\n=== T-204 OVERLAY SLEEVE (SPY/AGG/GLD EW long-flat, lookback 105) — DIRECTIONAL (sleeve, not the base book) ===')
print(f'  over {sl.index[0].date()}..{sl.index[-1].date()}: Sortino={so:.3f} (ci_low={ci:.3f}) MaxDD={md*100:.1f}% Calmar={cg/abs(md):.3f} CAGR={cg*100:.2f}%  up/down-cap vs 60_40={uc:.2f}/{dc:.2f}')
print('  per-crisis maxDD:')
for nm,a,b in crises:
    dd,ret=dd_in_window(sleeve,a,b)
    r6,_=dd_in_window(robo6040,a,b)
    print(f'    {nm:12} sleeve {dd*100 if dd else float("nan"):.1f}%   vs 60_40 {(f"{r6*100:.1f}%" if r6 else "n/a")}')
