# Regime Models for Retail Algo Trading: An Honest Field Guide

## Brief restatement of the task

This report evaluates machine-consumable market-regime models for a technically sophisticated retail algo trader running Python/Alpaca with $5k–$100k capital and a 3–12 month deployment horizon. The primary use cases assumed are **strategy filtering** (turn trend-following on/off, turn vol-selling on/off), **dynamic weighting** between sub-strategies, and **position sizing / risk-on-off scaling** — not standalone "macro prediction." Highest priority is given to multi-day to multi-week signals that translate into actual trading actions on retail-feasible data (FRED/ALFRED, CBOE, Alpaca/Polygon prices, CFTC, ICE/BAML credit indices). Every model is labeled **IDENTIFICATION** (nowcasting current regime), **PREDICTION** (calling a transition in advance), or **FORECASTING** (regime at horizon t+N), because almost every published "regime model" is actually nowcasting marketed as predictive — a confusion this report tries to extinguish.

---

# PART 1 — Framework

## 1. Taxonomy of regimes

| Regime family | Variable classified | Why it matters | Typical persistence | SNR | Better for |
|---|---|---|---|---|---|
| **Volatility** | Realized vol, IV (VIX), conditional variance | Drives position sizing, premium-selling viability, stop placement | Calm 4–8 mo; crisis 2–6 wk but clustered | **High** (vol is directly observable) | **Identification** |
| **Trend vs mean-reversion** | Hurst, variance ratio, return autocorr, trend strength | Filters whether to deploy TF vs MR | Asset-class trending sustains years; TSM decays after 12–24m (Moskowitz-Ooi-Pedersen 2012) | Medium-low | Identification w/ lag |
| **Macro (growth/inflation/policy)** | Recession indicator, inflation regime, real rates | Determines duration/equity/commodity leadership; stock-bond correlation sign | NBER expansions ~5y avg; inflation regimes multi-year | Medium (heavily revised data) | Mostly nowcast; modest prediction via credit/term-spread |
| **Liquidity** | Spreads, NFCI, MOVE, dealer balance sheet | Slippage, gap risk, exit feasibility | Bursts (days–weeks) inside secular regimes | Med-high | Identification |
| **Correlation** | Rolling cross-asset corr, eigenvalue dispersion | Effective diversification, hedge availability | Stock-bond regimes 15–30y; short-horizon corr jumps in crises | Medium | Identification |
| **Factor leadership** | Realized factor spreads (value/mom/qual/lowvol) | Whether to tilt factor exposures | Multi-year (value drawdown '17–'20 lasted ~3y) | **Low** (cross-sectional noise) | Identification; timing is hard (Asness et al. 2017) |
| **Risk-on/risk-off** | Composite (VIX, HY OAS, USD, breadth) | Macro overlay; duration on/off | Weeks–quarters | Medium | Identification only |
| **Microstructure** | Order-flow imbalance, dealer gamma, VPIN | Execution algo, intraday signal half-life | Minutes–days | High intraday | Identification, very short horizon |

The retail-actionable kernel: vol regime → position sizing; trend regime → strategy filter; liquidity regime → risk overlay. Everything else is supplementary.

## 2. Identification vs prediction — the honest version

**What is genuinely achievable in identification (nowcasting).** Volatility state is nowcastable in real time with low error using GARCH/HAR/HMM smoothed probabilities — vol is one of the few directly observable regime variables. Recession nowcasting via the Sahm Rule and Atlanta Fed GDPNow identifies recessions within ~0–4 months of onset, well before NBER announcement. Realized correlations over 60–252-day windows are reasonably stable. These work — but they are nowcasts, not forecasts.

**What is achievable in transition prediction.** Very limited. The yield-curve→recession signal has lead times ranging from **6 to 24+ months** (San Francisco Fed; Harvey's own data), with the **2022 inversion producing no NBER recession through 2026** — the cleanest false positive on record. The Conference Board LEI signaled recession for **21 consecutive months** in 2022–2024 with no recession. ISM PMI sub-50 persisted **16+ months** without recession — the longest such streak in series history. The Sahm Rule triggered August 2024 with no follow-through, and **the rule's own creator publicly stated it was misfiring** ("My Recession Rule Was Meant to Be Broken," Bloomberg Opinion Aug 2024). The pattern is clear: indicators based on **level thresholds** (curve sign, PMI 50, Sahm 0.5) broke in 2022–2024; indicators based on **credit risk premia and forward-rate decompositions** (EBP, NTFS, ANFCI) held up.

**What is achievable in forward forecasting (regime at t+N).** Accuracy collapses rapidly with N. For N > 1 month, regime forecasts essentially revert to base rates. Multi-state HMMs forced to label out-of-sample data overfit middle states.

**Where academic literature inflates claims.** The core trick: papers fit a Markov-switching/HMM on the full sample, report **smoothed (Kim 1994) probabilities**, and call this "regime prediction." But smoothed probabilities at time *t* use information through time *T* — this is contemporaneous classification with a forward-looking peek. Examples of inflated-then-deflated:

- **Hamilton 1989** itself: Doornik (2013) shows the celebrated NBER-match breaks down extending past 1984. *"By about 1985 we enter a period of relatively stable GNP growth … Regime-switching models lost some of their appeal."*
- **Ang & Bekaert 2002/2004**: their own paper concedes regime alpha is "difficult to exploit within a framework focused on global equities" — the value comes from cash/bond switching mechanically driven by high-vol/high-rate coincidence.
- **Sahm rule**: marketed as recession early-warning; in real-time-vintage data it has **2–4 historical false positives** rather than the often-quoted "1" (Ash & Nickelsburg 2024; Richmond Fed Economic Brief 25-07, Feb 2025).
- **LEI**: Conference Board quietly recalibrated its "3D's" recession threshold from −4.0% → −4.4% → −4.1% across 2022–2024 publications, then capitulated Feb 2024 ("for the first time in the past two years … the leading index currently does not signal recession").
- **Variance Risk Premium (Bollerslev-Tauchen-Zhou 2009)**: Papagelis (2025, *J. Financial Markets*) re-runs the canonical regression and finds slopes **statistically insignificant in Feb 2012 → Sep 2022** across all horizons. The headline R² has decayed.

**The honest test** is real-time, ALFRED-vintaged, purged-OOS, multiple-testing-deflated Sharpe — and this hurdle eliminates most published regime alpha.

## 3. Evaluation methodology — how not to fool yourself

**Walk-forward and CPCV.** Standard k-fold CV fails in finance because observations aren't IID and labels overlap into the future (López de Prado 2018, *Advances in Financial Machine Learning*, Ch. 7). Use **purged k-fold** (remove training observations whose labels overlap test labels) plus an **embargo** gap. For regime models specifically, walk-forward is preferred because it preserves the temporal ordering of regime transitions; CPCV can leak regime persistence across folds and inflate estimates. Johansson & Meldrum (Fed FEDS 2020-38) explicitly show that **switching from naive CV to proper time-series CV reverses model rankings** for ML recession forecasters — RF/XGBoost gains over probit shrink substantially or disappear.

**ALFRED vs FRED — the look-ahead-bias killer.** FRED serves the latest revised vintage; ALFRED stores every historical vintage, letting you retrieve the data actually available on date *t*. Croushore (2011, *JEL*) documents systematic revision patterns: *"during recessions, initial release of GDP tends to be higher than later estimates."* A recession classifier trained on revised data appears cleaner than it would have been in real time. Concrete cases:

- **Sahm rule** has false positives in 1959 and 1967 using real-time data that disappear in revised data.
- **LEI** Diebold-Rudebusch (1991) showed the original Composite Leading Index *"did a poor job of forecasting recessions and output"* in real time despite strong ex-post fit.
- **GDP** signs of advance vs latest estimate match only 97% of the time 1999–2022, with much larger gaps in recession quarters.

**If your backtest of a macro regime model touches FRED current-vintage data, your backtest is biased.** This is non-negotiable.

**Measuring false positive rate.** Base rates are imbalanced — recessions are ~12–15% of post-WWII months — so a "no recession always" classifier has 85–88% accuracy. Use balanced accuracy, precision/recall, or AUROC. Critically, **conditional FPR matters**: one false positive that fires mid-expansion can torpedo a regime-conditional strategy that goes 100% cash.

**Lead time vs accuracy tradeoff.** Fundamental tension. Yield-curve illustrates this: 6–24 month lead with low FPR but enormous variance in lead time. **A 20-month-early signal that requires capital deployment for 20 months has negative NPV even if the recession eventually occurs.**

**Economic value, not classification accuracy, is the only test that matters.** Classification accuracy ≠ Sharpe improvement. The mapping requires hit rate conditional on regime, asymmetry of regime returns, and transaction costs of switching. Hoffstein (2019, "Fragility Case Study: Dual Momentum GEM") documents that specification risk across lookback windows produces *"year-to-year performance differences spanning hundreds to thousands of basis points"* with the same underlying signal. Use **Sharpe of (regime-conditional strategy minus unconditional benchmark)**, on purged OOS paths, deflated for trials.

**p-hacking and multiple-testing.** Each threshold (Sahm 0.5 vs 0.3; LEI −4.2 vs −4.4; yield curve 10y-2y vs 10y-3m vs 5y-3m) is a separate test. Harvey, Liu & Zhu (2016, *RFS*) propose a hurdle of **t > 3.0** rather than the conventional t > 2.0 for cross-section finance, derived from a Benjamini-Hochberg-Yekutieli FDR framework. Hou-Xue-Zhang (2020) using this cutoff find **82.5% of 452 anomalies lose significance**. The Bailey-López de Prado **Deflated Sharpe Ratio** typically deflates an observed Sharpe by 30–60%. For regime models the analogous hurdle is steep — MS-AR, HMM, change-point, CUSUM, ML classifiers have all been tried on the same recession sample; the effective number of independent tests is plausibly in the dozens to hundreds.

## 4. Common failure modes

**Confusing structural breaks with cyclical regimes.** A Markov-switching model interprets one-time shifts (end of Bretton Woods, post-2008 ZIRP, 2022 inflation regime) as cyclical states, inflating estimated transition probabilities. Doornik (2013) interpreted Hamilton's post-1984 model failure as model breakdown — but it was a structural break (Great Moderation) mis-coded as a Markov state. Run CUSUM (Brown-Durbin-Evans) and Supremum-ADF tests as sanity checks before fitting regime models.

**Post-hoc rationalization.** After every crisis, regime models are retuned to "explain" it. López de Prado's First Law: *"Backtesting is not a research tool. Feature importance is."* Re-tuning thresholds to make 2008 work is data mining disguised as research.

**Over-fitting to 2–3 transitions.** Modern data has only ~3–7 recessions and ~5–10 distinct vol regimes. Any model with 3+ parameters fit to this is dangerously overfit at the latent-variable level. Cross-validation cannot help because the *entire dataset* is the small-n sample.

**Ignoring base rates.** The actionable Bayesian question is **P(recession | signal) / P(recession)** — the Bayes factor — not raw hit rate. Common error: report 95% sensitivity, ignore that a 12% base rate × 95% sensitivity vs 88% prior × 10% FPR gives a surprisingly modest posterior.

**Mistaking volatility for information.** Many vol spikes are transient (Aug 2015, Feb 2018, Mar 2020, Aug 2024). Vol-triggered strategy changes whipsaw — Hoffstein's recurring point that *"Q4 2018 highlights model specification risk."*

**Non-actionable classifications.** A correct call of "we are in a slow-growth regime" gives no actionable trade if your strategy has a 20-day holding period and the regime persists 5 years. Horizon matching is the most-skipped step in retail regime modeling.

## 5. Source diet — curated, with verdicts

**Foundational (the canon, read once, internalize the limitations).**

- **Hamilton 1989** (*Econometrica*) — Markov-switching original. Apply for understanding, not as a working trading model. Known issue: middle-state ambiguity in smoothed probabilities; breakdown post-1984.
- **Ang & Bekaert 2002 (*RFS*), 2004 (*FAJ*); Ang & Timmermann 2012 (*ARFE*)** — best regime-asset-allocation series. The Annual Review piece is the single best survey of the literature.
- **Lopez de Prado 2018, *Advances in Financial Machine Learning*** — Ch. 5 (fractional differentiation), 7 (purged k-fold), 12 (CPCV), 17 (structural breaks). Mandatory reading. Plus **Lopez de Prado 2018 *JPM*** "The 10 Reasons Most Machine Learning Funds Fail."
- **Harvey, Liu & Zhu 2016 (*RFS*) "...and the Cross-Section of Expected Returns"** — mandatory for any paper claiming a new regime signal works.
- **Bailey & López de Prado 2014 *J. Risk* "Deflated Sharpe Ratio"** — read before any backtest result you generate.
- **Diebold & Yilmaz 2012** — volatility connectedness/spillovers; foundational for cross-asset vol regime work.
- **NBER Business Cycle Dating methodology (Hall, 2003)** — clarifies that NBER itself is *not* a real-time prediction protocol. NBER dates announced 6–18 months after the peak; **NBER recession dating has zero predictive value for tradable signals**.
- **Croushore 2011 (*JEL*) "Frontiers of Real-Time Data Analysis"** — must-read on revision effects.

**Practitioner / tactical (where the rubber meets the road).**

- **Carver, *Systematic Trading* (2015, 2nd ed. 2023)** — vol-targeting, forecast-scaling. Carver holds an explicit anti-regime-timing prior: *"systematic traders … should avoid trying to forecast anything, but just keep executing a system with positive expectancy."* This is the steelman against most of this report.
- **Hoffstein / Newfound Research, *Flirting with Models*** — single best practitioner source on tactical signal decay, specification risk, rebalance timing luck, and process diversification. Recurring theme: tactical signals decay, specification risk dominates, diversification across implementations is more robust than picking "the right" model. Key posts: "When Simplicity Met Fragility" (2018), "Fragility Case Study: Dual Momentum GEM" (2019), "Tactical Credit" (2019).
- **AQR research library** — Asness, Chandra, Ilmanen & Israel 2017 *JPM* "Contrarian Factor Timing is Deceptively Difficult"; Asness, Ilmanen & Maloney 2015 "Practical Market Timing: Sin a Little"; Hurst-Ooi-Pedersen 2017 "A Century of Evidence on Trend-Following." AQR is publicly skeptical of regime timing — the most defensible practitioner posture.
- **GMO quarterly letters (Grantham, Inker, Montier)** — useful valuation-regime perspective; **caveat**: Grantham's bubble calls have decade-long lead times and are not tradable signals.
- **Bridgewater All Weather / Dalio *Big Debt Cycles*** — useful as narrative regime taxonomy; **low operational testability, no OOS evaluation; treat as structural lens, not a signal**.
- **Robot Wealth, Quantian, Epsilon Theory** — practitioner sources with verifiable analytic track records, opinion-labeled.

**Real-time data infrastructure (non-negotiable).**

- **St. Louis Fed ALFRED** (alfred.stlouisfed.org) — vintage macro data.
- **Philadelphia Fed Real-Time Data Set for Macroeconomists** (Croushore & Stark 2001).

**Where famous recommendations have been challenged out-of-sample:**

| Claim | Source | OOS challenge |
|---|---|---|
| Hamilton 2-state matches NBER | Hamilton 1989 | Doornik 2013; breaks post-1984 |
| Yield curve reliably predicts recession 12m ahead | Estrella-Mishkin 1998 | 2022 inversion → no recession through 2026 |
| LEI is 7-month leading | Conference Board | 21-mo false alarm 2022–24; Feb 2024 capitulation |
| Sahm rule: only 1 false positive | Sahm 2019 (revised data) | 2–4 false positives in real-time vintages; Aug 2024 trigger failed |
| VRP predicts equity returns | Bollerslev-Tauchen-Zhou 2009 | Papagelis 2025 — insignificant 2012–2022 |
| Factor timing via value spreads | various pre-2015 | Asness et al. 2017: "Deceptively Difficult" |
| ISM PMI <50 → imminent recession | classic Wall Street rule | 16+ mo sub-50, no recession |
| 60/40 stock-bond diversification | post-1998 stylized fact | 2022: −16% drawdown, correlation flipped positive |
| Dual Momentum GEM | Antonacci 2012 | Hoffstein 2019 — hundreds of bps year-to-year specification dispersion |

**Avoid as evidence:** generic retail content, fintwit threads about the yield curve, YouTube macro pundits, paywalled course marketing, Medium/TowardsDataScience posts with no OOS protocol.

---

# PART 2 — Ranked menu of regime models

## Ranking methodology

The composite score below blends three dimensions: **out-of-sample validity** (does it work outside the sample it was fit on, across multiple structural breaks?), **retail feasibility** (free/cheap data, daily-to-monthly retraining cadence, no GPU clusters), and **economic value when actually applied** (Sharpe improvement, drawdown reduction, conditional return predictability — not classification accuracy). Models are grouped by category and then re-ranked head-to-head at the end.

## Tier 1 — Use, with discipline

### #1. VIX term structure (VIX / VIX3M slope; also VIX9D, VIX6M)

- **Thesis:** Contango = calm carry regime; backwardation = stress regime. The slope filters out persistent VRP from acute fear and is structurally grounded in option-hedging mechanics.
- **Regime variable / horizon:** Vol carry state; 1–20 days.
- **Label: IDENTIFICATION** of carry-state plus modest **PREDICTION** of short-vol P&L direction. **Not** a return-prediction model for SPX.
- **Mechanism:** Front-vs-back implied vol slope tracks acute hedging demand vs steady-state VRP. Macrosynergy and Avellaneda et al. (2021) show Sharpe >1 from long M1 / short M5 in contango and reverse in backwardation.
- **Data:** CBOE free daily; VIX9D, VIX, VIX3M, VIX6M. Trivial.
- **Signal characteristics:** Contango is the base state ~80–84% of trading days. When ratio inverts and SPX has already sold off, forward SPX returns are positive on average (oversold contrarian signal). Lead time vs VIX spike: ~0–2 days (it often inverts the same day VIX spikes).
- **Implementation reality:** Compute VIX/VIX3M nightly. Standard threshold 1.0; ~0.95 as early warning. Gotcha: VX1/VX2 futures ratio has known week-before-expiration drift (Harwood, Six Figure Investing); thin VIX9D liquidity pre-2014 makes backtests suspect.
- **OOS track record:** Worked in 2008, 2011, 2015–16, COVID 2020. **Signature failure: Feb 2018 Volmageddon** — term structure was in contango up to the day before XIV blew up. Mixed in 2022 chop. Worked again in Aug 2024 yen-carry unwind.
- **How to use:** Hard switch viable for vol-sellers (SVIX/SVXY long when ratio <0.92, exit >0.97); soft risk-off overlay for trend-followers; linear scaling of short-vol exposure with contango steepness.
- **Counter-thesis:** It tells you what the market already knows — slope inverts because SPX already fell. The trade is *the VRP itself in disguise*; you're harvesting carry, not predicting. Feb 2018 proves zero predictive value for endogenously generated vol spikes from the short-vol complex itself.
- **Verdict 2026:** **Best vol regime signal for retail.** Cheap, transparent, theoretically grounded, decades of OOS. Understand it is carry-state identification, not crash prediction. **Pair with a vol-of-vol kill switch (VVIX z-score > 3 → flatten short-vol) sized for an 8× Volmageddon, not a typical drawdown.**

### #2. Excess Bond Premium (EBP) + HY OAS

- **Thesis:** Credit-spread sentiment component leads real activity by 6–12 months; widening high-yield spreads compound that signal.
- **Regime variable / horizon:** Risk premium / recession risk; multi-month to ~12 months.
- **Label: PREDICTION for EBP; mostly COINCIDENT for raw HY OAS.** EBP is one of the few genuinely leading indicators in this entire report.
- **Mechanism:** Gilchrist-Zakrajšek (*AER* 2012) decompose bottom-up senior unsecured corp spreads into Merton-style default risk plus residual = EBP. Rising EBP → tighter credit supply → real activity slows 6–12 months later.
- **Data:** FRED `BAMLH0A0HYM2` (HY OAS daily), `BAMLC0A0CM` (IG), Fed publishes EBP CSV monthly. All free, ALFRED-supported. Retail-trivial.
- **Signal characteristics:** EBP rising ≥+0.5σ → 12m recession probability rises sharply (Favara et al. FEDS Note 2016). HY OAS thresholds: <300bp euphoric, 400–500 neutral, >700 stress, >1000 crisis.
- **Implementation reality:** Trivial. Gotchas: HY OAS includes BB-CCC mix shift (use CCC-only for sentiment-pure read); EBP revises modestly due to bond-panel composition changes.
- **OOS track record:** Worked in dot-com, GFC, COVID. Partial false alarm in 2015–16 (energy sector). Caught Dec 2018. **Crucially: in 2022–2024, EBP did not signal recession — correctly identifying that 2022 was a rate-driven repricing, not a credit-driven recession. The single best macro indicator call across this entire menu.**
- **How to use:** EBP >+0.5σ → reduce risk; >+1σ → defensive. Δ HY OAS >+100bp in one month is a meaningful warning regardless of level. HY–IG spread widening is more informative than absolute HY level.
- **Counter-thesis:** Bybee et al. (arXiv 2412.04063, 2024) show ~80% of EBP variation is explained by news-attention factors — partly mood-driven. QE/QT distorted spreads structurally. Sentiment hard to disentangle from default risk.
- **Verdict 2026:** **Top-tier macro indicator for retail use.** EBP is the single most cost-effective regime signal, correctly avoided false-alarming in 2022–2024. Pair daily HY OAS with monthly EBP.

### #3. Faber 10-month / 200-day moving average — as a multi-asset tranched overlay

- **Thesis:** Time-series momentum + drawdown asymmetry means a simple "above MA = risk on" filter cuts left-tail without sacrificing CAGR (Faber 2007, SSRN 962461; Hurst-Ooi-Pedersen 2017 "Century of Evidence").
- **Regime variable / horizon:** Binary above/below 10-month SMA; persistence 6–24 months typical.
- **Label: IDENTIFICATION**, lagging by construction. Not a forecast.
- **Mechanism:** Captures time-series momentum / under-reaction (Moskowitz-Ooi-Pedersen 2012, *JFE*). Bear markets tend to be slow-rolling, giving the filter time to exit.
- **Data:** Monthly close on indices; trivial.
- **Signal characteristics:** ~30–35% of crossings are whipsaws (Hoffstein, "When Simplicity Met Fragility," 2018). Persistence of state averages ~14 months; whipsaw clusters in 2010, 2011, 2015–16, Q4 2018, Q1 2020.
- **Implementation reality:** Trivial. **Critical gotcha: rebalance timing luck.** Different evaluation days produce hundreds of bps/year dispersion (Hoffstein "Tranching"; Zarattini, Gabriel & Pagani 2025, SSRN 5230603). Use 4-tranche staggered rebalance.
- **OOS track record:** Strong dot-com, GFC, 2022. Multiple whipsaws 2011, 2015–16. Faber's own 2013 update notes underperformed buy-and-hold 6 of 8 years 2009–2016. Textbook COVID whipsaw — sold near bottom, re-entered into recovery. Marmi et al. (2009) bootstrap tests cast doubt on whether the risk-adjusted edge is statistically distinguishable from luck once you adjust for parameter cherry-picking.
- **How to use:** **Soft weighting / risk-budget overlay** (e.g., 50% risk below the line) — not a binary hard switch. Apply across a basket (Faber's GTAA) to absorb single-asset whipsaws via diversification.
- **Counter-thesis:** It's just delayed price information. Edge is conditional on prolonged trending declines; in V-shaped corrections (1987, 1998, March 2020, Q4 2018) it is structurally guaranteed to whipsaw. Post-publication Sharpe haircuts on technical signals average 30–50% (Falck-Rebelo-Wang 2021).
- **Verdict 2026:** **The canonical baseline.** Best single price-based regime filter for retail, provided used as a position-sizing tool across multiple assets with tranched rebalancing. Do not run as a hard single-asset switch.

### #4. Chicago Fed ANFCI (adjusted national financial conditions index)

- **Thesis:** 105-variable weekly factor of risk, credit, leverage proxies financial conditions; tightening precedes real-economy weakness — and the ANFCI variant strips out the part already reflected in growth/inflation.
- **Regime variable / horizon:** Financial conditions / liquidity regime. Multi-week; leverage sub-index leads activity by 1–4 quarters.
- **Label:** Mostly **IDENTIFICATION** of current stress, but with documented **PREDICTION** properties at 1–4 quarter horizons via the nonfinancial leverage sub-index (Brave & Butters 2012; Adrian-Boyarchenko-Giannone "Vulnerable Growth" *AER* 2019).
- **Mechanism:** Financial accelerator — tighter credit, falling collateral, deleveraging → reduced spending.
- **Data:** FRED `NFCI`, `ANFCI`, sub-indices. Weekly, free, ALFRED-supported. **Use ANFCI** for a financial-stress signal cleansed of contemporaneous growth/inflation.
- **Signal characteristics:** Threshold ~-0.39 historically (Brave & Butters 2012); >0 = tighter than average; >+1 = stress.
- **Implementation reality:** Trivial. Critical gotcha: backward revisions on each weekly release — naive backtests on current vintage are biased. Use ALFRED.
- **OOS track record:** Big GFC spike. Caught 2015 China stress (ANFCI more responsive than NFCI). Caught 2018 Q4 (ANFCI better than NFCI here). COVID spike. **2022 weakness:** NFCI/ANFCI stayed near zero or negative through most of the 2022 bear market — a real miss because equity vol stayed modest and bank credit conditions remained ample. Brief SVB spike March 2023 then fast normalization.
- **How to use:** ANFCI >0 → reduce equity beta; >+1 → defensive. Δ matters more than level — rapid tightening matters more than steady stress.
- **Counter-thesis:** Mostly a high-dimensional summary of things visible in spot prices (HY OAS, VIX, repo). Correlated with — not leading — equity markets. The 2022 failure is awkward.
- **Verdict 2026:** **Best-of-class financial-conditions index for retail.** Strictly dominates STLFSI. Use ANFCI specifically, not headline NFCI.

### #5. Engstrom–Sharpe Near-Term Forward Spread (NTFS)

- **Thesis:** 18-month forward 3m rate minus current 3m rate statistically dominates 10y-2y in probit recession models because it reflects only the market's near-horizon Fed-easing expectations, undistorted by long-end term premium.
- **Regime variable / horizon:** Recession probability; ~12 months ahead.
- **Label: PREDICTION** — one of the few genuine forecasting models in this list.
- **Mechanism:** Engstrom & Sharpe (FEDS 2018-055; *FAJ* 2019). Inversion only when the market prices imminent Fed easing — and easing happens because the Fed responds to weakness.
- **Data:** Weekly at neartermforwardspread.com (free). Computable from FRED Treasury data.
- **Signal characteristics:** Engstrom-Sharpe argued in Q1 2022 that NTFS was *not* signaling recession even as 10y-2y compressed (FEDS Notes March 2022, "Don't Fear the Yield Curve, Reprise"). NTFS later did invert in late 2022, and the Chicago Fed Letter No. 469 (2022) noted the configuration was "rare … not observed prior to a U.S. recession since 1962." In retrospect, NTFS's early-2022 skepticism was correct — no recession arrived.
- **Implementation reality:** Trivial. Use the published series or rebuild from Treasury forward rates.
- **OOS track record:** Statistically dominates 10y-2y in formal probit comparisons. Slightly less binary failure in 2022 than 10y-2y because it never produced the kind of confident "recession imminent" signal the 10y-2y did.
- **How to use:** Probit output as recession-risk soft weight on equity exposure. NTFS-vs-10y-3m divergence is itself informative.
- **Counter-thesis:** Still relies on yield-curve information; the 2022–2024 episode showed forward-rate decompositions also have limits when QE/QT distort the curve.
- **Verdict 2026:** **Preferred yield-curve signal.** Use this instead of the popular 10y-2y. Combine with EBP for an ensemble macro recession read.

### #6. Factor momentum (1- to 12-month lookback)

- **Thesis:** Past performance of equity style factors predicts next-month factor returns (Ehsani-Linnainmaa *JF* 2022; Arnott-Kalesnik-Linnainmaa *RFS* 2023; Gupta-Kelly *JPM* 2019 "Factor Momentum Everywhere").
- **Regime variable / horizon:** Factor-return state; 1-month forward.
- **Label: PREDICTION / FORECASTING** — strongest documented anomaly in this list.
- **Mechanism:** Most factors are positively autocorrelated. Ehsani-Linnainmaa: avg monthly factor return of +6 bps after a losing year vs +51 bps after a winning year.
- **Data:** Factor ETFs (MTUM, VLUE, QUAL, USMV, SIZE) or Ken French library. Free.
- **Signal characteristics:** Significant in 23 of 51 countries (Ehsani-Linnainmaa); Sharpe ~0.5–0.8 in-sample. Post-publication decay is real but factor momentum has held up better than most anomalies (Cakici et al. 2023).
- **Implementation reality:** Monthly rebalance across 5–6 ETFs; moderate turnover. Parameter sensitivity to lookback (1, 3, 6, 12) is meaningful — diversify across lookbacks.
- **OOS track record:** Worked dot-com, GFC, 2015–16, 2018, 2022 (value's 2022 leadership was predictable from late-2021 factor returns). Mixed COVID (March 2020 reversal hurt mom-of-mom).
- **How to use:** Soft weighting across factor ETFs based on 6-12 month returns. Combine with absolute trend filter (don't load up on a factor when the whole market is in drawdown).
- **Counter-thesis:** Ehsani-Linnainmaa themselves show high-eigenvalue PC factor (market beta) subsumes individual stock momentum — much of "factor momentum" may just be repackaged market momentum. Net of transaction costs and crowding, alpha is smaller than the in-sample headline.
- **Verdict 2026:** **Probably the single best regime-rotation tool for equity-focused retail.** Use with conservative turnover. Tier 1.

### #7. PELT / BOCPD changepoint detection — as adaptive infrastructure

- **Thesis:** Don't model regimes parametrically; just detect structural breaks in real time and adapt downstream models. Pure change detection has nothing to overfit.
- **Regime variable / horizon:** Probability of changepoint at time t. Lead-lag depends on signal-to-noise.
- **Label: IDENTIFICATION** of breaks. Honest — it does not pretend to forecast.
- **Mechanism:** PELT (Killick-Fearnhead-Eckley 2012 *JASA*): O(n) exact dynamic-programming changepoint with penalty. BOCPD (Adams-MacKay 2007): Bayesian online, exact inference, conjugate updates.
- **Data:** Any. Python `ruptures`, R `changepoint`.
- **Signal characteristics:** BOCPD typically signals within 5–20 observations of the shift. FPR controlled by hazard prior / penalty.
- **Implementation reality:** Retail-feasible. Penalty/hazard choice dominates results — same brittleness as state-count in HMMs. Univariate by default; multivariate adds complexity.
- **OOS record:** Strong precisely because it makes no forecasts. Habibi (2022) and Chen et al. (2025) document BOCPD/PELT detecting 2008, 2020, and 2022 inflation regime breaks within days/weeks.
- **How to use:** Meta-signal — when a break is detected, retrain downstream models, reset position sizing, raise risk premia. López de Prado's AFML promotes structural-break-based event sampling.
- **Counter-thesis:** Tells you something changed, not what to do. Useful only with another model.
- **Verdict 2026:** **Tier 1 as adaptive infrastructure.** Every retail algo trader should run a BOCPD or PELT on equity returns and a few macro series to trigger model refits. Cheap, robust, no overfit risk.

## Tier 2 — Solid secondary tools

### #8. Principal Components / Absorption Ratio (Kritzman et al. 2011)

- **Thesis:** Fraction of cross-sectional variance absorbed by top eigenvectors measures market unification; high AR = systemic fragility (Kritzman-Li-Page-Rigobon, *JPM* 2011).
- **Regime variable / horizon:** AR = Σ(top-N eigenvalue) / Σ(all). Multi-week to multi-month.
- **Label: PREDICTION** — one of the genuinely-leading indicators in the price-based class.
- **Mechanism:** When idiosyncratic risk is squeezed out, shocks propagate to all assets; grounded in factor structure.
- **Data:** 11 SPDR sector ETFs daily (free retail proxy for the original 51-industry version).
- **Signal characteristics:** Standardized 15-day-vs-1-year AR ratio is the actionable signal; 1σ AR increase precedes negative SPX over the next month on average.
- **OOS track record:** **Best showcase:** AR spiked starting Aug 2007, well before the GFC. Mixed in 2011, 2015–16 (many false positives). Modest Q4 2018 spike. **COVID March 2020: AR spiked concurrently with the crash, not before — the speed defeated the indicator.** Useful Q1 2022 warning.
- **How to use:** Soft risk-budget toggle — reduce gross at top decile, increase at bottom. Combine with Kritzman-Li turbulence index for richer state.
- **Counter-thesis:** Essentially a smoothed function of cross-sectional correlation (Forbes-Rigobon 2002 *JF* caveat applies — measured correlation is upward-biased in volatile periods). The 2008 success was partly because GFC was a slow-rolling crisis.
- **Verdict 2026:** **One of the best PREDICTIVE indicators** in this list. Recommend computing weekly on the 11 SPDRs as a position-sizing overlay.

### #9. Statistical Jump Model (Nystrup et al. 2020, 2024) — the better HMM

- **Thesis:** Replace EM/Baum-Welch with a clustering objective on temporal features plus an explicit jump penalty λ for state transitions; tune λ by time-series CV.
- **Regime variable / horizon:** K-state hard label; online, no look-ahead.
- **Label: IDENTIFICATION** (online classification, not retrospective smoothing).
- **Mechanism:** Nystrup-Lindström-Madsen 2020 *Expert Systems with Applications*; Nystrup-Kolm-Lindström 2020 *J. Financial Data Science*; Shu-Yu-Mulvey 2024 *J. Asset Management*. Persistence is a controllable hyperparameter (not emergent), so turnover is bounded.
- **Data:** Daily/intraday returns + realized-vol features. Retail-feasible.
- **Signal characteristics:** Higher classification accuracy than MLE-HMM in simulation; Shu et al. 2024 demonstrate strict OOS dominance over HMM on equity downside-risk reduction across US/Germany/Japan.
- **OOS record:** Stronger than vanilla HMM by every metric Nystrup et al. report — Sharpe, drawdown, persistence — across multiple developed-equity markets and breaks.
- **How to use:** 0/1 or scaled risk-on/risk-off overlay; size positions against state probability. Don't trade jumps directly.
- **Counter-thesis:** Still essentially an elaborate vol filter. A simple 20-day realized-vol z-score does much of what the jump model does on equity data, without ML machinery.
- **Verdict 2026:** **Strict improvement over vanilla HMM.** Tier 2 when run with intraday vol features. Implement this instead of any plain Hamilton/HMM regime model.

### #10. MOVE Index (Treasury implied vol) — delta and cross-asset use

- **Thesis:** Rates volatility regime affects equity discount rates, leverage, collateral; rising rates vol leads VIX in specific stress episodes.
- **Regime variable / horizon:** Implied 1m option vol on 2y/5y/10y/30y Treasuries. Days to weeks.
- **Label:** Mostly **IDENTIFICATION** of current rates-vol stress, with weak **PREDICTION** (1–14 days) into equity vol in specific episodes.
- **Mechanism:** Treasuries are global collateral. Rising rates vol → margin calls on basis trades → forced deleveraging → equity vol. Mechanically linked to credit (HY OAS) and repo.
- **Data:** Daily, free via Yahoo `^MOVE`. Not on FRED.
- **Signal characteristics:** Normal range 55–125; >150 severe. March 2023 SVB stress: MOVE rose several days before VIX. April 2025 basis-trade unwind: MOVE spiked, VIX caught up later.
- **OOS track record:** Worked in GFC, 2018 Q4, COVID, SVB 2023, April 2025. **2022–2023:** MOVE >120 for ~18 months while equities recovered — sustained level was a regime feature, not a signal.
- **How to use:** Use Δ MOVE and MOVE/VIX ratio, not level. When ratio spikes (typically >7), bond stress is leading equities — multi-day warning. SOA Sept 2025 paper proposes a MOVE-adjusted VIX → equity allocation rule (cap weight 60–100%); backtest CAGR 14% Jan 2014–Feb 2025 vs static 60/40.
- **Counter-thesis:** Post-QE/QT, structural rates vol is permanently higher (term premium volatile, fewer price-insensitive buyers). Elevated MOVE may be the new normal, not stress.
- **Verdict 2026:** **Useful as delta + cross-asset signal, not as level signal.** Particularly good for catching bond stress that hasn't yet leaked to equities.

### #11. VIX absolute level (percentile-normalized)

- **Thesis:** VIX z-score against trailing-1y window is a useful risk thermometer; fixed thresholds are not.
- **Label: IDENTIFICATION** of current vol state. Not a return predictor.
- **Mechanism:** GARCH-type persistence makes today's IV regime the best naive estimate of next ~5 days' realized vol. R² ~20–25% for VIX → 30-day realized vol; Sarwar (2012) and others document **four structural breaks in the VIX mean since 1993**, making fixed "20" or "30" thresholds non-stationary.
- **Data:** CBOE/FRED daily, free.
- **OOS:** **Catastrophic in Feb 2018** (VIX 13 the week before exploding). **Never crossed 40 in 2022 despite −25% drawdown** — fixed thresholds totally missed it.
- **How to use:** Position sizing — target_vol / VIX scaling, or percentile-normalized z-score against 1y rolling. Hard switch off short-vol when VIX > rolling 1y 90th percentile or 5-day VIX %-change > +50%.
- **Verdict 2026:** Useful as a regime thermostat and for vol-scaling, not as a return predictor. **Always percentile-normalize.**

### #12. Vol targeting / vol-managed exposure

- **Thesis:** Scaling exposure inversely to realized variance produces Sharpe improvement when vol changes are persistent (Moreira-Muir 2017 *JF*).
- **Label: IDENTIFICATION** of current vol regime with weak forecasting via persistence.
- **Signal characteristics:** Daily vol clustering coefficient ~0.7–0.9; persistence days-to-weeks. Moreira-Muir contested — Cederburg et al. (2020) find no improvement in long samples; Barroso-Santa-Clara 2015 show it works specifically for momentum.
- **OOS:** Works when vol changes are persistent (2008, 2020). **Badly when vol spikes are short** (Feb 2018: de-levered into the lows — fully crowded short-vol/vol-target strategies were trapped). Mixed 2022.
- **How to use:** **Position-sizing layer, not a regime switch.** Cap leverage at ~2×; use vol floor (don't over-lever in calm) and vol ceiling (de-lever fast in shocks). Pair with absolute trend filter.
- **Verdict 2026:** **Always-on plumbing, not a "regime model" per se.** Every retail algo trader should run portfolio-level vol targeting; almost none should treat it as a regime predictor.

### #13. Cross-asset correlation regime (rolling stock-bond, stock-commodity)

- **Thesis:** Rising rolling correlations among diversifiers signal a risk-off / inflation regime where diversification fails.
- **Regime variable / horizon:** 60- or 120-day rolling Pearson correlation between SPY/TLT, SPY/DBC, SPY/GLD. Highly persistent regimes (multi-year).
- **Label: IDENTIFICATION** with persistence-driven forecast content.
- **Mechanism:** Macro factor exposure dominates when one shock (typically inflation surprises) drives all assets. **Forbes-Rigobon 2002 (*JF*) caveat: measured correlation spikes during crises are partly heteroskedasticity artifact** — don't over-react to a single spike. Use volatility-adjusted (DCC-GARCH or rank correlation) or interpret raw rolling correlations skeptically.
- **Signal characteristics:** Stock-bond regime was +0.35 in 1970s–99, −0.29 in 2000–21, +0.65 in 2022. Regime persistence multi-year.
- **How to use:** Position-sizing input — when 60-day SPY/TLT correlation > +0.2, reduce reliance on bond hedges in 60/40 or risk-parity sleeve; lean into trend-following / cash.
- **Verdict 2026:** Real and economically meaningful regime variable; actionable insight largely collapses to "don't assume −0.3 stock-bond correlation will return."

### #14. XGBoost / Random Forest on macro+price features (with rigorous CV)

- **Thesis:** Tree ensembles capture nonlinear interactions between term spread, credit spread, equity drawdown, employment data that linear probit misses.
- **Label: PREDICTION / FORECASTING** when done with discipline.
- **Mechanism:** Gu, Kelly & Xiu (2020 *RFS*) show trees and NNs dominate linear models — but most gains come from cross-sectional return prediction, not time-series regime classification per se.
- **Critical methodology warning:** Johansson & Meldrum (Fed FEDS 2020-38) — RF/XGBoost/NN all beat probit under standard k-fold CV, but **with proper time-series CV the rankings reverse and ML gains shrink substantially**. Standard k-fold violates causality on time series.
- **Implementation reality:** XGBoost/LightGBM retail-feasible (CPU, minutes). Gotchas: NBER recession labels are revised retroactively — real-time labeling is itself a forecasting problem. Triple-barrier and meta-labeling (López de Prado AFML Ch. 3) address path-dependent labels.
- **OOS track record:** Modest improvements over yield-curve probit and naive vol-quantile baselines. Most published "60–80% accuracy" numbers do not survive deflation for multiple testing.
- **How to use:** Build a recession-probability nowcast (RF on yield curve + credit spreads + employment momentum + financial conditions) and use it to scale equity exposure. **Avoid using ML for 6+ month forecasts; noise is too high to clear deflated significance.**
- **Counter-thesis:** With ~3–5 NBER recessions in modern data, any flexible ML model can fit perfectly. Sample size at the latent-variable level is the binding constraint, not data volume.
- **Verdict 2026:** **Tier 1 with discipline (purged CV, deflated Sharpe, tracked trial counts, interpretable features). Tier 4 without.** Beats raw HMM/GMM. Doesn't reliably beat probit-on-yield-curve for the recession problem.

### #15. Regime-conditional factor / risk models (Ang-Bekaert tradition)

- **Thesis:** Factor risk premia are not stationary; estimate factor returns/risk conditional on detected macro regime.
- **Label: PREDICTION** conditional on a regime model.
- **Mechanism:** Bear/high-vol regimes favor low-vol and quality; bull regimes differ in value/momentum dynamics.
- **OOS record:** Ang-Bekaert 2004 *FAJ* — regime-switching dominated static OOS in multi-asset (cash/bonds/equities) universes; alpha within all-equity hard to capture. AQR's own posture (Asness, Ilmanen): factor *timing* is hard; factor *exposure* is robust.
- **How to use:** **Conservative use — regime-conditional risk (covariance, vol, drawdown) for portfolio construction, not regime-conditional return timing.** This is the AQR house view.
- **Counter-thesis:** "Regime" may be endogenous to recent factor returns; low-vol does well after high-vol periods (mean reversion in vol), not because of a regime per se.
- **Verdict 2026:** **Use regime models to scale risk, not to time factors.** Ang-Bekaert multi-asset result is the most defensible commercial application.

## Tier 3 — Use carefully, with strong caveats

### #16. Yield curve 10y-3m / 10y-2y

- **Label: PREDICTION** — but with massive lead-time variance.
- **Lead time distribution:** 6–24 months historically; **the 2022 inversion now exceeds the upper bound at 27+ months with no NBER recession through May 2026**. Harvey's own evolution: Jan 2023 "this time could be different"; Oct 2024 NPR Indicator: "premature to declare false signal" but conceded "at some point I would have to."
- **OOS:** Worked dot-com, GFC. Did not invert 2015–16 (correctly no US recession). Near-inverted Dec 2018 — borderline. COVID inversion technically correct but recession was exogenous. **2022 is the first clear failure of 10y-3m.**
- **Counter-thesis:** Harvey 2024 (Fortune): reflexivity — companies/Fed respond to the curve, suppressing the very recessions it would otherwise predict. Sample size is 8 recessions — essentially anecdotal at probit confidence intervals.
- **Verdict 2026:** **Useful as one input in a composite, never as a switch.** NTFS variant > 10y-3m > 10y-2y. The 2022–2024 episode is a genuine wound, not a flesh wound — binary backtest rules will whipsaw.

### #17. Markov-switching / HMM on returns (Hamilton classics)

- **Label: IDENTIFICATION strong, PREDICTION modest, FORECASTING weak.**
- **The smoothed-vs-filtered trap:** every blog/paper plot of "HMM beautifully identifies regimes" uses the Kim smoother, which conditions on the full sample — i.e., look-ahead bias. Real-time filtered probabilities are far noisier.
- **Practitioner critique:** Nystrup et al. (2017, 2018) document that real-time HMM state sequences switch far more frequently than smoothed sequences shown in papers — high turnover and Sharpe degradation. Bulla et al. (2011, *J. Asset Management*): profitable HMM strategies exist only with confidence thresholds >95%, which filters out most signals → very low signal frequency. That effectively concedes the raw HMM is too noisy to trade.
- **Hess (2006):** "a wrong regime forecast may lead not just to a non-optimal but to a *detrimental* allocation in the contrary direction." HMM mis-classifications are not symmetric in cost.
- **Verdict:** Most overhyped model class in retail fintech. **Implement the statistical jump model (#9) instead.** Useful only as a transparent risk overlay with strong hysteresis.

### #18. Sahm Rule

- **Label: IDENTIFICATION / NOWCAST.** Sahm herself: "designed to indicate that the U.S. economy is in the early months of a recession, rather than forecasting future recessions" (Sahm 2019). The CRS (IN12410): "the Sahm rule has typically been triggered in the beginning months of a recession, meaning that it does not predict recessions so much as indicate one is occurring." **Anyone selling it as predictive is misusing it.**
- **2024 false positive:** July 2024 print 0.53 → no NBER recession through May 2026. Sahm's own Bloomberg op-ed (Aug 2024) "My Recession Rule Was Meant to Be Broken"; blamed labor-supply shocks (immigration, returning workforce) — ~half the unemployment increase came from entrants, not job-losers. Powell (July 2024 FOMC): "statistical regularity, not an economic rule."
- **How to use:** **Confirm-not-predict.** Risk-reduction filter when Sahm > 0.35 AND ANFCI > 0 AND HY OAS > 500bp.
- **Verdict 2026:** Coincident indicator with marginal alpha for retail algo. The 2024 episode destroyed the "100% accurate" marketing claim.

### #19. COT (Commitments of Traders) — commodities and FX only

- **Label: IDENTIFICATION** of crowded positioning, **contested PREDICTION** depending on asset class.
- **Asset-class differentiation matters enormously:**
  - **Commodities:** ~65–70% accuracy in commercial-hedger decile signals for 6-month direction in agriculture/energy.
  - **S&P 500 futures:** **Mostly NEGATIVE result.** CXO Advisory: "evidence does not support belief that aggregate S&P 500 Index futures positions reliably predict future stock market returns." Foster-Kharazi: relationship unstable across time; weekly COT lag prevents real-time exploitation.
  - **Currencies:** Mixed; high false-positive rate at extremes.
- **How to use:** Free CFTC data; 3-year COT Index or z-score, extremes >90/<10.
- **Verdict 2026:** **★★★ in commodities/FX; ★ in equity indices.** Use for commodity vol and FX carry regime, not S&P timing.

### #20. Conference Board LEI

- **Label: PREDICTION** with material false-alarm rate; **24-month false alarm 2022–2024.**
- Conference Board capitulated Feb 2024: "the leading index currently does not signal recession ahead." Quietly drifted threshold from −4.0% → −4.4% → −4.1% across 2022–2024 — exactly the regime-overfit critics predicted.
- Over-weighted to manufacturing (3 of 10 components) in a 12% manufacturing economy. Yield-spread component double-counts with #16.
- **How to use:** 6-month annualized growth rate of LEI > binary 3D rule; build your own LEI from FRED components (avoids paywall and enables ALFRED).
- **Verdict 2026:** One soft input among several; do not weight heavily.

### #21. AAII Sentiment Survey (extremes only)

- **Label: IDENTIFICATION** with weak contrarian **PREDICTION** at >2σ extremes.
- **Decay:** AAII's own analysis — predictive power across most studied indicator/return relationships derives from the first 16 years (1987–2003). Only one neutral-sentiment signal triggered between 2003 and 2014. CXO Advisory: weak/inconsistent forward S&P 500 relationships post-2010.
- **2022 failure:** sustained "extreme bearish" for nine consecutive months without producing the contrarian buy. Schwab May 2025: attitudinal washouts no longer coincide with behavioral (positioning) washouts.
- **Verdict 2026:** Modest contrarian utility at >2σ only. Meta-sentiment input, not standalone signal.

### #22. CBOE Put/Call ratio — OI-based equity only

- **The 0DTE problem:** post-2022, 0DTE volume is >50% of SPX daily — structurally depressed daily P/C baselines, breaking pre-2022 thresholds.
- **How to use post-2022:** OI-based P/C (overnight open interest unaffected by 0DTE); 21-day MA smoothing; rolling z-score against trailing 6-month. **Headline daily total P/C is functionally broken — discard.**
- **Verdict 2026:** Damaged but not dead. Use OI-based equity P/C with rolling z-scores only.

## Tier 4 — Avoid as primary signals

### #23. Variance Risk Premium (BTZ 2009)

- **Label:** Originally **FORECASTING** of 1–6m equity returns.
- **Decay:** Papagelis (2025, *JFM*) finds slopes statistically insignificant Feb 2012 → Sep 2022 across all horizons. **The headline pre-2012 R² has substantially weakened OOS — post-publication arbitrage.**
- **Use as carry rationale (you're paid VRP for selling vol), not as return predictor.**

### #24. CBOE SKEW Index

- Marketed as PREDICTION; empirically poor forward signal. Did not warn before Aug 2015, Feb 2018, COVID, 2022. Bevilacqua-Tunaru: only the put-only component has meaningful tail-risk content; the headline is contaminated by call-side activity.
- **Verdict:** Mostly a marketing artifact. Skip.

### #25. ISM Manufacturing PMI

- **2022–2024 problem:** sub-50 for 16+ consecutive months — longest sub-50 streak without recession in series history. Services PMI stayed above 50 throughout.
- Manufacturing is 11% of US GDP — PMI is now a sector indicator, not macro.
- **Verdict:** **Demoted to sector rotation (XLI, materials) signal only.** Pair with Services PMI; treat as a sector-cycle indicator.

### #26. Copper/gold ratio

- CFA Institute (March 2023) "Is the Copper–Gold Ratio a Dependable Leading Indicator on Rates?": ratio neutralizes USD effects, making it disconnect from Treasury yields (which ARE positively dollar-correlated). Bloomberg Dec 2020: "Copper-Gold Ratio Breaks From Treasury Yields in New Normal."
- 2022–2024: ratio collapsed to multi-decade lows while 10y yields rose — pure divergence.
- **Verdict 2026:** **Skip.** Famous, intuitive, empirically useless for retail algo. Use HY OAS or ANFCI instead.

### #27. Dual MA crossover (golden/death cross)

- Redundant slower version of the 200-day. ~33 signals on S&P in 66 years — sample too small to draw inference. FactSet 1998–2018 found death crosses often preceded positive 6-month returns (sample dominated by post-2009 bull).
- **Verdict:** No incremental information over the 200-day alone.

### #28. ADX, Hurst exponent

- **ADX:** No published OOS evaluation in top-tier journals. Coincident at best — "ADX rising" is a lagged second derivative of price. Replaceable with simpler |price − SMA| / ATR construction.
- **Hurst:** Heavy parameter sensitivity; H typically hovers near 0.5 ± wide noise for liquid equity indices. Cornell Data Science 2022: Hurst-based regime switching produced higher returns and higher risk — no Sharpe improvement. Most "Hurst > 0.6" results are in-sample or window-dependent.
- **Verdict 2026:** Avoid both as primary regime classifiers for retail.

### #29. Breadth indicators ($SPXA200R, McClellan, A/D)

- Coincident or barely-leading. In 1999 breadth deteriorated for >18 months before the top. Mag-7 distortion in 2023–24 made S&P 500 mask catastrophic small-cap breadth without consequence.
- **Useful only at extremes as contrarian re-entry** (<20% above 200dma coincided with Mar 2009, Mar 2020, Oct 2022 bottoms). Not useful in normal markets.

### #30. Donchian channel breakouts (Turtle 20/55-day)

- Public disclosure of Turtle rules (2003–04) coincides with sharp decay in commodity TF; BTOP50 Sharpe collapsed from ~0.7 pre-2003 to ~0.2 over 2010–2019.
- **Niche:** useful only for *cross-asset, futures-based* implementations (KMLM, DBMF). Not useful as a single-asset regime classifier for equity-focused retail.

### #31. Deep learning regime classifiers (LSTM, GRU, Transformer)

- **No convincing peer-reviewed evidence that any DL architecture reliably beats well-tuned XGBoost (or probit) for regime classification at monthly-to-yearly horizons using retail data.**
- Andreoletti (2026 arXiv 2604.00064) formally shows that under squared loss for weakly conditional series like returns, added Transformer expressivity *increases* prediction variance without reducing bias — transformers underperform a linear benchmark on a majority of forecasting windows in high-frequency EUR/USD.
- Den & Vincent (2026 arXiv 2603.16985): "state-of-the-art time-series Transformers often **underperform even vanilla Transformers** on financial tasks."
- Overfitting risk catastrophic — with ~5 recessions and millions of parameters, DL is essentially memorizing the GFC.
- **Verdict 2026:** Avoid for regime classification. Compute is feasible but expected economic value net of overfitting is negative.

### #32. STLFSI, defensive/cyclical sector ratios, CNN Fear & Greed, Investors Intelligence

- **STLFSI:** strictly dominated by ANFCI; methodology has been redefined three times (LIBOR → backward SOFR → forward SOFR). Skip.
- **XLY/XLP, XLF/XLU:** practitioner favorites with no rigorous OOS evaluation; composition drift (XLY is ~25% Amazon/Tesla now). Visual confirmation at best.
- **CNN F&G:** Farrell & O'Connor (2024 *Finance Research Letters*) document **post-publication decay** in Granger-causality predictability. Equal-weight composite of signals already covered above.
- **Investors Intelligence:** paywalled; AAII dominates on cost-benefit.

## Composite head-to-head ranking (best → worst for retail algo, 2026)

| Rank | Model | Category | Primary use |
|---|---|---|---|
| 1 | **VIX term structure (VIX/VIX3M)** | Vol | Vol-selling switch; risk-off overlay |
| 2 | **EBP + HY OAS** | Macro/credit | Risk overlay; recession-prob input |
| 3 | **Faber 200d / 10mo SMA (multi-asset, tranched, soft-weighted)** | Price | Strategy filter; risk budget |
| 4 | **ANFCI (Chicago Fed adjusted)** | Macro/liquidity | Risk overlay |
| 5 | **Engstrom-Sharpe NTFS** | Macro/rates | Recession-probability input |
| 6 | **Factor momentum (6–12mo)** | Cross-sectional | Factor ETF rotation |
| 7 | **PELT / BOCPD** | Statistical | Model-retraining infrastructure |
| 8 | **Absorption Ratio (PCA on SPDR sectors)** | Cross-asset | Risk budget |
| 9 | **Statistical Jump Model (Nystrup et al.)** | ML/statistical | Risk-on/risk-off overlay |
| 10 | **MOVE Index (Δ and ratio to VIX)** | Vol/rates | Short-horizon risk sizing |
| 11 | **VIX absolute (percentile)** | Vol | Position-sizing thermometer |
| 12 | **Vol targeting** | Plumbing | Always-on portfolio sizing |
| 13 | **Cross-asset correlation regime** | Cross-asset | Portfolio construction |
| 14 | **XGBoost on macro+price (with rigorous CV)** | ML | Recession nowcast |
| 15 | **Regime-conditional risk (Ang-Bekaert)** | ML/multi-asset | Multi-asset SAA |
| 16 | **Yield curve 10y-3m / 10y-2y** | Macro/rates | One input only |
| 17 | **Markov-switching / HMM on returns** | Statistical | Implement jump model instead |
| 18 | **Sahm Rule** | Macro | Confirm-not-predict |
| 19 | **COT (commodities/FX)** | Positioning | Commodity & FX only |
| 20 | **LEI** | Macro composite | Light soft input |
| 21 | **AAII (>2σ extremes)** | Sentiment | Meta-sentiment cross-check |
| 22 | **OI-based equity P/C** | Options | Damaged but usable |
| 23 | **VRP (BTZ 2009)** | Vol | Carry rationale only |
| 24 | **CBOE SKEW** | Options | Skip |
| 25 | **ISM PMI** | Macro | Sector-rotation only |
| 26 | **Copper/gold ratio** | Cross-asset | Skip |
| 27 | **Dual MA crossover** | Price | Redundant with #3 |
| 28 | **ADX, Hurst** | Price | Avoid as primary |
| 29 | **Breadth indicators** | Price | Extremes only |
| 30 | **Donchian breakouts (single-asset equity)** | Price | Futures multi-asset only |
| 31 | **Deep learning regime classifiers** | ML | Avoid |
| 32 | **STLFSI, defensive/cyclical ratios, CNN F&G, II** | Various | Skip; redundant or paywalled |

## Final synthesis — what to actually build

For a retail algo trader on Alpaca with $5k–$100k and a 3–12 month horizon, the highest-leverage regime infrastructure is a **three-layer stack**:

**Layer 1 — Always-on risk plumbing (no regime claims required).** Portfolio-level vol targeting capped at ~2× leverage with both a vol floor (don't over-lever in calm regimes — Feb 2018 lesson) and a fast de-levering ceiling. Tranched monthly rebalance across 4 evaluation days (Zarattini-Gabriel-Pagani 2025). A PELT or BOCPD changepoint detector on equity returns and a few macro series, triggering downstream model refits when breaks fire.

**Layer 2 — A small set of orthogonal regime signals, each labeled honestly.** The minimum-effective ensemble: (a) **VIX/VIX3M slope** (vol carry / risk-off identification, 1–20 days); (b) **EBP + HY OAS Δ** (credit-driven recession prediction, 6–12 months); (c) **ANFCI** (financial conditions identification, weekly); (d) **Faber multi-asset trend filter** (price regime identification, monthly). These four together capture ~80% of the actionable regime signal available to retail at near-zero cost. Combine as **soft probabilistic weights (0–1) on base strategy gross exposure**, not as hard switches — hard switches are documented to whipsaw across every published OOS evaluation.

**Layer 3 — Strategy-specific overlays.** Factor momentum for equity-factor ETF rotation (monthly); regime-conditional **risk** estimates (not return timing) for multi-asset allocation; OI-based equity P/C z-score and AAII >2σ extremes as soft contrarian filters layered on top.

**What to NOT build:** Hard binary regime switches on any single indicator. ML regime classifiers without purged CV + deflated Sharpe + tracked trial counts. Deep-learning regime models. Yield-curve-only or Sahm-only recession switches. Any signal validated mainly on 2008. Anything trained on revised FRED data when ALFRED vintages are available.

**The single hardest discipline.** When a regime signal disagrees with your strategy, the dominant error is to **add another regime signal until something agrees**. Resist this — that path is exactly the multiple-testing trap that the Harvey-Liu-Zhu (2016) and Bailey-López de Prado (2014) literature warns against. Pre-commit your ensemble in writing, document every model you tried (not just the ones you kept), and deflate your Sharpe by trial count. Almost everyone running ML regime models in retail is using a 2σ threshold against an effective trial count in the hundreds — i.e., guaranteed false discovery.

**One-line decision rule.** If you cannot articulate the macroeconomic or microstructural theory of the signal AND the deflated Sharpe ratio after accounting for the number of trials you ran, you should not be trading the regime model. A VIX-term-structure overlay + EBP-led risk dial + Faber multi-asset trend filter + BOCPD safety net covers ~95% of the achievable retail edge in regime-based trading. The remaining 5% is not worth the overfitting risk.