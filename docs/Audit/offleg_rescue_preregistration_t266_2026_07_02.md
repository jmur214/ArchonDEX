---
title: "Off-leg RESCUE A/B — PRE-REGISTRATION (family N=2, FINAL; frozen before running)"
task: T-2026-07-02-266
status: pre-registered (committed BEFORE the run)
---

# T-266 — off-leg RESCUE (2022-aware duration-trend gate) — FROZEN PRE-REGISTRATION

**Off-leg family trial N=2 — FINAL.** User-approved rescue of the T-259 off-leg
(which was REFUTED: point-favorable but not significant, and it degraded 2022 by
−0.53pp because 12-month momentum held IEF into the bond crash). **Whatever the
verdict, the off-leg family CLOSES after this.** Fresh trial: N_trials += 1. This
doc is committed BEFORE any result is seen; the spec below is immutable.

## The failure this fixes (diagnosis)
T-259's flat leg = argmax-12mo-momentum{BIL, IEF}. IEF's 12-month total return
stayed positive into early 2022 (a 2020–21 bond bull), so the off-leg held IEF as
the 2022 crash began → it caught the drawdown → the 2022 hard gate failed. The lag
is the whole problem: a 12-month filter cannot exit a fast bond selloff in time.

## THE SPEC (ONE, immutable — my design, frozen)
Identical to the T-259 off-leg EXCEPT one added eligibility gate on IEF:

1. **Base selection (unchanged from T-259):** sel = IEF iff (IEF 12mo total return
   > BIL 12mo total return AND IEF 12mo return > 0), else BIL.
2. **NEW fast duration-trend eligibility gate:** IEF is actually held ONLY IF the
   base selection is IEF **AND** IEF's price is above its **63-trading-day
   (3-month) simple moving average** as-of the decision date (`TrendOverlay(63)` on
   IEF — the system's own trend rule, at a fast/quarterly lookback, 4× faster than
   the failed 12-month). If IEF fails the 63d trend gate → hold **BIL** (T-bills).
3. Everything else INHERITED UNCHANGED from the T-255 fair harness + the T-259 A/B:
   menu {BIL, IEF} (GLD excluded — long-leg asset), causal (position over t+1 =
   signal_t), off-leg rotation charged 1.5 bps, flat instruments from
   `data/processed/tr_reconciled/`. The ONLY change vs T-259 is the 63d IEF gate.

No sweep: ONE fast lookback (63 td), ONE menu, ONE base rule. The 63d choice is
the canonical fast (quarterly) trend and is fixed before running — not tuned.

Economic frame (honest): this reclaims **duration BETA only when duration is
actually trending up** — legitimate for beat-the-robo, NOT an alpha claim
(consistent with T-247/T-263: carry/duration is beta).

## Comparison + GATES (same as T-259, frozen)
**A/B:** rescue off-leg sleeve (candidate) vs the **cash-off-leg fair sleeve**
(control), SAME sleeve/harness, differing ONLY in the flat leg. Window = where the
off-leg is fully defined (both 12mo momenta + the 63d SMA exist) — the fail-closed
floor, no silent cash fallback.

| Gate | Threshold |
|---|---|
| **Primary — paired ΔSortino** | block-bootstrap `ci_low(Sortino_rescue − Sortino_cash) > 0` |
| **Δterminal-wealth** | paired `ci_low(ΔlnWealth or Δterminal) > 0` |
| **2022 must-NOT-degrade (HARD)** | rescue 2022 MaxDD ≥ control − 0.5pp AND 2022 return ≥ control − 0.5pp |
| **MBL** | `[NN-MBL]`: N_trials += 1; window Sharpe ≥ `sqrt(2·ln(N)/years)` |
| **Fail-closed** | `[NN-FAIL-CLOSED]`: missing input on a flat bar → FAIL, never silent cash |

**Decision rule.** PASS = paired ΔSortino ci_low > 0 **AND** Δwealth ci_low > 0
**AND** 2022 does not degrade. If PASS → a real spec-change candidate for the
deploying sleeve (USER decision). If any fails → **the off-leg family closes with
evidence** (N=2 exhausted). No partial credit, no threshold relaxation, no third
trial.
