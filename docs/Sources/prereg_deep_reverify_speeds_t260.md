---
task_id: T-2026-07-27-260-deep
title: Pre-registration — DEEP re-verify the multi-speed ensemble selection (T-260) on the 58-64yr substrate
date: 2026-07-27
worker: Agent B
branch: feature/deep-reverify-speeds-t260
status: DRAFT — awaiting director FREEZE before any run. N_trials += 1 (one family, jointly reported).
---

# T-260-deep — does the ensemble-speed choice survive 64 years?

## What is being re-verified (the frozen 2000-2026 claims, verbatim)
`[NN-SUBSTRATE-REVERIFY]`, second in the order (T-255 ✓ → **T-260** → T-298). The
original T-260 verdict on the shallow window made three claims:
1. **Spec-selection risk is material:** Sortino range **0.401** across 4-10mo single
   specs; **"100-350 bps/yr of the edge is spec-selection."**
2. **The {2,5,10}mo ensemble vs single 5mo: ΔSortino 95% CI [−0.023, +0.207]** —
   DIRECTIONAL, **NOT CI-significant** (lower bound just below zero).
3. **Verdict:** adopt the ensemble as a **ROBUSTNESS** choice, **NOT** on a claim of
   significant lift.

The deep window is the first that can honestly resolve claim 2 (a near-miss CI is
exactly what more independent data should settle) and stress-test claim 1.

## THE HARD PRE-COMMITMENT (the anti-overfit control that matters here)
**NO RE-SELECTION. The deployed `{42,105,210}` spec is FROZEN and will not be changed
by this run's results, whatever they show.** The dispersion scan below is
**CHARACTERIZATION ONLY** — it quantifies how much of the edge is spec-luck; it is
NOT a menu to pick from. If some other speed triple scores higher on the deep window,
that is **reported as spec-selection risk**, not adopted. Re-selecting speeds using
64 years of now-seen data would be precisely the free-parameter fit that killed
MetaLearner/HRP/concentration — and it would contaminate T-314's baseline, which is
this exact frozen spec.

This pre-commitment is the whole reason the scan is safe to run at all.

## Substrate + conventions (identical to T-311 — reuse, do not re-derive)
- **PRIMARY:** D-A 2-asset (equity+bond), 1962→2026 (~64yr). **SECONDARY:** D-B
  3-asset, 1968→2026 (~58yr).
- T-255 fair conventions verbatim (ER when long, 1.5bps/side, flat leg @ short rate),
  `calendar_guard.reindex_onto` onto the equity calendar, causal `.shift(1)` signals
  (T-273). Same code path as `scripts/deep_reverify_sleeve_t311.py`.

## Arms
- **A (the deployed, frozen):** ensemble `{42, 105, 210}` = {2,5,10}mo.
- **B (the original comparator):** single **105d (5mo)** — the head-to-head the
  shallow-window CI was computed on.
- **C (constituents):** singles 42d, 210d — does the ensemble beat *each* leg?
- **D (dispersion scan, CHARACTERIZATION ONLY):** single-speed lookbacks over a
  **pre-registered grid: 21, 42, 63, 84, 105, 126, 147, 168, 189, 210, 252 days**
  (≈1-12mo, fixed here before the run). Reports the Sortino/MaxDD/wealth **range**
  and the deployed ensemble's **percentile within it**.

## Gates (FROZEN)
Paired **A − B** on aligned daily returns, 21-day block-bootstrap, 1000 iter, seed 0:
- **PRIMARY GATE — ΔSortino(ensemble − single 5mo): the shallow window gave
  [−0.023, +0.207] (not significant). The deep window RESOLVES it:**
  - `ci_low > 0` ⇒ **claim 2 UPGRADES** — the ensemble lift is real and significant;
    the "robustness choice, not a lift" caveat is retired.
  - `ci_low ≤ 0` ⇒ **claim 2 CONFIRMED AS-IS** — still a robustness choice, now
    settled at MBL-cleared N rather than pending. **This is a real answer, not a
    failure** (and it is the honest prior below).
  - `ci_high < 0` ⇒ **claim 2 REFUTED** — the ensemble is a *drag* vs the single
    5mo on the deep window; report loudly and escalate (it would put the deployed
    spec in question and must NOT be quietly averaged away).
- **Secondary:** ΔSortino vs each constituent (42d, 210d); ΔMaxDD and Δcompound-rate
  (annualized log-wealth — the T-311 well-behaved wealth statistic, NOT raw
  Δterminal-wealth, which is degenerate over 60+yr compounding).
- **Dispersion (claim 1):** Sortino range across the grid, deep vs the shallow 0.401,
  and the bps/yr spread. Does more data SHRINK spec-selection risk or expose it as
  larger than the shallow window suggested?

**MBL/DSR:** at ~64yr and N≈77 (after this trial) the required Sharpe ≈ 0.37 —
cleared by the sleeve's ~1.5. State the honest-N and margin.

## Scope exclusions (stated so they cannot creep in)
- **NO rate-regime slicing.** T-311's cash-rate regime split is a post-hoc finding;
  conditioning this run on it would import that contamination. It belongs to family
  experiment #2 (forward/out-of-time), not here.
- **NO speed re-selection** (see the pre-commitment).
- **NO new ensemble shapes** (weighting schemes, >3 legs) — that would be a search.

## Honest prior (BEFORE the run)
- **Claim 2 (ensemble lift becomes significant): ~35%.** The shallow CI was a near
  miss and 2.5× more data helps — but the ensemble's *mechanism* is variance
  reduction across specs, which raises the floor more than the mean. I expect it to
  remain a robustness win, not a significant-lift win.
- **Claim 1 (dispersion): expect it to PERSIST or WIDEN.** The deep window adds the
  1970s-80s, where trend-following's speed sensitivity was historically large.
- If the deep window shows the deployed spec is mid-pack, that is the honest and
  *expected* outcome of an unbiased selection — and it is exactly what the
  no-re-selection pre-commitment exists to let us report calmly.

## Sequence / N
Draft → **director FREEZE** → run → results + verdict appended here → outbox →
**then T-314 (#1)**, whose frozen baseline is this same unchanged spec.
**N_trials += 1** (one family: arms A-D jointly reported; no selection performed).

## DIRECTOR FREEZE — 2026-07-27 (as drafted, no amendments; BINDING)
Frozen exactly as written. The three load-bearing terms are quoted here so they cannot drift:
(1) **NO re-selection** — {42,105,210} does not change regardless of what the grid shows; a higher-scoring
triple is REPORTED as spec-selection risk, never adopted (protects both the deployed spec and T-314's
baseline, which is this same frozen spec); (2) **all three outcomes pre-named**, including the bad one — an
ensemble-drag result is escalated loudly with the deployed spec in question, never averaged away;
(3) **rate-regime slicing excluded by name** (post-hoc; belongs to family #2, forward-only). Honest prior
~35% as stated. Run → then T-314 (#1). N_trials += 1 at run.
