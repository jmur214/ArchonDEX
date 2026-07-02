# T-276 — BTC SHADOW-TRACK spec + FROZEN forward gates (report-only)

**Date:** 2026-07-02 · **Agent:** C · Branch `feature/btc-shadow-spec-t276`
Design + report-only build for the forward validation of the T-272 +5%-BTC arm. **No spec change, no trading, zero order effect.** BTC earned a forward slot, not integration ([[project_t272_btc_arm_2026_07_02]]); this starts the OOS clock at go-live without touching the deploying sleeve. E wires the one-call patch POST-Monday (do NOT touch E's staged branch `feature/sleeve-ensemble-spec-t260-e`).

## What it does (`paper_trader/btc_shadow.py`, `BtcShadowTracker`)
Each paper run, alongside the real sleeve track, records a HYPOTHETICAL +5%-BTC-leg variant. Because the deploying sleeve IS the 3-asset {SPY,AGG,GLD} ensemble, the variant daily return is exactly:

    variant_ret = (1 − 0.05) · actual_sleeve_return  +  0.05 · btc_leg_return

— it reuses the **real** sleeve return (no re-derivation) and adds a BTC leg under the SAME frozen multi-speed {42,105,210}d long/flat rule (flat → cash), from BTC-USD (24/7 spot). Records daily: variant NAV, base NAV, BTC exposure, the would-be BTC trade (notional turnover of the 5% leg), and BTC-USD + IBIT closes (the wrapper-basis pair). Persisted to `data/state/btc_shadow_tracking.json` (schema `btc_shadow/v1`).

**Report-only + FAIL-CLOSED:** if BTC history is missing / < the 210d warmup, the day is `degraded=True` with the BTC leg parked in cash (no fabricated exposure) and the gates exclude it. A shadow failure has ZERO effect on orders. 6 unit tests green.

## FROZEN forward PROMOTION gates (pre-registered NOW, BEFORE the clock starts — `[NN-MBL]`)
Passing ALL THREE promotes BTC from report-only shadow → a REAL PAPER leg. **NOT to live** — live still needs the full MBL/DSR bar that BTC's single-bull-era sample cannot clear for years. Do NOT loosen a threshold to pass; the question changes, the bar does not.

- **Gate A — OOS winter test (the load-bearing one).** Fires on the NEXT in-forward BTC peak→trough **≥ 30%**. The variant's in-window drawdown must be **≤ base sleeve in-window DD + 4.0pp** (`GATE_A_VARIANT_EXCESS_MAX = 0.04`). This is the out-of-sample version of T-272's in-sample finding (the trend rule capped BTC's −75/−81% winters to +0.6–1.7pp on the sleeve DD). If the BTC leg adds > 4pp during a real BTC winter, the trend rule failed to exit OOS → **FAIL, do not promote.**
- **Gate B — directional Δ consistency.** Over **≥ 18 forward months** (`GATE_B_MIN_FORWARD_MONTHS`): forward **Δwealth(variant − base) > 0 AND ΔSortino > 0**. This is a *directional*-consistency check, NOT an MBL-clearing proof (18mo ≪ the DSR bar) — it only asks whether T-272's positive direction persists forward. Under 18 months → `accruing` (never a premature PASS).
- **Gate C — IBIT-vs-spot basis (`[NN-SUBSTRATE-REVERIFY]`).** Forward annualized |IBIT − BTC-USD| return tracking-diff, net of the 0.25% ER, must be **≤ 1.5%/yr** (`GATE_C_IBIT_BASIS_MAX`). The shadow signals on 24/7 spot BTC-USD but the tradeable wrapper is IBIT; if IBIT decouples from spot, the shadow overstates. (T-272 measured a 0.82 *daily* corr = 24/7-vs-market-hours timing, not a tracking failure — this gate watches the realized *return* basis, which the monthly-signal cadence is robust to.)

`forward_gates()` reports each gate's status + `promote_to_paper_leg` (all-three-PASS). Report-only.

## Integration patch — E applies POST-Monday (≈4 lines, after `SleeveTracker.record(...)`)
In the paper run, right after the existing `tracker.record(trade_date, sleeve_equity, closes, ...)`:

```python
from paper_trader.btc_shadow import BtcShadowTracker

# sleeve daily return from the last two tracked equities (report-only shadow)
_pts = tracker._load()                       # already-persisted points, sorted by date
_prev = [p for p in _pts if p["date"] < trade_date]
_sleeve_ret = (sleeve_equity / _prev[-1]["sleeve_equity"] - 1.0) if _prev else 0.0
BtcShadowTracker(root=tracker.root).record(
    trade_date, _sleeve_ret, cash_daily_rate=RF_ANNUAL / 252)   # fetches BTC/IBIT fail-closed
```

Notes for E:
- Place it AFTER the sleeve record so `_prev` sees yesterday's equity. Idempotent on `trade_date` (safe to re-run).
- The shadow fetches BTC-USD + IBIT itself (yfinance, fail-closed) — no new inputs to thread. If the cloud image lacks outbound network on the paper path, instead pass `btc_hist=<BTC-USD close Series>` (and `ibit_close=`) from wherever the run already has market data; the degraded path keeps it safe until then.
- Surface `BtcShadowTracker(root=...).forward_gates()` in the same place the execution-gates report is surfaced. Never wire it to any kill/act path.
- The frozen constants live in `btc_shadow.py` — do not edit them; that is the pre-registration.

## Honest framing carried
This is forward VALIDATION of an EXPLORATORY arm — the shadow accrues OOS evidence; it is not itself deployment evidence. The best outcome (all gates PASS) graduates BTC to a real *paper* leg for continued validation, still short of the live MBL/DSR bar.

**T-276 done.** Design + report-only module + tests + the patch; E wires post-Monday.
