"""T-254 factor momentum (Ehsani-Linnainmaa): do factors' own returns predict their next? Pre-registered."""
import sys, re
import pandas as pd, numpy as np
ROOT='/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0,ROOT)
from core.metrics_engine import MetricsEngine as ME
TD=252

def parse_ff(path, cols):
    """Ken French daily CSV: skip metadata, read the YYYYMMDD data block."""
    rows=[]
    for ln in open(path):
        m=re.match(r'^\s*(\d{8})\s*,(.*)', ln)
        if not m: continue
        vals=[float(x) for x in m.group(2).split(',') if x.strip()!='']
        if len(vals)>=len(cols): rows.append([pd.Timestamp(m.group(1))]+vals[:len(cols)])
    df=pd.DataFrame(rows, columns=['d']+cols).set_index('d').sort_index()
    return df/100.0  # FF are in percent

ff5=parse_ff(f'{ROOT}/data/research/ff5_daily.csv', ['Mkt-RF','SMB','HML','RMW','CMA','RF'])
mom=parse_ff(f'{ROOT}/data/research/mom_daily.csv', ['Mom'])
F=ff5.join(mom, how='inner')
print(f'[factors] {F.index[0].date()}..{F.index[-1].date()} ({len(F)} days); cols {list(F.columns)}')
RF=F['RF']
# the tradeable factor return streams (long-short factors); Mkt-RF is the market premium
FACS=['Mkt-RF','SMB','HML','RMW','CMA','Mom']
Fr=F[FACS]

# monthly factor returns
Fm=(1+Fr).resample('ME').prod()-1
RFm=(1+RF).resample('ME').prod()-1

# ---- FACTOR MOMENTUM (E-L time-series): each factor timed by its own trailing 12-1 return ----
# signal at month t = cumulative factor return over [t-12, t-2] (skip most recent month)
sig=(1+Fm).rolling(11).apply(lambda x: x.prod(), raw=True).shift(1)-1  # 11-month, lagged 1 (=12-1)
# position next month = sign of trailing momentum (long winners, SHORT losers = the E-L TS factor-mom)
pos=np.sign(sig)
fm_ret=(pos.shift(0)*Fm).mean(axis=1)   # EW across the 6 factor-momentum streams
fm_ret=fm_ret.dropna()
# long-only variant (only tilt INTO positive-momentum factors, EW; cash otherwise)
pos_lo=(sig>0).astype(float)
fm_lo=(pos_lo*Fm).sum(axis=1)/pos_lo.sum(axis=1).replace(0,np.nan)
fm_lo=fm_lo.dropna()

def stats(r, lbl, mfreq=True):
    r=r.dropna(); ann=12 if mfreq else TD
    eq=(1+r).cumprod(); so=ME.sortino_ratio(r,0.0,ann)
    try: ci=ME.bootstrap_distribution(r,lambda x:ME.sortino_ratio(x,0.0,ann),n_iterations=1000,seed=0).get('ci_low')
    except: ci=float('nan')
    yrs=len(r)/ann; cg=(eq.iloc[-1]/eq.iloc[0])**(1/yrs)-1
    print(f'  {lbl:34} Sortino={so:.3f} ci_low={ci:.3f} Sharpe={ME.sharpe_ratio(r,0.0,ann):.3f} CAGR={cg*100:.1f}% MaxDD={(eq/eq.cummax()-1).min()*100:.1f}%')
    return r

print(f'\n=== FACTOR MOMENTUM (monthly, {fm_ret.index[0].date()}..{fm_ret.index[-1].date()}) ===')
fmr=stats(fm_ret, 'Factor-mom (long-short, EW 6 factors)')
stats(fm_lo, 'Factor-mom (LONG-ONLY tilt)')
print('  --- individual factors for reference ---')
for f in FACS: stats(Fm[f].loc[fm_ret.index], f'  {f}')

# ---- BETA-OR-EDGE KILL TEST: regress factor-mom on FF5+Mom (does alpha survive net of the factors?) ----
import numpy as np
print('\n=== is_it_beta_or_edge (regress factor-mom on FF5+Mom, Newey-West HAC) ===')
def hac_alpha(y, X, L=6):
    Xc=np.column_stack([np.ones(len(X)), X.values]); yv=y.values
    b=np.linalg.lstsq(Xc, yv, rcond=None)[0]; resid=yv-Xc@b
    n,k=Xc.shape; XtX_inv=np.linalg.inv(Xc.T@Xc)
    S=(resid[:,None]*Xc).T@(resid[:,None]*Xc)  # lag-0
    for l in range(1,L+1):
        w=1-l/(L+1); G=(resid[l:,None]*Xc[l:]).T@(resid[:-l,None]*Xc[:-l]); S+=w*(G+G.T)
    cov=XtX_inv@S@XtX_inv; se=np.sqrt(np.diag(cov))
    return b[0], b[0]/se[0]  # alpha (monthly), t-stat
al={}
for name,ser in [('FM long-short',fm_ret),('FM long-only',fm_lo)]:
    j=pd.concat([ser.rename('y'), Fm], axis=1).dropna()
    a,t=hac_alpha(j['y'], j[FACS])
    print(f'  {name}: monthly alpha={a*100:.3f}% (ann {a*12*100:.1f}%), t_HAC={t:.2f} {"-> EDGE (t>2)" if abs(t)>2 else "-> BETA (not sig)"}')
    # also net of JUST Mom (is it subsumed by the momentum factor?)
    a2,t2=hac_alpha(j['y'], j[['Mom']])
    print(f'    net of Mom-only: alpha={a2*100:.3f}%/mo t_HAC={t2:.2f}; corr(FM,Mom)={j["y"].corr(j["Mom"]):.2f}')
