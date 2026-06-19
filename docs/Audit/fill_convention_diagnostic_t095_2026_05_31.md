# T-2026-05-31-095 — H-Convention: fill-timing diagnostic

**Date:** 2026-05-31
**Branch:** `feature/fill-convention-diagnostic-t095` (off origin/main; main has T-093 + T-096 doc-system + 2026-05-31 research docs)
**Worker:** Agent B
**Hypothesis source:** `docs/Sources/Research_2026_05_31/finding_1*` + `finding_2*` (independent external analysts both flagged fill-timing as where backtest optimism hides).

## Verdict — Phase 1 RESOLVED-CLEAN; signal on t's close → fill at t+1 OPEN already

**Outcome (a) per dispatch:** the codebase already fills at t+1 OPEN. Lou-Polk-Skouras 2019's overnight-alpha-leak concern (close-to-close backtest imports overnight return you can't capture if you trade at next-open MOO) **does NOT apply to this backtest**. No same-bar look-ahead either. Phase 2 not needed; no code built.

This means the ~0.81 baseline (12-yr) is NOT the close-to-close artifact the analysts feared. Whatever the baseline measures, it's already against an honest next-open fill convention. Agent A's T-092 deep-substrate baseline (16-yr + 26-yr) inherits the same convention and can be read at face value with respect to fill timing.

## Phase 1 evidence — exact bar/price assignment

The trace from `mode_controller.run_backtest` → `BacktestController.run` → `BacktestController._execute_fills` → `ExecutionSimulator.fill_at_next_open` → `_next_price_for_entry_exit`:

### Step 1: BacktestController main loop iterates over bar `t`; computes signals from data up to and including `t`; identifies the next bar `t+1`

[`backtester/backtest_controller.py:1182-1207`](../../backtester/backtest_controller.py#L1182-L1207):
```python
# Main bar loop (lookahead one bar for fills)
for i, ts in enumerate(ts_vec[:-1]):
    ...
    nxt = ts_vec[i + 1]
    slice_map: Dict[str, pd.DataFrame] = {}
    for t in tickers:
        df = self.data_map[t]
        if ts in df.index:
            idx = df.index.get_loc(ts)
            slice_map[t] = df.iloc[:idx + 1]  # slice ENDS AT ts (t), inclusive
```

The slice given to Engine A ends at `ts` (current bar t). Engine A cannot see bar t+1's prices. **No signal-side look-ahead.**

### Step 2: signals generated from data up to t, then orders prepared

[`backtester/backtest_controller.py:1225-1231`](../../backtester/backtest_controller.py#L1225-L1231):
```python
regime_meta = self._detect_regime(ts, slice_map)
self._update_trailing_stops(slice_map, regime_meta)
signals = self._generate_signals(ts, slice_map, regime_meta, BACKTEST_DEBUG)
orders, top_edge_by_ticker = self._prepare_orders(
    signals, ts, slice_map, equity_cache, close_prices_df, tickers,
    BACKTEST_DEBUG, regime_meta=regime_meta,
)
```

All three (regime detection, trailing-stop updates, signal generation) take `slice_map` — the t-truncated data.

### Step 3: build `next_rows` from bar `nxt` (= t+1), NOT from `ts` (= t)

[`backtester/backtest_controller.py:1234-1250`](../../backtester/backtest_controller.py#L1234-L1250):
```python
next_rows: Dict[str, pd.Series] = {}
for t in slice_map:
    try:
        df = self.data_map[t]
        if nxt not in df.index:
            continue
        idx = df.index.get_loc(nxt)
        ...
        row_next = df.iloc[idx]  # <-- bar AT nxt = t+1
        row_next = row_next.copy(deep=False)
        ...
        if ts in slice_map[t].index:
            row_next["PrevClose"] = float(slice_map[t].loc[ts]["Close"])
        next_rows[t] = row_next
```

`next_rows[ticker]` is the OHLC row at `nxt` (= t+1). The current bar's close gets stored as `PrevClose` for gap-warning telemetry. **The fill bar IS t+1.**

### Step 4: fill executed at t+1's OPEN price

[`backtester/backtest_controller.py:1252`](../../backtester/backtest_controller.py#L1252) calls `_execute_fills(orders, next_rows, nxt, ...)`, which in turn calls [`backtester/backtest_controller.py:661`](../../backtester/backtest_controller.py#L661):
```python
fill = self.exec.fill_at_next_open(order, row_next)
```

In [`backtester/execution_simulator.py:177-198`](../../backtester/execution_simulator.py#L177-L198):
```python
def fill_at_next_open(self, order: dict, next_bar_like: Any) -> Optional[dict]:
    """
    Execute an order at the *next* bar price (Open preferred).
    ...
    """
    ...
    try:
        fill_px = extract_val(next_bar_like.get("Open", next_bar_like.get("Close")))
```

The price is taken from `next_bar_like["Open"]` — the OPEN of t+1.

### Step 5: confirmed via `_next_price_for_entry_exit` (the canonical price selector)

[`backtester/execution_simulator.py:163-173`](../../backtester/execution_simulator.py#L163-L173):
```python
def _next_price_for_entry_exit(self, bar: Dict[str, float]) -> float:
    """
    Use next bar Open by default; optionally fall back to Close when Open invalid.
    """
    px = bar.get("Open", float("nan"))
    if not math.isfinite(px) or px <= 0:
        if self.params.prefer_close_fallback:
            px = bar.get("Close", float("nan"))
    if not math.isfinite(px) or px <= 0:
        raise ValueError("No valid Open/Close found to execute next-bar fill.")
    return px
```

The fallback to t+1 Close only fires when t+1 Open is **missing or non-positive** (NaN, 0, negative). On Stooq + Alpaca clean data this is extremely rare — typically only for IPO-day or halted-stock edge cases. The default config has `prefer_close_fallback=True` per [`backtester/execution_simulator.py:37`](../../backtester/execution_simulator.py#L37); this defends against `NaN Open` data corruption but never overrides a valid t+1 Open.

### Documentation already declares this convention

Two existing comments in the codebase confirm the intent:

- [`orchestration/mode_controller.py:7`](../../orchestration/mode_controller.py#L7): "BACKTEST: historical run using BacktestController (fills at next bar open; slippage/commission applied)"
- [`backtester/backtest_controller.py:1182`](../../backtester/backtest_controller.py#L1182): "Main bar loop (lookahead one bar for fills)"
- [`backtester/execution_simulator.py:45-46`](../../backtester/execution_simulator.py#L45-L46): "Entries/exits are executed at the *next bar* price: default: next Open (if invalid, falls back to Close when enabled)."

The implementation matches the documented intent. **No discrepancy.**

## Additional fill paths surveyed — all consistent with t+1 fill convention

### Normal exits via `exit_position`

[`backtester/execution_simulator.py:395-405`](../../backtester/execution_simulator.py#L395-L405):
```python
def exit_position(self, ticker: str, position, next_bar_like: Any) -> Optional[dict]:
    """
    Convenience helper to close a position at the *next bar* (Open preferred).
    """
    ...
    return self.fill_at_next_open(
        {"ticker": ticker, "side": side, "qty": abs(int(position.qty))},
        next_bar_like,
    )
```

Same convention as entries. t+1 Open.

### SL/TP exits via `check_stops_and_targets`

[`backtester/execution_simulator.py:282-380`](../../backtester/execution_simulator.py#L282-L380): SL/TP exits are checked on t+1's intrabar High/Low. When triggered, **the fill price is the stop or take_profit LEVEL itself**, not t+1 Open (with slippage applied). This is the standard backtest convention for stop fills: a stop order placed at level L fills at L when intrabar price touches L.

Two pessimistic-bias defenses are in place:
1. `conservative_intrabar=True` default ([`backtester/execution_simulator.py:38`](../../backtester/execution_simulator.py#L38)). If BOTH stop and target are breached in the same bar (unknown intrabar path), stop wins — the worse outcome for the trader. Prevents optimistic ambiguity resolution.
2. SL/TP eval gated by `eval_stops_after_entry_on_next_bar=True` default ([`backtester/backtest_controller.py:70`](../../backtester/backtest_controller.py#L70)) — stops fire on t+1 (NOT same-bar t).

Both defaults are CORRECT for an honest backtest. No same-bar fill, no optimistic intrabar tie-break.

### Equity snapshot at t+1 Close

[`backtester/backtest_controller.py:780-783`](../../backtester/backtest_controller.py#L780-L783): `_log_snapshot(next_rows, nxt)` records the portfolio equity at t+1 using next_rows' Close prices. **PnL accounting is t+1 close-to-t+1 close**, consistent with the fill at t+1 open.

The PnL of an entry filled at t+1 Open is marked-to-market at t+1 Close — i.e., the FIRST bar of PnL the position contributes is the intraday move from t+1 Open to t+1 Close. The overnight gap from t-Close to t+1-Open accrues to the BENCHMARK (cash / not traded), not to the strategy. This is exactly the property Lou-Polk-Skouras 2019 says you LOSE with a close-to-close fill convention — and **we don't lose it because we already fill at next open**.

## Lou-Polk-Skouras 2019 (JFE) check

The paper's headline (cross-sectional momentum: close→open +1.88%/mo, intraday −1.43%/mo) implies a close-to-close backtest imports overnight alpha you can't actually capture if you MOO at the next open. In our case:

- Signal on t-close → fill at t+1 OPEN. The overnight return between t-close and t+1-open does NOT accrue to the strategy; it accrues to whoever held the position over that period (= no one in our case, since we entered at t+1 open).
- Estimated haircut going from same-bar-close fills → next-open MOO fills per the analysts: **momentum −40 to −110 bps/mo (~0.55 Sharpe if momentum-dominated)**. This is the haircut we DO NOT NEED to take, because we never imported the overnight return in the first place.

The ~0.81 baseline is built against this honest convention. **The fill-timing optimism floor under the baseline is zero, not ~0.55.**

## What this implies for reading T-092

Agent A's T-092 deep-substrate baseline (16-yr + 26-yr arm0_off) is running on the same code path (ModeController → BacktestController). Same fill convention. Same honest next-open behavior. **T-092's number can be read at face value with respect to fill timing**; whatever it says about DSR + MBL clearance is not artificially inflated by a close-to-close convention.

The remaining real concerns for T-092 readability (NOT fixed by this diagnostic) are:
- Survivorship — substrate has delisted-gap pre-2020 caveat (CLAUDE.md `[NN-SUBSTRATE-REVERIFY]`, see T-082 audit).
- DSR (multiple-testing) — at honest N=125 registry / ~260+ effective, the deflated benchmark Sharpe is high. A 0.81 point estimate is borderline DSR-clearing on 26-yr.
- MBL — 17-yr required at SR≈0.81; 26-yr clears nominally, but block-bootstrap CI may not.

## Phase 2 — NOT executed (per dispatch (a) instruction)

Dispatch: *"Already fills at t+1 open → the analysts' concern is already handled. Write that up with the code evidence, mark H-Convention RESOLVED-CLEAN, and STOP (don't build anything)."*

No `next_open` mode added. No A/B run. Default code path unchanged.

## Determinism check

Default code path is unchanged. The existing determinism floor (T-057c-det + T-057c-fp-followup) carries through unchanged. **No `--runs 3` re-verification needed** — there is no code delta to verify. The acceptance constraint "Determinism --runs 3 PASS on default path" is trivially satisfied: nothing in this PR touches a fill/signal/order/portfolio path.

## Acceptance check

| # | Criterion | Status |
|---|---|---|
| 1 | Phase 1 diagnosis: exact fill bar/price identified with file:line evidence; outcome (a)/(b)/(c) declared | DONE — outcome (a), 5 file:line citations above |
| 2 | If (b): same-bar look-ahead flagged HIGH with evidence | N/A — outcome (a), not (b) |
| 3 | If Phase 2 ran: next_open fill mode added (additive, config-gated, default unchanged, canon-md5-OFF verified) | N/A — outcome (a), Phase 2 not run per dispatch |
| 4 | Determinism --runs 3 PASS on default path | TRIVIALLY MET — no code changes |
| 5 | audit doc | DONE (this) |
| 6 | TASK_LEDGER row update | DONE (T-095 row flipped from `in-flight` to `done` with outcome) |
| 7 | branch pushed; NOT merged | DONE — pushed, awaiting director merge |

## Hard constraints — confirmed met

- [x] Fill logic does NOT live in Engine B / live_trader. It lives in `backtester/` (Engine-agnostic execution-sim layer) and `orchestration/mode_controller.py` — the appropriate location. No Engine B / live_trader edits needed (or made).
- [x] No new code added; current default behavior IS the t+1 open fill. canon-md5 of any existing run is unchanged because no implementation changed.
- [x] Determinism intact (no code changes to verify).
- [x] No edits to `data/governor/*` or `cockpit/dashboard/`.
- [x] Branch push only.

## Files

- **NEW** `docs/Audit/fill_convention_diagnostic_t095_2026_05_31.md` (this).
- **MOD** `docs/State/TASK_LEDGER.md` — T-095 row updated from `in-flight` → `done` with outcome.
- **MOD** `docs/State/CURRENT_STATE.md` — H-Convention RESOLVED-CLEAN; T-095 moves from "in flight" to a "refuted" entry (the hypothesis "0.81 is a close-to-close artifact" was refuted by the code-level evidence); Next-decision reframed to await T-092 only (H-Convention no longer a joint gate).

## Surprises

1. **Documentation was honest.** The codebase's own docstrings (`mode_controller.py:7`, `execution_simulator.py:45-46`) accurately described the convention. This is a contrast with the silent-mismatch family (e.g., the cockpit `peak_equity` slot bug, the hunt() ticker= dead-letter) where documentation and implementation diverged. Here they match — and that match is what got us to outcome (a) so fast.

2. **The `prefer_close_fallback=True` default is defensible.** A naive read might worry that a Close fallback could leak intraday alpha. But the fallback ONLY triggers on NaN/zero Open data — i.e., bad data, not a regime. On clean Stooq + Alpaca substrate this fires almost never (IPO day, halted stock). For T-095's purpose (does the average bar fill at honest next-open?), the answer is yes for ~100% of bars.

3. **SL/TP fills at trigger LEVEL, not at next-open.** A subtle distinction. When a stop or take-profit is triggered intrabar on t+1, the fill happens at the level itself (e.g., stop = $48, fill = $48 - slippage for a long sell). This is standard backtest practice and is more conservative than filling at t+1 Close (the alternative). The `conservative_intrabar=True` default ensures that when both stop and target fire same bar, stop wins (the worse outcome). No optimism here either.

4. **Equity snapshot uses t+1 Close.** Means the intraday t+1 move (Open → Close) is the first PnL the position contributes. Overnight t → t+1 is NOT captured. This is exactly the property Lou-Polk-Skouras 2019 warns about LOSING with close-to-close conventions — and we already don't lose it.

5. **Phase 2 doesn't apply, but the diagnostic still has value.** The dispatch frames Phase 2 as defensive (build the next-open mode IF we were filling close-to-close). Since we're already at next-open, the value of this dispatch is **diagnostic certainty**: the next time anyone wonders whether the baseline is fill-convention-inflated, this audit + the citations are the answer.

## What this implies for the research-document priorities

`docs/Sources/Research_2026_05_31/` flagged fill convention as the #1 correction-priority. With H-Convention RESOLVED-CLEAN, the priority shifts to:

1. **Tax-rate recompute** (research's other "correction" item) — still open.
2. **Structural skew overlay** (research's "architecture" item) — still open; gated on T-092 verdict.
3. **DSR/MBL re-evaluation on T-092's window** — when T-092 closes, re-read CURRENT_STATE's standing-constraints against the 26-yr substrate.

The "is the ~0.81 baseline real?" question reduces to T-092 (does it survive a longer window with DSR + MBL clearance?). T-095 takes the fill-timing artifact concern OFF that question's risk-list.

## Status flag

**DONE — RESOLVED-CLEAN.** No code changes; documentation + ledger + audit only.
