# T-2026-06-04-101 — HMM kill-switch Phase 0+: wire `hmm_enabled=true` + verify

**Date:** 2026-06-04
**Branch:** `feature/hmm-wire-phase0plus-t101`
**Worker:** Agent B
**Predecessor:** T-100 (`crisis_path_diagnostic_t100_2026_06_04.md`) — established that the existing crisis defenses were STARVED (HMM not wired; 0/1174 advisory calls received `hmm_proba`).
**Proposal:** `docs/Core/Ideas_Pipeline/hmm_crisis_killswitch_proposal_2026_06_04.md` Phase 0+

## TL;DR

**Verdict: CAPABILITY failure, not WIRING failure.** Flipping `hmm_enabled=true` in `config/regime_settings.json` makes the validated HMM posterior flow into `advisory.generate()` as designed — but **changes nothing observable in production trading behavior**. Trade-canon is **bitwise identical** between HMM-OFF and HMM-ON. The HMM modulates `risk_scalar`, which lives on dead Path B (T-088 dead-knob); Path A (production target_weight sizing) doesn't consume it. **The −59% MDD T-092 saw is NOT a wiring failure. Phase 1 (Engine B binary kill-switch, propose-first) is the required fix.**

| Question | T-100 (HMM OFF) | T-101 (HMM ON) | Change |
|---|---|---|---|
| **Q1' — does `hmm_proba` reach advisory?** | 0/1174 calls | **all 1174 calls** | ✓ wire flows |
| Q2' — regime_summary state counts | crisis=55, stressed=223, cautious=575, benign=321 | crisis=55, stressed=223, cautious=575, benign=321 | **0 change** (regime_summary derived from 5-axis, not HMM) |
| Q2' — 2020 COVID crisis bars (May-Dec) | 0 crisis + 0 stressed | 0 crisis + 0 stressed | **still missed COVID** |
| Q2' — 2022 crisis bars | 44 crisis + 137 stressed | 44 crisis + 137 stressed | 0 change |
| Q3' — Δ gross_crisis vs gross_benign | −0.012 | −0.012 | **0 change** |
| Q3' — 2022 Δ gross | −0.106 | −0.106 | 0 change |
| Side: mean risk_scalar (benign) | 0.887 | 0.868 | −0.019 (HMM-confidence damp) |
| Side: mean risk_scalar (crisis) | 0.476 | 0.476 | 0 change |
| **2022 default-cell canon md5** | `0145c03a6496d9d823bc8e50b0635ec2` | `0145c03a6496d9d823bc8e50b0635ec2` | **BITWISE IDENTICAL** |
| Determinism --runs 3 (HMM ON) | n/a | 3/3 identical canons | ✓ PASS |

The only behavior delta is a 0.019 (2.1%) damp on `mean_risk_scalar_benign` — and it's silent in the order book.

## What I did

1. **Verified HMM prereqs** (no engine edits). Confirmed `engines/engine_e_regime/models/hmm_3state_v1.pkl` exists, T-087/T-089-validated. Confirmed `feature_set="legacy"` (4 features: spy_vol_20d, yield_curve_spread, credit_spread_baa_aaa, dollar_ret_63d) pairs with that model. Drove `RegimeDetector(cfg=HMMConfig(hmm_enabled=True, feature_set='legacy'))` in-process and confirmed:
   - `_hmm_clf` loaded ✓
   - `_hmm_feature_panel` built: 1513 rows, 2020-04-09 → 2026-04-17
   - T-100 window coverage (2020-05-01 → 2024-12-31): 1175 rows ✓
   - NaN counts in window: 0-48 per column out of 1175 (all <5%; `HMMRegimeClassifier` handles NaN gracefully).

2. **Flipped the JSON flag** at `config/regime_settings.json:99-104`:
   ```diff
       "hmm": {
   -       "hmm_enabled": false,
   +       "hmm_enabled": true,
           "model_path": "engines/engine_e_regime/models/hmm_3state_v1.pkl",
   +       "feature_set": "legacy",
           "min_confidence_floor": 0.6,
           "on_model_missing": "warn"
       }
   ```
   `feature_set: "legacy"` was added explicitly to make the (model, features) pairing self-documenting in the config.

3. **Re-ran T-100 harness** on the same 2020-05-01 → 2024-12-31 window via `scripts/diagnose_crisis_path_t100.py` (unchanged code; reuses the monkey-patch instrumentation on `AdvisoryEngine.generate`). 618.2 s wall, 1174 advisory.generate calls captured, 1175 portfolio snapshots, 1175 offline-HMM dates.

4. **Compared T-101 vs T-100** side-by-side; see TL;DR table.

5. **Determinism --runs 3** with HMM ON on the 2022 default cell under `isolated()`: all 3 produced canon `0145c03a6496d9d823bc8e50b0635ec2` — identical to the pre-T-101 baseline canon (T-098 had this same hash for the same cell with HMM OFF). **Determinism PASS, AND the canon equality is itself a finding** (see below).

## Q1' — does `hmm_proba` flow? (the make-or-break check)

**YES, fully.** `hmm_proba_was_passed_in_live_run_any_bar=True`. 1174 / 1174 advisory.generate calls received a non-None `hmm_proba` dict with keys `{benign, stressed, crisis}`. The per-bar CSV records `hmm_p_crisis` values matching the offline-computed `hmm_p_crisis_offline` to ~6 decimals (small noise from the live vs offline feature-panel build paths; both use `predict_proba_at` filtered/causal).

The wiring at `engines/engine_e_regime/regime_detector.py:218 → 237` is functional. The proposal's central risk — "panel empty/thin → silent abstention" — did NOT materialize.

## Q2' — does `regime_summary` now flip to crisis in 2020 / 2022 with HMM ON?

**No change vs HMM OFF.** Identical regime_summary distributions across both runs.

Mechanism (re-confirmed from `advisory.py:160-176`):
```python
risk_score = self._compute_risk_score(axis_states, axis_confidences)
...
regime_summary = self._risk_to_summary(risk_score)
```
`regime_summary` is computed from the **5-axis risk_score** ONLY. The HMM posterior is consumed later, ONLY to damp `risk_scalar`. So flipping HMM cannot change `regime_summary` by design.

**Implication:** the proposal's "outcome (b) 5-axis miscalibrated for COVID" finding from T-100 STANDS. Wiring HMM doesn't recalibrate the 5-axis; it adds a SECOND channel that has no path to influence `regime_summary` today. To get HMM to drive the crisis label, Engine E would need a different change: either replace `_risk_to_summary` with an HMM-driven label or compose the two.

## Q3' — does realized gross fall in those crisis bars now that HMM is on?

**No change vs HMM OFF.** Aggregate Δ gross_crisis − gross_benign remains **−0.012** (−1.2pp). Per-year deltas are identical to the second decimal.

Mechanism (from T-100 + T-088 + this run): `risk_scalar` lives on Path B (atr-risk sizing). Production uses Path A (`target_weight`). HMM-confidence damp on `risk_scalar` does not flow to Path A position sizing.

The only observable delta is `mean_risk_scalar_benign` 0.887 → 0.868 (−0.019). This appears in the advisory log dictionary but never reaches the order book.

## Q4' — wiring vs capability verdict

**CAPABILITY failure.**

The 2022 default-cell canon md5 is **bitwise identical** between HMM-OFF and HMM-ON. Flipping the flag from off to on changes neither the trades.csv nor the equity curve. The HMM posterior flows correctly (Q1' YES) AND modulates `risk_scalar` (visible in the advisory log — benign mean dropped 2.1%) but the modulation is silent in production sizing.

**The −59% MDD T-092 saw is NOT a wiring failure that this Phase 0+ flag flip would have prevented.** Engine B's existing consumer wiring (risk_engine.py:725-748) lacks a path from HMM to gross. Specifically:

- `suggested_max_positions` consumer (line 729-731) — Path A's `effective_max_positions` count. Computed from 5-axis (correlation regime + regime_summary). HMM not consulted.
- `suggested_exposure_cap` consumer (line 734-736) — Path A's `effective_max_gross`. Computed from 5-axis risk_score. HMM not consulted.
- `risk_scalar` consumer (line 739-741 → :915 `risk_scaler *= advisory_risk_scalar`) — Path B atr-risk only. HMM-modulated but production-dead.

So:
- (a) HMM not wired → **FIXED** in T-101 (posterior flows).
- (b) 5-axis miscalibrated for COVID → **STILL OPEN** (and not fixable by wiring HMM, because regime_summary doesn't read HMM).
- (c) De-gross too weak → **STILL OPEN** (and not affected by wiring HMM, because the path that HMM modulates is dead).

**Phase 1 (Engine B binary kill-switch, propose-first) is required.** The −59% MDD cannot be saved by Engine-E/config changes alone. The proposal's outcome (c) classification was the binding one, as T-100 already suggested; T-101 confirms by showing that even fully wiring HMM produces zero change in production trading behavior.

## Determinism guard

3 independent 2022 default-cell runs at `hmm_enabled=true` produced identical trade canons:

| Run | canon_md5 |
|---|---|
| 1 | `0145c03a6496d9d823bc8e50b0635ec2` |
| 2 | `0145c03a6496d9d823bc8e50b0635ec2` |
| 3 | `0145c03a6496d9d823bc8e50b0635ec2` |

3/3 identical. **PASS.**

Plus the cross-flag observation noted above: HMM-OFF baseline (T-098-vintage 2022 canon) = `0145c03a6496…` = HMM-ON canon. **Identical across the flag toggle on the default cell** — this isn't a determinism win, it's the headline capability finding.

## Substrate caveat — unchanged from T-100

Local `data/processed/SPY_1d.csv` starts 2020-04-09. The HMM feature panel (which depends on SPY-derived `spy_vol_20d` + `spy_ret_5d`) inherits this floor. The 2008 GFC and 2000-02 dot-com regimes that drove T-092's −59% MDD are NOT testable on the local substrate.

**Phase 0b (cloud cell on T-082b Stooq-extended substrate) is still the recommended verification path for those crises.** Even there, the T-101 finding implies Phase 0b would also show "wiring works, trades unchanged" — but verifying that on the actual crises is worth the cost since it nails down whether ANY part of the HMM-on-Path-B wiring helps under sustained drawdown stress.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | `hmm_enabled: true` set + feature_set/model_path verified | DONE — `feature_set: "legacy"` paired with `hmm_3state_v1.pkl`; panel covers full window; in-process drive verified clf + panel load |
| 2 | T-100 harness re-run; Q1' advisory-calls-with-`hmm_proba` count reported | DONE — **1174 / 1174 = 100%** (was 0/1174 in T-100) |
| 3 | Q2' 2020+2022 crisis-bar counts WITH vs WITHOUT | DONE — IDENTICAL (regime_summary derives from 5-axis, not HMM) |
| 4 | Q3' realized-gross-in-crisis WITH vs WITHOUT | DONE — IDENTICAL aggregate Δ (−0.012); identical 2022 Δ (−0.106) |
| 5 | Q4' verdict: wiring vs capability failure | DONE — **CAPABILITY failure** (canon bitwise identical across the flag toggle). Phase 1 required. |
| 6 | Determinism --runs 3 PASS at new flag value | DONE — 3/3 identical canon `0145c03a6496…` on 2022 default cell |
| 7 | Audit doc + TASK_LEDGER row | DONE |
| 8 | NO Engine B edits | DONE — only `config/regime_settings.json` edited; zero edits under `engines/` |
| 9 | Branch pushed; NOT merged | (pushed at close) |

## Hard constraints — confirmed met

- [x] No edits to `engines/engine_b_risk/`. No edits to `engines/engine_e_regime/` code (only the JSON config).
- [x] Engine E config + wiring is autonomous scope; consumed it.
- [x] `_predict_hmm` had no bug — feature-panel build path worked first try; no engine fix required.
- [x] No `data/governor/*` or `cockpit/dashboard/` edits.
- [x] Branch push only.

## Files

- **MOD** `config/regime_settings.json` — `hmm_enabled: false` → `true`; explicit `feature_set: "legacy"` added.
- **NEW** `docs/Audit/hmm_wire_phase0plus_t101_2026_06_04.md` (this).
- **NEW** `docs/Audit/hmm_wire_phase0plus_t101_2026_06_04.json` — aggregate + per-year analysis payload.
- **NEW** `docs/Audit/hmm_wire_phase0plus_t101_per_bar.csv` — 1175-row joined per-bar frame.

## Surprises

1. **The HMM-OFF → HMM-ON canon delta is ZERO.** Bitwise identical trades.csv on the 2022 default cell. The single most consequential observation in the run. It says: regardless of the HMM signal quality (validated T-087/T-089 AUC 0.887), the existing Engine B / Engine C consumer pipeline cannot ACT on it.
2. **Q1' answered YES, Q2'/Q3' answered NO.** The wiring works exactly as designed — but the design wires HMM to a behaviorally-inert channel (`risk_scalar` → Path B dead). This is the silent-mismatch family again: a knob that looks live but consumes nothing.
3. **2020 COVID is still missed by `regime_summary`** — 0 crisis bars in 170 days. Offline HMM caught 17 high-`p_crisis` bars there. The fix for (b) is genuinely Engine E recalibration or a `regime_summary` rewire to read HMM, not just turning HMM on.
4. **The proposal's Phase 0+ description ("autonomous Engine E config flip") was correctly scoped but the action does not, on its own, meet the proposal's implicit objective** ("change the crisis response"). T-100 said Phase 0+ "adds the validated signal to the live wire" — true. T-101 confirms the live wire feeds a dead channel. The proposal's Phase 1 framing ("if Phase 0 = outcome c") was already correct; T-101 just nails it down.
5. **Determinism floor inherited from T-099 carries through with the flag flipped on.** Long-window FP-determinism fix is robust against the HMM module's added compute (small `predict_proba_at` per bar).

## What this implies for the next step

**Phase 0+ is COMPLETE but DELIVERS no defensive improvement on its own.** Specifically:

- Leaving the flag flipped to `true` is fine — it's behaviorally inert in production sizing today AND adds a clean diagnostic stream (visible in advisory.risk_scalar damping for observability).
- It is NOT a substitute for Phase 1.
- Phase 0+ does NOT need to be reversed; it's a no-op for trading but a yes-op for telemetry.

**Director decision needed:**

| Option | Description | Cost | Defense delta |
|---|---|---|---|
| A | Merge T-101 as a no-op observability win + dispatch Phase 1 binary kill-switch (Engine B, propose-first) | Engine B PR + A/B campaign | Real (Phase 1 designs the actual de-gross path on Path A) |
| B | Merge T-101 + dispatch a smaller Engine E rewire (regime_summary reads HMM) before Phase 1 | Engine E PR + verify; smaller blast radius than Engine B | Modest (would fire crisis on COVID but de-gross magnitude still bounded by `suggested_exposure_cap` cap floor of 0.30) |
| C | Revert flag flip + dispatch Phase 1 directly | minimal | Phase 1 only |

Recommendation: **A.** Keep T-101's flag flip merged (it's observability-useful even if behaviorally inert) and dispatch Phase 1 propose-first to design the binary kill-switch.

## Status flag

**DONE — wiring verified (Q1' YES), capability gap confirmed (Q2'/Q3'/Q4' NO change). Phase 1 Engine B kill-switch propose-first is the required next step.**
