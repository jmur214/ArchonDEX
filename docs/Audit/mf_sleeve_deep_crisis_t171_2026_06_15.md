---
task_id: T-2026-06-15-171
title: Deep-crisis backtest of the bought-MF sleeve — close the T-170 literature gap (dotcom + GFC), net-of-haircut
date: 2026-06-15
scope: allocation evaluation on FREE proxies (AQR TSMOM monthly factor, pinned snapshot; RYMFX + T-108 sleeve as net GFC anchors); NO trend model built; no live-money path
data: AQR TSMOM monthly snapshot data/external/aqr/aqr_tsmom_monthly_snapshot_20260615.xlsx (sha256 e75450e2…, "AQR Capital Management, LLC", terms-of-use credited); base 26yr curve (T-128r arm0 158fe678); RYMFX net via yfinance; T-108 spot-trend JSON
status: PRE-REGISTRATION committed BEFORE running (honest-N); results appended after
outcome: "[PENDING — committed before any portfolio number is unblinded.]"
---

# T-171 — Deep-Crisis Backtest of the Bought-MF Sleeve

## 1. PRE-REGISTRATION (committed before any result)

### 1.1 Why

T-170 recommended a 20% DBMF separate-account sleeve but its HEADLINE
claim — that managed futures cuts the GFC −32.6% / dotcom −21.3%
drawdown nothing in-house can touch — rested on a literature citation
(SG Trend +20.9% in 2008), because no MF ETF predates 2019. A free,
file-verified source (AQR TSMOM monthly factor, 1985→2025, both crises
present) now lets us convert that citation into a measured,
net-of-haircut verdict for $0.

### 1.2 Data (pinned)

- **AQR TSMOM** (all-asset diversified, monthly excess returns),
  `data/external/aqr/aqr_tsmom_monthly_snapshot_20260615.xlsx` (sha256
  `e75450e2…`, 'TSMOM Factors' sheet, 481 rows 1985-01→2025-01). AQR
  reconstructs history on each update → this snapshot is pinned for
  reproducibility. Credit: AQR Capital Management, LLC (terms-of-use).
- **Net GFC anchors** (for the haircut): RYMFX (Rydex Managed Futures,
  net of fees, via yfinance) and the on-disk T-108 spot-trend sleeve
  (`docs/Measurements/2026-06/t108_phase0_diversified_trend.json`).
- **Base book**: T-128r 26yr arm0 daily curve, resampled to month-end.

### 1.3 The gross→net haircut (the whole ballgame — fixed before running)

AQR TSMOM is a GROSS, long/short, vol-scaled ACADEMIC factor (no fees,
no slippage, theoretical leverage) → it overstates any investable MF
product. Our kill gate is CI-aware NET (ci_low < 0.4). Calibration:
scale AQR monthly returns by a constant `k` chosen so AQR's GFC-window
(2007-07→2009-06) return matches RYMFX's net GFC return, then carry the
SAME `k` into the dotcom window (where no net source exists).

- **Primary haircut** `k = RYMFX_GFC / AQR_GFC` (GFC-window match, per dispatch).
- **Conservative sensitivity** `k = RYMFX_2008cal / AQR_2008cal` (the
  harsher peak-crisis-year match — RYMFX captured far less of AQR's
  2008 gross spike). The verdict must be reported under BOTH; if it
  only survives the lenient haircut, say so.

Both gross AND haircut-net are reported. **The gross factor is NEVER
quoted as deploy-ready.**

### 1.4 The A/B (fixed)

Month-end portfolio A/B on the two deep-crisis windows:
- **dotcom** 2000-01→2002-12; **GFC** 2007-07→2009-06 (incl. recovery).
- Arms: base-alone vs base + x% trend-sleeve (haircut-net AQR), x ∈ {10, 20, 30%}.
- Combination: `r = (1−x)·r_base + x·r_mf_net`, month-end, separate-account
  (no shared constraint — the valid linear combination, per T-170).

### 1.5 The read + decision rule (fixed; same as T-170/T-118b)

Per window per allocation, NET-of-haircut: combined MDD (monthly —
reported as CONSERVATIVE/approximate, monthly understates intra-month
peak-to-trough), Sharpe + block-bootstrap ci_low (block=7, n=1000,
seed=42 — on monthly series, so CI is wide; report honestly).

**The sleeve's deep-crisis claim is BACKTEST-SUPPORTED iff, net-of-haircut
on the deep windows:** (1) combined MDD reduction ≥ 25% vs base, AND
(2) combined Sharpe ci_low not down. Plus: does 20% still hold vs 10/30
on the deep windows (do NOT overfit allocation to one episode), and
does the claim survive the CONSERVATIVE haircut.

### 1.6 Caveats pre-stated (honest before results)

- AQR TSMOM (pure diversified TSMOM) ≠ KMLM/DBMF (manager idiosyncrasy
  + multi-strat) — AQR characterizes trend SHAPE/crisis-convexity; the
  specific bought product was validated on its post-2019 record (T-170).
- Survivorship/backfill bias in the academic factor → directional
  crisis-diversification evidence, NOT achievable returns.
- Monthly MDD understates daily peak-to-trough.
- Thin N (2 deep crises + COVID/2022) → no allocation overfit to one episode.

### 1.7 N-trials

**N_trials += 1** (deep-crisis allocation test on the free proxy). The
haircut sensitivity arm is the same hypothesis, not a new trial.

---

## 2. RESULTS

[APPENDED AFTER THE PRE-REGISTRATION COMMIT — see git history.]
