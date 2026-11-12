# READ-ONLY census of the T-265 price stage: no returns, no signals.
import pathlib
import sys

import numpy as np
import pandas as pd

WT = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
P = WT / 'data/research/t265/prices'
spy = pd.read_csv(WT / 'data/processed/tr_reconciled/SPY_1d.csv', index_col=0, parse_dates=True)
cal = pd.to_datetime(spy.index).normalize()
cal = cal[(cal >= '2016-01-01')]
rows = []
for f in sorted(P.glob('*.parquet')):
    df = pd.read_parquet(f)
    c = df['close'].dropna()
    if len(c) == 0:
        rows.append(dict(ticker=f.stem, n=0))
        continue
    idx = pd.to_datetime(c.index).normalize()
    first, last = idx[0], idx[-1]
    span = cal[(cal >= first) & (cal <= last)]
    present = pd.Series(span.isin(idx), index=span)
    miss = (~present).astype(int)
    runs = int(miss.groupby((miss == 0).cumsum()).sum().max()) if len(miss) else 0
    dv = (df['close'] * df['volume']).dropna()
    rows.append(dict(ticker=f.stem, n=len(c), first=first, last=last,
                     frac_present=float(present.mean()) if len(span) else np.nan,
                     max_gap_days=runs, last_close=float(c.iloc[-1]),
                     min_close=float(c.min()), n_nonpos=int((c <= 0).sum()),
                     med_dv_last60=float(dv.iloc[-60:].median()) if len(dv) else np.nan))
d = pd.DataFrame(rows)
d.to_parquet(OUT)
print('files', len(d), 'empty', int((d.n == 0).sum()), 'n<60', int((d.n < 60).sum()))
print('first date min/median/max', d['first'].min(), d['first'].median(), d['first'].max())
print('last date min/max', d['last'].min(), d['last'].max())
print('start on/before 2016-01-05:', int((d['first'] <= '2016-01-05').sum()))
print('last bar >= 2026-06-26 (alive at panel end):', int((d['last'] >= '2026-06-26').sum()))
eb = d[d['last'] < '2026-06-01']
print('series terminating before 2026-06-01:', len(eb))
print('  by year:', eb['last'].dt.year.value_counts().sort_index().to_dict())
print('max_gap_days quantiles:', d.max_gap_days.quantile([.5, .9, .99, 1]).to_dict())
for g in [10, 21, 63, 126, 252]:
    print(f'  max internal gap > {g} market days:', int((d.max_gap_days > g).sum()))
print('files with a nonpositive close:', int((d.n_nonpos > 0).sum()))
print('terminating series last close: <$1', int((eb.last_close < 1).sum()),
      '$1-5', int(((eb.last_close >= 1) & (eb.last_close < 5)).sum()),
      '>=$5', int((eb.last_close >= 5).sum()))
