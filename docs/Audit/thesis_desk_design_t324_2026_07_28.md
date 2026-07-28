---
task_id: T-2026-07-28-324
title: The Thesis Desk — thematic/narrative investing, made falsifiable
date: 2026-07-28
author: Agent D
type: INFRA + forward-accrual design (0 N_trials; forward-only BY NECESSITY)
status: BUILT — the user-seeded channel is OPEN; thesis #1 seeded. Branch feature/thesis-desk-t324
---

# T-324 — the Thesis Desk

**User directive:** the machine's H0 covered QUANT cross-sectional selection and never THEMATIC thesis
investing — "finding stocks or sectors poised for growth." The design spec is the **user's own record**:
BTC @$500, NVDA pre-inflection, RKLB @$23 on the story despite weak fundamentals (sold @$151),
defense-during-war, picks-and-shovels-for-AI. That faculty requires reading narratives and mapping
**second-order beneficiaries** — impossible pre-LLM, possible now.

Sibling of the event-interpreter (T-304): **the interpreter reads ONE discrete document; the thesis desk
reads THEMES ACROSS TIME.**

## The load-bearing design decision: `falsifiers` is REQUIRED
**A thesis without a falsifier is a story, not a position.** Every `thesis_call/v1` must carry ≥1 falsifier —
machine-checkable where possible (a resolver/v1 spec A's harness scores), always with a hard `check_by`
date so it cannot drift indefinitely. Schema-enforced: a falsifier dated before `as_of` or beyond the
thesis horizon (+30d grace) is rejected — *a falsifier that can only fire after the thesis already resolved
is not a falsifier.* **Every thesis resolves or dies visibly.**

## `thesis_call/v1` (`intelligence/thesis_desk/thesis_schema.py`)
- `narrative` (the story in words), `theme_class` from a CLOSED taxonomy (`tech_inflection`,
  `geopolitical`, `supply_demand`, `adoption_curve`, `picks_and_shovels`, `regulatory`, `other`),
  `conviction`, `entry_basis` (why NOW, not just the idea), `horizon_days` (**months-to-years — the schema
  says so honestly** rather than forcing a 21-day window that would misprice the faculty; capped at 5yr).
- **`instruments`: each leg carries its `mapping_reason`** — for `second_order` legs that reasoning IS the
  intellectual content ("AI → compute → power/thermal → the named supplier"), and the schema rejects a
  second-order leg whose chain is too thin to be a real argument.
- **Structural rule:** a `picks_and_shovels` thesis MUST name ≥1 `second_order` instrument — otherwise it is
  just the obvious winner wearing a second-order label.
- Reuses `Provenance`/`Usage` + `is_resolvable_spec` from the analyst package (one contract, one source).

## Two channels, one standard (`intelligence/thesis_desk/thesis_desk.py`)
- **(a) USER-SEEDED — the channel is now OPEN at `data/coordination/thesis_inbox.md`.** The format is
  deliberately dead-simple: a `## title`, a few lines of plain English, optional `tickers:` line. The user
  specifies **no** falsifiers, weights, or second-order maps — the agentic analyst (E/T-321) researches the
  seed across our stores and the desk formalizes it. *The user's instinct picks the theme; the machine is
  its research desk and its honest scorekeeper — collaboration, not replacement.*
- **(b) MACHINE-ORIGINATED** — a weekly thematic scan (strong tier) over the news panel + event flow +
  rate-path: what themes are emerging, who benefits second-order, write the theses.
- Both produce a `thesis_call/v1` that must fully validate; a bad thesis is **never filed** (raw archived).
- **Forward-only guard (`[NN-AI-GATE]`):** `assert_forward_only` REFUSES any `as_of` materially in the past
  — **a backtested thesis is memorization** (the model knows how the story ended). Even fixtures are synthetic.

## Scoring: skew-aware BY DESIGN (`thesis_scoring.py`)
Thematic wins are rare-but-large, so a Brier/hit-rate view would score the user's actual record as a
failure. The promotion bar therefore carries **both**: Brier (is the stated conviction *honest*?) **and** a
skew-aware payoff metric — the **mean log-wealth ratio vs the twin**, bootstrapped over theses (each is one
independent bet). A desk can be badly calibrated yet profitable, or well calibrated and useless; the two
together are the honest picture.

### ⚠️ A finding that came out of building the metric — the skew break-even is STEEP
The metric is honest in both directions, which surfaced a number worth stating plainly. Against a twin at
+5%, for a record with ONE winner:
| losers | at | the single winner must return | to break even |
|---|---|---|---|
| 3 | −40% | **+463%** | (5.6×) |
| 4 | −40% | **+885%** | (9.8×) |
| 4 | −60% | +4,885% | (49.9×) |
| 9 | −50% | +83,299% | (834×) |

**The actual RKLB trade (+557%) clears a 3-loser record but NOT a 4-loser one.** So "1-in-5 with a
10-bagger" is only a good record if the winner is *genuinely* ~10× — the metric refuses to launder a
losing skewed record into a win, and it says so with a number. (Both directions are locked in tests:
`test_one_in_five_with_a_big_winner_scores_POSITIVE` and
`test_the_metric_refuses_to_launder_a_losing_skewed_record`.) This is the honest version of the design
concession the task asked for: the metric *can* say a low hit rate is good — but only when it actually is.

## THE PRE-STATED PROMOTION BAR (written NOW so it cannot move later)
A `theme_class` earns **nothing** until **BOTH**: (1) **≥20 RESOLVED theses in that class**, and (2) the
**bootstrap CI on the mean log-wealth ratio vs the twin EXCLUDES ZERO** (`ci_low > 0`). Brier/calibration is
reported alongside — a profitable-but-miscalibrated record is flagged, never silently promoted. Implemented
as `promotion_check(...)`, which returns `PROMOTED: False` with reason `insufficient_n` or
`ci_straddles_zero`; both paths are tested.

## The book + handoffs
- **C (T-322):** the thesis book is the **third instance** of the shadow machinery. Thesis positions are
  **long-horizon**, so the parameterized book must support **months-long holds + falsifier-triggered exits**
  (not just a daily mark). Twin = **SPY over matched windows** (not 60/40 — a thesis is an equity bet).
- **E (T-321):** the agentic analyst is the researcher for the user-seeded channel — it reads
  `thesis_inbox.md`, researches across our stores, and returns a payload the desk validates and files.
- **A:** falsifiers of `kind="resolver"` are resolver/v1 specs, so the existing harness scores them unchanged.

## Thesis #1 (user-named, seeded on arrival)
**"AI picks-and-shovels"** is in the inbox: the obvious AI winners are priced; the under-priced leg is the
physical supply chain every buildout must pass through regardless of which model or cloud wins (electrical
gear, thermal, power delivery, interconnect) — datacenter compute as a power-and-heat problem. It is a
**seed**, deliberately not a filed thesis: it becomes a `thesis_call/v1` when the agentic analyst researches
it and the desk adds the second-order map + falsifiers, forward-dated. **Nothing is filed retroactively.**

## Status
BUILT + tested (`tests/test_thesis_desk_t324.py`, **16 passing**). The user-seeded channel is OPEN. Armed on
E/T-321 (the researcher) and C/T-322 (the long-horizon book). N_trials = 0 — this is infra plus a forward
record; it earns nothing until the pre-stated bar clears.
