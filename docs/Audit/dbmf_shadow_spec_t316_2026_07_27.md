# T-316 — the DBMF managed-futures forward shadow: SPEC + FROZEN GATES (report-only)

**Date:** 2026-07-27 · **Agent:** C · Branch `feature/dbmf-shadow-t316` · **0 N_trials** (infra)
Starts the only clock that can honestly answer the "**awaits a genuinely-independent 3rd return stream**" question (T-248/T-263, tripwire #2 from B/T-305). **Report-only, zero order effect.**

## Why a LIVE clock (every backtest route is exhausted)
- **T-296 (RSST / return-stack):** walled by a **±5%/yr hypothetical-replication basis** — the fund's MF program is proprietary; no free proxy is level-faithful. Not a verdict, a data wall. *(It did produce one real finding: stacking our long/flat gate on an internally-overlaid fund **INTERFERES** — our gate reads the combined price and the MF up-trend masks the equity decline.)*
- **T-313 (international equity):** **REFUTED at the data stage** — crisis corr +0.87 (2008) / **+1.00 (COVID)** / +0.87 (2022). The T-214 trap; equity-family legs co-fall.
- **T-253:** DBMF's convexity is real but regime-specific (+33/+49% in the sustained 2022 bear, −6% in the fast 2020 crash).
So the open question — *is a managed-futures leg genuinely tail-independent?* — cannot be settled by another proxy backtest. A live forward record can.

## The shadow (`paper_trader/dbmf_shadow.py`, `DbmfShadowBook`)
Each Account-1 pulse records a hypothetical **+5% DBMF sleeve leg** alongside the real sleeve:

    variant_ret = 0.95 · actual_sleeve_return + 0.05 · dbmf_return

- Reuses the **real** sleeve return (no re-derivation) — the same construction as my T-276 BTC shadow.
- **The MF leg is deliberately UNGATED** (not trend-ruled). DBMF *is* a trend program, and T-296 measured that stacking our gate on top interferes. That finding is designed into this shadow.
- DBMF price via the **existing Alpaca `fetch_daily_closes`** (no new dependency).
- **Fail-OPEN:** no price → `degraded=True`, leg parked at **0** (never a fabricated return), and the gates exclude the day. Idempotent per `trade_date`; S3-durable via `DURABLE_PATHS`. 6 unit tests green.
- Heartbeat line: `DBMF-SHADOW n_days=… clean=… degraded=… corr=…`.

## FROZEN forward PROMOTION gates (pre-registered NOW, before the first record — `[NN-MBL]`)
The promotion question is **NOT "did MF make money"** — it is whether the leg delivers the **tail independence** every proxy failed to prove. Passing BOTH promotes the MF leg from report-only shadow to a **real PAPER leg** — never straight to live. Do not loosen a threshold to make it pass.

- **Gate A — LIVE crisis independence (the load-bearing one).** Fires on the next sustained sleeve peak→trough **≥ 10%** (`GATE_A_CRISIS_TRIGGER`). Inside that window, daily **corr(DBMF, sleeve) must be ≤ +0.30** (`GATE_A_CORR_MAX`) — the tripwire-#2 bar, measured LIVE in a real crisis. This is exactly what T-313 failed at +0.93/+1.00. A crisis correlation above +0.30 means the leg is not an independent stream, whatever its backtest said.
- **Gate B — carry-drag falsifiability.** Over **≥ 24 forward months** (`GATE_B_MIN_FORWARD_MONTHS`), cumulative **Δwealth(variant − base) ≥ −3%** (`GATE_B_DWEALTH_FLOOR`). MF bleeds carry in calm markets; this makes "**insurance that also returns**" **falsifiable** — if the leg costs more than 3% of terminal wealth while never proving crisis independence, it is a losing hedge and fails. (Under 24 months → `accruing`, never a premature PASS.)

## ON THE RECORD — the long-vol / tail-overlay door is CLOSED (no trial burned)
Per the strategic review's ruling, **long-volatility and tail-hedge overlays (long VIX futures/VXX, standing OTM put programs, tail-risk funds) are REJECTED for this investor profile** and must never consume a trial:
- They are **structurally negative-EV** — the variance risk premium is the *premium the seller earns*; a permanent buyer pays it, and the documented bleed (−5 to −15%/yr) compounds against a 40-year accumulator.
- The insurance they buy is **against forced liquidation** — but this holder has pre-declared they **will not sell in downturns** ([[feedback_max_wealth_north_star_2026_07_06]]) and faces **no margin call, no redemption, no liability schedule**. There is no forced-seller risk to insure.
- Our own trend overlay already delivers the drawdown reduction *at negative cost* (the flat leg earns the short rate), which is why the sleeve's structural win is drawdown.
This is distinct from **managed futures** (this shadow), which is a *positive-carry-in-trending-regimes* diversifier, not a permanent premium payer — hence MF gets a live clock and long-vol gets a closed door.

**T-316 done (armed; the clock starts on the next Account-1 pulse).**
