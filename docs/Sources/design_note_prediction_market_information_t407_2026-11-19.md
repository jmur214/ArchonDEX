---
task_id: T-407
title: Prediction markets as an INFORMATION source for this book — what free history exists, what could be tested, and whether any use clears the bar
date: 2026-11-19
type: PRE-RUN DESIGN NOTE (public no-auth endpoints, public papers, and read-only counts of the project's archive; no account, no key)
status: PROPOSAL. No hypothesis measured. No Kalshi or Polymarket price was joined to any release outcome or any asset return. The draft prereg states no trial count.
companion: docs/Sources/prereg_t407_kalshi_surprise_validity_DRAFT_2026-11-19.md (DRAFT, not frozen)
follows: T-403 (docs/Sources/design_note_prediction_markets_t403_2026-11-17.md), the user's re-frame of 2026-11-18
---

# T-407: can prediction-market prices help direct this book's trades?

## 0. The answer

**The free data are much better than the project assumed. But no use of them that would change what this book trades can be seen by the project's bar. My recommendation is to close the trading question, keep the archive running, and run at most one cheap calibration check, and only if you want Kalshi's numbers shown to you as information.**

In plain terms:

- **The data exist, free, back to 2021.** Kalshi gives away, with no account, the hour-by-hour (even minute-by-minute) bid, ask and trade prices of every settled market. That covers 65 monthly CPI releases (since mid-2021), 57 jobs reports (since 2022), 42 Fed meetings, 22 GDP releases and 26 core-PCE releases. Most of these had a usable two-sided ladder just before the release, except FOMC and core PCE (§1.1). Polymarket gives 3- and 12-hour price history back to November 2022, but no bid/ask. Neither venue's history has to be collected by the project. The project's own archive is not the bottleneck for any test.
- **The prices are good forecasts.** A Federal Reserve staff paper (Diercks, Katz & Wright, February 2026) finds Kalshi's CPI forecast on release morning slightly better than Wall Street's survey consensus, and its Fed-meeting forecast exactly right the day before every meeting since 2022.
- **That is exactly why the book cannot trade them.** Stocks and bonds already price the same expectations. The surprise lands at 8:30 am, before this system can trade. What is left for a long-only Roth book holding SPY/VOO, MTUM/QUAL, AGG/GLD and cash comes in three kinds:
  1. **Nudging the timing of trades around a release.** At this book's turnover, that is worth a few hundredths of a percent a year at most.
  2. **Switching risk on or off on a recession or rate signal.** That is regime timing, measured dead here three times.
  3. **Betting that markets follow the Wall Street survey rather than Kalshi.** Research says markets see through stale surveys, and the survey history is not free.
- **The arithmetic.** Assume about 45 usable releases a year and a plausible edge of 0.1–0.2 % per release, against about 1.3 % of noise in SPY on a release day. The bar (N_eff ≈ 372) then needs **600 to 2,400 releases, which is 14 to 55 years**. The free history holds about 4.8 years.
- **What can be tested now** is whether Kalshi's last pre-release forecast explains the release-day move of the bond sleeve. This is a validity check, not a trade. It would probably pass: about 70 % at the honest-N bar and about 92 % at a one-trial bar, on about 100 usable release days. A pass licenses only one thing: showing the number to you.

**My priors:**
- some prediction-market-driven trading rule for this book has a real net edge: about 5 %;
- it passes the project's bar on the free history: ≤ 2 %;
- the validity check passes: ≈ 70 % at z 2.96 (≈ 92 % at z 1.645). Its true correlation is very likely non-zero (≈ 85 %), but about 100 events limit the power.

---

## 1. What free history exists (the census)

**Method.** I used public endpoints only: generic User-Agent `ArchonDEX-research/1.0`, no contact details, about one request a second per worker (up to four workers for about 15 minutes), about 4,500 requests in all.
- I read counts, timestamps, volumes and quotes only.
- No release outcome was read beyond whether a market had settled and whether its settled value was populated. No price was joined to an outcome or to an asset return.
- From the project's own price files I read only the all-day daily volatility of SPY, AGG, TLT and GLD (planning values) and calendar-year AGG returns (the total-return check). No release-day return was read.
- The scripts and their raw output are in the session scratchpad, not the repo.

### 1.1 Kalshi (verified 2026-11-19)

| What | Finding |
|---|---|
| Live tier | `GET /series/{series}/markets/{ticker}/candlesticks`, `GET /markets`, `GET /events`, `GET /markets/trades`. All declare `security: []` (no auth) |
| Historical tier | `GET /historical/markets`, `/historical/markets/{ticker}`, `/historical/markets/{ticker}/candlesticks`, `/historical/trades`, all `security: []`. **Today's cutoff** (`GET /historical/cutoff`): markets that settled before **2026-09-19** are served only from `/historical/*`. The cutoff moves forward |
| Events | `GET /events?series_ticker=…` lists **every** event, including archived ones. The legacy tickers (`CPI-22JUN`, `PROLLS-23MAR`, `FED-22JUL`, `GDP-21SEP30`, …) are listed **inside** the KX series (`KXCPI`, `KXPAYROLLS`, `KXFED`, `KXGDP`). The legacy series tickers themselves return 0 events |
| Resolution | Candles at **1 minute, 1 hour or 1 day** for live and historical markets alike. Each candle carries OHLC of `yes_bid`, `yes_ask` and trade price, plus volume and open interest. One request spans ≤ 5,000 periods |
| Sparse candles | A candle exists only for an hour with a quote change or a trade. The standing quote is the **last candle carried forward**. In a sample of 8 events per family, the carried candle at the close was a median 8.4 h old for CPI and GDP (the book last moved overnight), and 0.4–1.4 h old for PCE, payrolls and FOMC. Over the final 7 hours the count of quoted strikes barely changes, so the pre-release snapshot is stable |
| FOMC ladders are one-sided | In 8 of 8 sampled FOMC events, no hour in the final 7 had ≥ 3 two-sided strikes (median 1). On a near-certain decision, most strikes sit at a one-sided 0/1 book. The ladder still says "certain", but it is not a two-sided distribution. This matches DKW's "exact the day before" |
| Quote coverage (one example) | `CPI-22JUN-T1.1` (June 2022 CPI, "above 1.1 %"): 54 hourly candles over the final 4½ days, a two-sided quote in every one; 1-minute candles to 12:25 UTC, five minutes before the 8:30 ET release |
| Market close vs release | Most macro ladders close at 08:25–08:29 ET on release day (CPI: 12:25 UTC in summer, 13:29 UTC in winter); FOMC ladders close at 13:55 ET. Two exceptions: some 2021–22 events closed at 19:00 or 23:59 ET **the evening before**, and **four closed after the 08:30 release** (08:33, 10:00, 10:01, 11:13 ET; GDP and payrolls). A snapshot must therefore be cut at the release instant, never at the market's close. Otherwise post-release prices enter and the measured surprise collapses toward zero (the draft prereg's §3.2 rule) |
| Settled value | Each market carries `expiration_value`, the released figure, plus `result`, so the actual print is free and self-consistent |
| Rate limits | Unauthenticated requests "are subject to separate limits"; **no number is published**. Every one of the census's 3,024 candle requests ended in HTTP 200, at up to ≈ 4 req/s from four workers. The probe retried a 429 silently with back-off and did not log retries, so I cannot rule out that a few occurred. The documented Basic authenticated tier is 200 read tokens/s (20 req/s at 10 tokens) |
| Not free | `GET /series/{s}/events/{t}/forecast_percentile_history` (Kalshi's own percentile forecast series) needs a signed key, i.e. an account. Not used |

**Events per family.** In this census table, a "quoted ladder" means at least 3 strikes with a two-sided quote (bid > 0, ask < 1, spread ≤ 10c) in the last hourly candle at or before the market's close. That candle is carried forward, but it must lie within the final 30 hours.

All families: resolution 1 minute / 1 hour / 1 day; endpoint `/historical/markets/{t}/candlesticks` before the cutoff and `/series/{s}/markets/{t}/candlesticks` after it.

| Family | Series (legacy tickers inside) | Settled events | Span of closes | **Quoted ladder just before the close** | … at the prior day's 16:00 ET | Median spread of quoted strikes |
|---|---|---|---|---|---|---|
| CPI, headline m/m | `KXCPI` | 65 | 2021-07 → 2026-11 | **52** (from 2021-11) | 58 | 3c |
| Core CPI m/m | `KXCPICORE` | 53 | 2022-07 → 2026-11 | **44** (from 2022-07) | 47 | 4c |
| Core PCE m/m | `KXPCECORE` | 26 | 2022-12 → 2026-10 | **4** (from 2025-05) | 8 | 5c |
| Payrolls | `KXPROLLS`, `KXPAYROLLS` | 57 | 2022-04 → 2026-11 | **50** (from 2022-05) | 56 | 3c |
| Unemployment rate | `KXU3` | 64 | 2021-08 → 2026-11 | **49** (from 2022-02) | 55 | 3c |
| GDP, advance | `KXGDP` | 22 | 2021-07 → 2026-10 | **16** (from 2022-01) | 19 | 4c |
| FOMC (upper bound) | `KXFED` | 42 | 2021-07 → 2026-10 | **0** (books one-sided) | 1 | 1c |
| Jobless claims | `KXJOBLESS`, `KXJOBLESSCLAIMS` | 134 | 2021-07 → 2022-11, then 2025-06 → 2026-11 | **52** (2 in 2021–22, 50 in 2025–26) | 62 | 4c |
| **Total** | | **463** | | **267** | 306 | |

Notes on the table:
- These are **events**, not release days. CPI and core CPI share a day, as do payrolls and unemployment.
- **Distinct release days with a quoted ladder** across the families H1 uses (CPI, payrolls, GDP, core PCE, FOMC), 2022-01 → 2026-10: **117–118**.
- Census rules:
  - Only markets with lifetime volume ≥ 100 contracts were candle-checked (3,024 markets). All requests returned HTTP 200.
  - Of those markets, 268 had no candle in the 30 hours before the close, and count as unquoted.
  - The "just before the close" snapshot is the last candle at or before the market close. For the four events that closed after the release (the "Market close vs release" row above), that candle can be post-release. The draft prereg cuts at the release instant instead.

**Other Kalshi families** (event counts from `/events`; not candle-checked):

| Family | Series | Events listed | Span | Use for this book |
|---|---|---|---|---|
| S&P 500 daily close range | `KXINX` (legacy `INX`, `INXD`, `INXW`) | 1,164 | 2022-04 → today | None. An implied distribution of the index the book holds, which is what options already give |
| 10-year yield daily | `KXTNOTED` (legacy `TNOTED`) | 664 | 2023-02 → 2026-07 | Same: a level market |
| WTI oil daily | `KXWTI` (legacy `WTI`) | 887 | 2022-09 → today | Not held |
| Gold weekly / monthly | `KXGOLDW`, `KXGOLDMON` | 38 / 10 | 2026 only | Too short |
| New tariffs (monthly) | `KXNEWTARIFFS` | 11 | 2026 | Too few |
| Government shutdown | `KXGOVTSHUTDOWN` | 3 | 2026 | Too few |
| NBER recession (annual) | `KXRECSSNBER` | 6 | 2022 → 2027 | Too few, and it is regime timing |
| Fed decision (multi-outcome) | `KXFEDDECISION` | 39 | 2023-05 → | Duplicates `KXFED` |
| ISM manufacturing PMI | `KXISMPMI` | 16 | 2025-03 → | Too short |

### 1.2 Polymarket (verified 2026-11-19)

| What | Finding |
|---|---|
| Event lists | `gamma-api.polymarket.com/events?tag_slug=…&closed=true`, public. **Pages above 50 rows are served gzip-only (HTTP 406 otherwise).** Documented limit: 500 req/10 s on `/events` |
| Price history | `data-api.polymarket.com/v2/prices-history?token_id=…&interval=max`, public. **3-hour and 12-hour series are permanent back to 2022-11-18; 1-, 5- and 30-minute grains expire after about 7, 60 and 90 days.** Limit 200 req/10 s. The older `clob.polymarket.com/prices-history` returned **an empty series** for a resolved 2024 market |
| Fields | One `price` per point (last trade/mid), **no bid/ask history**, and a final settlement point (0/1) |
| US macro coverage (closed events, by tag; titles only) | **Fed decision: 25** (Dec 2023 → Oct 2026; volume from $57k to $208M per meeting). **US CPI: 77** closed events (2023: 1, 2024: 14, 2025: 26, 2026: 36), i.e. one market a month from 2024 and several per release from 2025. **US jobs/unemployment: 33** (from Sept 2024). **US GDP: 16** (from 2025). **US recession:** 3–4 events |
| Who can trade it | A US person cannot open positions (T-403). Reading the prices is unrestricted |

Polymarket adds a Fed cross-check from 2024 and nothing that Kalshi does not already cover with a longer, quoted history.

### 1.3 What the project already archives (read-only)

| File | State on 2026-11-19 | Value given §1.1–§1.2 |
|---|---|---|
| `kalshi_snapshots.parquet` | 26,374 rows. Before 2026-11-19 they are sports parlays (T-404/T-405). The **first macro-series collection** is the 11-19 run: 5,080 rows over 365 series (Economics 2,888; Financials 1,241; Commodities 564; Politics 244; Crypto 143) | One snapshot a day of bid/ask **and sizes**. Kalshi's candles already give bid/ask hourly for free, so the archive's unique content is the **top-of-book size**, which candles lack |
| `kalshi_kxfed_snapshots.parquet` | 18,796 rows, 2026-07-07 → 2026-11-19, 101 snapshot days, 14 KXFED events | Redundant with `/historical` candles, except for sizes |
| `polymarket_snapshots.parquet` | 56,721 rows, 2026-06-10 → 2026-11-19. bid/ask only from 2026-11-18. 74 macro-keyword markets | Polymarket keeps only 3h/12h permanently, so the archive's daily bid/ask from 11-18 on is the one thing not otherwise recoverable |
| `polymarket_resolutions.parquet` | 242 rows, mostly 5-minute crypto markets | Not macro |

**Conclusion on the archive:** keep it running. It costs nothing; it keeps sizes and Polymarket quotes that the venues do not keep; and it insures against a venue withdrawing its free history (a policy that could change without notice). But no test in this note needs it: today the venues serve the history themselves.

### 1.4 What is not free

- **The Wall Street survey consensus** (Bloomberg / Reuters median forecast per release): no free, licence-clean historical series found. H2 below needs it.
- **Kalshi's forecast-percentile history** needs an account.
- **Fed funds futures history** (CME) is not free. Kalshi's `KXFED` stands in for it from 2022.

---

## 2. What the literature already says

1. **Accuracy.** Diercks, Katz & Wright, "Kalshi and the Rise of Macro Markets", FEDS 2026-010 (Feb 2026) [S1], read 2026-11-19.
   - On release day, Kalshi beats or ties the Bloomberg consensus. Headline CPI MAE: Kalshi mean 0.069, median 0.063 (significant at 10 %), against Bloomberg's 0.081. Core CPI and unemployment are tied.
   - The Kalshi Fed ladder's median and mode were **exact on the day before every FOMC since 2022**, significantly better than fed funds futures.
   - Their probability-integral-transform checks find the densities "fairly well calibrated", with "some evidence of risk premia overstating the odds of higher inflation and higher unemployment". A hawkish tilt in Kalshi's prices is therefore partly premium, not information, which weakens H2 further.
   - They study how the Kalshi fed-funds distribution responds to surprises: CPI significant (a 10 bp surprise moves the mean 3–4 bp), **PCE small, payrolls insignificant** over 2022–25. **They do not test asset returns.**
2. **Markets see through stale surveys.** Campbell & Sharpe (FEDS 2007-12; JFQA 2009) [S2, abstract read 2026-11-19], on Money Market Services consensus forecasts for 1990–2006:
   - consensus forecasts anchor on the previous month's release, giving "sizable predictable forecast errors";
   - but "bond yields react only to the residual, or unpredictable, component of the surprise and not to the expected piece".

   This is direct evidence against H2's mechanism.
3. **The announcement premium.** Savor & Wilson (JFQA 2013) [S3, from memory]: over 1958–2009, days with CPI, PPI, employment or FOMC news earned about 11 bp of excess return against about 1 bp on other days. Ai & Bansal (Econometrica 2018) [S4, from memory] explain it as pay for resolving uncertainty, which is the basis of H3.
   - The related **pre-FOMC drift** (Lucca & Moench, JF 2015) [S5, from memory] is reported to have disappeared in later data ("The Disappearing Pre-FOMC Announcement Drift", Kurov, Wolfe & Gilbert 2021) [S6; title verified, content from memory].
   - The project's own FOMC-cycle tests (T-250/T-268/T-291) were refuted.
4. **Trading the venue itself** was T-403's question (Bürgi–Deng–Whelan 2026): takers lose. That is not repeated here.

---

## 3. How this book could act on the information, and why every route is narrow

**What the book holds and when it trades.** It holds SPY/VOO at its core, MTUM/QUAL tilts, AGG/GLD sleeves, and cash/SGOV. It trades:
- once a day after the open, through the paper fleet at about 09:45 ET;
- on drift (about 0.3 % of the book a month; T-386, `docs/Sources/prereg_b8_execution_timing_2026-11-11.md`);
- on new contributions.

**Three structural limits apply to any prediction-market input:**

1. **The information is public at the same moment as the asset price.** A Kalshi forecast is free for every bond and equity desk to read. A forecast that is *better* than the survey earns money only if markets price off the *survey*, which Campbell & Sharpe find they do not.
2. **The surprise arrives before this system can trade.** CPI, jobs, PCE and GDP land at 08:30 ET. The move happens pre-market, so by the 09:45 trade it is priced. FOMC (14:00 ET) is intraday, but the book trades once a day.
3. **A held book's timing value scales with the traded fraction.** Moving the drift trade or a contribution by a day around a release touches about 0.3 % of the book. Even a perfect per-release oracle is worth about a few bp a year (T-386's arithmetic). Moving the whole book is not timing a trade: it is a regime switch, which is the stay-dead list's "regime-timing of anything" (three nulls, and T-333 at −5.16 pp/yr).

**What survives** is a per-event design, in which one release is one observation, a signal that refreshes at each release, and a fixed short hold. Such a design must also be big enough per event to be seen in about 45 events a year. §4 tries the three best candidates against that.

---

## 4. The candidate hypotheses (at most three)

**Shared planning values:**
- release-day close-to-close σ: **SPY 1.3 %** (sensitivities 1.0 / 1.6), **AGG 0.45 %**.
  - Grounding: the **unconditional** daily σ over all trading days 2022-01 → 2026-05 in the project's total-return files (`data/processed/tr_reconciled/`) is SPY 1.11 %, AGG 0.40 %, TLT 1.01 %.
  - Announcement days are noisier, so I scaled these up.
  - I deliberately did **not** compute σ on release days. That would read the outcome variable on the events.
- bar `z_c` = E[max of 372 nulls] = **2.96** (computed; one trial: 1.645);
- power 80 %;
- MDE = `(z_c + 0.84) · σ / √N`;
- pass probability = `Φ(δ·√N/σ − z_c)`; for correlations, Fisher's `Φ(atanh ρ · √(N−3) − z_c)`.

### H1 — validity: does Kalshi's last pre-release forecast explain the release-day bond move? (NOT a trade)

- **Theory (ex ante):** hawkish surprises raise the expected rate path, so bonds fall. DKW show Kalshi measures "expected" at least as well as the survey.
- **Design:** one observation per release day across CPI, core PCE, payrolls, advance GDP and FOMC.
  - Surprise = settled value − Kalshi implied median, read from the last hourly candle before the release instant (quoted mids, monotone-enforced, rounding-boundary aware).
  - Hawkish-signed and standardised within family.
  - AGG total-return close-to-close on the release day, regressed with family fixed effects.
  - Full rule in the DRAFT prereg.
- **Independent observations** (census planning count: ≥ 3 quoted strikes whose mids bracket 0.5):
  - **107 release days** from 2022-01 to 2026-05-22, the end of the AGG total-return file: CPI 45, payrolls 44, GDP 14, core PCE 4, FOMC 0;
  - **117** if AGG is refreshed through 2026-10: CPI 49, payrolls 49, GDP 15, core PCE 4, FOMC 0.
  - No two eligible events fall on the same day. Release days are distinct, and clustering is weak.
- **MDE:** |ρ| = **0.36** (107 days) / **0.34** (117) at z 2.96; 0.24 / 0.23 at z 1.645.
- **Pass probability:**
  - CPI alone is likely ρ ≈ −0.5;
  - payrolls are likely weaker (DKW: insignificant for the fed-funds path in 2022–25); GDP is untested there and probably weaker still;
  - core PCE and FOMC add almost no eligible days (thin or one-sided ladders).
  - At pooled |ρ| 0.30 → 58 % (107 days) / 63 % (117); at 0.40 → 91 % / 94 % (z 2.96).
  - Weighted over my prior on |ρ| (0.2: 15 %, 0.3: 30 %, 0.4: 35 %, 0.5: 20 %): **≈ 72 % / 75 % at z 2.96, ≈ 93 % / 94 % at z 1.645.** V3 and V4 of the prereg trim this a little.
- **Trials added:** 1, if the director counts a calibration check in the strategy family; it changes `z_c` from 2.962 to 2.963.
- **Regime timing in disguise?** No. It takes no position.
- **What a pass buys:** permission to *show* the forecast and the realised surprise to the owner (digest, attribution), and a validated input for any later design. **Nothing tradeable.**

### H2 — pre-release positioning on the gap between Kalshi and the survey consensus (tradeable form)

- **Theory:** if bond and stock prices sit on the survey consensus `C`, and Kalshi's `K` is the better forecast, then the expected release-day move is `β·(K − C)`. That is knowable at the prior close.
  - Trade: before the release, move the AGG sleeve to SGOV when `K − C` is hawkish, and hold otherwise. The SPY version is analogous, but its sign flips by regime.
- **Breaking it:**
  - Campbell & Sharpe find markets already discount the predictable part of survey surprises.
  - The same desks can read Kalshi's public prices (an inference; see §8).
  - **There is no free consensus history**, so the test as theorised cannot be built on free data.
  - The Kalshi-only proxy is the forecast's own revision over the last five days. It assumes the bond market ignores news Kalshi absorbs, which is weaker still.
- **Size if real:**
  - The part of the survey's error that Kalshi can predict is bounded by how much better Kalshi forecasts. On headline CPI, DKW's MAE improvement is 0.012–0.018 pp (0.081 against 0.069 / 0.063); on core CPI and unemployment it is ≈ 0.
  - My planning value: AGG moves ≈ 0.4–0.5 % per 0.1 pp of CPI surprise. That makes `δ` ≈ **0.03–0.08 % per event** on the moved sleeve.
  - At 15 % of the book × 44 events, that is ≲ 0.5 %/yr even if real.
- **Independent observations:** at most the ≈ 117 release days with a quoted ladder (the H1 census). But `K − C` is persistent within regimes (2022's consensus was systematically low), so the effective N is smaller.
- **MDE (AGG, N = 117):** **0.16 %** at z 2.96 (0.10 % at z 1.645), above the plausible 0.03–0.08 %.
- **Pass probability:** at δ = 0.05 %, 3.9 % (z 2.96). Times a ≈ 15 % prior that markets anchor on the survey, **≈ 0.6 %**, and **0 % on free data**.
- **Trials added:** 1 per instrument; the SPY and AGG arms would be 2.
- **Regime timing in disguise?** Partly. A per-event signal, but its persistent part sorts by regime.

### H3 — the announcement premium, scaled by Kalshi's pre-release uncertainty (tradeable form)

- **Theory:** announcement-day returns pay for resolving uncertainty (Savor–Wilson; Ai–Bansal). Kalshi's ladder measures the uncertainty directly (the implied spread of the print).
  - Trade (Roth-legal): hold an extra unit of equity (SSO for SPY) on announcement days whose Kalshi-implied uncertainty is above its trailing median; 1× otherwise.
- **Breaking it:**
  - The premium's post-2010 evidence is weak, and the pre-FOMC drift faded.
  - The book already holds SPY on every announcement day and so already earns any premium. Only the *extra* unit is new.
  - It is levered-ETF timing, a family refuted here (T-382, T-294).
  - Kalshi's implied uncertainty is **persistent, and contaminated by contract redesigns**. I measured a quotes-only proxy (no outcome, no return): the number of quoted strikes priced between 10c and 90c just before the release, averaged per year.
    - CPI: 3.9 in 2022, 2.2 in 2023, 1.5 in 2024, 1.25 in 2025, 2.2 in 2026.
    - Payrolls: 2.3–3.0 through 2025, then **10.4 in 2026**, when Kalshi re-cut the ladder into finer strikes.

    "High-uncertainty events" therefore sorts mostly by year and by ladder design, **so this IS regime timing in disguise**, with an effective N close to the number of regimes, not events.
- **Independent observations:** about half of the eligible days, ≈ 75–90.
- **MDE (σ 1.3 %, N = 88):** **0.53 %** per event at z 2.96 (0.34 % at z 1.645). The plausible premium is 0.10–0.20 %.
- **Pass probability:** δ 0.10 % → **1.3 %**; δ 0.15 % → **3.0 %**; δ 0.20 % → 6.4 % (z 2.96). At z 1.645: 18 / 29 / 42 %.
- **Trials added:** 1.

### Summary

| | Design | Events now | MDE (z 2.96) | Plausible effect | Pass probability (z 2.96) | Trials | Regime timing? | Free data? |
|---|---|---|---|---|---|---|---|---|
| **H1** validity | AGG return on standardised Kalshi surprise | 107 (117 after an AGG refresh) | \|ρ\| 0.36 | \|ρ\| 0.3–0.5 | **≈ 70–75 %** (≈ 93 % at z 1.645) | 1 | No (no position) | **Yes** |
| H2 survey gap | AGG→SGOV one day before hawkish K − C | ≤ 117 | 0.16 %/event | 0.03–0.08 % | < 1 % | 1–2 | Partly | **No** (consensus) |
| H3 uncertainty premium | SSO on high-uncertainty release days | ≈ 75–90 | 0.53 %/event | 0.10–0.20 % | 1–6 % | 1 | **Yes**, mostly | Yes |

---

## 5. When would enough events exist for a forward per-event test?

The forward archive adds about 44 distinct release days a year: 12 CPI, 12 jobs, 12 PCE, 4 GDP and 8 FOMC make 48 releases, and a few share a day. Claims are excluded.

| Form | σ | Plausible δ | Events for 80 % power at z 2.96 | Years from zero at 44 (H3: 22) a year | Date, counting the ≈ 117 quoted release days already in the free history (H3: half) |
|---|---|---|---|---|---|
| H2 on SPY | 1.3 % | 0.20 % | 611 | 13.9 | ≈ 2038 |
| H2 on SPY | 1.3 % | 0.10 % | 2,446 | 55.6 | ≈ 2080 |
| H2 on AGG | 0.45 % | 0.05 % | 1,172 | 26.6 | ≈ 2051 |
| H3 | 1.3 % | 0.15 % | 1,087 | 49.4 | ≈ 2074 |

In MBL terms, a per-event Sharpe of 0.115 (0.15 % / 1.3 %) annualises to 0.77 at 44 events a year (0.54 at 22). The required annualised Sharpe on 4.8 years is 2.96/√4.8 = **1.35**.

**No forward date inside a useful horizon exists.** The fresh-eyes audit's "per-event niche" class needs effects that are large *per event* relative to per-event noise, as with odd-lot tenders (3–8 % against 8 %). Here the ratio is about 0.1. These are time-series timing rules that happen to fire on event days.

---

## 6. Recommendation

1. **Close the trading question for this book on free data.** Do not register H2 or H3. Both are hopeless at the bar (H2 < 1 % and not buildable on free data; H3 1–6 % and regime timing in disguise). No trial is spent.
2. **Keep the archive running** (T-405), as it is: free, already deployed, and the only keeper of top-of-book sizes and Polymarket bid/ask. **Do not build a separate forward recorder for a per-event test.** §5 shows no such test reaches power before the late 2030s, and the venues keep the history anyway.
3. **H1, the validity check, only if the owner wants the information shown.** If the director wants the digest or advisor layer to say, before a release, "Kalshi expects core CPI 0.3 %; the chance of 0.4 % or more is 22 %", and after it, "the print beat Kalshi by 0.1, which explains AGG's −0.4 %", then freeze the draft prereg and run it once.
   - It costs about 45 minutes of public API calls and a short local run.
   - It probably passes (≈ 70 % at z 2.96), and the pass licenses only the display ("informs, never steers"). A fail at the honest-N bar would most likely mean "not demonstrable on ~100 days", not "Kalshi is wrong"; the verdict text must say which.
   - Displaying the *forecast* alone, labelled as Kalshi's, needs no test. Only the attribution claim does.
4. **The one adjacent idea worth a separate look is not a prediction-market question.** Brooks, Katz & Lustig (NBER WP 25127, 2018; abstract read 2026-11-19) document **post-FOMC announcement drift** in longer Treasury yields after Fed funds target changes. Their mechanism: bond-fund investors sell gradually, so arbitrageurs absorb a slowly rising supply.
   - It conditions on the target change itself, which is free back to the 1990s (≥ 250 meetings), not on Kalshi.
   - It is per-event, has an ex-ante theory, and acts on the AGG sleeve.
   - Whether to scope it is the director's call. It first needs a supersession check against T-250/T-268/T-291 and the stay-dead list, and a ceiling check: target changes are lumpy (none at most meetings), and moving a 15 % sleeve may still be worth only bp a year.

---

## 7. Incidental findings (for the director)

1. **The local archive is not the scarce resource.** Kalshi serves hourly and minute bid/ask candles for every settled market since 2021, and Polymarket serves 3h/12h prices since 2022-11. Any historical study should pull from the venues. The archive's unique fields are top-of-book **sizes** (Kalshi) and **bid/ask** (Polymarket, since 2026-11-18).
2. **Kalshi re-ticketed its history.** Legacy events (`CPI-…`, `PROLLS-…`, `FED-…`, `TNOTED-…`) are listed inside the KX series, while the legacy series tickers return zero events. A recorder or resolver keyed on legacy series would see nothing. T-405's KX-series discovery is correct.
3. **Gaps in Kalshi's history:**
   - jobless claims have **no events from 2022-12 to 2025-05** (`JOBLESS` ends 2022-11; `KXJOBLESSCLAIMS` starts 2025-06);
   - core PCE has 4 events before 2025;
   - payrolls run `PROLLS` 2022-03 → 2023-02, then `KXPAYROLLS` from 2023-03.
4. **Polymarket API hazards for a future script:**
   - `gamma /events` returns HTTP 406 unless gzip is accepted, for pages above 50 rows;
   - `clob /prices-history` returns an **empty** series for a resolved market, so use `data-api /v2/prices-history`;
   - fine grains silently expire (an explicit `bucket_seconds` over an expired window returns an **empty page**, by design). A fail-closed reader must treat empty as missing, never as "no change".
5. **No published unauthenticated Kalshi rate limit.** A cloud job should back off on 429 and log every one: the limit can change without notice.
6. **Kalshi re-cuts its ladders.** The payrolls ladder went from about 3 strikes priced between 10c and 90c to about 10 in 2026. Any series built on ladder width, strike count or the number of "live" strikes breaks at a redesign; a forward recorder should log each event's strike grid.
7. **The total-return ETF files end 2026-05-22.** All 40 files in `data/processed/tr_reconciled/` (SPY, AGG, GLD, TLT, IEF, …) end there; the files were written 2026-07-02. H1's window ends at that date unless AGG is refreshed through the total-return writer. The canonical `data/processed/AGG_1d.csv` is split-only (known; it is ≈ 3.3–4.1 pp/yr below the TR file in 2023–25) and must not stand in.

---

## 8. UNCONFIRMED items

1. Savor & Wilson (2013), Ai & Bansal (2018), Lucca & Moench (2015), Kurov et al. (2021): their bibliographic records were checked on Crossref (DOIs in Sources), but their findings are cited from memory and were not re-read today. (Campbell–Sharpe and Brooks–Katz–Lustig: abstracts read.)
2. The planning σ values (SPY 1.3 %, AGG 0.45 % on release days) are planning values, deliberately **not** measured from the project's price files on release days.
3. "Bond and equity desks read Kalshi's prices": an inference (the prices are public and free; the DKW paper is Fed-staff work), not verified.
4. That no free historical survey consensus exists: none found. Calendar sites show forecasts, but I found no licence-clean bulk history.
5. Kalshi's unauthenticated rate limit (unpublished).

---

## Sources (read 2026-11-19 unless marked)

1. Diercks, A. M., Katz, J. D. & Wright, J. H., "Kalshi and the Rise of Macro Markets", Finance and Economics Discussion Series 2026-010, Federal Reserve Board, Feb 2026, https://www.federalreserve.gov/econres/feds/kalshi-and-the-rise-of-macro-markets.htm (PDF https://www.federalreserve.gov/econres/feds/files/2026010pap.pdf; also NBER w34702). Table 3 (forecast accuracy) and §7.2 (surprise responses) read.
2. Campbell, S. D. & Sharpe, S. A., "Anchoring Bias in Consensus Forecasts and Its Effect on Market Prices", FEDS 2007-12, https://www.federalreserve.gov/pubs/feds/2007/200712/200712abs.html (abstract read 2026-11-19); published JFQA 44(2), 2009.
3. Savor, P. & Wilson, M., "How Much Do Investors Care About Macroeconomic Risk? Evidence from Scheduled Economic Announcements", JFQA 48(2), 2013 (working paper doi:10.2139/ssrn.1364265; findings from memory).
4. Ai, H. & Bansal, R., "Risk Preferences and the Macroeconomic Announcement Premium", Econometrica 86(4), 2018, doi:10.3982/ECTA14607 (findings from memory).
5. Lucca, D. & Moench, E., "The Pre-FOMC Announcement Drift", Journal of Finance 70(1), 2015 (working paper doi:10.2139/ssrn.1923197; findings from memory).
6. Kurov, A., Wolfe, M. H. & Gilbert, T., "The Disappearing Pre-FOMC Announcement Drift", Finance Research Letters, 2021, doi:10.1016/j.frl.2020.101781 (findings from memory; the title states the result).
7. Brooks, J., Katz, M. & Lustig, H., "Post-FOMC Announcement Drift in U.S. Bond Markets", NBER WP 25127, 2018, https://www.nber.org/papers/w25127 (abstract read 2026-11-19).
8. Kalshi API docs: "Historical Data" https://docs.kalshi.com/getting_started/historical_data ; "Get Historical Market Candlesticks" https://docs.kalshi.com/api-reference/historical/get-historical-market-candlesticks ; "Get Market Candlesticks" https://docs.kalshi.com/api-reference/market/get-market-candlesticks ; "Batch Get Market Candlesticks" https://docs.kalshi.com/api-reference/market/batch-get-market-candlesticks ; "Get Events" https://docs.kalshi.com/api-reference/events/get-events ; "Get Event Forecast Percentile History" https://docs.kalshi.com/api-reference/events/get-event-forecast-percentile-history ; "Rate Limits and Tiers" https://docs.kalshi.com/getting_started/rate_limits ; index https://docs.kalshi.com/llms.txt
9. Kalshi public API, live probes 2026-11-19: `GET https://api.elections.kalshi.com/trade-api/v2/historical/cutoff`, `/series?category=Economics|Financials`, `/events?series_ticker=…`, `/historical/markets?event_ticker=…`, `/markets?event_ticker=…`, `/historical/markets/{ticker}/candlesticks`, `/series/{series}/markets/{ticker}/candlesticks`.
10. Polymarket docs: "Rate Limits" https://docs.polymarket.com/api-reference/rate-limits ; "Get a token's price history" https://docs.polymarket.com/api-reference/markets/get-a-tokens-price-history ; "Get prices history" https://docs.polymarket.com/api-reference/markets/get-prices-history ; index https://docs.polymarket.com/llms.txt
11. Polymarket public API, live probes 2026-11-19: `gamma-api.polymarket.com/events?tag_slug=…&closed=true&limit=50`, `data-api.polymarket.com/v2/prices-history?token_id=…&interval=max`, `clob.polymarket.com/prices-history?market=…`.
12. Crossref metadata API (`api.crossref.org/works?query.bibliographic=…`), used 2026-11-19 to check the bibliographic records of sources 3–6.
13. [REPO] T-403 design note; the fresh-eyes and salvage audits (`docs/Audit/fresh_eyes_and_salvage_audits_2026-11-14.md`); T-386 (execution timing); T-404/T-405 ledger rows; `data/macro_data/alt/*.parquet` (read-only).
