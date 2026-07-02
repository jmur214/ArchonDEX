---
task_id: T-2026-07-02-265
title: Survivorship-complete small-cap panel + PEAD low-coverage event-study pilot
date: 2026-07-02
author: Agent D (measurement lane)
type: PRE-REGISTERED event study (1 trial, N_trials += 1) + data-integrity report
status: DONE — H0/NULL (robust); no Norgate purchase. Branch feature/smallcap-pead-pilot-t265
---

# T-265 — small-cap survivorship-complete panel + PEAD low-coverage pilot

This reverses my own T-249 wall ("no free survivorship-free small-cap data"). The gap audit found
Alpaca serves delisted names; the honest, verified refinement is below.

## FOUNDATIONAL DATA-REALITY FINDINGS (verified this session, BEFORE the study) — these reshape the premise

1. **"$0" is only true for a ~2020-2026 window; the 2016-2026 panel requires SIP (paid, already-owned).**
   The FREE Alpaca IEX feed floors at **~2020-07-27** (verified: AAPL/most names first bar 2020-07-27;
   SPY 2018-11). Every name that delisted 2016→mid-2020 returns **0 IEX bars** (GNC, JCP confirmed) — a
   real survivorship hole on the free tier. The account's keys ALSO carry **SIP** access, which serves
   full **2016-01-04+** history INCLUDING pre-2020 delistings (GNC 2016→2020-06, JCP 2016→2020-05
   verified). So the 2016-2026 survivorship-complete panel IS buildable — via SIP, a paid Alpaca data
   subscription this account already holds. **Honest label: "$0-marginal to this account," NOT
   "free-tier / reproducible-by-anyone-at-$0."** A strictly-free reproduction is limited to ~2020-2026
   (and is survivorship-holed pre-2020). Census records the feed used per name.

2. **`/v2/assets?status=inactive` is an UNRELIABLE delisting list.** It returns 19,243 "inactive"
   us_equity assets, but the list is dominated by non-common-stock corporate-action artifacts
   (CVR/RGT/ESC/CNT identifiers, e.g. `003CVR016`), and real delistings are frequently marked ACTIVE
   (FRAN, BBBY, REV, SIVB, ATVI all verified delisted yet flagged active). Some tickers return phantom
   bars past their delisting (BBBY, CBL to 2026-06 — reused/reorganized tickers). **We therefore do NOT
   source delistings or the universe from the Alpaca flag.** The survivorship-complete universe comes
   from **EDGAR XBRL frames** (every filer per period, delisted included by construction).

3. **EDGAR XBRL frames = the survivorship-complete, estimate-free earnings backbone.** Verified:
   `frames/us-gaap/EarningsPerShareDiluted/USD-per-shares/CY{Y}Q{Q}` returns every filer's quarterly
   diluted EPS (CY2019Q1 → 3,360 filers; CY2023Q1 → 4,994), and per-CIK `companyconcept` carries the
   `filed` date + `form` (the event date) + `fy`/`fp`. Shares frames (`CommonStockSharesOutstanding`)
   give the share count for market-cap sizing. This is survivorship-complete (a since-delisted firm is
   still in its historical quarter's frame) and estimate-free (no analyst consensus needed).

## Framing (load-bearing — per the brief)
This is an **EVENT STUDY** — the statistic of interest is the **t_HAC on post-announcement abnormal
returns** pooled across thousands of earnings events — NOT a Sharpe-clearing deployment backtest. The
~10yr (or ~6yr free) window **cannot clear the MBL deployment bar (~1.05 Sharpe at honest N)**, and no
Sharpe headline here should be read as deployment evidence (`[NN-MBL]`). Statistical power comes from
the **event count**, not the calendar span. This pilot decides one thing: is there enough signal to
justify the **Norgate Platinum ($346.50, 1990+, PIT Russell 2000)** purchase for a deployment-grade test.

## Hypothesis (pre-registered, H1)
In low-coverage US small-caps 2016-2026, positive-SUE stocks earn positive factor-adjusted abnormal
returns over the **[+2, +63] trading-day** window after the earnings **filing date** (post-earnings
announcement drift, Bernard-Thomas 1989), and the **top-minus-bottom SUE quintile** drift is positive.
Per Hong-Lim-Stein (2000), the drift is **larger in smaller / lower-institutional-ownership** names
(the "retail-advantaged-universe" signature) — this interaction is the specific thing the price-machine
H0 could not have seen.

## Method (pre-registered — no parameter sweep; these are fixed BEFORE results)
- **Universe:** union of all CIKs in the EPS frames CY2016Q1..CY2026Q1 (survivorship-complete). Map
  CIK→ticker (SEC `company_tickers.json` + the existing `data/edgar/cusip_ticker_map.parquet`; record
  join loss). Keep names with SIP daily bars. **Small-cap filter:** market cap (shares × price at the
  event) in **$50M–$2B** at the event date; micro = <$300M, small = $300M–$2B.
- **SUE (estimate-free, seasonal random walk, Bernard-Thomas):**
  `SUE_q = (EPS_q − EPS_{q−4}) / σ(ΔEPS)` where σ is the std of the trailing 8 seasonal differences
  `EPS_{t} − EPS_{t−4}`. Requires ≥8 prior quarters → an event needs ~3yr of EPS history. Winsorize SUE
  at ±3σ. (No analyst estimate → survivorship-complete and coverage-unbiased.)
- **Event date:** the `filed` date of the 10-Q/10-K carrying that quarter's EPS (EDGAR). Entry at the
  **+2 open** (skip the announcement-day jump; +1 to allow the filing to be public) → tradable.
- **Abnormal return:** two definitions, both reported — (a) **market-adjusted** (`r − r_SPY`); (b)
  **factor-adjusted** residual (FF5+Mom via `core/factor_decomposition`) as robustness. CAR over
  [+2,+63] (~one quarter of drift).
- **Delisting / truncation handling (`[NN-CENSUS]`/`[NN-FAIL-CLOSED]`):** a name whose SIP bars stop
  before the window end is a delisting/truncation. **Two arms:** (i) *last-price* — CAR uses whatever
  bars exist (the naive, optimistic read); (ii) **bankruptcy-haircut-to-zero stress arm** — for events
  whose price series terminates within the window AND the EDGAR form stream also stops (no further
  filings ⇒ likely dead), set the terminal return to **−100%** from the last observed price. Report both;
  the gap between them is the delisting-bias magnitude.
- **Low-coverage proxy:** size tercile × **13F institutional-holder count** tercile
  (`data/edgar/13f/ownership_panel.parquet`, `n_holders`; low n_holders = low coverage). Report the
  drift in each cell — the pre-registered prediction is monotone: **largest drift in micro × low-13F.**
- **Cost:** the T-249 honest small-cap model — **35 bps** half-spread (small), **75 bps** (micro) —
  charged on entry+exit of a long-top-SUE-quintile monthly-formed portfolio (and the L/S variant).

## Gates (pre-registered)
- **Primary (signal exists):** pooled top-minus-bottom SUE-quintile mean CAR[+2,+63] **> 0 with
  t_HAC ≥ 2.0** (Newey-West, ~21-lag), GROSS.
- **Tradable (survives cost):** the long-top-quintile drift (and the L/S) remains **positive net of the
  35/75bps honest small-cap cost**. If it dies at honest cost → the T-249 "cost is the assassin" verdict
  extends to PEAD → FAIL.
- **Low-coverage signature:** drift is larger in micro × low-13F than in small × high-13F (the
  Hong-Lim-Stein monotone). If PEAD is FLAT across coverage → it's not the retail-advantaged effect.
- **Robustness:** the sign/significance survives the bankruptcy-haircut-to-zero stress arm.

## Decision rule (pre-registered)
- **Signal survives net-of-cost, low-coverage-concentrated, robust to haircut** → recommend the Norgate
  Platinum ($346.50) purchase to the user WITH this pilot as evidence (deployment-grade test on 1990+
  PIT Russell 2000). This is a user-gated spend decision, not an autonomous one (`[NN-AI-GATE]`-adjacent).
- **Null, or cost-killed, or not low-coverage-concentrated** → the free-window retail-advantaged-universe
  thesis **closes honestly** at $0; no Norgate spend.

## Honest prior
PEAD is among the most-replicated anomalies and is documented LARGER in small/low-coverage names, so the
prior that SOME gross drift exists is **HIGH**. But the prior it **survives honest small-cap costs net**
and is big enough to justify a paid-data deployment test is **MODERATE** — cost was the T-249 assassin,
and the drift is slow (a quarter-long hold on names with 35-75bps spreads). N_trials += 1.

---
## RESULTS

### Panel integrity / census (`[NN-CENSUS]`)
| stage | count | note |
|---|---|---|
| EDGAR EPS-frames universe (2013-2026 union) | **9,373 CIKs** / 191k rows | survivorship-complete by construction (delisted firms are in their historical quarter's frame) |
| CIK→ticker mapped | **6,034 (64%)** | live SEC list 4,904 + **1,130 delisted recovered** via EDGAR-name↔Alpaca-name match |
| — residual unmapped | 3,339 (36%) | **the free-data survivorship hole at the join** — no free survivorship-complete CIK↔ticker link table exists (a weaker echo of the T-249 wall) |
| SIP price series obtained | 4,674 tickers | free IEX floors ~2020-07; **SIP (paid, account-owned) reaches 2016+ incl pre-2020 delistings** |
| eps_filed (first-reported, PIT) | 130,693 rows / 4,609 CIKs | companyconcept `filed` dates + first-reported EPS |
| **small-cap events ($50M–$2B)** | **24,990 across 1,891 names** | 1,065 dead/haircut, 1,069 truncated — real delisted representation |
| 8-K item-2.02 announcement match | 23,067 / 24,990 (92%) | **median filed−announce gap = 1 day** (small-caps file the 10-Q ≈ with the earnings 8-K) |

### PEAD event study — market-adjusted CAR, by estimate-free SUE quintile
| entry | top−bottom CAR (quarter) | nw_t | monotone? | verdict |
|---|---|---|---|---|
| 10-Q filing +2 | **+0.55%** | **+0.34** | no (Q0<Q1≈Q2>Q3<Q4) | not significant |
| 8-K announcement +1 | **+0.60%** | **+0.45** | no | not significant |
| — matched-only (n=23,067) | +0.59% | +0.84 | no | not significant |
| **DECILE d9−d0, announcement** | **+0.82%** | **+0.09** | — | not significant |
| haircut-to-zero stress arm (quintile) | +1.37% | +0.40 | no | not significant |

Per-quintile CAR (announcement entry): q0 +0.53%, q1 +0.94%, q2 +0.76%, q3 +0.63%, q4 +1.13%. The
**sign is correct** (q4 > q0) — the SUE is measuring the right thing — but the spread is economically tiny
(~0.6% quintile / 0.8% decile over a full quarter vs the literature's ~3–6%) and statistically
insignificant (t ≈ 0.1–0.8 « the pre-registered 2.0 gate). All quintiles carry a common ~+0.5–1.1%
small-cap market-adjusted drift; there is **no tradable SUE-sorted edge**.

### Low-coverage signature (Hong-Lim-Stein) — ABSENT (announcement entry, top−bottom CAR)
| | low-13F | high-13F |
|---|---|---|
| micro (<$300M) | **−0.11%** (n=7,349) | +7.38% (n=828, small-sample noise, wrong direction) |
| small ($300M–$2B) | +1.74% (n=4,264) | +0.28% (n=10,626) |

The pre-registered monotone prediction (largest drift in micro × low-13F) **fails**: the prime cell is
FLAT/negative. The one large cell is 828-event noise in the *wrong* direction. (Caveat: the 13F panel was
built for large/mid-caps [T-145] → small-cap `n_holders` coverage is thin, so the 13F axis is
underpowered — but the clean SIZE axis agrees: micro shows no more PEAD than small.)

### Tradability + cost
Long top-SUE-quintile, ~61td hold: gross +1.28%/event (~+5.3%/yr market-adjusted, the common small-cap
drift), net of the honest 35/75bps round-trip small-cap cost +0.29%/event (~+1.2%/yr) — but this is the
*absolute* market-adjusted return of one quintile, not a SUE edge; the SUE **spread** (+0.6%, t≈0.4) is
what a signal needs and it is insignificant and would not survive as a long/short net of cost.

## VERDICT — H0 / NULL (robust, decisive). The retail-advantaged small-cap PEAD thesis closes at $0.
PEAD does **not** survive as a significant, monotone, low-coverage-concentrated, cost-surviving SUE-sorted
signal in the survivorship-complete free/SIP small-cap universe 2016-2026. The null is robust across:
entry timing (filing vs announcement, ~1 day apart), sort granularity (quintile AND decile), and the
delisting stress arm (haircut-to-zero does not manufacture a spread → the null is **not** a survivor-bias
artifact). The classic effect is directionally present but ~5–10× too small and insignificant, and it does
**not** concentrate in the smallest names — the specific "retail-advantaged-universe" prediction fails.

**Per the pre-registered decision rule → NO Norgate Platinum ($346.50) purchase.** The pilot found no
signal worth a deployment-grade test. Two honest doors remain but neither argues *for Norgate specifically*:
(1) **estimate-free SUE is noisier than analyst-forecast SUE** — a sharper (paid, e.g. I/B/E/S) estimate
*might* lift the sort, but that is a *different* data bet than Norgate (prices + Russell membership), and
the size/coverage-concentration test — which is estimate-agnostic — already fails, undercutting the whole
retail-advantaged premise; (2) the residual 36% CIK↔ticker join loss is a real free-data limitation, but
the delisting stress arm shows closing it would not overturn the null.

**Consistency with the strategic arc:** this extends the "comprehensive H0" coverage test (T-250 calendar,
T-254 factor-momentum) into the small-cap/low-coverage universe the price-machine sweep could not see — and
PEAD, the textbook small-cap anomaly, does not clear the honest bar here either. N_trials += 1.

### Reproducibility (`[NN-CENSUS]`)
`scripts/smallcap_pead_pilot_t265.py` (staged: `edgar|map|prices|study|announce`, all cached to
`data/research/t265/`). EDGAR frames/companyconcept/submissions are public+free; prices need the
account's SIP entitlement (recorded, NOT free-tier). No secrets committed.

