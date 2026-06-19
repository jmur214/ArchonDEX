# T-118 — HMM regime-transition gross-exposure overlay (PRE-REGISTRATION + default-OFF PoC)

**Date:** 2026-06-06
**Agent:** C (worktree `trading_machine-agent-c`, branch `feature/hmm-transition-trigger-overlay-t118`)
**Status:** PROPOSE-FIRST. **Pre-registration + default-OFF overlay built + canon-proven inert.** The ~36-config A/B campaign is **NOT yet run** — it is gated on three director decisions (§7). This document is the pre-registration required by CLAUDE.md `[NN-MBL]` *before* any cell runs.
**Builds on:** T-116 (HMM `risk_scalar` Path-A wire, merged `9ba28f8`). The overlay reuses the exact T-111/T-116 Path-A `target_notional`-multiplier shape.
**Source spec:** `docs/Sessions/Other-dev-opinion/6-6-26_gaps.md` Q7 (ranked #1-priority experiment) + "SINGLE HIGHEST-EV EXPERIMENT" §.

---

## 0. The headline question

T-092 found the base ensemble is **bull-conditional**: 16-yr (crisis-free 2010-2025) Sharpe **1.018** (ci_low 0.560), but 26-yr (2000-2025, includes 2008+dotcom) Sharpe collapses to **0.246** (ci_low −0.119), MDD **−59.3%**. **Does a regime-transition-triggered gross-exposure de-gross close that gap on the deep window?** This is the actual experiment the plumbing sequence T-087→T-100→T-101→T-103→T-105→T-106→T-111→T-116 was built to enable.

---

## 1. Why a TRANSITION trigger (not a level) — settled by prior work

- The Engine-E combined posterior `p_combined = p_crisis + p_stressed = 1 − p_benign` is a **validated forward-drawdown signal**: AUC@5d **0.914** ci_low 0.880 on the crisis-trained model (T-103), **0.848** on the production model (T-087), fires 5/5–7/7 stress events with 27–60-day lead, causal-verified (T-089, look-ahead inflation bounded +0.0015…+0.006 AUC).
- But it is **disqualified as a LEVEL**: T-105 measured the live 60-bar posterior at threshold 0.5 sitting in stressed-or-crisis **44–50% of the time**, p90 run-length **198–265 days** (max 632d). A level-de-gross there re-creates the documented "always-on light leverage" pathology.
- **Resolution (T-105 verdict): "DEGRADED-BUT-OK-AS-TRANSITION-TRIGGER, NOT AS LEVEL."** Trade the **change** in the posterior, with hysteresis, asymmetric (re-gross slower than de-gross). This is the design below.

---

## 2. The overlay (built; default-OFF; canon-proven)

**Module:** `engines/engine_b_risk/regime_transition_overlay.py` — `RegimeTransitionOverlay` (stateful, deterministic, idempotent-by-timestamp).

**Signal (causal-path contract):** consumes ONLY `regime_meta['hmm_regime']['probabilities']`, the per-bar posterior the live backtest already computes via `HMMRegimeClassifier.predict_proba_at` (60-bar **growing** window, last row only — filtered/forward, never the forward-backward `predict_proba_sequence`). The overlay adds **no new inference**; it only differences a series the engine already produces causally → it cannot introduce look-ahead.

**Trigger logic:**
- Per-bar `p_t = p_crisis + p_stressed` (fail-safe 0.0 if HMM block absent → never arms).
- `Δ_k = p_t − p_{t−k}` (causal change over k bars).
- **De-gross (arm):** when disarmed and `Δ_k ≥ τ_on` → arm.
- **Re-gross (disarm, asymmetric/slower):** when armed, require `p_t ≤ τ_off` for `n_off` **consecutive** bars (any non-calm bar resets the counter) → disarm.
- Emits gross multiplier = `degross_level` when armed, else `1.0`.

**Integration (mirrors T-111/T-116):**
- Per-bar buffer advanced in `manage_positions` (runs every bar in the backtest loop, before `prepare_order`), keyed on `regime_meta['timestamp']`.
- `prepare_order` reads `current_multiplier()` and applies it to Path A: `target_notional = equity · target_weight · optimizer_weight · portfolio_vol_scalar · _drawdown_size_mult · _advisory_risk_scalar_mult · _regime_overlay_mult`.
- Because Path A is target-weight **rebalancing**, scaling the target IS a gross-exposure scaling (the book rebalances toward the de-grossed target; `degross_level=0.0` rebalances new sizing to flat).

**Proofs (2022 cell, `run_isolated --task q1 --year 2022`):**
| State | Canon md5 | Note |
|-------|-----------|------|
| OFF (default) | `0145c03a6496d9d823bc8e50b0635ec2` | ≡ T-101/T-111/T-116 baseline — **bitwise-inert default** |
| ON (aggressive arm: level 0.0, k5, Δ0.20) | `97875aeb4453d41492dbdb360b8693d2` | **DIFFERS** — trigger arms in the 2022 benign→stress transition, de-grosses |
- Determinism `--runs 3` default-OFF → `0145c03a…` ×3, range 0.0000. **PASS** (T-099 floor preserved).
- Unit tests: `tests/test_regime_transition_overlay_t118.py` — **8/8** (de-gross on Δ, asymmetric re-gross, idempotency, disabled no-op, level-1.0 null arm, level-0.0 flatten, posterior fail-safe).

---

## 3. PRE-REGISTERED parameter grid (FIXED before any cell runs)

Per the gaps-doc Q7 grid: **de-gross levels × k-day Δ lookback × 4 hysteresis pairs.**

- **`degross_level` ∈ {1.0, 0.5, 0.0}** — 1.0 is the **null/placebo arm** (trigger fires but multiplier is neutral → a canon-consistency control); 0.5 halves the rebalance target; 0.0 flattens new sizing.
- **`k_days` ∈ {3, 5, 10}** — Δ lookback in trading days. (Operative forward horizon is 10d per T-105; k is the *trigger* lookback, swept.)
- **4 hysteresis pairs** (all asymmetric: re-gross strictly slower than de-gross; anchored to posterior scale [0,1], transition magnitudes 0.3–0.5, and T-105 dwell median 12–19d):

  | Pair | `degross_delta` (τ_on) | `regross_level` (τ_off) | `regross_bars` (n_off) | character |
  |------|---:|---:|---:|---|
  | **H_A** | 0.40 | 0.30 | 5  | balanced |
  | **H_B** | 0.30 | 0.25 | 10 | fast-degross / slow-regross (doc-recommended asymmetry) |
  | **H_C** | 0.50 | 0.25 | 10 | conservative-degross / slow-regross |
  | **H_D** | 0.30 | 0.20 | 15 | fast-degross / very-slow-regross (max persistence) |

**Grid = 3 × 3 × 4 = 36 configs per window.** Plus **arm0** (overlay OFF) = the T-092 baseline. Windows: **16-yr (2010-01-01→2025-12-31)** and **26-yr (2000-01-01→2025-12-31)**. At reps=1 → **36×2 + 2 arm0 = 74 cells**; reps≥3 recommended on 26-yr (T-092 found FP-drift scales with depth) → budget ~90–110 cells.

**This grid is FROZEN. No post-hoc expansion.** Any change after the first cell runs voids the pre-registration and must be logged as a new trial set.

---

## 4. Hypotheses + decision gate (pre-registered)

- **H1:** A de-gross multiplier triggered by an upward transition in `p_combined` (with hysteresis) raises the full-26-yr Sharpe from 0.246 toward the bull-cell level AND reduces MaxDD by ≥25%, vs arm0, out-of-sample.
- **H0:** The overlay does not improve deflated Sharpe vs the static book after accounting for the ~36-config trial cost.
- **Recommend the overlay IFF ALL hold** (honest, CI-aware per CLAUDE.md `[NN-SHARPE-CI]`):
  1. **Block-bootstrap `ci_low > 0` on the DIFFERENCE in Sharpe** (best arm − arm0), not on each arm alone; AND
  2. **MaxDD reduction ≥ 25% on the 26-yr** window; AND
  3. **Holds across BOTH crisis and non-crisis sub-samples** (no single-event dependence — an overlay that "works" only because of 2008 is rejected).
- **If** it helps only via one crisis, OR craters calm-year Sharpe, OR `ci_low` on the difference crosses 0 → **do NOT recommend.** Either outcome answers the headline question definitively.

**Metric discipline:** Sharpe + block-bootstrap CI recomputed from `portfolio_snapshots.csv` equity via `MetricsEngine.bootstrap_distribution` (n=1000, seed=0, Politis-White block length), NOT read from rounded `performance_summary.json` (T-090 lesson). Compare `ci_low` against DSR benchmark **0.6612 at N≈270**.

**N_trials accounting:** +36 configs (the 12 `level=1.0` arms are null controls but still count) → N ≈ 270 → **~306 (+13%)**. One mechanism, small pre-registered grid → deflated-Sharpe penalty stays clearable if the effect is real. 16-yr clears MBL (req 10.81yr); **26-yr fails MBL hard (req 185.5yr) — the 26-yr is diagnostic for drawdown/robustness, not a deployment-Sharpe claim.**

---

## 5. arm0 reproduction targets (overlay OFF == T-092 baseline)

| Window | Sharpe | ci_low | MDD | arm0 canon md5 |
|--------|-------:|-------:|----:|----------------|
| 16-yr (2010–2025) | 1.018 | 0.560 | −15.4% | `b9cb088f3d7b793598ea5b6db60579d9` |
| 26-yr (2000–2025) | 0.246 | −0.119 | −59.3% | `c579566c881d…` |

The mandatory 2-cell cloud pre-flight (CLOUD_USAGE.md) must reproduce **arm0 16-yr canon `b9cb088f…`** before the full grid is trusted. (Survivor-only substrate → both are UPPER bounds; 26-yr especially.)

---

## 6. THE MODEL FORK (director decision — §7.1)

**Pivotal:** production loads `hmm_3state_v1.pkl` (the *original* model; `config/regime_settings.json` `hmm.model_path`), **NOT** `hmm_3state_crisis_v1.pkl` (the crisis-trained model that produced the AUC@5d **0.914**). Both exist on disk; `multires_enabled=False`. The gaps-doc H1 says "on the crisis-inclusive retrain," but acceptance criterion #2 says "canon arm0 == T-092 baseline" — and T-092 ran on the **production** model. These pull in opposite directions.

| Option | arm0 == T-092 canon? | Signal (AUC@5d) | Conflates repoint? | Verdict |
|--------|:--:|:--:|:--:|---|
| **(1) Production model `hmm_3state_v1`** (RECOMMENDED) | **YES** (`b9cb088f`) | 0.848 (T-087, causal, 5/5 events) | No | Clean overlay isolation; satisfies acceptance #2; doesn't smuggle in the unshipped repoint |
| (2) Crisis model `hmm_3state_crisis_v1`, held constant across all arms | No (new baseline) | 0.914 (T-103) | **Yes** — repoint is a separate propose-first (T-103) | Better signal + matches gaps wording, but breaks arm0==T-092 and folds in an unshipped change |
| (3) Model as a 4th grid dimension | partial | both | — | Doubles cost/N; over-engineered for a first pass |

**Recommendation: Option (1) — production model.** It satisfies the hard acceptance criterion, **isolates the overlay effect cleanly** (the only thing varying between arm0 and treatment is the overlay, not the model), and respects T-103's explicit "production wiring [of the crisis model] is a separate propose-first dispatch." The production model's combined posterior is itself validated (0.848, fires 5/5). If the primary shows promise, a **follow-up dispatch** can re-run on the crisis model (Option 2) as a sensitivity check. **Director: confirm Option (1), or direct Option (2)/(3).**

---

## 7. What must be decided BEFORE the campaign runs (the gate)

1. **Model fork (§6)** — confirm Option (1) production model (recommended) vs (2)/(3).
2. **Cloud image off-branch.** The ECR `:dev` image bakes `main` at build time AND is currently **STALE** (built at T-112, missing T-115+T-116). The overlay code is on this **feature branch, not main**, so a normal main-image rebuild will NOT contain it. The campaign requires an image built from `feature/hmm-transition-trigger-overlay-t118` (or the branch merged to main first, then rebuilt). This is a deliberate gate — propose-first means no merge-to-main without director review. **Director: approve building the `:dev` image off this branch for the campaign (temporary), or merge-then-build.**
3. **Cloud spend + grid sign-off.** ~74–110 cells, est. ~$2–4 spot, ~3–5h wall (26-yr OFF arm flirts with the 4h job timeout; use `--job-timeout 14400`+). Confirm the §3 grid is frozen as-is.

**The double-count carry-forward (from T-116) is baked into the design and the must-measure list:** this overlay is a gross-de-gross keyed off the same regime signal as the LIVE advisory floors. Per T-116 it composes as min() vs `suggested_exposure_cap` (no double-cut on gross) but compounds multiplicatively (count×size) vs `suggested_max_positions` in the cap-slack crisis regime — exactly the windows this overlay targets. **The campaign MUST log per-cell crisis-window realized gross** so the true combined de-gross is visible (and if any arm also has T-116's `risk_scalar` lift on, account for the triple-stack). This is added to the campaign spec, not deferred.

---

## 8. Acceptance checklist

- [x] Pre-registered ~36-config grid documented BEFORE running (hypothesis + gates + N_trials) — §3, §4
- [x] Transition-trigger overlay (Δ combined-posterior + asymmetric hysteresis) on the CAUSAL 60-bar path, default-OFF flag — built, `regime_transition_overlay.py`
- [x] Canon arm0/default-OFF inert (2022 cell `0145c03a` == baseline); ON differs (`97875aeb`); determinism `--runs 3` PASS; unit tests 8/8
- [ ] **16-yr + 26-yr A/B; deflated-Sharpe ci_low on the DIFFERENCE, MDD reduction, crisis vs non-crisis split** — GATED on §7 director decisions (not yet run)
- [ ] **Decision-gate verdict** — pending the campaign
- [x] Audit doc (this file) + proposed ledger row in OUTBOX
- [x] NO prod-default change (config reverted); branch pushed NOT merged

## 9. Files
- **NEW** `engines/engine_b_risk/regime_transition_overlay.py` — the overlay (logic + causal posterior extraction).
- **MOD** `engines/engine_b_risk/risk_engine.py` — 6 `RegimeOverlayConfig` fields (default-OFF) + overlay instantiation + `manage_positions` per-bar hook + `prepare_order` Path-A multiplier. All gated default-OFF.
- **NEW** `tests/test_regime_transition_overlay_t118.py` — 8 unit tests.
- **NEW** `docs/Audit/hmm_transition_trigger_overlay_t118_2026_06_06.md` (this file).
