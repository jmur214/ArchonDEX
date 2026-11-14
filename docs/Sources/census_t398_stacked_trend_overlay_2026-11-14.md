---
task_id: T-398
title: Census notes — investable evidence for a stacked trend overlay on 100% equity (inputs for the T-398 pre-registration)
date: 2026-11-14
worker: regime-analyst lens (in-session worktree subagent), branch research/stacked-trend-overlay-t398
status: Phase 1, read-only. NOTHING was fetched. No strategy, arm, fund, composite or benchmark return was computed. The only arithmetic is a reading of B-5's results already on disk (§5) and the MBL line (§6).
basis_legend: "D = read from disk today; B5 = B-5's merged record; M = FROM MEMORY, unverified, to be confirmed by the planned yfinance metadata fetch before the prereg is frozen"
---

# T-398 census — what investable, net-of-fee trend evidence exists, and what it can and cannot decide

## 0. The five findings that shape the pre-registration

1. **The investable record is short and survivor-conditioned.** Trend mutual funds and ETFs that
   yfinance can serve start in 2007 (one fund), reach three funds in 2010 and about ten by 2014. Dead
   funds are not fetchable from yfinance, so any composite built in 2026 holds survivors only.
2. **B-5's AQR arm survives the two measured over-captures on 1985–2025 and fails both on 2000–2025**
   (§5). The break-even haircut on the trend leg is **6.56 %/yr** (W-85, 50% overlay) and
   **2.00 %/yr** (W-00m). The measured over-captures are 2.9 and 5.3 %/yr, each on about 2.5 years.
3. **At the corrected honest N (~371) the W-85 arm's MBL line binds at a haircut of about 4.5 %/yr**,
   which sits between the two measured over-captures. The haircut is the one number that decides
   whether the deep-window evidence stands. Neither existing reading measures it to better than about
   ±6 %/yr (§5.3).
4. **A stacked overlay has a fixed hurdle before it adds anything.** Per 100% of overlay: the stack's
   expense-ratio increment (1.00 − 0.09 = 0.91 %/yr), the financing spread (0.10–0.50 %/yr) and the
   variance cost of the added leg (σ²/2 ≈ 0.4–0.8 %/yr). The trend leg must earn **about 1.5–2.3 %/yr
   over cash, gross of its own fund fee**, to break even. Net CTA indices earned roughly 1–3 %/yr over
   cash since 2000 and about zero over 2011–2019 (M).
5. **No investable record can confirm an effect of the plausible size at the program's standard.** A
   true information ratio of 0.2–0.3 needs 43–96 years for a 50% chance of `ci_low > 0`, and about 97
   years to clear the MBL line at N ≈ 371. The live-fund window is 15.4 years (§6). The frictionless
   factor "clears" because its IR (0.81) is inflated, not because the question is easy.

## 1. Live funds obtainable free and keyless through yfinance (`fetch_yf_tr`, Adj Close, `auto_adjust=False`)

**None of the mutual funds is on disk** (the Stooq dump has no mutual funds). First-bar dates marked D
come from the on-disk Stooq dump (`data/raw/stooq/daily/us/`) or B-5's yfinance snapshot. Everything
marked M is from memory and is a candidate to verify, not a fact.

### 1.1 Trend / managed-futures funds (candidates for the composite)

| ticker | fund (M) | first bar | ER (M) | known problems (M unless marked) |
|---|---|---|---|---|
| RYMFX | Guggenheim (Rydex) Managed Futures Strategy | 2007-03 (M) | ~1.7% | Tracked the S&P Diversified Trends Indicator (no equity-index futures, energy never short) until about 2012, then became an actively managed multi-strategy fund. The only fund covering 2008. T-171 measured it capturing 28% of AQR's 2008 gross gain (B5-era record). |
| AQMIX | AQR Managed Futures Strategy I | 2010-01 (M) | ~1.25% | The cleanest live analogue of the AQR factor (same authors). Signal set widened after 2018. A 1.5×-vol sibling (QMHIX, 2013) is the same program. |
| ASFYX | Virtus AlphaSimplex Managed Futures Strategy Y (ex Natixis ASG) | 2010-07 (M) | ~1.45% | Adviser sold Natixis → Virtus in 2023; ticker continuity on yfinance unverified. |
| WTMF | WisdomTree Managed Futures Strategy | **2011-01-10 (D)** | ~0.65% | Tracked the same Diversified Trends Indicator as RYMFX until about 2016, then a WisdomTree index, then active. Low volatility. Duplicates RYMFX's program in 2011–2012. |
| EVOIX | Altegris Futures Evolution Strategy I | 2011-10 (M) | ~1.6% + embedded manager fees | Trend via Winton/ISAM swaps (Winton cut its trend weight about 2018). Collateral is an actively managed bond sleeve, so the fund carries duration and credit beta. |
| FMF | First Trust Managed Futures Strategy | **2013-08-07 (D)** | ~0.95% | Index tracker (Morningstar Diversified Futures) turned active. Very low volatility. |
| PQTIX | PIMCO TRENDS Managed Futures Strategy Inst | 2013-12 (M) | ~1.4–1.7% | Collateral actively managed (short-duration). Reported ER includes interest expense. |
| ABYIX | Abbey Capital Futures Strategy I | 2014-07 (M) | ~1.8% + embedded manager fees | Multi-manager; a majority, not all, is trend. |
| LOTIX | LoCorr Market Trend I | 2014-07 (M) | ~1.75% | Single sub-adviser (Graham). |
| AHLIX | American Beacon AHL Managed Futures Strategy | 2014-08 (M) | ~1.5% | Added by this census: a pure trend program with 11 years of history. AHLT (ETF, 2023-09-01 D) is the same program. |
| GMSSX | Goldman Sachs Managed Futures Strategy Inst | 2012-02 (M) | ~1.0% | Added by this census. Existence and strategy to verify. |
| CSAIX | Credit Suisse Managed Futures Strategy I | 2012-09 (M) | ~1.3% | Added by this census. Tracks a rules-based trend index. May have been liquidated or renamed after the 2023 UBS takeover, in which case it is unfetchable. |
| DBMF | iMGP DBi Managed Futures Strategy ETF | **2019-05-08 (D, B5)** | 0.85% (B5) | Replicates the SG CTA index by regression, not SG Trend. Correlation 0.88, TE 6.76%, a "3-sigma miss" in 2023 (route research). |
| KMLM | KFA Mount Lucas Managed Futures Index ETF | **2020-12-03 (D)** | 0.90% (B5) | Rules-based; commodities, currencies and rates only, no equity-index futures. |
| CTA | Simplify Managed Futures Strategy ETF | **2022-03-09 (D)** | ~0.75% (M; the route research's 0.35% is flagged "re-check") | Short history. |

Launched 2023 or later and on disk in the Stooq dump (D): AHLT 2023-09-01, TFPN 2023-07-13, MFUT
2024-05-30, HFMF 2025-07-15. They add nothing before 2023 and are left out of the composite by a
launch-date rule (prereg §5.2).

On disk but **not** trend funds, named so they are not mistaken for one: TRND (a trend-timed
fund-of-funds), FLSP (multi-factor premia), and `btop.us.txt` (an unrelated ETF ticker, not the BTOP50
index).

### 1.2 Stacked funds (the vehicles, and the validation anchors)

| ticker | structure (M unless marked) | first bar | ER | note |
|---|---|---|---|---|
| RSST | 100% US equity + 100% managed-futures trend | **2023-09-06 (D, B5)** | 1.00% frozen in B-5 (0.95% management fee; ~0.99–1.04% total, M) | The decision arm's structure. 2.3 years of history. |
| RSSB | 100% global equity + 100% Treasury futures | **2023-12-05 (D, B5)** | 0.41% (B5) | B-5 refuted the structure (+0.21 %/yr, CI [−1.91, +2.30]). Not a trend vehicle. |
| NTSX | 90% US equity + 60% Treasury futures | **2018-08-02 (D, B5)** | 0.20% (B5) | Same; not a trend vehicle. |
| RSBT | 100% bonds + 100% trend | **2023-02-09 (D)** | ~0.95–1.06% (M) | Same trend program as RSST on a bond base. Wrong base for a maximum-wealth investor. |
| BLNDX | Standpoint Multi-Asset: ~50% global equity + a full trend program | 2019-12 (M) | ~1.25% (M) | The longest live equity-plus-trend fund. Not 100/100. A reported anchor, never a composite member. |
| MAFIX | Abbey Capital Multi Asset: equity futures + managed futures | 2018-04 (M) | ~1.8% (M) | Reported anchor only. |

### 1.3 The honesty problems of the live-fund route

- **Survivorship.** Every ticker above is alive in 2026. Managed-futures mutual funds that liquidated
  after the 2011–2019 drought are delisted on Yahoo and cannot be fetched. Literature anchor (M):
  survivorship in equity mutual funds is 0.9 %/yr (Elton–Gruber–Blake 1996) to 1.5 %/yr (Malkiel
  1995). Nothing measured exists for this category. The prereg carries a pre-declared 1.0 %/yr haircut
  for it.
- **Strategy changes.** RYMFX, WTMF and FMF each changed strategy at least once; EVOIX and PQTIX carry
  collateral beta. They are flagged, kept in the broad composite, and removed in a named sensitivity.
- **Distributions.** These funds pay large, irregular December distributions. If Yahoo's Adj Close
  misses one, the series shows a false one-day loss of several percent. The prereg has a halt-and-rule
  guard for it. Yahoo's handling of these particular funds is unverified.
- **The window starts at the worst moment for trend.** Three funds are alive only from mid-2010, so the
  decision window opens after 2008 and at the start of the flat decade. That is what the investable
  record is. It is adverse to trend in the way a 2000 start is adverse to equity.
- **Fees differ from the vehicle's.** The funds charge 0.65–1.8 % (plus embedded manager fees in three
  of them); the stacked ETF charges about 1.00 % for both legs. The prereg grosses each fund up by its
  own reported ER and charges the stack ER once (B-5's rule for DBMF), and reports the double-fee
  version beside it.

## 2. Published net-of-fee CTA / trend indices (all M unless marked; none on disk)

| index | history | construction | access | known biases |
|---|---|---|---|---|
| **SG Trend** | 2000-01 →, daily | 10 largest trend CTAs open to investment, equal weight, annual reconstitution, net of fees, includes collateral interest | **Registration required** (the route research's record, D). Not registered; no contact detail submitted. | No survivorship after launch (a closed fund's returns stay in). Possible launch backfill for the first years. Selected on size. Net of institutional fees (about 1–2% plus 15–20% of profit), which are heavier than a 1% ETF. Not investable. |
| **SG CTA** | 2000-01 →, daily | 20 largest CTAs (not all trend), same rules | Registration required | Same. DBMF's target. |
| **BTOP50** (BarclayHedge) | 1987-01 →, monthly | The largest investable CTA programs making up at least 50% of industry assets, selected each January | The route research lists it as "free"; a public monthly table is believed to exist. Automated reading of it is a new external source and a terms question → needs a ruling. | Annual selection limits backfill. Includes non-trend CTAs. Net of fees. |
| **Barclay CTA Index** | 1980-01 →, monthly | Equal-weight average of several hundred reporting programs with at least four years of history | As BTOP50 | Self-reporting and delisting bias; equal weight favours small programs nobody could have bought in size; the four-year rule removes instant-history backfill. |
| **Credit Suisse Managed Futures** | 1994-01 →, monthly | Asset-weighted, minimum size and track record | Registration required | Database-based; mild survivorship. |
| **ReSolve's SG Trend replication** | 2000-01 → 2023-01, daily, gross and net | A hypothetical replication, not fund returns | Form download (route research, D) | Hypothetical; ends 2023. |
| **AQR TSMOM** | 1985-01 → 2026-05, monthly (D) | Paper long/short 12-month momentum on 58 instruments | **On disk** | Gross of all fees and costs. The file itself says AQR "reconstructs the full history each time the returns are updated" (D): it is not point-in-time. |

**Literature haircuts for CTA data (all M, to be re-verified before any is used):**
- Fung and Hsieh (1997, 2000): survivorship about 3.5 %/yr and instant-history about 1.4–3.6 %/yr in
  CTA *databases*.
- Bhardwaj, Gorton and Rouwenhorst (2014): after correcting both, the average CTA earned about
  T-bills + 1.8 %/yr net over 1994–2012, not statistically different from zero. Gross returns were
  about T-bills + 6 %/yr, so fees took about 4 %/yr.
- Hurst, Ooi and Pedersen (2013, 2017): paper trend is positive in every decade since 1880; with a
  2-and-20 fee and estimated costs the gross-to-net gap is of the order of 4–6 %/yr.

These numbers concern databases and gross factors. A live-calculated index such as SG Trend has far
less of the database bias. The 4–6 %/yr gross-to-net gap is the same order as B-5's W-85 break-even
haircut (6.56 %/yr), which is why the pre-2000 part of the AQR result cannot be taken at face value.

## 3. What is already on disk

| item | path | span | md5 | note |
|---|---|---|---|---|
| AQR TSMOM (B-5's file) | `data/research/aqr_tsmom_monthly_t296.xlsx` (byte copy in `data/research/b5/inputs/`) | 1985-01-31 → 2026-05-29, 497 months | `5bcb8dbf28146f729b99b629147bb0cd` | Columns TSMOM, ^CM, ^EQ, ^FI, ^FX. Excess returns. |
| AQR TSMOM (older snapshot) | `data/external/aqr/aqr_tsmom_monthly_snapshot_20260615.xlsx` | 1985-01-31 → 2025-01-31, 481 months | `33b749ff2b70ee3436140b434f9516a4` | A second vintage. The two allow a restatement check in Phase 2. |
| Equity leg (T-306) | `data/research/substrate_multidecade/equity_tr_daily.csv` | 1926-07-01 → 2026-04-17, 26,224 rows | `c2030019b8846792b5f8e3d18421c905` | SPY Adj-Close TR from 1993-02-01. |
| Cash leg (T-306) | `…/cash_daily.csv` | 1926-07-01 → 2026-05-29 | `28a1446d578e3867c2a1d3b33eabe182` | **Quantized to 1 bp/day (health MEDIUM). Not used.** |
| 3-month bill (H.15) | `data/research/b5/inputs/frb_h15_all_sdmx.zip` | 1954-01-04 → 2026-11-09 | `50fa80972f99b5f8ea06ef52483c5926` | B-5's financing base to 2018-04-02. Filter on `OBS_STATUS="A"`, never on the value. |
| SOFR | `data/research/b5/inputs/nyfed_sofr.csv` | 2018-04-02 → 2025-12-31, 1,936 rows | `8cbceec98342202d2168618b48822ade` | Ends 2025-12-31, which bounds every window. |
| B-5 yfinance snapshot | `data/research/b5/inputs/yf_{DBMF,RSST,RSSB,NTSX,SPY,…}.csv` | DBMF 2019-05-08 →, RSST 2023-09-06 →, RSSB 2023-12-05 →, NTSX 2018-08-02 →, SPY 1993-01-29 →; all to 2025-12-31 | in `MANIFEST.json` | Adj Close, `auto_adjust=False`. |
| B-5 results | `data/research/b5/run_A/results.json` | — | `9c63575d…` (verdict §1) | Holds the 81-point spread curves used in §5. |
| ETF price files | `data/processed/tr_reconciled/{DBMF,KMLM}_1d.csv`; Stooq dump for WTMF, FMF, CTA, RSST, RSSB, RSBT, NTSX | see §1 | — | Stooq is price-only. Not used for returns. |
| Gold front-month close | `data/research/gold_gcf_t255.csv` | 2000-08-30 → 2025-12-31 | `77fa0313aef1deb32a0ef4a8ffc18323` | The only futures series on disk. |

No continuous-futures panel, no CTA index and no trend mutual fund is on disk.

## 4. The third option — a self-built 12-month time-series-momentum replication (scope only)

- **Data.** Not on disk. Yahoo `=F` series cover about 25 US-listed markets from roughly 2000-08 (M;
  gold's 2000-08-30 start is confirmed on disk). The 15-market, 2000-start requirement is probably
  met for US markets only; there are no Bund, JGB, FTSE or Nikkei futures. Stooq futures are
  bot-walled (route research).
- **The honesty problem is structural.** Yahoo's series are unadjusted front-month prices. On each
  roll the price jumps by the gap between two contracts. That gap is the carry. A return computed from
  the series therefore equals the spot change and gets the roll yield wrong in sign-dependent ways:
  it understates what a short earns in a contango market (natural gas, crude in 2009–2019) and what a
  long earns in bonds. Roll dates are not flagged, and without the back-month price the gap cannot be
  removed. Both the signal and the profit are corrupted. The route research already ruled: "a home
  replication on Yahoo front-month data is worse than DBMF by construction."
- **An honest version needs individual-contract data.** That is a paid feed (tens of dollars a month)
  and the owner's decision.
- **Cost.** About two days for a harness, tests and a cost model. It adds a fork space (lookback,
  volatility scaling, universe, cost assumptions), each a trial.
- **What it would prove.** Another paper factor with costs assumed by us. It is the same kind of
  evidence as the AQR series, and weaker. It does not answer the investable question.
- **A spot-ETF trend basket already exists in the record, and it is not this.** T-108 built a
  long-only trend rotation on eight ETFs (SPY, TLT, GLD, USO, UUP, EEM, IEF, DBC), 2008–2025: Sharpe
  0.51 with ci_low 0.085, but negative skew, and its integrated form was refuted (T-128r). It cannot
  go short, it has no futures carry, and a Roth cannot stack it on top of 100% equity without the
  levered-ETF financing B-5 priced.
- **Verdict.** Not recommended. Its only real use is a later direct micro-futures program, which is not
  a Roth-at-Alpaca instrument and needs far more than $10k to diversify.

## 5. Break-even haircut on the AQR trend leg, read from B-5's results (no new run)

### 5.1 The arithmetic

B-5's arm (iv) month return is `e_m − 0.09 %·(1−w)/12 + w·(τ_m − s/12 − 1.00 %/12)`. A constant haircut
`h` on the trend leg enters exactly where the spread `s` enters. B-5 wrote `ci_low` at 81 spreads from
0 to 400 bp with the same bootstrap draws at every spread. So:

    ci_low(haircut h, at s = 50 bp)  =  ci_low(s = 50 bp + h)  on the curve already on disk
    break-even haircut  h*  =  s*_ci − 50 bp

`h` is per 100% of trend notional, and it is **on top of** the 50 bp spread and the 1.00 % ER the arm
already pays. Where the curve is still positive at 400 bp, `h*` is extrapolated with the curve's own
slope and labelled. First-order check: `h* ≈ ci_low / w`.

### 5.2 The table

Source: `data/research/b5/run_A/results.json`, block `monthly`. Δ is Δ log wealth in %/yr vs 1× equity.

| window | overlay | point Δ | ci_low | curve slope (per 1 %/yr of haircut) | **break-even haircut, ci_low → 0** | break-even, point → 0 |
|---|---|---|---|---|---|---|
| W-85 (1985–2025, 41 yr) | 50% | +5.11 | +3.25 | −0.495 | **6.56 %/yr** (extrapolated; first-order 6.49) | 10.34 |
| W-85 | 25% | +2.61 | +1.67 | −0.247 | **6.75 %/yr** (extrapolated; first-order 6.69) | 10.53 |
| W-00m (2000–2025, 26 yr) | 50% | +3.47 | +0.99 | −0.496 | **2.00 %/yr** (on-disk `s*_ci` 249.8 bp − 50) | 7.00 |
| W-00m | 25% | +1.79 | +0.55 | −0.249 | **2.19 %/yr** (on-disk `s*_ci` 269.2 bp − 50) | 7.20 |

Against the two measured over-captures:

| window | overlay | ci_low after 2.9 %/yr (B-5) | ci_low after 5.3 %/yr (T-296) | point after 2.9 / 5.3 |
|---|---|---|---|---|
| W-85 | 50% | **+1.81** (clears) | **+0.62** (clears) | +3.68 / +2.49 |
| W-85 | 25% | +0.95 (clears) | +0.36 (clears) | +1.89 / +1.29 |
| W-00m | 50% | **−0.45** (fails) | **−1.64** (fails) | +2.03 / +0.84 |
| W-00m | 25% | −0.18 (fails) | −0.77 (fails) | +1.07 / +0.47 |

### 5.3 What the table does and does not say

- **The MBL line binds before `ci_low` does at the corrected N.** W-85 at 50% has a Δ volatility of
  6.28 %/yr (point 5.11 / IR 0.814). The line needs an IR of 0.337 at N_eff 37 and 0.463 at N ≈ 371.
  That is a haircut of at most **6.06 %/yr** at the pinned gate and at most **4.46 %/yr** at the
  corrected count. The corrected line falls between the two measured over-captures: the arm passes it
  at 2.9 and fails it at 5.3.
- **Neither over-capture is a measurement in the sense the program requires.** B-5's is on 27 months
  with a tracking error of 8.95 %, so its standard error is about 6 %/yr. T-296's is on 31 months, on
  a volatility-scaled AQR series, and its verdict does not say whether the 1 % ER and the spread were
  already netted. The two are not on one basis.
- **A constant haircut is the wrong shape for 1985–1999.** The stack ER and spread in the arm are
  today's. Before 2000 an investor paid 2-and-20 or more plus much higher trading costs: a gap of the
  order of 4–6 %/yr (§2, M), which is the size of the W-85 break-even. The 41-year clearance leans on
  the years in which nobody could have bought the factor at a 1 % fee.
- **Read plainly:** the deep-window evidence stands or falls on a number between about 2 and 6.5 %/yr
  that has been measured twice, badly. Measuring it on 15 years of live funds would cut its standard
  error to about 2.2 %/yr (an assumed tracking error of 8.6 % over 15.4 years). That still spans both
  break-evens unless the result is extreme.

## 6. Windows, the MBL line and the power line

Required information ratio of the Δ series (arm minus benchmark; an *active* ratio, never the arm's own
Sharpe): `E[max_N]/√T`, with `E[max]` = 2.1594 at N_eff 37.08 (the pinned gate, +1) and 2.9627 at
372.28 (T-391's corrected count, built and reviewed, not merged, +1). The plain two-sided 95% line is
`1.96/√T`.

| window | set by | T (yr) | IR for `ci_low > 0` (50% power) | IR needed @ 37.08 | IR needed @ ~371 |
|---|---|---|---|---|---|
| Live composite, ≥ 3 funds (expected 2010-08 or 2010-09 → 2025-12) | fund inceptions (M) | 15.3–15.4 | 0.499 | 0.550 | **0.754** |
| Live composite, ≥ 1 fund (expected 2007-04 → 2025-12) | RYMFX (M) | 18.75 | 0.453 | 0.499 | 0.684 |
| SG Trend / SG CTA, if the owner allows registration | index start | 26.0 | 0.384 | 0.423 | 0.581 |
| BTOP50, if a ruling allows it | index start 1987 | 39.0 | 0.314 | 0.346 | 0.474 |
| AQR (B-5, already run) | file start 1985 | 41.0 | 0.306 | 0.337 | 0.463 |
| DBMF live (B-5, already run) | 2019-06 | 6.6 | 0.764 | 0.842 | 1.155 |
| RSST itself | 2023-10 | 2.25 | 1.307 | 1.440 | 1.975 |

**Power, before any data.** The plausible net premium, all from memory and to be replaced by the
measurement:
- Net trend indices: about T-bills + 3 %/yr since 2000 at 12–13 % volatility (Sharpe about 0.3); about
  T-bills + 1.5–2 %/yr since 2010; about zero over 2011–2019.
- Live mutual funds since 2010: about T-bills + 0.7–1.7 %/yr net, so about 2.0–3.2 %/yr gross of their
  own fees.
- Less the stack's hurdle at a 100% overlay (0.91 ER + 0.50 spread + about 0.4 variance + about 0.1
  correlation = about 1.9 %/yr) and the 1.0 %/yr survivorship haircut.
- **Expected Δ for the decision cell: about −1.0 to +0.3 %/yr, an IR of about −0.1 to +0.15.**

At a true IR of 0.15 on 15.4 years the chance of `ci_low > 0` is about **8 %**. The chance of clearing
the MBL line is about 6 % at N_eff 37 and under 1 % at N ≈ 371. The chance of a significant *loss* is
about the same few percent. **The likely outcome, at roughly 85–90 %, is a confidence interval of about
±4.5 %/yr around a point near zero.** On SG Trend's 26 years the chance of `ci_low > 0` is about 4 %
on a conservative fee reading and about 30 % if the index is restated to an ETF's fee.

Years of data needed for a 50 % chance of `ci_low > 0`: 96 at a true IR of 0.2, 43 at 0.3, 15 at 0.5.

## 7. What each earlier result tested (each is a different use from T-398's)

| task | what was tested | why it does not answer T-398 |
|---|---|---|
| **T-296** (refuted) | A synthetic RSST (SPY + vol-scaled AQR, excess of cash) **replacing the equity leg inside the long/flat gated 3-asset sleeve**, 2001–2025 monthly; gates on ΔSortino and Δwealth vs the plain sleeve and the 2× offense arm | The sleeve's gate read the combined price, so the trend leg masked the equity decline (2022: −7.5 % vs −5.2 %). Its own verdict says it does not test an un-gated buy-and-hold RSST. Its wealth gate was discarded for the +5.3 %/yr basis. |
| **T-253** (not clearly better) | DBMF and KMLM standalone, and as a 20% **satellite displacing** part of an 80% bond core, against the in-house trend sleeve; 2019-05+; decided on 2020 and 2022 crisis returns and barbell Sortino | Displacement, a bond core, a Sortino yardstick, 6 years. Not an overlay on 100% equity; not wealth vs equity. |
| **T-170 / T-171** (shelf #5) | 20% DBMF **displacing** 20% of the active equity book in a separate account; drawdown and Sharpe gates; the deep window through AQR with a scalar haircut (0.71 / 0.28) | A drawdown-defense claim. Haircut-fragile at the GFC. Not wealth vs equity; not stacked. |
| **T-311 / T-333** | The in-house long/flat trend **sleeve that times equity exposure** (to cash), 64 years | Substitution, not addition. It costs wealth (buy-and-hold $5.73M vs $1.96M) and its timing is worth −5.16 pp/yr net of cash in the modern era. Says nothing about a diversified long/short futures overlay held on top of a constant 100% equity. |
| **Shelf #4** (in-house 8-ETF sleeve) | A spot-ETF trend basket inside the equity book's capital | Refuted on the integrated path (T-128r). In-house, capital-partitioned. |
| **Shelf #7** (T-253's entry) | A bought managed-futures ETF as a narrow tail hedge | Waits on a sustained-bear detector that does not exist. |
| **T-316** (armed, 0 trials) | A forward shadow: 0.95 × sleeve + 0.05 × DBMF, un-gated; gates on crisis correlation ≤ +0.30 and Δwealth ≥ −3 % over 24 months | A 5% displacement of the *sleeve*, judged on independence. Not an overlay; not vs equity. |
| **B-5 arm (iv)** | **The overlay itself**: 100% equity + 50% / 25% trend, AQR (refute-only) and DBMF (6.6 yr, exploratory) | The only prior test of T-398's structure. AQR cannot open the door; DBMF is too short: +2.58 [−1.70, +7.04]. |
| Route research D5 / H4 | Priors: 25% (overlay), 35% (RSST forward) | "The 2010–19 CTA winter plus ~1.5% all-in overlay cost eats most of a 0.4-Sharpe sleeve's ~3% excess." |

## 8. Reproduce this census (read-only; no network)

```bash
# §3 spans and md5s
for f in data/research/substrate_multidecade/*.csv data/research/gold_gcf_t255.csv; do sed -n 2p "$f"; tail -1 "$f"; md5 -q "$f"; done
python -c "import json; m=json.load(open('data/research/b5/inputs/MANIFEST.json'))['files']; [print(k, v.get('first'), v.get('last'), v['md5']) for k, v in m.items()]"
# §1 first bars of the ETFs in the Stooq dump
for t in wtmf fmf cta dbmf kmlm rsst rssb rsbt ntsx ahlt tfpn mfut hfmf; do f=$(find data/raw/stooq/ -name "$t.us.txt"); echo "$t $(sed -n 2p "$f" | cut -d, -f3)"; done
# §5 break-even haircuts: read the on-disk curves (s*_ci − 50 bp; extrapolate with the end slope beyond 400 bp)
python -c "
import json
m=json.load(open('data/research/b5/run_A/results.json'))['monthly']
for wk in ('W-85','W-00m'):
    for wn in ('w50','w25'):
        c=m[wk][wn]['curve']; s=c['spreads_bp']; lo=c['ci_low_per_year']
        x=next((s[i]+5*lo[i]/(lo[i]-lo[i+1]) for i in range(80) if lo[i]>0>=lo[i+1]), None)
        x=x if x is not None else 400-lo[-1]/((lo[-1]-lo[-2])/5)
        print(wk, wn, round(100*lo[10],3), round((x-50)/100,3))
"
# §6 the MBL line
python -c "
from core.measurement.mbl_gate import expected_max_normal as e
import math
for T in (15.42,18.75,26,39,41,6.58,2.25): print(T, round(1.96/math.sqrt(T),3), round(e(37.08)/math.sqrt(T),3), round(e(372.28)/math.sqrt(T),3))
"
```
