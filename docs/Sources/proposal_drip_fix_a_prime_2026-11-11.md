# Proposal: option (a′) — repair the era-wrong pre-seam drip in the price cache (T-384)

**For:** the director, then **the USER**. A change to the canonical substrate is the user's decision
(`[NN-SUBSTRATE-REVERIFY]`). **Status:** CANDIDATE ON A COPY. Nothing in `data/processed/` has been
written. **N_trials: 0** (a substrate repair, not a strategy configuration).

**The defect being repaired:** `docs/State/health_check.md` HIGH of 2026-11-11 (main `d82f4b8`), "The
canonical price cache's pre-seam 'drip' is ERA-WRONG".

---

## §1. The acceptance test — PRE-DECLARED (committed alone, before the candidate was built)

This section was written and committed before any candidate file existed. The thresholds below
are not to be changed after the results are seen. If the candidate fails them, the failures are
reported as failures.

### 1.0 What was measured before this section was written (inputs to the thresholds, not results)

All of this was measured on the cache, the raw Stooq bundle and a yfinance reference cached under
`/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11/yf/`. No candidate file
existed at the time.

- **The merge input is the raw bundle, exactly.** For every name checked (MO, KO, XOM, AAPL, BBBY,
  STI, NBR, AAL, KG, VLTO, POM), `cache_pre × exp(−b·(t − seam))` divided by the raw Stooq close is
  constant to 7e-16 in log terms. The raw bundle ends 2026-05-22.
- **Per-ex-date probe (≈ 10,700 ex-dates, 105 names, extended to the universe for the build).** For
  each yfinance ex-date e, over the window e ± 1 trading day:
  `m = Σ(log adj − log stooq) / Σ(log adj − log close)`, where m = 0 means Stooq captured the
  dividend and m = 1 means Stooq missed it. The confident values (σ(m) ≤ 0.15) are bimodal: 5,280
  near 0, 3,267 near 1, and 26 between 0.25 and 0.75.
- **The global edges are single weeks, universe-wide.** Captured → missed between 2003-03-30 and
  2003-04-07. Missed → captured between 2011-02-20 and 2011-02-21. Captured → missed from
  2022-12-19.
- **Before 2003-04-01 the behaviour is per name, not global.** In 1990–2002, 8–32 % of the measured
  ex-dates each year are missed. Examples: BA missed 1980–1999, captured 1999-05 → 2001-02, then
  missed again from 2001-05. BAX and CI missed 1982–2000. MO, AA, CAT and AXP were captured until
  2001-01 and missed from 2001-04/05. AEP, APD, COP and CLX were captured from the 1970s/80s to
  2003-03. Before about 1988 the yfinance and Stooq daily data differ by 0.2–1 % a day (different
  vendor histories), so single-ex-date measurement is often impossible there.
- **Spin-offs inside a missed era are usually CAPTURED by Stooq.** Examples: MO/Kraft 2007-04-02
  (m = 0.00), MO/PM 2008-03-31, CAH 2009-09-01, AYI 2007-11-01. Special cash dividends follow the
  era: AIV 2008 and AN 1995 were missed. So a pure era rule would add a 25–69 % "dividend" Stooq
  already applied. The per-ex-date label prevents that.
- **Reference noise on name-years that are ALREADY exact.** These are 2000–2015 name-years in which
  every ex-date was measured as captured, or there was no dividend: 2,054 name-years, 304 names.
  |Stooq − yfinance TR| per year:

  | statistic | value |
  |---|---|
  | pooled median | 0.0037 pp |
  | pooled p95 | 0.039 pp |
  | non-payer years: median / p95 | 0.0006 / 0.027 pp |
  | payer years: median / p95 | 0.0062 / 0.082 pp |
  | per-year median, worst year (2000) | 0.0114 pp |
  | per-year p95, worst year (2013) | 0.280 pp |

  The p99 is 0.77 pp and the maximum 38.5 pp. Those tails are corporate actions the two vendors
  treat differently: EXPE 2011, LDOS 2013, KMB 2014, ELV 2004, BLDR 2009 and others.
- **The reference proven both ways, on SPY.** yfinance SPY Adj Close against the in-repo S&P 500
  total-return index (`data/processed/SP500TR_1d_pinned.parquet`), 2000–2015: the median annual gap
  is −0.084 pp, which is SPY's expense ratio, 0.0945 %. The range is −0.70 to +0.66 pp (year-end
  premium/discount). The same comparison with the price-only close gives −2.06 pp, which is SPY's
  yield. So the reference includes dividends, and in the right amount.

### 1.1 Populations

- **Pre-seam universe:** every `both` file in `_merge_meta.json` with `n_stooq_pre_seam > 0`
  (575 files).
- **Reference-backed:** a yfinance price history exists for the symbol (`yahoo_symbols` table),
  and for the calendar year in question it is the SAME security. That means the median |Δ daily
  log return vs Stooq| is ≤ 0.004 or the daily-return correlation is ≥ 0.95. Everything else is
  **no-reference**: delisted symbols, identity-invalid years, and years before the reference's
  first day.
- **Non-payer:** reference-backed, and yfinance lists no dividend with an ex-date before the seam.

### 1.2 The four tests

Let **x** = candidate annual log return − reference annual log return, in pp. It is measured on
the two series' common dates, from the last common date of year y−1 (or the first common date) to
the last common date of year y.

**(i) Against the T-265 panel (Alpaca `adjustment='all'`, `data/research/t265/prices/`).**
- Scope: every name in the pre-seam universe with a T-265 file, for every year from 2016 to the
  seam. This includes the **seam stub**, the stretch of the seam year that ends at the seam bar
  and therefore contains the splice return.
- Criterion, per name-year: |x| ≤ 0.05 pp + q.
- q = 100 · (0.005 / P_start + 0.005 / P_end) is the reference's own quantization floor: T-265
  closes are rounded to the cent. A test tighter than the reference's rounding would fail a
  perfect candidate.
- The strict count (|x| ≤ 0.05 pp with no floor) is reported next to it.
- **PASS iff every name-year passes.**

**(ii) Against yfinance Adj Close, 2000–2015.** This is a census, not a sample.
- Population, per year y: every reference-backed name whose pre-seam span covers the full year y
  (both endpoints on or after Dec 24, and y < the seam year), with a valid identity in y. Every
  yield level and sector is therefore included, and the strata are reported.
- Strata:
  - yield quintile: the quintile of the name's mean yfinance dividend log-yield over its valid
    2003–2010 years, or over 2000–2015 if it has none in 2003–2010;
  - GICS sector from `data/universe/sp500_membership.parquet`, with "unknown" where missing.
- Criteria, per year:
  - (a) median |x| ≤ **0.05 pp**;
  - (b) p95 |x| ≤ **0.30 pp**;
  - (c) median |x| ≤ **0.05 pp inside each yield quintile**, so the yield-proportional defect
    cannot hide behind the non-payers;
  - (d) at least 100 names, or the year is INSUFFICIENT, which counts as a FAIL.
- **PASS iff every year 2000–2015 passes (a)–(d).**
- Why these thresholds:
  - 0.05 pp is 4.4 × the worst single-year median of the already-exact population (0.0114) and
    about 30 × below the defect it must catch. In a missed-era year the cache's error is
    ≈ −yield, a median of about 1.5 pp for payers.
  - 0.30 pp is the worst single-year p95 of the already-exact population (0.280), rounded up to
    0.05. A lower p95 bar would fail years in which the candidate is untouched Stooq (2012–2015)
    on reference noise alone. A test has to be passable by the reference's own agreement with an
    exact series.
- Known limit, stated now: in 2003-04 → 2011-02 the dividends the candidate adds come from the
  same source as the reference. So (ii) tests the era labels, the per-ex-date arithmetic and the
  splice. It does NOT test the dividend AMOUNTS. Those are tested independently in two ways:
  - Stooq's own adjusted eras (2000-02 and 2011-22) agree with yfinance to a pooled median of
    0.0037 pp;
  - (i), against Alpaca, from 2016.

**(iii) Non-payers.**
- (a) candidate − raw Stooq annual log return: |x| < 1e-6 pp in every pre-seam year. The fix
  injects nothing into a non-payer.
- (b) every 2016→seam name-year passes (i)'s criterion.
- **PASS iff both hold for every non-payer.**

**(iv) Post-seam bytes.** For every written file:
- every post-seam row's Date, Open, High, Low, Close and Volume fields are byte-identical to the
  cache;
- ATR is byte-identical from the 15th post-seam row on, and PrevClose from the 2nd;
- every pre-seam row's Date and Volume fields are byte-identical, and the row count is unchanged.

The first 14 post-seam ATR values and the seam bar's PrevClose are functions of pre-seam bars and
change by construction. That is declared here, not discovered later. **PASS iff every file
passes.**

**Verdict: PASS iff (i), (ii), (iii) and (iv) all pass.** Every failing name-year is reported with
a cause class. The classes are:
- a corporate action the references treat differently, shown by T-265 and yfinance disagreeing
  with each other beyond the tolerance;
- identity;
- a partial adjustment (0.25 < m < 0.75);
- an unlabelled ex-date (global rule used);
- the splice;
- other.

A cause class explains a failure. It never excuses one.

### 1.3 The rules the candidate applies (declared before it is built)

1. **Undo the drip.** pre-seam OHLC × exp(−b·(t − seam)). If the result is not proportional to the
   raw Stooq bundle to within 1e-9 (log), REFUSE the file.
2. **Label every reference ex-date before the seam.**
   - MEASURED where σ(m) ≤ 0.15: missed iff m ≥ 0.5.
   - Otherwise from the nearest measured neighbours: both agree, or the only one present lies in
     the same global era block.
   - Otherwise the global edges: missed in [2003-04-01, 2011-02-21) and from 2022-12-19.
3. **Add each MISSED dividend in full**, as a back-adjustment factor 1 − D/P_prev on every earlier
   bar. D is the yfinance dividend; P_prev is the yfinance split-adjusted close on the previous
   common day; D/P is clipped at 0.95. Nothing is added for a captured ex-date.
4. **No-reference spans (delisted names, identity-invalid years, before the reference's first
   day).**
   - Inside a global missed era: a LABELLED approximation. Each bar carries a drift of Y(year) /
     bars-in-year, where Y is the cross-sectional MEDIAN annual dividend log-yield of the
     reference-backed universe that year, with non-payers counted as zero. The median minimises
     the expected absolute error when the name's own yield is unknown. Every file records its
     `approx_years`.
   - Before 2003-04-01: Stooq as-is, labelled **pre-2003 convention UNVERIFIED**. The measured
     majority there is "captured", but it is per name.
5. **ONE constant at the seam.** The pre-seam series is rescaled so that the Stooq seam-day return
   is kept, using the raw bundle's seam bar. If the raw bundle has no seam bar, the cache's
   seam-day return is kept and labelled.
6. **Post-seam text is copied, not rewritten** (test (iv) is also enforced at write time).
7. The candidate is written only outside the repository's data tree. Every file and every refusal
   is recorded.

### 1.4 Amendment to the CANDIDATE's rules after the v1 run (thresholds, populations and verdict NOT changed)

Written after the v1 run and before the v2 run. The v1 script is `f69b475`. Its evidence is kept
under `drip_fix_a_prime_2026_11_11/v1_evidence/`, with aggregate manifest md5
`10a8f55cb3c867bb428c38da291acbf4`.

**v1 result: FAIL.**
- (i) 1,771 of 1,830 name-years pass (59 fail, across 46 names).
- (ii) 15 of 16 years pass. 2013 fails with p95 0.71 pp against the 0.30 pp limit; its median,
  0.004, passes.
- (iii) 8 names are flagged.
- (iv) 575 of 575 pass.

The failures were traced to mechanisms. Three were defects in the candidate. Each change below
fixes one of them, and each is reversion-proven: undoing the change fails a planted test.

- **A1 — the probe was fooled by Stooq's TRANSIENT offsets.**
  - Raw Stooq contains blocks of bars that sit one dividend off the reference and revert days
    later. Measured since 1995: 4,517 such blocks over 414 names. The largest dates are
    2008-05-07 (214 names), 2009-01-23 (162), 2011-03-21 (102), the 2013 month-ends from June to
    November (about 85 names each), 2013-12-03 and 2013-12-19 → 2014-01-03, and 2015-03-12.
  - When a block reverts inside v1's ex-day ± 1 window, a CAPTURED dividend reads m ≈ 1. v1 then
    added it a second time. Examples: AEE 2013-12-09 (block 12-03 → 12-06), HD 2013-12-03,
    PEP 2013-09-04, TJX 2019 and HST 2017.
  - Change: a level-shift probe. It compares the median of 5 CLEAN bars on each side
    (≤ e−2 / ≥ e+1). Clean means outside a detected block: a jump > 0.25 % that a bar within 15
    undoes to within 15 %. σ(m) = noise × √10 / |y|.
  - Unchanged: σ(m) ≤ 0.15 for MEASURED, and m ≥ 0.5 for missed.
- **A2 — the approximation per bar** is Y(year) / business days in that year. v1 divided by the
  bars PRESENT, so CHTR's December 2009 stub received a whole year's yield in one month.
- **A3 — a stub of ≤ 45 calendar days before the reference's first bar is covered by the
  reference.** This is a vendor IPO or relisting date offset, not a missing source: BLDR, LYV and
  TDC by days, CHTR by 34 days. v1 approximated these stubs, which put a drift into non-payers.
- **Test code brought into line with §1's text. These are bugs, not rule changes.**
  - (iii)'s population is restricted to REFERENCE-BACKED non-payers, as §1.1 defines it. The v1
    code admitted BBBY, PSKY, SATS and POM, whose yfinance symbols now point to a different,
    recent security.
  - The cause classifier treated a missing diagnostic (NaN) as "m outside".
  - A descriptive sub-label inside the declared "other" and "splice" classes records whether a
    period endpoint sits inside a Stooq transient block.

**Not changed, and stated in advance:** the candidate does not repair Stooq's prices where Stooq
is already total return (§1.3). The 2013 year-end block (2013-12-19 → 2014-01-03, ≥ 12 names) sits
ON the 2013/2014 year-end endpoint. The cache and the candidate both inherit it. If (ii) 2013 still
fails because of it, that is reported as a FAIL.

**A second correction to A1, after the v2 run.** This is the last change. v3 is the candidate
whatever its result.
- v2 is commit `acb1e72`, evidence under `v2_evidence/`, manifest `244bcf07…`.
- **v2 result: FAIL.**
  - (i) 1,770 of 1,830 pass.
  - (ii) 2013 improved from p95 0.71 to 0.32, still above the 0.30 limit. 2000 and 2001
    REGRESSED, to p95 0.415 and 0.414.
  - (iii) 6 names fail, all through (i). Its part (a) passes for 110 of 110.
  - (iv) 575 of 575 pass.
- The 2000–01 regression came from my A1 implementation, not from the data. The 5-bar medians made
  σ(m) √(10/3) times larger than v1's. In the noisier 2000–01 data that turned measured labels
  into global-rule labels (CMI, AXP, RTX, PGR, EXC and others), and the global rule says
  "captured" before 2003-04.
- **v3** keeps v1's window, the 3 daily returns around the ex-date, and only moves an endpoint
  outward when it sits inside a detected block: PRE is the nearest clean bar ≤ e−2, POST the
  nearest clean bar ≥ e+1. σ(m) = noise × √(returns spanned) / |y|.
- The blip test and the five other reversion modes still fail exactly as intended.

---

## §2. The defect, in plain English

The price files for 575 stocks join two sources at a "seam" date:
- **After the seam** (usually 2018-01-02 or 2020-04-09), the prices are Alpaca's. They correctly
  fold every dividend into the return.
- **Before the seam**, the prices are Stooq's. Stooq is inconsistent about dividends, and the
  inconsistency follows calendar dates:
  - it includes the dividends paid from 2011-02-21 to 2022-12-18;
  - it leaves out the dividends paid from 2003-04-01 to 2011-02-20;
  - before 2003 it depends on the stock. Some, like KO and XOM, lack every dividend since 1970.

When the two sources were joined in May, the code assumed Stooq always included dividends. Stooq
differs from Alpaca only because it lacks the 2023-onward dividends, and the code read that gap as
a steady difference. It then added that same steady difference to every year before the seam.

So the cache:
- adds a dividend stream the stock never paid on top of years that were already right
  (2011 → seam): about +0.6 pp/yr on the median stock, and about +4.6 pp/yr for MO;
- under-states years whose dividends were genuinely missing (2003 → 2011), and many pre-2003 years.

The errors are proportional to dividend yield. They therefore tilt every backtest toward or away
from high-yield, value and low-volatility names, depending on the decade. Cutover option (a), as
ruled, keeps these years and only rescales them, so the error would survive the cutover unchanged.

## §3. The candidate (v3): what was built and where

- **Script:** `scripts/drip_fix_candidate_t384.py`, with subcommands `fetch`, `build`, `accept`
  and `manifest`, command of record in `docs/Core/execution_manual.md`.
- **Tests:** `tests/test_drip_fix_candidate_t384.py` has 15 tests. Each one plants a known-good or
  known-defective name and checks that the fix moves only the defective one.
- **Code not touched:** `tr_writer.py`, the merge script and `data/`.
- **Location:** the candidate is at
  `/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11/`. Its contents:
  - `processed/<T>_1d.csv` and `processed/parquet/<T>_1d.parquet` for the 575 files that carry
    pre-seam bars. Every other cache file is unchanged and is not copied.
  - `build_records.jsonl` holds one record per file: the seam, b, the splice, every missed run of
    ex-dates, how many dividends were added and by which rule, the approximation years, and the
    unverified pre-2003 span.
  - `probe/labels/<T>.parquet` holds every labelled ex-date with its m and σ(m).
    `probe/xs_median_yield.csv` holds the per-year cross-sectional median yield used by the
    approximation.
  - `acceptance/` holds the §1 test outputs: `summary.json`, `i_t265.csv`, `ii_yf.csv`,
    `iii_nonpayers.csv`, `iv_bytes.csv`, `era_deltas.csv` and `b_before_after.csv`.
  - `yf/` is the yfinance cache: prices and dividends for 576 symbols, plus the fetch log.
  - `v1_evidence/` and `v2_evidence/` hold the superseded runs' records, acceptance outputs and
    manifests.
  - `MANIFEST.md5` holds the md5 of every file. The aggregate md5 is stated in §4.5.
- **Written: 575, refused: 0.** Every file passed the fail-closed checks:
  - the de-drifted cache is proportional to raw Stooq to within 1e-9;
  - the pre-seam bar count equals the merge record;
  - the seam bar is the first Alpaca bar;
  - the post-seam text is byte-identical.
- **Coverage:**
  - 564 files are reference-backed.
  - 11 have no reference: AVB, CTRA, EA, EQR, HOLX, LEG and QRVO have no yfinance prices at all
    (Yahoo: "No data found, symbol may be delisted", confirmed by a serial retry); BBBY, PSKY,
    SATS and POM have a yfinance symbol that is now a different, recent security.
  - 34,575 ex-dates were labelled across 449 payers. 27,642 are MEASURED, 5,210 come from
    neighbours and 1,723 from the global rule. 11,096 were missed and added; 9,602 of those were
    measured.
  - 1,610 measured labels contradict the global era rule:
    - 1,322 before 2003-04, missed where the global rule says captured;
    - 163 in 2003-04 → 2011-02, captured where it says missed, such as MO/Kraft 2007, CAH 2009
      and XOM 2009-05;
    - 125 in 2011-02 → 2022-12.
  - The approximation is used by 12 files: the 11 above plus DAL, ELV and PLD over their
    no-reference years.
  - 54 files carry a pre-2003 span labelled UNVERIFIED.
- **Before 2000, now established where measurable.** 11,517 ex-dates on 201 names; 53.5 % are
  measured. Of the measured ones, 16.4 % were missed, and 40 of 172 names have at least one
  measured miss. KO and XOM missed every dividend from 1970; BA missed them from 1980 to 1999.
  Where a name has no measurable reference (yfinance and Stooq disagree day to day before about
  1988), the span is LABELLED unverified, not guessed.

## §4. The acceptance result — **FAIL** under the pre-declared test

### 4.1 (ii) Against yfinance, per year, 2000–2015. The era structure is tested here.

The thresholds are median 0.05, p95 0.30 and per-quintile median 0.05. The "cache" columns are the
same statistic for today's cache.

| year | era (global) | names | median \|x\| | p95 \|x\| | worst quintile median | cache median | cache p95 | verdict |
|---|---|---|---|---|---|---|---|---|
| 2000 | per-name | 243 | 0.0128 | 0.122 | 0.0171 | 0.93 | 2.84 | PASS |
| 2001 | per-name | 250 | 0.0133 | 0.147 | 0.0151 | 0.88 | 2.76 | PASS |
| 2002 | per-name | 254 | 0.0123 | 0.067 | 0.0129 | 0.92 | 2.47 | PASS |
| 2003 | edge 04-01 | 254 | 0.0098 | 0.050 | 0.0107 | 0.69 | 2.73 | PASS |
| 2004 | missed | 255 | 0.0063 | 0.032 | 0.0105 | 0.74 | 3.03 | PASS |
| 2005 | missed | 256 | 0.0068 | 0.030 | 0.0079 | 0.78 | 2.86 | PASS |
| 2006 | missed | 452 | 0.0056 | 0.037 | 0.0077 | 0.66 | 3.04 | PASS |
| 2007 | missed | 461 | 0.0048 | 0.029 | 0.0061 | 0.69 | 3.07 | PASS |
| 2008 | missed | 471 | 0.0045 | 0.026 | 0.0060 | 0.95 | 4.45 | PASS |
| 2009 | missed | 477 | 0.0048 | 0.027 | 0.0074 | 1.07 | 4.68 | PASS |
| 2010 | missed | 482 | 0.0066 | 0.132 | 0.0116 | 0.88 | 3.49 | PASS |
| 2011 | edge 02-21 | 494 | 0.0065 | 0.101 | 0.0099 | 0.49 | 2.21 | PASS |
| 2012 | captured | 503 | 0.0056 | 0.054 | 0.0081 | 0.68 | 2.42 | PASS |
| **2013** | captured | 512 | 0.0039 | **0.350** | 0.0057 | 0.68 | 2.43 | **FAIL** |
| 2014 | captured | 525 | 0.0033 | 0.035 | 0.0057 | 0.62 | 2.28 | PASS |
| 2015 | captured | 534 | 0.0027 | 0.027 | 0.0052 | 0.65 | 2.28 | PASS |

The census covers 534 names and 6,423 name-years. The yield quintiles' upper bounds are 0, 0.74,
1.68, 2.98 and 23.8 pp. Sector medians run from 0.0026 to 0.0069 pp.

**Why 2013 fails.** 29 of 512 name-years exceed 0.30 pp:
- **13 sit on a Stooq transient block at the 2013 year-end**, the 2013-12-19 → 2014-01-03 block
  on CPB, DGX, DRI, ERIE, GIS, LNC, LVS, MAS, NTAP, ORCL, UDR, VZ and XEL. The raw bundle, the cache
  and the candidate all carry it, because the candidate keeps Stooq where Stooq is total return
  (§1.3).
- 7 are corporate actions the vendors treat differently: LDOS, MUR, VLO, JEF, TMUS, FCX and PSX.
- 2 are partial adjustments: T (yfinance's AT&T dividends read about 1.3 × Stooq's in every
  year 2001–2012, consistent with the known yfinance AT&T anomaly) and MDLZ.
- 7 are small unexplained Stooq/yfinance gaps of 0.3–1.8 pp: BLK, LNT, FLS, VFC, CBOE, ROST and
  BUD. Several had splits that year.

Without the 13 inherited-block rows, the 2013 p95 would be 0.138. That counterfactual explains the
failure; under the rule it does not change the verdict.

### 4.2 (i) Against T-265 (Alpaca 'all'), every name-year from 2016 to the seam

| period | names | median \|x\| | p95 \|x\| | failing name-years | cache median |
|---|---|---|---|---|---|
| 2016 | 535 | 0.0081 | 0.077 | 27 | 0.648 |
| 2017 | 545 | 0.0077 | 0.061 | 19 | 0.648 |
| 2018 (2020-seam names) | 98 | 0.0071 | 0.038 | 3 | 0.900 |
| 2019 | 99 | 0.0074 | 0.025 | 2 | 0.863 |
| 2022 / 2023 (late seams) | 1 / 1 | 0 | 0 | 0 | 0 |
| seam stub (incl. the splice return) | 551 | 0.0061 | 0.033 | 8 | 0.011 |

- **Pass rate:** 1,771 of 1,830 name-years with the floor, and 1,741 with no floor. 59 fail,
  across 46 names. The cache passes 747 of 1,830.
- **Who fails, and why.** Of the 59:
  - **35: the two references disagree with each other** (yfinance − T-265 beyond the tolerance).
    In 27 of those the candidate equals yfinance, so T-265 is the outlier. Examples: AEE 2016,
    COR, DD, F (supplemental dividends), PM, SPGI, SRE, RL, PHM, QCOM, TMUS, UAA, IR, META and
    SYK. The other 8 are large corporate actions where all three series differ: AA 2016,
    APTV 2017, AVGO 2018, DOC 2016, JCI 2016, RTX 2020 stub, XRX 2017 and PGR 2020 stub.
  - **13: spin-offs and mergers that Stooq never applied, though yfinance and T-265 agree.**
    APD 2016 (−7.2), CAG 2016 (−25.1), HPE 2017 (−54.3), HLT 2017, HON 2016 and 2018, GE 2019,
    BIIB 2017, CHTR 2016–17, and VNO 2017.
  - **5: small Stooq/reference gaps** of 0.2–1.0 pp: ACN 2016, AFL 2017, HST 2017, NWSA 2017 and
    WMB 2016.
  - **2: no reference.** BBBY 2016–17. Its yfinance symbol is now a different security, so no
    ex-date could be measured, and Stooq appears to miss its 2016–17 dividends.
  - **5: the splice.** The 2017-12-29 → 2018-01-02 seam day, Stooq's return against Alpaca's,
    off by 0.08–0.24 pp, for AFL, CHTR, MTCH, NWSA and POOL. The cache's stub fails the same
    way.
  - **1: WM 2016**, an ex-date m outside [−0.25, 1.25].
- The cache also fails 55 of these 59 name-years.
- In 34 of the 59 the cache happens to sit closer to the reference than the candidate. In those
  rows its drip partly offsets a Stooq corporate-action error: GE 2019 has cache +1.05 against
  candidate −3.95.

### 4.3 (iii) Non-payers — FAIL, only through (i)

- (a) holds for all 110 reference-backed non-payers: the candidate equals raw Stooq to below
  1e-6 pp in every year. The fix injects nothing.
- (b) fails for 6 names on 9 name-years: BIIB 2017 (the Bioverativ spin-off), CHTR 2016–18
  (merger), IR 2017, META 2016–17 (T-265 vs yfinance, −0.07 pp), MTCH 2018 (stub) and UAA 2016
  (T-265 vs yfinance).

### 4.4 (iv) Post-seam bytes — PASS, 575 of 575

### 4.5 The candidate's identity

- Final candidate (v3): commit `69620e7` (script) and the aggregate manifest md5 below.
- The superseded runs, kept as evidence:
  - v1 (`f69b475`, manifest `10a8f55c…`) had the same (i) and (iii) failures. (ii) failed 2013 at
    a p95 of 0.71, because v1's probe added dividends a second time inside Stooq's transient
    blocks.
  - v2 (`acb1e72`, manifest `244bcf07…`) fixed that but regressed 2000–01 (§1.4).
- v3 is the best of the three on every test. It is still a FAIL.

**Manifest.**
- `MANIFEST.md5` lists 3,674 files. The md5 of the whole manifest file is
  `a2aad09fd687f4e6260eaa9312ab0430`.
- The candidate substrate alone is the 1,150 `processed/` lines (575 csv + 575 parquet), with
  aggregate md5 `5646d03d91f8392218e8239bb228e93b` (computed as `grep "  processed/" MANIFEST.md5 | md5`).
- Size: about 0.93 GB, of which `processed/` is 0.81 GB.

**Full suite** (`python -m pytest -q`, on this branch, before the script's lock-marker comments
were added):
- result: 4,692 passed, 2 failed, 56 skipped;
- failure 1: the known environmental `edges.yml` capability-ledger contract;
- failure 2: the repo-wide `test_processed_globbers` lock, which my new script tripped. It now
  carries the `# ticker-exclusions: bypassed — data-ops …` marker beside each per-ticker read.

**Re-run after the fix:** the full suite was NOT repeated, because the host was below 15 GB free.
I re-ran every script-scanning lock (17 files) and the new tests: 286 passed, plus the same known
`edges.yml` failure. The canonical `data/processed/` listing (names, sizes, mtimes) was identical
before and after the suite.

## §5. What changes in the numbers people quote

**Per-name mean annual return, candidate − cache, in pp/yr.** Medians [p10, p90] over files:

| era | files | median | p10 | p90 | what moved |
|---|---|---|---|---|---|
| pre-2000 | 246 | −0.86 | −1.91 | 0.00 | the drip removed; KO +1.25, XOM +3.87, PG +1.52 where Stooq missed dividends since the 1970s |
| 2000 → 2003-03 | 259 | −0.76 | −1.91 | 0.00 | the drip removed; per-name missed eras added (MO, AA, CAT from 2001) |
| 2003-04 → 2011-02 | 500 | +0.39 | −0.65 | +2.47 | the missing dividends restored, net of the drip |
| 2011-02 → seam | 571 | −0.59 | −1.78 | 0.00 | the drip's over-count removed |

**By seam group, 2011-02 → seam:** −0.55 for the 2018-01-02 seam and −0.77 for the 2020-04-09
seam.

**Named examples, the same four eras in order:**
- MO −4.58 / −0.99 / +0.79 / −4.58
- PFE −4.03 / −4.03 / −0.04 / −4.03
- VZ −3.64 / −3.64 / +1.33 / −3.64
- XOM +3.87 / −0.35 / +0.32 / −1.82
- KO +1.25 / +0.15 / +1.04 / −1.61
- AAPL and AMZN 0.00 throughout

**Share of files whose drift exceeds 0.5 pp/yr.**
- The merge applied b > 0.5 pp/yr to 313 of these 575 files, 54 %. The health-check figure is
  334 of 730, counting the `both` files with no pre-seam bars.
- Measured as the mean annual excess against the reference over 2012 → seam, the files above
  0.5 pp/yr fall from **299 of 564 in the cache to 33 of 564 in the candidate**.
- Every one of the 33 is a corporate-action name: AA, APTV, CNX, DHR, JCI, YUM, HPE, XRX, GE,
  KMB, PPL, SPG, MUR, VLO, OXY, WMB and others. The yfinance AT&T anomaly accounts for T. These
  are Stooq's unapplied spin-offs, which the drip had partly masked. Across the (ii) census, the
  name-years with |x| > 0.30 pp fall from 4,549 of 6,423 to 169.

## §6. What it changes for the cutover runbook (described, NOT made)

`engines/data_manager/tr_writer.py` option (a), lines 45–55, keeps the cached pre-seam bars and
scales them by the ratio at the seam. The mechanism is right; the bars it keeps are wrong. (a′)
implies:

1. **A new step before S2** (the one-step replacement), on the cutover COPY:
   - build (a′) pre-seam bars for the copy's 575 seam files, using this script's `build` logic
     pointed at the copy, or an (a′) mode added to the writer;
   - then re-run P2/P3 (the guard and label readings) and regenerate the candidate manifest.
   The post-seam bars in the copy come from yfinance exact total return, not Alpaca. (a′) leaves
   them alone, and the writer's existing seam-ratio rail checks the splice.
2. **The convention label changes.** `tr_writer.py:122-124` defines `DRIP` as "T-082b's
   `apply_dividend_strip`". (a′) needs its own label (for example `era_tr`: "Stooq where Stooq is
   total return; the missed dividends restored per ex-date"). The census's convention reader and
   the write record's `convention` block must carry it, along with the per-file
   `approx_years` / `unverified_pre2003_span`, or the census can no longer say what each span
   IS.
3. **Records owed:**
   - the cutover proposal §1's "not systematic" (refuted);
   - the merge script's docstring premise, lines 13–15;
   - `_merge_meta.json`'s `implied_annual_div_yield_pct`, which uses × 252 on a per-calendar-day
     slope.
4. **Re-pin #2 content grows** by the 575 pre-seam rewrites. The S6 class-by-class manifest diff
   gains that class.
5. **What (a′) does NOT fix:** Stooq's unapplied 2012–2019 spin-offs and its transient blocks
   (§4, §10). Under option (a) or (a′), those stay in the substrate until a separate repair.

## §7. Verdicts that must be re-run on a corrected substrate

These are `[NN-SUBSTRATE-REVERIFY]` cases. "Re-verify required" means the verdict was measured on
a substrate with a known yield-proportional error.

- **B-1 / T-365, the decisive price-vocabulary test** (`docs/Audit/b1_raw_signal_decile_verdict_2026-10-14.md`):
  - its forward returns over 2000–2019 carry this bias, tilted toward high-yield names in
    2011 → seam and away from them in 2003–10 and in the per-name pre-2003 eras;
  - value, low-vol and momentum deciles are the most exposed;
  - re-run as a NEW pre-registered run. Its null is not a clean refutation of those signals
    until then.
- **The RR-1 equity-book list**
  (`docs/Sources/referee_repair_proposal_RR-1_2026_09_30.md` §5): the 29 controller-produced
  verdicts and the 4 consumption verdicts (T-170, T-206, and per R's review T-148 and T-169).
  - The 29:
    - T-066, T-092, T-126, T-140, T-140-fu3, T-180;
    - T-055c/d/e/g/h, T-057, T-057b, T-109, T-118-rerun, T-120, T-121, T-128r, T-154, T-162,
      T-174;
    - T-041b, T-122, T-129, T-144, T-145, T-196, T-241;
    - T-211.
  - These are already UNTESTED under RR-1. This defect is a second, independent reason, and
    their re-runs must happen on the corrected substrate or they will be re-verified on a wrong
    one.
- **Also:**
  - the harnesses that read `data/processed` closes over pre-seam windows (T-123, T-135, T-137,
    T-150, T-153, T-269, per R's read of the cutover proposal);
  - the base-curve consumers (T-171, T-178);
  - T-239, which "reads raw price files". If those files are `data/processed`, it is affected
    too, so check before quoting it;
  - any Discovery or Gate-7 window that reaches before a seam.
- **B-4 must not run on the current cache.** B-6 must read a clean price source.
- **Unaffected:**
  - the T-306 family, SPY, `tr_reconciled/` and the T-265 panel;
  - anything whose window starts after 2020-04-09.

## §8. Risks

1. **The amounts come from the reference's own source.** Inside the missed era the added
   dividends come from yfinance, the same source as (ii)'s reference. They are checked
   independently only at the era edges, where Stooq's own dividend amounts agree with
   yfinance's (pooled median 0.0037 pp), and against Alpaca from 2016. A systematic error in
   yfinance's 2003–2010 dividend amounts would not be caught. (Since the SPY check proves
   yfinance to 0.08 pp/yr, this is not the expected failure.)
2. **The 11 no-reference names carry an approximation:** the cross-sectional median yield, about
   1.2–2 %/yr, through 2003–2011. BBBY was very likely a non-payer then, so for BBBY the
   approximation is an over-count. Each file's record names its `approx_years`. A future source
   for the delisted names (EDGAR dividend facts, SimFin) can replace it.
3. **54 files have unverified pre-2003 spans.** The candidate leaves Stooq as-is there. The
   measured pre-2000 miss share is 16 %, so some of these spans are likely under-counted.
4. **Stooq's transient blocks and unapplied spin-offs stay in the substrate.** Any monthly
   rebalance reading the 2013 month-end closes (June–November 2013, about 85 names) sees a
   spurious ±1-dividend move each month. That applies under (a) as well.
5. **The forking path.** Three candidate versions ran against one test. Every change was a
   diagnosed defect, recorded before the next run, and the thresholds never moved. Still, this
   is three looks, not one. A reviewer should re-run `accept` on v3 independently.
6. **The yfinance data is a snapshot.** It is cached in `yf/`, so the candidate is reproducible
   from that cache. A re-fetch on another day may differ by the ex-dates Yahoo restates.

## §9. Recommendation

**Do not cut over on option (a) as ruled.** It carries a measured, yield-proportional bias:
- the cache fails 1,083 of 1,830 name-years against Alpaca from 2016, where the candidate fails
  59;
- it has 4,549 of 6,423 name-years against yfinance above 0.30 pp, where the candidate has 169.

**Adopt (a′) as the pre-seam convention for cutover day, knowing it FAILS its pre-declared test,**
because:
- every failing name-year traces to a cause outside the dividend-era repair: spin-offs Stooq
  never applied, Stooq transient blocks, reference-vs-reference disagreement, one no-reference
  name, and the seam-day return;
- the cache fails 55 of the 59 too;
- the (ii) medians sit at the reference's own noise (0.003–0.013 pp) in every year, every yield
  quintile and every sector.

The failure is the true statement that **Stooq has defects beyond dividends**. That claim needs
its own unit, held to this same §1 test unchanged: repair the 2012–2019 unapplied spin-offs and
the transient blocks, measured, with a declared list. Until that unit passes, label those
name-years in the census.

This reopens the 2026-10-22 cutover ruling, so it is **the user's decision**. The alternatives:
- keep (a) and label every pre-seam number "drip-biased, yield-proportional";
- delay the cutover until the second unit lands.

## §10. Findings beyond the brief

1. **Stooq transient blocks** (4,517 since 1995, over 414 names). These are runs of bars offset by
   about one dividend that revert within days. They are now a health-check candidate (MEDIUM).
   They hit the cache's month-end closes in 2013 and any return measured across them.
2. **Stooq did not apply 2012–2019 spin-offs** on at least 13 names: APD, CAG, HPE, HLT, HON,
   GE, BIIB, VNO, KMB, PPL, SPG, MUR, VLO and OXY. Yet it did apply spin-offs inside the
   2003–2011 "missed" era: MO/Kraft, MO/PM, CAH and AYI.
3. **Pre-2003 eras are per name.** KO and XOM lack every dividend from 1970, and BA from 1980 to
   1999. So the cache's pre-2003 years are ALSO wrong for those names, by −yield + b. The
   investigation's "≈ 0 % missed 2000 → 2003-Q1" holds for most names but not all: in 2001–02,
   22–32 % of measured ex-dates were missed.
4. **POM's seam-day return is −90.8 %**, in the cache and in the candidate alike. The pre-seam
   Stooq level is about 10× Alpaca's: a reused ticker or a split mismatch. Not touched here.
5. **yfinance quirks:**
   - `Ticker.dividends` answers an EMPTY series for a delisted symbol rather than an error;
   - Yahoo returns "possibly delisted" for live-looking names it has dropped (AVB, EA, EQR,
     HOLX, LEG, QRVO, CTRA);
   - SATS, BBBY and PSKY now map to recent securities with months of history.
