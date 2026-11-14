---
task_id: T-398
title: Pre-registration — a buy-and-hold stacked trend overlay (100% equity + trend, the RSST structure) vs 1× equity on terminal wealth, on INVESTABLE net-of-fee trend returns
date: 2026-11-14
worker: regime-analyst lens (in-session worktree subagent)
branch: research/stacked-trend-overlay-t398
status: DRAFT — Phase 1 STOP. The read-only census is done (`docs/Sources/census_t398_stacked_trend_overlay_2026-11-14.md`). NOTHING has been fetched. No fund, composite, arm or benchmark return has been computed. Awaiting the director's acknowledgment and the rulings in §17. N_trials consumed on acknowledgment: +1.
---

# T-398 — does equity PLUS a trend overlay beat equity alone, when the trend returns are ones an investor could actually have earned?

## 1. The question, H1 and the refutation

The investor: about $10k in a Roth IRA, +$5k a year, about 40 years, will not sell in downturns. The
objective is maximum terminal wealth against buy-and-hold SPY.

B-5 (`docs/Audit/b5_levered_diversified_verdict_2026-11-11.md`, arm (iv)) left one door "neither closed
nor opened". A 50% trend overlay stacked on 100% equity beat 1× equity by +5.11 %/yr, CI
[+3.25, +6.95], over 1985–2025. The trend series was AQR's frictionless paper factor, so the arm was
pre-registered refute-only. The live version (DBMF, 6.6 years) gave +2.58 [−1.70, +7.04].

T-398 asks the same question with **investable, net-of-fee trend returns**.

**H1.** The decision arm — 100% equity + 100% trend, held as one stacked fund (§5) — built on the
live-fund composite (§4.1) in the decision cell (§7) has a paired block-bootstrap Δ log terminal wealth
**ci_low > 0** against 1× equity on the decision window W-L3 (§6).

**Refutation.** ci_low ≤ 0 in the decision cell ⇒ **H1 NOT MET**: the investable record does not show
the stacked overlay beating 1× equity. The graded readings are pre-named in §10.

T-398 runs in a **standalone harness** (the T-311 / B-5 pattern). It does not use
`BacktestController`. It touches no engine, `paper_trader/`, `live_trader/`, `ops/` or `config/`.

## 2. The hard pre-commitments

1. **One decision cell** (§7). Every other number is reported, never substituted for it.
2. **The trend series has a fixed order of authority** (§4): live investable funds first; a net index
   with a pre-declared haircut second; the AQR factor only as a labelled upper bound. A lower level
   never overrides a higher one.
3. **The fund list and the inclusion rule are fixed here, before any fund return is seen** (§4.1). The
   only step still open is verifying each fund's category, start date and expense ratio from yfinance
   metadata. That happens before any price is loaded and is recorded in an amendment committed alone.
4. **No tuning after any result.** Arms, weights, ERs, spread, haircuts, windows, the bootstrap, the
   gates and the sensitivities are frozen here. Any change after the freeze is a new pre-registration
   and a new trial.
5. **Every sensitivity is named here** (§4.3, §8.5) and is reported beside the decision cell.
6. **Fetch once, then read only the snapshot** (§16), md5-pinned.
7. **Smoke on the FIRST 12 months of each window.** No smoke number is quoted.
8. **Determinism ×2** (bit-identical md5 of every output) before any number is quoted.
9. **2026 is a holdout.** Every window ends 2025-12-31 and the fetch stops at `2026-01-01`. Nothing
   dated 2026 is loaded in this study.
10. **Nothing is deployed from T-398.** A positive result still needs the MBL line (§13) and the
    director's and the owner's decision.

## 3. Input census

The census is its own committed document: `docs/Sources/census_t398_stacked_trend_overlay_2026-11-14.md`.
It lists the candidate funds and their start dates, the indices and their access terms, what is on
disk, the break-even haircut on B-5's AQR arm, the windows with their MBL lines, and what each earlier
managed-futures result tested. The items this pre-registration depends on:

| input | path | span | md5 |
|---|---|---|---|
| equity leg | `data/research/substrate_multidecade/equity_tr_daily.csv` | 1926-07-01 → 2026-04-17 | `c2030019b8846792b5f8e3d18421c905` |
| bond leg (sub-sample classification only) | `…/bond_tr_daily.csv` | 1962-01-03 → 2026-07-08 | `0ac665e8a30d04cf5506c63aaf4e0093` |
| 3-month bill (H.15, full SDMX) | `data/research/b5/inputs/frb_h15_all_sdmx.zip` | 1954-01-04 → 2026-11-09 | `50fa80972f99b5f8ea06ef52483c5926` |
| SOFR | `data/research/b5/inputs/nyfed_sofr.csv` | 2018-04-02 → 2025-12-31 | `8cbceec98342202d2168618b48822ade` |
| AQR TSMOM | `data/research/aqr_tsmom_monthly_t296.xlsx` | 1985-01 → 2026-05 | `5bcb8dbf28146f729b99b629147bb0cd` |
| B-5 results (quoted, not re-run) | `data/research/b5/run_A/results.json` | — | `9c63575d…` |

**The T-306 cash leg is not used.** It is quantized to 1 bp/day (health_check MEDIUM). Financing and
cash come from B-5's H.15 / SOFR snapshot.

**No trend mutual fund, CTA index or futures panel is on disk.** The fund prices are a planned fetch
(§16).

## 4. The trend return series — order of authority

### 4.1 Level 1 (decides H1): an equal-weight composite of live investable funds

**The candidate list (fixed now, 15 tickers).** Start dates and ERs marked M are from memory.

| ticker | fund | first bar | fallback ER | flag |
|---|---|---|---|---|
| RYMFX | Guggenheim Managed Futures Strategy | 2007-03 (M) | 1.70% | strategy change (~2012) |
| AQMIX | AQR Managed Futures Strategy I | 2010-01 (M) | 1.25% | — |
| ASFYX | Virtus AlphaSimplex Managed Futures Strategy Y | 2010-07 (M) | 1.45% | — |
| WTMF | WisdomTree Managed Futures Strategy | 2011-01-10 (disk) | 0.65% | strategy changes (2016, 2021) |
| EVOIX | Altegris Futures Evolution Strategy I | 2011-10 (M) | 1.60% | bond-sleeve collateral |
| GMSSX | Goldman Sachs Managed Futures Strategy Inst | 2012-02 (M) | 1.00% | — |
| CSAIX | Credit Suisse Managed Futures Strategy I | 2012-09 (M) | 1.30% | may be delisted |
| FMF | First Trust Managed Futures Strategy | 2013-08-07 (disk) | 0.95% | strategy change |
| PQTIX | PIMCO TRENDS Managed Futures Strategy Inst | 2013-12 (M) | 1.40% | — |
| ABYIX | Abbey Capital Futures Strategy I | 2014-07 (M) | 1.79% | — |
| LOTIX | LoCorr Market Trend I | 2014-07 (M) | 1.75% | — |
| AHLIX | American Beacon AHL Managed Futures Strategy | 2014-08 (M) | 1.50% | — |
| DBMF | iMGP DBi Managed Futures Strategy ETF | 2019-05-08 (disk) | 0.85% | — |
| KMLM | KFA Mount Lucas Managed Futures Index ETF | 2020-12-03 (disk) | 0.90% | — |
| CTA | Simplify Managed Futures Strategy ETF | 2022-03-09 (disk) | 0.75% | — |

**The inclusion rule (fixed now; decided on published facts, never on returns).** A candidate is a
member if all of these hold:
- (a) `fetch_yf_tr` returns a price history for it;
- (b) the Morningstar category yfinance reports for it is "Systematic Trend". If the field is empty the
  fund stays in. If it names any other category the fund is out;
- (c) its first price is on or before 2022-12-30;
- (d) it is not a second share class or a re-levered copy of a program already in the list (QMHIX and
  AHLT are pre-named duplicates and are not candidates);
- (e) it is not a stacked fund with a structural equity or bond exposure (RSST, RSBT, BLNDX and MAFIX
  are never members).

**Membership in time.** A fund enters on the first trading day of the first full calendar month after
its first price. It stays until its last price. A fund whose history ends before 2025-12-31 leaves
after its last return; that return is kept. Nothing is backfilled.

**Each fund's excess return, gross of its own fee.**

    x_{f,t} = r_{f,t} − c_t + ER_f / 252

- `r_{f,t}` is the Adj Close return (`fetch_yf_tr`, `auto_adjust=False`).
- `c_t` is the cash accrual of §5.2.
- `ER_f` is the fund's net expense ratio as yfinance reports it in the metadata step, capped at 2.00%.
  If yfinance reports none, the fallback in the table is used. Today's ER is applied to the whole
  history. Fees have fallen, so this under-corrects, which is the conservative direction.

**The composite.** `x_t` is the simple average of `x_{f,t}` over the funds that are members on day t.
It stands for one representative trend program. No trading cost is charged for the averaging.

**The survivorship haircut.** Every candidate is alive in 2026; dead funds cannot be fetched from
Yahoo. The decision cell subtracts **h_surv = 1.0 %/yr** from `x_t`. The anchor is the equity
mutual-fund literature (0.9–1.5 %/yr, from memory). It is a judgment, not a measurement for this
category, and the zero-haircut result is reported beside it.

### 4.2 Level 2 (secondary; runs only if access is ruled before Phase 2): a net CTA index

- **SG Trend** (2000-01 →), then **SG CTA**. Both are registration-gated. **This study does not
  register and submits no contact detail.** They are used only if the owner obtains the file.
- **BTOP50** (1987-01 →, monthly) only if the director rules that reading BarclayHedge's public table
  is permitted.
- The index is net of its managers' fees and includes collateral interest. Its excess return is
  `I_m − C_m` (monthly), with **no fee gross-up**. The stack ER is charged on top. That double-charges
  trend management and is deliberately conservative.
- **Pre-declared bias haircuts** (from the census's reading of the literature; judgment):
  SG Trend and SG CTA **0.5 %/yr** (live-calculated; possible launch backfill; not investable);
  BTOP50 **1.0 %/yr** (self-reported, includes non-trend programs).
- A level-2 arm is the same structure as the decision arm, monthly. It carries the secondary
  hypothesis **H2**: ci_low > 0 on the index's full window. H2 never replaces H1.
- An index added after Phase 2 has started is a new trial.

### 4.3 Level 3 (a labelled UPPER BOUND, never evidence for H1): AQR TSMOM

- B-5's W-85 and W-00m results are quoted unchanged. They are not re-run.
- The same arm is run on the months of W-L3, so the factor and the funds are compared on one window.
- **The measured over-capture.** `h_L = 12 × mean over W-L3 months of (τ_AQR,m − x_gross,m)`, where
  `x_gross` is the composite's monthly excess return gross of fund ERs and with no survivorship
  haircut. It is reported with a block-bootstrap CI and read against the break-evens the census took
  from B-5's curves (§10).

### 4.4 Named sensitivities on the composite (all reported; none decides)

- **S1 pure-play:** the composite without the four flagged funds (RYMFX, WTMF, FMF, EVOIX).
- **S2 ETFs only:** DBMF, KMLM, CTA, WTMF, FMF.
- **S3 screener:** if a yfinance fund screen on category "Systematic Trend" works, the composite of
  every fund it returns (oldest share class per fund, rule (c) to (e) applied).
- **S4 double fee:** no ER gross-up.
- **S5 no survivorship haircut:** h_surv = 0.

## 5. The stacked return (frozen)

### 5.1 The three sleeves, per trading day

    equity sleeve      R^E_t = e_t − 0.09 % / 252
    stacked sleeve     R^S_t = e_t + x_t − s · Δcal_t / 360 − ER_S / 252
    benchmark          R^E_t

- `e_t` is the daily return of T-306 `equity_tr`, read as T-311's `buyhold_equity` reads it (SPY
  Adj-Close total return in every T-398 window). The 0.09% is that function's ER, as in B-5.
- `x_t` is the composite of §4.1. In the decision cell it is the composite less `h_surv / 252`.
- `ER_S` = **1.00 %** (the RSST-class all-in expense ratio, as frozen in B-5).
- `s` = **50 bp** (B-5's frozen spread), charged on the whole overlay notional. Physically the spread
  falls only on the part of the equity the fund holds through futures, so 50 bp is conservative.

**Arms.**

| arm | holding | trend notional | blended ER | rebalance |
|---|---|---|---|---|
| **+100% — DECISION** | 100% stacked sleeve (one ticker) | 1.00 | 1.00% | inside the fund (daily additive, as written) |
| +50% | 50% equity sleeve + 50% stacked sleeve | 0.50 | 0.545% | monthly |
| +25% | 75% equity sleeve + 25% stacked sleeve | 0.25 | 0.318% | monthly |

In the two-ticker arms the sleeves drift with their returns. They are reset to target after the close
of the last trading day of each month, at 5 bp per traded dollar.

### 5.2 Why cash is not counted twice

A managed-futures fund keeps its capital in T-bills and holds futures on top. Its total return is the
futures profit plus the T-bill yield minus its fee. In a stacked fund the capital is in **equity**
instead, and the same futures sit on top. So the stack earns equity plus the futures profit. The
T-bill yield is not earned a second time.

That is why `c_t` is subtracted from every fund's return before it is added to equity. Adding the
fund's total return to equity would overstate the stack by the whole T-bill yield: T-296 measured that
error at about 4.6 %/yr in 2023–2025.

- **Financing base** (B-5 §5.1, unchanged): the H.15 3-month bill, converted from a discount yield to a
  money-market yield `r = 360·d / (360 − 91·d)`, through 2018-04-02; SOFR from 2018-04-03. Parsed from
  B-5's snapshot keeping `OBS_STATUS="A"` only.
- **Cash accrual:** `c_t = r_{t−1} · Δcal_t / 360`, with the last rate published on or before day t−1.
- The fee is handled the same way: each fund's own ER is added back and the stack's ER is charged
  once.

## 6. The windows — set by input availability

| window | rule | expected dates (M; fixed mechanically at the fetch) | years | role |
|---|---|---|---|---|
| **W-L3** | from the first trading day on which at least **3** funds are members (§4.1's entry rule), to 2025-12-31 | 2010-08-02 or 2010-09-01 → 2025-12-31 | 15.3–15.4 | **decision** |
| W-L1 | the same with at least **1** member | 2007-04-02 → 2025-12-31 | ~18.75 | reported; one fund (RYMFX) until 2010 |
| W-I | the index's first month → 2025-12 | 2000-01 → 2025-12 (SG) | 26 | level 2, conditional |
| W-85, W-00m | B-5's | 1985-01 / 2000-01 → 2025-12 | 41 / 26 | level 3, quoted |

Every window ends 2025-12-31: the SOFR snapshot ends there, and 2026 is the holdout.

**The start is adverse to trend, and that is disclosed, not corrected.** W-L3 opens after 2008 and at
the start of the 2011–2019 flat decade. It is what an investor could have bought.

Reported sub-periods of W-L3: 2011-01 → 2019-12 (the flat decade); calendar 2022; 2020-01 → 2025-12.

## 7. The decision cell

Arm **+100%**. Trend series: the **level-1 composite**, all members, ER gross-up on, **h_surv =
1.0 %/yr**. Spread **50 bp**. Stack ER **1.00 %**. Window **W-L3**. The primary bootstrap of §8.2.

## 8. Metrics

### 8.1 The paired statistic
`d_t = ln(1 + R_arm,t) − ln(1 + R_bench,t)`. **Δ log terminal wealth = Σ d_t**, also reported per
year. Resampling `d_t` in blocks is the paired bootstrap.

### 8.2 The bootstrap
- **Primary:** moving-block bootstrap, 21-trading-day blocks, 1,000 resamples, seed 0, two-sided 95%
  percentile interval, through `MetricsEngine.bootstrap_distribution` (B-5's primary). **ci_low is the
  2.5th percentile.**
- **Sensitivity 1:** the project-standard automatic block (`block_length=None`).
- **Sensitivity 2:** 252-day blocks. Trend's droughts last years; a one-month block understates them.
- **Block-fragility rule.** If the primary clears and the 252-day interval does not, H1 is reported as
  "met on the primary, block-fragile", and it is not deployment evidence.
- Monthly series (levels 2 and 3) use 1-month, automatic and 12-month blocks.

### 8.3 Reported for every arm and window
Δ log wealth (point, ci_low, ci_high, all three bootstraps); CAGR and terminal multiple; annualized
volatility; **MaxDD** on daily data and ΔMaxDD; Sortino with its ci_low (scorecard only); the IR of
`d_t` against the MBL line (§13).

### 8.4 What a won't-sell investor must sit through
- **Worst 3-year relative shortfall:** the minimum over all 756-trading-day spans of Σ d_t, reported
  as a percentage of relative wealth with its dates.
- **Longest relative drought:** the longest stretch during which cumulative Σ d_t stays below its
  earlier peak, and the depth of that relative drawdown.
- **The flat decade:** Σ d_t over 2011-01 → 2019-12.
- **Correlation of the trend leg with equity in equity drawdowns.** An episode is a benchmark
  peak-to-trough decline of at least 10% inside W-L3. For each episode: the number of days, the
  correlation of `x_t` with `e_t` on daily and on non-overlapping 5-day returns, and the composite's
  cumulative excess return from peak to trough. Pooled over all episode days: the correlation with a
  paired block-bootstrap CI (both series resampled together). It is read against T-316's bar of +0.30.
- **Does it deepen the hole?** Arm MaxDD against benchmark MaxDD inside each episode.

### 8.5 Characterization (reported; never selected from)
- **Break-even spread curve,** 0–400 bp in 5 bp steps, with the same bootstrap draws at every point.
  It doubles as the break-even haircut and the break-even fee credit.
- **Stock–bond correlation regime** (B-5's R-10 definition): Δ on calendar years with a positive daily
  equity–bond correlation and on the rest.
- **Accumulation scorecard:** $10k at the window start plus $5k on the first trading day of each
  later year; terminal dollars for each arm and the benchmark. Point values only.

## 9. Evaluability gates and data-integrity halts (set before any data)

**Evaluability.** H1 is **NOT EVALUABLE** — no arm Δ is computed or quoted — if any of these fails:
- **E1 depth.** W-L3, fixed by the ≥ 3-member rule on funds that pass the integrity checks, is at
  least **12 years** long.
- **E2 the composite measures the same thing as the one replicator built to track the industry.** The
  monthly correlation of the composite excluding DBMF with DBMF, on DBMF's overlap, is at least
  **0.50**. The prior is about 0.75 (fund-to-fund correlations in this category run 0.6–0.9; DBMF to
  SG CTA is 0.88 in the route research). On 79 months the standard error is about 0.05, so the band is
  more than four standard errors wide. This gate has power.
- **E3** no unresolved integrity flag (below).
- **E4** every pinned input matches its md5.

**No tracking-difference gate is set against live RSST.** On 2.25 years its standard error is about
6 %/yr. A gate there would rule on noise (B-5 caveat 9). The comparison is reported with its CI.

**Reported validations.**
- V1: the synthetic +100% arm (no survivorship haircut) against live RSST, 2023-10 → 2025-12.
- V2: the composite against DBMF, KMLM and CTA separately, and against BLNDX's and MAFIX's excess over
  their equity share (shape only).
- V3: the composite against AQR TSMOM on W-L3.
- V4, if level 2 runs: the composite against the index on the common window. This is the direct
  survivorship check.

**Integrity halts on fund prices.** The harness stops and lists every case; a ruling is recorded in an
amendment before any arm return is computed.
- **D1 unrecorded distribution.** A one-day raw-close fall of 3% or more, with no distribution in
  yfinance's own actions within one trading day, on a day when the median member return is above −1%.
- **D2 stale prices.** Five or more consecutive identical closes.
- **D3 gaps.** More than five consecutive missing trading days inside a fund's membership.
- **D4 implausible move.** An absolute one-day Adj Close return above 8%.

## 10. Pre-named outcomes

| outcome | what it means | what it does NOT mean |
|---|---|---|
| **H1 met** and the IR clears the MBL line at N ≈ 371 | The investable record supports the stacked overlay at the program's standard. Goes to the director and the owner as a candidate for a paper leg. | Not a deployment by itself. |
| **H1 met**, MBL not cleared at ~371 (or at 37) | "ci_low clears, MBL does not": **exploratory**. Justifies a forward clock on the real fund, nothing more. | Not deployment evidence (`[NN-MBL]`). |
| **H1 not met, interval straddles zero** | **NOT SUPPORTED on investable evidence.** The door is shut for deployment. The interval is the record: it bounds what the overlay could be worth. | Not proof the overlay loses. |
| **H1 not met, ci_high < 0** | **CLOSED.** The stacked overlay lost wealth on the investable record. | — |
| **Clears only with h_surv = 0 (S5)** | NOT MET. | Not a pass. |
| **NOT EVALUABLE** | An evaluability gate failed. No arm Δ is quoted. | Not a refutation. |
| H2 met (level 2), H1 not | Exploratory support on a longer net record. | Never overrides H1. |
| Level 3 (AQR) clears | Uninterpretable alone, as in B-5. | Never a confirmation. |

**The transport reading of the measured over-capture `h_L` (§4.3), pre-named.** The census read these
break-evens from B-5's curves, per 100% of trend notional, for the 50% overlay: `ci_low` reaches zero
at **2.00 %/yr** on 2000–2025 and **6.56 %/yr** on 1985–2025; the MBL line at N ≈ 371 is lost at
**4.46 %/yr** on 1985–2025.

| `h_L` | reading |
|---|---|
| ci_low of `h_L` > 6.56 | B-5's AQR arm no longer clears on either window: the overlay door is **closed on the deep window too**. |
| ci_low of `h_L` > 2.00 | The 2000–2025 AQR clearance is void. |
| ci_high of `h_L` < 2.00 | Both AQR windows survive a live-cost haircut. Exploratory only: carrying a 2010–2025 haircut back to 1985 assumes modern fees and costs, which is optimistic. |
| anything else | The haircut is still not pinned; say so with the interval. |

`h_L` is on B-5's basis: both arms pay the same 50 bp and 1.00%, so replacing the AQR series by the
composite is a haircut of exactly `h_L`. The two closing rows use `h_L` alone, which makes closing
harder. The surviving row uses `h_L + h_surv`, which makes surviving harder.

This reading can close; it cannot open on its own.

## 11. Predictions (frozen here; the verdict compares against them line by line)

All from memory of fund and index returns. Their purpose is to be checked.

- **Composite.** 3 members at the W-L3 start, 12 to 15 by 2022. Volatility 7–10 %/yr. Net excess
  return over cash +0.3 to +2.0 %/yr; gross of fund ERs +1.5 to +3.5 %/yr.
- **Decision cell.** Point Δ between **−1.5 and +1.0 %/yr**. CI half-width 3.5–5.5 %/yr. ci_low
  between −6 and −3 %/yr. **H1 NOT MET.**
- **+50% and +25%.** Points within ±0.6 and ±0.3 %/yr. Neither clears.
- **S5 (no survivorship haircut).** Point between −0.5 and +2.0 %/yr; ci_low < 0.
- **S1 pure-play.** Point above the broad composite's by 0 to +1.0 %/yr.
- **The flat decade.** Σ d_t over 2011–2019 between −10% and −30% of relative wealth for the +100% arm.
- **Worst 3-year relative shortfall.** Between −15% and −30%.
- **2022.** Δ between +12 and +28 pp for the +100% arm.
- **MaxDD.** The +100% arm's is between −30% and −42%, against about −34% for the benchmark (2020).
  It is not shallower in the 2020 crash.
- **Drawdown correlation.** Pooled daily correlation between −0.35 and +0.25. At least two episodes
  exceed +0.30 (early 2018 is the expected worst). 2022 is negative.
- **`h_L`.** Point between +1 and +6 %/yr, CI half-width about 4. It does not resolve either break-even.
- **AQR on W-L3, +50%.** Point between +0.5 and +3 %/yr, far below its 1985–2025 figure of +5.11.
- **V1.** Synthetic minus live RSST between −4 and +6 %/yr; the interval includes zero.
- **E2.** Correlation between 0.65 and 0.85.

## 12. The cost side, stated before the data

Per 100% of overlay the stack must first pay for itself:

| item | %/yr |
|---|---|
| stack ER over the equity fund's (1.00 − 0.09) | 0.91 |
| financing spread on the overlay | 0.50 (physically nearer 0.10–0.25) |
| variance cost of the added leg, σ²/2 at 9–13% volatility | 0.4–0.8 |
| correlation cost, ρ·σ_e·σ_x at ρ ≈ +0.1 | ~0.1 |
| **hurdle on the trend leg's excess return, gross of its own fund fee** | **about 1.9–2.3** |

From memory: net trend indices earned about 3 %/yr over cash since 2000, about 1.5–2 since 2010, and
about zero over 2011–2019. Live mutual funds earned about 0.7–1.7 %/yr over cash net since 2010, which
is about 2.0–3.2 gross of their fees. **The honest expectation for the decision cell is about −1.0 to
+0.3 %/yr, with a nine-year stretch in which the overlay costs 1.5–3 %/yr.**

## 13. Honest prior, N_trials, the MBL line and the power line

**N_trials: +1** (one family). The three overlay weights, the sensitivities, the curve, the
sub-periods, the validations and the level-3 comparison are characterization. A level-2 index admitted
before Phase 2 is inside the family; one admitted later is a new trial.

**Honest N.** The pinned gate reads N_eff 36.92, **37.08 at +1**. T-391's corrected count (built,
reviewed, not merged) is 371.28, **372.28 at +1**. Both are reported. The corrected count is the honest
one.

**The MBL line.** The required IR of the Δ series is `E[max_N]/√T`. It is an *active* ratio (arm minus
benchmark), never the arm's own Sharpe.

| window | T (yr) | IR for ci_low > 0 at 50% power | IR needed @ 37.08 | IR needed @ ~371 |
|---|---|---|---|---|
| **W-L3 (decision)** | 15.4 | 0.499 | 0.550 | **0.754** |
| W-L1 | 18.75 | 0.453 | 0.499 | 0.684 |
| W-I (SG, conditional) | 26.0 | 0.384 | 0.423 | 0.581 |
| BTOP50 (conditional) | 39.0 | 0.314 | 0.346 | 0.474 |
| W-85 (AQR, quoted) | 41.0 | 0.306 | 0.337 | 0.463 |

**The power line.** Minimum detectable effect for the +100% arm, in %/yr of Δ log wealth, as a function
of the trend leg's volatility σ (`1.96·σ/√T` for 50% power, `2.80·σ/√T` for 80%):

| window | σ = 7% | σ = 9% | σ = 11% | at 80% power, σ = 9% |
|---|---|---|---|---|
| W-L3 (15.4 yr) | 3.5 | **4.5** | 5.5 | 6.4 |
| W-L1 (18.75 yr) | 3.2 | 4.1 | 5.0 | 5.8 |

On W-I (26 years; SG Trend's volatility is about 13%) the figure is 5.0 %/yr at 50% power and 7.1 at
80%.

The plausible effect is −1.0 to +0.3 %/yr (§12), or up to about +1.3 without the survivorship haircut.
**The minimum detectable effect is three to fifteen times the plausible effect.** A true IR of 0.2
needs 96 years for a 50% chance of ci_low > 0; 0.3 needs 43 years.

**Honest prior.**
- H1 met (ci_low > 0 in the decision cell): **6 %**.
- H1 met and the MBL line cleared at N_eff 37: 4 %. At N ≈ 371: **1 %**.
- A significant loss (ci_high < 0): 6 %.
- The interval straddles zero: **about 88 %**.
- H2 met on SG Trend, if it runs: about 4 % as specified; about 30 % only if the index were restated to
  an ETF's fee, which this study does not do.

**What the study is therefore for.** It is unlikely to open the door and unlikely to close it by
significance. What it delivers:
- an investable estimate, with its interval, in place of a frictionless +5.11 %/yr;
- the over-capture measured on 15 years instead of 2.5. By §11's own prediction that interval will
  still span both break-evens;
- numbers for the drought, the worst three years and the crash correlation. These are the part most
  likely to be useful to the owner;
- the transport reading, which retires the AQR headline only if the result is extreme.

By B-8's standard (closed unrun at a minimum detectable effect three times the plausible one) a
strictly confirmatory reading would close T-398 without running it (N_trials 0). See ruling R-9.

## 14. For the owner — how this would be held, and what could go wrong

**How it is held.**
- **One ticker.** RSST (Return Stacked U.S. Stocks & Managed Futures; launched September 2023; expense
  ratio about 1.0%) is 100% US stocks plus 100% trend-following futures in a single ETF. A Roth can
  hold it like any other ETF. No margin, no options approval, no futures account.
- **Or two tickers** for a smaller overlay: half SPY and half RSST is 100% stocks plus 50% trend, at a
  blended cost of about 0.55%. Three-quarters SPY and one-quarter RSST is the 25% version, about 0.32%.
- **Fully automatable.** It is buy-and-hold. New contributions buy toward the target weights; a monthly
  or yearly rebalance between two tickers is a small job for the existing system. Wiring it into the
  live path is a separate, propose-first decision.
- **What is not available.** A managed-futures ETF bought beside SPY (DBMF, KMLM) *replaces* stocks; it
  does not stack on them. That was T-253's and T-170's question, not this one. Running futures
  directly needs a different broker and far more than $10k to spread across enough markets. Options
  strategies (collars, puts, covered calls) are already closed in the record as wealth-losing.

**What could go wrong.**
1. **A decade of nothing.** From 2011 to 2019 trend-following earned about zero. The overlay would have
   cost roughly 1.5–3% a year against plain SPY for nine years. This study will put a number on it.
2. **The fee is certain; the premium is not.** About 1% a year is paid every year. The trend premium
   after institutional fees has been about 1–3% a year, with long gaps.
3. **It does not protect in a fast crash, and can make one worse.** After a long rally a trend program
   is long stocks. In early 2018, March 2020 and April 2025 it lost alongside them. It helped in 2022
   and 2008, which were slow.
4. **Two layers of exposure in one fund.** A bad stretch for trend (its own funds have fallen 20–28%)
   on top of a stock bear market is a deeper hole than SPY alone.
5. **One manager's program is not "trend" in general.** In 2025 two trend ETFs finished 17 percentage
   points apart (DBMF +13.9%, KMLM −3.0%; route research). RSST has 2.3 years of history.
6. **Fund risk.** A small ETF can close. In a Roth that costs no tax, but it forces a decision at a bad
   moment.
7. **The evidence cannot settle it.** No investable record is long enough to confirm an edge of the
   plausible size. If this is ever held, it is held on judgment, not on a passed test.

## 15. Substrate note (`[NN-SUBSTRATE-REVERIFY]`)

- The verdict is conditional on the T-306 build of 2026-07-10 at the md5s in §3. A rebuild demotes it
  to "re-verify required".
- Every T-398 window lies after 1993, where `equity_tr` is SPY's Adj-Close total return. The pre-1993
  broad-market splice is not used.
- The fund prices are Yahoo Adj Close as of the fetch date. Yahoo restates Adj Close with every new
  distribution; the snapshot is the record.
- The AQR file is restated by its publisher on every update. Two vintages are on disk; their
  difference on the common months is reported.
- The level-1 composite is **survivor-conditioned**. The 1.0 %/yr haircut is a judgment.

## 16. Planned fetches (declared now; NONE executed; yfinance only)

All keyless and free. One snapshot under `data/t398_local/inputs/` (a real, worktree-local directory)
with `MANIFEST.json` (source, call, UTC time, rows, span, md5, yfinance version 1.2.0). The harness
verifies every md5 on every run.

**Step 1 — metadata, before any price.** For each of the 15 candidates and the anchors: yfinance
`Ticker.info` (category, inception date, net expense ratio, summary) and `Ticker.actions`
(distributions). The membership table and the ER table are then frozen in an amendment committed
alone.

**Step 2 — prices,** through `scripts/reconcile_stooq_tr_t256.py::fetch_yf_tr` (Adj Close,
`auto_adjust=False`; its writer is never called), `start="1990-01-01"`, `asof="2026-01-01"`:
- the 15 candidates: RYMFX, AQMIX, ASFYX, WTMF, EVOIX, GMSSX, CSAIX, FMF, PQTIX, ABYIX, LOTIX, AHLIX,
  DBMF, KMLM, CTA;
- the anchors: RSST, BLNDX, MAFIX, and SPY and VT for the anchors' equity share;
- S3 only: one yfinance fund-screen call on category "Systematic Trend", then prices for what it
  returns.

**Not fetched.**
- SG Trend / SG CTA: registration-gated. Needs the owner's word; the owner would supply the file.
- BTOP50 / Barclay CTA: a new source with terms to read. Needs a ruling.
- ReSolve's replication: form download.
- Yahoo `=F` futures and Stooq futures: not needed. The self-built replication is scoped out (census
  §4).
- H.15, SOFR, AQR, equity: byte copies of the md5-pinned files already on disk.
- Anything dated 2026.

## 17. Rulings requested

| # | choice | proposed | ruling |
|---|---|---|---|
| **R-1** | The decision arm | **+100%** (the single-ticker RSST structure, as the brief words it). +50% and +25% reported. | confirm |
| **R-2** | The decision composite | All 15 candidates that pass the rule, flagged funds included. The pure-play subset is S1. | confirm |
| **R-3** | The survivorship haircut inside the decision cell | **1.0 %/yr**, with zero reported as S5. | **yes** |
| R-4 | Fees | Each fund grossed up by its own ER (capped at 2.00%), the stack's 1.00% charged once (B-5's rule for DBMF). The double-fee version is S4. | confirm |
| R-5 | Financing | 50 bp on the whole overlay notional; the 0–400 bp curve reported. | confirm |
| R-6 | Windows | W-L3 by the ≥ 3-member rule; end 2025-12-31; 2026 held out. | confirm |
| R-7 | Bootstrap | 21-day primary (B-5's), automatic and 252-day sensitivities, the block-fragility rule. | confirm |
| **R-8** | Level 2 | Does the owner want to register for the SG indices and supply the file? May BarclayHedge's public table be read? If neither, level 2 does not run. | **yes (owner)** |
| **R-9** | Run, or close on power | **Recommended: run level 1 once, as an estimate, expecting H1 NOT MET.** It costs one trial and about a day, the owner asked the question directly, and it replaces a frictionless number in the record with an investable one. It is unlikely to change a decision. The alternative, equally defensible, is to close on §13's power analysis as B-8 was closed. | **yes** |
| R-10 | Metadata before prices | Membership and ERs verified from yfinance metadata and frozen in an amendment before any price is loaded. | confirm |
| R-11 | The transport reading of `h_L` | Pre-named secondary (§10); can close, cannot open. | confirm |
| R-12 | The self-built futures replication | Not built (census §4). | confirm |
| R-13 | A forward clock on RSST itself | Out of scope here (`paper_trader/` is not touched). The verdict will carry a short proposal with gates frozen at t = 0, on the T-316 pattern (0 trials). It is the only instrument that can eventually answer the question. | note |

**No blocker to Phase 2** beyond the acknowledgment and these rulings. Level 2 is blocked on R-8.

## 18. Fail-closed conditions and the census block (`[NN-FAIL-CLOSED]`, `[NN-CENSUS]` in spirit)

The harness halts, with a non-zero exit and no number written, on any of:
- an input md5 that differs from the manifest or from §3;
- an evaluability gate (E1–E4) failing, or an integrity flag (D1–D4) without a recorded ruling;
- fewer than 3 members on any day of W-L3;
- a member with no ER (neither yfinance nor the fallback table);
- a financing-base gap of more than 5 business days, or any rate outside [−1%, +25%];
- a NaN or infinity in any return inside a window;
- any row dated 2026 in a loaded series;
- the primary bootstrap run with n ≠ 1000 or block ≠ 21;
- a determinism ×2 md5 mismatch.

Standard-deviation guards use tolerance (`std < 1e-12 or not np.isfinite`), never `== 0`
(`[NN-FP-GUARDS]`).

Every results file carries a `census` block: input md5s; the membership table with each fund's entry
and exit dates and ER source; the member count by year; the window dates and bar counts; the integrity
flags and their rulings; the gate values; the bootstrap settings; the output md5s.

## 19. Sequence

1. This pre-registration (this commit, alone).
2. **STOP → the director's acknowledgment and the rulings of §17.**
3. Metadata fetch → the membership-and-ER amendment, committed alone.
4. Price fetch → snapshot and manifest.
5. Integrity checks (D1–D4) → rulings recorded if any fire.
6. Evaluability gates (E1–E4) and the reported validations.
7. Smoke on the first 12 months of W-L3 and W-L1. Nothing from it is quoted.
8. The full run, twice, to identical md5s.
9. The verdict, with §11's predictions compared line by line.
10. The full test suite; commit on `research/stacked-trend-overlay-t398`. New CLI goes in
    `docs/Core/execution_manual.md`.

Script: `scripts/t398_stacked_trend_overlay.py`. Tests: `tests/test_t398_stacked_trend_overlay.py`.
Outputs: `data/t398_local/`.

## Reproduce the census

See `docs/Sources/census_t398_stacked_trend_overlay_2026-11-14.md` §8. Every command there is
read-only and uses no network.
