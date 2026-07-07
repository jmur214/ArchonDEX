---
run_date: 2026-07-08
agent: external research agent (no codebase access, web-enabled)
model: not recorded (run predates the self-report rule — see SESSION_PROCEDURES.md "External prompt runs")
executed_by: user (relayed verbatim to the director)
prompt_working_copy: data/coordination/prompt_research_agent_2026_07_07.md (v2, expansive 16-question form)
status: findings triaged 2026-07-08 (see the Director Triage section at the bottom)
---

# External Prompt Run — Research Agent v2 (Info-Layer program + standing-strategy stress test)

This doc is the permanent record of the prompt AS RUN and the findings VERBATIM,
per the archive-every-run rule (SESSION_PROCEDURES.md, user directive 2026-07-08).

---

# THE PROMPT (as run)

# PROMPT — External Research Agent (no codebase access) — v2, expanded

You are a research analyst supporting an autonomous retail algorithmic trading project. You have NO access to the project's codebase — everything you need is in this brief. Your job is deep, source-cited research. Use web search and any public literature: academic, practitioner, regulatory, community. This is a wide-ranging brief on purpose — the project has repeatedly found that doors it closed on stale information contained real value when reopened, so we are asking you to look everywhere the missing ingredient might be *information we don't have*.

## Project context (all you need to know)

- Retail scale: $5K–$250K, a Roth IRA plus (soon) a taxable brokerage. US equities/ETFs via Alpaca. The investor is ~40 years from the end goal, contributes ~$7K/yr, explicitly will NOT sell in downturns, and defines success as **maximum terminal wealth vs buy-and-hold SPY** — with the system's drawdown protection as the mechanism that lets them stay fully invested.
- The validated core: a **multi-speed (2/5/10-month) long/flat trend ensemble on SPY/AGG/GLD** — beats the investor's Schwab robo on wealth, Sortino, and max-drawdown in a bias-corrected backtest (now live in paper trading). An offense variant — **2× SPY (via SSO) when the trend is ON, cash when off** — beat buy-and-hold SPY ~×1.2 on terminal wealth over 26 years including the accumulation (contributing) case.
- A comprehensive multi-year hunt found **no extractable alpha in free price-data vocabulary** (momentum variants, cross-sectional factors, VRP, PEAD, carry, intraday, event studies — all null under honest point-in-time universes, realistic costs, bootstrap-CI gates). One real-but-parked exception: **closed-end-fund discount reversion** (statistically significant on a bias-conservative test) parked ONLY because no affordable point-in-time NAV history exists.
- Now launching an **Information + Judgment Layer**: (1) a point-in-time news panel (Alpaca/Benzinga, verified ~11yr depth, delisted tickers covered); (2) daily-archived prediction-market data (Kalshi/Polymarket), especially Fed rate-path odds — information source only, never traded; (3) a **forward-only LLM analyst** producing a daily schema-validated note with machine-resolved, Brier-scored probabilistic predictions, climbing a frozen authority ladder (report-only → virtual shadow book → its own paper account). LLM evaluation of historical returns is forbidden (training-data memorization = look-ahead).
- Discipline: pre-registered tests, block-bootstrap CIs, honest trial counting, survivorship paranoia, "brutal realism beats reassurance."

## How to answer

For every question: findings with citations (author/venue/year, links), an honest confidence level, and a **"so what" line — what this changes about our design if true**. Flag thin or conflicted literature instead of smoothing it over; "unknown/contested" is a valuable answer. Prioritize within each part as marked, but partial depth on many questions beats exhaustive depth on one.

---

## PART I — The active program (highest priority)

**Q1 — News-based trading: what actually survives?** Post-2015 evidence on news sentiment/volume/novelty as signals for US equities and index-level risk sizing. Which published effects replicated out-of-sample vs decayed post-publication (McLean-Pontiff lineage)? What's realistically extractable at daily-rebalance retail latency? Dictionary methods (Loughran-McDonald, VADER) vs transformer/LLM sentiment — measured difference? Anything documented about **Benzinga's feed** specifically (coverage breadth, revision practices, known biases)?

**Q2 — LLMs as market analysts/forecasters: the honest state of the art.** Published results on LLM stock-picking, macro forecasting, probabilistic prediction — and critically, which evaluations are contaminated by training-cutoff memorization and how the careful ones control for it. Known calibration properties of frontier LLMs (base-rate hedging? overconfident tails?). Demonstrated prompt-injection attacks on LLM pipelines ingesting untrusted text, and current best defenses. Documented failures of LLM trading agents.

**Q3 — Prediction markets as an information source.** Calibration evidence for Kalshi and Polymarket vs CME FedWatch / fed funds futures on rate-path expectations. Do prediction-market odds lead or lag asset prices around FOMC/CPI? How do professionals consume implied rate-path distributions (levels vs changes)? **Is there any free/cheap HISTORICAL archive of implied Fed-path or prediction-market odds** (our own archive only starts accruing now — backfill would be a real unlock)?

**Q4 — Evaluating a forecaster rigorously.** Forecasting-tournament best practice (Tetlock/GJP, Metaculus): scoring baselines (climatology, market-implied, persistence), minimum resolved-count for discrimination, calibration diagnostics, and known gaming modes (base-rate parroting, gimme-padding, horizon selection, resolution ambiguity). What does a genuinely hard promotion gate look like?

## PART II — Parked decisions where information is the missing piece (high priority — each answer could directly unpark a decision)

**Q5 — CEF NAV history (the parked alpha).** We measured real closed-end-fund discount-reversion alpha but parked it for lack of affordable point-in-time NAV data (CRSP is the standard, priced institutionally). Hunt for ANY cheaper path: academic authors' posted datasets, CEFConnect/CEFA historical archives, Wayback Machine coverage of NAV pages, fund-sponsor archives, SEC N-CEN/N-PORT filings as a NAV source, retail data vendors. Also: the current state of the CEF discount opportunity post-2024 (activism wave, fund consolidations) — is the anomaly still live?

**Q6 — Micro-futures CTA replication at retail scale.** Evidence on replicating diversified trend-following (the classic CTA family) with micro futures at $15–65K: realistic universe breadth, margin, roll costs, broker approval friction, and documented retail/small-account live track records (not backtests). Cheapest honest data path for 15–20yr continuous futures history (Databento? Norgate? free alternatives?). The §1256 60/40 tax treatment's measured after-tax advantage for monthly-turnover futures strategies.

**Q7 — The cost of leverage: SSO vs the alternatives.** For a trend-GATED 2× equity exposure held weeks-to-months at a time: compare daily-reset 2× LETFs (SSO: ER + embedded financing), capital-efficient stacked ETFs (NTSX 90/60, RSSB, and kin — Roth-holdable, no margin), micro futures, and portfolio-margin box-spread financing. Which is cheapest per unit of exposure at our scale, what are the failure modes of each (volatility decay in chop for LETFs, tracking/roll for stacked funds), and is there live evidence on gated-LETF strategies run with real money? Also: known critiques of "Leverage for the Long Run" (Gayed) implementations.

**Q8 — Taxable-account design (the wrapper is about to open).** Asset-location best practice for a two-account (Roth + taxable) system running trend strategies: which sleeve goes where and the measured cost of getting it wrong; tax-loss harvesting's realistic net value at retail (robo TLH claims vs independent measurements); wash-sale traps for systematic monthly rebalancers running near-identical ETFs across accounts; direct-indexing at small scale — real edge or marketing?

## PART III — The standing strategy: stress-test our own convictions (medium priority)

**Q9 — Lifecycle/accumulation investing.** The Ayres-Nalebuff "lifecycle leverage" literature (leverage when young, de-lever with age — time diversification): its empirical record, published critiques, and whether anyone has combined it with trend gating. Glide-path evidence for a 40-year accumulator. Sequence-of-returns risk: when does it start mattering for us?

**Q10 — The behavior gap and commitment devices.** Measured gap between investment returns and investor returns (Dalbar critiques included — use the careful studies). Evidence on automation/commitment devices preventing capitulation. This quantifies the system's core value proposition ("the machine won't sell in March 2020") — how big is that edge, honestly?

**Q11 — What evidence-backed practices do sophisticated small investors actually run** that we haven't tested? Scan practitioner/quant-retail communities and small-RIA practice (return stacking, managed-futures allocations, buffered products [likely bad — verify], factor tilts that survived replication, TIPS ladders, anything with credible evidence at retail scale). We've tested a lot — flag only things with genuine evidence, and say what the evidence is.

**Q12 — Trend-following's live out-of-sample record.** The strategy class we deployed: how has time-series momentum performed LIVE (funds, indices like SG Trend) since the key publications (post-2013)? Is the much-discussed "trend decay" real, regime-dependent, or crowding-driven? What conditions make monthly-speed trend fail structurally (2015-16-style chop clusters) and is there evidence on multi-speed ensembles mitigating it?

## PART IV — The data landscape (medium priority — the gap audit repeatedly found gold here)

**Q13 — Map the free/cheap PIT-honest data world.** A structured inventory of datasets a retail quant can get free or <$200 one-time, with survivorship-clean or vintage-stamped history: delisted-equity prices, options surfaces (CBOE DataShop? ORATS samples?), futures, macro vintages (ALFRED), academic replication sets (Open Source Asset Pricing, JKP global factors, Ken French), SEC full-text/EDGAR derivatives, insider/13F/short-interest, crypto, international ETFs. For each: coverage, PIT-honesty, access path, catch. **Emphasize sources you'd guess we DON'T know about** — we already use EDGAR, Stooq, CBOE index data, FRED/ALFRED, Alpaca, yfinance.

**Q14 — Anything structurally new in 2025-26?** New/changed data access (regulatory pushes for free market data, consolidated tape developments, exchange API changes), new brokers/APIs relevant to small algorithmic accounts, changes at Alpaca specifically (reliability record, paper-vs-live fill fidelity evidence), and the T+1/PFOF/fractional-share microstructure picture as it affects daily-rebalance retail execution.

## PART V — The open horizon (do NOT skip — this is why the brief is expansive)

**Q15 — Autonomous-system operational risk.** Documented failure modes of small autonomous trading systems (not Knight Capital — our scale): runaway loops, stale-data trades, credential leaks, cloud-scheduler failures, LLM-agent-specific incidents. Best practices for kill-switches, dead-man monitoring, and change control that a two-person (human + AI) operation can actually sustain.

**Q16 — What should we have asked?** You now know our system, goals, constraints, and everything above. Name the 3–5 most important questions this brief FAILED to ask — blind spots, risks, or opportunities implied by what you found while researching the rest — and answer the best one or two as far as you can. This section is mandatory and we weight it heavily; past external reviews found our biggest issues in exactly this category.

---

## Deliverable

One report, organized by part and question, each with citations + confidence + the "so what" line. End with: (a) a ranked top-10 "most decision-relevant findings" list across the whole report, and (b) the Q16 blind-spot section. Do not pad. Where Parts II–V surface something that changes Part I's design, say so explicitly.

---

# THE FINDINGS (verbatim)

# Research Report: The Information + Judgment Layer and Standing-Strategy Stress Test

## TL;DR
- **The active program is worth building but only as an information/risk-sizing overlay, never as a standalone alpha source.** Post-2015 news-sentiment alpha is real but decays fast and is thin at daily retail latency; frontier LLMs forecast at roughly general-public (not superforecaster) level and are systematically miscalibrated by RLHF; prediction markets (especially Kalshi) are genuinely well-calibrated on Fed-path and beat futures/surveys on a small sample — so the forward-only, report-only-first authority ladder is exactly the right design.
- **Two parked decisions can be partially unparked now.** The CEF discount anomaly is still live post-2024 but the "affordable point-in-time NAV" problem is largely unsolved (CEFData/Nasdaq Fund Network history starts May 2012, weekly pre-2018; no cheap CRSP substitute exists) — and the anomaly's own economics are shifting under an activism wave and a June 2026 Supreme Court ruling. On leverage, capital-efficient stacked ETFs (NTSX/RSSB) are Roth-holdable and have historically cost *less* than their financing benchmark, making them a stronger gated-2x vehicle than SSO for a weeks-to-months hold.
- **The biggest risks are operational and behavioral, not signal-quality.** The measured behavior gap is ~1.2%/yr (Morningstar Mind the Gap 2025), not DALBAR's 848 bps, so quantify the "won't sell" edge honestly; and the most documented failure mode of small autonomous systems is silent stale-data/monitoring failure, which demands a dead-man switch and economic-health monitoring as first-class infrastructure.

---

## PART I — THE ACTIVE PROGRAM

### Q1 — News-based trading: what actually survives?

**Findings.** The McLean–Pontiff lineage is the anchor. McLean and Pontiff (2016, *Journal of Finance*) find published anomaly returns decline ~26% out-of-sample and ~58% post-publication. Chen and Zimmermann's *Publication Bias in Asset Pricing Research* (2022, arXiv:2209.13623) replicates this: 74% of return predictability persists out-of-sample in the first three years, so decay is real but not total. Falck, Rej and Thesmar's "When do systematic strategies decay?" (*Quantitative Finance*, 2022; arXiv:2105.01380) add that publication date is the dominant predictor: post-publication Sharpe decay of a newly published strategy increases ~5 percentage points per year, i.e., newer signals decay faster as arbitrage capital rushes in.

For news specifically, the honest read of recent work (e.g., the 2025 MDPI *JRFM* study using TextBlob/VADER/FinBERT, and the arXiv "Backtesting Sentiment Signals" 2507.03350) is that daily-news sentiment is a weak, decaying, cost-sensitive signal in equities, contested between "signal" and "noise" camps. The most credible extractable effects at daily latency are (a) news *volume/attention* and *novelty* spikes as risk/volatility indicators rather than directional alpha, and (b) index-level risk sizing rather than cross-sectional stock picking. On dictionary vs transformer methods: FinBERT/transformer sentiment consistently shows incremental predictive value over Loughran-McDonald/VADER dictionaries in ablation studies, but the measured gap is modest and often swamped by transaction costs. On the Benzinga feed specifically: I found no independent academic audit of coverage breadth, revision practices, or biases — this is a genuine evidence gap.

**Confidence:** High on the decay lineage; Medium on "news = risk-sizing not alpha"; Low/thin on Benzinga-specific properties.

**So what:** Confirms the Part-I decision to treat the news panel as an *information/risk-sizing* input, not a directional alpha engine. Use news volume/novelty to modulate exposure or flag regime stress, not to pick stocks. Do NOT expect cross-sectional sentiment alpha to survive costs at daily rebalance. Budget effort to characterize Benzinga's own revision/timestamp behavior since the literature won't do it for you.

### Q2 — LLMs as market analysts/forecasters: the honest state of the art

**Findings.** Contamination by training-cutoff memorization is the central threat and is now well-documented. Lopez-Lira and Tang's GPT sentiment work, and the arXiv paper "Assessing Look-Ahead Bias in Stock Return Predictions Generated by GPT Sentiment Analysis" (2309.17322), show apparent predictive power that is inflated in-sample. "The Memorization Problem: Can We Trust LLMs' Economic Forecasts?" (arXiv:2504.14765) shows models can reconstruct identity even from anonymized/masked text, so masking is not a reliable safeguard. Formal detection tools now exist: the "Lookahead Propensity (LAP)" test (arXiv:2512.23847) — LAP is positive in-sample and collapses to zero after the training cutoff — and MemGuard-Alpha (arXiv:2603.26797), which reports in-sample accuracy rising with contamination (40.8%→52.5%) while out-of-sample accuracy falls (47%→42%). Careful evaluations restrict to strictly post-cutoff data, use time-stamped/leak-free models (DatedGPT, StoriesLM), or filter contaminated signals.

On raw forecasting skill: Halawi et al. (2024, NeurIPS; arXiv:2402.18563) built a retrieval-augmented GPT-4 forecaster that "nears the crowd aggregate" and beats it when the crowd is uncertain (Brier 0.199 vs crowd 0.246 in the 0.3–0.7 band) but underperforms when the crowd is confident because it "rarely outputs low probabilities… due to its safety training." ForecastBench (Karger et al., ICLR 2025, N=498) puts superforecasters at Brier 0.096, the general public at 0.121 (p<0.001), and the best LLM (Claude-3-5-Sonnet-20240620) at 0.122; a 2025 ForecastBench update has superforecasters at 0.081 vs GPT-4.5 at 0.101. Schoenegger et al. (2024) find a 12-LLM ensemble is statistically indistinguishable from 925 human forecasters, but with documented biases: an acquiescence bias (predictions skew >50% despite ~even resolution) and strong favoring of round numbers, and most models "badly calibrated, with… overconfidence."

On calibration: the GPT-4 Technical Report (2023) Figure 8 shows expected calibration error rising from ECE 0.007 (pre-trained) to 0.074 (post-RLHF) on MMLU — roughly a 10× degradation from post-training — and states "the post-training hurts calibration significantly." Multiple 2025 papers confirm RLHF/RLVR induces overconfidence. Caveat: the GPT-4 figure is a multiple-choice logprob measure, so generalization to forecasting calibration is inferential (though Halawi's independent hedging finding is consistent).

On prompt injection: this is a first-class risk for any pipeline ingesting untrusted news text. OWASP lists LLM01:2025 Prompt Injection as the top LLM risk. Indirect/RAG injection (Greshake et al. 2023) and memory/RAG poisoning (PoisonedRAG) are demonstrated. Real-world web-based indirect injection is now observed in the wild (Palo Alto Unit 42, Dec 2025), though mostly low-impact so far. Anthropic's Claude Opus 4.5 system card reports indirect-injection attack success of 4.7% at 1 attempt rising to 63.0% at 100 attempts — i.e., defenses are probabilistic, not absolute. Best current defenses: spotlighting/delimiting untrusted data, instruction hierarchy (Wallace et al. 2024), privilege separation / CaMeL-style "defeating prompt injections by design" (Debenedetti et al. 2025), and out-of-band verification.

**Confidence:** High on contamination and calibration degradation; High on prompt-injection risk; Medium on "LLMs ≈ general public, not superforecasters."

**So what:** Strongly validates every Part-I guardrail: forward-only evaluation (the contamination literature makes historical-return evaluation indefensible), the frozen authority ladder (LLMs are not superforecaster-grade and are overconfident, so earn trust slowly), and Brier scoring (needed to catch the documented hedging/round-number/acquiescence biases). ADD: the LLM's probabilities should be recalibrated (e.g., isotonic/Platt against its own resolved history) before use, and expect it to hedge toward 0.5 — a genuinely informative low-probability call is where it will most often be wrong. Prompt injection must be treated as an active adversary: the news-ingesting LLM must have NO tool access to the trading account (privilege separation), untrusted text must be delimited/spotlighted, and outputs must be schema-validated (which the design already does).

### Q3 — Prediction markets as an information source

**Findings.** The key new evidence is Diercks, Katz and Wright, "Kalshi and the Rise of Macro Markets" (Federal Reserve FEDS Working Paper 2026-010; NBER w34702). They find the "Kalshi median and mode have a perfect forecast record on the day before the FOMC meeting," a statistically significant improvement over both the NY Fed Survey of Market Expectations and fed funds futures, over ~12 meetings from 2022. Kalshi captured intraday shifts around Waller/Bowman remarks and the June 2025 jobs report that "surveys and futures did not." For headline CPI, Kalshi statistically beats Bloomberg consensus; for core CPI and unemployment it is statistically similar. They conclude these markets yield "well-calibrated, rapidly updating density forecasts," with positive CPI surprises moving the rate distribution ~4× more than negative ones. Important caveats: small sample (~12 meetings), working-paper (not peer-reviewed), and the "day-before" comparison is not apples-to-apples because survey/futures snapshots are taken 1–2 weeks earlier. Separately, Bonini et al., "Watching the FedWatch" (*Journal of Futures Markets*, 2026) find the FedWatch model predicts FOMC decisions with 88% accuracy 30 days out vs 75% for raw fed funds futures.

Methodology matters: CME FedWatch derives probabilities from 30-day fed funds futures (100 − implied EFFR); near-term it can only solve two outcomes and cannot replicate the full multi-outcome distribution that a prediction-market order book provides (Polymarket "FedWatch vs Polymarket" analysis). So for a *distribution* over outcomes, prediction markets are richer; for depth/liquidity, futures dominate. On lead/lag around FOMC/CPI: the direct high-frequency price-discovery study (information-share vs Treasuries/equities) does NOT exist — this is the thinnest part of the evidence. Diercks et al. show contemporaneous responsiveness but no formal lead-lag decomposition; an older Sornette et al. (PLoS ONE, 2011) macro study even finds the stock market leads the fed funds rate, but that is low-frequency and pre-2011.

On a free historical archive: there is no single free, long-horizon downloadable archive of FedWatch-style implied probabilities. CME's FedWatch download offers only ~1 year of history. Free paths: (a) reconstruct probabilities yourself from raw ZQ fed funds futures (FRED/Yahoo/Barchart); (b) the Diercks-Katz-Wright open-source repo (github.com/jdkatz21/Prediction_Markets_Public), limited by Kalshi's ~100-day API cutoff as of March 2026; (c) the Atlanta Fed Market Probability Tracker and Minneapolis Fed Market-Based Probabilities (free downloadable CSVs, but SOFR/Treasury-option-implied rather than fed funds).

**Confidence:** Medium-High on Kalshi calibration (strong new paper, small sample); High on "no free long backfill exists"; Low on lead/lag (evidence essentially absent).

**So what:** The "information source only, never traded" stance is correct and well-supported: Kalshi is well-calibrated on Fed path, so it is a legitimate input for index-level risk sizing. UNLOCK for the backfill problem: you cannot buy a clean implied-probability history cheaply, but you CAN reconstruct one from free raw ZQ fed funds futures back many years and cross-check against the Fed regional trackers — this is the realistic path to the "backfill unlock," not a purchased dataset. Note explicitly that Part-I's premise that the prediction-market archive "only starts accruing now" is partly avoidable via ZQ reconstruction.

### Q4 — Evaluating a forecaster rigorously

**Findings.** Forecasting-tournament best practice (Tetlock/Good Judgment Project; Metaculus; ForecastBench) centers on: strictly proper scoring (Brier/log score), which decomposes into calibration + discrimination; scoring *relative to a baseline* (the GJP standard subtracts the daily mean Brier across all active forecasters per question); and requiring a minimum resolved count for discrimination — GJP required forecasters to answer ≥25 questions per tournament to be ranked reliably. Benchmarks: elite superforecasters reach Brier ~0.02 on some sets and ~0.08–0.10 difficulty-adjusted; the general public ~0.12; always-50% = 0.25. Known gaming modes are well-documented: the arXiv "Alignment Problems With Current Forecasting Platforms" (2106.11248) shows scoring rules incentivize *selective question-picking* (skipping questions where you can't beat the base rate), and Tetlock's own commandments warn about it; the "Pitfalls in Evaluating Language Model Forecasters" (arXiv:2506.00723) documents a "winner's curse" where the top model among many is likely overestimated via systematic overconfidence, and warns Brier over-emphasizes high-base-rate questions. Other modes: base-rate parroting, gimme-padding (loading easy questions), horizon selection, and resolution ambiguity.

**Confidence:** High.

**So what:** A genuinely hard promotion gate should: (1) score the LLM against multiple baselines simultaneously — climatology/base-rate, market-implied (Kalshi/futures), and persistence — and require beating ALL of them, not just random; (2) mandate a minimum resolved-question count (GJP's ≥25 is a floor; for a daily forecaster, require well over 100 machine-resolved questions before any promotion) with pre-registered question sets to defeat selective picking and horizon-shopping; (3) require calibration AND discrimination improvements, not just aggregate Brier (to catch hedging and gimme-padding); (4) use block-bootstrap CIs on the Brier *differential* vs the market baseline and require the CI to exclude zero. This directly hardens the "frozen authority ladder." So what changes: promotion from shadow book to paper account should be gated on beating the *market-implied* baseline, because beating climatology alone is trivial and beating the crowd is the real bar.

---

## PART II — PARKED DECISIONS

### Q5 — CEF NAV history (the parked alpha)

**Findings.** The anomaly literature is deep and the mean-reversion of discounts is real (Pontiff 1995; Lee-Shleifer-Thaler 1991; the MDPI 2023 ARDL study finding cointegration/mean-reversion in 31 CEFs 1999–2018). On the *data* problem: CEFData.com/CEF Advisors is the specialist database, distributed via the Nasdaq Fund Network (NFN) on Nasdaq Data Link as "CEFUR" — but history only goes back to May 2012, and pre-Sept-2018 data is weekly, not daily. That is the affordability/PIT reality: the specialist archive is both shallow (2012) and coarse (weekly) for the early years, and institutionally priced for daily depth. Free/cheap paths worth testing: (a) Wayback Machine snapshots of CEFConnect/fund-sponsor NAV pages (irregular cadence, gap-ridden — usable only as spot checks); (b) SEC N-CEN/N-PORT filings as a NAV source (post-2019 for N-PORT, monthly, with reporting lags — PIT-honest but not daily and not deep historically); (c) fund-sponsor archives (Calamos, Nuveen) which publish Z-score/NAV history but per-sponsor and non-standardized.

On whether the anomaly is still live post-2024: yes, but its economics are shifting. Activism is concentrated in three firms (Saba, Karpus, Bulldog); as of Dec 31 2024, activists had $5.6B at work (~$20.7B with followers per CEFData). Forced tender offers (44 between 2015 and mid-2023) narrow discounts, and activists typically exit within a year. Critically, the Supreme Court ruled June 11, 2026 (*FS Credit Opportunities Corp. v. Saba*) that ICA Section 47(b) has no implied private right of action — narrowing the activist toolkit and favoring fund boards/poison pills. So the discount-narrowing *catalyst* channel just got weaker, which could keep discounts wider (more raw anomaly) but slower to close (less reliable reversion).

**Confidence:** High on the data-availability picture; Medium on "anomaly still live but catalyst-weakened."

**So what:** The parked decision stays *mostly parked* on data grounds — there is no cheap, deep, PIT-honest daily NAV history; the best available (CEFData via NFN) starts 2012 and is weekly pre-2018, which is enough for a limited, honest backtest but not a bias-conservative multi-decade one. If you accept a 2012-start, weekly-early dataset, you CAN run a pre-registered test now — that is the realistic unpark. But factor in the June 2026 SCOTUS ruling: model the reversion half-life as *longer* than the pre-2024 literature implies, and treat any backtest that assumes fast activist-driven convergence as optimistic.

### Q6 — Micro-futures CTA replication at retail scale

**Findings.** Trend-following/time-series momentum is one of the most robust anomalies (Moskowitz-Ooi-Pedersen 2012; Lempérière et al. 2014; Baltas-Kosowski 2020 find post-2008 Sharpes broadly comparable to pre-2008). Replication is feasible: ReSolve's "Peering Around Corners" provides a hypothetical net-of-cost replication of the SG Trend Index 2000–2023 across ~20 liquid markets (equities, FX, rates, commodities) and posts the daily return series free. Micro futures (Micro E-mini S&P /MES, Micro Gold /MGC, Micro crude, plus micro Treasuries/FX) are 1/10th notional and qualify for Section 1256 60/40 treatment (see below). At $15–65K, the binding constraints are: universe breadth (you can hold maybe 8–15 micro markets with sane risk per contract, vs 50+ for a real CTA — meaningful diversification loss), roll costs and bid/ask on less-liquid micros, and broker futures approval. On data: the cheapest honest path for 15–20yr continuous futures history is Databento (pay-as-you-go, tick-to-daily) or Norgate Data (subscription, continuous back-adjusted futures popular with retail systematic traders); free alternatives are patchy and rarely properly back-adjusted.

On section 1256: 60% long-term / 40% short-term regardless of holding period → blended top federal rate ~26.8% vs 37% ordinary; micros (MES/MNQ/MGC) qualify; ~$10,200 saved per $100K of gains vs a short-term-taxed equity strategy in the top bracket, plus a 3-year loss carryback.

**Confidence:** High on trend robustness and 1256 treatment; Medium on retail micro-replication fidelity; I found NO credible *live, audited* small-account (<$65K) trend track record — practitioner claims exist but audited retail records do not, which is itself the finding.

**So what:** A diversified micro-futures trend sleeve is a legitimate, tax-advantaged diversifier that the project has not tested, and it directly addresses trend's known equity-only weakness (Q12). But at this account size the diversification is materially truncated and there is no audited retail live proof, so treat any backtest with extra skepticism and size the sleeve small. Cheaper/simpler alternative: a managed-futures ETF (see Q11) or the RSST/RSBT return-stacked funds capture most of the benefit without the operational load — likely the better first step than DIY micros.

### Q7 — The cost of leverage: SSO vs alternatives

**Findings.** For a *trend-gated* 2x equity exposure held weeks-to-months, the candidates differ sharply. SSO (ProShares Ultra S&P 500) is a daily-reset 2x LETF: ~0.90% ER plus embedded financing at short rates, and — critically — daily reset causes volatility decay in choppy/sideways markets (the return path, not just level, matters). The Bogleheads-cited academic point is that over 2006-onward, long-term SSO holders "mostly got screwed" through the two crashes, and ULPIX (a 2x S&P fund Ayres-Nalebuff themselves suggested) never caught up to VFINX after the tech and 2008 crashes. Capital-efficient stacked ETFs are the strong alternative: NTSX (WisdomTree 90/60 stocks/bonds = 1.5x) and RSSB (Return Stacked Global Stocks + Bonds) are Roth-holdable, need no margin, and — per an independent 2025 analysis (mdickens.me) — have historically cost *less* than their financing benchmark (NTSX excess cost ≈ −0.50% in 2025, i.e., it *beat* levered-benchmark expectations). Their failure mode is tracking/rebalancing drift (rebalance when weights drift 5%, method-sensitive to ~1%/yr) and they cap at 100% equity (no pure 2x equity). Micro futures give cheap financing (embedded in the futures basis, near risk-free) and 1256 tax treatment but require margin management and roll. Portfolio-margin box-spread financing (borrowing via SPX box spreads) is the cheapest marginal financing for large accounts but needs portfolio margin (typically $125K+ and options approval) — out of reach at the low end of this range.

On "Leverage for the Long Run" (Gayed): the strategy uses a 200-day SMA to gate into leveraged equity — exactly the gated-LETF concept here. Known critiques: it is heavily curve-fit to the specific MA and leverage, whipsaws in chop clusters (2015-16, 2018) cause repeated gated losses, and daily-reset decay bites during the very volatile periods where the signal flips most. I found no *audited live-money* gated-LETF track record; implementations are backtests and forum/PortfolioVisualizer runs.

**Confidence:** High on LETF decay and stacked-ETF cost; Medium on Gayed critique specifics; Low on live gated-LETF evidence (essentially none audited).

**So what — this changes Part I's design.** The validated offense variant uses SSO. The evidence says a *trend-gated* hold of weeks-to-months is the regime where daily-reset decay is least harmful (gating avoids the worst chop), so SSO is defensible — but NTSX/RSSB are Roth-holdable, cheaper per unit of financing, and avoid daily-reset decay entirely, at the cost of not reaching a full 2x on equity alone. Recommendation: benchmark the SSO offense variant head-to-head against a gated NTSX/RSSB (or a gated SSO+cash blend sized to match) before committing real money; the leverage vehicle, not the signal, may be where the offense variant's edge is quietly leaking.

### Q8 — Taxable-account design

**Findings.** Asset-location best practice: tax-inefficient, high-turnover, and ordinary-income-generating sleeves belong in the Roth/tax-advantaged account; tax-efficient buy-and-hold equity belongs in taxable (where you also retain loss-harvesting and step-up-at-death optionality). A trend strategy with monthly turnover generates short-term gains, so it strongly prefers the Roth — putting the active trend sleeve in taxable is the expensive mistake. Wash-sale traps are the acute risk for this system: Revenue Ruling 2008-5 established that a repurchase of substantially identical securities in an IRA (including Roth) disallows a loss taken in the taxable account — permanently. So a systematic monthly rebalancer running near-identical ETFs (e.g., SPY in taxable and SPY/an S&P fund in the Roth) can trigger cross-account wash sales that are *permanently* lost (no basis addition in an IRA). Tax-loss-harvesting's realistic net value: robo claims (Wealthfront/Betterment) are high, but independent analysis (Kitces) stresses the benefit is a *deferral* that can be clawed back and is easily degraded by wash sales; realistic net at retail is far below marketing numbers and depends on ongoing contributions/volatility. Direct indexing at small scale ($5–250K): the edge is real only with enough lots to harvest and a high tax bracket; at the low end it is mostly marketing, and it multiplies wash-sale surface area.

**Confidence:** High.

**So what — this changes Part I's design directly.** When the taxable wrapper opens, the monthly-turnover trend sleeves must live in the Roth, and the taxable account should hold the most tax-efficient, lowest-turnover exposure. Most importantly: because the same core ETFs (SPY/AGG/GLD/SSO) will be traded systematically in BOTH accounts, you must implement a cross-account wash-sale guard — either use deliberately non-substantially-identical tickers across accounts (e.g., SPY in one, VOO/IVV in the other) or coordinate the rebalance calendar so a taxable loss-sale is never mirrored by a Roth buy within the 61-day window. This is a concrete new engineering requirement the two-account design introduces.

---

## PART III — STRESS-TESTING OUR CONVICTIONS

### Q9 — Lifecycle/accumulation investing

**Findings.** Ayres-Nalebuff (NBER w14094, 2008; *Diversification Across Time*, 2010 book) argue young investors should lever up to 2:1 to diversify equity exposure across time, claiming (historical, 1871-on) expected retirement wealth ~90% higher than lifecycle funds and ~19% higher than 100% stock, with a 21%-lower standard deviation vs a constant-75%-stock strategy. The theory rests on Samuelson/Merton's rejection of naive time-diversification, so it is contested at the foundation: Samuelson (1969) and Merton (1969) argue horizon does not reduce risk for a CRRA investor, so the "time diversification" framing is disputed. Empirical critiques (Vars, *Vermont Law Review* 2012, "Don't Try This At Home"; the Seeking Alpha "Good in Theory, Bad in Practice" analysis) stress the practical failure modes: margin calls/forced deleveraging at the worst time, the 2:1 borrowing rate assumption breaking down, and behavioral inability to hold levered positions through crashes. I found no study combining lifecycle leverage with *trend gating* — that is a genuine white space (and precisely this project's implicit thesis).

**Confidence:** High on the literature and critiques; the trend-gating combination is untested in the literature.

**So what:** The project's offense variant is effectively a *trend-gated* implementation of Ayres-Nalebuff — which directly addresses the single biggest critique (forced deleveraging / holding through crashes) by going to cash when trend is off. That is a genuinely novel and defensible synthesis, and worth framing explicitly as such. But the Samuelson/Merton objection still applies to the un-gated portions, and sequence-of-returns risk (below) means the leverage should taper as the horizon shortens. Since the investor is ~40 years out, sequence risk is minimal now but the glide-path should pre-commit to de-levering in roughly the final 10–15 years.

### Q10 — The behavior gap and commitment devices

**Findings.** DALBAR's Quantitative Analysis of Investor Behavior reports large gaps — QAIB 2025 found an 848-basis-point (8.48 pp) gap for 2024, with the average equity fund investor earning 16.54% vs the S&P 500's 25.02% (the 2026 QAIB reports the 2025 gap *narrowed* to 72 bps: 17.16% investor vs 17.88% market) — but the methodology is discredited by Kitces, Blanchett, and Pfau: it compares a lump-sum market return to dollar-weighted investor flows, an apples-to-oranges comparison that conflates "didn't have the money yet" with "bad timing." Morningstar's *Mind the Gap* — the careful study — finds a gap of ~1.1 pp for the 10 years to Dec 2023 (fund 7.3% vs investor 6.2%) and 1.2 pp for the 10 years to Dec 31, 2024 (funds ~8.2% vs investor ~7.0%), "equivalent to around 15% of funds' aggregate total return," concentrated in volatile/sector funds where investors trade most. Barber-Odean ("Trading Is Hazardous to Your Wealth," 2000) independently establishes that active individual trading destroys returns. Both DALBAR and Morningstar converge on the fix: automate and simplify; volatility (not fees) drives the gap.

**Confidence:** High.

**So what:** Quantify the system's core value proposition honestly: the "machine won't sell in March 2020" edge is worth ~1–1.5%/yr on average (Morningstar), NOT the DALBAR headline — but it is *larger* for exactly this investor, because (a) volatile/leveraged holdings (SSO) have the widest behavior gaps, and (b) the whole point is to survive drawdowns while fully/over-invested. So the automation edge here plausibly sits above the 1.2% average but should be claimed as "low-single-digits percent per year, larger in high-volatility sleeves," not a headline 8%. This is the strongest evidence-backed justification for the entire project: the drawdown-protection mechanism's real payoff is behavioral (staying invested), and that payoff is measurable and real, just smaller than the marketing literature claims.

### Q11 — Evidence-backed practices this project hasn't tested

**Findings (only genuinely evidenced items):**
- **Return stacking / capital efficiency (NTSX, RSSB, RSST, RSBT, PIMCO PSLDX):** overlaying bonds or managed futures on equity via one ticker. Independent 2025 analysis shows the WisdomTree/Return Stacked funds have historically delivered *lower* all-in cost than levering the benchmark yourself. Roth-holdable, no margin. Strong evidence; directly relevant.
- **Managed-futures / trend allocation as a diversifier:** robust anomaly (Q12), low equity correlation, crisis-alpha profile. Accessible via ETF without micros.
- **Factor tilts that survived replication:** Jensen-Kelly-Pedersen (2023) "Is There a Replication Crisis in Finance?" find finance replicates better than other social sciences; the durable factors (value, momentum, profitability/quality, low-risk) are those with cross-country, post-publication persistence. Free data at jkpfactors.com.
- **TIPS ladders:** credible for liability-matching/decumulation; less relevant to a 40-year accumulator but worth noting for the eventual glide path.
- **Buffered / defined-outcome ETFs:** LIKELY BAD, verified. Per Morningstar Direct (Dec 31, 2025), the defined-outcome/buffer ETF category held ~$78 billion across 420 funds — the largest ETF category by fund count — but costs are high (First Trust, the largest provider at ~$40B/110 funds, charged an average 0.88% fee, the highest of the eight major issuers). Caps are punitive (e.g., an ~8.55% cap for 15% downside protection), and the protection only holds for buyers at the *start* of the outcome period who hold to the end (Innovator's own April 2026 disclosure warns "investors buying after the start of an outcome period may not benefit fully from the buffer"). For a *maximum-terminal-wealth, won't-sell, 40-year* investor, capping upside to buy downside protection is directly counterproductive — the trend system already provides the downside mechanism. Avoid.

**Confidence:** High.

**So what:** Return-stacked funds (RSST = stocks + managed futures; RSBT = bonds + managed futures) are the highest-value untested idea: they add the trend/managed-futures diversifier AND leverage in a single Roth-holdable ticker, addressing Q6, Q7, and Q12 simultaneously with minimal operational load. This is likely a better next experiment than DIY micro futures. Buffered ETFs should be explicitly rejected for this investor profile.

### Q12 — Trend-following's live out-of-sample record

**Findings.** The SG Trend / SG CTA Index (industry benchmark) has visibly struggled since ~2008-09 (arXiv 2607.01550, "Is Trend Still Your Friend?"), which fuels the "trend is dead" narrative. But the careful academic read is more nuanced: Lempérière et al. (2014), Baz et al. (2015), and Baltas-Kosowski (2020) find 3–12-month time-series momentum Sharpes broadly comparable to the pre-2008 era; the *short-term* trend is what decayed (Narayan et al. 2015; microstructure/crowding). Trend famously failed 2011–2013 and in chop clusters (2015–16, 2018) when correlations rose and there was no sustained directional move — and then delivered strongly in 2022. Multi-speed ensembles: the academic literature (arXiv 2310.10500; the 2025 "Deep momentum networks with market trend dynamics") explicitly recommends combining signals across timescales (1/3/6/12-month) to mitigate regime-change whipsaws — which is precisely the project's 2/5/10-month multi-speed design.

**Confidence:** High.

**So what:** The "trend decay" concern is real but is concentrated in short-term trend and in the SG index's equity-heavy, crowded large-CTA composition; the medium-speed (2–12 month) time-series momentum the project uses is the part that has held up. This *supports* the multi-speed ensemble design and the decision to run trend on multiple assets (SPY/AGG/GLD) rather than equities alone. Structural failure mode to respect: monthly-speed trend fails in sustained low-volatility chop clusters (2015–16), and no ensemble fully removes that — it is the price of the crisis-alpha payoff. Diversifying the trend across more assets (via managed-futures ETF/RSST) is the evidenced mitigation.

---

## PART IV — THE DATA LANDSCAPE

### Q13 — Free/cheap PIT-honest data the project likely doesn't know

**Structured inventory (emphasizing the less-obvious):**
- **Open Source Asset Pricing (openassetpricing.com):** ~200+ replicated equity return predictors with signals and portfolio returns; free; `pip install openassetpricing`. PIT-quality documented per signal. Catch: US equity, factor/portfolio level, not raw firm panel.
- **Global Factor Data / JKP (jkpfactors.com):** Jensen-Kelly-Pedersen replicated factors across ~150 countries; free factor returns (CC BY-NC). Firm-level panel needs WRDS (CRSP/Compustat), but pre-computed factor portfolios and stock characteristics are downloadable free. Catch: the deep panel requires WRDS.
- **Open Source Bond Asset Pricing (openbondassetpricing.com):** free corporate-bond factor and daily TRACE-derived panels, credit spreads/duration. Catch: bond-specific; deepest version needs WRDS/TRACE license.
- **Ken French Data Library:** the classic free factor/portfolio source (already likely known).
- **ALFRED (already used):** vintage macro (PIT-honest).
- **Fed regional probability trackers:** Atlanta Fed Market Probability Tracker and Minneapolis Fed Market-Based Probabilities — free downloadable option-implied probability CSVs (useful for the Q3 backfill).
- **ReSolve managed-futures trend replication series:** free daily/monthly SG-Trend-replication returns 2000–2023 (hypothetical, net-of-cost estimates).
- **QuantConnect / LEAN data:** US equities since 1998 with corporate actions, options since 2010, futures since 2009 — PIT-modeled; free tier for research, cloud backtesting. Catch: platform lock-in for the free tier.
- **Options:** CBOE DataShop (pay per slice) and ORATS (samples) for surfaces; free full surfaces remain scarce.

**Confidence:** High.

**So what:** OSAP, JKP, and Open Source Bond Asset Pricing are the highest-value additions — they let the project run honest, survivorship-clean *cross-sectional* replication (and re-confirm the "no free-price alpha" finding on a bias-controlled panel) without paying for CRSP. They also enable a proper factor-replication filter for Q11 tilts. The Fed regional trackers plus raw ZQ futures are the concrete backfill path for Q3.

### Q14 — Anything structurally new in 2025–26?

**Findings.** T+1 settlement (US equities moved to T+1 in May 2024) is now the baseline; for a daily-rebalance retail system it slightly tightens the cash/settlement cycle but is largely benign for cash accounts and helps reduce counterparty risk. PFOF and fractional shares remain the retail execution backdrop; fractional shares (which Alpaca supports) materially help a small account rebalance precisely across SPY/AGG/GLD/SSO. On Alpaca specifically: it is positioned as the leading API-first broker for algorithmic retail (BrokerChooser 2026 "Best broker for algorithmic trading," 4.1/5), commission-free US equities/ETFs/options, fractional shares, $0 minimum; the trade-offs are US-only scope, bank-transfer-only funding, and community/GitHub-based support. Paper-vs-live fill fidelity: Alpaca's own docs state paper trading "simulates the order filling based on the real-time quotes" and explicitly warn "active markets can cause results to vary." Community forum reports document material paper-vs-live *latency* differences (paper fills behaving differently from live), so paper fills are optimistic for anything latency-sensitive. I did not find a systematic regulatory-driven free consolidated-tape change that materially alters the retail data picture in this window (the SEC market-data infrastructure rules remain in slow implementation).

**Confidence:** High on Alpaca positioning and paper-fill caveat; Medium on the microstructure/consolidated-tape status (thinner sourcing).

**So what:** For a daily-rebalance system, Alpaca is fit-for-purpose and fractional shares are a genuine advantage at $5–250K. But do NOT trust paper-trading fills as live-execution proxies for fill *quality or timing* — the project's own paper-trading validation should be treated as optimistic on execution, and a small real-money pilot is the only honest fill test. Build the live system assuming worse fills than paper.

---

## PART V — THE OPEN HORIZON

### Q15 — Autonomous-system operational risk

**Findings.** At this scale the documented failure modes are mundane and silent, not spectacular. A widely cited practitioner field guide ("Production Trading Bots: 15 Failure Patterns," florinelchis/Medium) catalogs real incidents: relative database paths that silently read stale data depending on how cron/systemd invoked the process; a P&L checker with hardcoded month-old prices whose output "format was identical to real-time data"; monitoring that failed silently for 60% of pairs while bots traded normally — "A monitoring tool that fails silently is worse than no monitoring." General guides (Alchemy, Dysnix, BloFin) converge on the same failure taxonomy: runaway execution loops / duplicate orders, stale-data trades, credential/key leaks (keys handled by remote services), and cloud-scheduler failures. Anecdotal bot audits attribute ~60% of failures to execution issues, ~25% to timing/latency, ~15% to model. LLM-agent-specific incidents add prompt injection (Q2). Best practices for a two-person (human + AI) operation: circuit breakers (max-loss thresholds that auto-pause), rate limiters and cooldowns, a hard kill-switch, a dead-man/heartbeat monitor on an *independent* system (patents describe auto-going-offline and cancelling all orders on loss of connectivity), economic-health monitoring (alert on "no successful trade in 72h," error-rate thresholds, positions without matching exit orders), absolute paths / startup validation of every data dependency, local-first credential storage, and a rollback procedure executable in under five minutes.

**Confidence:** High.

**So what:** This is arguably the highest-leverage area for a two-person operation, and the evidence says the danger is *silent wrongness*, not a dramatic blowup. Concrete requirements: (1) an independent dead-man monitor that cancels all orders and halts on heartbeat loss; (2) economic-health alerts (stale-data detection via timestamp freshness checks, "no trade in N days," position/exit reconciliation); (3) a pre-registered kill-switch and <5-minute rollback runbook; (4) the LLM layer strictly privilege-separated from order submission. Because the system is explicitly designed to "never sell in downturns," the kill-switch semantics must be carefully defined — halting must mean "stop *new* automated actions," not "liquidate," or the safety mechanism could itself cause the capitulation the system exists to prevent.

### Q16 — What should we have asked? (MANDATORY blind-spot section)

The brief is unusually thorough, but researching it surfaced five questions it failed to ask. The two most important are answered as far as the evidence allows.

**Blind spot #1 (most important) — Leverage-vehicle risk swamps signal risk in the offense variant, and the SSO path has an un-modeled path-dependency and rebalance-decay cost.** The brief validates the offense variant's *signal* (2x when trend ON) but never stress-tests the *vehicle*. Q7's evidence shows daily-reset LETFs decay in chop and that Roth-holdable stacked ETFs (NTSX/RSSB) have historically cost less than the financing they replace. **Answer:** Before scaling the offense variant, run a pre-registered head-to-head of (a) gated SSO, (b) gated NTSX/RSSB, and (c) gated micro-futures, on the same signal, measuring realized financing cost and chop-decay drag, not just terminal wealth. The offense variant's ~1.2x edge over buy-and-hold SPY may be partly a leverage-vehicle artifact that a cheaper vehicle would widen — or a decay cost a better vehicle would remove.

**Blind spot #2 (answered) — Regime/structural-break risk in the validated core: the backtest is dominated by a 40+ year secular bond bull market that ended in 2022.** The core ensemble trades SPY/AGG/GLD; AGG's trend contribution and the classic 60/40 diversification benefit were flattered by four decades of falling rates. 2022 (stocks and bonds down together) is the regime that breaks trend-on-bonds and the equity/bond hedge simultaneously. **Answer:** The multi-asset trend design partially self-corrects (it can go flat on AGG), but the project should explicitly test the core in the 2022-style joint-drawdown regime and in a sustained-rising-rate path, and should NOT assume the bond sleeve's historical Sharpe persists. This is a first-order threat to a 40-year forward projection and is under-weighted in a backtest anchored to the bond bull market.

**Blind spot #3 — Contribution-timing / dollar-cost-averaging interaction with the trend gate.** The investor contributes ~$7K/yr and will accumulate for 40 years. When the trend gate is OFF (in cash), where do new contributions go, and does parking contributions in cash during "off" regimes create a large cash drag or a market-timing bet on the contribution schedule itself? The brief never addresses how new money interacts with the gate. This deserves a pre-registered rule (e.g., contributions follow the gate vs. always-invest-contributions-then-let-gate-manage).

**Blind spot #4 — Single-broker / single-custodian concentration risk.** The entire system depends on Alpaca for execution, data, and custody. Alpaca is a relatively young broker (SIPC-covered, but with GitHub/community support and a thinner track record than incumbents). A prolonged Alpaca API outage during a trend-flip is an un-hedged operational risk. The brief's operational-risk framing (Q15) is about the *bot*, not the *broker*.

**Blind spot #5 — Tax-drag and the terminal-wealth objective in the taxable account.** Success is defined as maximum terminal wealth vs buy-and-hold SPY, but a monthly-turnover trend strategy in a *taxable* account generates short-term gains that buy-and-hold SPY never incurs. The correct benchmark in taxable is *after-tax* terminal wealth, and the trend system starts with a structural tax handicap there (mitigated only by keeping active sleeves in the Roth — see Q8). The brief's success metric should be after-tax and account-specific.

---

## Ranked Top-10 Most Decision-Relevant Findings

1. **The offense variant's leverage vehicle is under-tested and may be leaking edge.** Roth-holdable NTSX/RSSB have historically cost *less* than the financing they replace, while daily-reset SSO decays in chop; benchmark gated-SSO vs gated-NTSX/RSSB before scaling. (Q7, Q16-#1)
2. **Cross-account wash sales are a permanent, concrete new risk when the taxable wrapper opens** (Rev. Rul. 2008-5): a Roth buy can permanently disallow a taxable loss. Keep monthly-turnover sleeves in the Roth and use non-identical tickers or a coordinated calendar across accounts. (Q8)
3. **LLM contamination makes forward-only evaluation non-negotiable, and RLHF makes frontier LLMs overconfident and prone to hedge toward 0.5** (GPT-4 ECE 0.007→0.074 post-RLHF; Halawi "rarely outputs low probabilities"). Recalibrate the LLM's probabilities and expect its confident low-probability calls to be its weakest. (Q2)
4. **Kalshi is genuinely well-calibrated on Fed path and beats futures/surveys on a small sample** (Diercks-Katz-Wright, FEDS 2026-010) — validating "information source only" — but no free long-horizon implied-probability archive exists; reconstruct one from free raw ZQ fed funds futures. (Q3)
5. **The honest behavior-gap edge is ~1–1.5%/yr (Morningstar Mind the Gap: 1.2 pp to Dec 2024), not DALBAR's 848 bps** — but it is larger in the volatile/leveraged sleeves this system runs, and it is the strongest evidence-backed justification for the whole project. (Q10)
6. **Silent stale-data/monitoring failure — not a dramatic blowup — is the dominant autonomous-system risk at this scale;** require an independent dead-man switch, economic-health alerts, and a kill-switch that halts new actions without force-liquidating. (Q15, Q16-#5)
7. **The validated core is anchored to a 40-year bond bull market that ended in 2022;** explicitly stress-test the AGG sleeve and the equity/bond hedge in joint-drawdown and rising-rate regimes before trusting a 40-year projection. (Q16-#2)
8. **The offense variant is effectively a trend-gated Ayres-Nalebuff lifecycle-leverage strategy** — a novel, defensible synthesis that neutralizes the literature's main critique (forced deleveraging), but should pre-commit to de-levering in the final ~10–15 years. (Q9)
9. **Return-stacked funds (RSST/RSBT) are the highest-value untested idea**, capturing managed-futures diversification + leverage in one Roth-holdable ticker — likely a better next experiment than DIY micro futures; buffered/defined-outcome ETFs should be rejected for this profile. (Q11, Q6)
10. **The CEF anomaly is still live but its catalyst weakened** (June 2026 SCOTUS *FS Credit v. Saba* ruling narrows activism), and no cheap deep PIT NAV history exists (CEFData starts 2012, weekly pre-2018); a limited 2012-start test is possible but should model a longer reversion half-life. (Q5)

---

### Staged Recommendations

**Now (0–3 months):**
- Keep the news panel and prediction-market feed as information/risk-sizing inputs only; do not build directional stock-picking on sentiment (Q1). *Threshold to revisit:* only if a pre-registered, cost-and-CI-gated test on an OSAP-clean panel shows sentiment surviving — unlikely.
- Implement the operational-safety layer BEFORE scaling capital: independent dead-man monitor, economic-health alerts, stale-data timestamp checks, privilege-separated LLM, <5-min rollback runbook (Q15). This is the highest-leverage work.
- Recalibrate LLM probabilities against its own resolved history and score on Brier vs *multiple* baselines including market-implied; freeze the promotion gate at "beats the crowd/market baseline with a bootstrap CI excluding zero" (Q2, Q4).

**Before the taxable wrapper opens (near-term):**
- Codify the asset-location rule (active/monthly-turnover sleeves → Roth) and build the cross-account wash-sale guard (non-identical tickers or coordinated calendar) (Q8). *This is a blocking requirement, not optional.*
- Redefine "success" as *after-tax, account-specific* terminal wealth vs buy-and-hold SPY (Q16-#5).

**Before scaling the offense variant (medium-term):**
- Run the pre-registered leverage-vehicle bake-off: gated SSO vs gated NTSX/RSSB vs gated micros, measuring realized financing cost and chop decay (Q7, Q16-#1).
- Stress-test the SPY/AGG/GLD core in 2022-style joint-drawdown and rising-rate regimes; do not extrapolate the bond sleeve's historical Sharpe (Q16-#2).
- Pre-register the contribution-vs-gate rule (Q16-#3).
- Evaluate RSST/RSBT as a single-ticker way to add managed-futures diversification + leverage in the Roth (Q11).

**Ongoing benchmarks that would change the plan:**
- If the LLM fails to beat the market-implied baseline over 100+ resolved questions, freeze it at report-only.
- If a real-money pilot shows live fills materially worse than paper, re-derive all cost assumptions (Q14).
- If CEF reversion half-lives lengthen materially post-SCOTUS, keep the CEF idea parked (Q5).

### Caveats
Evidence is genuinely thin or absent — and is flagged as such rather than smoothed — on: Benzinga feed coverage/revision properties (Q1, no independent audit); audited *live-money* retail micro-futures trend records (Q6, none found); live gated-LETF track records (Q7, none audited); and any formal high-frequency prediction-market lead/lag / information-share study vs Treasuries and equities (Q3, essentially non-existent). The Kalshi calibration result (Q3) rests on a small-sample (~12 meetings) working paper with a non-apples-to-apples comparison. The GPT-4 RLHF calibration figure (Q2) is a multiple-choice logprob measure, so its generalization to forecasting calibration is inferential. LLM forecasting-Brier leaderboards are methodologically fragile (winner's curse; overconfidence can top a leaderboard by luck), so treat single-number comparisons cautiously.

---

# DIRECTOR TRIAGE (2026-07-08) — every finding gets a disposition

| # | Finding | Disposition |
|---|---|---|
| 1 | Leverage-vehicle under-tested (SSO decay vs NTSX/RSSB negative-cost stacking) | **DISPATCHED → D/T-294** — pre-registered vehicle bake-off (gated SSO vs gated NTSX/RSSB vs gated micro-futures financing model, same signal) BEFORE real money routes to the offense config |
| 2 | Cross-account wash-sale trap (Rev. Rul. 2008-5, permanent loss disallowance) | **ADOPTED as a BLOCKING requirement** — recorded in the advisor spec amendment; the taxable wrapper cannot open without the guard (non-identical tickers across accounts or a coordinated rebalance calendar). Engineering task when the taxable account is actually opened |
| 3 | LLM RLHF miscalibration → recalibrate probabilities (isotonic/Platt vs own resolved history); expect hedging toward 0.5 | **ADOPTED → folded into E/T-292 + A's harness** (recalibration layer = a stage-1 feature; raw AND recalibrated Brier both reported) |
| 4 | Kalshi well-calibrated on Fed path (FEDS 2026-010); ZQ fed-funds-futures reconstruction = the free backfill | **DISPATCHED → B/T-295** — reconstruct the implied rate-path history from free ZQ/FRED + Atlanta/Minneapolis Fed tracker CSVs; gives A's G1 market-implied baseline HISTORY instead of starting cold |
| 5 | Honest behavior gap ≈ 1.2%/yr (Morningstar), not DALBAR 848bps | **ADOPTED into the goal framing** — the system's automation edge is claimed as "low-single-digits %/yr, larger in volatile/levered sleeves," never the DALBAR number |
| 6 | Silent stale-data failure = the dominant ops risk; kill-switch must halt-new-actions, NEVER liquidate | **ADOPTED** — kill-switch semantics codified (halt ≠ liquidate, else the safety mechanism causes the capitulation the system exists to prevent); econ-health alerts (no-trade-in-N-days, timestamp freshness) queued to E after the fleet |
| 7 | Bond-bull anchoring: stress AGG sleeve in joint-drawdown/rising-rate regimes | **PARTIALLY HELD ALREADY** (2022 is a named must-not-degrade window in the fair harness; the ensemble can go flat AGG) — a dedicated sustained-rising-rate stress arm folded into T-294's named windows |
| 8 | Offense = trend-gated Ayres-Nalebuff (novel synthesis); pre-commit de-lever glide final 10-15yr | **ADOPTED as framing + a future advisor row** — glide-path arm goes to B's accumulation model when the offense config graduates paper |
| 9 | RSST/RSBT return stacking = highest-value untested idea; buffered ETFs REJECTED | **DISPATCHED → C/T-296** — data-reality audit + pre-reg draft (short live history → synthetic replication validated vs real funds, ReSolve SG-trend series). Buffered/defined-outcome ETFs: REJECTED for this profile, on the record |
| 10 | CEF catalyst weakened (SCOTUS 6/2026); CEFData 2012-start weekly-early is the only cheap path | **STAYS PARKED** — the 2012-start test is possible but low-priority vs the above; if ever run, model longer reversion half-life. Shelf #13 updated |
| BS#3 | Contribution-vs-gate rule unpre-registered | **QUEUED → B** (accumulation-model arm: contributions-follow-gate vs always-invest) — folded into B's next accumulation task |
| BS#4 | Single-broker (Alpaca) concentration | **ACCEPTED RISK, recorded** — real money currently sits at Schwab; revisit before real capital routes through Alpaca |
| BS#5 | After-tax, account-specific benchmark in taxable | **ADOPTED** — advisor-spec amendment: the taxable column's bar is AFTER-TAX terminal wealth vs buy-and-hold SPY (T-191 machinery exists) |
| Q1 | News = risk-sizing not directional alpha; Benzinga properties unaudited anywhere | **CONFIRMS the frozen T-289c design** (interaction/sizing only); D's F1-F3 amendments already cover the revision/coverage characterization the literature lacks |
| Q4 | Promotion gates: beat ALL baselines, block-bootstrap CI on the Brier differential, pre-registered question sets | **ADOPTED → G1 second amendment** (CI-on-differential + pre-registered question-set requirement added to the already-amended market-implied-prior gate) |
| Q13 | OSAP / JKP / Open Source Bond Asset Pricing free replication panels | **RECORDED in the data ledger** — candidate future use: re-confirm the no-free-alpha H0 on a bias-controlled cross-sectional panel; no task until a question needs it |
| Q14 | Paper fills are optimistic; only a real-money pilot tests fills honestly | **RECORDED** — strengthens the existing exec-gate framing; the eventual live pilot's cost re-derivation is pre-committed |
