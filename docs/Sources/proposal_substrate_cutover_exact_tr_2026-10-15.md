# Proposal: cut the canonical substrate over from the T-082b drip to EXACT total return

**For:** Agent R (review), then the director, then **the USER**. A change of the canonical
substrate is the user's decision. **Status:** PROPOSAL ONLY. The drip stays canonical until the user
rules. Nothing in the real `data/processed/` has been written. **N_trials: 0.**

**Direction already ruled** (director, 2026-10-15): exact ex-date total return is the honest form of
the TOTAL RETURN convention. But it is a **planned cutover**, not a refresh. The convention guard
switches on **on cutover day, all files at once, never before**, because its
`RESCALED → full re-fetch` path would otherwise adopt exact total return file by file, leaving a mixed
universe.

**Evidence base:** the writer `engines/data_manager/tr_writer.py` (on main via `23a5ef7`; its two
fixes — one provider for the universe, and the overlap refusal — on
`feature/tr-writer-provider-and-overlap` @ `3618688`, with R), run against a copy of the cache at
`/Users/jacksonmurphy/Dev/_substrate_candidates/processed_exact_tr_2026-10-15/`:
- real cache aggregate md5 BEFORE: `8ead63bc2271b38fc7adf56a0aa2918c` (2,172 files);
- the measure-only inventory: `/Users/jacksonmurphy/Dev/_substrate_candidates/measure_2026-10-15.jsonl`
  (730 files; the first pass routed files by span, see §2a);
- the yfinance re-measure of the 172 files that pass routed to Alpaca:
  `/Users/jacksonmurphy/Dev/_substrate_candidates/measure_2026-10-15_yfinance172.jsonl`.

---

## 1. Finding one: the cutover changes per-name RETURNS — as DISPERSION across names, not a systematic shift

T-082b's `apply_dividend_strip` gave pre-seam history a smooth constant-yield drip. Replacing it with
exact ex-date total return does not just move price levels: it moves each name's pre-seam RETURN.
Measured as exact minus drip, annualised log return from the file's start to its seam, over the 542
files with a pre-seam span that the first pass fetched from yfinance:

| percentile | p1 | p5 | p10 | p25 | **median** | p75 | p90 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|---|
| exact − drip, %/yr | −3.24 | −1.88 | −1.33 | −0.66 | **−0.10** | +0.10 | +0.59 | +0.91 | +2.05 |

The median is near zero (mean −0.25%/yr; 37% of names positive), so the drip is **not** a systematic
under- or over-count across the universe. What the cutover adds is **dispersion**: 100 of the 542
names move by more than 1%/yr in one direction or the other. XOM's +1.98%/yr, the trial that first
surfaced the effect, sits at the 98.7th percentile, a tail rather than the typical name. *(This
section's first wording, "the drip under-counted dividends", generalised from that tail and is
withdrawn.)*

**Consequence: every pre-2018 equity-book number is still a RE-QUALIFICATION, not a relabel.**
Equity-book verdicts are cross-sectional (deciles, ranks, long/short spreads). A per-name return
shift reorders names, and that moves a cross-section even when the median shift is near zero.
*(Wording endorsed by R and adopted by the director, 2026-10-15.)* The yfinance re-measure of the 172
Alpaca-routed files extends n; the final distribution goes in §4.

## 2. Finding two: delisted names cannot be re-fetched, so a naive cutover splits the universe on SURVIVORSHIP

yfinance returns **nothing** for delisted tickers. The trial hit ABMD, ABS, ALXN and ANSS in its
first 64 files. Count: *(PENDING: the full measure pass)*.

A naive cutover would therefore move live names to exact total return and leave delisted names on the
drip. The survivorship-corrected universe would be split into two conventions **exactly along
survivor status**. Given finding one, that is not a cosmetic split: it converts the existing upward
survivorship bias into an upward bias whose SHAPE differs by survivor status.

**This proposal rules nothing on it.** The three candidate treatments, with their consequences:

| option | what it does | consequences |
|---|---|---|
| **(a) One convention everywhere: keep the drip, labelled universally** | No cutover of deep history until a delisted-capable total-return source exists. Every deep history is labelled "drip (constant-yield approximation)", everywhere. | Homogeneous and survivorship-consistent. **Knowingly keeps** the dividend under-count (finding one) in every pre-seam number, labelled rather than fixed. Post-seam is already exact. Cheapest; no re-qualification beyond the label. |
| **(b) Exact where available, drip where not, with a per-name convention field** | Live names cut over; delisted names stay on the drip. Each file carries a `convention` field (`exact_tr` / `drip`); the **census reads it**, and every equity-book measurement reports the split (share of names, share of weight, on each convention). | The most exact per name. The universe is **mixed by construction**, and the mix correlates with survivor status, so a long/short or cross-sectional result can partly reflect the convention split. That is visible because it is reported, but it is a confound. A census field becomes a referee change. |
| **(c) Buy a survivorship-complete total-return source** | Acquire a source that covers delisted names with exact total return (the B-1 prereg's re-verification clause already names this path). One provider, one convention, the whole universe. | The only option that is exact AND homogeneous. Costs money and is a new external dependency (a propose-first gate under CLAUDE.md), plus provider evaluation and a manifest of its own. Until it lands, (a) or (b) must hold. |

## 2a. The provider rule: ONE provider for the whole universe (C-1's per-span rule overturned by measurement)

The writer was first built to C-1's per-span rule: Alpaca (`adjustment="all"`) for files whose span
starts on or after 2016, and yfinance for deeper files. The first measure pass overturned it. The
project's Alpaca feed is IEX, and its daily history starts **2020-07-27**:

- of the 172 files the rule sent to Alpaca, **69 came back empty**;
- **69 of the 103** that returned could not cover the cached span (52 of them start exactly on
  2020-07-27);
- **99 of the 103** read DIFFERENT_CONVENTION against the cache, because an IEX tail is not the tape
  the cache was built from.

**Ruled (director, 2026-10-15; provisional until the yfinance re-measure confirms it):** one
provider for the whole universe, **yfinance**. The writer has no per-file route. The Alpaca writer
provider is archived (`Archive/data_engine/tr_writer_alpaca_provider_2026_10_15.py`), and a providers
map without yfinance is refused (`af97347`). The span check and the two-mode basis measure stay.

## 2b. Files the writer REFUSES, and what each class needs at cutover

The writer refuses to replace a file unless the re-fetch covers the cached span AND agrees with the
last 252 cached bars up to a rescale (`3618688`). Agent R reproduced the gap this closes: a split-only
provider's two modes are identical, so the basis measure reads "unverified" (exactly as for a
non-payer) and, unguarded, the writer replaced a total-return cache with a nominal series under a
clean write record. The window is a trading year because a 40-bar tail is blind to any payer whose
last ex-date is older than the window: inside it, a total-return tail and a split-only tail are
identical.

The branch writer was run measure-only (`write=False`) over the real copy, fed by the replay, with no
network. On 548 yfinance-fetched files, **529 would be written** (419 RESCALED, the steady state; 110
APPEND), and **19 were refused**. The copy's md5 was unchanged.

| class | files | why refused | treatment at cutover |
|---|---|---|---|
| **Split-only in the canonical cache** | **AGG, EFA, VNQ** | DIFFERENT_CONVENTION. One writer, `scripts/backfill_t052_macro_data.py`, wrote exactly these three with `auto_adjust=False`; the yfinance/cache ratio steps up at every ex-date | **Adopted:** a DECLARED split-only path. The declaration is verified against the provider's split-only mode, recorded, and only then is the file re-fetched over its whole span. Not built. |
| **(i) Ticker reuse — identity** | **BBBY, PSKY** | span: yfinance's history for the symbol starts in 2026-07, a different entity | **Refused forever.** The identity rail is the span check plus the DIFFERENT_CONVENTION refusal. These are never re-fetched under the reused symbol. |
| **(ii) Stitched identity** | **DAL** | span: cache from 1980, yfinance from 2007-05-03 (pre-2007 is old Delta) | **The user's decision:** declared truncation vs a declared seam. Note: the writer does not yet apply DAL's declared load-time exclusion (`dal_pre2007_excluded`) to the span it must cover. |
| **(iii) Stooq history deeper than yfinance** | **C** (+7 yr), **INTC** (+8), **JPM** (+10), **ELV** (+8), **MAR** (+4.5), **PLD** (+2), **AXP** and **WMT** (+5 months) | span | **The user's decision:** declared truncation (lose the oldest years) vs a declared seam (keep the drip before yfinance's first bar — a two-convention file, the T-082b class, but declared and census-recorded) |
| **(iv) Start-window leads, 9–34 days** | **CHTR, KDP, TDC, UAL, WU** | span: yfinance starts 9–34 days after the cache, past the 7-day slack (listing or emergence windows) | **The user's decision**, the same choice as (iii) at a much smaller scale |

**One-bar stubs.** RX (one bar, 2018-02-22) and SRCL (one bar, 2026-03-02, after the company's 2024
acquisition) are too short for any overlap (`OVERLAP_MIN_BARS` = 10), so the writer refuses them as
INSUFFICIENT whenever a fetch returns. A one-bar file is not a history to agree with. Both are
data-quality items in their own right, and SRCL's is likely an identity problem. A cache of 10–251
bars reads normally: a 252-bar slice of a shorter file is the whole file.

## 3. The re-pin list (every pinned artifact the cutover moves)

| artifact | why it moves |
|---|---|
| the backtester golden master | its fixture reads the processed closes |
| the 26-yr anchor `158fe678` | the canonical-window equity book |
| B-1's panel md5 `d9d449d17f8f` | built from the processed closes (R's lock 7: it must move VISIBLY) |
| `config/substrate_manifest.sha256` | exact-match verify of `data/processed/` |
| the exact-TR candidate's own manifest | pinned now, so the candidate is a fixed object |
| *(PENDING)* | any other pin whose inputs read `data/processed/`, enumerated by grep before the user's gate |

## 4. Measured deltas per file *(PENDING: the full measure-only pass)*

Per file: provider (yfinance throughout, after §2a; the first pass's span routing is superseded by the
re-measure for the 172 Alpaca-routed files), span coverage, measured basis, overlap class over the
last 252 cached bars, pre-seam and post-seam level ratio, and pre-seam and post-seam annualised return
delta. A distribution summary goes here; the full
per-file inventory is the jsonl above.

## 5. Per-verdict re-qualification plan under `[NN-SUBSTRATE-REVERIFY]`: first classification

**Scope authority:** `docs/Sources/referee_repair_proposal_RR-1_2026_09_30.md` §5, the verdict list
read row by row. The cutover's own test is different from RR-1's. **Does the verdict's evidence read
PRE-SEAM equity closes in `data/processed/`, or a dollar-ADV computed from them?** There are two
reasons a pre-seam number moves: §1's dividend under-count, and the item (d) dollar-ADV deflation
(`docs/Sources/scan_price_level_consumers_item_d_2026_10_15.md`).

| class | verdicts | cutover action |
|---|---|---|
| **Controller-produced (RR-1: UNTESTED under corrected sizing, 29)** | T-066, T-092, T-126, T-140, T-140-fu3, T-180; T-055c/d/e/g/h, T-057, T-057b, T-109, T-118-rerun, T-120, T-121, T-128r, T-154, T-162, T-174; T-041b, T-122, T-129, T-144, T-145, T-196, T-241; T-211 | **RE-RUN, once, on the post-cutover substrate** (see the sequencing below) |
| **Consumes a controller curve (2)** | T-170, T-206 | **RE-RUN** with their inputs |
| **B-1** (raw-signal deciles, PIT S&P 500 2000–2025, verdict 2026-10-14) | reads the processed closes across 2000–2018 pre-seam | **RE-RUN** on the cutover substrate. DAL is not a factor (masked; PIT from 2013) |
| **Mechanism, determinism, infra (RR-1: unaffected)** | T-038-CONT … T-218 (RR-1 §5) | **RE-LABEL**: the claims are invariant to prices. Determinism canon md5s **re-pin** and the claim is re-confirmed on the new substrate (bitwise N=5) |
| **T-306-substrate family** (sleeve T-255/T-311; tilts T-318/T-320; offense T-294/T-294b/T-298/T-312/T-315) | built from FF, DGS10 and LBMA data | **UNAFFECTED**: they read no `data/processed` equity closes |
| **ETF verdicts on `tr_reconciled/`** | already exact total return; untouched by this cutover | **UNAFFECTED** |
| **Independent harnesses on RAW Stooq files** (CONFIRMED from each script, 2026-10-15) | T-204 (`trend_overlay_validation_t204.py:35-37`: SPY/AGG/GLD from `data/raw/stooq/daily/us/nyse etfs/…`), T-213 (`industry_momentum_t213.py:25-30`: sector ETFs globbed from `data/raw/stooq/daily/us/**`), T-239 (`moonshot_rescore_t239.py:11`: `data/raw/stooq/daily/us/**/<t>.us.txt`) | **UNAFFECTED by this cutover**, which rewrites only `data/processed/`. Their basis is raw Stooq, split-only before about 2011 (R's per-era finding). That is T-256's known question, not a cutover one, and is noted here, not reopened |
| **RR-1's "needs a reviewer" (7)** | T-136, T-148, T-166, T-169, T-172, T-214, T-220 | inherit RR-1's resolution, then the same test |

**Sequencing (RULED 2026-10-15 by the director, for the user to override).** The 31 controller and consumer verdicts are
already slated for re-scoring under the corrected referee (RR-1/RR-5). The cutover changes their
substrate too. Re-scoring them on the drip substrate and again after the cutover would spend the
campaign twice and leave two incompatible sets of numbers. **Recommended: one re-run, on the
post-cutover substrate, after the referee repairs and the cutover both land**, with the RE-SCORE
labels carrying both reasons.

## 6. Sequence, if the user approves

1. The user's choice among (a), (b) and (c), and the user's choice for §2b classes (ii)–(iv):
   declared truncation vs a declared seam.
2. The write pass completes on the copy (HELD until `3618688` merges); the §2b declared paths run
   (split-only trio verified against the provider's split-only mode; the (ii)–(iv) declarations
   applied); the candidate manifest is pinned.
3. Re-qualification runs per §5.
4. Cutover day: the copy replaces the canonical substrate in one step; every §3 pin is re-pinned
   together; the guard switches on at every writer in the §4 inventory of the guard proposal, all at
   once. **A hard requirement of the switch-on commit (R's O-3):** the one live write path, an
   uncached ticker saved by `save_cache`, goes through `full_refetch` or is refused in canonical runs.
   Otherwise the first new ticker after cutover re-opens the basis mix.
5. First artifact: the next canonical run's census reports the convention, and, under (b), the split.
