# READ-ONLY: in-band ($1M-$200M 20d median dollar ADV) month-end universe and the terminations
# (last TRADED bar; a >=63-market-day no-trade run ends a segment) inside the following month.
import pathlib
import sys

import numpy as np
import pandas as pd

WT = pathlib.Path(sys.argv[1])
P = WT / 'data/research/t265/prices'
spy = pd.read_csv(WT / 'data/processed/tr_reconciled/SPY_1d.csv', index_col=0, parse_dates=True)
cal = pd.DatetimeIndex(pd.to_datetime(spy.index).normalize())
cal = cal[(cal >= '2016-01-01')]
me = pd.DatetimeIndex(pd.Series(cal, index=cal).groupby(cal.to_period('M')).max().values)
me = me[me <= '2026-04-30']
inband = pd.Series(0, index=me)
deaths = pd.Series(0, index=me)
deaths_last_lt1 = pd.Series(0, index=me)
SPLICE = 63
for f in sorted(P.glob('*.parquet')):
    df = pd.read_parquet(f)
    df.index = pd.to_datetime(df.index).normalize()
    df = df[~df.index.duplicated(keep='last')]
    tr = df[df['volume'].fillna(0) > 0]
    if len(tr) < 20:
        continue
    pos = cal.searchsorted(tr.index)
    brk = np.where(np.diff(pos) - 1 >= SPLICE)[0]
    seg_ends = [tr.index[i] for i in brk] + [tr.index[-1]]
    seg_starts = [tr.index[0]] + [tr.index[i + 1] for i in brk]
    for s0, s1 in zip(seg_starts, seg_ends):
        life = cal[(cal >= s0) & (cal <= s1)]
        if len(life) < 20:
            continue
        seg = tr.loc[s0:s1]
        dv = (seg['close'] * seg['volume']).reindex(life).fillna(0.0)
        med = dv.rolling(20, min_periods=20).median().reindex(me)
        ib = (med >= 1e6) & (med < 2e8)
        inband += ib.astype(int).values
        dead = s1 < pd.Timestamp('2026-05-01')            # segment ends before the window end
        if dead:
            k = me.searchsorted(s1) - 1                   # month-end strictly before the death
            if 0 <= k < len(me) and bool(ib.iloc[k]):
                deaths.iloc[k] += 1
                if float(seg['close'].iloc[-1]) < 1.0:
                    deaths_last_lt1.iloc[k] += 1
y = pd.DataFrame({'inband_mean': inband.groupby(inband.index.year).mean(),
                  'deaths_next_month': deaths.groupby(deaths.index.year).sum(),
                  'of_which_last_close_lt1': deaths_last_lt1.groupby(deaths.index.year).sum()})
y['annual_death_rate'] = y['deaths_next_month'] / y['inband_mean']
print(y.round(3).to_string())
print('TOTAL in-band deaths:', int(deaths.sum()), '| mean in-band names:', round(float(inband.mean()), 0))
pd.DataFrame({'inband': inband, 'deaths': deaths}).to_csv(sys.argv[2])
