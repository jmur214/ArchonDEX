# PROPOSAL (propose-first, Engine B) — HMM crisis kill-switch / de-gross

**Status:** DRAFT for user approval. NO code, NO dispatch until signed off.
**Date:** 2026-06-04 · **Author:** director · **Decision context:** T-092 Path B (ratified 2026-06-04)
**Scope flags:** Engine B (Risk) = **propose-first**. Engine E read-only wiring = autonomous. Gated behind **T-099** (long-window determinism) for any 16/26-yr A/B to be trustworthy.

---

## 0. The headline you need before approving

**A crisis de-gross path ALREADY EXISTS in the codebase — it is ~70% built.** This proposal is therefore *mostly diagnose-then-decouple*, not build-from-scratch. Concretely, already on `main`:

- `engines/engine_e_regime/advisory.py` ingests an HMM posterior (`hmm_proba`) and emits `regime_summary ∈ {benign, cautious, stressed, crisis}` plus `suggested_exposure_cap`, `risk_scalar`, `suggested_max_positions`.
- On `regime_summary == "crisis"` it ALREADY tightens `suggested_max_positions` (→ `crisis_max_positions`) and exposure cap — a real de-gross — consumed by Engine B when `risk_advisory_enabled=True` (default ON).
- `RiskConfig` ALSO has `portfolio_vol_target_crisis_multiplier: 0.40` (T-055e) — a *second* crisis de-gross channel, BUT it rides on `portfolio_vol_target_enabled`, **the overlay T-055 REFUTED**. So it's dead in production.

**Implication:** the first task is NOT "write a kill-switch." It's **"instrument the existing crisis path on the 26-yr window and find out why the base still drew -59%."** Three possible findings, each with a different fix — see §3 Phase 0.

This reframing is the single most important thing in this doc: building a new kill-switch before diagnosing the existing one would risk re-deriving machinery that's already there (the exact mistake the project's silent-mismatch history warns against), and could double-de-gross.

---

## 1. Objective + honest framing

**Goal:** reduce crisis-regime drawdown (the -59% MDD that killed the 26-yr window), NOT lift Sharpe. Primary KPI = **MaxDD reduction**; Sharpe is secondary and must not be promised.

**Why this is a band-aid, stated plainly:** the research's sharpest finding was that our construction is structurally SHORT skew; the *structural* cure is a positive-skew trend/managed-futures sleeve (Path B layer 2). The kill-switch is sequenced FIRST only because it (a) reuses an asset we ALREADY validated (T-087/089 `p_crisis`, AUC 0.887) and (b) attacks the MDD fastest. It is not the whole answer.

**Why binary/discrete, not gradual:** T-055 (ours) + Cederburg 2020 + the 2026-05-31 research all agree gradual vol-targeting fails OOS. Bongaerts-Kang-van Dijk 2020 shows *discrete state-switching on a high-AUC signal* works (≈doubled momentum Sharpe, MaxDD 54→20%). Our AUC 0.887 is exactly the precondition that result requires. The existing `regime_summary`-keyed path is ALREADY discrete — good.

---

## 2. The validated signal (already built, do not rebuild)

- Producer: `HMMRegimeClassifier` (`engines/engine_e_regime/hmm_classifier.py`), model `models/hmm_3state_v1.pkl` (benign/stressed/crisis).
- **Causal method: `predict_proba_at()`** — filtered (no look-ahead) posterior. This is the path T-089 verified holds AUC 0.887 on 12-yr with +0.006 leakage inflation, firing 27–60d ahead of stress troughs.
- **NON-causal `predict_proba_sequence()` (forward-backward) must NOT be used in the live sizing path** — it sees the future. T-089's whole point. Any wiring uses the filtered prefix path.

---

## 3. Proposed work — phased, diagnose-first

### Phase 0 — DIAGNOSE the existing crisis path (autonomous; no Engine B edit) — DO THIS FIRST
Instrument a 26-yr arm0_off backtest (post-T-099) to log, per bar: `p_crisis`, `regime_summary`, `suggested_exposure_cap`, `suggested_max_positions`, realized gross. Answer:
- **Is `hmm_proba` even reaching the advisory in the backtest?** (It's an optional arg — if the backtest never passes it, the crisis path is dormant and the fix is just *wiring it on*, near-zero risk.)
- **When `p_crisis` was high in 2008/2020, did `regime_summary` flip to "crisis" and did gross actually fall?**
- Three outcomes → three fixes:
  - **(a) HMM not wired into backtest advisory** → fix = wire the filtered posterior in (Engine E read-only + backtest plumbing; autonomous). Likely the highest-probability finding.
  - **(b) Wired but `regime_summary` never hit "crisis"** → the risk_score→summary thresholds are miscalibrated for true crises → recalibrate (Engine E; autonomous).
  - **(c) Fired correctly but de-gross too weak** → THEN we need the stronger binary kill-switch below (Engine B; propose-first).

**Phase 0 may resolve the whole thing autonomously.** Only outcome (c) needs new Engine B code.

### Phase 1 — (ONLY if Phase 0 = outcome c) the binary crisis kill-switch — Engine B, propose-first
Decoupled from the dead `portfolio_vol_target` path. New `RiskConfig` block, default-OFF:
```
crisis_killswitch_enabled: bool = False        # default OFF (canon-md5 identical when off)
crisis_killswitch_floor: float = 0.25          # de-gross TO this gross fraction (not zero)
crisis_killswitch_p_on: float = 0.70           # enter crisis: p_crisis > p_on ...
crisis_killswitch_n_on: int = 3                # ... for n_on consecutive bars (hysteresis)
crisis_killswitch_p_off: float = 0.30          # exit crisis: p_crisis < p_off ...
crisis_killswitch_n_off: int = 5              # ... for n_off consecutive bars
```
- **Floor = 0.25, NOT 0** (the one judgment imposed ahead of data): a switch whose failure mode is "de-grossed to zero right before a V-recovery" reintroduces fragility. HMM fires *early* (27–60d), so a hard-zero risks exiting before the top and missing the recovery. De-grossed capital → **cash/T-bills** (no cross-asset bet; 2022 broke the bond hedge; tail-puts are wealth-destroying per research).
- Composes as a hard floor on gross, applied with the existing advisory de-gross (whichever is more conservative wins — preserves the "advisory can only tighten" contract). NEVER overrides protective SL/TP exits.

### Phase 2 — A/B validation (gated on T-099)
- **Arms:** off / floor-0.25 / floor-0.50 / floor-0.0 (the hard-kill, for reference) / tiered-3-state (100/50/20 on benign/stressed/crisis).
- **Windows:** 16-yr AND 26-yr (the crisis-bearing one is the whole point), block-bootstrap CI per CLAUDE.md #6.
- **Calibrate-then-verify (CLAUDE.md #9):** fit θ/N/M on one window, verify OOS on the other; do NOT report the fitted window as evidence.
- **Decision gate:** adopt only if **MaxDD reduction ≥ 25% on the 26-yr window AND Sharpe ci_low does not DROP** (we'll accept flat Sharpe for big MDD cuts; we will NOT accept a Sharpe-killing overlay). Pre-register this before running.

---

## 4. Risks / honest caveats
- **HMM validated as a SIGNAL, never as a trading RULE.** AUC 0.887 ≠ "a kill-switch on it makes money." Mistimed exits can miss V-recoveries. Phase 2 tests *equity impact*, not AUC.
- **Only ~3 regimes in the HMM's training span (no 2008/1970s in-sample for the model itself).** The model classifies 2008 in backtest, but it was trained on a shorter span — out-of-regime risk is real. Flag in the audit.
- **Double-de-gross hazard:** if Phase 0 = (a)/(b) we fix the existing path; we must NOT then also add Phase 1 on top without checking they don't stack. The "more conservative wins" floor contract prevents multiplicative stacking.
- **Determinism:** all A/B is gated on T-099 — a 0.19-Sharpe cross-container drift at 26-yr would swamp the effect we're measuring.
- **Survivorship:** 26-yr is survivor-only → MDD is an *under*-estimate; real crisis drawdowns were worse, which only strengthens the case for the switch but also means the backtest understates the problem.

## 5. What I need from you
1. **Approve the phased plan** (Phase 0 diagnose-first is the key ask; it's mostly autonomous and may resolve without Engine B code).
2. **Ratify the two imposed defaults:** floor=0.25-not-zero, and cash-not-bonds. Or override.
3. Confirm the **decision gate** (MDD −≥25% AND Sharpe-ci_low-not-down).
4. Sequencing: kill-switch first, **trend/managed-futures sleeve as the acknowledged Path-B layer 2** (the real skew fix). Agree?

Nothing dispatched until you sign off. Phase 0 is autonomous once approved; Phase 1 (if reached) comes back for a second look since it's live Engine B sizing code.
