---
task_id: T-2026-06-10-129
title: The FAIR BAB re-test — deep 2008-inclusive window (the honest alpha referendum)
date: 2026-06-10
author: Agent D (alpha/edge lane)
outcome: BAB does NOT clear t>2 even on the fairest window. Full 26-yr (2000-2025,
  incl. 2008) long-short α=+1.31%, t=+0.19, ci[−1.70,+2.09], p(α>0)=0.58 — a coin
  flip. The literature's pre-2014 α does NOT exist on our substrate (2000-2013
  t=+0.04; best segment 2008-2013 t=+0.78). FF5 spans BAB harder on the deep
  window (CMA 1.27, RMW 0.71). Survivor-only substrate → these are UPPER bounds.
  REFERENDUM: the substrate-empty hypothesis is now EVIDENCED; the
  architecture/mission fork is earned.
status: CURRENT
reproduce: |
  PYTHONHASHSEED=0 python -m scripts.analyze_bab_deep_t129   (determinism PASS, md5 f6ac0e27…)
---

# T-129 — BAB deep re-test: the referendum, done right

## TL;DR — the fair test confirms the miss; the fork is earned

T-123 found BAB ~0 α on 2014-2025 but flagged the test as unfair (documented
low-beta headwind + large-cap-only). This re-test removes the unfairness: the
**full 26-yr window 2000-2025 including the 2008 crisis**, on the broadest
universe the substrate supports (246-673 names per rebalance, median 519),
identical construction, pre-registered windows and interpretation.

**Headline (survivor-only substrate → α is an UPPER bound):**

| stream | window | α ann | α t | 95% CI | p(α>0) | clears t>2 | Sharpe (ci_low) |
|---|---|---|---|---|---|---|---|
| **BAB long-short β-neutral** | **2000-2025 (26y)** | **+1.31%** | **+0.19** | [−1.70, +2.09] | 0.58 | **NO** | +0.37 (+0.01) |
| BAB long-only low-beta | 2000-2025 | −1.29% | −0.90 | [−2.94, +0.75] | 0.14 | NO | +0.60 (+0.23) |

**The pre-registered sub-period split — the literature's pre-2014 α does NOT
show up on our substrate:**

| sub-period | α ann | α t | 95% CI |
|---|---|---|---|
| 2000-2007 | −4.35% | −0.22 | [−2.26, +1.68] |
| **2008-2013** (BAB's literature heyday) | +3.49% | **+0.78** | [−1.13, +2.71] |
| 2014-2025 (headwind, = T-123) | +0.47% | +0.08 | [−1.79, +1.97] |
| pre-headwind aggregate 2000-2013 | +0.44% | +0.04 | [−1.76, +2.05] |

Every segment is a statistical coin flip. The crisis era is directionally
positive (+3.49%) — consistent with the literature's *sign* — but at t=+0.78
it is noise, and the aggregate pre-headwind window is t=+0.04.

---

## 1. Why the test is now fair (and what still isn't perfect)

**Fixed vs T-123:** window includes 2008 + the dot-com unwind tail (2000-2002);
universe breadth ~5x at the median (519 vs T-123's effective ~100-200 dense
names); 6539 daily obs vs 2766; 313 monthly rebalances.

**Still imperfect, stated plainly:**
- **Survivor-only (T-092):** dead names are absent. Long-leg α is an UPPER
  bound; the short-high-beta leg is *understated* (the best shorts —
  bankruptcies — are missing). Net direction ambiguous but the headline is
  already ~0, and an upper-bound ~0 is the damning direction.
- Still S&P-flavored large/mid caps. Frazzini-Pedersen's strongest BAB effects
  load on micro-caps + international + 1926-era data — instruments we do not
  and will not trade. The deployment-relevant statement is about OUR universe.

**Local run (not cloud):** the deep substrate is on local disk
(`data/processed/`, the T-082b extension; 249 names with data ≤1999, 489 ≤2008)
and the analysis is pandas-only — no backtest engine, no image. Cloud would
have added image-pinning overhead for zero compute benefit. Construction is
bit-deterministic (seed 0, PASS ×2).

## 2. Mechanism: FF5 spans BAB *harder* on the deep window

Long-short loadings, 26-yr: MktRF 0.61, SMB −0.47, HML −0.20, **RMW 0.71, CMA
1.27**, Mom 0.24 (R² 0.14). On 2014-2025 (T-123) the span was CMA 0.66/RMW
0.29 — on the deep window it *doubles*. On our substrate, "low-beta" IS
conservative-investment + profitability exposure; once FF5+Mom takes its
share, the residual is statistically nothing. The brief's premise ("FF doesn't
span the low-beta anomaly") holds in FP's broad/micro-cap universe; it does
NOT hold on an S&P-survivor large/mid-cap panel.

Book correlation: +0.10 (overlap 2014+ only, vs the 0dcae34c 12-yr book) —
orthogonal as a return stream, but with no α to contribute.

## 3. THE REFERENDUM VERDICT (per the pre-registration)

> *~0 α even with 2008 → the substrate-empty hypothesis is now EVIDENCED
> (friendliest factor, fairest window, still nothing).*

That is the result. Stated plainly: **the equity-cross-sectional,
S&P-survivor, large/mid-cap substrate this system trades does not contain
accessible factor-orthogonal alpha at the t>2 standard.** The evidence chain:

| task | what was tested | result |
|---|---|---|
| T-117 | all 13 dense existing edges | factor-NEGATIVE (closet beta) |
| T-122 | VRP (timing) | α≈0; equity proxy collapses into MktRF |
| T-123 | BAB, 2014-2025 | α≈0 (flagged unfair) |
| **T-129** | **BAB, 26-yr incl. 2008, broad universe, upper-bound bias** | **α≈0 (t +0.19)** |

The architecture/mission fork is earned. The honest options (ranked by my
read, decision is the user's):
1. **Accept the system as a risk-management + falsification platform.** Its
   defensive/MDD properties and its measurement discipline are real and
   demonstrated; its equity-cross-sectional alpha generation is not. This is a
   legitimate end-state and costs nothing.
2. **Non-equity instruments** (options/variance for true VRP, futures trend) —
   the premia there are structurally outside FF5 span (T-122 §4). Real cost:
   new data, new sleeve architecture, new risk surface. User-gated.
3. **Universe expansion (micro-cap/international)** — where the literature's
   BAB/factor α actually lives. Costs data (Norgate etc.) and brings
   capacity/liquidity constraints at retail size.

What is NOT supported by the evidence: continuing to implement equity
cross-sectional literature edges on the current substrate and expecting a
different outcome. T-129 closes that loop.

## 4. Files

- `scripts/analyze_bab_deep_t129.py` (NEW — pre-registered deep re-test; T-123
  construction + coverage guard)
- `data/measurements/bab_deep_retest_t129/bab_deep_analysis.json` (gitignored)
- This audit: `docs/Audit/bab_deep_retest_t129_2026_06_10.md`
- Builds on: T-123 (`bab_literature_edge_t123_2026_06_06.md`), T-122, T-117

## 5. NOT included (hard boundaries honored)

- No promotion (BAB stays candidate), no edges.yml/edge_weights/governor edits.
- No TASK_LEDGER write (T-114 — proposed row in outbox). No cockpit/dashboard edits.
- No Ken-French/AQR external BAB-factor download (not in cache; would be a new
  network dependency — noted as not-cheap, skipped; our FF5+Mom cache is the
  cross-check basis). Branch only; director merges.
