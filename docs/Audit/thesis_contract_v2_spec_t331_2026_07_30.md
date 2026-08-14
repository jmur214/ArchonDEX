---
task_id: T-2026-07-30-331
title: thesis_call/v2 — the contract upgrade (valuation-embedding, ETF-existence signal, sub-claim decomposition, null baseline)
date: 2026-07-30
author: Agent D
type: SPEC DRAFT — awaiting director freeze. **DO NOT APPLY before the first canonical scan lands.**
status: SUPERSEDED by docs/Audit/thesis_contract_v2_FREEZE_t331b_2026_08_13.md (the finalized, stamp-ready
        consolidation). Kept as the drafting record; do NOT implement from this file.
---

# thesis_call/v2 (DRAFT — ⚠️ SUPERSEDED) — four evidence-backed upgrades

> **`[NN-SUPERSEDED]`** — the finalized contract is
> **`docs/Audit/thesis_contract_v2_FREEZE_t331b_2026_08_13.md`**, which consolidates this draft with the
> T-335/T-335b resolver taxonomy and states the applicability boundary (**v2 applies from SCAN 5 / rev28**).
> This file is the drafting record only — implement from the FREEZE doc.

Source: the external review (`docs/Sources/External_Prompt_Runs/2026-07-28_research-agent-v3.md`, Q2). All
four upgrades below are evidence-backed, and one of them (#3) fixes a defect that would otherwise make the
desk **unmeasurable this decade**.

## ⏸️ SEQUENCING — binding, and the reason matters
**This spec does NOT go live before Wednesday's first canonical scan.** The blind-scan experiment (T-324b.3)
depends on the machine's first scan being generated under the contract it was designed against. Changing the
contract first would (a) contaminate the experiment's baseline and (b) make the first scan's output
non-comparable to everything after it. **v1 stays the live contract until the first canonical scan lands and
the director freezes this.** The migration story (§5) is written so that nothing already filed is disturbed.

---

## 1. VALUATION-EMBEDDING — the mandatory "is it already in the price?" claim
**Evidence:** Ben-David et al. — thematic ETFs lose **~4%/yr alpha for 5 years post-launch**, driven by
*launch-at-peak-overvaluation*. The decomposition matters: **identifying a real theme is the easy half**;
thematic investing dies on **consensus-recognition timing**. A desk that only identifies themes is
systematically buying the top.

**New required field** on every thesis:
```
valuation_embedding: {
  verdict:   "not_priced" | "partially_priced" | "fully_priced",   # required
  evidence:  str,        # what SPECIFICALLY supports the verdict — multiples vs history, sell-side
                         # coverage density, retail attention, price move already made, ETF existence (§2)
  what_would_change_it: str,   # required — the observation that would flip the verdict
}
```
A `fully_priced` verdict is **not** an automatic reject — it is a legitimate, valuable output ("the theme is
real and you are late"). But a thesis whose `verdict` is `fully_priced` **must** state why it is still being
filed. The desk's most valuable product may turn out to be *refusing* themes, and the contract must let it
say so.

## 2. "A thematic ETF for this theme now exists" — a machine-checkable NEGATIVE signal
**Evidence:** the same Ben-David result — ETF launch clusters at peak overvaluation, and the subsequent 5yr
alpha is ~−4%/yr. **Launch is a sentiment marker, not a validation.**
```
thematic_etf_exists: {
  exists:        bool,          # machine-checkable
  tickers:       [str],         # the named thematic ETFs, if any
  first_launch:  str|null,      # ISO date of the EARLIEST such launch (the timing signal)
  months_since_launch: int|null,
}
```
**Prior, pre-registered:** `exists == true` with `months_since_launch <= 60` is a **negative** prior on the
thesis and MUST be reflected in `valuation_embedding.verdict` (it cannot be `not_priced` while a <5yr-old
thematic ETF for the same theme exists, unless `evidence` explicitly rebuts it). This is a *prior*, not a
veto — it shifts the burden, it does not forbid the thesis.

## 3. ⚠️ THE BIG ONE — sub-claim decomposition, because the desk is otherwise UNMEASURABLE
**The defect in v1, stated plainly:** at ~20 long-horizon theses/yr, and a promotion bar of ≥20 resolved per
theme_class, a single theme class needs **~a decade** to produce a skill estimate. **The binding constraint
is POWER, not the scoring rule.** v1 would have accrued a record that could never say anything.

**The fix (required):** every thesis decomposes into **≥10 quarterly-checkable sub-claims**, each with a
pre-registered resolution rule. n = ~20 theses/yr becomes **n = hundreds of resolutions/yr**.
```
sub_claims: [                      # >= 10 required
  { id: str,
    statement: str,
    check_quarter: "YYYYQn",       # quarterly cadence — the whole point
    resolution_rule: dict,         # resolver/v1 where possible (A's harness scores it unchanged)
    market_analogue: dict|null,    # §4: a prediction-market contract covering the same claim, if one exists
    prior: float (0,1),            # the model's probability — required for calibration scoring
  }, ...
]
```
**Scoring — Murphy decomposition (required):** score **calibration** and **discrimination** SEPARATELY.
A desk can be well-calibrated but undiscriminating (it says 0.5 to everything and is "right"), or sharply
discriminating but overconfident. Reporting one number hides which. The existing skew-aware log-wealth metric
(v1) is retained for the **thesis-level** payoff question; the sub-claim layer answers the **skill** question.
**These are different questions and the v2 contract keeps them separate on purpose.**

**Honest caveat that must ride with this:** sub-claim resolutions are **not independent** — ten sub-claims of
one thesis share its fate. So the effective n is between 20 (theses) and 200 (sub-claims), and the CI must be
computed by **clustering on thesis** (block-bootstrap over theses, not over sub-claims) or it will overstate
significance. **Stated now so nobody later quotes an inflated n.**

## 4. The matched NULL-GENERATOR baseline + prediction-market scoring
**Evidence:** a Brier score against zero is uninterpretable — "0.21" means nothing without a matched baseline.

**(a) Null generator (required before any skill claim):** a **random/consensus-theme generator** producing
theses in the same format, scored identically through the same pipeline. The comparison is *desk vs null*,
not *desk vs an abstract 0.25*. Cheapest honest form: sample theme classes at their observed frequency and
draw instruments from the same universe, with priors set at base rates.
**(b) Prediction-market scoring where an analogue exists:** sub-claims with a market analogue are scored
against the **market-implied probability**, which is a far stronger baseline than a base rate. **Reading
prediction-market odds was never prohibited** — trading them is what the standing constraint covers. This
distinction is explicit so nobody mistakes it for scope creep.

**Promotion bar (v2) — supersedes v1's:** a theme_class earns nothing until **ALL** of:
1. ≥20 resolved theses in the class **AND** ≥100 resolved sub-claims (thesis-clustered);
2. sub-claim skill **beats the null generator** (and the market-implied baseline where analogues exist), with
   a thesis-clustered bootstrap CI excluding zero;
3. the thesis-level **log-wealth ratio vs the SPY twin** CI excludes zero (the v1 bar, retained);
4. Murphy calibration/discrimination both reported, neither pathological.

## 5. MIGRATION — v1 theses are grandfathered, NOT retro-edited
**Nothing already filed is touched.** Retro-editing a filed thesis would destroy the forward record's
integrity — the whole point is that what was written is what is scored.
- Every filed thesis keeps `schema_version: "thesis_call/v1"`. **No back-fill of `valuation_embedding` or
  `sub_claims` onto v1 records, ever** — a valuation verdict written *after* seeing the price action is not
  evidence, it is hindsight.
- v1 theses are scored under the **v1 bar** (log-wealth vs twin) and reported as a **separate cohort**. They
  never enter a v2 sub-claim skill estimate.
- The scorer branches on `schema_version`; both cohorts appear in A's table, labeled.
- **Version tagging is the migration** — there is no data migration, and that is deliberate.
- v2 applies to theses filed **on or after** the freeze date. The first canonical scan's output is v1 by
  construction (it predates the freeze) and is grandfathered like any other v1 record.

## 6. What this costs, honestly
- **A ≥10-sub-claim requirement is a real burden on the generator.** Some genuine theses do not decompose into
  ten quarterly-checkable claims; the honest failure mode is a model padding with trivia to hit the count. The
  spec must therefore require sub-claims be **materially load-bearing** (if a sub-claim's resolution would not
  change the thesis's standing, it does not count) — and the review of the first v2 scan should look for
  padding explicitly.
- **The null generator is real work** and must be built before any skill claim is made, not after a promising
  number appears.
- **The desk gets slower and more expensive per thesis.** That is the correct trade: v1 was cheap and
  unmeasurable.

---
**DRAFT — NOT LIVE.** v1 remains the contract. **Do not apply before the first canonical scan lands**, then
the director freezes. Any change after the freeze line = a new pre-registration.
