# Prompt evolution log — the provenance stamp for every prompt version

**Append-only. One entry per prompt VERSION, written at the time of the bump.**

A prompt is not configuration; it is the instrument. Editing it changes what the
machine believes and therefore what every downstream record measures, so a prompt
change has to be documented to the same standard as a measurement-methodology
change: what triggered it, what it is expected to do, and how to undo it.

The mechanical guard already exists — the eval record segments by
`(model, prompt_version)` by construction (T-292), and each note's provenance
carries `prompt_version` + `prompt_sha256`. That makes a bump a **labeled cohort
boundary** rather than a corrupted record. This log is the human half: the
*reason* the boundary is there, so a future reader comparing two cohorts knows
what actually differed and whether the comparison is fair.

## The required stamp

Every entry states, without exception:

| Field | Why it is required |
|---|---|
| **Version + file** | the exact artifact; the SHA-256 is in every note's provenance |
| **Scope of change** | which sections moved and which are byte-identical — a comparison across the boundary is only valid for the parts that did not move |
| **Trigger** | the evidence that forced it. Never "it seemed better" |
| **Pre-stated outcome measure** | what we expect to see, **written before** the first note lands, so the change can be judged rather than rationalised |
| **Revert ID** | the exact prior version + caller change, so reverting is one edit and not an excavation |
| **Cohort note** | what downstream records must treat as a boundary |

Pre-stating the outcome is the load-bearing one. A prompt edit is a hypothesis
about behaviour; writing down what would count as it working — and what would
count as it failing — is what stops the next reader from finding the change
obviously correct in hindsight.

---

## `daily/v3` — open the `hypothetical_actions` channel (evidence 2026-08-15, bumped 2026-08-18, T-329c)

**Version + file:** `daily/v3` — `config/prompts/analyst/daily_v3.md`
(copied from `daily_v2.md`, then edited, so the diff is provably scoped).
Caller: `paper_trader/intel_pulse.py` → `prompt_path` + `prompt_version`.

**Scope of change:** the `hypothetical_actions` bullet, plus one added line in the
output-shape block (`no_action_reason`) and the header comment. The
**anchor-questions, calibration, and resolver sections are byte-identical to
daily/v2**, verified by diff — so the predictions contract, and therefore the
Brier/calibration record, is unchanged across the boundary.

**Trigger:** account-3 (the stage-2 AI trader) was built to turn
`hypothetical_actions` into real paper orders, and the pre-ignition check found
the channel structurally empty: **0 of 15 notes carried a single action**
(2026-07-27 → 2026-08-14). Not a bug — v2's own words. It called the actions
"SMALL exploratory satellite tilts", stated "**They are never executed**", and
ended "**Omit the whole list if you have no small-tilt view.**" The model complied
every day. Corroborating evidence from the independent consumer: C's
`LlmShadowBook` had 14 accrued points, every one `n_actions: 0, turnover: 0,
positions: {}, book_nav: 1.0` against a twin that compounded to 1.0329 — while
reporting `degraded: false, action: "applied"` daily. Igniting account-3 on that
input would have produced zero orders forever, reported as canonical.

**Pre-stated outcome measure** (written 2026-08-15, before any v3 note existed —
and unchanged since; the point of pre-stating is that it cannot be edited once the
first result is in):

1. **Primary — the channel opens.** Actions appear on days the note's own
   `market_assessment` expresses a directional or defensive view. Measured over
   the first 10 v3 notes: if **0** carry an action, v3 has failed and the cause
   is not the prompt; escalate rather than re-edit.
2. **Empty days are explained.** Every note with an empty list carries
   `no_action_reason`. The constructor records `no_view_reason` as `UNSTATED`
   when it does not — a rising `UNSTATED` count is a v3 failure, not a quiet one.
3. **Guardrail — no firewall breaches.** The ±20% / gross / turnover firewall is
   unchanged and rejects-whole rather than clamping. Expected breach rate: zero.
   **Any** breach means v3 loosened behaviour it was not meant to touch.
4. **Guardrail — the predictions record does NOT move.** The predictions sections
   are byte-identical, so a step change in prediction count, anchor compliance, or
   Brier at the v2→v3 boundary is a *contamination signal* (the action framing
   bleeding into prediction behaviour), not a result. Watch it explicitly.
5. **Honest null:** if actions appear but the resulting paper record is flat or
   negative, that is a finding about the analyst, **not** a reason to edit the
   prompt again. v4 requires its own trigger and its own stamp.

**Mechanical confirm (independent of anyone's judgement):** T-342's channel-liveness
registry asks "has this consumed field EVER been non-empty?" and currently scores
`hypothetical_actions` as **NEVER_ALIVE (0/17)** while `predictions` scores
**LIVE (17/17)** in the very same note files. That contrast is the cleanest possible
statement of the defect. When T-342 merges, **`hypothetical_actions` flipping to LIVE
is the confirm that v3 worked** — and its staying NEVER_ALIVE past outcome measure 1
is the confirm that it did not. The registry was built independently of this change,
which is what makes it a real check rather than a self-graded one.

**Revert ID:** set `prompt_path="config/prompts/analyst/daily_v2.md"` and
`prompt_version="daily/v2"` in `paper_trader/intel_pulse.py` (the two lines
changed in T-329c). `daily_v2.md` is unmodified and stays on disk permanently.
The `no_action_reason` schema field is optional in both directions and needs no
revert — v1/v2 notes validate with or without it.

**Cohort note:** notes with `provenance.prompt_version == "daily/v2"` and earlier
are the **channel-dark cohort** — their empty action lists are an artifact of the
prompt, not an allocation decision, and must never be pooled with v3 notes when
scoring allocation skill. C annotates the shadow book's 14 channel-dark days as
their own cohort — **17 such days as of 2026-08-18** (14 when this defect was found
on 08-15; the channel stayed dark for the three days it took to rule and fix, which is
itself part of the record). The real (account-3) and shadow books re-baseline together on
the same v3 notes from the same day, which is what keeps that A/B clean.
Account-3's own trading record carries `streams.llm_analyst.prompt_version` per
run, so the boundary is visible in the order record and not only in the eval one.

---

## `daily/v4` — the ticker-agnostic `market_tape` input repair (evidence 2026-08-20, bumped 2026-08-25, T-331bc)

**Version + file:** `daily/v4` — `config/prompts/analyst/daily_v4.md`
(copied from `daily_v3.md`, then edited, so the diff is provably scoped).
Caller: `paper_trader/intel_pulse.py` → `prompt_path` + `prompt_version`.
Companion CONTEXT change, same rev: `intelligence/analyst/context_builder.py`
adds the `market_tape` bundle section and bumps `bundle_version` to
`analyst_input/v2` — the prompt bump and the bundle bump are one evolution and
deploy together (a v4 prompt reading a v1 bundle would describe a section that
is not there).

**Scope of change:** one added prose section (`# Market tape (ticker-agnostic
context)`) before `# Anchor questions`, plus the header comment. The
**anchor-questions, calibration, and resolver sections are byte-identical to
daily/v3 — and therefore to daily/v2** — verified by test, so the Brier record
stays comparable across every boundary. The actions contract is untouched from
v3. Bundle side: `market_tape` is a NEW key; no existing section changed shape.

**Trigger:** the analyst flagged degraded news evidence on **19 of 19 notes**
(2026-07-27 → 2026-08-20, all spelling variants counted). T-331bc's diagnosis:
NEITHER the analyst nor the panel census was lying — the cloud panel was healthy
(2,706 rows) while the analyst's slice is TICKER-SCOPED and its ETF sleeve is
structurally near-uncovered on a company-tagged tape (SPY 47 tags, GLD 10,
AGG/BIL/IEF **zero** of 6,237). The ticker-agnostic blind scan sees a full
bundle on the SAME tape. Post-v3 confirmation the bottleneck moved here: all
three v3 notes (08-21/24/25) carried `actions: []` with an honest
`no_action_reason` **each citing degraded news evidence** — the analyst
correctly refusing to trade on inputs it cannot trust, forever, until the
inputs are repaired. Director ruling 2026-08-25: the held repair is released
(its hold condition — a clean v3 outcome read — was satisfied).

**Pre-stated outcome measure** (written 2026-08-25, before any v4 note exists):

1. **Primary — the evidence-starvation reason disappears.** Over the first 10
   v4 notes, `no_action_reason` citing thin/degraded news evidence should drop
   to ~zero on days the tape itself is healthy (`market_tape.degraded ==
   false`). If the analyst still declines FOR THAT REASON on a healthy tape,
   v4 has failed; escalate, don't re-edit.
2. **The canonical flag tells the truth.** With T-331c's writer-side canonical
   tokens on the same rev, a news-related risk flag now appears ONLY when the
   tape is actually degraded (`market_tape`/`news` `degraded == true`). The
   19/19 permanent-condition shape must break.
3. **Actions remain view-driven, not tape-driven.** No requirement that actions
   appear — a genuine no-view day stays legitimate. What must NOT happen: action
   frequency jumping because the model narrates headlines into trades without a
   stated view (watch the firewall-rejection and `no_view` counts).
4. **Guardrail — the predictions record does NOT move.** Byte-identical
   predictions contract again; a step change in prediction count, anchor
   compliance, or Brier at the v3→v4 boundary is a contamination signal.
5. **Guardrail — no invented tickers.** `market_tape` headlines name non-sleeve
   companies by design. Any prediction/action referencing a symbol outside
   portfolios/watchlist is a v4 failure (the firewall rejects it; the count
   must stay zero).
6. **Honest null:** if the analyst reads a full tape and simply performs no
   better, that is a finding about the analyst, not a licence for v5. v5 needs
   its own trigger and stamp.

**Revert ID:** set `prompt_path="config/prompts/analyst/daily_v3.md"` and
`prompt_version="daily/v3"` in `paper_trader/intel_pulse.py`, and remove the
`market_tape` key + restore `bundle_version: "analyst_input/v1"` in
`context_builder.build_bundle`. `daily_v3.md` is unmodified and stays on disk
permanently (sha256 `64bd8544c50fd5b0…`).

**Cohort note:** v4 changes the analyst's INFORMATION SET, not just its
instructions — both arms of the A/B (constrained + agentic share
`build_bundle`) receive `market_tape` from the same first day, so the paired
comparison stays like-for-like. Notes with `prompt_version` ≤ `daily/v3` are
the ticker-scoped-starvation cohort for any news-evidence analysis; do not pool
their risk-flag rates with v4's.

---

## `daily_agentic/v2` — open the agentic `hypothetical_actions` channel (ruling 2026-08-28, drafted 2026-09-01, A/T-348)

**Version + file:** `daily_agentic/v2` — `config/prompts/analyst/daily_agentic_v2.md`
(copied from `daily_agentic_v1.md`, then edited, so the diff is provably scoped).
SHA-256 `c1a3ac1e52add266b42f7288c456086192066715e27c1e564081a414ee03f334`.
Caller: `paper_trader/intel_pulse.py` → agentic `prompt_path` + `prompt_version`
(**deployment is E's**; prompt authorship is A's, per the standing pattern).

**Scope of change — verified by diff, section by section:**

| section | state |
|---|---|
| Role · How to investigate (tools) · **Anchor questions** · **Calibration** · **Resolvers** · Input bundle | **BYTE-IDENTICAL** |
| Absolute rules — the `hypothetical_actions` bullet | **changed (the whole point)** |
| Output shape — one added key (`no_action_reason`) | changed |
| Header comment | changed (version stamp) |

**The predictions contract is untouched**, so the Brier record stays comparable across
the cohort boundary and the paired prediction A/B is unaffected by this bump.

**Trigger:** the T-348 ruling (`docs/Audit/agentic_channel_ruling_t348_2026_08_28.md`).
The book-vs-book leg of the T-323 A/B is **structurally impossible** while only one arm
can act — a book with no action channel holds nothing. v1 carried the exact wording that
killed the constrained channel ("never executed", "omit the whole list"), which produced
**0 actions in 19 notes**, a book at **100% cash**, and **−$240/$10K** in the first
production digest. Leaving v1 in place would re-run a known-dead measurement.

**Pre-stated outcome measure** (written before the first v2 note lands):
1. actions appear on genuine-view days, and `no_action_reason` is present on the days
   they do not — i.e. an empty list becomes *distinguishable from a broken pipe*;
2. the agentic shadow book stops being structurally 100% cash;
3. the paired book comparison becomes computable at all (it currently cannot run).
**Not** a prediction that the agentic arm wins — see the tie-break below.

**★ BINDING CONDITIONS (carried from the ruling, and load-bearing):**
- **The book comparison runs on the COMMON WINDOW ONLY** — starting from the **later**
  of the two channel-open dates (constrained opened **2026-08-18**; the agentic open
  date is whatever E deploys). Without this the constrained book's head start reads as
  skill (T-323 §1.3, the different-windows error).
- **Record the agentic open date here when E deploys**, so the common-window start is a
  stamped fact rather than a later reconstruction.
  - ✅ **STAMPED AT DEPLOY (E, 2026-09-03): the agentic channel opens 2026-09-04.**
    rev31 (`paper-sha-55ef859`) was deployed the evening of 2026-09-03 with the
    caller on `daily_agentic/v2`, so the FIRST note written under v2 is the
    2026-09-04 09:45 ET scheduled pulse. This is the deploy-day fact, not a
    reconstruction: the image was verified in-container to carry
    `daily_agentic_v2.md` at SHA-256 `c1a3ac1e52add266…`, matching the repo.
  - **⇒ COMMON-WINDOW START = 2026-09-04** (the later of 2026-08-18 constrained and
    2026-09-04 agentic). Any paired book-vs-book directional comparison that begins
    earlier than this date is measuring the constrained arm's head start, not skill.
- **The T-323 tie-break is unchanged: no difference proven ⇒ KEEP THE CONSTRAINED ARM.**
  Opening the channel makes the comparison possible; it does not presume its outcome.

**Revert ID:** `daily_agentic/v1` — `config/prompts/analyst/daily_agentic_v1.md`;
revert = point the agentic `prompt_path`/`prompt_version` back at v1. One edit.

**Cohort note:** `(model, prompt_version)` segmentation makes this a labeled boundary
automatically. v1 and v2 agentic notes must **never be pooled** in a book comparison;
prediction-side pooling is acceptable *only* because the predictions contract is
byte-identical — and even then the record segments by version by construction.
