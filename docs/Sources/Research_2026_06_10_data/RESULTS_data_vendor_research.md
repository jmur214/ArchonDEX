# RESULTS — data-source hunt (RESEARCH MODE; all prices verified on live pages 2026-06-10)

> Provenance: the user ran `PROMPT_data_sources.md` with the deep-research feature.
> Prices verified on vendor pages 2026-06-10; login-walled prices flagged unverified,
> not guessed. Director-extracted actions tracked in session todos. Key correction on
> the record: **Norgate Platinum (the tier that actually fixes survivor bias) is USD
> 630/yr — far above the director's stale priors. Silver/Gold ($270/$360) do NOT
> include delisted data and are useless for our use case.**

## TL;DR (researcher's)
- Single highest-value PAID purchase: **Norgate US Stocks Platinum, USD 630/yr**
  (only retail product ≤$650/yr with BOTH PIT historical index constituents AND
  delisted price histories w/ delisting returns, back to 1990). Catches: Windows-only
  proprietary DB, personal-use-only, **data inaccessible the moment the subscription
  lapses** (verbatim from norgatedata.com), VM counts as a machine, no remote query.
- **Eliminate the larger share of survivor bias for $0 first:** free GitHub repos
  (fja05680/sp500, riazarbi/sp500-scraper, hanshof/sp500_constituents) give PIT
  S&P 500 membership back to 1996; EDGAR's own structured datasets give
  production-grade Form-4/8-K/13F/short-interest panels with no vendor.
- The one thing free CANNOT give: **delisting RETURNS** (that's the $630).
- **Do NOT pay for intraday yet.** IEX = 3.2% of consolidated volume (Q4 2025) —
  real skew for volume/imbalance features, tolerable for price-shape features.
  Cheapest consolidated fixes when needed: Databento pay-as-you-go ($125 free
  credits; Standard $199/mo) or Polygon Stocks Starter $29/mo.

## Verified pricing table (checked 2026-06-10)
- Norgate: Silver $270/yr (listed-only, 10yr) · Gold $360/yr (listed-only, 20yr) ·
  **Platinum $630/yr (delisted + historical constituents, 1990+)** · Diamond
  $787.50/yr (1950+). 6-month ≈55% of annual. No first-year discount. Futures/Forex
  separate packages (not price-verified). ~25,222 delisted securities (1950–2022 doc).
- EODHD: All-World $19.99/mo; All-in-One $99.99/mo; commercial internal-use $399/mo.
  Constituents history only ~12yr.
- Tiingo Power: $10/mo (one page-capture rendered $30/mo — verify at checkout).
- Polygon (rebranded "Massive" Oct 2025): Stocks Starter $29/mo (15-min-delayed,
  5yr) / Developer $79/mo (10yr). Flat files included.
- Databento: $125 sign-up credits; usage-based $/GB; flat Standard $199/mo (2025
  restructure). Permissive license incl. redistribution.
- optiondata.org: $59/mo (EOD options all US symbols since 2002; free 2013 sample).
- OptionsDX: free EOD chains (limited symbols); cheap intraday (~$5/15-min/yr/symbol).
- ORATS: one-time historical purchase via Nasdaq Data Link (OSMV, 2013+); API
  $99/mo delayed / $199/mo live. Users report sparse pre-2014 data.
- CBOE DataShop: per-order; index bid/ask requires CGI license ("fees start at
  $1k/month"); Intraday Open-Close $2,000/mo. Free index family (VIX/VIX9D/VIX3M/
  VVIX/SKEW) + free put/call ratio stay free.
- UNVERIFIED (login-walled): Sharadar SEP / Core US Bundle (historically ~$30/mo /
  ~$150/mo — explicitly unverified today); FMP tiers (JS-gated; 3rd parties ~$99/mo+);
  FirstRate/Kibot.

## Free infrastructure (the months-1-2 plan, $0)
- **PIT S&P 500 membership:** fja05680/sp500 (Clenow base + maintained changes) +
  Wikipedia revision-history cross-check → `in_index` boolean per (ticker,date),
  1996+. Converts deep-window results from "upper bound" to membership-correct.
- **SEC Insider Transactions Data Sets** (Form 3/4/5 flattened XML, quarterly,
  2006+) + **Financial Statement Data Sets** (all XBRL numerics; reprocessed Dec
  2024) + full-text search + daily indexes (~10 req/s, mandatory User-Agent).
  EDGAR sufficiency verdict: production-grade panels achievable vendor-free.
  Breakpoints: amended filings (4/A, 8-K/A) dedup; quarterly-set lag (use daily
  indexes for freshness); 13F CUSIP→ticker mapping mess; pre-2006 Form-4 absent.
- **Positioning (start archiving NOW — shallow histories):** FINRA Reg SHO daily
  short volume (TRF/ADF/ORF files must be combined; short VOLUME ≠ short interest),
  FINRA bi-monthly short interest, SEC FTDs (2008+), CFTC COT (1986+), AAII weekly
  sentiment (1987+, free login, sentiment.xls), NAAIM exposure (2006+), FINRA
  margin debt.
- **Stooq reality-check:** NASDAQ ~4,652 + NYSE ~3,627 + AMEX ~302 + ETFs; close is
  split+dividend adjusted (verified via AAPL 4:1 2020); bulk-ZIP only (~333MB US
  daily); survivor-skewed, occasional silent adjustment gaps. Workhorse, not
  survivor-bias-free.

## LICENSE TRAPS (critical for our AWS Batch/Docker pipeline)
- **Norgate is the dangerous one:** personal-use-only + Windows-only proprietary DB
  + no remote/networked query + VM-counts-as-machine + data dies on lapse. **Baking
  Norgate data into private AWS Docker images is hard to reconcile with its terms —
  treat as NON-COMPLIANT unless written clarification obtained.** This is a real
  architecture conflict, not a nuance.
- EODHD/Tiingo/FMP personal plans: internal personal use; a solely-controlled cloud
  VM generally OK; sharing/redistribution not.
- Sharadar: professional vs non-professional licensing distinction.
- **Safe to bake into images: SEC/FINRA/CFTC/AAII/NAAIM + the GitHub constituent
  repos (public domain / open data).**

## Quality traps
Stooq (pre-adjusted close, silent gaps, no API); Alpaca IEX (~3% volume → skewed
volume/imbalance features); yfinance (instability/rate limits); ORATS (sparse
pre-2014; option-snapshot vs underlying timing mismatches → put-call-parity
violations); cheap options vendors generally (underlying not synced to snapshot).
Cross-asset: free/cheap continuous-futures (old Quandl Stevens) is DEAD post-Nasdaq
acquisition; QuantConnect hosts but forbids download; free gov't archives give
positioning (COT) and rates/FX (FRED), not futures prices — multi-decade futures
prices = Norgate Futures package (paid, unverified price) or institutional feeds.

## The researcher's staged roadmap (opinionated)
- **Months 1-2 ($0):** PIT membership layer + EDGAR event panels + positioning
  archiving (start hoarding the shallow series immediately).
- **Month 3 ($630, GATED):** Norgate Platinum — IF AND ONLY IF membership-corrected
  backtests still show edge. Take the 3-week free trial first and validate the
  Windows/Python(`norgatedata`) integration against our AWS pipeline BEFORE paying
  (the Windows-only DB is the real adoption risk, not the price).
- **Months 4-6 (≤$200, demand-driven):** Databento pay-as-you-go for targeted
  consolidated intraday only if IEX-skew demonstrably corrupts a feature we rely
  on; optiondata.org $59/mo only on a formal options-fork commitment.
- Core principle: **spend nothing until the free membership layer proves the edge
  survives a bias-corrected universe; then spend exactly once, on delisting
  returns.**

## Q&A highlights (abridged)
Q1: nothing ≤$300/yr kills survivor bias with delisting returns → the $0 membership
layer is the highest-value "acquisition"; at ≤$650/yr the community converges on
Norgate Platinum. Q3: no free delisting-returns path exists. Q4 community usage:
PIT = free GitHub repos + Sharadar; delisted EOD = Norgate (AmiBroker/Python crowd)
or Sharadar SEP (pandas crowd); intraday = Polygon/Databento with Alpaca free as
entry. Q6 post-cutoff: Databento flat-rate restructure (+$125 credits); Polygon
"Massive" rebrand (Oct 2025); EODHD launched options-with-greeks + an MCP server
for AI agents; Norgate tiers/lapse policy unchanged.
