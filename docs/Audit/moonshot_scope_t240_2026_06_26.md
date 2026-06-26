---
task_id: T-2026-06-26-240
title: Moonshot / upside-half BUILD — pre-registered design (SCOPE only, not a build)
date: 2026-06-26
author: Agent D
type: pre-registered experiment design (no build, no run)
status: SCOPED — awaiting go/no-go
---

# T-240 — moonshot / upside-half: pre-registered design

## The strategic prize + the constraint
T-236 shipped the DOWNSIDE half (trend sleeve: Sortino 1.085, MaxDD −12%, survives dotcom) — but
it costs ~1%/yr terminal wealth (the give-up). T-239 confirmed there is **no buried upside half**
in existing artifacts (the trend family is structurally downside-only). So the moonshot/return
half must be BUILT. **The prize:** a working upside sleeve PAIRED with the trend sleeve → beat the
robo on BOTH terminal wealth (moonshot upside) AND drawdown (sleeve protection), closing the give-up.

**The hard constraint (T-215 lesson):** a $5-15K cash Roth has NO margin / borrowing / shorting.
So the right tail must be amplified by **ASSET SELECTION** (concentration, universe, asymmetric
exits), NOT leverage. Measure on **Sortino + up-capture + skew + Calmar** (the reframe that
un-cancels asymmetric upside — `[[feedback_measure_sortino_tail_not_sharpe_2026_06_25]]`).

**The honest overall prior is MEDIUM-LOW.** Two prior findings cut against it: the single-gene
Foundry vocabulary is H0 (T-196), and the dense edge book is closet-beta (T-117, factor-negative).
The counter-evidence is the ensemble-alpha-paradox (T-2026-04-30): the system showed alpha
*standalone at full risk* (17× position size) that vanished when capital was split across noise
edges — i.e. alpha may exist but be DILUTED by diversification. The moonshot thesis IS that
paradox's other side. Whether concentration surfaces that alpha or just amplifies H0 noise is the
single most important disambiguating question, and Candidate 1 tests it cheaply.

---
## CANDIDATE 1 — Concentrated conviction-weighting of the existing edge book  ⭐ RECOMMENDED FIRST
- **Hypothesis:** the diversified (MVO/EW-across-100s) book averages the highest-conviction
  signals into closet-beta. Concentrating capital into the **top-K** highest-conviction names per
  rebalance KEEPS the asymmetric upside (winners aren't diluted) → fatter right tail (higher
  skew/up-capture) that Sortino rewards and Sharpe (rightly, for a levered book) penalized — but
  here there is no leverage, just concentration.
- **Mechanism (asymmetric upside):** rank by the `signal_processor` aggregate conviction score;
  allocate to the top-K (sweep K ∈ {5, 10, 15, 20}); EW or conviction-weight within top-K; monthly
  rebalance; per-name cap for idiosyncratic-blowup control. The right tail comes from a few
  high-conviction names running; the left tail is bounded by the per-name cap + the PAIRED trend
  sleeve.
- **Universe/data:** EXISTING — the PIT equity book + the existing edge signals. **No new data.**
  Cheapest build (a top-K concentration layer in the Engine-C composer + a backtest re-run).
- **Honest prior:** MEDIUM-LOW→MEDIUM. Directly tests the ensemble-alpha-paradox. RISK: if the book
  is genuinely H0 (T-196), concentration amplifies VARIANCE not ALPHA — a few names run, but
  randomly → higher skew but ci_low collapses (no real edge). That outcome is itself decisive +
  cheap to learn.
- **Pre-registered gate:** top-K book vs (a) the diversified book, (b) both robos, (c) PAIRED with
  the trend sleeve, on Sortino/up-capture/skew/Calmar with **block-bootstrap ci_low** (`[NN-SHARPE-CI]`).
  **PASS iff** `ci_low(Sortino_topK) > ci_low(Sortino_robo)` AND up-capture > the diversified
  book's (concentration actually restored upside) AND `is_it_beta_or_edge` ≠ pure beta (the
  concentrated return isn't just amplified market exposure). MBL at honest-N (the K-sweep adds
  4 trials → N += 4; account for it). **H0:** ci_low collapses / it's amplified beta → concentration
  amplifies noise, not alpha → the book is confirmed edgeless even concentrated.
- **Build effort:** LOW-MEDIUM (reuse `signal_processor` + a top-K layer in `engines/engine_c_portfolio/composer.py`; one backtest). **Owner: C (Engine-C concentration/composition).**

## CANDIDATE 2 — Small-cap / high-momentum universe
- **Hypothesis:** the large-cap S&P universe has thin right tails (mature firms). A small-cap /
  high-momentum universe has structurally FATTER right tails (small firms can multi-bag) → higher
  skew/up-capture. A genuinely DIFFERENT universe, not the exhausted large-cap vocabulary.
- **Mechanism:** momentum/trend selection on a small-cap universe; the asymmetry is in the
  universe's return distribution (winners run further).
- **Universe/data:** NEW — survivorship-free small-cap PIT price data (Russell 2000-ish). The
  survivorship problem is WORSE for small-caps (high delisting). A real data build.
- **Honest prior:** MEDIUM-LOW. Small-cap momentum is a documented factor (real right tails) BUT
  (a) wide small-cap spreads → the realistic-cost model (T-210/T-219) hits HARD (could eat the
  tail), (b) crowding (well-known factor), (c) harder survivorship data. **Net-of-cost is the
  binding uncertainty.**
- **Pre-registered gate:** small-cap-momentum sleeve vs robos + PAIRED, Sortino/up-capture/skew
  ci_low, **NET of realistic small-cap costs** (the make-or-break), `is_it_beta_or_edge` (is it
  just the small-cap + momentum factor premium, capturable via a cheap small-cap ETF?). MBL. **PASS
  iff** it beats the robo on Sortino ci_low NET of small-cap costs AND adds real up-capture AND
  isn't replicable by a plain small-cap-momentum ETF.
- **Build effort:** HIGH (new survivorship-free universe data + backtest). **Owner: quant-dev
  (data/universe) + a backtest.**

## CANDIDATE 3 — Breakout edges (asymmetric exit)
- **Hypothesis:** breakouts (price > N-day high / volatility-contraction breakout) with a
  cut-losses-fast / ride-winners exit are STRUCTURALLY positive-skew (small loss when wrong, large
  gain when it runs) — exactly the asymmetry Sortino rewards and Sharpe penalizes.
- **Mechanism (asymmetric upside):** the asymmetry is in the EXIT — tight stop on failure, trailing
  stop to let winners run. Entry on a breakout signal. Positive skew by construction.
- **Universe/data:** EXISTING large-cap to start (cheap); fatter on small-caps (overlaps C2).
- **Honest prior:** MEDIUM. Stock breakout/CTA-style is a documented positive-skew approach, BUT
  (a) large-cap breakouts are less explosive (smaller right tail), (b) the edge lives in the exit
  rule (researcher DOF — overfit risk), (c) false-breakout whipsaw → net-of-cost uncertain on
  large-caps.
- **Pre-registered gate:** breakout sleeve vs robos + PAIRED, Sortino/up-capture/**skew** (the
  skew must be materially positive — that's the mechanism working), ci_low, net-of-cost,
  `is_it_beta_or_edge`. MBL (the exit-rule params add trials — pre-register a SINGLE exit config,
  no sweep). **PASS iff** positive realized skew + up-capture > 1 + Sortino ci_low > robo's.
- **Build effort:** MEDIUM (new Engine-A edge: breakout entry + asymmetric exit; backtest).
  **Owner: A (Engine-A edge).**

## CANDIDATE 4 — Catalyst/LLM-on-text frontier (FLAG ONLY — separate `[NN-AI-GATE]` track)
New-data / LLM-on-text (news, filings, sentiment) to capture moves EARLY (before the trend
overlay's ~5mo lag) — the highest-ceiling, lowest-prior moonshot. **NOT designed here** — it is a
separate forward-only `[NN-AI-GATE]` track (gated, billed, plateau-before-AI per
`[[feedback_plateau_before_ai_2026_05_01]]`). Flagged so it isn't conflated with the asset-selection
candidates above.

---
## THE PAIRING TEST (the whole point — pre-registered for every candidate)
Each candidate is judged not just standalone but **PAIRED with the trend sleeve** (pre-register a
sizing: 50/50 and a vol-/risk-parity blend). The decisive question: **does the PAIR beat BOTH
robos on BOTH terminal wealth AND MaxDD?** The moonshot supplies upside (fixes the sleeve's ~1%/yr
give-up); the trend sleeve caps the moonshot's own drawdowns (it de-grosses in crises). If the
pair beats the robo on both axes under honest-N, that is the deploy case the whole arc has been
chasing. A candidate that only wins standalone (but the pair doesn't beat the robo on both) does
NOT clear.

## RECOMMENDATION — GO on Candidate 1 first; defer 2/3; flag 4
- **Build Candidate 1 (concentrated conviction-weighting) FIRST.** Highest prior, LOWEST cost (no
  new data — reuses the existing book/signals + a top-K layer), and it directly + cheaply
  disambiguates the ensemble-alpha-paradox (does concentration surface alpha or amplify H0 noise?).
  Either result is decisive and cheap. Owner: C.
- **Defer Candidates 2 (small-cap data build) and 3 (breakout edge)** pending C1's read — they cost
  more (new universe data / new edge) and C1 tells us whether the existing book has ANY
  concentratable alpha before we invest in new universes/edges.
- **Flag Candidate 4 (LLM/catalyst)** for the separate `[NN-AI-GATE]` track; do not start it now.
- **Honest go/no-go:** GO — but as a CHEAP, HIGH-INFORMATION first probe (C1), not an open-ended
  moonshot program. The prior is medium-low; C1 is the right-sized bet because it's nearly free and
  resolves the key uncertainty. If C1 is H0 (concentration = noise amplification), that is a strong
  signal the equity book has no upside half to extract, and the honest conclusion becomes "the
  trend sleeve (downside half) + the robo's own return is the realistic ceiling" — at which point
  the moonshot frontier moves to Candidate 4 (new data) or is conceded.

## Pre-registration summary (per `[NN-MBL]`)
- Candidates 1-3 each: hypothesis + mechanism + gate as above; ci_low block-bootstrap on Sortino;
  `is_it_beta_or_edge`; MBL at honest-N (C1: +4 K-sweep trials; C2/C3: +1 each, single pre-registered
  config, NO param sweep). The PAIR-with-trend-sleeve test is mandatory for each.
- No build, no run in this task. The build (if greenlit) is a separate pre-registered task per candidate.
