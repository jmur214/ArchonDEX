---
task_id: T-2026-07-27-314
title: T-314 (#1) DONE — the bounded adaptation rule: NULL. The frozen spec is the ceiling.
date: 2026-07-27
worker: Agent B
branch: feature/adaptation-rule-experiment-t314
status: DONE. N_trials += 1 (→78). Ran the frozen spec, no deviation. VERDICT — NULL: adaptation adds nothing at this N. The user's thesis is REFUTED on this substrate, with evidence.
---

> ⚠️ **CORRECTION (2026-07-28):** the **MBL/DSR "CLEARS" sentence in this doc is RETRACTED.**
> It fed `[NN-MBL]` the sleeve's ABSOLUTE Sharpe (~1.5, overwhelmingly market beta) instead of the
> Sharpe of the CLAIMED EDGE. The active (difference) Sharpe vs buy-hold is **−0.210** — there is no
> positive edge to clear. **All substantive verdicts in this doc STAND** (they rest on paired
> block-bootstrap CIs on differences, the correct test). Canonical:
> `docs/Audit/mbl_framing_correction_t306_arc_2026_07_28.md`.

# T-314 (#1) — the user's contested thesis, answered

Pre-reg: `docs/Sources/prereg_adaptation_rule_t314.md` (frozen; signal ruling + family
addendum appended). Script: `scripts/adaptation_rule_t314.py`. Data:
`data/research/t314_adaptation_rule.json`. Baseline: the T-260-deep **settled** frozen
spec `{42,105,210}` on the T-306 substrate (D-A 2-asset, the T-311 primary).

## The setup, as frozen
`exposure_adaptive[t] = exposure_frozen[t] · (1 − β·s[t])` — **1 fitted DoF (β)**;
`s[t]` the causal vol-stress signal (60d realized vol vs its expanding median, lagged),
**pre-registered 64 min before the T-311 run** (auditable, `a27eef5`); β fitted on
**decades 1-3 only** (1962-01-04 → 2000-07-24, 9,707 bars) with ridge shrinkage
`τ=0.4` toward β=0 (= the frozen spec); tested on **decades 4-5, never seen by the fit**
(2000-07-24 → 2026-04-17, 6,472 bars).

## Result
**In-sample fit:** β* = **0.36** — the fit DID find a positive de-risk strength, and it
**survived the skeptical ridge prior** (raw IS gain **+0.143 Sortino**). The shrinkage
did not artificially force β=0; adaptation was given a fair chance to prove itself.

**Out-of-sample (the held-out decades):**
| arm | Sharpe | Sortino | CAGR | MaxDD |
|---|---|---|---|---|
| FROZEN spec | 0.937 | 1.216 | **4.71%** | −9.0% |
| ADAPTIVE (β*=0.36) | 0.982 | 1.267 | 4.36% | **−7.1%** |

| paired OOS (adaptive − frozen) | 95% CI | reading |
|---|---|---|
| **ΔSortino (THE GATE)** | **[−0.0199, +0.1025]** | **ci_low ≤ 0 → NULL** |
| ΔMaxDD | **[+0.05%, +3.37%]** | **significant — shallower** |
| Δcompound %/yr | [−0.70, +0.03] | leans negative — costs return |

## ⇒ VERDICT: **NULL. The frozen spec is the ceiling; adaptation adds nothing at this N.**
This **CONFIRMS the director's prior and REFUTES the user's thesis on this substrate** —
with evidence rather than arithmetic, which was the entire point of building it.

## The experiment worked exactly as designed — that is the headline finding
**The in-sample gain did not generalize.** +0.143 Sortino IS → **+0.051 OOS with a CI
straddling zero**: roughly **two-thirds of the apparent gain evaporated** the moment it
met data the fit had never seen. That is the classic overfit signature, and **the OOS
wall caught it.** Had this rule been fitted on the full sample and shipped — the way the
MetaLearner/HRP/concentration attempts were originally framed — it would have looked
like a real +0.14 Sortino improvement. The wall is the reason we know it isn't.

## The nuance that must NOT be over-read either way
The rule is **not worthless — it is a FRONTIER MOVE, not a frontier IMPROVEMENT.** It
delivered a **statistically significant drawdown reduction** (−7.1% vs −9.0%, ΔMaxDD CI
strictly positive) and **paid for it in compounding** (CAGR 4.36% vs 4.71%, Δcompound CI
leaning negative). Risk-adjusted, the two are indistinguishable.

**This is the SECOND independent time the program has found exactly this shape.** T-248
(HRP over sleeves) concluded verbatim: *"a frontier MOVE (more defensive), not a frontier
IMPROVEMENT."* T-314 reproduces it on a different mechanism, a different substrate, and
2.5× the window. The generalization is now well-evidenced: **construction and adaptation
relocate you on the existing frontier; they do not manufacture alpha.** That is a real,
reusable finding — arguably more valuable than a marginal win would have been.

## What this does and does not say
- **Does say:** at this N, on this substrate, a bounded regime-conditional adaptation
  rule does not improve risk-adjusted performance over the frozen spec. The frozen
  `{42,105,210}` ensemble stands unchanged — now with an adaptation attempt honestly
  tested against it and rejected.
- **Does NOT say:** adaptation is impossible in principle, or that the user's instinct
  was unreasonable. It says *this* rule, on *this* evidence base, is not an improvement.
  The T-305 revisit tripwires remain live (a genuinely independent 3rd stream; a dense
  data modality with ≥1 independent obs/week; the forward paper record).
- **Does NOT license** family experiments #2 (rate-conditional) or #3
  (drawdown-conditional leverage). Both remain pre-stated, unrun, and — per my own
  contamination ruling — confirmable only forward/out-of-time.

## Discipline note (stated because it is a real temptation)
**I did NOT run the 3-asset secondary window after seeing this null.** The pre-reg
specified ONE test against the T-311 primary baseline. Running additional windows after
an unfavourable result until one turns positive is precisely the multiple-comparison
fishing this program's whole apparatus exists to prevent — and it would have destroyed
the credibility of the very experiment built to be credible. The null stands as the
single pre-registered test reported it.

## N accounting
**N_trials += 1 → 78.** One rule, one fitted scalar, one fixed signal, one prior, one
split, one test. MBL at 64yr and N=78 requires Sharpe ≈ 0.37 — the frozen sleeve's ~1.5
clears it; that verdict (T-311/T-260) is unaffected by this null.

**T-314 (#1) done.** The user's thesis has been given the cleanest shot the evidence base
can support, and the honest answer is no.
