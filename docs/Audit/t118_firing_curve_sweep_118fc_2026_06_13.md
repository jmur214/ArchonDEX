# T-118fc — the de-gross firing-curve sweep (FIRING-ONLY) + the cloud-null root cause

**Date:** 2026-06-13
**Agent:** C (branch `feature/t118-firing-curve-sweep-118fc`, off origin/main `2e9923f`)
**Status:** DONE. **FIRING-ONLY — zero performance metrics computed or reported** (only causal posteriors, arm-event counts, and canon-differs/regime diagnostics; no Sharpe/MDD/return/gross). The firing question is answered, and answering it surfaced the real cause of the T-118 campaign null — which **corrects my own T-118 interim.**

---

## 0. Bottom line (3 lines)
1. **A firing δ EXISTS — for BOTH models, at ALL δ ∈ {0.05…0.30}** — on any window containing a real benign→stress TRANSITION (COVID 2019→2020: max Δ_k = 1.0). The 2022 "crisis never fires" result was a **window artifact** (the crisis model entered 2022 already-stressed; its transition was end-2021, out of window). The transition-Δ trigger is **viable, not dead.**
2. **The T-118 campaign null was NOT a trigger/calibration problem.** The cloud cells ran with the **regime/HMM layer dead** (`'regime': 'unknown'` ×438, **zero** `hmm_regime` posteriors) → the overlay was **starved of input** (`combined_posterior → 0.0` → never armed). The image code is identical to local (0 diff). The overlay fires + changes trades end-to-end **when the signal is present** (verified, both allocators).
3. **Recommendation: keep the transition-Δ formulation** (it fires at onset, correctly silent during sustained stress — the opposite of T-105's always-on level pathology). The binding blocker is the **dead cloud regime layer**, not the trigger; accept-vs-reopen is premature until the campaign actually exercises the overlay.

---

## 1. The firing curve (the task deliverable) — causal `predict_proba_at` 60-bar, 2022 + COVID

`scripts/firing_curve_sweep_t118fc.py` captures the per-bar causal combined posterior `p_combined = p_crisis + p_stressed` once per (model, window) (overlay run at neutral level=1.0 → zero trade change; posterior is δ-independent), then sweeps the trigger OFFLINE across δ×k. **Fire-count = arm-events; max Δ_k = the firing threshold (any δ ≤ max Δ_k fires).** Artifact: `data/research/t118fc/firing_curve.json`.

| Window | Model | p_combined (min/mean/max) | max Δ_k (k=3/5/10) | fires at δ 0.05→0.30? |
|---|---|---|---|---|
| 2022 | crisis | 0.964 / 0.9998 / 1.0 | 0.035 / 0.035 / 0.036 | **NO** (no in-window transition) |
| 2022 | v1 | 0.0 / 0.951 / 1.0 | 0.998 / 1.0 / 1.0 | **YES, all δ** (×1) |
| COVID 2019-2020 | **crisis** | 0.0 / 0.864 / 1.0 | **1.0 / 1.0 / 1.0** | **YES, all δ** (×1) |
| COVID 2019-2020 | v1 | 0.0 / 0.651 / 1.0 | 1.0 / 1.0 / 1.0 | YES, all δ (×2) |

**Answer:** a firing δ exists for both models across the entire 0.05–0.30 ladder, **provided a benign→stress transition is in-window.** The crisis model's 2022 non-firing is not a property of the model — it is that the crisis model classifies *all* of 2022 as stressed (`p_combined ≈ 1.0` pinned), so there is no Δ to trigger on; its actual transition (end-2021) sits outside the dispatch's window. On COVID — a genuine benign→stress boundary — the crisis model fires identically to V1 (full 0→1 swing).

## 2. Firing → trade effect (canon-differs; still firing-only, no performance read)
The trigger arming is one thing; whether the arm reaches trades is another. Confirmed at the **grid's δ=0.30** on the COVID window, in BOTH allocators:

| Allocator | crisis + overlay OFF | crisis + overlay ON (L0.5, k5, δ0.30) | armed→trades? |
|---|---|---|---|
| adaptive (local default) | canon `e2cfb30d` | canon `53815e87` | **YES (differs)** |
| mean_variance (cloud allocator, artifact displaced) | canon `c00fc5d8` | canon `8c564e2b` | **YES (differs)** |

So the overlay works end-to-end — fires AND de-grosses AND changes the trade log — at the grid threshold, in the cloud's own allocator, **when the regime signal is present.** (Artifact displaced copy-preserved + restored, md5 `bfa53946` pre==post.)

## 3. So why did the CLOUD campaign show zero overlay effect? — the regime layer is dead in the cloud
The T-118 campaign's 52 cells all reproduced arm0 lottery attractors (0 novel canons). That CONTRADICTS §1–2 (the overlay fires + acts when the signal is present, and the 16yr/26yr windows contain COVID/2008/2020 transitions). Pulling a treatment cell's CloudWatch log resolves it:

- `market_state` in every fill is `{'regime': 'unknown', 'trend': 'unknown', 'volatility': 'unknown', 'details': {}}` — **438 `'regime': 'unknown'` lines, ZERO `hmm_regime`-with-probabilities lines, no advisory.**
- The image (`sha-5323a3c`) contains the **identical** overlay code (`git diff 5323a3c..HEAD` over the overlay files = 0 lines; module + `manage_positions` hook present). The config patch applied and the overlay keys loaded (not in the "ignoring unknown key" list).

So the overlay was **enabled and correct, but starved**: with no `hmm_regime`, `RegimeTransitionOverlay.combined_posterior(regime_meta)` returns its fail-safe **0.0** every bar → `Δ_k = 0` → never arms → every treatment cell is bitwise-identical to arm0. **The campaign measured the lottery because the regime/HMM layer produced nothing in the cloud — not because the trigger is mis-calibrated.**

### Root-cause confirmation: it is NOT hermetic mode (local hermetic regime is RICH)
A local 2022 run under `ARCHONDEX_HERMETIC=1` (the cloud's exact mode) produces a **fully populated** regime layer: `'regime'` distribution = neutral_normal_vol ×710, neutral_high_vol ×413, bull_high_vol ×46, bear_high_vol ×25, bull/bear/low-vol the rest; **1,292 `hmm_regime` lines.** So hermetic blocking is **NOT** why the cloud regime is unknown — locally, hermetic mode leaves the HMM/regime layer fully alive.

**Therefore the cloud `regime: unknown` is CLOUD-ENVIRONMENT-specific, not a code or hermetic property.** Narrowing the container gap: the baked substrate manifest DOES contain the benchmark + cross-asset files (SPY ×4, TLT ×5, GLD ×3 entries) — so it is **not** a simple "benchmark data not baked" gap. The **VIX panel is the suspect**: the manifest has no `^VIX_1d`/`VIX_1d`-shaped entries (0 on the strict pattern; 4 ambiguous "vix" lines), and the regime detector's `forward_stress` axis consumes `^VIX`/`^VIX3M`. A missing/mis-named VIX panel in the container — combined with hermetic blocking the network fallback — could hard-fail the detector to all-axes-unknown (locally the VIX data is present, so it works even under hermetic). **This is a hypothesis, not a confirmed mechanism** — the dedicated follow-up should reproduce a cloud cell and trace the regime detector's data load. The point that stands for the director: the regime layer is dead in the cloud, it is the sole reason the overlay never armed, and it is **bigger than T-118** — it implicates every cloud regime-conditional result (§5), including the anchors.

## 4. This CORRECTS my T-118 interim (2026-06-13)
My T-118 interim (`docs/Audit/hmm_overlay_campaign_interim_t118_2026_06_13.md`) attributed the null to **the trigger / the crisis model's level-like posterior** and to **threshold mis-calibration (δ≥0.30 too high)**. **Both attributions were wrong:**
- δ=0.30 fires fine on a real transition (COVID, §1).
- the crisis posterior is NOT inertly level — it makes full 0→1 transitions at onsets (§1).
The true cause is upstream of the overlay entirely: **the regime layer emits nothing in the cloud.** I'm flagging the interim as superseded on the mechanism (the *verdict-HELD* outcome stands, but for a different and bigger reason).

## 5. The bigger implication (flag — beyond T-118, for the director)
If the regime/HMM layer is dead in the cloud backtest, it is dead for **every** regime-conditional consumer there, not just the overlay: the advisory exposure-cap / max-positions floors, Engine A's stressed/crisis `risk_scalar` brake, and **the anchors themselves**. The cloud "hmm-ON" canonical baseline (`529e5520`/0.237 etc.) appears to be running **regime-BLIND** (`regime: unknown` throughout). That does not change the anchors' internal consistency, but it means the cloud canonical substrate is **not exercising the regime machinery at all** — a substrate-validity finding that dwarfs T-118 and warrants its own dispatch.

## 6. Transition-vs-level recommendation
**Keep the transition-Δ trigger.** §1 shows it does exactly what T-105 wanted: fires on the *onset* Δ (COVID 0→1) and stays silent during *sustained* stress (2022 pinned ~1.0, Δ≈0) — i.e. it avoids the always-on pathology that a level-crossing trigger would re-introduce (a level trigger on the crisis model would be de-grossed all of 2022). The δ-grid (0.30–0.50) is fine; **do not reopen the pre-registration to lower δ or switch to level-crossing on the strength of the null** — the null was a starved-signal artifact, not a trigger failure.

## 7. Decision input for the director (accept-vs-reopen)
- **Neither "accept the null" nor "reopen to recalibrate the trigger" is warranted yet** — the campaign did not test the overlay (the regime layer was dead). 
- **The binding fix is the cloud regime layer** (§3/§5): make `hmm_regime` actually populate in the cloud backtest, then re-run the EXISTING grid (pre-registration UNCHANGED — δ is fine). 
- Only after a re-run on a regime-live substrate can the frozen gate be read. The determinism/lottery issue (B's T-140-followup) is still also required, but it is now the *second* blocker, behind the regime layer.

## 8. Firing-only compliance + provenance
- **Zero performance metrics computed or reported.** Diagnostics used: causal posterior series, arm-event counts, max Δ_k, canon-differs (a firing signal), and the regime='unknown' log census. No Sharpe/MDD/return/gross was read at any point.
- Local only; zero N_trials (no performance hypothesis selected). All config/model/artifact mutations copy-preserved and restored; **git status config/ clean**, artifact md5 `bfa53946` pre==post.
- **NEW:** `scripts/firing_curve_sweep_t118fc.py`, this audit, `data/research/t118fc/` (gitignored). Engine code untouched.
