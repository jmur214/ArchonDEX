# READ-ONLY universe census: month-end counts by 20-day median dollar-ADV band. No returns.
import pathlib
import sys

import numpy as np
import pandas as pd

WT = pathlib.Path(sys.argv[1])
P = WT / 'data/research/t265/prices'
spy = pd.read_csv(WT / 'data/processed/tr_reconciled/SPY_1d.csv', index_col=0, parse_dates=True)
cal = pd.DatetimeIndex(pd.to_datetime(spy.index).normalize())
cal = cal[(cal >= '2016-01-01') & (cal <= '2026-05-22')]
me = pd.Series(cal, index=cal).groupby(cal.to_period('M')).max()
me_idx = pd.DatetimeIndex(me.values)
bands = {'lt1M': (0, 1e6), '1-20M': (1e6, 2e7), '20-200M': (2e7, 2e8), 'ge200M': (2e8, np.inf)}
cnt = pd.DataFrame(0, index=me_idx, columns=list(bands) + ['ends_next_month_in_band'])
for f in sorted(P.glob('*.parquet')):
    df = pd.read_parquet(f)
    df.index = pd.to_datetime(df.index).normalize()
    df = df[~df.index.duplicated(keep='last')]
    first, last = df.index.min(), df.index.max()
    life = cal[(cal >= first) & (cal <= last)]
    if len(life) < 20:
        continue
    dv = (df['close'] * df['volume']).reindex(life).fillna(0.0)
    med = dv.rolling(20, min_periods=20).median()
    m = med.reindex(me_idx)                      # NaN outside life
    for b, (lo, hi) in bands.items():
        cnt[b] += ((m >= lo) & (m < hi)).astype(int)
    # in-band at month-end t and the series ends within the following calendar month
    inb = (m >= 1e6) & (m < 2e8)
    nxt = me_idx.shift(1, freq='MS') if False else None
    for i in range(len(me_idx) - 1):
        if bool(inb.iloc[i]) and me_idx[i] < last <= me_idx[i + 1] and last < pd.Timestamp('2026-05-01'):
            cnt.iloc[i, cnt.columns.get_loc('ends_next_month_in_band')] += 1
cnt.to_csv(sys.argv[2])
yr = cnt.groupby(cnt.index.year).agg({'lt1M': 'mean', '1-20M': 'mean', '20-200M': 'mean', 'ge200M': 'mean',
                                       'ends_next_month_in_band': 'sum'})
print(yr.round(0).astype(int).to_string())
print('first 3 month-ends:\n', cnt.head(3).to_string())
print('last 3 month-ends:\n', cnt.tail(3).to_string())
