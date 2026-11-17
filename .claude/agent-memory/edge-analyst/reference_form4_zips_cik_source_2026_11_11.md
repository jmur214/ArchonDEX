---
name: form4-zips-are-the-cik-source
description: data/insider_sec/ (T-136 flattened Form 4 panel) has NO issuer CIK, owner CIK, 10b5-1 flag or form type — the upstream SEC zips in data/edgar/insider_zips/ have all of them
metadata:
  type: reference
---

- `data/insider_sec/<TICKER>.parquet` (in agent-d's tree only; 6,778,137 rows, filings 2006-01-03 →
  2026-03-31) is keyed by the FILED ticker. It keeps only filing_date, ticker, insider_name/title,
  code, A/D, price, shares, holdings and value. Ticker-joining it mis-joins reused tickers (126 issuer
  CIKs on T-265).
- `data/edgar/insider_zips/YYYYqQ_form345.zip` (main tree, 81 quarters 2006q1–2026q1) has the tables
  SUBMISSION (ISSUERCIK, ISSUERTRADINGSYMBOL, FILING_DATE as a date only, DOCUMENT_TYPE, and AFF10B5ONE
  **from 2023q1 only**), NONDERIV_TRANS (TRANS_CODE, TRANS_ACQUIRED_DISP_CD, TRANS_DATE),
  REPORTINGOWNER (RPTOWNERCIK) and FOOTNOTES (10b5-1 text before 2023).
- Neither source has an acceptance timestamp. Use FILING_DATE + 1 trading day as PIT entry.
- A full scan, one quarter at a time with usecols, takes about 27 s and peaks at 1.1 GB RSS.

How to apply: any CIK-joined insider work reads the zips. See [[t265-panel-not-survivorship-complete]].
