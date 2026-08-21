---
task_id: T-2026-08-15-341b
title: T-341b — the section-carve diagnosis: ~half the "15.1% parse failure" is a MISLABELLED structural absence
date: 2026-08-15
worker: Agent B
branch: feature/similarity-panel-clock-t341b
status: DIAGNOSIS DONE (bounded unit). Repair NOT applied — the cheapest fix is a RECLASSIFICATION requiring a parse re-run; specified, not half-done. N+=0.
---

# T-341b — diagnosing the Item-1A/Item-7 carve failures

Panel: 10,860 rows, `ok` = 0.8486 → **1,644 failures (15.1%)**.
Upstream sections: 11,464 filings, `parse_ok` = 0.8584 → **1,623 failures (14.2%)**.

## The failure classes (from `sections.parquet.skip_reason` — the parser's own field)
| class | n | share |
|---|---|---|
| `section_not_located:item_7` | **734** | 45.2% |
| `section_not_located:item_1a` | **520** | 32.0% |
| `section_not_located:item_1a,item_7` | 288 | 17.7% |
| **`fetch_error:URLError`** | **78** | 4.8% |
| `fetch_error:TimeoutError` | 3 | 0.2% |

## ⚠ FINDING 1 — ~419 "parse failures" are NOT failures. Item 1A did not exist yet.
Item-1A-mentioning failures by filing year:

| year | item_1a failures | of filings | rate |
|---|---|---|---|
| **2005** | **419** | 429 | **98%** |
| 2006 | 38 | 449 | 8% |
| 2007 | 26 | 461 | 6% |
| 2008+ | ~15-21/yr | ~470 | 3-5% |

**A 98% → 8% cliff at exactly the 2005/2006 boundary is the SEC rule, not a parser bug.**
Item 1A (Risk Factors) became **mandatory only for fiscal years ending on or after
2005-12-01** (Securities Offering Reform). 10-Ks filed in 2005 cover FY2004 and
**legitimately contain no Item 1A at all**.

Labelling a structurally-absent section `parse_failed` is exactly the mislabel the
dispatch's own contract forbids: the honest value is **`NOT_COVERED: item_1a not required
before the Dec-2005 rule`**, never a failure and never a silent null.

**This also explains the panel's 2006 wall.** 2006 panel rows (98.4% fail) compare against
**2005 priors** — 323 of them carry `parse_failed:prior`. Those priors are the very
filings that have no Item 1A. **The panel's worst year is a downstream shadow of the same
rule boundary**, not a second defect.

**Restated honestly: roughly 419 section-level and ~323 panel-level "failures" are a
correctly-absent section, i.e. a large share of the 15.1% headline is a labelling defect,
not a parsing defect.** The true parser-defect rate is materially lower than advertised.

## FINDING 2 — 81 failures never parsed at all (they are FETCH errors)
`fetch_error:URLError` (78) + `TimeoutError` (3) = **81 rows (5.0%)** that were never
downloaded. **Cheapest genuine repair in the set: re-fetch.** No parser change needed.
(Note the resonance with T-295/T-334: transient/UA-sensitive fetch failures persisting as
permanent-looking data defects because nothing retried them.)

## FINDING 3 — the real parser defect is `item_7`, and it is CONCENTRATED
`section_not_located:item_7` (734, 45.2%) is the genuine carve failure, and it is not
scattered:
- **15 tickers fail 100% of the time — every year, every filing:** `C, CLX, CVX, DE, ETN,
  HAL, IBM, ICE, MOS, NFLX, NI, PGR, USB, WFC, XOM` (295 panel rows, **17.9% of all panel
  failures**).
- **ETN is the clean exhibit:** 14/14 filings, `section_not_located:item_7` every year,
  while its **Item 1A carves fine**. So the document is fetched and parsed — only the
  Item-7 heading is unmatched. That is a heading-pattern gap (non-standard MD&A titling
  or incorporation-by-reference), not a broken document.
- In the modern era (2015+), these 15 tickers are **42.6%** of failures; the remaining 351
  are scattered across 68 tickers.

These are large, well-known filers, so the defect is **systematically biased toward
mega-caps** — which matters for any breadth measure built on the panel.

## Recommendation (repair NOT applied — specified so it is done once, properly)
1. **RECLASSIFY (cheapest, highest value):** emit `NOT_COVERED: item_1a not required
   pre-2006` for filings whose period predates the rule, at both section and panel level.
   This is a correctness fix to the *contract*, not a parser change — but it needs a parse
   re-run to restamp, so I have specified rather than half-applied it.
2. **RE-FETCH the 81 fetch_errors** — no parser work; likely recovers most.
3. **Item-7 heading survey on the 15 always-fail tickers** — a bounded next unit: dump the
   heading region for ETN and 2-3 others, find the unmatched pattern, extend the carve.
   Highest yield per effort of the remaining work (45.2% of failures, concentrated).

## Honest residual
Even after all three, **some filings are genuinely uncarvable** (incorporation by
reference, exhibit-only MD&A). The contract stands: those must report
**`NOT_COVERED` + reason**, never a silent null and never a fabricated similarity. No
repair was applied in this unit; nothing in the panel changed.
