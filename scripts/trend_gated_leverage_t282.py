"""T-282 — trend-gated leverage: the validated ensemble sleeve with its SPY leg at up to 2x WHEN trend on.
Fair T-255 harness. SSO-synthetic (2x SPY gross TR - borrow - ER), basis-checked vs real SSO. Wealth-primary."""
import csv, sys, pathlib
from datetime import datetime
import pandas as pd, numpy as np
ROOT = '/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
TD = 252; ER = {'SPY': 0.0009, 'BOND': 0.0003, 'GOLD': 0.0040}; TXN = 0.00015
SPY_ER = 0.000945; SSO_ER = 0.0089; BORROW_SPREAD = 0.0060
CACHE = pathlib.Path(f'{ROOT}/data/research/t282'); CACHE.mkdir(parents=True, exist_ok=True)

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

# ---- SSO synthetic (2x SPY gross TR - borrow - SSO ER), daily-rebalanced ----
spy_idx = closes['SPY'].index
aret_spy = closes['SPY'].pct_change()
spy_tr_gross = aret_spy + SPY_ER / TD
borrow_daily = cash_on(spy_idx) + BORROW_SPREAD / TD
sso_syn = (2 * spy_tr_gross - borrow_daily - SSO_ER / TD).rename('sso_syn')

# ---- basis check vs real SSO (yfinance, 2006+) ----
def real_sso():
    p = CACHE / 'sso_real.parquet'
    if p.exists():
        s = pd.read_parquet(p)['close']; s.index = pd.to_datetime(s.index); return s.sort_index()
    import yfinance as yf
    df = yf.download('SSO', start='2006-06-01', end='2026-04-30', auto_adjust=True, progress=False)
    s = df['Close']; s = s[s.columns[0]] if hasattr(s, 'columns') else s
    s.index = pd.to_datetime(s.index).tz_localize(None); s = s.dropna()
    pd.DataFrame({'close': s}).to_parquet(p); return s
try:
    sso = real_sso(); sso_r = sso.pct_change()
    j = pd.concat({'syn': sso_syn, 'real': sso_r}, axis=1).dropna()
    j = j[j.index >= '2006-06-21']
    eq_syn = (1 + j['syn']).cumprod(); eq_real = (1 + j['real']).cumprod()
    te = (j['syn'] - j['real']).std() * np.sqrt(TD)
    cg_syn = eq_syn.iloc[-1] ** (TD / len(j)) - 1; cg_real = eq_real.iloc[-1] ** (TD / len(j)) - 1
    print(f"=== BASIS CHECK (synthetic vs REAL SSO, {j.index[0].date()}..{j.index[-1].date()}, n={len(j)}) ===")
    print(f"  ann. tracking-error(daily diff) = {te*100:.2f}%/yr | CAGR syn {cg_syn*100:.2f}% vs real {cg_real*100:.2f}% "
          f"(gap {(cg_syn-cg_real)*100:+.2f}%/yr) | terminal ratio syn/real = {eq_syn.iloc[-1]/eq_real.iloc[-1]:.3f}")
except Exception as e:
    print(f"[basis] real-SSO check skipped: {str(e)[:100]}")

# ---- sleeve builder (SPY leg optionally levered to 2x via SPY+SSO blend) ----
def build_sleeve(spy_lev=1.0):
    parts = []
    for k, c in closes.items():
        c = c.astype(float); aret = c.pct_change()
        ens = pd.concat([TrendOverlay(s, enabled=True).exposure(c) for s in [42, 105, 210]], axis=1).mean(axis=1)
        pos = ens.shift(1); ch = cash_on(aret.index)
        if k == 'SPY' and spy_lev > 1.0:
            e = (spy_lev * pos).clip(upper=spy_lev)
            lo = e * (aret - SPY_ER / TD) + (1 - e) * ch                       # e<=1
            hi = (2 - e) * (aret - SPY_ER / TD) + (e - 1) * sso_syn.reindex(aret.index)  # e>1
            r = lo.where(e <= 1, hi) - e.diff().abs().fillna(0) * (1 / 3) * TXN
        else:
            r = pos * (aret - ER[k] / TD) + (1 - pos) * ch - pos.diff().abs().fillna(0) * (1 / 3) * TXN
        parts.append((r * (1 / 3)).rename(k))
    s = pd.concat(parts, axis=1)
    return s[s.index >= COMMON_START].dropna(how='any').sum(axis=1).dropna()

arm = build_sleeve(spy_lev=2.0)
plain = build_sleeve(spy_lev=1.0)
# baselines
W = arm.index                                          # common window
bh_spy = aret_spy.reindex(W).dropna()                  # buy-hold SPY TR (ER already in adj series)
bh_sso = sso_syn.reindex(W).dropna()                   # naked 2x
bond_r = closes['BOND'].pct_change()
sf = pd.concat({'s': aret_spy - ER['SPY'] / TD, 'b': bond_r - ER['BOND'] / TD}, axis=1).reindex(W)
r6040 = (0.6 * sf['s'] + 0.4 * sf['b']).dropna()       # daily-rebal 60/40, net ER (continuity baseline)

def stats(r):
    r = r.dropna(); eq = (1 + r).cumprod(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    so = ME.sortino_ratio(r, 0.0, TD)
    try: ci = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0).get('ci_low')
    except Exception: ci = float('nan')
    md = (eq / eq.cummax() - 1).min(); cg = eq.iloc[-1] ** (1 / yrs) - 1
    return dict(sortino=so, ci=ci, sharpe=ME.sharpe_ratio(r, 0.0, TD), maxdd=md,
                calmar=(cg / abs(md) if md < 0 else float('nan')), cagr=cg, wealth=10000 * eq.iloc[-1])
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

print(f"\n=== T-282 5-way (WEALTH-led), {W[0].date()}..{W[-1].date()} ===")
print(f"  {'strategy':30}{'$10k→':>12}{'CAGR':>7}{'Sortino':>9}{'ci_low':>8}{'Sharpe':>8}{'MaxDD':>8}{'Calmar':>8}")
rows = [('TREND-GATED 2x ARM', arm), ('buy-hold SPY TR (THE BAR)', bh_spy), ('plain ensemble sleeve', plain),
        ('60/40 (continuity)', r6040), ('buy-hold SSO-syn (naked 2x)', bh_sso)]
S = {}
for nm, r in rows:
    st = stats(r); S[nm] = st
    print(f"  {nm:30}{st['wealth']:>12,.0f}{st['cagr']*100:>6.1f}%{st['sortino']:>9.3f}{st['ci']:>8.3f}{st['sharpe']:>8.3f}{st['maxdd']*100:>7.1f}%{st['calmar']:>8.2f}")

print("\n  PRIMARY GATE — paired Δterminal-wealth (×start) 95% CI:")
for bnm, b in [('buy-hold SPY TR', bh_spy), ('plain ensemble sleeve', plain)]:
    lo, hi = paired(arm, b); print(f"    arm − {bnm:22}: [{lo:+.2f}, {hi:+.2f}]  ({'WIN' if lo>0 else 'not sig' if hi>0 else 'LOSS'})")

print("\n  NAMED WINDOWS (CAGR / in-window MaxDD): arm | plain | BH-SPY")
for label, a, b in [('CHOP 2011', '2011-01-01', '2011-12-31'), ('CHOP 2015-16', '2015-01-01', '2016-12-31'),
                    ('CHOP 2018', '2018-01-01', '2018-12-31'), ('CRASH 2008', '2008-01-01', '2009-03-31'),
                    ('CRASH 2020', '2020-01-01', '2020-12-31'), ('CRASH 2022', '2022-01-01', '2022-12-31')]:
    aw = win(arm, a, b); pw = win(plain, a, b); sw = win(bh_spy, a, b)
    print(f"    {label:14} {aw[0]*100:+6.1f}%/{aw[1]*100:5.1f}%  | {pw[0]*100:+6.1f}%/{pw[1]*100:5.1f}%  | {sw[0]*100:+6.1f}%/{sw[1]*100:5.1f}%")
