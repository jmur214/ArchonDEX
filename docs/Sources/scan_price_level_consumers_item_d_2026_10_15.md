# Item (d): who reads a price LEVEL, and what a back-adjusted level does to each

**For:** Agent R, then the director. **Status:** the scan is read-only. Steps 1–2 are built on
`feature/item-d-price-levels` (`1de85c4`). Every other row below has a ruling attached or requested.
**N_trials: 0.**

## Why this matters now, not at the cutover

The cache is **already** dividend back-adjusted: exact post-seam, and the drip ≈ total return in level
pre-seam. A back-adjusted close is the true price multiplied by the cumulative dividend factor still to
come. Measured from yfinance (Adj Close ÷ split-only Close), nothing written:

| ticker | 2000 | 2005 | 2010 | 2015 | 2020 |
|---|---|---|---|---|---|
| XOM | 0.432 | 0.487 | 0.537 | 0.612 | 0.742 |
| KO | 0.474 | 0.520 | 0.600 | 0.693 | 0.816 |
| SPY | 0.625 | 0.673 | 0.744 | 0.824 | 0.909 |
| AAPL | 0.837 | 0.837 | 0.837 | 0.884 | 0.962 |

Every **dollar** quantity computed from a back-adjusted close is deflated by that factor: XOM's 2000
dollar volume reads at **43% of true**. The deflation scales with **dividend yield**, so it is a
yield-correlated bias, not noise.

## The consumers (measurement path: `engines/`, `core/`, `backtester/`, `orchestration/`)

| # | site | reads | effect of a back-adjusted level | ruling |
|---|---|---|---|---|
| L1 | `engines/engine_a_alpha/edge_base.py:58-65` `_below_adv_floor` (rolling median Close × Volume), used by **five edges**: `atr_breakout`, `gap_edge`, `herding_edge`, `momentum_edge`, `volume_anomaly_edge` | dollar-ADV | understated in the past by the factor above, so high-yielders fall below the floor more often in early years: a yield-tilted universe | **RULED:** compute on SPLIT-ONLY price × volume (`close_unadj`), shipped **with the cutover writer**; lock "on an ex-date, dollar-ADV = split-only price × volume to the cent"; recorded tonight (HIGH row) |
| L2 | `engines/execution/slippage_model.py:279` (20-day Close × Volume → half-spread bucket, `:209`) | dollar-ADV | early years and high-yielders land in costlier buckets | **RULED:** same as L1 |
| L3 | `backtester/borrow_rate_model.py:127` (Close × Volume → borrow bucket, `:84`) | dollar-ADV | shorts charged more borrow in early years and on high-yielders | **RULED:** same as L1 |
| L4 | `engines/engine_b_risk/risk_engine.py:1110` (`add_qty = int(delta_notional / price)`), `:1256` (`max_qty_by_value`); `engines/engine_c_portfolio/dynamic_optimizer.py` Path A (`int(delta_notional/price)`) | the price, for INTEGER shares | a lower historical price means more shares per dollar, so the truncation error shrinks in early years. Corrupt DAL at ~$4,000 bought 2 shares per $10k (now withheld) | **TO RULE, propose-first** (Engine B). Option: size on split-only price as the shares that actually traded, then value at the adjusted price. The magnitude is small at retail tickets except on very high-priced names |
| L5 | `engines/data_manager/data_manager.py` `_normalize_df` **÷10 auto-scale** | the median close | fired on ONE series (DAL), half-masking a corrupt stitch | **DONE (step 1):** removed, with the true-level lock |
| L6 | DAL pre-2007 bars | two securities stitched under one ticker | corrupt levels; roughly real returns | **DONE (step 2):** declared, census-recorded withholding that fails closed. DAL is in the PIT file only from 2013-09-11, so PIT-masked consumers (B-1, PIT backtests) were never exposed. The routes the loader now closes: a PIT-mask fallback, a cache-wide universe (`discover_cached_tickers`), and research scripts reading `data/processed/` directly |
| L7 | **MARKET CAP = latest close × shares_diluted**, in two ACTIVE edges: `engines/engine_a_alpha/edges/value_earnings_yield_edge.py:87` (`value_earnings_yield_v1`) and `value_book_to_market_edge.py:81` (`value_book_to_market_v1`). A repo-wide sweep of `engines/`, `core/`, `backtester/` and `orchestration/` finds no other price × shares reader | the price LEVEL × shares | (i) **A total-return back-adjusted close** understates past market cap by the cumulative dividend factor, so high-yielders' early-year yields are overstated: the same direction and size as L1's dollar-ADV deflation, and it reorders the value cross-section. (ii) **The three ÷10 files (AZO, MTD, NVR; health_check HIGH)** make market cap ten times too small and the yield ten times too large. A measured that all three sat in `value_earnings_yield_v1`'s top basket in **54 of 54** short-window months | **Listed 2026-10-15** (added on A's measurement; the first scan listed only the three Close × Volume readers, L1–L3). A re-scores `value_earnings_yield_v1` with the three removed, under a rule stated before the numbers; R reads it. **`value_book_to_market_v1` carries the identical exposure** (the same formula, and active) and is not yet measured. The band rail's per-name declarations are also the list of names whose price-LEVEL verdicts need a dated caveat |

**Level-independent; only the convention touches them** (drip vs ex-date steps):
- `core/feature_foundry/features/dist_52w_high`, `drawdown_60d`, `moving_avg_distance_50d` are ratios to the series' own history;
- the bad-tick band in `_normalize_df` is relative to a rolling median;
- the `px <= 0` sanity checks.

**No per-share fees exist.** Commissions and spreads are in basis points, so they are level-free.

## Direct readers of `data/processed/` and the DAL declaration (Agent R's O-1)

The declaration is ONE read gate, not a property of today's universes.

| reader | how it reads | status |
|---|---|---|
| `DataManager.load_cached` / `ensure_data` | the loader | **gated** (truncate on the raw read, check on the served frame) |
| `core/feature_foundry/sources/local_ohlcv.py` (`_read_one`, `close_series`) | every foundry feature reads the CSVs directly, bypassing DataManager | **gated** (fixup commit), with a lock |
| `core/benchmark.py:103-104` | benchmark ETFs only (`tr_reconciled/` preferred, flat file as fallback) | **safe by construction today**: never reads DAL. Its comment at `:134` calls the flat `data/processed/` "PRICE-ONLY", which item (d)'s R-5 measurement shows is false (the flat cache is dividend back-adjusted); recorded, not edited here |
| `scripts/build_signal_panel_b1.py:159` | direct `read_csv`, masked per month-end by PIT membership | **safe by construction today**: DAL is in the PIT file only from 2013-09-11 |

## Not in the scan's scope, named

- **Research scripts in `scripts/`** read `data/processed/` directly and may compute dollar volume
  themselves. They are not the measurement path, but any verdict built on one inherits L1's bias. The
  per-verdict re-qualification plan of the cutover proposal should check each one it relies on.
- **The fleet** reads live broker prices, not this cache. It is unaffected.

## For the cutover proposal

L1–L3 are the **second** reason every pre-seam number is re-qualified rather than relabelled; the
first is the drip's dividend under-count. The `close_unadj` column and the readers that switch to it
ship with the writer.
