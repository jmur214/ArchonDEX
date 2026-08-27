---
task_id: T-2026-08-26-346
title: The Gate-1 +0.000 GRAVEYARD residue review — and the SUPERSESSION-DEPENDENTS rule
date: 2026-08-26
author: Agent D
type: DESK REVIEW — doc only, 0 N_trials, verdict-mapping. No measurement run, none needed.
status: FOR REVIEW
---

# The Gate-1 +0.000 graveyard — enumerated, mapped, and mostly empty

**The premise, as dispatched:** inverse-vol normalization algebraically cancels uniform timing signals
(T-156, verified EXACT at runtime by T-158), so every edge killed at Gate-1 with the +0.000 tell has no valid
negative verdict *as a sleeve-level input*. **The task:** enumerate the graveyard, map each family to its
later sleeve-level retest, and output the residue — the families whose only death was architectural.

**The headline is an inversion of what the premise expects, in both directions:**

> **The residue is ONE family, and it did not die of inverse-vol cancellation.** Two of the three graveyard
> entries were *already* closed by independent factor-α evidence that never depended on Gate-1 at all.
> **But the machinery defect the premise points at is real, un-fixed, and PROSPECTIVE** — it does not
> invalidate old verdicts so much as it means the *next* hand-written edge cannot get a valid one.

---

## 1. ⚠️ FIRST: `+0.000` IS NOT DIAGNOSTIC — at least THREE mechanisms produce it

The premise treats the tell as identifying a cause. It does not. From the record, an *exactly* +0.000 Gate-1
contribution has three distinct known causes, and **only the first invalidates the verdict as claimed:**

| # | mechanism | signature | invalidates? |
|---|---|---|---|
| **A** | **Architectural cancellation** — inverse-vol normalization makes weights scale-invariant in signal level, so a **uniform** (identical-across-names) timing/regime signal cancels algebraically (T-156 @ `policy.py:277/285`; T-158 exact at runtime) | uniform signal geometry | **YES** — the premise's case |
| **B** | **Sparse signal density** — too few names/bars to register against 6 actives producing thousands of trades (T-019: 5 paused edges → *zero* trades over 5yr while a peer at the same weight produced 451) | narrow, event-driven signal | **Partially** — verdict is real but scoped to "this configuration," not to the hypothesis |
| **C** | **The candidate never spoke** — a hand-written candidate that emits no non-zero signal makes the with-arm behaviourally identical to baseline, so contribution is *exactly* 0 | **exactly** 0.000, bit-level | **YES — and worse: it is not a verdict at all** |

**Cause C is the one nobody has ruled out**, and T-123 spotted it in real time (§3, 2026-06-06):

> *"two distinct hand-written candidates both yielding **exactly** +0.000 contribution warrants a look at
> whether `validate_candidate` actually loads injected candidates — otherwise **every future hand-written
> edge's Gates 1-6 are untestable**."*

T-123 also **explicitly retracted** the premise's discriminator: *"'cross-sectional vs timing' is not the
discriminator for Gate-1 contribution; both add ~0 here."* BAB is cross-sectional and cancellation should not
touch it, yet it returned the same exact zero. **Two different signal geometries returning bit-identical zeros
is evidence for C, not for A.**

## 2. THE GRAVEYARD — the complete enumeration is THREE entries

Documented Gate-1 `+0.000` / short-circuit deaths across the whole audit tree:

| edge | task(s) | date | signal geometry | independent evidence BESIDES Gate-1? |
|---|---|---|---|---|
| **VRP** (variance risk premium, equity proxy) | T-122 | 2026-06-06 | **uniform** timing (vol-managed market overlay) | ✅ **YES** — factor α = **−0.21%, t = −0.36, ci [−2.25, +1.58], p(α>0) = 0.37** |
| **BAB** (betting-against-beta) | T-123, deep retest **T-129** | 2026-06-06 / 06-10 | **cross-sectional** | ✅ **YES** — standalone analytical factor-α, *"the headline, independent of the Gate-1 short-circuit"*; T-129 re-ran on the friendliest factor + fairest window (incl. 2008) → **still ~0 α** |
| **spinoff reversion** | T-041b, **T-041c** | 2026-05-22 / 05-23 | **event-driven, sparse** | ❌ **NO** — Gate-1 is the only measurement |

The *"inert `macro_*` edges"* referenced by T-122 (`macro_yield_curve_v1`, `macro_credit_spread_v1`,
`macro_unemployment_momentum_v1`, `macro_real_rate_v1`, `macro_dollar_regime_v1`) are **not** gauntlet deaths —
they were never gauntleted; they were inert *inside* the ensemble. They belong to the macro/regime-timing
family, whose sleeve-level question was answered separately (§3).

## 3. THE MAPPING — later sleeve-level retests, by family

| family | later sleeve-level retest | verdict there |
|---|---|---|
| **VRP / premium harvesting** | **T-279** (premium-harvesting tier) | NEGATIVE **even where implementable**; put-write refuted as a diversifier. **A sleeve-level retest exists and it is a null.** |
| **BAB / low-beta / defensive tilt** | **T-129** (deep retest) then the tilt family **T-318 / T-320** | long-only **momentum** the only CI-significant tilt; **growth/tech REFUTED, quality straddles**. Low-beta/quality does not clear at sleeve level. |
| **macro / regime timing** (`macro_*`) | **T-172 / T-220 / T-221 / T-222 / T-233** — regime science SETTLED | **regime-GATING a self-timing signal HURTS**; tail protection is the always-on overlay, not the regime flip; HMM fires late. **Sleeve-level answer exists and is negative.** |
| **event-driven / spinoff reversion** | **— none —** | **THE RESIDUE** |

## 4. ⭐ THE RESIDUE — one family

### `spinoff_reversion_v1` / event-driven reversion — **CLOSE-WITH-REASON, with the scope restated**

**Why it is the only residue:** it is the sole graveyard entry with **no independent measurement** beside the
Gate-1 contribution, and **no later sleeve-level retest** of its family.

**But it did NOT die of inverse-vol cancellation (cause A).** The record is explicit about cause B: only
**~24 of 150** spin-off children had cached OHLCV in the validate-effective window, and T-041c re-ran it
cleanly with the paused-tier confound removed — **identical FAIL**. A sparse event edge produces too few
trades to move a 6-active ensemble; that is cause B, and the premise's mechanism does not apply.

**Verdict: CLOSE-WITH-REASON — subsumed by a broader null, with the scope already honestly stated.**
`lessons_learned.md` already records the correct reading: *"the verdict says 'this configuration doesn't show
measurable contribution,' not 'spin-offs don't generate alpha.'"* **That scoping was written at the time and
is still right** — nothing needs re-opening. It is further subsumed by **T-196's H0** (the cheap
price-vocabulary alpha hunt is exhausted, 0/35 cleared) and by the **re-anchor** finding that the honest
PIT × cost base is ~0.1-0.3.

**Stated prior if anyone ever revisits it: LOW.** A retest would need (a) a real spin-off child universe with
PIT-honest OHLCV coverage far above 24/150, (b) measurement as a **standalone sleeve**, never as an ensemble
contribution against 6 actives, and (c) a pre-registration consuming honest N. **I do not recommend it** —
this is the "closed by evidence" branch, not the "honestly open" one.

**Nothing else is residue.** VRP and BAB were **never** closed by architecture: both carry independent
factor-α measurements that stand whatever Gate-1 did, and BAB's was deliberately re-run (T-129) on the
friendliest possible terms. **The graveyard the external review worried about is, for practical purposes,
empty.**

## 5. 🔴 THE LIVE DEFECT — the finding that actually matters, and it is forward-looking

Cause C was never ruled out, and **the guard that would rule it out does not exist.**

- `validate_candidate` **does** inject the candidate today (`with_edges[cand_id] = cand_edge`,
  `discovery.py:1270-1271`) — so the crudest form of the T-123 worry is not present in current code.
- **`assert_baseline_healthy()`** (`gate1_signal_cache.py:310`, added by T-197 after T-195) fails loud on a
  degenerate baseline — **but it guards the BASELINE, and only against CRASHES**, not against an edge that
  runs fine and emits nothing.
- **There is NO candidate-side blind check.** `core/census.py` implements exactly the right test —
  `edges_blind` = "active edge fired 0 signals" — and **`discovery.py` never calls `assert_census`.**

> **A hand-written candidate that emits zero non-zero signals yields a contribution of exactly +0.000 and is
> recorded as REFUTED, indistinguishable from a genuine no-contribution result.** `[NN-CENSUS]` already
> declares such a run non-canonical (*"a run is NON-CANONICAL … if `edges_blind` is non-empty"*); the gauntlet
> path predates that rule and bypasses it.

**Recommendation (propose-first, Engine D):** call `assert_census` — or minimally a candidate-side
`edges_blind` assertion — inside `validate_candidate` before Gate-1's contribution is computed, so a silent
candidate raises instead of publishing a fake zero. **This is the T-123 item-4 recommendation, still
un-owned after ~2.5 months.** Its value is prospective: it does not change a single verdict above, and it is
the difference between the next hand-written edge getting a verdict and getting a number.

## 6. THE SUPERSESSION-DEPENDENTS RULE — and this review as its retroactive sweep

**The class-fix, for the verdict protocol:**

> **When any verdict flips to `refuted` or `superseded`, the SAME commit must sweep for the T-number across
> `docs/State/conditional_shelf.md`, `ROADMAP.md`, `forward_plan.md`, `CURRENT_STATE.md`, `config/`,
> `data/governor/`, and any open recommendation, and must either RE-OWN or FORMALLY RETIRE every dependent
> whose activation trigger, precondition, or "tested by" pointer cited it.** A refutation dissolves the
> trigger of everything downstream of it; without the sweep those dependents do not fail — **they go quiet**,
> which is indistinguishable from being fine. The sweep is part of the verdict, not follow-up work: a verdict
> that leaves live dependents pointing at a dissolved trigger is **half-recorded**.

**This review is the retroactive sweep for the biggest instance, and it found live orphans:**

1. **T-123 item 4 — the un-owned recommendation (§5).** Filed propose-first 2026-06-06: *"fix the gauntlet
   candidate-injection / Gate-1 path … otherwise every future hand-written edge's Gates 1-6 are untestable."*
   Never re-owned, never retired. **The guard still does not exist.** ← *re-own*
2. **T-195's two prod fixes.** Recorded as *"ship in the harness but are NOT yet applied to production
   discovery."* A deliberate, correctly-flagged deferral — but it has no owner and no trigger. ← *re-own or
   formally retire*
3. **`conditional_shelf.md` entry 4 — a stale forward-looking trigger.** It reads *"**T-172 tests whether** a
   deep-history re-train fixes generalization"* (line ~238). **T-172 has since run** (verdict MARGINAL) and
   the regime family closed via T-220/221/222/233. The entry's activation condition is phrased as awaiting a
   pending test that has already returned. ← *re-own: restate against the settled verdict*

**The grep habit, for `SESSION_PROCEDURES.md`** (added in this task):
```
grep -rn "T-<number>" docs/State/ docs/Core/ config/ data/governor/ | grep -v TASK_LEDGER
```
Run it in the same commit that writes a `refuted`/`superseded` status. Every hit is a dependent: **re-own it
or retire it in that commit.** `TASK_LEDGER.md` is excluded because the ledger is the *record* of the
verdict, not a dependent of it.

## 7. What this review did NOT do
- **No measurement, 0 N_trials.** Nothing was re-run and nothing needed to be.
- **No verdict was re-opened.** Two entries were already closed by independent evidence; the third is closed
  with its scope restated.
- **It does not fix §5's defect** — that is a propose-first code change on Engine D, recommended here, not
  taken unilaterally.

---
**DESK REVIEW — doc only, 0 N_trials.** The residue is one family, low-prior, close-with-reason. The value is
§5 (a live, prospective measurement defect) and §6 (the class-fix, plus three orphans it immediately found).
