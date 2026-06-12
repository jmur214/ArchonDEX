---
task_id: T-2026-06-11-157
title: Re-price T-135's LPS overnight harvest under the SHIPPED auction-fill model (T-146)
date: 2026-06-11
scope: pure analysis on existing artifacts — no engine code, no flags, LOCAL only, zero behavior change
status: CURRENT (pre-registration committed first — see git history; results appended after)
outcome: "**UNHARVESTABLE VERDICT SURVIVES — in every account context, under both borrow arms.** But the margin story transforms: legacy 5bp/side said cost-dead 4-5× (net −36.8%/yr); the shipped auction model says net +1.68%/yr POINT-POSITIVE (Roth, 0.30% borrow) with ci [−2.01, +5.94] — Sharpe 0.09, ci_low < 0 → fails CLAUDE.md #6 decisively. Taxable-IL +1.09%/yr, same negative ci_low. The false-negative channel is now closed under the CORRECT cost model, not the wrong one: the overnight α is real (+13.6%/yr gross, ci_low +9.9) but the harvest consumes 12 of its 13.6 points in auction safety + fees + borrow, leaving a remainder indistinguishable from zero. N_trials += 0 per pre-registered policy. Fidelity gate PASSED (rebuilt panel reproduces artifact to 1e-6)."
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

(Appended after the pre-registration commit — verify in git history
that section 1 predates every number below.)

### 2.1 Fidelity gate — PASS

Rebuilt `s_on` (6,539 obs): `ann_ret = 13.60304523983977`,
`ann_vol = 18.009753538803963` — **exact** reproduction of the T-135
artifact targets (rtol 1e-6). The panel is the same object T-135
measured.

### 2.2 The verdict table

Net annualized return (% / yr), block-bootstrap 95% CI (block=7,
n=1000, seed=42) on the net daily series:

| Arm | Cost/day | Roth net (ci) | Taxable-IL net (ci) | Harvestable (ci_low>0)? |
|---|---|---|---|---|
| Gross (no costs) | 0 | **+13.60** [+9.91, +17.86], Sharpe 0.76 | +8.85 [+6.45, +11.62] | (diagnostic only — not tradeable) |
| **Legacy 5bp/side (the standing T-135 verdict)** | 20.0 bp | **−36.80** [−40.49, −32.54], Sharpe −2.04 | −36.80 (no gains to tax) | **NO** — cost-dead, matches T-135's "dead 4-5×" |
| **Auction (T-146) + fees + 0.30%/yr borrow — PRIMARY** | 4.730 bp | **+1.68** [−2.01, +5.94], Sharpe 0.09 | +1.09 [−2.01, +3.87] | **NO** — point-positive, ci_low < 0 |
| Auction + fees + 1.00%/yr borrow — sensitivity | 5.008 bp | +0.98 [−2.71, +5.24], Sharpe 0.05 | +0.64 [−2.71, +3.41] | **NO** |

Cost-channel decomposition (primary arm, bp/day): auction safety
4.000 + SEC 0.556 + TAF 0.055 + borrow 0.119 = **4.730 bp/day ≈
11.92%/yr** against 5.40 bp/day (13.60%/yr) gross.

### 2.3 The binary answer

**NO account context flips to harvestable. T-135's UNHARVESTABLE
verdict SURVIVES the shipped auction-fill model** — under the
pre-registered decision rule (net annualized ci_low > 0), in Roth and
taxable-IL, under both borrow arms.

### 2.4 What changed anyway (the honest characterization)

The legacy model said the harvest was **cost-dead 4-5×** (net
−36.8%/yr — an absurdity scale). The shipped auction model says the
harvest is **point-positive (+1.68%/yr Roth) but statistically
indistinguishable from zero** (Sharpe 0.09, CI spanning ±4%). The
auction safety buffer alone (4 bp/day = 74% of gross) is the binding
channel — the strategy's gross edge is 5.4 bp/day and a 4-leg daily
round-trip pays 4.0 bp even at auction prints.

Two structural notes for the record:

1. **The verdict is now robust to the fill model being wrong by a
   factor of 2** — at 0.5 bp/side safety the cost would be 2.73 bp/day
   → net ≈ +6.7%/yr with ci_low ≈ +3.0: that WOULD flip it. The
   binding assumption is T-146's 1.0 bp adverse safety per side. It is
   a conservative buffer for imbalance/thin-auction risk, not a
   measured cost; if live auction-fill telemetry (paper milestone)
   ever shows realized adverse deviation ≪ 1 bp, this cell deserves
   one re-read. Until measured evidence exists, the shipped default
   stands and the verdict is NO.
2. **Capacity/borrow caveats run the wrong way for retail:** at
   2× gross daily auction flow the strategy is tiny relative to
   auction volume (no impact concern at our size), but
   hard-to-borrow names inside the short tercile would push borrow
   well above the GC assumption on exactly the highest-signal names.
   Both unmodeled channels make the harvest WORSE, not better.

### 2.5 N-trials accounting

Per the pre-registered policy: **N_trials += 0** (re-accounting of the
closed T-135 measurement; no new hypothesis, no variant selection —
every cost input was a shipped default or a stated assumption committed
before unblinding). The stricter N += 1 reading is available to the
director at merge if preferred; it does not change any conclusion (the
result is a decisive NO, not a marginal pass).

## 3. Files

- `scripts/reprice_lps_auction_t157.py` (NEW — imports T-135's
  `build_panels`/`build_strategy` unchanged; fidelity-gated)
- `data/measurements/lps_reprice_t157/lps_reprice_auction_t157.json`
  (gitignored output; numbers quoted above)
- this audit (pre-registration committed first; see git history)

## 4. Memory updates needed (post-merge)

- "T-157 (2026-06-11): T-135's LPS overnight UNHARVESTABLE verdict
  SURVIVES the shipped T-146 auction-fill model — net +1.68%/yr point
  (Roth, 0.30% borrow) but ci [−2.01, +5.94], Sharpe 0.09 → fails
  ci_low>0 in every account context. The legacy 5bp model overstated
  the cost (−36.8%/yr); the correct model leaves it point-positive but
  CI-dead. Binding channel = T-146's 1.0bp/side auction safety buffer
  (74% of gross); if paper-trading telemetry ever measures realized
  auction adverse deviation ≪ 1bp, re-read this cell once. The
  false-negative channel flagged by the outside review (T-156) is now
  closed under the correct cost model. N_trials += 0 (pre-registered
  re-accounting policy)."
