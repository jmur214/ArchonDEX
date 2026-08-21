# T-342 — CHANNEL LIVENESS + the shadow book's dark cohort

**Date:** 2026-08-18 · **Agent:** C · Branch `feature/channel-liveness-t342` · **0 N_trials** (infra)
Read-only, zero order effect.

## The gap this closes
The T-338 census asks **"did this clock ADVANCE today?"** That question is structurally blind to a different failure: a consumer that runs perfectly every day while **the field it consumes has never once been non-empty.**

The `llm_shadow_book` ran **17 honest days** reporting `action:'applied'` over a structurally empty `hypothetical_actions` — and every record was **true**, because applying nothing *is* applying the note. Every clock ticked. Nothing degraded.

> **E's rule is the charter: an always-empty channel DEGRADES NOTHING**, so no freshness gate, no clock, and no daily assertion can see it. **Only an existence-over-history assertion can:** *has this load-bearing field EVER been non-empty, across its entire observed history?*

## Part 1 — the class fix: `channel_liveness()`
A **channel registry declared per consumer** (who breaks if this field is dead), each scanning the **entire** history of its source. Four statuses:

| status | meaning |
|---|---|
| `LIVE` | non-empty at least once in all history |
| **`NEVER_ALIVE`** | **empty in every record ever — "verify upstream intent"** |
| `UNVERIFIABLE` | source missing / unparseable / check raised — **a FINDING, never assumed alive** |
| `NO_HISTORY` | no records yet — nothing to assert (kept distinct so a newly-armed consumer isn't a false alarm) |

**Verified against REAL production notes (17 pulled from S3):**
```
NEVER_ALIVE  llm_shadow_book   hypothetical_actions   EMPTY in all 17 records of its entire history
LIVE         eval_harness      predictions            non-empty in 17/17 records
```
**Those are the same 17 files.** One field dead, one field alive — that discrimination is the proof the check isn't merely flagging everything.

Fail-closed in spirit, read-only like the census, and wired into the pulse under heartbeat key **`channel_liveness`** with its own same-day notify naming `consumer:field`.

## Part 2 — the dark-cohort annotation (the instance)
`llm_shadow_book.heartbeat()` now carries a `cohort` block when its consumed channel was structurally empty:
- **label:** *"daily_v2 era — channel structurally empty; NOT an allocation decision"*
- **CAN evidence:** the book, firewall and fill path **ran correctly end-to-end** — the plumbing is proven.
- **CANNOT evidence:** *any* judgement about allocation skill. **100% cash was the PROMPT's behaviour, not the model's choice** (daily_v2 said the actions are never executed and to omit the list). Do not score this stretch against the twin.
- **re_baseline:** when a new prompt version lands, the book **re-baselines at the version boundary** together with the real account — that is the clean A/B; comparing across the boundary is not.

Same class as the NOT-EVALUABLE guard: **the framing travels WITH the numbers**, raw points byte-unchanged. It **self-clears** the moment a real allocation appears (tested).

## Why this is worth more than the instance
The instance is one book's 17 days. **The class is every consumer we will ever wire.** An always-empty input is invisible to every guard we had — the record looks healthy, the clock advances, the verdict is honest — and it can only be caught by asking a question about *history*, not about *today*. That question now runs daily and is registered per consumer, so a new consumer declaring a load-bearing field inherits the check.

**10 new tests; 92 green across the book+census family.** doc_lint clean.

**T-342 done.**
