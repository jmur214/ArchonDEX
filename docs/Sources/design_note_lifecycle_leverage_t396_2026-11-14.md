---
task_id: T-396
title: Lifecycle leverage in the accumulation frame, and the cheapest Roth-legal vehicle — a pre-run design note
date: 2026-11-14
author: regime-analyst lens (director-dispatched)
type: PRE-RUN DESIGN NOTE — arithmetic and reading only
status: COMPLETE as a note. No backtest run, no arm's wealth path computed. N_trials consumed 0.
branch: research/lifecycle-leverage-note-t396
---

# T-396 — lifecycle leverage for a contributing Roth saver: what is known before any run

> **SUPERSEDED IN PART 2026-11-24 (director; found by T-409's independent reconciliation).** The §2d table (+22 / +10 / −1 / −12 % at 0 / −1 / −2 / −3 pp), its 29–64 % "chance of ending below 1×" and "sd ≈ 35 %" rest on an expected-path recurrence (around lines 257, 280–288 and 585) that is exact for a lump sum but biased toward 1× for a stream of contributions. A path simulation gives about +0.15 log at −2 pp where the recurrence gives −0.013. Read `docs/Audit/real_money_home_verdict_t409_2026-11-24.md` for the corrected figures. The note's other conclusions (untimed leverage cannot pass the gate; no LEAPS path; the T-315 cost defect) stand; whether its LEAPS table used the same shortcut was not checked.


**The investor.** About $10k in a Roth IRA now, about $5k a year for decades, a ~40-year horizon, will
not sell in downturns, objective = maximum terminal wealth against buy-and-hold SPY.

## 0. Bottom line

1. **1× is about right once real costs and a −2 pp forward haircut are in.** With the two levered-ETF
   blends the repo has measured, the growth-optimal exposure is 2.0–2.2× at the realized 1968–2025
   premium, 1.3–1.5× at −2 pp and 1.0–1.1× at −3 pp, each ± 0.75 (one standard error from the sample
   alone). Half-Kelly is 1.0× at every haircut.
2. **Lifecycle leverage has never been run here.** The nearest thing is one 1968-start accumulation path
   with a calendar glide in T-315 (§1). The director's reading is right, with that one correction.
3. **T-315's static arms carry a phantom cost of about 1.29 %/yr** — a pandas period-shift charges the
   "annual" rebalance cost every day (§1.2). "1.25× significantly LOSES" is that defect, not the fund's
   expense ratio. The record needs a corrected re-run; "no arm CI-beats" almost certainly survives.
4. **The lifecycle gain is not earned on the small balance.** Under the rule "equity exposure = 100 % of
   lifetime savings, capped at 2×", the cap binds for 12–15 years and leverage is still 1.3–1.5× at year
   20 on a $180–290k balance. Years 0–4 contribute about a tenth of the expected gain (§2d).
5. **Dollars.** Expected-path terminal wealth vs 1×, real dollars at year 40, SSO+SPY blend:
   **+$250k (+22 %)** at the realized premium, **+$86k (+10 %)** at −1 pp, **−$8k (−1 %)** at −2 pp,
   **−$59k (−12 %)** at −3 pp. One cohort's outcome has a standard deviation of about 35 % around that:
   from the realized premium down to −2 pp, a 30–50 % chance of ending below 1× and a 5 % chance of
   ending below 0.56–0.67× of it.
6. **LEAPS are not the cheap vehicle at this account size.** One SPY or XSP contract controls about
   $71k; a deep-in-the-money contract fits a 2× target only above roughly $36k. On stated assumptions
   the all-in cost of a LEAPS (financing + the embedded put + spread on the roll) is 0.8–2.9 %/yr per
   borrowed dollar, central 1.8 %, against a measured 0.96 % for a UPRO+SPY blend and 1.37 % for
   SSO+SPY. Nothing on disk can price a LEAPS historically.
7. **No backtest of this can pass the program's gate.** The best achievable t-statistic for any
   untimed leverage on 1926–2025 is about 2.6–2.8 (free financing, infinitesimal leverage); the deflated
   bar at N_eff ≈ 371 is 2.96. Realistic arms sit at 0.7–2.0. This is an expected-utility decision
   about how much equity-premium risk to hold, not a discoverable edge.

**Recommendation (§5): do nothing on leverage; correct T-315; offer the owner an optional, descriptive
cohort study that is pre-declared unable to pass a gate.**

---

## 1. What the repo has already tested

### 1.1 The inventory

| Task | Frame | Vehicle | Window | Decision rule | What it answered | Where |
|---|---|---|---|---|---|---|
| T-282 | lump sum $10k | SSO synthetic inside a ⅓-equity sleeve | 2000-10 → 2025-12 | trend-gated, e ∈ {0, ⅔, 4/3, 2} | arm − SPY Δwealth CI [−25.80, +4.93]: no | `docs/Audit/trend_gated_leverage_t282_2026_07_06.md:17-38, 65, 84` |
| T-284 | lump sum | SPY + SSO-synthetic blend, 100 % equity base | 2000-10 → 2025-12 | trend-gated | [−12.38, +30.81]: straddles | `docs/Audit/fullequity_gated_leverage_t284_2026_07_06.md:18-24, 62, 75` |
| T-283 | **$7k/yr stream** | unlevered configs | 2000–2026, five starts 2000–2012 | static allocations | buy-and-hold wins the race; DCA widens its edge | `docs/Audit/accumulation_model_verdict_t283_2026_07_06.md:23-38` (dollars superseded, `:10-14`) |
| T-283b / c | **$7k/yr stream** | T-282/T-284 gated curves; naked 2× as a context row | 2000–2026 | gated 2×; one static 2× | gated 2× ×1.20 vs buy-hold; naked 2× $1.96M vs $929k with a −$613k worst drawdown, no CI | `docs/Audit/accumulation_levered_t283b_2026_07_06.md:25-37`; `docs/Audit/accumulation_t284_reconcile_t283c_2026_07_06.md:23-35` |
| T-299 | $7k/yr stream | gated arm | 2000–2026 | where new money goes when the gate is off | sub-1 % effect; always-invest adopted | `docs/State/TASK_LEDGER.md:209` |
| T-294 / T-294b | lump sum | SSO vs NTSX/RSSB vs futures | 2000–2026 | gated | vehicle leak is daily-reset decay; futures die after tax | `docs/State/TASK_LEDGER.md:198, 200` |
| T-312 | lump sum | SPY + SSO-synthetic blend | 1968+, 1962+, 1926+ | trend-gated, damped | [−1486, +1438] on 1968+: straddles | `docs/Audit/deep_reverify_offense_t312_2026_07_27.md:91-93` |
| T-315 | lump sum, **plus one $7k/yr path from 1968** | one synthetic daily-reset fund charging 0.89 % on the whole balance at every L | 1968+, 1962+, 1926+ | static {1.25 … 2.0}×; a 2×→1× glide over the **final 12 calendar years** | no arm CI-beats; 1.25× "loses"; haircut table; 1929 dollar test | `docs/Audit/static_leverage_t315_2026_07_27.md:56-63, 111-119, 135-139, 172-178`; `scripts/offense_campaign_t312_t315.py:26-54, 195-208` |
| B-5 / T-382 | lump sum | levered stock/bond stacks (RSSB-class) | 1968–2025 | static stack | +0.21 %/yr, CI [−1.91, +2.30]; measured swap spreads SSO 57 [18, 96] bp, UPRO 56 [35, 81] bp | `docs/Audit/b5_levered_diversified_verdict_2026-11-11.md:15-25, 44-46, 175-177` |

Literature and named-but-not-run items:

- **Ayres–Nalebuff was reviewed, not run.** `docs/Sources/External_Prompt_Runs/2026-07-08_research-agent-v2.md:192-196`
  summarises the argument and its critiques. The disposition at `:337` was "ADOPTED as framing + a
  future advisor row — glide-path arm goes to B's accumulation model when the offense config graduates
  paper". The offense config was refuted at depth (T-312), so that arm never ran.
- **LEAPS as a financing vehicle: named, not run.** `docs/Audit/static_leverage_t315_2026_07_27.md:195-201`
  names "LEAPS-embedded leverage at the $65k+ tier" as a follow-up needing its own pre-registration.
  The only LEAPS code in the repo is a catalyst-signal edge priced with synthetic Black-Scholes
  (`engines/engine_a_alpha/edges/leaps_catalyst_edge.py`; `docs/State/health_check.md:972-974`), which
  is unrelated to financing.

**Was lifecycle leverage in the accumulation frame ever run? No.** Ayres–Nalebuff set exposure as a
fraction of *lifetime* savings, so leverage falls as the balance grows relative to the contributions
still to come. Nothing here does that. The closest run is T-315's accumulation race
(`static_leverage_t315_2026_07_27.md:175-178`): one cohort starting in 1968, a glide keyed to the
calendar (2× for 46 years, then down to 1× over the last 12), the full realized premium, no confidence
interval, no cohort variation, no haircut. It reported the glide at $86.5M against $35.0M for 1× and
$70.1M for static 2×. Those static-arm numbers are affected by the defect in §1.2.

### 1.2 A defect in T-315, found while reading (not re-run)

`scripts/offense_campaign_t312_t315.py:37-38`:

```python
yr = r.index.to_period("Y")
cost[yr != yr.shift(1)] = SLIP_EQ * rebal_per_yr    # ~nothing
```

`PeriodIndex.shift(1)` moves every period forward one year; it does not shift positions. The mask is
therefore true on **every** row, and every static arm above 1× pays 0.51 bp **per day**, about
1.285 %/yr, instead of 0.51 bp once a year.

Three checks, none of them a re-run:

- On the installed pandas (3.0.1), the same two lines on eight business days spanning a year-end give a
  mask that is true on 8 of 8 rows.
- The published 1968+ table (`static_leverage_t315_2026_07_27.md:113-118`) decomposes exactly. Fitting
  Δlog growth vs the bar as `(L−1)·a − c − ½(L²−1)·v` over the five static arms gives a = 6.69 %,
  **c = 2.00 %/yr**, v = 2.87 % (σ 16.9 %), with a largest residual of 0.2 bp. The specified fixed cost
  is 0.71 %/yr (SSO's 0.89 % less two 0.09 % add-backs). The unexplained 1.29 %/yr equals 0.51 bp × 252.
- The glide arm (`:54`) and the gated arm (`:74-76`) charge cost on `diff()` of the exposure and are not
  affected. The bar is not affected.

What it does to the record, by arithmetic only (each static arm's terminal value × about 2.11 over
14,670 bars; confidence intervals need the re-run):

| haircut | bar | 1.25× | 1.35× | 1.5× | 1.75× | 2.0× |
|---|---|---|---|---|---|---|
| none — published, × bar | 1.00 | 0.52 | 0.61 | 0.77 | 1.04 | 1.25 |
| none — restated, × bar | 1.00 | **1.09** | 1.30 | 1.63 | 2.19 | 2.65 |
| −2 % — published | 1.00 | 0.39 | 0.41 | 0.43 | 0.43 | 0.39 |
| −2 % — restated | 1.00 | 0.82 | 0.86 | 0.91 | 0.91 | 0.83 |
| −3 % — published | 1.00 | 0.33 | 0.33 | 0.32 | 0.28 | 0.22 |
| −3 % — restated | 1.00 | 0.71 | 0.71 | 0.68 | 0.59 | 0.46 |

- **"1.25× significantly LOSES, [−371, −7]" does not survive.** Restated, 1.25× is about +0.16 %/yr
  against the bar. With a sampling error near 0.55 %/yr it straddles zero.
- **"No static arm CI-beats" almost certainly survives.** Restated 2× is about +1.7 %/yr with a standard
  error near 2.2 %/yr (t ≈ 0.76).
- **The haircut verdict survives in direction, not in size.** At −2 % every arm still trails the bar,
  by 9–18 % rather than by more than half; at −3 % the ordering still inverts.
- **The accumulation race's "glide wins" is probably the defect.** The glide escaped a cost the static
  arms paid for 58 years.
- **The cash-rate regime split (`:162-165`) uses the same static arms.** "Static leverage loses in the
  high-rate era" (1.5×: 8.55 % vs 9.97 %) restates to roughly a tie.

Two further issues in the same document, both leaning against leverage:

- **The fund model overcharges low leverage.** `lev_daily` (`:26-29`) takes 0.89 % off the whole balance
  at any L > 1. A holder who wants 1.25× would hold 75 % SPY and 25 % SSO and pay 0.89 % on a quarter of
  the balance; the gated arm in the same script does exactly that (`:70-73`). The overcharge is
  (2 − L) × 0.80 %/yr: 0.60 %/yr at 1.25×, zero at 2×. The "non-monotone break-even" headline
  (`static_leverage_t315_2026_07_27.md:32-36`) is this modelling choice.
- **Geometric and arithmetic premia are mixed.** The break-even formula (`:22-23`) takes an arithmetic
  mean; it is compared with a difference of CAGRs (`:39-49`), and Kelly is computed as that difference
  over σ² (`:82-84, 143`). On 1968–2025 the CAGR difference is 6.12 %; the arithmetic excess mean is
  7.10 %. Kelly is 2.54, not 2.20.

I changed nothing in `scripts/` and wrote no `health_check.md` entry; both are the director's call.
A positional mask (`years = r.index.year; first = np.r_[True, years[1:] != years[:-1]]`) is the
one-line repair.

---

## 2. The arithmetic, pre-run

### 2.0 Inputs

Realized moments of the T-306 equity and cash legs (`data/research/substrate_multidecade/`;
`equity_tr_daily.csv` md5 `c2030019…`, `cash_daily.csv` md5 `28a1446d…`; cash present on every equity
bar). Only the 1× benchmark's moments were computed.

| window | equity CAGR | cash CAGR | CAGR gap | **arithmetic excess μ** | σ (daily, annualised) | σ² | SE(μ), Newey-West 252 | t(μ) |
|---|---|---|---|---|---|---|---|---|
| 1926-07 → 2025-12 | 9.73 % | 3.06 % | 6.68 % | 7.75 % | 17.14 % | 2.94 % | 1.83 pp | 4.2 |
| 1962 → 2025 | 10.45 % | 4.38 % | 6.06 % | 6.97 % | 16.23 % | 2.63 % | 1.97 pp | 3.5 |
| **1968 → 2025 (primary)** | 10.58 % | 4.46 % | 6.12 % | **7.10 %** | **16.73 %** | **2.80 %** | **2.11 pp** | 3.4 |
| 1990 → 2025 | 10.75 % | 2.71 % | 8.03 % | 9.19 % | 18.19 % | 3.31 % | 2.51 pp | 3.7 |
| 2000 → 2025 | 8.00 % | 1.91 % | 6.09 % | 7.69 % | 19.39 % | 3.76 % | 3.20 pp | 2.4 |

- Annualisation is 252 bars. Before 1952 the market traded six days a week, so the 1926 window holds
  103.8 "252-bar years" in 99.5 calendar years and its annual figures read about 4 % low.
- The cash leg is quantised to 1 bp/day (`docs/State/health_check.md:127-131`). Multi-decade means are
  fine; single-year financing costs are not.
- Before 1993 the equity leg is the broad market, not the S&P 500 (`validation_report.md`).

**Vehicle costs, per borrowed dollar per year, over the bill rate.**

| vehicle | cost c | built from | on disk? |
|---|---|---|---|
| UPRO + SPY blend | **0.96 %** | (0.90 % − 0.09 %) / 2 fee per borrowed dollar + 56 bp spread | ER `scripts/b5_levered_diversified.py:92-93`; spread 56 [35, 81] bp, B-5 §3 |
| SSO + SPY blend | **1.37 %** | (0.89 % − 0.09 %) fee + 57 bp spread | same; spread 57 [18, 96] bp |
| LEAPS, optimistic | 0.80 % | financing +0.25, embedded put 0.25, trading 0.30 | **assumption** |
| LEAPS, central | 1.80 % | financing +0.50, embedded put 0.60, trading 0.70 | **assumption** |
| LEAPS, adverse | 2.90 % | financing +0.75, embedded put 1.15, trading 1.00 | **assumption** |
| frictionless | 0 | borrow at the bill rate | reference only |

How the LEAPS rows were built — every figure here is an assumption; no option price is on disk:

- **Parity.** A deep-in-the-money call costs the stock, less the present value of the strike, less the
  dividends, **plus a put at the strike**. The holder therefore pays three things: an implied interest
  rate on the strike, the put, and the bid-ask each time the position is rolled. "Implied financing
  near the risk-free rate" describes only the first.
- **Financing.** Assumed +0.25 to +0.75 % over bills at the ask.
- **The put.** Black-Scholes at S = 100, r = 3.6 %, q = 1.2 %, strike at half of spot (about 2×), two
  years: 0.17 %/yr of the borrowed amount at 25 % implied volatility, 0.49 % at 30 %, 1.03 % at 35 %,
  1.78 % at 40 %. A strike at 60 % of spot (2.4×) costs 0.56–3.1 %/yr; at 33 % of spot (1.5×) it is under
  0.4 %. Deep strikes trade at a large skew premium; I do not know today's.
- **Trading.** A round trip of 0.3–1.0 % of the premium once a year. At 2× the premium equals the
  borrowed amount, so this is 0.3–1.0 %/yr per borrowed dollar. At 1.25× done with a single
  very-deep-strike contract the premium is four times the borrowed amount and the same spread costs
  1.2–4 %/yr per borrowed dollar. Low leverage would have to be SPY shares plus a 2× LEAPS on part of
  the account.
- **Roll.** One roll a year (buy two years out, roll with a year left) is assumed.

A LEAPS is also a different instrument, not just a different price. It does not reset daily: leverage
rises as the market falls, and the position expires. §3 covers what that means for a holder who will
not sell.

### 2a. Expected log-growth gain on the current balance

`Δg(L) = (L − 1)·(μ − c) − ½·(L² − 1)·σ²`, with μ the arithmetic excess return, σ = 16.73 %. The
break-even is `μ* = c + ½·(L + 1)·σ²`. Entries are %/yr of the current balance, against 1×.

| vehicle (c) | break-even μ at 1.25 / 1.5 / 2.0× | μ 7.10 % (realized) | μ 6.10 % (−1 pp) | μ 5.10 % (−2 pp) | μ 4.10 % (−3 pp) |
|---|---|---|---|---|---|
| UPRO + SPY (0.96 %) | 4.11 / 4.46 / 5.16 % | +0.75 / +1.32 / +1.94 | +0.50 / +0.82 / +0.94 | +0.25 / +0.32 / −0.06 | −0.00 / −0.18 / −1.06 |
| SSO + SPY (1.37 %) | 4.51 / 4.86 / 5.56 % | +0.65 / +1.12 / +1.54 | +0.40 / +0.62 / +0.54 | +0.15 / +0.12 / −0.46 | −0.10 / −0.38 / −1.46 |
| LEAPS optimistic (0.80 %) | 3.95 / 4.30 / 5.00 % | +0.79 / +1.40 / +2.10 | +0.54 / +0.90 / +1.10 | +0.29 / +0.40 / +0.10 | +0.04 / −0.10 / −0.90 |
| LEAPS central (1.80 %) | 4.95 / 5.30 / 6.00 % | +0.54 / +0.90 / +1.10 | +0.29 / +0.40 / +0.10 | +0.04 / −0.10 / −0.90 | −0.21 / −0.60 / −1.90 |
| LEAPS adverse (2.90 %) | 6.05 / 6.40 / 7.10 % | +0.26 / +0.35 / +0.00 | +0.01 / −0.15 / −1.00 | −0.24 / −0.65 / −2.00 | −0.49 / −1.15 / −3.00 |
| frictionless (0) | 3.15 / 3.50 / 4.20 % | +0.99 / +1.80 / +2.90 | +0.74 / +1.30 / +1.90 | +0.49 / +0.80 / +0.90 | +0.24 / +0.30 / −0.10 |

(each cell: L = 1.25 / 1.5 / 2.0)

- **The vehicle matters less than the premium.** The whole spread between UPRO and central LEAPS is
  0.84 pp per borrowed dollar; one percentage point of forward premium moves every cell by (L − 1) pp.
- **At 2× the variance cost is the large term**, 4.2 %/yr of the 5.6 % break-even on the SSO blend.
  A cheaper vehicle cannot remove it.
- **Chance the true gain is negative**, treating μ as known only to its sampling error (2.11 pp), SSO
  blend: at 1.5×, 14 % / 28 % / 46 % / 64 % across the four columns; at 2×, 23 % / 40 % / 59 % / 76 %.
- **In dollars on today's $10k**, 2× on the SSO blend is worth +$154 in the first year at the realized
  premium and −$46 at −2 pp.

### 2b. Kelly and half-Kelly

`L* = (μ − c)/σ²` when that exceeds 1, else 1. One standard error of μ moves L* by 2.11 / 2.80 = **0.75**.

| vehicle | realized | −1 pp | −2 pp | −3 pp |
|---|---|---|---|---|
| frictionless | 2.54 | 2.18 | 1.82 | 1.46 |
| UPRO + SPY | 2.19 | 1.84 | 1.48 | 1.12 |
| SSO + SPY | 2.05 | 1.69 | 1.33 | 1.00 |
| LEAPS central | 1.89 | 1.54 | 1.18 | 1.00 |
| half-Kelly, any real vehicle | 1.0–1.1 | 1.00 | 1.00 | 1.00 |

- **A log-wealth maximiser uses the mean of what they believe about μ.** Parameter uncertainty does not
  shrink the Kelly fraction by itself; it widens the band (± 0.75 from the sample alone) and makes the
  haircut the whole question.
- **The growth curve is flat near its top.** Holding 1× when L* is 1.33 gives up 0.15 %/yr; when L* is
  1.69, 0.67 %/yr; when L* is 2.05, 1.54 %/yr.
- **Half-Kelly (risk aversion 2) says 1×** with any real vehicle at any haircut, and below 1× without
  costs at −2 pp (0.91) and −3 pp (0.73).
- Fat tails pull L* down a little further: T-315's own arms fit an effective σ of 16.9 % against 16.7 %.

### 2c. The lifecycle frame

Rule: equity exposure = λ × (balance + present value of contributions still to come), capped at 2× the
balance and floored at 1×. Real dollars; $10k now, $5k at each year-end for 40 years; contributions
discounted at a real bill rate of 1.0 % (**assumption**), which makes them worth $164k today ($136k at
2 %, $200k at 0 %). The balance follows its expected log-growth path on the SSO blend.

| λ | haircut | cap stops binding | L at year 0 / 5 / 10 / 12 / 15 / 20 / 30 | balance at year 10 / 20 |
|---|---|---|---|---|
| 1.0 | none | **year 12** | 2.00 / 2.00 / 2.00 / 1.97 / 1.62 / 1.31 / 1.07 | $97k / $289k |
| 1.0 | −2 pp | **year 15** | 2.00 / 2.00 / 2.00 / 2.00 / 1.91 / 1.50 / 1.13 | $76k / $181k |
| 0.75 | none | year 9 | 2.00 / 2.00 / 1.74 / 1.48 / 1.23 / 1.00 / 1.00 | $97k / $274k |
| 0.75 | −2 pp | year 11 | 2.00 / 2.00 / 2.00 / 1.73 / 1.42 / 1.12 / 1.00 | $76k / $185k |
| 1.5 | none | year 20 | 2.00 throughout to year 19; 1.60 at year 30 | $97k / $296k |

- **On day one the target is 17× the balance** ($174k of lifetime savings against $10k). The 2× cap is
  what the investor actually holds for more than a decade.
- **With λ = 1 the investor never returns to exactly 1×.** Leverage decays toward it.
- **A lower premium keeps the cap binding longer**, because the balance grows more slowly against the
  same contributions.
- **A high λ turns the rule into static leverage**, which is T-315's question: λ = 2 is 2× forever,
  and λ = 1.5 already holds the cap for 20–24 years.
- **Lifecycle leverage relative to 1× forever is added risk, not shifted risk.** Ayres–Nalebuff's
  lower-dispersion result compares against strategies with the same lifetime exposure, pairing early
  leverage with less than 100 % equity late. This investor's baseline is already 100 % late.

### 2d. The dollar size of the effect

Expected-path terminal wealth at year 40, real dollars, λ = 1, cap 2×. The per-cohort mean and standard
deviation of Δ log terminal wealth use independent annual returns with σ = 16.73 %; the chance of
ending below 1× and the 5–95 % range use a normal approximation.

| vehicle | haircut | 1× | lifecycle | Δ | as extra contributions | cohort Δlog mean / sd | P(below 1×) | 5 %–95 % of lifecycle ÷ 1× |
|---|---|---|---|---|---|---|---|---|
| SSO + SPY | none | $1,126k | $1,376k | **+$250k (+22 %)** | ≈ +$1,280/yr | +20.7 % / 36.7 % | 29 % | 0.67 – 2.25 |
| SSO + SPY | −1 pp | $846k | $933k | **+$86k (+10 %)** | ≈ +$580/yr | +9.9 % / 36.0 % | 39 % | 0.61 – 1.99 |
| SSO + SPY | −2 pp | $643k | $635k | **−$8k (−1 %)** | ≈ −$70/yr | −1.2 % / 34.9 % | 51 % | 0.56 – 1.75 |
| SSO + SPY | −3 pp | $494k | $435k | **−$59k (−12 %)** | ≈ −$660/yr | −12.2 % / 33.5 % | 64 % | 0.51 – 1.54 |
| UPRO + SPY | none / −1 / −2 / −3 | as above | $1,433k / $973k / $664k / $456k | +$307k / +$127k / +$21k / −$38k | | sd ≈ 35 % | 25 / 35 / 46 / 59 % | |
| LEAPS central | none / −1 / −2 / −3 | as above | $1,317k / $890k / $604k / $413k | +$191k / +$44k / −$39k / −$81k | | sd ≈ 35 % | | |

- **Each percentage point of forward premium moves the lifecycle gain by about 11 % of terminal
  wealth.** With μ known only to ± 2.11 pp, the honest standard deviation of the outcome is about 43 %.
- **A 30-year horizon** gives +$92k (+17 %), +$34k, −$4k, −$28k on the SSO blend.

**Where the gain and the risk sit** (SSO blend, realized premium; contribution to the cohort's Δlog):

| years | leverage | balance | borrowed-equivalent | expected gain | sd |
|---|---|---|---|---|---|
| 0–4 | 2.00 | $10k → $37k | $10k – $37k | **+2.1 %** | 10.8 % |
| 5–9 | 2.00 | $45k → $85k | $45k – $85k | +4.0 % | 19.8 % |
| 10–14 | 2.00 → 1.72 | $97k → $158k | $97k – $121k | +5.1 % | 23.3 % |
| 15–24 | 1.62 → 1.18 | $176k → $411k | $74k – $110k | +7.0 % | 16.6 % |
| 25–39 | 1.16 → 1.00 | $446k → $1,282k | $5k – $69k | +2.4 % | 4.6 % |

- **The first five years are nearly free in both directions.** Cumulative expected extra by year 5:
  +$1,750 at the realized premium, +$590 at −1 pp, −$500 at −2 pp.
- **Sixteen of the twenty-one points come from years 5–24**, when the levered amount is $45–120k.
  That is where the variance is too.
- **Leverage confined to the small balance is small:**

| variant (SSO blend) | none | −1 pp | −2 pp | −3 pp | 5 %–95 % range at realized |
|---|---|---|---|---|---|
| 2× for the first 5 years, then 1× | +$22k (+1.9 %) | +$5k | −$3k | −$6k | 0.87 – 1.20 |
| 2× for the first 10 years, then 1× | +$66k (+5.9 %) | +$15k | −$9k | −$18k | 0.74 – 1.51 |
| 1.5× for the first 10 years, then 1× | +$47k (+4.2 %) | +$18k | +$2k | −$5k | 0.88 – 1.24 |
| lifecycle, cap 1.5× | +$211k (+18.7 %) | +$90k | +$17k | −$24k | 0.81 – 1.76 |
| static 1.25× for 40 years | +$236k (+21.0 %) | +$100k | +$26k | −$13k | 0.86 – 1.70 |
| static 2× for 40 years | +$656k (+58 %) | +$139k | −$75k | −$150k | 0.40 – 6.44 |

  A flat 1.25× for forty years has about the same expected gain as the capped-2× lifecycle rule
  (+19.2 % against +20.7 % in log terms) with about half its dispersion against the 1× holder (20.7 %
  against 36.7 %). Total dispersion of log terminal wealth is 81 % for 1×, 104 % for flat 1.25× and
  111 % for the lifecycle rule. In this arithmetic the lifecycle shape does not buy more per unit of
  risk than a small constant amount of leverage: with real financing costs and the variance penalty,
  the second unit of leverage earns much less than the first quarter-unit.

**The bad tail.** One crash replaces one year's growth; every other year sits on the expected path, and
the rule re-levers afterwards. Crash sizes for a daily-reset holder are taken from the record: 2008-scale
1× −56.6 %, 2× −84.8 % (`fullequity_gated_leverage_t284_2026_07_06.md:85`, interpolated for other L);
1929-scale 1× −84.1 %, 1.5× −95.0 %, 2× −98.5 % (`static_leverage_t315_2026_07_27.md:147-154`).
Terminal figures compare with a 1× holder who lived through the same crash.

| crash | year | L then | balance before (lifecycle, realized premium) | lost in the crash: 1× vs lifecycle (realized premium) | terminal vs 1×, realized premium | terminal vs 1×, −2 pp |
|---|---|---|---|---|---|---|
| 2008-scale | 1 | 2.00 | $16k | $9k vs $13k | +14 % | −6 % |
| 2008-scale | 3 | 2.00 | $29k | $16k vs $25k | +9 % | −9 % |
| 2008-scale | 8 | 2.00 | $74k | $39k vs $62k | −4 % (−$35k) | −17 % (−$80k) |
| 2008-scale | 12 | 1.97 | $125k | $63k vs $105k | **−13 % (−$93k)** | **−23 % (−$101k)** |
| 2008-scale | 20 | 1.31 | $289k | $137k vs $197k | +1 % | −23 % (−$83k) |
| 1929-scale | 3 | 2.00 | $29k | $24k vs $29k | +13 % | −5 % |
| 1929-scale | 12 | 1.97 | $125k | $94k vs $123k | −7 % (−$34k) | −15 % (−$52k) |
| 1929-scale | 20 | 1.31 | $289k | $203k vs $267k | −8 % (−$27k) | −22 % (−$52k) |

- **In the first three years the extra loss is under two years of contributions** ($4–9k).
- **The expensive crash is the one in years 8–20.** It costs $35–100k of real terminal wealth against
  1×, and the −2 pp column shows the leverage does not earn it back.
- **A 1929-scale crash at 2× leaves 1.5 % of the balance.** Because 1× also loses 84 %, the relative
  damage is smaller than in a 2008-scale crash; the absolute damage is nearly total.
- These figures compress a multi-year decline into one year and assume the fund behaves as the
  synthetic does. They are sizing, not a forecast.

---

## 3. Feasibility in a $10k Roth

**Contract sizes against the account.** SPY's last cached close is $710.14 (2026-04-17,
`data/processed/SPY_1d.csv`).

| instrument | notional per contract | vs a $10k account | note |
|---|---|---|---|
| SPY option | about $71,000 | 7.1× | American, pays no dividend to the call holder |
| XSP (mini-SPX) option | about $71,000 | 7.1× | one tenth of SPX; same size as SPY — **from memory, not on disk** |
| SPX option | about $710,000 | 71× | |
| Micro E-mini future | about $36,000 | 3.6× | `docs/Audit/taxable_futures_vehicle_t294b_2026_07_08.md:60`; ruled out by the wrapper facts |
| a low-priced S&P 500 ETF with listed options | about $8,000 if the share is near $80 | 0.8× | **from memory, unverified** — see below |

- **One SPY or XSP contract plus SPY shares** gives the account a levered amount equal to the strike
  times 100. Holding L or less needs a balance of at least notional ÷ L: **$35,500 for 2×, $47,300 for
  1.5×, $56,800 for 1.25×.** That matches T-315's "$65k+ tier" and is four to seven years away on the
  expected path.
- **The only SPY call a $10k account can buy** has a premium under $10k, which is a strike about 13 %
  below spot. That is roughly 5–7× exposure that expires worthless on a modest decline. It is not
  lifecycle leverage.
- **A low-priced S&P 500 ETF is the only way to size LEAPS at $10k.** State Street's low-cost S&P fund
  (ticker SPLG; I believe renamed in late 2025) trades near one eighth of SPY. I do not know whether it
  lists expiries two years out, how deep its strikes go, or what its quoted spreads are. None of that
  is on disk; it must be read from a live chain before anything is planned on it.

**Approval and broker.**

- **The broker is undecided.** `docs/State/CURRENT_STATE.md:184`: "broker undecided — 'Alpaca IRA' is
  the 2026-09-30 review's assumption"; "options conservatively Level 2 (covered calls / cash-secured
  puts / long options)".
- **The repo's record on Alpaca IRAs is not consistent with itself.**
  `docs/Sources/alpha_frontier_review_2026_09_30/02_route_research.md:310-311` says Level 2 includes
  long calls; `:277` says "verified only for covered calls / CSPs". Neither has a first-artifact check
  behind it.
- **Unknown from the docs:** whether an Alpaca IRA can hold two-year expiries, index options (XSP), or
  options on a thinly traded ETF. Alpaca's options history starts 2024-02 (`:315`).
- **No options order path exists in the code.** A search of `paper_trader/`, `live_trader/`, `brokers/`,
  `engines/` and `core/` for an options contract or order call found none. Building one touches the live
  path and is propose-first.
- A long call needs no margin. Buying one is the only options structure this needs.

**Liquidity assumptions** (not on disk): deep-in-the-money SPY LEAPS are quoted wide, on the order of
0.5–1.5 % of the premium, with thin open interest at deep strikes. Limit orders near the midpoint are
the working assumption behind the 0.3–1.0 % round trip in §2.0.

**Operational burden.** One roll a year, by hand or by new code: choose the expiry and strike, sell the
old contract and buy the new one with limit orders, and re-size against the balance and the contribution.
A levered-ETF blend needs one rebalance a year or a band and nothing else; it works in any Roth at any
size with no options approval.

**Failure modes, and what they mean for an investor who will not sell.**

- **A LEAPS expires.** If the index is below the strike at expiry the position is worth zero and the
  exposure is gone. The holder cannot wait for the recovery; the instrument sells for them, at the
  bottom. On T-306, the 1× index was down 50 % or more over two years on 1.5 % of days since 1926 and
  on none since 1946 (worst −49.5 %, March 2009); down 40 % or more on 2.6 % and 0.5 %.
- **A LEAPS does not de-lever on the way down.** A daily-reset fund sells as it falls and keeps a
  remnant (2008: about 15 % of the balance at 2×). A call struck at half of spot holds full share
  exposure down to the strike: at −45 % it keeps about 10 % of its premium, at −50 % nothing but
  time value. In a deep crash it is as bad as the fund or worse.
- **It is better than the fund in one case:** a sharp fall and recovery inside the option's life, where
  the fund's daily reset loses ground and the option does not.
- **After a wipe-out, new exposure comes only from new contributions** — $5k a year against a lost
  balance of $50–150k in the years that matter.
- **Rolling in a crash is the worst time to trade it.** Implied volatility and spreads are at their
  widest when the roll is most needed.
- **A levered ETF's failure mode is different:** it cannot be called or expire, but a long decline with
  high volatility grinds it down (T-294 measured +1.97 %/yr of decay on the levered leg), and a fund
  can be closed or restructured by its sponsor.

---

## 4. The statistical question

**The gate.** Block-bootstrap ci_low of Δ log terminal wealth against 1× above zero; deflated for the
number of trials. With `E[max_N]` in the Bailey–López de Prado form, the information ratio of the daily
difference series must reach `E[max_N] / √T`:

| N_eff | source | E[max] | IR needed, 58 yr | IR needed, 99.5 yr |
|---|---|---|---|---|
| 1 (undeflated, t > 1.96) | — | 1.96 | 0.258 | 0.196 |
| 37.08 | the merged gate | 2.16 | 0.284 | 0.216 |
| 267 | Option B | 2.86 | 0.376 | 0.287 |
| **371.28** | T-391's R3 rule, reviewed, not merged | **2.96** | **0.389** | **0.297** |

The 37 and 267 rows reproduce B-5's own line (0.284 and 0.375,
`b5_levered_diversified_verdict_2026-11-11.md:193-195`).

**The expected t-statistic of the leverage premium.** For a static L against 1×, the yearly difference
has mean `(L−1)·[(μ − c) − ½(L+1)σ²]` and standard deviation `(L−1)·σ`, so
`IR = [(μ − c) − ½(L+1)σ²] / σ` and `t = IR·√T`.

| window | vehicle | L → 1 | 1.25× | 1.5× | 2.0× |
|---|---|---|---|---|---|
| 1968–2025 | frictionless | 1.95 | 1.80 | 1.64 | 1.32 |
| 1968–2025 | UPRO + SPY | 1.51 | 1.36 | 1.20 | 0.88 |
| 1968–2025 | SSO + SPY | 1.33 | 1.18 | 1.02 | 0.70 |
| 1968–2025 | LEAPS central | 1.13 | 0.98 | 0.82 | 0.50 |
| 1926–2025 | frictionless | 2.79 | 2.59 | 2.37 | 1.95 |
| 1926–2025 | UPRO + SPY | 2.23 | 2.03 | 1.81 | 1.39 |
| 1926–2025 | SSO + SPY | 2.00 | 1.79 | 1.58 | 1.15 |

- **Cross-check.** T-315's realized 2× difference, with the phantom cost removed, is about +1.68 %/yr
  on a standard error near 2.2 %/yr: t ≈ 0.76, against 0.70 here.
- **The ceiling is the equity premium's own t-statistic less the Kelly penalty.** The most any untimed
  leverage can show is `t(μ − σ²)`: 2.04 on 1968–2025 and 2.63 on 1926–2025 with autocorrelation-robust
  errors. Both are below 2.96. **It cannot pass the deflated gate by construction**, even with free
  financing and infinitesimal leverage.
- **Undeflated, a low-leverage cheap-vehicle arm on the full 1926 window sits at the line** (UPRO blend
  1.25×: 2.0, about 1.9 with robust errors). A corrected T-315 could show that. It would say that the
  US premium exceeded σ² plus costs over the last century. That is the known fact that equities paid;
  it is not evidence about the next forty years, and a levered ETF did not exist for 80 of those years.
- **With a haircut it is gone.** SSO blend on 1968–2025: 1.25× t = 0.72 / 0.27 / −0.19 at −1 / −2 / −3 pp.
- **Years of data needed** at the 1968+ moments: SSO blend 2× needs 456 years for t = 1.96 and 1,041
  for 2.96; SSO 1.25× needs 161 and 367; UPRO 1.25× needs 120 and 275.
- **The lifecycle rule in the cohort frame is weaker still.** One 40-year cohort has an expected t of
  0.56 (SSO) to 0.68 (UPRO) at the realized premium. A century holds about two and a half
  non-overlapping 40-year cohorts, so the whole history yields roughly 0.9–1.1. Overlapping start years
  add rows to a table, not independent evidence.

**What kind of decision this is.** Leverage on the index is more of the same risk at a known price. Its
payoff is the equity premium, which is real, large, and measured to ± 2 pp after a century. Whether to
hold 1×, 1.5× or 2× of it is a choice about risk preference and belief in the forward premium. A
backtest cannot settle it and the program's gate is the wrong instrument for it.

**What a rational owner should weigh instead.**

- **The forward premium they actually believe**, stated as a number. At the realized premium the
  growth-optimal answer is about 2×; at −2 pp it is about 1.3×; at −3 pp it is 1×.
- **The cohort distribution across start years**: the spread of terminal lifecycle ÷ 1× over every
  historical start, not its average.
- **Worst-cohort regret in dollars and in years of contributions**: which start year did worst, by how
  much, and when in the cohort's life the damage came.
- **The chance of finishing below 1×**, which §2d puts at 30–50 %.
- **A ruin-type event defined in advance**: for example the balance below cumulative contributions at
  year 20, or below half of the 1× holder's.
- **The financing regime.** Leverage paid for at a 6.6 % bill rate (1962–89) is a different trade from
  leverage at 2.7 % (1990–2026).
- **What the same dollars buy elsewhere.** The lifecycle rule's expected gain equals contributing an
  extra $1,280 a year at the realized premium, $580 at −1 pp, and nothing at −2 pp — with no tail.

---

## 5. Recommendation

**(i) Do nothing on leverage, and (iii) correct T-315. (ii) is offered as an option, not recommended as
a priority.**

1. **Hold 1×.** At the realized premium lifecycle leverage is worth about a fifth of terminal wealth in
   expectation, with a one-in-three chance of ending behind. At −2 pp it is worth nothing and carries
   the same dispersion. Half-Kelly says 1× everywhere. The early, small-balance years where leverage is
   cheap to be wrong about are also the years where it earns almost nothing (+$22k real at year 40 in
   the best case for five years at 2×).
2. **Do not build a LEAPS path.** It does not fit the account for several years, it is not cheaper on
   honest assumptions, it cannot be backtested from anything on disk, and its expiry is a forced sale
   for an investor whose whole premise is never selling. If the owner ever wants leverage, the vehicle
   is a UPRO+SPY or SSO+SPY blend rebalanced once a year.
3. **Correct T-315.** The standing record says the 1.25× arm significantly loses and that the glide wins
   the accumulation race. Both rest on a cost charged 252 times too often. Proposed unit: the one-line
   mask repair, the blend fee model for L < 2, arithmetic means in the break-even and Kelly rows, a
   re-run of the frozen arms, and corrected wording at `docs/State/CURRENT_STATE.md:155, 160` and
   `docs/State/TASK_LEDGER.md:206`. Whether a repaired re-run of a frozen pre-registration consumes a
   trial is the director's ruling.
4. **Raise contributions before raising leverage.** Each extra $1,000 a year is worth about $196k of
   real terminal wealth on the 1× path at the realized premium, and it is not a bet.

**My prior.** I put most of my weight on a forward arithmetic excess return 1–3 pp below the realized
7.1 %; that is a judgement, not a measurement. On it, the chance that lifecycle leverage finishes ahead
of 1× over forty years is 45–60 %, the expected gain is 0–10 % of terminal wealth, and the bad twentieth
of outcomes is 35–45 % behind. I would not take that trade for a holder whose stated plan already works
at 1×. I put about a 15 % chance on the cohort study below changing that view.

### 5.1 The optional study — a descriptive cohort table, pre-declared unable to pass

For the owner to approve or decline. Runs only after item 3, because it would reuse the same arm code.

- **Hypothesis.** None that can pass. Declared before the run: no arm can clear ci_low > 0 at
  N_eff 371 (§4); no arm may be promoted, deployed or quoted as an edge on this output. The verdict
  vocabulary is limited to DESCRIPTIVE.
- **Substrate.** T-306 `equity_tr_daily.csv` and a full-precision cash leg (the DTB3 file B-5 fetched
  from 1954; the quantised T-306 leg before that, labelled). md5 pinned; halt on any missing bar.
- **Cohorts.** One per January start. 40-year horizon: starts 1927–1986 (60 cohorts). 30-year horizon:
  starts 1927–1996 (70 cohorts). Reported as distributions; about 2.5 and 3.3 independent cohorts.
- **Contributions.** $10k at the start, then $5k a year scaled by the cumulative cash index (a
  no-new-data stand-in for real contributions; CPI on disk starts in 2000). Flat nominal as a
  sensitivity.
- **Arms.** (A0) 1×, the bar. (A1) lifecycle λ = 1, cap 2×, floor 1×, contributions discounted at the
  trailing 12-month bill rate. (A2) lifecycle λ = 1, cap 1.5×. (A3) 2× for the first ten years, then 1×.
  (A4) static 1.25×. Annual re-leveraging.
- **Vehicles.** SSO+SPY blend at 57 bp and UPRO+SPY blend at 56 bp, daily reset, fees on the levered
  sleeve only. **No LEAPS arm**: there is no option price history on disk, and a Black-Scholes
  synthetic is the Phase-0 defect already recorded at `docs/State/health_check.md:974`.
- **Metric.** Per cohort: Δ log terminal wealth vs A0.
- **The regret table.** For each arm × vehicle: minimum, 5th, 25th, median, 75th, 95th percentile and
  maximum of lifecycle ÷ 1×; the share of cohorts below 1×; the worst cohort's start year, its dollar
  shortfall and that shortfall in years of contributions; the share of cohorts whose balance is below
  cumulative contributions at year 20; the largest dollar gap to 1× at any point inside a cohort and
  its date; the same table at −1, −2 and −3 pp.
- **Interval.** A stationary block bootstrap of 40-year paths for the median Δ, ci_low reported. It is
  expected to be below zero.
- **N_trials consumed.** 8 (four levered arms × two vehicles), counted raw under the R3 rule; the
  haircut and nominal-contribution tables are reported sensitivities of those eight, following T-315's
  convention. The director may rule a different count before the freeze.
- **Expected result, stated now.** A median near +15–25 % at no haircut and near zero at −2 pp; a
  quarter to a third of cohorts behind 1×; the worst cohorts those that meet 1929–32, 1973–74 or 2008
  between years 8 and 20, at 30–50 % behind.

---

## Appendix — what is measured and what is assumed

**On disk, read or computed for this note**

- T-306 moments (§2.0), 1× drawdowns and trailing-return frequencies: computed from
  `data/research/substrate_multidecade/`.
- SSO 0.89 %, UPRO 0.90 %, SPY 0.09 % expense ratios: `scripts/b5_levered_diversified.py:92-96`.
- Swap spreads SSO 57 [18, 96] bp and UPRO 56 [35, 81] bp: B-5 §3.
- Crash factors: T-284 (2008) and T-315 (1929) tables. The 1929 figures come from the affected static
  arms; over those three years the phantom cost moves them by about four percent of what remained.
- SPY $710.14: `data/processed/SPY_1d.csv`, last bar 2026-04-17.
- N_eff 37.08, 267, 371.28: `docs/State/TASK_LEDGER.md:292`, B-5 §4.

**Assumptions, not on disk**

- Every LEAPS input: the financing spread, implied volatilities, bid-ask, strike and expiry
  availability, and the existence and depth of a chain on a low-priced S&P 500 ETF.
- XSP's contract size; any broker's support for long-dated or index options in an IRA.
- A real bill rate of 1.0 % for growth and for discounting contributions; contributions of $5k in real
  terms for 40 years.
- Independent annual returns and a normal approximation for every probability and percentile in §2d.
- The forward haircut itself.

**Formulas**

- Growth: `g(L) = r + L·μ − (L−1)·c − ½·L²·σ²`; gain vs 1×: `Δg(L) = (L−1)(μ−c) − ½(L²−1)σ²`.
- Lifecycle path: `W(t+1) = W(t)·exp(g(L_t)) + C`, `L_t = clip(λ·(W_t + PV_t)/W_t, 1, cap)`.
- Cohort moments: with `w_t` the share of terminal wealth that passes through the balance in year t,
  mean `Σ w_t·Δg(L_t)` and variance `Σ w_t²·(L_t−1)²·σ²`.
- Deflation: `E[max_N] = (1−γ)·Φ⁻¹(1−1/N) + γ·Φ⁻¹(1−1/(N·e))`, γ = 0.5772.

The two scratch scripts that produced the tables were not committed; every number above follows from
the inputs and formulas listed here.
