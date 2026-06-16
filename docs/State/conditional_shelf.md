# Conditional Shelf

**Status:** seeded 2026-06-13 (T-166). Mutates in place — add an entry at
every conditional burial; re-test entries when a gating switch is validated.

## What this is

The 2026-06-11 decompose directive (`forward_plan.md`) established that a
strategy killed at the **unconditional** gate is not necessarily dead — it
may be a real **conditional** lift whose activation switch we haven't
validated yet. Burying it as a "uniform-lift miss" throws away the measured
conditional profile. This shelf preserves that profile so the regime layer
(Engine E/F) can shop it the moment a switch is validated.

A shelf entry is NOT a live capability and NOT a recommendation to flip a
flag. It is a recorded, audit-cited hypothesis of the form *"strategy X
helped in regime R and hurt elsewhere; if a switch that detects R is
validated, X becomes a re-test candidate under fresh pre-registration."*

## The one validated switch today

Only **`hmm_p_crisis`** (Engine E HMM combined crisis posterior, causal
`predict_proba_for_row`) is a validated regime switch — AUC 0.887 on the
12-yr causal test, fires 5/5 stress events with 27-60d lead
(`docs/Audit/...engine_e_reversal_predictive...`, T-087; verified causal by
T-089). **Caveat: it is currently cloud-dead** (T-118fc) — wired but not
feeding a live consumer on the cloud path. So every shelf entry that gates
on it is **"armed when the switch is live,"** not deployable today. No other
switch (VVIX-z was NO-GO per T-087; dwell-time monitors can't see alpha
decay per T-152) is validated.

## Convention — how an entry is ADDED and RE-TESTED

**ADD (at burial).** When a measurement kills a strategy as a uniform lift
but the per-regime / per-year breakdown shows it helped somewhere and hurt
elsewhere, record one entry here in the same session as the burial. Required
fields: (a) **measured profile** — where it helped / hurt, with the audit
numbers and the audit filename; (b) **named activation condition** — the
regime/account/AUM state under which it's a candidate; (c) **capacity
ceiling** if known; (d) **gating switch** it would key on (today: only
`hmm_p_crisis`, or "none validated yet"). Quote audit numbers; never
paraphrase from memory.

**RE-TEST (when a switch validates).** A shelf entry is re-tested only via a
**fresh pre-registration** (hypothesis + threshold + N_trials consumed,
written before the run, per CLAUDE.md #7). The conditional re-test is a NEW
measurement and **consumes honest-N** — the shelf does not grant a free pass.
The re-test question is narrower than the original: not "does X lift
unconditionally" but "does X lift WHEN the validated switch says regime R,"
and the gate is still `ci_low > 0` on the conditional sub-sample (with the
sub-sample's MBL checked — conditioning shrinks N). This is the T-118b
template: the gate never loosens; the QUESTION changes.

**Gates never loosen.** Being on the shelf is not evidence. An entry leaves
the shelf only by (i) clearing a fresh conditional pre-registration → promote,
or (ii) failing it → retire to `docs/Archive/` with the negative result
recorded.

---

## Seed entries

### 1. Regime-conditional vol-target (Engine B) — `hmm_p_crisis`-gated

**Measured profile.** The vol-target overlay is a volatility-cluster
rescue that decays monotonically as the window lengthened and rigor rose:

| Stage | Δ Sharpe | ci_low | Verdict | Source |
|---|---|---|---|---|
| 5-yr Alpaca-only (T-055e) | **+0.549** | **+0.047** | DEFENSIBLE (cleared #6) | `engine_b_vol_target_regime_conditional_t055e_2026_05_23.md` |
| extended substrate, 75-cell (T-055g) | +0.413 | **−0.177** | no arm clears ci_low>0 | `vol_target_multiplier_sensitivity_t055g_2026_05_24.md` |
| 12-yr MBL window (T-055h) | **−0.214** | **−0.688** | CHAPTER CLOSED | `vol_target_12yr_verify_t055h_2026_05_29.md` |

Per-year signature (the conditional core, T-055e/T-055g): **2024 = rescue**
(+1.564 Δ on Alpaca; +0.221 on extended), **2025 = trap** (−0.198 on Alpaca
vs the rolling-60d −0.942 it eliminated; but −0.390 on extended — every arm
loses 2025). The mechanism: it helps when a vol cluster spikes faster than
the OFF book's rolling-60d can react (2024-style); it hurts in choppy
whipsaw where targeting de-risks into the reversal (2025-style).

**Activation condition.** Crisis-onset volatility clustering — a sharp
vol-regime transition, NOT steady chop. `hmm_p_crisis` rising through its
threshold is the candidate trigger; the 2025 trap is precisely the
"elevated-but-not-transitioning" state the switch must exclude.

**Capacity ceiling.** Engine-B overlay on the existing book; no added
capital, no capacity constraint of its own.

**Gating switch.** `hmm_p_crisis` (armed when live). Re-test question: does
the overlay lift `ci_low > 0` *restricted to bars where `hmm_p_crisis` is
above threshold*?

---

### 2. Confidence-gated execution (N≥3) — weak-base-regime-gated

**Measured profile.** A regime-dependent floor-raiser: it raises the floor
when the base book is weak and clips the ceiling when the base is strong.

| Stage | Δ Sharpe | ci_low | Verdict | Source |
|---|---|---|---|---|
| 5-yr Alpaca-only (T-057) | **+0.793** | — | "strongest lift ever" (artifact) | `confidence_gated_execution_2026_05_12.md` |
| extended substrate (T-057b) | **−0.075** | −0.532 iid / −1.154 block | DEFER | `confidence_gated_flag_flip_t057b_2026_05_24.md` |
| 12-yr MBL window (T-053b) | **−0.128** | — (p(Δ>0)=32%) | REFUTED | `multi_year_window_harness_t053b_2026_05_25.md` |

Per-year signature (T-057b, the conditional core): gate **HELPED when OFF
was weak/negative** — 2021 +0.722 (OFF very weak), 2024 +1.432 (OFF
negative); gate **HURT when OFF was strong** — 2022 −1.787, 2023 −1.131 (OFF
very strong both years). The net wash across the cycle is exactly what a
floor-raiser-ceiling-clipper produces when averaged over mixed regimes.

**Activation condition.** Predicted-weak-base regime — the state where the
unconditional book is expected to be weak or negative (2021/2024-type). This
is the inverse-correlated cousin of entry #1's trigger: confidence-gating
pays off in the same low-base-Sharpe states a crisis switch flags.

**Capacity ceiling.** Execution-layer change (N≥3 signal confirmation); no
capital/capacity constraint.

**Gating switch.** `hmm_p_crisis` as a proxy for the weak-base state (armed
when live), OR a future validated predicted-base-Sharpe state. Re-test:
does the gate lift `ci_low > 0` restricted to predicted-weak-base bars?

---

### 3. The base book itself — bull-conditional (the "bull machine missing a switch")

**Measured profile.** The 6-edge base ensemble is the largest conditional
strategy on the shelf — it is itself bull-conditional, and the 16-yr/26-yr
split IS the conditional profile (`deep_substrate_baseline_t092_2026_05_31.md`,
canons since re-anchored deterministic by T-140/T-155):

| Window | Sharpe | ci_low | CAGR | MDD | Contains |
|---|---|---|---|---|---|
| 16-yr 2010-2025 (crisis-free) | **1.018** (det. 1.021) | **+0.560** | +11.00% | −15.4% | no GFC, no dot-com |
| 26-yr 2000-2025 (crisis-inclusive) | **0.246** (det. 0.237) | **−0.119** | +2.64% | −59.3% | + 2008 GFC + 2000-02 dot-com |

The book clears every gate on the crisis-free window and fails every gate
the moment 2008 + the dot-com crash enter. It is a bull machine with no
crisis defense — the −59.3% MDD on 26-yr is the unhedged tail.

**Activation condition.** This is the meta-entry: the book is "always on,"
so the conditional is inverted — it needs a crisis **kill/de-gross switch**
to flatten or reduce in 2008/dot-com-type regimes, converting the 26-yr
−0.119 ci_low toward the 16-yr profile. The named condition is `hmm_p_crisis`
crossing its de-gross threshold.

**Capacity ceiling.** The production book; retail-AUM scale ($5-15K) per the
deployment context.

**Gating switch.** `hmm_p_crisis` de-gross (armed when live). This is the
single most fork-relevant entry: it is the switch the whole engines-first
program has been circling. Re-test: does a `hmm_p_crisis`-driven de-gross
overlay lift 26-yr `ci_low` above 0 / cut the −59.3% MDD without giving back
the 16-yr bull return?

---

### 4. Spot 8-ETF crisis-diversifier sleeve — `hmm_p_crisis`-gated additive sleeve

**Measured profile.** A cross-asset diversified-trend ETF basket
(SPY/TLT/GLD/USO/UUP/EEM/IEF/DBC) that is a crisis-alpha diversifier, NOT a
uniform lift (`managed_futures_trend_t108...`, `dbmf_kmlm_managed_futures_t110_2026_06_05.md`,
`spot_basket_extended_sweep_t115...`). On the 17.9-yr deep window the spot
basket @ 25% cleared the strict gate — **MDD reduction +16.2% (+8.55pp
absolute), calm-Sharpe-Δ +0.197, Sharpe ci_low Δ +0.083, CAGR +0.64pp** (the
Pareto curve never turned through 30%). BUT the integrated path is the open
question: T-120/T-121 found engine-side capital-scale-dependence runs
**negative** (the analytical partition isn't scale-invariant), and the
T-128 + 2026-06-12 relaunch A/B is **INVALID** — substrate nondeterminism
(arm0 16-yr drew the minority attractor;
`spot_sleeve_closeout_relaunch_2026_06_12.md`). So the conditional profile is
**measured analytically (crisis-helps/calm-mild) but not confirmed in the
integrated engine**.

**Activation condition.** Crisis regime — the basket's help concentrates in
2008/2020/2022 flashes (per-window T-108 confirmed 8/8 crisis wins); its
drag is the calm-stretch carry cost. `hmm_p_crisis` is the natural trigger
to scale the sleeve up entering crisis.

**Capacity ceiling.** Spot basket = 8 liquid ETFs, no meaningful retail
capacity limit. The DBMF/KMLM single-product variants have ~5-yr history
(shallower evidence) and ~0.9% ER drag — capacity fine, evidence-depth is
the limit there.

**Gating switch.** `hmm_p_crisis` to scale sleeve allocation (armed when
live). Re-test is double-blocked: needs (i) the determinism dispatch to fix
the cloud substrate so the integrated A/B is valid, THEN (ii) a fresh
conditional pre-registration. Until (i), this entry cannot even be
unconditionally re-measured.

**UPDATE 2026-06-15.** Both blocks resolved, opposite ways. (i) Determinism
FIXED (cov-pin, T-140-fu3) + substrate re-anchored (T-167). (ii) The
INTEGRATED **in-house capital-partitioned** sleeve was re-tested and
**REFUTED** (T-128r: 2-7% MDD cut not +16.2%, worse in 2008 — the analytical
partition is not scale-invariant, T-120/121 mechanism confirmed). BUT the
**separate-account BOUGHT** variant (own capital, no shared constraint stack)
escapes that mechanism and is **VALIDATED as an always-on floor** — see entry
#5. So this entry's IN-HOUSE form is retired-to-Archive-eligible; its
crisis-diversifier thesis lives on in the bought form. (Numbers in entries
#3 here predate the T-167 re-anchor — 26-yr is 0.751/−33% MDD, not
0.246/−59.3%; CURRENT_STATE is the live truth.)

---

### 5. Dynamic MF-sleeve sizing — the AMPLIFIER on the always-on bought sleeve (the one shelf entry whose FLOOR already works)

**Measured profile.** Unlike entries #1-4 (strategies killed at the
*unconditional* gate), this entry's unconditional version WORKS: the always-on
20% bought managed-futures **separate-account** sleeve is a validated
drawdown-defense — T-170 (recent: MDD −7.5%→−5.6%, +25.1%; 2022 DBMF
+32.7%/KMLM +48.8%) + T-171 (deep, net-of-haircut via the free AQR TSMOM
proxy — **director-corrected**: dotcom −19.0%→−11.8%/−13.5% (clears ≥25% both
haircuts); GFC −30.2%→−21.9%/−23.6% (clears the PRIMARY haircut, FAILS the
conservative — **haircut-FRAGILE at 20%**; 30% needed for a robust GFC cut)).
It is a measured DRAWDOWN-defense, NOT a proven Sharpe-lifter (ci_low
indeterminate on thin crisis samples), and an OPTIMISTIC ceiling (real
DBMF/KMLM replication distorts crisis shape vs the pure factor). *(T-171's
original combined-MDD cells were ~2× overstated by a combination bug — caught
by adversarial verification + independent director recompute; fix = T-173.)* The CONDITIONAL hypothesis (the amplifier): dynamically
SIZE the sleeve by a validated crisis signal — heavier when crisis-probability
is high, lighter in clear bull — to recover the bull-market upside the fixed
20% concedes, without losing the protection.

**Activation condition.** A regime detector that clears the OOS-generalization
bar: fires with lead on a crisis TYPE it did NOT train on, AND a dynamic-sized
sleeve beats always-on 20% net-of-cost OUT-of-sample. (Not "fires before
2018/2022" — that is in-sample-era cheap.)

**Capacity ceiling.** Separate-account bought ETF (DBMF/KMLM), ~0.9% ER;
retail-AUM fine.

**Gating switch.** `hmm_p_crisis` is predictive (T-087/089) but does NOT yet
clear the bar (dotcom-blind, T-118r). **T-172 tests whether a deep-history
re-train fixes generalization.** Same family as the de-gross overlay (T-118r
REFUTED) but a **DIFFERENT action — size the BOUGHT sleeve, not de-gross the
equity book** — so the de-gross failure does not pre-doom it, but the
dotcom-blindness must be fixed first. Re-test: does a `hmm_p_crisis`-sized
sleeve beat always-on 20%, OOS, net-of-cost, on a held-out crisis?

---

## Not-yet-shelved candidates (flagged, not seeded — need an audit re-read)

- **`value_book_to_market_v1`** — flagged possibly-regime-conditional
  (+$2,081 5-yr cumulative but $3,006 from 2021 alone → net −$925 ex-2021)
  in `2024_attribution_dive_2026_05_12.md` (T-044 candidate). Not seeded:
  it's a single-edge lifecycle question for Engine F, not a switchable
  overlay, and the conditional profile isn't cleanly measured yet.

## Cross-references

- Decompose directive: `docs/State/forward_plan.md` (2026-06-11 block) +
  `[[feedback_decompose_dont_require_allweather_2026_06_11]]`
- Validated switch: T-087 reversal (`hmm_p_crisis` AUC 0.887); cloud-dead
  status per T-118fc.
- Re-test template: T-118b pre-registration discipline.
