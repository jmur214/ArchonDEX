<!-- Research prompt #2 — synthesized 2026-05-31 from a 7-lens brainstorm workflow. Complement to prompt #1. Self-contained; analyst has no codebase access. -->

# ArchonDEX — External Research Prompt #2: Execution, Alt-Data, Tax, Tail-Risk Construction, and Deployment

**For the AI research analyst reading this:** You have **no access to our codebase, data, or prior internal documents.** Everything you need is inline below. Do not ask for files; reason from the embedded context and the open literature. Where you cite a result, cite it properly (author, year, venue/working-paper) and state whether the evidence is **strong** (replicated, out-of-sample, adversarially tested), **thin** (single study, in-sample, or small-N), or **folklore** (widely repeated, weakly evidenced). We would rather hear "this doesn't work / there is no good evidence" than receive a confident answer built on a thin reed. Effect sizes must come **with uncertainty** (CI, SE, or an explicit range), not as bare point estimates. If a question's honest answer is "the literature can't resolve this at your scale," say so and explain why.

---

## System context (read this first)

**ArchonDEX** is an autonomous algorithmic trading system. Profile:

- **Capital:** small retail, ~$5–15K AUM, growing to low-six-figures over years. **TAXABLE individual account** (no tax-advantaged wrapper).
- **Instruments:** US equities, **daily bars**, long-biased (some long/short). ~109-ticker S&P 500 subset. Survivor price history to 1962; delisted names missing pre-2020 (a survivorship gap we already bound separately).
- **Strategy:** 6-edge ensemble (cross-sectional momentum, low-vol, value / quality / profitability factors), weighted-sum combine, ATR-based risk sizing, up to 10 concurrent positions, 30%-of-equity single-name cap.
- **Honest performance:** baseline Sharpe ~**0.81** on a 12-year window (2014–2025), CAGR ~8%, max drawdown ~−14%. Borderline under Deflated-Sharpe / Minimum-Backtest-Length at ~260 accumulated trials — a **plausibly-real but not formally-validated modest edge**.
- **Validated asset:** an HMM regime classifier that is **genuinely predictive of forward drawdowns** (causal AUC ~0.89 @ 5 days). We trust and act on this crisis/regime probability.
- **Repeatedly failed on rigorous re-test:** overlays on the base (vol-targeting, confidence-gating) — short-window false positives that **reverse on longer windows**.
- **Objective:** **NOT pure Sharpe.** At this AUM a smooth 1%/yr edge is meaningless in dollars, so **asymmetric upside / positive skew / tail-capture is a co-equal objective.**
- **Measurement discipline (already strong):** block-bootstrap CIs, Deflated Sharpe, Minimum Backtest Length, PBO/CSCV, substrate-honesty. **We gate on `ci_low`, not point estimates.** A point estimate of 0.45 with `ci_low = 0.10` does not clear a 0.4 gate.
- **Parked for later:** an LLM-as-analyst layer (theme / narrative conviction), deliberately deferred until the quant bones are maxed.
- **Known deployment facts to use:** the live execution layer is **unwritten** (broker = Alpaca by current default, never cost-validated). Sub-$25K equity means **PDT / settlement constraints apply.** A prior internal measurement put **after-tax Sharpe at −0.577 vs pre-tax ~0.984** — tax drag is a first-order, account-specific killer here, not a footnote.

**Already covered in Research Prompt #1 — do NOT re-derive these:** position sizing / concentration / optimal position count, regime→exposure mapping (how much to de-risk on a crisis signal), the retail alpha frontier, convexity / tail-strategy *structure*, multiple-testing N management, and survivorship-bias bounding. Prompt #2 is the **execution, alternative-data, tax-mechanics, tail-risk-construction, and live-deployment** complement. Where a question is adjacent to a Prompt-#1 topic, the framing below states the orthogonal axis it owns — stay on that axis.

---

## What we want from you

For **every** question: (1) name the **decision it informs** for us (we restate it so you can optimize your answer for it); (2) give **effect sizes with uncertainty**; (3) **cite**, and **tier each citation strong / thin / folklore**; (4) tell us where the honest answer is **"this doesn't work" or "no usable evidence at your scale."** Scale realism is mandatory — an answer that's true at $1B AUM and false at $10K is a wrong answer for us. Where your recommendation depends on a parameter we haven't pinned (e.g., turnover, holding period), give the answer **as a function of that parameter** and identify the inflection point.

---

## TIER 1 — Immediately actionable, deepest treatment requested

These four directly gate whether the borderline base edge is even deployable. Treat them as the core of the report.

### Q1. Slippage / market-impact cost model for a daily-rebalanced equity book at retail size — and the Sharpe-sensitivity to mis-specifying it.

**Decision it informs:** whether to paper-trade / ship the base ensemble at all (does `ci_low` survive realistic costs?), the exact cost parameters to harden into the backtest, and whether to cut rebalance frequency to reduce cost drag.

The backtest currently prices fills with at-most a crude flat assumption — no explicit spread, market-impact, or per-trade-bps term. For S&P large-caps at $5–50K clips, true *market impact* is plausibly negligible, but **half-spread + commission-equivalent + the gap between the assumed fill price (e.g., next-open) and the achievable fill** is not. We need:

- The most **defensible, citation-grounded cost model** for this regime: a half-spread term + a square-root impact term (Almgren et al.; Kyle-λ-style), with the impact term shown to be **provably small** at $5–50K notional in liquid names — quantify "small" in bps with a source.
- A **sensitivity sweep**: how many **bps of added round-trip cost** moves a 0.81-Sharpe, ~8%-CAGR daily-rebalanced book's `ci_low` below a 0.4 kill threshold? Give the approximate bps-per-Sharpe-point translation for a book at this turnover (state your turnover assumption and vary it).
- Explicitly separate **strong evidence** (TAQ-based spread estimates for large caps, published impact-law calibrations) from **folklore** ("just use 5 bps").

### Q2. Execution timing for a signal computed on daily CLOSE — next-open MOO vs MOC vs VWAP/TWAP slice vs limit-with-fallback — and how much backtested edge is actually capturable.

**Decision it informs:** which execution timing to standardize in **both** backtest and live (they must match — backtest/production mismatch is our recurring bug class), and whether to **un-defer intraday-bar accumulation** to model fill timing honestly.

The signal is computed on the close, so trades execute on a **later** bar — an unavoidable signal-to-fill gap. We have **no intraday data**, so the backtest today can only honestly assume open or close, not an intraday VWAP. We need:

- The **alpha-decay-per-hour (or per-bar)** profile for *these specific factor families* (cross-sectional momentum, low-vol, value/quality). Which fill point (next-open MOO, next-close MOC, intraday slice) is both **achievable at retail** and **least alpha-destroying**? Quantify the expected edge haircut at each choice.
- Whether the **open vs close** choice systematically biases the backtest optimistic, and by roughly how much for daily cross-sectional factor signals.
- A clear verdict on whether honest fill-timing modeling **requires** us to start accumulating intraday bars now, or whether a defensible next-open / next-close convention suffices given our holding period.

### Q3. Execution mechanics for the **validated HMM crisis signal** during real drawdown conditions — gaps, halts, liquidity evaporation.

**Decision it informs:** the order-type and timing protocol for regime-driven de-grossing in live trading (market vs marketable-limit vs stop; open vs intraday), and the **haircut to apply to the backtested benefit of the HMM signal** to account for un-executable crisis fills.

Prompt #1 covers *how much* to de-risk on a crisis signal. This is the orthogonal **can-the-trade-fill** axis. Our most valuable asset (the AUC-0.89 @5d classifier) is most valuable exactly when execution is worst. A daily-bar system acts at most once/day: a crisis flagged at today's close can only be acted on at tomorrow's open, which in a real crash often **gaps 5–15% against you before a single share trades.** We need:

- Evidence on **overnight-gap distributions** conditional on the prior session being a crisis-onset day (how fat is the gap tail you eat by being a once-a-day actuator?).
- **Trading-halt / limit-down (LULD) mechanics** and how they interact with a daily-bar system's single action window — what fraction of the protective trade realistically fills, and at what price degradation.
- **Order-type guidance** for the crisis-exit path: market (certain fill, uncertain price) vs marketable-limit (price floor, fill risk) vs stop (slippage-through) — with the realized-cost tradeoff in crash conditions.
- A defensible **backtest haircut** so we don't credit the HMM signal with fills the market won't give us. If the honest answer is "a daily-bar system structurally cannot capture much of this protective value," say so plainly.

### Q4. The empirical backtest→live Sharpe haircut for a daily-bar retail equity system, and the pre-registered forward-validation gate before risking real capital.

**Decision it informs:** the pass/fail gate and minimum duration for the paper-trading phase before committing real money — potentially a **no-deploy** decision for a borderline edge.

Our backtest discipline is elite, but the live layer has never run, and the base edge is borderline (0.81, fails MBL/DSR at ~260 trials). A typical 30–50% live haircut would push realized Sharpe under 0.4. We need:

- An **honest prior** on the in-sample/backtest → live realized Sharpe gap (PSR-vs-live degradation) for daily-bar retail equity systems, with sources and a range — separating the portion DSR already removes from the residual execution/selection haircut it doesn't.
- The **paper-trading sample size and statistical test** (forward PSR, SPRT/sequential test) required to *confirm* the backtested edge survived the transition, given a borderline true Sharpe — how many trading days / trades before a confirm-or-refute is statistically honest?
- The conditions under which the correct answer is **"do not deploy this edge"** rather than "deploy and monitor."

---

## TIER 2 — Strategic (orthogonal-information & tail-objective alignment)

### Q5. Which retail-accessible, free-or-cheap alt-data feeds carry **incremental, non-decayed** signal over price+fundamentals for a daily large-cap US book — and which are hype?

**Decision it informs:** which (if any) alt-data feed to ingest into the feature foundry first, vs concluding alt-data is net-negative-EV at this scale and staying price/fundamental-only.

Candidate feeds: short interest / days-to-cover, options OI / skew, insider transactions, 13F / ETF flows, Google Trends, earnings-call NLP, retail-sentiment. For each, triage on: **(a)** free/cheap and daily-cadence at retail, **(b)** covers liquid S&P 500 names, **(c)** peer-reviewed or robust evidence of **incremental** signal *after controlling for the price/fundamental factors we already harvest*, **(d)** crowded / decayed as of 2026. We need the honest verdict that most published alt-data alpha is large-cap-saturated, capacity-constrained, or already arbitraged — and which one or two feeds, if any, survive that filter.

### Q6. Which **non-price leading indicators** measurably improve a regime/crisis classifier's **forward** power vs a price-only HMM — and would they lift causal AUC or just inflate trial count?

**Decision it informs:** whether to expand the HMM input panel with specific non-price leading features (and which), vs keeping the validated price-only classifier untouched because candidates are coincident-not-leading.

This is the highest-leverage place to add alt-data because we already **trust and act on** this signal. Candidates: VVIX / vol-of-vol, options-implied skew / term structure, credit spreads (HYG/LQD), short-interest spikes, cross-asset flows, breadth / dispersion. Our prior internal work found most candidates **coincident, not leading** (VIX term structure trailed; a VVIX-proxy was the lone salvageable non-price signal at ~AUC 0.64). For each candidate: is the forward-predictive lift real and out-of-sample, or an artifact of fitting to the handful of historical crisis events? Address the **multiple-testing burden** of panel expansion explicitly — a marginal AUC gain that costs 20 trials of N may be net-negative under our DSR accounting.

### Q7. Which portfolio-construction choices **preserve vs destroy positive skew**, independent of their Sharpe effect — and what's the realistic factor-crash / crowding tail of *this specific* 6-edge ensemble?

**Decision it informs:** whether to replace naive weighted-sum with a **tail-aware / crowding-penalized** combine and/or **skew-aware rebalance rules** (trim-laggards-not-winners, let-winners-run bands, relaxing the single-name cap for momentum-confirmed names), and whether to tilt edge selection toward convex/positive-skew legs and away from fat-left-tail legs.

Two coupled sub-questions, both owned by this item (Prompt #1's convexity work is *structure*; this is *construction mechanics and ensemble crowding*):

- **Skew-hostility of standard construction.** Periodic rebalancing mechanically sells winners / buys losers (short-gamma, negative-skew-inducing); risk-parity down-weights the high-variance names that produce convex right tails; a 30% single-name cap truncates a runaway winner. Quantify, with sources, which construction levers quietly harvest the right tail away — and which preserve it. We need this scored on **skew/upside-capture, not Sharpe**, because a construction that lifts Sharpe 0.1 while killing the tail is self-defeating for our objective.
- **Factor-crash tail of the ensemble.** The validated HMM predicts *market* drawdowns; it is blind to a **factor-internal crash** (Aug-2007 quant quake; 2009/2020 momentum reversals; 2020–21 value/low-vol whipsaws) where our own crowded legs unwind while the index is flat. Our edges are **not independent** (we observe intra-cluster correlations up to ρ≈0.99 in some legs), and naive weighted-sum double-counts crowded directions. Momentum and low-vol have fat left tails / negative skew when they unwind — meaning the base may be **structurally short the convexity our objective wants.** Quantify the joint factor tail and whether the ensemble is implicitly net-short volatility, and say whether a crowding-aware reweight is warranted *before* any overlay is worth testing.

---

## TIER 3 — Methodological & operational (tax mechanics, cadence, ML crossover, CV protocol)

### Q8. The tax-aware turnover frontier and lot-level after-tax modeling for a daily cross-sectional book in a taxable account.

**Decision it informs:** (a) whether to invest in a holding-period-aware long-term-gains-deferral overlay at all vs accepting the strategy is tax-incompatible at retail, and the target turnover/holding-period before pre-tax alpha bleed exceeds tax saving; (b) whether to make **after-tax-Sharpe `ci_low`** (not pre-tax) the primary gate for all future overlay A/Bs, and which **lot-accounting method (HIFO / specific-lot / FIFO)** to implement deterministically in the harness.

Our largest documented deployability killer is the after-tax Sharpe collapse (−0.577 vs +0.984 pre-tax; a 1.56 gap). We need:

- The **literature-backed recoverable fraction** of that gap from tax-aware rebalancing / gain-loss deferral / the after-tax efficient frontier, and **where the inflection is** — forcing positions past the 1-year long-term boundary mechanically degrades a signal whose edge decays in days. Express recovery as a function of target holding period.
- The **literature-correct way to model lot-level tax accounting deterministically** inside a daily backtest (specific-lot ID, HIFO vs FIFO, mark-to-tax-year), so after-tax becomes a first-class reproducible measurement, not a post-hoc adjustment. Note that an overlay that's a pre-tax drag can be an after-tax *improvement* (anything that cuts short-term realizations) and vice versa — so the gate choice flips verdicts.
- **Tax-loss-harvesting efficacy at our scale**, honestly: at $5–15K AUM with the **$3K/yr net-loss-against-ordinary-income cap**, the **61-day wash-sale window**, lot granularity, and few uncorrelated substitutes in a 109-name concentrated book — what is the realistic annual harvested-loss yield in **dollars** vs the turnover/tracking-error cost it adds? Is there an **AUM threshold** below which a purpose-built TLH layer is not worth building? We expect the honest answer may be "TLH is marginal until well above your current AUM" — confirm or refute with numbers.

(If, and only if, the evidence is strong, you may briefly note whether the validated HMM could **time tax realizations** — defer gains in calm, harvest losses ahead of predicted crisis — as a lever distinct from gross-exposure scaling. Keep this to a paragraph; it's speculative.)

### Q9. The empirically-correct **rebalancing cadence + no-trade-band** for this signal-decay profile, and whether a between-rebalance de-risking layer survives long-window block-bootstrap.

**Decision it informs:** the production rebalance schedule, whether to add a no-trade band / turnover budget, and whether de-risking should be an **event-driven interrupt** (fires when HMM crosses threshold) decoupled from the periodic rebalance.

We generate daily signals but have only ever tested an **annual** cadence — which was falsified because "the 2022 bear drawdown happened entirely between annual rebalances" (a pure cadence/latency failure, orthogonal to signal quality). Daily rebalancing on a borderline 0.81-Sharpe edge would be eaten by spread + ST-gains turnover. We need the **cadence/turnover-cost frontier** (daily vs weekly vs monthly vs threshold/no-trade-band) mapped against the alpha-decay profile from Q2, including: (a) where the net-of-cost, net-of-tax optimum sits; (b) whether **regime-conditional cadence** (rebalance faster only when crisis-prob rises) is defensible without generating the short-window false positives that killed our prior overlays; (c) the minimum observation cadence at which drawdown control actually *binds* for a daily-bar book. A fast 5d HMM behind a slow actuator is wasted — quantify that.

### Q10. Where does nonlinear ML actually beat a regularized linear/shrinkage combine for **our** data shape, and what is the leakage-free CV protocol — and at what edge-count N does diversification-weighting start adding value?

**Decision it informs:** (a) whether to build a nonlinear ML combine at all vs better-regularized linear combos (ridge / elastic-net / shrinkage) on the existing factors, and if ML, which class at what feature/sample budget; (b) the exact purged-k-fold + embargo CV configuration to standardize for every learned component; (c) whether to keep plain weighted/equal weighting at current breadth or invest in covariance-shrinkage weighting now, and the concrete edge-count target to revisit HRP.

Three tightly-related methodological sub-questions:

- **ML crossover.** Under what concrete conditions (sample size, signal-to-noise, feature count, regime-stationarity) does GBM / shallow-net beat a regularized linear factor combine out-of-sample — and where is the crossover for **~109 names × 12yr × 6–20 features**? Reconcile Gu-Kelly-Xiu (ML wins with data abundance) against de Prado / small-sample caveats. Our prior adaptive attempt (online meta-learner) was falsified (−0.58 Sharpe). Give a crisp decision rule, not "it depends."
- **CV protocol.** The correct purged k-fold / embargo length / combinatorial-purged-CV (de Prado) for **overlapping-return daily features** with 5-day holds. Critically: **how much of our signature "short-window-lift-that-reverses" failure could be CV leakage / insufficient embargo rather than genuine non-stationarity?** This distinguishes a *fixable CV bug* from an *unfixable data limit* — tell us how to tell them apart and whether past reversals warrant a leakage re-audit.
- **Small-N weighting crossover.** At what *effective edge-count N* does HRP / risk-parity / min-variance begin to **add** risk-adjusted value rather than destroy conviction? We falsified HRP twice at small N (a 3-edge ensemble: 0.740 vs 0.953) and paused it "until ~20+ edges" — but ~20 was a guess. Use the shrinkage / Ledoit-Wolf / Bayesian-weighting vs naive-1/N literature (DeMiguel et al.) to give a **derived** crossover N for our covariance-estimation-error regime, and say whether breadth expansion is a *prerequisite* for better construction.

*(Optional, only if evidence is strong: when the co-equal objective is positive skew, which **trainable loss functions** — CVaR, Omega, upside-capture, ES-penalized utility, quantile/skew-aware losses — are estimable and non-overfitting at ~12yr, and do they select materially different models than a Sharpe loss? Flag clearly if these are too high-variance at our sample size to be defensible.)*

---

## TIER 4 — Open invitation

We are not asking you to confine yourself to the above. If, from this profile, you see:

- a **broker-selection** consideration that materially changes net-of-cost Sharpe at sub-$25K equity (PDT, settlement / good-faith violations, fractional-share support for the 30% cap, tax-lot reporting for specific-ID) that we've under-weighted;
- a rigorous **live kill/pause protocol** distinguishing normal drawdown from genuine edge decay on a tiny live sample (CUSUM/SPRT on live Sharpe, live-vs-backtest-distribution divergence, HMM-conditional expected-drawdown bands) — and how it should differ from our backtest-time DSR/MBL kill thesis;
- a **stop-loss verdict** for a systematic daily cross-sectional book (the literature is split: Kaminski/Lo convexity for momentum vs stop-driven realized-loss-plus-wash-sale damage for value/low-vol), and if "no stop," what replaces it for single-name tail control on a 30%-cap book;
- whether the binding drawdown constraint should be **MDD (a single worst-path point estimate)** or a **path/tail measure (CDaR, Ulcer, average-drawdown)** that actually has a stable `ci_low` under block-bootstrap — consistent with our gate-on-`ci_low` house style;
- or a genuinely **adjacent-market tail-capture sleeve** (defined-risk listed options, crypto, micro futures) reachable *only* by a nimble small account, with its real operational/tax (e.g., §1256) cost of running alongside the equity core —

then raise it, with the same evidence discipline. Tell us what we **should** be asking that we did not.

---

## Closing — what to deliver

End your report with a **ranked list of pre-registerable, testable hypotheses** drawn from your findings. For each, give exactly:

1. **Hypothesis** — one falsifiable sentence.
2. **Metric** — the specific statistic we would measure (and on what window / substrate), reported as a bootstrap `ci_low` where applicable, **after costs and after tax** where the hypothesis touches deployability.
3. **Confirm / refute threshold** — the pre-registered number that decides it (e.g., "`ci_low(Δ Sharpe) > 0` on a ≥12-yr block-bootstrap" or "added-cost-to-kill ≥ X bps").

Rank by **expected information value per unit of trial-budget consumed** — we have a hard multiple-testing N constraint and will only run the top few. Be explicit about which hypotheses you expect to **refute** (negative results are valuable here) and which are long shots.