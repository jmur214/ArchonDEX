---
task_id: T-382 (B-5)
title: Levered diversified book vs 1× SPY under honest Roth financing — verdict
date: 2026-11-11
author: regime-analyst lens (in-session worktree subagent), branch research/levered-diversified-b5
outcome: "H1 NOT MET. Arm (ii) (RSSB-class 100/100) on 1968–2025 has Δ log wealth +0.21 %/yr, 95 % CI [−1.91, +2.30] %/yr vs 1× equity at s = 50 bp. Route C is CLOSED for a levered-ETF Roth holder as briefed. Financing is NOT the binding constraint: ci_low ≤ 0 already at zero spread (−1.41 %/yr)."
status: COMPLETE — awaiting the director's read and an independent review. Determinism ×2 is bit-identical. N_trials consumed +1.
reproduce: "python scripts/b5_levered_diversified.py validate && python scripts/b5_levered_diversified.py smoke && python scripts/b5_levered_diversified.py run --tag A && python scripts/b5_levered_diversified.py run --tag B   # reads the md5-verified snapshot data/research/b5/inputs/ (fetched once; see §2)"
---

# B-5 verdict — levered diversified portfolio vs 1× SPY under honest Roth financing

## 0. The answer

**H1 is NOT MET.** H1 asked whether arm (ii), an RSSB-class 100/100 US-equity + Treasury stack, beats
1× equity with ci_low > 0 on 1968–2025 at the current embedded spread.

| | point | 95 % CI (21-day MBB, 1000 iter, seed 0; MetricsEngine) |
|---|---|---|
| Δ log terminal wealth, total | **+0.122** | [−1.109, +1.332] |
| Δ log wealth per year | **+0.21 %/yr** | **[−1.91, +2.30] %/yr** |

- The sensitivities agree: [−1.94, +2.29] with the project-standard 24-day block and [−1.97, +2.49]
  with 252-day blocks.
- Per the brief's refutation, **Route C is closed for a levered-ETF Roth holder, and the break-even
  curve (§6) is the record.**

**Is financing the binding constraint? No.** This is the brief's acceptance sentence, made exhaustive
in R-12. Arm (ii)'s ci_low is already −1.41 %/yr at **zero** spread over the bill/SOFR rate. The
point estimate crosses zero at s*_pt = 71 bp.

What binds is the size and sampling noise of the premia. Over 58 years:
- the substrate's 10-year term premium over bills is 1.46 %/yr;
- the equity premium is 6.82 %/yr;
- with the ER and the variance cost, that leaves a stack whose edge over equity has an information
  ratio of 0.03.

A cheaper spread cannot fix that. The validation (§3) measured the futures-financed stacked funds'
real embedded spread at ≈ 0 bp (NTSX s* = 0.4 bp). At that realistic spread the H1 cell is still
+0.71 %/yr, with ci_low −1.41 %/yr.

**What this means for a Roth holder, in plain English.** Swapping SPY for an RSSB-style "100 % stocks +
100 % Treasuries" fund would, over 58 years of history, have added about **0.2 % a year**. That is
indistinguishable from zero: anything from about −1.9 % to +2.3 % a year is consistent with the data.
It would have come with the **same worst crash (−56 %)**, **deeper losses in every inflation shock**
(1973–74, 1980–82, and 2022 at −37 % vs −25 %), and shallower losses in the deflationary crashes
(2000–02, 2008, 2020). It is a bet that stocks and bonds stay negatively correlated, not a free lunch.
Cheaper borrowing would not change the answer.

## 1. What was run

- **Pre-registration:** `docs/Sources/prereg_b5_levered_diversified_2026-11-11.md`.
  - **Frozen at `535a3fc`.**
  - **Amendment 1** (`3dcf399`): director freeze, rulings R-1…R-14, pre-data implementation decisions.
  - **Amendment 2** (`891cc3c`): the financing series come from their publishers, because FRED's
    keyless endpoint was blocked for this client.
  - **A2.1** (`b0c05b8`): the H.15 DDP call corrected to the full-release SDMX/ZIP.
  - **A2.2** (`7307ed2`): a parser defect voided the first validation output. Fixes were recorded
    before the re-run.
  - Each amendment and note was committed **alone, before** the data step it governs. The frozen text
    (lines 1–593) is byte-identical throughout (sha256 `c5e8164c…`).
- **Harness:** `scripts/b5_levered_diversified.py`, at `8ee1cb6` for the run.
  - Tests: `tests/test_b5_levered_simulator.py`, 20 of them. They cover the simulator identities, the
    bootstrap replay against MetricsEngine (1e-12), the parsers, and the ND-sentinel regression.
  - Standalone; never `BacktestController`. Substrate = T-306 through T-311's `load_substrate`
    (imported, never edited); md5-verified on every run.
- **Determinism ×2:** runs A and B are **bit-identical** file for file:

  | md5 | file |
  |---|---|
  | `9c63575d…` | `results.json` |
  | `54df180b…` | `returns_W-68.csv` |
  | `910f0cd1…` | `returns_W-72.csv` |
  | `d71a7752…` | `returns_W-00.csv` |
  | `8fbbba62…` | `returns_monthly_W-85.csv` |
  | `b6b82b05…` | `returns_monthly_W-00m.csv` |
  | `74330ba9…` | `returns_monthly_L-19.csv` |
  | `0aaf35d6…` | `run_manifest.json` |

  Run time is 14 s, with 210 MB peak RSS.
- **Inputs:** fetched once (`data/research/b5/inputs/MANIFEST.json`).
  - **3-month T-bill** (= FRED DTB3) from the **Fed Board H.15 Data Download Program**, full-release
    SDMX/ZIP, series `RIFSGFSM03_N.B`: "3-month Treasury bill secondary market rate discount basis",
    18,205 business-day observations, 1954-01-04 → 2026-11-09.
  - **SOFR** from the **NY Fed Markets API**: 1,936 rows, 2018-04-02 → 2025-12-31.
  - **yfinance** `fetch_yf_tr` (Adj Close, `auto_adjust=False`): SSO, UPRO, UBT, TMF, NTSX, RSSB,
    RSST, SPY, TLT, IEF, VT, DBMF.
  - **AQR TSMOM**, byte copy.
  - **Misidentification guard** against the on-disk FRED siblings: bill vs DGS3MO, level correlation
    0.99993, mean gap 5.4 bp; SOFR vs EFFR, 0.9991, −0.25 bp. Both PASS.
- **Windows** (R-1): **W-68** 1968-01-02 → 2025-12-31 (H1; 14,597 days); **W-72** 1972-01-03 →
  2025-12-31 (13,614); **W-00** 2000-01-03 → 2025-12-31 (6,539); arm (iv) monthly **W-85** 1985-01 →
  2025-12 (492), **W-00m** 2000-01 → 2025-12 (312), **L-19** 2019-06 → 2025-12 (79, DBMF).
- **Census:**
  - Equity is never forward-filled.
  - Bond legs are forward-filled on ≤ 150 single bond-market holidays, longest run 1 day.
  - Gold is forward-filled on 148 days, longest run 2.
  - The longest financing-base gap is 2 business days.
  - No halt condition fired in the run.
- **UGL/UST ERs** (R-5, informational, yfinance fund data): UST 0.95 % (the assumption holds) and UGL
  1.19 % (Yahoo's annual-report figure, possibly gross). At 1.19 %, arm (iii)'s vehicle-mix ER would be
  0.72 % instead of the frozen 0.66 %. That is +6 bp of equivalent spread, readable off the curve. The
  frozen 0.66 % stands.

## 2. The fetch and the void first validation (disclosed in full)

1. **FRED was blocked.** Its keyless `fredgraph.csv` and `.xlsx` endpoints timed out or reset for this
   client (~20 min of attempts, IPv4/IPv6, up to 540 s), while FRED's HTML pages and yfinance
   responded. Nothing was obtained. Amendment 2 moved to the publishers.
2. **The first H.15 call was the wrong package, and the identity check HALTED it.** Amendment 2's
   package hash is the DDP's "Treasury Constant Maturities" package. The Fed retired "Build your
   package" the week of 2026-11-09, so the bill series exists only in the full SDMX/ZIP (A2.1). The
   halted attempt directory `inputs_attempt_20261112T030007Z/` is kept, unused.
3. **The first validation run is VOID.** The SDMX marks no-data days `OBS_STATUS="ND"
   OBS_VALUE="-9999"`, and my parser kept −9999 as a rate on **809 holidays**. SSO, UPRO and TMF then
   "failed" G1 (TD −149, −282, −259 bp/yr).
   - Read-only diagnosis traced the largest misses to 2011-11-14 and 2016-11-14, the Mondays after
     Veterans Day (bond market shut, stocks open), across two issuers. The implied financing on those
     days was about −400 %/yr.
   - The amendment-2 guard missed it because DGS3MO has no row on those holidays.
   - Fixes (A2.2, recorded before the re-run): keep `OBS_STATUS="A"` only; add a HALT-only
     [−1 %, +25 %] range check; correct the implied-spread sign (§8 printed `50 + TD/(L−1)`; the
     algebra is `50 − TD/(L−1)`). G1 is symmetric in TD, so the sign fix does not touch it.
   - The void output is kept as `data/research/b5/validation_VOID_sdmx_ND_sentinel.json`.
   - The re-run on the unchanged snapshot is the validation of record. No gate, threshold, arm or
     window moved.
4. **The smoke step caught one more harness bug.** The DBMF leg's cash accrual ran over the 2026 part
   of the equity calendar, past SOFR's declared 2025-12-31 end, and the staleness guard halted. Fixed
   at `8ee1cb6` by limiting that calendar to the windows' common end.

## 3. Validation (V1 gates; V2 reported) — all gating products PASS, H1 EVALUABLE

V1 compares each live product with the frozen simulator on its live underlying, at s = 50 bp over
bill/SOFR. TD is Δ log wealth per year (live − synthetic). s* is the implied embedded spread.

| product | role | overlap | TD (bp/yr) | G1 band | TE | slope | corr | s* (bp) | verdict |
|---|---|---|---|---|---|---|---|---|---|
| SSO (2× SPY) | GATING (all arms) | 2006-07 → 2025-12, 19.5 yr | −7.2 | ±100 | 3.64 % | 0.979 | 0.9955 | +57 | **PASS** |
| UPRO (3× SPY) | GATING (all arms) | 2009-07 → 2025-12, 16.5 yr | −12.5 | ±200 | 3.07 % | 0.996 | 0.9982 | +56 | **PASS** |
| UBT (2× TLT) | GATING (iii) | 2010-02 → 2025-12, 15.9 yr | +87.5 | ±100 | 5.31 % | 0.970 | 0.9849 | −38 | **PASS** (near the edge) |
| TMF (3× TLT) | GATING (iii) | 2009-05 → 2025-12, 16.7 yr | +2.8 | ±200 | 3.57 % | 0.991 | 0.9969 | +49 | **PASS** |
| NTSX (0.9/0.6 stacked) | GATING (i, ii) | 2018-09 → 2025-12, 7.3 yr | +24.8 | ±50 | 5.38 % | 1.011 | 0.9582 | **+0.4** | **PASS** |
| RSSB (1/1, VT + IEF) | reported | 2024-01 → 2025-12, 2.0 yr | +78.0 | (±100) | 4.45 % | 0.974 | 0.9624 | −28 | (pass) |
| RSST (SPY + AQR − s − 1 %) | reported | 2023-10 → 2025-12, 2.2 yr, monthly | **−288.0** | (±100) | 8.95 % | 0.873 | 0.840 | +338 | (fail) |
| V2 SSO (substrate equity) | reported | as SSO | −7.2 | — | 3.64 % | 0.979 | — | +57 | no caveat |
| V2 NTSX (substrate legs) | reported | as NTSX | +32.7 | — | 5.17 % | 1.018 | — | −15 | no caveat |

**Reading.**
- **The frozen 50 bp swap spread is right for the swap-financed products:** SSO 57, UPRO 56 and TMF 49
  bp implied. That matches the route research's SOFR + 40–60 bp.
- **Futures-financed NTSX embeds ≈ 0 bp.** So H1 at 50 bp is conservative by about 50 bp/yr for
  arm (ii), and §6 reads the curve at the realistic spread too.
- **The AQR-based RSST synthetic over-captures the live fund by 2.9 %/yr**, consistent with T-296's
  +5.3 %/yr on a different window. That is why arm (iv)-A is refute-only.
- **V2 raises no substrate-basis caveat.**

## 4. The H1 cell and the MBL line

- **Point and CI:** see §0; the replay equals `MetricsEngine.bootstrap_distribution` to < 1e-9 by
  assertion. p(Δ > 0) = 0.56.
- **The IR of the daily Δ series is 0.027.** The MBL line needs **0.284** at the pinned gate's
  N_eff 37.08 (registry N_raw 231, +1) and **0.375** at the Option-B ruling's N_eff 267. Neither is
  remotely cleared. Both N figures understate: the registry never sees standalone-harness trials
  (health_check MEDIUM, `573fc62`).

## 5. The five-arm tables

Δ is Δ log wealth per year vs 1× equity (the benchmark is T-311 `buyhold_equity`, broad-market TR
before 1993). Brackets are the primary 95 % CI. "auto" uses the project-standard block, "252" uses
252-day blocks (both non-gating). ΔMDD is arm − benchmark; positive means shallower. Sortino carries
its ci_low. Spread s = 50 bp.

### W-68 — 1968–2025 (58.0 yr; the H1 window)

| arm | Δ %/yr [95 % CI] | auto / 252 CI | CAGR | ×wealth | vol | MaxDD (trough) | ΔMDD | Sortino [ci_low] | IR |
|---|---|---|---|---|---|---|---|---|---|
| benchmark 1× equity | — | — | 10.47 % | ×322 | 16.7 % | −55.3 % (2009-03) | — | 0.870 [0.535] | — |
| (i) NTSX 90/60 | −0.04 [−1.33, +1.16] | [−1.36, +1.26] / [−1.34, +1.43] | 10.43 % | ×316 | 15.7 % | −48.5 % (1974-10) | +6.8 | 0.955 [0.591] | −0.01 |
| **(ii) RSSB 100/100** | **+0.21 [−1.91, +2.30]** | [−1.94, +2.29] / [−1.97, +2.49] | 10.70 % | ×364 | 18.4 % | −55.8 % (1974-10) | −0.6 | 0.876 [0.497] | 0.03 |
| (v) 60/40 | −1.35 [−3.15, +0.38] | [−3.02, +0.33] / [−3.18, +0.50] | 8.99 % | ×147 | 10.4 % | −33.1 % (2009-03) | +22.1 | 1.182 [0.804] | −0.18 |

### W-72 — 1972–2025 (54.0 yr)

| arm | Δ %/yr [95 % CI] | auto / 252 CI | CAGR | ×wealth | vol | MaxDD (trough) | ΔMDD | Sortino [ci_low] | IR |
|---|---|---|---|---|---|---|---|---|---|
| benchmark | — | — | 10.95 % | ×274 | 17.0 % | −55.3 % (2009-03) | — | 0.886 [0.533] | — |
| (i) NTSX 90/60 | −0.01 [−1.39, +1.48] | [−1.41, +1.48] / [−1.46, +1.55] | 10.94 % | ×272 | 15.9 % | −48.5 % (1974-10) | +6.8 | 0.976 [0.621] | −0.00 |
| (ii) RSSB 100/100 | +0.34 [−1.67, +2.74] | [−1.87, +2.68] / [−2.05, +3.04] | 11.33 % | ×329 | 18.7 % | −55.8 % (1974-10) | −0.6 | 0.902 [0.540] | 0.04 |
| (iii) 1.9× inverse-vol eq/bond/gold | −1.86 [−5.89, +2.46] | [−5.73, +2.50] / [−6.20, +1.86] | 8.91 % | ×100 | 13.1 % | −48.9 % (1982-06) | +6.4 | 1.012 [0.639] | −0.12 |
| (v) 60/40 | −1.52 [−3.43, +0.44] | [−3.48, +0.50] / [−3.28, +0.52] | 9.28 % | ×120 | 10.5 % | −33.1 % (2009-03) | +22.1 | 1.191 [0.826] | −0.20 |
| (iv-A) +50 % AQR overlay, **W-85 1985–2025, REFUTE-ONLY** | +5.11 [+3.25, +6.95] | [+3.29, +6.87] / [+3.13, +6.96] | 17.45 % (bench 11.60 %) | — | — | −43.5 % (bench −50.8 %, monthly) | +7.4 | 1.523 [0.949] | 0.81 |
| (iv-A) +25 % AQR overlay, W-85 | +2.61 [+1.67, +3.53] | [+1.70, +3.49] / [+1.61, +3.53] | 14.54 % | — | — | −47.2 % | +3.6 | 1.323 [0.785] | 0.83 |

### W-00 — 2000–2025 (26.0 yr)

| arm | Δ %/yr [95 % CI] | auto / 252 CI | CAGR | ×wealth | vol | MaxDD (trough) | ΔMDD | Sortino [ci_low] | IR |
|---|---|---|---|---|---|---|---|---|---|
| benchmark | — | — | 7.89 % | ×7.2 | 19.4 % | −55.3 % (2009-03) | — | 0.622 [0.185] | — |
| (i) NTSX 90/60 | +0.56 [−1.18, +2.42] | [−1.15, +2.47] / [−1.32, +2.48] | 8.50 % | ×8.3 | 16.5 % | −46.0 % (2009-03) | +9.3 | 0.758 [0.299] | 0.11 |
| (ii) RSSB 100/100 | +1.41 [−1.05, +4.04] | [−0.92, +4.04] / [−1.22, +3.93] | 9.43 % | ×10.4 | 18.4 % | −48.2 % (2009-03) | +7.1 | 0.777 [0.305] | 0.21 |
| (iii) 1.9× inverse-vol | +1.66 [−4.83, +8.00] | [−4.39, +8.17] / [−4.59, +7.66] | 9.69 % | ×11.1 | 11.8 % | −31.2 % (2022-10) | +24.0 | 1.200 [0.662] | 0.09 |
| (v) 60/40 | −1.22 [−4.33, +1.99] | [−4.14, +1.85] / [−4.28, +1.76] | 6.58 % | ×5.2 | 11.0 % | −33.1 % (2009-03) | +22.1 | 0.832 [0.364] | −0.13 |
| (iv-A) +50 % AQR, W-00m, REFUTE-ONLY | +3.47 [+0.99, +5.99] | [+1.06, +5.80] / [+1.12, +5.72] | 11.70 % (bench 7.89 %) | — | — | −43.5 % (bench −50.8 %, monthly) | +7.4 | 1.266 [0.624] | 0.53 |
| (iv-A) +25 % AQR, W-00m | +1.79 [+0.55, +3.06] | [+0.58, +2.95] / [+0.60, +2.92] | 9.84 % | — | — | −47.2 % | +3.6 | 1.059 [0.426] | 0.55 |
| (iv-L) +50 % DBMF live, 2019-06 → 2025-12, EXPLORATORY | +2.58 [−1.70, +7.04] | [−2.76, +7.07] / [−2.57, +6.14] | 19.49 % (bench 16.45 %) | — | — | −19.9 % (bench −24.0 %, monthly) | +4.1 | 2.020 [0.788] | 0.46 (needs 0.84) |
| (iv-L) +25 % DBMF live | +1.33 [−0.82, +3.57] | [−1.34, +3.58] / [−1.25, +3.11] | 18.00 % | — | — | −19.7 % | +4.3 | 1.822 [0.676] | 0.47 |

**No arm built from levered ETFs clears ci_low > 0 vs 1× equity on any window.** That covers (i),
(ii), (iii) and the 60/40 control.

**Arm (iv)-A (AQR) clears everywhere, which per §10 is UNINTERPRETABLE.** The refute-only arm cannot
refute. The AQR factor is frictionless and over-captures the live RSST by 2.9 %/yr (§3). That one
basis applied to the 50 % overlay is ~1.4 %/yr, less than the W-85 point but comparable to the W-00
ci_low. The overlay door is therefore neither closed nor opened by B-5.

**Arm (iv-L), the only live-cost trend leg**, is positive on the point with a CI straddling zero.
Its 6.6 years are far below the MBL line (IR 0.46 vs 0.84 needed).

## 6. Break-even spread curves (characterization; the record the refutation names)

**Arm (ii), the decision arm, on W-68.** Δ %/yr at each spread s over bill/SOFR:

| s (bp) | 0 | 25 | 50 | 75 | 100 | 150 | 200 | 300 | 400 |
|---|---|---|---|---|---|---|---|---|---|
| point | +0.71 | +0.46 | +0.21 | −0.04 | −0.29 | −0.80 | −1.31 | −2.32 | −3.34 |
| ci_low | **−1.41** | −1.66 | −1.91 | −2.16 | −2.42 | −2.93 | −3.43 | −4.46 | −5.48 |

The 81-point curve lives in `results.json` (`windows.W-68.ii.curve`).

| arm / window | s*_ci (ci_low = 0) | s*_pt (point = 0) | binding? |
|---|---|---|---|
| (ii) W-68 | < 0 (fails at s = 0) | 70.9 bp | NOT binding |
| (ii) W-72 | < 0 | 84.1 bp | NOT binding |
| (ii) W-00 | < 0 | 190.9 bp | NOT binding |
| (i) W-68 / W-72 / W-00 | < 0 / < 0 / < 0 | 42.7 / 47.3 / 162.3 bp | NOT binding |
| (iii) W-72 / W-00 | < 0 / < 0 | < 0 / 231.4 bp | NOT binding |
| (iv-A) W-85 / W-00m (w = 50 %) | > 400 / 249.8 bp | > 400 / > 400 | uninterpretable (AQR) |
| (iv-L) DBMF (w = 50 %) | < 0 | > 400 | NOT binding (exploratory) |

In every gated arm on every window, ci_low ≤ 0 at zero spread. The point-estimate break-even spreads
(43–231 bp) sit **above** the measured embedded spreads of ≈ 0 bp (futures) and 49–57 bp (swaps) in
most cells. On the point estimate, a holder would come out ahead at today's financing. The data
cannot tell that edge from zero.

## 7. ρ(stock, bond) > 0 sub-samples and 2022

The ρ > 0 years are calendar years with a positive daily equity–bond correlation (R-10). In W-68 that
is 36 of 58 years: 1968–1997 except 1998, plus 1999, 2005, 2006 and 2022–2024. W-00 has 5 such years.
Δ %/yr, with the primary-bootstrap CI on each concatenation:

| arm / window | ρ > 0 years | ρ ≤ 0 years |
|---|---|---|
| (ii) W-68 | −1.80 [−4.84, +1.37] | **+3.49 [+0.92, +6.28]** |
| (ii) W-00 | **−6.41 [−12.14, −0.47]** | **+3.28 [+0.79, +6.26]** |
| (i) W-68 | −1.12 [−2.81, +0.58] | +1.73 [−0.28, +3.89] |
| (i) W-00 | **−4.05 [−7.33, −0.85]** | +1.66 [−0.30, +3.84] |
| (iii) W-72 | **−4.74 [−9.07, −0.61]** | +2.35 [−4.37, +9.43] |
| (v) W-68 | −1.71 [−3.78, +0.26] | −0.76 [−4.07, +2.95] |

**2022** (calendar year; Δ log wealth in pp, arm and benchmark MaxDD within the year):

| arm | Δ in 2022 [CI] | arm MaxDD | bench MaxDD |
|---|---|---|---|
| (i) | −8.1 [−16.5, +2.0] | −29.7 % | −24.5 % |
| (ii) | **−18.0 [−32.8, +1.3]** | −36.8 % | −24.5 % |
| (iii) | −5.3 [−33.0, +20.5] | −30.0 % | −24.5 % |
| (v) | +2.9 [−13.1, +16.6] | −20.0 % | −24.5 % |
| (iv-A) +50 % AQR | +11.9 | — | — |
| (iv-L) +50 % DBMF | +10.3 | — | — |

**Crisis-window drawdowns** (computed from `returns_W-68.csv` and `returns_W-72.csv`; MaxDD within
each window):

| episode | bench | (i) | (ii) | (iii) | (v) |
|---|---|---|---|---|---|
| 1973–74 | −48.2 | −48.4 | **−55.8** | −21.1 | −31.9 |
| 1980–82 Volcker | −20.2 | −26.8 | **−39.3** | **−48.9** | −14.9 |
| 1987 crash | −33.1 | −31.0 | −36.9 | −22.8 | −20.9 |
| dotcom 2000–02 | −47.6 | −37.4 | −38.9 | −9.0 | −24.8 |
| GFC 2007–09 | −55.2 | −46.0 | −48.1 | −26.1 | −33.1 |
| COVID 2020 | −33.7 | −26.8 | −27.6 | −15.4 | −19.1 |
| 2022 | −24.5 | −29.7 | **−36.8** | −30.0 | −20.0 |

**The regime reading (the macro lens).** The bond-levered stack is a **stock–bond correlation-regime
bet**:
- In ρ ≤ 0 years (deflationary, bonds hedge equity) arm (ii) beat equity by about 3.3–3.5 %/yr with
  ci_low > 0.
- In ρ > 0 years (inflationary: 1968–97, 2022–24) it lost 1.8–6.4 %/yr.
- It is deeper than equity in every inflationary rate shock and shallower in every deflationary crash.

The 58-year average nets those regimes to ~0. **The sub-samples are classified ex post** (the
correlation measured in the same calendar year), so they show the mechanism, not a tradeable rule. A
regime-switched stack would need ρ forecast ex ante. B-5 does **not** test that; it would be its own
pre-registered trial, and a trailing-correlation signal is a lagging indicator that recognizes the
regime only after the 2022-type damage.

## 8. The brief's break-even arithmetic, reproduced with measured inputs

E and T are the arithmetic excess returns over the financing base. σ and ρ are measured on each
window.

| window | E | T | σ_e | σ_b | ρ(e, b) |
|---|---|---|---|---|---|
| W-68 | 6.82 % | 1.46 % | 16.7 % | 7.5 % | +0.01 |
| W-72 | 7.39 % | 1.55 % | 17.0 % | 7.7 % | +0.00 |
| W-00 | 7.65 % | 1.99 % | 19.4 % | 6.4 % | −0.28 |

- **Arm (i) = 1.5 × 60/40**, brief: `Δ ≈ 0.6·T − 0.1·E − 0.5·s − ER`.
  - W-68: 0.6·1.46 − 0.1·6.82 − 0.25 − 0.20 = **−0.25 %/yr**.
  - Adding the variance term `(σ_e² − σ_p²)/2 = +0.16` and the benchmark ER (+0.09): **−0.01 %/yr**.
  - **Simulated: −0.04 %/yr.** W-00: brief −0.02, with variance +0.54, simulated +0.56.
  - Brief's `s* = 2·(0.6·T − 0.1·E − ER)`: −1 bp (W-68), −1 bp (W-72), +45 bp (W-00).
  - With the variance term: ≈ 48 / 50 / 158 bp vs simulated s*_pt 42.7 / 47.3 / 162.3 bp.
  - The brief's no-variance form understates the break-even by about the variance benefit (σ_p <
    σ_e). The arithmetic and the simulator agree to within ~6 bp once it is included.
- **Arm (iii) at 1.9×:** brief `SR_rp* ≈ (E + 0.9·s + ER)/16.2`.
  - W-72: (7.39 + 0.45 + 0.66)/16.2 = **0.525**. At the realized levered vol (1.9 × 6.9 % = 13.1 %,
    not 16.2 %) the hurdle is **0.649**.
  - The realized unlevered inverse-vol SR is **0.458**, below both. Arithmetic Δ −2.50 %/yr vs
    simulated −1.86 (the gap is the variance benefit).
  - W-00: hurdle 0.541 (brief) / 0.745 (realized vol) vs realized SR **0.781**, so it just clears.
    Simulated +1.66 %/yr, CI [−4.8, +8.0].
  - The Route C research cited realized RP SR ≈ 0.6 for 1972–2025. On this substrate (a duration-7
    bond synthetic plus LBMA gold, inverse-vol rather than equal-risk-contribution) it is 0.46.
- **Arm (ii), same algebra:** `Δ ≈ T − s − (ER − ER_bench) − (σ_b² + 2ρσ_eσ_b)/2`.
  - W-68: 1.46 − 0.50 − 0.32 − 0.30 = **+0.34 %/yr** vs **simulated +0.21**.
  - Break-even s* ≈ 84 bp vs simulated 71 bp. W-00: +1.31 vs +1.41.
  - The small gaps are quarterly drift and compounding.

The route research's forward inputs (T 1.5 %, E 4 %) bracket the realized T closely: 1.46–1.99 %.
Realized E (6.8–7.7 %) was much higher than the forward 4 %, which **hurts** the stacks that give up
equity (arm (i)) and is neutral for arm (ii), whose equity exposure is 1.0.

## 9. Predictions (prereg §11) vs outcomes, line by line

| prediction | outcome | hit? |
|---|---|---|
| Arm (ii) W-68 point +0.3 to +1.8 %/yr | +0.21 | **miss** (just below) |
| Arm (ii) W-68 ci_low between −1.5 and 0 | −1.91 | **miss** (CI wider than estimated) |
| H1 NOT MET | NOT MET | hit |
| s*_pt 80–230 bp | 70.9 bp | **miss** (just below) |
| s*_ci −100 to +40 bp; whether < 0 a coin flip | < 0 (ci_low −1.41 %/yr at s = 0, i.e. ~−140 bp extrapolated) | **miss** on the range; the coin landed "not binding" |
| Arm (ii) W-72, W-00: point > 0, ci_low < 0 | +0.34 / +1.41; ci_low −1.67 / −1.05 | hit |
| Arm (i) W-68 point −0.3 to +0.8; ci_low < 0 | −0.04; −1.33 | hit |
| Arm (iii) W-72 point +0.5 to +3.5; ci_low ≤ 0 | −1.86; −5.89 | **miss** on the sign (1980–82 gold and rate crash, −48.9 % DD); hit on ci_low |
| Arm (iii) W-00 point −1.5 to +1.5 | +1.66 | **miss** (just above) |
| Arm (v) W-72 −1.5 to −0.2; W-00 −1.5 to +0.5; CI straddles | −1.52 / −1.22; straddles | W-72 **miss** by 0.02; W-00 hit; straddle hit |
| 2022: (ii) −28 to −15; (i) −14 to −7; (iii) −25 to −5 | −18.0 / −8.1 / −5.3 | hit / hit / hit |
| ρ > 0 sign: (ii) Δ lower on ρ > 0 years | −1.80 vs +3.49 | hit |
| Arm (ii) W-68 MaxDD −65 to −45 %, deeper in 1973–74 and 1980–81, milder in 2008 | −55.8 %; deeper in both shocks; milder in GFC | hit |
| Validation: SSO/UPRO/UBT/TMF/NTSX PASS; SSO s* 0–120; NTSX s* −40 to +60 | all PASS; 57; 0.4 | hit |
| RSST synthetic TD −3 to −8 %/yr | −2.88 %/yr | **miss** (just outside) |
| Arm (iv)-A W-85 ci_low > 0 (basis-inflated) | +3.25 | hit |

The calibration was directionally right on every H1-relevant call. It was over-optimistic on arm
(ii)'s point estimate and on arm (iii) over 1972–2025 (the 1980–82 gold crash), and it under-estimated
the CI width.

## 10. Caveats (each disclosed, none changes the verdict)

1. **Substrate (`[NN-SUBSTRATE-REVERIFY]`).** T-306 as built 2026-07-10 (md5s in prereg §3.1).
   - Pre-1993 equity is broad-market, not the S&P 500.
   - The bond leg is a fixed-duration-7 DGS10 synthetic without roll-down or convexity, so it
     **understates** the term premium a real 10-year ladder earns. That is conservative for every
     bond-levered arm. V2 vs live NTSX shows TD +33 bp/yr, with no caveat triggered.
   - Gold is LBMA spot to 2000-08-30, then `gold_gcf`.
   - A T-306 rebuild (including the pending cutover) demotes this verdict to "re-verify required".
2. **The T-306 cash leg is quantized to 1 bp/day** (FF RF; up to ±1 pp/yr in a single year). B-5 does
   not use it for financing. Pre-1993 `equity_tr` carries the same RF rounding. It enters arm and
   benchmark alike, cancelling to first order for arm (ii) and only partly for (i), (iii) and (v).
   Logged by the director in health_check; not fixed here.
3. **T-311's `load_substrate` hole check can never fail** (line 72 compares the frame to itself). B-5
   adds a real forward-fill-run guard; none fired. Logged by the director; not fixed here.
4. **Pre-2018 financing is bill + s.** Swap-financed products then paid LIBOR + spread. The TED gap
   (largest in 1974, 1982 and 2008) would raise arm (iii)'s swap-built share's cost, which is readable
   off the curve. Futures-financed NTSX/RSSB price near repo, so H1 is unaffected.
   - The SSO validation spans 2006–2017 (LIBOR era) and still recovers s* = 57 bp. Over that window
     the bill + 50 bp proxy was adequate on average.
5. **Arm (ii) uses US equity** (Route C's "US proxy"). Live RSSB holds global equity; its 2-year
   validation used VT and is reported only.
6. **Arm (iv) has no faithful deep trend leg.** SG CTA is registration-gated. AQR TSMOM over-captures
   (§3). DBMF covers 6.6 years.
7. **Honest N** is understated by the registry's blindness to standalone-harness trials (`573fc62`).
   The MBL line is failed by a wide margin regardless.
8. **Data provenance.** FRED's keyless endpoint was blocked for this client on 2026-11-11, and the Fed
   retired the DDP's custom-package option the same week. Any project script using
   `fredgraph.csv` (the T-306 builder, T-295) is exposed. The full-release SDMX encodes no-data as
   `-9999` with `OBS_STATUS="ND"`: **filter on the status, never on the value's type.**

## 11. What this means

**For the program.** Route C ("lever a diversified book through Roth-holdable levered ETFs and stacked
funds") is **closed as briefed**:
- the decision arm's 58-year edge is +0.2 %/yr, indistinguishable from zero;
- no gated arm clears ci_low > 0 on any window;
- financing is not what binds.

The 2000–2025 point estimates are positive (+0.6 to +1.7 %/yr), but they are the deflationary
negative-correlation regime's rent (§7). They are not a structural edge, and they straddle zero.

The trend overlay is **neither opened nor closed**. The only faithful leg (DBMF) is too short to
measure, and the deep leg (AQR) is frictionless. A future test needs a live-cost trend series with
depth: SG CTA by registration, or an accruing forward book.

**For a Roth holder.** Holding an RSSB/NTSX-class fund instead of SPY is, on the historical record, a
coin flip on terminal wealth. It wins when stocks and bonds hedge each other and loses badly when
inflation drives them down together, as in 1973–74, 1980–82 and 2022. Borrowing costs are fair (≈ 0 bp
over SOFR in the futures-based funds, ≈ 50 bp in the swap-based ones); the premia are simply too small
and too noisy. 1× SPY remains the honest default.

## Reproduce

```bash
# inputs: fetched ONCE (refuses to re-run); every later step reads the md5-verified snapshot
python scripts/b5_levered_diversified.py validate      # -> data/research/b5/validation.json
python scripts/b5_levered_diversified.py smoke         # -> data/research/b5/smoke.json (never quoted)
python scripts/b5_levered_diversified.py run --tag A   # -> data/research/b5/run_A/
python scripts/b5_levered_diversified.py run --tag B   # determinism twin
diff <(cd data/research/b5/run_A && md5 -r * | sort) <(cd data/research/b5/run_B && md5 -r * | sort)
python -m pytest tests/test_b5_levered_simulator.py -q
```
