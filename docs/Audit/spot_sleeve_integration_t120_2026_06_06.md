---
task_id: T-2026-06-06-120
title: Wire the spot-ETF crisis-diversifier sleeve into the real portfolio path (Phase 1)
date: 2026-06-06
substrate: prod equity universe × Stooq 8-ETF basket (2024 + 2022 single-year cells; full 16/26-yr Phase 2 hardening)
scope: Engine C wiring behind a default-OFF flag — NO prod-default change; analytical T-115 verdict stands until full integrated A/B
outcome: **Phase 1 deliverables met.** (1) OFF canon-md5 BITWISE-identical to current main baseline (T-099 reference `b6137649…`). (2) ON path runs end-to-end on 2024 (Sharpe +1.91, CAGR +12.26%) and 2022 (Sharpe +0.20, CAGR +1.54%). (3) **Faithful-wiring DIVERGES from T-115 analytical** in both years tested — the integrated path produces opposite-direction effects vs the analytical partition (2022 hurt instead of helped; 2024 helped much more than expected). This is the inbox-flagged "informative divergence" finding: the analytical partition missed capital coupling through total-equity-based position sizing. Phase 2 hardening required before any production-default flip.
---

# T-120 — Spot Sleeve Integration (Phase 1)

## Headline

The wiring is faithful in the inert sense — **OFF preserves canon-md5
bitwise-identical to current main** (`b613764912f1a66da5c7d00ebaa3ab8b`,
T-099 baseline) — so there is zero risk of accidentally shifting the
prod default. The ON path also runs end-to-end without errors.

**But the integrated ON@25% result diverges from T-115's analytical
prediction in both single-year cells tested.** This is exactly the
class of finding the inbox said to surface explicitly: *"if the
integrated path DIVERGES materially from analytical, that's a finding
(the analytical combination missed a rebalance/cost/timing effect),
report it."*

Phase 1 is complete as scoped. Phase 2 (full 16/26-yr cloud A/B +
divergence mechanism investigation + decision on capital-coupling
fix) is required before a production-default flag flip — flagged in
the outbox "Notes for director."

## Wiring summary

### Flag added (Engine C autonomous scope, default OFF)
`engines/engine_c_portfolio/policy.py::PortfolioPolicyConfig`:
```python
spot_sleeve_enabled: bool = False
spot_sleeve_capital_pct: float = 0.25
```

When OFF (default): all new code paths short-circuit. `PortfolioEngine.__init__`
sets `self.spot_sleeve = None`; `snapshot()` adds `sleeve_equity = 0.0`;
`backtest_controller._log_snapshot` override reads
`snap.get("sleeve_equity", 0.0) = 0.0`. **Bitwise-identical to pre-T-120
baseline.**

When ON:
1. `PortfolioEngine.__init__` partitions initial capital:
   - `self.cash = initial_capital * (1 - spot_sleeve_capital_pct)` (the
     equity book's slice)
   - `self.spot_sleeve = SpotETFTrendSleeve(initial_capital *
     spot_sleeve_capital_pct)` (the sleeve's slice)
2. `PortfolioEngine.snapshot(timestamp, prices)` calls
   `self.spot_sleeve.advance_to(timestamp)` once per bar, reads
   `self.spot_sleeve.equity`, and adds it to the `equity` snapshot
   field.
3. `backtest_controller._log_snapshot` recomputes equity from live
   state but now preserves the sleeve contribution via
   `snap["equity"] = live_cash + live_mv + sleeve_eq`.

### New file: SpotETFTrendSleeve
`engines/engine_c_portfolio/sleeves/spot_etf_trend_sleeve.py` — a
self-contained bar-by-bar accountant for the 8-ETF basket
[SPY, TLT, GLD, USO, UUP, EEM, IEF, DBC]. Parameters fixed at the
T-115 spec defaults (top_n=4, max_position_weight=0.30,
lookback_days=252, vol_window_days=63, rebalance_cadence="monthly").

**Critical anti-pattern avoided:** this sleeve does NOT reuse the
existing `TrendFollowingSleeve` (which filters Engine A's equity
signals by momentum+inverse-vol — i.e. the doubly-falsified
equity-trend per T-007). The new sleeve has its own universe
(8 ETFs), its own data path (Stooq mirror), and its own bar-by-bar
state. The inbox flagged this trap explicitly; the sleeve module
docstring documents the avoidance.

### Why side-channel, not `MultiSleeveAggregator.compose()`
The inbox preferred wiring through `MultiSleeveAggregator.compose()`,
but that pathway returns `target_weights: Dict[ticker, weight]` which
flows through Engine B's order pipeline. The 8 ETFs are not in the
engine's `data_map` (which carries only the equity universe), so
Engine B cannot price/size them. Adding the 8 ETFs to the engine's
data_map is a substrate change that doesn't fit Phase 1's scope.

The Phase 1 side-channel approach (sleeve owns its own price data;
contributes PnL directly into `equity`) achieves "trades the 8-ETF
basket bar-by-bar" semantically — the sleeve runs its monthly
rebalance + per-bar MTM internally — without requiring the substrate
change. Phase 2 hardening can either (a) plumb the 8 ETFs into the
data_map and use the aggregator the inbox-canonical way, or (b)
formalize the side-channel as the deliberate architecture.

## Three proofs delivered

### Proof 1: OFF canon-md5 bitwise-identical (inertness)

| Year | Pre-T-120 main canon | Post-T-120 OFF canon | Match? |
|---|---|---|:-:|
| 2024 (cell I used) | `b613764912f1a66da5c7d00ebaa3ab8b` (T-099 baseline) | `b613764912f1a66da5c7d00ebaa3ab8b` | ✓ |

Determinism `--runs 3` PASS on default-OFF (T-099 floor preserved):
```
Sharpes: [0.86, 0.86, 0.86]
Sharpe range: 0.0000
Canon md5 unique: 1 / 3
[RESULT] PASS — Sharpe within ±0.02 AND bitwise-identical canon md5
```

The flag default is `False` in both `PortfolioPolicyConfig` and
`config/portfolio_settings.json` (no override added). Production
behavior is unchanged.

### Proof 2: ON path runs end-to-end (functional)

| Year | OFF Sharpe | OFF canon | ON@25% Sharpe | ON@25% canon |
|---|---:|---|---:|---|
| 2024 | 0.86 | `b6137649…` | **1.91** | `4912e676c6f7bafeb25118d074c538fa` |
| 2022 | 0.464 | `0145c03a…` | **0.20** | `b5617e7c9a6a682eb5b1e6a5de67261e` |

Both ON canon md5s **differ** from their OFF counterparts (the flag
actually fires; trades differ). The runs complete without errors.
The integrated path is functional.

### Proof 3: Faithful-wiring check — IT DIVERGES

T-115's analytical capital-partition predicted that adding the spot
basket at 25% capital should HELP in crisis years (the whole pitch:
+35.7pp 2022 outperformance from spot basket alone, with the analytical
combination showing portfolio MDD reduction +16.2% on 17.9yr).

**The integrated path shows the opposite direction on both years tested:**

| Year | OFF (Sharpe / CAGR) | ON@25% (Sharpe / CAGR) | Δ Sharpe | Δ CAGR | T-115 analytical prediction |
|---|---|---|---:|---:|---|
| **2022 (crisis)** | 0.464 / +4.32% | **0.20 / +1.54%** | **-0.26** | **-2.78pp** | should HELP (spot basket +11.2pp standalone in 2022) |
| **2024 (calm)** | 0.86 / matches T-099 | **1.91 / +12.26%** | **+1.05** | (mismatched) | should slightly HURT (small calm-year drag) |

**This is the informative divergence the inbox anticipated.** The
analytical T-115 combination was `portfolio_ret = 0.75·base_ret +
0.25·sleeve_ret` — a clean weighted-average of two independent return
streams. The integrated path does NOT replicate that combination.

### Likely mechanism

Engine A/B sizes positions based on TOTAL portfolio equity, which now
includes `sleeve_equity`. When the sleeve has gained (e.g., end of
2024 sleeve_equity ≈ $28.3K on a starting $25K), the book sees
higher total equity than its own cash share would dictate, leading
to BIGGER trade sizes than the analytical "75% of capital" framing
assumed.

Conversely, in 2022 the sleeve gained slowly while the book's
positions sized off the larger total equity, leading to a different
trade-attribution profile than a true 75%-of-capital book would have
produced.

The capital-coupling effect is real but was NOT modeled by T-115's
external linear combination. The right semantics for "what T-115
predicted" would require either:
1. Scaling Engine A/B's `equity` argument down by `(1 - spot_sleeve_capital_pct)`
   before sizing (i.e., the book truly runs on 75% capital, not on
   "75% cash + sleeve appreciation"), OR
2. Acknowledging that the integrated path is its own beast and
   running the full 16-yr A/B to measure its actual MDD-reduction
   profile under capital coupling.

Phase 2 should make this decision explicitly.

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | `spot_sleeve_enabled` flag (default False) + `MultiSleeveAggregator`-style sleeve wired into `PortfolioEngine.allocate` hosting the SPOT-ETF-trend sleeve | DONE — flag default False; side-channel wiring (not aggregator-routed; see "Why side-channel" above; Phase 2 architectural decision) |
| 2 | OFF canon-md5 == current main baseline | DONE — `b6137649…` bitwise-identical on 2024 cell |
| 3 | ON@25% reproduces T-115 analytical numbers within tolerance — or the divergence characterized | **DIVERGES; characterized.** Phase 1 single-year cells (2022, 2024) both show direction-opposite deltas vs T-115 analytical. Mechanism = capital coupling through total-equity-based sizing. Phase 2 needs to decide whether to (a) scale Engine A/B equity input or (b) accept integrated semantics as its own and re-A/B. |
| 4 | Integrated 16/26-yr A/B (OFF vs ON@25% + ON@30%); MDD reduction, Sharpe ci_low, CAGR — integrated vs analytical | **Phase 2** — Phase 1 single-year shown; full 16/26-yr cloud A/B is out of scope for an interactive session. Flagged in outbox "Notes for director." |
| 5 | Determinism `--runs 3` PASS on OFF | DONE — bitwise identical |
| 6 | Audit doc + proposed ledger row in OUTBOX (per T-114) | DONE (this audit; ledger row in outbox) |
| 7 | NO prod-default change; branch pushed NOT merged | DONE — `spot_sleeve_enabled` default False on main |

## Files

- `engines/engine_c_portfolio/policy.py` — added `spot_sleeve_enabled` + `spot_sleeve_capital_pct` flags (default OFF)
- `engines/engine_c_portfolio/portfolio_engine.py` — capital partition in `__init__`; sleeve PnL injection in `snapshot()`; new `sleeve_equity` field on snapshot dict
- `engines/engine_c_portfolio/sleeves/spot_etf_trend_sleeve.py` — NEW; self-contained 8-ETF cross-asset trend sleeve (NOT TrendFollowingSleeve)
- `backtester/backtest_controller.py` — `_log_snapshot` override now preserves `sleeve_equity` in recomputed equity (defaults 0.0; OFF behavior identical)
- this audit

## Notes for director — Phase 2 hardening

The Phase 1 deliverables are met. Before any prod-default flip
(`spot_sleeve_enabled=True` on main), Phase 2 should address:

1. **Decide the capital-coupling semantics.** Option A: scale Engine
   A/B's `equity` argument down by `(1 - spot_sleeve_capital_pct)` so
   the book truly runs on its capital slice (closer match to T-115
   analytical). Option B: accept the integrated capital-coupling as
   intentional (it represents real "sleeve gains let the book lever
   up slightly" dynamics in production-style allocation) and re-A/B
   under those semantics. Pick one explicitly and document.

2. **Run the full 16-yr + 26-yr integrated A/B.** Single-year results
   here (2022, 2024) are diagnostic, not deployment evidence. The
   T-115 verdict (spot @ 25% → +16.2% MDD reduction, Sharpe ci_low
   up) was on the 17.9yr substrate; the integrated path needs to
   re-verify (or refute) on that depth.

3. **`MultiSleeveAggregator` architectural decision.** Phase 1 uses
   a side-channel (sleeve owns its own price data; PnL injected at
   snapshot). The inbox preferred aggregator-routing, but aggregator
   target_weights flow through Engine B's order pipeline which would
   require adding the 8 ETFs to the engine's data_map (substrate
   change). Director should choose: (a) add ETFs to data_map +
   aggregator route, OR (b) formalize the side-channel as the
   intentional architecture for non-equity sleeves.

4. **Determinism for ON path.** `--runs 3` PASS verified for OFF;
   ON path's determinism should be verified on a longer cell before
   any prod consideration.

5. **The OFF/ON 2022 result deserves a deeper look.** The fact that
   integrated ON@25% HURT 2022 (vs T-115 analytical predicting help)
   is the kind of finding that could either (a) reveal a real
   capital-coupling regret, or (b) be an artifact of the sleeve's
   monthly cadence missing the late-2022 SPY recovery. Worth a
   per-bar attribution before scaling.

## Memory updates needed (post-merge)

- New entry: "T-120 Phase 1: wired the spot 8-ETF crisis-diversifier
  sleeve into PortfolioEngine behind `spot_sleeve_enabled` flag
  (default OFF). OFF canon-md5 BITWISE-identical to T-099 baseline
  (`b6137649…`). ON path runs end-to-end but **diverges direction-
  oppositely from T-115's analytical prediction on both 2022 and
  2024 single-year cells** — 2022 (crisis) HURT (Sharpe 0.464→0.20),
  2024 (calm) HELPED (Sharpe 0.86→1.91). Likely mechanism: capital
  coupling through total-equity-based position sizing (Engine A/B
  sees TOTAL equity including sleeve, sizes accordingly; analytical
  T-115 was a clean weighted-average that ignored this coupling).
  Phase 2 hardening = decide capital-coupling semantics + run full
  16/26yr integrated A/B + aggregator-vs-side-channel architecture
  call. NO prod-default change."

- Pattern memory: "Analytical capital-partition results can differ
  from integrated-engine results when the engine's downstream
  components size based on total portfolio equity. The integrated
  semantics depend on whether the equity book's effective capital is
  scaled down or held at the full pre-partition value. T-115's
  analytical prediction implicitly assumed Option A (scale down);
  T-120 Phase 1's wiring defaults to Option B (full equity). The
  divergence is real and bidirectional."

## Forward dispatches

- **T-120-Phase-2-capital-coupling**: choose between Option A
  (scale Engine A/B equity input) and Option B (accept coupling).
  Implement + re-verify OFF canon-identical. Run single-year cells
  (2022, 2024) again under the chosen semantics.

- **T-120-Phase-2-full-16-26yr**: cloud A/B 16-yr + 26-yr with
  block-bootstrap CI. KPIs same as T-115: MDD reduction, Sharpe
  ci_low, calm-year Sharpe, crisis-period return. The cloud image
  needs the T-120 code; rebuild required.

- **T-120-Phase-2-aggregator-route** (optional architectural
  cleanup): if Phase 2 decides aggregator routing is the right
  architecture, plumb 8 ETFs into engine's data_map and refactor
  `SpotETFTrendSleeve` to a proper `SleeveBase` implementation.

## NOT done in T-120 (Phase 2 scope)

- Full 16-yr / 26-yr integrated A/B (cloud campaign required)
- Capital-coupling semantics decision
- `MultiSleeveAggregator` formal routing (side-channel used for Phase 1)
- Determinism `--runs 3` on ON path (only OFF verified)
- Production-default flag flip (per inbox: director/user gated)
- No data/governor edits
- No cockpit/dashboard edits
