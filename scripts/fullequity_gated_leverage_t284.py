"""T-284 — trend-gated leverage on a FULL-EQUITY base. PRIMARY = 100% SPY 2x-when-trend-on;
SECONDARY = 3-asset sleeve each leg 2x-gated. Fair T-255 harness + T-282 SSO-synthetic (basis carried fwd)."""
import csv, sys, pathlib
from datetime import datetime
import pandas as pd, numpy as np
ROOT = '/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
TD = 252; ER = {'SPY': 0.0009, 'BOND': 0.0003, 'GOLD': 0.0040}; TXN = 0.00015
ADD_ER = {'SPY': 0.000945, 'BOND': 0.0003, 'GOLD': 0.0040}   # gross-up per leg (add back the 1x ER)
LEV_ER = {'SPY': 0.0089, 'BOND': 0.0095, 'GOLD': 0.0095}     # 2x-product ER: SSO / 2x-treasury / UGL-like
BORROW_SPREAD = 0.0060
CACHE = pathlib.Path(f'{ROOT}/data/research/t284'); CACHE.mkdir(parents=True, exist_ok=True)

def spy_close():
    r = list(csv.DictReader(open(f'{ROOT}/data/processed/SPY_1d.csv')))
    return pd.Series({datetime.strptime(x['Date'][:10], '%Y-%m-%d'): float(x['Close']) for x in r}).sort_index()
def cser(f):
    d = pd.read_csv(f, index_col=0); d.index = pd.to_datetime(d.index); return d.iloc[:, 0].astype(float).sort_index()
def macro(s):
    d = pd.read_parquet(f'{ROOT}/data/macro/{s}.parquet')['value'].astype(float); d.index = pd.to_datetime(d.index); return d.dropna().sort_index()
closes = {'SPY': spy_close(), 'BOND': cser(f'{ROOT}/data/research/bond_synth_dgs10_t255.csv'),
          'GOLD': cser(f'{ROOT}/data/research/gold_gcf_t255.csv')}
dgs3 = macro('DGS3MO'); cash_daily = (dgs3 / 100.0 / TD).reindex(pd.date_range(dgs3.index[0], dgs3.index[-1], freq='D')).ffill()
def cash_on(idx): return cash_daily.reindex(idx).ffill().fillna(0.0)
COMMON_START = max(c.dropna().index[0] for c in closes.values())

# per-leg synthetic 2x series: 2*leg_gross_tr - borrow - lev_ER
syn2x = {}
for k, c in closes.items():
    aret = c.pct_change(); gross = aret + ADD_ER[k] / TD
    borrow = cash_on(c.index) + BORROW_SPREAD / TD
    syn2x[k] = (2 * gross - borrow - LEV_ER[k] / TD)

def ens_frac(c):
    return pd.concat([TrendOverlay(s, enabled=True).exposure(c.astype(float)) for s in [42, 105, 210]], axis=1).mean(axis=1)

def leg_ret(k, lev, weight):
    """return series of a strategy that is `weight` in the k-leg, gated at up to `lev`x when trend on, cash off."""
    c = closes[k].astype(float); aret = c.pct_change(); ch = cash_on(aret.index)
    pos = ens_frac(c).shift(1)
    if lev > 1.0:
        e = (lev * pos).clip(upper=lev)
        lo = e * (aret - ER[k] / TD) + (1 - e) * ch
        hi = (2 - e) * (aret - ER[k] / TD) + (e - 1) * syn2x[k].reindex(aret.index)
        r = lo.where(e <= 1, hi) - e.diff().abs().fillna(0) * weight * TXN
    else:
        r = pos * (aret - ER[k] / TD) + (1 - pos) * ch - pos.diff().abs().fillna(0) * weight * TXN
    return (r * weight).rename(k)

def combine(legs):
    s = pd.concat(legs, axis=1)
    return s[s.index >= COMMON_START].dropna(how='any').sum(axis=1).dropna()

primary   = combine([leg_ret('SPY', 2.0, 1.0)])                                           # 100% SPY, 2x-gated
secondary = combine([leg_ret(k, 2.0, 1/3) for k in closes])                               # 3-leg each 2x-gated
t282_arm  = combine([leg_ret('SPY', 2.0, 1/3), leg_ret('BOND', 1.0, 1/3), leg_ret('GOLD', 1.0, 1/3)])
plain     = combine([leg_ret(k, 1.0, 1/3) for k in closes])
aret_spy = closes['SPY'].pct_change()
bh_spy = aret_spy.reindex(primary.index).dropna()
bh_2x  = syn2x['SPY'].reindex(primary.index).dropna()
# align EVERY series to one common window so the wealth column is apples-to-apples
_all = [primary, secondary, t282_arm, plain, bh_spy, bh_2x]
common = _all[0].index
for s in _all[1:]: common = common.intersection(s.index)
primary, secondary, t282_arm, plain, bh_spy, bh_2x = [x.reindex(common).dropna() for x in _all]
W = common

def stats(r):
    r = r.dropna(); eq = (1 + r).cumprod(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    so = ME.sortino_ratio(r, 0.0, TD)
    try: ci = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0).get('ci_low')
    except Exception: ci = float('nan')
    md = (eq / eq.cummax() - 1).min(); cg = eq.iloc[-1] ** (1 / yrs) - 1
    dd = (eq / eq.cummax() - 1); worst_end = dd.idxmin()
    return dict(sortino=so, ci=ci, sharpe=ME.sharpe_ratio(r, 0.0, TD), maxdd=md,
                calmar=(cg / abs(md) if md < 0 else float('nan')), cagr=cg, wealth=10000 * eq.iloc[-1],
                worst=str(worst_end.date()))
def paired(a, b, L=21, n=1000):
    jj = pd.concat({'a': a, 'b': b}, axis=1).dropna(); A = jj['a'].values; B = jj['b'].values; N = len(A)
    rng = np.random.default_rng(0); dw = []; nb = int(np.ceil(N / L))
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb); ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
        dw.append(np.prod(1 + A[ix]) - np.prod(1 + B[ix]))
    return np.percentile(dw, 2.5), np.percentile(dw, 97.5)
def win(r, a, b):
    s = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    if len(s) < 2: return float('nan'), float('nan')
    eq = (1 + s).cumprod(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return eq.iloc[-1] ** (1 / yrs) - 1, (eq / eq.cummax() - 1).min()

print(f"=== T-284 full-equity gated leverage, {W[0].date()}..{W[-1].date()} (WEALTH-led) ===")
print(f"  {'strategy':32}{'$10k→':>12}{'CAGR':>7}{'Sortino':>9}{'Sharpe':>8}{'MaxDD':>8}{'Calmar':>8}  worst")
rows = [('PRIMARY 100%SPY 2x-gated', primary), ('SECONDARY 3-leg 2x-gated', secondary),
        ('buy-hold SPY TR (THE BAR)', bh_spy), ('naked 2x SSO-syn (ceiling)', bh_2x),
        ('T-282 arm (1/3 sleeve 2x)', t282_arm), ('plain ensemble sleeve', plain)]
for nm, r in rows:
    st = stats(r)
    print(f"  {nm:32}{st['wealth']:>12,.0f}{st['cagr']*100:>6.1f}%{st['sortino']:>9.3f}{st['sharpe']:>8.3f}{st['maxdd']*100:>7.1f}%{st['calmar']:>8.2f}  {st['worst']}")

print("\n  PRIMARY GATE — paired Δterminal-wealth (×start) 95% CI vs buy-hold SPY:")
for nm, r in [('PRIMARY', primary), ('SECONDARY', secondary)]:
    lo, hi = paired(r, bh_spy); print(f"    {nm:10} − BH-SPY : [{lo:+.2f}, {hi:+.2f}]  ({'WIN' if lo>0 else 'not sig' if hi>0 else 'LOSS'})")

print("\n  NAMED WINDOWS (CAGR / in-window MaxDD): PRIMARY | BH-SPY | naked-2x")
for label, a, b in [('CHOP 2011', '2011-01-01', '2011-12-31'), ('CHOP 2015-16', '2015-01-01', '2016-12-31'),
                    ('CHOP 2018', '2018-01-01', '2018-12-31'), ('CRASH 2008', '2008-01-01', '2009-03-31'),
                    ('CRASH 2020', '2020-01-01', '2020-12-31'), ('CRASH 2022', '2022-01-01', '2022-12-31')]:
    pw = win(primary, a, b); sw = win(bh_spy, a, b); nw = win(bh_2x, a, b)
    print(f"    {label:14} {pw[0]*100:+7.1f}%/{pw[1]*100:6.1f}%  | {sw[0]*100:+6.1f}%/{sw[1]*100:6.1f}%  | {nw[0]*100:+7.1f}%/{nw[1]*100:6.1f}%")

# accumulation handoff: save daily curves for B/T-283
pd.DataFrame({'primary': primary, 'secondary': secondary, 't282_arm': t282_arm, 'plain': plain,
              'bh_spy': bh_spy, 'bh_2x': bh_2x}).to_parquet(CACHE / 'daily_curves.parquet')
print(f"\n[handoff] daily curves -> data/research/t284/daily_curves.parquet (for B/T-283 accumulation overlay)")
