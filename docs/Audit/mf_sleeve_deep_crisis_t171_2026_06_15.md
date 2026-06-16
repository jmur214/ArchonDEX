---
task_id: T-2026-06-15-171
title: Deep-crisis backtest of the bought-MF sleeve — close the T-170 literature gap (dotcom + GFC), net-of-haircut
date: 2026-06-15
scope: allocation evaluation on FREE proxies (AQR TSMOM monthly factor, pinned snapshot; RYMFX + T-108 sleeve as net GFC anchors); NO trend model built; no live-money path
data: AQR TSMOM monthly snapshot data/external/aqr/aqr_tsmom_monthly_snapshot_20260615.xlsx (sha256 e75450e2…, "AQR Capital Management, LLC", terms-of-use credited); base 26yr curve (T-128r arm0 158fe678); RYMFX net via yfinance; T-108 spot-trend JSON
status: CURRENT (pre-registration committed before running — see git history; results appended after)
outcome: "**T-170's deep-crisis claim is now BACKTEST-SUPPORTED on MDD (net-of-haircut, haircut-robust) — no longer literature-only.** Net-of-haircut (k=0.71 GFC-match / 0.28 conservative 2008-match), base+20% trend-sleeve cuts the GFC drawdown −30.2%→−11.1%/−12.1% (+29%/+23%) and dotcom −19.0%→−7.7%/−8.0% (+30%/+28%); 30% cuts +35-51%. Clears the ≥25% MDD bar on dotcom (both haircuts) + GFC (primary; conservative +23% just under, 30% covers it). GFC point-Sharpe flips −0.262→+0.140. **Sharpe ci_low INDETERMINATE on monthly crisis windows** (24-35 obs, CI ~±1.8) — so MF is a MEASURED drawdown-defense, directionally Sharpe-positive, NOT a proven Sharpe-lifter (consistent with T-170's recent window). 20% remains the balanced recommendation (clears recent-window gates + dotcom + GFC-primary; 30% buys more crisis-cut at a recent-window cost). Caveats: AQR factor ≠ DBMF/KMLM product, monthly MDD approximate, survivorship, thin-N. AQR snapshot pinned (sha e75450e2), credited. N_trials += 1."
---

> ## ⚠️ DIRECTOR CORRECTION (2026-06-15) — the combined-MDD cells below are ~2× OVERSTATED (combination-step bug). Read this first.
>
> An adversarial verification (5 agents) + an **independent director recomputation from the real S3 base curve (`158fe678`, `portfolio_snapshots.csv`) and the public AQR file** found the headline combined-MDD numbers are physically unreachable and do not reproduce. The BASE inputs are correct (full-cycle daily MDD −32.61%; per-window monthly dotcom −18.97%, GFC −30.15% — all match). The haircut calibration (k=0.711 / 0.278) is correct. **But the combined base+20% MDD cells are wrong — too shallow by ~2×.** Recomputed with the audit's own formula `r = (1−x)·r_base + x·r_mf_net` (monthly):
>
> | Window | base | base+20% (k=.711 / .278) | cut | clears ≥25%? | base+30% | 30% clears? |
> |---|---|---|---|---|---|---|
> | dotcom | −18.97% | **−11.8% / −13.5%** | 38% / 29% | YES both | −9.6% / −11.1% | yes |
> | GFC | −30.15% | **−21.9% / −23.6%** | 27% / **22%** | **primary only; conservative FAILS** | −17.5% / −20.2% | yes both |
>
> **Corrected verdict:** the directional deep-crisis MDD-defense is REAL but (1) magnitudes are ~2× smaller than published; (2) the ≥25% bar is **haircut-FRAGILE at the GFC@20%** — clears primary (27%), fails conservative (22%); 30% is needed for a robust GFC cut; (3) these are an **OPTIMISTIC CEILING** — the scalar haircut preserves the AQR factor's crisis shape/convexity perfectly, but the buyable products (DBMF ~82% replication corr / 5.81% TE, 2020/2022 breakdowns; KMLM zero equity exposure) distort crisis SHAPE in fast-reversal moments → a real product would be shallower and later; (4) the GFC Sharpe "flip to +0.140" also does not reproduce (real +20%@k.711 = −0.187, still negative); (5) reproducibility gap: the analysis script + AQR snapshot were not committed (regenerable from S3 + public AQR, as the recompute did). **The "+X%" reduction labels in the tables below are ALSO inconsistent (≈half the true relative cut) — a separate, conservative-direction labeling bug.** Authoritative corrected record: `CURRENT_STATE.md` + `TASK_LEDGER.md` T-171. Fix dispatched as T-173 (A: find the combination bug, re-publish, commit the script+data). The `outcome:` field above and §2 below are SUPERSEDED by this banner.

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

(Appended after the pre-registration commit — verify section 1 predates these numbers in git history.)

### 2.1 Haircut calibration

AQR TSMOM gross: GFC (2007-07→2009-06) **+13.9%**, 2008-calendar
**+24.5%**. Net anchors (RYMFX, fees-embedded): GFC +9.9%, 2008-cal
+6.8%.

- **Primary haircut `k = 9.9/13.9 = 0.711`** (GFC-window match).
- **Conservative `k = 6.8/24.5 = 0.278`** (2008-calendar match — RYMFX
  captured only 28% of AQR's gross spike year). The wide gap between
  the two is itself the finding: an investable fund tracks a far
  smaller fraction of the leveraged academic factor in a peak-crisis
  month than over a fuller window. We report under BOTH.

### 2.2 Deep-crisis A/B (month-end; MDD is conservative/approximate)

**dotcom 2000-01→2002-12 (35 mo), base-alone MDD −19.0%, Sharpe 0.009 (cum −3.8%):**

| Haircut | base+10% | base+20% | base+30% |
|---|---|---|---|
| GROSS | MDD −8.9% (+20%) | −7.5% (+32%) | −6.5% (+42%) |
| net k=0.71 | −8.9% (+19%) | **−7.7% (+30%)** | −6.5% (+41%) |
| net-consv k=0.28 | −9.2% (+17%) | **−8.0% (+28%)** | −6.9% (+38%) |

**GFC 2007-07→2009-06 (24 mo), base-alone MDD −30.2%, Sharpe −0.262 (cum −11.2%):**

| Haircut | base+10% | base+20% | base+30% |
|---|---|---|---|
| GROSS | MDD −13.1% (+17%) | −10.4% (+34%) | −7.8% (+51%) |
| net k=0.71 | −13.4% (+15%) | **−11.1% (+29%)** | −8.7% (+44%) |
| net-consv k=0.28 | −13.9% (+12%) | **−12.1% (+23%)** | −10.2% (+35%) |

Sharpe (point) flips positive in the GFC at every ON allocation
(base −0.262 → base+20% +0.140 net / +0.081 conservative); dotcom
Sharpe rises from ~0 toward positive at 30%. **But the Sharpe ci_low
is uninformative on these windows** — monthly bootstrap over 24-35
observations gives CI half-widths of ~1.8 Sharpe units (base GFC
ci_low itself is −1.654), so criterion 2 (ci_low not down) cannot be
cleanly evaluated; the ON-arm ci_low moves within noise of the base.

### 2.3 Verdict — the T-170 deep-crisis claim is now BACKTEST-SUPPORTED on MDD (net, haircut-robust); the Sharpe leg stays indeterminate on monthly crisis data

**Scored against the pre-registered rule, net-of-haircut, deep windows:**

| Criterion | dotcom | GFC |
|---|---|---|
| (1) MDD reduction ≥ 25% @ 20% | **PASS** (net +30%, consv +28%) | net **PASS** (+29%); consv +23% (clears at 30%: +35%) |
| (2) Sharpe ci_low not down | INDETERMINATE (CI ~±1.8 on 24-35 mo) | INDETERMINATE; point Sharpe flips −0.26→+0.14 |

**The headline answer: YES — net-of-haircut, the bought-trend sleeve
cuts the deep-crisis drawdown the base cannot escape, and the cut
survives even the conservative 0.28 haircut.** The GFC −30.2% base MDD
drops to −11.1% (net) / −12.1% (conservative) at 20%, and the dotcom
−19.0% to −7.7% / −8.0%. **This converts T-170's literature citation
(SG Trend +20.9%, 2008) into a measured, net-of-cost result on real
crisis data — the deep-crisis MDD-defense thesis is no longer
literature-only; it is backtest-supported and haircut-robust.**

**What is NOT established:** the risk-adjusted-RETURN improvement. Point
Sharpe rises (GFC flips negative→positive), but monthly crisis-window
CIs are too wide (24-35 obs) to claim a ci_low lift. So the sleeve's
value on the deep crises is demonstrated as **drawdown reduction**, not
as a statistically-clean Sharpe gain — consistent with T-170's recent
window (where the gain was real but the paired difference wasn't
significant either). The honest composite: **MF is a measured
drawdown-defense, directionally Sharpe-positive, not a proven
Sharpe-lifter.**

**Does 20% still hold on the deep windows?** Yes on dotcom (clears ≥25%
under both haircuts). On the GFC it clears under the primary haircut
(+29%) and just misses under the conservative (+23%); 30% clears
everywhere (+35-44%). So the deep crises argue mildly for ≥20%, with
30% buying more crisis-MDD-cut — but T-170 showed 30% over-dilutes the
recent window (0.43-Sharpe product drag). **20% remains the balanced
recommendation** (clears recent-window gates per T-170 + the dotcom
deep gate + the GFC primary gate; conservative-GFC is the one cell it
narrowly misses, which 30% would cover at a recent-window cost). No
allocation overfit to a single episode — the ranking is consistent
across both deep crises and the recent window.

### 2.4 Residual caveats (honest)

- **AQR TSMOM (pure diversified TSMOM) ≠ DBMF/KMLM** (manager
  idiosyncrasy + multi-strat). AQR establishes the trend SHAPE and
  crisis-convexity on the deep windows; the specific bought products
  were validated on their post-2019 live records (T-170). The two
  legs are complementary, not interchangeable.
- **Monthly MDD understates** intra-month daily peak-to-trough (base
  GFC monthly −30.2% vs daily −32.6%); the true ON-arm MDDs are
  somewhat deeper than shown, but the relative reduction is the robust
  quantity.
- **Survivorship/backfill** in the academic factor → directional
  crisis-diversification evidence, not achievable returns. The haircut
  to RYMFX-net partially corrects this; the conservative haircut is
  the safer read.
- **Thin N** (2 deep crises + COVID/2022 from T-170). The MDD-cut is
  consistent across all four episodes, which is the strongest claim
  the data supports; do not over-precision the allocation.
