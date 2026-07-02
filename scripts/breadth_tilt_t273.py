"""T-273 — market-breadth sizing tilt on the SPY leg of the multi-speed ensemble sleeve (fair T-255 harness).
Pre-registered ONE arm. Breadth = PIT survivorship-aware % of S&P members > 200dma (BreadthDetector defn,
vectorized). Multiplier = 0.5 + 0.5*causal-252d-percentile(breadth). Reuses T-268 harness + T-271 membership."""
import csv, os, sys, pathlib
from datetime import datetime
import pandas as pd, numpy as np
ROOT = '/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
TD = 252; ER = {'SPY': 0.0009, 'BOND': 0.0003, 'GOLD': 0.0040}; TXN = 0.00015

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

# ---- PIT survivorship-aware breadth: % of S&P members > 200dma ----
def build_breadth():
    mem = pd.read_parquet(f'{ROOT}/data/universe/sp500_membership_pit.parquet')
    mem['start'] = pd.to_datetime(mem['start']); mem['end'] = pd.to_datetime(mem['end'])
    cols = {}
    proc = pathlib.Path(f'{ROOT}/data/processed')
    for t in mem['ticker'].unique():
        f = proc / f'{t}_1d.csv'
        if not f.exists(): continue
        try:
            r = list(csv.DictReader(open(f)))
            s = pd.Series({datetime.strptime(x['Date'][:10], '%Y-%m-%d'): float(x['Close']) for x in r if x.get('Close')})
            if len(s) >= 200: cols[t] = s.sort_index()
        except Exception:
            continue
    C = pd.DataFrame(cols).sort_index()
    C = C[C.index >= pd.Timestamp('1999-01-01')]
    sma200 = C.rolling(200, min_periods=200).mean()
    above = C > sma200
    member = pd.DataFrame(False, index=C.index, columns=C.columns)
    for _, row in mem.iterrows():
        t = row['ticker']
        if t not in member.columns: continue
        end = row['end'] if pd.notna(row['end']) else C.index[-1]
        member.loc[(C.index >= row['start']) & (C.index <= end), t] = True
    valid = member & C.notna() & sma200.notna()
    nvalid = valid.sum(axis=1)
    breadth = (above & valid).sum(axis=1) / nvalid.where(nvalid >= 20)
    breadth = breadth.dropna()
    print(f"[breadth] {len(cols)} member tickers with prices; series {breadth.index[0].date()}..{breadth.index[-1].date()} "
          f"({len(breadth)} days); median members/bar = {int(nvalid.reindex(breadth.index).median())}; "
          f"breadth mean {breadth.mean():.2f} min {breadth.min():.2f} max {breadth.max():.2f}")
    return breadth
breadth = build_breadth()
# causal trailing-252d percentile of breadth -> multiplier in [0.5,1.0]
pct = breadth.rolling(252, min_periods=60).apply(lambda x: (x[-1] >= x).mean(), raw=True)
mult = (0.5 + 0.5 * pct).clip(0.5, 1.0)
spy_mult = mult.reindex(closes['SPY'].index).ffill()
print(f"[breadth] multiplier: mean {spy_mult.reindex(pd.date_range(COMMON_START, closes['SPY'].index[-1])).dropna().mean():.3f}, "
      f"frac at 0.5-floor {np.mean(spy_mult.dropna()<=0.55):.2f}, frac at 1.0-cap {np.mean(spy_mult.dropna()>=0.95):.2f}")

# ---- tilted ensemble sleeve (T-268 harness) ----
def sleeve_tilted(speeds, tilt_spy=False):
    parts = []
    for k, c in closes.items():
        c = c.astype(float); aret = c.pct_change()
        base = pd.concat([TrendOverlay(s, enabled=True).exposure(c) for s in speeds], axis=1).mean(axis=1)
        pos = base.shift(1)
        if k == 'SPY' and tilt_spy:
            # CAUSAL: breadth[t] uses close[t]; lag the multiplier one trading day (like the trend's .shift(1))
            m = spy_mult.reindex(pos.index).ffill()
            pos = pos * m.shift(1).fillna(1.0)
        ch = cash_on(aret.index)
        r = pos * (aret - ER[k] / TD) + (1 - pos) * ch - pos.diff().abs().fillna(0) * (1 / 3) * TXN
        parts.append((r * (1 / 3)).rename(k))
    s = pd.concat(parts, axis=1)
    return s[s.index >= COMMON_START].dropna(how='any').sum(axis=1).dropna()

def stats(r):
    r = r.dropna(); eq = (1 + r).cumprod(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    so = ME.sortino_ratio(r, 0.0, TD)
    try: ci = ME.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0, TD), n_iterations=1000, seed=0).get('ci_low')
    except Exception: ci = float('nan')
    return so, ci, (eq / eq.cummax() - 1).min(), (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1, 10000 * eq.iloc[-1] / eq.iloc[0]
def ddwin(r, a, b):
    s = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    if len(s) < 2: return float('nan')
    eq = (1 + s).cumprod(); return (eq / eq.cummax() - 1).min()
def cagrwin(r, a, b):
    s = r[(r.index >= pd.Timestamp(a)) & (r.index <= pd.Timestamp(b))]
    if len(s) < 2: return float('nan')
    eq = (1 + s).cumprod(); yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return (eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1
def paired(a, b, L=21, n=1000):
    j = pd.concat({'a': a, 'b': b}, axis=1).dropna(); A = j['a'].values; B = j['b'].values; N = len(A)
    rng = np.random.default_rng(0); dso = []; dw = []; nb = int(np.ceil(N / L))
    for _ in range(n):
        st = rng.integers(0, N - L + 1, size=nb); ix = np.concatenate([np.arange(t, t + L) for t in st])[:N]
        aa, bb = A[ix], B[ix]
        def so_(x): d = x[x < 0]; return (x.mean() / (np.sqrt((d ** 2).mean()) if len(d) else 1e-9)) * np.sqrt(TD)
        dso.append(so_(aa) - so_(bb)); dw.append(np.prod(1 + aa) - np.prod(1 + bb))
    return (np.percentile(dso, 2.5), np.percentile(dso, 97.5)), (np.percentile(dw, 2.5), np.percentile(dw, 97.5))

base = sleeve_tilted([42, 105, 210], tilt_spy=False)
tilt = sleeve_tilted([42, 105, 210], tilt_spy=True)
print(f"\n=== T-273 breadth tilt on SPY leg of the {{2,5,10}}mo ensemble ({base.index[0].date()}..{base.index[-1].date()}) ===")
for nm, r in [('unconditioned ensemble (T-260 spec)', base), ('breadth-tilted SPY leg', tilt)]:
    so, ci, md, cg, tw = stats(r)
    print(f"  {nm:36} Sortino={so:.3f} ci_low={ci:.3f} MaxDD={md*100:.1f}% CAGR={cg*100:.1f}% $10k={tw:,.0f}")
(dslo, dshi), (dwlo, dwhi) = paired(tilt, base)
print(f"\n  paired Δ(tilt − base): ΔSortino 95%CI [{dslo:+.3f},{dshi:+.3f}]  Δwealth(×start) 95%CI [{dwlo:+.3f},{dwhi:+.3f}]")
print("  named windows (CAGR / MaxDD) — divergence tops where breadth SHOULD help:")
for nm, a, b in [('2007-08 top', '2007-07-01', '2009-03-31'), ('late-2021 narrow', '2021-11-01', '2022-12-31'),
                 ('2015-2018 bull', '2015-01-01', '2018-09-30'), ('COVID-2020', '2020-01-01', '2020-12-31')]:
    print(f"    {nm:17} base {cagrwin(base,a,b)*100:+.1f}%/{ddwin(base,a,b)*100:.1f}%   tilt {cagrwin(tilt,a,b)*100:+.1f}%/{ddwin(tilt,a,b)*100:.1f}%")
