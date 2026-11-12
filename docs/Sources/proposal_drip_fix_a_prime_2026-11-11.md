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

<!-- §2 onward (the build, the acceptance result, the runbook consequence, the re-run list, the
risks and the recommendation) is written AFTER the candidate is built and tested. -->
