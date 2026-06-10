# Research prompt — the four operational blind spots (2026-06-10)

> Paste everything below the line to the research agent (research mode preferred —
> areas 1 and 4 are recency-heavy). Results file into this folder. Companions:
> `../Research_2026_06_10_system/` (methodology) and `../Research_2026_06_10_data/`
> (vendors) — do NOT repeat their ground.

---

You are a researcher with live web access supporting an AI-agent-operated retail
systematic trading platform (AI director + 4 AI worker agents + one human
approver; Python; rigorous reproducibility/falsification discipline; ~$5K live
capital staging to $50K+; both taxable-IL and Roth accounts at Alpaca; backtest-only
today, paper trading next). My training cutoff is ~Jan 2026 — verify anything
time-sensitive and cite URL + date-checked. **Deliver everything in actionable form
(specs, checklists, parameter tables, decision rules with citations) — never
reading assignments.** Four areas, each mapped to a decision we face within ~30
days.

## AREA 1 — Operating an AI-AGENT-RUN trading codebase safely (my biggest blind spot; fast-moving post-cutoff)

We are unusual: the code is written, reviewed, and operated by LLM agents with a
human approval gate. The external review already flagged agent-generated-code risk
("a single sign error introduced by an agent into a live signal is a faster path to
ruin than any market event"). Go deeper:

1. **Defense catalog for AI-written financial code:** what do teams using AI coding
   agents on money-touching systems actually mandate in 2026? Extract concrete
   practices: mutation testing (which tools/configs for Python/pandas), golden-master
   /snapshot regression for numeric pipelines, property-based testing
   (hypothesis) patterns for financial invariants (no-lookahead properties,
   sign/units checks, P&L conservation), differential testing, CI gates. Rank by
   defect-class coverage per effort.
2. **Prompt-injection / data-poisoning via ingested data — TIMELY for us:** we are
   about to ingest SEC EDGAR filing text, GDELT news events, and (later) news/social
   feeds into an agent-operated pipeline. Document the known attack surface:
   adversarial text in filings/news that could steer an LLM agent processing it;
   established mitigations (content/instruction separation, no-execution quarantine
   of external text, structured-extraction-only patterns, allowlist parsing). Any
   documented real incidents.
3. **Known failure modes of multi-agent dev systems** (state divergence, silent
   assumption drift between agents, verification debt) and the practices that
   catch them. Any published post-mortems of AI-agent-driven trading/automation
   errors (incl. regulatory commentary on AI in trading 2025-2026).
4. **Post-cutoff tooling:** anything since Jan 2026 that materially helps an
   agent-operated quant shop (agent sandboxing, deterministic-replay harnesses,
   eval frameworks for code agents).

## AREA 2 — Validating RARE-EVENT overlays (the crisis-replay methodology)

We run a regime-transition de-grossing overlay whose value concentrates in a
handful of crisis episodes (2008, 2011, 2015, 2018Q4, 2020, 2022). Full-window
Sharpe-difference CIs are structurally underpowered for such payoffs (an external
reviewer already flagged this; we pre-registered the concern before unblinding).
We may need to design a successor evaluation ("T-118b") on a crisis-replay framing.

1. **The canonical methodology:** how do credible practitioners/academics evaluate
   insurance-like overlays? Extract: event-study/scenario-replay designs (window
   definitions, what counts as an episode, multiplicity handling across episodes),
   the statistics for small-N skewed payoffs (exact tests? Bayesian? bootstrap
   variants that respect episode structure?), and "calm-period cost ceiling"
   formulations (how is acceptable drag pre-registered and measured?).
2. **How CTAs/tail-hedge funds present crisis evidence** (SG Trend/CTA indices'
   crisis-window conventions; Universa-style claims and their critiques) — what
   presentation survives scrutiny vs what is marketing.
3. **A concrete pre-registration template** for a crisis-replay evaluation: episode
   list locked ex-ante, per-episode metrics, aggregation rule, calm-drag ceiling,
   pass/fail logic — written so we can adopt it nearly verbatim.

## AREA 3 — Survivor-bias REPAIR conventions (the delisting-return question)

We are building a free point-in-time membership layer (1996+) but free sources
lack DELISTING RETURNS; the paid fix (Norgate Platinum $630/yr) has a
cloud-license conflict. Before any purchase:

1. **The academic conventions:** Shumway (1997)/Shumway-Warther delisting-return
   corrections — the standard imputation values by delisting reason (performance
   delists vs mergers vs exchanges), how CRSP codes map to them, and what modern
   replication studies actually use.
2. **The practical question:** with PIT membership + delisting DATES (free) + imputed
   delisting returns per the literature, how close does one get to the paid
   delisted-price product for backtest purposes? What biases remain, in which
   direction, and how do published papers bound them? Is there ANY free/cheap
   source of delisting dates+reasons at scale (EDGAR Form 25 filings? exchange
   notices?)?
3. **A decision rule:** under what measured conditions (e.g., survivor-inflation
   found by our membership-correct re-test) is the $630 product worth it vs
   imputation-with-caveats?

## AREA 4 — The factor-premia DEPLOYMENT blueprint at our scale (the likely backbone)

External research (Q2) says the documented successful-retail path is deliberate
factor/style-premia harvesting + vol targeting + cost control (net Sharpe ~0.6-0.9,
MDD ~15-25%), with t>2 idiosyncratic alpha not required for deployment. If we adopt
that as the deployment backbone, I need the concrete blueprint:

1. **The smallest-account implementation** (Carver's leveraged-trading/"starter
   system" line and successors): exact instrument set (ETF universe for a US
   retail account), rule set (which trend/carry/momentum variants), lookbacks,
   vol-target %, rebalance cadence, buffering, expected net-of-cost performance
   WITH citations — as a parameter table we can implement directly.
2. **The capital staircase:** what changes at $5K → $25K → $50K → $100K (number of
   instruments, whole-share constraints, when futures become viable, when
   diversification multiplier stops being capped by capital). Cross-reference
   Carver's dynamic-optimization smallest-capital guidance.
3. **After-cost/after-tax honesty at each step:** realistic net figures for a
   taxable-IL + Roth split (which sleeves go where), and the breakeven account size
   below which this is education rather than income (state it plainly).
4. **The strongest published CRITIQUES of this path** (style-premia drawdowns
   2018-2020, AQR's own retrospectives, trend crisis-alpha decay debate) — so we
   adopt with eyes open, not as religion.

## OUTPUT FORMAT
Per area: actionable briefs tagged [effort S/M/L | EV high/med/low | evidence:
replicated/published/anecdotal] + citations with dates. Then: a consolidated top-8
"adopt these" list across areas; a do-not-bother list; explicit answers to every
numbered item; a "couldn't verify" section (never guess paywalled specifics).
