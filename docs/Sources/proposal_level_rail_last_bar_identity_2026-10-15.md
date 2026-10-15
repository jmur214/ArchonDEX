# Proposal: the writer's LEVEL rail — the cache's last bar must equal the true print (replaces a ratio band)

**For:** Agent R (review), then the director. **Owner:** Agent B. **Status:** PROPOSAL ONLY; nothing
built. Ruled to land BEFORE cutover day and ahead of any real-cache write (director, 2026-10-15). This
answers the declared level-ratio band, as it was asked for, with a sharper check that the data
supports.

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
`lift_verified` then checks at re-pin #2. SLE's write is refused anyway on identity grounds (reused
ticker, class (i)); its declaration exists so the ÷10 is on record.

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
