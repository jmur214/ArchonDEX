---
task_id: T-2026-07-27-312
title: DEEP re-verify of the T-298 offense config — does the directional edge become CI-significant on ~58yr?
date: 2026-07-27
author: Agent D (fair-harness lane)
type: PRE-REGISTRATION DRAFT (draft → director freeze → run; N_trials += 1)
status: DRAFT — NOT RUN. Awaiting freeze.
---

# T-312 (DRAFT) — deep re-verify of the offense config

`[NN-SUBSTRATE-REVERIFY]` demotes the offense arc. T-298 asymmetric damping cleared the Roth buy-hold-SPY bar
at **every** slippage grid point (0/1.55/5/10 bps) with crash exit-lag ≡ 0 — but held **EARNED-BUT-DIRECTIONAL**:
its paired Δwealth CI **straddled zero** (vs buy-hold SPY [−15.98, +22.29], vs undamped V1 [−7.51, +9.11]) on a
window with **only 4 crises** (dotcom, GFC, COVID, 2022). The deep substrate is the honest test of exactly that
CI: does the exit-lag-0 tail protection compound to a **CI-significant** Δwealth over ~10 crises, or does the
path-shift-to-~1.1× advantage stay directional? This is the offense program's make-or-break, and it feeds the
still-open account-2 charter question (undamped-2× vs whipsaw-free ~1.1×).

## Substrate (D-B, gold in-spec) — `data/research/substrate_multidecade/`
Joint 3-asset span **1968-01-03 → 2025-12-31 (~58.3 yr)**, gold-bound floor (LBMA gold reaches 1968). Legs
(all TR, T-306, per-splice provenance + the T-256 basis battery): equity = FF broad-market TR spliced to SPY-TR
at 1993-02 (the "SPY-equivalent"); bond = DGS10 synthetic (reproduces the frozen T-255 bond exactly on the
overlap, |Δ|=0); gold = LBMA fix spliced to gold_gcf (immaterial to a 42-210d sleeve — corr 0.97 at 21d);
cash = the short rate.

**Interpretation flag for the freeze (please confirm):** the T-298 config that cleared the bar is the T-284
**PRIMARY — equity-only** (100% SPY-equivalent at up to 2× when its own trend is on; the 3-asset-sleeve variant
was the SECONDARY, REFUTED by T-285). So this re-verify is **equity-only**: it needs `equity_tr` + `cash` only,
both of which reach **1926**. I propose running on the **D-B window (1968-2025, ~58yr)** so it shares B/T-311's
substrate exactly (shared honest-N), and reporting an **optional ~99yr extension (1926-2026, equity+cash only)**
that adds 1929 + the Great Depression + 1937 + WWII — the deepest honest test an equity-only strategy admits.
If instead you want the 3-asset-sleeve-with-levered-equity-leg variant, name it and I add it as a second arm
(but that is the T-285-refuted structure, not what cleared the bar). `core.calendar_guard.assert_no_calendar_holes`
asserted on the buy-hold benchmark; `cash` reindexed ONTO the equity calendar (`reindex_onto`, the T-297 rule).

## The arm (FROZEN on freeze) — faithful to the T-298 config that cleared the bar
- **T-298 asymmetric-damped:** 100% equity_tr at exposure `e = min(2·ensemble_fraction, 2)` when the {2,5,10}mo
  ensemble trend (on `equity_tr`) is on, **damp re-entry (band ⅔ on e2) / NEVER damp de-risking** (exit-lag ≡ 0,
  the invariant `e_held ≤ e_target` asserted), cash (short rate) when off. 2× via the SSO-synthetic
  (`2·equity_gross − borrow − 0.89% ER`, borrow = `cash + 60 bps`).
- **Baselines:** (1) **buy-hold equity_tr** — THE bar (the SPY-equivalent); (2) **undamped 2×** — the reference.
- **Costs are now DATA, not assumptions (`[NN-SUBSTRATE-REVERIFY]`):** charge E's **measured 2.2 bps** on the
  SSO leg's turnover (E's settled real number; note 2.2 > the 1.55 bps breakeven ⇒ the *undamped* config loses —
  irrelevant to T-298, which cleared at every grid point), and the measured **0.51 bps** on the 1× equity leg.
- **Synthetic caveat (carried):** SSO (the ETF) postdates 2006, so the deep SSO-synthetic is basis-checkable
  only on the 2006-2026 overlap (T-282: +0.23%/yr, defensible). The construction is extended, not re-validated,
  pre-1968 — stated. The **1970s-80s high-rate regime is the point**: borrow = cash+60bps was ~15%+ in 1980-81,
  so the leverage genuinely bleeds there — an adversarial, honest test, not a flattering one.

## The named deep crises the 2000-2026 window NEVER saw (why ~58yr is the honest test)
2000-2026 had 4 crises. The D-B window adds ~6 the offense config has **never** faced:
**1973-74 stagflation** (−48% equity + *sustained high rates* — bonds and equity fall together; a levered-equity
strategy pays a punishing borrow AND may whipsaw a grinding bear), **1980-82 Volcker** double-dip, **1987 Black
Monday** (a *one-day* −22% crash — the regime that may actually FAVOR the fast-exit design, or may gap through it
before the daily gate can act), 1970 recession, 1990, 1998 LTCM. Report each window's in-window MaxDD + return
for the arm / bar / undamped, and call out 1973-74 and 1987 explicitly as the two regimes with opposite priors.

## Gate (FROZEN)
- **PRIMARY (the whole question): paired Δwealth 95% block-bootstrap CI vs buy-hold equity must EXCLUDE ZERO**
  for a "significant" verdict — the exact bar the T-298 directional caveat flagged as unmet. Also report the
  paired CI vs undamped 2×.
- **Scorecard (reported honestly, NOT gating):** terminal wealth, CAGR, MaxDD, **mean exposure** (it is a ~1.1×
  strategy on 2000-2026 — say what it is here, deep leverage-cost may push it lower), Sortino/Calmar.
- **MBL/DSR (`[NN-MBL]`):** T_required ≈ 2·ln(75)/0.598² ≈ 24.1 yr; the ~58yr window clears DSR with ~2.4×
  margin — state the DSR margin at the offense config's realized SR, honest-N.

## Honest prior — MEDIUM-LOW that it clears CI-significance
The 2000-2026 straddle was **not close to the boundary**, and adding crises cuts BOTH ways: **1987** (one-day
crash) plausibly favors the exit-lag-0 design; **1973-74** (sustained-high-rate stagflation) plausibly hurts it
(expensive borrow on the leverage + a grinding bear the trend whipsaws). Net: genuinely uncertain, leaning
**stays directional**. Either verdict is decisive: **significant → a real-money offense candidate; still-
straddling / flips → the honest ceiling is named and the offense program stops reaching** (and the account-2
charter resolves toward the whipsaw-free ~1.1× being the actual prize, not 2×).

## Sequencing + N
Runs **AFTER B/T-311** (the defensive sleeve gates real money first) on the SAME D-B substrate for shared
honest-N. N_trials += 1 (this is the pre-registered offense re-verify demanded by `[NN-SUBSTRATE-REVERIFY]`;
the 2000-2026 T-298 verdict demotes to "DEFENSIBLE (prior substrate); superseded by this run").

---
**DRAFT — NOT RUN.** Awaiting director freeze (and confirmation of the equity-only interpretation + the D-B vs
~99yr window choice). On freeze this runs on the T-298 harness extended to the deep substrate; any change after
the freeze line = a new pre-registration.
