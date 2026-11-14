# READ-ONLY census of the SEC Form 3/4/5 quarterly datasets (the upstream of data/insider_sec/).
# One quarter in memory at a time; only the columns needed. No returns, no signals.
import io
import json
import pathlib
import re
import sys
import zipfile

import pandas as pd

WT = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
Z = WT / 'data/edgar/insider_zips'
RX = re.compile(r'10b5-?1', re.I)


def rd(z, name, cols):
    with z.open(name) as f:
        hdr = f.readline().decode('utf-8', 'replace').rstrip('\n').split('\t')
    use = [c for c in cols if c in hdr]
    with z.open(name) as f:
        return pd.read_csv(f, sep='\t', usecols=use, dtype=str, quoting=3,
                           on_bad_lines='skip', encoding_errors='replace')


per_q = []
p_rows = []
any_issuers_by_year = {}
for zp in sorted(Z.glob('*_form345.zip')):
    q = zp.name[:6]
    z = zipfile.ZipFile(zp)
    sub = rd(z, 'SUBMISSION.tsv', ['ACCESSION_NUMBER', 'FILING_DATE', 'DOCUMENT_TYPE', 'ISSUERCIK',
                                   'ISSUERTRADINGSYMBOL', 'AFF10B5ONE'])
    nd = rd(z, 'NONDERIV_TRANS.tsv', ['ACCESSION_NUMBER', 'SECURITY_TITLE', 'TRANS_DATE', 'TRANS_CODE',
                                      'TRANS_SHARES', 'TRANS_PRICEPERSHARE', 'TRANS_ACQUIRED_DISP_CD'])
    f4 = sub[sub['DOCUMENT_TYPE'] == '4']
    yr = int(q[:4])
    any_issuers_by_year.setdefault(yr, set()).update(f4['ISSUERCIK'].dropna().astype(int).tolist())
    p = nd[(nd['TRANS_CODE'] == 'P') & (nd['TRANS_ACQUIRED_DISP_CD'] == 'A')]
    p = p.merge(sub, on='ACCESSION_NUMBER', how='inner')
    p4 = p[p['DOCUMENT_TYPE'] == '4']
    # 10b5-1 via footnotes (accession-level mention)
    acc = set(p4['ACCESSION_NUMBER'])
    fn_hit = set()
    with z.open('FOOTNOTES.tsv') as f:
        for chunk in pd.read_csv(f, sep='\t', usecols=['ACCESSION_NUMBER', 'FOOTNOTE_TXT'], dtype=str,
                                 quoting=3, on_bad_lines='skip', chunksize=200_000,
                                 encoding_errors='replace'):
            ch = chunk[chunk['ACCESSION_NUMBER'].isin(acc)]
            fn_hit |= set(ch.loc[ch['FOOTNOTE_TXT'].fillna('').str.contains(RX), 'ACCESSION_NUMBER'])
    aff = p4['AFF10B5ONE'] if 'AFF10B5ONE' in p4 else pd.Series(dtype=str)
    per_q.append(dict(q=q, sub_rows=len(sub), form4_subs=int((sub['DOCUMENT_TYPE'] == '4').sum()),
                      nonderiv_rows=len(nd), p_rows_all_forms=len(p), p_rows_form4=len(p4),
                      p_issuers=int(p4['ISSUERCIK'].nunique()),
                      aff_col=('AFF10B5ONE' in sub.columns),
                      aff_true=int(aff.fillna('').str.strip().isin(['1', 'true', 'TRUE', 'Y', 'True']).sum()),
                      aff_values=sorted(aff.fillna('NA').astype(str).unique().tolist())[:6],
                      fn_10b51=int(p4['ACCESSION_NUMBER'].isin(fn_hit).sum()),
                      pref_title=int(p4['SECURITY_TITLE'].fillna('').str.contains('prefer', case=False).sum())))
    p_rows.append(p4[['ISSUERCIK', 'ISSUERTRADINGSYMBOL', 'FILING_DATE']].assign(q=q))
    print(per_q[-1], flush=True)
pq = pd.DataFrame(per_q)
pr = pd.concat(p_rows, ignore_index=True)
pr['ISSUERCIK'] = pd.to_numeric(pr['ISSUERCIK'], errors='coerce')
pr.to_parquet(OUT / 'p_issuers.parquet')
pq.to_json(OUT / 'per_quarter.json', orient='records')
json.dump({str(k): sorted(v) for k, v in any_issuers_by_year.items()}, open(OUT / 'form4_issuers_by_year.json', 'w'))
print('TOTAL nonderiv rows', int(pq.nonderiv_rows.sum()), 'form4 subs', int(pq.form4_subs.sum()),
      'P/A form4 rows', int(pq.p_rows_form4.sum()))
