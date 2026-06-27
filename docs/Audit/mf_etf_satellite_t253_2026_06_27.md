# Bought MF-ETF vs Our Trend Overlay as the Convex Satellite — VERDICT (T-253, 2026-06-27)

Reads against the pre-registration (`mf_etf_satellite_preregistration_t253`,
locked `92f8c16` BEFORE measurement). Branch `feature/mf-etf-satellite-t253`.
FREE, deterministic. Reproduce: `python -m scripts.mf_etf_satellite_t253`.

## VERDICT: NOT clearly better — USE OUR (free, full-history) trend overlay.
On the available 2019+ window, the bought MF-ETFs do NOT clear the
pre-registered "clearly-better convex satellite" bar. **Our trend sleeve
dominates them on every standalone risk-adjusted metric**; DBMF/KMLM buy
genuine 2022-style convexity our long/flat overlay lacks, but only in
*sustained* bears (not the fast 2020 crash), and they bleed carry/whipsaw the
rest of the time.

## Standalone satellites (2019-05+; KMLM 2020-12+)
| satellite | Sortino (ci_low) | MaxDD | CAGR | COVID-2020 ret | 2022 ret |
|---|---|---|---|---|---|
| **our trend sleeve** | **1.49 (0.65)** | **−7.5%** | **+9.0%** | −6% | −6% |
| DBMF | 0.64 (−0.21) | −23.7% | +5.9% | −6% | **+33%** |
| KMLM | 0.51 (−0.41) | −28.1% | +5.1% | n/a | **+49%** |

## The two things that actually matter
1. **The convexity is REAL but regime-specific.** DBMF/KMLM printed **+33% /
   +49% in the sustained 2022 bear** — genuine right-tail crisis-alpha our
   long/flat overlay structurally cannot produce (it goes to cash: −6% in
   2022). BUT in the **fast 2020 V-crash DBMF was −6% — caught long, NO
   convexity** (same as our sleeve; trend models need a sustained move to flip
   short). So the bought MF-ETF is a **sustained-bear hedge, not an
   all-crisis** hedge.
2. **Standalone, our overlay is far better risk-adjusted.** Sortino 1.49
   (ci_low **+0.65**) vs DBMF 0.64 (ci_low **−0.21**) / KMLM 0.51 (−0.41);
   MaxDD −7.5% vs **−24% / −28%**; higher CAGR. DBMF/KMLM carry-bleed and
   whipsaw hard in the calm/reversal years (2019-21, 2023-24) → their own deep
   drawdowns. Our long/flat overlay is the smoother, higher-Sortino sleeve.

## 80/20 barbell (AGG safe core + 20% satellite, DBMF window)
| barbell | Sortino (ci_low) | MaxDD | 2022 ret |
|---|---|---|---|
| AGG80 + our sleeve 20 | **0.29 (−0.60)** | −18.1% | −14% |
| AGG80 + DBMF 20 | 0.20 (−0.63) | **−13.9%** | −8% |
| AGG80 + KMLM 20 | −0.41 (−1.46) | −11.7% | −5% |
| AGG core only | −0.12 (−1.04) | −22.3% | −16% |

In the barbell the MF-ETF's 2022 convexity **does** cut the 2022 drawdown more
(−8%/−5% vs our sleeve's −14%, vs the AGG core's −16% — bonds crashed in 2022),
but the **overall Sortino is worse** (DBMF 0.20 < our sleeve 0.29) and all
barbells carry negative ci_low on this short, bond-hostile window.

## Decision rule → result
"Clearly better" required (a) materially-positive crisis returns in **BOTH**
2020 AND 2022, AND (b) better barbell Sortino AND shallower MaxDD. DBMF fails
(a) — flat-to-negative in the fast 2020 crash — and is split on (b) (better
MaxDD, worse Sortino). → **NOT clearly better → use OUR trend overlay.**

## Honest read + recommendation
- **For the convex-satellite role generally: use our FREE trend overlay** —
  better Sortino, far shallower drawdown, full-history-validated (T-236), no
  carry bleed, no expense ratio.
- **DBMF/KMLM earn a place ONLY as a narrow, specific tail-hedge** for a
  *sustained inflationary bear* (2022-type), where their long/short convexity
  (+33%/+49%) genuinely diversifies a bond-heavy core that our long/flat
  overlay cannot. They are a tail satellite that bleeds in calm — confirming
  the task's framing and consistent with T-170 (the bought-MF sleeve as a
  crisis floor, always-on, not a return engine).
- **DATA CAVEAT (load-bearing):** this rests on a **2019+ window** that misses
  the deep crises (dotcom/GFC). The MF deep-crisis defense is **literature-
  based** (AQR; T-170). If a 2008-style *slow grinding* deep bear recurs,
  DBMF's convexity would likely show more than it did in the fast 2020 crash —
  but on the available evidence our overlay is the better satellite, and a
  bought product is a real-money / propose-first decision (`[NN-AI-GATE]`-adjacent).

## Scope
FREE probe, no build, no canon change, no integration. N_trials: the satellite
set + the 80/20 barbell are pre-registered (no sweep) → counts as 1 structural
comparison.
