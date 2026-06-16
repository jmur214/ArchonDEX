# Session Summary: 2026-06-16 (Agent E — T-172, regime OOS Step 1)

## What was worked on

- **T-172 Step 1**: regime-detector deep-history retrain + leave-one-
  crisis-out OOS generalization test (user-prioritized). Plus the
  paper-lane carryover (combined-candidate scorecard methodology).

## What was decided / built

- **Data-feasibility finding first**: the production model's dotcom-
  blindness is TWO problems — STRUCTURAL (its VIX-term features didn't
  exist in 2000: VIX3M 2007, VIX9D 2011) and FIXABLE (cache depth —
  ^VIX to 1995, yield/credit to 2000, a DGS10 bond proxy). The deep OOS
  test uses a reduced base feature set (the deepest honest common set).
- **Pre-registered** the LOCO test (committed BEFORE running): firing =
  p_crisis≥0.5 sustained 3d with lead>0, FA ≤1/yr, causal p_crisis,
  crisis-state = max-mean-vol, dotcom is the bar.
- **Built + ran** `scripts/regime_oos_loco_t172.py` (deep panel + LOCO
  + causal forward-filter).

## What was learned

- **Generalizes OOS to FAST/credit crises** it didn't train on — GFC
  (333td, FA over budget), COVID (17td sharp), 2022 (108td); calm years
  silent (p_crisis 0.00, not degenerate). The production blindness was
  data-floor + term-features, NOT fundamental.
- **Dotcom (the slow valuation bear) is substantively WEAK** — p>0.5 on
  only 4%/15%/35% of 2000/2001/2002; fires via a brief real spike
  (Apr-2000 Nasdaq crash) then mostly quiet through the 2001 grind.
  Letter-passes the pre-reg, spirit is partial. The slow de-rating
  middle is largely invisible to a vol/credit/curve feature set —
  partly structural.
- **Verdict**: the signal is regime-classification-grade, not
  sharp-timing-grade (why de-gross T-118r failed; why a sleeve SIZER is
  the right use). Crash detection is viable for fast crises (always-on
  is NOT the ceiling there); slow valuation bears stay hard. Step 2
  GATED OPEN but scoped as a fast-crisis regime sizer.

## Pick up next time

- Step 2 is its own pre-registered task (wire detector → dynamic
  MF-sleeve sizing, A/B vs always-on 20% OOS net-of-cost), framed per
  the verdict. Carryovers: paper run cadence (Day-1 OPG-window finding
  stands), combined-candidate scorecard accrues, canonical safe_f on
  `158fe678` when downloaded.

## Files touched

```
docs/Audit/regime_oos_preregistration_t172_2026_06_16.md (locked pre-reg)
scripts/regime_oos_loco_t172.py (new — harness)
data/research/regime_oos_loco_t172.json (results)
docs/Audit/regime_oos_loco_t172_2026_06_16.md (new — verdict)
docs/State/paper_run_scorecard.md (combined-candidate methodology)
```
Measurement-only; no production regime-model swap; no live path.

## Subagents invoked

- None.
