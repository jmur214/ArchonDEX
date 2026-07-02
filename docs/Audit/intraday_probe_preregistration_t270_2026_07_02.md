---
title: "Intraday probe — PRE-REGISTRATION (Gao momentum primary / ORB-1x secondary; frozen before running)"
task: T-2026-07-02-270
status: pre-registered (committed BEFORE fetch/run)
---

# T-270 — the ONE intraday probe — FROZEN PRE-REGISTRATION

Committed BEFORE fetching data or seeing any result. N_trials += 1. Prior ~15–25%
(the better-evidenced single-instrument intraday anomaly, but post-publication
decayed and friction-fragile). Closes the user's ORB/VWAP ideas with evidence.

## Data (frozen)
SPY **SIP** consolidated minute bars, 2016-01-01 .. 2026 (Alpaca free historical,
15-min-delayed end → free; SIP entitlement pre-flight OK; IEX rejected — 0 bars
pre-2020, ~3% volume → unreliable extremes). Aggregated to DAILY at fetch time
(raw minutes not retained). **Bar-extreme cross-check:** on a random 15-day
sample, compare the first-30min high/low against a second source (Stooq daily H/L
as a sanity bound + yfinance 1-min where available); flag >3× dispersion (the ORB
authors' own firm found >3× cross-provider dispersion — stop-driven designs are
data-fragile). If the sample fails, the ORB (secondary) result is quarantined.

## PRIMARY — Gao-Han-Li-Zhou market intraday momentum (long-only), ONE spec
- Predictor (causal, known by 15:30 ET): `r_first = P_10:00 / P_prev_close − 1`
  (first-half-hour return vs the PRIOR day's 16:00 close, per the paper).
- Rule: if `r_first > 0` → hold SPY long **15:30 → 16:00**; else FLAT.
- Daily gross return = `1[r_first>0] · (P_16:00 / P_15:30 − 1)`.
- No sweep: threshold 0, fixed 15:30→16:00 window, fixed predictor. One arm.

## SECONDARY — ORB long-only, 1× (cost-inclusive), ONE arm (for closure)
- Opening range OR = [high, low] of 09:30–10:00.
- After 10:00: if price rises to `OR_high` → enter long at `OR_high`; hold to 16:00
  close; hard stop at `OR_low` (exit there if hit post-entry). LONG-ONLY, **1×** (no
  leverage, no shorts — the honest version; the paper's 675% = 4× + 49% shorts +
  0 slippage). If no upside breakout → flat that day.
- Daily gross return = breakout ? `(exit / OR_high − 1)` (exit = 16:00 close, or
  OR_low if stopped) : 0.

## Frictions (frozen, applied to BOTH arms)
1. **Transaction cost 2.5 bps/side** (SPY at 15:30–16:00 / at breakout — tight, but
   include slippage) → 5 bps per round-trip, charged on every active day.
2. **Cash-account settlement (Roth, no margin):** daily round-trips cannot redeploy
   unsettled T+1 funds → **~50% average capital deployment (GFV limits)**. Realized
   daily return = `0.5 · (gross − cost) + 0.5 · cash_rate(DGS3MO)`.
3. **Windows:** report FULL 2016–2026 AND **post-2018 OOS** (the paper's sample ends
   2013; decay is documented) — the post-2018 row is the honest read.

## Gates (frozen)
- Sortino + Sharpe + block-bootstrap **ci_low**, NET of all frictions, vs **both
  robos (60_40, schwab_like) AND the trend sleeve** (the deployed incumbent).
- **MBL** at effective-N (honest accumulated ~263).
- **Decision:** clears iff ci_low(Sortino) > 0 net of ALL frictions AND beats the
  robos + trend sleeve on the honest (post-2018, cash-account) read → "something
  survives, escalate". Otherwise → **"intraday closes with evidence"** (the modal
  outcome). No sweep, no threshold relaxation; the ORB arm is reported for closure
  regardless of the cross-check (but quarantined if the extreme-check fails).
