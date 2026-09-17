# T-355 — ANALYST_DESK retired; the agentic arm gets the book that fits it

**Date:** 2026-09-16 · **Owner:** E · **Trigger:** D's T-356 durability sweep, finding #5

## The finding, restated from the artifact

`data/state/analyst_desk_book.json` was **durable** — synced every session, in
`DURABLE_PATHS`, covered by a clock. Its source, `data/intel/agentic_analyst_calls.jsonl`,
**had no writer anywhere in the tree and never existed.**

Read off the live S3 object:

```
desk: analyst_desk | open: 0 | closed: 0 | days: 36
first day 2026-07-28 … last day 2026-09-16 | any day with calls? False
```

**36 durable sessions recording nothing.** This is the inverse of C's T-351
defect: C found a record that accrued and was not saved; this is one that was
saved and could never accrue. Both read "too early to say" forever, and no
durability check can see either — only a liveness check (T-342) can.

## The verdict: RETIRE, not wire

The desk shipped "dormant-but-armed until the feed exists — point `source_path`
at it when it lands; **no code change**." The feed did land. It landed in a shape
this desk cannot consume.

The agentic analyst emits `hypothetical_actions` — **continuous target weights**:

```json
{"account": "shadow", "symbol": "SPY", "set_weight": 0.025, "target_weight": 0.025}
```

No symbol carries a horizon. `EventShadowBook` is a **call-driven** book: a call
opens a shadow position that closes when its horizon elapses, scored against a
twin. A weight-driven feed and a call-driven book are different objects, so the
"no code change" premise was false from the moment the arm's output shape was
settled — and nobody noticed, because the book stayed green.

**Writing a producer for `agentic_analyst_calls.jsonl` would have been the wrong
fix**: it would manufacture a feed the arm does not actually produce, purely to
make a durability check go green. That is the shape of a live channel created to
satisfy a metric.

A second, smaller defect found alongside it: `DeskConfig.loader` advertised
`"event_calls" | "analyst_notes"`, but `_load_calls` never branched on it —
**the `analyst_notes` loader was never implemented.** A config key promising a
behaviour that does not exist is part of why the desk looked wireable. The field
is now documented as single-valued, with the instruction to add the branch before
adding a value.

## What replaces it

Nothing new was built. `LlmShadowBook` already implements weights → NAV-vs-twin
and already books the **constrained** arm; it was already parameterized on
`path` and `notes_dir`. So the agentic arm is a second instantiation —
**repoint over rebuild**:

| arm | notes | book | feeds the eval harness' G1 leg |
|---|---|---|---|
| constrained | `data/intel/analyst_notes` | `llm_shadow_book.json` (36 pts, from 07-28) | **yes** (unchanged) |
| agentic | `data/intel/analyst_notes_agentic` (29 notes) | `llm_shadow_book_agentic.json` (**t=0 pending**) | no |

The constrained arm remains the **only** input to `_shadow_twin`. That is a
running measurement with accrued history; blending or swapping its input would
corrupt it silently. Each arm keeps its own book so the A/B compares two records
rather than one record and an assumption.

## Disposition of the retired artifact — [NN-ARCHIVE]

`analyst_desk_book.json` is **removed from `DURABLE_PATHS`, not deleted.**
Dropping it from the sync freezes the existing S3 object exactly as it stands: it
is archived by being left alone. The census stops counting a phantom; the 36-day
record of the mistake stays readable.

## Not done yet — [NN-FIRST-ARTIFACT]

The agentic book has **no artifact**. It accrues on the first account-1 pulse
after this ships. Until `llm_shadow_book_agentic.json` appears in S3 with
`n_days ≥ 1`, this is a code change, not a working book — the same standard the
desk failed for 36 sessions.

**Backfill is possible but is a separate decision.** 29 agentic notes already
exist, so the arm's book could start with history rather than at zero. The same
rule applies as for C's tracker: a reconstructed point must be **labeled**
reconstructed and never blended into the forward series. Forward-only from t=0 is
the default here; backfill-with-labeling is the alternative, and it is a choice
to be made explicitly, not by whoever runs the job first.
