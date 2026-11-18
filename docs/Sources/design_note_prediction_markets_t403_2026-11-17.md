---
task_id: T-403
title: Prediction markets — venues, tax, the one effect worth a forward paper probe, and its power
date: 2026-11-17
type: DESIGN NOTE (public pages and public no-auth endpoints only; no account, no key, no form, no wallet)
status: PROPOSAL. Nothing built, nothing traded, no backtest run. The probe's trial count is the director's ruling at freeze.
companion: docs/Sources/prereg_t403_prediction_market_paper_probe_DRAFT_2026-11-17.md (DRAFT, not frozen)
---

# T-403: prediction markets as a per-event niche

## 0. Decision summary

- **Venue.** **Kalshi**, used directly, is the only venue that has everything at once:
  - it is a CFTC-regulated exchange;
  - it has the widest US-legal market list;
  - its signed-key trading API documents no key expiry;
  - its market data, order books and trade tape are public with no account;
  - its fee is published as a formula.

  **Polymarket US** (QCX LLC, also a CFTC-regulated exchange) is a usable second venue, but its new-account taker fee is about a third higher (Θ 0.095 against Kalshi's 0.07). The international **Polymarket** is closed to US persons for new positions [S14]. The project's Polymarket archive therefore records a venue the owner cannot trade.
- **The wrapper is the biggest blocker.** No venue I could read lets event contracts sit inside a Roth IRA:
  - tastytrade says Kalshi contracts are "not IRAs" [S20];
  - Kalshi itself offers individual accounts only;
  - whether IBKR allows ForecastEx or Kalshi contracts in an IRA is **UNCONFIRMED**.

  A live version would therefore run in a **taxable** account, and there the tax treatment is **unsettled** (§2):
  - if event contracts count as wagering, losses are deductible only by itemizers, only up to winnings, and (as §165(d) now reads) at 90 %;
  - a high-turnover strategy with zero edge would then owe tax on its gross winnings;
  - a professional must rule before any taxable trading.
- **The one hypothesis (chosen from the literature, not from our data).** The **favorite–longshot bias at the close**, captured as a **taker**. On Kalshi, buying the favourite side of a binary contract at the displayed ask in [0.90, 0.99], between 24 h and 1 h before the scheduled close, earns a positive mean net return per event after Kalshi's taker fee.
  - The bias is well documented on Kalshi: Bürgi, Deng & Whelan 2026 (BDW), 46,282 contracts, 2021–Apr 2025 [S1].
  - The taker form is chosen because it is the only form a paper record can test honestly. A taker fills at a displayed ask and size; a maker's fill depends on queue position and adverse selection, which paper cannot see.
- **Breaking it first.**
  - BDW find that **takers lose on average even at high prices** after fees [S1 §5.5]. The positive cell is **makers**: +2.6 % on contracts at 50c and above, with an SD of 33 %, measured before maker fees existed [S1 §4].
  - BDW's 2025 coefficient is less than half of 2024's (ψ 0.021 against 0.048). My arithmetic from their published coefficients: the favourite's pre-fee edge at 95c was about +2.8c in 2024 and **+0.1c in Jan–Apr 2025**. A taker pays about 1.4c (half a 2c spread plus the fee).
  - The paper itself appeared in Sept 2025 – Mar 2026 [S1–S3]. **The prior for the taker form is low.**
- **Power, per event.**
  - The live census of 2026-11-17 found ~23 qualifying events per day; I plan on 10–20.
  - At 20 a day, the minimum detectable mean edge per event at 80 % power is:
    - **0.71 % at 12 months** (one-trial bar), or **1.09 %** at the honest-N bar (N_eff ≈ 372);
    - **0.50 % / 0.77 % at 24 months**.
  - The plausible true edge, if any, is 0–0.5 %. The probe can **catch an edge of 1 % or more** and **kill** the idea cheaply. It **cannot see a 0.3 % edge** at the honest-N bar inside 24 months.
- **My priors.**
  - The effect exists net of fees, in the taker form, for this operator over the next 1–2 years: **20 %**.
  - It is material (≥ +0.5 % per event): **8 %**.
  - The probe passes its gate within 12 months: **≈ 8 %** at a one-trial bar, **≈ 2 %** at the N_eff ≈ 372 bar.
- **Capacity.** Thin. The median depth at the favourite's best ask was **$42**, and the 25th percentile **$1.84** [census §5.1]. At $25 a market, the probe deploys about $600 a day with about $1,200 in flight. Good money is $1–2k a year only if the edge is ≥ 0.5–1 %. A $1k–$10k account is big enough. Size does not help beyond that.
- **Recommendation.** **Freeze and run the forward paper probe only if the director wants a cheap kill-test.** It costs no account and no money, and it consumes one forward trial. Do **not** expect deployment evidence from it. Even a pass would only buy a small real-money pilot, which needs a new pre-registration, the owner's account and a tax ruling.
- **Incidental defects found (not fixed; §10):**
  - the archiver sends the owner's contact address to Polymarket, Kalshi and other non-SEC hosts;
  - the generic Kalshi snapshot has captured **zero prices in five months**;
  - the CEF feed has failed every day since 2026-10-19.

**Markers.** **[S n]** = source n at the end, read 2026-11-17. **UNCONFIRMED** = third-party page, search excerpt, inference I could not check against the venue's own terms, or not read. **[REPO]** = this repository. **[census]** = my read-only count, §1 and §5.1.

---

## 1. What the project already archives (read-only census)

**The writer.**
- Code: `scripts/archive_altdata_t136.py::snapshot_polymarket` [REPO].
- Local schedule: launchd job `com.archondex.altdata-archive` at 17:30 local, through `scripts/run_altdata_archivers.sh`.
- Cloud: the same pulls fold into the cloud pulse through `paper_trader/altdata_archive.py`. That copy is a separate 09:45 ET series on S3, which I did not read.

**What the Polymarket archiver pulls.** `gamma-api.polymarket.com/markets?closed=false&limit=100&offset=0…1000`. That is the **first 1,100 open markets in the API's default order**, not ranked by volume. It keeps those whose question matches about 60 macro, politics and crypto keywords.

**What I looked at, exactly.**
- I read three parquet files read-only: schema, date span, rows per day, distinct ids, gaps, end-date distribution, field completeness, and for KXFED the quoted spreads.
- I computed **no** price-versus-outcome statistic. I joined no price to any result.
- The census script is in the session scratchpad, not the repo.

| File | Rows | Span | Fields | Usable for a probe? |
|---|---|---|---|---|
| `polymarket_snapshots.parquet` | 55,777 | 2026-06-10 → 2026-11-17, 99 snapshot days in a 161-day span; **13 gaps > 1 day, longest 27 days** | snap_date, id, question, category (**100 % null**), outcomes, prices (the `outcomePrices` string), volume, end_date | **No.** No bid/ask, no depth, no token ids, no resolution. A non-random 1,100-market slice. A venue US persons cannot open positions on [S14] |
| ″ detail | median 574 rows/day (342–594); 698 distinct markets; 99.99 % Yes/No | End date at first sighting: median 177 days ahead (December 2026 and November 2028 markets dominate); 173 markets ended before the last snapshot | — | — |
| `kalshi_snapshots.parquet` | 20,930 | 2026-06-10 → 2026-11-17, 99 days | ticker, title, category, yes_bid, yes_ask, last_price, volume, close_time | **No.** **All four price/volume fields are 100 % null on every day.** The code's own comment says the legacy fields are null on the current API. Rows still land, so the freshness gate passes |
| `kalshi_kxfed_snapshots.parquet` | 18,280 | 2026-07-07 → 2026-11-17, 99 days | full bid/ask both sides, volume, open interest, status, result | Fed-rate buckets only: 14 FOMC events, 280 tickers. Quoted (0 < bid < ask < 1) 59 % of rows, median spread 19c (far wings included). Too few events for a per-event test |

**Verdict on the archive.** It can support counts, but it cannot be the probe's substrate. It also cannot honestly choose the probe's rule. Using it for that is forbidden by the brief and by `[NN-MBL]`'s pre-registration rule.

---

## 2. Venues a US individual can use today

| | **Kalshi (direct)** | **Polymarket US** | **ForecastEx (via IBKR)** | **Kalshi / CME via an FCM** (IBKR, tastytrade, Robinhood, …) | Polymarket (international) |
|---|---|---|---|---|---|
| Status | CFTC-regulated DCM; designated Nov 2020 [S1 §1]; "subject to U.S. regulatory oversight by the CFTC" [S5] | "QCX LLC d/b/a Polymarket US, a CFTC-regulated Designated Contract Market" [S10] | CFTC-registered DCM and DCO; an IBKR affiliate [S16, S17] | The FCM is CFTC-registered. Robinhood: "Robinhood Derivatives, LLC., a registered futures commission merchant" [S21] | **US = close-only, frontend and API** [S14] |
| Account types | Individual. **No IRA found** | Individual, KYC with SSN [S12]. IRA not found | IBKR IRAs exist and allow futures [T-402 S56]. **Event contracts in an IRA: UNCONFIRMED** | tastytrade: Kalshi contracts on "cash or margin accounts (not IRAs)" [S20]. Others not read | — |
| Fees | Taker `round_up(0.07·C·P·(1−P))`. Maker `0.0175·C·P·(1−P)` on maker-fee series only. S&P/Nasdaq series 0.035. No settlement fee; ACH free; debit 2 % [S4] | Taker Θ × C·P·(1−P) with **Θ = 0.095** below $10k of 30-day taker volume (0.085 / 0.075 / 0.0695 above). Makers: no fee and no rebate below $10M. Banker's rounding. Effective 2026-11-14 [S11] | $0.00 commission + $0.01 per contract exchange fee [S18]; "$0.01 per contract, charged to each side" [S17]. Pays a **3.38 % APY incentive coupon** on position value [S16] | Kalshi via IBKR: $0.01 commission + $0.01 exchange fee per contract [S18]. Whether Kalshi's own formula fee is also charged: **UNCONFIRMED**. CME via IBKR: $0.01 + $0.01 [S18] | — |
| Unattended API | REST/WebSocket/FIX. Requests signed with an Ed25519 or RSA key pair; the timestamp must be within 30 s. Scoped keys (read / write::trade / write::transfer). **No key expiry stated**; up to 100 keys [S6, S7] | REST + WebSocket. Ed25519-signed headers, 30 s window. Keys from a developer portal after KYC. "Revoke compromised keys immediately"; **no expiry stated**. App access may need an invite code [S13] | TWS API / Web API (OAuth 2.0 private_key_jwt) [S19]. Sessions reset at midnight, with a weekly 2FA login (T-402 [S57–S61], excerpt): **fragile unattended** | Varies by FCM; not read | — |
| Public no-account data | **Yes**: `/markets`, `/events`, `/series`, `/markets/{t}/orderbook`, `/markets/trades`, candlesticks all declare `security: []` [S7, S8]. Unauthenticated requests have separate IP rate limits [S9] | **Yes**: market book, BBO, settlement and price history on `gateway.polymarket.us`, `security: []` [S13] | Daily CSVs: pairs, prices, summary; ~83 pages of dates [S17] | — | gamma/CLOB public (the archive uses gamma) |
| History | Live and historical tiers: settled markets, candlesticks and trades older than a moving cutoff move to `/historical/*` [S8] | Price history, candlesticks, reporting [S13] | Daily CSVs since ~2024 (page count; start not verified) | — | — |
| Position limits | CPI contract terms: "Position Accountability Level … $25,000 per Member" [S15]. Other series not read | App market buy ≤ $1,000,000 [S12] | Not read | — | — |

**Others not read today (UNCONFIRMED):**
- PredictIt's current status, fees and caps;
- Webull, Coinbase and Crypto.com event-contract routes;
- state actions against sports event contracts;
- where Kalshi customer cash is held (DCO or FCM segregation).

**Third-party claim, UNCONFIRMED:** Kalshi's CEO said its contracts would reach 401(k) providers in 2026 [S22].

**Why Kalshi direct for the probe.**
1. It has the most non-sports daily events: in the census, 74 daily-frequency events closed within 24 h, across weather, economics, commodities and entertainment.
2. Its book and trade tape are public, so the recorder needs no account.
3. Its taker fee is the lowest per contract for favourites. At 95c it is 0.36c per contract on a 25-lot, against ForecastEx's flat 1c and Polymarket US's ~0.45c.
4. The paper record and any later pilot would run on the same venue.

---

## 3. Tax treatment for a US individual: **unsettled; for a professional**

**What the venues say.**
- Kalshi issues 1099-INT (interest), 1099-MISC (rewards), 1099-B ("crypto transfers") and 1099-DA. **Event-contract trading appears only in a profit-and-loss statement, with no tax characterization.** It adds: "Kalshi cannot give members advice on their taxes … consult with a tax professional" [S5].
- IBKR: "IBKR does not give tax advice" [S18].
- I found no IRS publication that addresses exchange-traded event contracts.

**The candidate treatments, from the statute text** (characterization is the open question):

| If they are … | Then | Consequence for a high-turnover strategy |
|---|---|---|
| §1256 contracts ("regulated futures contract" or "nonequity option") | Marked to market at year end; gains 60 % long-term / 40 % short-term [S23] | Favourable. But §1256(b)(2)(B) excludes swaps "or similar agreement" [S23], and the CFTC treats many event contracts as swaps or options. Unclear |
| Ordinary derivatives or capital assets outside §1256 | Short-term gains at ordinary rates, given ≤ 24 h holds | Neutral: tax on net profit |
| **Wagering** | Losses deductible **only if you itemize**, only up to winnings [S25]. §165(d) now reads "**90 percent** of the amount of such losses" [S24] | **Punitive.** A standard-deduction filer pays tax on gross winnings. A zero-edge book with ~$200k a year of turnover could show ~$10k of winnings and owe tax on it |

**Inside a Roth IRA** the characterization would mostly not matter, but no venue is confirmed to allow it. Whether unrelated business income could arise is for a professional. **Mark the whole section for the owner's tax professional before any taxable trading.**

---

## 4. Which effect: the four candidates, tried against each other

| Candidate | Literature effect, net of fees | Why it might persist | Capacity at $1k–$10k | Verdict |
|---|---|---|---|---|
| **A. Favorite–longshot bias** (buy favourites) | **Kalshi, 2021–Apr 2025** [S1], pooled over 0–10 days:<br>• contracts ≥ 70c have "statistically significant, though small, positive post-fee returns"<br>• makers buying ≥ 50c: **+2.6 %** post-fee (pre maker fees), SD 33 %<br>• **takers "still lose money on average"** as prices rise [S1 §5.5]<br>• bias "diminishing": ψ 0.048 in 2024 → 0.021 in 2025<br>**Classic betting markets:** robust for decades; Snowberg & Wolfers attribute it to misperceived probability [S26] | Probability weighting (Prospect Theory); risk-love; small volumes keep professionals out; a 33 % SD deters capital [S1 §6] | Tens of dollars per market at the best ask (median $42) | **Primary, in the near-close taker form (A + C)** |
| **B. Overpricing of low-probability contracts** (sell longshots) | Contracts < 10c lose > 60 % including taker fees; makers buying ≤ 10c also lose [S1] | Same | Same | **The same trade as A.** On Kalshi, selling a longshot's Yes = buying its No, the favourite. Merged into A; testing both would double-count |
| **C. Near-expiry convergence** | Page & Clemen 2013: the InTrade bias sits in long-dated markets; near close the market is calibrated (cited in [S1 §2.1]). **But on Kalshi** the closing-day losses on cheap contracts are as large for makers as for takers, "a version of Page's (2012) Yogi Berra effect" [S1 §4]. That is the counterparties' gain: favourites are cheapest at the close. BDW's closing-day regression gives +1.40c pre-fee at 95c (my arithmetic, Table 5) | Yogi Berra bias; residual uncertainty over-weighted; capital locked for < 1 day | Capital turns daily; same depth limit | **Combined with A into the one rule** |
| **D. Cross-venue gaps** on identical contracts | Within Polymarket: ~$40M of realised arbitrage, Apr 2024–Apr 2025 [S27]. **No academic effect size for US-accessible cross-venue pairs found.** The fee wedge for a Kalshi taker + Polymarket US taker at 50c is ~1.75c + ~2.4c ≈ 4.1c per pair | Fragmented liquidity; different resolution sources | Small; capital split across two KYC'd venues | **Rejected.** Fleeting gaps cannot be paper-tested; resolution-rule mismatch is a hidden tail; it is a latency race against bots |

**Why A + C, and why the taker form.**
1. It is the literature's most robust effect: it holds in every year, category, horizon, volume quintile and transaction-size quintile [S1 Tables 4–9].
2. It has an ex-ante theory (probability misweighting, plus the Yogi Berra close).
3. It is the **only** form a paper record can test without inventing fills. A taker pays a displayed ask for displayed size.
4. The maker form has the bigger documented edge (+2.6 %). But a paper maker gets "filled" only by assumption: queue position and adverse selection are invisible, and the T-379 lesson applies ("paper fills at the quote"). It is therefore deferred to a real-money pilot, if ever. It is **not** a second hypothesis here.

**My effect-size arithmetic** (from BDW's published Mincer–Zarnowitz coefficients; profit and price in cents; a linear fit, which understates curvature at the extremes; **UNCONFIRMED as a bin estimate**):

| BDW fit | Pre-fee profit at 95c | Minus the taker's cost (half of a 2c spread + 0.36c fee = 1.36c) |
|---|---|---|
| All years, all days (Table 4) | +1.49c | +0.13c ≈ **+0.1 %** |
| Closing day (Table 5) | +1.40c | +0.04c ≈ **0 %** |
| 2024 only (Table 9) | +2.77c | +1.41c ≈ **+1.5 %** |
| 2025 Jan–Apr only (Table 9) | +0.14c | −1.22c ≈ **−1.3 %** |

The median spread in the live census was 2c (10th/90th percentile 1c / 8c). **Central expectation ≈ 0, falling.** This is why the prior is 20 % and not 60 %.

---

## 5. Power, per event

### 5.1 How many events (live census, 2026-11-18 03:19 UTC = 2026-11-17 21:19 CST)

The census used public endpoints only, ≤ 1.1 requests/s, about 80 requests in all. It recorded counts, asks, spreads and depth. No outcome was read.
- **Open markets closing in the next 24 h** (multivariate excluded): 9,367 markets in 217 events.
  - By event frequency: 74 daily, 57 hourly, 23 fifteen-minute, 27 one-off, 25 custom, 11 other.
- **Passing the draft screen:**
  - exclusions: Sports, hourly, 15-minute;
  - volume ≥ 1,000 contracts;
  - a favourite ask in [0.90, 0.99] with a live bid.

  Result: **42 markets in 23 events from 21 series**, mostly Economics, Weather, Entertainment and Commodities. Median 1 market per event, max 7.
- **Ask mix:** 19 of the 42 sit at 0.99. This did **not** change the rule. 0.99 is inside the literature's 90–99c bin, so excluding it would be tuning.
- **Spread** (favourite side): 10th/50th/90th percentile 1c / 2c / 8c.
- **Depth at the favourite's best ask:** 10th/25th/50th/75th/90th percentile **$0.96 / $1.84 / $42 / $206 / $2,168**.
- **Settled in the last 7 days:** ≥ 4,130 events, of which ≥ 381 non-sports, non-hourly. My 60-page cap truncated this count, so it is a **lower bound only**.

**Planning value:** 10 (pessimistic) to 20 (central) qualifying events a day, so **3,650–7,300 a year**. A snapshot misses markets that enter the band later in their final day, so 23 is a floor for that evening. But weekends thin the economics events.

### 5.2 Clustering

- Inside an event, mutually exclusive buckets are perfectly dependent: exactly one Yes wins. **The event is the unit.** Each event's return is its summed P&L over its summed stake.
- Across events, the same day's weather systems, macro releases and news stories correlate outcomes. **Standard errors are clustered by resolution date** (the calendar day in ET). The bootstrap resamples blocks of dates (§8 of the prereg). As a sensitivity, I cluster by (series, ISO week).
- For planning I assume a design effect of 1.5. The probe measures the real one.

### 5.3 Minimum detectable mean edge per event (80 % power, one-sided)

- Per-event SD of net return per dollar: planning value **σ = 0.20**. The census ask mix gives 0.173 per market at the null; 0.15 and 0.25 are shown as sensitivities in the scratch output.
- Bar: `z_c = max(1.645, E[max of N nulls])`, which is 1.645 for one trial and **2.96 at N_eff ≈ 372** (the fresh-eyes audit's figure, which I reproduced).

| Horizon | 10 events/day, N = 1 | 10/day, N_eff ≈ 372 | 20/day, N = 1 | 20/day, N_eff ≈ 372 |
|---|---|---|---|---|
| 6 months | 1.43 % | 2.18 % | 1.01 % | 1.54 % |
| 12 months | 1.01 % | 1.54 % | **0.71 %** | **1.09 %** |
| 24 months | 0.71 % | 1.09 % | 0.50 % | 0.77 % |

### 5.4 Pass probability under a plausible true effect (σ 0.20, DE 1.5)

| True mean per event | 12 mo, 20/day, N = 1 | 12 mo, N ≈ 372 | 24 mo, 20/day, N = 1 | 24 mo, N ≈ 372 |
|---|---|---|---|---|
| ≤ 0 | ≤ 5 % (false positive) | ≤ 0.2 % | ≤ 5 % | ≤ 0.2 % |
| +0.3 % | 28 % | 3 % | 43 % | 7 % |
| +0.5 % | 54 % | 11 % | 79 % | 31 % |
| +1.0 % | 97 % | 70 % | > 99 % | 98 % |

**Honest reading.** The effect sizes the literature makes plausible are 0 to +0.5 %, and that range is underpowered at the honest-N bar even at 24 months. The probe is a **kill-test**. It confirms only if the edge is ≥ ~1 % per event, which the 2025 evidence argues against. It does have one real advantage over every ≤ 26-year backtest: evidence accrues at about 7,000 events a year, not one observation a month.

---

## 6. The paper probe (full rule in the DRAFT pre-registration)

- **Forward only.** Decisions are written, timestamped and hash-chained **at least an hour before** each market's scheduled close. Resolutions are appended after settlement. Nothing is back-filled.
- **No rule choice from data.** Every parameter comes from BDW's sample definition, or from what an hourly unattended job can execute:
  - the 90–99c bin;
  - volume ≥ $1,000 (approximated by ≥ 1,000 contracts at decision);
  - spread ≤ 20c;
  - markets open ≥ 24 h;
  - the closing-day horizon.
- **Paper fills.** At the best ask, up to the displayed size, with the fee computed by the published formula at the order's size, rounded up. Each fill is capped at $25 a market; one under $5 is skipped and counted. A paper taker fill at a displayed quote is close to real for a bot. The residual is latency slippage, which a later real-money pilot would measure.
- **Gate** (numbers in the prereg §8). Evaluation is set by an information rule: the later of 12 months and 3,650 resolved events, capped at 24 months. PASS needs all of:
  - the one-sided block-bootstrap `ci_low > 0` at the director's z_c;
  - a cluster-robust t ≥ z_c;
  - mean ≥ +0.50 % per event;
  - ≥ $300 a year projected at the recorded stakes;
  - no single category supplying more than half the profit;
  - a clean census.

  REFUTED if the mean is ≤ 0, or at a 6-month futility look if the mean is ≤ −0.5 % with t ≤ −2.

---

## 7. The proposed recorder (shape only; NOT built)

| Piece | Proposal |
|---|---|
| Code | `scripts/pm_probe_t403_recorder.py` (hourly scan + decisions), `scripts/pm_probe_t403_resolver.py` (appends resolutions), `scripts/pm_probe_t403_evaluate.py` (run once at the horizon; read-only; deterministic ×2 by md5). Outside `engines/`: this is a research record, like the T-277 watcher, not a signal in Engine A |
| Inputs | Public Kalshi endpoints only: `/series` (daily cache of category, frequency, fee_type, fee_multiplier), `/markets?status=open&mve_filter=exclude&min_close_ts=now+1h&max_close_ts=now+24h`, `/markets/{t}/orderbook?depth=5`, `/markets/{t}` for settlement. **Generic User-Agent, no contact details** |
| Outputs | Append-only JSONL, partitioned by day: `scans`, `decisions`, `resolutions`. Every row carries `prev_hash` and `row_hash` (SHA-256). Each day's file hash goes to a write-once S3 object (versioned, object lock) so the record cannot be edited after the fact. Root `data/research/pm_probe_t403/`, written **only** by the scheduled job, never by a worktree agent (the shared-symlink merge-gate hazard) |
| Where it runs | **Cloud, hourly** (EventBridge → a small Batch or Lambda job; propose-first: a new scheduled job). The local launchd path shows 13 multi-day gaps in five months, the longest 27 days. Gaps cut the sample and add no bias, but the cloud avoids them |
| Fail closed | A truncated market list, a failed orderbook read, an unknown `fee_type`, or a clock skew > 30 s marks the scan **degraded** and writes **no** decisions for the affected markets. Never a stale or zero fill |
| Census per scan | Markets seen, screened, eligible, skipped for depth, decisions written, failures. Daily: unresolved decisions older than 7 days, voids, hash-chain verification |
| First artifact (`[NN-FIRST-ARTIFACT]`) | DONE only when the first scheduled cloud firing has written a decision row and a later firing has appended its resolution, both read back from S3 and chain-verified |
| Tests | The fee formula against the schedule's published table; the eligibility screen; no-backfill; chain integrity. A drill: kill the orderbook read, then expect a degraded scan and zero decisions |

---

## 8. What going live would take (listed, NOT done; every item is the owner's decision)

1. **Venue and wrapper.** Kalshi direct (individual, taxable), or an FCM route. First ask IBKR whether ForecastEx, Kalshi or CME event contracts are allowed in a **Roth IRA**; that one answer decides the tax problem.
2. **Account and KYC.** Legal name, date of birth, address, SSN, possibly an ID photo and a selfie (Polymarket US's stated process [S12]; Kalshi's help centre has matching articles [S5]). No sign-up was started.
3. **Funding and where the money sits.** ACH (free at Kalshi [S4]) or wire. A pilot of $500–$1,000 of separate taxable money; the cash sits at the venue or its clearing house (custody details **UNCONFIRMED**).
4. **API key.** Generated in Kalshi account settings: Ed25519, scoped read + `write::trade` only, no transfer scope [S6]. Stored outside the repo (`.env` or a secrets manager) and never committed.
5. **A tax professional's ruling** on characterization before the first taxable trade.
6. **Engineering, propose-first:**
   - a new external service and a signing dependency;
   - risk limits that belong to Engine B (a per-market cap, a daily loss cap, a maximum open exposure);
   - the `live_trader` boundary;
   - a kill switch.
7. **A separate pre-registered real-money pilot.** Paper → real is a substrate change (`[NN-SUBSTRATE-REVERIFY]`). The pilot re-measures fills, slippage and fees before any scaling.

---

## 9. Priors, in numbers

| Statement | Prior |
|---|---|
| The near-close favourite edge exists **net of taker fees and spread**, for this operator, over the next 12–24 months | **20 %** |
| …and is material (≥ +0.5 % per event, ≳ $1k/yr at the census depth) | **8 %** |
| The probe passes its gate within 12 months, one-trial bar (z 1.645) | **≈ 8 %** (true pass ≈ 6–7 % + false pass ≈ 1–2 %) |
| The probe passes within 12 months at the N_eff ≈ 372 bar (z 2.96) | **≈ 2 %** |
| A pass would survive the real-money pilot and the tax ruling to become worth running | **≈ 3 %** |

These sit in line with the fresh-eyes audit's ~10 % for "a durable bot edge", a little lower because BDW's 2025 slice and their taker-side result arrived after that estimate.

---

## 10. Incidental findings (not fixed; for the director)

1. **Contact-address leak.**
   - `scripts/archive_altdata_t136.py` sets one `User-Agent` containing the owner's contact address. It uses that header for **every** host: Polymarket gamma, Kalshi, GPR, EPU, FRED and USASpending.
   - The 2026-11-11 ruling approves the address **for SEC hosts only**.
   - Fix: a generic UA for non-SEC hosts, as `snapshot_cef` already does.
2. **Dead Kalshi feed.** `kalshi_snapshots.parquet` has 100 % null `yes_bid / yes_ask / last_price / volume` on all 99 days. It is a durable-but-never-fed feed that passes the freshness gate because rows land. Either repoint it to the `*_dollars` / `*_fp` fields, as KXFED already does, or retire it.
3. **Failing CEF feed.** The CEF feed has failed since **2026-10-19**: the last `snap_date`, and today's log shows `cef: FAILED (JSONDecodeError …)` with `[verify-altdata] FAIL — zero fresh rows: cef`. A month of the T-267 PIT discount panel is lost, and the alarm path should be checked.
4. **A blind Polymarket archive.** It stores mid/last `outcomePrices` but no book and no resolution. A US person cannot trade that venue anyway.

---

## 11. UNCONFIRMED items

1. Whether any broker (IBKR above all) allows event contracts in a Roth IRA.
2. The Kalshi CEO's 401(k)-availability statement [S22].
3. BDW's taker-only returns in the 90–99c bin. The figure values are not in the extractable text; "takers still lose on average" is from their §5.5 prose.
4. My effect-size arithmetic from BDW's linear coefficients (§4).
5. The current Kalshi fee schedule. It was read from a Wayback capture of 2026-06-12 (effective 2026-02-05) because kalshi.com returned HTTP 429; the live API's `fee_type` / `fee_multiplier` fields are consistent with it.
6. Whether the S&P/Nasdaq 0.035 fee maps to the API's `fee_multiplier` 0.5 (KXINXU reads 1). The probe uses the higher fee when the two disagree.
7. Kalshi and Polymarket US key lifetimes: "not stated" is not "none".
8. Whether Kalshi's formula fee is charged on top of IBKR's per-contract fees.
9. IBKR's unattended session rules (T-402 excerpts).
10. Polymarket US invite codes, IRA availability and position limits beyond the app cap.
11. Kalshi customer-fund custody.
12. Position limits for series other than CPI.
13. PredictIt, Webull, Coinbase and Crypto.com routes.
14. State legal actions.
15. Every tax characterization in §3.
16. ForecastEx's public CSV currency (the page listed dates through 2026-11-03).
17. The semantics of Polymarket's `outcomePrices`.
18. A third-party blog's §1256 claim [S28], not relied on.

---

## Sources (all read 2026-11-17)

1. Bürgi, Deng & Whelan, "Makers and Takers: The Economics of the Kalshi Prediction Market", Jan 2026, https://www.karlwhelan.com/Papers/Kalshi.pdf (also GWU CER WP 2026-001, https://www2.gwu.edu/~forcpgm/2026-001.pdf; MPRA 126350, Sept 2025, https://mpra.ub.uni-muenchen.de/126350/)
2. Whelan, NYU Stern Fintech Conference slides, 2026-03-06, https://www.karlwhelan.com/Presentations/Whelan-NYU.pdf (maker fees 0.0175·p(1−p) "introduced in 2026"; "Contracts below 10c lose over 50%")
3. CEPR VoxEU column, https://cepr.org/voxeu/columns/economics-kalshi-prediction-market (HTTP 403; title from a search listing only)
4. Kalshi fee schedule PDF, Wayback capture 2026-06-12, https://web.archive.org/web/20260612075630id_/https://kalshi.com/docs/kalshi-fee-schedule.pdf ("Last updated and effective: Feb 5, 2026"). The live https://kalshi.com/docs/kalshi-fee-schedule.pdf and https://kalshi.com/fee-schedule returned HTTP 429
5. Kalshi Help Center, "What Tax Documentation Does Kalshi Provide?", https://help.kalshi.com/en/articles/13823849-what-tax-documentation-does-kalshi-provide ; "Fees", https://help.kalshi.com/en/articles/13823805-fees ; Trading collection, https://help.kalshi.com/en/collections/18616612-trading
6. Kalshi API docs, "API Keys", https://docs.kalshi.com/getting_started/api_keys
7. Kalshi API docs, Get Market Orderbook, https://docs.kalshi.com/api-reference/market/get-market-orderbook.md ; Get Trades, https://docs.kalshi.com/api-reference/market/get-trades.md ; Get Markets, https://docs.kalshi.com/api-reference/market/get-markets.md ; Get Series, https://docs.kalshi.com/api-reference/market/get-series.md ; index, https://docs.kalshi.com/llms.txt
8. Kalshi API docs, "Historical Data", https://docs.kalshi.com/getting_started/historical_data ; "Market Settlement", https://docs.kalshi.com/getting_started/market_settlement.md ; "Fee Rounding", https://docs.kalshi.com/getting_started/fee_rounding
9. Kalshi API docs, "Rate Limits and Tiers", https://docs.kalshi.com/getting_started/rate_limits.md
10. Polymarket US home page footer, https://polymarket.us/
11. Polymarket US Fee Schedule (effective 2026-11-14), https://docs.polymarket.us/fees.md
12. Polymarket US, "Create an Account", https://docs.polymarket.us/learn/get-started/signup.md ; "Trading Limits", https://docs.polymarket.us/learn/trading/access-and-limits/trading-limits.md ; "Trading Restrictions", https://docs.polymarket.us/learn/trading/access-and-limits/trading-restrictions.md
13. Polymarket US, "Authentication", https://docs.polymarket.us/api-reference/authentication.md ; Get Market Book, https://docs.polymarket.us/api-reference/markets/get-market-book.md ; index, https://docs.polymarket.us/llms.txt
14. Polymarket (international) docs, "Geographic Restrictions", https://docs.polymarket.com/developers/CLOB/geoblock
15. Kalshi CPI contract terms, https://assets.kalshi.com/contract_terms/CPI.pdf ; temperature contract terms, https://assets.kalshi.com/contract_terms/GLOBALTEMPERATURE.pdf
16. IBKR Prediction Markets / ForecastTrader page, https://forecasttrader.interactivebrokers.com/ (redirects to the IBKR prediction-markets home)
17. ForecastEx FAQ, https://forecastex.com/faq ; Data, https://forecastex.com/data
18. IBKR event-contract commissions, https://www.interactivebrokers.com/en/pricing/commissions-events.php
19. IBKR Web API overview, https://www.interactivebrokers.com/campus/ibkr-api-page/web-api/ ; IBKR IRA information, https://www.interactivebrokers.com/en/trading/ira-information.php
20. tastytrade support, "Kalshi Event Contracts", https://support.tastytrade.com/support/s/solutions/articles/Kalshi-Event-Contracts (search excerpt: "eligible cash or margin accounts (not IRAs)")
21. Robinhood prediction markets page, https://robinhood.com/us/en/prediction-markets/
22. CDC Gaming, "Kalshi boss: Our contracts will be available from 401(k) providers in 2026", https://cdcgaming.com/brief/kalshi-boss-our-contracts-will-be-available-from-401k-providers-in-2026/ (search excerpt; UNCONFIRMED)
23. 26 U.S.C. §1256, https://www.law.cornell.edu/uscode/text/26/1256
24. 26 U.S.C. §165(d), https://www.law.cornell.edu/uscode/text/26/165
25. IRS Topic no. 419, Gambling income and losses, https://www.irs.gov/taxtopics/tc419
26. Snowberg & Wolfers, "Explaining the Favorite-Longshot Bias: Is it Risk-Love or Misperceptions?", NBER WP 15923 (2010), https://www.nber.org/papers/w15923
27. Saguillo, Ghafouri, Kiffer & Suarez-Tangil, "Unravelling the Probabilistic Forest: Arbitrage in Prediction Markets", arXiv 2508.03474 (2025), https://arxiv.org/abs/2508.03474
28. kalshiview.com, "Are Kalshi Event Contracts Section 1256 Contracts?", https://kalshiview.com/blog/are-kalshi-event-contracts-section-1256-contracts-what-traders-should-know-2026/ (search excerpt; third party; not relied on)
29. Kalshi public API, live census, 2026-11-18T03:19Z and 03:22Z (2026-11-17 local): `GET https://api.elections.kalshi.com/trade-api/v2/series`, `/markets?status=open&mve_filter=exclude&min_close_ts&max_close_ts`, `/markets?status=settled&min_settled_ts&max_settled_ts` (counts only), `/markets/{ticker}/orderbook?depth=5`
30. T-402 design study [REPO], `docs/Sources/design_study_real_money_venue_t402_2026-11-17.md` (IBKR IRA and API sources S56–S61 there)
