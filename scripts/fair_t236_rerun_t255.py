"""T-255 FAIR T-236 re-run — corrects the biases the 2026-07-02 gap audit verified (all AGAINST the sleeve):
  (a) sleeve flat leg earns the short rate (DGS3MO), not 0%;  (b) robo cash earns the SAME short-rate path
  (+ a below-market sweep variant, Tbill-125bps, modeling the real Schwab drag);  (c) ER charged BOTH sides;
  (d) 1.5bps txn cost BOTH sides;  (e) paired-difference block-bootstrap CIs;  (f) MBL on ci_low.
Inputs are the COMMITTED data/research/*_t255.csv (scripts/build_fair_inputs_t255.py). 0 new N_trials (a correction)."""
import csv, math, sys
from datetime import datetime
import pandas as pd, numpy as np
ROOT='/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0,ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
TD=252
ER={'SPY':0.0009,'BOND':0.0003,'GOLD':0.0040}  # annual expense ratios (ETF-equivalent)
TXN=0.00015  # 1.5 bps/side

def spy_close():
    r=list(csv.DictReader(open(f'{ROOT}/data/processed/SPY_1d.csv')))
    return pd.Series({datetime.strptime(x['Date'][:10],'%Y-%m-%d'):float(x['Close']) for x in r}).sort_index()
def csv_ser(f):
    d=pd.read_csv(f,index_col=0); d.index=pd.to_datetime(d.index); return d.iloc[:,0].astype(float).sort_index()
def macro(s):
    d=pd.read_parquet(f'{ROOT}/data/macro/{s}.parquet')['value'].astype(float); d.index=pd.to_datetime(d.index)
    return d.dropna().sort_index()

SPY=spy_close(); BOND=csv_ser(f'{ROOT}/data/research/bond_synth_dgs10_t255.csv'); GOLD=csv_ser(f'{ROOT}/data/research/gold_gcf_t255.csv')
closes={'SPY':SPY,'BOND':BOND,'GOLD':GOLD}
# short-rate daily path (DGS3MO), ffilled to all days
dgs3=macro('DGS3MO')
cash_daily=(dgs3/100.0/TD).reindex(pd.date_range(dgs3.index[0],dgs3.index[-1],freq='D')).ffill()
def cash_on(idx): return cash_daily.reindex(idx).ffill().fillna(0.0)

def sleeve_returns_fair(lookback=105):
    """EW SPY/BOND/GOLD long-flat; FLAT leg earns the short rate; ER when long; txn cost on flips."""
    parts=[]
    for k,c in closes.items():
        c=c.astype(float); aret=c.pct_change()
        sig=TrendOverlay(lookback, enabled=True).exposure(c); pos=sig.shift(1)
        ch=cash_on(aret.index)
        r = pos*(aret - ER[k]/TD) + (1-pos)*ch          # long: asset−ER; flat: cash@short-rate
        flip=pos.diff().abs().fillna(0)
        r = r - flip*(1.0/3.0)*TXN                        # flip trades 1/3 weight, 1.5bps
        parts.append((r*(1.0/3.0)).rename(k))
    return pd.concat(parts,axis=1).dropna(how='all').sum(axis=1,min_count=1).dropna()

def robo_fair(weights, cash_rate):
    """monthly-rebal; ETF legs net of ER; _cash earns cash_rate (a daily Series); 1.5bps rebal cost."""
    etfs=[k for k in weights if k!='_cash']; cw=weights.get('_cash',0.0)
    rets=pd.concat({k:closes[k].pct_change()-ER[k]/TD for k in etfs},axis=1).dropna()
    cr=cash_rate.reindex(rets.index).ffill().fillna(0.0)
    hold={k:weights[k] for k in etfs}; cash=cw; out={}; pm=None
    for dt,row in rets.iterrows():
        m=(dt.year,dt.month); rebal_cost=0.0
        if pm is not None and m!=pm:
            tot=sum(hold.values())+cash
            newh={k:tot*weights[k] for k in etfs}; newc=tot*cw
            rebal_cost=sum(abs(newh[k]-hold[k]) for k in etfs)/max(tot,1e-9)*TXN
            hold=newh; cash=newc
        prev=sum(hold.values())+cash
        for k in etfs: hold[k]*=(1+row[k])
        cash*=(1+cr.loc[dt])
        out[dt]=(sum(hold.values())+cash)/prev-1 - rebal_cost; pm=m
    return pd.Series(out)

sleeve=sleeve_returns_fair()
r6040=robo_fair({'SPY':0.60,'BOND':0.40}, cash_daily)
# schwab_like: variant A = cash at market short rate; variant B = below-market sweep (short rate − 125bps)
cash_below=(cash_daily-0.0125/TD).clip(lower=0.0)
rschwabA=robo_fair({'SPY':0.45,'BOND':0.30,'GOLD':0.05,'_cash':0.20}, cash_daily)
rschwabB=robo_fair({'SPY':0.45,'BOND':0.30,'GOLD':0.05,'_cash':0.20}, cash_below)

start=max(sleeve.index[0],r6040.index[0],rschwabA.index[0]); end=min(sleeve.index[-1],r6040.index[-1])
def win(s): return s[(s.index>=start)&(s.index<=end)].dropna()
def maxdd(eq): return (eq/eq.cummax()-1).min()
def cagr(eq): return (eq.iloc[-1]/eq.iloc[0])**(365.25/(eq.index[-1]-eq.index[0]).days)-1
def so(r): return ME.sortino_ratio(r,0.0,TD)
def so_ci(r):
    try: return ME.bootstrap_distribution(r,lambda x:ME.sortino_ratio(x,0.0,TD),n_iterations=1000,seed=0).get('ci_low')
    except: return float('nan')

names={'TREND SLEEVE':sleeve,'60_40':r6040,'schwab_like (cash@mkt)':rschwabA,'schwab_like (below-mkt sweep)':rschwabB}
print(f'=== FAIR T-236 RE-RUN {start.date()}..{end.date()} (flat leg @ short rate; robo cash @ short rate; ER+txn both sides) ===')
print(f'{"strategy":30}{"Sortino":>9}{"ci_low":>8}{"Sharpe":>8}{"CAGR":>7}{"MaxDD":>8}{"$10k→":>10}')
res={}
for nm,r in names.items():
    rw=win(r); eq=(1+rw).cumprod(); res[nm]=(rw,eq)
    print(f'{nm:30}{so(rw):>9.3f}{so_ci(rw):>8.3f}{ME.sharpe_ratio(rw,0.0,TD):>8.3f}{cagr(eq)*100:>6.1f}%{maxdd(eq)*100:>7.1f}%{10000*eq.iloc[-1]/eq.iloc[0]:>10,.0f}')

# paired-difference block-bootstrap: sleeve vs each robo, ΔSortino + Δterminal-wealth CIs
def paired(sl, rb, L=21, n=1000):
    j=pd.concat({'s':sl,'r':rb},axis=1).dropna(); s=j['s'].values; r=j['r'].values; N=len(s)
    rng=np.random.default_rng(0); dso=[]; dtw=[]
    nb=int(np.ceil(N/L))
    for _ in range(n):
        st=rng.integers(0,N-L+1,size=nb); ix=np.concatenate([np.arange(t,t+L) for t in st])[:N]
        ss,rr=s[ix],r[ix]
        def sortino(x):
            d=x[x<0]; dd=np.sqrt((d**2).mean()) if len(d) else 1e-9; return (x.mean()/dd)*np.sqrt(TD)
        dso.append(sortino(ss)-sortino(rr))
        dtw.append(np.prod(1+ss)-np.prod(1+rr))
    return (np.percentile(dso,2.5),np.percentile(dso,97.5)), (np.percentile(dtw,2.5),np.percentile(dtw,97.5)), np.mean(np.array(dso)>0)
print('\n=== PAIRED-DIFFERENCE block-bootstrap (sleeve − robo; 21d blocks, 1000 iter) ===')
for nm in ['60_40','schwab_like (cash@mkt)','schwab_like (below-mkt sweep)']:
    (dlo,dhi),(tlo,thi),pwin=paired(win(sleeve),win(names[nm]))
    print(f'  sleeve − {nm:30}: ΔSortino 95%CI [{dlo:+.3f},{dhi:+.3f}]  Δterminal(×start) 95%CI [{tlo:+.2f},{thi:+.2f}]  P(sleeve Sortino>robo)={pwin:.0%}')

# MBL on ci_low (honest-N — this is a CORRECTION, N_trials unchanged; the sleeve lineage ~16)
N=16; mbl=math.sqrt(2*math.log(N)/((end-start).days/365.25))
print(f'\nMBL (N={N}, {((end-start).days/365.25):.0f}yr): Sharpe bar {mbl:.3f}; sleeve Sharpe {ME.sharpe_ratio(win(sleeve),0.0,TD):.3f} ci_low(Sortino) {so_ci(win(sleeve)):.3f}')
