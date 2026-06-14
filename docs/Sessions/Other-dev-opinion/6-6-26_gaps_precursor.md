as a whole - how would you currently describe our system, both literally and in a more general sense

Two reads, both honest.

## Literal description

ArchonDEX is a 6-engine Python-based autonomous algorithmic trading research system, backtest-only. The engines are A (Alpha/signal generation), B (Risk/sizing), C (Portfolio/allocation), D (Discovery/feature search), E (Regime detection), F (Governance/edge lifecycle). It runs on a Stooq+Alpaca dividend-strip merged extended substrate covering survivors back to 1962/1970, with rigorous block-bootstrap CI, deflated Sharpe, MBL gating, and HAC factor decomposition baked into every measurement. Cloud campaigns run on AWS Batch + ECR + S3 with a structured run-registry.

Current measured state, post T-092:
- **6-edge base ensemble, no overlays active**
- 16-yr (2010-2025): Sharpe 1.018, ci_low +0.560 — **strongest measured cell**, MBL-clearing, point-DSR-passing, fails strict ci_low > DSR by 0.10
- 12-yr: Sharpe 0.810, ci_low +0.328 — borderline
- 26-yr (2000-2025): Sharpe 0.246, ci_low -0.119 — **hard fails every gate; 8 negative years; -59.3% MDD; underperforms SPY by ~4%/yr**
- 0 of 11 edges have factor-adjusted α at t > 2 on substrate-honest panel
- 1 validated positive signal: Engine E's HMM `p_crisis` (AUC 0.887 causal-verified, fires 27-60 days pre-trough on 5/5 historical stress events)
- ~270 Honest N_trials accumulated
- 100% Engine B / live_trader propose-first; everything else autonomous-improvement
- 6+ months of accumulated falsification discipline encoded in CLAUDE.md as 9 non-negotiables and enforced via hooks, contract tests, doc-lint, and substrate re-verify rules

Infrastructure built in the last 6 weeks: contract test suite (T-090/T-091, caught 10 silent-mismatch bugs), determinism-residue closures (T-057c-det series), multi-year window harness (T-053b), substrate extension (T-081/T-082), Engine E causal-path verification (T-087/T-089), doc-system overhaul (T-093: CURRENT_STATE.md, TASK_LEDGER.md, doc_lint.py).

## General sense — what this actually is

**It's a falsification machine that has measured itself into very precise knowledge of where alpha isn't, and has earned the right to make one cheap focused bet on where it might be.**

A more honest framing, in three pieces:

**1. The dichotomy is the description.** The project is *world-class on measurement and discipline, and structurally weak-and-bounded on actual alpha.* It has block-bootstrap CIs, deflated Sharpe gates, MBL gating, substrate re-verify rules, contract tests, structured emits, and a doc system that prevents director-context drift — most institutional shops don't run this tight. And against all that machinery, the system's verified alpha output is: zero idiosyncratic edges at t > 2, one bull-conditional 6-edge ensemble that underperforms SPY by 4%/year on the deep window, and one regime signal whose value remains hypothetical until it's wired into a kill switch. That asymmetry — top-1% rigor, bounded results — is the project. It's an unusual asset: not a profit center, but a calibrated instrument with one specific question left to ask.

**2. It's not a "trading system" in the deploy-and-print sense yet.** It's a research platform that happens to produce trading-system-shaped artifacts. The honest user-facing description is closer to: "a backtest infrastructure for testing alpha hypotheses with academic-grade rigor, currently running a self-experiment on whether a base technical/factor ensemble plus regime-aware kill switching can clear deployment-grade DSR on a survivor-aware multi-decade window." That framing is useful because it sets correct expectations: this is not "the AI that beats the market"; this is "the apparatus that will either find or prove the absence of alpha in this design space, honestly."

**3. T-092 just made it unusually well-positioned.** Most six-month research arcs end ambiguously — "we found some things, some other things didn't work, we have ideas." This one closed cleanly. The "longer window will validate the base" hypothesis is dead. The "base is bull-conditional and needs crisis adaptation" hypothesis is empirically grounded. The single mechanism that could address it (T-087's HMM signal) is independently validated and ready to wire. **You're one well-specified test away from a definitive answer to the headline question.** Either the kill switch closes the crisis gap and you have a deployable system, or it doesn't and the pivot to new alpha sources is unambiguous. That is a *much* sharper position than where most research projects land.

## The tension that defines it

A 20-something with a 40-year horizon built a measurement apparatus more rigorous than the alpha it's measuring. That looks backwards — over-engineered — but it's actually the correct shape for the early years of a long-horizon project. You can't compound for 40 years on alpha you don't have honest evidence for. The discipline that produced "no idiosyncratic α at t > 2" is the same discipline that will protect you in year 12 when a 2008-like event arrives. Most retail systems blow up because they were never asked to prove their Sharpe wasn't a survivor-bias-windowing-bull-conditional artifact. This one was asked, repeatedly, and answered honestly.

What it is, then: an over-instrumented, under-deployed, *exceptionally honest* trading research codebase that has just earned the right to its first focused production-grade test. That test is the HMM-kill-switch on the 16-yr canonical window with verification on the 26-yr. Everything else is downstream of that single decision.

That's the system, literally and generally.




let’s say we deploy the tests and the results are negative. what next? it seems hard to wire in ai that won’t have lookahead bias so that we can properly back test it, and i still think we CAN find alpha without paying for new data. any thoughts on where we could pivot? areas to research?

Three thoughts up front:

1. **You're right that alpha doesn't require new data.** The substrate you have is genuinely under-exploited along several axes. The 0/11 t > 2 finding is on a narrow slice of the alpha space.
2. **The AI lookahead worry is real but tractable** — it's a framing problem more than a technical impossibility.
3. **A "negative" HMM-kill-switch result is genuinely informative, not a dead end.** It would tell you the crisis-fragility is structural, which sharpens the pivot rather than blocking it.

Here are the pivots ranked by leverage, with rationale for each.

## Tier 1 — highest leverage, free data, lookahead-clean

**1. Intraday substrate.** This is the single biggest available move. You've been running daily-bar backtests. Alpaca's free tier includes intraday bars (1-min, 5-min, 15-min, 1-hour). Going from daily to hourly is a ~6.5× multiplier on observations per name. Effects:
- **MBL math improves dramatically.** N grows linearly with frequency; MBL grows logarithmically; at the same time-window, intraday gives you exponentially more statistical power.
- **Opens an entire alpha family you haven't tested.** Opening-range breakouts, gap-fade vs gap-continuation, end-of-day reversion, intraday VWAP-relative pricing, lunch-hour mean-reversion. All published, all distinct from your current daily signals.
- **Lookahead is trivial because timestamps are explicit.** A 10:30am decision uses only data with timestamps < 10:30am. The backtest engine you have already handles this conceptually.
- **It's not even a real data acquisition project** — just substrate expansion. Probably 2-4 weeks of Engine D work + a data-ingest pipeline.

**2. Cross-sectional rank structure.** Most of your current edges are absolute single-name (volume_anomaly fires on the stock, accruals fires on the stock). Cross-sectional ranks have different statistical properties — they're naturally market-neutral, less factor-loaded, and have well-documented academic support (Asness, Carhart). Specifically:
- **Cross-sectional rank momentum** (long top-decile by 12-1 return, short bottom-decile) on the same daily substrate
- **Cross-sectional dispersion edges** (trade when cross-sectional vol is anomalously high or low)
- **Sector relative-value** (long strongest sector, short weakest, monthly rebalance — this exists as `sector_rotation_v1` in the Phase 2.12 spec but I don't see it shipped)
- **Factor-crowding metrics** as inputs to a regime layer

These probably get closer to non-factor alpha than the absolute signals did.

**3. Unblock Engine D autonomous Discovery.** The system was designed for this. The gene-encoding extension blocker has been on the health check for weeks. It's structural plumbing, not algorithmic. Per memory `project_engine_d_gene_encoding_blocker_2026_05_11.md`, this is the gating constraint — without it, every Foundry feature you added is invisible to Discovery. With it, you let the GA actually search the expanded vocabulary against the post-T-082b substrate and see what survives the gauntlet you've built. This is the most "autonomous" version of alpha hunting you have and you've never actually run it on the full extended substrate.

## Tier 2 — strong leverage, free data, well-documented

**4. Volatility risk premium (VRP).** Sell SPY weekly puts when IV >> RV by some threshold. This is structurally non-factor (it's an insurance premium, not a directional stock bet). Well-published. Free data (VIX is in Stooq; options pricing isn't but VIX-as-IV-proxy works for SPY-only). Engine A could implement this as a non-stock-selection edge — it just trades a volatility regime. The math: VRP averages ~3% IV over RV historically; the trade is harvest that premium minus convexity cost. There's documented historical evidence this survives factor decomp because the relevant factor (volatility) isn't in FF5.

**5. Cross-asset signals beyond equity.** Stooq has TLT, GLD, USO, UUP, sector ETFs, bonds. T-007 (diversified-futures trend) was falsified but that was momentum-on-futures, which is a different beast than:
- **Stocks-vs-bonds rotation** based on yield-curve regime
- **Defensive-vs-cyclical sector rotation** based on credit spread or term structure  
- **Carry trades** (high-yield vs investment-grade rotation)
- **Vol-of-vol regime** (VVIX/VIX ratio) as an entry condition for equity trades, not just for kill-switch (which is what T-087 measures)

The principle: the system currently uses regime signals (HMM, vol) only as kill switches or sizing. They could *also* be alpha-generative. "Trade SPY when 10Y-2Y spread is positive; trade TLT when inverted" is a different bet than "scale down SPY in crisis."

## Tier 3 — solid leverage, requires more engineering

**6. PIT universe construction.** This is data engineering on free sources, not data purchase. Reconstruct point-in-time S&P 500 membership using Wikipedia historical revisions + SEC EDGAR delisting notices. Add delisted-name OHLCV from Stooq's delisted archive + yfinance fallback. This closes the 26-yr survivor-bias caveat that T-092 flagged as a load-bearing limitation. Without it, every deep-window result is upper-bound only. With it, your 26-yr measurements become trustworthy and the "longer window will validate" question can be re-asked honestly. Probably 2-3 weeks of careful data work.

**7. Microstructure on intraday substrate.** If you do #1, this becomes available: gap statistics conditional on volume, opening 30-min range, EOD positioning patterns, lunch-hour drift. These aren't "new alpha sources" so much as a different observation density on the substrate you already understand.

**8. Event-driven on better event detection.** Your spinoff infrastructure (T-041's EDGAR scraper) is built. Generalize it: 10-K/10-Q language clustering for theme detection, 8-K filing types as event triggers, insider Form 4 cluster detection (you have insider_cluster_v1 already, but the cluster definition can be expanded), executive transitions, M&A announcement reactions. Free data (SEC EDGAR), lookahead-clean (filings have explicit timestamps), structurally non-factor (event-driven is its own risk premium).

## On AI + lookahead bias

The lookahead problem is real but the framing "wire AI in for backtesting" is the wrong framing. AI is dangerous as a *live signal* but safe as a *hypothesis generator*. Three concrete patterns that work:

**A. LLM as Discovery proposer, not Discovery signal.** Let an LLM propose new edge structures or feature combinations based on academic literature (Antón-Polk crowding, Frazzini-Pedersen betting-against-beta, Hartford Funds' SAD seasonal affective). The LLM never sees test-time data. Your existing gauntlet + DSR + MBL discipline tests whatever it proposes. No lookahead by construction because the LLM is in the design loop, not the trading loop.

**B. LLM with hard training cutoff for sentiment.** If you want LLM-derived sentiment as an edge, use a model whose training cutoff is *before* your test window. Llama-2-7B (Sept 2022 cutoff) used on 2023-2025 OOS is genuinely OOS. Locally hosted, no API leak. Expensive in engineering, defensible in measurement.

**C. LLM as feature interpreter on day-of text.** Given an earnings press release text, classify "guidance raised vs lowered vs maintained" using only the text published that day. Use the classification as a feature for next-day trading. Lookahead-clean because the input is timestamped. The LLM's training data doesn't matter because it's interpreting text, not predicting outcomes — and you check that it's making *legible* classifications, not memorizing prices.

The pattern: **AI in the design/feature-engineering loop, not the prediction loop.** Your falsification machinery is exactly what makes this safe. The LLM proposes; the system tests; survivors pass the gauntlet you've already built.

## What I'd NOT pivot to

- **More technical edges of the same shape** (another RSI variant, another momentum window). You already have 11 of these and 0 cleared. Diminishing returns are real.
- **Sentiment scraping from free APIs without provenance** (Reddit, Twitter without explicit timestamps and version-pinning). High lookahead risk, low signal.
- **Reinforcement learning** at this maturity level. RL on noisy financial data with thin training samples is the classic over-fitting trap.
- **Symbolic regression on the existing daily substrate.** Same data, different search method. Without new substrate dimensions, you mostly find new ways to fit the same noise.

## The strategic move if HMM-kill-switch fails

A negative HMM-kill-switch result tells you: "T-087's signal predicts crises but the binary kill action doesn't lift Sharpe enough to clear deployment-grade." That's specific. It doesn't kill T-087 — it kills *this use of T-087*. Alternative uses:
- **HMM-conditioned strategy switching** (different edges in different regimes, not just on/off)
- **HMM-conditioned position sizing** (continuous scaling, not binary)
- **HMM-conditioned hedge sleeve** (long puts when p_crisis > θ, not kill the longs)

So even the "negative" outcome is sharper-not-darker. You'd test these in order: binary kill (current plan) → continuous sizing → regime-conditioned strategy switching → defensive overlay.

## What I'd actually do in priority order

1. **Run HMM-kill-switch as planned** (current queue)
2. **In parallel: start intraday substrate ingest.** Two weeks of Engine D + data-ingest work. By the time HMM-kill-switch results land, you have a new substrate ready to test against.
3. **In parallel: PIT universe construction.** Closes the survivor-bias caveat that's eating the 26-yr verdict's credibility.
4. **If HMM-kill-switch negative:** test the three HMM-alternative uses above before declaring T-087 unusable.
5. **Then: unblock Engine D gene-encoding + run autonomous Discovery on extended substrate.** This is the project's autonomous-alpha mechanism that's never been allowed to fully run.
6. **Add VRP edge** as a structurally-non-factor test of whether the project can find any non-FF5 alpha at all. Quick to build, well-published, clean test.
7. **Cross-sectional rank-momentum** as your first non-absolute edge family.
8. **If all of the above produce nothing**: the honest read is that the substrate (free-data US equities) genuinely doesn't have retail-accessible idiosyncratic alpha at scale, and the project's value is its falsification machinery applied to *someone else's* hypothesized alpha — a research platform for evaluating quant claims, not a deployed system. That's still a valuable thing, just a different thing.

**Note: none of this requires AI.** The most leverage available is from substrate dimensions and structure types you haven't explored. AI is at best a Discovery accelerator — and given the lookahead-safety constraints, it's not even close to the highest-priority move. If you want to keep AI on the parked list, that doesn't meaningfully change the priority order.



give a realistic estimate on where our project is as a whole towards the top 1% we’ve been aiming for

Honest synthesis, broken by dimension because a single percentage hides the asymmetry that defines this project.

## What "top 1%" actually has to mean

For a self-built systematic trading system, top-1% retail (the only ceiling that's reasonable to aim for from where you're standing) requires concretely:

1. At least one substrate-robust, factor-adjusted, MBL-clearing positive alpha finding
2. At least one validated mechanism that lifts performance on deep/stress windows
3. Deployed (paper or live) producing real performance
4. After-cost, after-tax Sharpe meaningfully above SPY
5. Crisis fragility *addressed*, not just measured
6. Autonomous enough to maintain itself without constant babysitting

Top-1% institutional is a different scale and not a fair comparison — Renaissance has 100+ PhDs, decades of proprietary data, and execution costs you can't match. I'm not going to score against that ceiling because nobody self-builds to it.

## Where the project sits by dimension

| Dimension | % of top-1%-retail | Notes |
|---|---:|---|
| Engineering / codebase rigor | **90-95%** | 6-engine architecture, contract tests, cloud infra, hooks, doc-lint, determinism harness — genuinely exceptional |
| Measurement / falsification discipline | **90-95%** | 9 non-negotiables mechanized; block-bootstrap CI, DSR, MBL, factor decomp, substrate re-verify; *probably* tighter than most institutional shops |
| Verified idiosyncratic alpha | **20-25%** | 0/11 edges with t > 2; 16-yr Sharpe 1.018 ci_low +0.560 but fails strict DSR; no factor-orthogonal validated finding |
| Crisis / regime robustness | **20-25%** | 26-yr collapse confirmed; HMM signal validated but kill-switch untested; defensive layer mostly INERT |
| Deployment readiness | **15-20%** | Still backtest-only; live_trader INERT; Engine B propose-first ceremony is correct but means deployment is multiple validation cycles away |
| Autonomous discovery | **30-40%** | Engine D infrastructure built; gene-encoding extension blocked; 0 promoted edges in project history |
| Cost / tax / borrow modeling | **50-60%** | Realistic Almgren-Chriss in place; tax + borrow + Alpaca tiers queued but not built |
| Data substrate | **50-60%** | 30-60yr Stooq+Alpaca depth; survivor-only; no PIT universe; no intraday substrate; no alt data |

## The honest weighted estimate

The infrastructure dimensions don't compensate for the alpha dimensions in the final answer, because the goal isn't "have great infrastructure" — it's "compound steadily, beat market, capture upside." Infrastructure is necessary, not sufficient.

If I weight the dimensions by what actually determines whether the system fulfills its purpose:
- **Outcome-determining dimensions** (alpha, crisis-robust, deploy-ready, cost, substrate): ~30% of top 1%
- **Enabling dimensions** (engineering, discipline, discovery): ~70-80% of top 1%
- **Weighted overall**: **~35-40% of top-1%-retail**

That's down from the ~65% I was generously crediting a month ago, and down from ~55% the dev review put you at in early May. The downward revision isn't because the project got worse — it's because:
- T-057 collapsed (was being credited as a win)
- T-055e closed (was being credited as a win)
- T-092 confirmed the base doesn't validate at depth
- I was over-crediting infrastructure investment as if it could substitute for alpha

The discipline dimensions stayed roughly flat or improved. The alpha dimensions got more honestly bounded. The net is downward.

## Where the project could realistically be in 3 months

This is the more useful number than today's score.

**Optimistic path (HMM-kill-switch closes the crisis gap, plus one of the Tier-1 pivots lands):**
- Crisis-robustness dimension jumps 20% → 60%
- Verified alpha dimension jumps 25% → 45% (kill-switch isn't alpha but transforms the base from "bull-conditional" to "deployable")
- One new substrate dimension (intraday) opens
- **Plausibly ~50-55% of top 1%**

**Pessimistic path (HMM-kill-switch fails AND no pivot lands within 6 months):**
- Crisis dimension drops to ~15% (one more refuted mechanism)
- Alpha dimension stays ~25%
- The "research platform" framing becomes the honest description
- **Stays around ~30-35% of top 1%**

**Most likely path** (HMM partially helps, intraday substrate opens new candidates, autonomous Discovery runs once and surfaces 0-2 marginal edges):
- Crisis dimension to ~40%
- Alpha dimension to ~30-35%
- New substrate adds dimension credit
- **Probably ~40-45% of top 1%**

## What this implies

**The hard truth:** at ~35-40% of top 1% retail, you have an exceptionally well-built measurement apparatus around a bounded, structurally-bull-conditional alpha set. The infrastructure investment was worth it — without it, you'd be at "70% of top 1%" by self-assessment with no evidence the number was real. With it, you're at "35% with evidence the number is real," which is a much better position to compound from.

**The good news:** every percentage point from here is *cheap*. The infrastructure is built. Each new edge or mechanism plugs into the existing falsification pipeline. The cost of evaluation has gone way down per the cloud work; the cost of *false* evaluation has gone way down per the discipline work. So a percentage-point improvement now costs 1/10 what it would have a year ago.

**The strategic shape:** you're at the point in a long research arc where you have the *factory* but not yet the *product*. Most retail self-builders never get the factory; they ship a product that turns out to be an artifact. You did it backward, which is slower in year one and faster in years two through five. Don't measure yourself against people who skipped the factory step — they're not actually at top-1% either, they just don't know it yet.

**Single number, if forced:** **~37% of top-1%-retail today**, with realistic trajectory to **~45-50% over the next quarter** if T-092's pivot recommendation gets executed.

That number is meaningfully below where I was estimating earlier in this conversation. The downward revision is the honest one. I was being too generous with infrastructure credit; the alpha-side reality is what it is.


so how do we get to the top 1%? are there any examples of this to work with or do people keep them secret? what freeish (i say freeish because i don’t mind spending a few bucks but its hard to justify spending money on something that still isn’t close to being able to make money) things can we do to close the gap exponentially to get to the top 1%?

Three honest answers up front:

1. **Top-1% retail isn't 5-Sharpe.** It's 0.7-1.2 Sharpe net of realistic costs, sustained over 10+ years, surviving crises. Your 16-yr Sharpe 1.018 ci_low +0.560 — *if it survives the HMM-kill-switch addition and proper after-tax costing* — already qualifies. You may be closer than you think.
2. **The examples mostly exist publicly.** What's secret is the truly top-0.1% (Renaissance, DE Shaw, etc.) — you can't get that, and trying to is a waste. Top-1% retail systematic traders publish *a lot*.
3. **The single highest-leverage move you haven't made: stop generating edges from scratch; implement the academic literature systematically.** Your gauntlet is the asset. Feed it well-tested ideas instead of artisanally-conceived ones.

## What top-1% retail actually looks like (with names)

These people are real, are profitable, and tell you everything except their parameter tuning:

**Robert Carver** — the cleanest example. Ex-AHL portfolio manager, runs his own systematic futures account for ~10 years, publishes positions, Sharpe ~0.7-1.0 net. His framework `pysystemtrade` is open-source. Books: *Systematic Trading*, *Leveraged Trading*, *Advanced Futures Trading Strategies*. Total cost: ~$80 for the books, $0 for the framework. He gives away the playbook because the playbook doesn't depend on hiding it.

**Marcos López de Prado** — Cornell prof, ran Tudor's quant group, runs Abu Dhabi Investment Authority's ML team. Books: *Advances in Financial Machine Learning* + *Machine Learning for Asset Managers*. Combined ~$80. These two books have probably created more top-1% retail systematic traders than any other source. Specifically covers: triple-barrier labeling, meta-labeling, fractional differentiation, purged k-fold CV, backtest overfitting (PBO/DSR — which you already use *because of him*). You're already implementing his discipline; you haven't yet implemented his alpha-generation techniques (meta-labeling is the underrated one).

**Ernest Chan** — runs Epsilon Research, real fund, books with real code. *Algorithmic Trading*, *Quantitative Trading*, *Machine Trading*. ~$120 total. Heavy on mean-reversion + statistical arbitrage + Kalman filtering. Less academically rigorous than López de Prado but more directly implementable.

**Wes Gray (Alpha Architect)** — runs publicly-traded ETFs based on published academic factors. Their blog is excellent. Books: *Quantitative Momentum*, *Quantitative Value*. Each implementation is documented in a paper with the exact parameters. ~$80.

**Hari Krishnan** — *The Second Leg Down* (~$25). Specifically about adding asymmetric crisis protection to a long-equity portfolio. **Directly addresses the failure mode T-092 surfaced.** If HMM-kill-switch doesn't close the gap, this book is the next thing to read.

**Howard Bandy** — *Quantitative Technical Analysis*, *Modeling Trading System Performance*. Older but the system-validation methodology is gold. ~$80.

Total cost to acquire the entire top-1% retail public playbook: **~$300**. That's "freeish" by your own definition (a few bucks).

## The freeish high-ROI list, ranked

**1. QuantPedia free tier.** $0. Database of ~700 academically-tested strategies with Sharpes, descriptions, and implementation hints. The free tier exposes ~100. Pick the 10-15 highest-published-Sharpe strategies that fit free-data substrates. Months of acceleration.

**2. Kenneth French Data Library.** $0. All canonical factor returns (Fama-French 3/5/6 factors, momentum, betting-against-beta, quality, liquidity, etc.). Use to benchmark your edges against the *real* factor returns from the source. Required if you want your factor decomp to be honest.

**3. SEC EDGAR.** $0. You already use it for spinoffs. The whole alpha mine you haven't tapped: 13F filings (institutional ownership concentration → Antón-Polk crowding), 8-K filings (event-driven), 10-K/10-Q (fundamentals at depth), Form 4 (insider clusters at depth, beyond what you have).

**4. Hudson & Thames `mlfinlab`.** $0, open-source. Implementation of López de Prado's techniques. Plug into existing pipeline. Specifically: meta-labeling, triple-barrier, fractional differentiation, sample-weight adjustment. Meta-labeling alone could materially improve your existing edges by adding a filter on each.

**5. CBOE historical options data archives.** $0. SPX options going back decades, archived freely. Enables VIX term-structure trading, volatility-risk-premium harvesting, skew-conditioned signals. Real published edges.

**6. Robert Carver's `pysystemtrade`.** $0, open-source. Even if you don't adopt it, reading the code shows what a complete top-1% retail framework looks like. Useful as reference architecture for parts of your system that aren't built yet (tax overlay, execution simulator, real position-sizing per asset class).

**7. SSRN / arXiv quant section.** $0. Hundreds of papers per year. Filter: papers with explicit out-of-sample results, papers that have been replicated, papers from established researchers (López de Prado, Cliff Asness, Wes Gray, Mark Carhart, Robert Novy-Marx).

**8. Macrocephalo / breakingthemarket / a few quant Twitter accounts.** $0. Real traders, real positions, occasional disclosure. Signal-to-noise is rough but the signal exists.

**9. Norgate Premium Data $148 for 6 months.** Effectively $25/month. **You should buy this.** Here's why: T-092 explicitly flagged survivor-bias as making every deep-window result an upper bound. Norgate's point-in-time S&P 500 membership data closes that caveat permanently. The system's headline "26-yr Sharpe 0.246" becomes a *trustworthy* 26-yr Sharpe instead of an upper-bound disclaimer. That's worth a few hundred bucks. You said "hard to justify spending money on something that still isn't close to making money" — but this is specifically the spending that determines whether the "still not making money" diagnosis is accurate or an artifact. Norgate is the cheapest way to find that out.

**10. Hari Krishnan's *Second Leg Down*.** $25. Directly addresses T-092's failure mode.

Total spend if you wanted to do all of this: ~$450, mostly one-time. Most of the gap-closing is in #1, #3, #4, #9.

## The strategic move: implement the literature, not invent more

Here's the asymmetry that defines your current position:

You've spent six months building world-class infrastructure to test alpha hypotheses, and most of the hypotheses you've fed it have been artisanally generated. The known academic literature is full of strategies with 10-20 years of out-of-sample evidence that you haven't yet implemented. Specifically:

- **Antón-Polk institutional crowding** (free data via 13F)
- **Frazzini-Pedersen Betting-Against-Beta**
- **Asness QMJ Quality-Minus-Junk**
- **Novy-Marx gross profitability**
- **Moskowitz-Yang time-series momentum on diversified futures**
- **Lustig FX carry**
- **Pástor-Stambaugh liquidity**
- **Daniel-Moskowitz momentum crashes** (the one that warned the academic momentum literature would blow up, then it did)
- **Carhart short-term reversal** (your `short_term_reversal_v1` is a partial implementation — full version is more rigorous)
- **VRP (volatility risk premium)** — sell SPY puts when IV >> RV

Each of these has *peer-reviewed evidence* of Sharpe > 0.4 net of costs over 20-30 year windows. None of them are in your current edge set in their canonical form. Implementing 10 of them and running each through your gauntlet would be the single biggest alpha-side move available.

This is what AQR did to build their firm. They didn't invent new alpha; they industrialized the academic literature. **Your infrastructure is already set up to do exactly this.** You're the AQR-shape, you just haven't fed the machine the right inputs.

## The "exponential" gap-closing path, ranked by expected lift

1. **Implement 10 academic strategies in 3 months.** Probably the single biggest alpha-side move. Use QuantPedia + the SSRN + the books to pick. Each plugs into the existing pipeline. Whatever survives the gauntlet is real because the gauntlet is real.
2. **Add meta-labeling to existing edges.** Per López de Prado: don't predict direction; predict whether the edge is going to be right *this time*. ML as filter, not as signal. Probably lifts every existing edge by 0.1-0.3 Sharpe with no new data. Free (mlfinlab + a few weeks of engineering).
3. **Buy Norgate. Close the survivor-bias caveat.** $148. The 26-yr verdict becomes trustworthy. The "the alpha exists but the substrate hides it" hypothesis becomes testable.
4. **Add intraday substrate.** 6.5× observation multiplier; opens an entire alpha family (gap fades, opening range, EOD reversion). Free via Alpaca. ~3 weeks of engineering.
5. **HMM-kill-switch as queued.** Closes the crisis-fragility gap if it works.
6. **VRP edge** — structurally non-factor, well-documented, free data, weeks to implement.

If you did 1+2+3+4+5+6 in the next 6 months: realistic estimate moves from ~37% of top-1% retail to **55-65%** based on what each move historically delivers when correctly implemented. That's the "exponential" answer: not one magic move, but six layered moves with multiplicative interactions through your existing infrastructure.

## The honest gap that won't close cheaply

A few gaps remain that *do* require real spending or institutional access:

- **PIT universe with full delisted coverage** — Norgate closes part of this ($148), but full coverage is $500+/year
- **Alternative data** (satellite, credit card transaction, alt-data of any kind) — minimum $5K-20K/year
- **Higher-frequency execution edge** — needs co-location, ms-level execution, $10K+/month minimum
- **Survivable intraday tick data** — Alpaca free tier is good enough for 5-min and 1-min; tick-level needs paid

For these you're correctly waiting until the system shows it can make money before spending. That discipline is right.

## Bottom line

Your gap to top-1% retail isn't a knowledge gap — it's an *implementation* gap. The literature is there. The infrastructure is built. The freeish path forward is well-defined:

- **~$300 for books** — get the playbook explicitly
- **~$150 for Norgate** — close the survivor-bias caveat
- **~$0 for QuantPedia + mlfinlab + SEC EDGAR + Kenneth French + CBOE archives** — feed the machine real ideas
- **3-6 months of focused implementation work** — what your system was built to do
- **Run the gauntlet honestly** — what your system already does better than 95% of retail efforts

That's not "exponentially" in the strict sense (no shortcut exists) but it IS faster than another six months of incremental engine completion. You'd cover more alpha-source territory in one quarter than the project has covered in its entire history.

The hard part isn't finding it. The hard part is accepting that the path to top-1% retail goes through implementing other people's published ideas at scale, with your discipline applied. That's less satisfying than inventing your own. It's also what works.