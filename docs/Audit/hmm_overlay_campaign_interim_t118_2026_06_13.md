# T-118 overlay campaign — INTERIM (verdict HELD; + a deeper finding: the overlay never armed)

**Date:** 2026-06-13
**Agent:** C
**Status:** INTERIM — **T-118 verdict HELD** (per the director's "anchors-not-durable" P0; the frozen gate + LOCKED T-118b read are NOT evaluated). This doc reports the in-campaign anchor checks and a finding that goes *beyond* the lottery confound: **the overlay was inert in every cell.** Not closing T-118.

**Campaign:** image `sha-5323a3c`, job def `archondex-backtest-t155-anchor:3`, 52-cell lean grid (arm0 + 24 crisis-model overlay arms + v1-blind) × 16yr/26yr; 45/55 cells done at this writing, 0 failed (10 deep 26yr cells + v1-blind still running; results below are 42/52 + will be appended).

---

## 1. Per-window arm0 anchor check (the in-campaign gate)

| Window | arm0 canon / Sharpe | vs published anchor | Read |
|---|---|---|---|
| 16yr | `62db5c0d` / 1.021 | == anchor `62db5c0d`/1.021 (the majority attractor, NOT minority `9153ff15`/0.945) | on-anchor draw |
| 26yr | `529e5520` / 0.237 | == anchor `529e5520`/0.237 | on-anchor draw |

Both reference legs drew on-anchor. **But these are single Fargate-task draws** — A's T-128-CO showed the placement lottery survives the thread pins (composition-level cov()→MVO FP), so "on-anchor" here is a lucky draw, not durability.

## 2. THE FINDING: the overlay never armed — the batch is null-by-construction, not merely lottery-confounded

Across all 42 collected cells (every one of the 24 overlay configs: degross_level {0.5, 0.0} × k {3,5,10} × hysteresis {HA,HB,HC,HD}, both windows), there are exactly **four distinct outcomes, and all four are arm0 lottery attractors**:

| Window | distinct (canon, Sharpe, MDD) | count |
|---|---|---|
| 16yr | `62db5c0d` / 1.021 / −15.38 | 22 |
| 16yr | `9153ff15` / 0.945 / −16.49 | 3 |
| 26yr | `529e5520` / 0.237 / −59.29 | 13 |
| 26yr | `2b2f2c2b` / 0.446 / −48.0 | 4 |

**Zero novel canons.** If the overlay had de-grossed even one rebalance anywhere in a run, `target_notional` would change → a novel `trades.csv` → a canon outside the arm0 attractor set. Every treatment cell is **bitwise-identical to an arm0 lottery draw.** So the apparent "arm deltas" (e.g. 26yr 0.237 vs 0.446) are **100% placement lottery, 0% de-gross** — there is no overlay effect in this batch for the lottery to confound.

**Wiring is confirmed correct** (not a patch failure): the cell entrypoint log shows `[entrypoint] Patched config/risk_settings.prod.json` with `regime_transition_overlay_enabled: true`, and the overlay keys are accepted as valid RiskConfig fields (absent from the "ignoring unknown key" list). The overlay loaded enabled — it simply never armed.

## 3. WHY it never armed (local mechanism test, 2022 cell)

| Run | config | canon | armed? |
|---|---|---|---|
| A | crisis model, overlay OFF | `0145c03a` | — (baseline) |
| B | crisis model, overlay ON, **δ=0.30** (grid's most sensitive arm, HB) | `0145c03a` | **NO** |
| C | crisis model, overlay ON, **δ=0.20** (the threshold that fired in the original V1 proof) | `0145c03a` | **NO** |

Contrast the original T-118 firing proof (`docs/Audit/hmm_transition_trigger_overlay_t118_2026_06_06.md`): **V1 model + δ=0.20 → canon `97875aeb` (ARMED).** So switching V1→crisis killed the trigger even at δ=0.20.

**Root cause — the crisis model's posterior is a persistent LEVEL, not sharp k-day transitions.** STEP 1 captured the crisis model's 2022 posterior as `{stressed: 0.9993, crisis: 1.6e-82, benign: 0.0007}` — `p_combined ≈ 0.9993`, essentially pinned high through the stress. The transition trigger fires on `Δ_k = p_t − p_{t−k} ≥ τ`; when the signal snaps once (often before/at window start) and then holds near 1.0, `Δ_k ≈ 0` for the rest of the run → never arms. This is **exactly the level-vs-transition pathology T-105 flagged** (the combined posterior is 44–50% always-on): the "convert the level into a transition trigger" premise does NOT rescue a signal that is genuinely level-like under the crisis model. The V1 model's posterior was evidently snappier (more in-window transitions), which is why it fired.

> The empirical cloud result corroborates beyond 2022: the 26yr window contains fresh benign→stress transitions (2008, 2020, 2011, 2018) — yet **no 26yr cell across any config produced a novel canon**, so the crisis-model overlay didn't arm on those either (or armed so marginally it changed nothing). The combination {crisis model × δ≥0.30 grid} is inert end-to-end.

## 4. Implication: the LOCKED grid cannot answer the question on the crisis model

The frozen T-118 gate (ci_low>0 on the Sharpe DIFFERENCE, MDD −≥25%, no single-event) and the LOCKED T-118b crisis-replay read presuppose an overlay that *acts*. On the crisis model with the pre-registered δ-grid, the overlay does not act, so:

- **The verdict is HELD on TWO independent grounds:** (a) the anchors are not durable (lottery — director's P0), AND (b) there is no overlay signal in the batch to gate (null-by-construction). Either alone blocks a clearing verdict.
- **A clean determinism fix (B's T-140-followup-2) is necessary but NOT sufficient** for a meaningful re-run. Even on a perfectly deterministic substrate, this exact grid would reproduce arm0 in every cell. The re-run needs a trigger that actually fires on the crisis model.

**This needs a director decision because the T-118b pre-registration is LOCKED/FINAL** (I will not unilaterally change thresholds). The options, stated neutrally:
1. **Accept the null as the answer:** "the transition-trigger overlay, driven by the validated crisis-model combined posterior, is inert across the pre-registered grid — the level-like posterior (T-105) does not yield a transition trigger at δ≥0.30." This is a real, publishable result and arguably the honest one.
2. **Re-open the pre-registration to recalibrate** the trigger so it fires on the crisis model — e.g. a much lower δ, a level-crossing-after-benign-run trigger instead of a Δ trigger, or driving the overlay with the snappier V1 posterior (the v1-blind arm, pending, tests exactly this: V1 + δ=0.30). Any of these is a *new* pre-registration, not a tweak — N_trials and the gate re-derived.

The v1-blind arm (V1 model + δ=0.30, pending) is the on-substrate disambiguator: if it produces a novel canon while the crisis arms don't, it confirms the non-firing is model-driven (snappy V1 fires, persistent crisis doesn't) and points option 2 toward the trigger formulation, not just the threshold.

## 5. What's staged
- Existing grid + generator unchanged and ready. arm0 anchor-gate intact (the standing safeguard).
- Gated re-run fires once (a) B pins the cov/MVO FP source (clean single draws) or proves it irreducible (→ N≥5 reps/cell), **AND** (b) the director resolves the trigger-calibration question above. Pre-registration otherwise UNCHANGED.

## 6. Provenance / hygiene
- Mechanism test patched `config/risk_settings.prod.json` + `config/regime_settings.json` locally, then restored — **git status config/ clean, verified.**
- Local mechanism test runs use the adaptive allocator (Apr-23 artifact present) — irrelevant to the arms-or-not question (the overlay multiplier on `target_notional` changes trades regardless of allocator); the canon values are local-family, used only for the within-test OFF-vs-ON comparison.
- No prod changes; no flag flips; the campaign's only cost was the 55 cloud cells (already spent).
