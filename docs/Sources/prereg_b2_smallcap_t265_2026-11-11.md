---
task_id: T-381 (B-2)
title: Pre-registration — small-cap momentum and insider-buying clusters on the T-265 panel
date: 2026-11-11
worker: edge-analyst subagent (in-session, director-dispatched with the user's go-ahead)
branch: research/smallcap-t265-b2
status: DRAFT — awaiting the director's acknowledgment and rulings R1–R9 (§11). NO strategy return, signal, cluster or event has been computed. The census in §3 read inputs only (benchmark returns read once, to identify the price convention).
N_trials: +2 at the run (momentum family; insider family) — §9
---

# B-2 — does small-cap momentum or insider-cluster buying pay on the survivorship-corrected panel?

## 1. The question (H1s and refutations verbatim from the brief)

Brief: `docs/Sources/alpha_frontier_program_2026_09_30.md` §3.2 "B-2" (+ the common SETUP / HARD
CONSTRAINTS block). T-249 killed small-cap momentum with a literature survivorship haircut, not a
measurement. T-265 built a small-cap panel that includes some pre-2020 delistings and ran only PEAD on
it (null). T-144 tested insider clusters on S&P names only.

**Momentum H1 (verbatim):** 25%-satellite Δ log wealth ci_low > 0 vs SPY-TR on 2016-01→2026-06 with
delistings at the frozen rule.
**Momentum refutation (verbatim):** ci_low ≤ 0 in the base arm ⇒ T-249's kill stands, now measured.

**Insider H1 (verbatim):** CAR(0,126) t_HAC > 2.0 for clusters ≥ 3 AND satellite ci_low > 0.
**Insider refutation (verbatim):** t_HAC < 2 ⇒ insider clusters are priced in small caps too — close
the region.

**DSR line (verbatim):** 10-year window: any standalone SR quoted must carry the DSR line (≈ 0.9 at
N≈260, 10 yr) as context; the satellite paired ci_low is the gate. N_trials += 2.

**What the census changes (§3):** the windows (§3.6), the delisting rule (§3.2), the Form 4 source
(§3.5), and above all **what a PASS can mean**: the T-265 panel is NOT survivorship-complete (§3.1). It
prices about one in five firms that stopped filing inside the window, against four in five that kept
filing. Under the asymmetric rule in §2.7 a FAIL here is a strong result and a PASS is only an upper
bound.

## 2. THE HARD PRE-COMMITMENTS (the anti-overfit controls)

1. **No tuning after any output.** Every threshold in §4–§5 is fixed here. A number that looks wrong is
   REPORTED, never re-specified.
2. **One gate arm per family.** Momentum: the base arm (§4.1, the delisting rule as ruled in R2, costs
   as ruled in R3). Insider: clusters ≥ 3 (§4.2). Every other arm in §5 is a pre-named diagnostic and
   **cannot meet H1**.
3. **No window shopping.** The windows in §3.6 come from input availability alone. No sub-window can
   replace them. Per-year rows are descriptive.
4. **No sign flipping.** Momentum is long the top decile of 12-1 return (+). Insider clusters are long
   (+). A significant NEGATIVE CAR is reported as a NEGATIVE result, never as a short signal (a Roth
   cannot short).
5. **Nothing is deployed and nothing is promoted.** A survivor of either family goes to Engine F's
   gates and to the survivorship re-verification in §2.7. B-2 never touches `BacktestController`,
   `engines/`, the governor, or the run registry.
6. **No PEAD × insider.** That is conditional brief C-1, and it runs only if this insider arm shows
   t_HAC > 2.
7. **★ Asymmetric interpretation (census-forced, §3.1; ruling R1).** The panel carries roughly 20% of
   the firms that died inside the window. The literature's survivorship bias inflates small-cap long
   returns (Shumway 1997; T-249's wall). For the insider event study, the missing firms plausibly
   include distressed issuers whose clusters preceded failure. So on this panel:
   - **H1 NOT met ⇒ the refutation stands**, robust in the direction the literature establishes (more
     deaths would push the result down, not up). It is not proven for every mechanism: a missing
     acquired firm removes a takeover premium.
   - **H1 met ⇒ "UPPER BOUND — not certifiable"**: no claim, and re-verification on the recovered panel
     (§3.1 remedy) is MANDATORY before any further step, under `[NN-SUBSTRATE-REVERIFY]`.

## 3. Pre-run census (inputs only; measured 2026-11-11 in this worktree)

The census computed no strategy returns, signals, clusters or events. The only returns read were the
twins' and four large caps' calendar-year returns, used to identify the price convention (§3.4). The
nine scratch census scripts are preserved and will be committed UNCHANGED with Phase 2 under
`scripts/b2_census_t381/`. Each figure below was produced by executing them.

### 3.1 ★ The T-265 panel is survivorship-CORRECTED, not survivorship-COMPLETE
T-265's universe is every CIK in the EDGAR XBRL diluted-EPS frames (CY2013Q1–CY2026Q1). It mapped CIK
to ticker through the **live** SEC ticker list, plus name-matching against Alpaca assets, and fetched
SIP bars for the mapped tickers. The live list holds only current filers, so the 36% join loss falls
mostly on dead firms:

| CIKs filing inside the window (last EPS frame ≥ 2016Q1) | n | mapped to a ticker | **priced** |
|---|---|---|---|
| continuing (last frame ≥ 2025Q1) | 5,180 | 90.5% | **78.9%** |
| ceased filing (last frame ≤ 2024Q4) | 3,064 | 37.2% | **19.8%** |
| … ceased 2016 / 2017 / 2018 | 356 / 289 / 260 | 19% / 18% / 20% | **6.7% / 3.8% / 9.6%** |
| … ceased 2019 / 2020 / 2021 | 251 / 203 / 294 | 46% / 66% / 56% | 27.1% / 46.8% / 45.9% |
| … ceased 2022 / 2023 / 2024 | 411 / 511 / 489 | 38% / 35% / 44% | 21.2% / 13.5% / 19.2% |

"Ceased filing" also includes firms that were never exchange-listed, or that only stopped tagging
diluted EPS. Treat the gap between 79% and 20% as the size of the problem, not as an exact measure.

**Inside the trading universe** (20-day median dollar ADV $1M–$200M; deaths are counted at the last
TRADED bar, with the segment rule in §3.3):

| year | mean names in band | in-band deaths next month | annual death rate |
|---|---|---|---|
| 2016 | 1,544 | 4 | 0.3% |
| 2017 | 1,818 | 8 | 0.4% |
| 2018 | 1,914 | 7 | 0.4% |
| 2019 | 1,981 | 24 | 1.2% |
| 2020 | 2,096 | 59 | 2.8% |
| 2021 | 2,443 | 100 | 4.1% |
| 2022 | 2,225 | 61 | 2.7% |
| 2023 | 2,195 | 7 | 0.3% |
| 2024 | 2,268 | 4 | 0.2% |
| 2025 | 2,369 | 16 | 0.7% |

The order-of-magnitude benchmark is the CRSP common-stock delisting rate, mid-to-high single digits
per year (Doidge-Karolyi-Stulz 2017). That is a literature benchmark, not a measurement on this
universe. The panel sees about 1/10 to 1/20 of the expected deaths in 2016–2018 and 2023–2025, and
about half in 2020–2022, when Alpaca's inactive list recovered more names. The cross-section also grows
from 2,735 priced names alive in 2016 to 4,213 in 2025 (+54%), the shape of a survivor-biased panel.

**Remedy, measured but not executed (it needs an API call; ruling R1):** Form 4 SUBMISSION rows carry
the issuer's own ticker at each filing (`ISSUERTRADINGSYMBOL`). This gives a CIK→ticker link for dead
firms. Of the 2,457 ceased-in-window CIKs with no prices, **2,097 have a clean `[A-Z]{1,5}` Form 4
symbol, and 1,993 of those symbols are not yet a T-265 price file.** A one-time Alpaca SIP fetch of
about 2,000 symbols would close most of the hole. The SIP entitlement is already owned, so the
marginal cost is $0, but the fetch needs a network/API call that this brief forbids. Reused symbols
would need the CIK's EPS-frame life span to cut out the wrong company's bars.

### 3.2 Delisting codes do not exist anywhere in the cached data
- The T-265 stages (`prices/`, `cik_ticker*.parquet`, `eps_*.parquet`, `shares_panel`, `events*`,
  `ann_dates`) carry **no delisting date, code or reason**. T-265 had no code either: its "dead" flag
  was a derived heuristic (the price series is truncated inside the window and there is no later EPS
  filing).
- The cached EDGAR form and item data cannot fill the gap. The `data/edgar/8k/panel_8k_items.parquet`
  (8-K Item 1.03 bankruptcy, Item 3.01 delisting notice) covers **624 CIKs, the S&P names**, and
  `data/edgar/raw/` submissions cover about 600. Small caps are not covered, and fetching more is
  forbidden.
- The Alpaca `inactive` flag was shown unreliable by T-265 (real delistings flagged active).

The frozen rule's "bankruptcy/deregistration codes → −100%" branch therefore **cannot be populated**.
The rule also says "Shumway −30% unless a last trade price exists". In bar data every delisting has a
last trade price and none has a post-delisting price. Read as CRSP's "unless a delisting return
exists", the clause never triggers. The proposed rule is in §4.3 (ruling R2).

### 3.3 Price-file artefacts the harness must handle (counted, not filled)
| artefact | count | treatment (§4.3) |
|---|---|---|
| price files / bars | 4,674 / 9,060,366 (44 files < 60 bars) | files < 60 bars excluded (T-265 `_load_prices` rule) |
| span | 2016-01-04 → 2026-06-30 (2,577 files start 2016-01-04; 4,172 still trading on 2026-06-26) | — |
| zero-volume bars | 220,696 (2.44%) in 1,307 files | not a trade: never an entry or exit price |
| **phantom TRAILING zero-volume runs** (≥ 5 bars) | 151 files (45 forward-filled flat to 2025-03-21; e.g. MDRX after 2024-02-28, AATC after 2022-12-29) | the death is the last TRADED bar; the phantom bars are ignored |
| **interior no-trade runs ≥ 63 market days** (ticker reuse / splice) | 141 files (e.g. MBLY: no trade 2017-08-31 → 2022-10-26; EDR: Education Realty to 2018-09-19, Endeavor from 2021-04-29) | split into segments; a non-final segment end is a death; the next segment is a NEW security |
| interior no-trade runs 21–62 days | 57 files | trading halts: held through, priced at the next trade |
| terminations by last traded bar < 2026-06-01 | 532 (by year 11, 7, 9, 30, 83, 126, 95, 43, 52, 53, 23) | §4.3 |
| tickers mapped from more than one CIK | 71 tickers / 145 CIKs | insider arm: events on these are dropped (counted) |
| non-positive closes | 0 | — |

### 3.4 Price convention — TOTAL RETURN, consistent with the twins (no dividend bias)
- T-265 fetched SIP bars with `adjustment='all'` (`scripts/smallcap_pead_pilot_t265.py:176`): splits,
  cash dividends and spin-offs, back-adjusted as of the 2026-07 fetch.
- **Verified by execution.** AAPL growth 2016-01-04→2026-04-15 matches the canonical TR cache to 1e-4
  (11.2265 vs 11.2254). MO's T-265 yearly returns equal Stooq's dividend-adjusted series in 2016–2021
  (2016–2019: 22.16 / 9.44 / −27.14 / 7.88%) and equal the TR cache in 2022–2025 (4.40 / −3.70 / 40.76 / 18.17%).
  The T-265 prices are total return throughout.
- **Twins:** `data/processed/tr_reconciled/{SPY,IWM}_1d.csv` (T-256) run 2005-02-22 → **2026-05-22**,
  and `BIL` (cash) 2007-05-30 → 2026-05-22. SPY-TR calendar-year returns 2016–2025 (12.0, 21.7, −4.6,
  31.2, 18.3, 28.7, −18.2, 26.2, 24.9, 17.7%) and IWM-TR (21.6, 14.6, −11.1, 25.4, 20.0, 14.5, −20.5,
  16.8, 11.4, 12.7%) match the published total returns. Both legs are therefore TR, and **no dividend
  bias runs between the arms and the twins.**
- **Residual bias (disclosed):** dollar ADV = adjusted close × volume, which understates early-sample
  dollar volume for dividend payers by the cumulative dividend factor. For example, MO's adjusted
  2016-01-04 close is 28.52, roughly half its traded price. Small-cap non-payers are unaffected. The effect is that a few early
  payers fall below the $1M floor.
- **Side finding, OUT OF SCOPE, flagged for the director:** the canonical `data/processed/{MO,T,VZ,O,
  XOM,KO}_1d.csv` exceed the T-265 and Stooq returns by about the dividend yield, every year 2016–2019
  (MO 2016: 27.82% vs 22.16%; 2018: −23.71% vs −27.14%), and match exactly from 2021. That looks like a
  pre-seam DRIP layered on Stooq bars that were already dividend-adjusted. B-2 does not read those
  files.

### 3.5 Form 4 — the panel named in the brief cannot do a CIK join; its upstream can
| | `data/insider_sec/` (agent-d, the brief's panel) | `data/edgar/insider_zips/` (main tree; the SEC Form 3/4/5 quarterly datasets the panel was flattened from, `scripts/wire_sec_insider_feed_t136.py`) |
|---|---|---|
| span / size | 21,057 files, **6,778,137 rows**, filing_date 2006-01-03 → 2026-03-31 | 81 quarters 2006q1 → 2026q1; 7,215,506 non-derivative rows; 3,884,991 Form 4 submissions; **808,146 P/A Form 4 rows** |
| issuer CIK | **ABSENT** (keyed by the filed ticker) | `ISSUERCIK` |
| distinct-insider id | name string only | `RPTOWNERCIK` |
| transaction code / A-D | yes | `TRANS_CODE`, `TRANS_ACQUIRED_DISP_CD` |
| 10b5-1 flag | **ABSENT** | `AFF10B5ONE` from **2023q1 only**; before that, footnote text only (`FOOTNOTES.tsv`) |
| acceptance timestamp | **ABSENT** | **ABSENT** — `FILING_DATE` (a date) only |
| form type / amendments | lost | `DOCUMENT_TYPE` (`4`, `4/A`, `5`) |

**Proposal (ruling R4): source the insider arm from the zips**, the same SEC dataset upstream of the
panel, read one quarter at a time with only the needed columns (a full scan took 27 s and peaked at
1.1 GB RSS). The brief's own rule "join by CIK, not ticker" makes this necessary: the panel has no CIK.

**Join census (P/A Form 4 rows filed 2016-01-01..2025-12-31: 305,209 rows, 7,770 issuer CIKs):**

| join | issuer CIKs joined | rows joined |
|---|---|---|
| **by CIK → T-265 priced map** | **52.4%** | **64.4%** (by year 53.1, 49.8, 71.6, 70.4, 63.5, 65.7, 69.9, 61.3, 64.6, 70.5%) |
| by filed ticker → T-265 ticker (the insider_sec way) | 47.8% | 57.7% |
| CIK-only / ticker-only / both | 476 / 116 / 3,599 | — |
| ticker join that lands on a DIFFERENT CIK (mis-join) | 126 issuer CIKs | — |

The CIK join is strictly better, but **it cannot recover the 36% CIK→ticker loss on the price side**: a
CIK with no T-265 ticker has no prices. The brief's "avoids the 36% loss" holds only for the Form 4
side. The remedy in §3.1 is the fix.

Coverage of the priced universe: **91–92% of alive T-265 names have at least one Form 4 each year;
41–52% have at least one open-market purchase.**

10b5-1 among P/A Form 4 rows: structured flag true on 971 / 1,594 / 1,653 rows (2023 / 2024 / 2025).
Footnotes mention "10b5-1" on 1,137–17,847 rows a year in 2016–2025, with a 2018–2019 spike (17,847 /
12,211) that looks like a few issuers' purchase plans. In-window P/A Form 4 rows by year (2016–2025):
33,967 / 27,505 / 44,722 / 38,556 / 30,409 / 25,544 / 33,280 / 27,880 / 21,856 / 21,490.

### 3.6 Windows — set by input availability (brief: 2016-01 → 2026-06)
| | start | end | length | binding input |
|---|---|---|---|---|
| **momentum** holding months | **2017-02** (first formation 2017-01-31: the 12-1 signal needs the 2016-01-29 month-end) | **2026-04** (last formation 2026-03-31) | **111 months = 9.25 yr** | prices start 2016-01-04; SPY/IWM TR end 2026-05-22 |
| **insider event study** entries | **2016-02-02** (filings ≥ 2016-02-01, the first day with a 20-day ADV) | **2025-11-19** (last entry whose 126-day window ends ≤ 2026-05-22) | ≈ 9.8 yr of entries | TR twins end; Form 4 data ends 2026-03-31 |
| **insider satellite** months | **2016-02** | **2026-04** | **123 months = 10.25 yr** | as above; entries through 2026-03-31 (Form 4 end); positions held into April 2026 |

### 3.7 Honest-N and the DSR line (read, never written)
`core.measurement.mbl_gate.compute_n_effective_correlated()` against the pinned
`data/observability/run_registry.sqlite` (pin verified, read-only `mode=ro`): **N_raw = 231 → N_eff =
36.9** (conservative; equicorrelated 33.5, ONC 36.9). SR required under MinBTL (exact `E[max_N]/√T`):

| window | at N_eff 36.9 | at N ≈ 260 (the brief's line) |
|---|---|---|
| momentum 9.25 yr | **0.71** | **0.94** |
| insider satellite 10.25 yr | **0.67** | **0.89** |

Any standalone SR in the verdict carries this line. The satellite paired ci_low is the gate. B-2 does
not write the registry. The director records +2.

### 3.8 Environment
`python -m pytest tests/test_contracts.py -q`: **28 passed, 1 xfailed, 1 FAILED** —
`test_layer3a_capability_ledger_source_files_exist`. The failure is environmental: the safe worktree
layout leaves `data/governor/` empty and `edges.yml` is gitignored (the known governor-set lock).
Nothing was installed.

## 4. Construction (frozen at acknowledgment)

### 4.1 Momentum arm — `scripts/smallcap_momentum_t265_b2.py`
- **Calendar:** trading days of `tr_reconciled/SPY_1d.csv`. A month-end is the last trading day of the
  calendar month.
- **Security:** a price-file SEGMENT (§3.3): traded bars only (volume > 0), split at no-trade runs of
  ≥ 63 market days.
- **Eligible at formation t:** (a) at least 12 month-ends of segment history: the last traded close in
  month t−12 and in month t−1 both exist inside the segment; (b) a traded bar ON day t; (c) 20-day
  median dollar ADV at t in **[$1M, $200M)**. ADV is close × volume on the market calendar over the
  last 20 market days, with a no-trade day counted as 0. The band's upper edge is ruling R5.
- **Signal:** 12-1 return = close(t−1) / close(t−12) − 1, using last traded closes in those months.
- **Portfolio:** top decile by signal, `k = max(10, floor(n_eligible / 10))` names, ties broken by
  ticker. Equal weight, bought at the close of t and held one month to the close of t+1 (the last traded
  close ≤ the t+1 month-end; a halt shorter than 63 days prices at the stale last trade).
- **Cost (ruling R3):** at each rebalance, Σ over names of |w_target − w_drifted| × (RT/2), with RT by
  the name's ADV bucket at t: **35 bps RT for $20M–$200M, 75 bps RT for $1M–$20M** (brief). A name
  leaving the decile is charged at its bucket at t. Delisted proceeds carry no exit cost.
- **ADV cap 2% per name** at a declared sleeve notional of **$250,000** (25% of a $1M account, above
  every current user tier). Weight above the cap goes to cash (BIL TR). The census reports capacity:
  the smallest sleeve AUM at which any position breaches 2% of ADV, in the median month.
- **Twins:** SPY TR and IWM TR month-end to month-end over the same holding months. Cash is BIL TR.

### 4.2 Insider arm — `scripts/smallcap_insider_t265_b2.py`
- **Source:** the SEC zips (ruling R4). Rows: `DOCUMENT_TYPE == '4'` (originals; amendments 4/A and
  Form 5 excluded, because the original is what was public at its date); non-derivative
  `TRANS_CODE == 'P'` AND `TRANS_ACQUIRED_DISP_CD == 'A'`. Code P already excludes option exercises
  (M/X/C) and awards (A). Also required: shares > 0, price > 0, and `SECURITY_TITLE` not containing
  "prefer" (case-insensitive).
- **10b5-1 exclusion:** drop the row if its submission has `AFF10B5ONE` ∈ {1, true} (2023q1+) OR any
  footnote of the same accession matches `/10b5-?1/i` (all years). Footnote matching is per accession,
  so it can slightly over-exclude.
- **Insider id:** `RPTOWNERCIK`. A joint filing (one accession, several owners) counts as ONE insider:
  the minimum `RPTOWNERCIK` on the accession. All Section 16 reporting owners count (officers,
  directors, 10% owners), as in T-144.
- **Cohen-Malloy-Pomorski filter (brief wording):** in calendar year Y, an insider is ROUTINE at issuer
  j, and all of their year-Y purchases at j are dropped from cluster counting, if in ≥ 3 distinct prior
  calendar years (< Y, data from 2006) they made a P/A purchase at j in the SAME calendar month. Routine
  status is judged on the history of ALL P/A Form 4 rows, including 10b5-1-flagged ones. This departs
  from CMP 2012 in two ways, both stated: it uses buys only, and the years need not be consecutive.
- **Cluster (PIT):** on each filing date d of issuer j, count the distinct non-routine, non-10b5-1
  insiders whose purchases have `FILING_DATE ≤ d` and `TRANS_DATE ∈ [d − 30 calendar days, d]`. The
  **event** is the first d where the count is ≥ 3. **PIT cluster size** is that count at d, bucketed
  {3, 4, 5+}. **Cool-off:** no new event for issuer j until the previous event's 126-trading-day hold
  has ended.
- **Join:** `ISSUERCIK` → `cik_ticker_final` → a priced file (≥ 60 bars). Events are dropped and
  COUNTED if their ticker maps from more than one CIK, if their ticker has a ≥ 63-day splice, or if the
  name has no traded bar within 5 market days after d.
- **Entry (PIT):** the close of the first trading day strictly after `FILING_DATE` on which the name
  trades (no acceptance timestamp exists, §3.5). Day 0 = the entry close.
- **Universe at the event:** 20-day median dollar ADV at d in **[$1M, $200M)**, the same band as
  momentum. Events in sub-$1M names are counted and their mean CAR is shown as a descriptive line only.
- **Event study:** CAR(0,126) = Σ_{k=1..126} (r_i,k − r_IWM,k), with IWM TR. After a death the
  proceeds earn BIL TR, so r_i,k = r_BIL,k. Events need the full 126-day twin window (entries ≤
  2025-11-19). **t_HAC:** Newey-West t of the mean over the series of monthly-cohort mean CARs (cohort =
  entry month; months without events are skipped), **6 lags** (126 trading days ≈ 6 months of overlap).
  Reported for clusters ≥ 3 (the gate) and for each size bucket {3, 4, 5+} (descriptive), with n,
  mean, median, % > 0, and a 1%/99% winsorized mean (descriptive; it cannot rescue H1).
- **Portfolio:** calendar time, daily. A position enters at the entry close and exits at the close of
  the 126th trading day after (or dies under §4.3). The book is EQUAL-WEIGHT across live positions,
  re-equalized daily (the standard calendar-time portfolio; the implicit rebalancing turnover is NOT
  charged, a disclosed upward bias). **Cap 40 live positions:** a new event arriving when 40 are live is
  SKIPPED (no displacement; same-day arrivals ordered by `ISSUERCIK`) and counted. **75 bps RT,** half
  charged at entry and half at exit on the position's weight at that time. With zero live positions
  the book holds BIL TR. Entries are allowed through 2026-03-31.
- **Census:** clusters/yr, names/yr, share of the universe with any Form 4, join coverage, every drop
  counted.

### 4.3 Delisting rule (census-forced; ruling R2)
A **death** is the last TRADED bar of a segment that is not followed by another trade in that segment
before 2026-05-22. A held position's return to the death is (last traded close / entry price) and then:

| arm | applied at the death | role |
|---|---|---|
| **BASE (gate)** | **D = −30% (Shumway 1997) on every death.** The −100% branch is empty because no code can identify bankruptcy or deregistration (§3.2). | gate |
| STRESS (brief) | D = −100% on every death | diagnostic |
| LAST-PRICE | D = 0 (T-265's naive arm) | diagnostic: brackets the base from above |

The proceeds (1 + D) × the position value sit in BIL TR until the next rebalance (momentum) or the end
of the 126-day window (insider). **Known bias of the base:** acquisitions (true D ≈ 0) and SPAC trust
liquidations (D ≈ 0) are penalized −30%, which is conservative for a long-only winners decile. The
LAST-PRICE arm shows the size of that penalty.

### 4.4 The satellite gate and the bootstrap (both arms)
- **Monthly returns.** The insider book is compounded from daily. The satellite is 75% SPY TR + 25% arm,
  rebalanced monthly. **Δ log wealth** = Σ_t [ln(1 + r_blend,t) − ln(1 + r_SPY,t)].
- **Paired moving-block bootstrap:** `MetricsEngine.bootstrap_distribution` on the MONTH INDICES (the
  B-1 pattern: one draw serves the arm, the twins and every diagnostic in a window, so all are paired).
  **1,000 iterations, seed 0, AUTO block length** = max(5, round(n^(1/3))) per that function (n = 111
  → 5 months; n = 123 → 5), two-sided 95% percentile CI. `ci_low` is the gate.
- Standalone Sharpe and Sortino are computed from monthly returns, rf = 0, ×√12, with the same bootstrap.
  MaxDD, CAGR, turnover, cost drag (bps/yr) and capacity are reported. The IWM-TR sleeve (75% SPY +
  25% IWM) Δ log wealth vs SPY is a pre-named diagnostic, ruling R6.

### 4.5 Fail-closed (`[NN-FAIL-CLOSED]`/`[NN-CENSUS]`): the harness HALTS (non-zero exit, no headline) if
- momentum: any formation has fewer than 500 eligible names or fewer than 50 in the decile; any holding
  month lacks a SPY / IWM / BIL TR return; a held name's month return is NaN without a death
  classification; fewer than 100 holding months;
- insider: CIK-join row coverage of in-window P/A Form 4 rows is **< 63.0%** (measured 64.4%, §3.5);
  zero events at size ≥ 3; an event CAR is NaN without a death classification; a twin is missing on any
  day of a CAR window or a book day; fewer than 100 satellite months;
- both: the bootstrap gets fewer than 24 months; any census count disagrees with its recomputation; or
  any input file named in the census is missing. `MetricsEngine.bootstrap_distribution` returns zeros
  for fewer than 4 observations, so the harness guards that itself.

### 4.6 Smoke, determinism, outputs
Each arm is smoked on its window's **first 12 months** (momentum formations 2017-01 → 2017-12; insider
entries 2016-02 → 2017-01). The first formation dates and first events are checked by eye before the
full run. Run with `PYTHONHASHSEED=0` and single-threaded BLAS pins (the B-1 pins). **Determinism ×2:**
two full runs must give an identical md5 of the canonical results JSON (floats to 12 significant
digits, keys sorted) before any number is quoted. Outputs go to `data/research/b2/`. In this worktree
that is a symlink into the main tree's gitignored `data/research/`, per the dispatch.

## 5. Arms and families

| family | gate arm (meets or fails H1) | pre-named diagnostics (cannot meet H1) |
|---|---|---|
| **momentum (+1 N_trials)** | base: §4.1 + §4.3 BASE + R3 cost; 25%-satellite Δ log wealth vs SPY TR `ci_low` | STRESS −100% · LAST-PRICE · **SURVIVOR-ONLY** (segments still trading at the window end, the same construction; the within-panel haircut = survivor-only − base, a LOWER bound on the true haircut since the base itself lacks most deaths) · T-249 cost basis (2× the brief, §11 R3) · IWM-sleeve · per-year table · standalone Sharpe/Sortino with ci_low + the DSR line · **T-249 as published** (Stooq 2006–2025, survivor-only, full-window ADV universe = look-ahead, per-side 35/75 bps: gross Sharpe 3.21, net-tier Sharpe 2.47 / Sortino 3.71 ci_low 0.49 / CAGR 10.8%), shown beside, not recomputed |
| **insider (+1 N_trials)** | clusters ≥ 3: CAR(0,126) t_HAC > 2.0 AND 25%-satellite Δ log wealth vs SPY TR `ci_low` > 0 | size buckets {3, 4, 5+} · STRESS and LAST-PRICE CARs and satellites · winsorized mean · median · sub-$1M-ADV events (count and mean CAR) · IWM-sleeve · per-year event counts |

## 6. Pre-named outcomes

| outcome | what it means | what it does NOT mean |
|---|---|---|
| momentum base `ci_low ≤ 0` | **T-249's kill stands, now measured** on a panel that still flatters the arm (§2.7) | not evidence that no small-cap momentum premium exists. The gate's power is low (§8.1): it detects only a large edge. |
| momentum base `ci_low > 0` | **UPPER BOUND, not certifiable.** Mandatory re-verify on the recovered panel (§3.1 remedy) | not deployable; no promotion |
| base passes, STRESS fails | the pass depends on the delisting assumption, which is unknowable here | — |
| base passes, cost sensitivity (2×) fails | cost-fragile; the T-249 cost basis kills it | — |
| insider t_HAC < 2 at size ≥ 3 | **insider clusters are priced in small caps too — close the region** (verbatim). C-1 does not run. | not a verdict on 10% holders vs officers, value thresholds, or non-cluster single buys |
| insider t_HAC > 2 but satellite `ci_low ≤ 0` | a real event-time effect that does not pay as a 25% satellite over 10 years. **H1 NOT met.** C-1 may run (its trigger is t_HAC > 2 alone). | not deployable |
| insider both legs met | UPPER BOUND, not certifiable (§2.7); mandatory re-verify | not deployable |
| a significant NEGATIVE CAR | reported as negative; never flipped (§2.4) | not a short signal |

## 7. Substrate + conventions
Reads `data/research/t265/` (the T-265 stages, built 2026-07-02, symlinked read-only from the main
tree), `data/edgar/insider_zips/` (read-only), `data/processed/tr_reconciled/{SPY,IWM,BIL}_1d.csv`,
and nothing in `data/processed/` beyond those. It never imports `engines/` or `backtester/`, and from
`core/` only `MetricsEngine` (bootstrap, ratios) and `mbl_gate` (read). It loads no `.env` and makes no
network call. **`[NN-SUBSTRATE-REVERIFY]`: any verdict here is "measured on the T-265 vintage +
T-256 twins; re-verify required after cutover"**, and a PASS also needs the recovered panel (§2.7).
**Memory (8 GB host, a parallel agent):** the zips are read one quarter at a time with `usecols`; the
price panel holds close and volume as float32 for about 4,700 segments × 2,600 days (about 100 MB);
the Form 4 rows and the price panel are never fully resident together.

## 8. Predictions (frozen; the verdict compares against them)

### 8.1 Power — what the satellite gate can detect (an assumption, not a measurement; no return computed)
Δ log wealth ≈ Σ 0.25 × (r_arm − r_SPY). Assume a small-cap decile book with 20%/yr tracking error to
SPY (15–25% plausible). Then sd(monthly Δ) ≈ 1.44%, and over 111 months SE(ΣΔ) ≈ 15%. `ci_low > 0`
needs a point of about +30% total, **≈ +3.2%/yr on the blend, i.e. the arm beating SPY TR by roughly
10–16%/yr net.** Over 2016–2025 IWM TR trailed SPY TR in eight of ten calendar years (§3.4). The
satellite gate therefore detects only a very large edge. A null on it is "not demonstrable at this
length", and the event-study t_HAC is the more powerful instrument.

### 8.2 Point predictions
- **Momentum:** base satellite Δ log wealth point **< 0**, ci_low clearly < 0. **H1 NOT met (≈ 93%).**
  Standalone net Sharpe 0.3–0.7, below the 0.71 DSR line. Within-panel haircut (survivor-only − base)
  +1 to +3%/yr. STRESS lowers the base by < 1%/yr: winners rarely die next month. LAST-PRICE raises it
  by < 0.5%/yr.
- **Insider:** size ≥ 3 mean CAR(0,126) vs IWM **+2% to +4%, t_HAC 1.5–2.5. P(t_HAC > 2) ≈ 40%.**
  Size buckets weakly increasing (5+ > 4 > 3), none individually significant. Satellite ci_low < 0.
  **H1 NOT met (≈ 95%).** Sub-$1M-ADV events carry a larger mean CAR than in-band ones (the
  untradeable-alpha pattern).
- **Census:** in-band cluster events (size ≥ 3) of roughly 150–400 per year, fewest in 2024–2025
  (where in-window P/A rows are lowest, §3.5); the 40-name cap binds in fewer than 10% of book-days.

## 9. Honest prior + N_trials
- Brief priors: momentum 30%, insider 30%. **Restated before any data, because of the census and the
  power arithmetic, not because of any result:** P(momentum H1 met on this panel) ≈ 7%, and P(it
  survives re-verification on a recovered panel | met) ≈ 40%, so **≈ 3% that B-2 finds a real momentum
  satellite.** Insider: P(H1 met) ≈ 5%. P(t_HAC > 2 alone) ≈ 40%, the event-time question the brief
  most needs answered.
- **N_trials: +2** (momentum family; insider family), as briefed. The B-1 ruling counted "what could be
  quoted". It changes nothing here, because §2.2 pre-commits that no diagnostic can be quoted as
  meeting H1. If the director rules the size buckets quotable, the count rises by up to +3; R7 asks.

## 10. Scope exclusions
No PEAD × insider (C-1). No value thresholds, role filters, or K ∈ {2, 4} cluster definitions as
gates. No quintiles, other lookbacks (6-1, 3-1), or price filters ($5). No window other than §3.6. No
fetch, no API, no `.env`. No BacktestController. No edits outside `scripts/`, `docs/`, and the gitignored
`data/research/b2/`.

## 11. Rulings requested at acknowledgment (my recommendation in bold)
- **R1 — survivorship (the load-bearing one).** (a) **Run now on T-265 as is, under the asymmetric
  interpretation of §2.7.** A fail closes the region a fortiori, and a pass triggers (b) before any
  claim. (b) Authorize the Form 4-symbol recovery and a one-time SIP fetch of about 2,000 dead-firm
  symbols first, then run once on the recovered panel. That needs an API call and the user's word.
  Recommendation: **(a)**. It costs nothing, and given §8 the likely outcome is a fail, which (a)
  settles.
- **R2 — delisting rule:** **BASE = Shumway −30% on every death** (the −100% branch cannot be populated,
  §3.2); STRESS −100%; LAST-PRICE 0%. The alternative is −100% when the last traded close is < $1 (the
  exchange minimum-bid rule) and −30% otherwise; that adds a threshold, so I do not recommend it.
- **R3 — cost basis.** The brief says "35 / 75 bps RT". T-249 charged 35 / 75 bps PER SIDE on Σ|Δw|
  (70 / 150 bps RT), and T-265 charged 2× (70 / 150 RT). The brief is half of both predecessors. **Gate
  on the brief (as frozen); report the T-249 basis as the pre-named sensitivity.**
- **R4 — Form 4 source:** **the SEC zips** (CIK, owner CIK, 10b5-1, form type). The insider_sec panel
  lacks all four.
- **R5 — universe upper edge:** **ADV < $200M**, the top of the brief's cost buckets and T-249's band.
  Names above $200M ADV have no defined cost: 113–525 names a year, excluded and counted.
- **R6 — second benchmark:** B-1 required beating both SPY and the EW sleeve. **Keep the brief's H1
  (vs SPY TR only) and report the IWM-sleeve as a diagnostic.** Over this decade IWM lagged SPY, so the
  IWM-sleeve bar is LOWER, not higher.
- **R7 — N_trials:** **+2.**
- **R8 — 10b5-1 before 2023:** **footnote regex** as in §4.2. The alternative is to exclude nothing
  before 2023.
- **R9 — CMP wording:** **the brief's version** (buys, ≥ 3 prior years, same month, non-consecutive).
  The alternative is CMP 2012 exactly (3 consecutive years, all trades).

## 12. Sequence
This prereg is committed alone. Then the director acknowledges and issues rulings R1–R9, and the
rulings are appended BELOW (this text is never edited). Then: build both scripts → smoke on the first 12
months → full run → determinism ×2 → verdict `docs/Audit/b2_smallcap_t265_verdict_2026-11-11.md` →
full suite → commit. No push, no merge.

## Reproduce the census
```
# scripts/b2_census_t381/ (committed unchanged with Phase 2). Each takes the worktree root first.
python census_prices.py <wt> <out>/price_census.parquet          # §3.3 spans, gaps, terminations
python census_delist.py <wt> <out>/price_census.parquet          # §3.1 filing-cessation vs priced
python census_adv.py <wt> <out>/adv_census.csv                   # band counts (R5)
python census_zerovol.py <wt> <out>/zerovol.parquet              # §3.3 phantom zero-volume bars
python census_splice.py <wt> <out>/splice.parquet                # §3.3 interior no-trade runs
python census_inband_deaths.py <wt> <out>/inband_deaths.csv      # §3.1 in-band death rate
python census_form4.py <wt> <out>/f4/                            # §3.5 zip scan (27 s, 1.1 GB peak)
python census_join.py <wt> <out>/f4/ <out>/price_census.parquet  # §3.5 CIK vs ticker join, coverage
python census_recover.py <wt> <out>/price_census.parquet         # §3.1 Form 4 symbol recovery
python -c "from core.measurement import mbl_gate as g; print(g.compute_n_effective(), g.compute_n_effective_correlated())"
```

---

## AMENDMENT 1 — director rulings R1–R9, 2026-11-11 (BINDING; pre-data)

The frozen text above is unchanged: md5 `d369e628779d93b8b10b95f9b8546d87`, the same at `780a49b`. This
amendment adds to it and rewrites nothing. It is committed together with the nine census scripts
(`scripts/b2_census_t381/`, byte-identical to the scratch copies that produced §3) BEFORE any strategy
return, signal, cluster or event exists. The commit time is earlier than every file under
`data/research/b2/`, and that ordering is the proof.

### A1.1 R1 Survivorship — option (a), the asymmetric rule (§2.7)
Run now on T-265. A FAIL stands. A PASS reads "upper bound — not certifiable on a survivor-biased
panel".
**Stop trigger for the fix:** any H1 met, OR any of the three pre-declared alpha diagnostics in A1.6
with t_HAC > +2.0. If it fires, STOP after the verdict draft and report. The director then rules on a
one-time Alpaca SIP fetch of the ~2,000 symbols recovered from Form 4 filings. Nothing is fetched now.

### A1.2 R2 Delistings — accepted, with the segment rules made explicit
- **BASE:** D = −30% (Shumway) on every death, at the last traded bar. **STRESS:** D = −100%.
  **No-penalty diagnostic:** D = 0. The proceeds earn BIL TR as in §4.3.
- **Phantom tails:** every file is truncated at its last bar with volume > 0, and that bar is the
  death. The census counted **151 files** with a trailing zero-volume run of ≥ 5 bars (45 of them
  forward-filled to 2025-03-21). Files with 1–4 trailing zero-volume bars are truncated the same way
  and counted separately.
- **Reused tickers:** **141 files** have an interior no-trade run of ≥ 63 market days. Each is split at
  that gap into separate securities. The first segment ends as a death under the base rule. The second
  starts fresh and needs its own full 12-1 lookback (momentum). The gap is counted on the
  `tr_reconciled/SPY` market calendar from 2016-01-04, exactly as `census_splice.py` counts it.
- **The harness re-measures both counts (151 and 141) and HALTS if either differs** (§4.5).
- **Death date, precisely:** a segment's last traded bar, when it is earlier than 2026-06-23 (the
  panel's final week). Every window ends on or before 2026-05-22, so a death after that date never
  enters a computation.
- **SURVIVOR-ONLY diagnostic:** segments with no death on or before 2026-05-22.

### A1.3 R3 Costs — the gate is the 70/150 bps round-trip basis (the T-249/T-265 basis)
- **Momentum gate:** 70 bps RT ($20M–$200M ADV) and 150 bps RT ($1M–$20M), charged as
  |Δw| × RT/2 per side. **Sensitivity:** the brief's 35/75 bps RT.
- **Insider gate:** I extend the ruling's reason ("stricter, pre-data; a pass at half the measured cost
  would be re-argued") to the insider arm. **Gate:** 70/150 bps RT by the name's ADV bucket at the
  event. **Sensitivity:** the brief's flat 75 bps RT. I flag this extension for the director.
- An exit from a name whose ADV has left the band is charged at 150 bps RT if ADV is below $20M or
  missing, and 70 bps if it is $20M or more.

### A1.4 R4–R9
- **R4** SEC zips: accepted.
- **R5** ADV < $200M: accepted.
- **R6** H1 against SPY TR only, with the IWM sleeve reported: accepted.
- **R7** N_trials +2: accepted.
- **R9** CMP filter in the brief's wording: accepted.
- **R8** footnote regex: accepted, plus two items. (i) The footnote-match rate and the
  `AFF10B5ONE` rate are reported per filing year among P/A Form 4 rows. (ii) A **sensitivity with no
  10b5-1 exclusion before 2023**: footnote matches are ignored for filings before 2023-01-01, and the
  structured flag (2023q1+) still applies. The sensitivity reports the event study (≥ 3) and the
  satellite. It cannot meet H1.

### A1.5 Point in time
No acceptance timestamp exists in either Form 4 source (§3.5). **Entry is the close of the first
trading day after the SEC `FILING_DATE`** on which the name trades, within 5 market days; otherwise
the event is dropped and counted. Day 0 is the entry close.

### A1.6 Power — minimum detectable effects (pre-data; assumptions stated)
MDE80 = (z_{0.975} + z_{0.80}) × SE = 2.80 × SE: a two-sided 5% test with 80% power. The "t > 2"
threshold itself is the 50%-power point.

| gate | SE model (assumptions) | **MDE80 (central)** | range across the assumptions |
|---|---|---|---|
| **momentum satellite** Δ log wealth, 111 months | SE = 0.25 × TE/√12 × √111; TE (arm vs SPY TR) **20%**/yr (15–25%) | **+0.43 total ≈ +4.6%/yr on the blend ≈ the arm beating SPY TR by ~18%/yr** (log) | +0.32 to +0.53 total (arm +14 to +23%/yr) |
| **insider satellite** Δ log wealth, 123 months | the same, with TE **25%**/yr (a ≤ 40-name small-cap book; 20–30%) | **+0.56 total ≈ +5.5%/yr on the blend ≈ the arm beating SPY TR by ~22%/yr** | +0.45 to +0.67 total (arm +18 to +26%/yr) |
| **insider event study** CAR(0,126), ≥ 3, t_HAC | about 118 entry-month cohorts with ~15 events each; event CAR σ **40%** (35–45%); a cohort-common style shock σ **8%** (6–10%) carried across 6 overlapping months, so long-run var = σ²/m + 6·σ_c² | **mean CAR ≈ +5.7%** (t = 2 is reached at about +4.0%) | +4.4% to +7.4% (t = 2 at +3.1% to +5.2%) |

The verdict also reports a **realized** MDE (2.80 × the bootstrap sd of the gate statistic). That
figure is descriptive; the pre-data MDEs above are the ones that bind.
**Labelling rule (binding):** a satellite null (ci_low ≤ 0) with a point estimate below its pre-data
central MDE80 is labelled **"not demonstrable at this length"**. The brief's refutation sentences (§1)
still apply verbatim beside that label.

**Two alpha diagnostics.** They carry no N_trials, cannot meet H1, and feed only the stop trigger in
A1.1.
1. **Momentum** base-arm monthly net returns in excess of BIL TR, regressed on (a) IWM TR minus BIL and
   (b) SPY TR minus BIL. Each regression reports the annualized intercept (alpha × 12) and its
   Newey-West t (statsmodels HAC, 6 lags), over the 111 holding months.
2. **Insider** base-book monthly net returns in excess of BIL TR, regressed on IWM TR minus BIL, with
   the same HAC (6 lags), over the 123 satellite months.

Their power, under the same assumptions: residual volatility against IWM of 12%/yr (momentum) and
18%/yr (insider book) gives an alpha SE of about 3.9 and 5.6%/yr, so t = 2 needs about +8 and +11%/yr
of alpha. Against SPY (momentum), residual volatility of 18% gives an SE of about 5.9%/yr.

### A1.7 Sequence from here
Commit this amendment with the census scripts → build `scripts/smallcap_momentum_t265_b2.py` and
`scripts/smallcap_insider_t265_b2.py` → smoke the first 12 months of each window and read the first
formations and events by eye → full run → determinism ×2 → verdict
`docs/Audit/b2_smallcap_t265_verdict_2026-11-11.md` (or, if the A1.1 trigger fires, the verdict DRAFT,
then STOP and report) → full suite → commit, including the memory files. No push, no merge.
