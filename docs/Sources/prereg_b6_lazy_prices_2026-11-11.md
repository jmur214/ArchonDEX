---
task_id: T-383 (B-6)
title: Pre-registration — Lazy Prices on a repaired 10-K + 10-Q text panel, S&P PIT and T-265 small caps
date: 2026-11-11
worker: ml-architect subagent (in-session, director-dispatched with the user's go-ahead; SEC User-Agent and the Loughran-McDonald download approved by the user 2026-11-11)
branch: research/lazy-prices-repair-b6
status: DRAFT, NOT FROZEN — the S&P text panel is COMPLETE and re-censused (2026-11-12: 46,040 filings, 100% fetched; §4); the T-265 small-cap stream is HELD at 45 of 4,099 CIKs (R8). The director rules R1–R9 at freeze, with the full-panel census; preliminary reads (2026-11-11) accept R1 option (d), R2, R3 and R6 in principle. Awaiting the director's rulings (§13). Phase 1 is TEXT ONLY. NO forward return, price, portfolio or benchmark return has been computed or read. The census in §3–§4 counts filings, sections and price FILES (existence only).
N_trials: +2 at the run (S&P arm; T-265 arm) — §9
---

# B-6 — do firms that stop changing their filings' language outperform those that change it?

## 1. The question (H1s and refutation verbatim from the brief)

Brief: `docs/Sources/alpha_frontier_program_2026_09_30.md` §3.2 "B-6" (+ the common SETUP / HARD
CONSTRAINTS block). T-237 ran long-only top-tercile non-changers on S&P PIT, annual, 2006–2025, and left
no verdict doc. Cohen-Malloy-Nguyen (2020, J. Finance, "Lazy Prices") put the alpha in the SHORT leg and
in low-attention names; the project never tested either.

**H1 (S&P) (verbatim):** long-leg 25%-satellite Δ log wealth ci_low > 0.
**H1 (T-265) (verbatim):** same.
**Refutation (verbatim):** both ≤ 0 AND short-leg t_HAC < 2 ⇒ Lazy Prices is H0 on free data for this
operator — record as the first verdict doc T-237 never got.
**N_trials (verbatim):** N_trials += 2. **Honest prior (verbatim):** 12% / 20% — read here, in the order
of the two H1s, as 12% for the S&P arm and 20% for the T-265 arm (§9).
**Second signal (verbatim, deliverable 4):** Loughran-McDonald tone change as a second pre-declared
signal in the same family (not a third trial).

**What Phase 1 changed (§3):** the T-237 panel is not a measurement of anything — 40% of its "ok"
Item 1A sections are financial statements. B-6 rebuilt the panel from scratch: a new parser, a new
date-aware S&P identity map, 10-Qs, and a small-cap arm that stores no text.

## 2. THE HARD PRE-COMMITMENTS (the anti-overfit controls)

1. **No tuning after any output.** Every threshold, window, leg, signal sign, pairing rule and cost in
   §5–§8 is fixed here. A number that looks wrong is REPORTED, never re-specified.
2. **One gate per arm.** The gate statistic is the long leg of the PRIMARY signal (similarity), the
   25%-satellite Δ log wealth `ci_low`, at the Bonferroni level across the family's two signals (§7.4).
   Everything else is a pre-named diagnostic and cannot meet H1.
3. **No sign flipping.** Similarity: long the HIGH-similarity tercile (non-changers), +. Tone change:
   long the HIGH Δtone tercile (tone improved), +. A clearing in the opposite direction is reported as
   not clearing.
4. **No window shopping.** Windows come from parse coverage and price-source cleanliness alone (§6).
   Per-year rows are descriptive.
5. **The parser is frozen at `b6_parse/1`.** No parser change after any return exists. A parser defect
   found after the run is reported, and the run is re-done in full under a new prereg amendment — never
   patched for a subset.
6. **No short position is ever proposed for deployment.** The short leg (changers) is a diagnostic
   (a Roth cannot short) and enters only the refutation clause.
7. **Nothing is deployed and nothing is promoted.** A survivor goes to Engine F's gates and (T-265) to
   the survivorship re-verification B-2 §2.7 defines. B-6 never touches `BacktestController`,
   `engines/`, the governor or the run registry, and runs in a standalone harness.

## 3. Phase 1 findings — what the T-237 panel actually was (measured 2026-11-11)

### 3.1 ★ The T-237 panel measured nothing: 40% of its "ok" Item 1A sections are not risk factors
T-341b diagnosed T-237's FAILURES (`skip_reason`) and never looked inside its SUCCESSES. Read-only, on
the shared `data/edgar/sections.parquet` (11,464 10-Ks, 604 tickers, 9,841 `parse_ok`):

| test on the 9,841 `parse_ok` rows | Item 1A | Item 7 |
|---|---|---|
| carries the signature-page boilerplate ("Pursuant to the requirements of Section 13 or 15(d)") | 3,610 (36.7%) | 124 (1.3%) |
| carries "Report of Independent Registered Public Accounting Firm" | 3,871 (39.3%) | 180 (1.8%) |
| **either** | **3,942 (40.1%)** | 188 (1.9%) |
| median length, marker-free vs marker-present | **54,170 vs 272,673 chars** | — |

**Mechanism (seen in ATI 2023, AAL 2025):** a cross-reference to "Item 1A. Risk Factors" inside MD&A's
forward-looking-statements paragraph passed T-237's title-lookahead classifier; no 1B/2 heading
followed it, so its carve ran to the end of the document, and "longest span wins" SELECTED that
runaway over the real section. FY2023+ filings made it worse: T-237's title map has no Item 1C
(Cybersecurity), so 1A could not terminate there (reversion-checked: T-237's `extract_sections` on the
B-6 fixture returns an 8,201-char "Item 1A" containing MD&A text and the auditor's report; B-6 returns
2,814 chars ending at 1C). The contaminated share rises from 38% (2006) to 67% (2026).

| year | T-237 10-Ks | `parse_ok` | ok AND marker-free | share |
|---|---|---|---|---|
| 2005 | 429 | 6 | 5 | 1.2% |
| 2006–2019 | 449–556 / yr | 345–502 | 246–301 | 54–58% |
| 2020–2026 | 522–598 / yr | 489–561 | 228–285 | 44–50% |
| **total** | **11,464** | **9,841** | **5,786** | **50.5%** |

"Marker-free" is an UPPER bound on usable rows (a wrong-start carve that stops before Item 8 passes
it), and a YoY pair needs both ends. **T-237's "leaning H0" is not evidence in either direction.** The
stored text cannot be repaired offline (the real Item 1A precedes the stored chunk), so B-6 refetched
and re-parsed every filing with one parser version.

### 3.2 ★ T-237's universe: 604 of 970 members, 13 of them the wrong company
`data/universe/sp500_membership_pit.parquet` lists **970 tickers** with membership since 2005; T-237 held
sections for **604** (the LIVE `company_tickers.json` resolves only today's filers). And **13 resolved to
the wrong company** — a recycled ticker with zero ingested filings inside its membership: `S` →
SentinelOne (not Sprint), `STI`, `NE`, `ADT`, `MMI`, `BEAM`, `DYN`, `KG`, `LIFE`, `SGP`, `TE`, `APC`,
`ADCT`.

### 3.3 The membership file's ticker convention, measured
Each company is listed under its LAST ticker for its whole history: `LB` = L Brands since 1996 (it
traded as LTD until 2013, while LaBarge Inc. used "LB"); `WM` = Waste Management since 1998 (WaMu used
"WM" and has its own `WAMUQ` interval); `PTC` 1997–2007 = Parametric (then PMTC); no ACE, NU, LTD or
WPO interval exists. A symbol's historical user is therefore not always the member.

### 3.4 What B-6 built (code `scripts/lazy_prices/b6_*.py`, tests `tests/test_b6_lazy_prices_*.py`)
- **Identity (`b6_cik_map`, `b6_build_panel universe`):** the SEC Form 3/4/5 datasets already cached
  (`data/edgar/insider_zips/`, 2006Q1–2026Q1, 4.40M filings) record who used which symbol when. Per
  (membership interval, month) the member CIK is chosen among the symbol's users at that time, the last
  chain user (the file's convention) and the live-map CIK — each only while it was a periodic FILER
  (its own submissions JSON) — by insider activity over the interval (≥ 1.5× wins; a tie goes to the
  symbol user, flagged); a CIK cannot be two different members in one month (a bankruptcy-suffix match
  loses; share classes keep one ticker). Verified on the hard cases: CB = Chubb Corp to 2016-05 then
  Chubb Ltd; MRK = old Merck to 2009-08 (Schering-Plough is SGP); LB = L Brands; WM = Waste
  Management; S = Sprint; SUNEQ ≠ Sunoco (dropped); GOOG = Google Inc then Alphabet.
  **131,673 member-months 2005-01 → 2026-11; 130,322 (99.0%) carry a CIK.** NOT_COVERED (counted, never
  guessed): FOXA before 2019 (News Corp / 21CF), DXC before 2017 (CSC), KATE (Liz Claiborne), ATGE
  (DeVry), IAC 2006–08, SUNEQ (MEMC/SunEdison), FRC and SBNY (FDIC filers, no EDGAR 10-Ks).
- **Parser (`b6_parse`, frozen as `b6_parse/1` before the bulk fetch):** block structure kept;
  line-start headings (plus bare "7." numbering in old plain-text filings); a section must be
  terminated by its STRUCTURAL successor (10-K 1A → 1B/1C/2/3; 7 → 7A/8; 10-Q MD&A → I-3/I-4/II-1/
  II-1A; 10-Q 1A → II-2…II-6), otherwise the candidate is rejected — the T-237 runaway cannot occur by
  construction; a title-located MD&A for the cross-reference-index layout (ETN, XOM, GHC, USB, C —
  T-341b's "15 always-fail mega-caps") recorded as its own source; ICFR reports trimmed off the end of
  Item 7 (Boston Scientific); every absence classified (`NOT_COVERED:pre_rule`,
  `incorporated_by_reference[_external]`, `item_absent`, `not_required`) and every failure named
  (`NOT_LOCATED`, `TOO_SHORT`, `CONTAMINATED`, `FETCH_FAILED`). 26 locks, each reproducing a measured
  failure class.
- **Smoke (35 real filings, 33 CIKs, 28 SIC industries, stratified over 2004–2026 × form, plus forced
  ETN / IBM / XOM / WFC / C 10-Ks; three iterations, every start and end read by eye):** 0 contaminated
  accepted sections; 10-K risk 15/20 OK (3 pre-rule, WFC's Annual-Report pointer, Citigroup NOT_LOCATED
  — its integrated report has no Risk-Factors item); 10-K MD&A 18/20 OK (WFC and IBM: MD&A only in
  Exhibit 13 → `incorporated_by_reference_external`); 10-Q risk 10/15 OK (3 pre-rule, 2 with no Part II
  Item 1A); 10-Q MD&A 15/15 OK.

## 4. The repaired panel — coverage census (before / after; S&P panel COMPLETE 2026-11-12)

### 4.0 Fetch record
| stream | state | filings | fetch success | notes |
|---|---|---|---|---|
| **S&P 10-K + 10-Q** | **COMPLETE** (954 CIKs) | **46,040** (11,409 10-K, 34,631 10-Q) | **100%** after one retry pass | halted once on the 15 GB floor (2026-11-12 04:36 UTC, at 5,584 filings), resumed on the director's word with a 10 GB floor (never tripped; 13.7 GB free at the end); 151 transient retries; 37 Cisco filings lost to a local DNS outage ("nodename nor servname provided") were re-fetched with `fetch --retry-failed` (0 failures) |
| T-265 signals-only | **HELD** at 45 of 4,099 CIKs (2,012 filings) | — | 100% | halted on the 15 GB floor; restarts on the director's word |

Footprint: 342 MB in `data/b6_local/` (zstd text shards, ~7 MB per 1,000 filings). ~47,000 SEC requests,
6.3 GB over the wire (gzip). Parser `b6_parse/1` throughout.

### 4.1 BEFORE — T-237's 10-K panel (`data/edgar/sections.parquet`, read-only; `b6_census`)
| year | 10-Ks | T-237 `parse_ok` | ok AND marker-free (§3.1) |
|---|---|---|---|
| 2005 | 429 | 6 | 5 |
| 2006 | 449 | 345 | 246 |
| 2007 | 461 | 376 | 256 |
| 2008 | 466 | 385 | 252 |
| 2009 | 473 | 402 | 261 |
| 2010 | 478 | 410 | 268 |
| 2011 | 487 | 425 | 280 |
| 2012 | 494 | 436 | 286 |
| 2013 | 505 | 447 | 291 |
| 2014 | 513 | 458 | 296 |
| 2015 | 528 | 470 | 299 |
| 2016 | 530 | 473 | 296 |
| 2017 | 535 | 480 | 297 |
| 2018 | 548 | 495 | 299 |
| 2019 | 556 | 502 | 301 |
| 2020 | 564 | 517 | 281 |
| 2021 | 572 | 527 | 255 |
| 2022 | 581 | 542 | 260 |
| 2023 | 584 | 542 | 270 |
| 2024 | 591 | 553 | 285 |
| 2025 | 598 | 561 | 274 |
| 2026 | 522 | 489 | 228 |
| **total** | **11,464** | **9,841 (85.8%)** | **5,786 (50.5%)** |
T-237 had no 10-Qs, and its universe held 604 of the 970 member tickers (§3.2).

### 4.2 AFTER — B-6, the complete S&P panel (per acceptance year)
"both" = Risk Factors AND MD&A OK; "combo / risk / MD&A pair" = a YoY pair (§5) defined for that text.

| form | year | filings | risk OK | MD&A OK | both | combo pair | risk pair | MD&A pair |
|---|---|---|---|---|---|---|---|---|
| 10-K | 2005 | 496 | 12 (pre-rule) | 392 | 12 | 0 | 0 | 29 |
| 10-K | 2006 | 512 | 461 | 424 | 390 | 13 | 13 | 372 |
| 10-K | 2007 | 527 | 490 | 452 | 429 | 365 | 440 | 399 |
| 10-K | 2008 | 540 | 510 | 463 | 446 | 392 | 455 | 413 |
| 10-K | 2010 | 521 | 500 | 465 | 454 | 427 | 484 | 438 |
| 10-K | 2012 | 514 | 496 | 467 | 459 | 435 | 480 | 443 |
| 10-K | 2014 | 512 | 494 | 473 | 464 | 436 | 471 | 443 |
| 10-K | 2016 | 524 | 505 | 495 | 483 | 436 | 464 | 448 |
| 10-K | 2018 | 509 | 491 | 483 | 470 | 432 | 456 | 442 |
| 10-K | 2020 | 513 | 492 | 491 | 478 | 434 | 456 | 446 |
| 10-K | 2022 | 519 | 498 | 504 | 487 | 461 | 476 | 479 |
| 10-K | 2024 | 517 | 497 | 499 | 484 | 458 | 472 | 476 |
| 10-K | 2025 | 523 | 504 | 510 | 494 | 467 | 481 | 483 |
| 10-Q | 2005 | 1,502 | 0 (pre-rule) | 1,416 | 0 | 0 | 0 | 386 |
| 10-Q | 2006 | 1,558 | 1,064 | 1,503 | 1,035 | 0 | 0 | 1,298 |
| 10-Q | 2007 | 1,610 | 1,269 | 1,582 | 1,257 | 920 | 960 | 1,401 |
| 10-Q | 2010 | 1,542 | 1,265 | 1,520 | 1,252 | 1,128 | 1,146 | 1,437 |
| 10-Q | 2013 | 1,552 | 1,278 | 1,543 | 1,272 | 1,157 | 1,175 | 1,434 |
| 10-Q | 2016 | 1,574 | 1,347 | 1,556 | 1,333 | 1,173 | 1,193 | 1,402 |
| 10-Q | 2019 | 1,566 | 1,366 | 1,542 | 1,350 | 1,205 | 1,219 | 1,409 |
| 10-Q | 2022 | 1,546 | 1,398 | 1,513 | 1,377 | 1,284 | 1,310 | 1,447 |
| 10-Q | 2025 | 1,554 | 1,418 | 1,524 | 1,394 | 1,338 | 1,363 | 1,479 |

(Every year 2004–2026 is in `data/b6_local/census/after_b6.csv`, regenerated by `b6_census`.)

**Rates, 2007–2025:** 10-K Risk Factors OK **95.9%**, MD&A OK **92.9%**, both **90.3%**, combo pair
**83.2%** (2016–2025: 86.3%). 10-Q MD&A OK **98.5%**, MD&A pair **91.7%** (2016–2025: 92.4%); 10-Q combo
pair 76.1%. **Against T-237's 54–58% "ok and marker-free" 10-Ks in the same years — and T-237's "ok"
rows were not clean, so the real comparison is worse for T-237 than that.**

**Section statuses (all 46,040 filings):**

| form | Risk Factors | MD&A |
|---|---|---|
| 10-K (11,409) | OK 10,410 · pre_rule 525 · TOO_SHORT 165 · NOT_LOCATED 161 · incorporated_by_reference 129 · not_required 7 · **CONTAMINATED 7** · unterminated 5 | OK 10,489 (item carve, title fallback for the cross-reference-index layout, or ICFR-trimmed) · **external (Exhibit 13 only) 768 (6.7%)** · TOO_SHORT 133 · NOT_LOCATED 18 · **CONTAMINATED 1** |
| 10-Q (34,631) | OK 27,820 (80.3%) · **item_absent 3,793 (11.0%)** · pre_rule 2,055 · NOT_LOCATED 387 · TOO_SHORT 345 · unterminated 150 · not_required 81 | OK 33,984 (98.1%) · TOO_SHORT 298 · NOT_LOCATED 263 · unterminated 73 · external 13 |

MD&A sources across all filings: item carve 42,145 · title fallback 2,134 (+52 end-of-document) ·
ICFR-trimmed 142. **CONTAMINATED (8 sections)** is the parser's end-of-document assertion firing on a
structurally terminated body that still carries the signature boilerplate: those sections fail closed,
as designed, and are counted. Pairs dropped for an MD&A source switch: 60 (10-K) and 219 (10-Q).

**Distributions (no returns; sanity only):** median YoY combo TF-cosine 0.981 (10-K); median 10-Q
MD&A TF-cosine 0.958; s.d. of 10-K Δtone 0.0022 (tone itself ≈ −1.7% of tokens).

### 4.3 ★ Usable ranking signals per quarter-end rebalance (the feasibility census; no prices)
Members of the PIT S&P 500 that month with a CIK; "usable" = the latest filing with
`decision_floor_date` ≤ t, accepted within 6 months, carrying a defined ranking signal under the
proposed R6 text rule (10-K → YoY combo; 10-Q → YoY MD&A). Full table:
`data/b6_local/census/rebalance_signal_coverage.csv`.

| rebalance | members with CIK | usable | share | of which 10-K / 10-Q |
|---|---|---|---|---|
| 2007-03-31 | 488 | 360 | 73.8% | 261 / 99 |
| 2010-06-30 | 492 | 461 | 93.7% | 22 / 439 |
| 2013-03-31 | 492 | 432 | 87.8% | 328 / 104 |
| 2016-03-31 | 498 | 430 | **86.3%** (window minimum) | 339 / 91 |
| 2016-06-30 | 498 | 460 | 92.4% | 24 / 436 |
| 2019-12-31 | 499 | 467 | 93.6% | 34 / 433 |
| 2022-03-31 | 498 | 454 | 91.2% | 357 / 97 |
| 2025-06-30 | 500 | 487 | 97.4% | 15 / 472 |
| 2025-12-31 | 500 | 476 | 95.2% | 38 / 438 |

**In the proposed 2016–2025 window: 40 rebalances, 430–487 usable names (median 464), 86.3%–97.4% of
members (median 93.0%).** Every rebalance clears §7.7's floor (≥ 150 ranked names) and §11's halt rule
(≥ 80% of members with a CIK) on the TEXT side; the price side is §11's coverage table. The March
rebalances are the low points (86–93%): they rank mostly fresh 10-Ks, whose combo needs both sections
(the Exhibit-13 hole and the 10-K combo's stricter pairing).

### 4.4 T-265 (HELD; 45 CIKs, 2,012 filings — no coverage claim possible)
Risk Factors OK 1,676 · item_absent 224 · not_required (smaller reporting companies) 46 ·
NOT_LOCATED 57; MD&A OK 2,002 of 2,012 (99.5%). YoY combo pair 82.0% (10-K) / 71.0% (10-Q); MD&A pair
88.7% / 90.9%. Remaining: 4,054 CIKs, roughly 20 h of fetching at today's rate.

### 4.5 S&P identity coverage (§3.4)
131,673 member-months 2005-01 → 2026-11; **130,322 (99.0%) carry a CIK**; by year 97.6% (2005) →
99.3% (2016) → 99.4% (2025). Price-file coverage of those member-months is in §11.

## 5. Signals (to be frozen at the director's FREEZE; code `scripts/lazy_prices/b6_signals.py`, LM file md5 `12dade0123e1d096c1d1192c755f08a3`)

- **Text.** Risk Factors (10-K Item 1A; 10-Q Part II Item 1A) + MD&A (10-K Item 7; 10-Q Part I
  Item 2), concatenated ("combo"). The combo is defined only when BOTH sections are OK in BOTH filings of
  a pair and the MD&A source (item carve vs title fallback) is the same in both. Per-section values are
  reported beside it, never gated. **Proposed (ruling R6, on coverage alone):** the 10-K ranks on the
  combo; the 10-Q ranks on MD&A alone (its Part II Item 1A is absent in 11.0% of 10-Qs and flips
  between a one-liner and the full list), the 10-Q combo reported as a diagnostic.
- **Pairing (PIT).** Same CIK, same form, prior accepted strictly earlier. 10-K: the prior 10-K whose
  period end is 9–15 months earlier. 10-Q (PRIMARY): the 10-Q for the same fiscal quarter a year
  earlier (period end 350–380 days earlier) — CMN's seasonality-controlled comparison. **Source,
  stated honestly:** Cohen, Malloy and Nguyen, "Lazy Prices", *Journal of Finance* 75(3), 2020,
  pp. 1371–1415 — the data/similarity-measure section, where (as I recall it) each quarterly filing is
  compared with the same fiscal quarter of the prior year to remove the seasonality of 10-Q content.
  **This is from memory and NOT verified against the text in this session** (no approved access to the
  paper); the section and page must be checked against the published article before freeze. The
  director accepted this pairing in principle (2026-11-11, R2). 10-Q (diagnostic): the adjacent prior
  10-Q (60–200 days). Both are computed.
- **Signal 1 — similarity (PRIMARY).** Cosine similarity of term-frequency vectors (CMN Sim_Cosine),
  lower-case alphabetic tokens ≥ 2 letters, sklearn's 318 English stop words removed. Jaccard (word
  sets) and T-237's per-pair sublinear TF-IDF cosine are reported, never gated.
- **Signal 2 — tone change.** tone = (N_positive − N_negative) / N_tokens on the same combo text, LM
  2025 master dictionary (Negative 2,355 words; Positive 354), positive words negated by
  no/not/none/neither/never/nobody within the three preceding words are not counted (Loughran-McDonald
  2011); Δtone = tone(t) − tone(prior). Uncertainty and litigious shares are reported.
- **Timing.** `acceptance_dt` (SEC acceptance stamp, true UTC — verified: ETN's
  `2023-02-23T21:22:19Z` carries filingDate 2023-02-23, impossible if it were ET past 17:30).
  `decision_floor_date` = the calendar day after the literal acceptance date. A signal is usable at a
  rebalance close only if its `decision_floor_date` ≤ the rebalance date.

## 6. Construction (both arms)

- **Rebalance:** the last trading day of each calendar quarter (Mar, Jun, Sep, Dec), equal weight,
  held one quarter. Quarterly, per the brief (T-237 was annual).
- **The signal a name carries at rebalance t:** its most recent filing (10-K or 10-Q) with
  `decision_floor_date` ≤ t and acceptance within the last 6 months, whose combo similarity (resp.
  Δtone) is defined. No such filing → the name is out of that quarter's ranking (counted).
- **Ranking:** percentile rank WITHIN FORM at t (10-K-latest names among themselves, 10-Q-latest names
  among themselves — 10-K and 10-Q similarity levels differ), then pooled terciles. **Long** = top
  tercile; **short (diagnostic)** = bottom tercile; **universe** = all ranked names, equal weight.
- **S&P arm universe:** PIT S&P 500 members at t (`data/universe/sp500_membership_pit.parquet`, the
  B-6 month map `sp_universe_months.parquet` for the CIK) with a usable signal and a price in the
  price source of §11.
- **T-265 arm universe:** T-265 priced CIKs with 20-day median dollar ADV in [$1M, $200M) at t —
  B-2's band (its R5) — with a usable signal. Deaths: **B-2's frozen rule by reference** (its §4.3 and
  amendment A1.2: BASE −30% Shumway at the last traded bar, proceeds in BIL TR; STRESS −100% and
  LAST-PRICE as diagnostics; phantom tails truncated; reused tickers split at a ≥ 63-day no-trade gap).
  B-2's survivorship caveat (§2.7, ruling R1) applies verbatim: a PASS here is an UPPER BOUND.
- **Windows:** set by text coverage and price-source cleanliness (§11), never by results.
  - Text supports YoY 10-K pairs from FY2006 filings (Item 1A mandatory for fiscal years ending on or
    after 2005-12-01) and 10-Q pairs from 2007; the price source is the binding constraint.
  - **S&P (as proposed in ruling R1):** 40 quarterly rebalances 2016-03-31 → 2025-12-31, holdings
    through 2026-03-31 (10.0 years). Sensitivity (c): 2020-06-30 → 2025-12-31 (23 rebalances, 5.75
    years). The partial quarter to 2026-05-22 (the end of the T-265 bars and the SPY/IWM/BIL TR twins)
    is excluded.
  - **T-265:** the same 40 rebalances (the 20-day ADV needs bars from 2016-01-04).

## 7. Gates, diagnostics, statistics

### 7.1 The gate (per arm)
Monthly returns. Satellite = 75% SPY TR + 25% long leg, rebalanced quarterly at the same dates (the
sleeve drifts within the quarter). **Δ log wealth** = Σ_t [ln(1 + r_blend,t) − ln(1 + r_SPY,t)].
H1 met for an arm if the PRIMARY signal's Δ log wealth has `ci_low` > 0 at the family level (§7.4).
SPY TR: `data/processed/tr_reconciled/SPY_1d.csv` (T-256; exact TR, unaffected by the dividend-era HIGH).

### 7.2 The short-leg diagnostic (the refutation clause)
Monthly series s_t = r(EW universe) − r(EW bottom tercile): positive when changers underperform.
`t_HAC` = Newey-West t of mean(s_t), 3 lags (a quarterly holding inside monthly data). Reported for
both signals and both arms; it enters only the refutation sentence.

### 7.3 Bootstrap
`MetricsEngine.bootstrap_distribution` on the MONTH INDICES (the B-1/B-2 pattern: one draw serves the
long leg, SPY, the short-leg series and every diagnostic, so all are paired), **1,000 iterations, seed 0,
AUTO block length** per that function, percentile CI. `[NN-SHARPE-CI]`: any Sharpe/Sortino quoted
carries its `ci_low` from the same draw.

### 7.4 Multiple testing inside the family
The family is {similarity, Δtone} per arm (the brief: "not a third trial"). Bonferroni over the two:
the gate's `ci_low` is the **1.25th percentile** (two-sided 97.5% interval) for each signal; H1 is
met by an arm if either signal clears at that level. The primary signal's 2.5th-percentile `ci_low` is
reported beside it and cannot meet H1 alone.

### 7.5 Pre-named diagnostics (cannot meet H1)
Long-short spread and its t_HAC · per-section signals (risk only, MD&A only) · Jaccard and TF-IDF
variants · the 10-Q adjacent-quarter pairing · LM uncertainty/litigious shares · 10-K-only and
10-Q-only rankings · per-year table · turnover, cost drag (bps/yr) · the brief's flat-75-bps T-265
cost · (T-265) STRESS, LAST-PRICE, SURVIVOR-ONLY, IWM-sleeve · standalone Sharpe/Sortino with
`ci_low` and the DSR line.

### 7.6 Costs
- **T-265 arm (gate): 70 bps RT for $20M–$200M ADV and 150 bps RT for $1M–$20M**, charged
  |Δw| × RT/2 per side at each rebalance, by the name's ADV bucket at t; an exit from a name whose ADV
  left the band at 150 bps if ADV < $20M or missing, 70 bps otherwise. This is B-2's amendment A1.3
  (ruling R3), adopted for consistency across the two small-cap briefs on the same panel. **Sensitivity:
  the brief's flat 75 bps RT** (cannot meet H1).
- **S&P arm: 10 bps RT** (B-1's large-cap basis; the brief names no S&P cost). Sensitivity: 20 bps.

### 7.7 Fail-closed (`[NN-FAIL-CLOSED]` / `[NN-CENSUS]`) — the harness HALTS (non-zero exit, no headline) if
- the LM file's md5 differs from the manifest, or any shard / signal file named in the census is
  missing or disagrees with its recorded row count;
- any rebalance has fewer than 150 ranked names (S&P) or 300 (T-265), or fewer than 40 in a tercile;
- a held name's monthly return is NaN without a death classification (T-265) or without a recorded
  index deletion (S&P);
- SPY TR (or IWM / BIL for T-265) lacks any holding month; the bootstrap gets < 24 months;
- the price source of §11 is not the declared one for any month (a source switch is a FAIL).

## 8. Power — minimum detectable effects (pre-data; assumptions stated, NOT measured)

MDE80 = 2.80 × SE (two-sided 5%, 80% power); the Bonferroni level of §7.4 raises the factor to
(2.24 + 0.84) = 3.08. Assumptions are literature/project-typical tracking errors, not computed here.

| gate | SE model (assumptions) | **MDE80 (central)** | at the family level (×3.08) | range across the assumptions |
|---|---|---|---|---|
| **S&P long-leg satellite**, window (d), 10.0 yr | SE = 0.25 × TE × √10; TE (top tercile EW vs SPY TR) **6%**/yr (4–8%) | **+0.133 total ≈ +1.3%/yr on the blend ≈ the long leg beating SPY TR by ~5.3%/yr** | +0.146 (≈ 5.8%/yr) | long leg +3.5 to +7.1%/yr |
| S&P long-leg satellite, window (c), 5.75 yr (sensitivity) | the same, √5.75 | +0.101 total ≈ 1.75%/yr blend ≈ long leg +7.0%/yr | +0.111 | +4.7 to +9.3%/yr |
| **T-265 long-leg satellite**, 10.0 yr | TE (in-band small-cap tercile EW vs SPY TR) **14%**/yr (10–18%) | **+0.310 total ≈ +3.1%/yr on the blend ≈ the long leg beating SPY TR by ~12.4%/yr** | +0.341 (≈ 13.6%/yr) | long leg +8.9 to +16%/yr |
| **S&P short-leg t_HAC** (monthly EW universe − EW changers) | σ(spread) **3.5%**/yr (2.5–5%) | **t = 2 at +2.2%/yr; MDE80 +3.1%/yr** | — | t = 2 at +1.6 to +3.2%/yr |
| **T-265 short-leg t_HAC** | σ(spread) **6%**/yr (4–8%) | **t = 2 at +3.8%/yr; MDE80 +5.3%/yr** | — | t = 2 at +2.5 to +5.1%/yr |

**Stated plainly, as the director asked: the SHORT-LEG diagnostic is the most informative statistic
B-6 produces, and the long-leg gates can only detect effects far above anything the literature
reports.** A long-leg null therefore says little; a short-leg t_HAC is where the evidence is — and it
enters only the refutation clause, never H1.

**What this means, plainly.** The long-leg gates detect only a long leg that beats SPY by 5%/yr (S&P)
or 12%/yr (small caps). CMN place the effect mostly in the SHORT leg (changers underperform); the
long side is small (my recollection of the paper: a long-short alpha of tens of basis points a month,
concentrated in the short leg — to be checked against the paper before freeze). **The long-leg gates
are badly underpowered for the effect the literature reports**: a FAIL there is weak evidence, and the
labelling rule below applies. The short-leg diagnostic has moderate power in the S&P arm and is the
most informative statistic B-6 produces — but it enters only the refutation clause, never H1.

**Labelling rule (binding, B-2's):** a satellite null (`ci_low` ≤ 0) whose point estimate is below its
central MDE80 is labelled **"not demonstrable at this length"**, and the brief's refutation sentence
still applies verbatim beside it.

## 9. Honest prior + N_trials + honest N

- **Brief:** 12% (S&P) / 20% (T-265). **Mine, stated before any return:** S&P **8%** — the
  long-leg satellite gate's MDE (§8) is several times the long-side effect CMN report, so even a
  real effect mostly fails the gate; T-265 **10%** — the small-cap satellite's MDE is larger still,
  and over this decade the size factor ran against small caps (IWM TR lagged SPY TR in 8 of 10 years,
  B-2 §3.4). **P(short-leg t_HAC ≥ 2):** S&P 25%, T-265 30% — CMN's effect is mostly there.
- **N_trials: +2** (S&P arm; T-265 arm), as briefed. Tone change is inside each arm's family (§7.4).
- **Honest N (read-only, `core/measurement/mbl_gate.py`, 2026-11-11):** registry N_raw = 231,
  `compute_n_effective_correlated()` = **36.92** (conservative = ONC 36.92; equicorrelated 33.51). The
  registry omits every standalone-harness trial (health_check MEDIUM, main `573fc62`): B-1's 6,
  B-9's 1, B-2's 2, T-379's and the T-306 series are not in it; CURRENT_STATE's hand count is "~260+".
  Both are quoted side by side, as that MEDIUM requires. N_eff ≈ 37–42 across those counts.
- **MinBTL at N_eff 36.92 (exact form):** SR 0.4 → 29.1 yr · 0.5 → 18.6 · 0.6 → 12.9 · 0.8 → 7.3 ·
  1.0 → 4.7. Required SR for a window of T years = √(4.66 / T): the proposed 10.0-yr window (§11
  option (d)) → **0.68**; the 5.75-yr sensitivity (c) → **0.90**; a 19-yr window (a)/(b) → **0.50**. `[NN-MBL]`: no window here clears MinBTL for a realistic text-signal SR; every
  standalone SR quoted carries the DSR line and the satellite paired `ci_low` remains the gate.

## 10. Pre-named outcomes

| outcome | what it means | what it does NOT mean |
|---|---|---|
| both arms `ci_low` ≤ 0 AND short-leg t_HAC < 2 in both | **Lazy Prices is H0 on free data for this operator** (verbatim) — the first verdict doc T-237 never got | not a verdict on paid full-text data, other sections, or other horizons |
| an arm `ci_low` > 0 | S&P: a measured pass, `[NN-SUBSTRATE-REVERIFY]` and MinBTL caveats attached. T-265: **UPPER BOUND — not certifiable** (B-2 §2.7) | not deployable; no promotion |
| both `ci_low` ≤ 0 but a short-leg t_HAC ≥ 2 | the refutation does NOT hold: the effect lives where a Roth cannot go. Recorded as such | not a long-only opportunity |
| tone clears, similarity does not | a tone effect, reported under the family's Bonferroni level | not a similarity result |
| a significant NEGATIVE long leg | reported as negative, never flipped (§2.3) | not a short signal |

## 11. PRICE SOURCE — why the S&P arm cannot read `data/processed/` before 2020-04, and what it reads instead

**The defect (main, `d82f4b8`, `docs/State/health_check.md` HIGH, 2026-11-11).** The canonical cache
`data/processed/*_1d.csv` mis-counts dividends by era: it over-counts by ≈ 0.58 × yield from 2011-Q2 to
each name's seam (2018-01-02 for 474 names; **2020-04-09 for 100 names, MO/VZ/XOM/KO/PFE/JNJ/PG among
them**; 6 others) and under-counts 2003–2010. 334 of 730 files are off by > 0.5%/yr. The tilt is
toward high-yield names in 2011–2019 and away from them in 2003–10 — exactly the names a text signal
on mature, unchanged filers is likely to favour. Under `[NN-FAIL-CLOSED]` the S&P arm may NOT read it
for any pre-2020-04 window; the HIGH itself says "B-6 must read a clean price source".

**Price-FILE coverage of PIT S&P member-months with a resolved CIK (measured 2026-11-11 from file
names only — no price read; `b6_census.price_coverage`):**

| year | T-265 Alpaca TR file | `data/processed` file | clean union* |
|---|---|---|---|
| 2016 | 83.4% | 86.8% | 83.4% |
| 2017 | 86.6% | 89.3% | 86.6% |
| 2018 | 88.7% | 91.4% | 88.7% |
| 2019 | 91.3% | 93.4% | 91.3% |
| 2020 | 92.7% | 96.4% | 92.7% → 98.9% after 2020-04-09 |
| 2021 | 93.1% | 97.7% | 99.2% |
| 2022 | 93.7% | 98.0% | 99.2% |
| 2023 | 94.7% | 98.5% | 99.2% |
| 2024 | 95.4% | 98.8% | 99.3% |
| 2025 | 96.5% | 99.1% | 99.5% |

\* `data/processed` counts as clean only after 2020-04-09 (every name's seam); before that only T-265
is clean. For 2005, `data/processed` holds a file for 64.7% of member-months — the canonical cache is
itself survivorship-truncated, independent of the dividend defect. The names missing from both
sources in 2016–19 are mostly acquired members (CELG, RHT, AET, TWX, MON, LVLT, PX, BCR, GGP, XL) plus
two share-class file-name forms (BRK-B, BF-B) Phase 2's census must resolve.

**The options, with their costs (MinBTL at N_eff 36.92, exact form, §9):**

| option | window (quarterly rebalances) | years | required SR | coverage of member-months | cost / risk |
|---|---|---|---|---|---|
| **(a)** wait for the user's substrate fix (the HIGH's option (a′)) | 2007-Q1 → 2025-Q4 (text supports pairs from FY2006) | ≈ 19 | ≈ 0.50 | `data/processed` 69–99% (truncated pre-2016, above) | an unknown wait; a USER ruling that reopens the 2026-10-22 cutover; the pre-2016 survivorship truncation remains even after the fix |
| **(b)** era-correct TR inside B-6 from raw Stooq + Alpaca (b = 0 from 2011-Q2; 2003–2011 dividends from a dividend source) | as (a) | ≈ 19 | ≈ 0.50 | as (a) | a SECOND, private substrate beside the canonical one (the divergence the cutover ruling exists to prevent); a dividend source (yfinance) is a network service not approved for B-6; delisted names have none (a survivor-correlated approximation); its acceptance test (excess vs T-265 = 0 ± 0.05 pp) cannot run before 2016, where T-265 does not exist — the years it adds are the years it cannot verify. 1–2 days + review |
| **(c)** `data/processed` after the last seam only | 2020-Q2 → 2025-Q4 | 5.75 | **≈ 0.90** | 96.4% → 99.1% | zero build; one regime; exploratory only under `[NN-MBL]`; MDE larger (§8) |
| **(d) — found in Phase 1** T-265's Alpaca `adjustment='all'` bars (verified total return throughout: B-2 §3.4 — AAPL 2016-01-04 → 2026-04-15 matches the TR cache to 1e-4; listed UNAFFECTED by the HIGH) | 2016-Q1 → 2025-Q4 | 10.0 | **≈ 0.68** | 83.4% (2016) → 96.5% (2025); with `data/processed` filling after 2020-04-09, 98.9–99.5% | zero build, no new substrate, the SAME price source as the T-265 arm; the cost is a survivorship hole of 8.7–16.6% of member-months in 2016–2019 (acquired members) |

**Recommendation (this SUPERSEDES the "(c) + (b)" I proposed in my first Phase-1 report, on evidence
found since): (d) as the S&P gate — 2016-Q1 → 2025-Q4 on T-265 TR bars, with `data/processed` filling
names T-265 lacks only for holding months after 2020-04-09 (both exact TR there; one source per name
per holding quarter, recorded) — plus (c) as the one pre-named sensitivity (the coverage-complete
sub-window, 2020-Q2 → 2025-Q4). (b) is NOT recommended inside B-6, and the pre-2016 extension waits for
(a) as its own pre-registered run.** Because the hole falls on members that LEFT the index, B-2's
asymmetric rule (its §2.7, ruling R1) is adopted for the S&P arm too: a long-leg PASS reads "UPPER
BOUND"; the short-leg diagnostic is biased TOWARD ZERO (distressed changers that later delisted are
missing), so a short-leg t_HAC ≥ 2 survives the hole while a short-leg null is weaker evidence than it
looks. **MBL, stated plainly: at the 10-year window a text signal needs a true Sharpe of about 0.68 to
clear MinBTL at today's N_eff, and 0.90 at the 5.75-year window. No Lazy-Prices strategy in the literature
has that Sharpe long-only. Neither window can produce deployment evidence; each can only refute, or
nominate for the longer window that (a) would open.** The harness HALTS if any quarter's ranked S&P
names fall below 80% of the PIT members with a CIK, and reports the coverage per quarter.

## 12. Predictions (frozen here; the verdict compares against them)

- **S&P, similarity, long-leg satellite:** point estimate in [−0.05, +0.10] total Δ log wealth;
  `ci_low` ≤ 0; labelled "not demonstrable at this length".
- **S&P, similarity, short-leg t_HAC:** +1.0 to +2.5 (changers underperform modestly; post-publication
  decay — CMN circulated from 2010).
- **T-265, similarity, long-leg satellite:** `ci_low` ≤ 0, dominated by the size factor.
- **T-265, short-leg t_HAC:** +1.5 to +3.0 — low-attention names are where CMN find the effect.
- **Tone change:** weaker than similarity in both arms (its information overlaps the similarity drop).
- **Expected verdict:** the refutation sentence does NOT fully hold (≈ 45%): a short-leg t_HAC ≥ 2 in
  one arm is the single most likely positive finding, and it is undeployable in a Roth.

## 13. Rulings requested (R1–R9)

- **R1 — the S&P price source (§11).** Proposed: **(d)** T-265 TR bars 2016-Q1 → 2025-Q4 as the gate,
  `data/processed` filling only after 2020-04-09; **(c)** 2020-Q2 → 2025-Q4 as the one sensitivity; (b)
  not inside B-6; the pre-2016 extension waits for (a) as its own prereg. This supersedes my first
  report's "(c) + (b)". The B-2 asymmetric survivorship rule extends to the S&P arm.
- **R2 — the 10-Q comparison.** The brief says "the prior same-form filing". I propose the SAME FISCAL
  QUARTER a year earlier as PRIMARY (seasonality-controlled, as I read CMN 2020 §I — please confirm
  against the paper) and the adjacent quarter as a diagnostic. Both are computed; the ruling only picks
  which one ranks.
- **R3 — costs.** T-265: B-2's 70 / 150 bps RT by ADV bucket (its A1.3) as the gate, the brief's flat
  75 bps RT as the sensitivity — consistency across the two briefs on one panel. S&P: 10 bps RT (B-1's
  basis; the brief names none), 20 bps as the sensitivity.
- **R4 — identity.** Accept the month-level CIK rule (§3.4) and its NOT_COVERED list, including the
  share-class rule (one ticker per firm per month, so an equal-weight book never holds Alphabet twice).
- **R5 — the family.** Similarity and Δtone per arm under Bonferroni (1.25th-percentile `ci_low`), as
  the brief's "same family (not a third trial)" requires some correction and Bonferroni is the simplest
  that holds under any dependence.
- **R6 — the text definition.** The combo (Risk Factors + MD&A, both OK in both filings, same MD&A
  source) ranks; a firm without it is out of that quarter. **Proposed, on coverage alone (§4.2 — no return exists):** the 10-K ranks on the combo (Items 1A + 7,
T-237's text); the **10-Q ranks on MD&A (Part I Item 2) alone**, with the 10-Q combo reported as a
diagnostic. Reason (complete-panel census, §4.2): 11.0% of 10-Qs carry no Part II Item 1A at all
(3,793 of 34,631; witnessed in Abbott's), and where it exists it flips between a one-line "no material
changes" and the full list (YoY cosine 5th percentile 0.21 on the first sample) — a formatting change,
not a language change. 10-Q MD&A pairs exist for 91.7% of 2007–2025 10-Qs vs 76.1% for the combo.
Ranking stays within form (§6), so the two texts never compete in one ranking. Re-confirmed on the
complete S&P panel; under this rule every 2016–2025 rebalance carries 430–487 usable names (§4.3).
- **R8 — the two arms' readiness.** The S&P panel is COMPLETE and re-censused (§4). The T-265 stream is
  HELD at 45 of 4,099 CIKs (≈ 20 h of fetching left at today's rate, signals only, a few MB of output);
  the director restarts it when the disk allows. Proposed: the S&P arm may freeze on its own; the T-265
  arm freezes after its census.
- **R9 — Exhibit-13 MD&A.** 768 of 11,409 10-Ks (6.7%; 13.7% in the old-line first sample) keep MD&A
  only in an EX-13 annual report. Recovering it costs one exhibit fetch per such filing and a title-based
  carve of a document with no Item structure. Proposed: NOT in B-6 — those 10-Ks rank on nothing
  (NOT_COVERED), counted per quarter. The complete census shows the hole is below the ~10% revisit line,
  and the text-side coverage never falls under 86.3% of members in the proposed window (§4.3).
- **R7 — the T-265 text universe.** Every T-265 priced CIK (4,743; the 644 also in the S&P panel are
  joined from it), filings from 2015. The ADV band is applied in Phase 2 at each rebalance.

## 14. Sequence
Draft (2026-11-11) → director rulings → FREEZE → Phase 2 harness (standalone; never `BacktestController`)
→ determinism ×2 (bit-identical md5) → verdict `docs/Audit/b6_lazy_prices_verdict_<date>.md` →
predictions compared line by line.

## Reproduce Phase 1 (execute, don't read)
```bash
python -m scripts.lazy_prices.b6_cik_map                 # offline: Form 3/4/5 symbol chains
python -m scripts.lazy_prices.b6_build_panel universe     # SEC submissions; member CIK per month
python -m scripts.lazy_prices.b6_smoke                    # 30+ real filings, printed for a read
python -m scripts.lazy_prices.b6_build_panel fetch --min-interval 0.22 --disk-floor 10
python -m scripts.lazy_prices.b6_build_panel fetch --retry-failed --ciks 858877   # the 37 Cisco DNS failures
python -m scripts.lazy_prices.b6_stream_t265 --min-interval 0.45
python -m scripts.lazy_prices.b6_signals sp
python -m scripts.lazy_prices.b6_census
python -m pytest tests/test_b6_lazy_prices_parse.py tests/test_b6_lazy_prices_signals.py -q
```


---

## AMENDMENT 1 — director rulings R1–R9 (2026-11-12; BINDING). Appended; the draft text above is NOT edited.

**Effect: this amendment FREEZES THE S&P ARM** (R8). The T-265 arm freezes after its own census. Where
a sentence above conflicts with this amendment, this amendment governs. Committed alone, before any
return, price-level statistic or portfolio is computed (`git log` on this file is the proof).

### A1.1 R1 — price source: ACCEPTED
- **Gate: option (d)** — T-265 Alpaca TR bars, rebalances 2016-Q1 → 2025-Q4, with `data/processed`
  filling names T-265 lacks ONLY for holding periods after 2020-04-09.
- **The one sensitivity: option (c)** — 2020-Q2 → 2025-Q4 on `data/processed`.
- **(b) stays out of B-6.**
- **B-2's asymmetric survivorship rule applies to the S&P arm:** a FAIL stands; a PASS is an UPPER BOUND.
- **Recorded:** on 2026-11-12 the USER ruled to ADOPT the T-384 (a′) drip fix for the cutover. The
  pre-2016 S&P extension waits for that cutover and runs under its own pre-registration.

### A1.2 R2 — the 10-Q comparison: RULED
- **PRIMARY: the same fiscal quarter a year earlier** (period end 350–380 days earlier). **Diagnostic:
  the adjacent prior 10-Q** (60–200 days).
- **Basis: the project's own design reason — seasonality control. It is NOT a citation.**
- **§5's attribution of this pairing to Cohen-Malloy-Nguyen (2020), including the section/page wording,
  is WITHDRAWN.** The paper's exact 10-Q comparison is **not verified here**; the director's check of
  secondary sources found them describing "quarter-to-quarter" changes. **The adjacent-quarter
  diagnostic is the closest reading of "quarter-to-quarter".** No sentence in this prereg may cite the
  paper for R2.

### A1.3 R3 — costs: ACCEPTED
T-265: 70 / 150 bps RT by ADV bucket (gate); flat 75 bps RT (sensitivity). S&P: 10 bps RT (gate);
20 bps RT (sensitivity).

### A1.4 R4 — identity: ACCEPTED
The month-level CIK rule (§3.4), its NOT_COVERED list, and one ticker per firm per month.

### A1.5 R5 — the family: ACCEPTED
Similarity and Δtone per arm under Bonferroni: the gate `ci_low` is the 1.25th percentile.

### A1.6 R6 — the text that ranks: ACCEPTED
10-Ks rank on the Items 1A + 7 combo; 10-Qs rank on MD&A alone (the 10-Q combo is a diagnostic);
ranking within form.

### A1.7 R7 — the T-265 text universe: ACCEPTED
Every T-265 priced CIK, filings from 2015; the ADV band applied at each rebalance.

### A1.8 R8 — readiness: ACCEPTED
The S&P arm freezes now (this amendment). The T-265 arm freezes after its own census. The T-265
stream was restarted 2026-11-12 19:48 UTC (`--min-interval 0.22 --disk-floor 10`), worktree-local.

### A1.9 R9 — Exhibit-13 MD&A: ACCEPTED
No Exhibit-13 fetch; those 10-Ks are NOT_COVERED, counted per quarter.

### A1.N N_trials
**+1 for the S&P arm at its run; +1 for the T-265 arm at its run.**

### A1.10 Harness conventions — the worker's operational decisions, fixed BEFORE any return (the B-1 §11.4 precedent; for the director's check; they alter no ruled term)
The draft left these unspecified; each is chosen for conservatism or for consistency with B-1/B-2.
1. **Calendar.** The trading calendar is `data/processed/tr_reconciled/SPY_1d.csv`. A rebalance is the
   last SPY trading day of each calendar quarter; monthly returns are month-end close to month-end
   close (the last bar on or before each month-end).
2. **Price join (option (d)).** CIK → T-265 ticker through `cik_ticker_final.parquet`; a T-265 ticker
   that maps to two CIKs is EXCLUDED (identity ambiguity) and counted. The `data/processed` fill uses
   the membership ticker's `Close`, only for rebalances on or after 2020-06-30 (a holding quarter wholly
   after 2020-04-09), only when the T-265 join gives no bar. One source per name per holding quarter,
   recorded.
3. **Eligibility at t.** A usable signal (R6; the latest filing with `decision_floor_date` ≤ t, accepted
   within 6 months) AND a bar on the rebalance date in the declared source.
4. **Holding.** Equal weight at the rebalance, buy-and-hold within the quarter (weights drift).
5. **Exits.** A held name whose bars end inside the quarter: return to its last close, then the
   proceeds earn BIL TR for the rest of the quarter (**D = 0**, the LAST-PRICE convention — S&P exits
   are overwhelmingly acquisitions, for which Shumway's −30% is a small-cap delisting estimate);
   **D = −30% as a diagnostic.** Every exit is recorded (name, date). A NaN return with no recorded exit
   HALTS (§7.7).
6. **Costs.** At each rebalance, Σ |w_target − w_drifted| × RT/2 over the leg, deducted from the
   leg's first month in the quarter; the first build turns over 100%.
7. **Δtone for a 10-Q** is computed on its MD&A (the text that ranks under R6); for a 10-K on the combo.
8. **Ranking.** Percentile rank within form (`method="average"`), pooled; long = pct > 2/3, short =
   pct ≤ 1/3, universe = all ranked.
9. **Satellite.** Monthly blend returns are computed on the true path (quarterly rebalance to 25/75,
   drift within the quarter, §7.1); the bootstrap resamples paired MONTH INDICES of the blend and SPY
   (`MetricsEngine.bootstrap_distribution`, 1,000 iterations, seed 0, auto block length — the B-1/B-2
   pattern); percentiles 1.25 / 2.5 / 97.5 reported.
10. **Newey-West** t with 3 lags (Bartlett). **Determinism:** two runs, identical md5 of the results
    JSON (sorted keys) before any number is quoted.

### A1.11 ★ PRE-RUN CENSUS FINDING — the frozen S&P gate HALTS as specified (worker, 2026-11-12; NO return computed)
§11 above freezes: *"The harness HALTS if any quarter's ranked S&P names fall below 80% of the PIT
members with a CIK."* On the joint census (a usable text signal AND a price bar at t in the declared
source; bar DATES only), **13 of the 40 gate rebalances fall below 80%**: every quarter from 2016-03-31 to
2018-03-29, 2018-09-28, 2018-12-31, 2019-03-29 and 2020-03-31. The minimum is **67.9% at 2016-03-31**
(338 ranked of 498 members). From 2020-06-30 the `data/processed` fill applies and every quarter clears
(87–97%).

| rebalance | members | usable text | priced in T-265 | ranked | share |
|---|---|---|---|---|---|
| 2016-03-31 | 498 | 430 | 338 | 338 | **67.9%** |
| 2017-03-31 | 500 | 443 | 362 | 362 | 72.4% |
| 2018-03-29 | 500 | 441 | 371 | 371 | 74.2% |
| 2019-03-29 | 499 | 433 | 380 | 380 | 76.2% |
| 2020-03-31 | 499 | 438 | 390 | 390 | 78.2% |
| 2020-06-30 | 499 | 472 | 424 + 18 fill | 442 | 88.6% |

**Cause:** T-265 holds no bars for 14–20% of S&P members in 2016–2019 — acquired or failed names (AET,
ANDV, ATVI, CELG, RHT, TWX, MON …) that T-265 never priced: the survivorship hole B-2 §3.1 documented.
A ticker-based join instead of the CIK join does not help (17 quarters below 80%): the bars do not
exist. Nothing inside B-6 can fill them without new price data.

**Consequence, under `[NN-FAIL-CLOSED]`: the S&P gate does not run, no smoke runs on real data, and no
return is computed until the director rules.** The options, each the director's:
- **(i)** keep the rule → the S&P arm is NOT EVALUABLE on (d) as frozen;
- **(ii)** lower the floor for 2016-Q1 → 2020-Q1 (the ranked count never falls below 338, far above
  §7.7's 150), the asymmetric rule already making any PASS an upper bound — at the cost of a gate on a
  cross-section missing up to a fifth of the index, non-randomly (acquisitions);
- **(iii)** make (c) the gate (5.75 years; MinBTL SR ≈ 0.90; coverage ≥ 87%) with (d) as a diagnostic;
- **(iv)** wait for price data that closes the hole — the one-time Alpaca SIP fetch of dead symbols that
  B-2 R1 measured, or the T-384 cutover.


---

## AMENDMENT 2 — the S&P gate window after the (d) census halted (director ruling on A1.11, 2026-11-12; BINDING). Appended; nothing above is edited.

Committed alone, BEFORE any return, price-level statistic or portfolio is computed (`git log` on this
file is the proof).

### A2.1 Window (d) 2016-Q1 → 2025-Q4 is NOT EVALUABLE
The frozen census (§7.7, §11; harness `scripts/lazy_prices/b6_harness_sp.py`, run 2026-11-12, exit 2,
no return computed) put **13 of 40 gate rebalances below the 80%-of-members floor; the worst is
2016-03-31 at 67.9%**. The census ran twice, bit-identical: census CSV md5
`c3effa85be82e4f5941051cd97dac980`, HALT list md5 `8f80dc57c89739fbae9ea976c86fe1e2`. **The cause is
missing T-265 bars for acquired or failed members — the B-2 §3.1 survivorship hole — not text
coverage** (86–97% of members carry a usable signal every quarter). **(d) re-runs as its OWN
pre-registered trial once the price hole closes** (the T-384 cutover and/or the one-time Alpaca
dead-ticker fetch B-2's census scoped).

**Option 2 of A1.11 (lowering the floor) is REJECTED** by the director: loosening a frozen gate because
it fired is goalpost-moving, even before returns. **Option 4 alone (wait) is not chosen**: the hole has
no date.

### A2.2 The S&P gate window is (c): rebalances 2020-06-30 → 2025-12-31 (2020-Q2 → 2025-Q4)
**The B-1 precedent: when a pre-return census halts, the gate window is set by INPUT AVAILABILITY.**
(c) is the input-available span — `data/processed` closes, exact total return for every name after
2020-04-09 (main's dividend-era HIGH) — where **every quarter passes the frozen 80% / 150 / 40 rules**
(census 2026-11-12: 23 rebalances, ranked share 87–97%). **It was chosen AFTER the (d) census halted and
BEFORE any return was computed.** 23 quarterly rebalances, holdings through 2026-03-31: **5.75 years
(69 months)**. **N_trials: +1 at its run.** The T-265 arm's +1 stands, at its own run.

**Power, stated up front.** At N_eff 36.92 the MinBTL Sharpe bar for 5.75 years is **≈ 0.90**. The
long-leg satellite gate can only detect a long leg beating SPY TR by roughly 7%/yr (MDE80, §8: +0.101
total Δ log wealth, ≈ +0.111 at the Bonferroni level) — far above the long-side effect in the
literature. **The short-leg t_HAC diagnostic remains the most informative statistic B-6 produces.**
Cohen-Malloy-Nguyen (2020) report their effect as concentrated in the short leg (the firms that change
their filings); no page is cited here.

**(c) no longer has a sensitivity, and none is pulled from inside (d).** The §7.5 pre-named
diagnostics (20 bps cost, D = −30% exits, Jaccard, TF-IDF, Risk-Factors-only, MD&A-only, the 10-Q
combo, the adjacent-quarter 10-Q pairing, 10-K-only and 10-Q-only rankings, the per-year table) run on
the gate's own window and source (c), as diagnostics of the gate; none can meet H1. *(This last
sentence is the worker's operational reading — the diagnostics follow the gate's window — recorded
here before any return so it is not decided after one.)*

### A2.3 A1.10 conventions: ACCEPTED as written
Delisted holdings exit at their last close into BIL TR, D = −30% as a diagnostic; a T-265 ticker mapped
to two CIKs is excluded (moot on (c), which reads `data/processed` only); the `data/processed` fill
only for rebalances on or after 2020-06-30; 10-Q Δtone on MD&A.

### A2.4 What runs next (S&P arm, on (c))
Smoke on (c)'s first 12 months (rebalances 2020-06-30 → 2021-03-31, holdings to 2021-06-30; sanity only,
not quoted) → the fail-closed census → the full run twice with an identical results md5 → the verdict
section (long-leg satellite vs SPY TR for both signals at the family level, the short-changers
diagnostic with t_HAC, and the brief's refutation sentence evaluated literally).

**ERRATUM to A2.2 (worker, 2026-11-12, after the (c) run; changes no ruling).** A2.2 says the (c)
census has a "ranked share 87–97%". That range was the (d)-source joint census (T-265 + fill) for the
same quarters. On (c)'s declared source (`data/processed` only) the census reads **83.4–94.8% (ranked
416–474; terciles ≥ 138)** — every quarter still passes the frozen 80% / 150 / 40 rules, so nothing in
A2.2 changes. Census file: `data/b6_local/harness_sp/run1/census_gate_similarity.csv`.


---

## AMENDMENT 3 — review findings F1–F5 and the defect-corrected S&P re-run (director rulings, 2026-11-12; BINDING). Appended; nothing above is edited.

**Disclosure (verbatim, as ruled): "a defect-corrected re-run after results were seen; the configuration
is unchanged; N_trials stays +1 (the B-5 A2.2 precedent)."** The original (c) run (results md5
`2ec68e5a9248af3a5138eb940960aa6f`, commit `e5a923f`) stays as the record — NON-COMPLIANT with §7.7 — and
the verdict shows both runs. Window (c), signals, ranking, legs, costs, satellite, bootstrap and gates are
unchanged; only the defects below are corrected. Committed BEFORE the corrected run.

### A3.1 F1 — §7.7 was not implemented (MEDIUM-HIGH, `[NN-FAIL-CLOSED]`)
The original harness booked ANY price-file end as an index exit (last close → BIL). §7.7 says a NaN return
with no recorded index deletion must HALT, and the harness had no deletion check. Of its 58 "exits",
≈ 27 were real M&A or failures, 8 renames (CDAY, FLT, RE, FBHS, WLTW, COG, DISCA, HFC) and ≈ 23 TRUNCATED
`data/processed` files of members still live (AVGO ends 2025-04-23; ANET, PWR, APH, MU, LRCX, CAT, DELL,
MPC, TER, GLW; CMA 2024-07-01); at 2025-12-31, 25 live members with a signal were unpriced because their
file had ended (NVDA from 2024-06, AVGO, PLTR, VST, APP, HOOD, KLAC). **Corrected:** each name-quarter's
price is resolved from bar DATES and membership records before any return — `data/processed` if it has a
bar at t and covers the quarter; else **T-265 bars joined BY CIK** (R1's primary source) if they cover
(renames resolve here, through the CIK map); else the name EXITS at its last bar ONLY if its PIT
membership interval ends within −10 / +45 days of that bar (a **recorded index deletion**); anything else
is **unresolved and HALTS the census**. Returns also halt on any exit the census did not record. A cause
table (ok / no_file / no_bar_at_t / truncated / rename / real_exit / unresolved / no_price_at_t) is in the
census, and every name-quarter's source and cause is in `price_manifest_<spec>.csv`.

### A3.2 F2 — joins (MEDIUM)
The membership writes `BRK-B` / `BF-B`; the files are `BRK.B_1d.csv` / `BF.B_1d.csv` — Berkshire and
Brown-Forman were excluded from all 23 quarters (the item §11 said Phase 2 "must resolve"). META was
excluded 2020-06 → 2022-06 (the membership ticker FB maps to a different security whose `FB_1d.csv`
starts 2025-06-26); IHS Markit likewise (INFO starts 2024-10-10); 38 later-acquired members were excluded
at 2020-06-30 because their files start 2020-07-27; MMC has no file. **Corrected:** both share-class
spellings are tried; everything else resolves through the same CIK-based T-265 fill (A3.1).

### A3.3 F4 — the parser (LOW; fixed BEFORE the T-265 arm's census and freeze)
The T-237 runaway still occurred through the title fallback: b6_parse/1 accepted an MD&A that ran to
end-of-document "when clean", and `_CONTAMINATION` knew only the 10-K signature sentence — **52 of 52 such
S&P sections carried a 10-Q signature sentence or an auditor `/s/` line** (Western Union's 2016–21 10-Q
MD&A runs through Part II to the signatures; Campbell's 2004–06 likewise). Cause: the fallback keyed
heading lines on letters only, so "Item 3. Quantitative and Qualitative …" became ITEMQUANTITATIVE… and
never matched. **b6_parse/2:** heading keys strip a leading "PART II" / "Item 3." (an item letter counts only
standing alone); "PART II", SIGNATURES, EXHIBIT INDEX, OTHER INFORMATION terminate; **end-of-document is
never a terminator** — with no terminating heading the body is cut at the first document-end marker
(signature block, either signature sentence, `/s/`, an auditor-report heading) or rejected;
`_CONTAMINATION` adds the 10-Q signature sentence, `/s/` and the auditor-report heading with its
salutation. Locks: `tests/test_b6_lazy_prices_parse.py` (the Campbell and Western Union shapes, the 10-Q
`/s/` contamination). **WITHDRAWN: the claim in §3.4 that the T-237 runaway "cannot occur by
construction".** It held for the item carve only; the title fallback broke it. **S&P panel re-parsed under
b6_parse/2** into `data/b6_local/sp_sections_v2/` (b6_parse/1 stays in `sp_sections/` as the record):
every row whose MD&A came from the title fallback or failed is re-fetched and re-parsed; every other row
keeps its item-carved text and is re-checked against the widened `_CONTAMINATION` on its stored text.
Signals recomputed (`signals_sp_v2.parquet`); the verdict states how many ranked name-quarters changed.
**The T-265 stream restarts from scratch on b6_parse/2** (its 3,880 b6_parse/1 filings archived unused).

### A3.4 F3 — the refutation framing (MEDIUM)
R2 stands — ruled pre-data, legitimate. But under the brief's literal "prior same-form filing" (the
ADJACENT 10-Q), the S&P short-leg t_HAC is **+2.27** (+2.32 with the review's fill). The verdict must say
plainly: **the S&P half of the refutation holds ONLY under R2's same-quarter-prior-year pairing; under
the adjacent pairing the short leg clears t = 2 in this window.** The "one of 8, needs |t| ≈ 2.7" discount
is withdrawn: two of the 8 are the gate signals and five (20 bps cost, D = −30%, Jaccard, TF-IDF,
MD&A-only) are near-copies of the gate, so the effective count is small and the adjacent-pairing
short-leg result is a LIVE finding, not noise. It is untradeable in a Roth (no shorts); it is named as
the candidate for a future pre-registered **negative-screen** test (exclude recent "changers" from a long
book) — not tested now.

### A3.5 F5 (LOW)
"Replaces ≈ 72% of its names" was wrong: 0.72 is the two-sided Σ|Δw|; the measured share of NEW long
names per rebalance is reported instead (≈ 32% on the original run). The 0.84 Sharpe is on RAW monthly
returns, not excess of cash. `data/processed` drops spin-off value relative to T-265 (AIV −54 pp; FTV, WDC,
LEN, J) — a known source difference of the (c) window, noted, not corrected.


---

## AMENDMENT 4 — shared T-265 tickers under the CIK-based fill (director ruling on the corrected run's census halt, 2026-11-12; BINDING; a GENERAL rule, not an AVGO exception). Appended; nothing above is edited.

Committed alone, BEFORE the corrected run computes any return. The corrected census halted (exit 2, md5
`2ede226fbca9bbd28859b299af9b447e`) on one name-quarter — AVGO, holding from 2025-03-31 — because
A1.10-2 (exclude a T-265 ticker mapped to more than one CIK) blocked the T-265-by-CIK fill F1 orders.

### A4.1 The rule
- A1.10-2's purpose is to prevent WRONG-COMPANY joins through a ticker that maps to more than one company.
  Under F1 prices join by CIK, so **the exclusion applies only to TICKER-based joins.**
- **A CIK-based fill is allowed whenever the CIK's date-aware mapping is UNIQUE at that rebalance date:**
  exactly one CIK holds the security in that month, and the T-265 bars used are keyed to that CIK or to a
  ticker that maps to it alone in that month.
- If the mapping is not unique at the date, or the bars cannot be attributed to the CIK unambiguously,
  the name-quarter stays **unresolved and the census HALTS**, as before.
- Re-domiciles and reorganisations that keep one economic issuer across a CIK change resolve by DATE,
  never by name.

**Implementation (harness `Prices.resolve`, data `data/b6_local/cik_map/t265_shared_ticker_users.parquet`,
built by `b6_cik_map --t265-shared` from the cached Form 3/4/5 data):** for a T-265 ticker mapped to more
than one CIK, the holders at t are the CIKs whose insider filings under that symbol span t (first − 90 d
≤ t ≤ last + 90 d — the same padding as the identity map); the fill is allowed only if that set is exactly
{the member's CIK}. A shared ticker with no symbol-use record is not attributable (no fill). Window (d)
keeps the original unique-ticker join, so its A2.1 record is unchanged (HALT list md5 `8f80dc57…`
identical; its census columns identical, plus all-zero cause columns).

### A4.2 AVGO 2025-Q1 — RESOLVES under the rule, by date
T-265 maps AVGO to three CIKs (1054374, 1649338, 1730168). The Form 3/4/5 data show four issuers using the symbol over time: 1317092
(2006-04-05 → 2007-04-19), Avago 1441634 (2009-08-05 → 2016-02-03), Broadcom Ltd 1649338 (2016-02-02 →
2018-03-28), **Broadcom Inc 1730168 (2018-04-06 → 2026-03-27)**. At 2025-03-31 exactly one CIK holds the
symbol, and it is the member's (1730168). The 2018 Broadcom Ltd → Broadcom Inc re-domicile resolves by
date.

### A4.3 Every name-quarter the rule resolves (the census, re-run; no return computed)
The corrected gate census now PASSES (ranked 438–489 per quarter, 87.8–97.8% of members, 0 unresolved).
The rule resolves **5 name-quarters, all Broadcom Inc (CIK 1730168, AVGO)**:

| rebalance | cause | why the fill was needed |
|---|---|---|
| 2024-12-31 | no_bar_at_t | `data/processed` has no bar at t |
| 2025-03-31 | truncated | `data/processed` ends 2025-04-23 inside the quarter |
| 2025-06-30 | no_bar_at_t | `data/processed` ended 2025-04-23 |
| 2025-09-30 | no_bar_at_t | as above |
| 2025-12-31 | no_bar_at_t | as above |

Every name-quarter's source, cause and the `shared_resolved` flag are in
`data/b6_local/harness_sp/<run>/price_manifest_gate_similarity.csv`. The other 12 (c)-window members
with shared T-265 tickers (PNR, CCL, COHR, CB, LDOS, PRGO, MDT, CI, DIS, STE, XRX, SNDK) needed no fill.

- Review round 2 (2026-11-12, APPROVED): text-only errata LOW-1 to LOW-4 (renames as exits, unresolved exclusions, smoke timing, framing) are in docs/Audit/b6_lazy_prices_verdict_2026-11-12.md §6; no number and no amendment above changes.


---

## AMENDMENT 5 — a pre-registered OUT-OF-SAMPLE confirmation, on T-265, of the S&P arm's one table-suggested finding (director, 2026-11-14; BINDING; PRE-DATA for the T-265 arm). Appended; nothing above is edited.

Committed alone, while the T-265 text stream is still running and BEFORE any T-265 return, price join or
signal ranking has been computed. **What exists for T-265 at this commit:** only the stream's per-filing text
signals and section statuses under `data/b6_local/t265_signals/` (3,053 of 4,099 CIKs processed; latest file
2026-11-14 00:13:29 local). No T-265 harness exists; B-6 has read no T-265 small-cap price, formed no
ranking and computed no return. (The S&P harness read T-265 bars only for S&P member CIKs, as fills.) No
distribution of any T-265 signal has been examined — only parse-coverage counts.

### A5.1 Why
On the S&P arm, under the brief's literal ADJACENT 10-Q pairing, the short leg (changers) had t_HAC **+2.23**
(the review: +2.21) in the sense "universe minus changers"; under the ruled same-quarter pairing it had the
wrong sign. That is a data-suggested slice and **cannot be certified on the data that suggested it.** The
T-265 small-cap universe has not been looked at, so it is the one honest out-of-sample test.

### A5.2 H_OOS (frozen now)
On the T-265 universe, names in the BOTTOM tercile of adjacent-quarter similarity ("changers") underperform
the equal-weight T-265 universe over the following quarter: **mean (changers − universe) monthly return < 0
with t_HAC ≤ −2.0** — Newey-West, 3 lags, the same lag rule as the S&P diagnostic — as a GROSS relative
return (net of nothing: it is a screen, not a traded short), on the T-265 arm's own window, with the same
rebalance dates and inclusion rules as the T-265 gate (the ADV band at t, the freshness rule, the gate's
death rule).

**The construction is the S&P diagnostic's, exactly** (harness spec `q10_adjacent`, unchanged): a name
whose latest usable filing at t is a 10-Q carries its MD&A cosine against the ADJACENT prior 10-Q (period
end 60–200 days earlier; `qoq_mda_cos`); a name whose latest filing is a 10-K carries its YoY combo cosine;
percentile rank within form, pooled terciles; changers = the bottom tercile; universe = all ranked names,
equal weight. *Worker's note for the freeze:* the ruling's words are "10-Q filers in the bottom tercile";
the statistic that produced +2.23 pooled both forms as above, so the identical pooled construction is the
one pinned here as H_OOS. The 10-Q-names-only variant (changers and universe restricted to names whose
latest filing is a 10-Q) is reported beside it as a labelled companion and cannot meet H_OOS. If the
director means the narrower reading to be the test, that ruling must land at the T-265 freeze, before any
T-265 return.

### A5.3 Refutation, and what a pass licenses
- **Refutation:** the wrong sign, or |t_HAC| < 2 ⇒ the adjacent-pairing finding is **closed permanently as
  a one-window artifact. No re-slicing** (no other pairing, window, tercile cut, form subset or universe).
- **If it holds:** it licenses ONLY a pre-registered **24-month forward paper book of a negative screen** (a
  long book that excludes recent changers) — never a backtest claim, never a deployment.

### A5.4 Accounting (proposed; the director rules at the T-265 freeze)
- **This is one extra pre-declared test in the T-265 arm.** Proposed N: **+1** (the T-265 arm then consumes
  +2 at its run: the gate family, and H_OOS) — H_OOS is a separately reported statistic that could be
  quoted, which is what honest N counts (the B-1 ruling).
- **Proposed family:** H_OOS is its own one-hypothesis family — a different hypothesis from H1 (it cannot
  meet H1 and H1 cannot meet it), one-sided, at its own frozen threshold t_HAC ≤ −2.0 (≈ 2.3% one-sided).
  The gate's Bonferroni family stays {similarity, Δtone} at the 1.25th percentile, unchanged. The
  stricter alternative, if the director prefers one family of three: t_HAC ≤ −2.39.
- **The T-265 GATE is unchanged:** its ruled primary 10-Q pairing remains the same fiscal quarter a year
  earlier (R2); the adjacent pairing enters the T-265 arm only through H_OOS (and as the §7.5 diagnostic).

### A5.5 Power (pre-data; assumptions stated, not measured)
Expected sample: the T-265 window's 40 quarterly rebalances (120 months, 10.0 years) if the T-265 freeze
keeps 2016-Q1 → 2025-Q4; roughly 1,000–1,500 ranked names per quarter, so ≈ 350–500 changers. With the
monthly (changers − universe) spread at σ = 6%/yr (4–8%; §8's small-cap assumption), SE of the annualised
mean = σ/√10 = 1.9%/yr (1.3–2.5%). **t_HAC = −2.0 is reached at a gap of −3.8%/yr (−2.5 to −5.1%); the gap
detectable with 80% power is −5.4%/yr (−3.6 to −7.2%).** The S&P estimate was −1.96%/yr: at that size the
test would reach t ≈ −1.0 and pass about one time in six. **So H_OOS can confirm only an effect roughly
twice the S&P one** — which is what the literature's "stronger in low-attention names" would imply, and no
more than that. A refutation here is therefore weak evidence against a small effect and is stated as such
in advance; the closure rule in A5.3 holds regardless.

---

## AMENDMENT 6 — director rulings on AMENDMENT 5 (2026-11-14; BINDING; PRE-DATA for the T-265 arm). Appended; nothing above is edited.

Committed alone, still before any T-265 return, price join or signal ranking has been computed (the only
T-265 outputs are the stream's per-filing text signals and statuses; no T-265 harness exists).

- **A6.1 Population — the worker's reading is RATIFIED.** H_OOS uses the IDENTICAL construction that
  produced the S&P statistic: ranked within form — a name whose latest filing is a 10-Q on adjacent-quarter
  MD&A similarity, a name whose latest filing is a 10-K on the year-on-year combo — then pooled; changers =
  the bottom tercile; universe = all ranked names, equal weight. Only the same construction is a
  confirmation; the ruling's "10-Q filers" wording in AMENDMENT 5 was loose. The 10-Q-names-only version is
  reported beside it as a diagnostic that CANNOT meet H_OOS.
- **A6.2 Accounting — ACCEPTED.** +1 N for H_OOS: the T-265 arm consumes **+2** at its run (the gate family;
  H_OOS). H_OOS is its own one-hypothesis family at **t_HAC ≤ −2.0**. The gate's Bonferroni family
  ({similarity, Δtone}, 1.25th-percentile `ci_low`) is unchanged.
- **A6.3 Power — to be stated in the verdict's FIRST paragraph, as in A5.5:** a pass at about 1-in-6 odds if
  the true gap equals the S&P estimate; a refutation is weak evidence against a small effect and closes
  only the adjacent-pairing finding as a certifiable claim.

---

## AMENDMENT 7 — director rulings on the T-265 text census (2026-11-17; BINDING; PRE-DATA for the T-265 arm). Appended; nothing above is edited.

Committed alone, BEFORE the overlap gap fill, any further stream, any T-265 price join, ranking or return.
**What exists for T-265 at this commit:** the stream's per-filing text signals and section statuses for the
4,099 streamed CIKs (`data/b6_local/t265_signals/`, parser `b6_parse/2`, DONE 2026-11-14 09:56:52Z) and the
text census of commit `6e52752` (counts only; `data/b6_local/census/t265_*.csv`). No T-265 small-cap price
has been read, no ranking formed, no return computed, and no distribution of any T-265 signal examined.

### A7.1 Ruling 1 — the overlap text gap: FILL IT
The director: stream the 252 overlap firms' 5,502 missing filings with the same stream code and parser
`b6_parse/2`, ≤ 5 requests/s, worktree-local, then re-census. Grounds: the hole is non-random (those firms
drop out of the ranking exactly in the quarters they were small caps), and filling it is a completeness
action taken before any T-265 return exists, so no outcome informs it. The freeze waits for it.

*Worker's operational definitions, fixed here before the fill (the A1.10 precedent; for the director's
check; they alter no ruled term):*
- **The 252 firms** = T-265 priced CIKs that the stream skipped because they are in the S&P fetch list
  (`data/b6_local/sp_fetch_list.parquet`) AND that have at least one 10-K/10-Q accepted from 2015-01-01 in
  the cached S&P candidate list (`sp_candidate_filings.parquet`, cached 2026-11-11) that the S&P fetch list
  does not contain. Deterministic from those two files (code: `b6_census.overlap_gap_ciks`); re-derived at
  this commit: 252 CIKs, 5,502 missing accessions, 11,047 candidate filings from 2015 in total.
- **Each of the 252 is streamed over its FULL 2015+ history** through the unchanged `process_cik`, not
  only the 5,502 missing accessions: pairing is within company, and a filing whose prior lies outside the
  S&P fetch window can be paired only if that prior is fetched too. For these 252 firms every T-265 text
  row then comes from the stream; their S&P-panel rows are not mixed in (one fetch per firm). The other
  392 overlap firms keep their S&P-panel text (all their 2015+ candidate filings are in it).
- **Condition (a) of ruling 3 is measured as follows.** Fetch: 0 CIK-level errors left after one
  `--retry-errors` pass, and filing-level fetch failures ≤ 1% of the filings the fill streams. Rates: per
  form, the six rates of the census table — Risk OK, Risk OK excluding not-covered, MD&A OK (acceptance
  from 2015); combo pair, MD&A pair, adjacent MD&A pair (10-Q) (acceptance from 2016) — computed on ALL
  filings the fill streams for the 252, each within **3.0 percentage points, two-sided as written**, of the
  same rate on the 4,099 streamed CIKs (the T-265 panel's own). The 5,502-accession subset is reported
  beside it and is not a condition.

### A7.2 Ruling 2 — the rebalance grid is the S&P harness's, not a new one
The director: H_OOS was ratified (A6.1) as the IDENTICAL construction that produced the S&P statistic, and
the gate arm follows §6–§7; read the S&P harness's rebalance-date rule and use exactly that rule on T-265;
if it is not calendar quarter-ends, re-run the per-rebalance census counts on that grid and report the
difference. Do not choose a grid.

**The rule, read from the code** (`scripts/lazy_prices/b6_harness_sp.py`, `rebalance_dates`, and
`load_inputs`/`main`): rebalance t = **the last bar of the SPY TR twin calendar**
(`data/processed/tr_reconciled/SPY_1d.csv`) **on or before each calendar quarter-end**
(`pd.date_range(start, end, freq="QE")`); the last holding period ends at the last bar on or before
2026-03-31; a filing is usable at t if `decision_floor_date` ≤ t and its acceptance date is later than
t − 6 months (`signals_at`). This is §6's "last trading day of each calendar quarter". **It is NOT calendar
quarter-ends:** the `6e52752` census evaluated eligibility at the calendar quarter-end date itself (e.g.
Saturday 2016-12-31 instead of Friday 2016-12-30). The per-rebalance counts are re-run on the harness grid
(reading the SPY twin's bar DATES only) and the difference is reported at the freeze. The T-265 harness
imports the S&P harness's `rebalance_dates` and `month_marks` — one code path, no new grid.

### A7.3 Ruling 3 — freeze and build: pre-authorized on conditions
After the gap fill and re-census, IF all of the following hold, the worker commits AMENDMENT 8 = the
T-265 FREEZE (alone), then builds the T-265 harness and runs it without stopping:
- (a) the 252 firms' filings are fetched with ≤ 1% failures and their parse and pairing rates are within
  3 percentage points of the T-265 panel's own (measured as A7.1 fixes);
- (b) no text-side census halt fires;
- (c) the window is still 40 rebalances 2016-Q1 → 2025-Q4 on the S&P harness's grid;
- (d) nothing departs from amendments 5–7 except what amendment 8 names.

If ANY condition fails, the worker stops and hands back instead. The harness then: the price join from
the sources B-2's census names (re-read from that census, not from memory); the ADV band; the §7.7 floors
checked AFTER the band (halt closed if short — no lowering a gate after it fires); the gate arm and H_OOS
exactly as frozen; a smoke on the FIRST 12 months only (no number quoted); the run twice to identical
md5s; the verdict with the power statement in its first paragraph; the full suite;
`python scripts/sync_docs.py`; the CLI into `docs/Core/execution_manual.md`.

*Worker's reading of (b), fixed here:* the text-side halts are §7.7's first bullet (the LM file md5 against
its manifest; every T-265 signal file present with its recorded row count — the freeze records the file
list, rows and md5s and the harness verifies them), 0 transient CIK errors left, and every rebalance's
text-side upper bound (gate-usable names before the ADV band) at or above §7.7's 300 ranked and 3 × 40
per tercile. The ADV-band floors themselves are price-side and are checked in the harness, after the band.

### A7.4 Ruling 4 — trials
The T-265 arm consumes **+2** (the gate family +1; H_OOS +1, its own family per A6.2). The director records
it on main when amendment 8 lands; the worker does not touch `config/honest_n_trials.json`. The count is
stated in the freeze text.

### A7.5 Ruling 5 — disclosures carried into the verdict
- 3.1% of small-cap 10-Ks omit Item 1A (smaller reporting companies — the smallest firms): no combo pair,
  so they cannot be gate-ranked on 10-K quarters.
- The one out-of-window fetch failure (HTTP 503; CIK 1837254, 10-Q 0001213900-26-057934, accepted
  2026-05-15).
- The census's text-side counts are upper bounds before the ADV band.

### A7.6 The SEC contact
Since 2026-11-14 a privacy control in this environment refuses commands that read or send the account's
email, including scripts that hold it. The fill is tried exactly as before. If the permission layer
refuses ANY step, the worker does not work around it (no copying the string, no new constant, no alternate
script): it adds a minimal change so the stream reads its User-Agent from the environment variable
`B6_SEC_USER_AGENT` and refuses with a clear message and exit 3 when it is unset (tests for both;
committed), then stops and hands back the exact command the user must run from the worktree. The address
is never written anywhere.

---

## AMENDMENT 8 — director ruling on the failed condition (a): ONE population-controlled check, two-sided at 3.0 pp (2026-11-17; BINDING; PRE-DATA for the T-265 arm). Appended; nothing above is edited.

Committed alone, BEFORE any conditional count is computed, and before any T-265 price join, ranking or
return. **What exists for T-265 at this commit:** the stream's per-filing text signals and statuses for the
4,099 streamed CIKs and the 252 AMENDMENT-7 fill CIKs (`data/b6_local/t265_signals/`, `b6_parse/2`), the
re-census of commit `ba1140d`'s tree (counts only), and the T-265 harness code (`43ab4bf`, `8b43a08`,
`ba1140d`), which has run on synthetic data only. No T-265 small-cap price has been read.

### A8.1 Condition (a) as written FAILED — on 5 of 11 rates, all on the HIGH side
The fill itself is complete: 252 of 252 CIKs, 11,195 filings, 0 fetch failures, 0 CIK-level errors after
one `--retry-errors` pass, every one of the 5,510 gap accessions fetched. The rates, as A7.1 fixed them
(`data/b6_local/census/t265_fill_check.csv`, md5 `57d6cc6d76e13ace5ec25ee52ac6d8af`; "panel" = the 4,099
streamed CIKs):

| form | rate | panel | fill | difference (pp) | within 3 pp |
|---|---|---|---|---|---|
| 10-K | Risk OK | 95.7 | 98.3 | +2.6 | yes |
| 10-K | Risk OK excl. not-covered | 98.8 | 98.3 | −0.5 | yes |
| 10-K | MD&A OK | 98.7 | 98.9 | +0.2 | yes |
| 10-K | combo pair (from 2016) | 87.9 | 95.4 | +7.5 | **no** |
| 10-K | MD&A pair (from 2016) | 92.0 | 96.8 | +4.8 | **no** |
| 10-Q | Risk OK | 90.4 | 93.8 | +3.4 | **no** |
| 10-Q | Risk OK excl. not-covered | 97.2 | 97.9 | +0.7 | yes |
| 10-Q | MD&A OK | 99.8 | 99.6 | −0.2 | yes |
| 10-Q | combo pair (from 2016) | 82.6 | 90.5 | +7.9 | **no** |
| 10-Q | MD&A pair (from 2016) | 93.2 | 97.3 | +4.1 | **no** |
| 10-Q | adjacent MD&A pair (from 2016) | 97.6 | 98.7 | +1.1 | yes |

The director rejected both readings the worker offered: a one-sided reading rewrites a tolerance after
seeing which side the data fell on; a carve-rates-only reading drops four of the named rates. The worker's
decomposition (no prior to pair with; Item 1A omitted) is a HYPOTHESIS until computed. It is tested by ONE
pre-written check (A8.3). No pairing rate carries outcome information, so one pre-written check does not
leak; it is one check, not a series of slices.

### A8.2 The failure-reason decomposition — COUNTS per form, panel vs fill (status columns only; no signal value read)
The code (`b6_signals.pair_signals`) emits exactly five values for a YoY pair: `ok`, `no_prior`,
`current_not_ok`, `prior_not_ok`, `mda_source_switch`. It emits no separate "not covered" pair code: a
filing whose Item 1A is NOT_COVERED yields `current_not_ok` (or `prior_not_ok`) for the combo; the
filing-level Item 1A statuses are listed after the pair tables. Filings accepted from 2016,
de-duplicated on (cik, accession):

| 10-K `yoy_combo_why` | panel | fill | | 10-K `yoy_mda_why` | panel | fill |
|---|---|---|---|---|---|---|
| ok | 27,628 | 2,450 | | ok | 28,911 | 2,486 |
| no_prior | 1,958 | 39 | | no_prior | 1,958 | 39 |
| current_not_ok | 1,434 | 60 | | current_not_ok | 384 | 27 |
| prior_not_ok | 293 | 8 | | prior_not_ok | 60 | 5 |
| mda_source_switch | 103 | 12 | | mda_source_switch | 103 | 12 |
| total | 31,416 | 2,569 | | total | 31,416 | 2,569 |

| 10-Q `yoy_combo_why` | panel | fill | | 10-Q `yoy_mda_why` | panel | fill |
|---|---|---|---|---|---|---|
| ok | 79,169 | 7,014 | | ok | 89,297 | 7,546 |
| no_prior | 5,967 | 125 | | no_prior | 5,967 | 125 |
| current_not_ok | 8,371 | 451 | | current_not_ok | 138 | 33 |
| prior_not_ok | 1,949 | 116 | | prior_not_ok | 54 | 2 |
| mda_source_switch | 396 | 46 | | mda_source_switch | 396 | 46 |
| total | 95,852 | 7,752 | | total | 95,852 | 7,752 |

Item 1A status of the filing itself (accepted from 2015; the parse-rate population):

| 10-K `risk_status` | panel | fill | | 10-Q `risk_status` | panel | fill |
|---|---|---|---|---|---|---|
| OK | 32,133 | 2,740 | | OK | 92,635 | 7,885 |
| NOT_COVERED:not_required | 1,008 | 0 | | NOT_COVERED:item_absent | 5,121 | 331 |
| NOT_COVERED:incorporated_by_reference | 33 | 1 | | NOT_COVERED:not_required | 1,971 | 26 |
| NOT_LOCATED | 234 | 19 | | NOT_LOCATED | 1,441 | 50 |
| NOT_LOCATED:unterminated | 5 | 0 | | NOT_LOCATED:unterminated | 209 | 4 |
| TOO_SHORT | 150 | 27 | | TOO_SHORT | 1,057 | 112 |
| | | | | CONTAMINATED | 2 | 0 |
| | | | | FETCH_FAILED | 1 | 0 |
| total | 33,563 | 2,787 | | total | 102,437 | 8,408 |

### A8.3 The check — word for word as implemented (`b6_census.fill_population_check`)
For each of the four failed pair rates — 10-K combo (`yoy_combo_why`), 10-K MD&A pair (`yoy_mda_why`),
10-Q combo (`yoy_combo_why`), 10-Q MD&A pair (`yoy_mda_why`) — on signal rows of that form accepted from
2016 (`acceptance_dt[:4] >= "2016"`), de-duplicated on (cik, accession), computed separately for the
fill (the 252 CIKs) and the panel (the 4,099 streamed CIKs):
- **numerator** = rows whose why value is `ok`;
- **denominator** = rows that satisfy (a), and, for the two combo rates only, also (b):
  - **(a)** the pairing rule's own prior exists in the CIK's fetched set: the row's `prior_accession` is
    not null. `prior_accession` is set by `b6_signals.company_signals` from `find_prior(f, i, 270, 460)`
    for a 10-K and `find_prior(f, i, 350, 380)` for a 10-Q, over every filing the stream recorded for that
    CIK (the code's definition, not re-specified). Equivalently, why ≠ `no_prior`.
  - **(b)** combo only: neither the current filing's `risk_status` nor the prior's (looked up by
    (cik, `prior_accession`) among the same CIK's rows) starts with `NOT_COVERED` — the census's own
    "not covered" definition, i.e. `NOT_COVERED:item_absent`, `NOT_COVERED:not_required`,
    `NOT_COVERED:incorporated_by_reference`. A prior that cannot be looked up HALTS the check.
- **Nothing else is excluded.** Every other failure stays in the denominator as a failure: `current_not_ok`
  or `prior_not_ok` from any other status (NOT_LOCATED, NOT_LOCATED:unterminated, TOO_SHORT,
  CONTAMINATED, FETCH_FAILED, an MD&A `NOT_COVERED:incorporated_by_reference_external`, anything else),
  and `mda_source_switch`.
- **rate** = 100 × numerator / denominator, rounded to 0.1; **difference** = fill − panel on the rounded
  rates, as `t265_fill_check` computes it.
- **10-Q Risk OK:** its population-controlled rate is the existing Risk OK excluding not-covered — panel
  97.2, fill 97.9, +0.7, within the band. Nothing new is computed for it.

**Pass rule:** all four conditioned pair rates within 3.0 pp, TWO-SIDED (|difference| ≤ 3.0), AND the seven
rates that already passed in A8.1 still pass, unchanged.
**Fail rule:** if ANY conditioned rate falls outside the band, condition (a) fails for good under this
ruling. No freeze; the worker hands back with the table. No second check, no further slicing.

### A8.4 Sequence
If the check passes: the conditioned table is written as a census file and committed (the table in the
commit; `data/` is gitignored, so the CSV's md5 is recorded with it), then **the freeze becomes
AMENDMENT 9; A7.3's other terms are unchanged, with "amendment 8" read as "amendment 9".** The director
ratifies, for AMENDMENT 9, the construction choices (1)–(7) of the worker's hand-back of 2026-11-17 as
written. N_trials: **+2** at the T-265 run (the gate family +1, H_OOS +1), recorded by the director on main
against AMENDMENT 9's hash; `config/honest_n_trials.json` is not touched here.

*Erratum to A7.1 (text only):* A7.1's "5,502 missing accessions" was the accession-only count; keyed on
(cik, accession), as `overlap_gap_accessions` computes it, the gap is **5,510** (8 co-registrant
accessions fetched under another CIK in the S&P panel); still 252 CIKs, all 5,510 fetched.

**A8 erratum (text only; committed alone, BEFORE the check's result was computed or seen).** A8.1's table has
**six** passing rates, not seven: 11 rates − 5 failed. The implementation of A8.3's pass rule halted on
that count (it asserted seven passing rows and found six) before printing or writing any conditioned rate.
"The seven rates" in the pass rule are the seven rates other than the four pair rates, with **10-Q Risk OK
read through its population-controlled rate**, the existing Risk OK excluding not-covered (panel 97.2,
fill 97.9, +0.7), as A8.3's own 10-Q Risk OK bullet and the director's ruling state. Concretely: 10-K Risk
OK (+2.6), 10-K Risk OK excl. not-covered (−0.5), 10-K MD&A OK (+0.2), 10-Q Risk OK via excl. not-covered
(+0.7), 10-Q Risk OK excl. not-covered (+0.7), 10-Q MD&A OK (−0.2), 10-Q adjacent MD&A pair (+1.1) —
each unchanged from A8.1. Nothing else in A8 changes.

---

## AMENDMENT 9 — the T-265 FREEZE (worker, 2026-11-17, under A7.3 as amended by A8; BINDING; PRE-DATA for the T-265 arm). Appended; nothing above is edited.

Committed alone (with its file list, below), after AMENDMENT 8's check PASSED (`d018f15`) and BEFORE any
T-265 small-cap price is read, any ranking is formed or any return is computed. The T-265 harness has run on
synthetic data only.

### A9.1 The four conditions of A7.3 (A8 for (a)) — all hold
- **(a)** Fetch: 252/252 CIKs, 11,195 filings, 0 failures, 0 CIK errors after one retry pass. Rates: under
  AMENDMENT 8's ONE population-controlled check, the four pair rates are within the two-sided 3.0 pp band —
  10-K combo 97.0 vs 96.9 (−0.1), 10-K MD&A 98.1 vs 98.3 (+0.2), 10-Q combo 96.2 vs 96.9 (+0.7), 10-Q
  MD&A 99.3 vs 98.9 (−0.4) (panel vs fill; `t265_fill_population_check.csv`, md5
  `4b65d2b58bdf61ff6291a29d6353f993`); the seven other rates pass unchanged (A8 erratum).
- **(b)** No text-side halt (`t265_text_halts.csv`): LM md5 file = manifest = frozen; 0 transient CIK
  errors; every rebalance's text upper bound ≥ 300 (min gate-usable 2,399; min H_OOS-usable 2,529) and
  ≥ 3 × 40 per tercile (min 799).
- **(c)** 40 rebalances, 2016-03-31 → 2025-12-31, on the S&P harness's grid; the last holding ends at the
  last SPY TR bar on or before 2026-03-31.
- **(d)** Nothing departs from AMENDMENTS 5–8 except what A9.3 names.

### A9.2 The frozen inputs and code
- **Text:** `data/b6_local/t265_signals/` — **1,317 files**: 412 `signals_*` (136,000 rows) + 27
  `signals_fill_*` (11,195), 412 `filings_*` (136,000) + 27 `filings_fill_*` (11,195), 412 `done_*` (4,100)
  + 27 `done_fill_*` (252); and `data/b6_local/signals_sp_v2.parquet` (46,040 rows, md5
  `722b413770edfa9cb99d0da341308b22`) for the 392 overlap CIKs the stream did not take. Every file's rows
  and md5 are in the freeze manifest `data/b6_local/t265_freeze_manifest.json`, committed byte-identical
  beside this prereg as `docs/Sources/prereg_b6_t265_freeze_manifest_2026-11-17.json` (md5
  `ea078498dd6ddb68569d389b3f875fc1`). The harness HALTS if any file is added, missing or changed (§7.7).
- **LM dictionary:** md5 `12dade0123e1d096c1d1192c755f08a3`. **Parser:** `b6_parse/2`.
- **Universe:** 4,743 T-265 priced CIKs = 4,099 streamed + 252 filled + 392 from the S&P panel.
- **Code:** `scripts/lazy_prices/b6_harness_t265.py` as of `ba1140d` (md5
  `ae76834b3f36e81fd9dbc2757f73a2b3`); `scripts/smallcap_t265_b2_common.py` byte-identical to main (blob
  `8ce8224e1fce734e80639827554dad7f52650a5b`); the S&P harness's `rebalance_dates`, `month_marks`,
  `signals_at`, `rank_terciles`, `summarize`, `boot`, `newey_west_t` imported unchanged.

### A9.3 The construction — the director's ratified choices (1)–(7), plus the harness's frozen terms
1. **Identity:** a T-265 priced CIK maps to exactly one priced ticker (checked; HALT otherwise). A ticker
   shared by more than one CIK (66 tickers, 135 CIKs) or reused (its file splits into more than one
   segment) is usable for a CIK at t only when the date-aware Form 3/4/5 holder set at t (first − 90 d ≤ t
   ≤ last + 90 d) is exactly {that CIK} — AMENDMENT 4's rule. A name that cannot be attributed is left out
   of that quarter's ranking and counted (`identity_unresolved`). The security at t is the segment alive
   at t.
2. **B-2's trading and band rules:** a traded bar ON t; 20-day median dollar ADV at t in [$1M, $200M).
3. **B-2's death rule:** at a segment's last traded bar — BASE −30% (gate), STRESS −100%, LAST-PRICE 0 —
   including a death on the formation day; proceeds in BIL TR. B-2's price census and A1.2 recount
   (151 / 141) are re-measured and HALT on mismatch.
4. **No ADV cap** (B-6's prereg has none).
5. **H_OOS:** spec `hoos_adjacent` = the S&P `q10_adjacent` construction, GROSS, under the gate's
   inclusion and BASE death rules; mean(changers − universe) < 0 with t_HAC ≤ −2.0 (NW 3 lags). Its own
   panel meets the §7.7 floors or H_OOS is NOT EVALUABLE.
6. **The 10-Q-names-only companion** reads NOT-EVALUABLE in any quarter it cannot be formed and never
   affects H_OOS.
7. **LM uncertainty and litigious rankings are not run** (parity with the S&P arm).
- **Also frozen:** price source T-265 bars only (no `data/processed` fill); equal weight, buy-and-hold to
  the next rebalance, month-end marks; costs per side 35 / 75 bps by ADV bucket at t (exits at the leaving
  name's bucket, missing → 75; dead proceeds free), deducted in the leg's first month; flat 75 bps RT
  sensitivity; 25% long + 75% SPY TR satellite, Δ log wealth vs SPY TR, paired month-index block bootstrap
  (1,000, seed 0, auto block), H1 met if either signal's 1.25th-percentile `ci_low` > 0; the short-leg
  diagnostic on net legs; the §7.7 floors (≥ 300 ranked, ≥ 40 per tercile) AFTER the band, halting with
  no return and never lowered; diagnostics: flat 75 bps, STRESS, LAST-PRICE, SURVIVOR-ONLY, Jaccard,
  TF-IDF, risk only, MD&A only, 10-Q combo, 10-Q adjacent (net), 10-K only, 10-Q only, the IWM sleeve
  beside each — a diagnostic failing its own floors is recorded as halted; smoke on the first 12 months
  (never quoted); two runs to identical md5s before any number is quoted.

### A9.4 N_trials
**+2 at the T-265 run: the gate family {similarity, Δtone} +1, and H_OOS +1 (its own family, A6.2).** The
director records it on main against this amendment's hash.

### A9.5 Disclosures carried into the verdict
3.1% of small-cap 10-Ks omit Item 1A (no combo pair; cannot be gate-ranked on 10-K quarters); the one
out-of-window HTTP 503 (CIK 1837254, accepted 2026-05-15); the census's text counts are upper bounds
before the ADV band; the census correction (co-registrant rows keyed on (cik, accession)); B-2's
survivorship caveat verbatim — a PASS here is an UPPER BOUND.
