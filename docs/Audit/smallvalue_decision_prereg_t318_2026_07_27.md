# T-318 — small-value tilt: DECISION-MEASUREMENT PRE-REGISTRATION (DRAFT — awaiting director freeze)

**Date:** 2026-07-27 · **Agent:** C · Branch `feature/smallvalue-decision-t318` · **0 N_trials until frozen** (N += 1 at run)
Decision-support, not an alpha claim. This is the one lane our in-house H0 doesn't touch: **the discovery was ours, the factor literature isn't** — small-value is an externally-replicated factor with a ~100-year record, so the question isn't "can we find an edge" but "**should a 40-year accumulator hold a permanent small-value satellite, eyes open about the regret?**"

## Data reality (measured, 2026-07-27 — the audit before the pre-reg, T-264 discipline)
- **Ken French `6_Portfolios_2x3`: monthly, 1926-07 → 2026-05 (8,704 rows, ~100 years).** `SMALL HiBM` = the small-value corner. Free, academic, the standard series. **Deeper than our ~58-64yr domestic substrate** — genuine rolling-40yr windows are possible (≈60 non-overlapping-ish starts).
- Benchmark leg = the same library's market series (or our T-306 deep SPY substrate for the deployable era) — pre-register ONE and keep it fixed.
- **Honest limits to carry:** (a) these are *paper portfolios* — no fund existed for most of the century; the deployable era begins with real small-value funds (~1990s, e.g. DFA/AVUV-style) and index costs before that are not observable; (b) FF portfolios are cap-weighted academic constructs, **not** the exact holdings of any tradeable fund → a wrapper basis exists (name it, don't hide it).

## The arms (pre-registered, no sweep)
Deployable blends of SPY + small-value (SV), monthly-rebalanced, **net of a 0.25% annual ER on the SV leg** (an honest AVUV-class fee; SPY at 0.0945%):
1. **80/20 SPY/SV**
2. **70/30 SPY/SV**
3. **A post-publication-decay variant** — the same 80/20 with the SV premium haircut to its **post-1993 (Fama-French publication) realized** level rather than the full-sample level, so the decision isn't made on a premium that may no longer exist. (Pre-register the haircut as *measured post-1993 realized*, not a chosen number.)
Baseline for every comparison: **100% SPY** (the max-terminal-wealth north star's benchmark).

## The three reported numbers (the decision metrics — NOT pass/fail gates)
This is decision-support: the deliverable is the **honest distribution**, not a verdict.
1. **Fraction of rolling 40-year windows the blend beats 100% SPY** on terminal wealth (all available start months; report N windows and their overlap honestly).
2. **Log-wealth-ratio 95% CI** — `ln(blend_terminal / SPY_terminal)` across the rolling windows, block-bootstrapped. **CI excluding zero is the "real edge" bar**; the honest prior says it probably won't.
3. **THE REGRET METRIC — worst rolling 15-year RELATIVE drawdown** (`blend / SPY` peak-to-trough over any 15yr span). This is the number the user must consciously accept: a tilt that trails SPY for a decade+ tests even a won't-sell holder. **Report it in dollars per $10k too**, so the regret is concrete rather than abstract.
Also reported: the worst *absolute* 15yr window for each arm, and the SV leg's own MaxDD (small-value crashes harder — 1929-32, 2008 — and the holder must see that before choosing).

## Honest prior (from the strategic review — carried into the pre-reg so results can't drift)
**~50-55% nominal beat, ~15-20% that the CI excludes zero.** This is a **"small permanent satellite, eyes open"** decision — *not* an alpha claim, *not* a robo-beat, and *not* something the sleeve depends on. A coin-flip-plus outcome with a wide CI is the EXPECTED result; the value of running it is that the user makes the tilt decision with the regret number in hand rather than on factor-lore.

## What a result CANNOT be used for (pre-stated)
- It cannot be quoted as an in-house edge (it is an external, replicated, published factor — our N-accounting doesn't own it).
- It cannot justify a *timing* or *sizing* rule on small-value (that would be a new trial and re-opens the H0 vocabulary we closed).
- A positive CI does **not** override `[NN-AI-GATE]`-style deployment discipline: the tilt is a **satellite allocation decision for the user**, not a system change. The deploying sleeve is untouched either way.

## N-accounting
**N_trials += 1 at run** (one measurement, three pre-registered arms reported together — the arms are the decision surface, not a sweep for a winner; no arm is selected post-hoc as "the" result).

**T-318 DRAFT — awaiting director freeze.** Nothing run. On freeze I execute exactly this and report the three numbers.
