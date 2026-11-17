# READ-ONLY: interior no-trade runs (zero-volume bars OR missing market days) = splice / halt candidates.
import pathlib
import sys

import pandas as pd

WT = pathlib.Path(sys.argv[1])
P = WT / 'data/research/t265/prices'
spy = pd.read_csv(WT / 'data/processed/tr_reconciled/SPY_1d.csv', index_col=0, parse_dates=True)
cal = pd.DatetimeIndex(pd.to_datetime(spy.index).normalize())
cal = cal[cal >= '2016-01-01']
out = []
for f in sorted(P.glob('*.parquet')):
    df = pd.read_parquet(f)
    df.index = pd.to_datetime(df.index).normalize()
    traded = df.index[df['volume'].fillna(0) > 0]
    if len(traded) < 2:
        continue
    life = cal[(cal >= traded[0]) & (cal <= traded[-1])]
    pos = life.searchsorted(traded)
    gaps = pd.Series(pos[1:] - pos[:-1] - 1)      # market days without a trade between trades
    out.append(dict(ticker=f.stem, max_notrade=int(gaps.max()), n_ge21=int((gaps >= 21).sum()),
                    n_ge63=int((gaps >= 63).sum())))
d = pd.DataFrame(out)
d.to_parquet(sys.argv[2])
for g in [5, 10, 21, 63, 252]:
    print(f'tickers with an interior no-trade run >= {g} market days:', int((d.max_notrade >= g).sum()))
print(d.sort_values('max_notrade', ascending=False).head(12).to_string())
