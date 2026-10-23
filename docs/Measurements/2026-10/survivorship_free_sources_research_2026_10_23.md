> **Point-in-time external research report (`[NN-AUDITS-NOT-CURRENT]`), 2026-10-23.** Produced by a separate research agent from the brief in the director's session; placed here by the director, unedited below this line. Measured against the brief's sample names, NOT against `docs/Sources/wanted_names_survivorship_gap_2026_10_23.csv` (the agent did not have the file), so every per-name result is on the sample. The director's reading and the decision it leaves are in CURRENT_STATE's 2026-10-23 block.

# Survivorship-free daily prices for delisted S&P 500 names (2000 to 2025): free, one-time and subscription sources compared

No free and legal source fully covers the delisted S&P 500 names that the target list needs. The best free dataset is the frozen Quandl/Nasdaq Data Link WIKI archive.\[1\]\[2\] In a 25-name P1 sample it served 3 names in full and 11 in part, and it lacked all 11 names that left the index in 2000 to 2010 (Enron through Sun Microsystems).\[3\] The cheapest verified paid fallback that covers all of requirements 1 to 4 is Sharadar Prices, Full History, at $39/month or $299/year (personal-use license).\[4\] Before paying for anything, though, the requester should ask UNL Libraries whether a College of Law staff member can get a WRDS account. UNL subscribes to WRDS,\[5\] and CRSP is the reference dataset for this exact problem.\[5\]\[6\]

## TL;DR
- **Free path (partial):** WIKI (Kaggle mirror of the frozen file, 1962-01-02 to 2018-03-27) covered 14 of 25 P1 sample names (3 fully, 11 partially) and 8 of 16 checked P2 names, but none of the 2000 to 2010 departures, and it keys only on ticker. Tiingo free (500 symbols/month) may fill post-2015 non-recycled names but is unmeasured. Overall the free path cannot recover most of the 235 P1 names that left in the 2000s.
- **Best no-cost route if eligible:** CRSP via WRDS. UNL Libraries lists WRDS among its subscribed resources, and the UNL College of Business advertises WRDS access. Whether College of Law staff qualify is unverified and must be confirmed with UNL Libraries (ask-a-question@unl.edu, 402-472-9568).
- **Best paid fallback:** Sharadar Prices Full History ($39/month or $299/year, verified on sharadar.com/subscribe on 2026-10-23).\[4\] It has history from December 1997, split, dividend and spinoff adjusted `closeadj`, a corporate actions table with delist reasons, a permaticker plus CUSIPs and FIGI, fund prices, and bulk/API delivery with no Windows client. Norgate Platinum ($630/year, verified) is the alternative if you need history back to 1990, but it requires the Windows updater. Per-name coverage of both is unmeasured.

## Key Findings

1. **WIKI is the only free source whose per-name coverage could be checked from public pages.** A public ticker list of the WIKI flat file (a GitHub gist by Aaron Hoffman, snapshot of 3,194 symbols as of 2017-11-06) shows a clear survivorship pattern.\[7\] Names that died before about 2014 are absent. Names that died between 2014 and 2018 are present with full history. Names still alive in 2018 are cut off at the 2018 freeze.\[3\]
2. **WIKI fails the P2 identity test by design.** It files history under the ticker alone. CCE in WIKI runs from 1986-11-24 under one symbol, even though at least two different Coca-Cola Enterprises entities traded as CCE in that period.\[3\] "WM" in WIKI is very likely Waste Management, not Washington Mutual (an inference; the list does not state the company).
3. **Alpha Vantage's free tier cannot deliver deep history at all.** Its documentation states that `outputsize=full` (the 25+ year series) on TIME_SERIES_DAILY "is available to premium keys"; free keys get the latest 100 data points.\[8\] The documentation does not state whether delisted symbols return time series. A third-party wrapper of the LISTING_STATUS endpoint reproduces the documentation text that "any YYYY-MM-DD date later than 2010-01-01 is supported", so point-in-time delisted lists do not reach back to 2000.\[9\]
4. **Tiingo's free tier is the most promising free supplement for post-2015 deaths, but it is unmeasured.** Tiingo's symbology documentation says it "supports delisted data for tickers that have not yet been recycled".\[10\] A Tiingo staff reply on the AmiBroker forum (2021) said delisted data runs from "approx. 2015 onward" and that a permaticker system exists for recycled tickers.\[11\] The free Starter plan allows 500 unique symbols per month.\[12\]
5. **Paid sources with documented delisted coverage and an identity key exist at low cost.** Sharadar documents a permaticker, CUSIPs, composite FIGI, first and last price dates, delisting dates and delist reasons.\[13\]\[14\] Norgate documents a -YYYYMM suffix on delisted symbols.\[15\]\[16\] FirstRate Data publishes ticker lists with a "-DELISTED" suffix and says its daily data covers 16,327 tickers, including over 7,000 delisted, starting January 2000.\[17\]\[18\] None of these could be sampled without paying.
6. **The brief's P2 count is inconsistent.** It says 17 names but lists 24 (10 with a later entity on the ticker, 7 reused or mixed, 7 relisted in 2026). 10 + 7 = 17, so the number "17" appears to count only the first two groups. All 24 are reported below.

## Details

### 1. Comparison table (one row per source)

All URLs and prices were read on 2026-10-23. "Unmeasured" means no per-name check was possible from public pages without an account, an API call or a purchase.

| Source | Delisted coverage measured (sample) | History start | Adjustment | Event tables | Identity key (P2 result) | ETFs | Fundamentals | Delivery | License for personal research | Price (status) | URL |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Quandl/Nasdaq Data Link WIKI (frozen 2018; Kaggle mirror) | P1 sample n=25: 3 full, 11 partial, 11 absent. P2: 16 of 24 checked: 4 full, 3 partial, 1 present but wrong/mixed entity, 8 absent; 8 unmeasured | 1962-01-02 (file min); per name varies | Raw plus adjusted columns; dividend and split fields present; adjustment formula not verified | Dividend and split columns per row | Ticker only; fails P2 (CCE mixed, WM ambiguous) | Not verified | No | Bulk CSV (Kaggle, 1.8 GB); Nasdaq Data Link API with key (current availability not confirmed) | Described as public domain by Nasdaq and Kaggle mirror | Free (verified as free on Kaggle; Nasdaq page requires login to view pricing) | data.nasdaq.com/databases/WIKIP; kaggle.com/datasets/marketneutral/quandl-wiki-prices-us-equites\[1\]\[19\]\[20\] |
| Alpha Vantage free | Unmeasured (API call needed) | 25+ years claimed, but full output is premium-only | Daily Adjusted endpoint lists split/dividend adjustments | Dividends and Splits endpoints exist | Ticker; LISTING_STATUS gives ipoDate, delistingDate | Yes (stocks and ETFs) | Yes (statements) | REST API | Not verified | Free key: 100 points per series; 25 requests/day. Premium from $49.99/month (75 requests/minute) to $249.99/month (1,200/minute), per third-party Macroption page; vendor premium page not fetched | alphavantage.co/documentation; macroption.com/alpha-vantage-api-limits |
| Tiingo free (Starter) | Unmeasured (API key needed) | 30+ years claimed; delisted approx. 2015 onward (staff forum post) | Not verified for this report | Splits endpoint (beta); dividends not verified | permaTicker (documented for fundamentals; search endpoint calls it a "placeholder") | Yes | 5 years on free tier | REST API | Not verified | $0; 500 unique symbols/month, 50 requests/hour, 1,000/day (Tiingo blog) | tiingo.com/documentation/appendix/symbology; tiingo.com/about/pricing\[11\]\[12\]\[21\]\[22\]\[23\]\[24\] |
| EODHD free | Unmeasured; free tier is 1 year of history, so cannot test depth | 1 year (free) | Adjusted close; dividends and splits API | Yes | Delisted list via `delisted=1`; reused tickers marked "_old" (third-party article, unverified) | Yes | No (free) | REST API | Personal plans | $0, 20 calls/day (verified) | eodhd.com/pricing\[25\]\[26\]\[27\] |
| Massive (ex-Polygon) free | Unmeasured. Vendor marketing claims "32,345+ active and delisted tickers" and gives TWTR as an example ("Delisted 2013 → 2022"); this does not measure coverage | 2 years on free tier (third-party pages); vendor says "every tick since 2003" | Not verified | Corporate actions listed on free tier | Ticker reference includes delisted tickers and returns composite_figi and share_class_figi (vendor page); P2 untested | Not verified | No (free) | REST, flat files on paid | Not verified | $0 (5 requests/min, no credit card); Stocks Starter $29/month, Developer $79/month, Advanced $199/month (vendor page, read 2026-10-23) | massive.com/stocks |
| Stooq bulk archive | Unmeasured (requires bulk download) | Varies | Public feeds lack corporate actions (third-party) | No | Ticker with .US suffix | Yes | No | Bulk zip | Not verified | Free (unverified) | quantstart.com article on Stooq\[28\]\[29\] |
| CRSP via WRDS (UNL) | Unmeasured (requires WRDS account) | 1925/1926 (other universities' guides) | Returns with and without dividends (CRSP standard; not verified here) | Yes (distributions, delisting) | PERMNO/PERMCO, CUSIP | Yes | Via Compustat if subscribed | Web query, cloud, Python | Academic subscription terms; personal use not verified | No cost to eligible users; eligibility of College of Law staff unverified | libanswers.unl.edu/faq/339059\[5\]\[30\] |
| Sharadar Prices / Bundle | Unmeasured (paid) | December 1997 (prices); June 1990 (tickers table) | Unadjusted, split-adjusted, and split+dividend+spinoff `closeadj` | `actions` table: splits, dividends, spinoffs, delisting dates, delist reasons, ticker changes | permaticker, CUSIPs, composite FIGI | Yes (`funds`, 10,000 tickers) | Bundle only (`fundamentals`, from 1998 per Sharadar) | API and bulk download | Personal Use License | Prices Full History $39/mo or $299/yr; Bundle Full History $69/mo or $499/yr (verified) | sharadar.com/prices; sharadar.com/subscribe\[4\]\[13\]\[14\] |
| Norgate US Stocks Platinum | Unmeasured (trial shows only recent bars per brief) | Delisted back to 1990 | Not verified in this pass | Dividends, capital events | Delisted suffix -YYYYMM, assetid | Yes | Current fundamentals only | Norgate Data Updater plus Python package | EULA; deletion after subscription end reported by a third party, not verified | 6 months $346.50; 12 months $630 (verified). Diamond to 1950: $787.50/yr | norgatedata.com/stockmarketpackages.php\[15\]\[16\]\[31\] |
| EODHD paid (EOD All-World) | Unmeasured | 30+ years | Adjusted close | Dividends and splits | As above | Yes | No (needs $59.99 Fundamentals or $99.99 All-in-One) | REST API | Personal use | $19.99/mo or $199.00/yr (verified) | eodhd.com/pricing\[25\]\[32\] |
| FirstRate Data stocks bundle | Unmeasured (ticker list page timed out). Vendor Stocks Complete page (search snippet) states "Jan 2000 - Sep 2026", 16,309 tickers, "Over 7000 delisted stocks" | January 2000 | Vendor FAQ: "For stocks and ETFs, all datasets contain both unadjusted and adjusted data"; adjustment method not verified | Not verified | Ticker with "-DELISTED" suffix | Separate bundles | "Stocks Bundle + Fundamentals" exists | Bulk download (Complete Stocks bundle 28 GB zipped, 290 GB uncompressed, per vendor FAQ) | Not verified | One-time purchase: $299 per third-party NexusFi listing (vendor price not confirmed); updates $59.95/month after purchase (vendor page snippet) | firstratedata.com/b/22; firstratedata.com/about/FAQ |
| Tiingo Power | Unmeasured | As above | As above | As above | permaTicker | Yes | 15+ years | REST API | Individual, non-commercial | $30/mo or $300/yr (Tiingo pricing page) | tiingo.com/about/pricing\[33\]\[34\] |
| SimFin, SEC EDGAR Financial Statement Data Sets, Kibot, QuantRocket/EDI, Finaeon, Algoseek | Not researched in this pass | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | Unverified | n/a |

### 2. Per-name results

The P1 sample was chosen as instructed because the target CSV was not available. **Every P1 name: membership in target list unconfirmed (CSV not available).** Departure decades are from public knowledge of each company's acquisition or failure, not from the CSV.

Source for every WIKI cell: GitHub gist by Aaron Hoffman listing all 3,194 WIKI symbols with first and last dates as of 2017-11-06, read on 2026-10-23.\[3\]\[7\] The final frozen file runs to 2018-03-27, so "last date" for names alive after November 2017 is probably later than shown.\[20\] Identity key in WIKI is the ticker for every row. For every other source (Alpha Vantage, Tiingo, EODHD, Massive, Stooq, CRSP, Sharadar, Norgate, FirstRate), every name is **unmeasured**.

**P1 sample (n=25)**

| Name | Ticker(s) tested | Departure | WIKI present | First date | Last date | Span covers to delisting? |
|---|---|---|---|---|---|---|
| Enron | ENE | 2000s | No | | | Absent |
| WorldCom | WCOM | 2000s | No | | | Absent |
| Compaq | CPQ | 2000s | No | | | Absent |
| Nextel | NXTL | 2000s | No | | | Absent |
| Lucent | LU | 2000s | No | | | Absent |
| Bear Stearns | BSC | 2000s | No | | | Absent |
| Lehman Brothers | LEH | 2000s | No | | | Absent |
| Washington Mutual | WM, WAMUQ | 2000s | No (WM present 1991-09-30 to 2017-11-06 but very likely Waste Management) | | | Absent |
| Circuit City | CC | 2000s | No | | | Absent |
| Wachovia | WB | 2000s | No | | | Absent |
| Sun Microsystems | SUNW, JAVA | 2010 | No | | | Absent |
| DirecTV | DTV | 2010s | Yes | 2003-12-23 | 2017-04-25 (likely file artifact; company acquired 2015) | Partial/uncertain |
| EMC | EMC | 2010s | Yes | 1988-12-16 | 2016-09-06 | Yes |
| Yahoo | YHOO | 2010s | Yes | 1996-04-12 | 2017-06-16 | Yes |
| Reynolds American | RAI | 2010s | Yes | 1999-06-01 | 2017-07-24 | Yes |
| Time Warner | TWX | 2010s | Yes | 1992-03-19 | 2017-11-06 | Partial (WIKI ends before 2018 acquisition) |
| Monsanto | MON | 2010s | Yes | 2000-10-18 | 2017-11-06 | Partial |
| Express Scripts | ESRX | 2010s | Yes | 1992-06-09 | 2017-11-06 | Partial |
| Celgene | CELG | 2010s | Yes | 1990-03-26 | 2017-11-06 | Partial |
| L3 Technologies | LLL | 2010s | Yes | 1998-05-19 | 2017-11-06 | Partial |
| Allergan | AGN | 2020s | Yes (pre-2015 history probably original Allergan; ticker shared with Actavis after 2015, inference) | 1989-06-22 | 2017-11-06 | Partial, identity mixed |
| Twitter | TWTR | 2020s | Yes | 2013-11-07 | 2017-11-06 | Partial |
| Xilinx | XLNX | 2020s | Yes | 1990-06-18 | 2017-11-06 | Partial |
| Cerner | CERN | 2020s | Yes | 1990-03-26 | 2017-11-06 | Partial |
| Activision Blizzard | ATVI | 2020s | Yes | 1993-10-25 | 2017-11-06 | Partial |

WIKI score on the P1 sample: 3 of 25 fully covered, 11 partial, 11 absent. All 11 absent names left in 2000 to 2010.\[3\]

**P2 (all 24 listed names)**

| Ticker | Group | WIKI present | First date | Last date | Result |
|---|---|---|---|---|---|
| ABS | Later entity holds ticker | No | | | Absent |
| BMC | Later entity holds ticker | No | | | Absent |
| CCE | Later entity holds ticker | Yes | 1986-11-24 | 2017-11-06 | Present but mixed entities under one ticker; fails identity |
| CFC | Later entity holds ticker | No | | | Absent |
| GR | Later entity holds ticker | No | | | Absent |
| HAR | Later entity holds ticker | Yes | 1986-11-14 | 2017-03-10 | Full (ends at 2017 acquisition) |
| MHS | Later entity holds ticker | No | | | Absent |
| NCC | Later entity holds ticker | No | | | Absent |
| TEG | Later entity holds ticker | Yes | 1988-01-05 | 2015-06-29 | Full |
| TIE | Later entity holds ticker | No | | | Absent |
| SLE | Reused or mixed | No | | | Absent |
| POM | Reused or mixed | Yes | 1987-01-02 | 2016-03-23 | Full |
| CA | Reused or mixed | Yes | 1984-09-07 | 2017-11-06 | Partial (ends 2018) |
| BBBY | Reused or mixed | Yes | 1992-06-05 | 2017-07-25 (probable gap) | Partial |
| PSKY | Reused or mixed | Not checked | | | Unmeasured |
| NFX | Reused or mixed | Yes | 1993-11-12 | 2017-11-06 | Partial (ends 2018) |
| CPWR | Reused or mixed | Yes | 1992-12-16 | 2014-12-15 | Full |
| AVB, EA, EQR, LEG, QRVO, SATS, WBD | Relisted in 2026 by new entity | Not checked | | | Unmeasured |

WIKI on P2: 16 of 24 checked; 4 full, 3 partial, 1 present but identity-mixed, 8 absent, 8 unmeasured.\[3\] Because WIKI keys only on ticker, any "present" P2 row must still be confirmed by hand to be the original company.

### 3. Which sources were checked per name, and which are unmeasured

- **Checked per name:** WIKI only, through a public ticker list with first and last dates (GitHub gist, snapshot 2017-11-06).\[3\]\[7\] The official Nasdaq Data Link ticker list and the Kaggle "Quandl WIKI Stocks Dictionary" page did not render (JavaScript-only), so the gist could not be cross-checked against them.
- **Unmeasured, requires an API call with a key:** Alpha Vantage, Tiingo, EODHD, Massive. No accounts were created.
- **Unmeasured, requires a bulk download:** Stooq, and the full WIKI file (needed to confirm final 2018 end dates).
- **Unmeasured, requires an institutional account:** CRSP via WRDS.
- **Unmeasured, requires purchase:** Sharadar, Norgate (the free trial is limited to recent bars per the brief, so it cannot prove deep coverage), FirstRate Data (its public ticker list page, which would allow a per-name check, timed out during this research).

### 4. WIKI status in October 2026

- The Nasdaq Data Link WIKIP page (as indexed) says the feed stopped being supported on April 11, 2018 and that Nasdaq "will continue to host this data feed", and it documents a delta-file API call that needs an API key.\[19\] The page itself requires JavaScript and login to show pricing, so current downloadability through Nasdaq could not be confirmed on 2026-10-23.
- A full mirror is on Kaggle (marketneutral, "Quandl WIKI Prices US Equites", WIKI_PRICES.csv, 1.8 GB, dates 1962-01-02 to 2018-03-27). It describes the data as released into the public domain by Quandl.\[1\]\[20\] Kaggle download terms were not checked.
- A per-name ticker list is publicly visible through the GitHub gist described above. The Nasdaq page says a list of all WIKI tickers is available, but the link could not be rendered.\[3\]\[19\]

### 5. CRSP/WRDS access for a UNL College of Law staff member

- UNL Libraries lists WRDS among its subscribed resources (libanswers.unl.edu/faq/339059, updated Sep 11, 2026).\[5\]
- UNL Finance job postings state "The department and college have excellent data resources and access to WRDS" (employment.unl.edu/postings/98932).\[35\]
- A UNL course file indexed in search lists CRSP Stock (Annual), CRSP Indexes and Compustat among WRDS databases.\[36\] The file did not load, so this is unverified.
- No UNL page found states who is eligible for a WRDS account. UNL's general rule limits off-campus library database use to currently enrolled students, faculty and staff, but many universities restrict WRDS further.\[37\] For example, Arkansas offers individual accounts to "standing faculty, full-time research staff, currently-enrolled Ph.D." students, and UNC limits access to "selected staff".\[38\]\[39\] Whether a College of Law staff member qualifies, and whether personal (non-university) research and local storage are allowed under the WRDS subscription, are both unverified.
- What an individual generally needs: an active affiliation with a subscribing institution, an account request at the WRDS site using the institutional email, and approval by the local WRDS representative.\[40\]\[41\] Alumni and outside researchers generally do not qualify (stated by the University of Denver guide).\[42\]\[43\] Walk-in terminal access at UNL was not found.

### 6. P3 note (pre-2000 departures)

Sources whose documented history reaches before 2000: CRSP (from 1925/1926 per other universities' guides),\[30\]\[44\] Norgate Diamond (to 1950, $787.50/year) and Platinum (to 1990), WIKI (some series from the 1960s to 1980s, but pre-2000 deaths appear absent, consistent with the pattern above), and Sharadar's tickers table (June 1990), though Sharadar prices start December 1997.\[14\]\[30\]\[31\] Coverage of P3 names was not measured for any source.

## Recommendations

1. **First, ask UNL about WRDS (free if eligible).** Email ask-a-question@unl.edu or call 402-472-9568\[45\] and ask: (a) whether College of Law staff can get a WRDS account, (b) whether the subscription includes CRSP daily stock files with delisting information, (c) whether personal, non-university research and local storage are allowed.\[5\] If the answer is yes to all three, CRSP covers requirements 1 to 4 with PERMNO as the identity key, and the paid steps below become unnecessary.
2. **Free path (partial) if WRDS is not available.**
   - Download WIKI_PRICES.csv from the Kaggle mirror. Join on ticker and date window, and accept a name only if the first and last dates match the company's known listing life. Hand-check every P2 hit, because WIKI cannot separate entities that shared a ticker.
   - Get a free Tiingo key. Use the search/meta endpoints to find delisted, non-recycled tickers and pull daily bars for post-2015 deaths.\[10\]\[23\] 500 unique symbols per month exceeds the 386 P1 names.\[46\]
   - Use Alpha Vantage LISTING_STATUS (`state=delisted`) for delisting dates, for dates after 2010-01-01 only.\[8\]\[9\]
   - Known gaps: almost none of the 235 P1 names that left in the 2000s; no identity key for ticker reuse in WIKI; no data after 2018-03-27 in WIKI; Tiingo depth and adjustment for delisted names unverified; delisting reasons not available.
3. **Best paid fallback: Sharadar Prices, Full History ($39/month or $299/year, verified 2026-10-23).** It is the only paid source here whose public documentation covers every core requirement: daily OHLCV for active and delisted US stocks from December 1997; a `closeadj` column adjusted for splits, dividends and spinoffs, plus unadjusted and split-only closes; an `actions` table with dividends, splits, delisting dates and delist reasons; permaticker, CUSIPs and FIGI for identity; ETF prices in the same plan; bulk download and an API usable from any OS.\[14\] Add the Bundle ($69/month or $499/year) only if point-in-time fundamentals are needed.\[4\] Before buying, read sharadar.com/terms to confirm (a) local storage is allowed and (b) whether data may be kept after cancellation. Neither point was verified. Its start date of December 1997 does not reach P3 names.
4. **Choose Norgate Platinum ($630/year) only if you need pre-1998 history, and only if a Windows machine for the updater is acceptable.** Also check the reported EULA clause requiring deletion of all data when the subscription ends.\[15\]\[31\]

## Caveats

- **What no source provides:** No source offers a free, legal, licensed, total-return daily history with a permanent identity key for companies that died in 2000 to 2010. That data is held by commercial or academic vendors (CRSP, Sharadar, Norgate, LSEG Datastream), and the one free community dataset (WIKI) was built from currently listed tickers, so it misses names that died before it was assembled.
- **Not verified:** current downloadability of WIKI from Nasdaq Data Link; WIKI's adjustment formula; WIKI ETF coverage; final 2018 end dates per name (the gist is a 2017-11-06 snapshot); the WIKI status of PSKY and the 7 relisted-2026 names; Alpha Vantage premium price on the vendor's own page (a third-party Macroption page gives $49.99 to $249.99/month) and whether delisted symbols return series; Tiingo delisted depth and adjustment method; EODHD "_old" suffix convention (third-party source); Massive adjustment method and actual delisted coverage (vendor page lists paid tiers at $29, $79 and $199/month); Stooq delisted coverage; FirstRate Data one-time price and per-name ticker coverage (vendor page timed out; the vendor's Stocks Complete snippet states "Over 7000 delisted stocks" from January 2000, and NexusFi lists "$299 / one-time"); Norgate's Windows-only updater and EULA deletion clause (reported by a third-party GitHub issue citing EULA version 20261002, clause 21);\[15\] Sharadar license retention terms; UNL WRDS eligibility for staff and CRSP inclusion; SimFin, SEC EDGAR Financial Statement Data Sets, Kibot, QuantRocket/EDI, Finaeon and Algoseek (not researched in this pass).
- **Sample design:** The P1 sample is not drawn from the target list. Its 10 / 10 / 5 split across decades only roughly mirrors the target's 235 / 127 / 24, so the WIKI sample score (3 full of 25) probably overstates WIKI's coverage of the full P1 list, which is weighted toward the 2000s.
- **Inferences flagged:** WM being Waste Management in WIKI, AGN identity mixing, DTV's 2017-04-25 end date being an artifact, and the departure decades are based on public company history, not on the source data.
- **No accounts were created, nothing was purchased, and nothing was scraped.** All dates read: 2026-10-23.

## Sources

1. [Quandl WIKI Prices US Equites](https://www.kaggle.com/datasets/marketneutral/quandl-wiki-prices-us-equites/data)
2. [Quandl data feed update: WIKI stock prices - NO LONGER UPDATING as of April 11, 2018 · Issue #2145 · quantopian/zipline · GitHub](https://github.com/quantopian/zipline/issues/2145)
3. [Quandl Historical NYSE Symbol Stock Price Data -- Wiki EOD Stock Prices API](https://gist.github.com/aaronhoffman/9ef359cbf39f2eefdf50fbd82f5d368a)
4. [Subscribe | sharadar.com](https://sharadar.com/subscribe)
5. [What databases and resources are searched by Quick Search? - ASKus FAQ](https://libanswers.unl.edu/faq/339059)
6. [CRSP Basics - Wharton Research Data Services](https://wrds-www.wharton.upenn.edu/pages/grid-items/crsp-basics/)
7. [NYSE Historical Stock Price Data From Quandl](https://aaron-hoffman.blogspot.com/2017/11/nyse-historical-stock-price-data-from-quandl.html)
8. [API Documentation | Alpha Vantage](https://www.alphavantage.co/documentation/)
9. [AlphaVantage.FundamentalData — Alpha Vantage v0.3.0](https://hexdocs.pm/alpha_vantage/AlphaVantage.FundamentalData.html)
10. [Symbology API Documentation](https://www.tiingo.com/documentation/appendix/symbology)
11. [Tiingo and delisted stocks - Tiingo - AmiBroker Community Forum](https://forum.amibroker.com/t/tiingo-and-delisted-stocks/26140)
12. [Finding the Best Stock Price API: The Top Stock APIs in 2026](https://www.tiingo.com/blog/best-stock-price-api/)
13. [Stock Fundamentals Data](https://sharadar.com/fundamentals)
14. [Stock Price Data | sharadar.com](https://sharadar.com/prices)
15. [Run Example 7.6's January effect on Norgate's delisted S&P 600 prices, so its point-in-time verdict can be decided · Issue #684 · l3a0/quantitative-trading · GitHub](https://github.com/l3a0/quantitative-trading/issues/684)
16. [Norgate Data - Data Content Tables](https://norgatedata.com/data-content-tables.php)
17. [Stocks Bundle + Fundamentals](https://firstratedata.com/cb/8/)
18. [Download Historical Intraday Data (25 Years Data)](https://firstratedata.com/)
19. [Financial, Economic and Alternative Data](https://data.nasdaq.com/databases/WIKIP)
20. [Quandl WIKI Prices US Equites](https://www.kaggle.com/datasets/marketneutral/quandl-wiki-prices-us-equites)
21. [How to Scale Your Investment Process With a Stock API - Tiingo Blog](https://www.tiingo.com/blog/scaling-investment-processes-through-a-stock-api/)
22. [U.S. Fundamental Data API Documentation](https://www.tiingo.com/documentation/fundamentals)
23. [Search API Documentation](https://www.tiingo.com/documentation/utilities/search)
24. [Stock, ETF, and Mutual Fund Split API Documentation](https://www.tiingo.com/documentation/corporate-actions/splits)
25. [Free and paid plans for Historical Prices and Fundamental Financial Data API](https://eodhd.com/pricing)
26. [Addressing Survivorship Bias: Incorporating Historical Data of Delisted Companies](https://wire.insiderfinance.io/addressing-survivorship-bias-incorporating-historical-data-of-delisted-companies-9ed370974ac1?gi=08c4251b2e48)
27. [Eodhd Plans Pricing](https://apis.io/plans/eodhd/eodhd-plans-pricing/)
28. [An Introduction to Stooq Pricing Data](https://www.quantstart.com/articles/an-introduction-to-stooq-pricing-data/)
29. [Stooq Scraper - Historical Stock, Forex & Index Price Data · Apify](https://apify.com/parseforge/stooq-historical-stocks-scraper)
30. [libguides.wesleyan.edu](https://libguides.wesleyan.edu/wrds)
31. [Norgate Data - Stock Market Packages](https://norgatedata.com/stockmarketpackages.php)
32. [Eod Historical Plans Pricing — API Pricing Plans](https://apis.io/plans/eod-historical/eod-historical-plans-pricing/)
33. [How to Use a Forex API for Forex Trading - Tiingo Blog](https://www.tiingo.com/blog/forex-api/)
34. [Tiingo API Pricing](https://www.tiingo.com/about/pricing)
35. [University of Nebraska-Lincoln](https://employment.unl.edu/postings/98932)
36. [Current databases available through WRDS Description](https://canvas.unl.edu/files/10002997/download?download_frd=1)
37. [Troubleshooting off-campus access to UNL Libraries online resources - ASKus FAQ](https://libanswers.unl.edu/faq/145419)
38. [Home - Wharton Research Data Services (WRDS) - LibGuides at UNC Kenan - Flagler Business School](https://kenan-flagler.libguides.com/wrds)
39. [Get Started with WRDS - WRDS: Wharton Research Data Services - Research Guides at University of Arkansas](https://libguides.uark.edu/wrds)
40. [WRDS - Datasets - LibGuides at Özyeğin University](https://ozyegin.libguides.com/c.php?g=707054&p=5096196)
41. [libguides.uky.edu](https://libguides.uky.edu/WRDS)
42. [Home - WRDS (Wharton Research Data Services) - Library Guides at University of Denver](https://libguides.du.edu/wrds)
43. [UW Libraries - Research Tools: Articles & Databases - Wharton Research Data Services](https://www.uwyo.edu/libraries/research/find/unique/wrds.cfm)
44. [CRSP (via WRDS)](https://biblioteca.luiss.it/en/resources/crsp-wrds)
45. [Connect From On & Off Campus](https://libraries.unl.edu/connect-campus/)
46. [Tiingo - ML4T Data](https://ml4trading.io/docs/data/providers/tiingo/)
