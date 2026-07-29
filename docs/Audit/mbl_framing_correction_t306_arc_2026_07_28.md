---
task_id: T-2026-07-28-correction
title: CORRECTION — my MBL/DSR "CLEARS" framing across the T-306/311/260/314 arc is RETRACTED
date: 2026-07-28
worker: Agent B
status: SELF-CORRECTION. The substantive verdicts STAND (they rested on the right test); the MBL gloss layered on top is retracted as wrong in direction, not merely imprecise.
---

# Correction — I fed MBL the wrong Sharpe, and it pointed the opposite way

The director's audit correction on `multidecade_substrate_scope_t306.md` is right, and
**the same error propagated into three more of my documents.** I am correcting all of
them here rather than waiting to be told again.

## What I claimed
| doc | the sentence |
|---|---|
| T-306 scope | "clears the 24.1yr requirement with a **2.4-2.6× margin** … the only lever that moves the baseline from 'cannot clear DSR' to 'clears with room'" |
| T-311 | "MBL/DSR: N=76, 64yr → required Sharpe 0.367; **sleeve Sharpe 1.516 → CLEARS**" |
| T-260-deep | "MBL: N=77, 64yr → required Sharpe 0.368 vs **ensemble 1.516 → CLEARS**" |
| T-314 | "MBL at 64yr and N=78 requires Sharpe ≈ 0.37 — **the frozen sleeve's ~1.5 clears it**" |

## Why it is wrong
`[NN-MBL]`'s `T ≥ 2·ln(N)/SR²` must be fed **the Sharpe of the edge being CLAIMED**.
I fed it the sleeve's **absolute** Sharpe. For a long/flat equity+bond sleeve the
absolute Sharpe is overwhelmingly **market exposure** — nobody claims beta as skill, and
asking "could a random strategy hit 1.5 absolute Sharpe across 76 trials" does not bear
on whether the sleeve beats a benchmark. The deploy decision rides on the **difference**
(active) return. Measured on the deep 2-asset window (1962-2026, 64.3yr):

| quantity | value |
|---|---|
| absolute Sharpe, sleeve | **1.516** ← what I wrongly fed MBL |
| absolute Sharpe, buy-hold equity | 0.696 |
| **ACTIVE (difference) Sharpe, sleeve − buy-hold** | **−0.210** ← the claimed edge; the correct input |

**So against buy-hold there is no positive edge to clear.** "CLEARS with a 2.4-2.6×
margin" is not an overstatement of a true thing — applied to the decision-relevant
quantity it points **the other way**. Retracted.

**And it contradicted my own headline in the same document.** T-311's finding was *"the
wealth verdict REVERSED — the sleeve LOSES to buy-hold, $1.96M vs $5.73M"*, and four
lines later I wrote *"CLEARS, with margin."* Those cannot both be the takeaway. I should
have caught that before publishing; the director did.

## What is NOT affected (stated precisely, not defensively)
**Every substantive verdict in the arc rested on paired block-bootstrap CIs on
DIFFERENCES — the correct test — not on the MBL sentence.** The MBL gloss was decoration
layered on top. Specifically, these stand unchanged:
- **T-311:** structural drawdown win CONFIRMED (ΔMaxDD vs buy-hold **[+21.2%, +54.2%]**,
  strictly positive); Sortino edge CI-significant (**[+0.544, +1.027]**); **wealth verdict
  REVERSED vs buy-hold** (Δcompound CI straddles, leans −1.7pp/yr). The negative active
  Sharpe above is *consistent with* — indeed another expression of — that reversal.
- **T-260-deep:** ensemble-vs-single ΔSortino **[+0.100, +0.252]** — an
  ensemble-vs-alternative-spec comparison, unaffected by the benchmark question.
- **T-314:** the NULL rests on ΔSortino **[−0.0199, +0.1025]**. Unaffected.

## The corrected standing statement
> The deep substrate's value is that it can test **difference metrics across 8-10
> crises** for the first time — which T-311/T-260/T-314 did. It does **not** license any
> "clears DSR" claim: the sleeve's active Sharpe vs buy-hold is **negative**, and the
> wealth CIs straddle zero. The substrate remains the program's most valuable measurement
> asset for exactly the reason the director stated — and for no more than that.

## The lesson (which generalizes, and is why T-333 matters)
I mistook an **absolute/mechanical** quantity for an **economic edge**. That is the same
class of error T-333 was dispatched to investigate — whether the sleeve's regime-option
verdict is an *arithmetic identity* (a long/flat strategy mechanically earns cash when
flat) rather than a discovery. Having just made the error one level up, I will run T-333
with that specific suspicion foregrounded.

**Action:** retraction banners added to the three audit docs; this note is the canonical
correction. No re-runs required — no result changes, only the framing that was never
supported by the test performed.
