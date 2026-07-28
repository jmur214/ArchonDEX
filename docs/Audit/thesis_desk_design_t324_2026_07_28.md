---
task_id: T-2026-07-28-324
title: The Thesis Desk — thematic/narrative investing, made falsifiable
date: 2026-07-28
author: Agent D
type: INFRA + forward-accrual design (0 N_trials; forward-only BY NECESSITY)
status: BUILT + AMENDED (T-324b: machine-originated is PRIMARY, bias firewall, blind-scan hold). Branch feature/thesis-desk-t324b
---

# T-324 — the Thesis Desk

**User directive:** the machine's H0 covered QUANT cross-sectional selection and never THEMATIC thesis
investing — "finding stocks or sectors poised for growth" (tech inflections, adoption curves,
geopolitical rearmament, picks-and-shovels plays). That faculty requires reading narratives and mapping
**second-order beneficiaries** — impossible pre-LLM, possible now. **Per T-324b (below) the machine is the
PRIMARY originator: it finds the themes IT likes and trades those.**

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
_(Priority CORRECTED by T-324b — see below: machine-originated is PRIMARY; the seeded channel is
low-priority AND firewalled out of the machine's generation context.)_
- **(a) MACHINE-ORIGINATED (PRIMARY)** — a weekly strong-tier thematic scan over the news panel + event flow
  + rate-path: what themes are emerging, who benefits second-order, write the theses it believes in.
- **(b) USER-SEEDED (low-priority, firewalled)** — `data/coordination/thesis_inbox.md`, a `## title` + a few
  lines of plain English + optional `tickers:`. The user specifies no falsifiers/weights/second-order maps;
  the agentic analyst (E/T-321) researches the seed and the desk formalizes it. **Seeds are invisible to the
  machine's generator** (§T-324b.2), so they cannot bias it.
- Both produce a `thesis_call/v1` that must fully validate; a bad thesis is **never filed** (raw archived).
- **Forward-only guard (`[NN-AI-GATE]`):** `assert_forward_only` REFUSES any `as_of` materially in the past
  — **a backtested thesis is memorization** (the model knows how the story ended). Even fixtures are synthetic.

## Scoring: skew-aware BY DESIGN (`thesis_scoring.py`)
Thematic wins are rare-but-large, so a Brier/hit-rate view would score a genuinely good skewed
record as a failure. The promotion bar therefore carries **both**: Brier (is the stated conviction *honest*?) **and** a
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

**A +557% (6.6×) winner clears a 3-loser record but NOT a 4-loser one.** So "1-in-5 with a
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

## Thesis #1 (user-seeded — HELD UNFILED pending the machine's first blind scan, per T-324b.3)
**"AI picks-and-shovels"** is in the inbox: the obvious AI winners are priced; the under-priced leg is the
physical supply chain every buildout must pass through regardless of which model or cloud wins (electrical
gear, thermal, power delivery, interconnect) — datacenter compute as a power-and-heat problem. It is a
**seed**, deliberately not a filed thesis: it becomes a `thesis_call/v1` when the agentic analyst researches
it and the desk adds the second-order map + falsifiers, forward-dated — and, per T-324b.3, **only after the
machine's first BLIND scan completes**, so convergence/divergence is a real experiment. **Nothing is filed
retroactively.**

## Status
BUILT + tested (`tests/test_thesis_desk_t324.py`, **16 passing**). The user-seeded channel is OPEN. Armed on
E/T-321 (the researcher) and C/T-322 (the long-horizon book). N_trials = 0 — this is infra plus a forward
record; it earns nothing until the pre-stated bar clears.

---
## T-324b AMENDMENTS (2026-07-28) — DIRECTIVE CORRECTION: the machine REPLACES the user on thematic work
The user's correction, verbatim intent: *"I DO want the machine to replace me. I want it to find the themes
or ideas it likes and trade those."* **"The machine becomes your research desk" was the opposite of the
intent** — the framing above is superseded by this section. Four amendments, all implemented.

### 1. Machine-originated is the PRIMARY channel (not a sidecar)
`intelligence/thesis_desk/thesis_scan.py` is the desk's main engine: a **weekly** (`SCAN_CADENCE_DAYS = 7`)
thematic scan on the **strong tier** (`SCAN_TIER = "weekly"`) over the news panel + event calls + rate path,
tasked to *"identify emerging themes and the second-order beneficiaries; write the theses you believe in."*
Cadence rationale: theses are long-horizon, so weekly is frequent enough to catch an emerging theme and slow
enough that the desk is not chasing noise. `due(as_of)` enforces it.

### 2. THE BIAS FIREWALL — structural, fail-closed
The generator's context may **never** contain user-seeded material. User theses live in a separate namespace
(`origin == "user_seeded"`), and enforcement is structural rather than procedural:
- `load_machine_theses()` returns **only** `origin == "machine"` rows — user theses are invisible to
  own-notes retrieval;
- `build_scan_bundle()` assembles only machine-visible sources and then calls
- `assert_bundle_is_blind()`, which **RAISES `FirewallBreach`** if any user seed id / narrative slice leaked
  into the bundle (checked against fingerprints drawn from BOTH the ledger and the inbox).
So a future refactor that widens retrieval trips a **test**, not the tape. **Both channels are scored
identically** in A's table; only **generation** is isolated — *the machine's record must be attributable to
the machine.*

### 3. THE BLIND-SCAN EXPERIMENT — sequenced and provenance-stamped
The user seeded "AI picks-and-shovels" *before* the machine's first scan, so that seed is **HELD UNFILED**
until the first blind scan completes (`seeds_are_held()` returns True while `scans == 0`); then **both** file.
The natural experiment: does the machine **independently converge** on AI-infrastructure themes, or find
different/better ones? Convergence and divergence are both informative — but only if the first scan is
**provably** blind, so `scan_provenance()` stamps `blind_scan_ordinal`, `is_first_blind_scan`,
`seeds_existed_at_scan_time` (the seed ids that existed but were invisible), and `firewall_asserted` into the
record. The inbox now carries the CHANNEL STATUS + BLIND-SCAN HOLD notice.

### 4. Fixtures scrubbed of user-specific trades
The skew break-even finding **stands as arithmetic** (it is a property of log-compounding, not of anyone's
record), but the fixtures now use synthetic numbers only. **The desk scores the theses it FILES; the user's
past trades are not under test.**

**Tests:** `tests/test_thesis_scan_firewall_t324b.py` (8) + `tests/test_thesis_desk_t324.py` (16) = **24 pass**,
covering the namespace split, both leak paths raising, fingerprints from ledger+inbox, the blind-scan hold,
provenance ordinals, and the weekly cadence.
