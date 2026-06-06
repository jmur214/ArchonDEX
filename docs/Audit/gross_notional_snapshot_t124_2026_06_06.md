---
task_id: T-2026-06-06-124
title: Add canon-safe `gross_notional` field to portfolio snapshot — durable de-gross-measurement infra
date: 2026-06-06
scope: Engine C autonomous; purely additive snapshot field; NO changes to equity/trades.csv/canon
outcome: **Field added + canon-md5 BITWISE-identical** to T-099 baseline (`b613764912f1a66da5c7d00ebaa3ab8b` on 2024 cell); equity unchanged (sleeve OFF); determinism `--runs 3` PASS bitwise; correctness verified on synthetic mixed-side bar (gross $55,750 ≥ |net| $26,250, shorts component +$29,500).
---

# T-124 — gross_notional Snapshot Field

## What changed (2 surgical edits)

1. **`engines/engine_c_portfolio/portfolio_engine.py` `snapshot()` dict**:
   added `"gross_notional": self.gross_notional(price_map)` immediately
   after the T-120 `sleeve_equity` field. Reuses the EXISTING helper at
   line 424 — no new gross calculation.

2. **`cockpit/logger.py` `SNAPSHOT_COLUMNS`**: added `"gross_notional"`
   immediately after `"current_drawdown_pct"` and before
   `"open_pos_by_edge"` so the new field reaches `portfolio_snapshots.csv`.

Both edits are purely additive. No existing fields renamed, no
consumers altered.

## The load-bearing canon-safety proof

| Check | Result |
|---|---|
| canon-md5 on 2024 cell post-T-124 | **`b613764912f1a66da5c7d00ebaa3ab8b`** = T-099 baseline EXACTLY |
| Sharpe on 2024 cell post-T-124 | **0.86** matches baseline |
| `equity` field equals `cash + market_value` (sleeve OFF default) | max abs diff = 0.000000 |
| Determinism `--runs 3` PASS bitwise | Sharpes `[0.86, 0.86, 0.86]`, range 0.0000, canon `1/3` unique |

The canon is over `trades.csv`, not `portfolio_snapshots.csv`. Adding a
read-only field to the snapshot dict cannot affect trades — verified
empirically (canon unchanged) and structurally (the new field is never
fed back into any sizing/risk/order path).

## Correctness proof

The 2024 production cell does not surface bars where shorts and longs
coexist in the snapshot (shorts appear to be entered/exited within the
same bar in this universe + risk config), so direct on-CSV verification
of "gross > |net|" on a 2024 bar is not possible. The maximum
gross-vs-|net| spread observed on the 2024 CSV is +$80.39 at 2024-02-22,
which is the existing helper's `avg_price` fallback artifact (the
`gross_notional` helper falls back to `pos.avg_price` when a ticker is
out of `price_map`, while `market_value` falls back to `pos.last_price`
— a pre-existing minor inconsistency in the helper, not a T-124
regression).

The shorts-component math is verified directly via a synthetic
mixed-side bar:

```
PortfolioEngine with:
  SPY:  qty = +100, last_price = 410
  QQQ:  qty =  -50, last_price = 295

market_value   = (100 × 410) + (-50 × 295)  = +$26,250 (signed net)
|market_value| = $26,250
gross_notional = |100 × 410| + |-50 × 295|  = $41,000 + $14,750 = $55,750

gross_notional ≥ |market_value|: $55,750 ≥ $26,250 ✓ (shorts component +$29,500)
```

The formula matches the helper exactly. For a book that holds shorts
overnight in any future cell, this field will surface the gross/net
gap correctly.

## Why this matters (T-118 + T-116 dependency)

- T-118 de-gross campaign needs per-bar gross exposure to measure
  count×size double-count.
- T-116's diagnostic surfaced that net `market_value` understates true
  exposure on a shorting book.
- C is using a post-hoc reconstruction in the current campaign; this
  field is the durable fix for ALL future de-gross measurement —
  cleaner than re-deriving gross from trades each time.

## Acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | `gross_notional` field added to `snapshot()` via existing helper (purely additive) | DONE — 1 dict entry add; helper unmodified |
| 2 | canon-md5 UNCHANGED on 2024 cell (`b6137649…`) | DONE — bitwise-identical to T-099 baseline |
| 3 | equity unchanged + determinism `--runs 3` PASS | DONE — max|equity Δ| = 0.000000; `--runs 3` PASS bitwise |
| 4 | correctness: gross_notional ≥ \|market_value\| on a sample shorting bar | DONE via synthetic mixed-side test (2024 cell didn't surface coexisting longs+shorts; helper formula verified directly) |
| 5 | Brief audit + proposed ledger row in OUTBOX | DONE (this audit; ledger row in outbox) |
| 6 | Branch pushed NOT merged | DONE |

## Files

- `engines/engine_c_portfolio/portfolio_engine.py` — 1 entry added to snap dict (4 lines incl. comment)
- `cockpit/logger.py` — 1 column added to `SNAPSHOT_COLUMNS` (1 line + 7-line comment)
- this audit

## Memory updates needed (post-merge)

- New entry: "T-124 added `gross_notional = Σ|qty·px|` per-bar field to portfolio snapshot dict + CSV schema (reuses existing `PortfolioEngine.gross_notional` helper). Canon-md5 BITWISE-identical, equity unchanged, det `--runs 3` PASS. Durable fix for T-118 de-gross campaign + T-116 count×size double-count diagnostic. Minor note: existing helper falls back to `avg_price` for out-of-map tickers while `market_value` uses `last_price` → small spread (~$80 on 2024 cell) is pre-existing helper inconsistency, not a T-124 regression."

## NOT done in T-124

- No production-default change
- No data/governor edits
- No cockpit/dashboard edits (dashboard is forbidden; `cockpit/logger.py` is NOT under dashboard and is the canonical snapshot writer)
- No TASK_LEDGER write (per T-114 protocol — proposed row in outbox)
- No fix to the helper's avg_price-vs-last_price inconsistency (pre-existing; flagged in memory for future optional cleanup)
