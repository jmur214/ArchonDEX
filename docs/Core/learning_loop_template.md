# The learning loop — Brier decomposition → prompt revision → forward validation

**A standing FORM, not an event.** `prompt_evolution_log.md` records *what changed and
why* (the provenance stamp). This file specifies the half that comes before and after:
**which measured readings justify a revision at all**, and **how the revision is judged
once it ships**. Together they make evidence-paced learning a process.

The loop exists because the alternative is tuning on vibes. A prompt edit changes what
the machine believes; without a stated trigger and a pre-stated outcome, every edit
looks correct in hindsight and the record silently becomes a story about our own taste.

---

## Stage 1 — TRIGGER: which readings justify a revision

Read from the eval harness's Murphy decomposition (`summarize()` → `g1_skill`,
`by_prompt_version`), `BS = reliability − resolution + uncertainty`:

| Reading | What it means | Justified revision |
|---|---|---|
| **reliability HIGH** (poorly calibrated) | 60%-claims don't happen ~60% of the time | ask for fewer, better-grounded probabilities; add calibration guidance |
| **resolution ≈ 0** (no discrimination) | the model hedges to the base rate — its probabilities carry no information | give it something to discriminate WITH (a richer/actually-relevant input), or stop asking that question class |
| **reliability LOW + resolution LOW** | well-behaved but uninformative | the question class may be unanswerable from the given input — fix the INPUT before the prompt |
| **a channel is 0/N** (never exercised) | the prompt forbade or discouraged the behaviour | open the channel (this is `daily/v3`, instance #1) |
| **coverage measurement shows a starved input** | the model is reasoning from near-nothing | repair the INPUT; do not ask the prompt to compensate for missing data |

**Two hard preconditions before ANY revision:**
1. **Minimum evidence.** No revision on fewer than **30 resolved predictions** in the
   affected class, and the reading must be **CI-supported** (block-bootstrap, the
   T-293c standard) — not a point estimate. Revising on noise is how a prompt
   random-walks while looking maintained.
2. **A 0/N channel is exempt from (1)** — "never once, across every note" is not a
   noisy estimate, it is a structural fact (the `daily/v3` case: 0 actions in 19 notes).

## Stage 2 — PROPOSED EDIT

- **One change at a time.** Two simultaneous edits make the outcome measure
  uninterpretable — you learn that *something* moved, not which thing.
- **Scoped and diffable.** Copy the prior version, edit, keep every unrelated section
  **byte-identical**, and say so. A cross-cohort comparison is only valid for the parts
  that did not move.
- **Fix inputs before prompts.** If the trigger is a starved or broken input, the prompt
  edit is the wrong instrument — repair the input and re-measure first.

## Stage 3 — PROVENANCE STAMP

Write the entry in **`docs/Core/prompt_evolution_log.md`** (that file owns the format:
version+file, scope, trigger, pre-stated outcome measure, revert ID, cohort note). Do
not duplicate it here. The mechanical half is automatic — the eval record segments by
`(model, prompt_version)` (T-292/T-331c), so a bump is a **labeled cohort boundary**
rather than a corrupted record.

## Stage 4 — VALIDATION: the NEXT forward window, never the triggering one

**The load-bearing rule: a revision is judged on the cohort that comes AFTER it, never
on the cohort that triggered it.** Validating on the triggering data is in-sample by
construction — it is the prompt-engineering form of fitting the noise you just observed.

- Compare `by_prompt_version[new]` against `by_prompt_version[old]` on the **pre-stated
  outcome measure**, with the block-bootstrap differential CI.
- **Minimum forward window: 30 resolved predictions in the new cohort** (same bar as the
  trigger). Below that the honest verdict is *"too early to say (n)"* — the digest's
  own rule applies to our learning as much as to the machine's performance.
- **Three outcomes, all recorded:** improved (CI excludes zero in the intended
  direction) / no difference proven / regressed. **"No difference proven" keeps the
  simpler prior version** — absence of evidence does not promote the newer, more
  elaborate prompt, exactly as the T-323 A/B tie-break keeps the constrained analyst.
- A failed revision is **reverted by its revert ID**, and the failure is logged. A
  reverted change is not an embarrassment; an unlogged one is.

## What this loop can and cannot do

- **CAN:** change a prompt, a context bundle, or a question class, on stated evidence.
- **CANNOT:** promote anything, move a gate, or shorten a forward record. G0/G1 are
  untouched by every instance of this loop. A better-calibrated analyst is still an
  analyst on paper.
- **N-accounting:** a prompt revision consumes **no backtest N_trial** (it is not a
  measurement of the market). It does consume **record comparability** — it creates a
  cohort boundary, so the pre-`n` and post-`n` records must be counted separately
  toward any ≥150-resolved bar, never pooled.

---

## Instances

| # | Change | Trigger | Outcome measure | Status |
|---|---|---|---|---|
| **1** | `daily/v3` — open the `hypothetical_actions` channel | **0 of 19 notes** ever carried an action; `daily/v2` said actions "are never executed" and the model complied. A structural 0/N, exempt from the 30-prediction floor | actions appear on genuine-view days; `no_action_reason` present otherwise | shipped 2026-08-18 (T-329c); **awaiting first forward cohort** |
| **2** | analyst news-context / universe broadening | **coverage measurement** (T-331b): the analyst's slice is thin BY CONSTRUCTION — SPY 47, GLD 10, **AGG 0, BIL 0, IEF 0** of 6,237 ticker-tags; 19/19 notes flagged it. An INPUT repair, per Stage 2 | per-ticker doc counts in the bundle's new `coverage` block; the flag stops firing on healthy days | **approved in principle, HELD** until after daily/v3's first firing (one change at a time) |

*Instance 2 also carries E's writer-side adoption of the canonical risk-flag tokens
(`intelligence/analyst/risk_flags.py`) in the same pass.*
