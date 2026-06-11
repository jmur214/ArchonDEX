---
task_id: T-2026-06-11-150
title: Intraday/OHLC-derived feature panel + pre-registered screens (the last build-gated door)
date: 2026-06-11
author: Agent D (alpha/edge lane)
outcome: THE ARC'S FIRST POSITIVE SCREEN — Yang-Zhang range-vol BEATS the
  production EWMA(0.94) at next-day vol forecasting under the pre-registered
  bar (SPA p=0.013-0.024, ci_low>0 on BOTH targets, 60-97% of names), plus a
  structural finding: the production EWMA has a catastrophic near-zero failure
  mode on quiet stretches that range-based estimators cannot have. 4/6 OHLC
  features + 2/3 index minute-features clear their MI nulls. This is the
  Engine-B thickening GO input. Feature panels landed with loaders;
  diagnostics only, no engine wiring, N_trials += 0.
status: CURRENT
reproduce: |
  python -m scripts.build_ohlc_features_t150
  python -m scripts.fetch_alpaca_minute_t150
  PYTHONHASHSEED=0 python -m scripts.screen_features_t150   (prereg committed at 78b27d5 before computing)
---

# T-150 — intraday-information features: built, screened, and a first GO

## Part A — OHLC-derived feature panel (zero new data)

`data/research/ohlc_features_t150/features.parquet` — **3.34M rows, 696
tickers, 1999-2025** + loader (`load_ohlc_features`). Features: Yang-Zhang
21d vol (overnight + open-close + Rogers-Satchell terms), Garman-Klass 21d,
trailing overnight mean / overnight-share (the T-135 decomposition repurposed
as conditioning features), gap shock z, gap frequency. **The mandatory
corrupt-opens filter** (T-135 snap-back repair) ran pre-compute — 652 rows
repaired across the panel.

## Part B — index-level minute features (Alpaca IEX, price-shape only)

SPY/QQQ/IWM/DIA/TLT/GLD daily aggregates: first-half-hour return,
opening-range fraction, last-half-hour return.
**Honest coverage correction:** the free-tier IEX minute history starts
**2020-07-27 uniformly** (~5.5 years), NOT the research's "2016+". Volume/
imbalance features deliberately NOT computed (IEX ≈3% of consolidated volume
— the research's explicit caveat). Raw minutes not retained (daily aggregates
only); incremental refresh built in. `data/research/` is not a baked
substrate dir → no manifest regen (T-131 policy checked).

## Part C — pre-registered screens (prereg committed 78b27d5 BEFORE computing)

### Screen 1 — MI vs circular-shift block nulls (T-132 machinery)

| feature | clears null p97.5? |
|---|---|
| yz_vol_21 | **YES** |
| gk_vol_21 | **YES** |
| on_mean_21 | **YES** |
| gap_freq_21 | **YES** |
| on_share_21 | no |
| gap_abs_z | no |
| or_frac (SPY, minute) | **YES** |
| last30_ret (SPY, minute) | **YES** |
| fhh_ret (SPY, minute) | no — the famous first-half-hour return does NOT clear at index level on the 5.5-yr window |

### Screen 2 — THE YZ-vs-EWMA HORSE-RACE (the Engine-B thickening input)

Production spec benchmark: RiskMetrics EWMA on close-to-close returns,
λ=0.94 (`engines/engine_b_risk/vol_target.py:70`). Forecast = next-day
variance; losses = QLIKE (primary) + MSE; verdict = block-bootstrap CI +
SPA on the daily cross-sectional mean QLIKE difference (EWMA − YZ; positive
= YZ better). **Both pre-registered verdicts PASS:**

| target | ΔQLIKE (EWMA−YZ) | 95% CI | SPA p | names where YZ better |
|---|---|---|---|---|
| GK-next (primary) | +21,382 (see below) | [+0.13, +57,558] | **0.024** | **97%** |
| r²-next (secondary) | **+0.0242** | [+0.0009, +0.0538] | **0.013** | 60% |

**The primary's magnitude, honestly decomposed:** the huge ΔQLIKE is NOT
typical-day improvement — it is dominated by episodes where the **production
EWMA collapses to ≈zero variance during quiet stretches** (runs of r²≈0 on
sparse/halted names drive the recursion toward 0) **and then a normal-vol day
arrives** → QLIKE's T/F term explodes. A post-hoc burn-in-trim sensitivity
(120 obs, clearly labeled post-hoc) did NOT remove it (ΔQLIKE +23,912,
ci_low +392, SPA p=0.017) — so it is not initialization; it is a structural
failure mode. **Range-based YZ cannot collapse this way** (daily ranges are
never all-zero). Two distinct findings, both real:
1. **Typical-day accuracy:** YZ modestly but significantly beats EWMA
   (the clean secondary: +0.024 QLIKE, p=0.013, 60% of names).
2. **Tail robustness:** the production EWMA's near-zero state is exactly the
   state where a vol-targeting engine dividing by σ would over-lever — the
   same failure family as the CLAUDE.md std<1e-12 tolerance non-negotiable,
   now measured in the wild at the estimator level.

## Consumer dispatch recommendations (no engine wiring done here)

1. **Engine B vol-target thickening: GO input delivered** — propose-first
   dispatch: YZ (or max(YZ, EWMA-floor)) as the vol-target σ estimator;
   the tail-robustness finding alone justifies the review (over-levering on
   quiet names is a live risk today). Director + user gate (Engine B).
2. **Regime/conditioning lane (C's, post-relaunch):** or_frac + last30_ret
   (cleared) as regime features; yz/gk vol + gap_freq into the Foundry
   (features exist now, loader ready). on_share/gap_abs_z/fhh_ret screened
   dead — do not consume.
3. **What minute data actually added beyond OHLC:** two cleared index
   features (or_frac, last30_ret) on a 5.5-yr window — modest; the OHLC-
   derived YZ/GK carry most of the value, exactly as the research ranked.

## Determinism + N

Screens seed-0, no wall-clock in artifact, determinism ×2 (md5 in outbox).
Diagnostics only: **N_trials += 0** (no backtest configs; consumers'
follow-ups will carry their own N).

## Files

- `scripts/build_ohlc_features_t150.py` (+ loader), `scripts/fetch_alpaca_minute_t150.py`,
  `scripts/screen_features_t150.py` (prereg in docstring, committed first)
- `data/research/{ohlc_features_t150,minute_features_t150}/` (gitignored)
- This audit. Builds on: T-135 (filter + decomposition), T-132 (MI machinery),
  T-149 (SPA), research Q5.

## NOT included

No engine wiring, no edge construction, no Engine-B edits (GO input only,
propose-first). No TASK_LEDGER write (T-114). Branch only; director merges.
