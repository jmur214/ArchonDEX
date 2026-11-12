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
- **RESTATED 2026-11-11 after the independent review (MAJOR-2). The text above is kept; this note
  supersedes its claim.**
  - "(ii) tests the era labels" OVERCLAIMS. In 2003-04 → 2011-02, and in every per-name pre-2003
    missed era, the "missed" labels (m ≥ 0.5) are computed FROM the same yfinance Adj Close series
    that (ii) then compares against. The added amounts are yfinance's own D/P_prev. So in those
    eras (ii) measures SELF-CONSISTENCY: the candidate reproduces the reference it was built from.
    It is not independent evidence that the eras or the amounts are right.
  - The independent evidence is listed separately in §4: (i) against Alpaca; (ii) in the 2011–15
    captured era, where the candidate is raw Stooq; and the step audit, which shows no price was
    copied from yfinance.

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

**v4 — the independent review's corrections.** Declared here BEFORE the v4 run. Thresholds,
populations of (i), (ii), (iii)(a)/(b) and (iv), and the verdict rule are UNCHANGED.
- The review (2026-11-11) judged v3 SOUND: every recomputed number matched to 1e-13, and the
  v1 → v3 path was judged legitimate defect-fixing. It returned two MAJOR and two MINOR findings.
  v3 stays as it is at `drip_fix_a_prime_2026_11_11/`. v4 is written to a NEW directory,
  `drip_fix_a_prime_v4_2026_11_11/`, and reads v3's `yf/` cache read-only (`--yf-dir`).
- **R1, rule change (MAJOR-1). No approximated dividend is ever added.**
  - v1–v3 gave no-reference spans in a missed era the cross-sectional median yield. With no payer
    reference, that ADDED about 1.08 pp/yr to the known non-payers HOLX, SATS and BBBY (merge
    b = 0, so v3 was WORSE than the cache, by about 7.6 % cumulative) and to the near-non-payer
    CTRA. It UNDER-counted the REIT and high-yield names AVB, EQR and LEG.
  - v4 rule 4 (§1.3), replaced: a bar with no same-security payer reference stays raw Stooq
    (after the drip is undone), in every era. The record labels it UNVERIFIED:
    `unverified_missed_era_spans`, plus the bias direction "UNDER-counts by the name's yield IF
    it paid; exact if it did not".
  - No source in hand establishes payer status for those names, so no approximation is applied.
- **R2, new test (iii)(c)** — the review's "(iii-b)". No bar without a reference may move off raw
  Stooq. It is checked daily:
  - on every no-reference name, across its whole missed-era span;
  - on the unverified missed-era spans of referenced names.
  Criterion: |Δ daily log return vs raw Stooq| < 1e-10. **(iii) now PASSES iff (a), (b) and (c)
  all hold.**
- **R3, a step audit (evidence, not a threshold).** On every file, the candidate's daily returns may
  differ from raw Stooq's ONLY at labelled added ex-dates, and there by exactly −log(1 − D/P_prev).
  This is the independent evidence that no yfinance PRICE enters the candidate.
- **R4, the circularity of (ii) is restated** (the note in §1.2). §4 separates INDEPENDENT evidence
  from evidence that is CIRCULAR BY CONSTRUCTION.
- **R5, three code paths get locks** (MINOR-3), each proven by reverting it:
  - the 3-return probe window;
  - the seam constant k;
  - the identity check.
- **R6, every count in the narrative is recomputed** from the machine output (MINOR-4).

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

## §3. The candidate (v4, after independent review): what was built and where

- **Script:** `scripts/drip_fix_candidate_t384.py`, with subcommands `fetch`, `build`, `accept`
  and `manifest`. The commands of record are in `docs/Core/execution_manual.md`.
- **Tests:** `tests/test_drip_fix_candidate_t384.py`, 19 tests. They plant a known-defective payer
  (built with the merge's own functions) and known-good names (a non-payer, and a payer whose Stooq
  data is total return in every era), and check that the fix moves only the defective one.
- **Every repair is proven by reverting it.** Nine reversion modes each fail their planted test:
  - the probe without the transient-block mask (v1);
  - v2's 5-bar window;
  - the seam constant k removed;
  - the identity check disabled;
  - the IPO stub removed;
  - v1's approximation arithmetic;
  - the v3 approximation switched back on;
  - never-add and always-add;
  - keeping the drip.
- **Not touched:** `tr_writer.py`, the merge script and `data/`.
- **v4:** `/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_v4_2026_11_11/`
  - `processed/<T>_1d.csv` and `parquet/<T>_1d.parquet`: the 575 files with pre-seam bars.
  - `build_records.jsonl`: one record per file (seam, b, splice, missed runs, dividends added and
    by which rule, `unverified_missed_era_spans` with the bias direction, unverified pre-2003 span).
  - `probe/labels/`: the labelled ex-dates.
  - `acceptance/`: the §1 outputs, plus `iii_c_no_reference.csv` and `step_audit.csv`.
  - `MANIFEST.md5`.
  - It reads v3's `yf/` cache read-only. That cache's md5s are in v3's manifest.
- **v3 is kept as it was:** `/Users/jacksonmurphy/Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11/`.
  It includes `v1_evidence/` and `v2_evidence/`.
- **Written: 575, refused: 0.** Every file passed the fail-closed checks: the de-drifted cache is
  proportional to raw Stooq to within 1e-9, the pre-seam bar count equals the merge record, the
  seam bar is the first Alpaca bar, and the post-seam text is byte-identical.
- **Coverage:**
  - 564 files are reference-backed.
  - 11 have no reference:
    - 7 because yfinance has no prices for them: AVB, CTRA, EA, EQR, HOLX, LEG and QRVO (Yahoo:
      "No data found, symbol may be delisted", confirmed on a serial retry);
    - 4 because their yfinance symbol is now a different, recent security: BBBY, PSKY, SATS and
      POM.
  - 34,575 ex-dates were labelled across 449 payers. 27,642 were MEASURED, 5,210 came from
    neighbours and 1,723 from the global rule. 11,096 were missed and added; 9,602 of those were
    measured.
  - 1,610 measured labels contradict the global era rule:
    - 1,322 before 2003-04;
    - 163 in 2003-04 → 2011-02 (for example MO/Kraft 2007, CAH 2009, XOM 2009-05);
    - 125 in 2011-02 → 2022-12.
- **v4 adds no approximated dividend.**
  - 12 files carry `unverified_missed_era_spans`: 15,487 bars in total, raw Stooq kept and
    labelled "UNDER-counts by the name's yield IF it paid; exact if it did not".
    - AVB, BBBY, CTRA, HOLX and PSKY: 2005-02 → 2011-02.
    - EQR and LEG: 2003-04 → 2011-02.
    - SATS: 2007-12 → 2011-02.
    - DAL: 2003-04 → 2007-03.
    - PLD: 2003-04 → 2010-12.
    - ELV: 2003.
    - POM: 2025-10 → 12.
  - 54 files carry a pre-2003 span labelled UNVERIFIED.
- **Before 2000, established where it can be measured.**
  - 11,517 ex-dates on 201 names; 53.5 % were measured.
  - Of the measured ex-dates, 16.4 % were missed. 40 of 172 names have at least one measured
    miss.
  - KO and XOM missed every dividend from 1970. BA missed them from 1980 to 1999.
  - Before about 1988 the reference cannot be measured against: yfinance and Stooq differ by
    0.2–1 % a day. Those spans are LABELLED, not guessed.

## §4. The acceptance result — **FAIL** under the pre-declared test (v3 and v4 alike)

### 4.0 v3 beside v4

| test | v3 | v4 | verdict |
|---|---|---|---|
| (i) vs T-265, name-years passing | 1,771 / 1,830 (strict 1,741) | identical | FAIL |
| (ii) years passing, 2000–15 | 15 / 16 (2013 p95 0.350) | identical, every cell | FAIL |
| (iii)(a) non-payers untouched | 110 / 110 | 110 / 110 | — |
| (iii)(b) non-payers in (i) | 6 names fail | identical | FAIL |
| (iii)(c) no-reference stays raw Stooq (new in v4) | not run; **v3 would fail**: it moved HOLX, SATS and BBBY by +1.24/+1.45 pp/yr | **14 / 14 pass** | — |
| (iv) post-seam bytes | 575 / 575 | 575 / 575 | PASS |
| step audit (new in v4) | — | 11,096 steps, 0 unexpected, max deviation 9.4e-16 | evidence |

The only files that move between v3 and v4 are the 12 with no-reference missed-era spans. None of
them was in the (i)/(ii)/(iii)(a) populations. Their 2003-04 → 2011-02 era deltas (candidate −
cache, pp/yr):

| name | v3 | v4 |
|---|---|---|
| BBBY | +1.24 | 0.00 |
| HOLX | +1.24 | 0.00 |
| SATS | +1.45 | 0.00 |
| AVB | −0.29 | −1.53 |
| EQR | −0.51 | −1.77 |
| CTRA | −0.21 | −1.44 |
| LEG | +0.79 | −0.47 |

v4's numbers are just the drip removed, −b. The REIT names now UNDER-count by their unknown
yield, and say so.

### 4.1 What is INDEPENDENT evidence, and what is circular by construction (restated after the review)

**INDEPENDENT of the build:**
- **(i) against Alpaca 'all' from 2016.** The candidate fails 59 of 1,830 name-years; the cache
  fails 1,083.
- **(ii) in the captured era 2011–15, where the candidate IS raw Stooq.** Name-years above
  0.30 pp fall from 1,725 to 92 of 2,568; for 2012–15 alone, from 1,422 to 74 of 2,074. These
  two items test the drip REMOVAL.
- **The step audit.** In all 575 files the candidate's daily returns differ from raw Stooq's only
  at the 11,096 labelled ex-dates, by exactly −log(1 − D/P_prev) (to 9.4e-16). No yfinance price
  enters the candidate.
- **(iv) and (iii)(c).**

**CIRCULAR BY CONSTRUCTION:**
- **(ii) in 2003-04 → 2011-02 and in every per-name pre-2003 missed era.** Over 2004–10 the median
  is 0.0054 pp across 2,854 name-years. The "missed" labels are computed from the same yfinance
  Adj Close this compares against, and the amounts added are yfinance's D/P. This shows that the
  candidate reproduces its reference. It does NOT show that the eras or the amounts are right.
- The amounts are corroborated only at the edges of those eras:
  - where Stooq applied its own dividends (2000–02, 2011–22), it agrees with yfinance to a pooled
    median of 0.0037 pp;
  - from 2016, against Alpaca.
- **"Proven both ways" holds for SPY,** whose total return reproduces S&P's published index less
  its expense ratio. It does NOT hold name by name: yfinance's AT&T dividends run ≈ 1.3 × what
  Stooq applied in every year 2003–2010 (median m 0.249; the review estimated ≈ 1.24 ×).

### 4.2 (ii) Against yfinance, per year, 2000–2015 (v3 = v4)

The thresholds are median 0.05, p95 0.30 and per-quintile median 0.05. The "cache" columns are the
same statistic for today's cache. Read the missed-era rows through §4.1: there, (ii) is
self-consistency.

| year | era (global) | names | median \|x\| | p95 \|x\| | worst quintile median | cache median | cache p95 | verdict |
|---|---|---|---|---|---|---|---|---|
| 2000 | per-name | 243 | 0.0128 | 0.122 | 0.0171 | 0.93 | 2.84 | PASS |
| 2001 | per-name | 250 | 0.0133 | 0.147 | 0.0151 | 0.88 | 2.76 | PASS |
| 2002 | per-name | 254 | 0.0123 | 0.067 | 0.0129 | 0.92 | 2.47 | PASS |
| 2003 | edge 04-01 | 254 | 0.0098 | 0.050 | 0.0107 | 0.69 | 2.73 | PASS |
| 2004 | missed | 255 | 0.0063 | 0.032 | 0.0105 | 0.74 | 3.03 | PASS (circular) |
| 2005 | missed | 256 | 0.0068 | 0.030 | 0.0079 | 0.78 | 2.86 | PASS (circular) |
| 2006 | missed | 452 | 0.0056 | 0.037 | 0.0077 | 0.66 | 3.04 | PASS (circular) |
| 2007 | missed | 461 | 0.0048 | 0.029 | 0.0061 | 0.69 | 3.07 | PASS (circular) |
| 2008 | missed | 471 | 0.0045 | 0.026 | 0.0060 | 0.95 | 4.45 | PASS (circular) |
| 2009 | missed | 477 | 0.0048 | 0.027 | 0.0074 | 1.07 | 4.68 | PASS (circular) |
| 2010 | missed | 482 | 0.0066 | 0.132 | 0.0116 | 0.88 | 3.49 | PASS (circular) |
| 2011 | edge 02-21 | 494 | 0.0065 | 0.101 | 0.0099 | 0.49 | 2.21 | PASS |
| 2012 | captured | 503 | 0.0056 | 0.054 | 0.0081 | 0.68 | 2.42 | PASS |
| **2013** | captured | 512 | 0.0039 | **0.350** | 0.0057 | 0.68 | 2.43 | **FAIL** |
| 2014 | captured | 525 | 0.0033 | 0.035 | 0.0057 | 0.62 | 2.28 | PASS |
| 2015 | captured | 534 | 0.0027 | 0.027 | 0.0052 | 0.65 | 2.28 | PASS |

The census covers 534 names and 6,423 name-years. The upper bounds of the yield quintiles are 0,
0.74, 1.68, 2.98 and 23.8 pp. Sector medians run from 0.0026 to 0.0069 pp.

**Why 2013 fails, recomputed from the machine output.** 29 of 512 name-years exceed 0.30 pp, by
machine cause class:

- **13: a Stooq transient block at a period endpoint**, inherited from raw Stooq by the cache and
  the candidate alike.
  - 11 END inside the 2013 year-end block, which opens 2013-12-19 and closes 2014-01-03/06: CPB,
    DGX, DRI, ERIE, GIS, LNC, MAS, NTAP, ORCL, UDR and VZ.
  - 2 START inside a block at 2012-12-31: XEL (a one-day blip) and LVS (a block from 2012-12-18
    to 2012-12-31).
- **11 "other".** These are corporate actions the vendors treat differently (LDOS, MUR, VLO, JEF,
  FCX, PSX) and unexplained gaps of 0.3–1.8 pp (BUD, CBOE, FLS, ROST, VFC), several in a split
  year.
- **2 with an ex-date m outside [−0.25, 1.25]:** BLK and LNT.
- **2 partial adjustments:** T (the yfinance AT&T anomaly) and MDLZ.
- **1 large distribution:** TMUS.

Without the 13 block rows, the 2013 p95 would be 0.138. That explains the failure; under the rule
it does not change the verdict.

### 4.3 (i) Against T-265 (Alpaca 'all'), every name-year from 2016 to the seam (v3 = v4)

| period | names | median \|x\| | p95 \|x\| | failing name-years | cache median |
|---|---|---|---|---|---|
| 2016 | 535 | 0.0081 | 0.077 | 27 | 0.648 |
| 2017 | 545 | 0.0077 | 0.061 | 19 | 0.648 |
| 2018 (2020-seam names) | 98 | 0.0071 | 0.038 | 3 | 0.900 |
| 2019 | 99 | 0.0074 | 0.025 | 2 | 0.863 |
| 2022 / 2023 (late seams) | 1 / 1 | 0 | 0 | 0 | 0 |
| seam stub (incl. the splice return) | 551 | 0.0061 | 0.033 | 8 | 0.011 |

**Who fails, and why: 59 name-years across 46 names.** By machine cause class
(35 + 18 + 5 + 1 = 59):

- **35: the two references disagree** (yfinance − T-265 beyond the tolerance). In 27 of the 35 the
  candidate EQUALS yfinance, so T-265 is the outlier. Examples: AEE 2016, COR 2016–17,
  DD 2016–17, F 2016–17 (supplemental dividends), PM 2016, SPGI 2016, SRE 2016, RL 2016, PHM 2016,
  QCOM 2018, TMUS 2016, UAA 2016, IR 2017, META 2016–17 and SYK 2019. In the other 8, all three
  series differ: AA 2016, APTV 2017, AVGO 2018, DOC 2016, JCI 2016, RTX 2020 stub, XRX 2017 and
  PGR 2020 stub.
- **18 "other". yfinance and T-265 agree; Stooq, and therefore the candidate, differs.** Split by
  hand from the public record:
  - 11 corporate-action name-years: APD 2016 (−7.19), BIIB 2017 (+8.22), CAG 2016 (−25.08),
    CHTR 2016 (−10.10), CHTR 2017 (+0.11), GE 2019 (−3.95), HLT 2017 (−2.98), HON 2016 (−0.54),
    HON 2018 (−4.26), HPE 2017 (−54.28) and VNO 2017 (+1.05);
  - 5 small gaps: ACN 2016 (+1.03), AFL 2017 (+0.24), HST 2017 (+0.23), NWSA 2017 (+0.22) and
    WMB 2016 (+0.48);
  - 2 with no reference: BBBY 2016 (−0.85) and 2017 (−1.86), whose 2016–17 dividends Stooq
    appears to miss, with no ex-date measurable.
- **5: the splice.** The 2017-12-29 → 2018-01-02 seam-day return, Stooq's against Alpaca's:
  AFL −0.24, CHTR −0.08, MTCH −0.12, NWSA −0.17 and POOL +0.09.
- **1: WM 2016**, an ex-date m outside [−0.25, 1.25].

The cache also fails 55 of these 59. The candidate sits closer to T-265 than the cache in 25 of
them. In the other 34, the cache's drip partly offsets a Stooq corporate-action error: GE 2019 has
the cache at +1.05 and the candidate at −3.95.

### 4.4 (iii) Non-payers and no-reference names — FAIL, only through (i)

- (a) holds for all 110 reference-backed non-payers: the candidate equals raw Stooq to below
  1e-6 pp in every year.
- (b) fails for 6 names on 9 name-years:
  - BIIB 2017 (Bioverativ spin-off);
  - CHTR 2016–18 (merger);
  - IR 2017 and UAA 2016 (the two references disagree);
  - META 2016–17 (T-265 vs yfinance, −0.07 pp);
  - MTCH 2018 (the stub).
- (c), new in v4: **14 of 14 pass.**
  - Checked: the 11 no-reference names, plus the uncovered spans of DAL, ELV and PLD.
  - No daily return moves off raw Stooq by more than 1e-10.
  - v3 would have failed (c) for every name in its approximation.

### 4.5 (iv) Post-seam bytes — PASS, 575 of 575

### 4.6 The candidate's identity and the checks run

**v4** (`48c99a8` declares it; this commit records it):
- `MANIFEST.md5` lists 1,610 files; the md5 of the manifest file is
  `6f47e3e885b5815e4d5452cd01902797`.
- The substrate alone, the 1,150 `processed/` lines (575 csv + 575 parquet), has aggregate md5
  `2cee41ef7d2e0bd8fa858d500f99dda2`, computed as `grep "  processed/" MANIFEST.md5 | md5`.
- Size 0.80 GB.

**v3** (`69620e7`):
- manifest `a2aad09fd687f4e6260eaa9312ab0430`, `processed/` md5
  `5646d03d91f8392218e8239bb228e93b`;
- kept, never deleted.

**Superseded:**
- v1 (`f69b475`, manifest `10a8f55c…`);
- v2 (`acb1e72`, manifest `244bcf07…`).

**The independent review** (coordinator, 2026-11-11):
- VERDICT SOUND. Every recomputed number matched to 1e-13.
- The v1 → v3 path was judged legitimate defect-fixing: the thresholds were identical and the era
  deltas moved ≤ 0.02 pp.
- **Scope safety is proven:** all 2,172 files under `data/processed/` match
  `config/substrate_manifest.sha256`.

**The test suite:**
- On v3, the full suite gave 4,692 passed and 2 failed. One failure was the known environmental
  `edges.yml` contract. The other was the repo-wide processed-read lock, which this script
  tripped; it is fixed with the bypass markers.
- On v4 the full suite was NOT repeated, because free disk was at 12.8–15 GB and other agents
  were running. Instead:
  - the 19 candidate tests pass;
  - `doc_lint` passes;
  - the 17 script-scanning lock files pass, apart from the same `edges.yml` failure.

## §5. What changes in the numbers people quote (v4)

**Per-name mean annual return, candidate − cache, in pp/yr.** Medians [p10, p90] over files:

| era | files | median | p10 | p90 | what moved |
|---|---|---|---|---|---|
| pre-2000 | 246 | −0.86 | −1.91 | 0.00 | the drip removed; +yield where Stooq missed (KO +1.25, XOM +3.87, PG +1.52) |
| 2000 → 2003-03 | 259 | −0.76 | −1.91 | 0.00 | the drip removed; per-name missed eras (MO, AA, CAT from 2001) |
| 2003-04 → 2011-02 | 500 | +0.35 | −0.65 | +2.47 | the missing dividends restored (v3: +0.39; v4 adds nothing where there is no reference) |
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
- The merge applied b > 0.5 pp/yr to 313 of these 575 files.
- Measured as the mean annual excess against the reference over 2012 → seam, the files above
  0.5 pp/yr fall from **299 of 564 in the cache to 33 of 564 in the candidate**. Every one of the
  33 is a corporate-action name, or AT&T with its yfinance anomaly.
- Across the whole (ii) census, the name-years with |x| > 0.30 pp fall from 4,549 of 6,423 to 169.
  **Only the 2011–15 part of that (1,725 → 92) is independent of the build** (§4.1).

## §6. What it changes for the cutover runbook (described, NOT made)

`engines/data_manager/tr_writer.py` option (a), lines 45–55, keeps the cached pre-seam bars and
scales them by the ratio at the seam. That mechanism is right; the bars it keeps are wrong. (a′)
implies:

1. **A new step before S2** (the one-step replacement), on the cutover COPY:
   - build (a′) pre-seam bars for the copy's 575 seam files, using this script's `build` logic
     pointed at the copy, or an (a′) mode added to the writer;
   - then re-run P2/P3 (the guard and label readings) and regenerate the candidate manifest.
   The copy's post-seam bars are yfinance exact total return, not Alpaca. (a′) leaves them alone,
   and the writer's existing seam-ratio rail checks the splice.
2. **The convention label changes.** `tr_writer.py:122-124` defines `DRIP`. (a′) needs its own
   label, for example `era_tr`, meaning "Stooq where Stooq is total return; the missed dividends
   restored per measured ex-date; no-reference spans UNVERIFIED". The census's convention reader
   and the write record must carry the per-file `unverified_missed_era_spans` and
   `unverified_pre2003_span`, or the census can no longer say what each span IS.
3. **Records owed:**
   - the cutover proposal §1's "not systematic" (refuted);
   - the merge docstring's premise, lines 13–15;
   - `_merge_meta.json`'s `implied_annual_div_yield_pct`, which multiplies a per-calendar-day
     slope by 252.
4. **Re-pin #2 grows** by the 575 pre-seam rewrites, which becomes a new class in S6's diff.
5. **What (a′) does NOT fix:**
   - the corporate actions Stooq handles differently, in 2016–19 and inside the missed era;
   - its transient blocks;
   - the 12 no-reference missed-era spans;
   - the 54 unverified pre-2003 spans.

## §7. Verdicts that must be re-run on a corrected substrate

These are `[NN-SUBSTRATE-REVERIFY]` cases.

- **B-1 / T-365** (`docs/Audit/b1_raw_signal_decile_verdict_2026-10-14.md`):
  - its forward returns over 2000–2019 carry this yield-proportional bias;
  - value, low-vol and momentum deciles are the most exposed;
  - re-run as a NEW pre-registered run. Its null is not a clean refutation of those signals
    until then.
- **The RR-1 equity-book list** (`docs/Sources/referee_repair_proposal_RR-1_2026_09_30.md` §5):
  - the 29 controller-produced verdicts:
    - T-066, T-092, T-126, T-140, T-140-fu3, T-180;
    - T-055c/d/e/g/h, T-057, T-057b, T-109, T-118-rerun, T-120, T-121, T-128r, T-154, T-162,
      T-174;
    - T-041b, T-122, T-129, T-144, T-145, T-196, T-241;
    - T-211;
  - the consumption verdicts: T-170 and T-206, plus T-148 and T-169 per R's review.
  - These are already UNTESTED under RR-1. This defect is a second, independent reason. Their
    re-runs must happen on the corrected substrate.
- **Also:**
  - the harnesses that read `data/processed` closes over pre-seam windows (T-123, T-135, T-137,
    T-150, T-153, T-269);
  - the base-curve consumers (T-171, T-178);
  - T-239, if its "raw price files" are `data/processed`;
  - any Discovery or Gate-7 window that reaches before a seam.
- **B-4 must not run on the current cache.** B-6 must read a clean price source.
- **Unaffected:**
  - the T-306 family, SPY, `tr_reconciled/` and the T-265 panel;
  - windows starting after 2020-04-09.

## §8. Risks — and what remains UNVERIFIED

1. **The dividend amounts in the missed eras are not independently verified.** In 2003-04 →
   2011-02, and in the per-name pre-2003 missed eras, both the labels and the amounts come from
   yfinance. They are corroborated only at those eras' edges (Stooq's own adjustments, Alpaca from
   2016), plus SPY's total return. A per-name yfinance error inside the era, like the AT&T case
   (≈ 1.3 ×; there the candidate is right because Stooq captured T), would not be caught.
2. **12 no-reference files keep raw Stooq in a missed era (15,487 bars).** For a payer that is an
   UNDER-count by its yield, plausibly about 1.5 pp/yr on the REITs AVB and EQR. For a non-payer
   it is exact. Each file's record says so. A citable dividend source for delisted names (EDGAR
   `DividendsDeclared`, SimFin) would let these be filled. Nothing is guessed until then.
3. **54 files have unverified pre-2003 spans**, where the measured pre-2000 miss share is 16 %.
   Some of these spans are likely under-counted.
4. **Stooq's corporate-action handling and transient blocks remain in the substrate**, under
   option (a) and (a′) alike:
   - spin-offs both inside the missed era (VZ/Idearc 2006 −3.7 pp, VZ/Frontier 2010 −6.4 pp,
     against yfinance) and in 2016–19;
   - 4,517 transient blocks, including the 2013 month-end closes on about 85 names.
5. **The forking path.** Four candidate versions ran against one test. The thresholds never
   moved, and the review judged v1 → v3 legitimate. v4 changed only the no-reference rule, which
   moves 12 files outside the test populations, and added stricter checks.
6. **The yfinance cache is a snapshot.** The candidate is reproducible from `yf/`. A re-fetch may
   differ by ex-dates Yahoo restates.

## §9. Recommendation

**Do not cut over on option (a) as ruled.** Measured against independent references, it carries a
yield-proportional bias:
- against Alpaca, the cache fails 1,083 of 1,830 name-years and the candidate 59;
- in the 2011–15 captured era against yfinance, the cache has 1,725 name-years above 0.30 pp and
  the candidate 92.
Both of those numbers measure the drip REMOVAL, and that part is independently established.

**Adopt (a′) v4 as the pre-seam convention for cutover day, stating plainly that:**
- it **FAILS** its pre-declared test: (i) 59 name-years, (ii) the 2013 p95, and (iii)(b). Every
  failing row traces to Stooq's corporate-action handling, its transient blocks, disagreement
  between the two references, one name with no reference, or the seam-day return. The cache
  fails 55 of the 59 as well;
- **the dividend RESTORATION in the missed eras is verified only for self-consistency**, plus
  SPY and the era-edge corroboration. It is not independently verified name by name;
- **12 files' no-reference missed-era spans and 54 files' pre-2003 spans are UNVERIFIED** and
  labelled. They are not guessed.

Then a separate unit, held to this same §1 test unchanged, for Stooq's corporate actions and
transient blocks. Until it lands, those name-years are labelled in the census.

This reopens the 2026-10-22 cutover ruling, so it is **the user's decision**. The alternatives:
- keep (a), labelling every pre-seam number "drip-biased, yield-proportional";
- delay the cutover until the second unit lands.

## §10. Findings beyond the brief

1. **Stooq transient blocks.** 4,517 since 1995, over 414 names: runs of bars about one dividend
   off that revert within days. They hit the cache's 2013 month-end closes and any return
   measured across them. This is a health-check candidate (MEDIUM).
2. **Stooq's corporate actions disagree with both references.**
   - In 2016–19: APD, BIIB, CAG, CHTR, GE, HLT, HON, HPE and VNO in (i). In (ii), MUR, VLO, LDOS
     and others in 2013, and KMB, PPL, SPG and OXY in 2014–15.
   - Inside the 2003–2011 missed era as well: VZ/Idearc 2006 (−3.7 pp) and VZ/Frontier 2010
     (−6.4 pp) went unapplied.
   - Yet MO/Kraft 2007, MO/PM 2008, CAH 2009 and AYI 2007 were applied.
   - So "spin-offs in the missed era were usually CAPTURED" (v3 text) is withdrawn. Stooq's
     spin-off handling is per event, in every era.
3. **Pre-2003 eras are per name.** KO and XOM lack every dividend from 1970, and BA from 1980 to
   1999. The investigation's "≈ 0 % missed 2000 → 2003-Q1" holds for most names but not all: in
   2001–02, 22–32 % of measured ex-dates were missed.
4. **POM's seam-day return is −90.8 %**, in the cache and in the candidate alike. The pre-seam
   Stooq level is about 10× Alpaca's. Not touched here.
5. **yfinance quirks.**
   - `Ticker.dividends` returns an EMPTY series for a delisted symbol rather than an error.
   - Yahoo answers "possibly delisted" for names it has dropped.
   - SATS, BBBY and PSKY now map to recent securities.
   - AT&T's dividends read ≈ 1.24–1.33 × Stooq's, depending on the estimator.
