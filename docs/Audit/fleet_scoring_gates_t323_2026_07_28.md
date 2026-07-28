---
title: "Fleet scoring — PRE-STATED A/B gates + the disagreement channel (P2.6)"
task: T-2026-07-28-323
status: PRE-STATED — written BEFORE the first agentic note and BEFORE any disagreement data exists
---

# T-323 — fleet scoring gates (pre-stated)

The judgment layer is becoming a FLEET: the constrained analyst (E/T-292), the
agentic analyst (E/T-321), the event-interpreter (D/T-304), each with notes,
predictions, and now BOOKS. My harness is the scoreboard. **This doc is written
BEFORE the first agentic note exists and BEFORE any disagreement data accrues** —
that timing IS the integrity of these gates. Nothing below may be revised after
seeing the data; a revision is a NEW pre-registration with its own record.

**Posture (program-official):** the G0/G1 ladder remains the **real-money** gate. On
paper, **everything runs and everything is scored**. Scoring is not authorization.

---

## §1 — Constrained vs agentic: the A/B gates

**The comparison must be paired on the SAME question set.** An agentic analyst that
answers *different, easier* questions than the constrained one is not better — it is
incomparable. This is the single largest gameability risk in the fleet comparison.

**1.1 The matched question set (defines eligibility).** A prediction pair is eligible
iff both sources emitted a prediction with:
- the same `resolver.type` AND the same resolver **target** (`symbol` / `symbol_a+b` /
  `event_id`), AND
- the same resolution date (`by_date` / `end_date`), AND
- both resolved `resolvable=True` (fail-closed applies symmetrically).
Everything else is scored in each source's own pool but is **excluded from the paired
A/B**. The eligible-pair count is REPORTED (a shrinking matched set is itself a
finding — it means the two sources are drifting apart in what they'll commit to).

**1.2 The gate.** Paired **Brier differential** (constrained − agentic) over eligible
pairs, **circular block bootstrap** on the resolve-date-ordered differential (block
~ n^(1/3), the project standard — same machinery as the amended G1):
- **Agentic WINS iff `diff_ci_low > 0`** (agentic's Brier is lower by a margin
  excluding zero), on **≥ 50 eligible pairs**.
- **Constrained WINS** symmetrically (the test is two-sided; state which side).
- **Otherwise: NO DIFFERENCE PROVEN** — and the tie-break is explicitly *cost + risk*:
  the constrained analyst is a single structured call with no tool surface; the
  agentic one has strictly more attack surface and cost. **A tie means keep the
  constrained one.** Absence of evidence does not promote the more complex system.
- Report **raw AND walk-forward-recalibrated** differentials (both sources
  recalibrated on their own history). A model that merely *sounds* more confident
  must not win on calibration artifacts.
- **Gimme exclusion** applies (drop pairs where a baseline is >0.9 or <0.1).

**1.3 Book-vs-book (directional).** Same G1-grade standard, applied symmetrically:
each source's shadow book vs **the 60/40 twin as the null** (not vs each other first).
- Report per book: Δwealth vs twin, MaxDD vs twin, and the paired Δ with block-
  bootstrap ci_low over the **common** window (books that started on different dates
  are compared only on their overlap — a longer window is not skill).
- **A book "clears" iff** Δwealth ci_low > 0 vs its twin AND MaxDD ≤ twin + 5pp
  (the G1 directional standard, unchanged).
- Head-to-head (agentic book vs constrained book) is reported but is **secondary** —
  beating the other model while both lose to the twin is not a result.
- **≥ 6 months** is the reporting floor and, per the program doc, still **cannot
  support a skill claim** — it promotes authority-on-paper, not belief.

**1.4 Anti-gaming clauses (stated now, not after).**
- **Question-set drift:** if the eligible-pair count falls below 50% of the smaller
  source's resolved count, the A/B is reported as **INCONCLUSIVE (drifted sets)**
  regardless of the differential.
- **Volume asymmetry:** emitting more predictions is not skill. All comparisons are
  per-prediction means, never totals.
- **Selective abstention:** a source that abstains on hard questions and answers only
  easy ones is caught by the matched-set requirement + by reporting each source's
  **coverage** (predictions emitted / eligible questions available).
- **Segment before pooling:** report by `category` as well as pooled; a pooled win
  driven entirely by one easy category is disclosed, not hidden.

---

## §2 — The disagreement channel (P2.6), pre-stated

A second-model pass runs on the **SAME input bundle** (the daily note is cheap-tier;
the governor covers it). We score **disagreement itself**. Pre-stated before data.

**2.1 Definition.** For each matched question (per §1.1) with probabilities
`p_A, p_B`: `divergence = |p_A − p_B|`. Bucketed: **LOW < 0.15 ≤ MID < 0.35 ≤ HIGH**.
Thresholds fixed here; no post-hoc tuning.

**2.2 The three pre-registered questions.**
- **Q1 — does either side win systematically when they diverge?** On HIGH-divergence
  pairs only: paired Brier differential (A − B), block-bootstrap ci_low. **A side
  "wins on disagreement" iff ci_low excludes zero on ≥ 30 HIGH pairs.** Honest prior:
  **NULL** — two RLHF models on the same bundle are highly correlated; expect no
  systematic winner. A null here is a real, publishable finding for the program.
- **Q2 — is divergence informative of VOLATILITY?** Test: does mean divergence on
  day *t* predict realized |return| of the referenced symbol over the prediction
  horizon, vs an unconditional baseline? Gate: rank-correlation with block-bootstrap
  ci_low > 0 on ≥ 60 observations. Honest prior: **LOW-MEDIUM** (plausible — model
  disagreement may proxy genuine ambiguity — but it is also a pure artifact channel).
- **Q3 — is the ENSEMBLE better than either?** Score the simple average
  `(p_A + p_B)/2` as a third virtual source in the §1 machinery. Honest prior:
  **MEDIUM-HIGH** — averaging two correlated-but-imperfect forecasters usually beats
  either individually; this is the most likely real win in P2.6 and the cheapest.
- **N-accounting:** these are FORWARD scoring questions on data the program accrues
  anyway (0 backtests). They consume **0 N_trials** under the program's Lane-3
  accounting, BUT Q1–Q3 are pre-registered here so they can never be reported as
  discoveries after the fact.

**2.3 The trap this closes.** Without pre-stating, "the models disagreed and X was
right" is an infinitely re-tellable story — you can always find a divergence subset
where one side won. Fixing the buckets, the minimum-N, and the CI rule NOW makes
Q1–Q3 falsifiable.

---

## §3 — The fleet table (dashboard contract)

One JSON, one table, **source × metrics** — so the fleet reads at a glance:

| source | notes | valid % | resolved | Brier raw | Brier recal | vs implied ci_low | book NAV | twin NAV | Δ vs twin | MaxDD vs twin |
|---|---|---|---|---|---|---|---|---|---|---|
| `analyst_constrained` | … | … | … | … | … | … | … | … | … | … |
| `analyst_agentic` | … | … | … | … | … | … | … | … | … | … |
| `event_interpreter` | … | … | … | … | … | … | (n/a) | (n/a) | (n/a) | (n/a) |
| `ensemble_avg` (virtual, Q3) | … | … | … | … | … | … | … | … | … | … |

Plus blocks: `ab_constrained_vs_agentic` (§1), `disagreement` (§2), and the existing
`g1_skill` per source. **Every source is scored by the SAME machinery** — no source
gets a bespoke metric, which is what keeps the comparison honest.

---

## §4 — What this does NOT do

- It does not authorize anything. **Scoring ≠ promotion**; the G0/G1 ladder is the
  real-money gate and is unchanged.
- It does not claim ~6 months of paper can establish skill (the program doc's own
  caveat, restated).
- It does not compare sources across different question sets, windows, or baselines —
  the matched-set and common-window rules are hard requirements, not preferences.

**T-323 gates pre-stated (before first agentic note, before disagreement data).**
