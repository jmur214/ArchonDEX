---
task_id: T-385 (B-10)
title: Pre-registration — a permanent 10% gold leg (90% core / 10% gold, monthly rebalance) vs 1× SPY on terminal wealth
date: 2026-11-11
worker: regime-analyst (worktree agent-a3cfbdde062836527)
branch: research/gold-leg-b10
status: DRAFT — Phase 1 STOP. A read-only input census is done (index spans, calendar gaps, file md5s, the honest-N read). NO arm, leg, blend or benchmark return has been computed. Awaiting the director's acknowledgment and the rulings in §17. N_trials consumed on acknowledgment: +1.
---

# B-10 — does a permanent 10% gold leg beat 1× SPY on terminal wealth?

## 1. The question (H1 and refutation verbatim from the brief)

Source: `docs/Sources/alpha_frontier_program_2026_09_30.md` §3.2, "### B-10".

**Deliverable (brief):** 90% core / 10% gold, monthly rebalance, 1971–2026 and 2000–2026; paired
Δ log TW vs 1× SPY ci_low; MDD both; the 2022 window.

**H1 (brief, verbatim):** "ci_low > 0 on the full window AND MDD reduction ≥ 3 pp."

**Refutation (brief, verbatim):** "ci_low < 0 on the full window OR on 2000–2026 alone."

**N (brief):** +1. **Brief prior:** 25% ("the hedge case is strong, the wealth case thin").

**Scope cut (director ruling, 2026-11-11):** the brief's forward twin on the `paper_trader` shadow
pattern is OUT OF SCOPE. `paper_trader/` is not touched. The verdict will carry a short proposal for it.

B-10 runs in a **standalone harness** (the T-311 pattern). It does not use `BacktestController`.

## 2. Hard pre-commitments

1. **One gating configuration.** 90% equity / 10% gold, monthly rebalance, IAUM-class gold ER
   0.09%/yr. No other weight, rebalance frequency, ER or window can become the headline.
2. **No tuning after any result.** Every sensitivity in §7 is named here and is reported beside the
   headline, never in place of it.
3. **Windows are set by input availability (§3.1), not by results.** Both start years come from the
   brief.
4. **Inputs are md5-pinned (§3.5).** The harness halts on any mismatch.
5. **Determinism ×2.** Bit-identical md5 of the results JSON before any number is quoted.
6. **Smoke first.** Smoke runs cover the FIRST 12 months of each window (1971 and 2000). They check
   mechanics only (rebalance count, turnover cost, parity lock, guards). No smoke number is quoted.
7. **Outputs are worktree-local** under `data/b10_local/`, a real directory. Nothing is written
   through the shared `data/research` symlink.

## 3. Input census (read-only; no returns computed)

### 3.1 Windows, set by input availability

| leg | file | native span | rows | md5 |
|---|---|---|---|---|
| equity | `data/research/substrate_multidecade/equity_tr_daily.csv` | 1926-07-01 → **2026-04-17** | 26,224 | `c2030019b8846792b5f8e3d18421c905` |
| gold | `data/research/substrate_multidecade/gold_tr_daily.csv` | 1968-01-03 → **2025-12-31** | 14,611 | `30c9d15d18ce2a0c511a0e2398c55a26` |

The gold leg ends first. **Both windows therefore end 2025-12-31.** No leg is forward-filled past its
last native print. The brief's "–2026" cannot be honoured: the equity leg's 2026-01-02 → 2026-04-17
rows exist, but there is no gold print to pair with them.

| window | base (initial investment at this close) | first return | last return | return days | years |
|---|---|---|---|---|---|
| **W-71 (full; the gating window)** | 1970-12-31 | 1971-01-04 | 2025-12-31 | 13,867 | 55.00 |
| **W-00 (the second refutation window)** | 1999-12-31 | 2000-01-03 | 2025-12-31 | 6,539 | 26.00 |
| W-22 (descriptive only) | 2021-12-31 | 2022-01-03 | 2022-12-30 | 251 | 1.00 |

Each window is a separate investment that starts at 90/10 (or 100% equity) at the base close. W-00 is
not a slice of the W-71 path.

### 3.2 The gold leg is not the splice the brief describes

The brief says "splice LBMA → GLD → IAUM". The T-306 build (`provenance.json`) is actually:

- **1968-01-03 → 2000-08-29:** LBMA gold AM fix (USD).
- **2000-08-30 → 2025-12-31:** `data/research/gold_gcf_t255.csv`, the COMEX front-month settle (the
  frozen T-255 series).

The file contains **no GLD segment and no IAUM segment.** T-306 validated the series as spot gold: the
LBMA/GCF level ratio is 1.0002, so there is no cumulative futures-carry drift; its tag is "price ≈ TR
(no yield)". The physical-gold ETF NAV is spot minus ER, so **spot minus a synthetic ER is the
ETF-equivalent path**. B-10 uses the substrate as built and applies the IAUM ER synthetically over the
whole window.

Two consequences:
- **The ER is anachronistic.** No gold ETF existed before 2004-11 and IAUM launched in 2021. The
  pre-ETF cost of holding gold (storage, insurance, dealer spread) was higher. The 0.40% sensitivity
  (§7) partially covers this.
- **The pre-2000 gold price is the 10:30 London fix; the equity close is 16:00 New York.** The
  ~10.5-hour asynchrony adds noise to the daily pairing and to the month-end rebalance price, but not
  bias: the log-wealth sum telescopes. T-306 measured the timing basis as benign: daily corr 0.39,
  21-day corr 0.965.

**Splice validation, Phase 2, non-gating but fail-closed:** the only local GLD file is
`data/processed/GLD_1d.csv`. It covers 2020-04-09 → 2026-04-17, md5
`8088c96fb0630fe9843d4c1c8d911609`; GLD pays no distributions. Over the common span
2020-04-09 → 2025-12-31 the harness computes:
- the annualized log-return gap, GLD − substrate gold. Expected ≈ −0.40%/yr (GLD's ER).
- the correlation of 21-day log returns.

**HALT** if the gap falls outside [−1.00, +0.20] %/yr or the correlation is < 0.95. These bounds catch
a gross splice defect (for example, a futures excess-return series would drift by the cash rate,
2–5%/yr in 2022–25). They do not test the ER to the basis point. No IAUM file exists locally and no
network is used.

### 3.3 Calendars: native gaps, checked before any alignment

Checked on each leg's NATIVE index:
- **equity:** monotonic, no duplicate, NaN or non-positive values. Its max gap inside W-71 is
  7 calendar days (2001-09-17, the 9/11 closure). Its Saturday rows end 1952-05-24, so none fall in
  any window.
- **gold:** monotonic, no duplicate, NaN or non-positive values. Its max gap inside W-71 is 6 days
  (1973-12-27 and 1984-12-27, Christmas). The T-306 report's 18-day gold gap is
  **1968-03-15 → 1968-04-01**, the London gold-market closure in the March 1968 gold crisis. It is a
  real event, and it is outside both windows.
- **Joint (W-71):** 148 equity days (1.07%) have no same-day gold print (London holidays), and
  140 gold days have no equity print (NYSE holidays). The maximum as-of staleness of the gold price on
  an equity day is **5 calendar days** (W-00: 4). In W-00 the calendars nearly coincide, because GCF
  is on the US calendar after 2000-08-30.

### 3.4 T-311's loader — what B-10 imports, and the two defects it does not import silently

The brief says to use the T-311 conventions by import. B-10 imports
`scripts/deep_reverify_sleeve_t311.py` unedited (md5 `a7f77d5f28fdfb889c1cd3add83befbb`):
`load_substrate`, `buyhold_equity`, `robo_returns`, `paired`, `ER`, `TXN`, `TD` and `CRISES`.

Three properties of `load_substrate` were verified on these inputs:

1. **The calendar-hole guard is vacuous** (`:72`; health_check LOW, 2026-11-11). B-10 adds its own
   guard on each leg's native index, before the reindex and ffill (§8 G2–G4).
2. **NEW: it forward-fills gold flat past gold's last print.** Aligned onto the equity calendar, gold
   runs to 2026-04-17. That adds **73 rows, all equal to the 2025-12-31 level.** This was verified by
   calling `load_substrate(["equity","gold"])` and comparing levels. No return was computed. B-10
   refuses any window end after min(native ends) (§8 G5).
   - Consequence for T-311's own SECONDARY (3-asset) arm: its window ran to 2026-04-17 with a flat
     gold leg for its last ~3.5 months. The effect is small but not zero. **Reported to the director;
     not fixed here** (T-311 is read-only for this brief).
3. **Its `reindex(cal).ffill()` alignment lags gold by 1–2 days on 9 dates inside W-71.** These are
   Christmas clusters in 1971, 1976, 1982, 1993 and 1999, where London printed on a NYSE holiday and
   then skipped the next NYSE day. A strict as-of join would use the newer print. B-10 keeps T-311's
   alignment for fidelity and discloses the 9 dates. The effect is a timing shift inside a month, and
   the window sum telescopes.

**Cash is not used.** The T-306 cash leg is quantized to 1 bp/day (health_check MEDIUM, 2026-11-11), and
a 90/10 equity/gold book has no cash sleeve.
- B-10's own rebalance function has no cash term.
- `load_substrate` reads `cash_daily.csv` and returns it aligned. **B-10 discards that return value.**
- The parity call to `t311.robo_returns` passes an all-zero cash-rate series and no `_cash` weight, so
  the cash term is identically 0 × 0.
- No number in B-10 depends on `cash_daily.csv`.

### 3.5 Pinned md5s (the harness HALTS on mismatch)

`equity_tr_daily.csv` `c2030019…c905`, `gold_tr_daily.csv` `30c9d15d…2a26`, `GLD_1d.csv`
`8088c96f…1609`, and `scripts/deep_reverify_sleeve_t311.py` `a7f77d5f…efbb` (full hashes in §3.1–3.4).

## 4. Arms and construction (frozen)

| arm | holdings | rebalance | ER (annual, accrued daily as ER/252) | trading cost |
|---|---|---|---|---|
| **B: 1× SPY (baseline)** | 100% equity leg | none (buy-and-hold) | equity 0.09% (T-311 `ER["equity"]`, SPY-class) | none |
| **T: 90/10 (treatment, gating)** | 90% equity, 10% gold | monthly | equity 0.09%; **gold 0.09% (IAUM)** | 1.5 bps × one-way turnover at each rebalance (T-311 `TXN`) |

- **Rebalance timing (T-311 `robo_returns` convention):** the book is reset to 90/10 at the close of
  the last trading day of each month. In implementation, holdings reset at the start of the first
  trading day of the new month, before that day's return. The cost Σ|Δw| × 1.5 bps is charged on that
  day. The book drifts with prices within each month.
- **Inception:** both arms are invested at the base close (§3.1) at target weights. Neither arm is
  charged an inception cost (the T-311 convention, symmetric).
- **The ER is neutral at the primary:** both legs carry 0.09%, so T and B pay the same total ER.
- **No taxes** (Roth wrapper). No dividends on gold. The equity leg is total return.
- **Implementation:** T is computed by B-10's own vectorized function, `rebal_returns(legs, weights, er)`.
  **Parity lock:** at T-311's ER (gold 0.40%) that function must reproduce
  `t311.robo_returns(legs, {"equity": 0.9, "gold": 0.1}, zero_cash)` to max |Δ| ≤ 1e-12 on every
  window, or the harness halts. The 0.40% sensitivity arm (§7) is therefore literally T-311's function
  output. B is `t311.buyhold_equity(legs)`.

## 5. Metric and bootstrap (frozen)

- **Paired daily differential:** d_t = log(1 + r_T,t) − log(1 + r_B,t), on identical dates (asserted).
- **Headline statistic:** Δ log TW = Σ d_t over the window, equal to log(TW_T / TW_B). Also reported
  annualized as Σ d_t / years.
  - Identity check: Σ d_t must equal log(TW_T/TW_B) from the two equity curves to 1e-9, or HALT.
- **Bootstrap (the gating CI):** `MetricsEngine.bootstrap_distribution(d, metric_fn=sum,
  n_iterations=1000, block_length=None, seed=0, confidence=0.95)`. This is the project-standard
  moving-block bootstrap (Künsch 1989) with the auto block max(5, round(n^⅓)): **24 days on W-71, 19
  on W-00.** `ci_low` is the 2.5th percentile.
- **Block sensitivity (pre-named, non-gating):** the same call with `block_length=252`.
- **Cross-check (non-gating):** `t311.paired(T, B)`, an independent implementation (L = 21,
  1000 iterations, seed 0). It reports `dLogWealthAnn_ci` and `dMaxDD_ci`.
- **Max drawdown:** each arm's realized equity curve, **including the base value 1.0**, so a first-day
  loss counts. **MDD reduction** = |MDD_B| − |MDD_T| in percentage points.

## 6. Decision rule and pre-named outcomes

Gating quantities, all at the standard block on the primary configuration:
- `ci_low(W-71)` and `ci_low(W-00)`;
- **MDD reduction on W-71**, the realized path (a point value: it is the drawdown an investor actually
  lived through). The paired-bootstrap ΔMDD CI is reported beside it, non-gating.

The brief's H1 and refutation can both fire at once (full-window ci_low > 0 and MDD ≥ 3 pp, while
W-00's ci_low < 0). **Proposed resolution (§17 ruling 1): the refutation takes precedence.**

| Outcome | Condition | What it means | What it does NOT mean |
|---|---|---|---|
| **H1 MET** | ci_low(W-71) > 0 AND MDD reduction(W-71) ≥ 3.0 pp AND ci_low(W-00) ≥ 0 | On 55 years of this substrate, 10% gold raised log wealth significantly and cut the worst drawdown. | Not deployment evidence unless the MBL line (§10) clears. Not a forecast: gold is at an all-time high (Erb-Harvey, §14). |
| **REFUTED** | ci_low(W-71) < 0 OR ci_low(W-00) < 0 | Not established on terminal wealth. **This includes a positive point estimate whose CI spans zero.** The verdict prints the point and the CI, so "not demonstrated" and "demonstrably negative" are visibly different. | Not a claim that gold lowers wealth, unless ci_HIGH < 0 as well. |
| **NOT MET, not refuted** | both ci_low ≥ 0, but MDD reduction < 3.0 pp | A wealth win without the hedge leg. | Not H1. |

Labels that attach without changing the category:
- "**not robust to annual blocks**" if the 252-day block flips the sign of a gating ci_low;
- "**not robust to GLD-era cost**" if the 0.40% ER arm flips it.

## 7. Pre-named secondary reporting (non-gating; consumes no N)

1. The 252-day block sensitivity (§5), on both windows.
2. **The ER sensitivity:** gold at 0.40%/yr (T-311 `ER["gold"]`, GLD-class), both windows.
3. `t311.paired` cross-check, including the ΔMDD CI.
4. **MDD both arms on W-71, W-00 and W-22**, plus the drawdown dates (peak, trough, recovery).
5. **W-22 (calendar 2022):** each arm's return, MDD and Δ, as a fresh investment at 2021-12-31. Also
   the T-311 `CRISES["2022"]` segment (2022-01-01 → 2022-10-31) of the W-71 path.
6. **Per-crisis MDD, both arms,** on the T-311 `CRISES` segments of the W-71 path that fall inside
   the window. "1970" is excluded (it falls before W-71).
7. **By-decade decomposition:** Σ d_t per calendar decade (1970s through 2020s) on the W-71 path, and
   the equity-gold correlation of monthly returns per decade. Descriptive only. **It answers "where did
   the Δ come from?"**: I expect the 1970s re-pricing ($35 → $850) to dominate. It is never a window
   to be quoted as the result.
8. The GLD splice validation (§3.2), with its gap and correlation.

## 8. Fail-closed guards (`[NN-FAIL-CLOSED]`) and the locks that prove them

| ID | Guard | Halts when |
|---|---|---|
| G1 | input md5s (§3.5) | any mismatch |
| G2 | native index integrity, per leg | non-monotonic, duplicate, NaN or non-positive values |
| G3 | native gap, per leg, inside [base, end] | any gap > 10 calendar days (observed max: 7 equity, 6 gold) |
| G4 | as-of staleness of gold on equity days inside the window | > 7 calendar days (observed max: 5) |
| G5 | window end ≤ min(native ends) | any window would use a forward-filled tail (catches §3.4 item 2) |
| G6 | base date has a native print within 7 days for each leg | violated |
| G7 | arms share an identical date index, with no NaN in d | violated |
| G8 | bootstrap input length ≥ 2 × 252 (`bootstrap_distribution` silently returns zeros below 4 obs) | violated |
| G9 | the parity lock (§4) and the Σd identity (§5) | violated |
| G10 | rebalance census: the number of rebalances equals the number of month boundaries in the window, and turnover > 0 | violated |
| G11 | GLD splice validation (§3.2) | outside tolerance |

**Locks:** `tests/test_b10_gold_leg_guards.py` uses synthetic data, with no dependence on `data/`.
- G3 and G5 are proven by PLANTING a 15-day hole and a flat forward-filled tail. Each must raise.
- G9's parity lock is proven by a positive control (it passes when the functions match) and a negative
  control (a 1-bp ER perturbation makes it fail).
- G8 has a planted short series.

## 9. Power and minimum detectable effect

The assumption comes from the literature, not the substrate: gold σ ≈ 19.5%/yr, equity σ ≈ 16.5%/yr,
ρ ≈ 0. The tracking error of T vs B is ≈ 0.1 × √(σ_g² + σ_e²) ≈ **2.55%/yr**. The MDE at 80% power for
ci_low > 0 (one-sided 2.5%) is (1.96 + 0.84) × TE / √T:

| window | T (yr) | SE of Δ (%/yr) | MDE (%/yr) | MDE (Δ log TW) |
|---|---|---|---|---|
| W-71 | 55.0 | 0.34 | **0.97** | 0.53 |
| W-00 | 26.0 | 0.50 | **1.40** | 0.37 |

These are iid-approximation figures. The block bootstrap on a differential with multi-decade
persistence will be wider: gold had a 20-year real bear market from 1980 to 2001. The 252-day block
sensitivity exists to show how much wider.

**The expected effect is far below the MDE** (§13). Only an upper-tail realization can meet H1.

## 10. Honest-N context (read-only, never written)

The gate was read through `core/measurement/mbl_gate.py` (`compute_n_effective`,
`compute_n_effective_correlated`, `load_n_effective_artifact`) on the pinned registry
(`config/honest_n_pin.json`).
- `run_registry.sqlite` md5 `83e474412a37075db16d419ad3dea414` was identical before and after the read.
  The connection is `mode=ro`.
- **The gate's N:** N_raw = **231**; ρ̄ (ci_low) 0.4325; ONC compression 0.1598. **N_eff (conservative)
  = 36.92** (equicorrelated 33.51, ONC 36.92). **At N_raw + 1 (this trial): N_eff = 37.08.**
- **The registry omits standalone-harness trials** (health_check MEDIUM, `573fc62`), so a hand count
  follows:
  - **267:** the director's ruling 9.2 on the Option-B data pass (2026-10-13, no borrowed correlation
    credit; `docs/State/CURRENT_STATE.md`, the 2026-10-13 entry);
  - **+13:** standalone trials recorded since then, from their verdicts: B-1 6, T-379 2, B-9 2, B-2 2,
    B-5 1;
  - **+1:** this trial;
  - **= 281.** This is a lower bound. I cannot establish whether the July T-306-family standalone
    series is inside the 267. If it is not, the count is ≈ 288. That series is T-311 → T-312/T-315 →
    T-314 → T-318/T-320 → T-333, whose counter ran 76 → 81. MBL is insensitive across 267–288.

**The MBL line for the differential's IR** uses the exact form E[max_N]/√T. It is a reported secondary,
not part of H1:

| window | T (yr) | IR needed @ N_eff 37.08 | IR needed @ hand N 281 (288) |
|---|---|---|---|
| W-71 | 55.0 | 0.291 | 0.388 (0.389) |
| W-00 | 26.0 | 0.423 | 0.564 (0.565) |

At the TE of §9, IR 0.291 on W-71 needs Δ ≈ 0.74%/yr, and 0.388 needs ≈ 0.99%/yr. If H1 is met with an
IR below the line, the verdict reports "**ci_low clears, MBL does not**: exploratory, not deployment
evidence" (`[NN-MBL]`).

## 11. N_trials

**+1** (one configuration, one family). Everything in §7 is characterization, not selection, and
consumes no N: the block and ER sensitivities, the cross-check, the 2022 and crisis windows, the decade
decomposition and the splice validation. The B-5 and B-9 practice is the same. The smoke runs consume
none.

## 12. Substrate note (`[NN-SUBSTRATE-REVERIFY]`)

The verdict depends on the T-306 build of 2026-07-10, at the md5s in §3.5.
- The equity leg after 1993-02-01 comes from the pre-cutover `data/processed/SPY_1d.csv`. Before
  1993-02-01 it is the **Fama-French broad-market TR, not the S&P 500**. "1× SPY" means "1× US broad
  market" for the first 22 years of W-71.
- **Every number from B-10 carries "re-verify required after cutover / any T-306 rebuild."**
- The two open T-306 caveats are handled as follows:
  - the quantized cash leg is not used (§3.4);
  - the vacuous guard is replaced by G2–G6;
  - the flat-tail ffill is new, reported in §3.4, and refused by G5.

## 13. Predictions (frozen here; the verdict compares against them)

These come from public long-run levels, not the substrate:
- gold ≈ $37 (1971-01) → ≈ $4,300 (2025-12), log growth ≈ 8.6%/yr;
- gold ≈ $288 (1999-12) → ≈ $4,300, log growth ≈ 10.4%/yr;
- US equity TR ≈ 10.3%/yr log (1971–2025) and ≈ 7.6%/yr log (2000–2025);
- the rebalancing (diversification) return of a 90/10 constant mix ≈ ½ Σ wσ² − ½ σ_p² ≈ +0.29%/yr.

| quantity | prediction (plausible range) |
|---|---|
| W-71 Δ annualized | **+0.1%/yr** (−0.4 to +0.6); **ci_low < 0** |
| W-00 Δ annualized | **+0.6%/yr** (0.0 to +1.2); **ci_low < 0** |
| W-71 MDD, B / T | B ≈ −51% to −55% (GFC); T 4–6 pp shallower → **the MDD clause passes** |
| W-22 | B ≈ −18% for the year, MDD ≈ −24%; T ≈ 2 pp better on both; the 2022 MDD reduction is **< 3 pp** (gold fell ~7–8% into the October trough) |
| 252-day block | CI ≥ 1.5× wider than at the auto block on both windows |
| ER 0.40% arm | Δ lower by ≈ 0.03%/yr; changes no category |
| Decades | the 1970s dominate the W-71 Δ; the 1980s and 1990s are clearly negative; the 2000s positive |
| **Outcome** | **REFUTED** (CI spans zero on both windows, with positive points), the MDD clause met |

## 14. Honest prior (before any data)

**P(H1 MET) ≈ 7%,** below the brief's 25%:
- The expected Δ is ~0.1–0.6%/yr against an MDE of ~1.0–1.4%/yr. Clearing needs roughly a 2-σ
  upper-tail realization on the 55-year window AND ci_low ≥ 0 on the 26-year window.
- **Both start dates in the brief favour gold.** 1971 precedes the post-Bretton-Woods re-pricing.
  2000 sits within ~15% of the 1999–2001 secular low. A pass would therefore be less informative than
  it looks, and a refutation stronger than it looks.
- **Erb-Harvey** (FAJ 2013; SSRN 5525138, 2025): gold's long-run real return is ≈ 0, and multi-year
  real returns from all-time highs have been low. Gold is at or near its ATH in 2025–26. **The
  historical Δ is a backward-looking upper bound on the forward case,** not a forecast.
- **Regime lens.** The brief's motivation, a positive stock-bond correlation in 2022, belongs to a
  BOND-holding book. This user's core is 1× equity in a Roth, so the relevant correlation is
  equity-gold, which is ≈ 0 on average and unreliable in liquidation crises (gold sold off in 2008-10
  and 2020-03).
- **A permanent leg's one structural virtue** is that it needs no regime detector, so it cannot be
  late. That virtue is real and shows up in MDD, not in log wealth.

P(MDD clause met) ≈ 85%. P(REFUTED) ≈ 88%. P(NOT MET, not refuted) ≈ 5%.

## 15. Scope exclusions

- The **forward twin** (core without gold on the `paper_trader` shadow pattern, evaluable 2028-09-30)
  is OUT (director ruling). `paper_trader/` is never touched. The verdict gives a proposal only.
- No other gold weight (5%, 15%, 20%), no timing rule, no 60/40 core, no bond leg.
- No `engines/`, `live_trader/`, `ops/`, `config/*`, `data/governor/*`, `backtester/` or `core/` edits.
  No registry write. No `BacktestController`. No network.

## 16. Computation performed before this draft (complete list)

1. Native index spans, row counts, monotonic/duplicate/NaN/non-positive checks, and calendar gaps of
   the equity and gold files; joint calendar overlap and as-of staleness per window (index operations
   only).
2. The md5s of the four pinned inputs.
3. `t311.load_substrate(["equity","gold"])` called once, comparing aligned gold LEVELS after
   2025-12-31 with the 2025-12-31 level (§3.4 item 2). The count of reindex-vs-as-of alignment
   differences (§3.4 item 3, index logic only).
4. The honest-N read (§10), plus MBL and MDE arithmetic on literature assumptions (§9, §10, §13).

**No arm, leg, blend, benchmark, differential or GLD return has been computed.**

## 17. Rulings requested before the run

1. **H1/refutation overlap:** the refutation takes precedence. H1 MET requires ci_low(W-00) ≥ 0 as well
   (§6).
2. **The MDD clause** is read on W-71, on the realized path, as a point value. The paired ΔMDD CI is
   reported but does not gate (§6).
3. **The ER:** primary IAUM 0.09% (the brief); T-311's 0.40% as a labelled sensitivity (§4, §7).
4. **The splice:** use T-306 as built (LBMA → COMEX front-month spot, not GLD → IAUM). The GLD
   2020–2025 validation halts on a gross mismatch (§3.2).
5. **Windows end 2025-12-31** (gold-bound) and are labelled 1971–2025 and 2000–2025.

## 18. Sequence

Draft (this commit) → **STOP: the director's acknowledgment and rulings** → build the harness and the
locks → smoke the first 12 months of W-71 and W-00 → full run → determinism ×2 (md5) → verdict
`docs/Audit/b10_gold_leg_verdict_2026-11-11.md` → full suite → commit on `research/gold-leg-b10`. No
push, no merge.

## Reproduce the pre-run census

```bash
# §3.1/3.3 native spans + gaps (index only)
python - <<'EOF'
import pandas as pd
S='data/research/substrate_multidecade/'
for leg in ['equity','gold']:
    s=pd.read_csv(S+f'{leg}_tr_daily.csv',parse_dates=[0],index_col=0).iloc[:,0]
    g=s[s.index>='1970-12-31'].index.to_series().diff().dt.days
    print(leg,s.index.min().date(),s.index.max().date(),len(s),'max gap in W-71',g.max())
EOF
md5 -q data/research/substrate_multidecade/{equity,gold}_tr_daily.csv data/processed/GLD_1d.csv scripts/deep_reverify_sleeve_t311.py
# §10 honest N, read-only
python -c "from core.measurement.mbl_gate import compute_n_effective_correlated as f; print(f(method='conservative'), f(method='equicorr'), f(method='onc'))"
```

---

## AMENDMENT 1 — 2026-11-11: DIRECTOR FREEZE + the five §17 rulings (BINDING; appended, frozen text above unedited)

**The director FROZE this prereg at `0cc3f56`.** All five §17 rulings were ACCEPTED as proposed. This
amendment is committed on its own, BEFORE any return is computed. The frontmatter `status:` line above
is part of the frozen text and is left as written. This section supersedes it as the record of the
freeze.

1. **The refutation takes precedence.** H1 MET also requires ci_low(W-00) ≥ 0. A W-71 ci_low > 0
   together with a W-00 ci_low < 0 reads as **REFUTED**. The §6 table stands as written.
2. **The MDD clause** is read on W-71, on the realized path, as a point value. The bootstrap interval
   of the MDD difference is reported but does not gate.
3. **The fee:** primary is gold 0.09%/yr (IAUM). The labelled sensitivity is 0.40%/yr (GLD), computed
   by T-311's own `robo_returns` with the 1e-12 parity check (§4).
4. **The splice:** T-306 as built (LBMA AM fix → COMEX front-month). The local GLD file checks
   2020-04-09 → 2025-12-31 and HALTS outside [−1.00, +0.20] %/yr gap, or below 0.95 21-day correlation
   (§3.2, G11).
5. **Labels:** **1971–2025** (W-71) and **2000–2025** (W-00), both ending 2025-12-31.

**The director's instruction on the T-311 finding:** the gold flat-tail forward-fill (§3.4 item 2) is
being logged in health_check by the director. The verdict carries it as a caveat on T-311's 3-asset arm.

**Operational decisions recorded before any data** (they alter NO frozen term):
- Harness: `scripts/b10_gold_leg.py`. Locks: `tests/test_b10_gold_leg_guards.py` (synthetic data).
- Outputs: a worktree-local real directory `data/b10_local/` (`b10_results.json`; smoke files
  `b10_smoke_*.json`). Nothing is written through `data/research`.
- **Determinism:** two full runs. The md5 of `b10_results.json` must match bit for bit. The JSON is
  written with sorted keys and carries no wall-clock timestamps.
- `bootstrap_distribution` takes `metric_fn = lambda x: float(np.sum(x))` and seed 0 for every call.
  `t311.paired` keeps its internal seed 0.
- **By-decade correlation** (§7 item 7): month-end-to-month-end simple returns of the two NET legs.
  These are the same daily net returns T uses, compounded within each calendar month. It uses the
  Pearson correlation.
- **Drawdown dates** (§7 item 4): peak = the last running-max date before the trough. Recovery = the
  first date after the trough when the curve regains the peak level, or `null` if it never does
  within the window.
- **The smoke** (the first 12 months of each window) calls the same pipeline on [base, end-of-first-year]
  with the G8 length floor lowered to the smoke's length. It checks only:
  - the rebalance census (11 rebalances);
  - turnover > 0;
  - the parity lock and the Σd identity;
  - that all guards pass.
  No smoke number is quoted.

N_trials consumed: **+1** (unchanged).
