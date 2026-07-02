# Free / Public Data — Exploration Inventory (2026-06-25)

**What this is:** a vetted candidate map of FREE / PUBLIC data sources for a *gated, low-prior* alt-data
EXPLORATION track, governed by `[NN-AI-GATE]` (separate track, no live integration, same falsification
gates as everything else, prior LOW). Produced by a research agent (web-verified). **This is NOT a
commitment to build** — it's the candidate set for the post-verdict fork decision (alongside the risk-model
work and the bought-MF sleeve). Scope: retail, daily-frequency, US equity.

## The one filter that kills most candidates
**Does a FREE *historical* archive exist with knowable as-of timestamps, so it can be backtested without
lookahead?** A source you can't backtest with point-in-time (PIT) discipline is near-worthless here — that
is exactly why the VADER news edge died (live-only, no PIT corpus). This filter is weighted above
everything else. Two priors carried in: (1) Form-4 insider clustering was BUILT + TESTED here (T-144) and
REFUTED → the "follow a disclosed trade" family inherits a skeptical prior; (2) the price-signal vocabulary
is H0-exhausted → a candidate is only interesting if it carries info price/fundamentals genuinely can't see.

## Ranked candidates (free AND PIT-backtestable AND orthogonal AND plausibly-non-arbitraged)

| Rank | Source | Free | PIT-honest | Orthogonal | Edge plausibility (post-decay) |
|---|---|---|---|---|---|
| **1** | **EDGAR 10-K/10-Q language change ("Lazy Prices")** | Yes | **Exact** (SEC acceptance ts) | **High** (doc-change info) | Real lit, decayed ~50%, residual plausible |
| **2** | **GDELT news/event intensity** | Yes | Ingest-time (careful) | High | Re-opens the news-PIT gap VADER couldn't; noisy |
| **3** | **13D/G activist post-filing drift** | Yes | Exact | Medium | Durable lit; disclosed-trade prior |
| **4** | **USASpending federal contract awards** | Yes | Modelable lag | High | Uncrowded, speculative, entity-mapping risk |
| **5** | **USPTO patents (KPSS value)** | Yes | Exact | High | Real but slow/priced; overlay not daily signal |
| **6** | **Wikipedia pageviews** | Yes | Clean (daily, 2015+) | Medium | Decayed attention proxy |
| **7** | **Short-interest *surprise* (FINRA)** | Yes | Yes (2014+) | Medium | Mostly arbitraged; surprise-residual only |

**SKIPs (with reason):** options implied skew/term-structure — *most orthogonal info type on the list, but
NO free historical PIT surface exists* (CBOE/ORATS/IVol all paid) → untestable under the free constraint,
the same wall that killed VADER; **#1 thing to revisit if a budget for one paid dataset opens.** · 13F clones
(decayed + 45-135d lag) · congressional trades (lag eats the window + clean history paywalled + disclosed-trade
family) · Google Trends (values renormalized to the query window → lookahead PIT-trap + non-replication) ·
free earnings transcripts (PIT-fragile timestamps; the orthogonal content is better captured via EDGAR text) ·
fund flows (free tier too coarse for single-name) · FRED macro (covered by the existing HMM regime stack — use
to enrich conditioning, not as standalone alpha).

## Top-3 minimal honest backtest sketches

**#1 — Lazy Prices (10-K/10-Q language change).** Compute consecutive same-type-filing text similarity
(cosine TF-IDF + Jaccard + section diffs on Risk Factors / MD&A); rank cross-sectionally monthly; retail-real
form = long-only "high-similarity / non-changers" tilt. **PIT trap:** key every signal to the SEC *acceptance
timestamp*, never period-end or cover date; build the prior-filing baseline only from filings accepted as of
the decision date; never use the restated 10-K/A. **Gate:** block-bootstrap `ci_low` net-of-retail-cost Sharpe
must clear the kill threshold (floor `ci_low ≥ 0.4`; real bar = beat-the-robo net of cost/tax); pre-register
N_trials vs the MBL window (`[NN-MBL]`); charge the short leg's borrow honestly; if it only survives in
untradeable micro-caps it FAILS.

**#2 — GDELT news/event intensity.** Per ticker per day, aggregate article count + GKG tone + event intensity
for the mapped entity; test abnormal *intensity* (vs trailing baseline) far more than the tone score. **PIT
trap:** use ingest timestamp as as-of + lag to next open; resolve entity→ticker using only names/aliases that
existed as of that date (no survivorship; include delisted); restrict to a stable post-2015 window. **Gate:**
same CI-aware net-of-cost bar + must survive a shuffled-timestamp placebo + must beat a price-only momentum
baseline on the SAME names (else it adds no orthogonal value).

**#3 — 13D/G activist post-filing drift.** Enter at the *next* open after filing acceptance, hold 6-12mo,
measure abnormal return vs FF + the existing book; the hypothesis is the *drift after the pop*, not the pop.
**PIT trap:** enter strictly after the announcement-day move is in price; don't let the (-20,+20) window leak
into entry. **Gate:** net-of-cost `ci_low` clears the kill threshold AND the drift survives stripping the
announcement window AND it beats the disclosed-trade null *decisively* (given T-144), not marginally.

## Honest prior (stated plainly)
The realistic prior that ANY of these clears a beat-the-robo bar, net of retail cost and after-tax, is **LOW —
~10-20% for the single best candidate, lower for the rest.** Reasons are structural: every source with strong
*published* alpha has been public 6-15 years and the decay literature (McLean-Pontiff ~50% post-publication;
Hou-Xue-Zhang ~93% after costs) predicts most headline alpha is gone; the *uncrowded* sources (USASpending,
raw GDELT) are uncrowded partly because they're noisy/hard to PIT-clean; the most orthogonal info type (options
skew) is the one with no free PIT history. **The likeliest durable output of this track is another
well-measured refutation that tightens the apparatus — which is a legitimate success under `[NN-AI-GATE]`, not
a failure.**

**The one to bet on first: EDGAR "Lazy Prices."** The only candidate simultaneously free, *exactly* PIT-able,
genuinely orthogonal (document-change info price literally cannot see), backed by a top-journal result
(Cohen-Malloy-Nguyen, J. Finance 2020), and sitting in the new-data/text modality `[NN-AI-GATE]` flags as the
only place residual value plausibly lives — and where an LLM earns a legitimate role (reading filings to build
features, not modeling exhausted price data). Known weakness: decay since the 2014 sample + a hard-to-trade
short leg → test the long-only non-changers tilt.

## Fresh data caveats (verified 2026-06)
- **FRED** restricted ICE BofA credit-spread series (e.g. `BAMLH0A0HYM2`) to a rolling ~3-year window (~Apr
  2026) — deep HY-OAS history may now survive only in ALFRED/Wayback snapshots. Verify depth before relying.
- **EDGAR EFTS** full-text API is free, no key, 10 req/s, requires a User-Agent header; full text 2001→present;
  free tooling `edgartools` (MIT) + Loughran-McDonald dictionary (Notre Dame SRAF).

## Key sources
Cohen-Malloy-Nguyen *Lazy Prices* (NBER w25084 / J.Finance 2020) · Loughran-McDonald / SRAF (Notre Dame) ·
SEC EDGAR EFTS API + edgartools · GDELT Project (BigQuery, 1979+) · FINRA Equity Short Interest + "surprise in
short interest" · 13D/G empirical (Columbia Law Review) · 8-K attention (Notre Dame) · 13F alpha (SSRN 3459526) ·
Kogan-Papanikolaou-Seru-Stoffman patent value · USAspending API · Preis-Moat-Stanley Google Trends (+ "Big
Data, Small Pickings" non-replication) · Moat et al. Wikipedia · Hou-Xue-Zhang *Replicating Anomalies* (decay).

---

## Reddit deep-dive addendum (2026-06-25)
Source: 11 r/algotrading threads (+ substitutes), 3 research agents. (Reddit hard-blocks the sandbox IP;
content recovered via Pushshift/arctic-shift mirrors. Two newest thread IDs unrecoverable: "API data for
futures", "consistent profitability".) New finds + corroboration:

**New FREE + actionable**
- **FRED daily market-based credit/vol series as REGIME-GATE features (highest-conviction free takeaway).**
  4+ practitioners independently: HY credit spread `BAMLH0A0HYM2` (ICE BofA HY OAS) beats yield-curve slope as
  a *faster* regime signal; also IG/HY OAS spread, **VIX/VIX3M term-structure ratio** (contango/backwardation),
  DXY momentum, Fed-funds-futures implied rates. Daily, free, low-revision (market-observable). **Slots directly
  into our validated regime=overlay/sizer thesis (T-220/221) — it enhances the one lever that already works.**
  Caveat: `BAMLH0A0HYM2` restricted to ~3yr rolling on FRED (~Apr 2026) → deep history via ALFRED/Wayback;
  FRED treasury rates lag a few days (fine for backtest).
- **finagg** (github.com/theOGognf/finagg, MIT) — wraps BEA+FRED+SEC EDGAR, normalizes XBRL tags into features,
  local SQLite. Solves the XBRL-normalization build for any EDGAR/Lazy-Prices work. Most useful repo surfaced.
- **Bulk SEC "Financial Statements & Notes" ZIP dumps > the REST API** (API silently 404s common tags); compute
  SUE yourself from raw XBRL. Free technique for the fundamentals/Lazy-Prices direction.
- **Stooq** — free bulk daily OHLCV, 30+yr US (price-only, not orthogonal; a free yfinance-class backup).

**The OPTIONS gap (most-orthogonal, our painful paywall) — the crack**
- **Databento — $125 free signup credit + BUY-AND-OWN per-GB pricing.** You buy the files (keep forever, no
  TOS-retention ambiguity). Concrete: "15yr futures for $2", "1mo MBP-10 ~$1"; covers OPRA options. Avoid the
  OHLCV schemas ($70-190/GB) — pull raw MBP/trades + aggregate. **THE cheap, ownable, orthogonal
  historical-options path that fits our constraint** → a scoped spike (single-digit $, verify PIT-usability).
- **ORATS** ~$2K one-time, 2-min options ~10TB (one-time, no TOS ambiguity, top of budget). **ThetaData**
  ~$200/mo OPRA-since-2012 NBBO (recurring + TOS-retention ambiguous + real coverage gaps → `[NN-FAIL-CLOSED]`).
  **IBKR free options API** — viable for us *specifically* (daily frequency doesn't need the minute granularity
  that kills it for others). **Unnamed EOD-options vendor, daily 2007→present, zipped CSVs** (one commenter) —
  closest match to our exact need; dirty data → identify it (open lead). Structural reason free historical
  options barely exists: exchange commercial licensing ("Extensive, Quality, Cheap — pick two").

**Data-INTEGRITY upgrade (not new alpha)**
- **Sharadar (Nasdaq Data Link SF1/SEP)** — PIT/as-reported fundamentals + survivorship-free + historical
  S&P constituents + delisted names back to 1998; cheap-end pro sub. The PIT/survivorship layer is exactly the
  honest-substrate integrity our discipline values (sub; retention-after-cancel unconfirmed). AVOID EODHD + FMP
  (documented coverage gaps).

**Meta-corroboration (reassurance, not new alpha):** the community independently re-derived our core
conclusions — regime-as-GATE-not-predictor (=T-220/221); price-vocabulary-exhausted = flat in AND out of
sample (=T-196); PIT-integrity-over-data-cost, "subtly-wrong data looks *better*" (=`[NN-MBL]`/`[NN-CENSUS]`/
`[NN-FAIL-CLOSED]`); retail-edge = capacity-constrained niches institutions can't deploy; tax (ST-vs-LT ~10%)
first-order (=T-148). **No one credited a secret data feed for profitability** — credit went to technique depth
(stat-arb/spreads), capacity-niches, regime-filtering, tax, honest testing → reinforces "the system AS A WHOLE
is the edge" + `[NN-AI-GATE]` (no data savior). "Is OHLC enough?" consensus: yes on daily+/small-caps (less
competition), no on intraday — the edge is the strategy/regime-filter, not the data.

**Ignore (vendor shill/astroturf):** Techsalerator, AltIndex "AI Share of Voice", WormholeQuant, AudioAlpha,
noctiq.ai, InsightSentry, StockFit/Engram/MarketCrunch/siriussignals, MarketTick. (AI-Share-of-Voice — LLM
referral traffic as an attention proxy — conceptually matches `[NN-AI-GATE]`'s new-modality direction, but
~3mo history + paid + no PIT → fails our filters; park until a free, deep, PIT corpus exists.)
