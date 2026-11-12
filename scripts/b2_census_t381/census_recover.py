# READ-ONLY: could Form 4 ISSUERTRADINGSYMBOL recover tickers for the dead CIKs T-265 never priced?
import pathlib
import re
import sys
import zipfile

import pandas as pd

WT = pathlib.Path(sys.argv[1])
PC = pd.read_parquet(sys.argv[2]).set_index('ticker')
Z = WT / 'data/edgar/insider_zips'
parts = []
for zp in sorted(Z.glob('*_form345.zip')):
    if int(zp.name[:4]) < 2013:
        continue
    z = zipfile.ZipFile(zp)
    with z.open('SUBMISSION.tsv') as f:
        s = pd.read_csv(f, sep='\t', usecols=['FILING_DATE', 'DOCUMENT_TYPE', 'ISSUERCIK', 'ISSUERTRADINGSYMBOL'],
                        dtype=str, quoting=3, on_bad_lines='skip', encoding_errors='replace')
    s = s[s.DOCUMENT_TYPE == '4']
    s['FILING_DATE'] = pd.to_datetime(s['FILING_DATE'], format='%d-%b-%Y', errors='coerce')
    s['ISSUERCIK'] = pd.to_numeric(s['ISSUERCIK'], errors='coerce')
    s['sym'] = s['ISSUERTRADINGSYMBOL'].fillna('').str.upper().str.strip()
    parts.append(s[['ISSUERCIK', 'sym', 'FILING_DATE']])
a = pd.concat(parts, ignore_index=True).dropna(subset=['ISSUERCIK'])
a = a.sort_values('FILING_DATE')
last = a.groupby('ISSUERCIK').agg(sym=('sym', 'last'), last_f4=('FILING_DATE', 'max'))
S = WT / 'data/research/t265'
eps = pd.read_parquet(S / 'eps_panel.parquet', columns=['cik', 'cal_q'])
eps['ord'] = eps['cal_q'].str.slice(0, 4).astype(int) * 4 + eps['cal_q'].str.slice(5).astype(int) - 1
g = eps.groupby('cik')['ord'].max().to_frame('last_ord')
fin = pd.read_parquet(S / 'cik_ticker_final.parquet').drop_duplicates('cik').set_index('cik')
g = g.join(fin)
g['priced'] = g['ticker'].isin(PC.index[PC['n'] >= 60])
dead = g[(g.last_ord >= 2016 * 4) & (g.last_ord <= 2024 * 4 + 3) & ~g.priced]
dead = dead.join(last, how='left')
clean = dead['sym'].fillna('').str.fullmatch(r'[A-Z]{1,5}')
print('ceased-in-window CIKs WITHOUT prices:', len(dead))
print('  with any Form 4 (2013+):', int(dead.sym.notna().sum()))
print('  with a clean [A-Z]{1,5} Form-4 symbol:', int(clean.sum()))
print('  ... of which the symbol is NOT already a T-265 price file:', int((clean & ~dead['sym'].isin(PC.index)).sum()))
print('  ... of which the symbol IS a T-265 file (reused by another CIK / already fetched):',
      int((clean & dead['sym'].isin(PC.index)).sum()))
