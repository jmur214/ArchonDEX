# Proposal: option (c), a survivorship-complete total-return source, priced

**For:** the director, then **the USER**. **Status:** PROPOSAL ONLY, propose-first under CLAUDE.md
("new engines, new dependencies, new external services" and "anything that would touch real money
paths"). No purchase, no account, no code, no trial has been started. Nothing in `data/` or
`engines/` is touched by this document. **N_trials: 0.**

**Where this sits.** The cutover batch was RULED by the user on 2026-10-22: option (a), the pre-2018
drip kept everywhere and labelled, the post-2018 span of every fetchable file rewritten exact; (b)
declined as a survivor-correlated confound; **(c) "priced separately AFTER (a)"**
(`docs/State/CURRENT_STATE.md`, the 2026-10-22 block). This is that pricing. The standing
data-spend gate is older and still in force: "still not ready to pay for data before this thing is
making money or even close to it" (user, 2026-05-12, quoted in `docs/State/forward_plan.md`). The
recommendation below respects it: the first step costs nothing, and the paid step waits on the
user lifting that gate.

**How claims are sourced.** Every provider claim below carries the URL it was read from and the
date read (all read **2026-10-22**, from this session). A price is marked **verified** only when it
was read on the vendor's own page; a figure from a reseller, a comparison site or a forum is marked
**unverified**. Where a vendor's page would not serve (Nasdaq Data Link's product pages render
client-side and returned only a title; Financial Modeling Prep's pages returned HTTP 403; Norgate's
system-requirements page returned 404) the gap is stated, never filled by a guess. Prices in USD
unless stated. Nothing here is a measurement of any provider's DATA; that is what the trial step is
for (§4.3).

---

## 1. The requirement, precisely

The canonical substrate is a per-ticker daily cache under `data/processed/` (`<TICKER>_1d.csv` and
`.parquet`, 730 files), total-return convention, built from one universe provider (yfinance) with a
2018 seam before which the T-082b drip applies a constant-yield approximation. The point-in-time
S&P 500 membership table (`data/universe/sp500_membership_pit.parquet`) holds **1,255 membership
rows over 1,202 distinct tickers, 1996-01-02 to 2026-06-02** (read 2026-10-22 from the main tree,
read-only). The measurement window is 2000 to 2025, 312 month-ends.

What the cutover proposal measured (`docs/Sources/proposal_substrate_cutover_exact_tr_2026-10-15.md`
§2, §2b):

- **75 of the 730 files (10.3%) are unfetchable** from yfinance: 45 "no timezone found", 30 "no
  price data found"; each retried serially (3 tries, 10/20/30 s backoff), none recovered, no
  rate-limit message in the log; on Alpaca's asset endpoint **none ACTIVE: 50 INACTIVE, 25
  unknown**. 66 of the 75 ended before the substrate's common end dates; 9 (AVB, CTRA, EA, LEG,
  QRVO, WBD, EQR, MHS, CA) ended on a common date and delisted between the 2026-04-24 snapshot and
  the pass.
- **The guard's first declaration set is 46** (`docs/Sources/proposal_stale_and_holed_files_guard_2026-10-15.md`;
  `config/data_gaps.json` holds exactly 46 declarations, 19 with `ends_at_delisting`): 32 delisted,
  10 files lying entirely after their PIT name's exit (later entities on the symbol: ABS, BMC, CCE,
  CFC, GR, HAR, MHS, NCC, TEG, TIE), the 3 class (i) reused tickers (BBBY, PSKY, CPWR), plus FISV
  2025-11-12 as a provider gap on a session that traded (SIP volume 6,244,651). That is 1,298 holes
  in 395 runs that NO provider in the current set can fill.
- Beyond those 46, the writer refuses forever under the symbol **CA, SLE, POM and NFX** (class (i):
  the cached file IS the reused entity) and holds BK (ticker change to BNY) for a declared class.
- **Coverage.** B-1's census first counted file existence: 52.7% of the 2000-01 members. Counting a
  month-end bar actually formed, true coverage was **38.4% in 2000-01, 207 of 312 months below 80%,
  last sub-80% month 2017-03** (A's §14.3; the ledger row for T-365 corrected). The guard's
  formation_coverage over every member on the date reads 0.38 / 0.70 / 208 of 312 on both
  substrates. The reason is not only the 75: **501 of the 1,202 PIT tickers have no cached file at
  all** (read-only count, 2026-10-22). On 2000-01-31 the table has 495 members; 261 have a file and
  **234 do not** (that is the 52.7%); on 2005-01-31, 187 of 495 lack a file; on 2010-01-29, 119 of
  499; on 2018-01-31, 49 of 506; on 2025-12-31, 3 of 503. The missing names are the members that
  later left the index (AABA, ABI, AGC, BSC, CPQ, DALRQ, and so on): the cache was built from what
  yfinance could serve, which is survivors.
- **The drip is dispersion, not a shift** (cutover proposal §1): exact minus drip over 559 files
  with a pre-seam span has median −0.10%/yr but **102 names move by more than 1%/yr**; every
  pre-2018 cross-sectional verdict is a re-qualification, not a relabel.

**What "exact total return" means here** (`docs/Sources/proposal_level_rail_last_bar_identity_2026-10-15.md`,
§2 and §8): daily bars, dividend back-adjusted at ex-dates and split-adjusted, **from the provider's
own dividend and split record**; the writer verifies (i) a LEVEL IDENTITY at the cache's last bar,
the provider's unadjusted close times the splits after it against the cached close, |ln residual|
within `LEVEL_TOLERANCE` 0.01, and (ii) a 252-bar overlap ratio against the cached tail
(`engines/data_manager/tr_writer.py`: `level_identity`, `classify_overlap`, `OVERLAP_TAIL_BARS`).
Any provider adopted under (c) must be able to feed both checks: a total-return series, a
split-only series (the two-mode basis measure) and an event table.

**The requirement list a candidate must meet, all of it:**

| # | requirement | why |
|---|---|---|
| R1 | delisted names with their full history to the last trading day (survivorship-free), for US common stocks since 2000, 1999 preferred | the 75 + the 501; the B-1 prereg §3.6 names "a survivorship-complete re-verification" as the condition before any clear counts |
| R2 | total-return daily bars, dividend AND split adjusted by the provider, with the split-only mode available | the writer's `Provider(adjusted=True/False)` contract and the basis measure |
| R3 | split and dividend event tables (ex-dates, amounts, factors) | the level rail's identity; `Actions` is REQUIRED when a cache exists |
| R4 | a stable security identity across ticker reuse (CA, SLE, POM, NFX, BBBY, PSKY, CPWR, the ten later-entity files) | the class (i) problem; "matching records on ticker alone can stitch two histories together into a single series that no investor ever held" (Algoseek, below) |
| R5 | US equities AND US ETFs in one convention (the 39 `tr_reconciled` ETF files, AGG/EFA/VNQ) | one provider for the whole universe (cutover proposal §2a; the writer refuses a providers map without the universe provider) |
| R6 | point-in-time S&P 500 membership, or at least compatible with the one already held | already held; a provider's own daily constituents are an independent check, not a requirement |
| R7 | a licence permitting personal, non-commercial research by one individual | the account is one person's Roth/IRA; no redistribution |
| R8 | a price the user can weigh, verified on the vendor's page, with a trial or sample for the pre-purchase measurement | the data-spend gate; `[NN-FIRST-ARTIFACT]`: the coverage of the 75 is observed before money moves |
| R9 | runs in, or exports to, the project's Python/parquet pipeline on this Mac or in the existing AWS account | the adapter under `engines/data_manager/`; the manifest pins files, not a vendor database |

---

## 2. Candidate providers, evaluated

Each entry: delisted coverage; total-return method; event tables; identity across reuse; history
start; US ETFs; delivery; licence; price; verdict against §1. Sources are listed in §8 with the
date read.

### 2.1 Norgate Data, US Stocks package, Platinum tier

- **Delisted coverage: YES.** "Delisted securities" are a Platinum and Diamond feature only; Silver
  and Gold are "Current major-exchange-listed securities" [N1, N2]. "Coverage is considered to be
  essentially complete back to late 1992"; NYSE "excellent back to 1950" [N3]. Platinum's history
  runs "back to 1990", Diamond "back to 1950" [N1].
- **Total-return method: provider-side back-adjustment, four modes.** Stock prices can be adjusted
  four ways, including "Adjusted for Capital Reconstructions, Special Distributions and Normal
  Distributions - aka Total Return" [N3]. The Python package exposes `priceadjust` =
  NONE / CAPITAL / CAPITALSPECIAL / TOTALRETURN (TOTALRETURN the default) and date padding
  NONE / ALLMARKETDAYS / ALLWEEKDAYS / ALLCALENDARDAYS [N4]. CAPITAL is the split-only mode the
  writer's `adjusted=False` needs; NONE is the unadjusted print the level identity needs.
- **Event tables: PARTIAL, to be confirmed on the trial.** `capital_event_timeseries` marks
  "splits, reverse splits, bonus issues, stock dividends"; `dividend_yield_timeseries` is a trailing
  twelve-month split-adjusted ordinary-dividend yield, "Special dividends, distributions and
  spin-offs are not included" [N4]. A per-ex-date cash-dividend table was NOT found in the package
  text read; the identity can be derived from the NONE / TOTALRETURN ratio steps if no table exists.
  **Unverified; a trial question (§4.3).**
- **Identity across reuse: YES, by construction.** A delisted security "gains a suffix of -YYYYMM
  indicating the year and month of the last trading day"; Enron became "ENRNQ-200411" with a last
  trading day 2004-11-17; AOL-201506, TWX-201806, NAV-202106 are further examples [N3]. A Wealth-Lab
  developer, 2024-08-05: "The date in delisted symbols serves only to create a unique name since
  symbols are often reused" [N5]. The month precision of the suffix is the KEY, not the delisting
  date; the series itself carries the last bar.
- **History start:** 1990 at Platinum [N1]; ETF coverage "commencing in 1993" [N3]. Covers 1999.
- **US ETFs: YES.** "ETF and ETN coverage is complete back to the introduction of those security
  types" [N3]; the same database holds equities and ETFs (a published tutorial filters
  `subtype1 == 'Equity'` to drop "ETFs, REITs") [N6].
- **Point-in-time index membership: YES, daily.** "Our historical index constituents are daily and
  show the exact constituents on each trading day", Platinum or higher [N3];
  `index_constituent_timeseries` in the package [N4]. An independent check on our parquet.
- **Delivery: a Windows desktop updater.** "The 'Norgate Data Updater' application (NDU) is a
  Windows-only application. NDU must be running for this Python package to work"; "Microsoft
  Windows 10/11 or Microsoft Windows 2019 Server/2022 Server/2025 Server" [N4]. **This project runs
  on a Mac.** The path is a Windows VM on the Mac or a Windows instance in the existing AWS account,
  exporting parquet that the pipeline then reads; the VM is in the data path only on refresh days.
  The cost of that VM is NOT priced in this document.
- **Licence: personal use, verified.** "No commercial use - the data can only be licensed for
  personal use by individuals" [N2]. The trial is "Personal use" only [N7]. Whether exported data
  stays usable after a subscription lapses is NOT stated on the pages read (corrections are applied
  "whilst your subscription is active" [N3]); **the EULA must be read before purchase.**
- **Price: VERIFIED on the vendor's page [N1].** US Stocks, 6-month / 12-month:
  Silver $148.50 / $270.00; Gold $198.00 / $360.00; **Platinum $346.50 / $630.00**; Diamond
  $433.13 / $787.50. Platinum is the tier that meets R1; Silver and Gold do not (no delisted
  names). The repo's 2026-07-02 correction ("Norgate Silver is survivor-ONLY; true survivorship-free
  = Platinum $346.50/6mo") is confirmed unchanged today.
- **Trial: VERIFIED [N7].** "Three Week Trial" at the Platinum tier for US stocks; "Daily price
  history limited to 2 years"; delisted securities INCLUDED in the stock trials; "No further data
  access after trial ends"; "Repeated free trials are not permitted unless approved and initiated by
  Norgate Data staff." Whether a card is required is not stated.
- **Verdict: meets R1 to R8 on the vendor's own statements; R9 only through a Windows VM.** The
  open items are the dividend table (R3, trial question) and the post-lapse usability of exports
  (EULA). Delisting-date precision is to the month in the symbol, which is a key, not a defect.

### 2.2 Sharadar via Nasdaq Data Link: SEP (equity prices), SFP (fund prices), TICKERS, ACTIONS

- **Delisted coverage: YES, from 1998.** "More than 16,000 active and delisted tickers", "History
  from 1998" (the Quandl data fact sheet, PDF metadata 2019-07-11) [S1]; "Active and delisted
  coverage extends back to the 90s", "nearly completely free of survivorship bias" [S2]; the
  reseller QuantRocket: "End-of-Day US Stock Prices (1998 to present)", "No survivorship bias:
  includes active and delisted tickers", and that bundle "excludes ETFs, CEFs, and ETNs" [S3].
  Caveat on depth: an independent analysis (2021-08-28) found "Sharadar's data shows no
  de-listings of any companies between 1986 and 1998" [S4]; irrelevant to a 2000 start, decisive
  against anything earlier.
- **Total-return method: UNVERIFIED definition.** The SEP datatable's fields are `ticker, date,
  open, high, low, close, volume, closeadj, closeunadj, lastupdated` (the datatable metadata
  endpoint, status "ON TIME", update frequency "CONTINUOUS") [S5]; SFP carries the same fields
  [S6]. The product page that defines `closeadj` and `closeunadj` would not render. A Numerai forum
  user (2022-01-27) observed `close` split-adjusted but not dividend-adjusted and had emailed
  Sharadar; no reply is in the thread [S7]. Whether `closeadj` is dividend-and-split adjusted from
  the provider's own record is exactly R2 and must be read from the data dictionary after login.
- **Event tables: YES, shape verified, content not.** ACTIONS fields: `action, contraticker,
  date, ticker` with primary key `(date, ticker, name, action, contraname, contraticker)` [S8].
  Dividend amounts and split ratios are presumably the `value` column; not visible in the metadata
  read. Trial question.
- **Identity across reuse: YES, a persistent id exists.** The TICKERS table carries `permaticker`,
  `isdelisted`, `firstpricedate`, `lastpricedate`, `relatedtickers`, `cusips`, `figi` [S9]. Tiingo's
  own docs use the word "permatickers" as a future feature; Sharadar has it today. **Open:** SEP is
  keyed by `ticker`; whether a reused symbol's two entities are separable in SEP (two TICKERS rows
  with disjoint price-date ranges, or a suffixed symbol) is a trial question.
- **History start:** 1998 [S1, S3]. Covers 1999.
- **US ETFs: YES, as a separate add-on.** "End-of-Day US ETF Prices (1998 to present)" covering
  ETFs, CEFs and ETNs [S3]; the SFP table [S6].
- **PIT membership:** "S&P 500 Constituents (1957 to present)" in the bundle [S3].
- **Delivery: REST API and bulk datatable export, Mac-native.** No desktop app.
- **Licence: personal tier exists; terms unread.** Nasdaq accounts are Personal / Academic /
  Business and some feeds show only "Contact Sales" depending on the account type (help-center
  listing) [S10]; the reseller's terms: "Professional use requires the appropriate professional or
  institutional license", no redistribution [S3].
- **Price: UNVERIFIED.** Nasdaq Data Link shows pricing only after login; the reseller's page reads
  "Log in or create account to see pricing" for both annual and month-to-month [S3]. No official
  figure was obtained. The repo's 2026-06-25 inventory called it a "cheap-end pro sub" with no
  number. **Pricing it costs nothing: a Nasdaq Data Link account needs "No credit card" [S2].**
- **Verdict: the strongest Mac-native candidate; blocked on two unverified facts (R2 definition,
  R8 price) that a free account resolves.** The comparison arm to Norgate.

### 2.3 EODHD (EOD Historical Data)

- **Delisted coverage: PARTIAL by era.** "A delisted ticker keeps its history: TWTR.US still returns
  Twitter's prices up to the day it stopped trading in October 2022"; the oldest US common stocks
  "begin on 2 January 1962" [E1]. Delisted symbols are listed per exchange with `delisted=1`. By
  delisting era: **after 2018: "EOD, Fundamentals, Dividends and Splits"; after 2021: plus
  intraday; "Before 2018: EOD only"** [E2]. Of the 32 delisted names in the declaration set, the
  ten later-entity files alone have PIT exits from 2006 to 2017; for a pre-2018 delisting EODHD
  offers no dividend or split table, so R3 fails for most of the names we need.
- **Total-return method:** `adjusted_close` is "Closing price adjusted for both splits and
  dividends"; volume split-adjusted only [E1]. Whether that holds for a pre-2018 delisted name
  whose event tables are absent cannot be checked from the provider's own record (R3).
- **Identity across reuse: NO.** Symbol-keyed. The docs cover renames (FB.US returns empty; use the
  US-only Symbol Change History endpoint) but not reuse [E1, E2]. A practitioner's note dated
  2026-05-07 reports the exact defect we hold: "ABS.US" apparently Albertson's (in the index 1996
  to 2006) but EODHD "only has data for 'ABS.US' from end of 1997", with a chart gap suggesting
  the ticker was reused [E3]. ABS is one of our ten later-entity files.
- **History start:** 1962 for the oldest live names [E1]; delisted depth per era as above.
- **US ETFs: YES** (the US exchange list spans "stocks, ETFs, and funds") [E2].
- **Delivery:** REST API, Mac-native. **Licence:** "Personal use" plans [E4].
- **Price: VERIFIED [E4].** Historian (EOD Historical All-World) **$19.99/month or $199.00/year**;
  Active trader $29.99 / $299.90; Equity analyst $59.99 / $599.90 (no EOD prices); ALL-IN-ONE
  **$99.99/month or $999.90/year**. The historical-data endpoint is listed as available on
  All-In-One, EOD Historical Data: All World, EOD + Intraday: All World Extended, and the free plan
  (one year, 20 calls/day) [E1]. Which plan includes delisted names is not stated on the pricing
  page [E4]: **unverified**.
- **Verdict: fails R3 for pre-2018 delistings and R4 outright.** Cheap, and the repo's 2026-06-25
  inventory already said "AVOID EODHD + FMP (documented coverage gaps)"; the 2026-05-07 note
  confirms it with our own name.

### 2.4 Tiingo

- **Delisted coverage: PARTIAL.** "Tiingo supports delisted data for tickers that have not yet been
  recycled"; "This section will be expanded as we ready to expand our API into permatickers and
  delisted ticker support" [T1]. So a recycled ticker's old entity is NOT served: CA, SLE, POM, NFX,
  ABS and the rest of class (i) fail by the vendor's own sentence.
- **Total-return method: GOOD.** The adjustment "follows CRSP methodology" and "incorporates both
  split and dividend adjustments"; fields `adjClose, divCash` (on the ex-date), `splitFactor`;
  "Both raw prices and adjusted prices are available" [T2]. Event data per bar satisfies R3's shape.
- **Identity across reuse: NO (not yet).** "permatickers" are a stated future [T1].
- **History start:** "data going as far back as 1962"; "over 80,000 Stocks, ETFs, and Mutual
  Funds" [T3]. US ETFs: yes [T3].
- **Delivery:** REST API, Mac-native. **Licence:** "Internal Use Only", "your own personal use"
  [T4].
- **Price: VERIFIED [T4].** Power **$30/month or $300/year "for individuals"**; limits 10,000
  requests/hour, 100,000/day, 110,360 unique symbols/month; $50/month or $499/year for internal
  commercial use.
- **Verdict: the best adjustment contract at the lowest price, but fails R4 by its own
  documentation.** If Tiingo ships permatickers it becomes a candidate again.

### 2.5 Polygon.io, now Massive

- `polygon.io/pricing` and the docs redirect 301 to `massive.com` (observed 2026-10-22) [P1, P2].
- **Delisted coverage: PARTIAL / unverified on the vendor's pages.** A third-party database project
  says Polygon serves delisted tickers "point-in-time by ticker, so renamed symbols must be handled
  by the user" [P3]; a forum user reports Polygon "does not appear to have dividend history for
  delisted businesses" [P4] (secondhand, unverified).
- **Total-return method: NOT provider-side.** The aggregates' `adjusted` flag is "Whether or not
  the results are adjusted for splits"; nothing about dividends [P2]. Dividends are a separate
  endpoint with `ex_dividend_date, cash_amount, historical_adjustment_factor`, "Records date back
  to January 15, 2000" [P5]. Total return would be OURS to build from a factor series, not the
  provider's series (R2 fails as specified).
- **History start: 2003-09-10 for bars.** "Records date back to September 10, 2003" [P2]. **Fails
  R1 for 2000 to 2003.**
- **Delivery:** REST API, Mac-native. **Licence:** every Stocks plan "Individual use"; Advanced
  "Non-pros only" [P1].
- **Price: VERIFIED [P1].** Stocks Basic $0 (2 years); Starter $29/month (5 years); Developer
  $79/month (10 years); **Advanced $199/month ("20+ Years")**, the only tier reaching 2003.
- **Verdict: fails R1 (start 2003), R2 (split-only bars) and R4 (ticker-keyed).**

### 2.6 Financial Modeling Prep (FMP)

- Every official page tried returned **HTTP 403** to this session (pricing, pricing-plans, the
  plan guide) [F1]. Nothing below is verified on the vendor's page.
- **Delisted coverage: a list, not a verified price history.** A "List Delisted Companies" endpoint
  exists (connector documentation) [F2]; whether delisted price series are served, and on which
  plan, was not found.
- **Price: UNVERIFIED.** A comparison site, "Last verified: Aug 20, 2026": Starter $22/month,
  Premium $59/month, Ultimate $149/month, billed annually; "over 30 years of historical data" [F3].
  A search snippet of FMP's own guide gives Starter "up to five years of historical data" and
  Premium "up to thirty years" [F4].
- **Identity across reuse:** symbol-keyed; nothing found.
- **Verdict: not assessable to the standard; the repo's 2026-06-25 inventory already said avoid.**

### 2.7 CRSP (via WRDS)

- **Status.** Morningstar agreed on 2025-09-23 to acquire CRSP from the University of Chicago for
  $375 million, "a growing share of CRSP's future opportunities in the commercial investment realm"
  [C1]; the acquisition is reported completed in February 2026 [C2]; `crsp.org` now redirects to
  Morningstar's index pages (observed 2026-10-22) [C3].
- **Access: institutional only.** WRDS: "All current faculty, staff, and students at a WRDS
  subscribing institution are eligible for access"; not eligible: "Alumni and community members,
  research colleagues and co-authors from other institutions"; "WRDS services are for academic and
  non-commercial research purposes only" [C4]. No individual subscription was found on any page.
- **Verdict: unavailable to an individual, and the academic licence would not cover a personal
  trading system even if a future affiliation opened a login.** It remains the reference standard
  the B-1 prereg meant by "a paid CRSP-class source" (§3.6); the candidates above are the
  retail-reachable approximations.

### 2.8 Others found, and why each is out

| provider | what was read | why out |
|---|---|---|
| **Finaeon** (the Global Financial Data brand) | "the most comprehensive, bias-free data on delisted US equities, beginning in 1792", "over 25,000 delisted stocks"; "Request a Demo" only; audiences listed are institutional [O1] | no published price, no individual channel; **not assessed** |
| **Algoseek** | Standard Daily OHLC "January 2007 to the present" on AWS Marketplace; survivorship-free daily coverage "since 1998" exists only as a QuantConnect-hosted dataset; pricing via sales [O2, O3] | daily product starts 2007 (R1); quote-gated; the 1998 set cannot leave QuantConnect |
| **Databento** | XNAS.ITCH "Available from 2018-05-01" [O4] | R1 |
| **MarketParquet** | one-time $79; US stocks, ETFs, futures "from 2000"; "delisted tickers included"; "split-adjusted"; parquet, any OS [O5] | split-only (R2); no event tables or ids stated (R3, R4); vendor-authored comparison page |
| **Kibot** | "Daily back to 1962"; "Unadjusted tape, split-adjusted, and fully-adjusted series"; one-time purchases; delisted coverage not stated on the page read [O6]; a competitor says the delisted set is "liquidity-filtered" [O5] | delisted coverage and a daily-package price unverified; **not assessed** |
| **QuantRocket EDI** | "No survivorship bias: includes active and delisted tickers", "Complete history since 2007", "Data may only be used within QuantRocket, no export" [O7] | R1, R9 |
| **Nasdaq Data Link EOD (QuoteMedia)** | a competitor's page says active-only [O5]; no official page served | **not assessed** |
| **Alpaca (held)** | IEX daily history starts 2020-07-27 (cutover proposal §2a) | R1 |
| **yfinance / Stooq (held)** | nothing for delisted names (cutover proposal §2) | R1 |

---

## 3. Comparison table

Legend: **V** verified on the vendor's page 2026-10-22; **U** unverified (reseller, forum,
comparison site, or a page that would not serve); **T** a trial question (§4.3).

| provider | delisted (R1) | TR method (R2) | event tables (R3) | id across reuse (R4) | start | US ETFs (R5) | delivery (R9) | personal licence (R7) | price for the qualifying tier (R8) | meets §1? |
|---|---|---|---|---|---|---|---|---|---|---|
| **Norgate Platinum** | yes, to 1990 (V) | provider back-adjusted, 4 modes incl. total return and capital-only (V) | splits yes; per-ex-date dividends (T) | yes: `-YYYYMM` suffix on delisted symbols (V) | 1990 (V) | yes, from 1993 (V) | Windows-only updater; parquet export; VM needed on a Mac (V) | yes, personal-only by licence (V) | **$346.50 / 6 mo, $630 / 12 mo (V)**; 3-week Platinum trial, 2-yr history, delisted included (V) | **yes**, pending T and the EULA |
| **Sharadar SEP+SFP** | yes, from 1998 (V datasheet 2019; U reseller) | `closeadj` / `closeunadj` fields exist (V); definition (U) | ACTIONS table exists (V shape); content (T) | yes: `permaticker` (V); SEP keyed by ticker (T) | 1998 (V/U) | yes, SFP add-on (V/U) | REST + bulk, Mac-native (V) | Personal account type exists (U) | **unverified**; login-gated; account free, no card (V) | **likely**, pending R2 definition and price |
| EODHD | partial: pre-2018 delistings "EOD only" (V) | adjusted_close splits+dividends (V) | only for post-2018 delistings (V) | no; reuse defect shown on ABS (U, 2026-05-07) | 1962 (V) | yes (V) | REST, Mac-native (V) | yes (V) | $19.99 / mo or $199 / yr; plan inclusion of delisted (U) | **no** (R3, R4) |
| Tiingo | partial: "tickers that have not yet been recycled" (V) | CRSP-style splits+dividends, raw + adjusted (V) | per-bar divCash, splitFactor (V) | no, "permatickers" future (V) | 1962 (V) | yes (V) | REST, Mac-native (V) | yes (V) | $30 / mo or $300 / yr (V) | **no** (R4) |
| Massive (ex-Polygon) | partial (U) | bars split-only; dividends separate (V) | dividends from 2000-01-15 (V) | no (U) | 2003-09-10 (V) | yes (V) | REST, Mac-native (V) | individual (V) | Advanced $199 / mo (V) | **no** (R1, R2, R4) |
| FMP | list endpoint only (U) | (U) | (U) | no (U) | (U) | (U) | REST | (U) | $22 / $59 / $149 per mo billed annually (U) | **no** (unassessable) |
| CRSP / WRDS | yes (the reference standard; not sourced here) | yes (reference; not sourced here) | yes (reference; not sourced here) | a permanent security id (reference; not sourced here) | pre-2000 (reference; not sourced here) | yes (reference) | institutional only (V) | academic, non-commercial only (V) | n/a to an individual (V) | **no** (R7, R8) |

---

## 4. Recommendation

### 4.1 The recommendation and the reason

**Norgate Data, US Stocks, Platinum, in two gated steps: the free three-week trial first, as the
pre-purchase coverage measurement; then, only if the trial clears its pre-registered line AND the
user lifts the 2026-05-12 data-spend gate, one six-month Platinum term at $346.50 as the
measurement purchase.** Sharadar is priced in parallel at zero cost (a free account, no card) as
the comparison arm, and overtakes Norgate only if its data dictionary verifies `closeadj` as the
provider's own dividend-and-split adjustment AND its personal-tier price is below Norgate's AND the
Windows VM is judged too high a cost.

Why Norgate over the field, in the order the requirements fail elsewhere:

1. **It is the only candidate that solves the identity problem by construction on the vendor's own
   page** (the `-YYYYMM` suffix on every delisted symbol). The class (i) names are the single
   repeating identity defect in the cache (SLE, POM written as the wrong entity; ABS and nine
   others lying entirely after the PIT name's exit). Tiingo excludes recycled tickers by its own
   sentence; EODHD reproduces our ABS defect; Massive and FMP are ticker-keyed. Sharadar's
   `permaticker` is the one peer, pending the trial.
2. **Total return is the provider's, in the modes the writer already needs** (TOTALRETURN,
   CAPITAL, NONE map to `adjusted=True`, `adjusted=False`, and the identity's unadjusted print).
   Massive makes us build the adjustment; EODHD cannot show its event record for a pre-2018
   delisting.
3. **Delisted coverage "essentially complete back to late 1992" with Platinum history to 1990**
   covers 2000 and the preferred 1999 start, where Massive (2003), Algoseek daily (2007), EDI
   (2007) and Databento (2018) do not.
4. **The price is verified and bounded**: $346.50 buys six months, which is longer than the
   cutover-and-re-run campaign needs; $630 a year if kept. It is personal-use by licence, which is
   what we are.
5. **The trial includes delisted securities**, so the pre-purchase measurement on the 75 (and the
   501) is possible at $0, which is what `[NN-FIRST-ARTIFACT]` asks of a new feed before anyone
   believes it.

### 4.2 Integration cost, in our terms

Everything below is propose-first and lands only after the trial clears; nothing is built on the
basis of this document. Estimates are agent-time, not money.

1. **A provider adapter under `engines/data_manager/`.** The writer's contract is already a plain
   callable: `Provider = (ticker, start, end, adjusted) -> OHLCV` and `Actions = symbol ->
   DataFrame[Dividends, Stock Splits]` (`tr_writer.py`). A `norgate_provider` implements both:
   `adjusted=True` → `priceadjust=TOTALRETURN`, `adjusted=False` → `CAPITAL`, the identity's
   unadjusted print → `NONE`; the actions record from `capital_event_timeseries` plus either
   Norgate's dividend record or the NONE/TOTALRETURN ratio steps (settled on the trial). The
   providers map stays single-keyed: `UNIVERSE_PROVIDER` flips from `"yfinance"` to `"norgate"`
   as a planned cutover, all files at once, never per file (the convention guard's rule).
2. **A symbol table, sibling to `yahoo_symbols.py`.** `norgate_symbols`: PIT ticker → Norgate
   symbol. For a live name the bare ticker; for a delisted name `TICKER-YYYYMM`, chosen among the
   symbols sharing the ticker by the PIT membership window (the entity whose last trading month
   is on or after the PIT exit). Every mapping is recorded with its evidence (name string, last
   bar, PIT window), the way BK → BNY was. A ticker with two Norgate entities and an ambiguous
   window is REFUSED, never guessed.
3. **An export step and a manifest of its own.** NDU runs on a Windows VM (local or EC2); a script
   exports every mapped symbol to parquet in the four modes the writer reads; the export directory
   gets its own sha256 manifest (the pattern of `scripts/gen_substrate_manifest.py` and
   `config/substrate_manifest.sha256`), pinned beside the candidate cache. The pipeline reads the
   export, never the NDU database, so the Mac and the cloud image stay vendor-free at run time.
4. **The identity rail against the current cache, unchanged.** Every one of the 654 fetchable
   files goes through `full_refetch(write=False)` first: last-bar LEVEL IDENTITY within 0.01 and
   the 252-bar overlap classification. The five LEGACY-W residuals (CAT +0.0019, ZTS +0.0043,
   LOW +0.0048, PG +0.0075, CVS +0.0087) are quoted beside Norgate's values, as the cutover
   proposal §6 already requires for yfinance. A refusal is diagnosed from Norgate's own event
   record; `LEVEL_TOLERANCE` is not moved for a new provider.
5. **New files for the names the cache never had.** The 75 unfetchable and the 501 never-fetched
   PIT members have no cached tail to agree with; they enter through the new-ticker path
   (`new_ticker_start` from the PIT entry date) with the provider's own record as their only
   evidence, and their write records say so. `config/data_gaps.json` declarations retire one by
   one, each only when the guard reads the hole filled.
6. **Census and referee.** A `provider` field and the retirement of the universal drip label are
   census changes by both producers, so a referee change; the Engine F gate and the honest-N
   registry take a new substrate id. **Every verdict re-runs** under `[NN-SUBSTRATE-REVERIFY]`:
   B-1 as a new pre-registration, the 2024 to 2025 verdicts, the deep re-verifications. That is
   the third substrate re-run in a year and it is the honest cost of (c), not a hidden one.
7. **The paper fleet is untouched.** The cutover proposal §3.1 established that the cutover
   changes no live trading input; the same holds here. Engine B and `live_trader/` are not in
   scope.

Rough agent-time: adapter and symbol table one unit; the export script and manifest one unit; the
rail pass and diagnosis one to two units depending on refusals; the census change one referee
unit; the re-run campaign a cloud campaign (≥ 4 cells, so AWS Batch by default). Money beyond the
subscription: the Windows VM (not priced here) and the cloud re-run campaign at the usual Batch
rates.

### 4.3 The pre-purchase measurement (the trial), pre-registered before it runs

The trial's two-year history limit means the deep-history identity CANNOT be verified before
paying. What the trial CAN prove, and the line it must clear, stated now:

- **H-c1 (existence and identity of the 75).** For each of the 75 unfetchable files, a Norgate
  symbol exists whose entity matches the PIT name (name string, last trading month on or after the
  PIT exit, and for the 9 that ended in 2026 the two-year overlap agrees with the cache within the
  rail). **Go line: at least 72 of 75 identity-matched, and 0 of the 10 later-entity names resolve
  to the WRONG entity.** Fewer than 72 is a STOP, with every miss named with Norgate's own reason.
- **H-c2 (the 501).** The share of the 501 never-fetched PIT tickers with a matching Norgate
  symbol, reported as a number, not gated (a lower bound on the coverage gain in §5).
- **H-c3 (the rail on live names).** For the live names, the last-bar identity and the two-year
  overlap against the cache: counts of APPEND / RESCALED / DIFFERENT_CONVENTION / over-tolerance,
  the way the cutover proposal §2b reports them. Any DIFFERENT_CONVENTION beyond the known
  split-only trio (AGG, EFA, VNQ) is diagnosed before any purchase.
- **H-c4 (the event record).** Whether Norgate exposes per-ex-date cash dividends, or the record
  must be derived from the NONE/TOTALRETURN ratio; and whether the derived record reproduces
  yfinance's ex-dates on a sample of 20 payers.
- **Also read during the trial:** the EULA (post-lapse usability of exports), and the Sharadar
  data dictionary and personal-tier price after a free login (the comparison arm).

N_trials consumed by the trial: 0 (no signal is scored; it is a data census).

### 4.4 The honest downside

- **Windows-only delivery on a Mac project.** A VM in the data path is a second machine to keep
  honest; the export manifest is the control, and the memory of baked-at-write-time defects
  (2026-10-15) says the export's END and last-bar LEVEL are read every time, never the row count.
- **A subscription, not a purchase.** Post-lapse usability of exports is unverified. If the EULA
  forbids keeping them, the honest price of (c) is $630 a year for as long as the substrate is
  canonical, not $346.50 once.
- **The deep history is paid for blind.** The trial proves identity and the recent tail; the
  1990 to 2024 total-return levels are checked only after the first $346.50.
- **A third substrate in a year.** Every verdict re-runs again, the honest-N registry gets a new
  id, and the re-run campaign is a cloud spend on top of the subscription.
- **A survivorship-free universe will lower the equity-book numbers.** That is the point, and it
  is stated here so no one reads it later as a regression: delisted names carry delisting returns
  that survivors do not.
- **The data-spend gate stands.** The user said on 2026-05-12 that data spend waits on the system
  making money or close to it. Nothing here argues that away; the paid step is the user's.

---

## 5. What the measurement program gains, concretely

Every figure here is the CURRENT measured deficit; the gain is realised only when the trial (§4.3)
and the purchased term confirm it. None of it is assumed.

- **The 46 declared names.** The 32 delisted files are restored to their last trading day with the
  delisting return in the series; the 10 later-entity files (ABS, BMC, CCE, CFC, GR, HAR, MHS, NCC,
  TEG, TIE) are replaced by the PIT entity's own history (Albertson's to 2006-06-02, not the 2019
  symbol); BBBY, PSKY and CPWR the same; FISV's 2025-11-12 provider gap is filled if Norgate holds
  the session. The 1,298 declared holes in 395 runs are re-measured and the declarations retire
  where filled. CA, SLE, POM and NFX, refused forever under the reused symbol today, get their PIT
  entity's `-YYYYMM` file.
- **Coverage in 2000.** File existence on 2000-01-31 rises from 261 of 495 members (52.7%) toward
  495, bounded by H-c2; month-end-bar coverage from the measured 38.4% toward that bound; the 207
  of 312 months below 80% shrink to whatever the deep-history pass leaves. The 368 lost
  member-month-ends over 66 names and the 180 stale member-months (158 selected by momentum_12_1
  then lost; B-1 §14) become real history.
- **R's EXIT amplifier retires.** The harness today treats a stale file's end as an exit at the
  last close, which biases the 2024 to 2025 wealth legs vs SPY DOWN (B-1 §3.6 caveat). With a
  delisted name's true last bar, an exit is an exit.
- **The pre-2018 drip replaced homogeneously.** Under the user's ruling (a) the drip stays
  everywhere, labelled, because only a delisted-capable source can replace it without splitting the
  universe on survivor status. Under (c) the whole 2000 to 2025 span is one provider, one
  convention: the 102 of 559 names whose pre-seam return moves by more than 1%/yr get their exact
  values, and the universal drip label retires from the census. That is the (a) → (c) path the
  ruling named.
- **The B-1 condition becomes satisfiable.** The prereg's §3.6 requires "re-verification on
  survivorship-complete data" before any clear counts, and the T-365 verdict is recorded as
  "CONSERVATIVE under an UPWARD survivorship bias". The null stands either way; what (c) buys is
  that the NEXT pre-registered run on the price vocabulary, or on a new modality, is measured on a
  substrate whose universe is the index's, not yfinance's.
- **An independent membership check.** Norgate's daily index constituents against our PIT
  parquet: a second witness for the 1,255 rows, found cheaply.

---

## 6. Decision for the user

The choices, with the verified price of each:

| choice | what happens | cost now | cost later |
|---|---|---|---|
| **(c-1) Trial now, decide after** (recommended) | Agent B runs §4.3 on the Norgate three-week Platinum trial (delisted included, 2-year history) and prices Sharadar on a free account; the result is a dated census doc with the go/stop line applied as written | **$0** (a Windows VM for NDU: not priced here; UTM or an EC2 Windows instance are the options) | none unless (c-2) is chosen |
| **(c-2) Trial, then one six-month Platinum term as the measurement purchase** | only if H-c1 clears AND the user lifts the data-spend gate: $346.50, the full-universe export, the rail pass on a copy, re-pin, the re-run campaign; a keep/lapse decision at month 5 | **$346.50** after the trial [N1] | $630 / year if kept [N1]; the cloud re-run campaign; the VM |
| **(c-3) Sharadar instead** | same as (c-2) on Sharadar, if the free login verifies `closeadj` as provider-side total return and a personal price below Norgate's; Mac-native, no VM | **unverified** (login-gated) | unverified |
| **(c-4) Defer (c)** | stay on (a) as ruled; the drip label stays; the 46 declarations stay; this document is the price on file | $0 | the survivorship caveat on every equity-book verdict stays |

What is asked of the user now: **(c-1) or (c-4)**. (c-2) and (c-3) are not asked today; they wait on
the trial's census and on the data-spend gate.

## 7. What we would NOT do

- **No mixed-convention universe.** Norgate for the 75 and yfinance for the rest is option (b)
  under another name: the writer keeps ONE universe provider for every file (cutover proposal §2a;
  a providers map without the universe provider is refused), and the flip is a planned cutover,
  all files at once.
- **No manual edits to the cache.** No hand-written files for the 75, no ×10 edits, no stitched
  histories. Every file is written by `full_refetch` under the rail or refused with its reason.
- **No loosening of the rail for a new provider.** `LEVEL_TOLERANCE` 0.01 and the 252-bar overlap
  stay; a disagreement is diagnosed from the provider's own event record (`[NN-FAIL-CLOSED]`).
- **No purchase before the trial census, and no trial result quoted before its artifact exists**
  (`[NN-FIRST-ARTIFACT]`): the go line is the numbers in §4.3, applied as written.
- **No vendor database in the measurement path.** The pipeline reads a manifested parquet export;
  the NDU database and the Windows VM are build-time only.
- **No silent degradation.** If a name is missing from Norgate it is declared with Norgate's own
  reason, never padded, never served from another provider.
- **No AI in this decision** (`[NN-AI-GATE]`): it is a data-integrity purchase, judged by the same
  gates as any other capability.
- **No deletion.** The yfinance adapter and the current cache are archived on cutover, never
  removed (`[NN-ARCHIVE]`).

---

## 8. Sources (all read 2026-10-22)

Norgate Data
- [N1] https://norgatedata.com/stockmarketpackages.php (the price table, the feature table, delisted and history extent per tier)
- [N2] https://norgatedata.com/subscribe/subscribe.php (package descriptions; "No commercial use - the data can only be licensed for personal use by individuals")
- [N3] https://norgatedata.com/data-package-faq.php (the `-YYYYMM` suffix and ENRNQ-200411; delisted coverage "essentially complete back to late 1992"; the four adjustment modes incl. "aka Total Return"; ETF coverage from 1993; daily index constituents)
- [N4] https://pypi.org/pypi/norgatedata/json (the package description: Windows-only NDU; priceadjust and padding options; `index_constituent_timeseries`, `capital_event_timeseries`, `dividend_yield_timeseries`; version 1.0.77)
- [N5] https://wealth-lab.com/Discussion/No-exact-date-for-delist-for-Norgate-data-11521 (2024-08-05: month-precision delisting in the symbol; "symbols are often reused")
- [N6] https://concretumgroup.com/how-to-construct-a-survivorship-bias-free-database-in-norgate-using-python/ (TOTALRETURN usage; `subtype1 == 'Equity'` filter; "Norgate Data only supports Python on Windows")
- [N7] https://norgatedata.com/subscribe/freetrial.php (three-week Platinum trial; 2-year history; delisted included; personal use; no repeat trials)

Sharadar / Nasdaq Data Link
- [S1] https://resources.quandl.com/a/res-hub/Sharadar_Datasheet_final.pdf (PDF metadata 2019-07-11; "More than 16,000 active and delisted tickers", "History from 1998")
- [S2] https://sharadar.com/ ("Active and delisted coverage extends back to the 90s"; "No credit card required")
- [S3] https://www.quantrocket.com/pricing/data/sharadar (reseller: 1998 start, delisted included, ETF add-on, S&P 500 constituents 1957; "Log in or create account to see pricing"; licence terms)
- [S4] https://www.r-bloggers.com/2021/08/exploring-stock-market-listing-mortality-since-1986/ (2021-08-28: "no de-listings of any companies between 1986 and 1998")
- [S5] https://data.nasdaq.com/api/v3/datatables/SHARADAR/SEP/metadata.json (SEP fields; status ON TIME; CONTINUOUS)
- [S6] https://data.nasdaq.com/api/v3/datatables/SHARADAR/SFP/metadata.json (SFP fields)
- [S7] https://forum.numer.ai/t/sharadar-core-bundle/4856 (2022-01-27: `close` observed split-adjusted only; no vendor reply)
- [S8] https://data.nasdaq.com/api/v3/datatables/SHARADAR/ACTIONS/metadata.json (ACTIONS filters and primary key)
- [S9] https://data.nasdaq.com/api/v3/datatables/SHARADAR/TICKERS/metadata.json (`permaticker`, `isdelisted`, `firstpricedate`, `lastpricedate`, `relatedtickers`)
- [S10] https://help.data.nasdaq.com/category/466-pricing and https://data.nasdaq.com/databases/SEP (the product and pricing pages rendered only a title to this session; the help-center listing says pricing may show only "Contact Sales" by account type)

EODHD
- [E1] https://eodhd.com/financial-apis/api-for-historical-data-and-volumes (adjusted_close definition; 1962 start; TWTR.US example; plan availability)
- [E2] https://eodhd.com/financial-apis/delisted-stock-companies-data-2 (coverage by delisting era: "Before 2018: EOD only"; `delisted=1`; rename endpoint US-only)
- [E3] https://incoherency.co.uk/notes/20260507.html (2026-05-07 practitioner note; the ABS.US / Albertson's reuse case; about £20/month)
- [E4] https://eodhd.com/pricing (Personal plans and prices; "Dividends & splits" rows; no delisted row seen)

Tiingo
- [T1] https://www.tiingo.com/documentation/general/symbology ("delisted data for tickers that have not yet been recycled"; "permatickers" as a future)
- [T2] https://www.tiingo.com/documentation/end-of-day (CRSP methodology; adjClose, divCash, splitFactor; raw and adjusted)
- [T3] https://www.tiingo.com/products/stock-api ("as far back as 1962"; "over 80,000 Stocks, ETFs, and Mutual Funds")
- [T4] https://www.tiingo.com/about/pricing (Power $30/month or $300/year; limits; "Internal Use Only")

Massive (formerly Polygon.io)
- [P1] https://massive.com/pricing (via 301 from https://polygon.io/pricing; Stocks plans, years of history, "Individual use", "Non-pros only")
- [P2] https://massive.com/docs/rest/stocks/aggregates/custom-bars (`adjusted`: "adjusted for splits"; "Records date back to September 10, 2003")
- [P3] https://github.com/shinathan/polygon.io-stock-database (third party: delisted data present, "point-in-time by ticker")
- [P4] https://community.developers.lseg.com/discussion/78518/which-api-is-best-for-fundamentals-data-from-the-last-15-20-years (a user report on missing delisted dividend history; unverified)
- [P5] https://massive.com/docs/rest/stocks/corporate-actions/dividends (fields; "Records date back to January 15, 2000")

Financial Modeling Prep
- [F1] https://site.financialmodelingprep.com/developer/docs/pricing , https://site.financialmodelingprep.com/pricing-plans , https://site.financialmodelingprep.com/insights/platform/how-to-choose-the-right-financial-modeling-prep-plan-for-your-workflow (each returned HTTP 403 to this session)
- [F2] https://docs.nexla.com/user-guides/connectors/financial_modelling_api ("List Delisted Companies" endpoint)
- [F3] https://multiples.vc/compare/fmp-api-alternatives ("Last verified: Aug 20, 2026"; Starter $22, Premium $59, Ultimate $149 per month billed annually; unverified)
- [F4] search snippet of [F1]'s plan guide (Starter five years, Premium thirty years; unverified)

CRSP / WRDS
- [C1] https://news.uchicago.edu/story/morningstar-inc-agrees-acquire-center-research-security-prices-uchicago (2025-09-23; $375 million; the commercial direction)
- [C2] https://pulse2.com/morningstar-expands-index-business-with-365-million-crsp-acquisition (completion reported February 2026; the $365 million figure differs from the announced $375 million)
- [C3] https://www.crsp.org/products/ (301 to https://indexes.morningstar.com/morningstar-market-indexes, observed 2026-10-22)
- [C4] https://guides.libraries.psu.edu/WRDS (eligibility; "academic and non-commercial research purposes only")

Others
- [O1] https://finaeon.com/product/us-delisted-equities/ ("over 25,000 delisted stocks", "beginning in 1792"; demo request only)
- [O2] https://aws.amazon.com/marketplace/pp/prodview-7u36yvhslofqm and sibling Algoseek listings (Standard Daily OHLC "January 2007 to the present"; sales contact)
- [O3] https://www.quantconnect.com/docs/v2/writing-algorithms/datasets/algoseek/us-equities (survivorship-free daily "since 1998", QuantConnect-hosted)
- [O4] https://databento.com/catalog/us-equities and https://databento.com/datasets/XNAS.ITCH ("Available from 2018-05-01")
- [O5] https://marketparquet.com/vs/norgate , https://marketparquet.com/vs/kibot , https://marketparquet.com/vs/quandl (vendor-authored comparisons; one-time $79; split-adjusted; the Kibot and QuoteMedia claims are this vendor's)
- [O6] https://www.kibot.com/ ("Daily back to 1962"; three adjustment series; one-time purchases)
- [O7] https://quantrocket.com/pricing/data/edi (EDI: delisted included, "since 2007", no export outside QuantRocket)
- [O8] https://algoseek.com/blog/survivorship-bias-in-backtesting-what-to-ask-a-data-vendor/ (the vendor checklist: delisting returns, index membership from the provider, a spinoff walkthrough, ticker reuse, "a persistent security identifier that follows a company through ticker changes, mergers and delistings")

Repository sources
- `docs/Sources/proposal_substrate_cutover_exact_tr_2026-10-15.md` §1, §2, §2a, §2b, §3.1, §6
- `docs/Sources/proposal_level_rail_last_bar_identity_2026-10-15.md` §2, §8
- `docs/Sources/proposal_stale_and_holed_files_guard_2026-10-15.md` (the 46-name declaration set)
- `docs/Sources/prereg_b1_raw_signal_decile_2026-09-30.md` §3.6 and the T-365 ledger row
- `docs/State/CURRENT_STATE.md`, the 2026-10-22 and 2026-10-15 blocks
- `docs/State/forward_plan.md` (the 2026-05-12 data-spend gate)
- `docs/Sources/free_public_data_exploration_inventory_2026_06_25.md` and its 2026-06-30 pass-2 (the earlier Norgate and Sharadar notes; the EODHD/FMP avoid)
- `engines/data_manager/tr_writer.py` (`Provider`, `Actions`, `full_refetch`, `LEVEL_TOLERANCE`, `OVERLAP_TAIL_BARS`, `UNIVERSE_PROVIDER`)
- `config/data_gaps.json` (46 declarations, 19 `ends_at_delisting`), `config/level_declarations.json`
- `data/universe/sp500_membership_pit.parquet` and `data/processed/` in the main tree, read-only on 2026-10-22 (1,255 rows, 1,202 tickers; 730 files; 501 PIT tickers without a file; 2000-01-31: 495 members, 261 with a file)
