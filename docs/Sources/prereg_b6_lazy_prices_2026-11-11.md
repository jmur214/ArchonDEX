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
