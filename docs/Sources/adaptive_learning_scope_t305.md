---
task_id: T-2026-07-09-305
title: Steelman — what would make strategy-level learning-from-paper honestly testable?
date: 2026-07-09
worker: Agent B
branch: feature/adaptive-learning-scope-t305
status: SCOPING DOC (0 N_trials). A steelman of the user's position, not a defense of the director's and not a capitulation.
---

# T-305 — Can the machine "progressively improve from what does/doesn't work" at the STRATEGY layer, rigorously?

## The disagreement, stated fairly
- **User (flagged 2026-07-09, program doc §P2):** the machine should progressively improve
  from what does and doesn't work. This should not be dismissed.
- **Director:** *strategy-parameter* learning from paper P&L is untestable at our
  signal frequency — the T-152 arithmetic + the MetaLearner/HRP/concentration graves.

Both are correct about different objects, and the whole scoping question turns on
keeping them apart:

> **The real axis is not "learning vs no learning." It is FITTING FREE PARAMETERS
> (a search that overfits at our N) vs VALIDATING A BOUNDED ADAPTATION RULE (fit on
> long history, pre-registered, then FROZEN so the parameters it emits are outputs,
> not fits).** The user's instinct is right and is *already partly shipped* — but only
> in the forms that respect that distinction. The dismissal is only correct for the
> free-fit form.

This doc (1) maps the evidence density that makes free-fitting hopeless today,
(2) catalogs the three graves and *why* each is structural, (3) lays out the
mechanisms that COULD make strategy adaptation rigorous and which we already own,
(4) pre-states the revisit tripwires, and (5) recommends the honest first move.

---

## 1. The evidence-density map — why free-fitting is data-starved by 1–2 orders of magnitude

A daily bar is **not** an independent observation. The deploying sleeve emits only a
handful of genuine long/flat round-trips per asset per year, gated by a 0.10 Carver
dead-band, across 3 *nested* speeds (correlated by construction) and 3 *crisis-correlated*
assets.

| Parameter | Frozen value | Learned or frozen-by-construction? | Independent obs/yr informing it |
|---|---|---|---|
| Ensemble speeds `[42,105,210]`d | {2,5,10}mo | selected (spec-search) | ~1–2 round-trips/yr (10mo) … ~4–6/yr (2mo); nested → **a few independent transitions/asset/yr**. Lookback dispersion is huge: Sortino range **0.401**, "100–350 bps/yr is spec-selection." |
| Asset weights | equal 1/3 | **frozen by fiat** (never learned) | 3 assets, crisis-correlated → **~1–2 independent weight-relevant obs/yr** |
| Damping band **B=2/3** *(offense arm only)* | 2/3 | **quantization-forced, "not tuned"** | ~16 re-entry events/yr (SPY leg), 89% single-increment |
| Exposure cap **2×** *(offense arm only)* | 2.0 | selected | **tail-only: ~1–2 crisis episodes/decade** |

Two facts kill the free-fit story before it starts:
1. **The deploying sleeve has only two knobs, and both are frozen by construction**
   (equal weights by fiat; speeds selected once, not adapted). The damper and cap
   belong to the *not-yet-deployed* offense arm. There is almost nothing to "learn"
   on the live config that isn't already a pre-registered constant.
2. **The tail parameters are informed by ~4 independent crisis episodes in 26 years**
   (dotcom / GFC / COVID / 2022) ≈ 1.5/decade. You cannot fit a crisis-conditional
   parameter from ~4 points. This is the [NN-MBL] wall restated in event-count terms.

**Where pooling is REAL vs FAKE replication** (the load-bearing distinction for any
"multiply the N" argument):
- **FAKE (counts correlated bets twice):** the 3 nested speeds on one price series;
  the 3 sleeve assets that co-fall in crises; HRP's 2 sleeves (carry is corr 0.44 to
  trend — "not a clean 3rd stream," T-263). Pooling these inflates apparent N without
  adding information — exactly the trap DSR's honest-N rule exists to block.
- **REAL (adds information):** genuinely-independent markets/instruments; **regime-pooled**
  observations across history *within* a regime type; and — the one genuinely new lever
  — a **denser data modality** whose signal arrives faster than price round-trips (see §3).

**Forward paper track:** account-1 is **~3 days old** (2026-07-08/09/10) against a
**≥60-day / ≥100-fill** promotion bar. Project doctrine already draws the line here:
"ALPHA validity is NOT paper-learnable — 60 days is statistical noise on alpha; the
robust paper outputs are per-EVENT-RATE measurements." That sentence is the whole
answer in miniature — see §3/§5.

---

## 2. The failure catalog — all three graves died STRUCTURAL, in two distinct kinds

| Grave | What it learned | Killed by | Kind |
|---|---|---|---|
| **MetaLearner (T-149)** | non-linear regime-conditional edge combiner | GBM−ridge = **−0.00251**, SPA p=0.595, ci straddles 0 — worse than the null combiner | **ceiling-set-by-inputs** |
| **HRP (T-248 / earlier edge-level)** | cross-sleeve risk budget | Sortino **2.10 vs 2.23** naive (a frontier *move*, not improvement); edge-level 0.740 vs 1.624 (~5× noise) | **ceiling-set-by-inputs** |
| **Concentration (T-241)** | select top-K conviction over diversify | idiosyncratic α **−2.91%, t_HAC −0.19** — residual IS market beta | **point-estimate-is-negative** |

**Two kinds, and only one even *has* a frequency lever:**
- **Ceiling-set-by-inputs** (MetaLearner, HRP): the learner worked; the *material* it
  learned over was the binding constraint. MetaLearner's own footnote: "combination
  quality was never the binding constraint; signal quality is." HRP: "construction
  cannot manufacture alpha that isn't in the sleeves." → **More paper P&L cannot help;
  more/better *edges or sleeves* might.** This is a BREADTH problem, not a FREQUENCY
  problem — and it is the only crack the steelman legitimately lives in.
- **Point-estimate-is-negative** (Concentration): the thing being learned toward does
  not exist (the residual is beta). More data only tightens a CI around a negative.
  No lever.

**The T-152 theorem that explains *why* the frequency lever is generally unavailable:**
at ~6bp edge on ~80bp daily vol, a 50% edge decay shifts the daily mean only **~0.04σ**
— undetectable inside a quarter at a sane false-alarm rate (a vol *doubling*, by
contrast, is caught in 13–16 days). And every parameter refit is itself an N_trials
increment, raising the DSR bar via `T ≥ 2·ln(N)/SR²` faster than paper trading grows T.
Paper P&L is thus **too slow AND too self-penalizing** to close a parameter-learning
loop — structurally, not just currently.

---

## 3. Mechanisms that COULD make strategy adaptation rigorous — and which we already own

Ranked by how honest each is at our N.

**A. Validate the RULE, not the parameters (the strongest; already our discipline).**
Learn an adaptation *rule* with a small, fixed number of degrees of freedom on the
multi-decade substrate, PRE-REGISTER it, FREEZE it, then run — the parameters it emits
each period are outputs of a validated rule, not fits. We already do the falsification
half of this: the **walk-forward / LOCO gate** (`regime_oos_loco_t172.py`) validates the
*mechanism* OOS and has already *falsified* the one regime-conditional adaptation tested
(in-sample −0.15 → OOS **−0.50**). The missing half is a substrate long enough to
validate a rule *and still hold out decades* — blocked on the multi-decade extension
(T-050 / Norgate, user-deferred).

**B. The Governor is the existing proof-of-concept — and reveals an honest asymmetry.**
Engine F already "learns from what doesn't work": SR<0 → weight 0; −25% MDD → kill;
±15%/cycle cap; ≥50 trades / ≥30 days evidence; EMA halflife 15d. It is a *validated
rule that adapts weights defensively.* But note what it can and can't do:
- **Killing is cheap and already works** — a −25% MDD is an unambiguous signal; the
  machine downgrades on validated evidence *today*.
- **Promoting/improving is expensive** — turning something ON or up requires clearing
  the discovery gates (backtest→PBO→WFO→significance), which have promoted **ZERO edges
  in project history.**
> **So the user's instinct is already satisfied in the defensive direction and is only
> blocked in the offensive direction.** "The machine progressively improves from what
> DOESN'T work" — that's the kill path, and it's live. "…from what DOES work" — that's
> promotion, and it's gated by DSR, which is gated by the substrate. The honest reframe
> is not "learning is untestable" but "*up-weighting* is DSR-bound; *down-weighting* is not."

**C. Cross-sectional / regime pooling — real only where replication is real.** Pooling
multiplies N *only* across genuinely-independent units (§1). Today we have neither the
independent sleeve breadth (carry corr 0.44) nor enough tail episodes (~4/26yr) for
regime-conditional fitting. This lever opens with breadth, not with time.

**D. Bayesian shrinkage toward the frozen spec (the bridge form).** Frame any adaptation
as a *bounded perturbation* of the frozen pre-registered spec, with pre-registered priors
— a re-fit becomes a small, constrained deviation (few effective DoF), which keeps the
N_trials inflation minimal and the DSR bar low. This is the principled way to let the
machine "nudge" without free-fitting. It exists in our aggregator machinery (ridge/
shrinkage) and the literature (JKP hierarchical shrinkage; Kelly-Malamud-Zhou: OOS Sharpe
rises with parameterization *only when shrinkage is applied correctly*) but is **not yet
shipped as a meta-validated adaptation rule.** It is the most promising *new* build.

**E. A denser data modality changes the arithmetic (the genuine opening).** The T-152
wall is a *frequency* wall: price round-trips are sparse. A modality that emits
strategy-relevant signal *daily and independently* — news/event flow (the info-layer
program, P2.4 event-interpreter) — could raise the independent-observation count by an
order of magnitude, moving some questions from "undetectable in a quarter" to
"estimable in a quarter." This is the one lever that attacks the density constraint
head-on rather than waiting on calendar time. **It is exactly what the info-layer program
is building** — which is why the honest place to *revisit* strategy learning is after
that substrate accrues, not now.

---

## 4. Revisit tripwires — pre-stated, so this stays a live question with a trigger

The verdict "not now" flips to "pre-register an experiment" when ANY of these is met.
Stated as measurable conditions, not vibes:

1. **Multi-decade substrate lands (T-050):** ≥ ~50yr honest substrate → enough tail
   episodes (≥ ~8–10 independent crises) to meta-validate a regime-conditional rule and
   still hold out decades. *Primary tripwire.*
2. **Breadth reaches honest pooling:** ≥ 3 sleeves / return streams with pairwise |corr|
   < ~0.3 across crises (a genuinely independent 3rd+ stream — the still-unfilled "awaits
   3rd" from T-248/T-263). Enables cross-sectional weight learning.
3. **A dense modality proves independent signal:** the info-layer news/event panel
   demonstrates ≥ ~1 independent, strategy-relevant, forward-scoreable observation per
   *week* (vs the price track's few per *year*) with a Brier/IC that clears its own
   pre-registered bar. Then the density arithmetic supports higher-frequency adaptation.
4. **Paper track reaches its own bar:** ≥ 60 trading days AND ≥ 100 auction fills on the
   live account — at which point *per-event-rate* learning (not P&L) is statistically
   real (this one is near — days, not years).

If none are met, the question stays parked-but-live; each tripwire has an owner-check at
the next substrate/breadth/modality milestone.

---

## 5. Recommendation

**No strategy-PARAMETER-learning experiment is pre-registerable today** — it would fail
the same gates the three graves failed, for the same structural reasons, and §1's counts
show the live sleeve has almost nothing free to fit. Proposing one now would be the
band-aid [NN-AI-GATE] warns against.

Three honest moves instead, in build order:

1. **NOW — extend learning to the ONE layer where it is already dense enough: per-event
   rates, not P&L.** This is the P2.1 execution-learning loop's logic applied one notch
   up: fill rates, slippage, gate-pass/defer rates, reconcile-clean rates are measured
   *every event*, clear their bar in ~60 days, and are governed by a pre-registered
   quarterly refresh (never silent drift). This satisfies "the machine improves from what
   works" on the substrate where it's true, and is the *only* paper-learnable thing at a
   3-day / 60-day horizon. **Recommend: adopt it as the concrete form of the user's
   instinct that ships now.** (Owner overlap with P2.1 — coordinate, don't duplicate.)

2. **NEXT (blocked on T-050) — the pre-registerable strategy experiment, specified now so
   it's ready the day the substrate lands:** *meta-validate ONE bounded adaptation rule.*
   Learn a single regime-conditional exposure-scaling rule (≤ 2 DoF) on decades 1–3,
   FREEZE it, test OOS on held-out decades 4–5; win condition = OOS Sharpe(adaptive) ≥
   OOS Sharpe(frozen-spec) with block-bootstrap ci_low > 0, N_trials pre-charged. This is
   the LOCO discipline generalized from "reject/enable" to "validate-and-freeze." It is
   the honest form of the user's idea — and it is *ready to pre-register the moment
   tripwire #1 fires.*

3. **PARALLEL — build the shrinkage bridge (§3D)** as the general mechanism that lets any
   future adaptation be a bounded perturbation of the frozen spec rather than a free fit,
   so that when tripwires #2/#3 open, adaptation is DSR-affordable by design.

**Bottom line for the user:** you are right — and the machine already improves from what
doesn't work (the Governor kills on validated evidence today). What is genuinely blocked
is improving from what *does* work at the strategy layer, because up-weighting must clear
DSR, which is substrate-bound. That is a *data* limit with named, measurable tripwires
(§4) — not a permanent "no." The info-layer's dense modality (§3E) is the most direct way
to move the wall; the multi-decade substrate is the most decisive. Nothing adaptive ships
without clearing the same gates as everything else. The question is **open, with a
trigger** — not closed.

---
*Grounding: MetaLearner `metalearner_falsification_t149_2026_06_11.md`; HRP
`strategy_riskparity_verdict_t248_2026_06_26.md` + `hrp_slice_3_normalization_2026_05.md`;
Concentration `moonshot_c1_verdict_t241_2026_06_26.md`; T-152 `divergence_monitors_t152_2026_06_11.md`;
[NN-MBL] `NON_NEGOTIABLES.md`; Governor `engine_f_governance/governor.py` + `engine_charters.md`;
LOCO `regime_oos_loco_t172.py` + execution_manual walk-forward section; density
`multispeed_robustness_t260`, `asymmetric_damping_t298`, `sleeve_constructor.py`,
`paper_run_scorecard.md`; P2.1 `info_layer_program_2026_07_07.md §P2`.*
