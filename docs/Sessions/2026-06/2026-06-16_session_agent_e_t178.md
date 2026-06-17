# Session Summary: 2026-06-16 (Agent E — T-178, regime Step 2 + safe_f)

## What was worked on

- **T-178**: regime Step 2 (greenlit-with-caveats) — the dynamic
  MF-sleeve sizer A/B vs always-on 20%; plus the canonical deep-window
  safe_f.

## What was decided / built

- **Canonical safe_f = 0.928** on the 158fe678 26yr curve (MDD −33%,
  mdd95@f1 21.3%) → live size cap min(1, safe_f) = 0.928. Supersedes
  benign-2024 1.602 and the 12yr-interim 1.104.
- **Pre-registered** the sizer A/B with the verification caveats baked
  in (held-out calm 2013-2019, fast-crisis framing, fixed-params causal
  filter, margined operating point), committed before running.
- **Built + ran** `scripts/regime_sleeve_sizer_t178.py` (HMM train
  2000-2012, OOS 2013-2025, dynamic x vs always-on 20%, monthly,
  net-of-cost, raw + 0.5× AQR haircut).

## What was learned (honest negative)

- **The dynamic sizer does NOT beat always-on 20%** OOS net-of-cost:
  Δsharpe +0.03 raw / +0.00 haircut, ΔMDD −0.4pp (worse), hurts the
  2022 grind. **Always-on 20% is the deployable ceiling — don't deploy
  the timer.**
- **Specificity is excellent** — held-out-calm 2013-2019: p_crisis>0.5
  in 0/84 months (the required genuinely-OOS check passes with margin,
  fixing T-172's in-sample FA).
- **The honest caveat**: the negative isn't a false-alarm problem or a
  wrong detector — the OOS window (2013-2025) is bull-dominated with one
  brief V-shaped fast crisis (COVID), underpowered for the sizer's use
  case. Still a deploy-NO: we don't ship a timer that doesn't beat the
  simple baseline on the evidence we have. Consistent with T-172
  (regime-grade not timing-grade) + T-118r.

## Pick up next time

- Regime crash-timing lane closes here on the honest evidence:
  always-on 20% is the sleeve. A future deep-OOS window with a sustained
  fast crisis could re-open it under fresh pre-registration. The live
  levers remain the bought-MF floor + new alpha.
- Carryovers: paper run cadence; the combined-candidate line now uses
  the fixed 20% (not a dynamic sizer); safe_f gate = 0.928.

## Files touched

```
docs/Audit/regime_sleeve_sizer_preregistration_t178_2026_06_16.md (locked pre-reg)
scripts/regime_sleeve_sizer_t178.py (new — A/B harness)
data/research/regime_sleeve_sizer_t178.json (results)
docs/Audit/regime_sleeve_sizer_t178_2026_06_16.md (new — verdict)
docs/State/paper_run_scorecard.md (canonical safe_f + sizer ceiling)
```
Measurement-only; no production swap; no live path.

## Subagents invoked

- None.
