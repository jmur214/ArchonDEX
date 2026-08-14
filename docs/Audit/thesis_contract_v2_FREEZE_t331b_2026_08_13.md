---
task_id: T-2026-08-13-331b
title: thesis_call/v2 — THE FINALIZED FREEZE (stamp-ready; applies from SCAN 5 / rev28)
date: 2026-08-13
author: Agent D
type: FROZEN CONTRACT (consolidates T-331 + T-335/T-335b) — awaiting the director's stamp. 0 N_trials.
status: FINAL — for stamp. **v1 remains live through scan 4; v2 applies from SCAN 5 (rev28).**
---

# thesis_call/v2 — the finalized contract

**Self-contained by design.** This supersedes the T-331 draft and folds in the T-335/T-335b resolver work, so
a builder implements from *this document alone* without chasing three others. Nothing here is new relative to
what was drafted and approved — it is the consolidation, plus the one thing the drafts could not yet state:
**the exact applicability boundary.**

## 0. APPLICABILITY — the boundary, stated precisely
| | contract | scored under |
|---|---|---|
| theses filed **through scan 4** (incl. scan 4's canonical output, ~Aug 19, rev27) | **v1** | the v1 bar, as a **separate labeled cohort** |
| theses filed **from scan 5 onward** (rev28) | **v2** | the v2 bar (§5) |

**Why a scan boundary and not a date:** a scan is atomic — a thesis is generated under exactly one contract,
so no scan is ever half-migrated. rev27 carries **only** the token-truncation fix (one change per rev while a
confirm is pending); v2 bakes into **rev28**. Scan 4 filing under v1 satisfies the original freeze gate
("after a scan files") literally, and its two theses (the fertilizer-geopolitical and AI-security calls that
the truncation had hidden) grandfather like any other v1 record.

---

## 1. Required field — VALUATION-EMBEDDING ("is it already in the price?")
**Evidence:** Ben-David et al. — thematic ETFs lose **~4%/yr for 5 years post-launch**, driven by
launch-at-peak-overvaluation. **Identifying a real theme is the easy half**; thematic investing dies on
consensus-recognition timing.
```
valuation_embedding: {
  verdict: "not_priced" | "partially_priced" | "fully_priced",   # required
  evidence: str,                 # multiples vs history, coverage density, move already made, ETF existence
  what_would_change_it: str,     # required — the observation that flips the verdict
}
```
`fully_priced` is **not** an auto-reject — it is a legitimate and valuable output ("the theme is real and you
are late"), but such a thesis must state why it is still being filed. **The desk's most valuable product may
be refusing themes, and the contract must let it say so.**

## 2. Required field — THEMATIC-ETF EXISTENCE (a machine-checkable NEGATIVE signal)
```
thematic_etf_exists: { exists: bool, tickers: [str], first_launch: str|null, months_since_launch: int|null }
```
**Pre-registered prior:** `exists == true` with `months_since_launch <= 60` cannot coexist with
`valuation_embedding.verdict == "not_priced"` unless `evidence` explicitly rebuts it. **A prior that shifts
the burden of proof — not a veto.**

## 3. Required — SUB-CLAIM DECOMPOSITION (the fix for a contract that was otherwise unmeasurable)
**The v1 defect, stated plainly:** at ~20 long-horizon theses/yr against a ≥20-resolved-per-class bar, a single
theme class needed **~a decade** to yield a skill estimate. **The binding constraint was POWER, not the scoring
rule.** v1 would have accrued a record that could never say anything.
```
sub_claims: [                       # >= 10 REQUIRED
  { id: str, statement: str,
    check_quarter: "YYYYQn",        # quarterly cadence — the whole point
    resolution_rule: dict,          # a resolver/v1 spec (see §4) — A's harness scores it unchanged
    market_analogue: dict|null,     # a prediction-market contract covering the same claim, if one exists
    prior: float,                   # strictly in (0,1) — required for calibration
    load_bearing: bool },           # see the anti-padding rule
  ... ]
```
**Anti-padding rule (binding):** a sub-claim counts toward the ≥10 **only if its resolution would change the
thesis's standing**. `load_bearing: false` claims may be filed for interest but **do not count**, and the first
v2 scan is to be reviewed for padding explicitly. A model that pads to hit a count produces a bigger n and a
worse estimate.

**Scoring — Murphy decomposition (required):** report **calibration** and **discrimination separately**. A desk
can be well-calibrated but undiscriminating (says 0.5 to everything and is "right"), or sharp but overconfident.
One number hides which. The **thesis-level** skew-aware log-wealth metric (v1, retained) answers the *payoff*
question; the **sub-claim** layer answers the *skill* question. **Different questions, kept separate on purpose.**

**⚠️ The caveat that rides with this, permanently:** sub-claim resolutions are **NOT independent** — ten
sub-claims of one thesis share its fate. **CIs MUST cluster on thesis** (block-bootstrap over theses, never
over sub-claims) or significance is overstated. Effective n is **between 20 and 200**, never 200. *Stated here
so nobody later quotes the inflated number.*

## 4. The RESOLVER TAXONOMY + the cheapest-substrate rule
**New closed metric set — `records_progress`:** `permit_filed`, `permit_withdrawn`, `interconnection_mw_queued`,
`queue_exit`, `capex_guide_delta`. Sources: public permit trackers, ISO/utility interconnection queues, EDGAR,
**and EIA open data** for grid/power.

**Resolver types added to `RESOLVER_TYPES`** (all share one skeleton: **target hashed at filing**, frozen
window + threshold, pinned `method_version`, **fail-closed `UNRESOLVED`** when the record is absent, and
rejection of any datum timestamped after the resolve window):

| type | class | substrate | cost | freshness |
|---|---|---|---|---|
| `records_progress` | permits / queue / capex | trackers + ISO queues + EDGAR | $0 | daily |
| `eia_series_change` | power / grid | EIA Open Data API v2 | $0 (key reg.) | hourly |
| `usaspending_award` | government contract | USASpending | $0 | days |
| `edgar_fact_change` | filings | EDGAR (ours) | $0 | minutes |
| `eo_area_change` | physical build-out | Sentinel-2 **direct** (never GEE) | $0 imagery | **LAST RESORT** |

Two per-type rules that are load-bearing, not stylistic:
- **`usaspending_award` keys on UEI, never company name** — names change and subsidiaries proliferate; a
  name-matched resolver silently resolves the wrong entity.
- **`edgar_fact_change` uses `first_reported`, never the restated value** — scoring against a restatement is
  hindsight (the T-265 PIT rule).
- **`eia_series_change` must pin its vintage** — EIA revises; an unpinned read lets a later revision silently
  change a settled outcome. Also honest: EIA is **balancing-authority granularity, not per-facility**.

**⭐ THE CHEAPEST-SUBSTRATE RULE (contract rule, enforced at validation):**
> **A sub-claim must use the cheapest substrate that can resolve it.** A thesis proposing an `eo_area_change`
> resolver where a `records_progress` / `eia_series_change` / `edgar_fact_change` route exists is **REJECTED at
> validation** — not because EO is bad, but because the cheaper route resolves **earlier** and with **fewer
> failure modes**.

The reusable finding behind it: **in the physical-build-out domain the paper trail structurally PRECEDES the
concrete** (land control → planning → permit → power offtake → interconnection queue → MEP → *only then* a
visible foundation), so **EO is the last-arriving signal in its own best domain**.

## 5. The MATCHED NULL GENERATOR + the v2 promotion bar
**A Brier score against zero is uninterpretable.** Before *any* skill claim, a **null generator** must exist: a
random/consensus-theme generator emitting theses in the same format, scored through the same pipeline. The
comparison is **desk vs null**, never desk vs an abstract 0.25. Cheapest honest form: sample theme classes at
their observed frequency, draw instruments from the same universe, set priors at base rates.
**Sub-claims with a market analogue are additionally scored against the market-implied probability** — a far
stronger baseline. *(Reading prediction-market odds was never prohibited; trading them is. Stated explicitly so
it is not mistaken for scope creep.)*

**THE v2 PROMOTION BAR — supersedes v1's.** A `theme_class` earns nothing until **ALL FOUR**:
1. **≥20 resolved theses** in the class **AND ≥100 resolved load-bearing sub-claims**;
2. sub-claim skill **beats the null generator** (and the market-implied baseline where analogues exist), with a
   **thesis-clustered** bootstrap CI **excluding zero**;
3. the thesis-level **log-wealth ratio vs the SPY twin** CI **excludes zero** (the v1 bar, retained);
4. **Murphy calibration and discrimination both reported, neither pathological.**

## 6. MIGRATION — version tagging IS the migration
- **Nothing already filed is touched.** Every v1 thesis keeps `schema_version: "thesis_call/v1"`.
- **No back-fill of `valuation_embedding` or `sub_claims` onto v1 records, ever** — a valuation verdict written
  *after* seeing the price action is hindsight, not evidence.
- v1 theses are scored under the **v1 bar** as a **separate labeled cohort** and **never enter a v2 skill
  estimate**. The scorer branches on `schema_version`; both cohorts appear in A's table, labeled.
- **There is no data migration, deliberately.**

## 7. Builder's delta (so this is implementable from one doc)
- `intelligence/analyst/eval_harness.py` — extend `RESOLVER_TYPES` with the five §4 types + their
  required-field validation in `is_resolvable_spec`.
- `intelligence/thesis_desk/thesis_schema.py` — add `valuation_embedding`, `thematic_etf_exists`, `sub_claims`
  (min 10 load-bearing) to a **v2** model; keep the v1 model intact and branch on `schema_version`.
- `intelligence/thesis_desk/thesis_scoring.py` — add the Murphy decomposition + the **thesis-clustered**
  bootstrap; extend `promotion_check` to the four §5 conditions; `MIN_RESOLVED_PER_CLASS = 20` stays and gains
  a `MIN_RESOLVED_SUBCLAIMS = 100`.
- `intelligence/thesis_desk/thesis_scan.py` — the generator emits v2 from **scan 5**; the bias firewall
  (T-324b) is unchanged and still applies.
- **Null generator:** a new sibling module, and it **must exist before any skill claim is made** — not after a
  promising number appears.

## 8. What v2 costs, stated plainly
- The ≥10-sub-claim requirement is a **real burden** and **invites padding** — hence the `load_bearing` rule and
  the explicit padding review of the first v2 scan.
- **The null generator is real work** that buys no theses of its own.
- **The desk gets slower and more expensive per thesis.** That is the correct trade: **v1 was cheap and
  unmeasurable.**

---
**FINAL — for the director's stamp.** On stamp this bakes into **rev28** and applies from **scan 5**. Any change
after the stamp line = a new pre-registration.
