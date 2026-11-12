---
task_id: T-380 (B-9)
title: Pre-registration — multi-factor combination tilts at deployable weights (VOO / MTUM / AVUV)
date: 2026-11-11
worker: regime-analyst subagent (dispatched by the director, 2026-11-11, with the user's go-ahead)
branch: research/combo-tilts-b9
status: DRAFT — awaiting director acknowledgment (FREEZE) before any return is computed. One ruling is REQUIRED at freeze (§3.2, the total-return source for the ETF-era legs). N_trials consumed at run: 1.
---

# B-9 — do two 20% factor tilts together beat 1× SPY where one alone could not?

## 1. The question (brief, verbatim)

Source: `docs/Sources/alpha_frontier_program_2026_09_30.md` § "B-9" (lines 728–745) and the common
SETUP / HARD CONSTRAINTS block of § 3.2 (lines 384–410).

**Background (brief).** T-318/T-320 tested single tilts (momentum CI-significant at 15–20%; quality
and small-value straddle). A 20% single tilt with 2%/yr long-only alpha and 8% tracking error has
t ≈ 1.3 on 26 years, underpowered by construction. Two 20% tilts with ρ ≈ −0.3 (value × momentum,
Asness-Moskowitz-Pedersen JF 2013) give α 0.8%/yr at TE 1.9% → **t ≈ 2.2**: the same alpha per
tilt-dollar, twice the power. Never run.

**H1 (verbatim):** arm (i) ci_low > 0.

**Refutation (verbatim):** arm (i) ci_low ≤ 0 ⇒ multi-factor closed, momentum stays at 15%.

**Prior (brief):** 25%.

The run is a standalone harness (the T-249 / T-311 / T-318 pattern) that extends
`scripts/tilt_decision_measure_t318_t320.py`. It does not fork it, and nothing runs through
`BacktestController`.

## 2. The hard pre-commitments

1. **Arms frozen** (§6). No weight search, and no switch of the decision arm after the run. If (ii),
   (iii) or (iv) clears and (i) does not, H1 is NOT met. The other arms are reported, never promoted.
2. **No re-spec after seeing a number.** If a number looks wrong, it is reported as looking wrong
   with the evidence, and the director rules. The construction is never quietly changed.
3. **Every convention is fixed here** (§5): proxies, splice months, haircut, ER, cost, rebalance
   timing, bootstrap, and seed. None of them is chosen after the run.
4. **The null is a result.** A refutation is reported at the same prominence as a pass.
5. **Nothing is deployed from B-9.** A pass is a proposal to the user, carrying the
   `[NN-SUBSTRATE-REVERIFY]` caveat in §12. It is never a config change. `config/deploy_candidate.json`
   and `paper_trader/` are not touched by this task under any outcome.

## 3. Pre-run findings, each needing a ruling at freeze

Every finding below came from reading code, configs, file spans, and the French files' headers. **No
return, blend, CI, or other performance statistic has been computed on any leg** (§13 lists every
computation performed before this draft).

### 3.1 The deployed mix is 85/15, not 80/20 (the brief's arm (iii) label is wrong)

The brief labels arm (iii) 80/20/0 "current deployment". The repository says the deployed mix is
**VOO 85% / MTUM 15%**:

- `config/deploy_candidate.json:3-9`: `core` VOO `weight 0.85`, `satellite` MTUM `weight 0.15`,
  `cash_ticker` SGOV (absorbs the residue only), share-quantum bands (buy 1.5 / sell 1.0 quanta,
  `max_drift` 0.10), and Rule-B contributions of $583/mo. The file's `_doc` says that "the approved plan
  gives RANGES (VOO core ~80-85%, MTUM satellite 15-20%)", with the default "at the CONSERVATIVE end".
  80/20 is therefore the top of the approved envelope, not the deployment.
- `paper_trader/deploy_candidate_constructor.py:58-60`: `DEFAULT_CORE = ("VOO", 0.85)`,
  `DEFAULT_SATELLITE = ("MTUM", 0.15)`, `DEFAULT_CASH = "SGOV"`.
- `docs/State/CURRENT_STATE.md:154`: "deployed as the 15% MTUM satellite". Line 142 records account 2's
  arrival holdings (12 VOO / 5 MTUM / 1 SGOV, 2026-09-15).
- The brief contradicts its own label: its refutation reads "momentum stays at **15%**"
  (`alpha_frontier_program_2026_09_30.md:741`).

Scope of what was read: the committed config and code at `3df64e1`, read-only. The deployed
container's baked copy was not read, because that would require an AWS call. Nothing was changed.

**Treatment (as the director instructed):**
- Arm (iii) **stays 80/20/0 as written**, relabelled "top of the approved envelope".
- A **REFERENCE row, 85/15/0**, is reported under identical conventions. It is labelled "deployed mix
  (reference)", is not a decision arm, and consumes no N.
- A **secondary line**: arm (i) paired against the 85/15 reference, Δ log TW (i − 85/15) with the
  same bootstrap. It is reported, not gated.
- Stated limitation: the live book rebalances by share-quantum bands with an SGOV residue. The
  reference row models neither: it rebalances annually and is fully invested. It is the deployed
  weights under B-9's conventions, not a replay of the live book.

### 3.2 ★ BLOCKER: no local total-return series exists for the ETF-era legs (ruling REQUIRED)

The brief splices the actual ETFs after their inception: MTUM from 2013 and AVUV from 2019 (VOO from
2010, which the brief implies). The metric is total-return wealth against SPY-TR, so every leg must be
total return. What exists locally:

| leg | local file | span | class |
|---|---|---|---|
| SPY | `data/processed/SPY_1d.csv` | 1993-01-29 → **2026-04-17** | TR (the 2026-10-15 ruling; data-locked by `tests/test_processed_cache_adjustment_class_2026_10_15.py`) |
| SPY | `data/processed/tr_reconciled/SPY_1d.csv` | 2005-02-22 → 2026-05-22 | TR (T-256: yfinance Adj Close) |
| VOO | `data/raw/stooq/daily/us/nyse etfs/2/voo.us.txt` | 2010-09-14 → 2026-05-22 | **Stooq raw, partial dividend adjustment** |
| MTUM | `…/nyse etfs/1/mtum.us.txt` | 2013-04-24 → 2026-05-22 | **Stooq raw, partial dividend adjustment** |
| AVUV | `…/nyse etfs/1/avuv.us.txt` | 2019-09-27 → 2026-05-22 | **Stooq raw, partial dividend adjustment** |

`data/processed/` has no VOO, MTUM or AVUV file, and neither does `tr_reconciled/`. The raw Stooq bundle
is not total return. T-337's premise check (`docs/Audit/dividend_strip_audit_prereg_t337_2026_07_30.md`
§ PREMISE CORRECTION) measured that Stooq "captures part of the dividend and misses the rest". The
T-256 tool's docstring (`scripts/reconcile_stooq_tr_t256.py:7-9`) and the PFF manifest entry (Stooq
captures 2.94 of a 6.26 %/yr yield) say the same. Treating it as TR would understate the MTUM and AVUV
legs by part of their yield against an exact-TR benchmark. **That bias works against H1. Under
`[NN-FAIL-CLOSED]` the Stooq files are refused as a TR source.**

The project's TR standard for ETFs is **yfinance `Adj Close`**, fetched with `auto_adjust=False` (T-256,
T-337 Ruling 1, and T-379's substrate). This dispatch permits no network access beyond the Ken French
library, so the fetch needs the director's word.

**Option A (RECOMMENDED; the brief as written):** authorize one free, keyless fetch of yfinance daily
`Adj Close` and `Close` for **SPY, VOO, MTUM, AVUV**, reusing `fetch_yf_tr` from
`scripts/reconcile_stooq_tr_t256.py`. That module only fetches; its writer is not called, and nothing is
written to `tr_reconciled/`.
- The fetch is snapshotted once into `data/research/b9/inputs/` with an md5 manifest. Both determinism
  runs read only the snapshot.
- **Input validation** (fail-closed, run before any return is computed):
  - (a) the T-256 split-jump detector, the maximum daily return divergence between the yfinance
    split-adjusted `Close` and the Stooq close, must be ≤ 0.20 for each of the four;
  - (b) the fetched SPY TR's year-end level ratio to the local `tr_reconciled/SPY_1d.csv` (2005–2025)
    and to `data/processed/SPY_1d.csv` (2000–2025) must be constant within ±0.5%. Both compare SPY with
    SPY, a data-class check rather than a result;
  - (c) every ETF monthly |return| must be ≤ 50%, a corporate-action guard. MTUM split 4-for-1 on
    2026-11-05, after the window, and `Adj Close` back-adjusts it.
- **Window: 2000-01 → 2026-06, the brief's window unchanged** (318 monthly returns).

**Option B (FALLBACK, if the fetch is declined; a materially weaker test):** local data only.
- Benchmark and VOO proxy from `data/processed/SPY_1d.csv`.
- MTUM and AVUV are the French proxies with the 50% haircut for the **whole** window.
- The window **ends 2026-03**, because the local SPY TR ends 2026-04-17 and its last full month is
  2026-03.
- Consequence: no month of actual ETF data enters, so the "deployable" evidence is entirely modelled.
  If the director prefers to defer B-9 rather than run B, that is a legitimate ruling.

The rest of this document is written for Option A. Where B differs, the difference is marked **[B]**.

### 3.3 Proxy columns (frozen; verified against the files' own headers)

- **MTUM proxy (pre-splice):** Ken French `6_Portfolios_ME_Prior_12_2`, column `BIG HiPRIOR`. This is
  the value-weighted top-30% of stocks by 2–12-month prior return among stocks above the NYSE median.
  It is the first table in the file ("Average Value Weighted Returns -- Monthly"), 1927-01 → 2026-09.
- **AVUV proxy (pre-splice):** Ken French `32_Portfolios_ME_BEME_OP_2x4x4`, column `SMALL HiBM HiOP`:
  below-NYSE-median ME, top BE/ME quartile, top OP quartile, value-weighted. It is the first table
  ("Average Value Weighted Returns -- Monthly"), 1963-07 → 2026-09. This is the literal reading of
  "small-value-robust-profitability". It is a narrow cell (1 of the 16 small-cap cells), so its
  idiosyncratic noise is higher than AVUV's. Stated, not adjusted: no broader cell or average is used.
- **Market for the haircut and the French-only test:** `F-F_Research_Data_Factors`, `Mkt-RF + RF`
  (1926-07 → 2026-09), via the harness's own `load_legs` / `_ff_raw` path.
- Missing-data sentinels (−99.99/−999): the 2x4x4 file has them only in its investment-average table
  (file lines 5523–5534, 1964-07 → 1965-06), not in the value-weighted return table that is read. The
  harness still HALTs on any selected value ≤ −0.99.

### 3.4 Bootstrap block length: the project standard is short for factor returns (disclosed now)

The project standard (`MetricsEngine.bootstrap_distribution`: moving-block, Künsch 1989, block
`max(5, round(n^(1/3)))`) gives **7 months** at n = 318 (9 at n = 756). Value and momentum spreads
carry multi-year cycles. The T-318 harness used 60-month blocks. **The decision uses the project
standard, as the director instructed.** A 60-month-block CI is reported beside it as a declared
sensitivity line. If the two disagree on the sign of arm (i)'s ci_low, the verdict says so in its
first paragraph ("H1 met on the standard block, not robust to a 60-month block", or the reverse). It is
never averaged away.

## 4. Inputs and window (Option A)

| leg | months used as proxy | months used as the actual ETF | source |
|---|---|---|---|
| Benchmark SPY-TR | — | 2000-01 → 2026-06 | yfinance `Adj Close` (snapshot) |
| VOO | 2000-01 → **2010-09** (SPY-TR + ER differential) | **2010-10** → 2026-06 | yfinance `Adj Close` |
| MTUM | 2000-01 → **2013-04** (French `BIG HiPRIOR`, haircut, − ER) | **2013-05** → 2026-06 | yfinance `Adj Close` |
| AVUV | 2000-01 → **2019-09** (French `SMALL HiBM HiOP`, haircut, − ER) | **2019-10** → 2026-06 | yfinance `Adj Close` |
| FF market TR | 2000-01 → 2026-06 (haircut reference only) | — | Ken French |

- **Splice rule (mechanical):** an ETF is used from the first month for which both the prior
  month-end close and the current month-end close exist. The expected months follow from inception
  (VOO 2010-09-07, MTUM 2013-04-18, AVUV 2019-09-24) and are confirmed by the local Stooq first rows
  (2010-09-14, 2013-04-24, 2019-09-27). **If the snapshot yields any other splice month, the harness
  HALTs before computing a return**, and the director rules.
- **First and last month with data:**
  - French: 2000-01 through 2026-09 for all three files.
  - yfinance: not fetched yet. The window needs 1999-12-31 → 2026-06-30 for SPY and the inception
    months above for the ETFs. The snapshot step asserts these.
  - The window is **2000-01 → 2026-06 (318 monthly returns, 26.5 years)**, the brief's window
    unchanged. The opening allocation is at the 1999-12-31 close.
- **[B]** The window is 2000-01 → 2026-03 (315 months). The benchmark and VOO come from
  `data/processed/SPY_1d.csv` (last full month 2026-03). MTUM and AVUV are French-proxy throughout.
- **Secondary French-only window:** 1963-07 → 2026-06 (756 months; 1963-07 is the 2x4x4 file's first
  month).

## 5. Conventions (frozen)

- **Total return everywhere.** French portfolio returns include dividends. yfinance `Adj Close` is
  total return. Cash is not used: every arm is fully invested.
- **Expense ratios:** VOO 0.03%, MTUM 0.15%, AVUV 0.25% per year.
  - French-proxy months: subtract ER/12 each month.
  - Actual-ETF months: subtract **nothing**, because the NAV already nets the ER. Subtracting again
    would double-count it.
  - VOO proxy months: SPY-TR (already net of SPY's ER) plus **(0.0945% − 0.03%)/12** per month. 0.0945%
    is SPY's ER as recorded in the harness (`ER["MKT"]`).
  - Benchmark: actual SPY-TR with no adjustment.
- **50% haircut on French-era alpha** (the brief: long-only ETFs capture ≈ half the academic premium,
  Novy-Marx-Velikov). For each French-proxy leg L, with E_L the leg's proxy months inside the window:
  `α̂_L = mean_{t∈E_L}(r_L,t − r_FFmkt,t)`, the monthly active return against the FF market TR
  (T-318/T-320's own definition of a premium, `(leg − mkt).mean()`). The proxy used is
  `r_L,t − 0.5·max(α̂_L, 0) − ER_L/12` for t ∈ E_L.
  - **This is a constant shift.** It removes half the realized alpha and keeps the leg's full tracking
    error. The alternative, shrinking the active return by half, would also halve the TE and flatter the
    CI, so it is NOT used.
  - A negative α̂ is not inflated toward zero (hence the max).
  - α̂_L and the shift are printed.
  - French-only test: E_L is the whole 1963-07 → 2026-06 window. **[B]**: E_L is the whole main window.
- **Rebalance:** annually, at each **December month-end close** (2000-12 … 2025-12; 26 rebalances), back
  to the target weights. Weights drift with returns between rebalances. There is no rebalance at the
  window end.
- **Cost:** 5 bp per rebalanced dollar, `cost = 0.0005 × Σ_i |V_i,target − V_i,pre|`. It is deducted
  from portfolio value at the December close and lands in December's return. The opening purchase is
  charged to neither the arm nor the benchmark (symmetric). The benchmark is buy-and-hold 1× SPY-TR with
  no cost.
- **Pre-tax.** No contributions (the paired comparison is of a lump sum held to the end).

## 6. Arms (FROZEN)

| arm | VOO | MTUM | AVUV | role |
|---|--:|--:|--:|---|
| **(i)** | 60 | 20 | 20 | **DECISION arm (H1)** |
| (ii) | 70 | 15 | 15 | reported |
| (iii) | 80 | 20 | 0 | reported. The brief says "current deployment"; it is the top of the approved envelope (§3.1) |
| (iv) | 80 | 0 | 20 | reported |
| REF | 85 | 15 | 0 | **deployed mix, reference only, no N** (§3.1) |

## 7. Metric and statistics

**Primary.** `d_t = log(1 + r_arm,t) − log(1 + r_SPY,t)` monthly, where r_arm,t is net of rebalance cost.
The primary metric is **Δ log TW = Σ_t d_t**, the log of the terminal-wealth ratio. Its CI comes from
`MetricsEngine.bootstrap_distribution(d, metric_fn=sum, n_iterations=1000, block_length=None → 7,
seed=0, confidence=0.95)` (moving block, Künsch 1989, project standard). **ci_low = 2.5th percentile.
H1: arm (i) ci_low > 0.** The table also shows Δ log TW per year (÷ 26.5) and the terminal-wealth ratio
`exp(Δ log TW)`.

Reported for every arm and the REF row (none of these gates):
- **t, measured:** `mean(d) / (sd(d)/√n)` (iid, monthly). This is the statistic comparable to the
  brief's α/TE·√T.
  - **Predicted t for arm (i): ≈ 2.2** (brief: α 0.8%/yr, TE 1.9%, 26 yr). It sits beside the measured
    one with the realized α = 12·mean(d) and TE = √12·sd(d) against the prior's 0.8% / 1.9%.
  - The bootstrap z (point ÷ bootstrap std) is reported as a companion.
- **The power premise, checked:** the realized correlation of the two tilt legs' monthly active returns
  (each leg as used, minus SPY-TR) over the window, against the brief's ρ ≈ −0.3. The "twice the power"
  argument rests on this number.
- **Regret table, as in T-318** (the existing `regret()`, unchanged): the worst rolling-15-year
  relative drawdown of arm/SPY wealth, $ per $10k, and time to recover the relative high ("NEVER
  (≥ x y)" where true). win40y is **n/a** on a 26.5-year window (stated, not fabricated).
- **60-month-block sensitivity CI** (§3.4).
- **Secondary:** arm (i) paired against the REF row, Δ log TW (i − 85/15), with the same bootstrap.
- **Descriptive sub-windows** (point and CI, labelled underpowered, never gating):
  2013-05 → 2026-06 (MTUM actual) and 2019-10 → 2026-06 (both tilts actual). They show how much of the
  full-window result rests on haircut-modelled French months rather than ETF data. **[B]**: not
  applicable.
- **DSR line** (`MetricsEngine.deflated_sharpe_ratio(d, n_trials=N, periods=12)`) at three N, none of
  which gates:
  - N_eff = 37.08, the conservative correlated N at the pinned registry count + 1 (§10);
  - the raw count N = 232;
  - the brief's figure N = 264.
- **MinBTL** at N_eff 37.08 for arm (i)'s realized annualized IR (`compute_mbl_min`), against the
  26.5-year window.

**Secondary: French-only sign test, 1963-07 → 2026-06.**
- Legs: VOO proxy = FF market TR − 0.03%/12; MTUM proxy = `BIG HiPRIOR`; AVUV proxy =
  `SMALL HiBM HiOP` (each haircut over the whole window, − ER).
- Benchmark: FF market TR − 0.0945%/12 (the T-318 harness's SPY proxy).
- Same rebalance and cost conventions. 756 months, standard block 9.
- Reported per arm and REF: the **sign** of Δ log TW (the sign test), its CI, regret, and win40y (the
  existing `rolling_win_and_ci` fraction).
- Pre-stated reading: if arm (i) passes H1 on 2000–2026 but its French-only sign is negative, or the
  reverse, the disagreement is reported as such. The French-only test does not decide H1.

## 8. Pre-stated readings

- **arm (i) ci_low > 0 → H1 MET.** The multi-factor combination clears at deployable weights on this
  window. Carried with it: the 60-month-block line, the share of the result that comes from
  haircut-modelled months (the sub-windows), the realized ρ, the DSR line, and the §12 re-verify
  caveat. The output is a proposal to the user. Nothing in the deployment changes.
- **arm (i) ci_low ≤ 0 → REFUTED.** "Multi-factor closed, momentum stays at 15%" (brief, verbatim). The
  other arms' numbers are reported and nothing is promoted.
- If measured t ≫ predicted, or the realized ρ is far from −0.3 in either direction, it is reported
  as a mechanism finding about the brief's power argument. It changes nothing about H1.

## 9. Fail-closed census (`[NN-FAIL-CLOSED]`, `[NN-CENSUS]` in spirit for a standalone harness)

The harness HALTs (raises, writes no results file) if any of the following holds:
- any leg lacks a finite return for any month in the window. There is no `dropna` that shortens a
  window; an alignment that would drop a month raises;
- a selected French value is ≤ −0.99 (sentinel);
- an ETF monthly |return| exceeds 0.50;
- a splice month differs from §4;
- an Option-A input validation (§3.2 a–b) fails;
- the snapshot's md5 manifest does not match at read;
- the month count differs from 318 [B: 315] / 756;
- the arm weights do not sum to 1;
- any cost is negative.

The results file carries a census block: months per leg per source (proxy vs actual), splice months,
α̂ and shift per proxy leg, the input md5s, n, block length, seed, n_iterations, and the honest-N
inputs read.

## 10. Honest-N context (read, never written)

Read through `core/measurement/mbl_gate.py` (`compute_n_effective`, `compute_n_effective_correlated`).
Both the pinned registry and the ρ̄ artifact were hash-verified against `config/honest_n_pin.json`.
The connection was read-only (`mode=ro`). `run_registry.sqlite` md5 `83e47441…` was identical before and
after, and no journal, WAL or SHM file appeared.

- **N_raw = 231** (the registry's rows, = `rows_at_pin`). **N_eff (conservative) = 36.92**:
  equicorrelated 33.51 at ρ̄ ci_low 0.4325, ONC 36.92 at compression 0.1598.
- **With this trial (+1): N_raw 232 → N_eff 37.08** (same identity, same pinned gate inputs). This is
  the DSR/MBL N.
- **The registry is a stale snapshot:** last modified 2026-08-05 and pinned 2026-10-13. It does not
  contain trials run since then (e.g. B-1's 6, T-379's 2). The code's number is quoted as the code's
  number. No corrected count is invented.
- **The brief's "N ≈ 264" has no derivation in the brief.** It is reported as a third DSR line, labelled
  as the brief's figure.
- **MBL arithmetic on the PREDICTION** (not a result): the predicted t 2.2 over 26.5 years is IR 0.427.
  At N_eff 37.08, E[max] = 2.159 and MinBTL = **25.5 years** against a window of 26.5, so the window
  clears with about one year to spare. At N = 264 (N_eff 42.2) MinBTL = 26.75 years, **which does not
  clear**. Even an exact hit of the prediction sits at the MBL margin. The verdict states this.

## 11. N_trials

**+1** (one family; arms (i)–(iv) are reported jointly and arm (i) decides). The REF row, the arm (i)
vs REF line, the 60-month sensitivity, the sub-windows, and the French-only sign test are pre-declared
secondary reporting. They consume no N, per the director's instruction for the REF row and the brief's
"+1".

## 12. Substrate note (`[NN-SUBSTRATE-REVERIFY]`)

This measurement runs on the **pre-cutover** substrate. Under Option A the legs come from the Ken
French library and a yfinance snapshot, and the pre-cutover `data/processed/SPY_1d.csv` and
`tr_reconciled/SPY_1d.csv` serve as validation references. Under [B] the benchmark and core come
directly from the pre-cutover cache. **Every number from B-9 carries "re-verify required after
cutover."** Separately, the French library revises history (CRSP vintage 202609 is stamped in each
file). The snapshot md5s pin the vintage used.

## 13. Computation performed before this draft (complete list)

1. Spans and first and last rows of the local SPY / VOO / MTUM / AVUV files (row reads only).
2. The Ken French files fetched, read for column names, first and last month, table titles, and
   sentinel line locations. **No return was aggregated, differenced, or compared.**
3. The honest-N read in §10, plus MinBTL arithmetic on the brief's *predicted* t.
4. A read of the deployed config and constructor (§3.1).

No yfinance call has been made. No leg, blend, arm, or benchmark return has been computed.

## 14. Honest prior (before any data)

**~20%** (the brief says 25%). The two actual-ETF eras, MTUM 2013+ and AVUV 2019+, sit inside the
mega-cap-growth regime, in which small-value in particular lagged cap-weighted SPY, and the 50% haircut
halves the French era's alpha. The 7-month standard block narrows the CI relative to the T-318
harness's 60-month block, which helps a pass. A pass on the standard block that fails at 60 months is
the most likely "positive" outcome. Regime note: value × momentum correlation is regime-dependent
(momentum crashes in junk rebounds such as 2009, which is when value rallies). The realized ρ over a
window with one such episode is a weak estimate of the long-run −0.3.

## 15. What a result does NOT license

No change to `config/deploy_candidate.json` and no change to the paper or live paths. No stacking of
additional tilts. No re-weighting search. A pass on 26.5 years at the MBL margin is decision support for
the user, not deployment evidence, until it is re-verified after cutover.

## 16. Reproduce and outputs (after freeze)

`python -m scripts.tilt_decision_measure_t318_t320 --b9`. The flag is new and the existing T-318/T-320
`main()` is unchanged. Outputs go under `data/research/b9/`: `inputs/` (snapshot + md5 manifest),
`b9_results.json` (sorted keys; its md5 is compared across two runs before any number is quoted), and
the printed tables. The verdict goes to `docs/Audit/b9_combo_tilts_verdict_2026-11-11.md`.
