---
name: project-b5-financing-inputs-census-2026-11-11
description: B-5 (T-382) input census — T-306 cash is quantized 1bp/day (±1pp/yr errors), DTB3/SOFR not on disk, SG CTA registration-gated, AQR TSMOM over-captures ~5%/yr vs live, T-311 calendar guard vacuous
metadata:
  type: project
---

B-5 (T-382, levered diversified vs 1× SPY under Roth financing). The prereg was committed at
535a3fc on `research/levered-diversified-b5` on 2026-11-11. Phase 1 STOPPED there, awaiting director
rulings R-1..R-14.

Census facts that outlive the task:
- **T-306 `cash_daily.csv` (FF RF daily) is quantized to 1 bp/day**, only 7 distinct values (≈2.52 %/yr
  steps). Against DGS3MO it is wrong by up to ±1.03 pp in a single year (2003, 2017, 2025). Over
  2000–2025 the signed errors net to ≈ 0, which is why long-window T-311-family verdicts are probably
  fine, but year- and regime-level reads are not.
- **Any financing or leverage study must NOT use it as the borrowing rate.** T-315's SSO synthetic did
  (`cash + 60 bp`).
- Pre-1993 `equity_tr` carries the same RF rounding.
- **DTB3 and SOFR are not on disk.** `data/macro` has only DGS3MO and DFF from 2000. FRED is keyless
  via fredgraph.csv (the T-306 builder pattern).
- **The SG CTA index is registration-gated**, and the ReSolve SG Trend replication is a form download.
  The only free deep trend series is AQR TSMOM (on disk, 1985-01 → 2026-05). It is gross and
  frictionless, and T-296 measured it over-capturing live RSST by ≈ +5.3 %/yr. So a trend-overlay arm
  built on it "passes" by construction. Treat it as refute-only.
- `scripts/deep_reverify_sleeve_t311.py::load_substrate` calls
  `assert_no_calendar_holes(frame.index, frame.index)`, which is vacuous. The real risk is ffill
  masking outages.
- No live levered-ETF prices are in `data/processed/`. UPRO, TMF and RSST are on disk nowhere. Old
  `data/research/t282|t285|t294` copies have auto_adjust or unknown provenance.

**FRED download blocked (2026-11-11, ~19:00 CT):**
- `fredgraph.csv` and `fredgraph.xlsx` timed out or reset the connection for this Mac. It was
  retried for about 20 minutes over IPv4 and IPv6 with up to 540 s timeouts. FRED's HTML pages,
  google and yfinance all responded.
- The keyless FRED path the T-306 builder used is therefore not reliable.
- RESOLVED (director ruling, amendment 2): the 3-month bill came from the Fed H.15 DDP and SOFR from
  the NY Fed Markets API (`/api/rates/secured/sofr/search.csv`). Both worked.
  - The DDP retired "Build your package" the week of 2026-11-09. The only full-history bill source
    there is now the full-release SDMX/ZIP (`Output.aspx?rel=H15&filetype=zip`, series
    `RIFSGFSM03_N.B`).
  - TRAP: SDMX no-data days are `OBS_STATUS="ND" OBS_VALUE="-9999"`. Filter on the STATUS. Keeping
    the value made 801 holidays read as −9,999 %/yr (≈ −380 %/yr after the money-market conversion) and
    manufactured fake LETF tracking failures. With the defect, H1 would have read MET (+2.98 %/yr,
    ci_low +0.75). The correction ran against H1, and the director ratified it as a data-defect fix.
  - A guard that joins against FRED (which has no holiday rows) cannot see it. A rate range check
    can.
- Fetch design: stage per attempt and rename into `inputs/` only after ALL inputs succeed, so a
  failed attempt never needs a delete.

**Why:** a regime or financing analysis lives or dies on the short rate. A 1 bp/day quantized rate is a
silent ±1 pp/yr error in exactly the regimes (ZIRP exits, 2018–19, 2025) where leverage verdicts flip.

**How to apply:**
- Use DTB3/SOFR (money-market converted) for any leverage cost.
- Flag FF-RF-based year-level results.
- Never let an AQR-factor trend arm confirm anything.

Related: [[project-macro-signal-lead-coincident-classification-2026-05-06]].
