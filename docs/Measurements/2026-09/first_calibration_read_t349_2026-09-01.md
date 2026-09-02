---
title: "The first calibration read — and the third broken clock behind it"
task: T-2026-09-01-349
status: REPORT-ONLY. No revision triggered. G1 untouched.
---

# First calibration read (n=55) — and the clock that was hiding it

## ★ Read this first: the production record said **0 resolved**, not 55

The dispatch's premise was that ~55 rows had resolved. They had not. **All 57 rows in
`analyst_predictions.jsonl` carry `resolvable: false` / `source_absent_or_stale`.** The
count of 55 is right; the word *resolved* was wrong. Every one of them resolves cleanly
against live prices — I verified all 55, with **zero** still-unresolvable.

**The mechanism (a third broken clock, the same shape as the first two):**
1. A prediction expires on day **D**.
2. The pulse's price series is causally trimmed to `< D` — correct for **signals**, which
   must never read a forming bar.
3. Resolution is the **opposite** operation: it looks backward at an expiry that already
   happened. With the trimmed series it cannot see its own expiry bar, fails
   `_has_thru`, and is logged **unresolvable**.
4. The idempotency rule — *"a prediction_id already in the log is never re-resolved"* —
   made that row **terminal**. The prediction was dead forever.

The baked fallback substrate (`data/processed/*.csv`) ends **2026-04-17**, so nothing
downstream could rescue it. Net effect: the eval ran daily, wrote records, printed a
clean line, and **settled nothing for a month**.

**Both halves fixed (T-349):**
- idempotency now binds on **settled** rows only; a fail-closed row is *"could not settle
  yet"*, not a verdict, and is retried (retries are marked `retry_of_unresolvable`, so the
  retry is visible rather than silent). Settled verdicts remain immutable.
- the eval is handed the **untrimmed** completed-bar series; the strategy still uses the
  trimmed one, so no signal can read a forming bar through this path.

**The numbers below are therefore a RECONSTRUCTION** — resolved offline against live
prices. They are not yet the production record; the production record repopulates when
the retry fix ships and the pulse re-attempts the 55.

## Reliability by decile (n=55)

| bucket | n | mean p | observed | gap |
|---|---|---|---|---|
| 0.3–0.4 | 5 | 0.354 | 0.000 | **−0.354** |
| 0.4–0.5 | 3 | 0.420 | 0.000 | **−0.420** |
| 0.5–0.6 | 45 | 0.553 | 0.422 | −0.130 |
| 0.6–0.7 | 2 | 0.620 | 0.500 | −0.120 |

**Every bucket over-predicts.** The direction is consistent across all four; the
magnitudes are not individually meaningful (three buckets hold 5, 3 and 2 rows).
**45 of 55 predictions sit in a single bucket (0.5–0.6)** — heavy clustering near a coin
flip.

## Murphy decomposition — `BS = reliability − resolution + uncertainty`

| set | n | Brier | reliability ↓ | resolution ↑ | uncertainty | base rate |
|---|---|---|---|---|---|---|
| **all** | 55 | 0.2445 | 0.0312 | **0.0136** | 0.2314 | 0.364 |
| constrained | 28 | 0.2450 | 0.0346 | 0.0060 | 0.2296 | 0.357 |
| agentic | 27 | 0.2440 | 0.0296 | 0.0239 | 0.2332 | 0.370 |

**vs the climatological baseline:** analyst **0.2445** vs base-rate **0.2314** — the
analyst is *worse* than always predicting the base rate. Mean differential **−0.0131**,
block-bootstrap **ci_low −0.0789**. The CI **straddles zero**, so "worse than
climatology" is *also* not established. n=55 cannot resolve the sign either way.

**Paired (22 days with both arms):** constrained **0.2406** vs agentic **0.2404** — a
difference of 0.0002. **No difference proven ⇒ the T-323 tie-break keeps the constrained
arm.**

## The learning-loop trigger table, evaluated explicitly

| trigger | reading | precondition ≥30 | CI-supported? | **verdict** |
|---|---|---|---|---|
| reliability HIGH | 0.0312, all four deciles over-predict | ✓ (n=55) | **No** — buckets hold 5/3/45/2; no per-decile CI | **NOT MET** |
| resolution ≈ 0 | **0.0136**, 45/55 clustered at 0.5–0.6 | ✓ (n=55) | **No** — skill differential ci_low −0.0789 straddles zero | **NOT MET** |
| both low → fix the INPUT | consistent with the reading | ✓ | No | **NOT MET** |
| 0/N channel | n/a here | — | — | n/a |

**NO TRIGGER IS MET → NO PROMPT REVISION.** Per the template's own rule, a revision needs
a **CI-supported** reading, not a suggestive one. The over-prediction direction is
consistent enough to be worth a **WATCH**, not an edit — acting on it now would be
tuning on noise, which is precisely what the precondition exists to prevent.

*Per-category note:* `relative_return` n=47 clears the floor; `dd_exceeds` n=8 does not,
so nothing category-specific is readable.

## ★ The structural finding: cohorts are starving

| cohort | n resolved | note-days |
|---|---|---|
| `daily_agentic/v1` | 27 | 23 |
| `daily/v2` | 22 | 18 |
| `daily/v3` | **3** | 3 |
| `daily/v4` | **3** | 3 |

Accrual runs at **~2.2 resolved/day**, so one cohort needs **~14 note-days** to reach the
30-resolved floor. The constrained prompt bumped **v3 → v4 in 7 days**. **The prompt is
evolving about twice as fast as its own evidence accrues** — at this cadence no cohort
ever becomes readable, and every validation is permanently "too early to say."

This is a defect in **our process**, not in the analyst. The learning-loop template
requires validation on the next cohort; a bump cadence faster than the accrual rate makes
that requirement unsatisfiable by construction. **Recommendation (not a unilateral
change):** adopt a **cohort-completion rule** — once bumped, a prompt holds until its
cohort reaches the 30-resolved floor (~14 note-days) unless the trigger is a structural
0/N, which is exempt because it needs no statistics. Both prompt changes made under the
0/N exemption were legitimate; the risk is the *next* one made on a statistical
rationale that its cohort can never supply.

## What this sample CANNOT say

- **Nothing about discrimination.** resolution 0.0136 on n=55 is not distinguishable
  from zero.
- **Nothing about skill.** The differential CI straddles zero in both directions.
- **Nothing about promotion.** G1 needs **≥150 resolved forward predictions**; we have
  55, of which none were in the production record until this fix.
- **Nothing about the arms.** 0.0002 apart is a tie, and a tie keeps the constrained arm.
- **Nothing about daily/v3 or v4.** n=3 each.

**The honest one-line summary:** *the analyst hedges near 0.5, over-predicts in every
bucket, and does not beat its own base rate — and n=55 is too small to establish any of
that at CI. The receipt worth having is that the record now exists at all.*
