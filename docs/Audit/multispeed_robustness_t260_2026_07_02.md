---
task_id: T-2026-07-02-260
title: Multi-speed ensemble + robustness scans (lookback dispersion + tranching) on the fair sleeve
date: 2026-07-02
author: Agent D
type: robustness measurements (0 hypotheses) + ONE pre-registered ensemble trial (N_trials += 1)
status: PRE-REGISTERED (results below the line)
---

# T-260 — multi-speed ensemble + robustness scans

## Robustness scans (0 hypotheses — measurements, no gate)
1. **Lookback dispersion:** the fair sleeve at lookbacks {3,4,5,6,7,10}mo — report the DISPERSION of
   Sortino / MaxDD / terminal wealth. Question: is the 5-mo headline partly spec-luck? (Published
   single-spec magnitude: 100-350 bps/yr of the edge is spec-selection.)
2. **Tranching / timing-luck:** a monthly-rebalanced variant of the sleeve with the signal evaluated
   on trading-day-offset k of each month, k = 0..20 — report the timing-luck band (Sortino/MaxDD/wealth).

## The multi-speed ensemble arm (ONE pre-registered trial — N_trials += 1)
**Pre-registered speed set (fixed BEFORE looking at results):** each asset's exposure = the MEAN of
its binary long/flat signals at **{2, 5, 10} months** (≈ {42, 105, 210} trading days) → fractional
exposure ∈ {0, 1/3, 2/3, 1}. **Justification (barbell, per the audit / ReSolve 1,226-variant
evidence):** a fast leg (2mo — the COVID-style fast-crash response our 5mo lacks) + our validated
center (5mo) + a slow leg (10mo — the classic ~12-1 trend, stability); this spans the trend-speed
spectrum. (The literature notes the middle band is the most redundant, so the payoff hypothesis is
robustness/whipsaw reduction from the fast+slow legs, NOT the center.) Flat leg earns the short rate,
ER + 1.5bps both sides — the SAME fair harness as T-255.

**Gates:** paired-difference block-bootstrap ΔSortino and ΔMaxDD ci vs the single-speed (5mo) FAIR
sleeve. **Named windows:** COVID-2020 (2020-02→2020-03 — where the FAST leg should pay) and 2022.
**Expectation (pre-registered):** robustness/whipsaw improvement (shallower COVID MaxDD, lower
dispersion) MORE than a mean-return lift — report whatever it is.

---
## RESULTS (fair T-255 harness, common 2000-08→2026 window — all 3 assets present)

_Note: the sleeve is run on the same common substrate as the T-255 headline (gold GC=F starts 2000-08),
so single-5mo here (Sortino 1.126 / MaxDD −11.8% / $10k→36,631) lines up with the T-255 fair headline
(1.163 / −11.8% / 39,931); small residual gap = sleeve-only end-alignment. An earlier draft ran on a
SPY-only pre-2000 tail at a degenerate 1/3-weight — discarded; these are the trustworthy numbers._

### (1) Lookback dispersion — MATERIAL; the defensive property is robust, the return is spec-sensitive
| lookback | Sortino | ci_low | MaxDD | CAGR | $10k→ |
|---|---|---|---|---|---|
| 3mo | 0.930 | 0.407 | −16.3% | 4.2% | 27,957 |
| 4mo | 1.178 | 0.671 | −12.0% | 5.6% | 38,770 |
| **5mo (headline)** | **1.126** | **0.644** | **−11.8%** | **5.3%** | **36,631** |
| 6mo | 1.126 | 0.617 | −12.2% | 5.3% | 36,405 |
| 7mo | 1.229 | 0.693 | −11.2% | 5.8% | 40,394 |
| 10mo | 1.331 | 0.823 | −9.6% | 6.5% | 46,401 |

**Dispersion:** Sortino range **0.401** (0.930–1.331); MaxDD [−16.3%,−9.6%]; wealth ~1.66× ($28.0k–$46.4k).
So the single-spec choice matters (the published 100-350bps/yr spec-luck is real here). BUT two honest
mitigants: (a) the **5mo headline is MIDDLE-of-pack, not cherry-picked** (10mo is the best spec, 3mo the
worst — we did not select the top; the monotone edge favoring slower lookbacks is itself a finding);
(b) the **DEFENSIVE property is robust** — every 4-10mo spec has MaxDD −9.6 to −12.2% and Sortino ≥1.13;
only the 3mo (whipsaw) degrades to −16.3%. Return varies more than risk across the speed choice.

### (2) Tranching / timing-luck — MODEST (not fragile)
5mo, monthly-rebal at day-offset k=0..20 (sampled): Sortino band **[1.156, 1.217] (range 0.061)**, MaxDD
[−15.4%, −12.5%]. Timing luck is small (0.061 « the 0.401 lookback dispersion). The monthly-rebal variant
runs slightly deeper MaxDD (−12.5 to −15.4%) than the daily sleeve (−11.8%) — the rebal lag — but the band
is tight → the sleeve is NOT timing-luck-fragile.

### (3) Multi-speed {2,5,10}mo ensemble vs single 5mo — DIRECTIONAL improvement, NOT CI-significant
| | Sortino | ci_low | MaxDD | CAGR | $10k→ |
|---|---|---|---|---|---|
| single 5mo (fair base) | 1.126 | 0.644 | −11.8% | 5.3% | 36,631 |
| **multi {2,5,10}mo** | **1.257** | **0.757** | −11.1% | 5.5% | 38,250 |

- **Paired Δ(ensemble − single): ΔSortino 95% CI [−0.023, +0.207]** — the lower bound is (just) BELOW
  zero → the improvement is DIRECTIONAL, **NOT CI-significant** (`[NN-SHARPE-CI]`). Standalone ci_low
  DOES rise 0.644→**0.757** (a higher worst-case floor). **ΔMaxDD 95% CI [−1.5%,+6.3%]** straddles zero.
  CAGR ≈ flat (5.3→5.5%).
- **Named windows (in-window MaxDD):** 2022 single −5.4% → ensemble **−4.5%** (better — the slow leg
  helped the grinding bear); COVID-2020 single −4.7% → ensemble −5.0% (slightly WORSE — the fast 2mo leg
  did NOT pay here, against the pre-registered expectation).

### Verdict — the ensemble is a mild robustness win (directional, not significant); optional paper-spec
- **The dispersion scan confirms real spec-sensitivity** (Sortino 0.401 range, wealth ~1.66×) — but the
  5mo is a fair middle-of-pack pick, not cherry-picked, and the DEFENSIVE property (shallow MaxDD) is
  robust across all 4-10mo specs. The ensemble is the principled fix for spec-selection: averaging
  {2,5,10}mo gives Sortino **1.257 (standalone ci_low 0.757)** — near the top of the single-spec range
  WITHOUT choosing a lookback, and it raises the worst-case floor.
- **As pre-registered, the payoff is ROBUSTNESS > mean lift** — and it is HONESTLY qualified: the paired
  ΔSortino over single-5mo is directional (+0.13 point) but **NOT CI-significant** (CI [−0.023,+0.207]
  straddles zero), exactly consistent with T-255's finding that the sleeve's edges are directional-not-
  significant. MaxDD/CAGR ≈ unchanged; the pre-registered COVID "fast-leg" hypothesis did NOT hold (COVID
  slightly worse), the 2022 slow-bear improved. **Recommendation:** the {2,5,10}mo ensemble is a sound,
  low-cost hardening of the paper-sleeve spec (removes lookback-selection fragility, higher ci_low floor)
  — but adopt it as a ROBUSTNESS choice, NOT on a claim of significant lift. A director/user decision, not
  an autonomous spec change to the T-238 paper machine. N_trials += 1.

