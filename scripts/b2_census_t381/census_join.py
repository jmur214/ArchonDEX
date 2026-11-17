# READ-ONLY join census: Form 4 open-market purchases <-> T-265 by CIK vs by ticker.
import json
import pathlib
import sys

import pandas as pd

WT = pathlib.Path(sys.argv[1])
F4 = pathlib.Path(sys.argv[2])
PC = pd.read_parquet(sys.argv[3]).set_index('ticker')
fin = pd.read_parquet(WT / 'data/research/t265/cik_ticker_final.parquet')
priced = set(PC.index[PC['n'] >= 60])
fin['priced'] = fin['ticker'].isin(priced)
cik_priced = set(fin.loc[fin.priced, 'cik'])
cik_mapped = set(fin['cik'])
t2c = fin[fin.priced].groupby('ticker')['cik'].apply(set).to_dict()

p = pd.read_parquet(F4 / 'p_issuers.parquet')
p['FILING_DATE'] = pd.to_datetime(p['FILING_DATE'], format='%d-%b-%Y', errors='coerce')
p = p[(p.FILING_DATE >= '2016-01-01') & (p.FILING_DATE <= '2025-12-31')]
p['sym'] = p['ISSUERTRADINGSYMBOL'].fillna('').str.upper().str.strip().str.replace('.', '-', regex=False)
print('P/A Form-4 rows filed 2016-01..2025-12:', len(p), '| issuer CIKs:', p.ISSUERCIK.nunique())
print('  bad FILING_DATE parse:', int(p.FILING_DATE.isna().sum()))
iss = p.groupby('ISSUERCIK').agg(n=('sym', 'size'), sym=('sym', lambda s: s.value_counts().index[0]))
in_map = iss.index.isin(cik_mapped)
in_pr = iss.index.isin(cik_priced)
print(f'CIK join: issuer CIKs in T-265 map {in_map.mean():.1%}; in T-265 PRICED {in_pr.mean():.1%} '
      f'(rows covered {iss.n[in_pr].sum() / iss.n.sum():.1%})')
# ticker join (the insider_sec way): issuer symbol as filed == a priced T-265 ticker
tick_hit = iss['sym'].isin(priced)
print(f'TICKER join: issuer CIKs whose filed symbol is a priced T-265 ticker {tick_hit.mean():.1%} '
      f'(rows {iss.n[tick_hit].sum() / iss.n.sum():.1%})')
# disagreement: ticker join hits but the ticker belongs to a DIFFERENT CIK in T-265 (reuse / mis-map)
wrong = [(c, s) for c, s in iss['sym'].items() if s in t2c and c not in t2c[s]]
print('ticker-join rows whose T-265 ticker maps to a DIFFERENT CIK (would be mis-joined):', len(wrong))
both = (in_pr & tick_hit).sum(); only_cik = (in_pr & ~tick_hit).sum(); only_t = (~in_pr & tick_hit).sum()
print(f'issuer CIKs: both {both}, CIK-only {only_cik}, ticker-only {only_t}')
# share of the priced T-265 universe with ANY Form 4 / ANY P buy, by year
iby = json.load(open(F4 / 'form4_issuers_by_year.json'))
pby = p.groupby(p.FILING_DATE.dt.year)['ISSUERCIK'].apply(lambda s: set(s.dropna().astype(int)))
alive = PC[PC['n'] >= 60]
print('year | priced T-265 names alive | with any Form 4 | with any P buy')
for y in range(2016, 2026):
    a = alive[(alive['first'] <= f'{y}-12-31') & (alive['last'] >= f'{y}-01-01')].index
    ciks = set().union(*[t2c.get(t, set()) for t in a])
    any4 = len(ciks & set(iby.get(str(y), [])))
    anyp = len(ciks & pby.get(y, set()))
    print(f'  {y} | {len(a)} names ({len(ciks)} CIKs) | {any4} ({any4 / max(len(ciks), 1):.0%}) | {anyp} ({anyp / max(len(ciks), 1):.0%})')
