"""T-294b — taxable-margin vehicle: gated 2x SPY via MES futures (§1256, annual mark-to-market)
vs after-tax taxable buy-hold SPY and the zero-tax Roth-SSO arm. Undamped T-284 PRIMARY path (T-297 failed)."""
import csv, sys
from datetime import datetime
import pandas as pd, numpy as np
ROOT = '/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
TD = 252; TXN = 0.00015
SPY_ER = 0.000945; SSO_ER = 0.0089; SSO_SPREAD = 0.0060; FUT_SPREAD = 0.0030
SPY_SLIP = 0.51/1e4
MES_SLIP = 0.5/1e4          # per side on |d notional| (~1bp round-trip: 0.35bp spread + 0.35bp commission)
ROLL_BPS_YR = 0.0008        # 4 quarterly rolls @ ~2bps of notional
DIV_YIELD = 0.0192          # measured: SPY TR 8.37% - price 6.45%
SSO_DIST = 0.005            # SSO distribution yield (small; leveraged ETFs distribute little)
BRACKETS = {'base (ST24/LT15)': dict(st=0.24, lt=0.15, qdiv=0.15),
            'high (ST37/LT20)': dict(st=0.37, lt=0.20, qdiv=0.20)}
def blended(b): return 0.60*b['lt'] + 0.40*b['st']       # §1256 60/40

def spy_close():
    r = list(csv.DictReader(open(f'{ROOT}/data/processed/SPY_1d.csv')))
    return pd.Series({datetime.strptime(x['Date'][:10], '%Y-%m-%d'): float(x['Close']) for x in r}).sort_index()
def macro(s):
    d = pd.read_parquet(f'{ROOT}/data/macro/{s}.parquet')['value'].astype(float); d.index = pd.to_datetime(d.index); return d.dropna().sort_index()

spy = spy_close(); spy_tr = spy.pct_change(); IDX = spy_tr.index
dgs3 = macro('DGS3MO'); rf = (dgs3/100.0/TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq='D')).ffill().reindex(IDX).ffill().fillna(0.0)
spy_gross = spy_tr + SPY_ER/TD
sso_syn = 2*spy_gross - (rf + SSO_SPREAD/TD) - SSO_ER/TD
ens = pd.concat([TrendOverlay(s, enabled=True).exposure(spy.astype(float)) for s in [42, 105, 210]], axis=1).mean(axis=1)
e2 = (2.0*ens.shift(1)).clip(upper=2.0)
START = pd.Timestamp('2000-08-30')
W = IDX[(IDX >= START) & spy_tr.notna() & e2.notna()]

def roth_sso(slip_bps):
    """V1 = T-284 PRIMARY blend, zero tax."""
    e = e2.reindex(W)
    lo = e*(spy_tr - SPY_ER/TD) + (1-e)*rf
    hi = (2-e)*(spy_tr - SPY_ER/TD) + (e-1)*sso_syn
    r = lo.where(e <= 1, hi)
    ta = e.diff().abs().fillna(0); ssow = (e-1).clip(lower=0); ts = ssow.diff().abs().fillna(0)
    tsp = (ta-ts).clip(lower=0)
    return (r - ta*TXN - ts*(slip_bps/1e4) - tsp*SPY_SLIP).reindex(W).dropna()

def taxable_sso(slip_bps, b):
    """Same ETF blend in taxable: gains DEFER (never sold); only dividends/distributions taxed annually."""
    e = e2.reindex(W)
    spy_frac = e.where(e <= 1, 2-e).clip(lower=0)          # fraction of NAV held as SPY
    sso_frac = (e-1).clip(lower=0)
    drag = (spy_frac*DIV_YIELD*b['qdiv'] + sso_frac*SSO_DIST*b['qdiv'])/TD
    return (roth_sso(slip_bps) - drag.reindex(W)).dropna()

def taxable_bh_spy(b):
    """Buy-hold SPY in taxable: dividend taxed annually; NO terminal cap-gains (never-sell / step-up)."""
    return (spy_tr.reindex(W) - DIV_YIELD*b['qdiv']/TD).dropna()

def taxable_futures(b, mes_slip=MES_SLIP):
    """MES futures on T-bill collateral. Notional reset only on gate change (no daily reset).
    §1256: year-end mark-to-market of futures P&L at the 60/40 blended rate, losses carried forward.
    Collateral interest taxed annually at the ST rate."""
    e = e2.reindex(W).values; sg = spy_gross.reindex(W).values; rr = rf.reindex(W).values
    dates = W
    nav = 1.0; notional = 0.0; prev_e = np.nan
    yr = dates[0].year; yr_pnl = 0.0; yr_int = 0.0; carry = 0.0
    out = []
    for i, t in enumerate(dates):
        if np.isnan(e[i]) or np.isnan(sg[i]): out.append(0.0); continue
        if np.isnan(prev_e) or e[i] != prev_e:                  # gate change -> re-set futures notional
            target = e[i]*nav
            cost = abs(target - notional)*mes_slip
            nav -= cost; notional = e[i]*nav; prev_e = e[i]
        pnl = notional*(sg[i] - rr[i] - FUT_SPREAD/TD)          # futures excess return (basis financing)
        pnl -= notional*ROLL_BPS_YR/TD                          # quarterly roll, amortized
        interest = nav*rr[i]
        new = nav + pnl + interest
        yr_pnl += pnl; yr_int += interest
        if t.year != yr or i == len(dates)-1:                   # calendar year end -> §1256 mark + interest tax
            taxable_pnl = yr_pnl + carry
            if taxable_pnl > 0:
                new -= taxable_pnl*blended(b); carry = 0.0
            else:
                carry = taxable_pnl                             # loss carryforward
            new -= max(yr_int, 0.0)*b['st']
            yr = t.year; yr_pnl = 0.0; yr_int = 0.0
        out.append(new/nav - 1.0 if nav > 1e-12 else 0.0)
        nav = max(new, 1e-9)
    return pd.Series(out, index=dates).dropna()

def stats(r):
    eq = (1+r).cumprod(); yrs = (eq.index[-1]-eq.index[0]).days/365.25
    md = (eq/eq.cummax()-1).min()
    return dict(wealth=10000*eq.iloc[-1], cagr=eq.iloc[-1]**(1/yrs)-1, sortino=ME.sortino_ratio(r,0.0,TD), maxdd=md)

print(f"=== T-294b taxable-futures vehicle ({W[0].date()}..{W[-1].date()}) | undamped T-284 path (T-297 failed) ===")
print(f"pretax reference: futures arm gross of tax = ", end='')
pf = taxable_futures(dict(st=0.0, lt=0.0, qdiv=0.0)); print(f"$10k->{stats(pf)['wealth']:,.0f}  CAGR {stats(pf)['cagr']*100:.2f}%")

for bname, b in BRACKETS.items():
    print(f"\n--- bracket {bname}: §1256 blended {blended(b)*100:.1f}%, qual-div {b['qdiv']*100:.0f}% ---")
    rows = [(f"TAXABLE futures 2x (§1256 annual MTM)", taxable_futures(b)),
            (f"after-tax taxable buy-hold SPY (the bar)", taxable_bh_spy(b)),
            (f"Roth SSO @0bps", roth_sso(0)), (f"Roth SSO @5bps (E's floor)", roth_sso(5)), (f"Roth SSO @10bps", roth_sso(10)),
            (f"taxable SSO @5bps (deferred gains)", taxable_sso(5, b))]
    S = {}
    print(f"  {'strategy':44}{'$10k→':>11}{'CAGR':>8}{'Sortino':>9}{'MaxDD':>8}")
    for n, r in rows:
        st = stats(r); S[n] = st
        print(f"  {n:44}{st['wealth']:>11,.0f}{st['cagr']*100:>7.2f}%{st['sortino']:>9.3f}{st['maxdd']*100:>7.1f}%")
    fut = S["TAXABLE futures 2x (§1256 annual MTM)"]; bar = S["after-tax taxable buy-hold SPY (the bar)"]
    roth5 = S["Roth SSO @5bps (E's floor)"]
    a = fut['wealth'] > bar['wealth']; c = fut['wealth'] > roth5['wealth']
    print(f"  GATE: beats after-tax BH-SPY? {'YES' if a else 'NO'} ({fut['wealth']:,.0f} vs {bar['wealth']:,.0f}) | "
          f"beats Roth-SSO@5bps? {'YES' if c else 'NO'} ({fut['wealth']:,.0f} vs {roth5['wealth']:,.0f}) "
          f"=> {'EARNS the row' if (a and c) else 'does NOT earn the row'}")
    print(f"  tax drag on the futures arm: pretax {stats(pf)['cagr']*100:.2f}% -> after-tax {fut['cagr']*100:.2f}% "
          f"({(stats(pf)['cagr']-fut['cagr'])*100:.2f}%/yr)")
