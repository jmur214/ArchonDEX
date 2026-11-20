---
name: reference-fomc-surprise-sources
description: Free sources for FOMC target changes and monetary-policy surprises (SF Fed Bauer-Swanson workbook, Fed open-market tables, FRED ids) and the 2026-11-19 FRED keyless-CSV outage
metadata:
  type: reference
---

**Monetary-policy surprises.** SF Fed "Monetary Policy Surprises" page, workbook `wp-content/uploads/monetary-policy-surprises-data.xlsx` (Bauer–Swanson; the update of 2024-10-11 runs to 2023-12).
- One row per FOMC announcement from 1988-02, with an `Unscheduled` flag (0 = the first announcement after a scheduled meeting).
- 30-minute FF1/FF2 changes **only from 2010**; ED1–ED4 (SOFR from 2023), Treasury futures and MPS throughout.
- No free 30-minute series after 2023. A one-day Kuttner surprise needs Yahoo ZQ=F (T-295, from 2016-07); its month-end events need the next-month contract, which Yahoo delists.

**Target changes.**
- federalreserve.gov `monetarypolicy/openmarket.htm` (2003→) and `openmarket_archive.htm` (1990–2002). These list effective dates: from 2015, the announcement date + 1.
- FRED DFEDTAR (1982-09-27 → 2008-12-15) and DFEDTARU/DFEDTARL (2008-12-16 →).
- Meeting vs conference call: `fomchistorical<year>.htm`.

**Repo calendar defect.** `config/fomc_calendar.json` includes 1994-04-18, which was a conference call.

**FRED outage (2026-11-19).** `fred.stlouisfed.org/graph/fredgraph.csv` timed out from this machine with both generic and Mozilla UAs. `api.stlouisfed.org` worked, with FRED_API_KEY read from the main repo `.env` without printing it.

See [[project-t408-post-fomc-drift-2026-11-19]].
