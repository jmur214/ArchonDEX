---
task_id: T-2026-07-27-314
title: Pre-registration — the bounded regime-conditional adaptation RULE (the steelman's experiment)
date: 2026-07-27
worker: Agent B
branch: feature/adaptation-rule-experiment-t314
status: DRAFT — design only (0 N). Awaiting director FREEZE; RUNS AFTER T-311 + T-260 close (needs the deep frozen-spec baseline). N_trials pre-charged below.
---

# T-314 pre-registration — can a bounded, validated adaptation rule beat the frozen spec OOS?

## What this is (and is not)
This is the honest form of the **user's contested thesis** — "the machine should
progressively improve from what works" — as scoped in T-305 §3A/§3D. It is **NOT** the
free-parameter fit that killed MetaLearner / HRP / concentration. It is a **bounded
adaptation RULE** (≤2 DoF, shrunk toward the frozen spec) **learned on early decades,
FROZEN, and tested OUT-OF-SAMPLE on held-out decades** — the LOCO discipline generalized
from "reject/enable" to "validate-and-freeze." T-306's substrate is the FIRST on which
this question is honestly askable (tripwire #1 of T-305 fired).

**Either verdict is decisive and publishable-internally:**
- OOS win → adaptation is a real lever; the user's thesis is validated on evidence.
- OOS null → *"the frozen spec is the ceiling; adaptation adds nothing at this N"* —
  which CONFIRMS the director's prior and REFUTES the thesis **on this substrate, with
  evidence instead of arithmetic.** That is a real answer, not a failure.

## Dependency / sequence
Runs **after T-311 → T-260 close**. The frozen-spec baseline it perturbs = the **deep
re-verified sleeve from T-311** (ensemble `{42,105,210}`, EW, T-255 fair conventions, on
the T-306 substrate). Do not run before that baseline is established + frozen.

## The rule (≤2 DoF — exact DoF named)
A **regime-conditional exposure multiplier** applied to the frozen sleeve exposure:

    exposure_adaptive[t] = exposure_frozen[t] · (1 − β · s[t])          # 1 DoF: β

- **`s[t]` — the causal regime STRESS signal (fixed, NOT fitted):** a deep-computable,
  causal equity-volatility stress indicator —
  `s[t] = clip( (rv60[t−1] − rv_med[t−1]) / rv_med[t−1], 0, 1 )`, where `rv60` is the
  60-day realized vol of the equity leg and `rv_med` is its EXPANDING-window median up to
  `t−1` (uses ONLY data before `t` — T-273 lag discipline). `s ∈ [0,1]`: 0 in calm, →1 in
  high-vol stress. Vol-clustering is the most robust deep regime signal (the HMM's own
  price axes are vol-based, but the HMM needs a macro panel that does NOT extend to 1962,
  so a vol proxy is the honest deep-computable choice). **`s` is pre-registered, not
  searched** — no grid over windows/definitions.
- **`β` — THE ONE fitted DoF:** the stress de-risk STRENGTH, `β ∈ [0, 1]`. `β=0` ⇒
  adaptive == frozen (no adaptation). The multiplier is capped so `exposure_adaptive ∈
  [0, exposure_frozen]` — the rule can ONLY de-risk in stress (never lever up), matching
  the T-298 "never damp de-risking" asymmetry and the defense-first prior. **Bounded
  perturbation:** by construction the adaptive book is a shrunk-toward-frozen version of
  the frozen sleeve; a null β returns the frozen sleeve exactly.
- **Hard DoF ceiling = 1** (β). A 2-DoF variant (add a stress threshold `λ`, pre-registered
  to a single value, NOT a grid) is available ONLY if the director prefers it at freeze —
  but the primary is the 1-DoF β. **No third knob, ever.**

## Fit procedure (shrinkage — a bounded perturbation, per T-305 §3D)
Fitted on the **IN-SAMPLE** window ONLY (decades 1–3 ≈ first 60% of the substrate):

    β* = argmax_{β ∈ [0,1]}  [ Sortino_IS(β)  −  τ · β² ]        # ridge shrinkage toward β=0

- **`τ` — the pre-registered shrinkage prior (fixed, NOT fitted):** a SINGLE value set at
  freeze (proposal: `τ` calibrated so a 10-pp Sortino gain is needed to move β from 0 to
  0.5 — a genuinely "moderate, skeptical" prior; the exact constant stated at freeze). The
  prior center β=0 IS the frozen spec, so if adaptation adds nothing the fit returns β*≈0
  → adaptive == frozen. **This makes "no improvement" the DEFAULT, not a coincidence.**
- **Scalar, bounded optimization** — one 1-D line search over β ∈ [0,1]. NO grid over
  `s`, `τ`, or lookbacks. Freeze `β*` before touching OOS.

## OOS test + win condition (FROZEN)
Apply the frozen `β*` to the **OUT-OF-SAMPLE** window (decades 4–5 ≈ last 40%), which the
fit NEVER saw:
- **WIN:** `OOS Sharpe(adaptive) ≥ OOS Sharpe(frozen-spec)` **AND** the paired
  `OOS[adaptive − frozen]` 21-day block-bootstrap (1000 iter, seed=0) has **`ci_low > 0`**.
- **NULL (equally decisive):** `ci_low ≤ 0` ⇒ *"the frozen spec is the ceiling; adaptation
  adds nothing at this N"* — reported as the confirming-the-prior verdict, not buried.
- Report OOS Sortino + MaxDD deltas alongside (a de-risk rule that trades wealth for a
  shallower OOS MaxDD is characterized honestly, not scored as a win on Sharpe alone).

## Anti-overfit guards (ALL pre-stated)
1. **Causality:** `s[t]` uses only data `< t` (expanding median, 60d vol on `t−1`) — T-273.
2. **Hard ≤2-DoF ceiling:** the primary is **1 DoF (β)**; the only optional 2nd DoF (`λ`)
   is a single pre-registered value, never a grid.
3. **Strict OOS wall:** decades 1–3 fit NEVER sees decades 4–5. One split, pre-declared,
   no re-slicing.
4. **Shrinkage default = frozen:** the ridge prior centers β at 0, so "adaptation helps"
   must overcome a skeptical prior; null → adaptive collapses to frozen.
5. **No signal/τ/λ search:** ONE regime signal, ONE τ, ONE split — all pre-registered. The
   whole experiment is a SINGLE rule test.

## N accounting
**N_trials += 1** — this is ONE pre-registered rule with one fitted scalar (β), one fixed
regime signal, one shrinkage prior, one OOS split. No search, no family. (If the director
elects the 2-DoF `λ` variant at freeze, it remains N_trials += 1 — same single rule, one
extra pre-registered constant, no grid.) At MBL-cleared depth (~58–64yr) the DSR bar is
already met by the frozen baseline (T-311); this rule adds 1 to honest-N — stated.

## Honest prior (BEFORE the run)
**LOW–MEDIUM.** 8–10 crises is still a small N for a regime-conditional rule, and the
frozen deep sleeve is a strong baseline (the trend overlay already de-risks in stress, so
a vol-conditional de-risk may be largely redundant with what the ensemble already does).
But this is the FIRST substrate on which the question is honestly askable — the user
earned this shot, and either verdict is decisive.

## Sequence
Draft (this doc) → **director FREEZE** (rule form, `s` definition, `τ`, the 1-vs-2-DoF
choice, the IS/OOS split fraction) → **run AFTER T-311 + T-260** → OOS result + verdict
appended here → outbox. Nothing runs until freeze. → "T-314 draft ready".
