"""T-268 — FOMC even-week tilt on the SPY leg of the multi-speed ensemble sleeve (fair T-255 harness).
Pre-registered ONE arm (even 1.0 / odd 0.5 on SPY leg only). Reuses T-260 harness + T-250 FOMC calendar."""
import csv, sys
from datetime import datetime
import pandas as pd, numpy as np
ROOT = '/Users/jacksonmurphy/Dev/trading_machine-agent-d'; sys.path.insert(0, ROOT)
from core.metrics_engine import MetricsEngine as ME
from core.trend_overlay import TrendOverlay
TD = 252; ER = {'SPY': 0.0009, 'BOND': 0.0003, 'GOLD': 0.0040}; TXN = 0.00015

# ---- fair T-255/T-260 substrate ----
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

# ---- FOMC even-week calendar (T-250) ----
FOMC = [
"1994-02-04","1994-03-22","1994-04-18","1994-05-17","1994-07-06","1994-08-16","1994-09-27","1994-11-15","1994-12-20",
"1995-02-01","1995-03-28","1995-05-23","1995-07-06","1995-08-22","1995-09-26","1995-11-15","1995-12-19",
"1996-01-31","1996-03-26","1996-05-21","1996-07-03","1996-08-20","1996-09-24","1996-11-13","1996-12-17",
"1997-02-05","1997-03-25","1997-05-20","1997-07-02","1997-08-19","1997-09-30","1997-11-12","1997-12-16",
"1998-02-04","1998-03-31","1998-05-19","1998-07-01","1998-08-18","1998-09-29","1998-11-17","1998-12-22",
"1999-02-03","1999-03-30","1999-05-18","1999-06-30","1999-08-24","1999-10-05","1999-11-16","1999-12-21",
"2000-02-02","2000-03-21","2000-05-16","2000-06-28","2000-08-22","2000-10-03","2000-11-15","2000-12-19",
"2001-01-31","2001-03-20","2001-05-15","2001-06-27","2001-08-21","2001-10-02","2001-11-06","2001-12-11",
"2002-01-30","2002-03-19","2002-05-07","2002-06-26","2002-08-13","2002-09-24","2002-11-06","2002-12-10",
"2003-01-29","2003-03-18","2003-05-06","2003-06-25","2003-08-12","2003-09-16","2003-10-28","2003-12-09",
"2004-01-28","2004-03-16","2004-05-04","2004-06-30","2004-08-10","2004-09-21","2004-11-10","2004-12-14",
"2005-02-02","2005-03-22","2005-05-03","2005-06-30","2005-08-09","2005-09-20","2005-11-01","2005-12-13",
"2006-01-31","2006-03-28","2006-05-10","2006-06-29","2006-08-08","2006-09-20","2006-10-25","2006-12-12",
"2007-01-31","2007-03-21","2007-05-09","2007-06-28","2007-08-07","2007-09-18","2007-10-31","2007-12-11",
"2008-01-30","2008-03-18","2008-04-30","2008-06-25","2008-08-05","2008-09-16","2008-10-29","2008-12-16",
"2009-01-28","2009-03-18","2009-04-29","2009-06-24","2009-08-12","2009-09-23","2009-11-04","2009-12-16",
"2010-01-27","2010-03-16","2010-04-28","2010-06-23","2010-08-10","2010-09-21","2010-11-03","2010-12-14",
"2011-01-26","2011-03-15","2011-04-27","2011-06-22","2011-08-09","2011-09-21","2011-11-02","2011-12-13",
"2012-01-25","2012-03-13","2012-04-25","2012-06-20","2012-08-01","2012-09-13","2012-10-24","2012-12-12",
"2013-01-30","2013-03-20","2013-05-01","2013-06-19","2013-07-31","2013-09-18","2013-10-30","2013-12-18",
"2014-01-29","2014-03-19","2014-04-30","2014-06-18","2014-07-30","2014-09-17","2014-10-29","2014-12-17",
"2015-01-28","2015-03-18","2015-04-29","2015-06-17","2015-07-29","2015-09-17","2015-10-28","2015-12-16",
"2016-01-27","2016-03-16","2016-04-27","2016-06-15","2016-07-27","2016-09-21","2016-11-02","2016-12-14",
"2017-02-01","2017-03-15","2017-05-03","2017-06-14","2017-07-26","2017-09-20","2017-11-01","2017-12-13",
"2018-01-31","2018-03-21","2018-05-02","2018-06-13","2018-08-01","2018-09-26","2018-11-08","2018-12-19",
"2019-01-30","2019-03-20","2019-05-01","2019-06-19","2019-07-31","2019-09-18","2019-10-30","2019-12-11",
"2020-01-29","2020-03-15","2020-04-29","2020-06-10","2020-07-29","2020-09-16","2020-11-05","2020-12-16",
"2021-01-27","2021-03-17","2021-04-28","2021-06-16","2021-07-28","2021-09-22","2021-11-03","2021-12-15",
"2022-01-26","2022-03-16","2022-05-04","2022-06-15","2022-07-27","2022-09-21","2022-11-02","2022-12-14",
"2023-02-01","2023-03-22","2023-05-03","2023-06-14","2023-07-26","2023-09-20","2023-11-01","2023-12-13",
"2024-01-31","2024-03-20","2024-05-01","2024-06-12","2024-07-31","2024-09-18","2024-11-07","2024-12-18",
"2025-01-29","2025-03-19","2025-05-07","2025-06-18","2025-07-30","2025-09-17","2025-10-29","2025-12-10",
]
fomc = sorted(pd.Timestamp(d) for d in FOMC)
def even_week(dt):
    prev = [f for f in fomc if f <= dt]
    if not prev: return True
    return ((dt - prev[-1]).days // 7) % 2 == 0
# SPY-leg multiplier series over all trading days: 1.0 even / 0.5 odd (FROZEN)
tdays = closes['SPY'].index
spy_mult = pd.Series({d: (1.0 if even_week(d) else 0.5) for d in tdays})

# ---- tilted multi-speed ensemble sleeve ----
def sleeve_tilted(speeds, tilt_spy=False):
    parts = []
    for k, c in closes.items():
        c = c.astype(float); aret = c.pct_change()
        base = pd.concat([TrendOverlay(s, enabled=True).exposure(c) for s in speeds], axis=1).mean(axis=1)
        pos = base.shift(1)                                   # causal price signal
        if k == 'SPY' and tilt_spy:
            pos = pos * spy_mult.reindex(pos.index).ffill().fillna(1.0)   # causal (FOMC pre-scheduled)
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
print(f"=== T-268 FOMC even-week tilt on SPY leg of the {{2,5,10}}mo ensemble ({base.index[0].date()}..{base.index[-1].date()}) ===")
print(f"even-week share of trading days: {spy_mult.reindex(base.index).eq(1.0).mean()*100:.0f}%")
for nm, r in [('unconditioned ensemble (T-260 spec)', base), ('even-week-tilted SPY leg', tilt)]:
    so, ci, md, cg, tw = stats(r)
    print(f"  {nm:36} Sortino={so:.3f} ci_low={ci:.3f} MaxDD={md*100:.1f}% CAGR={cg*100:.1f}% $10k={tw:,.0f}")
(dslo, dshi), (dwlo, dwhi) = paired(tilt, base)
print(f"\n  paired Δ(tilt − base): ΔSortino 95%CI [{dslo:+.3f},{dshi:+.3f}]  Δwealth(×start) 95%CI [{dwlo:+.3f},{dwhi:+.3f}]")
print("  named windows (CAGR / MaxDD):")
for nm, a, b in [('2015-2018 bull', '2015-01-01', '2018-09-30'), ('COVID-2020', '2020-01-01', '2020-12-31'), ('2022 bear', '2022-01-01', '2022-12-31')]:
    print(f"    {nm:15} base {cagrwin(base,a,b)*100:+.1f}%/{ddwin(base,a,b)*100:.1f}%   tilt {cagrwin(tilt,a,b)*100:+.1f}%/{ddwin(tilt,a,b)*100:.1f}%")
