"""T-298 — asymmetric damping: damp re-entry (B=2/3), NEVER damp de-risking. Frozen; no sweep.
Exit-lag == 0 by the invariant e_held <= e_target; verified empirically."""
import csv, sys
from datetime import datetime
import pandas as pd, numpy as np
ROOT = '/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
TD = 252; TXN = 0.00015
SPY_ER = 0.000945; SSO_ER = 0.0089; SSO_SPREAD = 0.0060; SPY_SLIP = 0.51/1e4
B = 2.0/3.0; TOL = 1e-9

def spy_close():
    r = list(csv.DictReader(open(f'{ROOT}/data/processed/SPY_1d.csv')))
    return pd.Series({datetime.strptime(x['Date'][:10], '%Y-%m-%d'): float(x['Close']) for x in r}).sort_index()
def macro(s):
    d = pd.read_parquet(f'{ROOT}/data/macro/{s}.parquet')['value'].astype(float); d.index = pd.to_datetime(d.index); return d.dropna().sort_index()
spy = spy_close(); spy_tr = spy.pct_change(); IDX = spy_tr.index
dgs3 = macro('DGS3MO'); rf = (dgs3/100.0/TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq='D')).ffill().reindex(IDX).ffill().fillna(0.0)
spy_gross = spy_tr + SPY_ER/TD
sso_syn = 2*spy_gross - (rf + SSO_SPREAD/TD) - SSO_ER/TD
ens = pd.concat([TrendOverlay(s, enabled=True).exposure(spy.astype(float)) for s in [42,105,210]], axis=1).mean(axis=1)
e_target = (2.0*ens.shift(1)).clip(upper=2.0)
START = pd.Timestamp('2000-08-30')

def asym(tgt, band=B):
    """FROZEN: de-risking always executes; re-entry only when target - held > band."""
    out = []; held = np.nan
    for v in tgt.values:
        if np.isnan(v): out.append(np.nan); continue
        if np.isnan(held): held = v
        elif v < held - TOL: held = v                    # de-risk: undamped, immediate
        elif v - held > band + TOL: held = v             # re-entry: only on >= 2 increments
        out.append(held)
    return pd.Series(out, index=tgt.index)

e_asym = asym(e_target)
def arm(e, slip_bps):
    e = e.reindex(IDX)
    lo = e*(spy_tr - SPY_ER/TD) + (1-e)*rf
    hi = (2-e)*(spy_tr - SPY_ER/TD) + (e-1)*sso_syn
    r = lo.where(e <= 1, hi)
    ta = e.diff().abs().fillna(0); ssow = (e-1).clip(lower=0); ts = ssow.diff().abs().fillna(0)
    tsp = (ta-ts).clip(lower=0)
    return (r - ta*TXN - ts*(slip_bps/1e4) - tsp*SPY_SLIP)[IDX >= START].dropna()

common = arm(e_target,0).index.intersection(arm(e_asym,0).index)
bh = spy_tr.reindex(common).dropna()
def stats(r):
    eq=(1+r).cumprod(); yrs=(eq.index[-1]-eq.index[0]).days/365.25
    md=(eq/eq.cummax()-1).min()
    return dict(wealth=10000*eq.iloc[-1], cagr=eq.iloc[-1]**(1/yrs)-1, sortino=ME.sortino_ratio(r,0.0,TD), maxdd=md)
def paired(a,b,L=21,n=1000):
    j=pd.concat({'a':a,'b':b},axis=1).dropna(); A=j['a'].values; Bv=j['b'].values; N=len(A)
    rng=np.random.default_rng(0); dw=[]; nb=int(np.ceil(N/L))
    for _ in range(n):
        st=rng.integers(0,N-L+1,size=nb); ix=np.concatenate([np.arange(t,t+L) for t in st])[:N]
        dw.append(np.prod(1+A[ix])-np.prod(1+Bv[ix]))
    return np.percentile(dw,2.5), np.percentile(dw,97.5)

BAR = stats(bh)['wealth']; yrs=(common[-1]-common[0]).days/365.25
print(f"=== T-298 asymmetric damping ({common[0].date()}..{common[-1].date()}) ===")
print(f"BAR: Roth buy-hold SPY ${BAR:,.0f} ({stats(bh)['cagr']*100:.2f}%)")
# INVARIANT CHECK
et, ea = e_target.reindex(common), e_asym.reindex(common)
viol = int((ea > et + TOL).sum())
print(f"[invariant] e_held <= e_target violated on {viol} days -> {'OK' if viol==0 else 'FALSIFIED'}")
print(f"\n{'arm':28}{'units/yr':>10}{'SSO-leg':>9}{'meanExp':>9}{'  @0bps':>10}{'@1.55':>10}{'@5bps':>10}{'@10bps':>10}{'MaxDD':>8}")
for nm, e in [('V1 undamped', e_target), ('T-298 asym damp B=2/3', e_asym)]:
    ec=e.reindex(common); ta=ec.diff().abs().fillna(0); ts=(ec-1).clip(lower=0).diff().abs().fillna(0)
    w={b: stats(arm(e,b).reindex(common).dropna()) for b in (0,1.55,5,10)}
    print(f"{nm:28}{ta.sum()/yrs:>10.2f}{ts.sum()/yrs:>9.2f}{ec.mean():>9.3f}"
          f"{w[0]['wealth']:>10,.0f}{w[1.55]['wealth']:>10,.0f}{w[5]['wealth']:>10,.0f}{w[10]['wealth']:>10,.0f}{w[0]['maxdd']*100:>7.1f}%")
    if 'asym' in nm:
        sso_ty = ts.sum()/yrs
        print(f"  -> SSO-leg {sso_ty:.2f} units/yr vs the pre-derived target <=4.56 : {'MEETS' if sso_ty<=4.56 else 'MISSES'}")
        a5 = arm(e,5).reindex(common).dropna(); v5 = arm(e_target,5).reindex(common).dropna()
        ga = stats(a5)['wealth'] > BAR
        print(f"  -> GATE(a) beat SPY @5bps: ${stats(a5)['wealth']:,.0f} vs ${BAR:,.0f} -> {'PASS' if ga else 'FAIL'}")
        lo,hi = paired(a5,bh); lo2,hi2 = paired(a5,v5)
        print(f"  -> paired dWealth @5bps: vs SPY [{lo:+.2f},{hi:+.2f}] {'SIG+' if lo>0 else 'straddles 0'} | vs V1 [{lo2:+.2f},{hi2:+.2f}] {'SIG+' if lo2>0 else 'straddles 0'}")
# exit-lag
def first_below(e,thr,a,b):
    s=e[(e.index>=pd.Timestamp(a))&(e.index<=pd.Timestamp(b))]; h=s[s<=thr+TOL]
    return h.index[0] if len(h) else None
print("\n[GATE(b)] empirical crash exit-lag (trading days vs undamped; expect 0 by invariant)")
worst=-99
for lbl,a,b in [('2008 GFC','2007-10-01','2009-06-30'),('2020 COVID','2020-01-01','2020-06-30'),('2022 bear','2022-01-01','2022-12-31')]:
    parts=[]
    for thr,tn in [(1.0,'de-lever'),(0.0,'full-exit')]:
        d0=first_below(et,thr,a,b); d1=first_below(ea,thr,a,b)
        if d0 is None or d1 is None: parts.append(f'{tn} n/a'); continue
        lag=int(common.searchsorted(d1)-common.searchsorted(d0)); worst=max(worst,lag); parts.append(f'{tn} {lag}d')
    print(f"  {lbl:12} " + ", ".join(parts))
print(f"  worst lag {worst}d -> GATE(b) {'PASS' if worst<=5 else 'FAIL'}  ({'exit-lag == 0 confirmed' if worst<=0 else 'positive lag!'})")
