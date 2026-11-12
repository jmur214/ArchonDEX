---
task_id: T-382 (B-5)
title: Pre-registration — levered diversified portfolio vs 1× SPY under honest Roth financing
date: 2026-11-11
worker: regime-analyst lens (in-session worktree subagent, branch research/levered-diversified-b5)
branch: research/levered-diversified-b5
status: DRAFT — Phase 1 STOP. The read-only input census is done; NOTHING has been fetched, and no arm, synthetic or validation return has been computed. Awaiting the director's acknowledgment and rulings on §15. N_trials consumed on acknowledgment: +1.
---

# B-5 — does a levered diversified book beat 1× SPY when the leverage is bought the way a Roth can buy it?

## 1. The question (H1 and the refutation, verbatim from the brief)

Brief: `docs/Sources/alpha_frontier_program_2026_09_30.md` § "B-5" (lines 605–647), under the common
SETUP and HARD CONSTRAINTS of § 3.2 (lines 384–410).

A Roth cannot borrow. It can hold leverage only inside daily-reset levered ETFs (SSO, UPRO, UBT, TMF)
or stacked funds (NTSX, RSSB, RSST). Their cost is the product's embedded financing (a short rate plus
a swap spread), its expense ratio, and the volatility drag of the reset. HRP (T-248) and RSST (T-296)
never asked the operator's question under those costs.

**H1 (brief, verbatim):** "arm (ii) at the current embedded spread has Δ log wealth ci_low > 0 vs 1× SPY
on 1968–2025."

**Refutation (brief, verbatim):** "ci_low ≤ 0 at the current spread ⇒ Route C is closed for a
levered-ETF Roth holder; the break-even curve is the record."

"The current embedded spread" is the brief's frozen **s = 50 bp** over DTB3 (pre-2018) / SOFR (2018+).
B-5 runs in a **standalone harness** (the T-249 / T-311 / T-318 pattern). Nothing goes through
`BacktestController`.

## 2. THE HARD PRE-COMMITMENTS

1. **One decision cell.** H1 is arm (ii), at s = 50 bp, on the H1 window (§4), with the primary
   bootstrap (§9). Every other number in B-5 is reported, never substituted for it.
2. **No tuning after any result.** Arms, leverage, weights, ERs, spread, financing conversion,
   rebalance rules, windows, the bootstrap and the validation thresholds are frozen here. Any change
   after the freeze is a new pre-registration and a new trial.
3. **The validation threshold is set before any validation output exists** (§8), and it is justified
   from the brief and its research, not from data. A gating failure HALTS the extension back in time
   for the arms it covers. It is never loosened after the fact.
4. **The spread sweep is characterization, not selection.** The 0–400 bp curve is reported as a curve.
   No spread other than 50 bp is ever read as the H1 verdict.
5. **Fetch once, then read only the snapshot.** Every fetched input is snapshotted under
   `data/research/b5/inputs/` with an md5 manifest. The runs read only the snapshot (§14).
6. **Determinism ×2** (bit-identical md5 of every output) before any number is quoted.
7. **Nothing is deployed from B-5.** Any positive arm still needs the MBL/DSR line (§12) and the
   director's and user's decision gate.

## 3. Input census (read-only, measured 2026-11-11 on `3df64e1`)

### 3.1 The T-306 substrate (`data/research/substrate_multidecade/`, built 2026-07-10)

| file | span | rows | md5 | content |
|---|---|---|---|---|
| `equity_tr_daily.csv` | 1926-07-01 → 2026-04-17 | 26,224 | `c2030019b8846792b5f8e3d18421c905` | FF Mkt-RF + RF daily (broad-market TR, **not** S&P 500) to 1993-01-31; SPY adj-close TR from 1993-02-01 |
| `bond_tr_daily.csv` | 1962-01-03 → 2026-07-08 | 16,112 | `0ac665e8a30d04cf5506c63aaf4e0093` | FRED DGS10 → T-255 synthetic `(carry − 7·Δy)`, fixed duration 7, no convexity, no roll-down |
| `gold_tr_daily.csv` | 1968-01-03 → 2025-12-31 | 14,611 | `30c9d15d18ce2a0c511a0e2398c55a26` | LBMA gold AM fix, spliced to `gold_gcf` on 2000-08-30; price ≈ TR (no yield) |
| `cash_daily.csv` | 1926-07-01 → 2026-05-29 | 26,253 | `28a1446d578e3867c2a1d3b33eabe182` | FF RF daily |
| `provenance.json`, `validation_report.md` | — | — | — | T-306's own record |

**Every window ends 2025-12-31.** Gold ends there, and the brief says "–2025".

### 3.2 Finding: the T-306 cash leg is quantized to 1 bp/day, so B-5 does not use it

`cash_daily.csv` takes only seven distinct values over 100 years: 0, 1, 2, …, 6 bp/day. One step is
≈ 2.52 %/yr. Against the on-disk DGS3MO (2000–2025, read-only comparison, no arm returns), the
annualized FF-RF series is off by up to **±1.03 pp in a single year** (2003: 0.00 % vs 1.03 %; 2017:
0.00 % vs 0.95 %; 2025: 5.17 % vs 4.21 %). The mean absolute error is 0.36 pp/yr. Over 2000–2025 the
signed errors net to −0.01 pp/yr, which is why long-window T-311-family verdicts that used it as cash
are probably unaffected in aggregate. Year-level and regime-level reads that used it are another
matter.

For a financing study this error is first-order: borrowing cost = (L−1)·(cash + s). **B-5 therefore
uses the brief's financing series, DTB3 then SOFR (§5.1), and never `cash_daily.csv`.** One residual
remains. Pre-1993 `equity_tr` is the sum of FF's rounded `Mkt-RF` and rounded `RF`, so it carries the
same RF rounding error. That error enters arm and benchmark in proportion to their equity exposure. It
cancels to first order for arm (ii), whose equity exposure is 1.0. It does not cancel fully for arms
(i), (iii) and (v). Disclosed, not corrected: correcting it would mean editing the substrate.

### 3.3 The financing series: not on disk

`DTB3` and `SOFR` are absent. On disk are `data/macro/DGS3MO.parquet` and `DFF.parquet`, both
2000-01 → 2026-04-23. Those are constant-maturity and effective fed funds, not the brief's series, and
they do not reach 1968. **Planned fetch** (§14).

### 3.4 The trend series for arm (iv)

- **AQR TSMOM is on disk:** `data/research/aqr_tsmom_monthly_t296.xlsx`, md5
  `5bcb8dbf28146f729b99b629147bb0cd`, monthly 1985-01-31 → 2026-05-29 (497 months). The sheet labels it
  "excess returns of the long/short Time Series Momentum factors" (Moskowitz-Ooi-Pedersen 2012). It is a
  **gross, frictionless research factor**: no fees, no trading costs. It needs no fetch.
- **The SG CTA index is NOT on disk** and is **registration-gated** (`02_route_research.md:607`: "SG
  CTA daily 2000+ (registration)"). It is not on the permitted keyless-fetch list, so B-5 cannot obtain
  it under the dispatch rules. The ReSolve SG Trend replication (2000-01 → 2023-01) is behind a form
  download (`02_route_research.md:394`), so the same applies.
- **Known basis (T-296, `docs/Audit/return_stack_arm_verdict_t296_2026_07_08.md`):** a synthetic
  `SPY_TR + AQR_scaled` against live RSST over a 31-month overlap over-captured by **+5.3 %/yr**. That
  is about the size of the whole overlay effect being tested. See §6 arm (iv) and ruling R-2 (§15).
- On disk and live, but short: `data/processed/tr_reconciled/DBMF_1d.csv` (2019-05-08 → 2026-05-22),
  an SG CTA replicator, and `KMLM_1d.csv` (2020-12-03 →). Both are read-only references. If ruled in,
  B-5 fetches its own DBMF copy (§14).

### 3.5 Live ETF prices for the validation step

- **None of SSO, UPRO, TMF, UBT, NTSX, RSSB, RSST is in `data/processed/`.**
- Earlier research copies exist, with unknown or `auto_adjust=True` provenance:
  - `data/research/t282/sso_real.parquet` (SSO 2006-06-21 →; written by `trend_gated_leverage_t282.py`
    with `auto_adjust=True`);
  - `t285/{SSO,UBT,UGL,TLT,GLD}.parquet` (UBT 2010-02-01 →);
  - `t294/{NTSX,RSSB,SSO}.parquet` (NTSX 2018-08-02 →, RSSB 2023-12-05 →).
- **UPRO, TMF and RSST are on disk nowhere.**
- B-5 uses **none** of these copies. The validation fetches every ETF, and its underlyings, fresh and
  in one snapshot (§14). The adjustment basis is then the director-specified `fetch_yf_tr` (Adj Close,
  `auto_adjust=False`), and live product and underlying are adjusted at the same instant.
- Underlyings on disk (`tr_reconciled/` SPY/TLT/IEF, 2005-02-22 →) start too late for the SSO overlap,
  and the dispatch puts `tr_reconciled/` out of bounds. They are fetched fresh as well.

### 3.6 The T-311 conventions imported, and one finding in them

Imported **read-only** from `scripts/deep_reverify_sleeve_t311.py`:
- `load_substrate` (lines 60–73: legs reindexed onto the equity calendar, forward-filled, `dropna`);
- `buyhold_equity` (lines 120–121: the benchmark, `equity_tr` minus a 0.09 %/yr ER per trading day);
- `ER` (line 42; unlevered leg ERs: equity 0.09 %, bond 0.03 %, gold 0.40 %);
- `TD = 252` (line 40), `maxdd`, `cagr` (lines 125–126).

T-311's `robo_returns` is **not** imported. It hard-codes T-311's 1.5 bp rebalance cost, and the brief
sets 5 bp for B-5 (§7).

**Finding (minor, not B-5's to fix):** `load_substrate` calls
`assert_no_calendar_holes(frame.index, frame.index, …)`. That compares the aligned frame to itself and
can never raise. Its construction (reindex onto the equity calendar plus ffill) cannot create holes
anyway. The real exposure is a **forward-fill silently masking a data outage**, and nothing checks it.
B-5 adds a real guard (§16). Separately, T-306's `validation_report.md` lists "gold 18d" and then says
"all ≤ 15d". The 18-day gold gap is the London gold market's 1968-03-15 → 04-01 closure. It lies
outside every B-5 gold window and warm-up.

## 4. The windows — the 1968/1972 conflict, resolved by input availability

The brief's deliverables say "1972–2025 (gold floats)". Its H1 says "1968–2025". The inputs settle it:

| window | dates (daily returns dated within) | arms | why |
|---|---|---|---|
| **W-68 (H1)** | 1968-01-02 → 2025-12-31 (~58 yr) | **(ii) — H1**; (i), (v) reported | Arm (ii) needs no gold. Equity (1926+), bond (1962+) and DTB3 (1954+) all cover 1968, so H1 runs **verbatim** on 1968–2025. |
| **W-72** | 1972-01-03 → 2025-12-31 (~54 yr) | (i), (ii), (iii), (v) | The brief's deliverable window. Arm (iii) needs gold and a 252-day vol warm-up. Its 1972 weights use calendar-1971 gold, which traded on the free London market (two-tier since 1968-04) through the August-1971 end of convertibility. 1968–1971 gold is excluded from arm (iii) by the brief's own "gold floats" condition. |
| **W-85** | months 1985-01 → 2025-12 (41 yr) | (iv) only | Input-bound: AQR TSMOM starts 1985-01. The brief names "AQR TSMOM 1985+ for the deep window". |
| **W-00** | 2000-01-03 → 2025-12-31 (~26 yr) | all five | The brief's second window. |

A window's first return is its first trading day, and the prior close is drawn from the data before
it.

## 5. The simulator (frozen)

### 5.1 Financing and accrual
- **Financing base r_t.** FRED `DTB3` through 2018-04-02, then FRED `SOFR` from 2018-04-03 (SOFR's
  first print).
  - DTB3 is a discount yield d. It is converted to a money-market (act/360) yield:
    `r = 360·d / (360 − 91·d)`.
  - SOFR is already act/360.
  - Missing FRED days are forward-filled. A gap of more than 5 consecutive business days inside any
    window HALTS (§16).
- **Daily financing accrual** over (t−1, t]: `f_t(s) = (r_{t−1} + s) · Δcal_t / 360`, where Δcal_t is
  the calendar days between trading days t−1 and t, and r_{t−1} is the last rate published on or
  before day t−1. **Cash accrual** for any cash balance: `c_t = r_{t−1}·Δcal_t/360`.
- **Expense ratios** accrue at `ER/252` per trading day. That is T-311's convention, so the benchmark's
  imported ER and the products' ERs are on one basis.

### 5.2 The three product mechanics (the brief's formula, applied at book level)
The brief: `r_L = L·r_underlying − (L−1)·(cash + spread) − ER`.
- **Daily reset** (SSO/UPRO/UBT/TMF-class, and arm (iii)'s book):
  `R_t = L·u_t − (L−1)·f_t(s) − ER/252`. Here u_t is the underlying's daily return. Each day starts at
  exactly L×.
- **Stacked fund, quarterly rebalance** (NTSX, RSSB). Equity exposure E and Treasury overlay F drift
  with their legs between rebalances:
  `R_t = (E_{t−1}·e_t + F_{t−1}·b_t)/NAV_{t−1} − ((E_{t−1}+F_{t−1})/NAV_{t−1} − 1)·f_t(s) − ER/252`,
  then `E_t = E_{t−1}(1+e_t)`, `F_t = F_{t−1}(1+b_t)`, `NAV_t = NAV_{t−1}(1+R_t)`.
  - Reset to target (E, F)/NAV after the close of the last trading day of each calendar quarter, and at
    the window start.
  - Cost: 5 bp × (|ΔE| + |ΔF|)/NAV.
  - The brief says "quarterly for NTSX-type". RSSB has the same structure (equity plus a Treasury
    futures ladder), so it is treated as NTSX-type (ruling R-4).
- **Monthly sleeve mix** (arm (iv)): §6.

## 6. Arms (frozen; every arm against the same 1× equity benchmark)

**Benchmark ("1× SPY"):** T-311 `buyhold_equity`, i.e. `equity_tr` daily return minus 0.09 %/252.
Pre-1993 this is broad-market TR, labelled as such. Arms and benchmark share the equity calendar.

| arm | construction | L | ER (on NAV) | rebalance | windows |
|---|---|---|---|---|---|
| **(i) NTSX-synthetic 90/60** | stacked: E = 0.90, F = 0.60 (bond_tr) | 1.5 | **0.20 %** | quarterly | W-68, W-72, W-00 |
| **(ii) RSSB-synthetic 100/100 — DECISION** | stacked: E = 1.00, F = 1.00 (bond_tr); **US equity** proxy (Route C "US proxy") | 2.0 | **0.41 %** | quarterly | **W-68 (H1)**, W-72, W-00 |
| **(iii) 1.9× equal-risk equity/bond/gold** | daily reset at 1.9× on an inverse-vol portfolio; book `R_t = 1.9·rp_t − 0.9·f_t(s) − ER/252` | 1.9 | **0.66 %** (§7) | monthly weights | W-72, W-00 |
| **(iv) 100 % equity + 50 % trend overlay** (and **+25 %**) | (1−w) NAV in a SPY sleeve (ER 0.09 %) + w NAV in an RSST-class sleeve (equity + 1.0 trend overlay, ER 1.00 %); w ∈ {0.50, 0.25} | 1+w | 0.09·(1−w) + 1.00·w | monthly | W-85, W-00 — **subject to ruling R-2** |
| **(v) 1× 60/40 control** | 0.60 equity_tr + 0.40 bond_tr, legs net of T-311 ERs (0.09 % / 0.03 %) | 1.0 | per leg | monthly | W-68, W-72, W-00 |

**Arm (iii) weights.**
- At each month-end m: `v_k = (1/σ_k) / Σ_j (1/σ_j)`, where σ_k is the standard deviation of leg k's
  daily log returns over the 252 trading days ending at m.
- The weights apply from the first trading day of m+1 and drift with the legs inside the month.
- rp_t is the drifting unlevered portfolio's daily return.
- Rebalance cost: 5 bp × 1.9 × Σ_k |v_k,new − v_k,drifted|.
- The leverage is fixed at the brief's 1.9× ("RP-at-SPY-vol"). It is not vol-targeted.
- Forward-filled gold days enter σ as zero returns; this is disclosed.

**Arm (iv) mechanics (monthly).**
- RSST-sleeve month return: `e_m + (τ_m − s/12) − 1.00 %/12`.
  - e_m is the compounded gross `equity_tr` month return.
  - τ_m is the trend leg's excess return.
  - The overlay is "at T-bill + 50 bp": τ is already in excess of cash, so the T-bill cancels and
    only s remains.
- SPY-sleeve month return: `e_m − 0.09 %/12`.
- The book resets to (1−w, w) at each month-end. Cost: 5 bp × turnover.
- The benchmark is compounded to calendar months.
- The paired bootstrap runs on monthly Δ (§9).
- **Trend leg τ:** the brief's SG CTA is unobtainable (§3.4). Ruling R-2 decides between:
  - (iv-A) AQR TSMOM, run **refute-only**;
  - (iv-L) DBMF live, **exploratory**;
  - dropping the arm.

## 7. Frozen inputs (all of them)

| input | value | source |
|---|---|---|
| swap spread s (H1) | **50 bp** over the financing base | brief (02_route_research §Route C, search-verified 2026-09) |
| spread sweep | 0, 5, 10, …, 400 bp (81 points) | brief ("sweep 0–400 bp as characterization") |
| financing base | DTB3 (→ money-market yield) to 2018-04-02; SOFR from 2018-04-03 | brief; conversion §5.1 |
| product ERs | NTSX 0.20 %, RSSB 0.41 %, RSST 1.00 %, SSO 0.89 %, UBT 0.95 %, UPRO 0.90 %, TMF 0.90 % | brief, frozen |
| arm (iii) ER | **0.66 %** of NAV | derived a priori below; brief silent (ruling R-5) |
| benchmark / 1× leg ERs | equity 0.09 %, bond 0.03 % | T-311 `ER` (imported) |
| rebalance cost | 5 bp per rebalanced dollar | brief |
| leverage | (i) 1.5, (ii) 2.0, (iii) 1.9, (iv) 1 + w with w ∈ {0.50, 0.25} | brief |
| arm (iii) vol window | 252 trading days, month-end, causal | this prereg (brief silent) |
| windows | §4 | brief + input availability |
| substrate files | md5s in §3.1 | T-306 |
| AQR TSMOM | md5 `5bcb8dbf28146f729b99b629147bb0cd` | on disk (T-296) |

**Arm (iii) ER, derived before any data.** The cheapest Roth-holdable vehicle mix at stylized,
unmeasured leg vols (equity 16 %, duration-7 bond 7 %, gold 16 %):
- inverse-vol weights are 0.233 / 0.533 / 0.233, so 1.9× exposures are 0.443 / 1.013 / 0.443;
- RSSB at 0.443 NAV carries 0.443 equity plus 0.443 bond, at 0.41 %;
- the remaining bond 0.570 comes from a 2× 7–10y Treasury ETF at 0.285 NAV;
- gold 0.443 comes from a 2× gold ETF at 0.222 NAV;
- the rest is 0.05 cash.

That gives `0.443·0.41 + 0.285·0.95 + 0.222·0.95 = 0.66 %`. The 2× Treasury and 2× gold ERs (0.95 %)
are **assumed** equal to the brief's frozen UBT ER (same issuer and class). They are not
search-verified. An all-2×-ETF build would cost ≈ 0.90 %. That difference is equivalent to +27 bp of
spread at L−1 = 0.9, so the curve answers it.

## 8. The validation rule (set BEFORE any validation output exists)

**What is validated.** The simulator's mechanics, meaning daily reset or quarterly stacking, leverage,
the financing base and its conversion, ER and frozen spread. Each live product is compared with its
synthetic built on the **live underlying** fetched in the same snapshot:

| product | synthetic | underlying |
|---|---|---|
| SSO | 2× daily | SPY TR |
| UPRO | 3× daily | SPY TR |
| UBT | 2× daily | TLT TR |
| TMF | 3× daily | TLT TR |
| NTSX | stacked 0.9/0.6, quarterly | SPY TR + IEF TR |
| RSSB | stacked 1.0/1.0, quarterly | VT TR + IEF TR |
| RSST | monthly: SPY TR + (AQR τ − s) − 1.00 % | SPY TR + AQR TSMOM |

IEF (7–10y) stands in for the 2/5/10/30 futures ladder because its duration (≈ 7) matches the ladder's
and the substrate bond leg's. Overlap: from the first full calendar month after the product's first
price through 2025-12.

**Statistics.**
- Tracking difference: `TD = 252 · mean_t[ln(1+r_live) − ln(1+r_syn)]` (×12 on monthly). It is the
  Δ log wealth per year, the B-5 metric's own unit.
- Tracking error: `TE = std(·)·√252`.
- Implied spread: `s* = 50 bp + TD/(L−1)`.
- OLS slope of live on synthetic daily returns.

**HALT thresholds (gating products).**
- **G1: |TD| ≤ 100 bp/yr × (L−1).** That is SSO, UBT and RSSB 100 bp; UPRO and TMF 200 bp; NTSX 50 bp.
  Equivalently, the implied spread s* must lie in [−50, +150] bp.
- **G2: the slope lies in [0.90, 1.10]** (daily products).

**Why these numbers (from the brief's research, not data).** `02_route_research.md` §Route C puts the
embedded financing of these products at:
- swaps ≈ SOFR + 40–60 bp;
- the 2022 UPRO/BofA swap at ≈ 40 bp;
- Treasury-futures implied repo ≈ SOFR ± 10 bp.

The true spread therefore lies in about [−10, +60] bp, and a correctly specified simulator recovers s*
within ~60 bp of the frozen 50 bp. G1 allows ±100 bp per unit borrowed. That is twice the frozen
spread, which absorbs the known spread range plus unmodelled frictions of the same order:
- close-vs-NAV timing;
- swap reset fees;
- the underlying ETF's own ER embedded in its TR (SPY 9 bp, TLT 15 bp, × L);
- the 2008 LIBOR–T-bill spread on swap-financed products.

A cost model wrong by more than twice the quantity the break-even curve exists to resolve cannot draw
that curve. G2 catches what G1 cannot: an exposure error. A wrong L or a wrong underlying changes the
slope by ≥ 0.2 at these leverages, while zero-mean noise leaves it near 1.

**Scope: what each gating product guards.**
- **SSO, UPRO** (equity, daily reset, 16–19 yr overlaps) gate the **shared financing model**, so a
  FAIL halts **all arms**.
- **UBT, TMF** (bond, daily reset) gate **arm (iii)**.
- **NTSX** (stacked, quarterly, ~7.3 yr overlap) gates **arms (i) and (ii)**. A FAIL makes H1
  **NOT EVALUABLE**, not refuted.
- **RSSB and RSST are REPORTED, not gating.** Their overlaps are about 2.0 and 2.25 years. At any
  plausible TE of 2–4 %/yr, the TD's sampling SE (≈ TE/√years) is at least the 100 bp band, so a gate
  there would rule on noise. NTSX is the gating instance of RSSB's structure class (ruling R-3).
- **Substrate basis (V2), reported, not gating (ruling R-6).** The same NTSX and SSO comparisons run
  with the synthetic built on the substrate legs (`equity_tr`, `bond_tr`), which is the object
  actually extended back. If V2 exceeds the G1 band while V1 passes, the verdict carries a dated
  substrate-basis caveat for arms (i) and (ii).

**HALT semantics.** A gating FAIL stops the extension back in time for its scoped arms: no Δ is
computed for them on any window. The doc reports the failure, and the director rules on a
re-specification, which would be a new pre-registered trial (+1).

## 9. Metrics and the bootstrap

**The paired statistic.**
- Per trading day: `d_t = ln(1+R_arm,t) − ln(1+R_bench,t)`.
- **Δ log terminal wealth** = Σ_t d_t; it is reported also per calendar year (÷ window years).
- Resampling d_t with blocks is exactly the paired bootstrap: both series are drawn at the same
  indices.
- Arm (iv) uses the monthly analogue.

**Bootstrap.**
- **Primary (H1):** moving-block bootstrap (Künsch 1989).
  - 21-trading-day blocks, per the brief; 1,000 resamples; seed 0; two-sided 95 % percentile CI.
  - Implementation: `MetricsEngine.bootstrap_distribution(d, metric=sum, n_iterations=1000,
    block_length=21, seed=0)`, or a vectorized equivalent proven equal to it on the H1 cell before use.
  - **ci_low = the 2.5th percentile.**
  - On arm (iv)'s monthly series a 21-day block is one month.
- **Sensitivity 1 (project standard):** the same call with `block_length=None`, i.e.
  `max(5, round(n^(1/3)))` ≈ 24 days on W-68 (8 months on monthly). Non-gating.
- **Sensitivity 2 (regime persistence):** 252-day blocks. Non-gating.
- The same seed gives the same block draws at every spread. Each resample's Δ is then monotone
  decreasing in s, so the curve is monotone by construction.

**Reported per arm per window:**
- Δ log TW (point, ci_low, ci_high; primary plus both sensitivities);
- CAGR and terminal multiple;
- annualized vol;
- **MaxDD** and ΔMaxDD;
- Sortino with ci_low (`MetricsEngine.bootstrap_distribution`, project-standard block; scorecard only);
- the IR of d_t, for the MBL line (§12).

**Sub-samples (reported).**
- **ρ(stock, bond) > 0 years:** calendar years in which the correlation of daily `equity_tr` and
  `bond_tr` returns is > 0. Δ/yr is reported on the union of those years and on its complement, with
  the primary bootstrap on each concatenation.
- **2022:** calendar year 2022. Δ log TW, arm and benchmark MaxDD within the year, and the bootstrap.

**Break-even spread curve.**
- Covers arms (i), (ii) and (iii), and (iv) if run, on each of their windows.
- At each of the 81 spreads: point Δ, ci_low and ci_high.
- Two crossings are read off it. `s*_ci` is where ci_low crosses 0, and `s*_pt` is where the point
  crosses 0; both use linear interpolation on the grid.
- Reported as "< 0" if the statistic is ≤ 0 already at s = 0, and "> 400" if it is still > 0 at 400 bp.

**"Is financing the binding constraint?" (the brief's acceptance sentence, made exhaustive here):**
- `s*_ci ≥ 50 bp`: H1 met; financing is **not** binding at today's spread.
- `0 ≤ s*_ci < 50 bp`: **financing IS the binding constraint**. The brief's case: a cheaper spread
  would flip the verdict.
- `ci_low ≤ 0 already at s = 0`: financing is **not** what binds. The arm fails even with zero spread
  over cash, so the premia (term, equity) and the ER bind. That is Route C's own ranking: term premium,
  then ER, then correlation, then spread.

**The brief's break-even arithmetic, reproduced with measured inputs** (E and T as excess over the
financing base, σ and ρ measured on the window):
- Arm (i) = 1.5 × 60/40 exactly:
  - `Δ ≈ 0.6·T − 0.1·E − 0.5·s − ER − (σ_p² − σ_e²)/2`;
  - `s* = 2·(0.6·T − 0.1·E − ER)`.
- Arm (iii): `SR_rp* ≈ (E + 0.9·s + ER)/(1.9·σ_rp)` (the brief's /16.2), compared with the realized
  SR of the unlevered inverse-vol portfolio.
- Arm (ii), the same algebra: `Δ ≈ T − s − ER − (σ_b² + 2ρσ_eσ_b)/2`.

Each analytic Δ is set beside the simulated point to show the first-order arithmetic agrees with the
simulator.

## 10. Pre-named outcomes

| outcome | what it means | what it does NOT mean |
|---|---|---|
| **H1 met** (arm (ii) ci_low > 0 at 50 bp, W-68) | A Roth holder buying RSSB-class 100/100 beat 1× US equity on log wealth over 58 years under honest financing, on this substrate | Not deployment evidence unless the MBL line (§12) also clears and the director and user gate it. Not a forecast of the forward term premium. |
| **H1 not met, 0 ≤ s*_ci < 50 bp** | Refuted as briefed; Route C closed for a levered-ETF Roth holder. **Financing binds**: a ≥ (50 − s*_ci) bp cheaper spread would flip it. | Not "leverage never pays". |
| **H1 not met, ci_low ≤ 0 at s = 0** | Refuted, and financing is **not** the binding constraint. Even free spread over cash does not clear. | Not a statement about the point estimate, which may be positive. |
| **NOT EVALUABLE** | A gating validation failed (§8). No arm Δ is quoted for the scoped arms. | Not a refutation. |
| **Arm (iv)-A (AQR) ci_low > 0** | **Uninterpretable**: the known +5 %/yr over-capture (§3.4) can produce it alone | Never a confirmation |
| **Arm (iv)-A ci_low ≤ 0** | Trend overlay refuted a fortiori: even a frictionless factor fails | — |

## 11. Predictions (frozen here; the verdict compares against them line by line)

These are written before any data. The reasoning is the brief's arithmetic with rough priors: realized
T on the duration-7 synthetic over 1968–2025 ≈ 2–2.5 %/yr, E ≈ 6 %/yr, σ_b ≈ 7 %, ρ near 0 over the
full span.

**Arm (ii) on W-68.**
- Point Δ log TW **+0.3 to +1.8 %/yr**.
- ci_low **between −1.5 and 0 %/yr**, so **H1 NOT MET**.
- `s*_pt` between 80 and 230 bp.
- `s*_ci` between −100 and +40 bp. Whether `s*_ci` is above or below 0 (financing binding or not) is a
  coin flip in my estimate.

**Arm (ii) on W-72 and W-00.** Point positive; ci_low < 0 on both.

**Arm (i).** W-68 point −0.3 to +0.8 %/yr; ci_low < 0.

**Arm (iii).**
- W-72 point +0.5 to +3.5 %/yr (1970s gold); ci_low ≤ 0.
- W-00 point −1.5 to +1.5 %/yr.

**Arm (v).** W-72 point −1.5 to −0.2 %/yr; W-00 −1.5 to +0.5 %/yr. ci straddles 0 on both.

**2022 (Δ log TW within the year).**
- Arm (ii): −28 to −15 pp.
- Arm (i): −14 to −7 pp.
- Arm (iii): −25 to −5 pp.

**ρ > 0 years.** Arm (ii)'s Δ/yr on ρ > 0 years is **below** its Δ/yr on ρ ≤ 0 years (sign
prediction).

**MaxDD.** Arm (ii)'s W-68 MaxDD is between −65 % and −45 %, and deeper than the benchmark's in the
1973–74 and 1980–81 rate shocks. 2008 is milder for arm (ii) than for equity, because bonds rallied.

**Validation.**
- SSO, UPRO, UBT, TMF and NTSX PASS G1 and G2.
- Implied spread s*: SSO 0 to 120 bp; NTSX −40 to +60 bp, since futures financing sits below the
  frozen 50 bp.
- The RSST synthetic's TD is −3 to −8 %/yr (the AQR over-capture).

**Arm (iv)-A on W-85.** ci_low > 0. That is **basis-inflated**, which is why it is refute-only.

## 12. Honest prior, N_trials and the honest-N context

**Prior.** The brief's prior is 15 % for the NTSX/RSSB arms, 20 % for RP, 25 % for the trend overlay
and 0 % for any SSO/UBT/TMF construction. **Mine for H1 is 15 %.** The expected Δ IR is ~0.15–0.2,
which gives t ≈ 1.2–1.5 over 58 years. Clearing ci_low > 0 needs an upper-tail realized term premium.
T-315 (1.25× SPY significantly loses on the same substrate) is the base rate for low-leverage ER drag.

**N_trials: +1** (one family). The spread sweep, the sub-samples, the sensitivities and the validation
are characterization, not selection. If the director adds an SG CTA arm after results, that is a new
trial.

**Honest N (read-only, never written).**
`core/measurement/mbl_gate.py::compute_n_effective_correlated` on the **pinned** registry
(`config/honest_n_pin.json`; registry sha256 `b3df6a15…`, artifact `n_effective_2026-09-30.json`):
- N_raw = **231**; ρ̄ (ci_low) 0.4325; ONC compression 0.1598;
- **N_eff (conservative) = 36.92** (equicorr 33.51, ONC 36.92); **37.08 at N_raw + 1**.

**The second figure: N_eff 267.** This is the director's 9.2 ruling on the RR-3 Option-B data pass:
no borrowed correlation credit, 258 distinct executed trials (`docs/State/CURRENT_STATE.md:124`, "the
merged honest-N gate understates N by at least half").

**What the registry omits.** The registry omits **standalone-harness trials**: the T-306-substrate
family (T-311's own counter read 76 on 2026-07-27), B-1's 6, and B-5 itself. The dispatch says a
health_check MEDIUM is open on that. I could not locate it by grep in `docs/State/health_check.md` at
`3df64e1`, so I cite CURRENT_STATE's caveat instead.

**The MBL line for a Δ IR.** Exact form `E[max_N]/√T`; this is a reported secondary, not part of H1:

| window | T (yr) | IR needed @ N_eff 37.08 | IR needed @ N_eff 267 |
|---|---|---|---|
| W-68 | 58.0 | 0.284 | 0.375 |
| W-72 | 54.0 | 0.294 | 0.389 |
| W-85 | 41.0 | 0.337 | 0.446 |
| W-00 | 26.0 | 0.423 | 0.561 |

H1 met with an IR below the line is reported as "**ci_low clears, MBL does not**: exploratory, not
deployment evidence" (`[NN-MBL]`).

## 13. Substrate note (`[NN-SUBSTRATE-REVERIFY]`)

The verdict is conditional on the T-306 build of 2026-07-10, at the md5s in §3.1. If T-306 is rebuilt,
the verdict demotes to "re-verify required". That includes a rebuild through the pending cutover
(option (a): exact post-2018 TR), which is not auto-propagated to `equity_tr`.

Known substrate properties, each disclosed:
- **Equity.** Pre-1993 equity is broad-market (CRSP value-weighted), not the S&P 500. Its daily
  returns carry FF's RF rounding (§3.2).
- **Bond.** The bond leg is a fixed-duration-7 DGS10 synthetic. It omits roll-down and convexity, so
  it **understates** the term premium a real 10-year bond or futures ladder earns. That is
  conservative for every bond-levered arm.
- **Gold.** Gold is LBMA spot to 2000-08-30, then `gold_gcf`.
- **Financing history.** Pre-2018 financing is DTB3 + s. The swap-financed products actually paid
  LIBOR + spread. The LIBOR–T-bill (TED) gap was material and episodic, with large spikes in 1974,
  1982 and 2008. The curve covers it: read the curve at s + TED. Futures-financed NTSX/RSSB price
  near repo (≈ T-bill), so the bias matters for arm (iii)'s swap-built share, not for H1.
- **Benchmark naming.** "1× SPY" is 1× `equity_tr`. Pre-1993 it is not literally SPY.

## 14. Planned fetches (declared now; NONE executed; fetched only after acknowledgment)

All keyless and free, and each source has been used by the project before. Each is fetched **once**
into `data/research/b5/inputs/`. `data/research/b5/inputs/MANIFEST.json` records, per file: source,
URL or call, fetch UTC, rows, span, md5, and the `yfinance` version (1.2.0 installed). The harness
verifies every md5 against the manifest on every run and HALTS on mismatch.

1. **FRED `DTB3`**, full history: `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3`. This is
   the keyless pattern of `scripts/build_multidecade_substrate_t306.py:55`.
2. **FRED `SOFR`**, full history: same pattern.
3. **yfinance via `scripts/reconcile_stooq_tr_t256.py::fetch_yf_tr`** (Adj Close, `auto_adjust=False`;
   the helper is imported, and the module's writer is **never** called). Start: first available date;
   end: 2026-01-01.
   - Brief products: **SSO, UPRO, UBT, TMF, NTSX, RSSB, RSST**.
   - Validation underlyings: **SPY, TLT, IEF, VT**.
   - **DBMF**: only if ruling R-2 admits (iv-L).
4. **AQR TSMOM: no fetch.** The on-disk file (§3.4) is copied byte-for-byte into the snapshot. Its md5
   must equal `5bcb8dbf…`.

Not fetched, and why:
- **SG CTA**: registration-gated.
- **ReSolve SG Trend**: form download.
- **LIBOR / Eurodollar**: ICE LIBOR series were withdrawn from FRED. Any Eurodollar substitute is
  not planned, because the brief prices pre-2018 financing on DTB3 and the curve covers the TED gap
  (§13).
- **UGL and UST** (arm (iii) vehicles): the brief does not list them, and their mechanics are the
  daily-reset class SSO/UPRO/UBT/TMF validate.

## 15. Deviations from the brief, and the rulings requested

| # | deviation / choice | proposed treatment | ruling needed? |
|---|---|---|---|
| R-1 | Windows: H1 on W-68 verbatim (arm (ii) needs no gold); table on W-72 and W-00 verbatim; arm (iv) on W-85 (AQR-bound) | §4 | confirm |
| **R-2** | **Arm (iv): the SG CTA index is unobtainable under the rules. AQR TSMOM over-captures ≈ +5 %/yr vs live RSST (T-296), which is about the whole effect.** | **Recommended:** (iv-A) run on AQR as **refute-only** (it can close the overlay door, never open it; expected uninformative) **plus** (iv-L) **DBMF-live exploratory** 2019-06 → 2025-12. DBMF's TR is converted to excess over the financing base and grossed up by its 0.85 % ER so RSST's 1.00 % is charged once. 6.6 years is below MBL at any N. **Alternatives:** the user supplies SG CTA or ReSolve (a fresh prereg row); or drop (iv) to F-2 forward. | **yes** |
| R-3 | RSSB and RSST validation reported, not gating (overlap ≈ 2 yr); NTSX gates the stacked class | §8 | **yes** |
| R-4 | RSSB treated as NTSX-type (quarterly), not daily reset | §5.2 | confirm |
| R-5 | Arm (iii) ER = 0.66 % (brief silent); UGL/UST ER 0.95 % assumed, not verified | §7 | confirm |
| R-6 | V2 (substrate-leg synthetic vs live NTSX/SSO) reported with a caveat rule, not gating | §8 | **yes** |
| R-7 | Financing conversion and accrual (DTB3 → money-market yield, act/360 on calendar days, rate of t−1); ERs at ER/252 per trading day | §5.1 | confirm |
| R-8 | 5 bp rebalance (brief) instead of T-311's 1.5 bp, so T-311 `robo_returns` is not imported for the 60/40 | §3.6 | confirm |
| R-9 | Arm (iii) vol window 252 trading days (brief silent) | §6 | confirm |
| R-10 | 2022 = calendar year; ρ > 0 sub-sample = calendar years with positive daily equity–bond correlation | §9 | confirm |
| R-11 | Two non-gating bootstrap sensitivities (project-standard auto block, and 252-day blocks) beside the 21-day primary | §9 | confirm |
| R-12 | The acceptance sentence made exhaustive (three cases) | §9 | confirm |
| R-13 | "1× SPY" = T-311 `buyhold_equity` on `equity_tr` (broad-market pre-1993) | §6, §13 | confirm |
| R-14 | The frozen 50 bp is conservative for futures-financed NTSX/RSSB (implied repo ≈ SOFR ± 10 bp). H1 stays at 50 bp; the validation's implied spread is reported beside it; the curve covers it. | §8, §11 | confirm |

**No blocker to Phase 2**, beyond the acknowledgment and the rulings above.

## 16. Fail-closed conditions and the census block (`[NN-FAIL-CLOSED]`, `[NN-CENSUS]` in spirit)

The harness HALTS (non-zero exit, no number written) on any of:
- an input md5 ≠ the manifest;
- a window not fully covered by every leg it uses, including the arm (iii) warm-up;
- a forward-filled run of more than 7 consecutive equity-calendar days in any used leg inside a window
  (plus its warm-up);
- a financing-base gap of more than 5 business days inside a window;
- a NaN or inf in any arm or benchmark return inside a window;
- a gating validation FAIL for a scoped arm;
- the primary bootstrap run with n ≠ 1000 or block ≠ 21;
- determinism ×2 md5 mismatch.

Every results file carries a `census` block:
- input md5s;
- per-window first and last dates and N bars;
- per-leg ffill counts and the longest ffill run;
- financing coverage;
- validation verdicts;
- `n_iterations`, `block_length` and seed;
- the output md5s.

## 17. Sequence

1. Prereg (this commit, alone).
2. **STOP → director acknowledgment and rulings (§15).**
3. Fetch once → snapshot + manifest.
4. Validation (V1 gates, V2 reported).
5. Smoke on the FIRST 12 months of each window (W-68 1968, W-72 1972, W-85 1985, W-00 2000): finite
   returns, the leverage identities, hand-checked financing accrual for one week. Nothing from the
   smoke is quoted.
6. Full run.
7. Run ×2 to identical md5s.
8. Verdict `docs/Audit/b5_levered_diversified_verdict_2026-11-11.md`, with predictions (§11) compared
   line by line.
9. Full suite.
10. Commit on `research/levered-diversified-b5`. New CLI goes in `docs/Core/execution_manual.md`.

Outputs go under `data/research/b5/`. Script: `scripts/b5_levered_diversified.py`. Simulator
identities get a unit test.

## Reproduce the census

```bash
# substrate spans + md5 (§3.1)
for f in data/research/substrate_multidecade/*.csv; do head -2 $f | tail -1; tail -1 $f; md5 -q $f; done
# cash quantization (§3.2): distinct daily values, and FF-RF vs DGS3MO by year 2000-2025
python -c "import pandas as pd,numpy as np; c=pd.read_csv('data/research/substrate_multidecade/cash_daily.csv',index_col=0,parse_dates=True).iloc[:,0]; print(np.unique(c.round(8)))"
# AQR TSMOM span (§3.4)
python -c "import pandas as pd; d=pd.read_excel('data/research/aqr_tsmom_monthly_t296.xlsx','TSMOM Factors',header=None).iloc[18:,:2].dropna(); print(d.iloc[0,0], d.iloc[-1,0], len(d))"
# honest N (§12), read-only
python -c "from core.measurement.mbl_gate import compute_n_effective_correlated as f; print(f(method='conservative'), f(method='equicorr'), f(method='onc'))"
```

---

## AMENDMENT 1 — 2026-11-11: DIRECTOR FREEZE + RULINGS (binding; recorded BEFORE the first fetch)

**Freeze.** The director acknowledged the pre-registration and FROZE it at `535a3fc`. Everything above
this amendment (frontmatter, §1–§17 and "Reproduce the census") is byte-identical to `535a3fc`: sha256
of the file at that commit is `c5e8164cc6d6a6d427eae9b924b785305555003fb7ccdab1cf1a1f9e5217a635`. The
frontmatter `status:` line above therefore still reads DRAFT. **This amendment supersedes it: the
prereg is FROZEN.** This amendment is committed alone, before any fetch, so git and file times prove
the order. N_trials consumed: **+1** (one family; unchanged by the rulings).

**Rulings — all ACCEPTED as proposed in §15:**
- **R-1 windows:**
  - H1 on W-68 (1968–2025);
  - the five-arm table on W-72 (1972–2025) and W-00 (2000–2025);
  - arm (iv) on W-85 (1985–2025) and W-00.
- **R-2 arm (iv):**
  - **(iv-A) AQR TSMOM, REFUTE-ONLY**. It can close the overlay door, never open it.
  - **(iv-L) DBMF live, 2019-06 → 2025-12, EXPLORATORY.**
  - **Neither gates H1.** Both are inside B-5's one family; N_trials stays +1.
- **R-3** RSSB and RSST validation is report-only; **NTSX gates the stacked-fund class**.
- **R-4** RSSB is quarterly-rebalanced (NTSX-type).
- **R-5** arm (iii) ER is **0.66 %**, frozen. The actual UGL and UST ERs are printed beside it from a
  public fund source if retrievable. If not, the 0.95 % assumption stays labelled. **Neither result
  changes the frozen 0.66 %.**
- **R-6** the substrate-leg synthetic vs live NTSX/SSO (V2) is reported with the dated-caveat rule. No
  halt.
- **R-7** DTB3 is converted to a money-market yield; act/360 on calendar days; the rate of t−1.
- **R-8** rebalancing costs 5 bp per rebalanced dollar.
- **R-9** arm (iii) uses a 252-day vol window.
- **R-10** 2022 is the calendar year; the ρ > 0 sub-sample is calendar years with positive daily
  equity–bond correlation.
- **R-11** both bootstrap sensitivities run (project-standard auto block; 252-day blocks), non-gating.
- **R-12** the three-way "is financing binding" sentence.
- **R-13** the benchmark is T-311 `buyhold_equity`.
- **R-14** H1 is evaluated at 50 bp.

**Validation gates as frozen (§8).**
- SSO or UPRO FAIL → **everything halts**.
- NTSX FAIL → **H1 is NOT EVALUABLE, not refuted**, and is reported exactly that way.

**Fetches approved, exactly as listed in §14.**
- FRED `DTB3` and `SOFR` (keyless `fredgraph.csv`).
- yfinance `fetch_yf_tr` (Adj Close, `auto_adjust=False`, never its writer) for SSO, UPRO, UBT, TMF,
  NTSX, RSSB, RSST, SPY, TLT, IEF, VT, **and DBMF** (R-2 (iv-L) approved).
- AQR TSMOM is copied byte-for-byte from disk.
- One snapshot under `data/research/b5/inputs/` with `MANIFEST.json` (md5 per file). The runs read
  ONLY the snapshot.

**Side findings (§3.2 cash quantization; §3.6 the vacuous `load_substrate` hole check at T-311 line 72).**
The director logs both in `health_check.md`. They are NOT fixed on this branch. The verdict carries
them as caveats.

**The registry MEDIUM (§12).** It is on main after this branch's point: `573fc62` ("docs(health):
MEDIUM — the honest-N gate's registry never sees a standalone-harness trial"). Cite it by that commit.
It replaces §12's "could not locate".

**Concurrency.** The outputs land in the MAIN tree's `data/research/b5/` through the `data/research`
symlink. This is expected.

### A1.1 Implementation decisions — recorded BEFORE any data (operational; they alter NO frozen term)

They fill in details §5–§9 leave implicit, so that none of them can be chosen after seeing a number.

1. **Script.** `scripts/b5_levered_diversified.py`, subcommands:
   - `fetch`: one-time; REFUSES if `inputs/MANIFEST.json` exists.
   - `validate`.
   - `smoke`.
   - `run --tag <A|B>`: writes `data/research/b5/run_<tag>/`.

   Simulator identities are covered by a unit test, `tests/test_b5_levered_simulator.py`.
2. **Fetch windows.**
   - yfinance: `start="1990-01-01"`, `asof="2026-01-01"`.
   - FRED: full history.
   - Per-ticker CSV columns: `Date, adj_close, raw_close`. FRED CSVs are stored as the exact response
     bytes.
3. **Validation alignment.**
   - Live product and underlying(s) are inner-joined on dates from the one snapshot.
   - Accrual uses Δcal between consecutive joined dates.
   - The overlap starts on the first trading day of the first full calendar month after the product's
     first price and ends 2025-12-31.
   - The slope is OLS-with-intercept of live on synthetic daily returns.
   - RSST is validated monthly (months 2023-10 → 2025-12): compounded SPY TR month + AQR τ_m −
     s/12 − 1.00 %/12.
   - V2 uses the substrate `equity_tr` and `bond_tr` in place of SPY and IEF, inner-joined with the
     live product's dates.
4. **(iv-L) trend leg.**
   - `τ_m = R_DBMF,m − C_m + 0.85 %/12`, where R_DBMF,m is the compounded DBMF Adj-Close month return
     and C_m is the compounded cash accrual (`c_t`, §5.1) over the same month.
   - That is DBMF's excess return over the financing base, grossed up by DBMF's own ER, so RSST's
     frozen 1.00 % is charged once. The rest is §6 arm (iv) unchanged.
   - Months 2019-06 → 2025-12, both w ∈ {0.50, 0.25}.
5. **Monthly bootstraps** (arm (iv-A), (iv-L)):
   - the primary block is 1 month (the brief's 21 trading days);
   - sensitivity 1 is `block_length=None` (`max(5, round(n^(1/3)))` months);
   - sensitivity 2 is 12-month blocks (the monthly analogue of 252 days).
6. **Bootstrap engine.** A vectorized prefix-sum re-implementation replays
   `MetricsEngine.bootstrap_distribution`'s exact RNG draws (seed 0, `rng.integers(0, n−L+1,
   size=ceil(n/L))` per iteration, the concatenation truncated to n). The same draws serve every
   spread on a cell.
   - Before any curve is computed, the harness ASSERTS the replay equals `MetricsEngine` on the H1
     cell: |Δci_low|, |Δci_high| and |Δmean| < 1e-9 per unit of Δ log TW. Otherwise it HALTS.
   - The H1 cell's quoted numbers are `MetricsEngine`'s own.
7. **Sub-sample bootstraps** (ρ > 0 years, ρ ≤ 0 years, 2022) resample the concatenated d_t of the
   sub-sample with the same spec.
8. **Sortino scorecard.** `MetricsEngine.bootstrap_distribution(r, lambda x: ME.sortino_ratio(x, 0.0,
   252), 1000, None, 0)` on each arm's own daily return (×12 basis for the monthly arms).
9. **Rebalance cost** is "per rebalanced dollar" = 5 bp × Σ|Δ exposure|/NAV over every leg traded:
   - stacked funds: |ΔE| + |ΔF|;
   - arm (iii): 1.9·Σ|Δv|;
   - arm (v): Σ|Δw|;
   - arm (iv): |ΔSPY sleeve| + |ΔRSST sleeve|.
10. **Determinism.** The `run` outputs (results JSON + per-window return CSVs at `%.17g`) carry NO
    wall-clock timestamps. Runs A and B must match by md5 file-for-file.

---

## AMENDMENT 2 — 2026-11-11: financing-series PUBLISHERS replace the blocked FRED endpoint (director ruling, option 2; binding; recorded BEFORE any fetch)

**Why.** FRED's keyless download endpoint for both approved series could not be fetched from this
client: `fredgraph.csv` and `fredgraph.xlsx` time out or reset the connection, while FRED's HTML pages,
google and yfinance all respond (2026-11-11, about 20 minutes of attempts; commit `ac8e1fa`). No byte
of any series was obtained. `data/research/b5/inputs/` is empty and has no manifest.

**Ruling.** The **same two series** come from the publishers FRED republishes. A generic User-Agent is
used, with no personal details. Everything downstream is **unchanged**:
- the DTB3 → money-market conversion `360·d/(360 − 91·d)`;
- the splice (bill rate through 2018-04-02, SOFR from 2018-04-03);
- act/360 accrual on calendar days at the rate of t−1;
- the spread, the arms, the gates, the windows, the bootstrap and every other frozen term in §1–§17
  and amendment 1.

| series | publisher (declared, and named in `MANIFEST.json`) | keyless call | identity check (HALT if it fails) |
|---|---|---|---|
| **3-month Treasury bill, secondary market, discount basis, business day** (= FRED `DTB3`) | **Board of Governors of the Federal Reserve System — H.15 Selected Interest Rates, Data Download Program** | `https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&series=bf17364827e38702b42a58cf8eaa3f78&lastobs=&from=&to=&filetype=csv&label=include&layout=seriescolumn&type=package` (the H.15 package CSV, `FRB_H15.csv`) | The column whose "Unique Identifier" row reads **`H15/H15/RIFSGFSM03_N.B`** is extracted. Its "Series Description" must contain both "3-month" and "secondary market" (case-insensitive). Non-numeric cells (`ND`, `NC`) are dropped, not filled. |
| **SOFR** (= FRED `SOFR`) | **Federal Reserve Bank of New York — Markets Data API** (SOFR's administrator) | `https://markets.newyorkfed.org/api/rates/secured/sofr/search.csv?startDate=2018-04-02&endDate=2025-12-31` | `Effective Date` and `Rate (%)` are taken; `Rate Type` must be SOFR. The effective-date convention means the rate dated D is the overnight D → next business day, consistent with §5.1's "rate of t−1". At least 1,900 rows. |

Both endpoints were confirmed alive by **header-only** requests before this amendment (2026-11-11):
- the Fed returned `HTTP 200`, `text/csv`, `filename=FRB_H15.csv`;
- the NY Fed returned `HTTP 200`, `text/csv`, `filename=Search.csv`.

No body was downloaded, and nothing was written anywhere.

**Misidentification guard** (set now, before any data; it can only HALT, never tune). Each fetched
series is compared with the on-disk FRED copy of a sibling series, read-only:
- **The bill series vs `data/macro/DGS3MO.parquet`** (3-month constant maturity, 2000-01-03 →
  2026-04-23). It HALTS if the correlation of levels over common dates is < 0.99, or if
  |mean(DGS3MO − bill)| > 50 bp. Both are 3-month bill yields that differ only by basis (bond-equivalent
  vs discount), so a correctly extracted column clears both easily. A wrong column (another maturity, a
  monthly series, percent vs decimal) does not.
- **SOFR vs `data/macro/DFF.parquet`** (effective fed funds), common dates 2018-04-03 → 2025-12-31. It
  HALTS if the level correlation is < 0.99, or if |mean(SOFR − EFFR)| > 25 bp. The SOFR–EFFR gap is a
  few bp on average, with rare one-day spikes such as 2019-09-17.

Both comparisons are recorded in the manifest.

**What changes in the code (operational only).**
- The fetch calls the two URLs above instead of `fredgraph.csv`.
- Snapshot files: `frb_h15_package.csv` (exact response bytes) and `nyfed_sofr.csv` (exact response
  bytes).
- Two parsers implement the identity checks.
- `financing_base()` reads them.

The yfinance list (11 + DBMF) and the AQR byte copy are unchanged. So is the staged-then-renamed
snapshot.

**Sequence.** This amendment is committed alone. **Then STOP:** no fetch, and no write under
`data/research/b5/`, until the director's "go". The director needs a quiet `data/` window to merge
B-9 and B-2 through the full-suite gate. After the go, Phase 2 runs exactly as frozen:
1. fetch (yfinance, H.15, NY Fed; AQR copied from disk);
2. the UGL/UST ER print;
3. the validation gates;
4. smoke;
5. run ×2;
6. the verdict;
7. the full suite;
8. commit.

No push, no merge. N_trials unchanged: +1.

### A2.1 Operational addendum — 2026-11-11 21:10 CT: the H.15 DDP call corrected (same publisher, same series, same identity checks; recorded BEFORE the re-fetch)

**What happened.** Amendment 2's H.15 URL (`series=bf17364827e38702b42a58cf8eaa3f78`) turned out to
be the DDP's preformatted **"Treasury Constant Maturities"** package. The halted attempt's label rows
show eleven CMT columns (`RIFLGFCM01_N.B` … `RIFLGFCY30_N.B`) and no T-bill secondary-market column.
**The identity check HALTED it as designed:** "0 columns with identifier H15/H15/RIFSGFSM03_N.B".
Nothing reached `inputs/`, and nothing was read by any run. The attempt directory
`data/research/b5/inputs_attempt_20261112T030007Z/` is kept, unused, and not deleted.

**Why the declared call cannot work.** The DDP H.15 page says the Board removes "Build your package"
the week of November 9 (a notice dated 2026-07-16). The preformatted CSV packages left are:
- Treasury Constant Maturities (all observations);
- weekly averages (last 52 observations);
- monthly averages (last 12 observations).

None of them carries the full-history business-day 3-month bill series. **At the approved publisher,
that series is now available only in the DDP's full H.15 release, "Download all H15 data as a single
XML file [SDMX/ZIP, 67.6 MB]"**, linked from the same DDP page.

**The corrected call (DTB3 only; SOFR unchanged).**
- URL: `https://www.federalreserve.gov/datadownload/Output.aspx?rel=H15&filetype=zip`.
- Publisher, as before: Board of Governors of the Federal Reserve System, H.15 Selected Interest
  Rates, Data Download Program.
- Snapshot file: `frb_h15_all_sdmx.zip` (the exact response bytes).

**Identity check (same substance as amendment 2, adapted to SDMX; HALT if it fails).**
- Exactly one SDMX series has the attribute `SERIES_NAME="RIFSGFSM03_N.B"`.
- Its description or annotation text must contain both "3-month" and "secondary market"
  (case-insensitive). If the file carries no description text for that series, it HALTS.
- Observations are read from `TIME_PERIOD` / `OBS_VALUE`. Non-numeric values are dropped, never
  filled. There must be at least 10,000 of them.
- The amendment-2 misidentification guard against DGS3MO (correlation ≥ 0.99, |mean gap| ≤ 50 bp) is
  unchanged.
- If `RIFSGFSM03_N.B` is absent, it HALTS and reports any series whose description matches. Such a
  series is NOT used without a ruling.

The XML is parsed by streaming, without loading the whole file, to stay inside the 8 GB host.

**Unchanged:** SOFR (NY Fed Markets API; the halted attempt's copy parses at 1,936 rows, 2018-04-02 →
2025-12-31, but it is re-fetched inside the new staged attempt). Also unchanged: yfinance, the AQR
copy, the staged-then-renamed snapshot, and every downstream term.

### A2.2 Operational note — 2026-11-11 21:25 CT: a parser defect voided the first validation output (recorded BEFORE the validation re-run; alters NO gate, threshold, arm or window)

**What the first `validate` run showed, and why it is VOID.** SSO, UPRO and TMF failed G1 (TD −149,
−282 and −259 bp/yr). Read-only diagnosis
(`scratchpad b5_val_diag.py`: by-year TD, worst days, adjustment-factor steps) traced the largest
daily misses to the same dates across two issuers, 2011-11-14 and 2016-11-14. Each is the Monday after
Veterans Day, a day the bond market is closed and the stock market open.

The H.15 SDMX encodes no-data days as `OBS_STATUS="ND" OBS_VALUE="-9999"`. My parser kept the numeric
`-9999` as a rate. **809 holiday rows became −99.99 %**, and every synthetic accrued a large negative
financing charge across those holidays.

The amendment-2 misidentification guard did not see it: it joins on dates common with FRED DGS3MO,
which has no row on those holidays. The raw snapshot bytes are correct, and the manifest md5s are
unchanged. Only the parse was wrong. **That first output is void.** It is kept, renamed and not
deleted, as `data/research/b5/validation_VOID_sdmx_ND_sentinel.json`.

**The fixes (each restores a rule already declared, or adds a HALT-only check).**
1. **`parse_h15_sdmx_zip` keeps only observations with `OBS_STATUS="A"`.** This is the faithful form
   of A2.1's "non-numeric values are dropped, never filled": in this format "no data" is a status
   flag, not a non-numeric string.
   - The manifest's H.15 `rows: 19006` field was written by the defective parse. It counts the 809
     ND sentinels. The corrected count is recorded in `validation.json` and the run census. The
     manifest itself is left as written (fetch once).
2. **New HALT-only input-validity check.** Every bill and SOFR value used must lie in [−1 %, +25 %]
   per year. It cannot tune anything; it would have caught this defect.
3. **Implied-spread sign.** §8 printed `s* = 50 bp + TD/(L−1)`. The algebra gives
   **`s* = 50 bp − TD/(L−1)`**: a live product that lags its synthetic (TD < 0) is paying a HIGHER
   spread.
   - The G1 gate (|TD| ≤ 100 bp × (L−1), symmetric) is unchanged, and so is its equivalent band of
     s* ∈ [−50, +150] bp.
   - Only the reported s* diagnostic flips sign.

**Then `validate` re-runs once on the unchanged snapshot.** Its verdict stands whatever it is: a gating
failure still halts exactly as frozen.

---

## RESULT (appended 2026-11-11; nothing above this line altered)

**H1 NOT MET.** Arm (ii) on W-68 at s = 50 bp: Δ log wealth +0.21 %/yr, 95 % CI [−1.91, +2.30] %/yr
(MetricsEngine, 21-day MBB, 1000 iter, seed 0). **Route C is CLOSED for a levered-ETF Roth holder, as
briefed.** Financing is NOT the binding constraint: ci_low is −1.41 %/yr already at s = 0, and the
point-estimate break-even spread is 71 bp.

All gating validations pass on the record re-run (A2.2): SSO s* 57 bp, UPRO 56, TMF 49, UBT −38,
NTSX 0.4. Determinism ×2 is bit-identical. Predictions in §11 are compared line by line in the
verdict: `docs/Audit/b5_levered_diversified_verdict_2026-11-11.md`. N_trials consumed: +1.
