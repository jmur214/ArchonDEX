"""T-294 — leverage-vehicle bake-off. Is the offense edge leaking through SSO's daily reset?
Collateral-aware synthetics (C/T-296 rule: overlay leg = excess-over-cash). Basis-checked vs real funds."""
import csv, sys, pathlib
from datetime import datetime
import pandas as pd, numpy as np
ROOT = '/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
from core.calendar_guard import assert_no_calendar_holes, reindex_onto
TD = 252; TXN = 0.00015
SPY_ER = 0.000945; SSO_ER = 0.0089; NTSX_ER = 0.0020; RSSB_ER = 0.0036
SSO_SPREAD = 0.0060; FUT_SPREAD = 0.0030
CACHE = pathlib.Path(f'{ROOT}/data/research/t294'); CACHE.mkdir(parents=True, exist_ok=True)

def spy_close():
    r = list(csv.DictReader(open(f'{ROOT}/data/processed/SPY_1d.csv')))
    return pd.Series({datetime.strptime(x['Date'][:10], '%Y-%m-%d'): float(x['Close']) for x in r}).sort_index()
def cser(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index); return d.iloc[:, 0].astype(float).sort_index()
def macro(s):
    d = pd.read_parquet(f'{ROOT}/data/macro/{s}.parquet')['value'].astype(float); d.index = pd.to_datetime(d.index); return d.dropna().sort_index()
def yf_close(t, start):
    p = CACHE / f'{t}.parquet'
    if p.exists():
        s = pd.read_parquet(p)['close']; s.index = pd.to_datetime(s.index); return s.sort_index()
    import yfinance as yf
    df = yf.download(t, start=start, end='2026-05-01', auto_adjust=True, progress=False)
    s = df['Close']; s = s[s.columns[0]] if hasattr(s, 'columns') else s
    s.index = pd.to_datetime(s.index).tz_localize(None); s = s.dropna()
    pd.DataFrame({'close': s}).to_parquet(p); return s

spy = spy_close(); bond = cser(f'{ROOT}/data/research/bond_synth_dgs10_t255.csv')
dgs3 = macro('DGS3MO'); cash_d = (dgs3/100.0/TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq='D')).ffill()
def rf_on(idx): return cash_d.reindex(idx).ffill().fillna(0.0)

spy_tr = spy.pct_change()
IDX = spy_tr.index
# CALENDAR FIX (T-297 correction): the DGS10 bond synth is missing 48 SPY trading days. Intersecting it
# holed the SPY bar's calendar ($64,421 vs the true $74,104). Project bond ONTO the SPY calendar instead.
bond = reindex_onto(IDX, bond)
bond_tr = bond.pct_change()
rf = rf_on(IDX)
spy_gross = spy_tr + SPY_ER/TD                       # SSO/futures don't pay SPY's ER
bond_a = bond_tr

# ---- collateral-aware synthetics (C/T-296: overlay leg = excess-over-cash) ----
ntsx_syn = 0.90*spy_tr + 0.10*rf + 0.60*(bond_a - rf) - NTSX_ER/TD
rssb_syn = 1.00*spy_tr           + 1.00*(bond_a - rf) - RSSB_ER/TD
sso_syn  = 2*spy_gross - (rf + SSO_SPREAD/TD) - SSO_ER/TD          # daily reset
# naive (WRONG) forms, for the C/T-296 error magnitude:
ntsx_naive = 0.90*spy_tr + 0.60*bond_a - NTSX_ER/TD
rssb_naive = 1.00*spy_tr + 1.00*bond_a - RSSB_ER/TD

def lev_monthly(sret, rate_daily, er, L=2.0):
    """L-x position reset MONTHLY (no daily reset): fixed notional within the month, NAV drifts."""
    nav = 1.0; out = []; month = None; eq = dbt = 0.0
    rd = rate_daily.reindex(sret.index).fillna(0.0)
    for t, r in sret.items():
        if month != (t.year, t.month):
            month = (t.year, t.month); eq = L*nav; dbt = (L-1.0)*nav
        eq *= (1.0 + (0.0 if pd.isna(r) else r)); dbt *= (1.0 + rd[t])
        new = (eq - dbt) * (1.0 - er/TD)
        out.append(new/nav - 1.0 if nav > 1e-12 else 0.0)
        nav = max(new, 1e-9)
    return pd.Series(out, index=sret.index)

fut_2x_m  = lev_monthly(spy_gross.fillna(0), rf + FUT_SPREAD/TD, 0.0, 2.0)     # V4 vehicle: ideal, monthly reset
sso_2x_m  = lev_monthly(spy_gross.fillna(0), rf + SSO_SPREAD/TD, SSO_ER, 2.0)  # decay counterfactual (same costs as sso_syn)

# ---- basis checks vs real funds ----
def basis(name, syn, real_close, note=''):
    j = pd.concat({'s': syn, 'r': real_close.pct_change()}, axis=1).dropna()
    if len(j) < 60: print(f"  {name:22} insufficient overlap"); return
    es, er_ = (1+j['s']).cumprod(), (1+j['r']).cumprod()
    te = (j['s']-j['r']).std()*np.sqrt(TD)
    cs = es.iloc[-1]**(TD/len(j))-1; cr = er_.iloc[-1]**(TD/len(j))-1
    print(f"  {name:22} {j.index[0].date()}..{j.index[-1].date()} n={len(j):5}: TE {te*100:5.2f}%/yr | "
          f"CAGR syn {cs*100:6.2f}% vs real {cr*100:6.2f}% (gap {(cs-cr)*100:+.2f}%/yr) | term {es.iloc[-1]/er_.iloc[-1]:.3f} {note}")

print("=== BASIS CHECKS (collateral-aware synthetic vs REAL fund) ===")
basis('SSO (2x, daily)', sso_syn, yf_close('SSO','2006-06-01'))
basis('NTSX (90/60)', ntsx_syn, yf_close('NTSX','2018-08-01'))
basis('RSSB (100/100)', rssb_syn, yf_close('RSSB','2023-11-01'), '<- SHORT window, weak evidence')
print("  -- naive (non-collateral-aware) forms, to size the C/T-296 error --")
basis('NTSX naive', ntsx_naive, yf_close('NTSX','2018-08-01'))
basis('RSSB naive', rssb_naive, yf_close('RSSB','2023-11-01'))

# ---- the gate (same signal everywhere) ----
ens = pd.concat([TrendOverlay(s, enabled=True).exposure(spy.astype(float)) for s in [42,105,210]], axis=1).mean(axis=1)
pos = ens.shift(1)                       # causal
e2 = (2.0*pos).clip(upper=2.0)           # V1/V4 equity exposure path: {0, 2/3, 4/3, 2}

def blend_2x(lev_vehicle):
    """T-284 PRIMARY structure: e<=1 hold SPY(1x); e>1 hold SPY + the 2x vehicle. Exposure = e2 either way."""
    lo = e2*(spy_tr - SPY_ER/TD) + (1-e2)*rf
    hi = (2-e2)*(spy_tr - SPY_ER/TD) + (e2-1)*lev_vehicle.reindex(IDX)
    return lo.where(e2 <= 1, hi) - e2.diff().abs().fillna(0)*TXN

def gate_fund(vehicle):
    """Hold the (unleverable) fund at weight = ensemble fraction; rest cash."""
    w = pos
    return w*vehicle.reindex(IDX) + (1-w)*rf - w.diff().abs().fillna(0)*TXN

V1  = blend_2x(sso_syn)                                   # incumbent (T-284 PRIMARY)
V4  = blend_2x(fut_2x_m)                                  # ideal 2x, no daily reset
V2  = gate_fund(ntsx_syn)                                 # NTSX native (0.9x eq + 0.6x bond)
V3  = gate_fund(rssb_syn)                                 # RSSB native (1.0x eq + 1.0x bond)
# V2m: exposure-matched control -> 0.9x equity via 0.45*SSO + 0.55*cash, gated the same way
V2m = gate_fund(0.45*sso_syn + 0.55*rf)

START = max(spy.dropna().index[0], bond.dropna().index[0], pd.Timestamp('2000-08-30'))
arms = {'V1 gated SSO 2x (incumbent)': V1, 'V4 gated ideal-2x futures (no daily reset)': V4,
        'V2 gated NTSX 90/60 (0.9x eq)': V2, 'V3 gated RSSB 100/100 (1.0x eq)': V3,
        'V2m gated SSO+cash @0.9x eq (matched)': V2m}
arms = {k: v[v.index >= START].dropna() for k, v in arms.items()}
common = None
for v in arms.values(): common = v.index if common is None else common.intersection(v.index)
_bench = spy_tr[spy_tr.index >= START].dropna().index
assert_no_calendar_holes(_bench, common, benchmark_name='spy_tr(bar)', common_name='t294_common')
arms = {k: v.reindex(common).dropna() for k, v in arms.items()}

def stats(r):
    eq = (1+r).cumprod(); yrs = (eq.index[-1]-eq.index[0]).days/365.25
    md = (eq/eq.cummax()-1).min(); cg = eq.iloc[-1]**(1/yrs)-1
    return dict(wealth=10000*eq.iloc[-1], cagr=cg, sortino=ME.sortino_ratio(r,0.0,TD), maxdd=md,
                calmar=cg/abs(md) if md < 0 else float('nan'))
def win(r,a,b):
    s = r[(r.index>=pd.Timestamp(a))&(r.index<=pd.Timestamp(b))]
    if len(s)<2: return float('nan'), float('nan')
    eq=(1+s).cumprod(); yrs=(eq.index[-1]-eq.index[0]).days/365.25
    return eq.iloc[-1]**(1/yrs)-1, (eq/eq.cummax()-1).min()

print(f"\n=== ARMS ({common[0].date()}..{common[-1].date()}), WEALTH-led ===")
print(f"  {'arm':40}{'$10k→':>11}{'CAGR':>7}{'Sortino':>9}{'MaxDD':>8}{'Calmar':>8}")
S = {}
for k, r in arms.items():
    st = stats(r); S[k]=st
    print(f"  {k:40}{st['wealth']:>11,.0f}{st['cagr']*100:>6.1f}%{st['sortino']:>9.3f}{st['maxdd']*100:>7.1f}%{st['calmar']:>8.2f}")

# ---- Q-A: the vehicle gap (V4 - V1), same 2x equity exposure ----
k1,k4 = 'V1 gated SSO 2x (incumbent)','V4 gated ideal-2x futures (no daily reset)'
print(f"\n=== Q-A VEHICLE GAP (V4 − V1; identical 2x equity exposure path) ===")
print(f"  Δwealth = ${S[k4]['wealth']-S[k1]['wealth']:,.0f}  ΔCAGR = {(S[k4]['cagr']-S[k1]['cagr'])*100:+.2f}%/yr")

# decomposition on the LEVERED sleeve itself (standalone 2x series, common window)
w = common
def cagr(s): s=s.reindex(w).dropna(); eq=(1+s).cumprod(); return eq.iloc[-1]**(TD/len(s))-1
decay = cagr(sso_2x_m) - cagr(sso_syn)     # identical costs; monthly vs daily reset => PURE reset effect
er_gap, fin_gap = SSO_ER, (SSO_SPREAD - FUT_SPREAD)
total_meas = cagr(fut_2x_m) - cagr(sso_syn)            # measured total advantage of the ideal vehicle
# integrity: did the monthly-reset simulator ever approach wipeout (clamp) ? that would fake `decay`
nav_m = (1+sso_2x_m.reindex(w)).cumprod(); nav_f = (1+fut_2x_m.reindex(w)).cumprod()
print(f"  [integrity] monthly-reset 2x min NAV (start=1.0): sso-costs {nav_m.min():.4f}, futures-costs {nav_f.min():.4f} "
      f"(clamp binds only near 0 -> {'OK, no wipeout' if min(nav_m.min(), nav_f.min()) > 0.02 else 'WARNING: clamp may bind'})")
print(f"  decomposition — advantage of the IDEAL futures 2x over the SSO 2x (annualized, on the LEVERED LEG):")
print(f"    + chop/path decay avoided (daily vs monthly reset, same costs) = {decay*100:+.2f}%/yr")
print(f"    + fund ER avoided                                              = {er_gap*100:+.2f}%/yr")
print(f"    + financing spread avoided (60bps vs 30bps on 1x borrowed)     = {fin_gap*100:+.2f}%/yr")
print(f"    = sum of parts {(decay+er_gap+fin_gap)*100:+.2f}%/yr   vs MEASURED total {total_meas*100:+.2f}%/yr")
print(f"    (arm-level gap is smaller: the levered vehicle is held only when the gate is on and only for the")
print(f"     (e−1) fraction of NAV — avg {(e2-1).clip(lower=0).reindex(w).mean():.2f}x — the rest is plain SPY/cash.)")
# decay measured on the CHOP windows only (where the mechanism is claimed to operate, no wipeout risk)
for lbl,a,b in [('2011','2011-01-01','2011-12-31'),('2015-16','2015-01-01','2016-12-31'),('2018','2018-01-01','2018-12-31')]:
    d = win(sso_2x_m,a,b)[0] - win(sso_syn,a,b)[0]
    print(f"    chop-window decay {lbl:8}: {d*100:+.2f}%/yr (monthly-reset minus daily-reset, same costs)")
# realized financing actually paid, per arm (avg annualized)
lev_frac = (e2-1).clip(lower=0).reindex(w).fillna(0)
print(f"  realized financing paid: V1 {(lev_frac*(rf.reindex(w)+SSO_SPREAD/TD)).mean()*TD*100:.2f}%/yr | "
      f"V4 {(lev_frac*(rf.reindex(w)+FUT_SPREAD/TD)).mean()*TD*100:.2f}%/yr | "
      f"avg levered fraction {lev_frac.mean():.2f}x")
# tracking error vs the IDEAL frictionless exposure (e2 x spy_tr)
ideal = (e2*spy_tr).reindex(w)
for k in (k1,k4):
    te = (arms[k]-ideal).std()*np.sqrt(TD)
    print(f"  TE vs ideal {e2.max():.0f}x-exposure path: {k[:26]:28} {te*100:5.2f}%/yr")

print(f"\n=== NAMED WINDOWS (CAGR / in-window MaxDD) ===")
print(f"  {'window':16}" + "".join(f"{k.split()[0]:>16}" for k in arms))
for lbl,a,b in [('CHOP 2011','2011-01-01','2011-12-31'), ('CHOP 2015-16','2015-01-01','2016-12-31'),
                ('CHOP 2018','2018-01-01','2018-12-31'), ('RATE-STRESS 2022','2022-01-01','2022-12-31')]:
    row = "".join(f"{win(r,a,b)[0]*100:+7.1f}%/{win(r,a,b)[1]*100:5.1f}%" for r in arms.values())
    print(f"  {lbl:16}" + row)

# blind-spot #2: the stacked funds' BOND leg in the 2022 joint drawdown
b22 = bond_a[(bond_a.index>='2022-01-01')&(bond_a.index<='2022-12-31')]
s22 = spy_tr[(spy_tr.index>='2022-01-01')&(spy_tr.index<='2022-12-31')]
print(f"\n  [blind-spot #2] 2022 joint drawdown — the stacked funds embed a bond leg V1 does NOT have:")
print(f"    bond leg (DGS10 TR) 2022: {((1+b22).prod()-1)*100:+.1f}%   equity (SPY TR) 2022: {((1+s22).prod()-1)*100:+.1f}%")
print(f"    -> V2/V3's bond overlay FELL WITH equity in 2022; it is not a diversifier in a rate shock.")
