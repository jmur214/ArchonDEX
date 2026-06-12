---
task_id: T-2026-06-11-157
title: Re-price T-135's LPS overnight harvest under the SHIPPED auction-fill model (T-146)
date: 2026-06-11
scope: pure analysis on existing artifacts — no engine code, no flags, LOCAL only, zero behavior change
status: PRE-REGISTRATION COMMITTED FIRST; results appended after
outcome: "[PENDING — this header updated after the nets are computed. The pre-registration below is committed BEFORE any net number is unblinded.]"
---

# T-157 — LPS Overnight Harvest, Re-Priced Under Auction Fills

## 1. PRE-REGISTRATION (committed before computing nets)

### 1.1 The question (binary, fixed in advance)

T-135 measured the project's first strict-gate factor-α — the LPS
overnight component, +13.88%/yr α, t=5.69, raw annualized +13.60%/yr —
and ruled the overnight-only harvest (enter MOC, exit MOO, daily)
**cost-dead 4-5×** under the legacy flat 5 bps/side assumption
(~20 bp/day cost vs 5.4 bp/day gross). T-146 then shipped auction
fills (official open/close auction print + 1.0 bp adverse safety, no
spread/impact at our <0.001% ADV size). The outside review (T-156)
flagged this as the cheapest open false-negative channel.

**Binary question: under the shipped auction-fill model + borrow +
taxes, does ANY account context (Roth / taxable-IL) produce a net
annualized return with block-bootstrap ci_low > 0?**

If NO in all contexts → T-135's UNHARVESTABLE verdict survives the
shipped fill model; the channel closes for good. If YES in any →
flagged to director (no flag-flip, no build — recommend-only).

### 1.2 The gross object (reused, not re-derived)

The T-135 overnight component daily series `s_on` (w·r_on of the
monthly-rebalanced tercile long-short, inverse-vol legs,
dollar-neutral, signal winsorized ±20%, snap-back opens repaired),
window 2000-2025, exactly as built by
`scripts/analyze_overnight_intraday_t135.py::build_strategy`. The
re-price script imports those construction functions UNCHANGED.

**Fidelity gate (must pass before any cost math):** the rebuilt series
must reproduce the T-135 artifact values
`ann_return_pct = 13.60304523983977` and
`ann_vol_pct = 18.009753538803963`
(artifact: agent-d worktree
`data/measurements/overnight_intraday_t135/overnight_intraday_analysis.json`)
to ≥6 significant figures. If it does not, STOP and report — no
re-pricing on an unverified panel.

### 1.3 Harvest mechanics (fixed)

Overnight-only harvest: enter BOTH legs at the closing auction (MOC),
exit BOTH legs at the opening auction (MOO), every trading day. Gross
book = 1× long + 1× short = 2× capital gross exposure. By
construction the harvest cannot carry positions through the intraday
session, so fills are full in/out daily:

- fills/day = entry 2× + exit 2× = **4× capital notional/day**
- sells/day = short entry 1× + long exit 1× = **2× capital
  notional/day** (fee-bearing sides)

No netting credit is taken for day-over-day weight overlap (the
overnight harvest exits every morning by definition).

### 1.4 Cost configuration (all values fixed BEFORE computing)

| Channel | Value | Source |
|---|---|---|
| Auction safety | **1.0 bp adverse per side** → 4 fills × 1.0 = **4.000 bp/day** | T-146 shipped default `auction_safety_bps: 1.0` (`config/backtest_settings.json`); no spread/impact per T-146 auction model |
| SEC §31 (sells only) | 2.78e-5 × 2× capital = **0.556 bp/day** | `backtester/alpaca_fees.py::AlpacaFeesConfig.sec_fee_per_dollar` (= $27.80/$1M, 2026 published) |
| FINRA TAF (sells only) | $0.000166/share; assumed median share price **$60** → 0.0277 bp × 2× = **0.055 bp/day** | `AlpacaFeesConfig.taf_per_share`; $60 is a stated assumption (cap $8.30/trade not binding at our size) |
| Commission | $0 | Alpaca equities commission-free (`base_commission: 0.0`) |
| Borrow (short leg) | **0.30%/yr on 1× capital ≈ 0.119 bp/day** (primary); **1.00%/yr ≈ 0.397 bp/day** (sensitivity arm) | Easy-to-borrow general-collateral assumption; Alpaca ETB base ≈ 0.3%/yr, IBKR GC ≈ 0.25%/yr (stated assumption — the T-135 universe is liquid large-cap, predominantly ETB). Charged nightly on the 1× short notional. |
| **Total cost/day (primary)** | **4.730 bp/day ≈ 11.92%/yr** (sensitivity arm: 5.008 bp/day ≈ 12.62%/yr) | sum of the above × 252 |

Legacy comparison column (the standing T-135 verdict): flat 5 bp/side
× 4 fills = 20 bp/day ≈ 50.4%/yr.

### 1.5 Tax treatment (fixed)

100% short-term (every position held <1 day). Per project conventions
(`backtester/tax_drag_model.py` + T-141 IL deployment context):

- **Roth:** 0% — after-tax net = pre-tax net.
- **Taxable-IL:** combined ST rate = 30% federal (project midpoint
  convention) + 4.95% IL flat = **34.95%**, applied as
  `net_after_tax = net_pre_tax × (1 − 0.3495)` when net_pre_tax > 0
  (annual netting, full intra-strategy loss offset). **Wash-sale
  disallowance NOT modeled** — daily re-entry of the same names makes
  wash-sale adjustments material in detail but they can only make the
  taxable result WORSE (deferral of losses), so this simplification is
  conservative-in-favor-of-harvestability for the taxable arm: if
  taxable fails under it, it fails a fortiori with wash-sales.

### 1.6 Statistics (fixed)

Net daily series = `s_on_daily − cost_per_day` (cost as a constant
daily decimal). Block bootstrap on the NET daily series: block = 7,
n_iter = 1000, seed = 42 (the same parameters as the T-115/T-128
analyses), 95% CI on the annualized net return (and net Sharpe
reported alongside). The α-channel is reported secondarily by shifting
T-135's α point/CI by the annualized cost constant (costs are
deterministic, factor-orthogonal).

### 1.7 Decision rule (fixed)

**Harvestable iff net annualized ci_low > 0 in at least one account
context** (Roth pre-tax; taxable after-tax). Point-positive with
ci_low ≤ 0 is NOT harvestable (CLAUDE.md #6 — ci_low, not point).

### 1.8 N-trials policy (stated before unblinding)

**N_trials += 0.** This is re-accounting of a CLOSED measurement: the
return series, hypothesis, and construction are unchanged from T-135
(which already consumed its trial); the only change is the
deterministic cost constant subtracted from an already-measured
series. The bootstrap on the net is a monotone shift of the gross
distribution — no new search dimension is opened, no variant is
selected post-hoc (every cost number above is fixed by shipped
defaults or stated assumptions, committed before unblinding). If the
director prefers the stricter reading (auction-model re-price = new
test of the same hypothesis), the honest increment is N += 1; flagged
for the merge decision. The pre-registered primary is N += 0.

---

## 2. RESULTS

[APPENDED AFTER THE PRE-REGISTRATION COMMIT — see commit history:
the section above is committed before any net number was computed.]
