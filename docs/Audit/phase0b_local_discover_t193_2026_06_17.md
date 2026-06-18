---
task_id: T-2026-06-17-193 (corrected — LOCAL on main HEAD)
title: Phase-0b honest --discover, run LOCALLY — INCONCLUSIVE; a real structural obstacle found
date: 2026-06-17
author: Agent D (alpha/edge + Discovery lane)
outcome: INCONCLUSIVE locally (NOT a fake H0). Preconditions verified-good (fresh
  fair foundry seed + simfin loads OFFLINE → census fundamentals_blind=0). But the
  local --discover path CANNOT produce a trustworthy foundry verdict for a real,
  decision-grade reason: the production discovery cycle validates on a 24-month
  "quick-filter" window, and MBL Gate-0 computes T_years from THAT window (2.0 yr)
  vs MBL_min ≈ 9.66 yr (N_eff≈125, SR_target≈1.0) → EVERY candidate dies at Gate-0
  artifactually before any alpha gate runs. Forcing an MBL-clearing 14yr window via
  a controlled standalone sweep clears Gate-0 and reaches Gate 1, but the standalone
  baseline ensemble computes Sharpe 0.0 (it doesn't reproduce the production
  baseline state) → its "0 cleared" is not trustworthy. The full literal production
  cycle (which sets baseline state correctly) is multi-hour locally. Recommend the
  cloud-discover follow-on (brief pre-authorized) and/or fixing the local Gate-0
  window wiring.
status: INCONCLUSIVE — trustworthy verdict needs cloud-discover or a local-cycle fix
---

# T-193 (corrected) — Phase-0b local --discover: what ran, and the obstacle

## Preconditions — VERIFIED GOOD (the corrected local-on-main-HEAD model is sound)
- Rebased to main HEAD (T-179 genes-fix + T-183 fair seed + T-180-v2 simfin-live +
  T-181 census, all together for the first time).
- **Fresh fair foundry seed:** archived `data/governor/ga_population.yml` so Gen-0
  seeds fresh (the `--discover` path reads it directly — `_run_discovery_cycle`
  does NOT go through `isolated()`, and there is no `_isolated_anchor/
  ga_population.yml`, so no restore overwrites the archive).
- **Census pre-flight PASS:** `get_panel()` loads the simfin panel OFFLINE
  (51133×30, real columns) — the T-180-v2 `_ensure_simfin_configured` cached-read
  fix works locally → the 4 value/accruals edges are NOT blind →
  `fundamentals_blind=0`. (If it had failed, that was the STOP-and-flag gap; it
  did not.)

## The obstacle (the decision-grade finding) — MBL Gate-0 vs the 24-month window
The production `_run_discovery_cycle` validates each candidate on a **24-month**
quick-filter window (`mode_controller.py:1301`, `DISCOVERY_VALIDATION_MONTHS=24`;
the comment says Gate-3 WFO does the real OOS). But `validate_candidate`'s **Gate-0
MBL** computes `T_years` from that same `(start_date, end_date)`:
```
gate_0: FAIL: T_years=2.00 < MBL_min=9.66  (N_effective=125, SR_target≈1.0)  → killed_by_gate=gate_0_mbl
```
Gate-0 runs FIRST (fail-fast), so on the 24-month window **every candidate dies at
Gate-0 before any alpha gate (1–8) runs** — verified directly. So "run `--discover`
locally" as specified produces a trivial all-die-at-Gate-0 result, NOT a foundry
verdict. This is either by-design (local = pure exploration, MBL is the cloud's
job — consistent with the standing rule) or a window mis-wire (Gate-0 should use
the full evaluation extent, not the 24-month quick-filter). Director call.

## Forcing the issue — a controlled 14yr vocabulary sweep (and why it's not trustworthy)
To get past Gate-0 I swept ALL 35 tier-A/B Foundry features, one single-gene long
composite each (the fair-seed's Gen-0 archetype; cross-sectional → percentile,
ticker-independent → absolute per the T-177 feature-class insight), through the
production gauntlet on a **14yr** MBL-clearing window (2010-2024 → T_years=15 >
9.66). Result: Gate-0 cleared, all reached Gate 1, **all died at Gate 1 with
contribution=0.0**. BUT `baseline_sharpe=0.0` for EVERY feature — the baseline
ensemble itself produced no return in the standalone driver (it doesn't reproduce
the production baseline state — active-edge weights / governor state; compounded by
registry/governor pollution from iterative local runs). So `contribution =
0 − 0 = 0` is an ARTIFACT, not a real null. **I do not report this as H0** — a
hand-rolled local verdict with a degenerate baseline is not trustworthy for the
load-bearing alpha test.

## Why not just run the literal full production cycle?
`python -m scripts.run_backtest --discover` sets the baseline state correctly, but
runs a full backtest + the ~20-min TreeScanner hunt + a per-candidate gauntlet over
~47 candidates (templates + GA composites) — multi-hour locally, not completable
this session, and STILL Gate-0-blocked on the 24-month window (above). The brief
pre-authorized: "if local proves too slow to be repeatable, build a cloud-discover
path as a SEPARATE follow-on — not gating this test."

## Verdict + recommendation
**H-INCONCLUSIVE locally.** A trustworthy FIRST foundry verdict needs ONE of:
1. **Cloud-discover follow-on** (brief pre-authorized): a clean image off main
   HEAD (≥`8cbdd50`, `ga_population.yml` archived in the substrate so Gen-0 is
   fair), the full gauntlet over an MBL-clearing window with DSR + census-gating.
   This is the canonical path; local was always going to be exploration-only.
2. **Local-cycle fix** (cheaper, if local is wanted): (a) wire MBL Gate-0 to the
   full evaluation extent rather than the 24-month quick-filter (or raise
   `DISCOVERY_VALIDATION_MONTHS` to an MBL-clearing value); (b) run from a CLEAN
   governor anchor (a fresh `reset_governor` + un-polluted `edges.yml`) so the
   baseline ensemble actually trades; then the controlled 14yr sweep
   (`scripts/run_phase0b_foundry_discover_t193.py`) gives a real per-feature
   verdict.

**Highest-value finding for the director:** the local `--discover` cycle, as
wired, kills every candidate at Gate-0 on its 24-month validation window — so it
structurally cannot promote anything locally regardless of foundry quality. That
should be resolved (or confirmed as intended-exploration) before "run it locally"
is treated as a real test.

## N_trials / state
Controlled sweep consumed 35 trials (DSR family n=35) — VOID (degenerate baseline).
No edges promoted; no `edge_weights.json` edited. Governor/registry state restored
(legacy `ga_population.yml` restored from Archive; `data/governor` is gitignored +
worktree-local, so no git/branch impact). Disk monitored (7.9Gi, stable).

## Files
- `scripts/run_phase0b_foundry_discover_t193.py` — the controlled 14yr foundry
  vocabulary sweep (the diagnostic that surfaced the MBL-window obstacle; NOT a
  trustworthy verdict tool until the baseline-state issue is fixed — documented).
