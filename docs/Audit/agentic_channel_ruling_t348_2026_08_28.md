---
title: "RULING — open the agentic action channel SYMMETRICALLY (A/T-348)"
task: T-2026-08-28-348
status: RULING (owner: A, as the owner of the T-323 A/B gates)
---

# Ruling — open the agentic `hypothetical_actions` channel symmetrically

**The question:** `daily/v3` opened the action channel for the **constrained** analyst.
Does the **agentic** arm open too — now, symmetrically — or does it stay single-arm so
the constrained arm establishes a baseline first?

**RULING: open it symmetrically. Asymmetry does not create a baseline; it creates a
confound.**

## The reasoning

**1. The two A/B comparisons have different dependencies — separate them first.**

| comparison | needs the action channel? | status |
|---|---|---|
| **prediction skill** (paired Brier differential, T-323 §1.2) | **No** — both arms already emit predictions | already symmetric and running; **unaffected either way** |
| **book-vs-book directional** (T-323 §1.3) | **Yes** — a book with no action channel holds nothing | **structurally impossible while asymmetric** |

So the decision only binds on the directional leg, and there it is decisive.

**2. A closed channel is not a baseline — it is a known-dead measurement.** We have
already run this experiment by accident: under `daily/v2` the constrained analyst
emitted **0 actions in 19 notes** and its shadow book sat **100% cash**, printing
**−$240/$10K** in the first production digest. That result taught us nothing about the
analyst's judgment; it measured the prompt's own prohibition. Repeating it on the
agentic arm would spend months of forward record re-learning it.

**3. Asymmetry confounds two variables at once.** With only the constrained arm acting,
a book comparison measures *tool access* **and** *channel state* together. The whole
purpose of the T-323 matched design is that exactly one thing differs between arms. The
symmetric open is the version that isolates the variable we care about.

**4. It does not contaminate `daily/v3`'s outcome measure.** v3's pre-stated measure
(actions appear on genuine-view days; `no_action_reason` otherwise) is computed on the
**constrained arm's own cohort**. The agentic prompt is a different arm with its own
`prompt_version`, and the eval record segments by `(model, prompt_version)` by
construction (T-292/T-331c). The director's "one change at a time" ruling protected v3's
read on **its own channel** — this is a different channel, so the rule is respected, not
bent.

**5. The risk is bounded and already governed.** Both are **shadow books** — report-only,
zero account cost, no real orders. The G0/G1 ladder is untouched; nothing here promotes
anything. Account-3's ignition is governed by its own frozen ladder (T-329 §1), which
this does not alter.

## The binding condition (do not skip this)

**The book comparison must start from the LATER of the two channel-open dates.** The
constrained channel opened 2026-08-18; if the agentic channel opens later, the paired
directional comparison runs on the **common window only** (T-323 §1.3). Without this the
constrained book carries a head start that would read as skill — the same
different-windows error the digest's own rules exist to prevent.

Practically: stamp the agentic open in `prompt_evolution_log.md` as its own instance
(trigger: this ruling; outcome measure: actions appear and the agentic book stops being
structurally 100% cash), and record the common-window start date with it.

## What this ruling does NOT do

- It does not promote either arm, or shorten any gate.
- It does not change the T-323 tie-break: **if the A/B proves no difference, the
  constrained arm is kept** (less attack surface, less cost). Opening the channel makes
  the comparison possible; it does not presume its outcome.
- It does not touch real orders.
