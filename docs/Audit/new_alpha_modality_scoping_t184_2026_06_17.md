---
task_id: T-2026-06-17-184
title: New-alpha-modality scoping — the informed fork (IF Discovery also comes up empty). DESIGN/FEASIBILITY ONLY.
date: 2026-06-17
scope: feasibility/cost/plausible-edge/retail-capacity/propose-first for 3 candidate modalities; NO build, NO new deps/services, NO code
status: CURRENT (scoping doc; decision-prep only — not a build green-light)
---

# T-184 — New-Alpha-Modality Scoping

## 0. Why this exists + the prerequisite

The equity-overlay alpha lane is closed: cross-sectional alpha 0/16
(8-K/Form-4/13F family-wise clean, metalearner didn't generalize),
VRP refuted in our equity form (T-174). The one LIVE equity path left
is Discovery's `--discover` cycle (D's Phase-0b). **This doc is parallel
prep, NOT a green-light:** test Discovery first. It exists so that IF
Discovery also comes up empty, the next fork is reached INFORMED rather
than scoped from cold. Nothing here is proposed for build; everything
is propose-first by construction.

## 1. The retail-capital reality (LEADS the whole analysis)

Per `[[project_retail_capital_constraint]]` (user directive, load-bearing):
at **$5-50K** working capital, a 1%/yr edge compounds to ~$1-3K over 20
years — meaningless. The objective function is therefore NOT "more
Sharpe" but **"catch a meaningful fraction of asymmetric (10x-ish)
winners"** — positive skew + tail-CAPTURE is the math that matters.
Two hard consequences that pre-filter the candidates below:

- **Skew sign is a first-class screen.** A modality that is *negative*
  skew (collect pennies, occasional large loss) is objective-MISALIGNED
  for this book no matter how real its premium — it's the opposite of
  the mandate.
- **Capacity/cost asymmetry favors the small account in exactly one
  direction:** tiny size means no market impact, so concentrated
  asymmetric bets are *feasible*; but it also means per-trade fees,
  slippage, spreads, and (critically) the **PDT rule** (<$25K margin
  accounts: max 3 day-trades / 5 business days) bite hardest. Anything
  high-frequency or high-turnover is the worst fit at this scale.

This screen is why the ranking below is NOT "which has the biggest
documented premium" — it's "which is both retail-accessible AND
objective-aligned (positive-skew, low-turnover, capacity-friendly)."

## 2. Candidate 1 — Options desk (the REAL VRP short-variance harvest)

**What it is:** the harvest T-174 said equity can't capture — sell
variance (SPX/SPY put spreads, iron condors, etc.) to collect the
IV>RV premium directly.

**Feasibility:** HIGH complexity. Requires (a) an options-capable broker
path (Alpaca options or IBKR — a new live integration), (b) a whole new
risk engine: Greeks, margin/buying-power, assignment/exercise, expiry
roll, defined-risk structuring — none of which the equity sizing stack
(Engine B) models; (c) effectively a **new engine** (options ≠ equity;
the charter boundary is real). This is the heaviest build of the three.

**Cost:** data = options chains / IV surface (broker-provided, modest);
infra = Greeks + margin + assignment machinery (substantial new code);
complexity = HIGH; ongoing = expiry/roll operational cadence the daily
loop doesn't have.

**Plausible edge + honest-N/capacity:** VRP is real and among the most
documented premia. BUT — **the disqualifying point for THIS book: short
variance is structurally NEGATIVE skew.** It collects small steady
premium and pays out large in vol spikes (2008/2020/COVID) — the exact
inverse of the user's tail-CAPTURE objective. On $5-50K, defined-risk
spreads cap the premium to ~$50-200/month gross while a single vol-spike
takes the structure to max loss; the realized return profile is
"small-positive most months, occasional large drawdown" — i.e. it
*adds* the negative skew the bought-MF sleeve (T-170/171/173) was
brought in to *defend against*. It would fight our own crisis lever.

**Propose-first implications:** new engine + new broker/live-money path
+ new real-money tail-risk surface → among the heaviest propose-first
gates in the codebase (touches live money, new external service, new
engine, Engine-B-adjacent risk). 

**Verdict: LOW priority for this book.** Real premium, wrong shape.
Negative skew is objective-misaligned, retail capacity is thin, tail
risk is real, and the build is the heaviest of the three. The "we
should harvest the real VRP" instinct is correct in the abstract and
wrong for a $5-50K positive-skew-seeking book.

## 3. Candidate 2 — A new data modality (alt-data for a retail book)

**What it is:** a new input stream beyond price/fundamentals.
Retail-accessible options, screened for edge vs noise:

| Alt-data | Retail-accessible? | Status / honest read |
|---|---|---|
| 8-K / Form-4 / 13F NLP | yes (EDGAR free) | **already tested — family-wise clean (0/16)**; don't re-litigate |
| News / social sentiment (raw) | yes (cheap APIs) | fast-decay, noisy at daily horizon; weak standalone edge in the literature |
| Options-flow / gamma / put-call | partial (some free) | positioning signal; overlaps regime/vol work; modest, not asymmetric |
| Google-Trends / web / app-download | yes (free-ish) | mostly noise at daily; capacity-limited; thin evidence |
| **LLM-as-analyst: narrative / thematic conviction** | **yes (LLM API cheap)** | **the one genuinely-unexplored + objective-ALIGNED path** |

**The standout — LLM-as-analyst for narrative/thematic conviction**
(`[[project_thematic_conviction_gap]]`, the deferred Goal-C path): the
system today cannot do narrative-driven picks (theme detection,
conviction sizing on a story). An LLM-analyst reading filings / news /
calls to surface *asymmetric-upside narrative candidates* is the one
new modality that is BOTH:
- **retail-accessible** (LLM API is cents-per-query; news/filings free), AND
- **objective-ALIGNED** — narrative/thematic picks are precisely the
  positive-skew, catch-a-10x channel the retail math demands. It is the
  only candidate whose *shape* matches the mandate.

**Feasibility:** MEDIUM. LLM-as-analyst integration (prompt/context
pipeline, a conviction→sizing bridge into a small dedicated sleeve);
no new broker, no new engine boundary crossed if scoped as an
Engine-A/D candidate-generator feeding the existing gauntlet. This is
the architectural answer the project already named for Goal C.

**Cost:** data ~free (news/EDGAR); LLM API cheap; complexity MEDIUM;
the hard cost is **validation**, not infra.

**Plausible edge + honest-N/capacity:** capacity is ideal (a few
concentrated conviction names on a tiny book — no impact). The plausible
edge is the only one that can produce the asymmetric outcomes the math
needs. **BUT the load-bearing caveat: narrative alpha is the HARDEST to
validate honestly** — small-N, survivorship/hindsight bias, look-ahead
leakage from LLM training cutoffs (the LLM "knows" which themes won),
and DSR/MBL are brutal on a low-frequency conviction strategy. Any test
must use strict point-in-time discipline (LLM sees only pre-decision
information) and treat N_trials honestly.

**Propose-first:** new data flow + LLM dependency (a new external
service) → propose-first, but scoped as a candidate-GENERATOR feeding
the existing Engine-F gauntlet it does NOT cross an engine boundary or
touch live money. Lightest propose-first of the three.

**Verdict: HIGHEST priority IF a new modality is pursued** — the only
candidate aligned with the retail objective's *shape*, retail-accessible,
and not an engine/broker rebuild. Tempered hard by validation
difficulty (it is the easiest to fool yourself with).

## 4. Candidate 3 — Intraday / higher-frequency

**What it is:** ingest 1-/5-min bars; pursue microstructure / intraday
momentum-reversal / opening-auction edges (`[[project_intraday_bars_thinkabout]]`).

**Feasibility:** technically possible (Alpaca WebSocket free live;
storage ~3-4GB/5yr compressed) but the **backtest wall-time is 78-390×**
(5-min ≈ 18 hr/cell, 1-min ≈ 91 hr/cell) — Discovery cycles
(cap×gates) become infeasible without a separate multi-resolution
architecture (signals daily / execution intraday — different code paths).

**Cost:** storage modest; **compute prohibitive** for research; a new
intraday research+execution architecture = HIGH complexity.

**Plausible edge + retail-capacity:** our entire alpha library is
daily-hold → intraday adds ZERO to existing edges; a new intraday edge
is a from-scratch research program. And retail capacity for HF is the
WORST of the three: (a) the **PDT rule legally blocks day-trading on a
<$25K margin account** (most of a $5-50K book) — a hard regulatory
constraint, not just a cost; (b) HF edges are the most fee/slippage/
spread-sensitive — exactly the costs that dominate at tiny size; (c) HF
is typically *low* positive-skew (many small bets) — objective-misaligned
again.

**Propose-first:** new data ingestion + storage + a parallel
intraday architecture → heavy, and gated behind a regulatory blocker
at the target AUM.

**Verdict: LOWEST priority.** Infeasible research cost, legally
constrained at retail (<$25K PDT), zero benefit to the daily-hold
library, and the wrong skew shape. Defer indefinitely (the original
2026-05-12 deferral stands; nothing has changed to revisit it).

## 5. Honest ranking + the fork recommendation

| Rank | Modality | Retail-accessible | Objective-aligned (skew) | Build cost | Worth the checkpoint? |
|---|---|---|---|---|---|
| **1** | LLM-as-analyst narrative/thematic (Cand. 2) | yes | **YES (positive-skew, tail-capture)** | MEDIUM | **YES — the one aligned path** |
| 2 | Options / true VRP harvest (Cand. 1) | thin | **NO (negative skew)** | HIGH (new engine) | No — real premium, wrong shape for this book |
| 3 | Intraday / HF (Cand. 3) | PDT-blocked <$25K | no | HIGH + infeasible research | No — defer indefinitely |

**The informed-fork recommendation (IF Discovery comes up empty):**
the retail-capital math points the next edge toward **positive-skew
tail-capture**, which rules OUT both options-VRP (negative skew) and
HF (capacity/PDT/skew) despite VRP being "the real premium." The single
candidate that is retail-accessible, objective-aligned, and not an
engine/broker rebuild is **LLM-as-analyst narrative/thematic conviction
(Goal C, long-deferred)** — with eyes wide open that it is the hardest
of the three to validate honestly (hindsight/look-ahead/small-N), so
its checkpoint must come with a brutal point-in-time validation
pre-registration before any capital.

**The honest meta-point for the user:** if Discovery is empty, there is
no cheap equity-implementable edge left — the remaining options are a
heavy build (options engine), a regulatorily-blocked dead-end (HF), or
a hard-to-validate but objective-aligned narrative sleeve (LLM-analyst).
The deployable system meanwhile is base + bought-MF sleeve: a
borderline base (0.751 / ci_low 0.382) with a partial crisis tail-defense
(T-173) — it defends the tail but has not produced a fresh *return*
edge. That is the real state to bring to the fork.

## 6. Constraints honored

- DESIGN/FEASIBILITY ONLY — no code, no new deps/services, no runs.
- Everything here is propose-first by construction; nothing proposed for build.
- Prerequisite stated: test Discovery first; this is parallel prep.
- NO TASK_LEDGER write (T-114 — row in outbox). Branch push; director merges.
