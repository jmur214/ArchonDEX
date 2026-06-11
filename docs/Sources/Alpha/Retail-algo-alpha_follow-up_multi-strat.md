# Compound Alpha From Weak Signals: A Multi-Strategy Combination Map

**Bottom line up front.** The empirical evidence that non-linear combination of weak signals produces idiosyncratic alpha is **real but narrow** — it concentrates in cross-sectional equity panels with effective sample sizes in the 100,000+ range (Gu/Kelly/Xiu 2020; Chen/Pelger/Zhu 2024; Bryzgalova/Pelger/Zhu 2025), where interaction effects roughly **double** the predictive R² over linear-additive models. That regime is **not** the user's regime. The user runs six edges with 0/6 individual t>2, almost certainly on a single-asset or small-universe substrate with effective N in the low hundreds to low thousands. In that regime, the dominant result from the literature is **DeMiguel/Garlappi/Uppal (2009)**: optimization mostly noise-fits, and 1/N is genuinely hard to beat after costs. The single most consequential finding for your situation is this: **if the six raw signals have average pairwise correlation above ~0.4, no aggregation scheme — linear, gradient-boosted, or otherwise — produces t>2 combined alpha from t≈1 components.** Run the pairwise raw-signal correlation matrix before doing anything else. If max ρ > 0.5, the answer is to prune signals or replace them, not to swap the aggregator.

The rest of this dossier maps where compound alpha exists, where it doesn't, what construction methodology actually helps versus marketing, what the practitioners actually do (publicly), and what specifically to do with your 6-edge stack.

---

## 1. Does compound signal alpha actually exist? The honest map

### What the top empirical papers actually show

**Gu, Kelly & Xiu (2020, RFS 33(5):2223-2273)** is the foundational horse race: 920 predictors, 1957-2016, monthly US equity panel. Their decomposition is the cleanest in the literature because they hold non-linearity constant and vary interactions:

| Model | OOS monthly R² (%) | Long-short VW decile Sharpe |
|---|---|---|
| OLS (3-char) | 0.16 | 0.61 |
| Elastic Net | 0.09–0.11 | — |
| GLM-spline (non-linear, NO interactions) | ~0.19 | — |
| Random Forest (interactions allowed) | 0.33 | — |
| GBRT | 0.34 | — |
| NN3 (best) | 0.39 | **1.35** |

The R² roughly **doubles** moving from GLM-spline to trees/NNs — interactions deliver about as much as the entire main-effects nonlinearity. **Their own attribution sentence is unambiguous:** "We... trace [their] predictive gains to allowance of nonlinear predictor interactions that are missed by other methods." **Chen/Pelger/Zhu (2024, Mgmt Sci 70(2):714-750)** independently confirm: deep-learning SDF Sharpe **2.6** vs. their linear special case **1.7** — a ~0.9 Sharpe-unit delta attributable specifically to non-linearity. **Bryzgalova/Pelger/Zhu (2025, JF 80(5):2447-2506)** is the cleanest "interactions are where the alpha lives" demonstration: trees that endogenously discover conditional sorts deliver "up to three times higher OOS Sharpe ratios and alphas" than dozens of marginal factor portfolios.

**Critical reading of Jensen/Kelly/Pedersen (2023, JF 78(5):2465-2518).** Anyone citing JKP for compound-alpha claims is misreading it. JKP tests 153 **univariate** characteristics across 93 countries and finds 82% replicate after Bayesian hierarchical shrinkage. **It does not model interaction effects.** Its "themes" are within-cluster averages of correlated marginal signals, not interaction terms. Use JKP to defend the existence of marginal cross-sectional factors against Hou-Xue-Zhang skepticism; don't use it as evidence for non-linear combination alpha.

### The counter-evidence

**Avramov, Cheng & Metzker (2023, Mgmt Sci 69(5):2587-2619)** is the single most important counter-result for a retail trader. ML edge in equity prediction collapses outside the dirtiest universe: excluding microcaps cuts deep-learning profitability by **62%**, non-rated firms by **68%**, distressed firms by **80%**. With realistic transaction costs, most of the ML alpha disappears via the implied turnover. The Gu/Kelly/Xiu and Chen/Pelger/Zhu Sharpes are dominated by names a retail trader on Alpaca/IBKR cannot trade efficiently.

**Nibbering et al. ("Can Machines Learn Weak Signals?" NBER WP 33421, working paper)**: Lasso fails in low-SNR regimes "regardless of tuning"; ridge dominates lasso; random forest beats GBRT under weak signals; NN with L2 regularization "excels in capturing nonlinear functions of weak signals." **Kelly/Malamud/Zhou (2024, JF 79(1):459-503)** prove formally that in low-SNR settings, OOS Sharpe is monotonically *increasing* in parameterization (random-feature ridgeless asymptotics) — but only when shrinkage is applied correctly; otherwise you get Sharpe-ratio double-descent. The signal is: under correct regularization, more complexity helps even with weak signals; under wrong regularization, it destroys.

**Friedman's H-statistic in equity literature is a real gap.** Christoph Molnar's interpretable-ML book and the `hstats` R package use it widely, but I found no peer-reviewed paper systematically reporting H-stats for the cross-section of equity returns. Gu/Kelly/Xiu use partial-dependence visualization instead; Bryzgalova/Pelger/Zhu report tree-split frequencies. **If anyone claims "H-statistic on factor data shows X," demand the citation.**

### Conditional execution rules ("trade when N≥k signals agree")

**No top-tier academic finance literature addresses this design specifically.** The related ML voting-classifier literature (Dietterich 2000) compares hard-vote vs. soft-vote ensembles in classification, not trading. **Reasoning from priors anchored on Grinold-Kahn math:** a hard ≥k-of-N rule is a particular non-linear function (thresholded sum) that throws away magnitude information. Under low-SNR conditions, you want to keep magnitude because every bit of signal counts. Hard agreement rules help only when individual signals have heavy-tailed false positives — i.e., as a robustness filter, not as an alpha amplifier.

### What practitioners actually disclose (vs. what gets repeated)

**RenTech:** Zuckerman's book and the 50.75%-hit-rate Mercer quote are the only "sources" for the "thousands of weak signals" narrative. Treat as flavor, not data. **Two Sigma:** the only publicly-stated mechanic is "consensus view forecast → cost/risk-aware portfolio construction" (two-stage). **AQR:** the most transparent — explicitly states (Israel/Kelly/Moskowitz, "Can Machines 'Learn' Finance?") that financial ML's edge is small because SNR is structurally low, and their public Sharpe estimates for combined factor strategies (after costs) are in the 1.0–1.5 range, not the 2+ academic gross numbers. **Public material does not let you distinguish "many weak signals combined non-linearly" from "moderate signals diversified linearly" for any of these firms.** The widely-circulated "RenTech has thousands of t<1 signals" claim cannot be sourced rigorously.

---

## 2. Theoretical foundations — the math that governs your situation

### Grinold-Kahn applied to your six edges

The Fundamental Law (Grinold 1989, JPM; Grinold & Kahn 2000): **IR = IC · √BR**. For K independent signals combined: **IR_combined² = Σ IR_i²**. A signal with t=1 over 10 years has IR ≈ 0.316. Six uncorrelated such signals: √(6·0.316²) ≈ 0.775 → t ≈ 2.45. **Six uncorrelated signals with individual t=1 mathematically suffice to produce combined t>2.** This is the optimistic ceiling.

The pessimistic floor with exchangeable correlation ρ:

$$\text{IR}_{\text{combined}}^2 = \frac{K \cdot \text{IR}_0^2}{1 + (K-1)\rho}$$

| ρ (avg pairwise) | Combined IR (K=6, IR₀=0.316) | Combined 10-yr t |
|---|---|---|
| 0.0 | 0.775 | 2.45 |
| 0.2 | 0.548 | 1.73 |
| 0.4 | 0.450 | 1.42 |
| 0.5 | 0.414 | 1.31 |
| 0.8 | 0.346 | 1.09 |

**At ρ > ~0.3, linear combination of six t=1 signals does not break the t=2 barrier.** This is the math you have to confront before debating linear vs. non-linear aggregators.

### How non-linear combination changes the calculus

Empirical anchor (Gu/Kelly/Xiu 2020): interaction-term R² gain over GLM-spline ≈ 0.19 → 0.39, roughly doubling. **If your raw signals carry any genuine information, the literature's best estimate is that non-linear aggregation extracts roughly twice the signal-to-noise of linear-additive aggregation, ceiling.** That converts to a Sharpe lift of roughly **0.3–0.6 units** (reasoning from priors anchored on cited effect sizes), conditional on having enough effective sample size to estimate the interactions reliably.

### Capacity, tail risk, and the 2007 quant quake lesson

For retail accounts ($5k–$100k), capacity is irrelevant. What matters is per-trade cost as fraction of edge. Combined signals typically imply higher turnover (each component triggers some rebalancing); small accounts cannot amortize fixed costs. Avramov-Cheng-Metzker is the empirical anchor here: ML alpha mostly disappears under realistic frictions.

Tail risk math (Embrechts/Lindskog/McNeil 2003; McNeil/Frey/Embrechts 2005): **Gaussian copulas have λ_U = λ_L = 0** for ρ < 1 — linear correlation systematically underestimates joint tail probability. **t-copulas with finite ν have λ > 0** explicit closed form. **The 2007 quant quake (Khandani-Lo 2007, NBER w14465) is the canonical lesson:** every quant fund's "diversified" signals had low linear correlation but tail dependence λ ≈ 1 because they all loaded on the same liquidation-pressure factor. Multi-strategy retail is exposed to a scaled-down version of this whenever forced selling hits the same names across sleeves.

### Deflated Sharpe — the discipline you cannot skip

Bailey & López de Prado (2014, JPM 40(5):94-107): if you've tried even a dozen aggregation schemes and picked the best, in-sample Sharpe must be deflated substantially. A 1.5 Sharpe over 5 years (T=60 monthly) with N=20 trials can deflate to 0.6 or less. **Every linear-vs-nonlinear A/B test you run on the same data adds to N_trials.**

---

## 3. Strategy correlations — what the data actually says

### The full correlation matrix (best estimates)

**E** = sourced empirical; **P** = reasoning-from-priors. Ranges reflect regime dependence.

| | Trend | μCap MR | CEF | Insider | VRP | M&A | Spin | PEAD | DivInit |
|---|---|---|---|---|---|---|---|---|---|
| **Trend** | 1.00 | −0.05/+0.10 (E) | −0.10/+0.10 (P) | −0.05/+0.10 (P) | **−0.2/+0.1, strongly neg. in stress** (E) | −0.05/+0.10 (E) | −0.05/+0.05 (P) | 0/+0.10 (P) | 0/+0.10 (P) |
| **Microcap MR** | | 1.00 | +0.3/+0.5 (P) | **+0.4/+0.6** (P) | +0.3/+0.5 (P) | +0.2/+0.4 (P) | +0.2/+0.4 (P) | +0.2/+0.4 (P) | +0.1/+0.3 (P) |
| **CEF Disc** | | | 1.00 | +0.2/+0.4 (P) | +0.3/+0.5 in stress (E) | +0.2/+0.4 (P) | +0.1/+0.3 (P) | +0.1/+0.2 (P) | +0.1/+0.2 (P) |
| **Insider Cl** | | | | 1.00 | +0.1/+0.3 (P) | +0.1/+0.2 (P) | +0.1/+0.3 (P) | +0.2/+0.4 (P) | +0.1/+0.2 (P) |
| **VRP Crush** | | | | | 1.00 | **+0.3/+0.6** (E, shared short-put structure) | +0.1/+0.3 (P) | ~0/+0.10 (P) | +0.1/+0.2 (P) |
| **Merger Arb** | | | | | | 1.00 | +0.2/+0.4 (P) | +0.05/+0.15 (P) | +0.05/+0.15 (P) |
| **Spinoff** | | | | | | | 1.00 | +0.1/+0.3 (P) | +0.1/+0.2 (P) |
| **PEAD** | | | | | | | | 1.00 | +0.1/+0.2 (P) |

**Trend-following is the only category with confidently negative-or-zero correlation to nearly everything else.** Every other pair is positive, mostly via shared equity-beta substrate.

### Stress-period behavior — what survived and what broke

| Event | Trend vs SPY | Merger Arb | VRP Crush | CEF Disc | μCap MR |
|---|---|---|---|---|---|
| 2008 GFC | TF +~13% / SPY −37% | drawdown | catastrophic | discounts widened | crushed |
| Feb 2018 Volmageddon | mild negative | held | **XIV terminated; −15 to −40% 1-day** | mild widening | mild |
| March 2020 COVID | roughly flat (too fast) | **MNA −16.7% DD** | crushed (20–50% DDs) | discounts to historic levels | −40%+ |
| 2022 bond-equity flip | **SG Trend +27%, SPY −18%** | flat (MNA −1.6%) | mixed | widened historically | underperformed large |
| Aug 5, 2024 yen carry | hurt (most TF short JPY) | held | spike loss | mild widening | hit (momentum hurt) |
| April 2025 tariff V-shape | **SG Trend −4.89% / −9.33% YTD** (BIS, Risk.net) | held | spike then recovered | widened then narrowed | hit then recovered |

The 2012 AQR HOP study's "9 of 10 worst 60/40 drawdowns positive for trend" claim is real but contains 2/20 hypothetical fees and 110+ years of construction choices. **Trend's crisis alpha works when crises unfold over weeks-to-months (2008, 2022) and fails when crises are one-week V-shapes (1987, COVID, August 2024, April 2025).**

**The "correlation → 1 in crisis" cliché is empirically true specifically for hidden-short-volatility strategies** (merger arb, VRP, CEF discount, convertible arb, fixed-income RV). These form a single risk-cluster that all collapse together. It is empirically **false** for trend and long-vol tail hedges.

### Pair-by-pair verdicts (Section 6)

- **Trend + Microcap MR.** Genuinely diversifying in *most* regimes but not a free lunch. ρ ≈ +0.05 unconditional, ≈ +0.2 in fast equity drawdowns, ≈ −0.4 in slow ones. The diversification depends on the crash being slow enough for trend signals to flip short.
- **VRP + Trend.** The genuine convexity pair — closest thing to structurally negative correlation in this universe (Hoffstein/Newfound 2020: trend ≈ long straddle, VRP ≈ short straddle). Empirical: ρ ≈ −0.10/+0.10 unconditional; ≈ −0.5 to −0.7 conditional on either tail. The unconditional Sharpe addition is smaller than naive correlation implies because the diversification benefit concentrates in tails.
- **Event-driven (M&A/spinoff/CEF) + Equity factors.** Market-neutral *only* in benign regimes. Mitchell-Pulvino (2001, JF): merger arb returns are ≈0-correlated to SPY in flat/up months, strongly positively correlated when SPY < −4%/month. Payoff resembles short-index-put. Spinoffs are small/mid-cap directional bets. CEF discount narrowing fails when discounts widen further in retail-liquidation episodes.
- **Long Equity Beta + Managed Futures Trend.** Canonical pair, magnitude often overstated. The 2008 (+13/−37) and 2022 (+27/−18) numbers are real; 1987, March 2020, August 2024, April 2025 are the counterexamples. HOP 2012 reports a 20% trend allocation reduced 60/40 max DD from −62% to −52% over 109 years. Realized 2010s decade Sharpe: 0.61 — the long-run number is dragged up by the high-inflation 1970s. Robustly diversifying; "crisis alpha" framing oversells event-by-event reliability.
- **Microcap MR + Insider Clusters.** Same substrate. Insider filter helps signal quality, does not break correlation. Both signals' dollar P&L is dominated by common β to the microcap-asset-class factor. ρ ≈ +0.4/+0.6 unconditional; +0.7+ in microcap-beta stress. **Use one or blend signals into one strategy; do not treat as two independent allocations.**
- **Earnings Vol Crush + PEAD.** Different exposures (vega/gamma vs delta), mechanically near-orthogonal. ρ ≈ 0/+0.10 unconditional. **One of the few genuine diversification pairs in this universe** — though both strategies' retail post-cost alpha is debatable.

### Estimator choice for small-sample correlation

Use **Ledoit-Wolf (2003/2004) shrinkage toward constant-correlation target** as the retail default (sklearn `LedoitWolf`). For <60 observations, manually impose block structure based on substrate (equity-beta block, futures-trend block, options-vol block). Avoid raw sample covariance over short windows and never use bull-market correlation as informative about crisis correlation.

---

## 4. Portfolio construction — the methods ranked honestly

### The DeMiguel-Garlappi-Uppal anchor

**DeMiguel/Garlappi/Uppal (2009, RFS 22(5):1915-1953)** evaluated 14 mean-variance-style optimizers across 7 empirical datasets: **none consistently beat 1/N on out-of-sample Sharpe**. Their analytical calibration: ~**3,000 months (~250 years)** of data required for sample-MV to beat 1/N at N=25 assets; ~**6,000 months** at N=50. The datasets include factor portfolios that functionally are "strategies," so the result transfers cleanly to multi-strategy retail. The pessimism is somewhat softened for strategies (means are more stable than for individual securities due to theoretical priors on premia like value, momentum, carry) but it remains binding at retail data sizes.

### HRP — clever marketing more than empirical innovation

López de Prado (2016, JPM, SSRN 2708678) proposed HRP and showed it dominates CLA in simulated jump-diffusion experiments. **The independent replication literature is far less generous:**

- **Pfitzinger & Katzke (2019, Stellenbosch WP 14/2019):** "the sample dependence and concomitant poor out-of-sample results of MV appear to be limited when applied to real historical JSE data" — i.e., MV is less broken on real data than HRP's marketing implies, and HRP's edge over MV shrinks accordingly.
- **Raffinot (2017, JPM) HCAA, (2018) HERC:** acknowledged HRP's recursive bisection ignores dendrogram topology; proposed superior variants — itself evidence HRP isn't optimal.
- **Multiple post-2020 SSRN replications:** HRP *ties* 1/N on Sharpe across many universes; wins on variance (its objective), loses or ties on risk-adjusted return. Inverse-vol weighting often beats HRP when covariance estimates are noisy.
- **Salas-Molina et al. (2025, Computational Economics):** HRP performance varies materially with distance-metric choice — another researcher degree of freedom.

**Verdict:** HRP's edge over 1/N or inverse-vol at retail scale is within the cross-validation noise band. It is closer to folk wisdom dressed in ML clothing than a meaningful Sharpe-lifting innovation.

### Kelly inherits Markowitz's pathology

The multivariate Kelly portfolio **f\* = Σ⁻¹μ** is mathematically identical to unconstrained Markowitz tangency at unit risk aversion — so it inherits all of MV's estimation-error pathology, plus it overbets short-run. Half-Kelly corresponds to CRRA-γ=2 (modest risk aversion); quarter-Kelly ≈ γ=4. The halving coefficient is convention. **The rigorous version is "shrink Sharpe estimates by 30–50% before applying Kelly"** — the shrinkage matters far more than the Kelly fraction.

### The actual ranking by realistic retail Sharpe lift over 1/N

| Method | Data req. (mo) | OOS evidence | Realistic lift over 1/N |
|---|---|---|---|
| **Vol-targeted 1/N** | 12–36 | Moreira-Muir (2017, JoF) doc 10–40% Sharpe lift across factors | **+0.10 to +0.20** |
| **Inverse-vol / ERC** | 24–60 | Modest when σ heterogeneous | +0.05 to +0.15 |
| **Half-Kelly w/ shrunk μ** | 60+ | Reasonable when priors strong | +0.05 to +0.15 |
| **HRP / HERC** | 24+ | Ties 1/N on Sharpe in replications | −0.05 to +0.05 |
| **Min-variance** | 60+ | Mixed; concentration risk | −0.10 to +0.10 |
| **Sample MV / Markowitz** | 3000+ | Strictly dominated by 1/N at retail sizes | **−0.20 to 0** |

**The single most under-priced upgrade for retail is portfolio-level vol targeting** (Moreira-Muir 2017). It's mechanically trivial, well-evidenced, and produces a larger Sharpe lift than any cross-sectional weighting refinement.

### Retail risk-parity products — the 2022 verdict

Bridgewater All Weather: **−22% in 2022, two points worse than 2008's −20%** (Markov Processes International, Dec 2023). RPAR: **−22.8% in 2022**. UPAR: **−37.5%**. HFR Risk Parity 10% Vol Index: **−19.5%**. The short-correlation thesis collapsed when stock-bond correlation flipped to +0.65 vs. long-run −0.2. **Retail risk-parity ETFs have not validated the institutional thesis since RPAR's 2019 inception.** This is structural — any leveraged short-correlation strategy is vulnerable to correlation flips, not a one-time fluke.

---

## 5. What the big firms actually do (public material only)

**AQR Style Premia (QSPIX, SEC 497K 12/31/2025):** 4 styles (Value, Momentum, Carry, Defensive) × 5 asset groups (stocks/equity indices/fixed income/currencies/commodities). Construction explicitly: *risk-balanced within and across asset groups* — risk parity over a 4×5 matrix. Fee 1.30%. **Bridgewater All Weather (SPDR ALLW, March 2025):** ~79% nominal bonds + ~43% equity + ~38% TIPS + ~37% commodities (~1.8x leverage), expense 0.85%. Dalio's "Holy Grail" mantra ("15 good uncorrelated streams cuts vol by 80%") is mathematically equivalent to √N Sharpe scaling. **Citadel:** multi-pod structure with strict per-pod drawdown limits, central risk book, pass-through expenses. Ken Griffin publicly (Bloomberg late 2024) flagged pod-shop crowding as a real concern. **Two Sigma's only publicly stated alpha-combination mechanic:** two-stage "consensus view forecast → cost/risk-aware portfolio construction." Their Factor Lens (18 factors) is used as a risk lens, not the alpha-blending mechanism. **D.E. Shaw:** three named funds (Composite/Oculus/Valence), $90B AUM, "quant + discretionary" — and essentially nothing else disclosed.

**Notable:** none of the four firms publicly uses Markowitz mean-variance optimization at the top level on their alpha streams. That itself is a strong market signal that DGU's pessimism applies to multi-strategy combination at retail too.

**The "30/30/30/10" institutional heuristic** is not a documented standard. NACUBO/Commonfund 2024: endowments >$1B average ~62.5% alternatives, ~30% public equity, ~7.5% fixed income+cash. Public pensions average ~50/25/25/5. 30/30/30/10 is rounded retail-advisor convention, not empirically validated.

---

## 6. Meta-questions — the diminishing-returns curve

The Bailey/López de Prado Strategy Approval framework gives the cleanest closed form. With N equal-Sharpe strategies (s=0.7) at average ρ̄=0.3 (realistic for partial-substrate-overlap retail sleeves):

| N | Combined SR | Marginal lift |
|---|---|---|
| 1 | 0.70 | — |
| 2 | 0.87 | +24% |
| 3 | 0.96 | +10% |
| 5 | 1.07 | +11% over two steps |
| 8 | 1.15 | +8% over three steps |
| 12 | 1.20 | +4% over four steps |
| ∞ (ceiling = s/√ρ̄) | 1.28 | — |

**Diminishing returns hit hard between N=6 and N=10.** Beyond N≈10–12 operational cost dominates. **The right retail sleeve count is 3–6** chosen for genuine economic distinctness, not 10+ flavors of the same factor.

### Strategy Approval — the result that destroys "always prefer uncorrelated"

Two equal-risk strategies, equal-risk-weighted: **SR_p = (s₁+s₂)/√(2(1+ρ))**.
- s₁=s₂=0.8, ρ=0.6: SR_p = **0.894**
- s₁=1.0, s₂=0.2, ρ=0.0: SR_p = **0.849**

**Two correlated strong strategies beat one strong + one weak uncorrelated.** The right invariant is **(s_new − ρ̄·s_existing)**, not pairwise correlation in isolation. This destroys the folk wisdom "always prefer uncorrelated."

### Decay and rebalancing

**McLean-Pontiff (2016, JoF 71(1):5-32)** found 58% post-publication decay across 97 anomalies and — critically — that **post-publication, predictor portfolios' pairwise correlations with other published-predictor portfolios INCREASE**. Falck/Rej/Thesmar (2021, arXiv 2105.01380) document ~5pp/year/cohort decay acceleration. **Diversifying across decaying anomalies is partially self-defeating** because the arbitrage capital driving decay also synchronizes failure modes.

**Bouchey/Nemtchinov/Paulsen/Stein (2012, J. Wealth Mgmt 15(2):26-35):** rebalancing premium ≈ ½(σ̄² − σ_p²). For equal-weight 5-strategy retail at σ_strategy≈10%, ρ̄≈0.2: expected premium ≈ 30–60 bps/year. **Tax drag in a taxable account at retail (25–45% marginal) plausibly eats the entire rebalancing premium.** In a tax-deferred (IRA) account, monthly→quarterly rebalancing likely nets 20–50 bps. Mindlin (2015) argues the "bonus" is largely illusory over short horizons.

---

## 7. Implementation reality at retail scale

### The capacity / operational burden matrix

| Strategy | Capacity (single retail) | $50k | $500k | $5M | Hrs/wk |
|---|---|---|---|---|---|
| Microcap mean reversion | $1M–$5M | OK | slippage | **binding** | 2–4 |
| Large-cap MR | $50M+ | trivial | OK | OK | 1–2 |
| ETF trend / MF replication | $100M+ | trivial | trivial | OK | 0.5–1 |
| Direct futures trend | $50M+ | margin-constrains | OK | OK | 1–2 |
| Merger arb (hand-curated) | $5M–$20M/deal | OK | OK | deal-size binding | **5–10** |
| CEF discount arb | <$500k/name | OK | binding | **very binding** | 3–5 |
| Earnings vol (short premium) | PM-constrained | margin-binding (no PM <$125k IBKR) | OK | OK | 4–8 |

A realistic $500k retail trader running 5 sleeves should expect **10–15 hours/week** to run it properly. Anyone telling you "set and forget" with merger arb and CEFs is lying or doesn't personally touch the books.

### The wash-sale killer

If your daily MR sleeve sells AAPL at a loss and your trend sleeve buys AAPL within 30 days, the loss is disallowed and added to basis. The IRS doesn't care it was two different "strategies" — one taxpayer, one CUSIP. **Spouse accounts are treated as one taxpayer** (Rev. Rul. 2008-5). The architectural fix: **enforce strategy-level ticker exclusivity for 31 days, OR run disjoint universes** (e.g., MR on Russell 2000 names, trend on ETFs/futures only). The latter is cleaner.

### Risk overlay — Harvey/van Hemert / Man AHL

Harvey/Hoyle/Korgaonkar/Rattray/Sargaison/van Hemert (2018, JPM "The Impact of Volatility Targeting"): vol targeting improves Sharpe by ~0.10–0.20 across asset classes. **Critical counter-finding:** for portfolios of i.i.d.-Sharpe managers, asymmetric drawdown-stop rules (reduce risk after −10% drawdown without buying back) are **destructive** to long-term SR — they ratchet down without recovering. Drawdown rules help only when a meaningful fraction of underlying strategies are bad (zero-Sharpe types), via selection.

**Distilled retail prescription:** target portfolio vol 10–12% annualized; de-gross when 60-day pairwise correlation > 0.6 (crisis regime is the killer); avoid asymmetric drawdown-stop rules.

---

## 8. Testing methodology — the protocol that won't lie to you

### Pair-wise interaction tests

| Test | Best for |
|---|---|
| Regression with interaction term + HAC SE | Cheap initial screen |
| Cross-validated AND signal | Discrete signal intersection at small N |
| SHAP interaction values (`shap.TreeExplainer.shap_interaction_values`) | Per-observation pair attribution when you have a fitted tree |
| Friedman H-statistic | Global interaction strength; high compute |

Start cheap (regression-interaction with HAC), confirm flagged pairs with SHAP on a tree model.

### Walk-forward for multi-cadence sleeves

Set fold size = LCM of rebalance cadences OR longer than the longest holding period. **Purge** all training observations whose label horizon overlaps the test set (López de Prado 2018, *Advances in Financial Machine Learning*, Ch. 7). **Embargo** of 1–2 max-holding-periods after each test fold. For sparse event sleeves (merger arb, index events), use **event-stratified folds** so each test fold has comparable event counts.

### Multiple-testing — pick the right correction

| Method | When |
|---|---|
| Bonferroni | Few tests, strict FWER |
| Benjamini-Yekutieli FDR | Many tests with arbitrary dependence (right answer for financial returns) |
| Deflated Sharpe Ratio | When the "best" was selected from many trials |
| López de Prado ONC + DSR | Many correlated trials — ONC estimates effective N which DSR then uses |

For 1000 grid-search variants of 5 base strategies, N_effective via ONC clustering is typically **15–30**, not 1000 (LdP working papers).

### Bootstrap that preserves cross-strategy dependence

i.i.d. bootstrap is invalid. **Stationary bootstrap (Politis-Romano 1994, JASA 89:1303-1313)** with random geometric block lengths is the right choice; use **Politis-White (2004)** automatic block-length selection. For multi-strategy: bootstrap **rows of the matrix** of strategy returns (preserving cross-sectional joint structure at each timestamp), not each strategy independently.

### The protocol checklist

```
□ Data hygiene: point-in-time, survivorship-free, T+1 fills, half-spread + impact
□ Strategy-level: CPCV with N=6 groups, k=2 test → 15 paths; purge = max label horizon; embargo = 1%
□ Report Deflated Sharpe adjusted for parameter trials
□ Ensemble-level: walk-forward at slowest cadence; stationary bootstrap on multivariate matrix
□ 10,000 bootstrap reps; report 5th/95th portfolio SR
□ Interaction: regression with all pairs + HAC SE; FDR via Benjamini-Yekutieli q=0.10
□ Attribution: Fung-Hsieh 7-factor on each sleeve; LOO Sharpe with bootstrap CI
□ Conditional SR by realized-correlation regime
□ Stress: forced de-grossing in high-ρ regime; wash-sale-adjusted after-tax returns; capacity haircut
□ Decision: add sleeve only if (s_new − ρ̄·s_existing) > threshold; DSR > 0.95 at portfolio level
```

---

## 9. Counter-evidence — the section that gets ignored

### AQR Style Premia (QSPIX) — the multi-factor disappointment

Sourced from Morningstar/YCharts:

| Year | QSPIX return |
|---|---|
| 2018 | −12.35% |
| 2019 | −8.20% |
| 2020 | −21.96% |
| 2021 | +24.83% |
| 2022 | +30.64% |
| 2023 | +12.81% |
| 2024 | +21.03% |

Peak AUM ~$5B → trough ~$500M. The fund recovered, but **>50% of AUM redeemed at the bottom.** AQR Equity Market Neutral (QMNIX) was worse: 38.7% drawdown Jan 2018 → Nov 2020; AUM crashed from $2.36B (Mar 2018) to $48.5M (Dec 2020) — a **98% AUM decline**. The honest reading: a product designed to deliver "equity-like returns at 10% vol with zero market beta" delivered a peak-to-trough drawdown of ~50%, with cross-asset diversification failing as value/momentum/defensive all suffered the same growth/risk-on regime.

### Managed futures lost decade

SG CTA Index Jan 2010 → Jan 2020: $100 → $117 (1.6% CAGR; Morningstar June 2024). iShares Core S&P 500 same period: $100 → $255. A decade of flat absolute returns while equities tripled. The 2022 +20.2% rescue does not erase a decade of opportunity cost. **Single-decade underperformance against the dominant asset is not a tail — it's a real possibility.**

### LTCM (1998) — when the correlation matrix collapsed

LTCM ran ~60,000 trades across convergence/sovereign/MBS/equity vol/merger arb/EM. President's Working Group report (CFTC 1999): "the simultaneous shocks to many markets... revealed that global trading portfolios like LTCM's were less well diversified than assumed." Designed correlation ~0.3; realized August 1998 correlation ~0.7. Fund lost 44% in August 1998 alone. **The textbook lesson:** multi-strategy diversification is conditional on a stable correlation matrix. In tails, the matrix collapses to one regime.

### Fund-of-funds — the systematic failure

**Brown/Goetzmann/Liang (2003, NBER w9464):** double-layer fee structure (typically 1/10 on 2/20) consumes most alpha; FoFs as a group underperform an equal-weight portfolio of individual hedge funds after fees. **Fung/Hsieh/Naik/Ramadorai (2008, JoF):** *"the average fund-of-funds delivers alpha only in the period between October 1998 and March 2000."* Outside that 18-month window, the average FoF delivered zero alpha vs. Fung-Hsieh 7-factor. **Implication for retail:** if institutional FoFs with full DD and access can't reliably extract multi-strategy alpha net of fees, retail DIY is doing the same job with worse information but no second fee layer. **The fee saving is the entire edge.**

### Style-premia funds beyond AQR

GMO Systematic Global Macro drew down meaningfully 2018–2019. Two Sigma closed several risk-premia products amid the quant winter. JPMorgan/Goldman/Wells Fargo Alternative Risk Premia mutual funds (launched 2014–2017 on 2009–2017 in-sample factor evidence) mostly underperformed cash through 2020. **The pattern is brutal:** products launched on in-sample factor evidence delivered roughly the opposite of marketed Sharpes in their first multi-year OOS test.

---

## 10. Specific guidance for your 6-edge stack

### Probability of compound alpha from non-linear combination (your situation)

The user's state: 6 edges, linear weighted-sum aggregator, 0/6 individual t>2.

**Probability that gradient-boosted or interaction-modeling aggregation produces OOS t>2 (reasoning from priors anchored on Gu/Kelly/Xiu effect sizes, downweighted for retail effective N):**

| Avg raw-signal ρ | Individual t-stat distribution | Probability of combined OOS t>2 |
|---|---|---|
| < 0.2 | [0.8, 1.5] | **35–55%** |
| 0.2–0.5 | [0.8, 1.5] | **15–30%** |
| > 0.5 | [0.8, 1.5] | **<10%** |
| Any | [0.0, 0.8] | **<15%** — signals likely too weak even for non-linear |

**The dominant value of moving to gradient boosting is NOT interaction effects per se** — it's the flexibility to learn that some signals are useful only conditional on other signals being in a certain range (a regime gate by another name). This is exactly the gain Gu/Kelly/Xiu attribute to trees.

### When non-linear combination will NOT help

1. **All signals are noisy versions of the same latent factor** (e.g., 6 momentum lookbacks). Non-linearity cannot manufacture information absent in the data.
2. **Effective sample size too small for interaction estimation.** Six features = 15 pairwise interactions. Reliable estimation needs roughly 50–100 effective observations per discoverable interaction (engineering folklore — reasoning from priors). With <1500 effective obs, you mostly overfit. Single-asset daily over 5 years: nominal N≈1250, effective N often 200–400 (due to autocorrelation and uniqueness weighting per López de Prado 2018 Ch. 4). **This is likely your binding constraint.**
3. **Conditional signals on rare regimes.** If signal 3 only works in 5% of months ("high VIX"), boosting cannot reliably discover that.
4. **Per-trade cost approaches per-trade edge** (Avramov-Cheng-Metzker is empirical anchor).
5. **Selection bias from researcher iteration.** Every aggregator you A/B test inflates N_trials for DSR.

### Regime-conditional alpha (bull-only + bear-only edges)

Two relevant strands: Markov-switching (Hamilton 1989; Guidolin-Timmermann 2007, JFE) and mixture-of-experts (Jacobs/Jordan 1991, Neural Computation). **For your setup specifically:** explicitly modeling a regime gate is exactly what a tree-based aggregator does implicitly. The first split in a boosted tree, applied to your 6 features plus a regime feature (VIX level, 200-day SMA slope, term spread), will likely partition on the regime feature. **This is higher value than adding more raw signals.** A single well-chosen regime variable, combined with one bull-edge and one bear-edge, can produce alpha that no linear combination of your 6 signals can produce. Grinold-Kahn breadth doubles when you can take both long and short bets (Clarke/de Silva/Thorley 2002, FAJ 58(5):48-66).

### Ensembling around one positive edge: dilute or amplify?

**Dilute, in expectation.** If one signal has t=2.5 and five others are t≈0:
- Equal-weight linear: combined t ≈ 2.5/√6 = 1.02 → **massive dilution**.
- Optimal weighting (1.0 on good signal, 0 on noise): preserves t=2.5 but requires knowing which is good.

Boosting under L2 + CV will, in expectation, learn to downweight noise — but small-sample shrinkage pulls toward equal weights, causing *some* dilution. **If effective T is large enough that boosting discovers the good signal: combined t can exceed individual t** because noise signals act as instruments helping identify when the good signal applies. **If T is small: boosting noise-fits and destroys the good signal.** This argues for hierarchical Bayesian shrinkage (JKP 2023 approach) where signals within a "theme" share a prior — harder to implement than boosting but more principled at small N.

### What to do, in order

1. **Run the pairwise correlation matrix of your 6 raw signal scores** (not their returns). If max ρ > 0.5, prune to a less-correlated subset before changing aggregator. Most likely lever in this dossier.
2. **Add a regime variable** (VIX level, 200-day SMA slope, term spread) as an explicit feature. Gu/Kelly/Xiu and Chen/Pelger/Zhu both show macro state matters more than additional micro signals.
3. **Test boosting vs. linear via CPCV walk-forward, never re-using test sets.** Compute Deflated Sharpe given trials. Hold out a true OOS period (≥18 months) never touched during model selection.
4. **Apply portfolio-level vol targeting** as a separate overlay (Moreira-Muir 2017 evidence). Bigger Sharpe lift than any aggregator change.
5. **Expected realistic lift from linear → non-linear (reasoning from priors): 0.3–0.6 Sharpe units IF underlying signals carry genuine information; zero or negative if they don't.**

---

## 11. The single most consequential finding for your situation

**Your problem is almost certainly not the aggregator.** It is one or more of:

1. **The six edges share substrate.** If they're all variants of "mean reversion on small caps" or "momentum at different lookbacks," their raw scores are correlated >0.5 and no aggregation function (linear, non-linear, voting, regime-gated, Bayesian) recovers t>2 from t≈1 components. **The math in §2 forecloses it.**

2. **Your effective sample size is too small for the interactions you're hoping the aggregator will discover.** Six features → 15 pairwise interactions, each needing roughly 50–100 effective observations. With single-asset or small-universe daily data over 3–5 years, effective N is in the low hundreds — sufficient for *one* well-specified interaction, not 15.

3. **The signals you're combining are inside the Avramov-Cheng-Metzker zone** — even academic ML alpha mostly disappears under realistic frictions when you exclude microcaps/distressed/non-rated names. If your edges trade liquid US equities, the literature's expected post-cost alpha is small to begin with.

4. **Switching aggregators is a researcher degree of freedom that inflates Deflated-Sharpe penalties.** Each variant you A/B test on the same data raises the effective N_trials and erodes any apparent improvement.

**The single most-consequential action:**

> **Compute the pairwise rank correlation matrix of your 6 raw signal scores (not their backtest returns). If the maximum off-diagonal entry exceeds 0.5, or the average exceeds 0.3, no aggregator change can rescue this stack. Replace the worst-correlated pair with one orthogonal signal — most plausibly a regime feature (VIX level, term spread, 200-day SMA slope) or a fundamentally different substrate (futures trend, options-vol-crush, event-driven) — before changing the aggregation function.**

The user is looking for a clever combination function to compensate for signals that don't individually carry information. The literature is unanimous that this is the wrong place to look: Gu/Kelly/Xiu's non-linear gains come from genuinely diverse raw features (94 stock characteristics × 8 macro states); DGU's 1/N result says optimization doesn't rescue weak inputs; Bailey-LdP's Strategy Approval theorem says **(s_new − ρ̄·s_existing)** is the invariant, not the aggregator topology. Fix the signals first. The aggregator question only matters once the inputs are genuinely diverse.

---

## Final ranking — methodologies by realistic retail Sharpe lift over single best strategy

1. **Portfolio-level vol targeting + 1/N across genuinely diverse sleeves.** Empirically backed by Moreira-Muir (2017, JoF). Estimated lift: **+0.20 to +0.40 Sharpe.** The dominant lever.
2. **Adding a regime feature + tree-based or mixture-of-experts aggregator across diverse sleeves.** Estimated lift over linear-on-same-features: **+0.10 to +0.30 Sharpe** (anchored on Gu/Kelly/Xiu interaction R² doubling).
3. **Equal Risk Contribution / inverse-vol weighting** when sleeves have heterogeneous σ. Lift: **+0.05 to +0.15.**
4. **Half-Kelly with shrunk μ estimates** when priors are strong. Lift: **+0.05 to +0.15.**
5. **Hierarchical Risk Parity / HERC.** Lift over 1/N: **−0.05 to +0.05** (within replication noise).
6. **Sample mean-variance / multivariate Kelly.** Lift: **−0.20 to 0.** Strictly dominated at retail data sizes.

The genuinely diversifying retail-tractable triple appears to be **managed-futures trend + VRP-crush (sized small enough to survive a Volmageddon-class event) + a microcap/event-driven sleeve** — with the understanding that the third leg shares substrate with equity beta and will bleed in any genuine systemic stress. Most "retail multi-strategy" portfolios are 5–8 variations of the same equity-beta substrate dressed in different signal clothing; their realized stress correlation is closer to 0.7 than to 0.2.

The empirical evidence that combining weak signals via non-linear methods produces idiosyncratic alpha that doesn't exist in any individual signal is **real, narrow, and conditional on (a) genuinely diverse raw features, (b) effective sample size in the thousands minimum for interaction estimation, and (c) post-cost frictions small relative to per-trade edge.** The retail-scale version of this evidence is much weaker than the academic version because all three conditions bind harder. The honest verdict for your 6-edge stack is that the aggregator function is a second-order question; the first-order question is whether the six edges encode genuinely different information about future returns. Audit the raw signal correlations first. Everything else follows from that.