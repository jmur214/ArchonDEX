# Research prompt — system-wide improvement hunt (knowledge extraction for an AI-driven quant platform) (2026-06-10)

> Paste everything below the line to the research agent verbatim. Results get filed
> in this folder. Companion to the concurrent DATA-sources hunt
> (`../Research_2026_06_10_data/`) — data-source recommendations are OUT of scope
> here to avoid duplication.

---

You are a quantitative-systems researcher with live web access. I am an AI
development director (training cutoff ~Jan 2026, no web access) running a retail
systematic-trading research platform with a fleet of AI agents. **Your job is to be
my eyes on the practitioner/academic/open-source world and bring back ACTIONABLE
knowledge — not reading lists.** A human was previously advised to "buy these books"
(Carver, López de Prado, Chan, Bandy, Krishnan) — that helps the human but not me.
**Every finding must be delivered in machine-actionable form: an implementable spec,
a parameter table, a decision rule, pseudocode, or a concrete checklist — with
citation + date.** If your answer to anything is "read chapter 7," you have failed
that item; extract what chapter 7 says.

## THE PROJECT (compact context)

Single-developer retail systematic trading research system, built and operated by AI
agents. Python/pandas; 6-engine architecture (Alpha signals / Risk sizing /
Portfolio / Discovery / Regime / Governance); backtest-only today (Alpaca paper/live
planned); ~$5K live capital staging to $50K+; BOTH taxable (Illinois) and Roth
accounts. Daily-bar US large/mid-cap equity substrate (survivor-biased — being
addressed separately).

Measurement discipline is the system's strength: block-bootstrap CIs on everything,
deflated Sharpe + minimum-backtest-length gates, FF5+Mom HAC factor decomposition,
pre-registered experiments with an honest accumulated trial count (~300), bitwise
reproducibility (pinned Docker substrate, deterministic runs). We falsify ~90% of
what we test, on purpose.

Current honest state: the base 6-edge ensemble is bull-conditional (16-yr Sharpe
~1.0; 26-yr ~0.24 with -59% MDD — fails our deployment gates). Recently CLOSED
empirically: our artisanal technical edges have no factor-orthogonal alpha;
linear edge recombination; equity-proxy VRP; BAB/low-beta on our panel. LIVE
workstreams: an HMM regime-transition de-grossing overlay (the crisis-defense bet,
A/B in flight); the untested alpha frontier = event/filing edges, intraday-derived
FEATURES for daily signals, cross-asset carry/rotation, non-linear edge combination
(gradient-boosted metalearner, built-never-trained), vol-term-structure signals.
Constraints: free-data-first; no LLM in the trading loop (ML fine); retail
execution scale; strict no-lookahead.

## THE HUNTING GROUNDS (8 areas — go deep on each)

### 1. Extract the canon (the "books" problem, solved properly)
From Carver (*Systematic Trading*, *Advanced Futures Trading Strategies*,
pysystemtrade docs), López de Prado (*Advances in Financial ML*, *ML for Asset
Managers*), Bandy (*Modeling Trading System Performance*), Krishnan (*The Second
Leg Down*), Chan: extract the OPERATIONAL pipelines as specs. Specifically wanted:
- Carver's full forecast-processing chain (raw forecast → scaling → capping at ±20
  → combination weights via handcrafting → buffering/position-inertia → vol
  targeting) with the actual numbers/formulas he uses.
- López de Prado's meta-labeling recipe end-to-end (triple-barrier labeling,
  sample-weight schemes, bet sizing from predicted probability) — as pseudocode.
- Bandy's system-validation + position-sizing (safe-f, CAR25) methodology — as a
  procedure.
- Krishnan's practical crisis-hedge structures ranked by cost/complexity for a
  small account.
Where public implementations exist (pysystemtrade IS Carver's), point to the exact
modules so my agents can read code instead of prose.

### 2. Mine the open-source ecosystem
pysystemtrade, QuantConnect LEAN, Microsoft qlib, vectorbt(.pro?), zipline-reloaded,
bt/ffn, Nautilus Trader, anything significant newer than Jan 2026. For each: what
specific subsystem is BETTER than a homegrown equivalent and worth porting concepts
from (their execution simulators? forecast combination? dynamic optimization?
portfolio buffering? live-trading state machines?). Name files/classes. We will not
adopt a framework wholesale; we steal ideas with attribution.

### 3. Replication evidence (spend our trial budget only on what replicates)
Which published anomalies/strategies have PUBLIC replication track records vs which
failed replication (Hou-Xue-Zhang "Replicating Anomalies"; the post-publication
decay literature — McLean-Pontiff; AQR's factor-zoo work; Quantpedia's
out-of-sample tracking if visible). Deliver: a ranked shortlist of strategies that
(a) replicate robustly, (b) are implementable on free/cheap retail data, (c) are
NOT spanned by FF5+Mom by construction — with expected NET-of-cost Sharpe ranges at
retail and the implementation gotcha that kills naive attempts. Our frontier
already includes event/filing edges, intraday market-momentum (GHLZ), cross-asset
carry/rotation — adjudicate THOSE specifically plus anything we're missing.

### 4. Validation/statistics upgrades (what would make our gates better)
We run DSR, MBL, block-bootstrap CI, pre-registration. What's current best practice
beyond that: CPCV (combinatorial purged CV) practical recipes; PBO estimation;
Romano-Wolf / White-Hansen SPA for multiple testing across a strategy family; false
strategy theorem applications; live drift-detection stats (CUSUM/SPRT/Page-Hinkley)
with parameterizations used in production by practitioners. For each: a when-to-use
rule + the formula/library + what it would change about our current gates.

### 5. Risk & portfolio layer: the implementable frontier
- Vol forecasting: HAR-RV exact spec (windows, log-vs-level, intercept handling) +
  current consensus on HAR-RV vs EWMA vs GARCH for daily equity vol-targeting.
- Vol-managed portfolios POST-Cederburg-critique: what implementations survive
  real-time constraints (conditional/transition-triggered forms, the exact
  scaling-cap conventions)?
- Drawdown control: Grossman-Zhou / CPPI-style rules in practitioner form;
  trend-overlay de-grossing parameterizations with published OOS results.
- Kelly at retail: the actual fractional-Kelly conventions practitioners use
  (and how they handle estimation error at our sample sizes).
- Anything genuinely new (post-2024) in retail-implementable portfolio
  construction we'd be embarrassed to not know.

### 6. Execution & operations at SMALL retail scale (Alpaca-specific where possible)
$5-50K account, Alpaca brokerage: MOO/MOC availability and mechanics, fractional
shares in systematic execution, realistic fill quality vs IEX routing, PDT
constraints, practical slippage models AT THIS SCALE (is Almgren-Chriss overkill
below $100K? what do small systematic traders measure in practice?), tax-lot
selection automation, wash-sale handling across taxable+Roth at the same broker
(the cross-account wash-sale trap — current IRS interpretation), and Roth-vs-
taxable strategy ALLOCATION logic (which strategy types belong in which account).
Deliver as decision rules and checklists.

### 7. Live-operation playbooks (for our eventual paper→live transition)
What separates surviving retail systematic operations: monitoring cadence and
metrics (what to alarm on), when-to-intervene policies (the "do nothing" discipline
vs kill criteria), live-vs-backtest divergence tracking (how much divergence is
normal before you stop), capital ramp schedules from paper to live, incident
post-mortem practices. Extract any published/blogged operational playbooks from
credible systematic traders into a single consolidated checklist.

### 8. New since my cutoff (Jan 2026)
Libraries, papers, regulatory changes (anything affecting retail systematic trading,
PDT rules, tax rules), broker/API changes at Alpaca, notable retail-quant community
developments, new tools for reproducible research. Anything where my stale knowledge
would actively mislead the project.

## GAP-BRIDGING QUESTIONS (answer each explicitly)

1. Given our exact state (strong falsification infra, weak alpha, ~300 trials
   spent, crisis-overlay bet in flight), what would a top systematic-trading
   practitioner say we should do DIFFERENTLY — not what to add, what to CHANGE?
   Be adversarial; assume our self-assessment has blind spots.
2. Is our "factor-orthogonal alpha at t>2" bar the RIGHT bar for a retail account,
   or do successful retail systematics deliberately harvest known factor premia +
   risk management and skip idiosyncratic alpha entirely? What does the evidence
   say that path realistically yields (net Sharpe, MDD) and what's the canonical
   construction?
3. The single highest-EV technique we appear to be missing, with its spec.
4. For non-linear edge combination at our scale (13 weak edges, daily data,
   ~3K observations/edge): what does the literature say about when gradient-boosted
   stacking adds value over linear, and the overfitting guards that actually work
   (purging/embargo/feature-importance honesty)?
5. Intraday-bars-as-FEATURES for daily strategies: published evidence this adds
   value (realized-vol features, opening-range, intraday momentum/reversal
   features feeding daily models) — specs of what worked.
6. What do the most credible practitioners say about minimum capital for
   systematic equity trading to be worth it AT ALL (costs/taxes/time), and does
   $5K starting capital change what strategy classes we should even attempt?
7. Post-publication alpha decay: current best estimates of decay rates by strategy
   class — which classes decay slowest (so a retail latecomer can still harvest)?
8. Anything important we didn't think to ask, given everything above. You can see
   our blind spots better than we can; use this question seriously.

## OUTPUT FORMAT

1. Per-area briefs in ACTIONABLE form (specs/tables/pseudocode/checklists), each
   item tagged: [effort: S/M/L] × [expected value: high/med/low] × [evidence
   strength: replicated/published/anecdotal] + citation with date.
2. A ranked TOP-10 "implement these" list across all areas, free-first, each with
   its concrete first step in OUR terms.
3. A DO-NOT-BOTHER list (things that sound good but the evidence says skip at
   retail scale) — equally valuable.
4. Explicit answers to the 8 numbered questions.
5. A "couldn't verify / paywalled" section — never guess; say what you couldn't see.
