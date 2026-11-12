---
name: drip-double-count-stooq-eras
description: Raw Stooq is dividend-adjusted only for ex-dates ~2011-Q2..2022-Q4 (and ~2000..2003-Q1); T-082b's drip slope is the 2023+ missed-dividend gap extrapolated back -> +b overcount 2011..seam, undercount 2003-2010
metadata:
  type: project
---

Measured 2026-11-11 (read-only, 38 names + 531-name T-265 sweep):

- Raw Stooq bundle (`data/raw/stooq/daily/us/**`) captures 100% of dividends with ex-dates ~2011-Q2 -> 2022-Q4, ~0% for 2003-Q2 -> 2011-Q1 and 2023-Q1 onward; ~100% 2000 -> 2003-Q1 for most names (MO missed from 2001). It is NOT "split-only" and NOT "total return"; it is era-windowed. Quarterly fraction-missed probe pinned the edges.
- T-082b `fit_ratio_loglinear` (two-endpoint, not a regression) therefore measures Stooq's 2023+ missed dividends spread over the overlap: b ~= 0.55 x recent yield (2020-04-09 seam) / ~0.40 x (2018-01-02 seam). `apply_dividend_strip` applies exp(b t) to ALL pre-seam bars -> exact +b/yr double count where Stooq is already TR (2011-Q2..seam, 2000-02), net undercount 2003-2010.
- cache - raw Stooq pre-seam == b to 0.02 pp (raw bundle is the merge input). cache - T-265 == b within 0.5 pp on 519/531 names; outliers are spin-offs/reused tickers.
- Full-span averages (cutover proposal section 1, "dispersion, not systematic", median -0.10 %/yr) cancel the two eras. Lesson: never average a convention defect over eras with opposite signs; measure per calendar year.

**Why:** the ruled cutover option (a) keeps pre-seam bars scaled by a CONSTANT (`engines/data_manager/tr_writer.py:45-55`), so the overcount survives cutover verbatim.
**How to apply:** any pre-2020-04 equity-book number on the cache carries a yield-proportional return bias; check the seam group (2018-01-02 x474 vs 2020-04-09 x100) before quoting. Scratch scripts were under the session scratchpad `divcheck/` (fetch_yf.py, analyze.py, summarize.py, universe.py).

Pitfalls/quirks logged:
- `data/research/t265/prices/<T>.parquet` (Alpaca adjustment='all', 2016-01-04+, 4,674 tickers) is a free universe-wide TR reference; matches yfinance Adj Close to 0.003 pp median except spin-off years and AT&T.
- yfinance AT&T (T) Adj Close runs ~1.7 pp/yr above BOTH Alpaca 'all' and Stooq 2012-2022 -- don't use yf as T's reference.
- `_merge_meta.json` `implied_annual_div_yield_pct` = 1-exp(-b*252) but b is per CALENDAR day -> understates the applied drift by 365/252. Use b*365.25.
- pandas: `df.xs` is a DataFrame method -- name a column `xs` and attribute access silently returns the method. Use `df["xs"]`.
