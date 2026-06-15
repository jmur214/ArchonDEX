---
name: crisis-defense-both-levers-refuted-2026-06-15
description: Both in-house crisis-defense levers (HMM de-gross overlay T-118r, spot/managed-futures sleeve T-128r) REFUTED on the trustworthy T-167 substrate; what survives and what to buy instead
metadata:
  type: project
---

On the first trustworthy substrate (T-167 re-anchor: 26yr Sharpe 0.751 /
ci_low 0.382 / MDD −33%, base is borderline-real + bull-conditional, Roth-only),
BOTH in-house crisis-defense levers are conclusively REFUTED. This supersedes
all earlier analytical/INVALID-substrate results.

**Lever 1 — HMM transition-trigger de-gross overlay (T-118r, refuted).**
26yr Sharpe 0.752→0.680 (HURT), ci_low 0.370→0.287 (moves AWAY from 0.40),
MaxDD identical −32.6%, terminal wealth on 3.98 < off 5.30 (~25% of cumulative
given up). STRUCTURAL, not a bug: the Δ-trigger de-grosses only slow grinds
(2022 +4.3pp / 2025 +2.9pp), is ABSENT on fast crashes (GFC/COVID +0.0), and
the HMM is dotcom-blind (macro-feature data floor ~2006-04 = the 26yr worst
DD). Pays ~1%/yr calm drag to occasionally blunt 2 slow bears while absent at
the crises that drive the DD. Signal-independent: v1 (AUC 0.49) and crisis
(AUC 0.914) models BOTH reproduce the same failure → the Δ-TRIGGER MECHANISM
is what fails, not signal quality. Transition-trigger family CLOSED per pre-reg.
**Why:** This is the strongest possible "close the family" — a better signal
can't rescue a mechanism that is structurally absent at fast/early crashes.
**How to apply:** Do NOT propose another HMM-gated de-gross variant. A LEVEL-gated
de-gross is disqualified separately (T-105: live 60-bar posterior sits stressed/
crisis 44-50% of the time, p90 run-length 198-265d → recreates always-on-light-
leverage pathology). Any HMM variant is dotcom-capped by the macro data floor.

**Lever 2 — spot/managed-futures crisis sleeve (T-128r, refuted as a HEDGE).**
First trustworthy integrated A/B (anchor-gated 5/5 bitwise). Decision rule FAILS
at criterion 1: integrated MDD cut only 2-7% (vs T-115 analytical +16.2%), and
WORSE in 2008 (−0.954 vs −0.710) + 2020 → NOT a drawdown hedge. Per-arm 26yr:
arm0 0.751/ci_low 0.333/−32.6%; on25 0.897/ci_low 0.501/MDD +0.74pp; on30
0.738/−0.013. Honest nuance: spot @25% lifts base Sharpe 0.751→0.897 + standalone
ci_low 0.333→0.501 (over 0.40) — but via CALM-PERIOD return DIVERSIFICATION, not
crisis protection, and the paired ON−OFF Δ is NOT statistically significant. A
marginal, statistically-soft return-diversifier at one allocation.

**The analytical→integrated collapse is the load-bearing mechanism (T-121).**
Standalone the basket cut its OWN MDD to −26.5% vs SPY −52.4% and beat SPY 8/8
crises (T-108: 2008 +28.6pp, 2022 +35.7pp, COVID +11.0pp); the analytical
partition predicted +16.2% MDD reduction @25% (T-115, no Pareto turn through 30%).
But the INTEGRATED book's %-return is NOT scale-invariant in capital — integer-
share rounding, min_notional, force_min_qty, position caps, and the vol-target
overlay all operate non-linearly on a smaller (75%) book capital pool, eating
~2.7pp/yr (2022). At retail $5K-50K this scale-non-invariance is WORST (smaller
pools hit min-notional/whole-share thresholds more often). So the crisis-alpha
is real in the asset but does not survive integration at retail scale.
**Why:** A diversifier that is a hedge standalone can fail to hedge once it
shares a capital pool with a constraint-heavy book at small AUM.
**How to apply:** When evaluating ANY external sleeve, the integrated A/B (not
the analytical weighted-sum) is the prod-relevant number, and it must be measured
at the actual deployment AUM. Capacity is not the limit here; scale-non-invariance
of the constraint stack is.

**What survives as crisis-defense (the honest residue):**
- safe-f sizing for the −33% MDD (accept the drawdown, size so it's survivable).
  This is the ONLY working "defense" today and it's a sizing decision, not a hedge.
- A SEPARATE-ACCOUNT (not capital-partitioned) managed-futures allocation would
  sidestep the T-121 scale-non-invariance entirely — the sleeve runs on its own
  capital with no shared constraint stack. UNTESTED; would need fresh pre-reg.
  DBMF/KMLM negative-skew (−0.75/−0.85) caps the size (chunky left-tail days).
- The base is dotcom/GFC-exposed structurally; no equity-only/HMM machinery in
  the toolkit cuts the full-cycle −33% MDD.
