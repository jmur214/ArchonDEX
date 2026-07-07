"""T-250 calendar/flow probe: FOMC even-week + turn-of-month on SPY. Pre-registered, no sweep."""
import csv, sys
from datetime import datetime, timedelta
import pandas as pd, numpy as np
ROOT='/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0,ROOT)
from core.metrics_engine import MetricsEngine as ME
TD=252; RF=0.04; COST=0.00015  # 1.5bps/side liquid ETF

# SPY daily returns
r=list(csv.DictReader(open(f'{ROOT}/data/processed/SPY_1d.csv')))
spy=pd.Series({datetime.strptime(x['Date'][:10],'%Y-%m-%d'):float(x['Close']) for x in r}).sort_index()
ret=spy.pct_change().dropna()
ret=ret[ret.index>=pd.Timestamp('1994-01-01')]
idx=ret.index

# --- FOMC decision dates: from the shared calendar (T-290 d3; config/fomc_calendar.json) ---
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))  # this repo, for the loader
from engines.data_manager.macro_calendar import load_fomc_dates
fomc=load_fomc_dates()
def even_week(dt):
    # weeks since most recent FOMC meeting; even (0,2,4,6) = the premium weeks
    prev=[f for f in fomc if f<=dt]
    if not prev: return None
    w=(dt-prev[-1]).days//7
    return w%2==0
ew=pd.Series({d: even_week(d) for d in idx}).dropna()

# --- Turn-of-month: last trading day of month + first 3 of next ---
ymd=pd.DataFrame({'d':idx}, index=idx); ymd['ym']=idx.to_period('M')
tom=pd.Series(False, index=idx)
for ym,grp in ymd.groupby('ym'):
    ds=list(grp.index)
    for x in ds[:3]+[ds[-1]]: tom[x]=True
isin_tom=tom.astype(bool)
ew=ew.astype(bool)

def measure(mask, label):
    m=mask.reindex(ret.index).fillna(False).astype(bool).values
    a=ret[m]; b=ret[~m]
    print(f'  {label}: in-window mean {a.mean()*1e4:.2f}bps/day (n={len(a)}) vs out {b.mean()*1e4:.2f}bps/day (n={len(b)}); diff {(a.mean()-b.mean())*1e4:.2f}bps')

def tilt(mask, label):
    m=mask.reindex(ret.index).fillna(False).astype(bool)
    pos=m.astype(float)
    chg=pos.diff().abs().fillna(0)
    excess=ret-RF/TD
    strat   = (RF/TD) + pos*excess        - chg*COST
    strat_hc= (RF/TD) + pos*excess*0.5     - chg*COST
    def st(x,l):
        x=x.dropna(); eq=(1+x).cumprod(); so=ME.sortino_ratio(x,0.0,TD)
        try: ci=ME.bootstrap_distribution(x,lambda z:ME.sortino_ratio(z,0.0,TD),n_iterations=1000,seed=0).get('ci_low')
        except: ci=float('nan')
        yrs=(eq.index[-1]-eq.index[0]).days/365.25; cg=(eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1
        print(f'    {l:30} Sortino={so:.3f} ci_low={ci:.3f} Sharpe={ME.sharpe_ratio(x,0.0,TD):.3f} CAGR={cg*100:.1f}% MaxDD={(eq/eq.cummax()-1).min()*100:.1f}% timeInMkt={pos.mean()*100:.0f}%')
    st(strat,    f'{label} tilt (net cost)')
    st(strat_hc, f'{label} tilt (net+50% haircut)')

print(f'=== CALENDAR/FLOW PROBE on SPY {ret.index[0].date()}..{ret.index[-1].date()} ===')
print('RAW EFFECT (is it present in our data?):')
measure(ew, 'FOMC even-week')
measure(isin_tom, 'Turn-of-month (4-day)')
print()
print('DEPLOYABLE TILT (long in-window / cash out; robo bars 60_40 Sortino 0.807 / schwab 1.008):')
tilt(ew, 'FOMC even-week')
tilt(isin_tom, 'TOM')
bh=ret.dropna(); eqh=(1+bh).cumprod()
print(f'  SPY buy-hold ref: Sortino={ME.sortino_ratio(bh,0.0,TD):.3f} Sharpe={ME.sharpe_ratio(bh,0.0,TD):.3f} CAGR={((eqh.iloc[-1]/eqh.iloc[0])**(252/len(bh))-1)*100:.1f}% MaxDD={(eqh/eqh.cummax()-1).min()*100:.1f}%')
