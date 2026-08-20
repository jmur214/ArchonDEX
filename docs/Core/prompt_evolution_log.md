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
