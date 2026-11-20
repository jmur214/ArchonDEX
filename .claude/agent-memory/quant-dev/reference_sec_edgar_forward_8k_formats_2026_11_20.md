---
name: sec-edgar-forward-8k-formats
description: EDGAR endpoint shapes verified live for the forward 8-K feed (daily form index, submissions JSON, company_tickers, body) and their timing — what a daily fetch can and cannot see at 09:00 ET
metadata:
  type: reference
---

Verified against real SEC responses on 2026-11-20 (SEC hosts only, the archiver's SEC user agent):

- Daily form index `https://www.sec.gov/Archives/edgar/daily-index/<YYYY>/QTR<q>/form.<YYYYMMDD>.idx`:
  fixed-width lines `FORM  COMPANY NAME...  CIK  DATE  edgar/data/<cik>/<accession>.txt`; split on
  whitespace and read from the END (company names contain spaces). Form "8-K" exact excludes 8-K/A. The
  index for day D is NOT available during D (404 at 15:53 ET); a 09:00 ET run sees D-1. Filings accepted
  after ~17:30 ET carry the next business day's date.
- `https://data.sec.gov/submissions/CIK##########.json` → `filings.recent` parallel arrays:
  `accessionNumber`, `filingDate`, `acceptanceDateTime` ("…T16:05:00.000Z"), `form`, `items` ("2.02,9.01"),
  `primaryDocument`. ~1 s per request including download (large filers' JSON is hundreds of KB).
- `https://www.sec.gov/files/company_tickers.json` (~870 KB): `{"0": {"cik_str", "ticker", "title"}}`;
  share classes spelled with "-" (BRK-B) where the membership file and Alpaca use "." (BRK.B).
- 8-K body = `Archives/edgar/data/<cik>/<acc-no-dashes>/<primaryDocument>`: the COVER page (~3k chars),
  not the Exhibit 99.1 press release.

Use when building or debugging any EDGAR forward feed; the code lives in `scripts/archive_altdata_t136.py`
(`pull_8k_items`) — read it with the Read tool, the privacy plugin refuses Bash that names it.
See [[t412-information-reaches-desks]].
