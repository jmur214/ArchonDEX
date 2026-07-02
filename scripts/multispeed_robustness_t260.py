"""T-260 multi-speed ensemble + robustness scans on the FAIR T-255 harness (same corrections)."""
import csv, sys
from datetime import datetime
import pandas as pd, numpy as np
ROOT='/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0,ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
TD=252; ER={'SPY':0.0009,'BOND':0.0003,'GOLD':0.0040}; TXN=0.00015

def spy_close():
    r=list(csv.DictReader(open(f'{ROOT}/data/processed/SPY_1d.csv')))
    return pd.Series({datetime.strptime(x['Date'][:10],'%Y-%m-%d'):float(x['Close']) for x in r}).sort_index()
def cser(f):
    d=pd.read_csv(f,index_col=0); d.index=pd.to_datetime(d.index); return d.iloc[:,0].astype(float).sort_index()
def macro(s):
    d=pd.read_parquet(f'{ROOT}/data/macro/{s}.parquet')['value'].astype(float); d.index=pd.to_datetime(d.index); return d.dropna().sort_index()
closes={'SPY':spy_close(),'BOND':cser(f'{ROOT}/data/research/bond_synth_dgs10_t255.csv'),'GOLD':cser(f'{ROOT}/data/research/gold_gcf_t255.csv')}
dgs3=macro('DGS3MO'); cash_daily=(dgs3/100.0/TD).reindex(pd.date_range(dgs3.index[0],dgs3.index[-1],freq='D')).ffill()
def cash_on(idx): return cash_daily.reindex(idx).ffill().fillna(0.0)

# common window: all three assets present (gold GC=F starts 2000-08) — matches the T-255 substrate,
# avoids a degenerate SPY-only 1/3-weight period pre-2000.
COMMON_START=max(c.dropna().index[0] for c in closes.values())
def sleeve(exposure_fn):
    """exposure_fn(close)->daily target exposure in [0,1]; flat portion earns cash; ER when exposed; txn on Δexposure."""
    parts=[]
    for k,c in closes.items():
        c=c.astype(float); aret=c.pct_change(); pos=exposure_fn(c).shift(1); ch=cash_on(aret.index)
        r=pos*(aret-ER[k]/TD)+(1-pos)*ch - pos.diff().abs().fillna(0)*(1/3)*TXN
        parts.append((r*(1/3)).rename(k))
    s=pd.concat(parts,axis=1)
    return s[s.index>=COMMON_START].dropna(how='any').sum(axis=1).dropna()

def single(lb_days): return sleeve(lambda c: TrendOverlay(lb_days,enabled=True).exposure(c))
def multi(speeds):   # mean of binary signals across speeds -> fractional exposure
    return sleeve(lambda c: pd.concat([TrendOverlay(s,enabled=True).exposure(c) for s in speeds],axis=1).mean(axis=1))
def monthly_offset(lb_days, k):
    """monthly-rebal: hold the signal evaluated on the k-th trading day of each month for that month."""
    def expo(c):
        sig=TrendOverlay(lb_days,enabled=True).exposure(c)
        out=pd.Series(index=sig.index,dtype=float); cur=0.0; ym=None; cnt=0
        for dt,v in sig.items():
            key=(dt.year,dt.month)
            if key!=ym: ym=key; cnt=0
            if cnt==k and not np.isnan(v): cur=v
            cnt+=1; out[dt]=cur
        return out
    return sleeve(expo)

MO={2:42,3:63,4:84,5:105,6:126,7:147,10:210}
def stats(r):
    r=r.dropna(); eq=(1+r).cumprod(); yrs=(eq.index[-1]-eq.index[0]).days/365.25
    so=ME.sortino_ratio(r,0.0,TD)
    try: ci=ME.bootstrap_distribution(r,lambda x:ME.sortino_ratio(x,0.0,TD),n_iterations=800,seed=0).get('ci_low')
    except: ci=float('nan')
    return so,ci,(eq/eq.cummax()-1).min(),(eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1, 10000*eq.iloc[-1]/eq.iloc[0]
def ddwin(r,a,b):
    s=r[(r.index>=pd.Timestamp(a))&(r.index<=pd.Timestamp(b))]
    if len(s)<2: return float('nan')
    eq=(1+s).cumprod(); return (eq/eq.cummax()-1).min()

base=single(105)
print('=== (1) LOOKBACK DISPERSION (fair sleeve) ===')
print(f'{"lookback":10}{"Sortino":>9}{"ci_low":>8}{"MaxDD":>8}{"CAGR":>7}{"$10k→":>9}')
disp={}
for mo,lb in MO.items():
    if mo in (3,4,5,6,7,10):
        so,ci,md,cg,tw=stats(single(lb)); disp[mo]=(so,md,tw)
        print(f'{str(mo)+"mo":10}{so:>9.3f}{ci:>8.3f}{md*100:>7.1f}%{cg*100:>6.1f}%{tw:>9,.0f}')
sos=[v[0] for v in disp.values()]; mds=[v[1] for v in disp.values()]; tws=[v[2] for v in disp.values()]
print(f'  DISPERSION: Sortino [{min(sos):.3f},{max(sos):.3f}] range {max(sos)-min(sos):.3f}; MaxDD [{min(mds)*100:.1f}%,{max(mds)*100:.1f}%]; $10k [{min(tws):,.0f},{max(tws):,.0f}]')

print('\n=== (2) TRANCHING / TIMING-LUCK (5mo, monthly-rebal at day-offset k=0..20) ===')
tl=[]
for k in range(0,21,4):
    so,ci,md,cg,tw=stats(monthly_offset(105,k)); tl.append((so,md,tw))
    print(f'  offset {k:2}: Sortino {so:.3f}  MaxDD {md*100:.1f}%  $10k {tw:,.0f}')
tso=[x[0] for x in tl]; tmd=[x[1] for x in tl]
print(f'  TIMING-LUCK BAND (sampled k): Sortino [{min(tso):.3f},{max(tso):.3f}] range {max(tso)-min(tso):.3f}; MaxDD [{min(tmd)*100:.1f}%,{max(tmd)*100:.1f}%]')

print('\n=== (3) MULTI-SPEED ENSEMBLE {2,5,10}mo vs single-speed 5mo (fair) ===')
ens=multi([42,105,210])
for nm,r in [('single 5mo (fair base)',base),('multi {2,5,10}mo',ens)]:
    so,ci,md,cg,tw=stats(r); print(f'  {nm:24} Sortino={so:.3f} ci_low={ci:.3f} MaxDD={md*100:.1f}% CAGR={cg*100:.1f}% $10k={tw:,.0f}')
# paired-diff bootstrap ens - base
def paired(a,b,L=21,n=800):
    j=pd.concat({'a':a,'b':b},axis=1).dropna(); A=j['a'].values; B=j['b'].values; N=len(A)
    rng=np.random.default_rng(0); dso=[]; dmd=[]; nb=int(np.ceil(N/L))
    for _ in range(n):
        st=rng.integers(0,N-L+1,size=nb); ix=np.concatenate([np.arange(t,t+L) for t in st])[:N]
        aa,bb=A[ix],B[ix]
        def so_(x): d=x[x<0]; return (x.mean()/(np.sqrt((d**2).mean()) if len(d) else 1e-9))*np.sqrt(TD)
        def md_(x): eq=np.cumprod(1+x); return (eq/np.maximum.accumulate(eq)-1).min()
        dso.append(so_(aa)-so_(bb)); dmd.append(md_(aa)-md_(bb))
    return (np.percentile(dso,2.5),np.percentile(dso,97.5)),(np.percentile(dmd,2.5),np.percentile(dmd,97.5))
(dslo,dshi),(dmlo,dmhi)=paired(ens,base)
print(f'  paired Δ(ensemble − single): ΔSortino 95%CI [{dslo:+.3f},{dshi:+.3f}]  ΔMaxDD 95%CI [{dmlo*100:+.1f}%,{dmhi*100:+.1f}%]')
print('  named windows (in-window MaxDD):')
for nm,a,b in [('COVID-2020','2020-02-19','2020-03-23'),('2022','2022-01-03','2022-10-12')]:
    print(f'    {nm:11} single {ddwin(base,a,b)*100:.1f}%   ensemble {ddwin(ens,a,b)*100:.1f}%')
