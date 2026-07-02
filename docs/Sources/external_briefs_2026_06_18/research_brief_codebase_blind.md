# Research Brief — Codebase-Blind Domain Research (2026-06-18)

**For:** an external research agent with NO codebase access — pure domain/market/literature
knowledge. **Purpose:** fill the director's knowledge gaps so the next phase is chosen from
evidence, not folklore. Answer with honest, evidence-grounded findings (cite sources/studies/
practitioner consensus where you can); flag where something is trader-folklore vs validated.

## Our situation (so your research is targeted — you do NOT need our code)
- A **solo/retail systematic EQUITIES** trading system. Small AUM (**$5–50K**). Brokerage =
  **Alpaca, equity-only** (no native options/futures/bonds/FX execution). **Daily-bar**
  frequency (not intraday/HFT).
- Benchmark + fallback = a **Schwab robo-advisor** (the money's current home). The bar:
  **beat the robo net-of-cost/after-tax, paper-confirmed.** Ultimate aspiration: "perform
  like a quant desk" and "significantly outperform the market."
- **What we've already found (so don't re-tread):** our equity-feature edge book shows **no
  validated alpha** — the measured Sharpe looks like market+momentum **beta + survivorship +
  risk-management, not edge**. A genetic-algorithm search over **universal, apply-to-every-name
  price/volume features** came up empty (0 of 35 cleared a deflated-Sharpe gauntlet). We have
  macro data (treasury yields, credit spreads, dollar, CPI, fed funds) and some retail
  positioning data (FINRA short interest, RegSHO short volume, margin debt, NAAIM exposure,
  SEC fails-to-deliver) — mostly **unused**.

## The questions (answer each honestly, with evidence + the realistic effect size)

1. **Realistic retail alpha at small AUM.** For a <$1M systematic *equity, daily-bar* trader,
   what edge sources genuinely persist and are NOT arbitraged/crowded out? Be brutal: is there
   honest evidence retail systematic equity can beat the market after costs, or is
   risk-managed beta the realistic ceiling? What edge categories survive at this scale vs
   require institutional infra?

2. **Regime-conditional / state-dependent strategies.** Does conditioning an edge on market
   regime (e.g., a volatility/crisis/trend state) actually *rescue* signals that fail when
   tested universally — or is it mostly an overfitting / degrees-of-freedom trap? How do
   serious practitioners design AND *validate* regime-conditional strategies without
   data-mining the regime boundaries? What's the honest track record of regime-switching
   approaches out-of-sample? What guardrails (DSR penalties, walk-forward, # of regimes) keep
   it honest?

3. **Retail-accessible positioning/flow data — does it carry tradeable signal?** For each of:
   **CFTC COT, FINRA short interest, NAAIM exposure, RegSHO short-volume, margin debt, SEC
   FTDs** — what's the *evidence* (academic + practitioner) that it predicts returns, at what
   horizon, and what realistic Sharpe/IC? Which are stale/lagged to the point of uselessness?
   Which are genuinely orthogonal to price/value/momentum factors?

4. **The "price is lagging; positioning leads" thesis.** Is this validated or folklore? WHICH
   positioning data genuinely leads price, and how much of *that* is retail-accessible vs
   institutional-only (prime-broker books, dealer gamma, options dealer positioning)? If the
   leading data is institutional-only, say so plainly.

5. **Conditional / sector-specific edges.** The hypothesis: "a signal (e.g., a moving-average
   crossover) may work for tech or energy but not the whole S&P." Is *specialization by
   sector/industry/characteristic* a real, robust source of alpha, or does it just multiply
   the overfitting surface? How do practitioners exploit cross-sectional heterogeneity
   honestly (conditional models, characteristic-sorted strategies)?

6. **What "perform like a quant desk" realistically means at retail scale.** Which quant-desk
   capabilities are achievable by a small equity-only system (factor risk models,
   conditional alpha, portfolio construction, execution discipline) and which are structurally
   institutional (flow, microstructure, cross-asset carry, alt-data)? Define a realistic
   target.

7. **Blind spots / creative angles.** Given the constraints (retail, equity-only, daily-bar,
   small AUM, positive-skew/tail-capture is valued over raw Sharpe), what alpha or
   *capability* angles might a small systematic trader exploit that aren't obvious — including
   non-"edge" ways a system can add value (better risk management, regime-aware sizing,
   tax-aware harvesting, behavioral discipline)? Where might WE specifically be too narrow?

## Output
A structured findings memo per question: the honest answer, the realistic effect size, the
evidence, and a verdict (worth pursuing at retail / institutional-only / folklore / overfit
trap). Rank the genuinely-promising directions. Brutal honesty over encouragement.
