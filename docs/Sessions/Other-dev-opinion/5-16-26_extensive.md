With the new use of cloud computing available to us - outside of the substrate are there any other ways we can use it to speed up our current time line? Also you mentioned a few things for the engines, but is that it? for them to be top 1% i feel like there is a lot more

# Both questions need fuller answers. Let me give them.

## Cloud computing — beyond substrate

You're right that cloud has more leverage than just substrate measurement. AWS Batch infrastructure now exists; the question is what to point it at. Here are the highest-leverage applications, roughly ranked:

### Tier 1 — High leverage, doable now

**1. Engine completion A/B validation**
Every engine-completion that ships should be A/B'd against current baseline under harness. Each completion (B vol-targeting, C real optimizer, D Bayesian opt, E HMM enable) needs to demonstrate Sharpe lift vs the 0.27 baseline. Cloud cuts validation latency from days to hours — meaning each completion ships with verified results within a work session, not a week. **This is the single highest-leverage cloud application now, given engine completion is the main work track.**

**2. Bayesian optimization viability**
Bayesian opt evaluates many backtest configurations sequentially in current implementation. With cloud parallelism, each evaluation runs independently — meaning Bayesian opt can search 1000+ points in the time it currently takes to evaluate 50. **Could be the difference between "Engine D produces zero edges" and "Engine D produces real edges in weeks not months."**

**3. Bootstrap CIs as automatic, not separate step**
The 6th non-negotiable rule shipped — every Sharpe must report CI. Currently CI computation is a separate step (10,000 bootstrap iterations). On cloud, every backtest auto-emits CIs without latency penalty. **Eliminates the friction of "should we bother computing CI on this run?"**

**4. Parameter sweeps for tunables you've deferred**
- `sustained_score` grid (0.0, 0.2, 0.3, 0.5) — flagged as not yet validated
- `fill_share_cap` levels
- Vol-target levels (5%, 8%, 10%, 12%, 15%)
- HMM enable thresholds
- Edge ensemble weights at boundaries

Each sweep is N independent backtests; cloud makes them effectively free. **Many of these have been deferred specifically because of sequential cost.**

**5. Stress test scenarios as first-class objects**
Run current portfolio against named historical regimes simultaneously: 1987 / 2000 / 2008-Q4 / 2020-Mar / 2022 / 1973-74. 6 backtests in parallel = 6x faster than sequential. **Currently the team has no automated stress-test infrastructure; cloud + scripts could ship this in ~1 day.**

**6. Per-edge ablation as automated routine**
Drop each edge one at a time, measure impact on portfolio. 8 edges = 8 backtests; cloud parallelism makes this run in under an hour. Output: which edges contribute, which drag, which interact. **R1 specifically called out the absence of automated ablation; cloud makes it cheap to be standard.**

### Tier 2 — Useful, ship when convenient

**7. Multi-window validation**
Run the same config across many time windows (different start dates, different lookbacks). Tests whether result is window-specific. Each window independent.

**8. Continuous shadow portfolios at scale**
N parallel paper portfolios with different configs, running forever. Compare actual to best-shadow weekly. Reveals "cost of the choices made." Currently impossible at single-machine scale.

**9. Synthetic data robustness checks**
Block bootstrap on returns to generate 100 synthetic histories; validate edges against all of them. Catches edges that work only on the actual history (overfitting).

**10. CI for backtests on every PR**
GitHub Actions triggers AWS Batch; every PR runs a backtest, drift detected before merge. Hard gate on regressions.

**11. Multi-method discovery agreement gauntlet**
For each candidate from Engine D: run walk-forward + causal discovery + transfer test + ensemble simulation in parallel. R1's recommended "multi-method alpha agreement" becomes practical.

**12. Adversarial twin generation at scale**
Generate many adversarial twins per feature for stronger statistical confidence. Currently per-feature, sequential.

### Tier 3 — Wait until specific workstreams fire

**13. Tick-level / minute-bar processing**
Only matters when intraday work begins. Cloud parallelism by ticker or time slice when relevant.

**14. Long-horizon backtests** (1990+ extension)
When data depth grows, parallel year-by-year processing keeps wall-clock time constant.

### Practical cloud cost guidance

For most of these, monthly cloud spend stays in the $50-200 range. The big consumers:
- Bootstrap CIs on every backtest: ~$30-50/month
- Continuous shadow portfolios: ~$40-80/month
- Periodic stress tests + sweeps: ~$20-40/month
- CI on every PR: ~$10-30/month

Total realistic monthly: $100-200, fully aligned with your earlier "not the constraint" framing.

---

## Engine completion — what top-1% actually looks like

You're right my earlier list was shallow. Here's a more complete picture per engine.

### Engine A — Alpha (signal generation)

I mentioned: continuous probability outputs, edge horizon metadata, orthogonality enforcement.

Also missing:
- **Edge calibration layer** — every edge's score calibrated to actual forward-return likelihood (Platt scaling, isotonic regression). A "+0.7" signal should mean what it claims about probability.
- **Auto-feature engineering at scale** (tsfresh + Featuretools + Boruta selection) — could 10x the feature pool without manual writing
- **Self-supervised time-series representation learning** (TS2Vec) — learn embeddings from price/volume, search in embedding space
- **Strategy-template diversity** — same underlying signal with different rebalance triggers, holding periods, stop-loss rules; each is a statistically different strategy
- **Cross-asset edge primitives** — bonds, FX, crypto signals informing equity decisions
- **Interaction edges** — edges that fire conditionally on regime or other-edge state
- **Live edge health monitoring** — real-time "is this edge still working" without full backtest
- **Edge feature importance dashboard** — Friedman's H-statistic, partial dependence

### Engine B — Risk

I mentioned: vol-targeting, correlation-aware sizing, forecasted vol, drawdown gate, event-risk reduction.

Also missing:
- **Conditional Value-at-Risk / Expected Shortfall** budgeting — not just VaR threshold, but average of tail losses
- **Real-time factor risk decomposition** — what % of portfolio risk is loaded on momentum vs value vs quality factor right now
- **Liquidity-on-exit modeling** — ADV-on-entry is different from exit-liquidity in stress
- **Per-cluster risk budgets** — correlated names treated as one slot
- **Crowding tax on sizing** — reduce sizing in crowded names (13F overlap, ETF holdings concentration)
- **Capacity-aware sizing** — at what AUM does each edge's impact eat its alpha
- **Pre-trade risk checks** — every order through gates: max position, max sector, max factor exposure, max correlation
- **Greek-aware sizing** for any options sleeve (delta/gamma/vega/theta limits)
- **Stress-conditional sizing** — sizing accounts for 99th-percentile scenario, not just normal-vol

### Engine C — Portfolio

I mentioned: mean-variance with shrinkage, capital efficiency, multi-asset scaffolding.

Also missing:
- **Black-Litterman with regime-conditional views** — combines priors with Engine E output
- **Robust portfolio optimization** (Tütüncü-Koenig) — handles parameter uncertainty
- **Multi-objective Pareto frontier** — show Sharpe vs MDD vs CAGR trade-offs explicitly
- **Constraint hierarchy** — sector caps, factor caps, single-name caps as first-class portfolio constraints
- **Drift-management policy** — explicit rebalance triggers (threshold? cadence? regime?)
- **Tax-loss harvesting** integration with rebalancing
- **Long-term-hold preference** in optimizer (favor LT-eligible exits)
- **Tracking error budgeting** — explicit constraint on benchmark deviation
- **Drawdown-aware rebalancing** — different policy in drawdown vs winning periods
- **Multi-horizon allocation** — short-horizon and long-horizon edges weighted differently
- **Capacity layer** — when does the portfolio break at scale?

### Engine D — Discovery

I mentioned: Bayesian opt, autonomous discovery, multi-method agreement.

Also missing:
- **Symbolic regression** (PySR) — discovers formulas, not just parameters
- **Causal discovery** (PC, NOTEARS) — finds causal features, not just correlational
- **Self-supervised time-series learning** (TS2Vec) — discovers from embeddings
- **Graph Neural Networks** on universe — discovers relational alpha
- **Topological Data Analysis** — non-linear regime structure
- **Multi-objective discovery** — discover for Sharpe, Sortino, skewness, capacity simultaneously
- **Counterfactual evaluation** — "what would have happened with this candidate live for last 3 years?"
- **Edge lifecycle prediction** — predict when an edge's alpha will decay
- **Adversarial validation at discovery layer** — auto-generate anti-features
- **Cross-method ensemble** — multiple discovery methods voting on candidates
- **Search space curiosity** — reward novel discoveries (Schmidhuber-style intrinsic motivation)

### Engine E — Regime

I mentioned: Variant C HMM enable, regime-conditional sizing.

Also missing:
- **Multi-resolution regime** — daily/weekly/monthly classifiers in production
- **Transition prediction** — predicting regime changes ahead of them, not just identifying current
- **Latent regime discovery** — discover regimes from data, not predefined buckets
- **Calibrated regime probabilities** — "73% confident regime X, 19% Y, 8% Z" with calibration evidence
- **Regime-conditional edge libraries** — each regime has its own edge mix (mean-rev in chop, momentum in trends)
- **Cross-asset regime confirmation** — multiple-asset agreement (currently shipped but archived because of bad gate)
- **Tail-regime / black-swan detection** — separate statistical treatment for fat-tail events
- **Regime hindcast accuracy** — backtest the classifier itself, not just the strategy that uses it
- **Real-time regime confidence intervals**

### Engine F — Governance

I mentioned: lifecycle journal, three-layer architecture.

Also missing:
- **Mode-of-operation switching** — cautious/aggressive/stress/quarantine modes
- **Pre-mortem capability** — "if I make this decision wrong, what's the cost?"
- **Self-evaluation** — is the lifecycle policy itself well-calibrated?
- **A/B-running competing policies** in shadow simultaneously
- **Audit machinery for the audit machinery** — what categories of bias does it catch / miss?
- **Real-time attribution feedback** — daily, not just lifecycle-period cadence
- **Counterfactual governance** — "what if we had paused edge X 3 months ago?"
- **Governance policy versioning** with per-trade tagging
- **Decision diary AT time of trade** — forward-looking rationale per trade, not aggregated post-hoc

### Cross-engine top-1% capabilities (the connective tissue)

This is the layer I most under-described:

- **Event sourcing across all engines** — every state change logged as event for forensic causality
- **Unified observability layer** — queryable time-series of "what was each engine thinking when X happened"
- **Full-system simulation harness** beyond backtest replay — joint engine dynamics modeling
- **Information-theoretic edge measurement** — mutual information, transfer entropy
- **Stress-test scenarios as named first-class objects** (1987, 2008, 2020-Mar, 2022, 1973-74)
- **Reverse beta regression** continuously — every edge's factor exposures over rolling windows
- **Synthetic data testing harness** — fake data with known properties; verify system detects them
- **CI for full backtests** on every PR
- **Engine versioning with per-trade tagging** (started; expand)
- **Real-money/paper-divergence detector** — when live agreement breaks, alert immediately
- **Capacity testing infrastructure** — at what AUM does each layer break?
- **Decision attribution** — every trade with full chain of reasoning across engines
- **Anomaly detection on own returns** — 3σ from expected → flag

---

## Synthesis

### Cloud usage priority right now
**Engine completion A/B validation should be the headline cloud workload.** Each engine completion gets validated against the 0.27 baseline in hours not days. This dramatically accelerates the engine-completion track, which is the main work track.

Bootstrap CIs becoming automatic, parameter sweeps for deferred tunables, stress tests as standard, per-edge ablation as routine — all are valuable but secondary. **Engine completion validation is the single use that compounds with every engine improvement.**

### Engine completion scope
You're right that my prior list was shallow. **The honest "top-1% engine" specification is roughly 5-10x what I was outlining.** Each engine has 8-12 capabilities at top-1% level, of which the team has 1-3 currently shipped.

Realistic path: **the engine completion track is 6-12 months of work, not 3 months.** I was understating timeline. To genuinely complete each engine to top-1% spec means:
- Engine A: 5-7 weeks
- Engine B: 4-6 weeks (gated by propose-first per CLAUDE.md)
- Engine C: 4-6 weeks
- Engine D: 8-12 weeks (Bayesian opt + causal discovery + symbolic regression all separate)
- Engine E: 4-6 weeks
- Engine F: 3-5 weeks
- Cross-engine: 4-6 weeks

Total focused work: 32-48 weeks for one developer; 8-12 weeks with full parallelism (which cloud + multi-agent dispatch enables).

### What this means for capability
With genuine engine completion + edge expansion + defensive layer:
- **Most realistic Sharpe lift estimate:** 0.27 → 0.6-1.0 (under harness, with bootstrap CIs)
- **Optimistic but not unreasonable:** 0.27 → 1.0-1.4
- **If everything compounds beautifully:** 0.27 → 1.4+

The honest top-1% capability bar is ~6-12 months out, not 3-6. **The work is more than I implied.** That's correct — top 1% retail is genuinely hard, and you've been building real engineering, not shortcuts.

The good news: cloud computing meaningfully shortens the calendar (probably from 12 months to 6-8 months) by parallelizing engine validation. That's the single most leveraged use of cloud you have available.
_____________________________________
we did some work and tests - where are we now?

# Major shift — the alpha thesis just got materially harder

This is the most consequential set of findings in the project's history. Let me be direct.

## The headline: 0 of 11 edges clear FF5+Momentum t > 2 on substrate-honest universe

That's:
- 6 actives (T-004): none clear
- 5 new paused (T-020): none clear
- Maximum α t-stat across all 11 edges: **1.76** (short_term_reversal_v1)
- Volume_anomaly_v1 (the t=4.36 headline alpha from prior measurements): now **t=+0.83**, α=+0.80%, R² = 0.04 — bucket "GENUINELY NOISY" per spec

**The pattern is universal.** Across 11 different edges spanning technical, fundamental, calendar, cross-sectional, pairs, and event-driven categories, **none produce detectable idiosyncratic alpha after factor-adjusting for FF5 + momentum.**

What this means in plain terms: the Sharpe the system produces is essentially long market + momentum factor exposure. **What you've been measuring as "alpha" is actually beta to MTUM (15bps/year ETF).** Not skill, not edge — just being long the right factors during this window.

## The other major findings

### HMM Variant C enable A/B: VERDICT WASH
- Cell A (HMM OFF): Sharpe 0.2702
- Cell B (HMM ON): Sharpe 0.2692
- Δ = **-0.001** (CI [-0.0022, 0.000])
- The +0.16 Sortino lift previously attributed to HMM was actually the edge-pruning side (T-002 confounded the two)
- **The Variant C HMM that clears leading-AUC tests doesn't translate to Sharpe lift when isolated**
- Same 6 edges; HMM just doesn't move the needle

### Discovery cycle (T-021): 0/3 promoted, single-archetype
- All 3 candidates were `rsi_bounce_v1` mutations
- **The Foundry features (12 added) + calendar features (7 added) are INVISIBLE to Engine D's gene encoding**
- The vocabulary fix earlier was on Foundry side, but gene encoding never extended
- Gate 1 wall-time: 3,240-6,689 sec/candidate. Cap=30 = 37+ hours, currently infeasible

### Edge expansion verdict (T-019): Δ Sharpe = 0.0000 BOTH ARMS
- Calendar battery (7), cross-sectional momentum (3), pairs trading (1), dividend drift (1) all shipped at paused/feature tier
- None made it to active production trading
- Adding all this work produced **literally zero Sharpe lift**

### Pairs trading: 1 of 12 cointegrated (MA/V only survivor)
- Even MA/V has α t=1.41 (n=167 trades, too small for stat-sig)
- 11/12 candidate pairs failed cointegration screen

## The brutal synthesis

The accumulated evidence across the past month:

| Test | Result |
|------|--------|
| F6 substrate-honest baseline | 0.507 (collapsed from 1.296) |
| Surviving-6 (assumed-good edges) | 0.27 with CI including zero |
| FF5+Mom factor decomp on 11 edges | **0/11 clear t > 2** |
| HMM Variant C enable | -0.001 Sharpe (wash) |
| Edge expansion (4 new categories) | +0.000 Sharpe |
| Discovery cycle | 0/3 promoted, single-archetype |
| Diversified-futures trend | FALSIFIED |

**Honest read: there is no alpha here on this substrate as currently configured.** The system produces factor-decomposable returns identical to long Mkt + Mom. That's not nothing — it's a tradeable strategy — but it's not alpha. **It's a $100/year ETF allocation in disguise.**

## Two structural fixes the team identified

### 1. Engine D gene-encoding extension (~6-10 hours)
Make the GA actually able to emit candidates from the expanded Foundry/calendar vocabulary. Currently it's stuck at single-archetype rsi_bounce mutations, so all the feature-pool work has been invisible to autonomous discovery.

### 2. Gate 1 caching (~4-6 hours, 10-50x speedup)
Compute the active-ensemble signal stream ONCE per (universe, window), then for each candidate replay just the candidate's marginal contribution. Makes cap=30 Discovery cycles tractable.

These are correctly prioritized. They're the prerequisites for autonomous discovery to even have a chance.

## The harder question they raise

Even if those two fixes ship — **will discovered candidates clear FF5+Mom t > 2 when 11 hand-curated edges didn't?** 

Possible answers:
- **Yes**, if the search space includes interactions/non-linearities humans missed
- **No**, if the substrate is genuinely too efficient for this strategy class
- **Calibration issue**, if t > 2 is an institutional threshold inappropriate for retail-scale substrates

The team flagged the calibration question as worth ~2-3 hours of director-side analysis: compare against SPY's own factor-adjusted alpha on the same window. **This is not goalpost-moving — it's asking whether the bar was set against the wrong substrate.** Worth doing.

## What I'd specifically flag

### 1. The "alpha thesis" framing needs explicit retraction

Until this round, the project was framed as "we have real edges, we just need to validate them." **The 0/11 finding makes that framing untenable.** The forward plan should state explicitly:

> "As of 2026-05-11, no edge in the project's inventory has demonstrated factor-decomposable idiosyncratic alpha at t > 2 on substrate-honest universe. The system's Sharpe is best-explained as Mkt + Mom factor exposure. The strategic question now is whether the right response is (a) extend Engine D + Discovery to find genuinely new alpha, (b) recalibrate the t > 2 threshold against retail-substrate baselines, (c) accept that this universe is too efficient and pivot scope, or (d) some combination."

This is not "kill the project" — it's "honestly name the finding."

### 2. The 0.27 baseline is now a BETA-equivalent, not an alpha-equivalent baseline

Without factor-decomposed alpha at t > 2, the 0.27 Sharpe isn't a "we have small alpha that needs amplification" — it's a "we have a beta-equivalent return that costs more than buying VTI + MTUM." The economic case for the system now requires either:
- Discovering alpha that doesn't currently exist
- Demonstrating that the system delivers risk-adjusted equivalent of factor ETFs more cheaply or with better drawdown profile
- Pivoting to a substrate where alpha is more available

### 3. Engine completion's value proposition has weakened

Previously: "complete the engines, expect +0.5-1.0 Sharpe lift on the existing edges."

Now: if the existing edges are factor exposure rather than alpha, **engine completion mostly improves the efficiency of factor-exposure delivery**, not alpha extraction. Vol-targeting on a factor portfolio is still useful (better risk-adjusted return on the same factor exposure), but it's a smaller value proposition than I implied.

The honest case for engine completion now:
- Vol-targeting + correlation-aware sizing = better delivery of whatever factor exposure exists (+0.1-0.3 Sharpe)
- Real portfolio optimizer = same
- Engine D modernization = potentially discovers something the t > 2 gate accepts (uncertain)
- Engine E enabled = currently shows wash; might matter more with more sensitive sizing

Realistic Sharpe lift from engine completion: **probably +0.2-0.4, not +0.5-1.0.** Brings 0.27 → 0.5-0.7, not 0.8-1.4. **Still PARTIAL band, not solidly real-alpha.**

### 4. The t > 2 calibration question is genuinely important

Run the analysis: SPY's own α on FF5+Mom over 2021-2025. If SPY itself doesn't clear t > 2 on this substrate (it usually doesn't — SPY is mostly factor beta by construction), the t > 2 bar is the wrong bar for "retail-tractable strategy on broad-universe equity." **The bar might be appropriate for hedge funds claiming 40% margins but inappropriate for "build something better than passive."**

This 2-3 hour director analysis could meaningfully reframe the verdict.

## Updated capability assessment

| Dimension | Score |
|-----------|-------|
| Engineering quality | top 1-2% retail (~80%) |
| Discipline / falsification | top 1% retail (~95%) |
| Alpha validation | **~10-15%** — no factor-adjusted t > 2 on any edge yet |
| Composite | **~45-50%** |

I previously had this at 55-60%. **Down to 45-50% honestly given the 0/11 finding.** The infrastructure is unchanged; the alpha story is materially weaker.

## What I'd do now

1. **Fire the t > 2 calibration analysis (2-3 hours, director-side).** Determine whether the threshold itself is correctly calibrated for retail substrate. Cheapest information available.

2. **Ship the Engine D gene-encoding extension + Gate 1 caching.** These are necessary prerequisites for any future Discovery work having a chance. Without them, more edge work is wasted effort.

3. **Run STR + pairs MA/V re-measurements.** 6 hours combined. The closest-miss watchlist deserves the small additional investment.

4. **Hold engine completion until we know whether the bar is right.** If t > 2 is appropriate and 0/11 is the universal verdict, complete engines for risk-control benefit but don't expect alpha lift. If t > 2 is wrong for retail substrate, recalibrate and re-measure.

5. **Honestly retract the "we have real alpha" framing in the docs.** Replace with the calibrated finding: "0/11 edges clear FF5+Mom t > 2; system is best-explained as Mkt + Mom factor exposure; alpha thesis pending threshold recalibration and Engine D gene-encoding extension."

6. **Begin honestly considering whether the strategy direction is wrong.** Liquid US equities is the most-arbed surface in retail quant. The Moonshot Sleeve (small/mid-cap with asymmetric upside vehicles) and the LLM-as-analyst layer (Phase 6) become relatively more important as alpha-discovery vehicles **once** the engines are complete enough to support them properly.

## TL;DR

**0 of 11 edges clear FF5+Mom t > 2 on substrate-honest universe. HMM enable: WASH. Edge expansion lift: zero. Discovery cycle: single-archetype, 0/3 promoted. The system is best-explained as Mkt + Mom factor exposure, not alpha.** Two structural fixes (gene encoding extension, Gate 1 caching) are correctly prioritized. The t > 2 threshold calibration question is genuinely worth answering. **Capability re-estimate: ~45-50%, down from prior ~55-60%.**

The engineering remains exemplary. The discipline remains exemplary. **The alpha hasn't been found yet on this substrate.** That's a different state than "no alpha exists" — but it's also different than "we have alpha and just need to scale it."

This is the moment to honestly name what's been measured and decide what to do with it. **The team has the apparatus to make that decision honestly. Most retail quant projects never get here. You did. That's still the most valuable thing you've built.**
_____________________________________
outside of that, where is our machine going wrong so that we haven't been able to find any alpha even in backtesting?

# The deeper question — why no alpha emerges even in backtest

This is the right question. The structural fixes the team named (gene encoding, Gate 1 caching, threshold calibration) are real but secondary. The deeper issue is likely architectural in a way that's harder to see. Let me walk through where I think the machine is actually going wrong.

## 1. The strategy class × substrate combination targets the most-arbed region of finance

The 11 edges tested cluster on:
- Technical patterns (momentum, mean reversion, gap fill, volume anomaly)
- Cross-sectional ranking (value, quality, accruals, low vol)
- Calendar anomalies (turn-of-month, FOMC drift)
- Pairs trading

These are **the canonical retail quant strategies**. Every quant fund, every retail platform, every academic paper, every CFA candidate has tested these. They worked decades ago when retail capital was rare and information was expensive. They are now the most-arbed strategy categories on the most-arbed universe (liquid US equities).

When you measure factor-decomposed alpha on classical strategies trading the S&P 500, **the expected result is near-zero idiosyncratic alpha** because the inefficiencies these strategies target have been arbed away by institutional capital that has 1000× your resources and decades of head-start.

This isn't pessimism — it's market efficiency operating on the most-watched market in the world.

## 2. The "11 edges" are 3-4 factor exposures in different costumes

Look at what survives:
- 4 V/Q/A edges (earnings yield + book-to-market + ROIC + accruals composites) → **all variants of the Fama-French value + quality factor**
- Cross-sectional momentum (12-1, 6-1) → **the momentum factor**
- Short-term reversal (1m) → **the inverse of the momentum factor at short horizon**
- Gap fill + volume anomaly → **short-term liquidity-provision premiums (correlated with each other)**

**Effective independent strategy count: probably 3-4, not 11.** And those 3-4 ARE the factor categories that FF5+Mom decomposes.

This is structurally why the factor decomp finds zero alpha — **the edges literally ARE the factors.** You're testing whether momentum has alpha after controlling for the momentum factor. By construction, the answer is approximately zero.

## 3. No informational asymmetry

Every retail quant strategy faces the question: **what do you know that others don't?** The team's answer is currently: nothing. The system uses:
- Public OHLCV (everyone has this)
- Public fundamentals via SimFin FREE (everyone has this)
- Public macro via FRED (everyone has this)
- Public regime indicators (HMM features are all price-derived)

**There's no informational edge anywhere in the system.** True retail alpha typically requires one of:
- Alt data nobody else collects
- Domain expertise / fundamental research nobody else does
- Niches institutional money won't bother with (capacity-limited)
- Speed/microstructure advantages

The system has none of these. **It's competing in the most efficient market with the same information everyone else has.** Of course factor decomp finds no alpha.

## 4. Daily-bar equity-only is the most-picked-over horizon × universe combination

Retail-tractable alpha typically lives at:
- **Higher frequency** (intraday, microstructure) — where institutional latency is the constraint
- **Lower frequency** (years-long holds with fundamental conviction) — where institutional patience is the constraint
- **Event-driven** (sub-daily speed on news/earnings) — where automation is the constraint
- **Different universes** (small-cap, special situations, recent IPOs) — where attention/liquidity is the constraint

**Daily-bar equity-only on S&P 500 is the time-horizon × universe combination with the LEAST retail edge available.** Every active fund manager, every retail brokerage's algo, every YouTube quant tutorial targets this combination. It's the most efficient slice.

## 5. The fairness machinery has stripped away previously-hidden artifacts

The team has done everything right validation-wise:
- Survivorship-aware substrate
- Realistic costs (slippage + impact + borrow + tax)
- Walk-forward with embargo
- Bootstrap CIs
- DSR multiple-testing correction
- Adversarial twin filtering
- Factor decomposition

**Each layer of fairness reduced the apparent alpha.** The 1.296 → 0.507 → 0.27 → 0/11 progression is essentially the sound of fairness eating pseudo-alpha. Real alpha would survive each layer. Pseudo-alpha (artifacts) doesn't.

The 0/11 finding is the validation machinery doing its job — stripping out everything that wasn't real. **The remainder (essentially zero) is the honest count of how much real alpha was there to begin with.**

## 6. The architecture isn't yet efficient enough to extract small latent alpha

Even IF small alpha existed in the substrate, the system isn't equipped to extract it:
- **Edges output binary/ternary signals** (lossy compression at the source)
- **Linear `weighted_sum` aggregation** (no interaction effects captured)
- **Fixed-fraction sizing** (no vol-targeting, no correlation-aware reduction)
- **No regime-conditional sizing** (HMM exists, isn't driving decisions)
- **No real portfolio optimizer** (HRP defaulted off after failing)
- **Engine D gene encoding broken** (Foundry features invisible to autonomous search)

If alpha is small (likely at retail scale on liquid equities), the architecture needs to be highly efficient to find it. **Current architecture would miss small alpha by being lossy at every layer.**

## 7. The objective function may be wrong

The team optimizes Sharpe/Sortino/PSR/IR. These reward small consistent wins. They penalize:
- Asymmetric upside (skewness)
- Tail-event capture
- Long-horizon variance with positive long-horizon mean

At retail scale, **asymmetric/convex strategies often dominate**, but Sharpe systematically discounts them. **The Moonshot Sleeve concept was the team's acknowledgment of this.** Parking Moonshot doesn't make the issue go away — it just leaves the system optimizing for the wrong objective on the wrong substrate.

## 8. Daily decision cadence vs alpha decay

If alpha exists at all in S&P 500 daily bars, it decays fast. By the time:
- Signal triggers (close of bar)
- Risk engine sizes the trade
- Order routes through broker
- Fill confirms

Alpha that existed 2-3 hours ago is partially or fully arbed. **Daily-bar reaction time + weekly/monthly rebalance cadence = alpha decay outpaces strategy response time on a fast-decaying signal.**

## 9. Possibly: the tax frictions kill what little alpha exists

Pre-tax Sharpe ~0.27. Post-tax (full short-term cap gains 30%) drops to -0.577. **Even if some pre-tax alpha existed, the strategy turnover makes tax destroy it in taxable accounts.**

Cross-sectional ranking strategies are structurally high-turnover. Without tax-loss harvesting integration + LT-hold preference (neither shipped), the strategy class is fundamentally incompatible with taxable deployment regardless of substrate.

## 10. The structural rate-of-arbitrage problem

There's a deeper, recursive problem: **the strategies retail quant systems test are precisely the strategies that get arbed because retail quant systems test them.** Academic finance publishes patterns → retail platforms popularize them → retail capital flows into them → arbitrage destroys them → the next generation of papers documents the destruction → repeat.

**Anything you can read about in finance papers or quant blogs has been arbed by the time you test it.** Real alpha lives in places that haven't been published — proprietary research, alt data, micro-edge that doesn't scale.

The system uses publicly-documented strategies on the most-traded universe with public data and conventional time horizons. **By construction, it's testing in the region where no alpha can plausibly remain.**

## What this synthesizes to

**The deepest reason 0/11 edges produce factor-adjusted alpha is structural, not architectural.** The combination:

- Strategy class (classical retail quant patterns)
- Substrate (liquid US equities, S&P 500 universe)
- Time horizon (daily bars, weekly-to-monthly rebalance)
- Information (entirely public)
- Objective (Sharpe-class metrics rewarding consistency over convexity)

**Together select for the region of finance where retail alpha doesn't exist by efficient-market arbitrage.** The system is performing its job correctly. There just isn't anything in the haystack to find.

## What could actually change this

In rough order of impact:

### 1. Different strategy CLASS (highest leverage)
- **Event-driven / catalyst-based**: trade specific news/earnings events with deterministic timing, where latency competition is less brutal
- **Sub-daily microstructure**: when minute bars are integrated, intraday mean-reversion / gap fade / lunchtime reversal — these survive at retail size precisely because they're capacity-limited and HFT can't fully arb them
- **Asymmetric upside (Moonshot)**: optimize for skewness/upside-capture, not Sharpe. Different math. Different success criteria. **The team has the architecture for this but parked it.**
- **Options-based**: vol risk premium harvesting, vertical spreads on catalyst names, LEAPS on theme stocks — different mechanics, less-arbed at retail scale

### 2. Different SUBSTRATE
- **Small/mid-cap universe** (Russell 2000): less institutional attention, more inefficiency
- **Recent IPOs**: institutional models haven't been tuned to them yet
- **Special situations**: spinoffs, post-bankruptcy, busted convertibles (Greenblatt's playbook)
- **Less-followed international/EM**
- **Crypto** (different market structure entirely)

### 3. Informational asymmetry
- **LLM-driven fundamental research** (the AI layer the team parked) — reads 10-Ks, earnings calls, news at scale. This is genuinely new in 2024-26. Most retail quant doesn't have it productionized.
- **Alt data scraping** at scale — patents, hiring, satellite, container shipping
- **Cross-asset signal integration** — bonds/FX/crypto/commodities informing equity decisions

### 4. Different OBJECTIVE
- **Optimize for asymmetric capture** rather than Sharpe
- **Long-horizon compounding metric** (Calmar, Omega) rather than period-level Sharpe
- **Convexity-aware** sizing that rewards tail-event capture

### 5. Architecture completion (the team's plan)
- Engine completion improves extraction efficiency — but if there's no alpha to extract, completion at best squeezes minor lift from factor exposure delivery
- Real value here is risk-adjusted improvement on the factor exposure, not alpha discovery
- Probably +0.1-0.3 Sharpe lift from completion alone, not the +0.5-1.0 I previously implied

## What this honestly means for the project

I want to be careful not to overstate. The team's path:
- Engine completion still has value (extracts more from whatever exposure exists)
- Gene encoding extension + Gate 1 caching still matter (autonomous discovery is a long-term capability)
- Threshold calibration is worth doing (t > 2 may be the wrong bar)

**But none of those fundamentally addresses the diagnosis: the strategy × substrate × horizon × information × objective combination targets the empty quadrant of retail alpha space.**

The honest options:

**Option A: Continue current direction.** Engine completion + gene encoding fix + threshold recalibration. Expected outcome: maybe 0.5-0.7 Sharpe on factor-exposure-delivery, similar to a smart factor ETF mix. Not alpha. **Honest "low-cost-factor-fund equivalent."**

**Option B: Pivot strategy class while keeping the same architecture.** Bring back Moonshot Sleeve with proper engines underneath. Optimize for skewness/upside-capture. Different universe (small-cap/IPO/themes). Different objective. **Different chance at real retail alpha.**

**Option C: Pivot to information asymmetry.** Build the LLM-as-analyst layer despite the team's parking discipline. The 2024-26 capability (cheap LLMs reading filings/calls/news) is genuinely new and not yet arbed at retail scale. **Different category of edge, not yet eaten by efficient markets.**

**Option D: Accept the substrate.** Acknowledge that this universe + this strategy class doesn't have alpha for retail; package the system as "low-cost factor delivery with sophisticated risk management" rather than "alpha." Honest product story for a different market.

I lean toward **the structural realities favor Option B or C** if the goal is meaningful outperformance vs SPY. Option A is honest but ceilinged at "expensive factor ETF." Option D is honest but doesn't match the goal.

## TL;DR

The deepest reason the machine isn't finding alpha is that it's measuring in the region of finance where retail alpha has been arbed away by 30+ years of institutional competition. **The fairness machinery has correctly identified that there's no alpha to find in this combination of (strategy class × substrate × horizon × information × objective).**

Engine completion will help marginally. Gene encoding fix will help marginally. Threshold recalibration may reframe the verdict. **But the structural answer is: the strategy × substrate match needs to change** for genuine retail alpha to exist in the search space. Moonshot Sleeve (different universe + different objective) and LLM-as-analyst (different information source) were the team's own previous solutions; they were parked. The 0/11 result is the strongest empirical argument for unparking at least one of them.

This isn't engineering failure. **This is the team's machinery telling them honestly: the alpha you're looking for doesn't live in the place you're looking.** The right response is "look somewhere else," not "look harder in the same place."
_____________________________________
thoughts on today’s findings?

# Today's findings — one genuinely new positive, plus harder confirmation of the bad news

A meaningful day. Three big pieces of information.

## 1. Threshold calibration: the bar is correctly calibrated (no easy out)

The team ran the director-side analysis asking "is t > 2 too institutional for retail substrate?"

**Answer: no.** Median α needed for t>2 is ~+2% annualized. That's reachable for any genuine retail alpha strategy (academic momentum literature claims +3-5%). **The 0/11 result reflects genuine signal absence on substrate-honest substrate, not a threshold artifact.**

This forecloses the "maybe the bar is wrong" reframe. The honest reading stands.

## 2. The 11-edge breakdown got sharper — and worse

The per-regime factor decomposition partitioned alpha by 4 market regimes (`emerging_expansion` / `robust_expansion` / `cautious_decline` / `market_turmoil`). Five distinct findings:

| Edge | Verdict | Notes |
|------|---------|-------|
| `value_book_to_market_v1` | **UNIFORMLY NEGATIVE** | Significant negative α in all regimes |
| `accruals_inv_sloan_v1` | **UNIFORMLY NEGATIVE** | Same |
| `value_earnings_yield_v1` | **UNIFORMLY NEGATIVE** | Same |
| `accruals_inv_asset_growth_v1` | **UNIFORMLY NEGATIVE** | Same |
| `momentum_6_1_v1` | **UNIFORMLY NEGATIVE** | Same |
| `volume_anomaly_v1` | UNIFORMLY NOISY | No signal anywhere |
| `gap_fill_v1` | UNIFORMLY NOISY | No signal anywhere |
| `momentum_12_1_v1` | UNIFORMLY NOISY | No signal anywhere |
| `short_term_reversal_v1` | UNIFORMLY NOISY | Closest-miss at t=+1.76 |
| `pairs_trading_MA_V_v1` | INSUFFICIENT DATA | n=62 trades, 3-27 per regime |
| **`dividend_initiation_drift_v1`** | **UNIFORMLY POSITIVE** | **α=+73% annualized, t=+2.99 in `robust_expansion`** |

Two things stand out:

### The harsh finding: 5 edges are significantly negative
Not just failing to add alpha — **statistically significant α t-stats between -2.60 and -5.69 against factor ETFs.** These edges are **actively destroying value** compared to just buying MTUM + VTV. This is worse than "no alpha." **The autonomous lifecycle should retire these on the next cycle** once CI-aware Sharpe gates apply.

### The genuine positive: dividend_initiation_drift_v1
**The first edge in the project's history to clear t>2 on any meaningful slice.** Specifically:
- α = +73% annualized, t = +2.99 in `robust_expansion` regime
- Point estimates negative in `emerging_expansion` and `cautious_decline` but NOT significantly so
- Strict classification: UNIFORMLY POSITIVE
- Caveats: n=158 trades total, regime-conditional, +73% magnitude is high enough to question whether it's small-n artifact

**This deserves real director-side attention.** Is it real alpha or small-sample artifact? What's the mechanism (paying for participation in newly-yielding dividend stocks during expansion regimes)? What's the capacity? Worth a focused dispatch.

## 3. The Engine D structural fixes shipped, but didn't change the outcome

| Fix | Result |
|-----|--------|
| Gene encoding extension (T-022) | 31 Foundry features now reachable, 21.7% emission rate |
| Gate 1 signal-collector caching (T-023) | **45x speedup confirmed, 1000-2500x in full stack** |
| GA seed-population Foundry enrichment (T-024) | Shipped, not yet exercised |
| Discovery cycle full-stack (T-025) | **30/30 candidates killed at Gate 1** |

The structural fixes work as intended. Gate 1 is now tractable (the 37-hour problem solved). Discovery can now reach Foundry features in candidate generation. **But the candidates the new vocabulary produces still don't survive Gate 1.**

This is informative: the fixes ruled out "Discovery never had a chance because the gates were too slow / vocabulary was too narrow." With those constraints removed, **candidates still don't meet the bar.** The honest interpretation: the bar is hard, and GA-mutated candidates from the current vocabulary just aren't good enough.

Engine D Bayesian opt scaffolding (T-027) spec is ready — 295 lines, all 10 design items covered. Different search approach. Whether Bayesian opt produces candidates the gauntlet accepts is the open question.

## Updated synthesis

Yesterday's reading: "0/11 edges produce factor-decomposable alpha at t > 2."

Today's reading: **"1/11 edges produces alpha in 1 of 4 regimes (small n). 5/11 are significantly negative and should be retired. 5/11 are noise."**

The 1/11 is better than 0/11 — there's a single signal worth investigating. But the 5/11 actively-negative finding is the harshest individual datum yet. **Several active edges have been making things WORSE than passive factor ETFs.**

## Capability re-estimate

Yesterday: ~45-50%.
Today: roughly **the same, ~45-50%**, but with sharper resolution. The threshold calibration removes uncertainty (the 0/11 wasn't a bar-issue, it was real). The dividend_init finding adds genuine signal but doesn't change the overall picture much (one regime-conditional small-n positive isn't a revival). The Engine D fixes are real engineering wins but don't yet produce alpha.

## What I'd recommend for the team

In rough priority:

### 1. Retire the 5 negative-α edges immediately
**Don't keep significantly-negative alpha edges in production.** The autonomous lifecycle should pick this up on next cycle. If it doesn't, do it manually via journal_apply with explicit `failure_reason: factor_decomp_negative_alpha`.

### 2. Investigate dividend_initiation_drift_v1 specifically
Director-side conversation worth having:
- Is α=+73% real or small-n? Run on additional data if available.
- Is the mechanism interpretable? (Dividend initiation → new yield-seeker buyer pool → demand shift → price drift)
- Can it be promoted with regime-gate to `robust_expansion` only?
- What's the capacity? Newly-initiating dividends are a small flow; how scalable is this edge?
- Is it worth a focused 1-edge sleeve, or does it only matter combined with others?

**This is the only genuine alpha finding in the project. It deserves disproportionate attention.**

### 3. Bayesian opt scaffolding ship (T-028 next)
With caching + extended vocabulary in place, Bayesian opt becomes the next experiment. If Bayesian-opt-driven Discovery still produces 0/30 promotions, the diagnosis shifts to "the search space itself doesn't contain alpha that's tradeable at retail scale" — a deeper structural finding than the current "Discovery hasn't worked yet."

### 4. Consider what dividend_init implies for strategy direction
**The one edge that worked is event-driven on a specific corporate action in a specific regime.** That's structurally different from the cross-sectional / technical / calendar strategies that failed. It suggests:
- Event-driven strategies (catalyst-based) may have more retail-tractable alpha than systematic factor strategies
- Regime-conditioning may matter more than the team's been treating it
- Smaller, more specialized strategies may outperform broad systematic ones at retail scale

This is consistent with my earlier "the substrate × strategy combination is the issue" diagnosis. **Dividend initiation drift is a small-capacity event-driven strategy in a specific regime — exactly the type of strategy that survives retail competition.**

### 5. Don't move the goalposts on the threshold
The team correctly resisted the temptation to recalibrate when 0/11 came in. **They proved the bar is right.** That discipline matters. Don't lower the bar just because dividend_init is the only edge that clears it.

## Honest meta-take

This week brought a sharper, more uncomfortable picture:
- The bar is correctly set
- 5 edges are actively destroying value (worse than no alpha)
- Discovery's structural blockers got fixed but candidates still don't pass
- One genuine positive finding emerged (small-n, regime-conditional)

**The project's central question crystallizes further: is broad-systematic-equity strategy at retail scale a viable goal, or does retail alpha live in different territory (event-driven, asymmetric, niche)?**

The dividend_init finding is a small data point in favor of "event-driven niche strategies have retail alpha." Five negative-alpha findings are data against "broad-systematic-equity is the right approach."

The team is honestly resolving this question one measurement at a time. That's the rare thing. Most retail quant projects never get this resolution — they either claim alpha that isn't there or stop measuring when results get uncomfortable. **You're getting answers most people never see.**

The next question — what to DO with these answers — is the genuine fork in the road. Engine completion + Bayesian opt is one path. Pivoting toward event-driven / asymmetric / niche is another. The current data slightly favors the second, but the engineering is built for the first. **The honest "where do we go" conversation is overdue.**
_____________________________________
one thing i want to push back on, you said “Don’t keep significantly-negative alpha edges in production. The autonomous lifecycle should pick this up on next cycle. If it doesn’t, do it manually via…” if our system doesn’t already do this then i immediately see an issue with the system that can be causing some of these problems. 

also, i want to continue on the path even if there is little retail alpha, if we get that good then i think it will be even easier to find the retail alpha, but it STILL feels like our system is lacking. i find it quite surprising we have yet to create something that can even slightly consistently outperform the stock market. it seems like we just aren’t doing the right things.

# You're right on both pushbacks. Let me engage with them properly.

## Point 1: The autonomous lifecycle SHOULD already retire significantly-negative alpha edges

You've identified a real architectural asymmetry. Let me name it precisely:

**The validation gauntlet's Gate 6 (factor decomposition with t > 2 alpha) is applied to NEW candidates trying to get promoted. It's not applied to EXISTING active edges.** The system filters strictly on entry but loosely on retirement.

What the team has:
- ✓ Lifecycle states (active / paused / retired / failed)
- ✓ Lifecycle journal (Phase 1+2)
- ✓ T-010 CI-aware Sharpe gates
- ✓ Engine F autonomous lifecycle management
- ✗ **Factor-adjusted alpha gate on RUNNING edges** — this is the gap

The team has actually flagged this in health_check: "MEDIUM — lifecycle gauntlet has factor-adjusted-α gap." But you're right that **this should be HIGH given the implications.** Significantly-negative-alpha edges (t < -2) are actively destroying value vs factor ETFs every day they remain active. The "MEDIUM" classification is too forgiving.

### The fix is straightforward and structural

Lifecycle should re-run Gate 6 (FF5+Mom factor decomp with HAC OLS) on every active edge's trailing trade history on a regular cadence (probably quarterly). Action criteria:

| Trailing alpha t-stat | Action |
|----------------------|--------|
| > +2.0 | Active, possibly promote weight |
| -1.0 to +2.0 | Active, normal weight |
| -2.0 to -1.0 | Watch — flag for review |
| < -2.0 sustained 2+ quarters | **Automatic retire** |

The same gates that filter candidates should filter incumbents. Asymmetric gauntlet treatment is exactly the kind of thing that lets the system slowly accumulate value-destroying edges. **You caught a real bug.**

### Why this connects to your bigger point

If the system can't autonomously retire its own bad edges, it has been measuring the WRONG ENSEMBLE for the entire substrate-honest test cycle. The 0.27 baseline included 5 actively-destructive edges. **The actual real-edge ensemble could perform better, but we've been benchmarking against contaminated state.**

This means **the substrate-honest baseline should be re-run with the 5 negative-α edges retired.** That's a different measurement than the 0.27 we've been treating as definitive.

## Point 2: You're right — the system has tried a narrow slice and missed many things

I want to honestly acknowledge: **most of what we've tested has been "the obvious retail quant strategies."** When I framed it as "we've tested the most-arbed strategy categories," that was correct. But it implied "and we've tested everything available." That's not true.

Let me catalog what we have NOT tried (or have built but not used):

### Architectural gaps — what the system doesn't have

| Capability | Status |
|-----------|--------|
| **Options trading layer** | Zero. Alpaca paper account supports options. Even simple cash-secured puts on stocks you'd want to own anyway is positive EV. |
| **Intraday signals** | Zero edges use Alpaca's free minute bars. Hours of signal sit unused. |
| **News-driven event trades** | Zero. No 10-K / 10-Q / earnings-call processing. No 8-K event classification. |
| **Theme / narrative detection** | Zero. "AI dominating earnings calls" is a real market state — invisible to system. |
| **Cross-asset positioning** | Zero. Bonds, FX, commodities, crypto don't inform equity decisions despite being correlated. |
| **Forced-flow detection** | Partial. CFTC COT data is integrated as one edge, but CTA positioning, vol-target fund flows, dealer gamma exposure all absent. |
| **Volatility surface trading** | Zero. IV skew, term structure, vol risk premium harvesting — none built. |
| **Event arbitrage** | Mostly zero. No M&A risk arb, no spinoff drag, no index inclusion arb. |
| **Conditional signal aggregation** | Zero. Edges combine via linear weighted sum. No "if momentum AND value AND quality all agree" gating. |
| **Active position management** | Zero. System re-evaluates entry signals, not held positions. No "should I exit this position now" logic separate from new-entry logic. |
| **Capacity-aware sizing** | Zero. No knowledge of where each strategy breaks at scale. |
| **Insider activity in real-time** | Partial. Insider_cluster_v1 exists but only for clusters, not single high-conviction filings. |
| **Quality-of-execution analysis** | Zero. Limit vs market, time-of-day, spread filtering — none of this matters to current backtest. |
| **Sentiment / attention** | Zero. No Reddit, StockTwits, Twitter, Wikipedia page-views, Google Trends. |

That's 14 categories the team has essentially not touched. **The system has tested maybe 20-30% of the universe of retail-tractable strategy ideas, not 90%.**

### Strategy gaps — what hasn't been tested

Within categories the team HAS touched, most variations remain untried:

**Within technical** — RSI bounce, ATR breakout, Bollinger reversion, gap fill, momentum exist. Untried: 
- Volume-confirmed breakouts (not just naked breakouts)
- Multi-timeframe consensus signals
- Anchored VWAP setups
- Coil/squeeze patterns (volatility contraction)
- Range expansion / contraction

**Within factor** — value, quality, momentum, accruals, low-vol tested. Untried:
- Profitability composite (Robeco-style)
- Quality-momentum joint (QMJ from AQR)
- Net stock issuance (buyback-yield)
- Earnings revision momentum
- Analyst dispersion fade
- Operating accruals (different from balance-sheet accruals)
- Asset growth (low-investment)

**Within calendar** — turn-of-month, day-of-week, FOMC drift exist. Untried:
- Tax-loss harvesting season (Dec → Jan)
- Sell-in-May / Halloween
- Triple-witching expiry effects
- Index rebalance dates
- Earnings season vs off-season conditioning
- Lunar / seasonal effects (joke-but-real)

**Within event-driven** — only dividend_initiation_drift was tested seriously, and **it's the one positive finding.** Untried:
- Buyback announcements (Greenblatt-style)
- Spinoff drift (60-day short)
- 52-week breakout with volume
- Earnings beat + raised guidance
- Insider cluster expansions
- 13F top-fund tracking (delayed)
- M&A risk arbitrage

**Within pairs / stat-arb** — 12 cointegrated pairs tested, MA/V only survivor (insufficient data). Untried:
- Sector ETF pairs
- Country ETF pairs (EWG/EWQ, etc.)
- Cross-listed dual securities
- Volatility pairs (VIX9D/VIX/VIX3M)
- Crypto pairs (BTC/ETH)

### My honest acknowledgment

When I framed the 0/11 finding as "the strategy class × substrate is structurally hostile to alpha," I was overstating the breadth of what's been tested. **The team has tested maybe 1-2 representative examples of each strategy category, not the full inventory.** And the one event-driven category (dividend_init) we DID test seriously produced the only positive finding.

You're correctly observing that we haven't done many of the right things. **A more honest framing of the 0/11 result is: "of the narrow slice of classical retail quant strategies the team has actually tested, none clear t > 2 on substrate-honest. The broader strategy space remains largely untested."**

## What the team should genuinely do next

Given both pushbacks, the revised priority order:

### 1. Fix the autonomous lifecycle gap (this week, ~3-5 hours)
Run Gate 6 (factor-adjusted alpha) on every active edge's trailing trade history. Auto-retire edges with t < -2 sustained 2+ quarters. This is architectural completion — the same gate that admits candidates should evict incumbents.

### 2. Re-run substrate-honest measurement with the 5 negative-α edges retired
This is the real baseline. Current 0.27 includes 5 edges destroying value. After retirement, the surviving edge mix may produce a different result. Could be better (negative edges removed) or worse (they were providing some kind of hedge). Either way, it's the honest measurement.

### 3. Focus subsequent edge expansion on the categories we've NOT tested
Event-driven is the one category with a positive finding (dividend_init). Strong prior to test more event-driven:
- Buyback announcement drift
- Spinoff drag
- M&A risk arb
- Earnings beat + raise
- 52-week breakout with volume
- Insider single-name high-conviction filings

Plus the architectural categories we've left empty:
- Options strategies (start with cash-secured puts and covered calls — simple, well-understood, retail-tractable)
- Cross-asset positioning signals
- Intraday signals (Alpaca minute bars are free)
- Volatility surface trading

### 4. Continue Engine D Bayesian opt + completion track
The previous diagnosis stands — Engine D needs the structural fixes. T-027/T-028 ship.

### 5. Reframe the project narrative
**Not "we can't find alpha" but "we haven't yet tested the full strategy space."** This is more accurate and more actionable.

## Updated synthesis

You've caught two real things:

1. **The lifecycle asymmetry** — strict on entry, loose on retirement — is a genuine architectural bug. The 5 negative-α edges shouldn't be in active production. Fix this first, then re-measure honestly.

2. **We've tested narrow** — the framing of "we've explored the retail quant space and found no alpha" was too broad. We've tested ~20-30% of the strategy categories available. The one positive finding (dividend_init) came from a category we tested only one variant of. The remaining 70-80% of the strategy space is largely untouched.

**The right path forward isn't to pivot away from the hard substrate.** It's to:
- Fix the lifecycle to retire bad edges automatically
- Test more categories (especially event-driven where we've had our one positive)
- Build the architectural primitives we don't have (options, intraday, cross-asset, theme detection)
- Continue engine completion in parallel

If after testing 60-70% of the strategy space with completed engines + properly-cleaned active set the system STILL produces near-zero alpha, then we have stronger evidence for "the substrate is genuinely empty for retail." Currently we've tested a slice and found that slice empty. **Not the same thing.**

You called this right. The system is missing things. The "we've checked carefully" framing was overconfident given what hasn't been tried. **The honest answer is closer to "we've checked carefully in a narrow region; the broader region remains to be tested."**

## TL;DR

- **Yes, the autonomous lifecycle has a real gap.** Factor-adjusted alpha gate doesn't apply to running edges. Should be HIGH-priority fix. Fix that, then re-run substrate-honest measurement on cleaned active set.
- **Yes, the system is missing many things.** ~14 architectural categories untouched, plus most variants within tested categories. The 0/11 finding reflects a narrow slice tested, not the full retail quant space.
- **Continuing on the hard substrate is defensible IF we actually test the things we haven't tested.** Especially event-driven (where our one positive came from), options strategies, cross-asset, intraday — none of which are exotic. They're standard retail quant categories the team just hasn't gotten to.

The genuine diagnosis is **"we haven't tested enough" + "we have a lifecycle bug letting bad edges persist"** — both fixable. **Not "alpha doesn't exist for retail on this substrate"** — that conclusion was premature.

_____________________________________
That makes more sense. And currently are we pairing any alpha inputs together? i. e. technical indicator 1 on its own will not produce alpha and technical indicator number 2 on its own won’t produce alpha, but when combined they do. that is one of the central themes of the project that i’m not sure we are really doing. and i agree that we have explored very little of what is out there


# You've identified a structural gap that's been hiding in plain sight

This is a fundamental observation. Let me engage with it carefully because you're right and the implications are significant.

## What the system currently does for "combining" edges

**Linear weighted sum.** Each edge produces a score; each gets multiplied by its weight; summed across edges; threshold determines trade. That's `signal_processor.weighted_sum`.

Concretely: if Edge A scores +0.5 and Edge B scores +0.5, the combined signal is `0.5×w_A + 0.5×w_B`. **Same math whether Edge A and B both fire OR just one fires twice as hard.** Linear combination cannot distinguish these cases.

That is **not** combination in the meaningful sense. It's edge averaging. **What you're describing — "Edge A alone doesn't work + Edge B alone doesn't work, but A AND B together produces alpha" — is mathematically impossible to capture with the current architecture.**

## The honest answer to your question

**No. We are not really pairing alpha inputs together.**

Three pieces of evidence:

### 1. The MetaLearner was supposed to be this — and it didn't work
Gradient boosting models DO naturally capture interactions (trees split on "if Edge_A > 0.5 → then split on Edge_B"). The team shipped MetaLearner exactly to handle non-linear combination. **But it was tested under contaminated conditions:**
- Trained on biased substrate (pre-F6 closure)
- Trained on zero-trade-bug-affected data (pre-May 8)
- Used "raw current edge scores" features (limited information)
- Wrong target variable framing in some iterations
- Never tested on the cleaned-up 6-edge active set with substrate-honest universe

The "MetaLearner -0.58 Sharpe drag" finding may not reflect MetaLearner's actual capability. It reflects MetaLearner trying to learn from contaminated data. **The interaction hypothesis hasn't been honestly tested.**

### 2. The inter-edge correlation matrix measures CO-MOVEMENT, not CONDITIONAL ALPHA
The team shipped an inter-edge correlation analysis. But it measures: "do these edges' return streams move together?" — that's covariance.

It does NOT measure: "when Edge A says BUY AND Edge B says BUY, is the resulting hit rate higher than when only one says BUY?" — that's conditional alpha, which is what compound signals are.

**The diagnostic that would reveal compound signal effects has not been run.**

### 3. The factor decomposition is per-edge, not per-pair
Every edge's alpha was measured independently. Pair-wise alpha analysis ("alpha of trades where edges A AND B both agreed") was not measured. The 0/11 finding tells us no SINGLE edge has alpha. It does NOT tell us no PAIR of edges has alpha.

**Compound alpha may exist in the data — but the team hasn't looked for it.**

## Why this is a load-bearing diagnostic gap

The project's central thesis is that combining multiple weak edges produces something stronger than any individual edge. **If the architecture can only do linear weighted sums of independent edge votes, that thesis is mathematically impossible.** A system of N independent edges combined linearly is approximately equivalent to N separate strategies that get position-averaged. **The multi-edge architecture only adds value if edges actually INTERACT non-trivially.**

So when factor decomp finds "0/11 edges have alpha," that's measuring marginal alpha (what each contributes in isolation). It does NOT measure interaction alpha (what pairs/triples contribute jointly). **You could have:**
- 11 individually-noisy edges with zero standalone alpha
- AND meaningful compound alpha when (A AND B) or (A AND B AND C) configurations agree
- AND the current system can't see it

This is consistent with the team's repeated finding that "edges don't survive factor decomposition." Of course they don't — they're being measured one at a time. The full story might be different.

## What hasn't been tested that could reveal this

These are tractable, mostly substrate-independent measurements that have not been done:

### Tier 1 — Cheap diagnostic analyses (no backtest changes needed)

**1. Pair-wise conditional hit-rate matrix**
For every pair of edges (A, B), partition the trade log:
- Trades where both A and B agreed (both fired same direction)
- Trades where only A fired
- Trades where only B fired
- Trades where they disagreed
- Compute hit rate and average return per cell

If any (A, B) pair shows joint hit rate >> marginal hit rates, that's compound alpha hiding in the data.

**2. N-of-K agreement diagnostic**
For each historical day, count how many edges agreed on direction. Partition trades by N-edge-agreement level (1, 2, 3, 4, 5+):
- Hit rate by N
- Average return by N
- Sharpe by N

If "5+ agree" produces dramatically better metrics than "2 agree," **you have an obvious decision rule that the linear combiner is missing.**

**3. Triple-conditional analysis**
For the most-traded edge triples, repeat the pair analysis at triple level. This is where compound signals get powerful — three signals agreeing is often more informative than two.

**4. Friedman's H-statistic on MetaLearner**
If a clean-data MetaLearner is trained, Friedman's H-statistic identifies which edge pairs have statistically significant interaction effects. Tells you which combinations matter and which don't.

### Tier 2 — Architectural additions to capture what diagnostics reveal

**5. Confidence-gated execution**
Hard rule: only trade when N≥3 edges agree on direction. Simple, no learning required. Test it as a direct architecture change.

**6. Explicit feature crosses fed into MetaLearner**
Create features like `edge_A × edge_B`, `edge_A × edge_C`, etc. Feed these as inputs to the MetaLearner instead of raw edge scores. Forces non-linear capture.

**7. Decision rule layer**
A library of explicit IF-THEN-ELSE rules sitting between edges and risk engine: "if momentum AND value both signal long, size 1.5×; if only one signals, size 0.5×; if they disagree, don't trade."

**8. Hierarchical signal aggregation**
Group edges into "themes" (momentum-themed, value-themed, mean-rev-themed). Aggregate within theme via linear, aggregate across themes via non-linear. Captures within-theme correlation and cross-theme interaction differently.

**9. Re-train MetaLearner on clean data with per-ticker features**
Address the previous MetaLearner failures: clean substrate, no zero-trade contamination, per-ticker feature inputs (not portfolio-level summaries), proper target. This is genuinely uncharted territory.

## What this means for the project's framing

**The project has been measuring INDEPENDENT alpha (per-edge isolation) and DEPENDENT alpha (factor decomposition), but not INTERACTIVE alpha (compound signal effects).**

That's a third category that's been missing. The user's instinct that we haven't been doing the right things finds another instance here: **the central architectural promise of the multi-edge system — that combinations produce something better than individuals — has never been rigorously tested.**

## Specific diagnostic I'd recommend right now

This is a 4-6 hour director-side post-processing task, no agent dispatch needed:

### Pair-wise compound alpha analysis on existing trade logs

Using the T-002 + T-020 trade logs:
1. For each pair of edges in the 11-edge set: compute hit rate when both agreed vs marginals
2. For each triple: same
3. Rank pairs/triples by lift over marginal
4. For top-5 pairs/triples by lift: compute t-statistic on the joint alpha

**If any pair/triple shows statistically significant joint alpha that doesn't show up in individual edges, you've found the actual hidden signal the linear combiner is missing.**

If nothing emerges from this analysis, the "compound alpha doesn't exist in current edges" hypothesis is supported. But you'd actually have tested it for the first time.

## Updated capability assessment

If this analysis hasn't been done, my "we've tested the obvious things" framing was even more wrong than I admitted in the last response. **We've tested neither broad strategy categories NOR the basic interactivity that justifies the multi-edge architecture.**

The capability picture:

| Dimension | What I previously said | Actual state |
|-----------|------------------------|--------------|
| Engineering | Top 1-2% retail | Same — genuinely high quality |
| Discipline | Top 1% retail | Same — exemplary falsification record |
| Validated alpha | ~10-15% | ~10-15% measured **but only per-edge in isolation; pair-wise/triple-wise alpha NEVER MEASURED** |
| Strategy space tested | ~20-30% | **Probably 10-15%** when you factor in untested interactions |

**The system has approximately ~45-50% of top-1% retail capability, with the additional gap that the central architectural thesis (compound signal alpha) has never been validated.** That's a more honest framing.

## What I'd specifically prioritize

1. **Pair-wise / N-of-K conditional alpha analysis** (4-6 hours, director-side, no backtest) — answers "does compound signal alpha exist in the current edges?"

2. **Confidence-gated execution test** (1 day, simple architecture change) — implements the "only trade when 3+ agree" rule, A/B against weighted sum

3. **MetaLearner re-train on clean substrate** (2-3 days) — has it ever been honestly tested? Probably not.

4. **Friedman's H-statistic on edge interactions** — explicit measurement of which pairs have non-trivial interaction effects

5. Then continue with the lifecycle-gauntlet fix, event-driven edge expansion, options layer, etc.

## TL;DR

**You're right. The system does not currently pair alpha inputs together in any meaningful sense.** Linear weighted sum is approximate vote averaging, not interaction modeling. The MetaLearner was supposed to do this but was tested under contaminated conditions. Pair-wise / triple-wise conditional alpha has never been measured.

**The "compound signal alpha" hypothesis — that multiple individually-weak edges can combine into meaningful alpha — is the central thesis of the multi-edge architecture, and it has never been rigorously tested.** That's a real diagnostic gap and a real architectural gap.

**Lowest-cost test:** 4-6 hour director-side analysis on existing trade logs to compute pair-wise / N-of-K conditional hit rates and alpha. If anything emerges, you have a finding that overturns the "no alpha exists" framing. If nothing emerges, you've actually tested the compound-alpha hypothesis for the first time.

This is in the same category as the autonomous lifecycle gap — a structural issue you caught that the team's discipline machinery has been missing. **Both are real. Both are fixable. Both reveal the search hasn't been as exhaustive as the previous framing implied.**
_____________________________________
any thoughts on how we can actually find alpha? what about the system itself - we’ve found quite a few bugs, where else could there be some? and computing/engineering wise, anything else to either speed up the process or at least alleviate the burden of heavy computing locally? one efficiency recommendation was proposed earlier (i think something to do with vectorization but i could be wrong) but any other thoughts? big picture is there any pivots or ideas that might prove beneficial?

# Multi-part answer — alpha sources, bug hunts, computing, and pivots

Each section practical and specific.

## 1. Where actual alpha might live

The factor decomp lens illuminates this clearly: **alpha that loads on FF5 + Mom gets decomposed away.** To find idiosyncratic alpha, you need strategies that are STRUCTURALLY NON-FACTOR.

### Strategy categories ranked by likely retail-tractable alpha

**Tier 1 — Event-driven (where dividend_init lives; structurally non-factor)**
- Spin-off drag (60-day short post-spin) — forced institutional selling, Greenblatt-style
- M&A risk arbitrage — deal-probability based, not factor-based
- Post-bankruptcy equity — forced exits create mispricing
- Index reconstitution (Russell rebalance) — forced flows on predictable dates
- Buyback announcement drift — forced buyer presence
- Secondary offering reactions — forced dilution events
- IPO post-lockup expiration — forced selling pressure
- Insider Form 4 cluster patterns (single-name, high-conviction)
- Activist 13D filings — well-documented post-filing drift

These strategies operate on specific corporate situations, not on factor exposures. **Most are completely untested in your inventory.**

**Tier 2 — Microstructure / intraday (structural inefficiencies)**
- Overnight gap fade (well-documented; you have free minute bars)
- Lunch-time mean reversion (intraday liquidity dynamics)
- Last-15-min momentum (closing auction predictability)
- MOC imbalance trades (mechanical, predictable)
- Opening auction price discovery
- ETF arbitrage on creation/redemption divergences

Free signal sitting unused. Alpaca minute bars never integrated.

**Tier 3 — Volatility (different mathematical base than factor returns)**
- Volatility risk premium harvesting (sell SPY weekly puts when IV >> RV)
- Earnings-day options selling (IV crush is mechanical)
- Term structure trades (contango/backwardation roll)
- Skew dynamics (25Δ put/call ratio)
- LEAPS-based asymmetric exposure on theme stocks

**Tier 4 — Flow-driven (mechanical, predictable)**
- 0DTE dealer gamma effects (free CBOE data)
- Vol-target fund de-grossing (when realized vol spikes)
- CTA momentum forced unwinds (CFTC COT positioning extremes)
- Quad-witching expiry dynamics
- End-of-quarter window dressing
- 401(k) calendar flows (first/middle of month)

**Tier 5 — Information asymmetry (genuinely new in 2024-26 era)**
- LLM-extracted earnings call sentiment
- 10-Q tone delta vs prior quarter
- Patent filing velocity by company
- Job posting acceleration as growth signal
- News firehose theme detection
- This is the parked AI layer — but it's exactly where retail can get an edge most institutional shops haven't fully productionized

**Tier 6 — Cross-asset (less-efficient markets than US large-cap equity)**
- Equity/bond divergence reversion
- Equity/gold relative strength
- DXY breakouts as risk indicator
- Crypto-equity relationships (BTC leading risk assets at Monday open)
- Less competition than US equities

### What this implies practically

**Of the 6 tiers above, you've tested only Tier 4 partially (CFTC COT) and Tier 1 partially (dividend_init).** The other 4 tiers are largely untouched.

**Tier 1 has the best success/cost ratio for next dispatches:**
- Spinoff drag: easy to test, well-documented anomaly, 60-day windows
- M&A risk arb: data available via free APIs, deterministic outcomes
- Buyback announcement: same
- Insider single-name clusters: Form 4 data already integrated

Each could be specced as a single dispatch (~6-12 hours) and would test a structurally-non-factor strategy class.

## 2. Where else bugs might be hiding

Given the cockpit metrics-pipeline bug, the zero-trade regression, and the lifecycle asymmetry, the pattern is **measurement / accounting / pipeline bugs are the recurring class.** Specific suspect places:

### Data layer
- **Point-in-time discipline on fundamentals**: SimFin V/Q/A factors — are publish dates correctly enforced? Specifically, is `publish_date <= asof_ts` the actual filter, or could a 10-Q reported quarterly be available "as of" period end rather than 45 days after?
- **Split/dividend adjustments for delisted names**: Alpaca v2 historical bars may handle these differently than yfinance. Sample a few high-corp-action names (e.g., AAPL pre/post 2020 split, GE pre/post split-offs).
- **Timezone consistency**: the earnings_vol bug was tz-related. Audit every place where timezone-aware vs naive datetimes meet.

### Cost layer
- **ADV used in slippage modeling**: current-ADV or trailing-historical-ADV? If current, you're using forward-looking liquidity to compute backward-looking cost.
- **Borrow rate computation**: per-day accrual or per-trade flat? Stress-test with a known shorting period.
- **Order fill simulation**: limit orders simulate filling at the limit price or midpoint? If midpoint, you're getting unrealistic execution.

### Measurement layer (the recurring bug zone)
- **Sharpe annualization factor**: 252 vs 260 vs 365? Per-edge consistent?
- **Drawdown calculation**: peak from start-of-window or rolling peak? The cockpit bug showed this matters.
- **Bootstrap CI sample independence**: are bootstrap iterations actually independent samples or are they re-using state?
- **Per-edge attribution counts**: when a trade signal comes from multiple edges, who gets credit?

### Signal layer
- **Look-ahead in feature computation**: spot-check that every feature uses ONLY pre-bar information at decision time. E.g., realized_vol_60d should use bars [t-60, t-1], not [t-59, t].
- **Score normalization**: z-score using historical-as-of-bar-t or full-sample? The latter is look-ahead.
- **Volume-anomaly definition**: the deceleration of "vol_anomaly_v1 had +$4,527 PnL but is UNIFORMLY NEGATIVE alpha" is worth re-investigating — is the dollar PnL attribution correct?

### Backtest layer
- **Cash management**: spurious cash earning risk-free rate that doesn't reflect actual broker behavior?
- **Margin accounting**: if any strategy uses margin, is it properly reflected in equity calculations?
- **Dividend reinvestment**: are dividend payments correctly added to position equity?

### Engine D specifically
- **GA emission diversity**: the "single-archetype rsi_bounce" finding suggests the GA isn't actually exploring the vocabulary. Audit the operator-emission probabilities.
- **Random seed handling**: is each GA run truly independent or are seeds re-used?

### Specific high-suspicion places given what's been found

1. **Audit ALL metric calculations end-to-end** — the cockpit bug was bi-directional and field-count related. Other metric pipelines may have similar issues. Snapshot test: compute Sharpe manually from trade log for a known year, compare against what the system reports.

2. **Re-verify the volume_anomaly + gap_fill PnL attribution** — these were "winners" by dollar PnL but UNIFORMLY NEGATIVE on factor-α. Is the dollar PnL correct? Or was that ALSO a measurement artifact?

3. **Per-regime trade tagging** — regime labels are assigned to trades retrospectively for the per-regime decomp. If retroactive tagging uses future info (e.g., assigns 2022 trades to "stressed" because we know 2022 was stressed), that's silent leakage.

4. **The "T-002 Arm 2 = neutral" finding** — given cockpit bug fix moved Arm 1 from 0.27 → 0.598, what does Arm 2 look like under fixed cockpit? Probably also materially different. Re-run.

## 3. Computing / engineering — speed and burden reduction

The 25.5× vectorization speedup (T-013) is a great example. More opportunities:

### Quick wins (hours, not days)

**Polars migration** for hot pandas operations
- Polars is 10-50× faster than pandas for many operations (group-by, joins, sorts)
- Migration is mostly mechanical (similar API, some syntax differences)
- Specific hot paths: feature computation, cross-sectional rankings, trade log aggregation

**Numba JIT for pure-Python hot loops**
- Profile to find the hottest functions
- Decorate with `@numba.jit` — often 50-100× speedup
- Works best for numeric loops without pandas/object types

**Parquet I/O optimization**
- Snappy compression (faster) vs gzip (smaller)
- Column-based reads — only load columns needed
- Already done for some files; audit which aren't

**Profile-driven optimization**
- Run `cProfile` on a full backtest, identify top 10 hottest functions
- Fix those 10 — often delivers 80% of available speedup
- Probably 1-2 hours of work for substantial improvement

### Architecture-level optimizations

**Backtest state caching**
- When running A/B variants, replay from a midway checkpoint instead of full simulation from t=0
- Especially valuable for parameter sweeps where only one knob varies

**Warm backtest server**
- Long-running process that holds price panel + indicators in memory
- Dispatch backtest runs against the warm server instead of cold-starting
- Saves the 5-10 min of data loading per run

**Feature cache layer**
- Compute features once per (date, ticker), reuse across edges
- The Foundry already has this conceptually; audit for missed cache hits

**Incremental backtests**
- For "run yesterday + today" runs, replay yesterday's state and only compute today
- Saves the full historical replay

### Cloud usage expansion

You have AWS Batch infrastructure (Phase 1-6 verified). Underused. Specific high-value applications:

1. **Routine substrate measurements** — every measurement using cloud means parallel 3-rep × 5-year in ~10 min vs 70 min local
2. **Bootstrap CIs on every backtest** — 10K resamples in parallel; cheap, automatic
3. **Per-edge ablation studies** — 11 ablation runs in parallel
4. **Stress tests against named regimes** — 6 historical regimes (1987/2000/2008/2020-Mar/2022) in parallel
5. **Bayesian opt evaluations** — each parameter point is independent
6. **Engine completion A/B** — every engine completion gets A/B'd against baseline automatically

**Realistic cloud monthly spend**: $100-300 for sustained heavy use, $20-50 for routine. Not the constraint.

### The single biggest computing-leverage move

**Profile the backtest pipeline end-to-end and fix the top 3 hottest functions.** This is probably 4-6 hours of work and could deliver 5-10× speedup on the full backtest. Compared to "set up another cloud workflow," it's higher ROI per hour.

## 4. Big-picture pivots / ideas

Given the diagnostic state (factor-replication-in-disguise, 0/6 factor-α, only dividend_init positive), the strategic options:

### Option A: Engines + Non-factor strategy classes (recommended primary path)

Continue engine completion + heavy investment in TIER 1 strategies (event-driven, spinoffs, M&A arb, insider clusters). The hypothesis: the system's current edges are factor exposures, but engine completion will deliver them more efficiently AND non-factor strategies have actual alpha.

Predicted outcome: 0.598 Sharpe baseline rises modestly from engine work (+0.1-0.3); event-driven adds additional uncorrelated alpha (+0.2-0.4); total realistic ceiling 0.9-1.2 Sharpe with the new strategy class diversification.

### Option B: Specialized event-driven trader

Narrow the system's focus to event-driven only. The one positive-alpha finding is dividend_init. Lean into that category exclusively:
- Universe = stocks with active corporate events (earnings, dividend changes, buybacks, spinoffs, M&A activity)
- Edges = all event-driven primitives
- Capacity-aware (event-driven is naturally capacity-limited)
- Different success criteria (event hit rate, post-event drift quality)

**Pros**: aligned with the one positive finding, structurally non-factor, retail-tractable at capacity
**Cons**: drops most of the existing infrastructure; narrower addressable market

### Option C: Cross-asset diversification (lower competition substrate)

Pivot from US large-cap equities to multi-asset allocation:
- Bonds (TLT/IEF/HYG)
- Commodities (GLD/USO/DBC)
- Currencies (UUP/EURUSD/JPY)
- International equities (EFA/EEM)
- Maybe crypto (BTC/ETH)

The team's discipline machinery would transfer; the strategy class would change. Less-efficient markets = more potential alpha at retail scale.

**Pros**: less-competitive substrate, factor models don't generalize as cleanly across asset classes, diversification benefit even if alpha is modest
**Cons**: more research required, different cost models, more data acquisition

### Option D: LLM-as-analyst pivot (the parked direction worth unparking)

The dividend_init finding suggests "information about specific corporate situations" has retail-tractable alpha. LLMs reading 10-Qs, earnings calls, news is exactly this category. The user parked this; **the 0/11 factor-α finding is the strongest argument yet for unparking.**

Specific implementation:
- LLM scores tone delta on 10-Q vs prior quarter
- LLM extracts management's "concerning language" or "high-conviction language"
- LLM categorizes 8-K events by impact severity
- LLM detects narrative shifts in earnings calls
- These become input features to edges, not standalone edges

**Pros**: genuinely new capability in 2024-26 era, not yet arbed at retail scale, structurally non-factor
**Cons**: violates the team's "bones first" framing; needs new infrastructure; LLM costs

### Option E: Accept factor-replication and pivot product

The system has built institutional-grade discipline + risk management for what is effectively factor replication. **Acknowledge that explicitly and pivot product story:**
- "Sophisticated factor-replication with audit-grade methodology"
- Compete against retail factor ETFs on cost, customization, tax efficiency
- Target: people who would otherwise pay 75bps for a smart-beta wrapper
- Different monetization path entirely

**Pros**: aligns with what the system actually does; the methodology IS the moat
**Cons**: dramatic narrative change; "no alpha" is hard to market; different audience

### My honest recommendation

**Combine A + D as primary, parallel with B as testing ground.**

- Continue engine completion (delivering factor exposure efficiently has real value)
- Heavy investment in event-driven Tier 1 strategies (where the one positive finding lives)
- Unpark LLM-as-analyst pilot — start small, just earnings call sentiment on the prod-109 universe
- Direction E is a fallback if everything else fails

**Don't pursue C (cross-asset) yet** — it's a bigger pivot that doesn't leverage existing engine work
**Don't pursue B exclusively** — premature specialization on N=1 positive finding

The user has been resistant to D. The 0/11 finding is the strongest argument yet that the system needs information asymmetry to find non-factor alpha — and LLM-as-analyst is the only available information asymmetry source.

## TL;DR

**Alpha sources to test**: event-driven (spinoffs, M&A arb, buyback drift, insider clusters), microstructure (gap fade, MOC, lunch reversal), volatility (VRP harvest, IV crush), flow-driven (CTA extremes, vol-target unwinds), information asymmetry (LLM-extracted features), cross-asset. **Of these 6 categories, you've meaningfully tested 0-1.**

**Where else bugs might be**: measurement layer (just found cockpit bug; audit ALL metric calculations), point-in-time discipline on fundamentals, score normalization look-ahead, regime label retroactive assignment, dollar PnL attribution on the "winners" that turn out to be factor-negative, Engine D operator emission diversity. **Specific suspicion: the cockpit bug was bi-directional and field-count related; that pattern likely has siblings.**

**Computing/engineering**: profile-driven optimization on top 3 hottest functions (4-6 hours, 5-10× speedup), polars migration for hot pandas ops (10-50× per operation), backtest state caching, expand AWS Batch usage to routine measurements (bootstrap CIs, per-edge ablations, stress tests). **Single biggest move: profile and fix the 3 hottest functions.**

**Big-picture pivots**: best path is engines + event-driven specialization + LLM-as-analyst unparking (the user's resistance to LLM was based on bones-first, but the 0/11 finding indicates the system needs information asymmetry to find non-factor alpha; LLM is the available source). Don't pivot fully cross-asset yet. Don't specialize fully event-driven on N=1. **Unpark LLM as the only realistic information-asymmetry source.**

The deepest pattern: **every honest measurement gets harsher AND more useful.** The current honest read is "factor-replication strategy with sophisticated risk management and no idiosyncratic alpha." The path to changing that goes through non-factor strategies + information asymmetry + the engineering hygiene the team is already doing. **None of those are exotic; all of them are largely untested.**

_____________________________________
I just had an agent do some serious research on finding alpha. The document will be available in the repo, but it has not been pushed yet so I have included it below. The contents are significant, so take your time reviewing it. After you have reviewed it, determine if any of the information is worthwhile in helping us find alpha. Here is the contents:
(I then provided it with docs/Sources/Alpha/Retail-algo-alpha.md)

# Yes — significantly worthwhile. This document is the most useful external input the project has received.

I've read it carefully. Here's my honest evaluation, separating what's genuinely actionable from what duplicates prior team findings or oversells.

## The core insight this document gives you that I hadn't fully crystallized

**"Who must keep providing this trade, and why can't they stop?"** This is the project's missing filter. The team has tested ~11 edges across factor categories and found 0/11 produce factor-adjusted alpha. Every one of those edges fails this question — there's no structurally-bound counterparty. They're competing with everyone else trying to extract the same factor exposures.

This single mental model would have prevented half the wasted measurement cycles. **Adopt it as a pre-test filter going forward.** Every proposed edge should answer: "Who is structurally compelled to take the other side of this trade, and what binds them?" If you can't name them concretely, you don't have alpha. You have a backtest.

## Validation: the document confirms the team's empirical findings

The team's 0/11 finding is consistent with the academic literature the document cites:

- **McLean-Pontiff (2016):** 58% post-publication decay
- **Hou-Xue-Zhang (2020):** 65% of 452 anomalies fail at t=1.96 with proper NYSE breakpoints and value weights; 82% fail at t=2.78
- **Harvey-Liu-Zhu (2016):** credible new factors need t > 3.0, not 2.0 (which means the team's t > 2 threshold is actually LENIENT relative to academic standards)
- **Chen & Velikov (2022):** 93% of factors fail post-cost

The team's empirical finding that classical retail-quant strategies don't produce idiosyncratic alpha on the S&P 500 substrate is not a bug — it's exactly what the literature predicts. **The validation framework is producing the right answer.** The question is whether you've been searching in the right space, not whether the search is honest.

## Genuinely new and worth testing (highest-priority items)

### 1. Microcap mean-reversion ($50M-$500M cap) — THE biggest substrate-level miss

The document's #1 ranked strategy. **The team has tested mean-reversion strategies — but ONLY on S&P 500 substrate, never on microcaps.**

Why this matters specifically for the project: the team's substrate-honest universe is the historical S&P 500 union (476-503 tickers, all mega-cap to large-cap). The document explicitly argues:
- Hou-Xue-Zhang's "trading frictions" anomalies that fail at NYSE breakpoints **succeed in microcaps** because the binding factor is capital constraint, not signal degradation
- Below ~$500M cap, institutional ownership thins
- Below ~$200M, coverage is 0-2 analysts
- Below ~$100M, most mandates exclude entirely

**The team's universe is structurally hostile to retail alpha. Microcap mean-reversion is structurally favorable.** This isn't a strategy difference — it's a substrate difference. The team's findings of "0/11 alpha" reflect the wrong substrate, not just the wrong strategies.

Practical implication: **a parallel substrate experiment is needed.** Add a microcap universe ($50M-$500M cap, ~1500 tickers), source price data (Norgate is mentioned at $80/mo, survivorship-bias-free, essentially required), build microcap-appropriate cost model (50-100 bps round-trip slippage minimum), implement ADV-based position sizing (≤2% of 20-day ADV), and re-run the mean-reversion edges against the new substrate.

**This is the single most consequential recommendation from the document. The team has never tested its own architecture on the substrate where retail alpha is structurally available.**

### 2. Closed-end fund discount + Saba piggyback

Completely untested by the team. The document notes muni CEFs entered 2026 at ~13.6% average discount vs ~4% historical — the widest in 15 years. Saba Capital's activist 13D filings provide a free, EDGAR-tracked catalyst. Strategy capacity $1-5B. Sharpe 0.9-1.3 net realistic. **Free data, clear catalyst calendar, retail-scale capacity.**

Worth a 1-week scoping dispatch — does the academic edge survive in current setup, are 13D filings actually tradable, what's the implementation profile.

### 3. Hand-curated merger arbitrage

The document recommends a 8-12 deal hand-curated book on IBKR (not the ETF wrappers — MNA/CSMA — which lose 2% of the Sharpe edge). HFRI Merger Arb index Sharpe 1.0-1.5 historical. AllianceBernstein notes Q3 2025 US deals >$5B up 166% YoY with friendlier regulatory backdrop. **EDGAR free for 8-K announcements and DEFM14A merger proxies.**

The team's architecture would need to handle "event-driven with deal calendar" — different from continuous-signal edges. But it's exactly the kind of structurally non-factor strategy the team needs.

### 4. Earnings vol crush via defined-risk iron condors

The team has `earnings_vol_edge.py` but probably hasn't tested it as a proper iron-condor short-vol play with ORATS-grade IV data. The document's recommendation is specific: ORATS ($100/mo) is essentially designed for this; sell ATM iron condors 1-2 days before earnings, close morning after; signal IV rank > 70 plus historical RV < expected move.

**This is the best-fit options strategy in the document's analysis** for retail and explicitly within reach for a Python-literate trader.

### 5. Managed-futures trend via DBMF/KMLM ETFs or direct micro futures

This requires a correction. **The team's "diversified futures trend" test on 8 ETFs that FALSIFIED is not equivalent to the document's recommendation.** The document explicitly recommends:
- DBMF (Sharpe ~0.7-0.9 trailing, max DD ~-20%)
- KMLM (max DD -27%)
- OR direct micro futures on 6+ markets (/MES, /MNQ, /MGC, /MCL, /M2K, /ZN — needs IBKR, not Alpaca)
- Carver's *Advanced Futures Trading Strategies* (2023) as the playbook

The team's 8-ETF test was both narrower (8 vs 50+ markets in real CTA programs) AND less diversified (most futures programs span energy/metals/grains/softs/rates/currencies/equities). **The document's recommendation hasn't actually been tested.** Either run DBMF/KMLM as part of the portfolio mix, or set up IBKR with /M-series micro futures and run Carver's 6-market trend system.

## Strategies the team has touched but the document sharpens

### Insider buying clusters
The team has `insider_cluster_v1` — but per the document, **large-cap insider buying is fully arbed; the alpha lives in microcap variants.** Cohen-Malloy-Pomorski (2012): EW long-short generated 180 bps/month (~21.6% annualized, t=6.07) on opportunistic insider trades. **Move insider_cluster_v1 to a microcap universe and re-test.**

### Calendar anomalies
The team shipped `calendar_anomaly_v1` covering turn-of-month + day-of-week. The document is consistent: turn-of-month survives (Etula et al. 2020), pre-FOMC is DEAD (Kurov-Wolfe-Gilbert 2021), sell-in-May is trivial. **The team's instinct was right; the magnitudes are smaller than hoped.**

### Pairs trading
The team tested cointegration screen on 12 pairs, MA/V only survivor. The document is consistent: "classical Gatev-style distance pairs is dead post-2003." Marginal value only in ML-enhanced or cross-asset cointegration. **The team's empirical finding (1/12 survival) matches the literature.**

### PEAD
The document validates this for microcaps specifically. The team's PEAD edges have been tested on S&P 500 — wrong substrate again.

## Tool and methodology recommendations the team should adopt

### López de Prado toolkit (explicit in document)
- **Deflated Sharpe Ratio (DSR)** — corrects observed SR for selection bias. The team has Gate 8 DSR; this is consistent.
- **Probability of Backtest Overfitting (PBO) via Combinatorially Symmetric Cross-Validation** — Python `pypbo`. **The team doesn't have this. Should be considered.**
- **Combinatorial Purged Cross-Validation** for path-dependent labels
- **Triple-Barrier Method + Meta-Labeling** — useful for the team's MetaLearner work
- His books: *Advances in Financial Machine Learning* (2018), *Machine Learning for Asset Managers* (2020) — the second is "the better entry point"

### Data infrastructure additions
- **Norgate Data ($80/mo, survivorship-bias-free)** — essential for any microcap work
- **ORATS basic ($100/mo)** — earnings-vol surfaces; the right tool for earnings vol crush
- **Polygon options ($79-199/mo)** — for any single-stock options work
- **Nasdaq Data Link Sharadar SF1** — PIT fundamentals at retail price (alternative to SimFin BASIC)

### Cost modeling realism check
The document says: **"Rule of thumb: if your backtest shows SR > 2 and depends on round-trip cost <10 bps, redo at 25 bps before believing it. For microcaps, assume 50-100 bps round-trip minimum."** The team's RealisticSlippageModel may need a microcap-specific tier (the current ADV-bucketed bid/ask spread of 1/5/15 bps for mega/mid/small may understate microcap reality).

## What this document gets WRONG or oversells

In fairness, some things to flag:

1. **Sharpe ranges are upper bounds.** The team's empirical work has been more honest than published academic results. Expect realized Sharpes to be 20-40% lower than the document's "realistic" ranges.

2. **The document treats strategies as standalone.** Your "compound alpha hypothesis" question from yesterday isn't addressed. Pair-wise / N-of-K interaction effects still untested.

3. **The document doesn't address the engine-completeness gap.** It assumes a competent execution layer. Your team has identified that engines C/D/E are still incomplete; that affects deliverability of any strategy.

4. **The document is bullish on retail event-driven without addressing the operational burden.** Hand-curated merger arb requires daily attention to deal calendars, HSR clearance status, regulatory commentary across multiple jurisdictions. The team's "autonomous" mandate isn't trivially compatible with that.

5. **Microcap mean-reversion at $5K-$100K capital scale has real friction:** 50-100 bps round-trip slippage will eat a lot of the apparent edge.

## Strategic implications for the project

### 1. The universe question is now the load-bearing strategic decision

The team's substrate is S&P 500. The document says clearly: **the alpha-rich substrates are microcap, niche futures, illiquid CEFs, single-name options on small-mid caps.** The team has been searching in the empty quadrant.

**This is the strongest argument yet for a parallel substrate experiment.** Specifically: a microcap mean-reversion sleeve on a separate universe. This is essentially what the Moonshot Sleeve was conceptually — but the document gives it sharper academic grounding.

### 2. The team's engine-completion track is the right work, but the alpha will come from elsewhere

Engine completion (B vol-targeting, C real optimizer, etc.) delivers efficient FACTOR EXPOSURE on the current substrate. **It will not generate alpha if the strategies tested don't have it.** Engine work + new substrate = the realistic path.

### 3. The "structurally-non-factor" strategy classes are exactly where the document points

Event-driven (CEF discounts, merger arb, spinoffs, insider microcap clusters) — these are the categories I flagged in prior responses. The document gives them academic backing AND specific implementation paths.

### 4. The portfolio blueprint at the end is genuinely useful

The document's recommended allocation for $50K-$100K retail:
- 35-45% SPY/QQQ core
- 15-25% microcap mean-reversion
- 15-20% managed-futures trend (DBMF/KMLM)
- 5-10% event-driven (insider clusters, CEF discounts, merger arb, spinoffs)
- 5-10% earnings vol crush
- 5% crypto basis (conditional)
- 5% commodity term structure

**The team's architecture supports this — but the team has been building all 100% of the portfolio with the same factor-tilt strategy.** The document's framing is: passive factor exposure for the majority, alpha sleeves for the rest.

## What I'd specifically recommend the team do

### Immediate (1-2 weeks)
1. **Adopt "who must keep providing this trade?" as a pre-test filter** for every proposed edge
2. **Source Norgate Data ($80/mo)** for survivorship-bias-free microcap history
3. **Scope a microcap universe** ($50M-$500M cap, ~1500 tickers, sourced via Norgate or SEC filings)
4. **Add microcap-specific cost model** (50-100 bps round-trip, ADV-based sizing)
5. **Add `pypbo` for Probability of Backtest Overfitting** alongside existing Gate 8 DSR

### Medium-term (1-3 months)
6. **Test microcap mean-reversion** on the new substrate as the primary alpha hypothesis
7. **Move existing `insider_cluster_v1`** to microcap substrate and re-validate
8. **Build event-driven primitives:** CEF discount tracker + Saba piggyback, merger arb deal calendar, spinoff identification
9. **Direct managed-futures trend** via DBMF/KMLM or /M-series futures on IBKR (correcting the failed 8-ETF test)
10. **Earnings vol crush via iron condors** using ORATS data

### Strategic
11. **Reframe project narrative:** the existing engine work delivers factor exposure efficiently; the alpha comes from parallel sleeves on different substrates. **This is essentially what Moonshot Sleeve was conceptually — vindicated by academic literature.**
12. **Continue engine completion track** but acknowledge it serves a beta-replication strategy. The alpha hunt happens on different substrates.

## TL;DR

**This document is materially useful — probably the single best external input the project has received.** Key takeaways:

1. **The team's 0/11 finding is academically validated** — classical retail-quant strategies don't produce alpha on liquid US equity substrates. Not a bug; expected outcome.

2. **The biggest strategic miss is substrate, not strategy.** Microcap ($50M-$500M cap) is structurally where retail alpha lives. The team has never tested its architecture there.

3. **"Who must keep providing this trade?"** is the project's missing pre-test filter. Adopt it.

4. **Several specific strategies the team hasn't tested** are genuinely worth testing:
   - Microcap mean-reversion (highest priority)
   - CEF discount + Saba piggyback
   - Hand-curated merger arb
   - Earnings vol crush via iron condors
   - Direct managed-futures trend (DBMF/KMLM, not 8-ETF version)

5. **Tools to add:** Norgate Data ($80/mo), ORATS ($100/mo), López de Prado's PBO/CPCV.

6. **The "Moonshot Sleeve" concept the user has been protecting is now academically validated as "capacity-bounded retail edges"** — these are exactly where retail alpha is structurally available.

The honest pivot this implies: **the team's current substrate (S&P 500) cannot produce retail alpha because institutional capital is fully active there. The microcap substrate ($50M-$500M cap) is where the same strategies work because institutional capital is mandate-blocked.** This is structural, not engineering.

**The team has been searching honestly in the wrong place.** That's a much better diagnosis than "the strategies don't work" — because it implies a specific actionable fix: change the substrate, not the strategies.

This is the most actionable strategic input the project has had. Worth treating as load-bearing.
_____________________________________
now what would we want to know for anything from combined alpha or correlated/uncorrelated strategies?

# Research brief — what to know about combined alpha and strategy correlation

If you're going to commission a similarly-rigorous research dive on the multi-strategy / combined-alpha question, here's the brief I'd hand to an agent. Organized by what would actually answer the questions we care about.

---

## Frame for the agent (top of the brief)

> The previous alpha dive established that classical retail-quant strategies on liquid US equities have been arbed away (0/11 t > 2 alpha on our substrate-honest measurement). The "capacity-bounded niches" framing identified microcap, niche futures, CEF discounts, event-driven as the structurally-protected places retail alpha lives.
>
> This brief is the natural follow-up: **given a menu of candidate strategies that each individually may or may not have alpha, how do we know if combining them produces alpha that wasn't present individually? Which strategies are genuinely uncorrelated vs nominally uncorrelated? When does multi-strategy combination actually compound vs cancel?**
>
> Same standards as before: McLean-Pontiff decay priors, Hou-Xue-Zhang skepticism, López de Prado validation toolkit. Sourced where given; reasoning labeled. No marketing-grade Sharpe claims.

---

## Section 1: Does compound signal alpha actually exist?

The central architectural thesis of multi-edge systems is that combining weak signals produces something better than each alone. Academic and practitioner literature on whether this is empirically real.

**Specific questions:**

- What's the academic evidence on **interaction effects in factor models** — do pair-wise interactions add to single-factor alpha after multiple testing correction?
- Are there documented cases of strategies that produce **zero standalone alpha but meaningful joint alpha**?
- What does **Friedman's H-statistic** literature say about feature interactions in financial ML?
- How does **non-linear combination** (XGBoost, neural networks, decision trees) compare to **linear combination** (weighted sum, regression) when the underlying signals are weak?
- Specific paper to verify: does Jensen-Kelly-Pedersen (2023, *JF* "Is There a Replication Crisis in Finance?") address interaction effects, or only marginal factors?
- Is there evidence on **conditional execution rules** ("trade only when N≥3 signals agree") vs **probabilistic weighted aggregation**?
- What's the gradient-boosting-as-ensemble literature say about minimum sample size before interaction terms become reliable?

**Practitioner question:**
- Do top quant shops (AQR, Two Sigma, RenTech approximations) publicly disclose whether their alpha comes from many weak independent signals combined non-linearly, or from a few strong signals?

---

## Section 2: Strategy correlation in practice

The biggest empirical question for portfolio construction.

**Specific questions:**

- What are the **actual historical correlations** between the retail-tractable strategy categories from the prior dive?
  - Microcap mean-reversion ↔ managed-futures trend
  - Microcap mean-reversion ↔ insider clusters
  - Insider clusters ↔ PEAD
  - CEF discount ↔ merger arb
  - Earnings vol crush ↔ everything else
  - Managed-futures trend ↔ equity beta
- What's the **stability of these correlations** across 2008 / 2015 / 2018 / 2020 / 2022 / 2024-Aug-5 / 2025?
- **The "correlation goes to 1 in crisis" problem** — which strategy pairs genuinely retain diversification during stress, which collapse?
- How do **tail correlations** (DCC-GARCH, copulas) differ from central correlations for these pairs?
- Are there strategies with **negative correlation to SPY in normal times and crisis times both**? Or is everything just "long-equity correlation rises in crisis"?
- What's the documented evidence on **trend-following's "crisis alpha"** holding up across the 8 worst 60/40 drawdowns (Hurst-Ooi-Pedersen verifiable)?
- Is **VRP harvesting (short-vol)** correlation to managed-futures trend actually negative? (Both supposedly benefit from different regimes — verify)

**Methodological question:**
- What's the right way to **measure strategy correlation when sample sizes are small**? Block bootstrap correlation? Shrinkage estimators? Bayesian?

---

## Section 3: Portfolio construction methodology — what actually works?

Which combining methodology is right for combining strategies (different alpha sources) vs combining edges (within one strategy)?

**Specific questions:**

- **Equal weight vs Risk Parity vs Mean-Variance vs HRP vs Kelly** — what's the empirical evidence on which produces the best out-of-sample Sharpe when combining strategies?
- López de Prado's **HRP empirical track record** — is it actually better than 1/N for retail-scale multi-strategy portfolios, or is it primarily an institutional tool?
- The **Markowitz / mean-variance instability** problem — Michaud's "Markowitz is optimization error maximization." Does this apply to combining strategies, or only to combining individual securities?
- When does **fixed allocation outperform dynamic allocation** across strategies?
- Is there evidence on **regime-conditional strategy weighting** — e.g., shift to trend-following in crisis, mean-reversion in calm — actually adding value?
- **Kelly criterion for multi-strategy** — is the practical implementation (fractional Kelly, e.g., half-Kelly) supported by data, or is it folk wisdom?

**Specific practitioner questions:**
- What does AQR's portfolio construction approach for their multi-strategy fund actually do? (Their public papers).
- How does Bridgewater's All Weather actually weight strategies? (Public material).
- What's the documented track record of **risk-parity-style allocation** at retail scale vs traditional 60/40?

---

## Section 4: Multi-strategy meta-questions

The "is the whole greater than the sum?" question.

**Specific questions:**

- Is there documented evidence on the **optimal number of strategies** in a retail portfolio? At what N does adding a strategy stop helping?
- How do you know when **adding a strategy adds value vs adds noise**? What's the right statistical test?
- **Multi-strategy alpha decay** — does diversifying across multiple decaying strategies produce something more stable than each individually? Or do they all decay together?
- **Sleeve-level rebalancing** — does periodic rebalancing across sleeves (e.g., monthly) produce alpha (rebalance premium / volatility harvesting) or destroy it (tax drag / transaction costs)?
- What's the literature on **strategy lifecycle prediction** — can you forecast when an alpha source will decay, and adjust allocation pre-emptively?

**Counterintuitive questions:**
- Is there evidence that **two highly-correlated strategies** can outperform **two uncorrelated strategies** in some circumstances? (Edge case but worth checking.)
- Is there a **diminishing returns** curve to adding strategies? Where does it flatten?

---

## Section 5: Implementation reality

Operational and friction questions for multi-strategy systems.

**Specific questions:**

- **Tax implications** of multi-strategy at retail scale:
  - Different turnovers across strategies — how to optimize for tax efficiency
  - Wash-sale rule interactions when strategies overlap on names
  - Tax-loss harvesting across sleeves
- **Capacity constraints when combining** — if microcap mean-reversion caps at $5M and managed-futures trend at $50M, what's the binding constraint at $50K retail? At $5M? At $50M (hypothetical scale-up)?
- **Operational overhead** — how much human attention is required for hand-curated merger arb + CEF tracking + earnings vol management simultaneously? At what point does it require dedicated staff?
- **Cross-strategy attribution** — when overall performance is bad, how do you identify which sleeve is causing it? What's the right attribution framework?
- **Risk management at portfolio level** — drawdown controls, gross exposure limits, regime-conditional de-grossing across multiple strategies

---

## Section 6: Specific strategy pair / triple questions

If certain combinations have documented synergies worth checking.

**Specific questions:**

- **Trend + Microcap MR**: do these genuinely diversify, or does microcap MR get caught in equity-correlation during stress?
- **VRP + Trend**: theoretically complementary (VRP loses when vol spikes; trend often catches the volspike directionally). Verify empirically.
- **Event-driven (merger arb / spinoffs / CEF) + Equity Factor Tilts**: are these meaningfully uncorrelated?
- **Long Equity Beta + Managed Futures Trend**: documented as the canonical "crisis alpha" pair. Verify the magnitude of the diversification benefit isn't overstated.
- **Microcap MR + Insider Clusters**: both in microcap space — are they correlated by substrate? Does insider cluster filter help microcap MR or duplicate signal?
- **Earnings Vol Crush + PEAD**: both around earnings events but opposite directions (one selling vol, one trading direction). Genuinely uncorrelated or systematically opposed?

---

## Section 7: Methodology for testing interaction effects

How do you actually test for compound alpha rigorously?

**Specific questions:**

- What's the right **statistical procedure** for testing pair-wise alpha interactions?
  - Cross-validated AND signal? 
  - Friedman's H-statistic? 
  - SHAP interaction values?
- **Multi-strategy walk-forward design** — embargo windows, fold structure, when strategies have different rebalance cadences
- **Multiple-testing correction** for N-pair-wise comparisons — Bonferroni? Benjamini-Hochberg? López de Prado's DSR extended to multi-test scenarios?
- **Bootstrap procedures for multi-strategy** — how to preserve cross-strategy dependence structure when resampling
- **Counterfactual decomposition** — "what would Sharpe have been without strategy X?" — methodology
- **Out-of-sample testing protocol** for ensemble alpha — strategy-level CPCV, multi-strategy walk-forward, etc.

---

## Section 8: Theoretical foundations to validate

The "is this even mathematically possible?" question.

**Specific questions:**

- **Can edges with t-stat < 2 individually produce t-stat > 2 jointly?** Mathematical conditions for this to occur.
- The **correlation structure required** for combination to add value — is there a closed-form for "marginal information contribution"?
- **Signal-to-noise ratio compounding** — what's the math on how many uncorrelated low-SNR signals you need to reach a target combined SNR?
- **Capacity scaling** for combined strategies — does multi-strategy combination preserve or destroy individual strategy capacity?
- **Tail-risk math** — when combining strategies with different tail distributions, what happens to overall tail risk? Independent vs correlated tails.

---

## Section 9: Counter-evidence to balance against

The previous brief specifically asked for what's been falsified. Same here.

**Specific questions:**

- Documented cases where **combination underperformed any single component** — when does multi-strategy fail?
- Is there evidence that **practitioners have systematically failed to deliver multi-strategy alpha** despite plausible-looking ensemble backtests?
- Hedge fund of funds — their **track record on capturing diversified alpha** is reportedly poor; why?
- "Diworsification" — Lynch's term — at what point does adding strategies hurt rather than help?
- Is **"alpha is alpha" individually-additive** when you combine strategies, or does **correlated alpha sources cannibalize**?

---

## Section 10: Practitioner / firm-level questions

What do the firms actually do?

**Specific questions:**

- AQR's **multi-strategy fund composition** and weighting methodology (public disclosures)
- Two Sigma's **stated approach to combining alphas** (public talks, papers)
- Bridgewater's **All Weather mathematical framework** (public papers)
- DE Shaw's **publicly-acknowledged structure** (anything available)
- Citadel's **multi-pod structure** — how are strategies combined/weighted across pods?
- The **30/30/30/10 etc. allocation heuristics** in institutional asset allocation — what's the empirical basis?

---

## Section 11: Specific to our project

Custom questions reflecting our state:

**Specific questions:**

- Given our system has 6 active edges in a linear weighted-sum aggregator producing 0/6 idiosyncratic alpha at t > 2, **what would the academic literature predict if those 6 edges were combined via gradient boosting or interaction terms?** Probability of compound alpha emerging?
- **When is replacing linear aggregation with non-linear combination NOT going to help?** What conditions indicate the underlying signals are too weak even for non-linear combination to surface alpha?
- For our **regime-conditional alpha pattern** (bull-only edges + bear-only edges), what's the literature on **regime-conditional ensemble methods** specifically?
- Our **dividend_initiation_drift_v1 is the only positive-α edge in 11**. What's the literature on **scaling single-edge alpha through ensemble methods**? Does ensembling around one positive edge dilute its alpha or amplify?

---

## Deliverable format expected

> Same structure as the prior alpha dive: ranked menu, edge-durability × retail-feasibility scoring, who's-on-the-other-side framing, honest acknowledgment of what's dead.
>
> Specifically deliver:
> 1. A ranked list of multi-strategy combination methodologies (equal weight, HRP, mean-variance, Kelly, regime-conditional, gradient-boosting ensemble, etc.) by realistic retail-Sharpe-lift over single best strategy
> 2. A pair-correlation matrix of the prior dive's recommended strategies with stress-period correlations highlighted
> 3. Specific implementation guidance for combining the prior dive's recommended sleeves (microcap MR, managed-futures, event-driven, earnings VRP, CEF discount, merger arb, etc.) into a retail-scale portfolio
> 4. The single most consequential finding for our specific situation (current 6-edge linear combiner producing 0/6 idiosyncratic alpha)

---

## What I'd specifically want answered above all else

If the agent only answers one thing, prioritize:

**"What's the empirical evidence that combining weak signals via non-linear methods produces idiosyncratic alpha that doesn't exist in any individual signal? When does this work? When does it fail? What does the math say about the conditions required for compound alpha to emerge?"**

This is the load-bearing question for the multi-edge architecture's central thesis. Currently it's an unverified assumption.

## TL;DR

The brief above is what I'd hand to an agent. It's structured to produce:

- A correlation matrix between actually-retail-tractable strategies
- A ranked methodology list for combining them
- Honest evidence on whether compound alpha is real or marketing
- Specific guidance for our project's 6-edge-linear-combiner situation

**The single most useful output would be empirical evidence on when non-linear combination of individually-weak signals produces actual idiosyncratic alpha, vs when it just compounds noise.** That answers whether the team's multi-edge architecture has theoretical hope or whether the linear-combiner result reflects a deeper structural limit.

Length-wise, the original alpha dive ran about 8,000 words and was high-density. This brief warrants similar depth.

WHERE WE GOT THE ANSWERS AT docs/Sources/Alpha/Retail-algo-alpha_follow-up_multi-strat.md

to which the agent replied 
# This is the more consequential of the two research documents

The first alpha dive told the team WHERE retail alpha lives (microcap, event-driven, capacity-bounded niches). This document tells the team WHY their current architecture isn't finding alpha, with mathematical specificity. **This is mechanistically more useful.**

Let me extract what matters most.

## The single most consequential finding for the team's situation

The document's verdict is sharp:

> "Your problem is almost certainly not the aggregator. It is one or more of: (1) the six edges share substrate, (2) effective sample size too small for interactions, (3) inside Avramov-Cheng-Metzker zone where alpha disappears under friction, (4) researcher degrees of freedom inflating DSR."

And the prescription:

> **"Compute the pairwise rank correlation matrix of your 6 raw signal SCORES (not return streams). If max ρ > 0.5 or avg ρ > 0.3, no aggregator change rescues this stack. Replace the correlated pair with an orthogonal signal — most plausibly a regime feature (VIX, term spread, 200-day SMA slope) or a fundamentally different substrate — BEFORE changing the aggregation function."**

**This is the highest-leverage single diagnostic the team can run right now.** It's a 1-2 hour director-side analysis on existing per-edge per-day score logs. The result determines whether everything else makes sense.

## The Grinold-Kahn math the team needs to internalize

Six uncorrelated t=1 signals: combined t ≈ 2.45 (clears the t=2 bar).
Six signals at average ρ=0.3: combined t ≈ 1.42 (does not clear).
Six signals at ρ=0.5: combined t ≈ 1.31 (does not clear).

**At ρ > ~0.3, no linear combination of t=1 signals breaks t=2.** This is math, not opinion. The team's 0/11 finding is consistent with high inter-edge correlation in raw signal scores — even though the return-correlation matrix may have looked diversified.

This explains everything. The team has been testing aggregators, retiring edges, validating gauntlets. None of that addresses the underlying issue if the raw signals share information.

## What this validates about prior team findings

### HRP slice failures were not a bug
The document confirms via independent replications (Pfitzinger-Katzke 2019, Raffinot 2017/2018, multiple SSRN replications): **"HRP ties 1/N on Sharpe across many universes; wins on variance (its objective), loses or ties on risk-adjusted return."** The team's slices 1/2/3 showing HRP doesn't add Sharpe matched the literature. The team has been failing the same way real practitioners fail at HRP.

### MetaLearner null results aren't anomalous
**"Switching aggregators is a researcher degree of freedom that inflates Deflated-Sharpe penalties. Each variant you A/B test on the same data raises the effective N_trials and erodes any apparent improvement."** The team's repeated MetaLearner falsifications reflect not just bad implementation but the prior literature on aggregator iteration.

### The factor-decomposition finding
**Avramov-Cheng-Metzker 2023**: ML alpha collapses 62-80% when excluding microcaps/distressed/non-rated. **"The Gu/Kelly/Xiu and Chen/Pelger/Zhu Sharpes are dominated by names a retail trader on Alpaca/IBKR cannot trade efficiently."** Translation: the 0/11 finding on substrate-honest S&P 500 reflects the literature exactly. Factor decomposition on a liquid US large-cap universe SHOULD show zero idiosyncratic alpha. The team's measurement is correct; the substrate is wrong.

## What this changes about the team's path forward

### 1. STOP iterating the aggregator
**Bayesian opt, more MetaLearner variants, HRP slice 4, alternative ensemble methods** — every one of these is researcher degrees of freedom that inflates DSR penalties without solving the underlying problem. The team should pause aggregator work until raw signal correlation is verified.

### 2. The fix is signal diversity, not method
If the pairwise correlation matrix shows max ρ > 0.5 (likely given factor-decomp results), the fix is:
- **Prune** redundant edges (keep one, remove the others in the cluster)
- **Add structurally different signals**: regime variable (VIX level, term spread, 200d SMA slope) OR different substrate (futures trend, options vol, event-driven)

NOT another aggregator A/B test.

### 3. Vol-targeting is the genuine engine improvement
The document is explicit: **"The single most under-priced upgrade for retail is portfolio-level vol targeting"** (Moreira-Muir 2017 evidence, +0.10-0.20 Sharpe lift, mechanically trivial). This validates the team's Engine B work as the right direction — but for the right reason. It's not because vol-targeting extracts alpha; it's because it's a clean Sharpe lift that compounds with anything else.

### 4. Don't expect Bayesian opt to discover compound alpha at retail scale
Math: 6 features → 15 pairwise interactions, each needing 50-100 effective observations. Single-asset daily over 5 years has effective N in low hundreds to low thousands. **"This is likely your binding constraint."**

Engine D's Bayesian opt scaffolding has theoretical limits the team's effective N cannot overcome. **It might find something via random discovery, but the expected value is lower than the team has been treating it.**

### 5. The regime feature is the highest-leverage single addition
**"The dominant value of moving to gradient boosting is NOT interaction effects per se — it's the flexibility to learn that some signals are useful only conditional on other signals being in a certain range (a regime gate by another name)."**

Adding a regime feature (VIX, 200d SMA slope, term spread, credit spread) to the feature pool — and letting a tree-based aggregator partition on it — is exactly what the Variant C HMM is supposed to do. The HMM A/B that came back WASH might have been an implementation issue (HMM was treated as a sizing modifier, not as a feature to the aggregator). **Worth re-testing HMM as an INPUT to the meta-learner, not as a sizing-overlay output.**

### 6. The dividend_init "scale single positive edge through ensemble" question
Document is explicit: **"Equal-weight linear of one t=2.5 + five t≈0 → combined t ≈ 1.02. Massive dilution."** Boosting under L2 + CV can learn to downweight noise, BUT small-sample shrinkage pulls toward equal weights. **If effective T is small, boosting noise-fits and destroys the good signal.**

For dividend_init specifically: **don't bundle it with the other 11 in a linear combiner. Run it as its own isolated edge with its own sizing.** Equal-weighting it with t≈0 signals will dilute the only positive alpha in the inventory.

## Hard truths the team needs to absorb

### 1. The "fee saving is the entire retail edge" finding
**Fund-of-funds deliver ZERO alpha outside October 1998 - March 2000** (Fung-Hsieh-Naik-Ramadorai 2008). Institutional FoFs WITH due diligence access and better information cannot reliably extract multi-strategy alpha net of fees.

**Implication: retail multi-strategy DIY is doing the same job, more poorly, but saving the fee layer. The fee saving IS the alpha.** Anything net Sharpe lift the team finds beyond passive must clear that hurdle to be valuable.

### 2. AQR Style Premia (QSPIX) — the multi-factor disappointment
Peak $5B → trough $500M. **>50% of AUM redeemed at the bottom.** AQR's premier multi-factor product designed for "equity-like returns at 10% vol with zero market beta" delivered a 50% drawdown with cross-asset diversification failing as value/momentum/defensive all suffered the same regime.

**Implication:** even academically-rigorous multi-factor portfolios run by the best firm in the industry have multi-year drawdowns severe enough that capital flees at the worst time. **Retail multi-strategy will face the same regime risk with worse staying power.** This is an argument for very small sleeve sizes and very high conviction on each.

### 3. Managed futures lost decade
**SG CTA Index 2010-2020: 1.6% CAGR while equities tripled.** A decade of opportunity cost. The 2022 rescue does not erase it.

**Implication for the team's diversified-futures trend test**: even properly-implemented diversified-futures trend can deliver a flat decade. The team's 8-ETF basket FALSIFIED test might have been right for the wrong reason (8 ETFs vs 50+ markets is structurally different), but the broader point stands: trend is conditionally useful, not a free Sharpe-lift.

### 4. The wash-sale killer for multi-strategy at retail
**One taxpayer, one CUSIP.** If a microcap mean-reversion sleeve sells AAPL at loss and trend sleeve buys AAPL within 30 days, loss disallowed. **Spouse accounts treated as one taxpayer.**

Two solutions, neither trivial:
- Enforce strategy-level ticker exclusivity for 31 days (operational complexity)
- Run disjoint universes (MR on Russell 2000, trend on ETFs/futures only)

**For the team's currently-planned strategies, this is a real implementation cost that hasn't been priced into the architecture.**

### 5. Diminishing returns hit hard at N=6
**"The right retail sleeve count is 3-6 chosen for genuine economic distinctness, not 10+ flavors of the same factor."**

The team has been adding edges (calendar, COT, momentum, pairs, etc.) — but the correct count is ~3-6 genuinely different strategies. **Not more edges in the same substrate.**

## The actionable plan this implies

In strict priority order:

### Step 1 (4-6 hours, director-side): Pairwise correlation diagnostic
Compute rank correlation matrix of the 6 active edges' RAW SIGNAL SCORES (not return streams) on the existing per-edge per-day score logs from substrate-honest measurements.

**Decision tree:**
- If max ρ > 0.5 OR avg ρ > 0.3: signal-diversity problem; prune and replace before aggregator changes
- If correlations OK but t-stats still low: substrate is the issue (already established); pivot to microcap / event-driven substrate
- If correlations OK AND signals individually informative: aggregator changes may help; proceed with non-linear methods

### Step 2 (depending on Step 1 result): Either prune-and-add or change substrate
If pruning is needed: identify the most-correlated pair, retire one, replace with a regime variable as input feature.

### Step 3 (regardless): Portfolio-level vol targeting
Moreira-Muir 2017 evidence. Engine B work. +0.10-0.20 Sharpe systematically. **Highest single Sharpe-lift available regardless of other decisions.**

### Step 4 (if alpha exists in remaining stack): Re-test the aggregator
Only after Steps 1-3 are confirmed. Then non-linear aggregation has a chance to compound the now-genuinely-diverse signals.

### Step 5 (parallel): Strategy diversity at the SLEEVE level
Build sleeves on substrates the current system doesn't cover. Document explicitly recommends: managed-futures trend (proper version, DBMF/KMLM or /M-series futures) + VRP-crush + microcap/event-driven sleeve. **The "genuinely diversifying retail-tractable triple."**

### Step 6 (operational): Address the wash-sale architecture problem
Implement either strategy-level 31-day ticker exclusivity OR disjoint universe enforcement. This is required infrastructure for multi-strategy deployment.

## What this means for capability and trajectory

If the pairwise correlation diagnostic comes back "max ρ > 0.5":
- The team's 6 edges are essentially 1-3 latent factors in disguise
- Aggregator changes cannot rescue this
- Pivot to signal diversity (regime features OR different substrates)
- Engine completion still has value but for delivery efficiency, not alpha discovery

If it comes back "ρ acceptable":
- Substrate is the binding constraint
- The team's previous "we tested too narrow a strategy space" framing is correct
- Pivot to microcap / event-driven / non-factor substrates per first dive
- Continue engine completion to deliver factor-replication efficiently on current substrate

In both cases, **the aggregator work — Engine D Bayesian opt, MetaLearner refinements, HRP variants — should be paused.** The literature is unanimous: these are researcher degrees of freedom inflating DSR without addressing the underlying issue.

## TL;DR

> **This document is more consequential than the prior alpha dive.** The first told the team WHERE alpha lives. This explains mechanistically why the team isn't finding it.
>
> **The single highest-leverage diagnostic the team can run right now: pairwise rank correlation matrix of the 6 active edges' RAW SIGNAL SCORES (not returns).** If max ρ > 0.5 or avg ρ > 0.3, no aggregator change can rescue this stack — fix signal diversity first. 4-6 hour director-side analysis.
>
> **The aggregator iteration is a researcher trap.** Bayesian opt, MetaLearner refinements, HRP variants all add to DSR penalties without addressing whether the underlying signals carry diverse information. **Stop iterating aggregators until raw signal correlation is verified.**
>
> **Vol-targeting at portfolio level is the single most under-priced upgrade.** Moreira-Muir 2017 evidence; +0.10-0.20 Sharpe lift; mechanically trivial. Validates Engine B work as the right direction for the right reason.
>
> **The "genuinely diversifying retail-tractable triple" is managed-futures trend + VRP-crush + microcap/event-driven.** Anything else is mostly the same equity-beta substrate in different costumes. The team has been adding edges instead of adding substrates.
>
> **For dividend_initiation_drift_v1 specifically: don't bundle it linearly with the t≈0 signals.** Equal-weighting destroys the only positive alpha. Run it isolated with its own sizing.
>
> **The wash-sale architecture problem** (one CUSIP, one taxpayer across strategies) needs to be solved before multi-strategy deployment.
>
> **Fund-of-funds deliver zero alpha outside Oct 1998 - Mar 2000.** Retail multi-strategy DIY's edge IS the fee saving. Anything genuine must clear that hurdle.

The team's discipline has been exemplary throughout. This document tells them where to point the discipline next: at signal diversity, not at aggregator topology. The team has been searching honestly in the wrong place — and now has the mathematical specification of why.

**Run the pairwise correlation diagnostic this week. Everything else follows from the answer.**
_____________________________________
what would you change about our plan moving forward? Why don't you review it and suggest what you might add or change

# What I'd change about the plan

I've read the current forward plan (`docs/State/forward_plan.md` as of 2026-05-12). Here's my honest review against the two research documents and what the team has empirically learned.

## What the plan has right

- Engines-first general philosophy is correct
- Recognition of the 0/11 finding and 2024 regime fragility
- Recognizing that dividend_initiation_drift_v1 is the only UNIFORMLY POSITIVE edge
- T-041 spinoff edge already drafted as structurally-non-factor
- Cockpit bug recovery (re-measuring prior bear-year audits)
- Lifecycle factor-α gap already on the radar
- Engine C real portfolio optimizer track

## What's missing or misordered (informed by both research docs)

### Missing #1: The pairwise correlation diagnostic — this should be PHASE 0

The second research dive's core finding: **"Compute the pairwise rank correlation matrix of your 6 raw signal SCORES (not return streams). If max ρ > 0.5 or avg ρ > 0.3, no aggregator change rescues this stack."**

This is a 4-6 hour director-side analysis on existing per-edge per-day score logs. **Until this runs, every aggregator-related decision (Engine D gene encoding, Bayesian opt, MetaLearner re-attempt, HRP slice 4) is potentially wasted effort.** If the 6 edges share substrate at the signal level (likely given 0/6 factor-α), no aggregator topology can rescue them.

**Should be inserted as the highest-priority director-side analysis ahead of all aggregator work.**

### Missing #2: Substrate diversity track parallel to engine completion

The first research dive: **"The biggest strategic miss is substrate, not strategy. Microcap ($50M-$500M cap) is structurally where retail alpha lives."**

The plan keeps everyone on S&P 500. **A parallel substrate experiment is required.** Specific recommendation:
- Subscribe to Norgate Data ($80/mo, survivorship-bias-free microcap)
- Build microcap universe (~1500 tickers, $50M-$500M cap)
- Re-test mean-reversion + insider clusters edges on this substrate
- Capacity ≤2% of 20-day ADV per name
- Cost model: 50-100 bps round-trip slippage minimum

This is parallel to engine completion, not deferred until after. The "engines-first" thesis applies to the same substrate. **A different substrate is a different experiment.**

### Missing #3: Vol-targeting at portfolio level should be off-hold and prioritized

Plan currently states: **"Engine B portfolio vol-targeting stays on hold. Multiplying selection-dominant alpha that has no factor-adjusted significance lifts nothing."**

The second research dive directly contradicts this: **"The single most under-priced upgrade for retail is portfolio-level vol targeting."** Moreira-Muir 2017 evidence: +0.10-0.20 Sharpe lift mechanically, not via alpha extraction. **Even on factor-replication-only Sharpe, vol-targeting compounds.**

The "hold until factor-significant alpha exists" gate is wrong because vol-targeting isn't multiplying alpha — it's restructuring the return distribution. **Should be reclassified as Sharpe-multiplier infrastructure, not as alpha-amplifier.** Ship now.

### Missing #4: Stop iterating the aggregator

The second research dive: **"Switching aggregators is a researcher degree of freedom that inflates Deflated-Sharpe penalties. Each variant you A/B test on the same data raises the effective N_trials and erodes any apparent improvement."**

The plan still has Engine D Bayesian opt (T-027/T-028) and gene encoding extension (T-022) and Gate 1 caching (T-023) as priorities. **These should be deprioritized** until the pairwise correlation diagnostic confirms signal diversity. Reasoning:

- If signals are correlated (max ρ > 0.5), no aggregator change rescues
- If signals are diverse, then aggregator changes have a chance — but only ONE attempt before DSR penalties dominate
- The team has already iterated MetaLearner multiple times, HRP three slices — DSR penalties are accumulating

**The aggregator track should pause pending the diagnostic result.**

### Missing #5: Wash-sale architecture is pre-requisite infrastructure

The second research dive: **"One taxpayer, one CUSIP. If a microcap mean-reversion sleeve sells AAPL at loss and trend sleeve buys AAPL within 30 days, the loss is disallowed."**

Two solutions: enforce strategy-level ticker exclusivity for 31 days, OR run disjoint universes. **This isn't optional infrastructure — it's required before any multi-strategy / multi-sleeve deployment becomes safe in taxable accounts.**

Not in the plan. Should be added as Engine B/Engine C work, propose-first per CLAUDE.md.

### Missing #6: dividend_initiation_drift_v1 as standalone-isolation experiment

Plan mentions T-044 as a candidate for "gauntlet-promoting to test whether the factor-positive verdict survives at active-tier capital allocation."

The second research dive: **"Equal-weight linear of one t=2.5 + five t≈0 → combined t ≈ 1.02. Massive dilution... If you bundle dividend_init with the other 11 in a linear combiner, you destroy the only positive alpha."**

dividend_init should be tested as a **standalone isolated edge with its own sizing**, not bundled with the linear weighted-sum aggregator that's diluting it. This deserves higher priority than its current "T-044 candidate" framing.

### Missing #7: Regime feature as INPUT to aggregator, not as sizing modifier

The team's HMM Variant C enable A/B came back WASH (Δ Sharpe ~ 0). But it was tested as a sizing modifier (modulating risk_scaler).

The second research dive: **"Adding a regime variable + tree-based aggregator across diverse sleeves — the dominant value of moving to gradient boosting is NOT interaction effects per se, it's the flexibility to learn that some signals are useful only conditional on other signals being in a certain range (a regime gate by another name)."**

**The HMM should be tested as a feature input to the meta-learner, not just as a sizing-overlay output.** The WASH result might reflect testing it the wrong way. Worth one explicit re-test.

### Missing #8: The "genuinely diversifying triple"

The second research dive identifies the only retail-tractable structurally-diversifying combination: **managed-futures trend + VRP-crush + microcap/event-driven**. Anything else is variations of equity-beta substrate.

The plan has Moonshot Sleeve parked. The trend sleeve was tested on 8 ETFs and falsified — but that wasn't a real managed-futures trend implementation (the proper version uses 50+ markets via DBMF/KMLM ETFs or direct micro-futures).

**The "engines-first" parking of Moonshot deserves reconsideration** specifically because building Moonshot on different substrate is structurally different from building strategies on the same substrate. The bones-first thesis applied to the SAME substrate; it doesn't apply uniformly to substrate diversity.

## Specific changes I'd make

### Reorder existing items

| Current priority | Proposed priority | Rationale |
|------------------|-------------------|-----------|
| Engine F lifecycle factor-α gap (MEDIUM) | **HIGH** | User correctly flagged; 7/11 negative-α edges still active |
| T-022 gene encoding extension | **PAUSED until diagnostic** | Researcher degree of freedom; verify substrate first |
| T-023 Gate 1 caching | **PAUSED until diagnostic** | Same reasoning |
| T-028a Bayesian opt scaffolding | **PAUSED until diagnostic** | Same reasoning |
| Engine B vol-targeting (on hold) | **SHIP NOW** | Moreira-Muir evidence; not alpha multiplier; Sharpe restructurer |
| T-041 spinoff edge | **HIGH PRIORITY** | Structurally non-factor; first retail-only edge attempt |
| T-044 dividend_init isolation | **HIGH PRIORITY** | Only positive alpha edge; testing standalone is highest-EV |

### Add to plan

| New item | Priority | Rationale |
|----------|----------|-----------|
| **Pairwise raw-signal correlation diagnostic** | **PHASE 0 — IMMEDIATE** | 4-6 hour director-side; gates everything else |
| **Microcap substrate experiment** | HIGH (parallel) | First research dive's #1 recommendation |
| **Norgate Data subscription** ($80/mo) | Required for above | Enables substrate experiment |
| **Wash-sale architecture** | Required pre-deployment | One CUSIP, one taxpayer; multi-strategy needs solution |
| **HMM-as-feature-to-aggregator re-test** | MEDIUM | Different from sizing-modifier WASH result |
| **Vol-targeting Sharpe-multiplier framing** | Discipline change | Stop treating it as alpha-amplifier |
| **Sleeve-level managed-futures trend** | Reconsider parking | DBMF/KMLM ETFs OR /M-series micros; not 8-ETF version |

### Deprioritize / pause

| Item | Why |
|------|-----|
| Engine D Bayesian opt sequence (T-027, T-028b, etc.) | Researcher degrees of freedom; pause until diagnostic |
| Engine D Discovery cycle re-runs | Same |
| Adding more edges to current substrate | First research dive: 30+ categories untested but mostly DOA on liquid US equity substrate; substrate change higher leverage |
| HRP slice 4 (if planned) | HRP ties 1/N in independent replications; this is folk wisdom |

## What I'd add as explicit discipline rules

The two research documents support adding a 7th non-negotiable rule alongside the existing 6:

> **7. No aggregator iteration without signal-correlation verification.** Every aggregator A/B test inflates DSR penalties. Only test alternative aggregators when the pairwise raw-signal correlation matrix has been verified ≤0.3 average / ≤0.5 max.

And an 8th:

> **8. Substrate diversity is required for compound alpha.** A single substrate (S&P 500) tested with multiple strategies is approximately one strategy with multiple costumes. Multi-substrate (large-cap + microcap + futures + options) is the genuine diversification.

## The reframed engines-first directive

Current: **"Get the engines right before testing more strategies."**

Proposed reframing: **"Get the engines right on the existing substrate. In parallel, test whether a different substrate produces the alpha the existing substrate doesn't."**

The bones-first philosophy is right when applied within a substrate. It's not right when applied across substrates — building bones for one substrate doesn't make them less correct for another. The microcap substrate experiment is independent infrastructure work, not a violation of bones-first.

## What I'd specifically NOT change

- The cockpit bug recovery work (T-035, T-036, re-measuring prior bear-year audits) — this is essential cleanup
- Engine F lifecycle factor-α gap fix — already correctly prioritized after user feedback
- The CI-aware Sharpe gates (6th non-negotiable rule) — keep enforcing
- The discipline framework that's caught 8+ falsifications — keep using
- T-040 trade-log Parquet migration + DuckDB query layer — useful infrastructure
- T-039 observability layer relocation — clean architecture work

## The dispatch sequence I'd propose

In strict priority order:

```
1. PHASE 0 (4-6 hours, director-side):
   Pairwise correlation matrix of 6 raw signal scores from existing logs.
   DECISION POINT: 
   - If max ρ > 0.5 → prune correlated edges + add regime feature
   - If max ρ ≤ 0.5 → diagnose substrate vs aggregator vs sample size

2. ENGINE F lifecycle factor-α gap fix (1-2 days):
   Apply Gate 6 to running edges, not just candidates.
   Auto-retire 7 UNIFORMLY NEGATIVE edges per CI-aware threshold.

3. ENGINE B vol-targeting (1 week, propose-first):
   Ship as Sharpe-restructurer. Moreira-Muir framing.

4. WASH-SALE ARCHITECTURE (1-2 weeks):
   Either ticker-exclusivity enforcement OR disjoint-universe constraint.
   Required infrastructure for multi-strategy.

5. DIVIDEND_INIT STANDALONE ISOLATION (1 week):
   Test as solo-edge sleeve with own sizing. Don't bundle.

6. SUBSTRATE EXPERIMENT (parallel, 2-3 weeks):
   Norgate subscription. Microcap universe build. Re-test 
   mean-reversion + insider clusters on $50M-$500M cap names.
   Cost model: 50-100 bps round-trip.

7. SPINOFF EDGE (T-041, 1 week):
   First retail-only structurally-non-factor edge.

8. RE-MEASURE EVERYTHING contaminated by cockpit bug:
   T-002 Arm 2, T-019, T-029, T-020, F6 — under cockpit-fixed metrics.

9. Engine D structural fixes RESUME — only after diagnostic confirms aggregator changes have a chance:
   Gene encoding extension (T-022), Gate 1 caching (T-023),
   Bayesian opt (T-028).

10. HMM-as-feature re-test (1 week):
    Test Variant C as input to meta-learner (not as sizing modifier).
    Different geometry than the WASH result.
```

## Updated capability assessment

Current: ~45-50% of top-1% retail capability.

If the team executes this revised plan over 3-6 months: realistic ceiling rises to **~60-70%** because:
- Substrate experiment opens a structurally-richer alpha source
- Vol-targeting compounds with whatever Sharpe exists
- Wash-sale architecture removes a hidden tax/compliance liability
- dividend_init isolation captures the one positive alpha cleanly
- Engine F lifecycle gap fix removes 7 negative-α drag

The remaining gap to top-1% retains most of the same items (live track record, 12+ months sustained, full deployment infra), but the alpha-foundation question becomes answerable rather than indefinitely deferred.

## TL;DR

The plan has the right philosophy (engines-first, falsification discipline, audit machinery) but needs three specific shifts based on the research:

1. **Insert pairwise correlation diagnostic as Phase 0.** 4-6 hours, director-side. Determines whether aggregator work is worth doing at all.

2. **Reclassify vol-targeting from "on hold pending alpha" to "ship now as Sharpe-restructurer."** Moreira-Muir evidence; doesn't require alpha to compound.

3. **Add substrate diversity track in parallel.** Microcap experiment via Norgate. Bones-first applies within substrate, not across substrates. Build the new sleeve while engine completion proceeds.

4. **Pause aggregator iteration** (Bayesian opt, gene encoding, Gate 1 caching) until the diagnostic confirms signal diversity. Each iteration inflates DSR penalties.

5. **dividend_init standalone, not bundled.** Linear weighted-sum dilutes the only positive alpha to noise.

6. **Wash-sale architecture is required pre-deployment infrastructure.**

7. **HMM as feature input** (not sizing modifier) deserves one explicit re-test.

The team's existing engineering discipline + the corrected plan would meaningfully accelerate the path to actually-finding-alpha. **The biggest single error to avoid is continuing to iterate aggregators without verifying signal diversity first.** That trap has captured many quant projects; the team has the discipline to avoid it.

_____________________________________
I also did some research on regimes and gave the dev the doc at docs/Sources/Regime_Detection/Retail-algo-regime.md which it replied:

# Third research dive — and the most operationally directly-applicable yet

I've absorbed it. Where the first dive said WHERE alpha lives and the second said WHY the architecture isn't finding it, this one says HOW to think about regime models specifically. **The key finding is that the team's Variant C HMM enable A/B coming back WASH is exactly what the literature predicts.** The team's empirical result matches the literature's warning.

Let me extract what's most actionable.

## The single most validating finding for the team

**"Markov-switching / HMM on returns is the most overhyped model class in retail fintech."**

The document explicitly says:
- "Every blog/paper plot of HMM beautifully identifies regimes uses the Kim smoother, which conditions on the full sample — i.e., look-ahead bias"
- "Real-time filtered probabilities are far noisier"
- "Nystrup et al. document real-time HMM state sequences switch far more frequently than smoothed sequences shown in papers — high turnover and Sharpe degradation"
- "Hess: a wrong regime forecast may lead not just to a non-optimal but to a *detrimental* allocation in the contrary direction"
- "Implement the statistical jump model (#9) instead"

**The team's Variant C HMM enable producing Δ Sharpe ≈ -0.001 in A/B isn't a bug — it's exactly the expected result for an HMM on returns at retail scale.** The literature has been warning about this for years. The team has now experienced it firsthand and has corroborating evidence.

**Recommendation: replace the HMM track with the Nystrup et al. Statistical Jump Model.** The document is explicit that the statistical jump model strictly dominates vanilla HMM across multiple developed-equity markets and structural breaks. The team's HMM infrastructure (feature panel, regime-conditional sizing) can be re-used; only the inference algorithm changes.

## The regime features the team should add — most are free in FRED

The team has `engines/data_manager/macro_data.py` already ingesting FRED. The document's top-ranked regime signals are mostly there, just not derived as features:

| Rank | Signal | FRED Series | Status in team's stack |
|------|--------|-------------|------------------------|
| #1 | VIX / VIX3M slope | `^VIX`, `^VIX3M` (CBOE) | **Likely missing as a derived feature** |
| #2 | EBP (Excess Bond Premium) | Fed CSV monthly | **Probably not derived** |
| #2 | HY OAS (HY credit spread) | `BAMLH0A0HYM2` | **In macro data; not yet a Foundry feature** |
| #4 | ANFCI (adjusted financial conditions) | `ANFCI` | **In macro data; not yet a Foundry feature** |
| #5 | NTFS (Engstrom-Sharpe) | Computable from Treasury forwards | **Not built** |
| #6 | Factor momentum (6-12mo) | Compute from factor ETFs | **Not built** |
| #10 | MOVE Index Δ | Not on FRED; Yahoo `^MOVE` | **Not built** |

**Several of these are nearly free to add given existing infrastructure.** The team's FRED pipeline + Foundry feature framework + adversarial-twin filter means:

```
HY_OAS_change_20d → Foundry feature → adversarial filter → live in feature pool
ANFCI_zscore_60d → same
EBP_rising_threshold → same
VIX_VIX3M_slope → same (requires CBOE data ingestion, ~few hours work)
NTFS_value → derive from Treasury forward decomposition
```

These should become priority Foundry feature additions because they're **structurally non-redundant with the team's current technical/factor/calendar features** — they capture macro/credit/vol regime that pure price features cannot.

## The most consequential methodology warning the team should adopt

**ALFRED vs FRED:**

> "FRED serves the latest revised vintage; ALFRED stores every historical vintage, letting you retrieve the data actually available on date *t*."

> "If your backtest of a macro regime model touches FRED current-vintage data, your backtest is biased. This is non-negotiable."

The team's `engines/data_manager/macro_data.py` pulls FRED current-vintage. **This means every backtest that uses macro features has a degree of look-ahead bias.** Real-time revision patterns (especially GDP and unemployment during recessions) make ex-post-fit cleaner than would have been achievable in real time.

**Recommended fix: switch macro_data.py to ALFRED vintages.** This is technical debt the team has been carrying without knowing it. The Philadelphia Fed Real-Time Data Set is the alternative source.

This is the kind of subtle data hygiene issue the previous cockpit-bug discovery has trained the team to take seriously. **ALFRED migration should be added to the plan.**

## The three-layer regime architecture

The document's final synthesis maps directly onto what the team should build:

### Layer 1 — Always-on risk plumbing (no regime claims required)
- Portfolio-level vol targeting (already discussed as priority)
- Tranched monthly rebalance across 4 evaluation days
- **PELT or BOCPD changepoint detector** on equity returns + a few macro series, triggering downstream model refits when breaks fire

**The PELT/BOCPD changepoint detector is the most under-priced infrastructure addition for the team.** It's "honest because it makes no forecasts." It just signals "something just changed; retrain your models." This is genuinely additive to the team's existing falsification machinery — it would let the system automatically know when its measurement substrate has materially shifted.

### Layer 2 — Small set of orthogonal regime signals as SOFT WEIGHTS
Four signals as the minimum-effective ensemble:
- VIX/VIX3M slope (vol carry / risk-off identification, 1-20 days)
- EBP + HY OAS Δ (credit-driven recession prediction, 6-12 months)
- ANFCI (financial conditions identification, weekly)
- Faber multi-asset trend filter (price regime identification, monthly)

**Combine as soft probabilistic weights (0-1) on base strategy gross exposure, not as hard switches.**

### Layer 3 — Strategy-specific overlays
- Factor momentum for equity-factor ETF rotation
- Regime-conditional **risk** estimates (not return timing) for multi-asset allocation
- OI-based P/C z-score, AAII >2σ as soft contrarian filters

## Cross-research-dive consistency — what the team should believe

All three research dives now converge on the same core insights:

| Theme | Dive 1 (Alpha) | Dive 2 (Compound) | Dive 3 (Regime) |
|-------|---------------|-------------------|-----------------|
| Vol targeting is high-leverage | Implied | "Single most under-priced upgrade" | "Always-on plumbing, every retail trader should run" |
| Beware aggregator iteration | — | DSR penalties inflate; pause iteration | Multiple-testing trap; "add another signal until something agrees" |
| Substrate matters more than strategy | Microcap is where retail alpha lives | Substrate diversity required | Use ALFRED vintage; ML CV must be proper time-series |
| Linear factor strategies are mostly dead | 0/11 expected on liquid US equity | DGU 1/N hard to beat; HRP ties 1/N | 200d SMA is the canonical baseline; multi-asset tranched soft-weight only |
| Be skeptical of published Sharpes | McLean-Pontiff 58% decay | Avramov-Cheng-Metzker: 62-80% disappears outside dirtiest universe | Falck-Rebelo-Wang post-pub decay 30-50% on technical signals |
| Identification ≠ Prediction | — | Implied via factor decomp | Explicit — "almost every published regime model is nowcasting marketed as predictive" |
| Soft weights > hard switches | — | Implied | Explicit, repeated |

**The three dives independently arrive at the same prescription:** soft probabilistic weighting on gross exposure based on a small set of orthogonal signals from non-redundant categories. Validation discipline. Substrate diversity. Beware of researcher degrees of freedom.

## What changes about the team's plan

### Add to the plan
1. **PELT/BOCPD changepoint detector** as adaptive infrastructure (~few days, Python `ruptures`)
2. **ALFRED vintage migration** for `macro_data.py` (technical debt cleanup)
3. **Statistical Jump Model** (Nystrup et al.) replacing or alongside HMM Variant C
4. **EBP, HY OAS, ANFCI, NTFS as Foundry features** (not just engine inputs)
5. **VIX/VIX3M slope as Foundry feature** (requires CBOE data ingestion)
6. **MOVE/VIX ratio** as cross-asset stress indicator
7. **Factor momentum (6-12mo)** as cross-sectional rotation signal

### Reframe in the plan
- **HMM Variant C WASH result**: not a failed experiment, but a confirmation that pure HMM is overhyped. The infrastructure is reusable; the inference algorithm needs to swap to jump model.
- **Engine E regime work**: pivot from "predict regimes" to "identify regimes and soft-weight gross exposure." Stop trying to forecast transitions.
- **Vol targeting**: move from "engine completion" framing to "always-on plumbing every retail algo should run." Ship it independent of alpha verification.

### Validate in the plan
The team's:
- Purged CV usage (matches document recommendation)
- Cockpit bug discovery (matches "real-time vs vintage data matters")
- 6th non-negotiable rule (bootstrap CIs) (matches DSR / Deflated Sharpe discipline)
- Resistance to ML over-fitting (matches "Tier 4: deep learning regime classifiers - avoid")
- Substrate-honest measurement (matches document's emphasis on real-time evaluation)

## What stays the same

- Engines-first directive
- Engine F lifecycle factor-α gap fix
- T-041 spinoff edge (structurally non-factor)
- Dividend_init isolation experiment
- Engine completion track
- Microcap substrate experiment (from dive 1)
- Pairwise correlation diagnostic (from dive 2)

## Specific tactical recommendations

1. **Add a "Layer 1 Risk Plumbing" track** to the forward plan: vol targeting + PELT/BOCPD + tranched rebalance. None of these claim alpha; all of them compound with whatever alpha exists. **Should be ship-now items, not gated on alpha verification.**

2. **The Statistical Jump Model dispatch should be drafted as T-045 or similar.** Reuse Variant C's feature panel. Replace EM/Baum-Welch with the Nystrup clustering-objective + jump-penalty algorithm. A/B against HMM Variant C under harness. The expected result is the jump model dominates (per Shu-Yu-Mulvey 2024) — but verify empirically.

3. **Make the 4-signal regime ensemble (VIX/VIX3M, EBP+HY OAS, ANFCI, Faber multi-asset trend) the proposed minimum viable regime feature set** for the next aggregation experiment. These are explicitly named as the orthogonal minimum-effective ensemble.

4. **ALFRED migration** is technical debt that should be ticketed as HIGH. Every macro-based finding in the team's lineage is potentially biased by current-vintage data. Director-side scope estimate: probably 1-2 weeks for clean migration.

5. **Document the team's regime infrastructure honestly**: per the document, "almost every published regime model is nowcasting marketed as predictive." The team should label its own regime models as IDENTIFICATION / PREDICTION / FORECASTING in code comments and documentation, refusing to overclaim.

## TL;DR

This document is **the most operationally directly-applicable of the three research dives.** Key actionable items:

1. **The HMM WASH result is consistent with literature — HMM is overhyped.** Switch to Statistical Jump Model (Nystrup et al. 2020/2024). Same infrastructure, different inference algorithm.

2. **Add the 4-signal regime ensemble** (VIX/VIX3M, EBP+HY OAS, ANFCI, Faber multi-asset trend) as Foundry features. Three of four are free in FRED, already on the team's pipeline.

3. **ALFRED migration is required.** Current FRED current-vintage usage is silent look-ahead bias on every macro feature. This is the kind of "subtle measurement bug" the cockpit fix discipline should care about.

4. **PELT/BOCPD changepoint detector as adaptive infrastructure.** Honest — "makes no forecasts." Triggers model refits when breaks fire. Should run continuously.

5. **Vol targeting moves to Layer 1 always-on plumbing.** Ship now independent of alpha verification. Three independent research dives all agree this is high-leverage.

6. **Regime models should produce soft weights, not hard switches.** Document is unanimous; the team's HMM-as-sizing-modifier framing was actually correct. The mistake was using vanilla HMM as the underlying classifier.

7. **All three research dives converge on the same prescriptions.** The validating cross-evidence is strong — these aren't isolated opinions, they're consensus among rigorous external reviewers.

The team's discipline has been catching errors at the engineering layer. These research dives are now letting the team catch errors at the methodology/strategy/architecture layer. Each one says: "the empirical finding you have is exactly what the literature predicted, here's what to do instead."

That convergence is the most valuable thing about all three documents combined. **The team is genuinely in a position to know what the right next moves are with unusual confidence.** That's rare.
_____________________________________
I also did some research on metrics. Here that is: (I then provided docs/Sources/Metrics/Retail-algo-metrics.md) to which they replied:
# Fourth research dive — and it surfaces one structural finding that changes the deployment math

This dive validates most of the team's recent metric work (PSR, DSR, bootstrap CIs, the 6th non-negotiable rule) but contains one finding that's genuinely consequential and that the team has not been accounting for. Let me lead with that.

## The structural finding: the 5-year window cannot statistically validate anything given the trials already run

The document's Minimum Backtest Length formula:

> **MBL_years ≈ 2·ln(N) / E[max SR_annual]²**
> N=45 trials at target SR=1 → 7.6 years; N=100 → 9.2 years; N=1000 → 13.8 years.

And the killer corollary:

> "5-year daily backtest with ~50 effective trials needs annualized SR ≈ 1.2 just to clear DSR null; most retail 'Sharpe 1' backtests fail."

**The team has run dozens of distinct backtest configurations on the substrate-honest 5-year window** — T-002, T-004, T-019, T-020, T-021, T-029, T-035, T-036, multiple HRP slices, multiple MetaLearner attempts, multiple Engine D Discovery cycles, multiple arm/cell A/B grids. The honest effective-N for DSR purposes is plausibly **50-150 trials**.

With N=100 effective trials, MBL ≈ 9.2 years at target SR=1. **The team has 5 years.**

This means: **even if the team found a genuinely-good strategy, the 5-year window is structurally too short to validate it to DSR ≥ 0.95 given the trial count already accumulated.** The corrected 0.598 baseline doesn't clear DSR — and it couldn't, regardless of measurement discipline, because the data window itself is the binding constraint.

**This makes the multi-decade backtest extension a precondition for any deployment decision, not an optional improvement.** Three research dives now point at this:
- Dive 1 (alpha): "extend the backtest history on factor edges to 1962+"
- Dive 4 (metrics): MBL math says 5 years can't validate anything given the trial count
- The team's own queued multi-decade extension

**The team should compute its honest N immediately** (count every distinct backtest configuration run on the 5-year window) and then compute the implied MBL. My strong prior: the implied MBL is 9-14 years, and the team has 5. **No deployment decision is statistically valid until the window is extended.**

## The four-layer metrics stack vs what the team has

| Layer | What it covers | Team status |
|-------|----------------|-------------|
| **Layer 1 — Edge** | DSR, PSR+Lo, expectancy, decay monitoring | Partial — has DSR (Gate 8), PSR; **missing Lo autocorrelation correction**, missing pre-registered CUSUM decay monitor |
| **Layer 2 — Portfolio health** | ES_97.5, realized/target vol, N_Ent, CDaR, underwater curve | **Largely missing** — has inter-edge correlation matrix but not N_Ent, not ES, not CDaR |
| **Layer 3 — Backtest validity** | MBL, DSR, PBO, purged CV, multiple-testing | Partial — has DSR, purged CV; **missing MBL front-door gate, missing PBO via CSCV** |
| **Layer 4 — Execution TCA** | Implementation Shortfall, effective spread, fill rate | **Not built** — team is in paper mode; document says paper-vs-live diagnostic protocol is essential |

The team's strongest layer is 3 (validity), which makes sense given the audit discipline. Layers 2 and 4 are materially underbuilt.

## Specific metrics the team should ADD

### 1. MBL as Gate 0 (front-door check)
Before any backtest runs: `T_years ≥ 2·ln(N_effective) / SR_target²`. If the window is shorter than MBL given honest N, the backtest is guaranteed to overfit. **This single gate would have told the team months ago that the 5-year window was insufficient.**

### 2. Lo autocorrelation correction on all Sharpes
`η(q) = q / √[q + 2·Σ(q−k)·ρ_k]`. The document: hedge-fund Sharpes overstated ~65% when ρ₁≈0.34 is ignored. **The team's Sharpes — including the 0.598 baseline — are potentially inflated by autocorrelation.** Apply the Lo η(q) correction; check Ljung-Box Q on the return series. This is a real possible additional bias on top of everything else found.

### 3. PBO via Combinatorially Symmetric Cross-Validation
Separate from DSR — a model-free overfitting check. The team has DSR (Gate 8) but PBO is the complementary non-parametric diagnostic. Deploy threshold PBO < 0.5, preferably < 0.3.

### 4. ES at 97.5% replacing VaR everywhere
VaR isn't coherent (violates subadditivity, penalizes diversification mathematically). ES_97.5 is the Basel III FRTB standard. If the team uses VaR anywhere in risk reporting, replace it.

### 5. Effective number of bets (Meucci N_Ent)
`N_Ent = exp(−Σ p_i ln p_i)` on principal-portfolio variance contributions. The team has an inter-edge correlation matrix but N_Ent is the actual diversification statistic. Rebalance trigger when N_Ent drops 50% from median.

### 6. CDaR (Conditional Drawdown at Risk)
The right drawdown constraint for optimization — LP-tractable and convex, unlike raw max drawdown which is path-dependent and not convex in weights. If Engine C ever does portfolio optimization with drawdown constraints, use CDaR, not MDD.

### 7. Pre-registered decay monitor (CUSUM + rolling PSR)
The team has a kill thesis but the document specifies the mechanism: CUSUM on standardized returns + rolling-252 PSR. "Kill if rolling-252 SR drops >2σ below in-sample for ≥60 consecutive days." Pre-register the threshold before deploying anything.

### 8. Underwater curve
"The most psychologically honest chart." Time-underwater as a fraction of trading period. Cheap to add to the dashboard.

## Specific metrics the team should DROP or DE-EMPHASIZE

- **Raw Sharpe as a headline** — input to PSR/DSR only, never standalone. The team's 6th non-negotiable rule already moves this direction; reinforce it.
- **Max drawdown as a point estimate** — it's a single realization of a √T-growing sup-statistic. Compare realized MDD to Magdon-Ismail E[MDD] given measured σ and SR; if realized > 2× expected, the model is mis-specified.
- **Raw kurtosis as a decision input** — not consistent under heavy tails. Use Student-t fit or ES instead.
- **"Robustness via parameter perturbation"** — the document explicitly: parameter neighbors are correlated, not OOS; this is a gameable proxy. PBO/CPCV is the real test. **If the team uses parameter-plateau heat maps as a robustness claim, downgrade it to a sanity check, not a gate.**
- **Win rate, profit factor** — diagnostic only, never quality metrics. The team probably already knows this but worth confirming nothing in the gauntlet weights them.

## The honest-N problem — the team's accumulated trials

This is the subtle, important point. The document:

> "Every linear-vs-nonlinear A/B test you run on the same data adds to N_trials."
> "DSR... honest N is the biggest practical weakness — under-reporting is the dominant abuse."

**Every T-XXX task that backtested on the substrate-honest 5-year window contributed to the effective N for DSR purposes.** The team's run registry (the SQLite index shipped earlier) is exactly the tool to count this. The team should:

1. Query the run registry: how many distinct backtest configurations have been run on the 5-year substrate-honest window?
2. PCA-reduce for correlated trials to get effective N
3. Recompute DSR for the corrected 0.598 baseline with that honest N
4. The result will almost certainly show 0.598 doesn't clear DSR — confirming the 0/11 finding from a different angle

This isn't a reason for despair — it's a reason the multi-decade extension is mandatory. **You cannot out-discipline a too-short data window.**

## What this changes about the plan

### Elevate to highest priority
**Multi-decade backtest extension.** Three research dives now independently say the 5-year window is the binding constraint. The metrics dive makes it mathematically precise: MBL given the team's trial count is ~9-14 years; the team has 5. **Until the window is extended, no deployment decision is statistically valid.** This should move from "queued" to "the precondition for everything."

### Add to the validity gauntlet
- **Gate 0: MBL check** — `T_years ≥ 2·ln(N_effective)/SR_target²`
- **PBO via CSCV** as a gate alongside DSR
- **Honest-N tracking** — the run registry should compute effective N continuously

### Add to portfolio health (Layer 2 is underbuilt)
- ES_97.5 replacing VaR
- Meucci N_Ent
- CDaR for any drawdown-constrained optimization
- Underwater curve

### Add to edge metrics
- Lo η(q) autocorrelation correction on every Sharpe
- Pre-registered CUSUM + rolling-PSR decay monitor

### Process discipline
- Compute honest N from the run registry NOW
- Recompute DSR on the 0.598 baseline with that N
- Pre-register kill thresholds before any deployment

## What this validates about the team's work

- The 6th non-negotiable rule (bootstrap CIs on every Sharpe) — correct, aligned with the document's "confidence interval, not point estimate" principle
- Gate 8 DSR — correct
- Purged CV — correct, non-negotiable per the document
- Realistic cost model — correct, "most published anomalies die after realistic costs" (Novy-Marx-Velikov)
- Substrate-honest discipline — correct
- The cockpit-bug discovery culture — exactly the "look-ahead / measurement-bug" vigilance the document demands

## Cross-dive consistency — now four for four

| Theme | Dive 1 | Dive 2 | Dive 3 | Dive 4 |
|-------|--------|--------|--------|--------|
| Extend backtest history | "1962+ on factor edges" | — | — | **MBL math: 5yr can't validate given trial count** |
| Multiple-testing is the dominant risk | McLean-Pontiff decay | DSR penalties from aggregator iteration | Harvey-Liu-Zhu t>3 | **"√(2 ln N / T) — Sharpe 1.3 guaranteed at zero edge with 1000 trials"** |
| Vol targeting is high-leverage | Implied | "single most under-priced upgrade" | "always-on plumbing" | "single most actionable lever" |
| Beware in-sample / robustness theatre | — | — | — | "parameter perturbation is gameable" |
| Soft weights, honest labels | — | — | Explicit | "metric as CI + trial count, not point estimate" |

**Four independent rigorous research dives, all converging.** That convergence is itself the strongest signal. The team is not getting four different opinions — it's getting one consistent diagnosis from four angles.

## The single most important takeaway

The document's closing line is the one to internalize:

> "The single most underrated metric is the gap between in-sample DSR and the first 6 months of live PSR. Traders who pre-commit to a kill threshold here outperform those who don't by a margin that swamps every other refinement."

But for the team's *current* situation, the operative finding is the MBL math. **The 5-year substrate-honest window, combined with the dozens of trials already run, means the team mathematically cannot validate a strategy to DSR ≥ 0.95 on the current data.** Every measurement to date — including the 0.598 baseline, including any future engine-completion lift — is statistically under-powered for a deployment decision.

**The multi-decade extension is no longer one item among many. It is the precondition.** Build the long-history dataset (Norgate / ALFRED vintages / extending the survivorship-aware universe back to 1990 minimum, 1962 ideally), then re-run the canonical measurement. Only then does a DSR-clearing result become *possible*.

## TL;DR

> Fourth research dive validates the team's metric work (PSR, DSR, bootstrap CIs) and surfaces one structural finding: **the MBL formula says the 5-year window cannot statistically validate any strategy given the ~50-150 trials already run on it.** MBL given honest N is ~9-14 years; team has 5. **The multi-decade backtest extension is now the precondition for any valid deployment decision, not an optional improvement.**
>
> **Add:** MBL as Gate 0, PBO via CSCV, Lo autocorrelation correction on all Sharpes, ES_97.5 replacing VaR, Meucci N_Ent, CDaR, underwater curve, pre-registered CUSUM decay monitor.
>
> **Compute now:** honest N from the run registry; recompute DSR on the 0.598 baseline with that N (it will almost certainly fail — confirming 0/11 from another angle).
>
> **De-emphasize:** raw Sharpe headlines, MDD point estimates, parameter-plateau "robustness," raw kurtosis as a decision input.
>
> **The four research dives now unanimously converge.** That's the strongest possible signal the diagnosis is right.

Run the honest-N computation and the MBL check this week. It's a few hours of director-side work and it will tell the team — with mathematical precision — that the data window itself is the binding constraint. Everything else follows from accepting that.