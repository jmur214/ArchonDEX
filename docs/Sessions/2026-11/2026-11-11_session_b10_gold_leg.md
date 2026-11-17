# Session Summary: 2026-11-11 — B-10 (T-385) permanent 10% gold leg

## What was worked on

- B-10 from the 2026-09-30 frontier program: 90% equity / 10% gold (IAUM fee), monthly rebalance, vs
  1× SPY on paired Δ log terminal wealth.
  - The prereg was committed at `0cc3f56`. The director froze it with all five rulings, recorded as
    amendment 1 at `f702523` before any return was computed.
  - The harness is `scripts/b10_gold_leg.py`; the locks are `tests/test_b10_gold_leg_guards.py`.
  - The verdict is `docs/Audit/b10_gold_leg_verdict_2026-11-11.md`.
- **The verdict is REFUTED, as pre-registered.**
  - 1971–2025: Δ +0.042, CI [−0.341, +0.441].
  - 2000–2025: Δ +0.124, CI [−0.105, +0.367].
  - The MDD clause is met: −55.25 % → −50.02 %, or 5.22 pp.
  - Determinism ×2 is bit-identical (md5 `add5cec0…`).

## What was decided

- The gold leg is T-306 as built: LBMA AM fix → COMEX front-month, which is spot. It is not a GLD →
  IAUM splice. The IAUM fee is applied synthetically.
- Both windows end 2025-12-31 because gold's data ends there. The refutation takes precedence over H1.
  The MDD clause is a W-71 realized-path point value. GLD's 0.40 % fee is a labelled sensitivity,
  computed by T-311's own `robo_returns`.
- The forward twin was out of scope by director ruling, so the verdict gives only a proposal.
  - The proposal tests the drawdown cushion at the next SPY drawdown of 15 % or more. A wealth edge
    cannot be told apart from zero in 3 years (MDE ≈ 4.4 %/yr).

## What was learned

- **pandas 3.0.1 parses CSV dates as `datetime64[us]`.** `asi8 // ns_per_day` silently makes every gap
  1,000× too small, so the native-gap and staleness guards could never fire.
  - The planted-hole lock caught it before the first run.
  - Use `TimedeltaIndex.days`.
- **T-311's `load_substrate` forward-fills gold flat for 73 rows past its last print** (to 2026-04-17).
  T-311's 3-asset arm is affected; the director is logging it in health_check.
- **Gold's hedge value depends on the real-rate regime.** It cut drawdowns in 1973–74 by 9.6 pp, the
  GFC by 5.2 and dotcom by 4.5. It made 1980–82 worse by 2.6 pp and helped little in 2022 (1.7 pp).
- **The wealth Δ comes from one decade's re-pricing.** The 1970s gave +0.25 and the 2000s +0.17,
  offset by the 1980s and 1990s at −0.33.
- The 252-day block barely widened the CI (1.16× on W-71, 0.96× on W-00), against a prediction of
  1.5×. At a 10 % weight, day-to-day noise dominates the differential's variance.
- The GLD check passed (+0.04 %/yr gap against an expected −0.40 %). The residual comes from starting
  inside the April 2020 COMEX/London EFP dislocation; from 2020-06-30 the gap is −0.34 %/yr.

## Pick up next time

- The director reads the verdict and dispatches an independent reviewer. The reviewer reproduces it
  with `python -m scripts.b10_gold_leg --out …` twice and compares md5s.
- Recording the +1 trial in the honest-N count is the director's call (MEDIUM `573fc62`).
- Re-run T-311's 3-asset secondary with end ≤ min(native ends) if that arm is ever quoted again.
- The forward-twin proposal (verdict §9) is propose-first, because it touches `paper_trader/`.

## Files touched

```
docs/Sources/prereg_b10_gold_leg_2026-11-11.md
docs/Audit/b10_gold_leg_verdict_2026-11-11.md
docs/Core/execution_manual.md
docs/Sessions/2026-11/2026-11-11_session_b10_gold_leg.md
scripts/b10_gold_leg.py
scripts/index.md
tests/test_b10_gold_leg_guards.py
.claude/agent-memory/regime-analyst/{MEMORY.md, project_b10_gold_leg_prereg_2026_11_11.md}
```

## Subagents invoked

- None. The regime-analyst lens ran as a single worktree subagent dispatched by the director.

## Addendum — independent review APPROVE, plus a text-only follow-up

- **The review found that the MDD clause had no cash control (MEDIUM).** 90 % equity / 10 % zero-return
  cash gives MDD −51.30 %, a 3.95 pp reduction with no gold.
  - About 3.95 of the 5.22 pp is de-equitization. Gold's own share at the GFC trough is ≈ 1.3 pp.
  - In 2022 gold did worse than the mattress (−22.89 % vs −22.25 %).
  - The cash leg costs ≈ 0.5 log TW over 55 years at 0 % yield.
- **The verdict is restated:** gold is a de-risking leg that costs no wealth, not a distinctive hedge.
  It was clearly distinctive only in 1973–74.
- **The cash control is added as a reviewer diagnostic (§4a).** The director counts N +1, so B-10
  records **N_trials +2**.
- **The forward twin now has a cash twin.** It asks whether gold beats cash by ≥ 1 pp at the next
  ≥ 15 % drawdown. The old "B ≥ 1.5 pp vs SPY" threshold was exactly the cash effect.
- **Low fixes:** 1973–74 is +9.5, not +9.6. The baseline MDD prediction is a miss (−55.25 % against a
  −51 to −55 % range). Turnover is two-sided Σ|Δw|.
- **Four guard-coverage notes added (§7):**
  - G4 is native-index staleness;
  - a frozen-value tail is caught only by G11;
  - the locks test `[us]` only (the reviewer checked other units);
  - the smoke never calls `boot`.
- **Lesson:** a static leg's drawdown benefit must be scored against a same-weight cash leg, never
  against 100 % equity alone. Otherwise the leg gets credit for the de-equitization effect.
