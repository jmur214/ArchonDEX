---
task_id: T-2026-06-11-152
title: CUSUM / Page-Hinkley divergence monitors — calibrated kill metrics, shadow-only
date: 2026-06-11
substrate: n/a (shadow/reporting infra + calibration on existing artifacts + synthetic injections; zero behavior change; zero N_trials)
scope: backtester/divergence_monitors.py + calibration script + additive summary fields; live_trader untouched (paper-loop hook documented only)
outcome: **Delivered, with two calibration findings that ARE the deliverable.** (1) Operating points locked at ≤1 false alarm/yr on 200 block-bootstrap null replicas: CUSUM-mean (k=1.0, h=5.0; 0.91/yr), CUSUM-variance (k=2.0, h=12.0; 0.95/yr — a channel ADDED after calibration showed why it's needed), Page-Hinkley (δ=0.05, λ=20σ; 0.64/yr — **the research's PH parameters were mis-scaled ~80× for standardized inputs and alarmed ~104×/yr; re-scaled and documented**). (2) **THE POWER HEADLINE, honest: vol-scale breaks are detected in ~13–16 trading days (miss ~5%), but a 50% edge degradation is a ~0.04σ/day mean shift — UNDETECTABLE by any daily mean-shift monitor on sub-quarter horizons** (same math as Sharpe needing years); realistic alpha decay belongs to safe-f/CAR25 + deep-window cadence, not daily monitors. (3) Face validity: on the real 2024 record the monitors fired exactly on the yen-carry unwind (2024-08-05) and the US-election week (10-31, 11-06) — unprompted.
---

# T-152 — Divergence monitors (CUSUM + Page-Hinkley), calibrated shadow kill metrics

## The headline (what the calibration bought)

At the chosen operating points (~≤1 false alarm/yr each):

| scenario (126td window) | CUSUM-mean | Page-Hinkley | CUSUM-var |
|---|---|---|---|
| vol doubling | **16d [p90 66d], miss 5%** | 38d [89d], miss 10% | **13d [53d], miss 5%** |
| sign-flip month | 48d [100d], miss 60% | 77d [119d], miss 70% | 44d [99d], miss 64% |
| fee shift −5bp/day | 40d [104d], miss 54% | 63d [117d], miss 54% | 36d [97d], miss 63% |
| 50%-degraded edge | **no detect** | 60d [119d], miss 92% | no detect |

**The structural finding:** at our signal-to-noise (daily edge ~6bp on
~80bp vol), halving the edge moves the daily mean by ~0.04σ — no daily
mean-shift detector can catch that inside a quarter at a sane
false-alarm rate. What daily monitors CAN catch fast is vol-scale
divergence (~2-3 weeks). **The ops kill stack therefore pairs:**
(a) these monitors for vol/regime-scale breaks (days-weeks),
(b) T-151's safe-f/CAR25 + scheduled deep-window re-measurement for
alpha-decay-scale divergence (months — irreducibly). Discovering this
NOW, on backtest data, instead of while capital is at risk, is the
entire point of the brief's "tune before paper" instruction.

**Face validity on the real record:** under the self-null at the
operating points, the actual 2024 book fires CUSUM-mean on
**2024-08-05** (the yen-carry unwind / VIX-65 day), **2024-10-31** and
**2024-11-06** (US election week); CUSUM-var on the same Oct/Nov pair;
PH once (2024-04-16, the April drawdown). The scrambled-null rate is
~0.9/yr — the real path alarms above it because it contains genuine
regime structure the 10-day-block null destroys. The monitors found
2024's two real market events without being told.

## Calibration findings (the deliverable working as designed)

1. **The research's Page-Hinkley parameters were mis-scaled for
   standardized inputs.** δ=0.005, λ=50δ=0.25 (σ-units) alarmed
   ~104×/yr across the whole research grid — the PH statistic on
   z~N(0,1) random-walks ~1σ/day, so λ must be O(5–20)σ. Re-scaled grid
   (δ ∈ {0.05, 0.1, 0.2} × λ ∈ {5, 10, 20}); the research values were
   presumably raw-return-units. Provenance + deviation documented in
   the module and the grid header.
2. **The mean channel is near-blind to the scenario that matters most**
   (50% edge degradation) — hence the **variance channel was added**
   (zv = (z²−1)/√2 through the same CUSUM machinery) with its own
   χ²-scaled grid (the N(0,1)-scale cells over-alarm 5–22×/yr on the
   heavy-tailed zv; k ∈ {1, 1.5, 2} × h ∈ {6, 8, 10, 12} reaches the
   target). The first grid pass printed the loud "NO cell meets target"
   warning rather than silently picking an over-alarming cell.

## What was built

- **`backtester/divergence_monitors.py`** — `CusumMonitor` (two-sided,
  standardized, reset-after-alarm), `PageHinkleyMonitor` (two-sided,
  running-mean PH), `standardized_innovations` (LAGGED rolling μ/σ —
  stats through t−1 standardize r_t, no lookahead; σ tolerance-guarded),
  `run_monitor` (batch driver, PROVEN equal to incremental `update()`
  calls — the streaming contract the paper loop will use), and
  `shadow_report` (the summary block at the calibrated operating
  points; config overrides via optional `divergence_monitors` block).
- **`scripts/calibrate_divergence_monitors_t152.py`** — the three-stage
  calibration: bootstrap-null false-alarm grids (B=200, 10d circular
  blocks, seed 0) → operating-point selection (most sensitive cell ≤1
  FA/yr; loud failure when none qualifies) → injected-divergence power
  (standardization FROZEN pre-break = the live semantics) → the actual
  record's alarms with dates.
- **Summary fields (additive, contract-extended atomically):**
  `divergence_alarms` (total at operating points) + `divergence_detail`
  (per-channel counts/dates/params, alarm-date lists nested per the
  pd.isna constraint). On a BACKTEST record these flag internal regime
  structure; on the future paper stream they're the kill metrics.

## The paper-loop hook (documented only — NOT built; live_trader untouched)

The live wiring (paper-trading milestone, propose-first): feed daily
(realized − expected) innovations where **expected = the backtest's
rolling stats** (not self-stats); one monitor set per account
(T-141 router); alarm action is PRE-REGISTERED as REDUCE/FLATTEN only
(ops playbook: "the only allowed manual action") with the operating
points frozen at these calibrated values unless re-registered BEFORE
go-live. The streaming `update()` contract is the integration surface;
`shadow_report` shows the exact consumption pattern.

## Tests — 15 new green; suite fully green

Detection on injected mean breaks (both sides) + vol doubling via the
variance channel; near-quiet on 4-year iid nulls at the operating
points; **streaming == batch equivalence** (both monitors); repeat-run
determinism; NaN-skip and σ-guard degenerates; invalid-param
validation; lookahead-free standardization (a 20σ spike is NOT shrunk
by its own day's σ); shadow-report shape/JSON/skip; producer emission.
Contract suite green. Full suite: **2316 passed, 0 failed** — the five
long-standing pre-existing failures are fixed on main as of this run
(first fully-green suite in this lane's records).

## Files

- `backtester/divergence_monitors.py` — NEW
- `scripts/calibrate_divergence_monitors_t152.py` — NEW
- `cockpit/metrics.py` — `_divergence_report()` + 2 summary keys
- `tests/test_contracts.py` — keys
- `tests/test_divergence_monitors_t152.py` — NEW; 15 tests
- this audit

## NOT done

- Paper/live wiring (documented above; live_trader untouched)
- Any action on alarms (shadow only)
- Deep-window calibration refresh (re-run the script on a 26-yr run dir
  when available — same one-command pattern as T-151; the operating
  points may tighten with more regime diversity in the null)
