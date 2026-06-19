---
task_id: T-2026-06-18-210
title: Realistic retail cost model — cap-tier half-spreads + market-cap join (default-OFF)
date: 2026-06-18
author: Agent D (cost / T-154/T-207 lane)
type: measurement-integrity (additive, default-OFF)
outcome: SHIPPED the configurable `realistic_retail_costs` mode (market-cap-tiered
  half-spreads grounded in retail effective-spread evidence) + the current-cap
  snapshot join, DEFAULT-OFF (canon byte-unchanged, proven). Re-rating finding:
  the CURRENT static-109 book barely moves under honest costs (−0.038 Sharpe @ 26×
  turnover) — it is ALL large-caps; the −0.12 to −0.74 bite from T-207 lives on the
  PIT-broadened universe's small/micro names. So the cost-honesty and survivorship
  corrections COMPOUND — you can't honestly do one without the other. Turnover is a
  LINEAR lever: halving the ~26× turnover recovers HALF the realistic-cost drag.
status: CURRENT — mode is the one the honest beat-the-robo gate adopts (cloud ON)
---

# T-210 — realistic retail cost model

## 1. The mode (additive, default-OFF)
`engines/execution/slippage_model.py` `RealisticSlippageModel`: a new
`realistic_retail_costs` flag (SlippageConfig + the `slippage_extra` config block,
default `false`). When ON, the half-spread switches from the ADV buckets (1/5/15
bps) to **market-cap tiers**; the Almgren-Chriss impact term is unchanged. When
OFF, the path is byte-identical to the existing model.

**Cap tiers (half-spread bps):** mega ≥$200B → **2**, large $10B-200B → **3**,
mid $2B-10B → **8**, small $300M-2B → **35**, micro <$300M → **75**.
**Basis (cited):** effective-spread microstructure — Corwin-Schultz (2012) high-low
estimator; the SEC Tick-Size Pilot (2016-18) measured small-cap effective spreads
~20-50 bps; FINRA/academic microcap evidence ~50-100+ bps — all at RETAIL (no
internalizer/rebate edge). Mid/conservative point chosen within each band; tunable
in config. The current config (1/5/15 ADV) understated this (the T-207 finding).

## 2. The market-cap join (current snapshot)
`scripts/build_market_cap_tiers_t210.py` fetches CURRENT market cap (yfinance
`fast_info`, free) for the universe → `data/universe/market_cap_tiers.json`
(`{ticker: {marketCap, tier}}`). Built for the static-109: **resolved 107/109**.
The model lazy-loads it; a ticker NOT in the snapshot (delisted/PIT) falls back to
the **ADV bucket** — so a missing cap NEVER silently under-prices (the fallback is
the existing realistic model).

**LIMITATION (flagged):** current-snapshot, NOT point-in-time. The PIT survivorship
cohort (delisted names) has no current cap → falls back to ADV-15 bps, so this mode
**UNDER-counts** friction on exactly the names where it matters most (delisted
small/micro). True PIT cost tiering needs survivorship-free cap history
(Norgate $80/mo, or FMP) — a later increment. This makes the current re-rating a
CONSERVATIVE lower bound.

## 3. OFF byte-identical — PROVEN
`tests/test_realistic_retail_costs_t210.py` (5, green): with the flag OFF the model
is byte-identical to the baseline across {mega, small} bars × {no-qty, small-qty,
large-qty} + the Series/ADV-None fallbacks; ON applies the cap tier; unknown cap →
ADV fallback (never under-prices); the factory defaults the flag OFF. By
CONSTRUCTION the OFF path is `<original>` verbatim (the new code is guarded by
`if realistic_retail_costs`), and the config default is `false` → **the production
canon is unchanged with the mode OFF**. 166 slippage/execution/cost tests pass, 0
regressions.

## 4. Base re-rating (OFF vs ON) — the number
**The CURRENT static-109 book barely re-rates.** Its cap distribution (from the
join): **47 mega + 59 large + 1 mid (106/107 large-cap)** → blended ON half-spread
**2.61 bps** vs OFF ~1.5 bps (liquid large-cap ADV). At the documented ~26×/yr
turnover: **+58 bps/yr drag = ΔSharpe −0.038** (−0.019 at 13×). So honest costs
alone move the survivorship-biased base only slightly — **because it is all
large-caps.**

**The big bite is the PIT-broadened universe** (T-207 / Phase-2): adding the
small/micro delisted cohort is what makes realistic costs worth −0.12 to −0.74
Sharpe (parametric in the small/micro turnover share f). **So the cost-honesty and
survivorship corrections COMPOUND — neither is honest alone.** The realized
OFF-vs-ON backtest on the PIT universe (the canonical number) is compute-bound
locally (T-207) → a cloud cell at re-baseline: flip `realistic_retail_costs:true`
in the cost config, run static & PIT × OFF/ON, report the 4-way Sharpe grid.

## 5. Turnover — the reducible lever (Phase-1 requirement)
Cost drag is LINEAR in turnover, so **halving the ~26× turnover recovers HALF the
realistic-cost drag:**
| small/micro turnover share f, stress s | 26× drag (ΔSharpe) | 13× drag (ΔSharpe) | recovered |
|---|---|---|---|
| f=10%, s=50bps | 182 bps/yr (−0.12) | 91 (−0.06) | +0.06 |
| f=25%, s=50bps | 455 (−0.30) | 228 (−0.15) | +0.15 |
| f=25%, s=100bps | 1105 (−0.74) | 552 (−0.37) | +0.37 |
This directly motivates Phase-1's "lower-turnover construction": at realistic
costs, turnover reduction (T-148 buffering / a lower-turnover composer) is the
single largest cost lever — it buys back as much Sharpe as the cost-honesty
correction takes, proportionally. (The static-109 −0.038 likewise halves to −0.019.)

## Honest read on the kill line
Static-109 base 0.751 − 0.038 (honest large-cap costs) ≈ **0.71** still clears the
0.40 kill line on its own. But the HONEST base is the PIT universe under realistic
costs: 0.751 − ~0.045 (survivorship) − [−0.06 to −0.74] (realistic costs, f-dep) →
**plausibly through 0.40** at the harsher (high-f / high-turnover) end. The number
that decides it is the PIT × realistic-ON realized cell (cloud) + the true PIT cap
history. Until then: the base is borderline and the two un-netted upward biases are
now both removable.

## Files
- `engines/execution/slippage_model.py` — `realistic_retail_costs` mode + cap-tier
  classification + the market-cap-join lookup (default-OFF, byte-identical OFF)
- `config/backtest_settings.json` — `realistic_retail_costs:false` + cap-tier
  spreads (the knob; default-OFF)
- `scripts/build_market_cap_tiers_t210.py` — the current-cap snapshot join builder
- `data/universe/market_cap_tiers.json` — static-109 caps (107/109; gitignored data)
- `tests/test_realistic_retail_costs_t210.py` — 5 tests (OFF-identical + cap-tier)

## NOT done (per constraints)
Default is OFF — the production canon is unchanged (proven). Did NOT turn the mode
ON in production (that's the cloud re-baseline / C's gate). The realized PIT×ON
Sharpe is a cloud cell. PIT point-in-time cap history (Norgate/FMP) is the flagged
follow-on. Branch only; director merges.
