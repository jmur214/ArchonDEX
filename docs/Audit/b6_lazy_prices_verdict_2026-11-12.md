---
task_id: T-383 (B-6)
title: B-6 Lazy Prices — verdict (S&P arm; T-265 arm pending its census and freeze)
date: 2026-11-12
author: ml-architect subagent (director-dispatched)
outcome: "S&P ARM, gate window (c), CORRECTED run (AMENDMENTS 3+4): H1 NOT MET for either signal — similarity Δ log wealth −0.028 (ci_low −0.117 at the family level), Δtone −0.037 (ci_low −0.122); short-leg t_HAC −0.72 / −0.89 under R2's same-quarter pairing, but +2.23 under the ADJACENT 10-Q pairing — the S&P half of the refutation holds only under R2. The ORIGINAL run is kept as the NON-COMPLIANT record. Window (d) NOT EVALUABLE."
status: "S&P arm DONE (corrected run); N_trials stays +1. T-265: stream restarted on b6_parse/2, not frozen."
reproduce: "corrected: python -m scripts.lazy_prices.b6_harness_sp --all --out data/b6_local/harness_sp/a4_run1  # md5 039750163d6f4a74e17b5022b38e5da9 (x2); original: commit e5a923f, md5 2ec68e5a9248af3a5138eb940960aa6f (x2); (d): --census-only --spec d_similarity --signals data/b6_local/signals_sp.parquet  # exit 2, HALT md5 8f80dc57c89739fbae9ea976c86fe1e2"
---

# B-6 Lazy Prices — verdict

Pre-registration: `docs/Sources/prereg_b6_lazy_prices_2026-11-11.md` — the draft; AMENDMENT 1 (rulings
R1–R9, `fc28a7d`); AMENDMENT 2 (gate window (c) after the (d) census halted, `2a90763`; erratum `2e51918`);
AMENDMENT 3 (review F1–F5 — **"a defect-corrected re-run after results were seen; the configuration is
unchanged; N_trials stays +1 (the B-5 A2.2 precedent)"**, `a089d8f`); AMENDMENT 4 (a shared T-265 ticker
may fill by CIK only when the date-aware mapping is unique, `ad8eaa7`). Each amendment was committed alone.
Harness: `scripts/lazy_prices/b6_harness_sp.py` (standalone; never `BacktestController`).

## 1. Window (d) 2016-Q1 → 2025-Q4 — NOT EVALUABLE (census halt, no return)
13 of 40 rebalances below the 80%-of-members floor (worst 2016-03-31, 67.9%); bit-identical twice (census
md5 `c3effa85be82e4f5941051cd97dac980`, HALT list `8f80dc57c89739fbae9ea976c86fe1e2`). Cause: missing T-265
bars for acquired or failed members (B-2's survivorship hole), not text. Re-runs as its own pre-registered
trial once the hole closes (AMENDMENT 2).

## 2. Window (c), the ORIGINAL run — H1 NOT MET, but NON-COMPLIANT (kept as the record)
**Why non-compliant (review, AMENDMENT 3):**
- **F1 (`[NN-FAIL-CLOSED]`, §7.7).** Any price-file end was booked as an index exit; §7.7 requires a
  recorded deletion or a HALT. Of its 58 "exits", ≈ 27 were real, 8 renames and ≈ 23 TRUNCATED
  `data/processed` files of live members (AVGO, ANET, PWR, APH, MU, LRCX, CAT, DELL, MPC, TER, GLW, CMA);
  25 live members with a signal were unpriced at 2025-12-31 (NVDA, AVGO, PLTR, VST, APP, HOOD, KLAC …).
- **F2 (joins).** BRK-B / BF-B never matched `BRK.B_1d.csv` / `BF.B_1d.csv` (excluded all 23 quarters);
  META 2020-06 → 2022-06 and IHS Markit hit a different security under FB / INFO; 38 later-acquired
  members' files start 2020-07-27; MMC had no file.
- **F4 (parser b6_parse/1).** 52 of 52 end-of-document MD&A sections ran to the 10-Q signatures.

**Its numbers (results md5 `2ec68e5a9248af3a5138eb940960aa6f`, ×2; commit `e5a923f`):**
| signal | Δ log wealth (69 m) | ci_low 1.25th (gate) | ci_low 2.5th | short-leg mean | short-leg t_HAC |
|---|---|---|---|---|---|
| similarity | −0.027 | −0.116 | −0.107 | −0.77%/yr | −0.77 |
| Δtone | −0.041 | −0.128 | −0.115 | −1.27%/yr | −1.29 |

**Refutation framing, corrected (F3).** R2 stands (ruled pre-data, legitimate). **The S&P half of the
brief's refutation ("ci_low ≤ 0 AND short-leg t_HAC < 2") holds ONLY under R2's same-quarter-prior-year
10-Q pairing. Under the brief's literal "prior same-form filing" — the ADJACENT 10-Q — the S&P short leg
CLEARS t = 2 in this window: t_HAC +2.27** (changers underperform by 2.1%/yr; +2.32 with the review's own
fill). **The earlier "one of 8, needs |t| ≈ 2.7" discount is WITHDRAWN:** two of the 8 are the gate signals
and five (20 bps cost, D = −30%, Jaccard, TF-IDF, MD&A-only) are near-copies of the gate, so the effective
number of distinct tests is small and **the adjacent-pairing short-leg result is a LIVE finding, not
noise.** It is untradeable in a Roth (no shorts). It is named as the candidate for a future
pre-registered **negative-screen** test — exclude recent "changers" from a long book — and is not tested
here.

**Corrections to the original text (F5).** "Replaces ≈ 72% of its names" was wrong: 0.72 is the
two-sided Σ|Δw|; the review measured ≈ 32% NEW long names per rebalance. The long leg's 0.84 Sharpe (ci_low
0.21) is on RAW monthly returns, not excess of cash. `data/processed` drops spin-off value against T-265
(AIV −54 pp; FTV, WDC, LEN, J) — a source difference of the (c) window, noted, not corrected. The
equal-weight-vs-cap decomposition stands: long − SPY −1.99%/yr ≈ (long − EW universe −0.42%) + (EW
universe − SPY −1.57%).

## 3. Window (c), the CORRECTED run (AMENDMENTS 3 + 4) — H1 NOT MET for either signal

**What changed (configuration otherwise unchanged; N_trials stays +1).**
- **Parser b6_parse/2** (F4): the S&P panel re-parsed into `sp_sections_v2/` — 3,753 filings re-fetched
  and re-parsed (0 failures), 42,287 re-checked on stored text (2 Risk-Factors and 6 MD&A sections newly
  CONTAMINATED). Signals recomputed (`signals_sp_v2.parquet`): **575 filings' ranking signal changed; in
  the gate panel 161 ranked name-quarters change** (70 enter, 2 leave, the rest change value; 48 move leg).
  The review counted 7 because it counted only the end-of-document runaways: in the (c) window the
  section-level changes are 6 runaway MD&A sections, **97 MD&A sections v1 failed to locate that v2 now
  carves** (the 70 entering name-quarters) and **563 title-located MD&A bodies re-carved** by the
  terminator-key fix ("Item 3. Quantitative …" now terminates).
- **Prices** (F1/F2, AMENDMENT 4): per name-quarter resolution — `data/processed` if it covers the quarter,
  else T-265 bars by CIK (through a shared T-265 ticker only when the date-aware mapping is unique), else an
  exit only at a recorded index deletion, else HALT. Every name-quarter's source and cause:
  `data/b6_local/harness_sp/a4_run1/price_manifest_gate_similarity.csv`.

**Census (×2 identical, md5 `c08c92319a363d699ee5d7b7ffb445c7`): PASS** — ranked 438–489 per quarter,
87.8–97.8% of members, terciles ≥ 145, **0 unresolved**. The first corrected attempt halted on AVGO
(census md5 `2ede226fbca9bbd28859b299af9b447e`) until AMENDMENT 4's general rule resolved it by date.

| cause (name-quarters with a usable signal, 23 quarters) | n | names (e.g.) |
|---|---|---|
| ok — `data/processed` covers the quarter | 10,520 | |
| no_bar_at_t → T-265 fill (late-starting or other-security files) | 138 | FB→META (9 qtrs), NVDA (8), AVGO (4), PLTR, APP, ANET … (57 names) |
| no_file → T-265 fill | 105 | MMC, ABC, ANTM, BLL, CTL, ETFC, FI … (12 names) |
| truncated → T-265 fill | 18 | AVGO, ANET, APH, CAT, DELL, GLW, JBL, LRCX, MCK, MPC, MU, NRG, PH, PWR … |
| rename → T-265 fill | 5 | FBHS, FLT, GPS, RE, WLTW |
| real_exit — a recorded index deletion within −10 / +45 days | 37 | ABMD, ALXN, ANSS, ATVI, CTXS, CXO, DFS … |
| unresolved | **0** | |
| no price at t (not ranked) | 86 | |

AMENDMENT 4 resolves exactly 5 name-quarters, all Broadcom Inc (AVGO, 2024-12-31 → 2025-12-31). BRK-B
and BF-B are priced in all 23 quarters; META in all 23. Exits fall from the original 58 to **37, every one a
recorded deletion**.

**Smoke** (the first 12 months): clean — ranked 438–473, 7 exits (all recorded), no NaN.
**Determinism: two full runs, identical results md5 `039750163d6f4a74e17b5022b38e5da9`.**

### 3.1 The gate — long-leg 25% satellite, Δ log wealth vs 100% SPY TR (family level, Bonferroni)
| signal | Δ log wealth (69 m) | ci_low **1.25th (gate)** | ci_low 2.5th | ci_high 97.5th | realized MDE80 | H1 |
|---|---|---|---|---|---|---|
| **similarity** | **−0.0278** | **−0.117** | −0.107 | +0.052 | 0.114 | **NOT MET** |
| **Δtone** | **−0.0365** | **−0.122** | −0.110 | +0.032 | 0.104 | **NOT MET** |

The review's independent fill (272 fills) gave similarity −0.028 (ci_low −0.115) and Δtone −0.036 (ci_low
−0.122); the corrected run lands on both. **Label (§8):** both points below the central MDE80 (+0.101) →
**"not demonstrable at this length."**

### 3.2 The short-changers diagnostic (R2's same-quarter-prior-year pairing — the gate construction)
| signal | mean s (universe − changers), ann. | **t_HAC** | long − short, ann. | t_HAC |
|---|---|---|---|---|
| similarity | −0.76% | **−0.72** | −1.26% | −0.61 |
| Δtone | −0.88% | **−0.89** | −1.97% | −1.06 |

### 3.3 The brief's refutation sentence, evaluated literally — and its dependence on R2
- S&P: ci_low ≤ 0 for both signals — TRUE; short-leg t_HAC < 2 — TRUE **under R2's same-quarter pairing**.
- **Under the ADJACENT 10-Q pairing (the brief's literal "prior same-form filing"), the S&P short leg CLEARS
  t = 2: changers underperform by 1.96%/yr, t_HAC +2.23** (long − short +2.98%/yr, t +1.72; satellite
  −0.002, ci_low 2.5th −0.101). The review measured +2.32 with its own fill; the gap is the b6_parse/2
  signals and the AVGO fill.
- **So the S&P half of the refutation holds ONLY under R2's pairing.** The refutation as a whole still needs
  the T-265 arm. Multiplicity: two of the 8 diagnostics that ran are the gate signals and five are
  near-copies of the gate, so the adjacent-pairing short-leg result is a **live finding, not noise** —
  untradeable in a Roth, and the named candidate for a future pre-registered **negative-screen** test
  (exclude recent "changers" from a long book). Not tested here.

### 3.4 Decomposition, standalone statistics, diagnostics
- **Where the shortfall comes from** (arithmetic on the reported means): long − SPY −2.03%/yr ≈ (long −
  EW universe −0.50%) + (EW universe − SPY −1.53%): mostly the equal-weight vs cap-weight tilt of 2023–25
  (per-year Δ log wealth +0.005 / +0.008 / +0.015 in 2020–22, −0.028 / −0.019 / −0.013 in 2023–25).
- **Long leg (similarity):** Sharpe 0.84 (ci_low 0.20) and Sortino 1.46 (ci_low 0.30) on RAW monthly
  returns, not excess of cash; SPY TR 1.01 over the same months; below the 5.75-year MinBTL bar (≈ 0.90).
  **NEW long names per rebalance: 32% (similarity), 44% (Δtone)** (two-sided Σ|Δw| 0.71 / 0.93).
- **Diagnostics** (none can meet H1): 20 bps −0.030 (short-leg t −0.62); D = −30% −0.033 (−0.62); Jaccard
  −0.036 (−0.89); TF-IDF −0.019 (−0.68); MD&A-only −0.027 (−0.67); adjacent pairing −0.002 (**+2.23**).
  HALTED at their own censuses: Risk-Factors-only (2020-06-30 share 0.780), 10-Q combo (2020-06-30
  0.765), 10-K-only and 10-Q-only (a single form cannot fill a quarter).
- `data/processed` drops spin-off value against T-265 (AIV −54 pp; FTV, WDC, LEN, J) — noted, not
  corrected (F5).

### 3.5 Predictions (§12; written for the 10-year window) vs the corrected run
| prediction | outcome |
|---|---|
| similarity satellite point in [−0.05, +0.10]; ci_low ≤ 0; "not demonstrable" | **as predicted** (−0.028; −0.117) |
| S&P short-leg t_HAC +1.0 to +2.5 | **wrong under R2** (−0.72); **inside the range under the adjacent pairing** (+2.23) |
| tone weaker than similarity | **as predicted** (−0.037 vs −0.028) |

## 4. N_trials
**+1 (the S&P arm), unchanged by AMENDMENTS 3 and 4.** The (d) census halt and the corrected run's first
(AVGO) census halt consumed none.

## 5. T-265 arm — pending
The stream was stopped, its 3,880 b6_parse/1 filings archived unused, and restarted from scratch on
b6_parse/2 (2026-11-12 21:38 UTC). Its census and freeze follow its completion.

## 6. ERRATUM — review round 2 (2026-11-12; APPROVED; text only, no number changes)
The round-2 review reproduced the corrected results md5 `039750163d6f4a74e17b5022b38e5da9` and recomputed
with its own code (similarity −0.0275 / ci_low −0.116; Δtone −0.0351 / −0.122; adjacent-pairing short-leg
t +2.21); it planted a §7.7 violation (both layers halted), audited all 268 fills (each matches its CIK)
and found no wrong-company join and no signature line in any of the 46,040 rows. Four corrections to the
text above:

- **LOW-1 — renames are not deletions.** "37 exits, every one a recorded deletion" (§3) is FALSE for three
  renames that keep the same CIK as an index member: COG→CTRA, DISCA→WBD, CDAY→DAY. AMENDMENT 3's A3.1
  rule reads the end of a TICKER's membership interval as a deletion — the wrong proxy for a rename.
  Effect: DISCA, in the short leg, sat in BIL instead of taking WBD's ≈ −45% in 2022-Q2; this moves the
  short-leg t by ≈ 0.04. Recorded as a KNOWN LIMITATION; not re-run.
- **LOW-2 — not "everything else" resolves.** AMENDMENT 3's A3.2 says everything else resolves through
  the CIK-based fill; that is false where T-265 has no bars. These names are counted as "no price at t"
  (86 name-quarters) and the ranked share stays ≥ 87.8%. At 2020-06-30, 28 members with a usable signal
  have no price at t (worker's recount; the review counted 23 of the 38 later-acquired names, plus the
  named exclusions below): ABMD, ANSS, ATVI, CMA, COG, CTXS, DFS, DISH, DRE, FLIR, HBI, HES, HFC, INFO,
  IPG, JNPR, JWN, K, LB, MRO, MYL, NLSN, PXD, SIVB, TWTR, VIAC, WBA, WRK. Over the window: **IHS Markit**
  (INFO) excluded 2020-06-30 → 2022-03-31 (8 quarters); **Paramount** excluded for the whole window
  (VIAC 7 quarters, then PARA 14); **WestRock** (WRK) excluded 2020-06-30 → 2024-06-28 (17 quarters). The
  review also found the **PEAK→DOC fills differ from `data/processed` by roughly the dividend yield**: a
  `data/processed` dividend shortfall before 2024 — the drip HIGH's class — not a join error.
- **LOW-3 — timing.** AMENDMENT 4 (committed 16:07:59 local) says it came "before the corrected run computes
  any return"; the corrected SMOKE (12 months of leg returns) was written at 16:02:06, before it. This is
  immaterial: the post-AMENDMENT-4 smoke (16:08:13) is byte-identical (md5
  `d3648722d00c8a8952a9f45dbb03962f` both), AMENDMENT 4 changes only AVGO from 2024-12-31 on, and both full
  runs (16:08:57, 16:09:42) follow the commit.
- **LOW-4 — framing.** "A live finding, not noise" (§2, §3.3) overclaims for t_HAC = 2.23 over 69 months.
  Restated: p ≈ 0.03 unadjusted (two-sided) and ≈ 0.08 across roughly 3 effective tests — the
  adjacent-pairing short-leg result **cannot be dismissed as noise**; it is not established either. In
  §3.5's predictions table, the "inside the range under the adjacent pairing" credit is **post hoc**: the
  frozen prediction was made for the gate construction (R2), where it was wrong.
