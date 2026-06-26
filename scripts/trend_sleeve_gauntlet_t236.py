"""T-236 trend-sleeve gauntlet — full-cycle (incl dotcom) on index substrate."""
import csv, math, os, sys
from datetime import datetime
import pandas as pd, numpy as np
ROOT='/Users/jacksonmurphy/Dev/trading_machine-agent-d'
sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import sleeve_returns
TD=252; RF=0.04

def spy_close():
    r=list(csv.DictReader(open(f'{ROOT}/data/processed/SPY_1d.csv')))
    s=pd.Series({datetime.strptime(x['Date'][:10],'%Y-%m-%d'):float(x['Close']) for x in r}).sort_index()
    return s
def csv_series(f,col=1):
    d=pd.read_csv(f, index_col=0); d.index=pd.to_datetime(d.index)
    return d.iloc[:,0].astype(float).sort_index()

SPY=spy_close()
BOND=csv_series('/tmp/t236/bond_synth.csv')   # synthetic treasury TR index
GOLD=csv_series('/tmp/t236/gold_gcf.csv')      # GC=F
closes={'SPY':SPY,'BOND':BOND,'GOLD':GOLD}

def daily_ret(s): return s.pct_change()
def robo(weights):
    etfs=[k for k in weights if k!='_cash']; cw=weights.get('_cash',0.0)
    rets=pd.concat({k:daily_ret(closes[k]) for k in etfs},axis=1).dropna()
    hold={k:weights[k] for k in etfs}; cash=cw; out={}; pm=None
    for dt,row in rets.iterrows():
        m=(dt.year,dt.month)
        if pm is not None and m!=pm:
            tot=sum(hold.values())+cash
            for k in etfs: hold[k]=tot*weights[k]
            cash=tot*cw
        prev=sum(hold.values())+cash
        for k in etfs: hold[k]*=(1+row[k])
        cash*=(1+RF/TD)
        out[dt]=(sum(hold.values())+cash)/prev-1; pm=m
    return pd.Series(out)

sleeve=sleeve_returns(closes,105)
r6040=robo({'SPY':0.60,'BOND':0.40})
rschwab=robo({'SPY':0.45,'BOND':0.30,'GOLD':0.05,'_cash':0.20})
spy_bh=daily_ret(SPY).dropna()

# common full-cycle window (gold starts 2000-08)
start=max(sleeve.index[0], r6040.index[0], rschwab.index[0]); end=min(sleeve.index[-1], r6040.index[-1])
def win(s): return s[(s.index>=start)&(s.index<=end)].dropna()

def maxdd(eq): p=eq.cummax(); return (eq/p-1).min()
def cagr(eq):
    yrs=(eq.index[-1]-eq.index[0]).days/365.25; return (eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1
def sortino_ci(r):
    s=ME.sortino_ratio(r,0.0,TD)
    try: ci=ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x,0.0,TD), n_iterations=1000, seed=0).get('ci_low')
    except: ci=None
    return s,ci
def sharpe(r): return ME.sharpe_ratio(r,0.0,TD)
def updown(strat,ref):
    sm=(1+strat).resample('ME').prod()-1; rm=(1+ref).resample('ME').prod()-1
    j=pd.concat({'s':sm,'r':rm},axis=1).dropna(); up=j[j.r>0]; dn=j[j.r<0]
    return (up.s.mean()/up.r.mean()), (dn.s.mean()/dn.r.mean())

print(f'=== FULL-CYCLE INDEX SUBSTRATE: {start.date()} .. {end.date()} (incl dotcom) ===')
rows={'60_40':r6040,'schwab_like':rschwab,'SPY buy-hold':spy_bh,'TREND SLEEVE':sleeve}
print(f'{"strategy":16}{"Sortino":>9}{"ci_low":>8}{"Sharpe":>8}{"MaxDD":>8}{"Calmar":>8}{"CAGR":>7}  up/dn-cap vs 60_40')
res={}
for nm,r in rows.items():
    rw=win(r); eq=(1+rw).cumprod(); so,ci=sortino_ci(rw); md=maxdd(eq); cg=cagr(eq); sh=sharpe(rw)
    uc,dc=updown(rw,win(r6040))
    res[nm]=dict(so=so,ci=ci,sh=sh,md=md,cg=cg,eq=eq)
    print(f'{nm:16}{so:>9.3f}{(ci or float("nan")):>8.3f}{sh:>8.3f}{md*100:>7.1f}%{cg/abs(md):>8.3f}{cg*100:>6.1f}%  {uc:.2f}/{dc:.2f}')

print('\n=== PER-CRISIS in-window MaxDD (INCL DOTCOM) ===')
crises=[('dotcom','2000-08-30','2002-10-09'),('GFC','2007-10-09','2009-03-09'),
        ('COVID','2020-02-19','2020-03-23'),('2022','2022-01-03','2022-10-12')]
print(f'{"crisis":10}{"60_40":>9}{"schwab":>9}{"SPY-BH":>9}{"SLEEVE":>9}')
def ddw(r,a,b):
    s=r[(r.index>=pd.Timestamp(a))&(r.index<=pd.Timestamp(b))]
    if len(s)<2: return None
    eq=(1+s).cumprod(); return (eq/eq.cummax()-1).min()
for nm,a,b in crises:
    vals=[ddw(rows[k],a,b) for k in ['60_40','schwab_like','SPY buy-hold','TREND SLEEVE']]
    print(f'{nm:10}'+''.join(f'{(v*100 if v is not None else float("nan")):>8.1f}%' for v in vals))

# MBL honest-N gate
N=16; mbl_bar=math.sqrt(2*math.log(N)/25)
print(f'\n=== MBL honest-N gate (N={N}, 25yr): Sharpe bar = {mbl_bar:.3f} ===')
print(f'  sleeve Sharpe={res["TREND SLEEVE"]["sh"]:.3f} -> {"CLEARS" if res["TREND SLEEVE"]["sh"]>mbl_bar else "FAILS"} MBL')
# strict ci_low gate
sl=res['TREND SLEEVE']
print('\n=== STRICT ci_low(Sortino) deploy gate ===')
for rb in ['60_40','schwab_like']:
    print(f'  sleeve ci_low {sl["ci"]:.3f} vs {rb} ci_low {res[rb]["ci"]:.3f} -> {"PASS" if sl["ci"]>res[rb]["ci"] else "FAIL"}; vs {rb} POINT {res[rb]["so"]:.3f} -> {"decisive" if sl["ci"]>res[rb]["so"] else "NOT decisive (ci_low<robo point)"}')

# money-EV (Roth = gross terminal; taxable = annual ST tax on positive gains ~ turnover-heavy)
print('\n=== MONEY-EV terminal wealth (Roth=gross) over full cycle ===')
for amt in (5000,15000):
    print(f'  ${amt}: ' + ' | '.join(f'{nm.split()[0]} ${amt*res[nm]["eq"].iloc[-1]/res[nm]["eq"].iloc[0]:,.0f}' for nm in ['60_40','schwab_like','TREND SLEEVE']))
