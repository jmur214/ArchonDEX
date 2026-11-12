---
name: drip-double-count-stooq-eras
description: Raw Stooq misses dividends by ERA (exact edges 2003-04-01 / 2011-02-21 / 2022-12-19) and PER NAME before 2003 (KO/XOM since 1970); T-082b drip slope double-counts 2011..seam; T-384 (a′) repair built on a copy, fails its strict test on Stooq's non-dividend defects
metadata:
  type: project
---

Measured 2026-11-11 (investigation, then T-384 per-ex-date probe over 449 payers / 34,575 ex-dates):

- Raw Stooq (`data/raw/stooq/daily/us/**`, ends 2026-05-22) is EXACTLY the T-082b merge input:
  cache_pre × exp(−b·(t−seam)) / raw is constant to 7e-16. Undo the drip with b alone (meta has no `a`).
- Universe-wide edges are single WEEKS: captured→missed 2003-03-30..04-07, missed→captured
  2011-02-20..21, captured→missed from 2022-12-19 (~90 % missed in 2023+, not 100 %).
- **Before 2003 it is PER NAME** (corrects the investigation's "≈0 % missed 2000→2003-Q1"): KO and XOM
  missed every dividend since 1970, BA 1980–99, BAX/CI 1982–2000; MO/AA/CAT/AXP from 2001-Q2; AEP/APD/
  COP captured 1970s→2003. 16 % of measured pre-2000 ex-dates missed; 22–32 % in 2001–02.
- Spin-offs INSIDE the missed era were usually CAPTURED by Stooq (MO/Kraft 2007, MO/PM 2008, CAH 2009,
  AYI 2007) — a pure era rule would add a 25–69 % "dividend"; label per ex-date.
- Stooq did NOT apply 2012–19 spin-offs (APD, CAG, HPE, HLT, HON, GE, BIIB, VNO, KMB, PPL, SPG, MUR, VLO,
  OXY) — the drip's +b partly masked these in the cache.
- AT&T: yfinance dividends read ≈1.3× Stooq's in EVERY year 2001–2012 (m ≈ 0.24 flat) — yf T is bad.

**T-384 state (2026-11-11):** candidate v3 at `Dev/_substrate_candidates/drip_fix_a_prime_2026_11_11/`
(branch `research/drip-fix-candidate-t384`, script `scripts/drip_fix_candidate_t384.py`, proposal
`docs/Sources/proposal_drip_fix_a_prime_2026-11-11.md`). FAILS its pre-declared test: (i) 1,771/1,830 vs
T-265 (cache 747), (ii) 2013 p95 0.350 > 0.30 (13 rows = inherited 2013 year-end Stooq block), (iii)
via (i). Every failure is a Stooq non-dividend defect or reference disagreement; the cache fails 55/59 too.

**Why:** cutover option (a) keeps the drip bars; (a′) restores per-ex-date missed dividends instead.
**How to apply:** before quoting any pre-seam equity-book number, ask whether the substrate was (a) or (a′);
a strict "every name-year" acceptance test cannot pass while Stooq's TR-era returns are kept as-is —
corporate actions and transient blocks need their own repair unit. See [[stooq-transient-blocks]].
