"""T-249 small-cap 12-1 momentum gauntlet — gross vs HONEST small-cap cost. Survivor-biased universe (upper bound)."""
import glob, math, sys
from datetime import datetime
import pandas as pd, numpy as np
ROOT='/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0,ROOT)
from core.metrics_engine import MetricsEngine as ME
TD=252

def load_monthly(f):
    """Return (month-end close Series, month-end trailing dollar-ADV Series) or None."""
    try:
        rows=[]
        for ln in open(f):
            if ln.startswith('<'): continue
            p=ln.split(',')
            rows.append((p[2], float(p[7]), float(p[8])))  # date, close, volume
    except Exception: return None
    if len(rows)<260: return None  # need ~1yr+
    df=pd.DataFrame(rows, columns=['d','c','v']); df['d']=pd.to_datetime(df['d'], format='%Y%m%d')
    df=df.set_index('d').sort_index()
    df['dv']=df['c']*df['v']  # daily dollar volume
    me_c=df['c'].resample('ME').last()
    me_adv=df['dv'].rolling(63).mean().resample('ME').last()  # ~3mo ADV
    return me_c, me_adv

print('[load] scanning stooq US stocks...', flush=True)
files=[f for f in glob.glob(f'{ROOT}/data/raw/stooq/daily/us/**/*.txt', recursive=True) if 'stocks' in f]
closes={}; advs={}
for i,f in enumerate(files):
    r=load_monthly(f)
    if r is None: continue
    t=f.split('/')[-1].replace('.us.txt','').upper()
    closes[t]=r[0]; advs[t]=r[1]
    if i%2000==0: print(f'  {i}/{len(files)} ({len(closes)} loaded)', flush=True)
C=pd.DataFrame(closes).sort_index(); A=pd.DataFrame(advs).reindex(C.index)
print(f'[load] {C.shape[1]} names, {C.index.min().date()}..{C.index.max().date()}', flush=True)

# monthly returns
R=C.pct_change()
# 12-1 momentum: cum return months t-12..t-2 (skip most recent month)
MOM=(C.shift(1)/C.shift(12)-1)
# small-cap ADV tiers (median dollar-ADV over the window per name, in $)
med_adv=A.median()
SMALL=(med_adv>=1e6)&(med_adv<2e8)   # $1M-$200M/day = small-cap investable, not mega
MICRO=(med_adv>=1e6)&(med_adv<2e7)   # $1M-$20M = micro (75bps); small = 20M-200M (35bps)
univ=[t for t in C.columns if SMALL.get(t,False)]
print(f'[universe] small-cap (ADV $1M-$200M): {len(univ)} names (of which micro<$20M: {int((MICRO&SMALL).sum())})', flush=True)

# backtest: each month, among small-cap names with valid MOM + price, long top decile EW, hold next month
def run(start='2006-01-01'):
    dates=[d for d in C.index if d>=pd.Timestamp(start)]
    port_ret={}; turn={}; cost_s={}; cost_m={}
    prev_w={}
    for i,d in enumerate(dates[:-1]):
        m=MOM.loc[d, univ].dropna()
        # require tradeable: price + adv this month
        valid=[t for t in m.index if not np.isnan(C.loc[d,t]) and A.loc[d,t]>=1e6]
        if len(valid)<20: continue
        m=m[valid].sort_values(ascending=False)
        k=max(10, len(m)//10)  # top decile
        longs=list(m.index[:k]); w={t:1.0/k for t in longs}
        nd=dates[i+1]
        rets=R.loc[nd, longs].fillna(0.0)
        port_ret[nd]=float((pd.Series(w)*rets).sum())
        # turnover + cost (Σ|Δw| × half-spread per side; entering+leaving)
        names=set(longs)|set(prev_w); dw=sum(abs(w.get(t,0)-prev_w.get(t,0)) for t in names)
        turn[nd]=dw
        # per-name spread tier
        hs=sum(abs(w.get(t,0)-prev_w.get(t,0))*(0.0075 if MICRO.get(t,False) else 0.0035) for t in names)
        cost_s[nd]=sum(abs(w.get(t,0)-prev_w.get(t,0))*0.0035 for t in names)  # all-small 35bps
        cost_m[nd]=hs  # tier-accurate (micro 75 / small 35)
        prev_w=w
    pr=pd.Series(port_ret); cs=pd.Series(cost_s); cm=pd.Series(cost_m); tu=pd.Series(turn)
    return pr, cs, cm, tu

gross, cost_small, cost_tier, turn = run()
net_small = gross - cost_small
net_tier  = gross - cost_tier
def stats(r, lbl):
    r=r.dropna(); eq=(1+r).cumprod()
    so=ME.sortino_ratio(r,0.0,TD)
    try: ci=ME.bootstrap_distribution(r,lambda x:ME.sortino_ratio(x,0.0,TD),n_iterations=1000,seed=0).get('ci_low')
    except: ci=float('nan')
    yrs=(eq.index[-1]-eq.index[0]).days/365.25; cagr=(eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1
    mdd=(eq/eq.cummax()-1).min()
    print(f'  {lbl:22} Sortino={so:.3f} ci_low={ci:.3f} CAGR={cagr*100:.1f}% MaxDD={mdd*100:.1f}% Sharpe={ME.sharpe_ratio(r,0.0,TD):.3f}')
print(f'\n=== SMALL-CAP 12-1 MOMENTUM (survivor-biased universe = UPPER BOUND) {gross.index[0].date()}..{gross.index[-1].date()} ===')
print(f'  avg monthly turnover (Σ|Δw|): {turn.mean():.2f} -> ~{turn.mean()*12*100:.0f}%/yr; annualized cost: small {cost_small.mean()*12*100:.1f}%/yr, tier {cost_tier.mean()*12*100:.1f}%/yr')
stats(gross, 'GROSS (no cost)')
stats(net_small, 'NET @ 35bps (small)')
stats(net_tier, 'NET @ tier (35/75bps)')
print('\n(robo bars, T-236 index substrate: 60_40 Sortino 0.807 / schwab_like 1.008)')
