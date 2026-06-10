# Research prompt — data-source hunt for a retail systematic trading research platform (2026-06-10)

> Paste everything below the line to the research agent verbatim. Results get filed
> in this folder when they come back.

---

You are a quantitative-data researcher with live web access. I am an AI development
director for a retail systematic trading research codebase; my knowledge has a
training cutoff and **my pricing/availability beliefs about data vendors are stale
and have repeatedly been wrong** (notably: I have repeatedly misquoted Norgate's
pricing as far cheaper than it actually is). **Do not trust any price, tier name, or
product claim I imply — verify EVERYTHING against the vendor's live pricing page as
of today, and cite the URL + the date you checked, for every price you report.**
Your job: find the best data sources for the specific needs below, with a hard
free-first bias, and answer my gap-bridging questions.

## THE PROJECT (context you need)

A single-developer autonomous trading research system (Python/pandas, backtest-only
today; Alpaca brokerage planned for eventual paper/live). Deployment: BOTH a taxable
individual account (Illinois) AND a Roth IRA. Capital: ~$5K now, $50K→low-100s K if
proven. Statistical discipline is institutional-grade (block-bootstrap CIs, deflated
Sharpe, minimum-backtest-length gating, FF5+Mom factor decomposition with HAC, strict
reproducibility pinning) — the bottleneck is NOT methodology, it's DATA BREADTH.

**Current data estate (do NOT recommend what we already have unless a strictly
better/cheaper variant exists):**
- **Stooq** free EOD: US equities (split-adjusted), survivors back to ~1962-1970;
  ETFs (SPY/TLT/GLD/USO/UUP/EEM/IEF/DBC...); VIX-family indices. Our workhorse.
- **Alpaca free tier**: IEX-feed daily + minute bars (~2016+), dividend-adjusted
  daily merged with Stooq into our canonical substrate. WebSocket available.
- **FRED** macro; **Kenneth French Data Library** factor returns; **CFTC COT**.
- **SEC EDGAR**: a Form 10-12B spinoff scraper is built; Form-4 partially used;
  8-K/13F untouched so far.
- **SimFin FREE** fundamentals: ~3,984 tickers, 2020-2025 point-in-time-ish, banks
  missing on the free tier.
- **Universe**: S&P-class large/mid-cap SURVIVORS only — survivorship bias is our
  #1 measurement caveat (every deep-window result is an upper bound). 48 delisted
  names hand-recovered once via Alpaca; no systematic delisted coverage.

**Hard constraints:** free strongly preferred; paid only with a compelling case —
and then I need ACTUAL current prices. Retail/personal-use licensing must permit
local storage + backtesting (flag academic-only or institutional-only sources).
Python-accessible (API or bulk files). No data that can't be timestamp-disciplined
(we enforce strict no-lookahead).

## THE SIX NEEDS, RANKED

### Need 1 — Point-in-time universe + delisted coverage (kills survivor bias; highest value)
Historical index/universe MEMBERSHIP with dates (S&P 500 minimum; 1000/3000-class
better) AND delisted-stock price histories INCLUDING delisting returns, ideally
1990s→present. Price-check at minimum: Norgate Data (every subscription level —
actual current AUD/USD prices + exactly which package includes historical
constituents + delisted securities), Sharadar/Nasdaq Data Link equity bundles,
EODHD, Tiingo, FMP, Polygon. Also hunt FREE reconstructions: Wikipedia
revision-history constituent scrapes, maintained GitHub historical-constituent
repos, academic postings, QuantConnect/QuantRocket in-platform data usable for
research export. For each: how complete is delisting-RETURN coverage (not just
membership lists)?

### Need 2 — Event/filing data (our newest alpha lane; mostly EDGAR-native?)
Form-4 insider transactions (bulk, parseable, historical depth), 8-K filings by
item-type with timestamps, 13F holdings (parsed, point-in-time), index add/delete
announcements, earnings-call transcripts, earnings guidance/estimates history.
Key question: how far does FREE EDGAR (full-text search API, daily indexes, the
SEC's own structured datasets — e.g., their Financial Statement and insider data
sets) actually get us before any vendor is worth it? Practical pitfalls (amended
filings, late filings, rate limits, parsing landmines)? Cheap vendors that just
sell cleaned EDGAR (and their actual prices)?

### Need 3 — Wider/cheaper full-US price universe (small/micro-cap inclusive)
Full US common-stock EOD including delisted, vs our large-cap survivors. Same
vendors as Need 1 plus anything specialist. Also: what does Stooq's full US
coverage ACTUALLY include beyond what retail folklore says (delisted? micro-cap?
known data-quality issues)? Any Stooq-like free gems (that's how we found our
current workhorse — official exchange daily files, national-archive datasets,
academic mirrors)?

### Need 4 — Intraday history for FEATURE-BUILDING (not HFT)
We want minute/5-minute bars to compute DAILY features (opening-range stats, volume
profile, auction imbalance, intraday realized-vol shape) — not to trade intraday.
Alpaca free = IEX-only from ~2016: how badly does IEX-only skew volume/positioning
features vs consolidated tape, and what's the cheapest consolidated-tape-quality
history (Polygon current prices, Databento actual per-GB/flat-file prices, FirstRate,
Kibot, anything free)? Depth target: 2008+ ideal, 2016+ acceptable.

### Need 5 — Options/vol-surface history (a strategic fork option for us)
Cheapest credible EOD options chains with history (strike/expiry/IV/greeks/OI), or
failing that, vol-SURFFACE summaries. CBOE DataShop actual prices; ORATS actual
prices; anything free beyond the CBOE-published index family (VIX/VIX9D/VIX3M/VIX6M/
VVIX/SKEW — which we can already get): free delayed chains worth archiving
going-forward? OptionsDX-class cheap historical bundles — legit? quality?

### Need 6 — Positioning/sentiment (free-first)
FINRA short interest + Reg SHO daily short volume + fails-to-deliver (all free? how
to bulk-pull), put/call ratios (post-CBOE-archive-changes: what's still free?),
margin debt, AAII / NAAIM sentiment (free tiers?), anything genuinely predictive-
grade that's free that retail quants actually use.

## MY GAP-BRIDGING QUESTIONS (answer each explicitly)

1. **The single highest-value purchase:** if forced to pick exactly ONE paid data
   product ≤ ~$300/yr for this project, what does the retail-quant community
   actually converge on in 2026, and why? (And is the answer different at ≤$600/yr?)
2. **Norgate, specifically:** current actual pricing for every tier, what each
   includes (US delisted? historical constituents? futures?), the renewal-vs-
   first-year structure, and the data-hostage question (what happens to stored data
   if the subscription lapses).
3. **Delisting returns for free:** does ANY free path give usable delisting
   returns (the half of survivor bias that membership lists alone don't fix)?
4. **Community consensus:** what do r/algotrading, QuantConnect forums, the
   pysystemtrade community, and similar actually USE today for (a) PIT universes,
   (b) delisted EOD, (c) intraday history? Name threads/posts if possible.
5. **EDGAR sufficiency:** can a competent engineer build Form-4/8-K/13F panels
   purely from free SEC infrastructure at production quality? What breaks first?
6. **New since 2025:** any sources/products launched or repriced in the last ~18
   months that someone with a Jan-2026 training cutoff would not know about?
7. **License traps:** which recommended sources forbid local storage, redistribution
   to a cloud VM (we run AWS Batch backtests — data gets baked into private Docker
   images on our own account; does that violate anyone's retail license?), or use
   after cancellation?
8. **Quality traps:** known data-quality landmines per source (split/dividend
   handling, IEX-volume skew, Stooq quirks, yfinance instability, etc.).
9. **Cross-asset depth:** cheapest path to multi-decade futures-or-proxy daily
   series (rates/commodities/FX) beyond the ETF-inception-limited (~2006+) window
   we have — including any free academic/government archives.
10. **The roadmap question:** given our exact situation (survivor-biased large-cap
    daily substrate, free-first, $5K live capital, strong infra), what data
    acquisition SEQUENCE over the next 6 months gives the most research power per
    dollar? Be opinionated.

## OUTPUT FORMAT

1. Per-need ranked tables: source | what you get | ACTUAL price + tier + URL + date
   checked | PIT/delisted quality | license notes for retail+cloud-backtest use |
   integration effort.
2. The top-5 "do these first" list (free moves first), each with a one-paragraph
   rationale and concrete first step.
3. The traps list (quality + license).
4. Explicit answers to all 10 numbered questions.
5. A "what I couldn't verify" section — if a price/claim is behind a sales wall,
   say so rather than guessing. NEVER report a price you did not see on a live page
   today.
