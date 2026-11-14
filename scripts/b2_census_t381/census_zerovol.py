# READ-ONLY: zero-volume bars and trailing zero-volume runs (phantom post-delisting bars?). No returns.
import pathlib
import sys

import pandas as pd

WT = pathlib.Path(sys.argv[1])
P = WT / 'data/research/t265/prices'
rows = []
for f in sorted(P.glob('*.parquet')):
    df = pd.read_parquet(f)
    v = df['volume'].fillna(0)
    n0 = int((v <= 0).sum())
    pos = v[v > 0]
    last_traded = pos.index.max() if len(pos) else pd.NaT
    trail0 = int((v.index > last_traded).sum()) if len(pos) else len(v)
    # zero-volume bars whose close differs from previous close (would be a 'price move' with no trade)
    c = df['close']
    moves0 = int(((v <= 0) & (c.diff().abs() > 1e-9)).sum())
    rows.append(dict(ticker=f.stem, n=len(df), n_zero_vol=n0, last_bar=df.index.max(),
                     last_traded=last_traded, trailing_zero_vol_bars=trail0, zero_vol_price_moves=moves0))
d = pd.DataFrame(rows)
d.to_parquet(sys.argv[2])
print('total bars', int(d.n.sum()), '| zero-volume bars', int(d.n_zero_vol.sum()),
      f'({d.n_zero_vol.sum() / d.n.sum():.2%})', '| tickers with any', int((d.n_zero_vol > 0).sum()))
print('tickers with a TRAILING zero-volume run >= 5 bars:', int((d.trailing_zero_vol_bars >= 5).sum()),
      '| >= 21:', int((d.trailing_zero_vol_bars >= 21).sum()), '| >= 252:', int((d.trailing_zero_vol_bars >= 252).sum()))
print('zero-volume bars where the close MOVED:', int(d.zero_vol_price_moves.sum()))
lt = d[d.trailing_zero_vol_bars >= 5]
print('last TRADED date year of those:', pd.to_datetime(lt.last_traded).dt.year.value_counts().sort_index().to_dict())
term = d[(pd.to_datetime(d.last_traded) < '2026-06-01')]
print('series whose last TRADED bar < 2026-06-01 (true terminations):', len(term))
print('  by year:', pd.to_datetime(term.last_traded).dt.year.value_counts().sort_index().to_dict())
