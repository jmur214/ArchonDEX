# T-118r — HMM transition-trigger de-gross overlay, RE-RUN on the T-167 trustworthy anchors: VERDICT = FAIL, family closes

**Date:** 2026-06-14/15
**Agent:** C (branch `feature/hmm-transition-overlay-rerun-t118r`)
**Status:** DONE. **The transition-trigger de-gross overlay FAILS both LOCKED reads on the pre-reg-faithful crisis model; per pre-registration §5 the family closes at this design. Do not recommend the overlay.** The fork's headline question — does the overlay push the 26yr 0.751/ci_low-0.382 base past the 0.40 line — is answered **NO: it moves ci_low the wrong way.**

This is the first VALID test of the de-gross thesis: the original 52-cell campaign was null because the cloud regime layer was dead (T-118fc/T-165); T-167 made the regime LIVE, so the overlay actually fires now.

---

## 0. Verdict (one paragraph)
On the trustworthy T-167 substrate (cov-pin N=5 unanimous, regime live, full universe, mean_variance config-true), the overlay **arms** (firing confirmed — canon differs from arm0, cov-pin-clean). But the LOCKED **primary config** (de-gross 0.5 / k=5 / shipped hysteresis 0.4/0.3/10) driven by the validated crisis HMM **reduces** risk-adjusted return on every window and **flattens no drawdown**: 26yr Sharpe 0.752→0.680, ci_low **0.370→0.287** (away from 0.40), MaxDD identical, terminal wealth on 3.98 < off 5.30 (−25%). It de-grosses **only on slow grinds** (2022 +4.3pp, 2025 +2.9pp ΔMaxDD) and does nothing on fast crashes (GFC +0, COVID +0) or corrections. Every criterion of both locked reads FAILS. **The transition-Δ overlay family is closed.** Separately: the model barely matters on the base (crisis-OFF 26yr 0.752 ≈ the v1 anchor 0.751) — prod running the weak v1 model is ~costless; the crisis model's only value would have been as a de-gross signal, which just failed.

## 1. The two LOCKED reads — results

### Frozen T-118 gate (Sharpe-diff ci_low > 0 AND 26yr MDD −≥25% AND no single-event)
| window / model | arm0 (OFF) Sharpe / ci_low / MaxDD% | primary (ON) Sharpe / ci_low / MaxDD% | gate |
|---|---|---|---|
| **26yr / crisis** (pre-reg model) | 0.752 / 0.370 / −32.61 | 0.680 / 0.287 / −32.61 | **FAIL** (Sharpe-diff <0; MDD 0% reduction) |
| 16yr / crisis | 1.118 / 0.608 / −16.17 | 1.042 / 0.536 / −16.17 | FAIL |
| 16yr / v1 (arm0 == anchor `3e9ea427`) | 1.162 / 0.658 / −16.17 | 0.984 / 0.444 / −16.17 | FAIL |
| 26yr / v1 (arm0 must == `158fe678`) | _pending (12h re-run)_ | _pending_ | _expected FAIL_ |

The overlay lowers ci_low in **every** cell and reduces MaxDD in **none** (all MaxDDs bitwise-identical to arm0). The 26yr MaxDD is **dotcom** (2000-2002), which the crisis HMM is structurally blind to (data floor 2006-04, disclosed in pre-reg §v3) — so the frozen-gate MaxDD criterion is confounded, and the T-118b per-episode read governs.

### T-118b crisis-replay (official harness `scripts/crisis_replay_t118b.py`, LOCKED v3, crisis-26yr primary): **FAIL on ALL**
Per-episode ΔMaxDD (positive = overlay shallower):

| episode | split | ΔMaxDD pp |
|---|---|---|
| dotcom | BLIND (reported, not gated) | +0.0 |
| GFC | in-sample | **+0.0** |
| 2010 | in-sample | +0.0 |
| 2011 | in-sample | +0.0 |
| 2018Q4 | in-sample | +0.0 |
| COVID (fast) | OOS | **+0.0** |
| 2022 (slow grind) | OOS | **+4.3** |
| 2025 (tariff) | OOS | **+2.94** |

| criterion | value | threshold | verdict |
|---|---|---|---|
| median ΔMaxDD | 0.0pp | ≥ +3pp | FAIL |
| sign test | 2/7 | ≥ 6/7 | FAIL |
| GFC floor | 0.0pp | ≥ +5pp | FAIL |
| OOS all improve | COVID 0.0 | all > +0.5pp | FAIL |
| calm drag | −99.5 bps/yr (CI90 [−206, −3]) | ≥ −40; CI excl −80 | FAIL |
| single-episode share | 0.595 | ≤ 0.5 | FAIL |
| terminal wealth | on 3.98 < off 5.30 | on ≥ off | FAIL |
| benefit/drag ratio | −0.23 vs 0.995 pp/yr | ≥ 3× | FAIL |

The harness also reported the honest-derivation divergence (the locked episode list is not fully reproducible from the 15%-DD rule on the pinned SPX TR; the mechanical rule yields a single dotcom 2000-09→2002-10 −47.4%) — surfaced per the §4 finality clause, not patched; the gate uses the locked month-pinned list and FAILS regardless.

## 2. Why it fails (mechanism, not a bug)
The Δ-trigger over k days fires only on a **sustained benign→stress ramp** — present in 2022 and 2025 (slow grinds), absent in fast crashes (COVID spikes faster than the k=5 de-gross can act) and in the GFC (which sits IN the crisis-HMM training window with an already-elevated posterior → no in-window Δ). So the overlay de-grosses in scattered calm transitions (paying ~1%/yr) and is missing at the crises that drive the MaxDD. This is precisely the **power-critique failure pattern** the T-118b pre-reg was constructed to detect: narrow crisis benefit + large calm drag + Sharpe-CI moving the wrong way.

## 3. Fork inputs (flagged per the director)
- **The model barely matters on the base.** crisis-OFF 26yr (0.752 / ci_low 0.370 / MaxDD −32.61 / CAGR 7.35) ≈ the published v1 anchor (0.751 / 0.382 / −33). Prod running the weak regime model (v1, AUC 0.49) vs the validated crisis model (AUC@5d 0.914) is **~costless on the full-cycle base** (different trades, same risk-adjusted result). "Switch prod to the crisis model" (Engine-E/F, propose-first) buys ~nothing on the base; the crisis model's value was only ever as an overlay signal — and that overlay failed.
- **Model-invariance refuted on the live-regime substrate.** crisis+OFF ≠ v1+OFF now (2022 1.328 vs 1.512; 16yr 1.118 vs 1.162; 26yr same Sharpe, canon `a429af59` vs `158fe678`). The HMM-modulated risk_scalar reaches Path-A sizing once the regime is live (the T-116 wash-out was regime-state-specific). Crisis-base anchors documented (cov-pin-clean): 2022 `598cc663`, 16yr `4309a934`, 26yr `a429af59`.
- **Honest-N:** the model dimension is a DECLARED 2-condition design (committed 2026-06-14 before any full-grid unblinding); both reads reported per the finality clause. No goalpost-fishing.

## 4. Operational notes
- **T-167 full-universe 26yr cells exceed the old 6h Batch timeout** — re-ran the 26yr at `--job-timeout 43200` (12h). Future 26yr campaigns must budget ≥10h/cell.
- The original-grid HA hysteresis (0.4/0.3/**5**) did NOT match the LOCKED primary (0.4/0.3/**10** = shipped defaults); corrected so `arm_L05_k5_HA` == the gate's primary config (grid-coverage fix, not a threshold edit).
- The mildest-config-fires pre-flight (CLOUD_USAGE standing gate) was satisfied: the overlay arms on the live-regime substrate (canon differs from arm0).

## 5. Recommendation
1. **Do NOT recommend the overlay.** Per pre-reg §5, FAIL → the transition-trigger de-gross overlay family CLOSES at this design. The fork should weigh the **decompose / conditional-sleeve / cross-asset-diversifier** agenda instead of de-gross — the overlay does not lift the borderline 26yr base; it lowers it.
2. **HOLD the 46-cell crisis sensitivity sweep** (recommendation): the gate is primary-config-only and the primary fails comprehensively (net-negative). A large 26yr sweep (>6h/cell) to confirm a closed family is poor spend; a different config preferred would in any case require a fresh pre-registration (pre-reg §v2.4). Run only on explicit director request.
3. The "prod regime model = weak v1" finding is a separate, low-stakes Engine-E/F item; this campaign shows switching the base model is ~costless, so there's no urgency.

## 6. Files / provenance
- `scripts/gen_t118_campaign_spec.py` (primary-config + T-167 anchor + crisis model), `scripts/analyze_t118r.py` (Sharpe/ci_low/MaxDD recompute from snapshots, block-boot n=1000 seed 0 — T-090 discipline), the LOCKED `scripts/crisis_replay_t118b.py` (T-143, used as-is — no edits).
- Cells: image `sha-4c0fc16` (T-167 substrate + overlay code, 0-diff from HEAD), job def `archondex-backtest-reanchor-mv-t167:1`. Spend: pre-flight + decisive + v1-26yr (~30 cells; the 26yr cells dominate). NO prod change; NO flag flips; branch push only.
