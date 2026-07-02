"""T-271 — S&P 500 deletion-reversal event study. Reuses the T-265 SIP path + event machinery.
Pre-registered ONE arm. Deleted names 2016-2025 (SIP floor); IWM size-matched control; factor kill-test."""
import os, pathlib, datetime as dt
import numpy as np, pandas as pd
ROOT = pathlib.Path('/Users/jacksonmurphy/Dev/trading_machine-agent-d')
import sys; sys.path.insert(0, str(ROOT))
CACHE = ROOT / 'data' / 'research' / 't271'; (CACHE / 'prices').mkdir(parents=True, exist_ok=True)

def _creds():
    env = pathlib.Path('/Users/jacksonmurphy/Dev/trading_machine-2/.env')
    for line in env.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ['ALPACA_API_KEY'], os.environ['ALPACA_SECRET_KEY']

def _nw_t(x, lags=None):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    if n < 5: return float('nan')
    mu = x.mean(); e = x - mu
    if lags is None: lags = max(1, int(n ** 0.25))
    var = (e @ e) / n
    for L in range(1, lags + 1):
        var += 2 * (1 - L / (lags + 1)) * (e[L:] @ e[:-L]) / n
    se = np.sqrt(var / n); return mu / se if se > 1e-12 else float('nan')

# ---- deletion events ----
mem = pd.read_parquet(ROOT / 'data' / 'universe' / 'sp500_membership_pit.parquet')
mem['end'] = pd.to_datetime(mem['end'])
dels = mem.dropna(subset=['end'])
dels = dels[(dels['end'] >= '2016-01-01') & (dels['end'] <= '2025-06-30')][['ticker', 'end']].reset_index(drop=True)
print(f"[t271] deletion events 2016-2025: {len(dels)} ({dels['ticker'].nunique()} unique tickers)")

# ---- SIP prices (deleted names + SPY + IWM) ----
def fetch_prices(syms):
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    import re
    KEY, SEC = _creds(); dc = StockHistoricalDataClient(KEY, SEC)
    outdir = CACHE / 'prices'; done = {p.stem for p in outdir.glob('*.parquet')}
    syms = [s for s in syms if re.fullmatch(r'[A-Z]{1,5}', str(s)) and s not in done]
    B = 150
    for i in range(0, len(syms), B):
        batch = syms[i:i + B]
        def _f(bb):
            req = StockBarsRequest(symbol_or_symbols=bb, timeframe=TimeFrame.Day,
                                   start=dt.datetime(2016, 1, 1), end=dt.datetime(2026, 7, 1), feed='sip', adjustment='all')
            return dc.get_stock_bars(req).df
        try:
            df = _f(batch)
        except Exception as e:
            m = re.search(r'invalid symbol:\s*([A-Z0-9.\-]+)', str(e))
            if m and m.group(1) in batch:
                batch = [s for s in batch if s != m.group(1)]
                try: df = _f(batch)
                except Exception: continue
            else: continue
        if df is None or len(df) == 0: continue
        for sym, g in df.groupby(level=0):
            g = g.reset_index(level=0, drop=True)[['close']]; g.index = pd.to_datetime(g.index).tz_localize(None).normalize()
            g.to_parquet(outdir / f"{sym}.parquet")

need = sorted(set(dels['ticker']) | {'SPY', 'IWM'})
fetch_prices(need)
def load(sym):
    p = CACHE / 'prices' / f"{sym}.parquet"
    if p.exists():
        s = pd.read_parquet(p)['close'].dropna(); s.index = pd.to_datetime(s.index); return s.sort_index()
    return None
spy = load('SPY'); iwm = load('IWM')
spy_ret = spy.pct_change(); iwm_ret = iwm.pct_change()
print(f"[t271] SPY bars {len(spy)}, IWM bars {len(iwm) if iwm is not None else 0}")

# ---- classify + CAR ----
HOR = {'1mo': 21, '3mo': 63, '6mo': 126, '12mo': 252}
def build(ENTRY):
    rows = []; n_priced = n_survivor = 0
    for _, e in dels.iterrows():
        s = load(e['ticker'])
        if s is None or len(s) < 30: continue
        n_priced += 1
        end = e['end']; pos = s.index.searchsorted(end); post = len(s) - pos
        if post < 126 + ENTRY:                # need ~6mo of trading after effective date
            rows.append(dict(ticker=e['ticker'], end=end, survivor=False)); continue
        n_survivor += 1; entry = pos + ENTRY
        rec = dict(ticker=e['ticker'], end=end, survivor=True, entry_month=pd.Timestamp(end).to_period('M'))
        for name, h in HOR.items():
            if entry + h >= len(s): rec[f'car_mkt_{name}'] = np.nan; rec[f'car_iwm_{name}'] = np.nan; continue
            seg = s.iloc[entry:entry + h + 1].pct_change().dropna()
            rec[f'car_mkt_{name}'] = float((seg - spy_ret.reindex(seg.index)).sum())
            rec[f'car_iwm_{name}'] = float((seg - iwm_ret.reindex(seg.index)).sum())
        rows.append(rec)
    return pd.DataFrame(rows), n_priced, n_survivor
ENTRY = 5
ev, n_priced, n_survivor = build(ENTRY)
surv = ev[ev['survivor']].copy()
print(f"[t271] priced {n_priced}/{len(dels)} deletions; SURVIVOR (>=6mo post, tradeable rule-like) = {n_survivor}; "
      f"M&A/delist (excluded) = {n_priced - n_survivor}")

def table(df, label):
    print(f"\n=== {label} (n={len(df)}) — mean post-deletion CAR (entry = effective +{ENTRY}td) ===")
    print(f"  {'horizon':8} {'CAR_mkt':>9} {'t_HAC':>7}   {'CAR_iwm':>9} {'t_HAC':>7}   n")
    for name in HOR:
        mk = df[f'car_mkt_{name}'].dropna(); iw = df[f'car_iwm_{name}'].dropna()
        mm = df.dropna(subset=[f'car_mkt_{name}']).groupby('entry_month')[f'car_mkt_{name}'].mean()
        mi = df.dropna(subset=[f'car_iwm_{name}']).groupby('entry_month')[f'car_iwm_{name}'].mean()
        print(f"  {name:8} {mk.mean()*100:>8.1f}% {_nw_t(mm.values):>7.2f}   {iw.mean()*100:>8.1f}% {_nw_t(mi.values):>7.2f}   {len(iw)}")

table(surv, 'ALL rule-deletions (survivors) 2016-2025')
table(surv[surv['end'] < '2020-01-01'], 'era 2016-2019')
table(surv[surv['end'] >= '2020-01-01'], 'era 2020-2025')
# robustness: entry at effective +1 (capture any immediate post-forced-selling bounce)
ev1, _, _ = build(1)
table(ev1[ev1['survivor']], 'ROBUSTNESS: entry = effective +1td (all survivors)')

# ---- factor kill-test: rolling long-only 6mo-hold deletion portfolio, daily returns -> FF5+Mom alpha ----
holdings = {}   # date -> list of (ticker, series)
port_ret = {}
# build a daily active-set: each survivor contributes from entry to entry+126
active = []
for _, e in surv.iterrows():
    s = load(e['ticker']); pos = s.index.searchsorted(e['end']); entry = pos + ENTRY
    end_i = min(entry + 126, len(s) - 1)
    r = s.iloc[entry:end_i + 1].pct_change().dropna()
    active.append(r.rename(e['ticker']))
if active:
    P = pd.concat(active, axis=1)
    daily = P.mean(axis=1).dropna()      # equal-weight active holdings each day
    print(f"\n[t271] rolling deletion-portfolio daily series: {len(daily)} days, "
          f"{daily.index.min().date()}..{daily.index.max().date()}")
    try:
        from core.factor_decomposition import regress_returns_on_factors, load_factor_data
        fac = load_factor_data()
        dec = regress_returns_on_factors(daily, fac, edge_name='deletion_reversal')
        print(f"[t271] FACTOR KILL-TEST (FF5+Mom): alpha_ann={dec.alpha_annualized*100:+.1f}% "
              f"t_HAC={dec.alpha_tstat:+.2f}  R2={dec.r_squared:.2f}")
        print(f"        betas: " + ", ".join(f"{k}={v:+.2f}" for k, v in dec.betas.items()))
    except Exception as ex:
        print(f"[t271] factor kill-test skipped: {str(ex)[:80]}")
