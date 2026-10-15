# Proposal: the writer's LEVEL rail — the cache's last bar must equal the true print (replaces a ratio band)

**For:** Agent R (review), then the director. **Owner:** Agent B. **Status:** PROPOSAL ONLY; nothing
built. Ruled to land BEFORE cutover day and ahead of any real-cache write (director, 2026-10-15). This
answers the declared level-ratio band, as it was asked for, with a sharper check that the data
supports.
**Status, later the same day (B):** BUILT on `feature/level-rail-last-bar-identity`. R approved c750827;
the director HELD the merge when the full sweep (§8) found the split-window defect (§2's correction
note). The fix, db8c110 on `fix/level-rail-split-window`, is with R for re-approval by diff. §8 is the
full record under the corrected window.

## 0. The defect

`classify_overlap` accepts ANY constant ratio between the re-fetch and the cached tail as RESCALED. It
has no notion of size. On the copy, the write pass adopted 14 level changes of 2× to 18× under clean
records, and three of them are the ÷10 scale defects (R's read; the cutover proposal §2b). A band on
the ratio was the ruled remedy. Measured below, a band is both too loose and too coarse.

## 1. What a band would do, measured on the 475 written RESCALED files

- **R's fixed band [0.80, 1.10]** catches the 14. It misses **HON at 1.0399** and **SPGI at 0.9418**,
  both corporate actions (spin-off adjustments, recorded by the provider as split factors 0.9535 and
  1.057). A dividend rescale can never exceed 1, because dividends only scale the past down.
- **A time-aware band**, ratio ∈ [exp(−y_max·Δt), 1 + rounding] with Δt the time since the cache's
  last bar, flags 16 files at y_max = 10 %/yr: the 14, plus HON and SPGI. At 8 %/yr it also flags
  HST (a 0.92 special dividend) and PRGO (regular dividends on a fallen price), which are legitimate
  dividend rescales.
- Either way, a band only says "out of range"; it cannot say WHY. Every flagged file then needs a
  hand declaration, including the nine that are ordinary splits.

## 2. The proposed check: LEVEL IDENTITY at the cache's last bar

A total-return cache, written at its last bar, holds that day's TRUE PRINT. Every later corporate
action (a split, a dividend, a spin-off) rescales the past, but the cache's last bar was a real
closing price when it was written. The provider can reconstruct that print independently:

    true_print(d) = provider_unadjusted_close(d) × Π (split factors the provider records AFTER d)

(yfinance's `auto_adjust=False` close is split-adjusted, so the later splits are multiplied back in.)

> **Corrected 2026-10-15 (the formula above is kept as drafted; it is WRONG for a stale file).** The
> splits to multiply back are those after the file's ADJUSTMENT DATE W (`adjusted_as_of`, the date its
> writer fetched it), not those after its last bar d. A file written at W is already in the post-split
> basis for every split before W. For a fresh file d ≈ W and the two readings agree. For a stale file
> they do not: NVDA ends 2024-05-10, its 10:1 split was 2024-06-10, and the file was written in 2026-04
> split-adjusted. The drafted formula read it 0.0999 and would have refused it as a ÷10 defect at
> cutover; SMCI likewise. Found by the full sweep (§8) after R's approval of c750827; the merge was held
> and nothing landed. The built rule (db8c110):
>
>     reference(d) = provider_unadjusted_close(d) × Π (split factors the provider records AFTER W)
>     identity     = cache_close(d) / reference(d)
>     residual     = identity / Π over ex-dates in (d, W] of (1 − D / C_prev)
>
> The check is `|ln residual| ≤ 0.01`. The record field is `reference`, not `true_print`: with a split
> in (d, W], the cache's correct basis is not the historical print. The 22-file table below is
> unchanged by the correction (none of the 22 has a split in (d, W]).

**The check:** `cache_close(d_last) / true_print(d_last)` must be 1, to within a dividend-sized
tolerance. If it holds, the cached LEVEL is right, and any constant overlap ratio is fully explained by
the provider's own actions since d_last. The write proceeds, recording the identity. If it fails, the
cached level is wrong, and the writer REFUSES unless a per-name declaration matches.

**Measured on 22 files** (the 16 band-flagged, plus XOM, AAPL, HST, PRGO, JNJ and BRK.B), against the
REAL canonical cache (read-only):

| cache / true print | files |
|---|---|
| **1.0000** | CTVA, CVNA, CRWD, MNST, AIV, FDX, SPGI, HON, DD, POM, XOM, AAPL, HST, PRGO, JNJ, BRK.B: every split, spin-off, special distribution and reverse split explained, with no declaration |
| 0.9970, 0.9947 | KLAC, APH: dividend-sized residuals. Both files END early (KLAC 2025-10-10, APH 2025-08-01: stale files, a separate fact), so dividends paid after their last bar but before their fetch scaled that bar |
| **0.1000 exactly** | **AZO, MTD, NVR, and SLE** |

**SLE is a FOURTH ÷10 file.** R's read classed it only as a reused ticker (Sara Lee left the index;
the cached SLE from 2019-02-26 is the reused entity). The identity shows it is also exactly one tenth
of its true print. It has **no PIT membership interval**, so PIT universes never reach it; a static or
cache-wide universe can.

**Tolerance, proposed:** |ln(cache / print)| ≤ 0.01. The measured legitimate cases sit within 0.0053
(APH); the scale defects sit at ln 10 = 2.30. That is a clean separation, a factor of about 400.
*(Superseded by the full record, §8: the 0.0053 is APH's identity BEFORE the dividend factor; the rail
tests the residual after it, where APH reads 0.0000. Across 651 files the largest legitimate residual is
0.0087 (CVS), and its cause is the LEGACY adjustment date, not provider noise. The margin to the
tolerance is 0.0013.)*

## 3. Declarations: only where the identity fails

`config/level_declarations.json`, a referee config. Each entry is per name: `kind` (`scale_defect` /
`identity` / …), `declared_ratio`, `source` (the evidence), `date`, `declared_by`. The writer, on an
identity failure:
- REFUSES if no declaration exists;
- REFUSES if one exists but |ln((cache/print) × declared_ratio)| > the tolerance;
- WRITES the provider's true level if the declaration matches, recording `level_declared: <kind,
  ratio, source>` in the write record.

**The first declaration set** is the four ÷10 files, kind `scale_defect`, declared_ratio 10.0, source
"the old loader's ÷10 fired on the Alpaca leg at the T-082b merge (R's read; B's identity
measurement)". For AZO, MTD and NVR this write IS the restoration. It is what the ticker exclusion's
`lift_verified` then checks at re-pin #2. **SLE is NOT covered by a declaration's write.** *(This
sentence first said SLE's write is "refused anyway on identity grounds". That was false: the write
pass WROTE SLE, RESCALED at 10.0, because its file IS the reused entity, so the span and the overlap
both pass. R's read, 2026-10-15.)* A matching `scale_defect` declaration would write Super League at
×10 under Sara Lee's symbol, and `lift_verified` would lift its exclusion. So SLE, with POM, is class
(i) in the cutover proposal's reused-ticker table, refused forever. Its `scale_defect` record exists
only so the ÷10 is on file, never as a license to write.

**R's other ten need NO declaration:** the identity explains them all.

## 4. Census: both producers

A run on a substrate written under declarations should carry them, because the declared names are the
list whose price-LEVEL verdicts need a dated caveat (director). **Proposed key:** `level_declarations`,
listing each declared name in the run's resolved universe with its kind, ratio and write date. It is
read from the substrate's write log, and written by `_build_census` and `candidate_census_block`
under the two-producer lock (`CENSUS_PROVENANCE_KEYS`). An errored record fails the census, as
`data_exclusions` and `ticker_exclusions` do.

## 5. Locks (reversion-proven; each drives `full_refetch` on planted files)

1. A cache whose last bar is 1/10 of the planted true print, with a provider on the right convention
   → **REFUSED** (today it is written RESCALED at 10.0; this is the reproduction).
2. The same, with a matching `scale_defect` declaration → **WRITTEN** at the true level, with the
   declaration in the record.
3. A declaration whose ratio does not match → **REFUSED**.
4. A legitimate split after the cache's last bar (planted provider splits) → identity holds →
   **WRITTEN** with no declaration.
   *(Corrected 2026-10-15: this lock only ever placed its split after W, so it could not tell "after
   d" from "after W", and the review and every reversion passed the defect. The built locks plant a
   split in EVERY interval the formula distinguishes, each with the cache in the basis a file written
   at W would have (R's rule): after W (pinned to a W before its split); in (d, W], both with a pinned
   record and through the LEGACY path (the NVDA shape); before d; and a dividend and a split both in
   (d, W]. Reverting only the split window fails exactly the three (d, W] locks.)*
5. A dividend residual within the tolerance → written; one just outside → refused (the boundary).
6. Both census producers write `level_declarations` (the contract), and an errored record fails.

## 6. What it costs and what it does not cover

- **Cost:** one extra provider read per file, the unadjusted close around d_last plus the split
  record (`yf.Ticker(t).splits`). The two-mode fetch already reads unadjusted bars; this reads one
  more date.
- **Not covered:** a reused ticker whose cached file IS the reused entity (POM reads 1.0000). The
  level is right, but it is the wrong company for the PIT name. That is the identity rail's question
  (the membership mapping), not the level rail's. Named for the cutover's class (i).
- **Provider dependence:** the true print comes from the same provider's unadjusted series and split
  record. An error in that record would pass. On the 22 measured files, the provider's splits matched
  every documented action.

## 7. For R and the director

1. **Adopt the last-bar identity in place of a ratio band?** Recommended: it explains R's 14 instead
   of flagging them, and it found the fourth ÷10 file.
2. **SLE:** add it to the ticker exclusion (a24bc20 is with R; a follow-up commit on that branch), or
   leave it as an identity-class refusal, since no PIT universe reaches it? Recommended: add it. A
   static or cache-wide universe can reach it, and the census should name it.
3. **The tolerance:** 0.01 in log terms (proposed).
4. **KLAC and APH end early** (2025-10-10, 2025-08-01). Those are live S&P names whose cache files
   stopped updating months before the common end. A staleness finding for the cache, for its owner.

## 8. The full record: every fetchable file (R's condition (a); re-pin #1's level record), 2026-10-15

**What was read.** Every file the measure pass could fetch (651), plus BRK.B and BF.B through the
shared symbol table: 654 files. Per file, the provider's unadjusted close at the REAL cache's last bar d
(the real cache opened read-only), the provider's split and dividend record, and the rail's arithmetic
under the corrected window (§2's correction note) with W = the LEGACY adjustment date 2026-04-25. These
are the provider reads the cutover's write pass will make. Artifacts, outside the repo in
`Dev/_substrate_candidates/`:
- `identity_652_2026-10-15.jsonl`, the sweep under the drafted window, md5 `5ee14203…`;
- `identity_652_2026-10-15_fixed.jsonl`, recomputed under the corrected window, md5 `263e885c…`;
- the two scripts beside them.

| result | files |
|---|---|
| no provider bar on or before d | **3**: BBBY, NFX, PSKY. The provider's series under those symbols starts 2026-07-17, 2026-07-07 and 2026-07-29: later entities on reused tickers (the cutover proposal's class (i)) |
| identity 1 to within 1e-6 | **616** |
| identity explained by the dividend factor over (d, W] (residual within the tolerance) | **30** |
| **over the 0.01 tolerance** | **5, exactly the declared and class (i) names:** AZO, MTD, NVR (`scale_defect`, declared ×10), SLE (0.1000; `reused_ticker`, never written), CPWR (2.0; a reused ticker, already refused DIFFERENT_CONVENTION by the write pass) |

The median |ln residual| is 0 and the p99 is 0.0061. **All 55 stale files are explained.** The
correction changed exactly two files, both splits in (d, W]: NVDA (identity 0.0999 → 0.9994, residual
1.0000) and SMCI (0.1000 → 1.0000). The eleven files with a split after W (APH, CRWD, CTVA, CVNA, DD,
FDX, HON, KLAC, MNST, POM, SPGI) read the same under both windows.

**Finding: the LEGACY adjustment date is an upper bound, not the write date.** The legacy cache was not
fetched at one time:
- DELL (last bar 2026-02-26, stale) carries its 2026-04-21 ex-date, so it was fetched on or after
  04-21.
- CAT (2026-03-30) and ZTS (2026-04-17) do NOT carry their 2026-04-20 ex-dates, so they were fetched
  before 04-20.

The file mtimes cannot settle it: all read 2026-05-23, a later copy.

So no single legacy W fits every file. Under W = 2026-04-25, a file fetched earlier is charged for
dividends its writer never saw. Its residual equals that unapplied dividend:

| file | last bar | unapplied ex-date | ln residual |
|---|---|---|---|
| CAT | 2026-03-30 | 2026-04-20 | +0.0019 |
| ZTS | 2026-04-17 | 2026-04-20 | +0.0043 |
| LOW | 2026-04-17 | 2026-04-22 | +0.0048 |
| PG | 2026-04-17 | 2026-04-24 | +0.0075 |
| CVS | 2026-04-17 | 2026-04-23 | +0.0087 |

All five sit inside the tolerance, so **none is falsely refused**. What makes this a measurement, not a
hope: the legacy set is CLOSED. Every new write pins its own record with its true W, so no file can
become legacy after today. The cutover's write pass reads the same provider record against the same
fixed (d, W]. This table therefore IS the cutover-day result, unless the provider revises its history.
A revision would surface as a refusal naming LEVEL IDENTITY (fail-closed and visible), never as a
silent write.

**The margin is thin, and that is stated, not tuned:** 0.0013 between CVS and the tolerance. A quarterly
dividend of 1% or more with an ex-date in the gap would have been refused. The tolerance is not moved
for it; a refusal would be the correct, visible outcome, resolved by a declaration with its evidence.
The splits have the same exposure in principle, since a split in (true W, 04-25] would read as its
ratio. The record shows none: the over-tolerance set is exactly the five above.

**For R:**
- (i) Accept LEGACY W = 2026-04-25 with this record as its proof on the closed set?
  Recommended: yes. The alternative, a per-cohort W, has no source: the mtimes are a copy's, and a
  stale file's d says nothing about when it was fetched.
- (ii) The cutover-day write log should quote these five residuals beside its own, so a provider
  revision between now and then is a visible diff.

**RULED (R, ratified by the director, 2026-10-15): LEGACY W = 2026-04-25 is ACCEPTED, with this
record as its proof on the closed set, on three grounds:**
- the set is closed, because every new write pins its true W;
- the exposure is bounded by the data, because any legacy file with an ex-date between its true
  fetch date and 04-25 large enough to breach 0.01 would already sit in the over-tolerance set,
  and that set is exactly the declared five;
- the affected files are named with their ex-dates and residuals: CAT +0.0019, ZTS +0.0043,
  LOW +0.0048, PG +0.0075, CVS +0.0087, all inside 0.01, the margin 0.0013 stated, not tuned.

So it is a measurement, not a bound. NO per-file W is read off each file's own content (the last
ex-date it carries): that would give residual 1 for all five, but choosing the hypothesis that yields
the smaller residual is tuning under another name. (ii) is ruled yes: the cutover-day write log
quotes the five residuals (the cutover proposal §6).
