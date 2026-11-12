# READ-ONLY: how much of EDGAR filing-cessation (dead firms) does the T-265 price stage carry?
import pathlib
import sys

import pandas as pd

WT = pathlib.Path(sys.argv[1])
PC = pd.read_parquet(sys.argv[2]).set_index('ticker')
S = WT / 'data/research/t265'
eps = pd.read_parquet(S / 'eps_panel.parquet', columns=['cik', 'cal_q', 'end'])
eps['ord'] = eps['cal_q'].str.slice(0, 4).astype(int) * 4 + eps['cal_q'].str.slice(5).astype(int) - 1
g = eps.groupby('cik').agg(first_ord=('ord', 'min'), last_ord=('ord', 'max'), last_end=('end', 'max'))
g['last_end'] = pd.to_datetime(g['last_end'])
fin = pd.read_parquet(S / 'cik_ticker_final.parquet')
print('EPS-frame CIKs', len(g), '| final map rows', len(fin), 'unique cik', fin.cik.nunique(), 'unique ticker', fin.ticker.nunique())
dup = fin[fin.duplicated('ticker', keep=False)]
print('tickers mapped from >1 CIK:', dup.ticker.nunique(), 'covering', len(dup), 'CIKs')
g = g.join(fin.drop_duplicates('cik').set_index('cik'), how='left')
g['priced'] = g['ticker'].isin(PC.index)
END_ORD = 2026 * 4 + 0      # 2026Q1
# 'ceased' = last EPS frame at or before 2024Q4 AND first frame at/after 2015Q1 not required
g['ceased'] = g['last_ord'] <= 2024 * 4 + 3
g['ceased_year'] = (g['last_ord'] // 4).where(g['ceased'])
# only firms alive inside the window: last frame >= 2016Q1
w = g[g['last_ord'] >= 2016 * 4]
print('CIKs filing inside window (last frame >= 2016Q1):', len(w))
print('  of which ceased (last frame <= 2024Q4):', int(w.ceased.sum()), '| continuing:', int((~w.ceased).sum()))
for lab, sub in [('continuing', w[~w.ceased]), ('ceased', w[w.ceased])]:
    print(f'  {lab}: mapped {sub.ticker.notna().mean():.1%}  priced {sub.priced.mean():.1%}  (n={len(sub)})')
c = w[w.ceased & w.priced].copy()
c['px_last'] = PC.reindex(c['ticker'])['last'].values
c['gap_days'] = (c['px_last'] - c['last_end']).dt.days
print('ceased & priced:', len(c))
print('  price series ends before 2026-06-01:', int((c.px_last < '2026-06-01').sum()))
print('  price series runs to panel end (ticker likely REUSED or firm alive w/o EPS tag):', int((c.px_last >= '2026-06-01').sum()))
print('  |px_last - last_frame_end| <= 270d:', int((c.gap_days.abs() <= 270).sum()))
print('by ceased year: n_ceased, mapped%, priced%, priced-and-terminating')
for y, sub in w[w.ceased].groupby('ceased_year'):
    pt = sub[sub.priced]
    term = (PC.reindex(pt['ticker'])['last'] < '2026-06-01').sum()
    print(f'  {int(y)}: {len(sub):5d}  mapped {sub.ticker.notna().mean():5.1%}  priced {sub.priced.mean():5.1%}  terminating {int(term)}')
