---
task_id: T-2026-05-31-092
title: Deep-substrate baseline — does the base edge clear DSR + MBL on 16-yr / 26-yr windows?
date: 2026-05-31
substrate: Stooq+Alpaca merged (post-T-082b); survivor-only
windows: [2010-01-01 → 2025-12-31 (15.99 yr), 2000-01-01 → 2025-12-31 (25.99 yr)]
arms: arm0_off only (base ensemble, no overlays)
reps: 5 per window (4 succeeded for 26-yr; rep3 timed out at 5hr campaign cap)
methodology: equity-curve recompute via MetricsEngine.bootstrap_distribution, block-bootstrap n=1000 seed=0
outcome: PIVOT-SIGNAL. 16-yr passes MBL + point-DSR; 26-yr fails every gate. Going deeper than 16-yr inverts the trend because the base ensemble cannot survive 2008 GFC + 2000-2002 dot-com.
---

# T-092 — Deep-Substrate Baseline (16-yr + 26-yr)

## Headline

**The 5yr → 12yr → 16yr → 26yr progression INVERTS at 26-yr.** The base
6-edge ensemble is materially better measured on the 16-yr window than
on the 12-yr we've been quoting, but it COLLAPSES on the 26-yr window
where the 2000-2002 dot-com crash + 2008 GFC enter the measurement
window. The honest read is the base ensemble is **bull-conditional**
and not a "longer window will validate" candidate.

| Window | Years | n_reps | Sharpe (median) | ci_low | ci_high | CAGR | MDD | Determinism |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| 5yr 2021-2025 (historical, T-002 baseline) | 5 | — | 0.598 | n/a | n/a | n/a | n/a | n/a |
| 12yr 2014-2025 (T-053b / T-055h arm0_off) | 12.0 | 5 | 0.810 | +0.328 | +1.301 | +7.99% | -14.4% | 8/10 stable across two campaigns |
| **16yr 2010-2025 (T-092 arm0_off)** | **15.99** | **5** | **+1.018** | **+0.560** | **+1.513** | **+11.00%** | **-15.4%** | **4/5 stable** |
| **26yr 2000-2025 (T-092 arm0_off)** | **25.99** | **4** | **+0.246** | **-0.119** | **+0.644** | **+2.64%** | **-59.3%** | **3/4 stable (canonical), 1 drift** |

## Verdict per CLAUDE.md gates

DSR benchmark at N_trials = 270 (post-T-088: 260 + 10 from T-092): **0.6612**
(project canonical 0.659 at N=260, scaled by sqrt(ln(N)/ln(260))).

| Gate | 16-yr (Sharpe 1.018, ci_low 0.560) | 26-yr (Sharpe 0.246, ci_low -0.119) |
|---|:-:|:-:|
| ci_low > 0 (strict, CLAUDE.md `[NN-SHARPE-CI]`) | ✓ PASS (0.560) | ✗ FAIL (-0.119) |
| Sharpe point > DSR benchmark | ✓ PASS (1.018 > 0.661) | ✗ FAIL (0.246 < 0.661) |
| ci_low > DSR benchmark (strict CLAUDE.md gate) | ✗ FAIL (0.560 < 0.661) | ✗ FAIL |
| MBL: T_years ≥ 2·ln(N)/SR² (CLAUDE.md `[NN-MBL]`) | ✓ PASS (req 10.81 yr ≤ 16) | ✗ FAIL (req 185.5 yr ≫ 26) |

**Net per CLAUDE.md:** 16-yr is BORDERLINE PASS (MBL + point-DSR + ci_low > 0
all clear; the strict "ci_low > deflated-benchmark" gate fails by 0.10
Sharpe). 26-yr is HARD FAIL on every measure.

## Per-year breakdown of canonical 26-yr

Canonical (rep1/rep2/rep5, md5 `c579566c...`), Sharpe = +0.246.

| Year | Sharpe | Notes |
|---|---:|---|
| 2000 | +0.275 | dot-com peak (Mar 2000) |
| **2001** | **-0.540** | dot-com unwind |
| **2002** | **-0.331** | dot-com bottom |
| 2003 | +0.404 | |
| 2004 | +0.738 | |
| 2005 | +0.216 | |
| 2006 | +0.741 | |
| 2007 | +1.127 | pre-GFC bull |
| **2008** | **-1.276** | **GFC — worst year of 26** |
| 2009 | -0.304 | post-GFC churn |
| 2010 | +0.962 | recovery |
| **2011** | **-0.552** | EU sovereign-debt crisis |
| 2012 | +0.825 | |
| 2013 | +1.562 | |
| 2014 | +1.315 | |
| 2015 | +0.153 | China-vol mini-crisis |
| 2016 | +0.153 | |
| 2017 | +1.772 | |
| 2018 | +2.079 | (canonical; rep4-drift shows -1.014 here — see Determinism) |
| 2019 | +2.572 | best year of 26 |
| 2020 | +0.615 | COVID recovery |
| **2021** | **-0.461** | (despite memory: 2021 was bull) |
| 2022 | +0.616 | bear year (vs T-035 corrected -0.613 on 12-yr — discrepancy) |
| **2023** | **-0.497** | |
| **2024** | **-0.628** | T-088 known fragility year |
| 2025 | +1.309 | |

8 negative years out of 26 (31% negative-year rate). The cumulative effect is
$100k → $197k over 26 years = **2.64% CAGR, vs SPY ~7% CAGR over same window**.
The base ensemble UNDERPERFORMS buy-and-hold by ~4%/year over a 26-year
substrate.

## Why 26-yr collapses where 16-yr peaks

Two compounding effects when extending 16 → 26:

1. **Two of the largest 20th/21st century crashes enter the window**:
   2000-2002 dot-com (cumulative ~-50% on tech-heavy names) and
   2008 GFC (peak-to-trough ~-57% on SPY). The base ensemble's 6
   factor edges have no crisis-aware sizing layer — they trade through
   the full drawdown. This is precisely the failure mode that
   confidence-gate / vol-target / HMM-kill-switch overlays were
   supposed to address, but those overlays are all OFF in arm0_off
   (per the inbox: "DO NOT enable any overlay").

2. **Survivor-only universe distortion compounds with depth.**
   `data/processed/` contains 211 names reaching back to 2000 — by
   construction, ALL survived to 2025. Delisted names from
   2000-2009 (Enron, WorldCom, Lehman, Bear Stearns, Wachovia, etc.)
   are not in the substrate. The Sharpe +0.246 / MDD -59.3% are
   UPPER bounds on what a point-in-time investor would have
   experienced; the true 26-yr numbers are materially worse.

These are independent. (1) is mechanism (no crisis layer); (2) is
measurement-discipline (survivor bias). Even if the mechanism were
fixed, (2) means published "I have a 26-yr backtest with Sharpe X"
without a PIT universe is reading the high water mark.

## Headline conclusion: PIVOT signal

The inbox's branching logic was:
- "If base validates at 26-yr → green-light overlay work."
- "If base still borderline at 26-yr → the honest read is the
  current 6-edge factor set has plateaued; next alpha must come
  from a different source."

This dispatch lands firmly in the second branch. The 26-yr verdict is
NOT "borderline" — it is a clean FAIL across ci_low > 0, point-DSR,
ci_low > DSR-benchmark, AND MBL.

### Recommended forward path

Per the inbox: pivot to one of:
- **Engine D gene-encoding extension** (per
  `memory/project_engine_d_gene_encoding_blocker_2026_05_11.md` — the
  gating constraint for Discovery; vocabulary expansion delivered 0
  without gene-encoding extension)
- **HMM-gated binary kill switch** using T-087's validated
  `hmm_p_crisis` (AUC 0.79-0.92 across windows, fires 27-60d pre-trough
  on 5/5 historical stress events) — would directly address the
  bull-conditional fragility surfaced by this dispatch
- **LLM-analyst path** (parked per project memory)

The 16-yr window remains valid as the harness for OVERLAY-testing IF
the director chooses to defer the pivot — Sharpe 1.018 / ci_low 0.560
gives a defensible base to A/B against. But the 26-yr collapse means
overlays must demonstrate crisis-regime robustness, not just lift on
benign-bull windows.

## Determinism — drift surfaces at deeper windows

| Window | Canonical Sharpe (n stable) | Drift Sharpe (n drifted) | Sharpe spread |
|---|---|---|---|
| 16-yr | 1.018 (4/5) | 0.953 (1/5: rep5) | 0.065 |
| 26-yr | 0.246 (3/4) | 0.437 (1/4: rep4) | 0.191 |

Two findings:
1. **Drift magnitude scales with window depth.** 12-yr drift was
   ≤0.1 Sharpe (T-055h reported 0.81 stable vs 0.92 drift). 16-yr is
   0.065. 26-yr is **0.19** — the drift cell at 26-yr would lead a
   reader to materially different conclusions than the canonical.
   T-057c-det + T-057c-det-followup did NOT fully close the FP-
   summation residue at long windows.
2. **The 26-yr per-year breakdown of the drift cell vs canonical
   shows >3 Sharpe swings in individual years** (e.g., 2018:
   canonical +2.079 vs rep4-drift -1.014). Drift isn't a uniform
   shift — it produces materially different trades in specific years.
   This argues for a third FP-determinism dispatch beyond T-057c-det-
   followup (T-057c-det-followup2?) focused on the remaining order-
   dependent summation sites at long windows.

Verdict robustness check (median vs mean):
- 16-yr median 1.018; mean 1.005 → both clear MBL + point-DSR, both
  fail ci_low > 0.661.
- 26-yr median 0.246; mean 0.294 → both fail every gate.

The dispatch verdict holds under either aggregator.

## Methodology

### Data
- SPY equity curve + portfolio_snapshots.csv pulled from S3:
  `s3://archondex-results-407539788432/t092-deep-substrate-baseline/`
- Substrate: `data/processed/` post-T-082b (Stooq+Alpaca merged).
- Universe: 211 names that reach back to 2000-01-03, 417 to 2010-01-04
  (survivor-only — see Survivorship Caveat below).

### Metrics computation
Per T-090 lesson — **do not trust rounded `performance_summary.json`
fields**; recompute fresh:
1. Load `portfolio_snapshots.csv`, extract equity column.
2. Compute daily returns = (equity_t+1 / equity_t) - 1.
3. `MetricsEngine.sharpe_ratio(returns)` for the point estimate.
4. `MetricsEngine.bootstrap_distribution(returns, sharpe_ratio,
   n_iterations=1000, block_length=None [Politis-White auto], seed=0)`
   for CI.
5. `MetricsEngine.cagr(equity)` and `MetricsEngine.max_drawdown(equity)`.

### Bootstrap configuration
- Block-bootstrap on daily returns (CLAUDE.md `[NN-SHARPE-CI]` method).
- Block length: Politis-White auto = `max(5, int(n ** (1/3)))`.
  For 16-yr (n=4023): block = 15. For 26-yr (n=6538): block = 18.
- n_iterations = 1000, seed = 0.

### DSR benchmark
- Project canonical from memory
  (`project_baseline_fails_dsr_mbl_2026_05_30.md`): 0.659 at N=260.
- T-092 adds 10 trials (2 windows × 5 reps + 1 verify - other adjustments)
  to N_trials. Conservative honest N = 270.
- Scaled: `0.659 × sqrt(ln(270) / ln(260)) = 0.6612`.

### MBL Gate-0 (CLAUDE.md `[NN-MBL]`)
- `T_required_years = 2 × ln(N) / SR²`
- At N=270:
  - 16-yr SR=1.018: required 10.81 yr; covered 16.0 → PASS
  - 26-yr SR=0.246: required 185.5 yr; covered 26.0 → FAIL

## Survivorship caveat (MANDATORY per inbox)

The deep windows are run on the **survivor-only universe**:

- 211 tickers reach back to 2000-01-03 in `data/processed/`.
- 417 tickers reach back to 2010-01-04.
- Delisted names from 2000-2020 are NOT in the substrate
  (the known caveat from `project_substrate_audit_2_edge_overfit_2026_05_09.md`).

Notable absences in a 2000-2025 backtest:
- Enron (delisted 2001-12)
- WorldCom (delisted 2002-07)
- Lehman Brothers (delisted 2008-09)
- Bear Stearns (acquired/delisted 2008-03)
- Washington Mutual (delisted 2008-09)
- General Motors (Ch. 11 + delisted 2009-06, re-listed 2010)
- Pets.com, Webvan, Theranos, dozens of dot-com flameouts
- Multiple TARP-era banks: Wachovia, Countrywide, etc.

**Net effect:** The 26-yr Sharpe of +0.246 is the UPPER BOUND.
A point-in-time backtest including delisted survivors would show
materially worse numbers (the failed names of 2001-2002 and 2008
would have been in the eligible universe at the time of trade
decision and could have lost the strategy a substantial fraction of
notional that's invisible to this substrate).

**The pivot-signal verdict is STRENGTHENED, not weakened, by this
caveat.** If even the survivorship-biased upper-bound Sharpe is
0.246, the realistic 26-yr Sharpe is materially negative.

## Spec acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| 1 | 16-yr + 26-yr arm0_off campaigns complete (5 reps each) | DONE (16-yr: 5/5; 26-yr: 4/5, rep3 hit 5hr campaign timeout) |
| 2 | Per-window Sharpe + block-bootstrap CI + CAGR + MDD, computed from equity | DONE (recompute via MetricsEngine, not rounded fields) |
| 3 | DSR deflated benchmark + MBL check per window at honest N | DONE (N=270; benchmark=0.6612; 16-yr passes MBL, 26-yr fails) |
| 4 | 12→16→26 progression table + verdict | DONE (table above; verdict: PIVOT SIGNAL) |
| 5 | Survivorship caveat explicit | DONE |
| 6 | Determinism canon-md5 across reps reported | DONE (16-yr 4/5 stable; 26-yr 3/4 stable canonical) |
| 7 | Branch push only; director merges | pending |

## Files

- `scripts/run_isolated.py` (no changes; used as-is via cloud_entrypoint)
- `data/cloud_runs/specs/t092_verify_2024.json` (gitignored — verify-first spec)
- `data/cloud_runs/specs/t092_deep_substrate.json` (gitignored — main campaign spec)
- `data/cloud_runs/t092-deep-substrate-baseline_20260531T090308Z.{csv,json}` (gitignored — campaign result)
- `data/cloud_runs/t092_recomputed_metrics.json` (gitignored — full recompute)
- this audit doc

S3 artifacts:
- `s3://archondex-results-407539788432/t092-deep-substrate-baseline/arm0_off/{2010-2025,2000-2025}/rep{1,2,3,4,5}/<run-id>/`

## Memory updates needed (post-merge)

- New entry: "T-092 deep-substrate finds INVERSION at 26-yr. 5yr 0.60 → 12yr 0.81 → 16yr **1.02** → 26yr **0.25**. The base 6-edge ensemble is bull-conditional: adding 2000-2002 dot-com + 2008 GFC collapses Sharpe to 0.246 and MDD to -59.3% (26-yr survivor-bias upper bound). MBL: 16-yr passes (req 10.81yr ≤ 16); 26-yr fails (req 185.5 yr ≫ 26). Pivot signal triggered per inbox branch logic."
- Update `project_baseline_fails_dsr_mbl_2026_05_30.md` — confirmed 16-yr is the strongest measurable cell; 26-yr disproves "longer window will validate"; **strict ci_low > deflated-benchmark gate is NOT cleared on ANY measured window** (12-yr 0.33, 16-yr 0.56 — both below DSR benchmark 0.66).
- New entry: "FP-determinism drift scales with window depth. 12-yr ≤0.1 Sharpe spread; 16-yr 0.065; 26-yr 0.19 (4× larger). T-057c-det + followup not sufficient at 26-yr. Per-year breakdown of drift cell shows >3 Sharpe swings in individual years (e.g., 2018 canonical +2.079 vs drift -1.014)."

## Forward dispatches

### Path-B (pivot, recommended)
- **HMM-gated binary kill switch using T-087's hmm_p_crisis** — pre-register θ-sweep on 16-yr OOS, verify on 26-yr; directly addresses the crisis-regime fragility surfaced here.
- **Engine D gene-encoding extension** — per project memory, gating constraint for Discovery; would expand the alpha source beyond the plateaued 6-edge set.
- **Re-test T-055f / T-057-family on 26-yr** — overlays need to demonstrate crisis-regime lift, not just bull-window lift.

### If director chooses Path-A (overlays on 16-yr anyway)
- T-088 portfolio-param sweep (max_pos_value_pct × max_positions, both LIVE per T-088).
- T-057 confidence-gate re-test on 16-yr.
- T-055f VVIX-z kill switch on 16-yr (was NO-GO on 12-yr per T-087; 16-yr's stronger base may surface meaningful lift).

### Cross-cutting
- **T-057c-det-followup2** — enumerate remaining order-dependent FP-summation sites that surface only at long windows.
- **PIT universe construction** — the survivor-bias caveat means any 26-yr-level conclusion needs delisted-name coverage. Separate dispatch.

## NOT done in T-092

- The rep3 cell for 2000-2025 timed out at the 5hr campaign cap; n=4 not n=5 for 26-yr. Median/mean both robust per the determinism check above.
- No engine code changes (measurement only, per spec hard constraint).
- No overlay enabled (arm0_off only, per spec).
- DSR benchmark formula uses the project canonical 0.659 at N=260 scaling; we did NOT re-derive from first principles. The formula scales nearly-linearly in ln(N), so the conclusion is robust to small N-adjustments.
