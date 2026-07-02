---
name: project-deployable-borrow-is-downstream
description: The deployable-account leverage (2.3x gross, -1.19x cash) originates in Engine-B per-name sizing with no cash budget — NOT the allocator weights. The allocator cap (T-230) is necessary but not sufficient.
metadata:
  type: project
---

T-215/T-230 finding: the mean_variance book runs to ~2.3x gross because CASH goes negative (-1.19x equity on ~25% of bars), NOT because target weights sum past 1. On the 109-ticker 2022 cell the per-bar target weights are already Σw ≤ 1.0, long-only (prod `portfolio_settings.json` sets `min_weight: 0.0`).

**The borrow originates downstream at `engines/engine_b_risk/risk_engine.py:1077-1083`** (Path-A sizing):
`target_notional = equity * target_weight * optimizer_weight`; `delta_notional = target_notional - current_notional`. Each name is sized to its own target INDEPENDENTLY with NO cross-name cash budget, and the rebalance threshold (`policy.py:362 requires_rebalance`, default 2%) gates SELLING → positions accumulate buy-to-target while stale holds aren't trimmed → cash goes negative.

The `deployable_cash_account` allocator cap (`engines/engine_c_portfolio/policy.py:478 _apply_deployable_constraints`, merged T-230, default OFF) operates on WEIGHTS (Σw ≤ 1) → a no-op on this universe → does NOT fix the sizing-layer borrow. It is necessary (catches Σw>1 on the larger PIT universe) but NOT sufficient.

**The real fix (NOT built yet, propose-first):** a no-borrow cash budget at the sizing/rebalance layer — cap executed gross ≤ equity (cash ≥ 0); rebalance must sell down to keep Σ|position·px| ≤ equity. Spans `portfolio_engine.py target_notional_values` + the `risk_engine.py:1077` Path-A path → touches Engine B → propose-first per CLAUDE.md. Pair with the already-merged allocator cap; add a `cash_negative_bars`/`max_gross_over_equity` census key so the de-levered book self-proves it never borrows.

**Therefore a deployable equity curve cannot be produced by replaying existing code — the load-bearing fix does not exist yet.**
