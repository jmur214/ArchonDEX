---
title: "Wave 1.1 off-leg A/B — PRE-REGISTRATION (design only; runs on T-255's fair harness)"
task: T-2026-07-02-258
status: pre-registered (NOT run)
---

# T-258 Wave 1.1 — the OFF-LEG A/B (pre-registration)

**This is a pre-registration ONLY. Nothing is run here.** It executes exactly
once, unchanged, on **D/T-255's fair sleeve harness** after that lands (per
`[NN-MBL]`: hypothesis + threshold + N_trials written BEFORE the run). Running
it on the current (biased) sleeve harness would measure against a broken
yardstick — see the 2026-07-02 gap audit (`docs/Sources/whole_project_gap_audit_2026_07_02.md`,
Parts 2–3: the flat-leg earned 0% and understated the sleeve ~0.65%/yr).

## Motivation (honest framing — this is BETA, not alpha)

The trend sleeve (T-236) holds each asset long when price > its 5-month trend,
else **flat at 0%/cash**. That 0% flat leg forgoes the return cash actually
earns. This A/B replaces it with a momentum-selected short-duration off-leg.

**This reclaims duration/term-premium BETA — it is NOT alpha, and the
pre-registration says so up front** (consistent with the T-247 verdict:
carry-on-bonds is duration beta, alpha_t_hac 0.815 < 2, `carry_gauntlet_t247.json`).
Reclaiming a beta the cash-off-leg forgoes is nonetheless **legitimate for the
beat-the-robo objective** — the robo's own return is largely duration/equity
beta, so harvesting the off-leg's term premium is a fair way to close the
~1%/yr wealth gap without any alpha claim. The gate is the same honest bar; we
simply expect a beta improvement, not an edge.

**Prior: MEDIUM.** The mechanism is mechanical (hold bills when duration falls,
short-duration Treasuries when it rises); the risk is that it reintroduces the
2022 duration drawdown the flat leg avoided — which is exactly why 2022 is a
named must-not-degrade gate below.

## THE SPEC (ONE spec, NO sweep — pre-registered, immutable)

When a sleeve asset (SPY / AGG / GLD) is FLAT on a given bar, its weight is
allocated to the off-leg as follows:

1. **Menu:** `{BIL, IEF}` — T-bills (BIL) vs 7–10y Treasuries (IEF). *GLD is
   deliberately EXCLUDED from the menu* — it is already a long-leg sleeve asset,
   so including it would double-count gold exposure.
2. **Selection:** hold the **argmax of trailing 12-month (252-trading-day) total
   return** over the menu, computed as-of the decision date (causal; the
   position over day *t+1* uses momentum through day *t*).
3. **Absolute-momentum gate:** the selected instrument is held ONLY if its own
   trailing 12-month return is **> 0**; otherwise hold **BIL** (T-bills) as the
   safe default. (BIL's own return is ~the cash rate, so "BIL vs positive-IEF"
   is the operative choice.)
4. No other parameters. ONE lookback (252 td), ONE menu, ONE absolute gate (>0).
   No optimization over lookback, menu, or threshold — a single-shot test.

Everything else (universe SPY/AGG/GLD, 5-month long/flat trend rule, rebalance
cadence, cost model) is INHERITED UNCHANGED from T-255's fair sleeve harness.
The only change under test is flat-leg = {BIL,IEF}-momentum instead of 0%/cash.

## Comparison + GATES (pre-registered thresholds)

**A/B:** off-leg sleeve (candidate) vs the **cash-off-leg sleeve** (control) —
the SAME sleeve on the SAME fair harness, differing ONLY in the flat leg.

| Gate | Threshold | Rationale |
|---|---|---|
| **Primary — paired ΔSortino** | block-bootstrap `ci_low(Sortino_offleg − Sortino_cash) > 0` | `[NN-SHARPE-CI]`; the tail-first objective (Sortino, not Sharpe) |
| **Δterminal-wealth** | paired `ci_low(ΔlnWealth) > 0` | the off-leg's whole point is to close the ~1%/yr wealth gap |
| **2022 must-NOT-degrade (NAMED HARD GATE)** | off-leg sleeve's **2022 MaxDD ≥ cash sleeve's − 0.5pp** AND **2022 return ≥ cash sleeve's − 0.5pp** | the off-leg must not reintroduce the duration drawdown the flat leg avoided (2022 = the −16% AGG-crash year). A degrade here FAILS the whole A/B regardless of the full-window lift |
| **MBL** | `[NN-MBL]`: **N_trials += 1**; sleeve-window Sharpe ≥ `sqrt(2·ln(N)/years)` at honest N | conditioning/adding a leg consumes honest-N |
| **Fail-closed** | `[NN-FAIL-CLOSED]`: missing BIL/IEF momentum input on a flat bar → explicit skip the gate treats as FAIL, never a silent 0% or fallback to cash | no degraded-but-plausible number |

**Decision rule.** PASS = paired ΔSortino ci_low > 0 **AND** Δwealth ci_low > 0
**AND** 2022 does not degrade **AND** MBL cleared. Any one failing → the off-leg
is REFUTED as an improvement and the sleeve keeps its cash flat-leg (a clean,
valid result). No partial credit, no threshold relaxation.

## Data + harness dependencies (BOTH required before running)

1. **T-255 fair sleeve harness** — the corrected harness (flat-leg return + the
   carry-gauntlet fixes back-ported). Running on the old harness is a broken
   yardstick.
2. **Deep-substrate BIL/IEF history** — on-disk IEF starts 2020-04-09 (the same
   short-history block found in T-247); a long-window A/B needs the 21-yr
   BIL/IEF series C/T-256 is ingesting from `data/raw/stooq/`. Until both land,
   this stays design-only.

## When it runs (NOT now)
On the first fair-harness + deep-substrate availability: execute the single spec
above, report the gate table, N_trials += 1. Expected honest outcome: a modest
BETA improvement in wealth/Sortino IF 2022 holds — or a REFUTATION if the off-leg
reintroduces the duration tail. Either is a valid deliverable.
