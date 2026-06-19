---
task_id: T-2026-06-18-212 (Part 2)
title: PRE-REGISTRATION — vol-target A/B (beta-exposure scaling, guard-ON)
date: 2026-06-18
worker: Agent B
branch: feature/voltarget-build-t212
status: PRE-REGISTERED (bound BEFORE the run) / PROPOSE-FIRST (Engine B)
---

# Vol-target A/B — pre-registration (T-212 Part 2)

**This document is bound BEFORE the campaign launches** (the MBL/DSR
discipline: hypothesis + threshold + N_trials fixed before seeing results).
Part 1 (the sigma-floor HARD precondition) is PROVEN and committed
(`40797cf`); no vol-target run is valid without it, and every treatment arm
below carries the validated floor.

## 0. The object under test (and why it is NOT the refuted T-055)
We scale the **whole-book beta EXPOSURE** inversely to realized portfolio
vol (Moreira-Muir): `scale = clip(target_vol / realized_vol, floor, ceiling)`,
applied as a SIZING MODIFIER after the kill-switch/drawdown-halt gates (never
a risk override). This is a DIFFERENT object from the refuted T-055, which
vol-targeted the *dead edge book at the signal level* (−0.214 on 12yr). The
Phase-1 diagnostic (T-206) established the book is a **low-β (0.33) long carry
whose −33% MDD, not its return, is what loses to the robo** — so engineering
the SIZE/SHAPE of that beta is the right lever. The lift is GROSS; it must
survive de-gross re-entry slippage + after-tax to matter (the fragile-net
prior).

## 1. Hypotheses
- **H1:** vol-targeting the beta exposure (guard ON) delivers a
  net-of-slippage-AFTER-TAX risk-adjusted improvement over the vol-target-OFF
  baseline — `Δ(after-tax Sharpe) ci_low > 0` (block-bootstrap) AND/OR a
  materially better MDD (the −33% tail is the robo-losing axis) — that clears
  the robo after-tax bar (C's gate), DSR/n_trials-penalized, and holds in the
  OOS sub-window.
- **H0 (the prior — plausibly the outcome):** the gross lift does NOT survive
  de-gross slippage + after-tax + the DSR penalty; `Δ(after-tax Sharpe)
  ci_low ≤ 0` and the MDD improvement is within noise.

## 2. Primary + secondary metrics
- **Primary:** `Δ(after-tax Sharpe)` with block-bootstrap CI (Künsch 1989,
  auto block length, 1000 iter); decision keys off **`ci_low`**, not the
  point estimate (CLAUDE.md #6). Threshold: `ci_low > 0` to declare a lift.
- **Co-primary:** `Δ(MDD)` and `Δ(downside-tail / CAR25)` — a tail-cut that
  does NOT raise Sharpe is still decision-relevant against the robo (the
  −33% MDD is the losing axis).
- **Gross vs net:** report BOTH gross Sharpe and net-after-tax Sharpe for
  every arm. The ~0.40→0.50 gross expectation must land at a net ~0.35-0.45
  to clear. Turnover (de-gross/regross round-trips) is reported per arm — it
  is a TAX lever first (T-148), so the after-tax channel is where the lift
  dies or survives.

## 3. The grid (SMALL + pre-registered — N_trials logged)
All treatment arms carry the **validated sigma-floor** (guard ON;
`vol_floor_full_sample_frac=0.5` for adaptive margin) and `regime_aware=OFF`
(isolate the pure exposure-scaling effect; the regime-gated variant is a
separate later build that must read the validated HMM p_crisis, not the
coarse 5-axis advisory). `target_annual_vol=0.10` fixed (retail-fit).

| arm | estimator | floor/ceiling | vol_floor_annual | note |
|---|---|---|---|---|
| `arm0_off` | — | — | — | **control** (empty patch → reproduces the published 26yr anchor) |
| `arm1_rolling` | rolling-60d | 0.5 / 2.0 | 0.05 | primary; T-055 default estimator |
| `arm2_ewma` | ewma λ0.94 | 0.5 / 2.0 | 0.05 | faster vol-up response (T-055d) |
| `arm3_yz` | yang_zhang | 0.5 / 2.0 | 0.05 | range-based (T-150 winner); needs OHLC data_map — if it no-ops to 1.0, that is itself a finding (OHLC not wired to the risk path) |
| `arm4_rolling_tight` | rolling-60d | 0.7 / 1.5 | **0.07** | floor/ceiling sensitivity. NOTE: bound = 0.10/1.5 = 0.0667, so the guard REQUIRES floor_annual ≥ 0.0667 — the T-212 guard enforces per-arm floor tuning (it is not vacuous). |

- **N_trials (this campaign):** **4** treatment configs (arm1–arm4). Logged
  toward cumulative honest-N (~260+); the DSR deflation uses #candidates.
- **Determinism:** `reps=3` per cell + the launcher's 3-rep canary on
  `arm0_off`/2022. A cell's arms are trusted only if the canary is 3/3
  bitwise-identical AND `arm0_off` reproduces the published anchor canon
  (the T-128/T-140 cross-task placement-lottery gate). Per the standing rule,
  the analyst requires `arm0_off` N≥5/window unanimous before quoting any
  arm-vs-arm delta as a verdict (this campaign launches N=3; top up if the
  primary clears).

## 4. Windows (MBL-clearing + OOS robustness)
- **`2000-2025` (26yr, full cycle)** — the MBL-clearing primary; `arm0_off`
  here reproduces the canonical re-anchor book.
- **`2013-2025` (late 13yr, OOS sub-window)** — robustness: vol-target has NO
  fitted parameters (target/floor/ceiling are pre-set, not in-sample-tuned),
  so the OOS concern is regime-robustness, not parameter overfit. The lift
  must hold in BOTH windows; a lift that appears only in the full window but
  not the recent regime is demoted.

Block-bootstrap CI on each; census-gated (measured-mode, T-194 loader-HALT);
cov-pin determinism; hermetic (no yfinance fallback).

## 5. Sanity gates BEFORE trusting any delta (flag-bites + anchor)
1. **Flag bites:** `arm1/2/4` trades-canon MUST differ from `arm0_off`
   (T-146 "flag-ON-must-change-canon" standard). An arm whose canon equals
   arm0 means the overlay never reached order sizing — a wiring no-op, not a
   null result.
2. **Anchor:** `arm0_off` 26yr canon == the published re-anchor canon
   (verify post-run; uninterpretable otherwise).
3. **Guard live:** every treatment cell ran with the sigma-floor ON (the
   manifest config echo confirms `portfolio_vol_target_floor_enabled=true`);
   a cell that somehow ran guard-OFF would have FAILED LOUD (VolTargetGuardError)
   — a FAILED cell on a treatment arm is a guard catch, not a flake.

## 6. Decision rule
- **Ship-candidate** (→ C's T-211 v2 composition): ≥1 arm with
  `Δ(after-tax Sharpe) ci_low > 0` OR a material `Δ(MDD)` improvement that
  clears the robo after-tax bar, holding in BOTH windows, flag-bites + anchor
  + guard gates all green. Still PROPOSE-FIRST: the flag-flip is a separate
  director-gated act.
- **H0 confirmed** (the prior): no arm clears net-after-tax `ci_low > 0` and
  MDD improvement is within noise → vol-target is gross-fragile; do NOT add to
  the composition; document the net-vs-gross gap.

## 7. Boundary
Engine B → PROPOSE-FIRST. This campaign runs on the branch via per-cell config
patches (`ARCHONDEX_CONFIG_PATCH_B64`); it does NOT flip
`portfolio_vol_target_enabled` in any prod config and does NOT merge to main.
The OFF-default path is byte-identical (the guard is unreachable when disabled).
Composable + default-OFF: the overlay is an exposure-scaling layer C can add as
the T-211 v2 increment if and only if it clears.
