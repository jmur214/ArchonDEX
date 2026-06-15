---
name: alpha-frontier-lane-closed-2026-06-15
description: The T-132 alpha-frontier categories were tested+closed (T-135→T-150) within 48h of the map; only VRP/intraday-execution remain genuinely open; honest base rate for new-alpha ~0
metadata:
  type: project
---

The cross-sectional new-alpha lane is EVIDENCE-CLOSED as a class, not just
"untested categories pending." The T-132 frontier map (2026-06-10) listed 16
untested categories, but the lane then TESTED almost all of them in 48 hours
and closed them. Anyone quoting "T-132 mapped untested categories" as if they
are still open is reading a stale snapshot — follow the supersession chain.

**Why:** at honest-N (~260 trials, MBL bar rises with every test) the EV of
another cross-sectional test on the S&P-survivor daily substrate is ~0, and
each test raises the MBL bar for everything else. The structural killers
(FF5-span circularity on this universe; the policy.py inverse-vol normalizer
that algebraically cancels any uniform/timing signal — fresh_view_2026_06_11)
are not edge-specific; they cap the whole lane.

**How to apply:** before proposing any new cross-sectional edge candidate,
state which of these closed cells it differs from. If it doesn't differ in
DATA / RESOLUTION / FUNCTIONAL-FORM / INSTRUMENT / UNIVERSE from a closed cell,
do not spend an N-trial on it. The closed record (all family-wise clean or
unharvestable, audits dated 2026-06-10/11):

- Overnight/intraday composition (T-135): LPS structure REPLICATES — overnight
  component is the project's FIRST strict-gate factor-α (α +13.9%/yr, t +5.69,
  ci_low clears t>2) — but intraday side nets total tradeable α to −1.05%
  (t −0.41), and direct overnight harvest is cost-dead ~4-5× at retail fees.
  Real alpha, structurally unharvestable. CLOSED definitively.
- 8-K item-type drift (T-137): 160k events, 24-test StepM family, survivors
  NONE (max |t| 1.93 < crit 2.95). Signs literature-consistent = credible null.
  CLOSED. Directional/text version untested-by-construction (prompt-injection
  gated; needs filing TEXT — item codes carry no sign).
- Form-4 insider clusters (T-144): 39k buys, dual-universe, survivors NONE
  (max |t| 0.63). Verdicts agree across universes. insider_cluster_v1 edge
  retirement-PROPOSED (never beat its feed). CLOSED.
- 13F crowding (T-145): 476k ticker-quarters, dual-universe, survivors NONE
  (max |t| 0.15). With it the STRUCTURED-EVENT LANE CLOSES AS A CLASS (8-K +
  Form-4 + 13F = 3 mechanisms, 3 data sources, all clean).
- Metalearner / non-linear combination (T-149): CPCV horse-race, ridge BEATS
  GBM OOS (IC +0.0064 vs +0.0039; SPA p=0.595, ci spans 0). Kill bar failed
  both prongs. Non-linear combination joins T-117's linear closure. The
  T-132 weak-prior GO (1-of-28 selection-uncorrected H-stat) did NOT
  generalize, exactly as its multiplicity caveat warned. CLOSED.

**Genuinely-open as of 2026-06-15 (only two):**
1. Options-class VRP (sell index puts / short variance when IV≫RV) — the REAL
   premium T-122's equity proxy couldn't reach. FORK-GATED: needs options data
   + a non-XS gross-exposure sleeve + a new Engine-B risk surface (propose-
   first). It is the ONLY currently-fundable cross-sectional/overlay alpha
   candidate per both forward_plan and fresh_view. NOT an XS edge — it's a
   short-vol overlay/sleeve, so it dodges the policy.py washout but inherits a
   left-tail risk that must be bounded BEFORE any backtest.
2. Intraday EXECUTION-gated strategies (GHLZ first-half→last-half SPY) — gated
   on an intraday execution path, not data. Deferred (latency-bound at retail).

**The honest base rate:** the artisanal lane went 0/11 on factor-α t>2, then
the frontier lane went ~0/5 on the materially-different categories (1 real-but-
unharvestable + 4 clean nulls). Combined cross-sectional record is ~0/16. The
prior for the NEXT cross-sectional test clearing is empirically near zero on
this substrate. The category split is strongly predictive: RISK/REGIME/
FORECASTING findings survive rigor (HMM AUC 0.914, Yang-Zhang vol > production
EWMA per T-150); cross-sectional RETURN alphas decay monotonically with rigor.

**The one positive screen of the whole arc (T-150):** Yang-Zhang range-vol
BEATS production EWMA(0.94) at next-day vol forecasting (SPA p=0.013-0.024,
ci_low>0 both targets) + EWMA has a zero-variance-collapse failure mode that
over-levers a vol-target engine. This is a RISK-engine input (Engine B,
propose-first), NOT an alpha edge — it confirms the value lives in the risk
lane, not the return-alpha lane.
