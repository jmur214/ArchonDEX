"""T-297 — turnover reduction on the offense config (execution-bound lever).
Arm1 = Carver deadband B=2/3 (>=2-of-3 speed confirmation); Arm2 = monthly-held e2. Frozen; no sweep."""
import csv, sys, pathlib
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
def cser(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index); return d.iloc[:, 0].astype(float).sort_index()

spy = spy_close(); bond = cser(f'{ROOT}/data/research/bond_synth_dgs10_t255.csv')
dgs3 = macro('DGS3MO'); cash_d = (dgs3/100.0/TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq='D')).ffill()
spy_tr = spy.pct_change(); IDX = spy_tr.index
rf = cash_d.reindex(IDX).ffill().fillna(0.0)
spy_gross = spy_tr + SPY_ER/TD
sso_syn = 2*spy_gross - (rf + SSO_SPREAD/TD) - SSO_ER/TD

ens = pd.concat([TrendOverlay(s, enabled=True).exposure(spy.astype(float)) for s in [42, 105, 210]], axis=1).mean(axis=1)
e_target = (2.0*ens.shift(1)).clip(upper=2.0)
START = pd.Timestamp('2000-08-30')

def deadband(tgt, band):
    """Carver buffering: hold unless |target - held| > band, then re-trade to target."""
    out = []; held = np.nan
    for v in tgt.values:
        if np.isnan(v): out.append(np.nan); continue
        if np.isnan(held) or abs(v - held) > band + TOL: held = v
        out.append(held)
    return pd.Series(out, index=tgt.index)

def monthly_hold(tgt):
    """Decide on the first trading day of each month; hold that exposure for the month."""
    df = pd.DataFrame({'e': tgt}); df['ym'] = df.index.to_period('M')
    first = df.groupby('ym')['e'].transform(lambda s: s.iloc[0])
    return first

paths = {'V1 undamped (T-284 PRIMARY)': e_target,
         'Arm1 Carver deadband B=2/3': deadband(e_target, B),
         'Arm2 monthly-held e2': monthly_hold(e_target)}

def arm_returns(e, slip_bps):
    """T-284 PRIMARY blend structure, exposure path = e. Fair slippage: extra bps on the SSO leg only."""
    e = e.reindex(IDX)
    lo = e*(spy_tr - SPY_ER/TD) + (1-e)*rf
    hi = (2-e)*(spy_tr - SPY_ER/TD) + (e-1)*sso_syn
    r = lo.where(e <= 1, hi)
    turn_all = e.diff().abs().fillna(0)
    sso_w = (e-1).clip(lower=0); turn_sso = sso_w.diff().abs().fillna(0)
    turn_spy = (turn_all - turn_sso).clip(lower=0)
    r = r - turn_all*TXN - turn_sso*(slip_bps/1e4) - turn_spy*SPY_SLIP
    return r[r.index >= START].dropna()

def stats(r):
    eq = (1+r).cumprod(); yrs = (eq.index[-1]-eq.index[0]).days/365.25
    md = (eq/eq.cummax()-1).min(); cg = eq.iloc[-1]**(1/yrs)-1
    return dict(wealth=10000*eq.iloc[-1], cagr=cg, sortino=ME.sortino_ratio(r,0.0,TD), maxdd=md)

# common window + the bar
common = arm_returns(e_target, 0).index
for e in paths.values(): common = common.intersection(arm_returns(e, 0).index)
bh = spy_tr.reindex(common).dropna(); bh_s = stats(bh)
print(f"=== T-297 turnover reduction ({common[0].date()}..{common[-1].date()}) ===")
print(f"buy-hold SPY TR (the bar): $10k={bh_s['wealth']:,.0f}  CAGR={bh_s['cagr']*100:.2f}%  MaxDD={bh_s['maxdd']*100:.1f}%")

yrs = (common[-1]-common[0]).days/365.25
print(f"\n{'arm':30}{'units/yr':>10}{'SSO-leg':>9}{'  |  $10k @0bps':>16}{'@5bps':>10}{'@10bps':>10}{'  Sortino':>10}{'MaxDD':>8}")
res = {}
for name, e in paths.items():
    ec = e.reindex(common)
    ta = ec.diff().abs().fillna(0); ssow = (ec-1).clip(lower=0); ts = ssow.diff().abs().fillna(0)
    row = {}
    for bps in (0, 5, 10):
        row[bps] = stats(arm_returns(e, bps).reindex(common).dropna())
    res[name] = (row, ta.sum()/yrs, ts.sum()/yrs)
    print(f"{name:30}{ta.sum()/yrs:>10.2f}{ts.sum()/yrs:>9.2f}{row[0]['wealth']:>16,.0f}{row[5]['wealth']:>10,.0f}"
          f"{row[10]['wealth']:>10,.0f}{row[0]['sortino']:>10.3f}{row[0]['maxdd']*100:>7.1f}%")

print(f"\n--- GATE (a): beats buy-hold SPY (${bh_s['wealth']:,.0f}) at the 5bps grid point? ---")
for name, (row, _, _) in res.items():
    ok = row[5]['wealth'] > bh_s['wealth']
    print(f"  {name:30} @5bps ${row[5]['wealth']:>8,.0f}  CAGR {row[5]['cagr']*100:5.2f}%  -> {'PASS' if ok else 'FAIL'}")

print(f"\n--- GATE (b): crash-window exit-lag (trading days) vs the undamped gate ---")
base = e_target.reindex(common)
def first_at_or_below(e, thr, a, b):
    s = e[(e.index >= pd.Timestamp(a)) & (e.index <= pd.Timestamp(b))]
    hit = s[s <= thr + TOL]
    return hit.index[0] if len(hit) else None
def lag_days(e, thr, a, b):
    d0 = first_at_or_below(base, thr, a, b); d1 = first_at_or_below(e.reindex(common), thr, a, b)
    if d0 is None or d1 is None: return None
    return int(common.searchsorted(d1) - common.searchsorted(d0))
crises = [('2008 GFC','2007-10-01','2009-06-30'), ('2020 COVID','2020-01-01','2020-06-30'), ('2022 bear','2022-01-01','2022-12-31')]
for name, e in paths.items():
    if name.startswith('V1'): continue
    parts = []
    worst = 0
    for lbl,a,b in crises:
        l1 = lag_days(e, 1.0, a, b); l0 = lag_days(e, 0.0, a, b)
        for l in (l1, l0):
            if l is not None: worst = max(worst, l)
        parts.append(f"{lbl}: de-lever {l1 if l1 is not None else 'n/a'}d, full-exit {l0 if l0 is not None else 'n/a'}d")
    ok = worst <= 5
    print(f"  {name:30} " + " | ".join(parts))
    print(f"  {'':30} worst lag {worst}d -> gate(b) {'PASS' if ok else 'FAIL'}")

print(f"\n--- VERDICT (both gates) ---")
for name, (row, ta, ts) in res.items():
    if name.startswith('V1'): continue
    a_ok = row[5]['wealth'] > bh_s['wealth']
    worst = 0
    for lbl,x,y in crises:
        for thr in (1.0, 0.0):
            l = lag_days(paths[name], thr, x, y)
            if l is not None: worst = max(worst, l)
    b_ok = worst <= 5
    print(f"  {name:30} gate(a) {'PASS' if a_ok else 'FAIL'} | gate(b) {'PASS' if b_ok else 'FAIL'} "
          f"=> {'EARNS the offense row' if (a_ok and b_ok) else 'does NOT earn the offense row'}")
