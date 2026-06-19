# Task T-2026-05-22-055d — Engine B vol-target EWMA λ=0.94 estimator + A/B re-run

**Branch:** `feature/engine-b-vol-target-ewma-t055d` (off origin/main, rebased on the just-merged T-055c)

## What

Replace (or alongside) the rolling-60d realized-vol estimator in
`engines/engine_b_risk/vol_target.py` with an EWMA estimator
(RiskMetrics standard, λ=0.94). Then re-run the T-055c A/B harness with
the new estimator and produce a fresh `Δ Sharpe / ci_low` headline.

The full-Moreira-Muir 2017 spec uses a fast estimator; rolling-60d on
real data is too slow to degross before vol expansions. T-055c's 2025
-0.942 Sharpe trap (Harvey 2018 failure mode) is the direct evidence.

Two implementation choices — your call:

(a) Add `estimator_type: Literal["rolling", "ewma"] = "rolling"` to
    `VolTargetConfig` + dispatcher in `compute_realized_vol_from_history`.
    Lower-risk: rolling stays as default, EWMA opts in via config.

(b) Add a new function `compute_realized_vol_from_history_ewma()`
    and a top-level toggle. Same outcome, cleaner module boundary.

Either way: the existing rolling implementation MUST stay reachable and
default-on (no flag-flip on main; this is measurement work).

## Why

T-055c shipped MARGINAL: ci_low -0.140 fails CLAUDE.md `[NN-SHARPE-CI]`. Per-year
shows the +0.256 mean is a regime-conditional restructuring, not a
uniform lift. The 2025 trap is the clearest failure mode and the one
EWMA directly addresses:

- λ=0.94 (RiskMetrics) effective half-life ≈ 11 days vs rolling-60d
  ≈ 30-day equivalent → much faster response to vol expansion.
- 2024 +1.303 Sharpe rescue is real — if EWMA preserves it AND fixes
  2025, the lift becomes deployable; if EWMA only fixes 2025 by giving
  back the 2024 rescue, we know it's a uniform-noise issue, not a
  speed-of-estimator issue.

Forward-look: if T-055d clears ci_low > 0, T-055b flag-flip becomes
defensible (still needs explicit user approval). If T-055d doesn't
clear ci_low, escalate to T-055e (regime-conditional target).

## Acceptance

- [ ] EWMA estimator implemented with λ=0.94; unit-tested against a
      synthetic vol-shock fixture (must respond faster than rolling-60d
      on a step-change in σ — concrete test: σ doubles at t=T/2,
      EWMA scale crosses 0.7 within 10 bars, rolling-60d does not).
- [ ] Existing rolling-60d codepath UNCHANGED and remains the default
      `VolTargetConfig` value (no production behavior change).
- [ ] 30-backtest A/B harness re-run using your T-055c
      `scripts/run_vol_target_arms_full.py` adapted for the EWMA arm
      (Arm 0 OFF unchanged; Arm 1 ON uses EWMA estimator).
- [ ] Bootstrap-CI headline + per-year breakdown in audit doc,
      following the T-055c structure for direct comparability.
- [ ] Determinism: 3-rep canon-md5 invariance per cell (10/10).
- [ ] Per CLAUDE.md `[NN-SHARPE-CI]`: lift verdict reported as `Δ point` AND
      `Δ ci_low`. T-055b recommendation pivots on ci_low > 0, not
      point.

## Hard constraints

- DO NOT flip `vol_target.enabled = True` on main. This is measurement.
  Config reverted at end of campaign.
- DO NOT touch Engine A / C / D / E / F.
- vol_target.py CAN be edited (Engine B propose-first ALREADY APPROVED
  via this dispatch). risk_engine.py edits ONLY if needed for the
  dispatch — minimize the surface area.
- Patch the env-resolved config file (risk_settings.prod.json) when
  toggling. Per the T-055c lesson, verify the patch propagated via
  canon-md5 comparison across arms before launching the full 30-run
  campaign.
- Time budget: ~6 hr (implementation + tests + 30-run + audit doc).

## When done

Write to `docs/Coordination/agent_b_outbox.md`:
- Branch name + final commit hash
- 5-line headline: Δ point, Δ ci_low, 2024 rescue status,
  2025 trap status, defensibility verdict
- Test count (pass / total)
- Pointer to audit doc at `docs/Audit/engine_b_vol_target_ewma_t055d_2026_05_22.md`
- Status flag: DONE / PARTIAL / BLOCKED

Then in chat: "T-055d done, see outbox" so the director knows to ping.
