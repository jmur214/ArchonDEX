---
task_id: T-385 (B-10)
title: A permanent 10% gold leg (90% equity / 10% gold, monthly) vs 1× SPY on terminal wealth — verdict
date: 2026-11-11
author: regime-analyst lens (in-session worktree subagent), branch research/gold-leg-b10
outcome: "REFUTED, as pre-registered. Δ log terminal wealth vs 1× SPY is +0.042 (+0.08 %/yr) on 1971–2025, 95 % CI [−0.341, +0.441]. On 2000–2025 it is +0.124 (+0.48 %/yr), CI [−0.105, +0.367]. ci_low < 0 on both windows. The MDD clause is met: −55.25 % → −50.02 %, 5.22 pp shallower. But a 10 % zero-return cash leg alone gives 3.95 pp (reviewer diagnostic, §4a). So any 10 % non-equity weight clears the clause, and gold's own share at the GFC trough is ≈ 1.3 pp. In 2022 gold did worse than cash. Gold is a de-risking leg that costs no wealth, where cash costs ≈ 0.5 log TW over 55 years; it is not a distinctive hedge and not a wealth tool."
status: COMPLETE — independent review APPROVE (2026-11-11). The follow-up commit corrects text only; no result number changed. Determinism ×2 is bit-identical (results md5 add5cec09a5c0dc5e5bcadd5eac105c0). N_trials consumed +2 (the run +1; the reviewer's cash-control diagnostic +1, by the director's count).
reproduce: "python -m scripts.b10_gold_leg --smoke && python -m scripts.b10_gold_leg --out data/b10_local/b10_results.json && python -m scripts.b10_gold_leg --out data/b10_local/b10_results_run2.json && md5 -q data/b10_local/b10_results*.json   # reads the md5-pinned T-306 substrate + data/processed/GLD_1d.csv; writes worktree-local data/b10_local/"
---

# B-10 verdict — a permanent 10% gold leg vs 1× SPY

Pre-registration: `docs/Sources/prereg_b10_gold_leg_2026-11-11.md`, FROZEN at `0cc3f56`, with amendment 1
(the director's five rulings) at `f702523`. Both were committed before any return was computed.

## 0. The answer

**REFUTED** under the pre-registered rule: ci_low < 0 on the full window, and on 2000–2025 alone. Both
point estimates are positive and both CIs span zero. This is **"not demonstrated," not "demonstrably
negative"**: neither ci_high is below zero.

| window | Δ log TW (point) | per year | 95 % CI, auto block (project standard) | 95 % CI, 252-day block | P(boot > 0) |
|---|---|---|---|---|---|
| **W-71, 1971-01-04 → 2025-12-31** (55.0 yr, 13,867 days, block 24) | **+0.042** | **+0.08 %/yr** | **[−0.341, +0.441]** = [−0.62, +0.80] %/yr | [−0.409, +0.500] | 0.57 |
| **W-00, 2000-01-03 → 2025-12-31** (26.0 yr, 6,539 days, block 19) | **+0.124** | **+0.48 %/yr** | **[−0.105, +0.367]** = [−0.40, +1.41] %/yr | [−0.110, +0.342] | 0.86 |

**MDD on W-71, realized path:**
- 1× SPY: **−55.25 %** (peak 2007-10-09, trough 2009-03-09, recovered 2012-08-16).
- 90/10: **−50.02 %** (peak 2007-10-12, trough 2009-03-09, recovered **2011-02-18**).
- **Reduction: 5.22 pp. The clause (≥ 3 pp) is met.** The 90/10 book was back at its old high about
  18 months sooner.
- **Most of that reduction is not gold.** A 90 % equity / 10 % zero-return cash book, rebalanced
  monthly, has an MDD of **−51.30 %**: a **3.95 pp** reduction with no gold at all. This is the
  reviewer's diagnostic, not pre-registered (§4a).
  - Gold's own share at the GFC trough is ≈ **1.3 pp**.
  - **Any 10 % non-equity weight clears the ≥ 3 pp clause.** The clause, as briefed, did not isolate
    gold.

**Decision (prereg §6 and amendment 1):**
- ci_low(W-71) = −0.341 < 0, so REFUTED.
- ci_low(W-00) = −0.105 < 0, so REFUTED independently.
- The MDD clause does not rescue it.
- **No robustness label attaches:** the 252-day block and the GLD-fee arm both leave every gating
  ci_low negative.

**For a max-terminal-wealth Roth holder, in one line:** over 55 years a permanent 10 % gold leg left you
with about the same money as 1× SPY ($10k → $3.32M vs $3.18M, a gap well inside the noise). It made the
worst crash about 5 points shallower, but ~4 of those 5 points come from simply holding 10 % outside
stocks.
- What gold adds over that is that it costs no wealth: a 0 % cash mattress gave up ≈ 0.5 log TW over
  the same 55 years.
- It is not a better crash cushion than cash. In 2022 it was a worse one.
- Gold now sits at an all-time high, which history says is the worst entry point (§5).

## 1. Both arms, both windows

Primary fees: equity 0.09 %/yr (T-311 SPY-class) on both arms; gold 0.09 %/yr (IAUM) on the 10% leg.
Rebalancing is monthly at 1.5 bps × turnover.

| window | arm | terminal multiple | CAGR | MDD | MDD peak → trough (recovery) |
|---|---|---|---|---|---|
| W-71 | 1× SPY | 317.9× | 11.04 % | −55.25 % | 2007-10-09 → 2009-03-09 (2012-08-16) |
| W-71 | 90/10 | 331.6× | 11.13 % | −50.02 % | 2007-10-12 → 2009-03-09 (2011-02-18) |
| W-00 | 1× SPY | 7.20× | 7.89 % | −55.25 % | 2007-10-09 → 2009-03-09 (2012-08-16) |
| W-00 | 90/10 | 8.15× | 8.40 % | −50.02 % | 2007-10-12 → 2009-03-09 (2011-02-18) |

**Rebalance census:** 659 rebalances on W-71 and 311 on W-00, matching the month boundaries.
- Mean **two-sided** turnover per rebalance (Σ|Δw| over both legs, so each leg's trade is counted
  once) is 0.97 % and 0.87 % of the book.
- The cost is 1.5 bps × Σ|Δw|, T-311's convention.
- Total rebalance cost is 0.10 % and 0.04 % of wealth, so the cost is not a factor.

**Tracking error and the MBL line** (`[NN-MBL]`, secondary): the differential's annualized IR is
**0.028** on W-71, against 0.291 needed at the gate's N_eff of 37.08, or 0.388 at the prereg's hand count of 281 (unchanged to 3 d.p. at 282).
On W-00 it is **0.177**, against 0.423 or 0.564. The realized tracking error is 2.72 % (W-71) and
2.70 % (W-00), against the 2.55 % assumed in the prereg. Even an H1 pass would have been "exploratory,
not deployment evidence."

## 2. 2022 (descriptive, prereg §7 item 5)

| 2022 view | 1× SPY return | 90/10 return | 1× SPY MDD | 90/10 MDD | MDD reduction |
|---|---|---|---|---|---|
| fresh investment at 2021-12-31, calendar 2022 | −18.25 % | −16.42 % | −24.55 % | −22.89 % | **1.66 pp** |
| T-311 `CRISES["2022"]` segment (01-01 → 10-31) of the W-71 path | −17.81 % | −16.94 % | −24.55 % | −22.89 % | 1.66 pp |

Both troughs fall on 2022-10-12. Against 1× SPY, gold helped a little. **Against a 0 % cash mattress it
hurt.** The reviewer's 90/10 equity/zero-return-cash book bottomed at **−22.25 %**, against gold's
−22.89 % (§4a). **In 2022 gold was not a hedge.** The year when stocks and bonds fell together was a rising-real-rate year,
and gold fell into the equity trough too. The brief's motivation (stock-bond correlation +0.52 in
2022) is about a bond-holding book. For a 1× equity core, the correlation that matters is equity-gold,
and it did not help when real rates rose.

## 3. Regime anatomy (descriptive, W-71 path; never a headline)

**Per-crisis MDD** on the T-311 `CRISES` segments, measured from each segment's prior close:

| episode | regime type | 1× SPY MDD | 90/10 MDD | reduction |
|---|---|---|---|---|
| 1973–74 stagflation | inflation shock, negative real rates | −48.2 % | −38.7 % | **+9.5 pp** |
| 1980–82 Volcker | **real-rate shock, disinflation** | −20.2 % | −22.8 % | **−2.6 pp (worse)** |
| 1987 crash | liquidity crash | −33.1 % | −29.7 % | +3.5 pp |
| 1990 | recession / oil shock | −20.8 % | −18.2 % | +2.6 pp |
| dotcom 2000–02 | equity-specific bust, falling rates | −47.6 % | −43.2 % | +4.5 pp |
| GFC 2007–09 | credit crisis, falling rates | −55.3 % | −50.0 % | +5.2 pp |
| COVID 2020 | liquidity crash | −33.7 % | −30.8 % | +2.9 pp |
| 2022 | **real-rate shock, inflation** | −24.6 % | −22.9 % | +1.7 pp |

**Δ log wealth by decade,** with the monthly equity-gold correlation:

| decade | Σ d (Δ log TW) | corr(equity, gold), monthly |
|---|---|---|
| 1970s | **+0.251** | −0.09 |
| 1980s | −0.151 | +0.18 |
| 1990s | −0.182 | −0.13 |
| 2000s | +0.167 | +0.04 |
| 2010s | −0.075 | +0.02 |
| 2020s (to 2025) | +0.032 | +0.16 |

**Read this table against cash, not just against SPY (added after review).** Every reduction above
includes the mechanical effect of holding 10 % outside equity. With monthly rebalancing, a 10 % cash
leg's cushion is at most about a tenth of the equity drawdown: the reviewer measured 3.95 pp at the
GFC (§4a). Only a reduction clearly above that bound is gold's own.

**The regime reading (restated after review):**
- **1973–74 stands out.** Its 9.5 pp is about twice a tenth of the 48.2 % equity drawdown. This is the
  one episode where gold was clearly a distinctive hedge: an inflation shock with negative real rates.
- **The GFC is ≈ 1.3 pp of gold-specific cushion.**
- **The rest is at or near the cash bound:** 1987, 1990, dotcom and COVID are within ~0.5 pp of a tenth
  of their equity drawdowns, or below it.
- **Gold did worse than cash in both real-rate shocks:** 1980–82 (worse than SPY itself) and 2022
  (worse than the cash control).
- So gold's hedge value depends on the **real-rate regime**. It is distinctive only when real rates
  are falling or negative and inflation is the shock.
- The **wealth** contribution is one decade's re-pricing. The 1970s (+0.25) and 2000s (+0.17) are
  offset by two decades of loss (1980s and 1990s, −0.33 together). That is why the 55-year total is
  ≈ 0.
- A permanent leg needs no regime detector, so it can never be late. The price is that it is also
  never switched off in the regimes where it fails.

## 4. Sensitivities and cross-checks (all pre-named; none gates)

- **The 252-day block** gives W-71 [−0.409, +0.500] and W-00 [−0.110, +0.342]. No sign change.
- **The GLD-class fee (0.40 %, T-311's own `robo_returns`):**
  - W-71: +0.025 (+0.05 %/yr), CI [−0.358, +0.424];
  - W-00: +0.116 (+0.45 %/yr), CI [−0.113, +0.359];
  - MDD −50.05 %.
  - It costs ≈ 0.03 %/yr and changes nothing.
- **`t311.paired`, an independent implementation (21-day blocks):**
  - Δ compounding: W-71 [−0.63, +0.84] %/yr and W-00 [−0.44, +1.36] %/yr. These agree with the headline.
  - **ΔMDD CI vs 1× SPY: W-71 [+1.3, +9.5] pp and W-00 [+1.6, +9.7] pp, both excluding zero.** The
    drawdown reduction against 100 % SPY is robust under resampling; the wealth benefit is not.
  - This CI does **not** test gold against a cash leg. Most of the reduction is what any 10 %
    non-equity weight gives (§4a).
- **GLD splice validation (G11; PASS):** over 2020-04-09 → 2025-12-31, GLD − substrate = **+0.04 %/yr**
  against bounds [−1.00, +0.20], and the 21-day correlation is 0.991 (68 blocks).
  - The expected figure was ≈ −0.40 % (GLD's ER).
  - **A post-hoc diagnostic** (non-gating; changes nothing) traces the 0.44 pp residual to the start
    date. The window opens inside the April 2020 COMEX-London EFP dislocation: the GLD/substrate ratio
    jumps 3.1 % between 04-09 and 04-30. From 2020-06-30 the gap is **−0.34 %/yr**, which is GLD's ER,
    as expected.
  - So the post-2000 gold leg tracks spot. The 2020 dislocation is a transient futures premium of
    about 3 % that unwinds within weeks. Because the level telescopes, it reaches terminal wealth only
    through the one or two month-end rebalance prices it touched, which is negligible at a 10 % weight.

## 4a. REVIEWER DIAGNOSTIC — the cash control (NOT pre-registered; added after review; N +1)

The independent reviewer ran a control the prereg did not have: **90 % equity / 10 % zero-return cash**.
It uses the same equity leg and fee, monthly rebalance and 1.5 bps × Σ|Δw|. The worker reproduced it
with the harness's own `rebal_returns`, matching every figure below to the precision shown, and wrote
nothing to `data/`. It is a diagnostic and gates nothing. **The director counts it as a trial, so B-10
records N_trials +2.**

| arm | W-71 MDD (GFC trough 2009-03-09) | reduction vs 1× SPY | Δ log TW vs 1× SPY, W-71 (point, not bootstrapped) | 2022 MDD (fresh 2021-12-31) |
|---|---|---|---|---|
| 1× SPY | −55.25 % | — | 0 | −24.55 % |
| 90/10 equity / **gold** (IAUM) | −50.02 % | 5.22 pp | +0.042 | −22.89 % |
| 90/10 equity / **0 % cash** (reviewer) | −51.30 % | **3.95 pp** | **≈ −0.515** | **−22.25 %** |

What it changes:
- **About 3.95 of the 5.22 pp is de-equitization, not gold.** Gold's own share at the GFC trough is
  ≈ 1.3 pp (−51.30 → −50.02).
- **The ≥ 3 pp clause is cleared by any 10 % non-equity weight,** so it never isolated gold.
- **What gold adds over cash is that it costs no wealth.** The 0 % mattress gave up ≈ 0.5 log TW over
  55 years; gold left log wealth within noise of SPY.
  - That is a statement about a ZERO-return mattress. A T-bill or money-market leg earns a positive
    yield and would cost less. Its wealth cost is not computed here: the T-306 cash leg is quantized,
    and B-10 does not use it.
- **In 2022 gold did worse than the mattress** (−22.89 % vs −22.25 %).
- **Restated reading.** A permanent 10 % gold leg is a de-risking leg that costs no wealth. It is not
  a distinctive drawdown hedge except in an inflation shock with falling or negative real rates (§3).
  The earlier wording, "the drawdown benefit is real and robust" and "buy it … for the drawdown", is
  withdrawn. It credited gold with what the 10 % weight does.

## 5. Predictions vs outcomes (prereg §13)

| quantity | predicted | observed | hit? |
|---|---|---|---|
| W-71 Δ | +0.1 %/yr (−0.4 to +0.6), ci_low < 0 | +0.08 %/yr, ci_low −0.341 | ✓ |
| W-00 Δ | +0.6 %/yr (0.0 to +1.2), ci_low < 0 | +0.48 %/yr, ci_low −0.105 | ✓ |
| W-71 MDD | B −51 to −55 %; T 4–6 pp shallower | **B −55.25 % (outside the range)**; T 5.22 pp shallower | **✗ (B range missed; the T reduction hit)** |
| 2022 | B ≈ −18 % year, MDD ≈ −24 %; T ≈ 2 pp better; reduction < 3 pp | −18.25 / −24.55 %; T better by 1.83 / 1.66 pp | ✓ |
| 252-day block | CI ≥ 1.5× wider | **1.16× wider (W-71); 0.96× (W-00, narrower)** | **✗** |
| 0.40 % fee | Δ lower by ≈ 0.03 %/yr; no category change | −0.031 %/yr; none | ✓ |
| decades | 1970s dominate; 1980s/1990s negative; 2000s positive | +0.25; −0.15 / −0.18; +0.17 | ✓ |
| outcome | REFUTED, MDD clause met | REFUTED, MDD clause met | ✓ |

**The two misses** (the second was flagged by the review):
- **The baseline MDD range.** I predicted −51 to −55 % for 1× SPY; it was −55.25 %, just outside the
  range. Narrow, but a miss.
- **The block width.** I expected the 20-year gold bear (1980–2001) to put enough long-range dependence
  into the daily differential that annual blocks would widen the CI by half. They did not. At a 10 % weight,
the differential's variance is dominated by day-to-day noise, so short blocks already capture most of
the uncertainty. The lesson for future static-leg tests is that the 24-day block is not materially
anti-conservative here.

**Erb-Harvey, the post-ATH caveat** (FAJ 2013; SSRN 5525138, 2025):
- Gold's long-run real return is ≈ 0, and its multi-year real returns from an all-time high have been
  low.
- The substrate ends at 2025-12-31 at about $4,300, at or near the all-time high.
- Both brief windows also start at gold-favourable points: 1971 precedes the $35 → $850 re-pricing, and
  2000 sits within ~15 % of the 1999–2001 secular low.
- **The +0.08 %/yr and +0.48 %/yr are therefore backward-looking upper bounds on the forward case.**
  Even those cannot be told apart from zero. A forward entry from today's level has the Erb-Harvey
  headwind on top.

## 6. Caveats

- **`[NN-SUBSTRATE-REVERIFY]`:** these numbers are conditional on the T-306 build of 2026-07-10 at the
  pinned md5s (prereg §3.5).
  - The equity leg is the Fama-French broad-market TR before 1993-02-01 and the pre-cutover
    `SPY_1d.csv` after.
  - **Re-verify required after the cutover or any T-306 rebuild.** A refutation this wide is unlikely
    to flip.
- **The ER is anachronistic.** IAUM's 0.09 % is applied from 1971. Before 2004 there was no gold ETF,
  and the real cost of holding gold was higher. The 0.40 % arm bounds part of that, and it moves the
  result by 0.03 %/yr.
- **Pre-2000 timing.** The gold price is the London AM fix (10:30) against a 16:00 New York equity
  close. This adds noise to the daily pairing and the month-end rebalance price, not bias: the log-
  wealth sum telescopes.
- **The cash leg is not used.** The quantized T-306 cash file has no path into any number here
  (prereg §3.4).
- **T-311 alignment.** The harness uses T-311's `reindex(cal).ffill()` alignment for fidelity. That
  lags gold 1–2 days on 9 Christmas dates inside W-71 (disclosed in the prereg; immaterial).

**Caveat on T-311's own 3-asset arm (director's instruction):** T-311's `load_substrate` forward-fills
the gold leg **flat for 73 rows past its last native print**, from 2026-01-02 to 2026-04-17. This was
verified at prereg §3.4 by comparing aligned levels.
- T-311's SECONDARY (3-asset, equity + bond + gold) window ran to 2026-04-17, so that arm's last ~3.5
  months carried a frozen gold price.
- Its trend signals on gold also read a flat price for those 73 days.
- The effect on a 58-year verdict is small but not zero. That arm's late-window numbers should be read
  with this caveat until T-311 is re-run with an end ≤ min(native ends).
- B-10 refuses such an end (guard G5) and is not affected. T-311 is unedited here; the director is
  logging the defect in health_check.

## 7. Measurement integrity (`[NN-FAIL-CLOSED]`, guards G1–G11)

All guards passed on both windows, on W-22 and on the smoke runs:
- md5 pins on the equity, gold and GLD inputs and the T-311 script, plus T-311's constants;
- native-index integrity;
- the largest native gap inside a window: equity 7 d (9/11), gold 6 d (W-71) / 5 d (W-00);
- as-of staleness of gold at most 5 d;
- window end ≤ min(native ends);
- base prints present;
- identical arm indexes;
- bootstrap length;
- parity with `t311.robo_returns`: max |Δ| 6.7e-16;
- the Σd = log(TW_T/TW_B) identity, to 7.2e-13;
- the rebalance census;
- the GLD validation.

**A lock caught a real defect in this harness before the first run.** pandas 3.0.1 parses the substrate
dates as `datetime64[us]`, not `[ns]`. The first draft of the gap and staleness guards divided `asi8`
by an ns-per-day constant, so every gap came out 1,000× too small and G3/G4 could never fire: the T-311
vacuous-guard class again, by a different route. The planted 15-day-hole lock failed, and the guards now
use unit-safe `TimedeltaIndex.days`. No tracked script outside B-10 uses `asi8` day arithmetic (grep of
`scripts/ core/ engines/ orchestration/ backtester/`).

The locks are in `tests/test_b10_gold_leg_guards.py` (19 tests, synthetic data):
- planted hole (G3), including a test that the hole becomes invisible after ffill;
- staleness (G4);
- the flat forward-filled tail (G5);
- base print (G6);
- four integrity defects (G2);
- parity, with a positive control and a 1-bp negative control (G9);
- rebalance census (G10);
- misaligned arms (G7);
- short bootstrap (G8);
- the decision rule, including amendment 1's precedence case;
- the base-value MDD.

**Determinism:** two full runs produced bit-identical `b10_results.json`, md5
`add5cec09a5c0dc5e5bcadd5eac105c0`. Each run takes about 3 s.

**Guard-coverage notes from the review** (none changes a number):
- **G4 measures as-of staleness on the NATIVE index,** not the age of the value T-311's ffill carries
  onto each equity date. Both peak at 5 d (W-71) and 4 d (W-00) on these inputs, so there is no effect.
- **A frozen-value tail with an intact index** (repeated levels, no missing dates) is caught only by
  G11, which covers 2020-04 → 2025-12. A planted 1990 frozen run passed silently. The pinned inputs are
  clean: the longest run of identical consecutive values is 3 d for gold and 2 d for equity.
- **The locks exercise `datetime64[us]` only.** The reviewer verified the gap and staleness arithmetic
  halts correctly at ns, us, ms and s resolution and with mixed units.
- **The smoke never calls `boot`,** so amendment 1's lowered G8 floor is not exercised by it. That is
  harmless: no smoke number is quoted.

## 8. N_trials and honest N

**N_trials consumed: +2.** The run is +1. The reviewer's cash-control diagnostic (§4a) is +1 by the
director's count: a new configuration, not pre-registered, though it gates nothing.
- The worker's reproduction of it is the same configuration and adds nothing.
- The sensitivities, cross-checks, crisis and decade tables and the GLD diagnostic are characterization
  and consume no N. This includes the post-hoc GLD ratio checkpoint read in §4, which changes no number.

Honest N, read-only (prereg §10):
- **the gate:** N_raw 231 → N_eff 36.92, which is **37.08 with the run** (the prereg's figure). The
  extra diagnostic trial moves it trivially; that is not recomputed here.
- **the hand count:** ≥ 282 (267 from ruling 9.2, + 13 standalone trials since, + B-10's 2), ≈ 289 if
  the July T-306 series is outside the 267.

The registry still cannot see this trial (health_check MEDIUM `573fc62`); recording it is the director's
call.

## 9. Proposal: the forward twin (OUT OF SCOPE by director ruling; proposal only)

`paper_trader/` was not touched. **A forward twin would not change this verdict**: a 10 % gold leg's
wealth edge is ~0.1–0.5 %/yr against a 2.7 % tracking error, so three years of forward data cannot
distinguish it from zero (the MDE over 3 years is ≈ 4.4 %/yr). What a twin *can* test is **whether
gold cushions the next equity drawdown BETTER THAN CASH,** entering at an all-time-high gold price.
Measuring it only against 100 % SPY would credit gold with the de-equitization effect (§4a).

Proposal, for the director's queue, propose-first since it touches `paper_trader/`. **Revised after
review: there is now a cash twin, and the question is gold vs cash.**
- **Shape:** on the `dbmf_shadow.py` pattern, three simulated books from one start date. Each holds
  SHARES plus cash, not weights (the Performance Laboratory convention).
  - Twin A: 100 % VOO/SPY-class.
  - Twin B: 90 % VOO / 10 % IAUM, monthly rebalance at the first close of each month, 1.5 bps × Σ|Δw|.
  - **Twin C (the control): 90 % VOO / 10 % cash,** same rebalance and cost. The cash leg is a real
    T-bill or money-market instrument earning its realized yield (an SGOV-class ETF, or the account's
    money-market sweep, named in the prereg), not a 0 % mattress. That makes C a fair wealth control
    too.
- **Inputs:** daily closes for SPY, IAUM and the cash instrument from the existing price path. If any
  price is missing, the day is marked NOT EVALUABLE (fail-closed). It is never forward-filled.
- **Pre-registered question:** at the first SPY drawdown of 15 % or more from a high after the start,
  is twin B's drawdown shallower than twin **C**'s by at least 1.0 pp, the GFC-scale gold-specific
  cushion (§4a)?
  - The original "B ≥ 1.5 pp shallower than A" threshold is withdrawn. 10 % × a flat gold price is
    exactly the cash effect, so it measured nothing about gold.
  - Secondary:
    - B vs A, which reproduces the brief's comparison, reported but not deciding;
    - the realized equity-gold correlation of daily returns inside that drawdown;
    - B vs C log wealth at the evaluation date, a point estimate, labelled "not decidable in 3 years".
  - **Evaluability:** 2028-09-30 per the brief, OR the first ≥ 15 % drawdown, whichever is LATER.
    Before that it reports "NOT EVALUABLE — n days."
- **What it can and cannot decide:**
  - It can falsify "gold cushions equity drawdowns better than cash at today's real rates."
  - It cannot establish a wealth edge.
  - A 2022-style real-rate drawdown, where gold falls with equities and loses to cash, is the
    informative failure case.
- **N_trials:** +1 at the evaluation, none while it accrues.

## 10. What this closes and what it does not

**Closed:** a permanent 10 % gold leg as a **terminal-wealth** improvement over 1× SPY on 55 and 26
years of the T-306 substrate. **Not closed:**
- gold vs cash as a drawdown cushion. Against 1× SPY the reduction is robust (the ΔMDD CI excludes
  zero), but ~3.95 of the 5.22 pp is what a 10 % cash leg gives (§4a). Gold-specific cushioning is
  ≈ 1.3 pp at the GFC, clear only in 1973–74, and negative in 2022. No gold-vs-cash CI was computed;
  the revised forward twin (§9) is the proposed test;
- other weights, which were not tested (pre-commitment);
- gold inside a timing rule, which is the sleeve's existing use and a different question;
- a forward-looking case from today's all-time-high price, which the backtest cannot speak to.

The result fits the pattern of B-5 and B-9: static diversifiers at deployable weights leave log wealth
within noise of 1× equity. Their value, if any, shows up in drawdown depth and time under water. **That
drawdown value has to be measured against a same-weight cash leg, not against 100 % equity.**
