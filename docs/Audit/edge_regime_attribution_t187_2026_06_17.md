---
task_id: T-2026-06-17-187
title: Per-edge × per-regime attribution — extend the existing per-year tooling + a reusable API
date: 2026-06-17
scope: measurement/analytics (autonomous-OK); no edge promotion, no flag flips
status: CURRENT
---

# T-187 — Per-Edge × Per-Regime Attribution

## 1. Assessment of the existing tooling (repoint target)

**`scripts/per_edge_per_year_attribution.py`** (Phase 2.10c diagnostic):
loads `trades.csv` (cols incl. `pnl`, `edge`, `trigger`, `regime_label`),
maps edge→lifecycle status from `edges.yml`, and computes per-(edge, **year**):
$PnL sum (exit rows carry PnL), a daily-axis Sharpe-like metric, fill
counts, and a 5-year stable/regime-conditional/noise/sparse
classification. Output: a markdown + CSV per-year report.

**`scripts/factor_decomp_substrate_honest.py`**: FF5+Mom HAC factor
regression with bootstrap-CI α — a *factor*-attribution tool (orthogonal
to per-edge PnL attribution), reused by the alpha audits.

**What was there vs missing:** per-**year** attribution existed and is
solid; the trade rows already carry Engine-E's `regime_label`, but
**nothing conditioned attribution on regime**, and there was **no clean
reusable function** (the per-year code is a CLI report over two hardcoded
run UUIDs). Gap = per-edge × per-**regime** + an importable API. Extended
in place; no parallel tool written.

## 2. The extension (per-edge × per-regime)

Added to the existing script (not a new file):

- **`attribute_by_edge_regime(trades, *, edge_col, regime_col, pnl_col,
  trigger_col, min_n, n_boot, seed) -> pd.DataFrame`** — the reusable,
  pure public API. Takes any trades frame, returns a tidy frame, one row
  per (edge, regime): `n_trades, total_pnl, mean_pnl, win_rate,
  pnl_ci_low, pnl_ci_high, thin`.
- **`load_trades(run_dirs)`** — flexible loader (UUIDs under
  `data/trade_logs/`, or paths to a `trades.csv`); repeatable so multiple
  runs aggregate into bigger per-regime sub-samples.
- CLI mode **`--per-regime --run-dir <id> [--run-dir ...] [--min-n N]`**.

**Attribution choice (documented):** PnL is realized on closing rows
(exit/stop/take_profit/cover); the `regime_label` on the closing row is
the regime **at realization**, so each edge's earned/lost PnL is
attributed to the regime in which the position closed.

**Honest stats — per-regime sub-samples are small and non-contiguous:**
- The resampling unit is the **trade**, not a day → the per-cell CI is a
  **percentile bootstrap on mean PnL-per-trade** (seed-pinned 42,
  n_boot=1000, deterministic). We deliberately do NOT compute a
  daily-axis Sharpe per regime (regimes aren't contiguous in calendar
  time — a daily Sharpe would be ill-defined).
- Every cell reports **N (`n_trades`)** and a **`thin` flag** (N < `min_n`,
  default 20). N=1 cells correctly return NaN CI. This is the census/MBL
  "don't over-read thin regimes" discipline made explicit per cell.

## 3. Reusable function signature (for D's --discover eval + C's T-188 API)

```python
attribute_by_edge_regime(
    trades: pd.DataFrame, *,
    edge_col: str = "edge",
    regime_col: str = "regime_label",
    pnl_col: str = "pnl",
    trigger_col: str = "trigger",
    min_n: int = 20,
    n_boot: int = 1000,
    seed: int = 42,
) -> pd.DataFrame
# columns: edge, regime, n_trades, total_pnl, mean_pnl, win_rate,
#          pnl_ci_low, pnl_ci_high, thin
```

Pure (no I/O, no globals) → **both** D's `--discover` evaluation (judging
which foundry edges add value, by regime) and C's dashboard data layer
(T-188 API contract) call the same function on whatever trades frame they
hold. Verified importable + callable on an in-memory frame. C's T-188
should treat the column set above as the data shape; coordinate if a
different tidy/long vs wide shape is preferred for the API.

## 4. Sample run (current substrate)

`--per-regime` on a single recent run (450 trade rows, regimes
cautious_decline / market_turmoil / emerging_expansion / robust_expansion)
→ 27 (edge×regime) cells, **25 flagged thin (N<20)** — a single-year run
has small per-regime sub-samples, exactly why the thin flag + CI exist.
Illustrative non-thin cells:

| edge | regime | N | total_pnl | mean_pnl | win_rate | CI [lo, hi] |
|---|---|---|---|---|---|---|
| accruals_inv_asset_growth_v1 | cautious_decline | 22 | −9474 | −431 | 0.27 | [−845, +13] |
| momentum_edge_v1 | cautious_decline | 28 | +1729 | +62 | 0.46 | [−240, +410] |

(Both CIs straddle/border zero even at N=22-28 — the honest read is "no
edge has a CI-clean per-regime signal on a single year"; multi-run
aggregation via repeated `--run-dir` is the path to populate cells. The
tool's job is to surface this honestly, which it does.)

## 5. Constraints honored

- Extended existing tooling; no parallel script; no rebuild.
- Measurement/analytics only — no edge promotion, no flag flips, no
  `edge_weights.json` edit.
- Vectorized (groupby + vectorized bootstrap via index sampling); type-hinted.
- Per-cell N + CI + thin flag (census/MBL discipline).
- NO TASK_LEDGER write (T-114 — row in outbox). Branch push.
