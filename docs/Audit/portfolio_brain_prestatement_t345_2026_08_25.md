---
task_id: T-2026-08-25-345
title: THE PORTFOLIO BRAIN — pre-statement (written BEFORE any code, and before any stream is winning)
date: 2026-08-25
author: Agent D (with the director)
type: PRE-STATEMENT — nothing built. 0 N_trials. C builds only on the §6 precondition.
status: FOR REVIEW / RATIFICATION
---

# The portfolio brain — pre-stated

**What it is:** the cross-stream allocator. It reads each stream's live record, conviction and risk, and
outputs **suggested account-level weights across streams**.

**Why this is written now:** the same reason T-329 was written before account-3 existed — *"so the rules that
decide who gets to trade it cannot be written after seeing which stream is winning."* Today no stream has
cleared the 60-day evaluability gate, so **no allocation rule written today can be motivated by a result.**
That property is perishable and expires the moment the first stream clears.

## 0. WHAT IS ALREADY DECIDED — inherited, not re-opened

**`docs/Audit/account3_ladder_netting_prestatement_t329_2026_07_28.md` governs and is cited, never
re-stated or relaxed:** streams are independent sub-budgets; **no netting, ever** (netting destroys
attribution); disagreement is logged as data; account-level risk limits bind on the **sum** and breach
resolves by **pro-rata scale-down of all streams**, never by silencing one; per-stream `client_order_id`
prefixes from order #1; the wash guard is the authority on cross-stream wash sales.

**The brain's delta, stated exactly:** T-329 froze the sub-budget fractions as **FIXED**. *The brain is the
proposal to make those fractions MOVE.* Everything else in T-329 stands unchanged.

**On the netting question the dispatch raises: netting NEVER — and the brain does not reopen it.** The brain
allocates *across* streams; it never nets *within* or *between* them. Two streams on opposite sides of the
same ticker both still trade, at whatever weights the brain assigns.

---

## 1. ⭐ THE WEIGHT FLOOR — because a zero weight is netting wearing an allocation costume

If the brain may set a stream's weight to **0**, it has silenced that stream — which T-329 forbids when a
risk limit does it, and which destroys the per-stream record the ladder needs. **The prohibition cannot
depend on which mechanism does the silencing.**

> **BINDING: while a stream is ON the ladder, its weight is confined to `[w_min, w_max]` with `w_min > 0`.
> The brain can never remove a stream. Only the ladder can** (T-329's reversible-joining rule), and that is a
> director act on a frozen bar, not an allocation output.

Proposed initial band: **`w_min = 0.05`, `w_max = 0.50`** of the account's stream budget — wide enough for the
brain to express a real view, narrow enough that a wrong view cannot end a record. A stream the brain wants
at zero is a stream the brain is arguing should leave the ladder; **that argument goes to the director as a
report, not to the order router as a weight.**

## 2. ⭐ THE CIRCULARITY TRAP — the brain must not grade its own homework

The brain allocates **on** per-stream records. If a stream's record is measured in **dollars**, then the
brain's own weight decision changes the record it will read next period — a stream the brain starved looks
bad *because* it was starved, and the brain confirms itself. **Attribution silently becomes a function of the
allocator.**

> **BINDING: every per-stream record used as a brain INPUT is computed on the stream's own UNIT-NORMALIZED
> return series — invariant to the weight the brain assigned.** Dollars are reported to the user; **per-unit
> returns are what the brain and every gate read.** A stream at 5% and the same stream at 50% must produce the
> identical Sharpe, wealth-ratio and `book_vs_twin` verdict.

This is the difference between an allocator that learns and one that manufactures its own evidence, and it
is invisible unless stated before the code exists.

## 3. Inputs and output

**Inputs, per stream** (all already produced or specified elsewhere — the brain introduces no new measurement):
- **Live record** — unit-normalized daily returns, `book_vs_twin` verdict, evaluable-day count, MaxDD vs twin.
  Reuses `intelligence/analyst/fleet_scoring.book_vs_twin` **unchanged**; the brain does not define a new gate.
- **Conviction** — the stream's own stated confidence where it publishes one (thesis `prior`, note
  `probability`). **Read as an input, never as an authority** — higher stated confidence is a known LLM
  artifact, not a skill signal (T-329's "loudest conviction wins" rejection, applied here).
- **Risk** — the stream's realized vol and drawdown, and its contribution to account gross.

**Output — exactly one artifact:**
```
data/intel/brain_book.jsonl        # append-only, one record per run
{ as_of, schema_version: "brain/v1",
  suggested_weights: {stream_id: float},     # sums to 1.0 over ON-ladder streams, each in [w_min, w_max]
  current_weights:  {stream_id: float},      # T-329's fixed fractions, for the paired comparison
  rationale: {stream_id: str},
  inputs_hash: str, evaluable_days: {stream_id: int},
  authority_level: "report_only"|"shadow_scored"|"paper",
  degraded: bool, skip_reason: str|null }
```
**Fail-closed:** a missing or stale per-stream record does **not** yield a plausible weight — the record is
emitted with `degraded: true` and a `skip_reason`, and **no weights are suggested at all** (`[NN-FAIL-CLOSED]`).
A partial allocation across an unknown subset is exactly the "abstain to a plausible number" defect.

## 4. THE AUTHORITY LADDER — three rungs, each with a frozen promotion bar

| rung | what it does | promotes when |
|---|---|---|
| **1. report-only** | writes `brain_book.jsonl`. **Nothing reads it.** Appears in the digest beside the fixed weights. | ≥ **60 evaluable days** of suggestions AND ≥2 streams with live records |
| **2. shadow-scored** | a **shadow NAV** compounds the suggested weights against the real per-stream returns. Still nothing trades on it. | its shadow beats its twin (§5): Δwealth **`ci_low` > 0** over ≥60 evaluable days AND MaxDD ≤ twin + 5pp |
| **3. paper authority** | the suggested weights become the actual sub-budget fractions, inside T-329's risk limits | **director AND user**, explicitly, after rung 2 clears. Never automatic. |

**Report-only means report-only, mechanically.** While `authority_level == "report_only"`, a **grep-assertion
test** asserts no execution or sizing path reads `brain_book.jsonl` — the same "closed by construction, not by
convention" pattern as T-344's allocator door and the seed firewall.

**Demotion is symmetric and automatic.** A brain that stops clearing its bar returns to the rung below and
keeps being scored — mirroring T-329's *"removal is not a punishment; it is the ladder working."* Without a
stated demotion rule, promotion is a ratchet.

## 5. THE BRAIN'S TWIN — the honest one is free

> **The twin is T-329's CURRENT POLICY: the fixed sub-budget fractions, over the same streams, on the same
> days, from the same per-unit returns.**

The brain must beat **"don't think — use the frozen fractions."** This twin is the right one for three
reasons: it is the actual status quo (so beating it is exactly the decision to adopt the brain); it costs
nothing to compute; and it cannot be gamed, since it is not a benchmark chosen for flattery. Reported
alongside: **equal-weight** across on-ladder streams, as a second, dumber reference.

**Both `[NN-SHARPE-CI]` and the evaluability gate bind:** block-bootstrap CI, gate on **`ci_low`**, never a
point estimate; and **a spectacular 10-day record still reads "too early to say"** (T-329/A's digest law).

## 6. PRECONDITION FOR BUILDING — and a caveat on today's state

**C builds the report-only brain book only after ≥2 streams have live records.** That is a gate on *records*,
not on streams existing: a stream that trades but is inside the 60-day window has no record yet.

**Honest note:** the first performance digest reported *"Nothing is decidable yet — all streams inside the
60-day minimum."* **This precondition should be checked against the current digest before C starts, not
assumed** — and the check is the digest's own output, not a code inspection (`[NN-FIRST-ARTIFACT]`). If fewer
than two streams have live records, the brain does not get built yet, and that is the ladder working.

## 7. ENGINE BOUNDARY — the brain is Engine C and may never set a risk limit

**Allocation across streams is Engine C's job. Risk limits are Engine B's.** The brain proposes weights
**inside** a risk budget it does not control; it may never propose a change to gross exposure, per-name caps,
or the drawdown kill. If the brain's suggestion would breach an account limit, **T-329's pro-rata scale-down
applies to the result** — the brain is not consulted about how to resolve the breach, because a resolution
that favours the brain's preferred stream is a discretionary override wearing a risk costume
(`[NN-ENGINE-BOUNDARIES]`; any Engine B touch is propose-first).

## 8. NON-uses
1. **Never nets.** Allocation across streams only, per T-329 (§0).
2. **Never zeroes a stream** while it is on the ladder (§1); never removes one (only the ladder does).
3. **Never sets or relaxes a risk limit** (§7).
4. **Never re-scores a stream.** It consumes `book_vs_twin`; it does not define its own gate.
5. **Never reads dollars** for allocation input — per-unit returns only (§2).
6. **Never promotes itself.** Rung 3 requires director **and** user.
7. **0 N_trials** — this is a pre-statement, and the brain's own forward record is its evidence.

## 9. What this costs, honestly
- **The brain cannot be built for a while, and the gate is real** — ≥2 live records, then 60 evaluable days at
  each rung. Rung 3 is, realistically, **many months** out. That is the correct pace for handing an allocator
  authority over real sub-budgets.
- **The weight floor deliberately caps the brain's upside.** A brain that is right about a bad stream still
  carries it at 5%. That is the price of keeping every record scoreable, and it is worth paying while the
  brain is unproven; `w_min` is revisable **only** by a new pre-statement, never mid-flight.
- **The unit-normalization rule (§2) is extra plumbing** — records must be produced weight-invariantly, which
  is more work than logging dollars. It is the plumbing that makes the whole exercise honest.

---
**PRE-STATEMENT — nothing built. 0 N_trials.** Written before any stream is winning, which is the only time
it can be written honestly. Inherits T-329 entirely; changes only "fixed" to "moving," under a floor.
