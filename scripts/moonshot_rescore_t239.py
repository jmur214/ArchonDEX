"""T-239 moonshot/return-side re-score: Wide-9 + 3-asset + robos on Sortino/up-capture/skew."""
import csv, math, sys
from datetime import datetime
import pandas as pd, numpy as np
ROOT='/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0,ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import sleeve_returns
TD=252; RF=0.04
def find(t):
    import glob
    for g in glob.glob(f'{ROOT}/data/raw/stooq/daily/us/**/{t}.us.txt', recursive=True): return g
    return None
def load(t):
    rows=[]
    for ln in open(find(t)):
        if ln.startswith('<'): continue
        p=ln.split(','); rows.append((datetime.strptime(p[2],'%Y%m%d'), float(p[7])))
    return pd.Series({d:c for d,c in rows}).sort_index()
W9=['SPY','EFA','EEM','AGG','TLT','TIP','GLD','DBC','VNQ']
closes={t:load(t) for t in set(W9+['SPY','AGG','GLD'])}
def dr(s): return s.pct_change()
def robo(weights):
    etfs=[k for k in weights if k!='_cash']; cw=weights.get('_cash',0.0)
    rets=pd.concat({k:dr(closes[k]) for k in etfs},axis=1).dropna()
    hold={k:weights[k] for k in etfs}; cash=cw; out={}; pm=None
    for dt,row in rets.iterrows():
        m=(dt.year,dt.month)
        if pm is not None and m!=pm:
            tot=sum(hold.values())+cash
            for k in etfs: hold[k]=tot*weights[k]
            cash=tot*cw
        prev=sum(hold.values())+cash
        for k in etfs: hold[k]*=(1+row[k])
        cash*=(1+RF/TD); out[dt]=(sum(hold.values())+cash)/prev-1; pm=m
    return pd.Series(out)
sleeve3=sleeve_returns({k:closes[k] for k in ['SPY','AGG','GLD']},105)
wide9=sleeve_returns({k:closes[k] for k in W9},105)
r6040=robo({'SPY':0.60,'AGG':0.40}); rschwab=robo({'SPY':0.45,'AGG':0.30,'GLD':0.05,'_cash':0.20})
spy_bh=dr(closes['SPY']).dropna()
alls={'60_40':r6040,'schwab_like':rschwab,'SPY buy-hold':spy_bh,'TREND 3-asset':sleeve3,'WIDE-9':wide9}
start=max(s.index[0] for s in alls.values()); end=min(s.index[-1] for s in alls.values())
def win(s): return s[(s.index>=start)&(s.index<=end)].dropna()
def maxdd(eq): return (eq/eq.cummax()-1).min()
def cagr(eq): 
    y=(eq.index[-1]-eq.index[0]).days/365.25; return (eq.iloc[-1]/eq.iloc[0])**(1/y)-1
def sortino_ci(r):
    s=ME.sortino_ratio(r,0.0,TD)
    try: ci=ME.bootstrap_distribution(r,lambda x:ME.sortino_ratio(x,0.0,TD),n_iterations=1000,seed=0).get('ci_low')
    except: ci=None
    return s,ci
def updown(strat,ref):
    sm=(1+strat).resample('ME').prod()-1; rm=(1+ref).resample('ME').prod()-1
    j=pd.concat({'s':sm,'r':rm},axis=1).dropna(); up=j[j.r>0]; dn=j[j.r<0]
    return up.s.mean()/up.r.mean(), dn.s.mean()/dn.r.mean()
def mskew(r): return ((1+r).resample('ME').prod()-1).skew()
print(f'=== RETURN-SIDE RE-SCORE: {start.date()}..{end.date()} (2006+ ETF substrate, DIRECTIONAL) ===')
print(f'{"strategy":15}{"Sortino":>9}{"ci_low":>8}{"Sharpe":>8}{"mSkew":>7}{"MaxDD":>8}{"Calmar":>8}{"CAGR":>7}  up/dn-cap vs 60_40')
for nm,r in alls.items():
    rw=win(r); eq=(1+rw).cumprod(); so,ci=sortino_ci(rw); md=maxdd(eq); cg=cagr(eq)
    sh=ME.sharpe_ratio(rw,0.0,TD); sk=mskew(rw); uc,dc=updown(rw,win(r6040))
    print(f'{nm:15}{so:>9.3f}{(ci or float("nan")):>8.3f}{sh:>8.3f}{sk:>7.2f}{md*100:>7.1f}%{cg/abs(md):>8.3f}{cg*100:>6.1f}%  {uc:.2f}/{dc:.2f}')
print('\n=== terminal $5K (Roth, over window) ===')
for nm,r in alls.items():
    eq=(1+win(r)).cumprod(); print(f'  {nm:15} ${5000*eq.iloc[-1]:,.0f}')
