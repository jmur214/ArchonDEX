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

## 2. RESULTS — CORRECTED (T-173, 2026-06-16)

> This section replaces the original (superseded) §2 per the DIRECTOR
> CORRECTION banner above. The original cells were ~2× too shallow.
> **Root cause (combination-step bug):** AQR's month-end dates and the
> base `resample('ME')` month-end dates do not match day-for-day in ~7
> of the 24 GFC months; the original code combined on the index
> INTERSECTION and `dropna()`'d the non-aligning rows — silently
> dropping the deep-trough months, so the combined MDD never reached
> the real trough (base MDD on the surviving 17-month subset is only
> −15.7% vs −30.15% on the full 24 months). **Fix:** align both monthly
> series on calendar-month PERIODS (`.to_period('M')`) and combine on
> the full window with NO `dropna`; assert mf-NaN-count == 0 per window.
> The "+X%" reduction labels were separately ~half the true cut and are
> corrected here too. Reproducible: `scripts/mf_sleeve_deep_crisis_t171.py`.

### 2.0 OPTIMISTIC-CEILING CAVEAT (read before the numbers)

**Every cell below is an upper bound on what a real bought product
delivers.** The scalar haircut `k` de-levers the AQR factor to a net
return level but **preserves the factor's crisis SHAPE and convexity
perfectly** — it assumes the investable product tracks trend's timing
exactly and only scales the magnitude. Real products do not: DBMF
replicates the trend factor at ~82% correlation with 5.81% tracking
error and had documented 2020/2022 breakdowns; KMLM carries zero
equity exposure and so distorts the crisis shape in fast reversals.
**A real product's drawdown cut is therefore SHALLOWER and LATER than
these figures** — the convexity that makes trend cut a crisis is
exactly what replication error degrades in the fast-reversal moments
that matter. Treat the MDD reductions below as the best case the
asset class could provide, not the deployable number.

### 2.1 Haircut calibration (unchanged — was correct)

AQR TSMOM gross: GFC (2007-07→2009-06) **+13.9%**, 2008-calendar
**+24.5%**. Net anchors (RYMFX, fees-embedded): GFC +9.9%, 2008-cal +6.8%.
- **Primary `k = 9.9/13.9 = 0.711`** (GFC-window match).
- **Conservative `k = 6.8/24.5 = 0.278`** (2008-calendar match — RYMFX
  captured only 28% of AQR's gross spike year).

### 2.2 Deep-crisis A/B — CORRECTED (month-end MDD; conservative/approximate)

**dotcom 2000-01→2002-12 (35 mo), base-alone MDD −18.97%:**

| Haircut | base+10% | base+20% | base+30% |
|---|---|---|---|
| net k=.711 | −15.0% (cut 21%) | **−11.8% (cut 38%)** | −9.6% (cut 49%) |
| net-consv k=.278 | −16.0% (cut 16%) | **−13.5% (cut 29%)** | −11.1% (cut 42%) |

**GFC 2007-07→2009-06 (24 mo), base-alone MDD −30.15%:**

| Haircut | base+10% | base+20% | base+30% |
|---|---|---|---|
| net k=.711 | −26.1% (cut 13%) | **−21.9% (cut 27%)** | −17.5% (cut 42%) |
| net-consv k=.278 | −26.9% (cut 11%) | **−23.6% (cut 22%)** | −20.2% (cut 33%) |

Base full-cycle daily MDD = −32.61% (sanity-anchor, matches T-128r).
GFC point-Sharpe does NOT flip positive under the corrected combine
(the earlier "+0.140" was part of the same truncation artifact); a
real +20% blend at k=.711 leaves the GFC Sharpe still negative
(≈−0.19). The Sharpe leg is in any case uninformative on 24-35 monthly
obs (CI half-widths ~±1.8) — do not claim a risk-adjusted-return lift.

### 2.3 Verdict — CORRECTED: directional deep-crisis MDD-defense is REAL but smaller, haircut-fragile at the GFC, and a ceiling

**Scored against the pre-registered rule (≥25% MDD cut, both haircuts):**

| Cell | dotcom | GFC |
|---|---|---|
| @20% primary (k=.711) | PASS (38%) | PASS (27%) |
| @20% conservative (k=.278) | PASS (29%) | **FAIL (22%)** |
| @30% primary | PASS (49%) | PASS (42%) |
| @30% conservative | PASS (42%) | PASS (33%) |
| Sharpe ci_low not down | INDETERMINATE | INDETERMINATE |

**The deep-crisis MDD-defense is real and now backtest-grounded (not
literature-only) — but materially weaker than T-171 originally
published.** Net-of-haircut, a 20% sleeve cuts the dotcom −18.97% to
−11.8%/−13.5% and the GFC −30.15% to −21.9%/−23.6% — meaningful, but
the GFC trough still sits near −22% even with the sleeve (it does not
collapse to ~−11% as originally claimed). **The ≥25% bar is
haircut-FRAGILE at the GFC@20%** (clears the primary 27%, fails the
conservative 22%); only at **30%** does the GFC clear under both
haircuts (42%/33%). On the Sharpe dimension nothing is established
(indeterminate on monthly data; the earlier GFC-Sharpe "flip" was an
artifact). **Composite: MF is a measured PARTIAL deep-crisis
drawdown-mitigant — it shaves roughly a quarter to a third off the
GFC/dotcom trough at 20-30%, net-of-haircut, as an optimistic ceiling
— not the near-halving the original (buggy) T-171 implied.**

### 2.4 Allocation re-examination (20 vs 30%) — corrected

The corrected GFC fragility sharpens the trade-off the original missed:

- **20%:** dotcom-robust (clears ≥25% both haircuts), recent-window-optimal
  (T-170: Sharpe 1.452, +25.1% recent MDD cut), but the **GFC defense is
  haircut-fragile** (27% primary / 22% conservative — a partial cut to
  ~−22%, not a robust one).
- **30%:** robust deep-crisis cut under both haircuts (GFC 42%/33%,
  dotcom 49%/42%), but T-170 showed 30% **over-dilutes the recent
  window** (Sharpe 1.341 vs 1.452, recent MDD cut +16% vs +25% — paying
  more to a 0.43-Sharpe product in the 95% of time that isn't a deep
  crisis).

**Recommendation (the rule is unchanged from T-170/T-171; only the
corrected numbers move which cells clear it — no re-pre-registration,
this is a correction not a goalpost move):** the honest call is a
**20-25% range, defaulting to 20%**, with the explicit understanding
that **at 20% the GFC defense is partial and haircut-fragile, and the
optimistic-ceiling caveat means the deployable cut is shallower still.**
If the user weights deep-crisis robustness over recent-window return,
30% is the lever that makes the GFC cut survive the conservative
haircut — but given the ceiling caveat (a real product won't deliver
even the 30% figures cleanly in a fast reversal), chasing the exact
≥25% threshold by sizing up to 30% is partly illusory precision. The
defensible posture: **20% as a partial crisis mitigant with eyes open,
not a crisis solution; size toward 30% only if deep-crisis protection
is the explicit priority and the recent-window Sharpe cost is accepted.**

### 2.5 Residual caveats (honest)

- **Optimistic ceiling (§2.0) is the load-bearing caveat** — real
  DBMF/KMLM (replication error, 2020/2022 breakdowns, KMLM zero-equity)
  delivers a shallower, later cut than the scalar-haircut figures.
- **AQR TSMOM (pure diversified TSMOM) ≠ DBMF/KMLM** — AQR gives the
  trend crisis-SHAPE on the deep windows; the products were validated
  on post-2019 records (T-170). Complementary, not interchangeable.
- **Monthly MDD understates** daily peak-to-trough (base GFC monthly
  −30.15% vs daily −32.61%); relative reduction is the robust quantity.
- **Survivorship/backfill** in the academic factor → directional
  evidence, not achievable returns; the conservative haircut is the
  safer read.
- **Thin N** (2 deep crises + COVID/2022) → do not over-precision the
  allocation.
- **The original T-171 §2 was wrong by ~2×** (combination bug, §2 head);
  this corrected record + the banner are the authoritative version.
