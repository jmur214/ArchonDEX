# Research request — ArchonDEX (retail algo trading system), 2026-05-31

> **For an AI research analyst.** Paste everything below the line. You do NOT
> have access to our codebase or any internal files — everything you need is
> stated inline in this prompt; nothing is referenced that you can't see.
> Optimize for decision-relevant depth and intellectual honesty over breadth or
> optimism. Where the honest answer is
> "this doesn't work" or "no durable edge here," say so plainly — this team
> values brutal realism and has killed many of its own promising-looking
> findings on rigorous re-test.

---

## Who's asking & system context (so research is targeted, not generic)

We run **ArchonDEX**, an autonomous algorithmic trading system. Relevant facts:

- **Capital scale:** small retail. Target AUM ~$5,000–$15,000, likely growing
  to low-six-figures over years. Deployment account is **taxable individual**
  (no tax-advantaged wrapper assumed). This scale is load-bearing — it changes
  the objective function (see below).
- **Instruments / cadence:** US equities, **daily bars**, long-biased (some
  long/short capability). Universe is a ~109-ticker S&P 500 subset; we have a
  survivorship-aware deep substrate back to **1962** for survivors (Stooq+Alpaca
  merged, dividend-adjusted to split-only), but **delisted names are missing**
  pre-2020 (known survivorship gap).
- **Strategy core:** a 6-edge ensemble — cross-sectional momentum, low-volatility
  factor, several value/quality/profitability (V/Q/A) fundamental factors,
  weighted-sum combination, ATR-based risk sizing, up to 10 concurrent positions.
- **Honest current performance:** baseline ensemble Sharpe **~0.81** on a 12-year
  (2014–2025) window, CAGR ~8%, max drawdown ~–14%. Under a deflated-Sharpe /
  minimum-backtest-length analysis at our accumulated trial count (~260 distinct
  backtests), this is **borderline** — the point estimate clears the
  multiple-testing noise floor but the bootstrap ci_low does not. So: a plausibly
  real but not-yet-formally-validated modest edge.
- **What we've validated rigorously:** a hidden-Markov **regime classifier** that
  is genuinely predictive of forward equity drawdowns (causal-filtered AUC ~0.89
  at 5-day horizon; fires ahead of the 2018-Q4, 2020-03, 2022, 2025 stress events
  by weeks). We can trust a regime/crisis probability signal.
- **What has repeatedly FAILED our re-tests:** overlays on the base ensemble —
  volatility-targeting (gradual de-grossing), confidence-gated execution — all
  showed promising lifts on short windows that REVERSED to zero or negative on
  the longer, multiple-testing-honest window. Pattern: short-window false
  positives.
- **Measurement discipline we already apply:** block-bootstrap confidence
  intervals on every Sharpe; Deflated Sharpe Ratio; Minimum Backtest Length
  (Bailey–López de Prado); PBO via CSCV; substrate-honesty (no survivorship/
  look-ahead). We gate on ci_low, not point estimates.
- **Objective function (important):** NOT pure Sharpe. At this AUM, a smooth
  1%/yr risk-adjusted edge compounds to a meaningless dollar amount over 20
  years. So **asymmetric upside / positive skew / tail-capture is a co-equal,
  load-bearing objective alongside risk-adjusted return.** We would rather have
  a lumpy +convexity profile than a smooth low-Sharpe one.
- **Parked for later:** an "LLM-as-analyst" layer (theme detection, narrative
  conviction). Deliberately deferred until the quantitative "bones" are as good
  as they can get. Not part of this request unless you think it changes the
  strategic picture.

For every question: tell us **what decision it informs**, give **effect sizes
with uncertainty** (not just directional claims), **cite** sources, and flag
**where the evidence is thin or conflicted.**

---

## TIER 1 — immediately actionable (please go deepest here)

**Q1. Optimal number of concurrent positions for a small, cost-constrained
account.**
We currently cap at 10 positions out of a ~109-name universe, and at 30%-of-
equity max per single name — both are unexamined round numbers. At $5–50K AUM,
every position carries fixed-ish cost drag (effective spread, slippage,
minimum-meaningful-size). 
- Is there a known framework or empirical sweet spot for position count as a
  function of (AUM, per-trade cost, signal breadth, signal correlation)?
- Where is the crossover between "more positions = better diversification" and
  "more positions = death by a thousand cost-cuts" for a sub-$50K account?
- Best practice for single-name concentration caps that still permit conviction
  tilt (vs. forced equal-weight)? How do concentrated retail/quant books set
  this, and what's the empirical return/risk cost of tight vs. loose caps?
- *Decision: sets the range for a planned position-count × concentration-cap
  parameter sweep, and whether 10 is leaving return on the table.*

**Q2. Translating a regime/crisis probability into exposure decisions.**
We have a trustworthy regime signal (forward-drawdown AUC ~0.89). Our gradual
vol-targeting overlay built on regime *failed* re-test. What's the best-practice
mapping from a probabilistic regime signal to action?
- Discrete de-grossing / binary kill-switch vs. continuous exposure scaling vs.
  Kelly-fraction modulation — what does the evidence say about which generalizes
  out-of-sample for a daily-rebalanced equity book?
- Why might gradual vol-targeting underperform a binary regime gate (we saw
  this empirically)? Is there literature on the "slow estimator misses the
  regime turn" failure mode?
- Should regime conditioning act on position *count*, gross *exposure*,
  per-name *cap*, or *which edges are active* — and is there evidence on which
  lever has the best out-of-sample payoff?
- *Decision: design of the next defensive/offensive overlay, now that we have a
  validated regime signal but a track record of overlays failing.*

## TIER 2 — strategic direction (high value; go deep if capacity)

**Q3. Where does durable, retail-accessible alpha actually come from in ~2026?**
An honest survey. Of the classic equity anomalies (momentum, value, quality,
low-vol, etc.), which have **survived post-publication decay** (McLean–Pontiff
and successors), which are **capacity-constrained** (i.e., *advantaged* at small
AUM because big funds can't fit), and which are effectively arbitraged away?
- What is a **realistic, after-cost, after-tax Sharpe ceiling** for a daily-
  rebalanced long-biased factor+technical equity system at small retail AUM?
  We want a calibrated expectation, not a sales pitch — is our ~0.8 actually
  near the achievable frontier for this approach, or is 1.5+ realistic?
- Which under-researched or capacity-constrained niches are *specifically*
  accessible to a small, nimble, daily-bar retail system that institutions
  structurally cannot or will not exploit?
- *Decision: whether to keep refining this edge class or pivot effort toward a
  structurally different alpha source.*

**Q4. Convexity / asymmetric-upside strategies accessible to small retail.**
Given our explicit tail-capture objective: what approaches deliver **positive
skew / convex payoffs** without requiring deep options-market-making expertise?
- Trend-following / time-series momentum convexity; momentum's own crash risk
  and how to hedge it; "barbell" (safe core + convex satellite) constructions;
  cheap tail-hedge overlays.
- Evidence on whether retail-implementable convexity strategies actually deliver
  the skew they promise after costs, and their drag in calm regimes.
- *Decision: whether to build a dedicated convexity/tail sleeve alongside the
  Sharpe-oriented core, and which construction.*

## TIER 3 — methodological (answer if you have room)

**Q5. Managing accumulated multiple-testing in an iterative research program.**
We're at ~260 distinct backtests and the count keeps rising; our Minimum-
Backtest-Length requirement now exceeds our available history. How do serious
quant shops handle the "every backtest inflates effective N" problem?
- PCA / clustering reduction of *correlated* trials to a smaller effective N;
  pre-registration; hold-out and CSCV discipline; the practical frontier of
  DSR/PBO in a continuously-iterating program.
- Is there defensible methodology for *not* counting highly-correlated re-runs
  as independent trials, and how is that justified to a skeptic?
- *Decision: how aggressively we can keep iterating without self-defeating our
  own validity bar.*

**Q6. Bounding survivorship bias when you only have survivors.**
We have survivor price history to 1962 but lack delisted names pre-2020. How
large is the survivorship bias in long-biased US equity backtests of this type
(quantified, by era), and what are cheap/free methods to *bound or correct* it
without buying a full delisted dataset?
- *Decision: how much of an asterisk to put on our deep-history results, and
  whether the delisted-data spend is justified.*

## TIER 4 — open invitation

**Q7. Anything we're not asking that we should be.**
Given the system profile above — small taxable retail AUM, daily US equities,
validated regime signal, borderline base edge, tail-capture objective, strong
measurement discipline, parked LLM layer — **what is the highest-value thing we
haven't thought to ask?** Where are we likely fooling ourselves, what's the
research or technique that would most change our trajectory, and what would you
do differently if this were your capital?

---

### Output format requested
- Lead with a 1-paragraph **bottom-line-up-front** per tier.
- Per question: **decision it informs → key findings (with effect sizes + CIs
  where they exist) → citations → confidence level → what would change the
  answer.**
- Explicitly separate **"strong evidence"** from **"plausible but thin"** from
  **"folklore / unsupported."**
- End with a **ranked list of concrete, testable hypotheses** we could turn into
  backtests — each phrased so we can pre-register it (hypothesis + the metric +
  the threshold that would confirm/refute).
