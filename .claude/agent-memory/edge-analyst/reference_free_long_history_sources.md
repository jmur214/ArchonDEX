---
name: reference-free-long-history-sources
description: Where free century-long return data lives (Shiller ie_data.xls, French daily, JST R6, FRED API, Schwab SIP brochure/sweep rate) and which repo copies are insufficient
metadata:
  type: reference
---

Probed 2026-11-19 with a generic User-Agent.

**Return data**
- **Shiller `ie_data.xls`**: linked from `shillerdata.com` and hosted on img1.wsimg.com; scrape the href, because the URL carries a version token.
  - Covers 1871-01 → present: P, D, E, CPI, GS10, real TR price, monthly total bond returns, CAPE. Read it with xlrd.
  - The repo copy `data/macro/shiller_ie_data.csv` lacks CPI and GS10 and ends 2024-09, so it is insufficient.
- **Ken French library**: `mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/<name>_CSV.zip`.
  - Daily factors run from 1926-07-01, CRSP vintage 202609.
  - Developed and Developed-ex-US monthly start 1990-07.
- **JST Macrohistory R6**: the `macrohistory.net/database/` page links `/app/download/.../JSTdatasetR6.xlsx`.
  - Annual 1870–2020, 18 countries; 16 carry `eq_tr` and `bill_rate` (not CAN or IRL).
  - Includes `gdp` and `xrusd` for USD weighting. Citation required.
- **FRED**: the keyless `fredgraph.csv` failed again on 2026-11-19. The API works with FRED_API_KEY read from the main repo `.env`, never printed.
  - CPIAUCNS from 1913, DTB3 from 1954, SOFR from 2018-04-03.

**Robo facts**
- **Schwab SIP disclosure brochure**: `disclosures.schwab.com/SchwabDashboard/63969/REG83246.pdf`; cash range on p.13, fees on pp.8–9.
  - No PDF renderer is installed (no pdftoppm), but `pypdf` is, so extract text with it.
- **Sweep rate**: `schwab.com/legal/sip-sweep-current-interest-rates`.
- **Vanguard TDF glide numbers**: the page is JS-rendered; use the prospectus.

**Tax and broker rules (read 2026-11-19)**
- **IRS inflation parameters**: `irs.gov/pub/irs-drop/rp-25-32.pdf` (2026) and `rp-26-35.pdf` (2027). §3.03 holds the 0 % / 15 % long-term-gain thresholds; extract with pypdf.
- **Schwab futures FAQ** (`schwab.com/futures/faqs`) is static and readable.
- **Schwab margin-rate table** (`/margin-rates`) is script-rendered and unreadable by curl.

See [[reference-fomc-surprise-sources]], [[project-t409-real-money-home-2026-11-19]].
