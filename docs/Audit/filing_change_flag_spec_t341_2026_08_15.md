---
task_id: T-2026-08-15-341
title: The FILING-CHANGE RISK FLAG — a negative-attention marker for the thesis desk (spec)
date: 2026-08-15
author: Agent D
type: SPEC — forward-accrual only, 0 N_trials, no backtest. Build sequencing: AFTER rev28 (see §7).
status: FOR REVIEW — nothing built. Depends on a COVERAGE REPAIR that is a hard precondition (§6).
---

# The filing-change risk flag

**What it is:** a large year-over-year change in a filer's risk-factor / MD&A language, surfaced to the
thesis desk as **context** when a thesis touches that name. Same class as `event_state` (T-291) and
`event_window`: it shifts *attention*, never a verdict and never a weight.

**What it is NOT, and why that framing is forced.** Lazy Prices (Cohen-Malloy-Nguyen) is **dead as alpha for
us** — the effect sign-flips under survivorship cleaning, and the informative leg is the **short** leg. We are
long-only in a Roth. **The leg that carries the information is the one we cannot trade.** That is not a
limitation we can engineer around; it is why the only defensible use of this metric here is attention, and it
is why this spec contains no backtest, consumes **0 N_trials**, and can never be promoted to a signal.

---

## 1. The change metric — REPOINT T-237, do not rebuild

The machinery exists and has already run. `scripts/lazy_prices/similarity_t237.py` carves **Item 1A (Risk
Factors)** and **Item 7 (MD&A)** out of raw 10-K HTML and scores each filing against **the same filer's
immediately-prior same-form filing**, ordered by `acceptance_dt`. `data/edgar/similarity_panel.parquet` holds
**10,860 rows / 9,216 scored / 596 tickers / 2005-12-20 → 2026-06-22**, with columns
`sim_cosine_tfidf`, `sim_jaccard`, `acceptance_dt`, `decision_date`, `prior_accession`, `ok`, `skip_reason`.

**The metric:** `filing_change = 1 − sim_cosine_tfidf` (cosine of per-pair-fit TF-IDF vectors, LM stopwords).
`sim_jaccard` rides along as a **corroborator only** — a flag that fires on cosine but not Jaccard is reported
as `elevated`, never `high`. Two metrics disagreeing is information, and collapsing them to one hides it.

**The flag rule is a TRAILING percentile, never a full-sample one.** The observed distribution is tight and
left-skewed (mean 0.915, median 0.936, sd 0.072, min 0.168), so a fixed threshold is meaningless and a
full-panel percentile is **look-ahead** — it ranks a 2026 filing against 2027's filings. Required form:

```
pct = rank of filing_change within all `ok` 10-K filings with acceptance_dt STRICTLY BEFORE this one
      (expanding window, minimum 250 prior filings or the flag is NOT_COVERED — see §3)

pct >= 0.95  and both metrics agree  -> "high"
pct >= 0.90  (or metrics disagree)   -> "elevated"
otherwise                            -> "none"
```

Three states, not a binary: this is an attention marker, and a hard threshold on a continuous quantity invites
exactly the false precision the metric cannot support.

## 2. The PIT rule

- **Scored on `acceptance_dt`; visible on `decision_date`** = the next business day, which the panel already
  computes. Never `period_end` — the period is over long before the document is public.
- **`first_reported` only.** An amendment (`10-K/A`) **never overwrites** the original filing's score. The
  original's flag stands as filed. Scoring an amended document against the original's date would let the desk
  read text that did not exist on that date — the same PIT rule as `edgar_fact_change` in the v2 contract
  (`docs/Audit/thesis_contract_v2_FREEZE_t331b_2026_08_13.md` §4).
- **Same-form pairs only.** The panel is **10-K only** today, so a pair is always annual-vs-annual. No
  cross-form comparison, ever — a 10-Q's language differs from a 10-K's for structural reasons that have
  nothing to do with risk.
- **Honest consequence:** a name's flag refreshes **once a year**. This is an annual marker, not a live one,
  and it must be labeled as such wherever it surfaces (§4 carries `as_of` and `staleness_days` for this
  reason). Anyone who reads it as current information is misreading it.

## 3. ⭐ THE LOAD-BEARING RULE — three states, because absence of a flag is not absence of a change

The panel is **not** uniformly covered, and the gaps are silent:

| | count | mechanism |
|---|---|---|
| PIT universe (S&P historical membership) | 690 names | — |
| appear in the panel | 596 | 94 never ingested |
| **fully blind** — *every* filing unparseable | **15** | section-carve failure |
| partially blind — some filings unparseable | 426 | section-carve failure |
| overall parse-failure rate | **15.1%** (1,644 / 10,860) | |

The 15 fully-blind names include **C, CVX, DE, IBM, NFLX, ETN, HAL, ICE, MOS, NI, PGR, CLX**. If the flag
returns null for IBM, the desk reads "IBM's language didn't change." **The truth is "we cannot parse IBM."**
That is the silent-wrongness pattern this project has now paid for repeatedly (T-338's stalled clocks,
T-337's census conflating throttling with delisting). It is not acceptable in a new feed.

> **BINDING:** the lookup returns **`high` | `elevated` | `none` | `NOT_COVERED`**, and `NOT_COVERED` carries
> a machine-readable `reason` (`not_in_universe` | `parse_failed` | `no_prior_filing` |
> `insufficient_trailing_history` | `panel_stale`). **A null is never returned.** A name the desk asks about
> and cannot get an answer for must say so in the bundle, in words the model will read.

This is the single most important rule in the spec. Everything else is tuning.

## 4. Where it surfaces in the v2 bundle

One new key in `build_scan_bundle` (`intelligence/thesis_desk/thesis_scan.py`), sitting beside `event_calls` —
the deliberate precedent, since `event_state` is already carried as context-only per T-291/T-233:

```
filing_change_flags: [
  { ticker: str,
    flag: "high"|"elevated"|"none"|"NOT_COVERED",
    reason: str|null,              # required when NOT_COVERED
    filing_change: float|null,     # 1 - sim_cosine_tfidf
    trailing_pct: float|null,
    accession: str, as_of: str,    # the filing's decision_date
    staleness_days: int,           # days since as_of — an annual marker, stated as one
    method_version: "filing_change/v1" },
  ... ]
```

**⭐ LOOKUP-ONLY, never a screen.** Flags are attached **only for tickers the thesis already names**. The desk
is never handed a ranked list of "biggest language changes this year." A ranked list is a screen, a screen is a
generator input, and a generator input is a signal wearing a context costume — and it would be the *dead* one.
The direction of the lookup is what keeps this honest: **thesis → name → flag**, never flag → name → thesis.

The bundle stays subject to `assert_bundle_is_blind` unchanged. Flags are machine-derived from EDGAR and carry
no user seed, so the T-324b firewall passes — but they are asserted, not exempted.

## 5. Explicit NON-uses (each one closes a specific door)

1. **Never a tilt, weight, or size input.** Engine C never sees this field. No allocator reads it.
2. **Never an auto-reject and never a veto** of a thesis. It shifts attention, not verdicts.
3. **Never a screen or a ranked generator input** — see the lookup-direction rule in §4.
4. **Never a sub-claim resolver substrate.** A resolver resolves a *record of the world*; this is a measure of
   *text about the world*. It is not admissible under the v2 resolver taxonomy and must not be added to
   `RESOLVER_TYPES`.
5. **Never scored as alpha, and never entering a promotion bar.** It contributes to no skill estimate and
   consumes **0 N_trials** — permanently, not just at v1.
6. **Never back-filled** onto an already-filed thesis. A flag attached after the fact is hindsight.
7. **Never a live/current-information claim.** It is annual (§2); `staleness_days` rides with every flag.

## 6. Preconditions — this is not free, and the "zero-cost" framing is only half true

The *data* is zero-cost (our archive, no vendor). The *engineering* is not, and two items are hard blockers:

**(a) The panel is 8 weeks stale and has no clock.** It ends 2026-06-22 and **nothing in the T-338 clock
registry covers it** (`paper_trader/clock_census.py`). A forward accrual with no clock is precisely the
disease T-338 cured. **Required before the flag surfaces anywhere:** an ingest step on a cadence plus a
`filing_change_panel_advanced` clock in the registry, fail-closed, artifact-derived like every other clock. A
stale panel must surface as `NOT_COVERED / panel_stale`, never as `none`.

**(b) The coverage repair.** 15.1% parse failure is too high for a feed whose whole contract is that its
silence is trustworthy. Two distinct fixes, distinct owners:
- **parser** — `_section_headings` / `_carve` fail on filers whose Item 1A/7 headings don't match the token
  regexes (ETN: 13 filings, all `parse_failed:current,prior`).
- **universe** — the PIT universe is S&P-500 historical membership, so mid-cap second-order suppliers are
  absent by construction (VRT: 0 rows). The desk's value is *second-order* names, which is exactly where this
  universe is thinnest.

**The check that motivated this section:** of the seven names from T-325's blind scan, **NEE, FTI, CF, CRWD are
covered; VRT and ETN are blind** (universe gap and parser gap respectively) and XLU is an ETF, correctly blind
since ETFs file no 10-K. **VRT and ETN were the headline of that scan's convergence.** A feed that is blind to
the desk's best-known output is worth building only after the repair, not before.

**Builder note:** `similarity_t237.py`'s own path constants are stale — `_LAZY_DIR` points at
`data/edgar/lazy_prices/`, which does not exist; the artifacts live at `data/edgar/`. Repoint the constants
(or add an override); do not re-derive the panel.

## 7. Sequencing — my call: AFTER rev28

The flag adds **no required field** to `thesis_call/v2` — it is bundle context, not contract. So it does not
need to ship with the contract, and rev28 should stay minimal under the same one-change-per-rev discipline
invoked for rev27. Proposed order:

1. **Now, cheap, independent of everything:** the refresh clock (§6a). The panel is already stale; a clock on
   a stale panel is how we learn it stopped. This is worth doing whether or not the flag is ever built.
2. **Then:** the coverage repair (§6b) — parser first (mechanical, measurable: parse-failure rate), universe
   second (a scoping decision about how far past S&P membership the desk's universe should reach).
3. **Then, and only then:** the lookup + the bundle key + the NON-use tests.

**If the repair is not funded, the honest outcome is that this does not get built.** A marker that is silently
blind on 15% of filings and on the desk's own second-order names would be worse than no marker, because the
desk would read its silence as information. I would rather ship nothing than ship that.

## 8. Tests the build must carry

- `NOT_COVERED` is returned (never null) for each of the five reasons, one test per reason.
- A fully-blind ticker (ETN) returns `NOT_COVERED / parse_failed`, **not** `none` — the named regression for §3.
- A stale panel returns `NOT_COVERED / panel_stale`.
- The trailing percentile uses only strictly-prior filings — a look-ahead regression that fails if the full
  panel is ranked.
- A `10-K/A` does not overwrite the original's score.
- The bundle passes `assert_bundle_is_blind` with flags attached.
- **A NON-use test:** no allocator/scoring path reads `filing_change_flags` (grep-assertion in the same style
  as the firewall tests) — the door in §5.1 stays closed mechanically, not by convention.

---
**0 N_trials. No backtest. Nothing built.** Forward-accrual context only, permanently outside every promotion
bar and every scoring path.
