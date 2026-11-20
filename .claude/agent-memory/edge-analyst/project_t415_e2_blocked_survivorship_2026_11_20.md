---
name: project-t415-e2-blocked-survivorship-2026-11-20
description: T-415 E-2 (S&P earnings-week basket) Phase-1 census 2026-11-20 — BLOCKED on paid data; free coverage 49% (2004) to 99% (2025), the hole is departed names; no clean TR before 2016; free windows pass ≈3.7% / 1.6%
metadata:
  type: project
---

**Verdict (2026-11-20, census only, 0 trials):** E-2 cannot be tested on free data over its pre-registered
window (2004-08 → 2026). Free windows can be tested but are not worth a trial.

- **Script:** `scripts/t415_e2_coverage_census.py`. Counts only, deterministic ×2, 7 positive controls.
- **Coverage of PIT member-days (any free store, CIK lineage):**
  - 48.8% in 2004, 64.7% over 2004–15, 90.9% over 2016–20, 98.8% over 2021–26.
  - Departed members 16.9% (2004) → 41% (2015). Continuing members 94–99%.
  - 96.8% of the missing days belong to members that later left the index.
  - By exit type: M&A targets 18.7%, failures 22%, demotions 68.8%.
- **Second blocker:** under the B-6 ruling R1, `data/processed` may not be read before 2020-04-09
  (dividend-era HIGH). T-265 Alpaca bars start 2016. So the clean coverage before 2016 is 0%.
- **Date source:** the T-137 8-K panel is good for names it holds.
  - Item 2.02 from 2004-08-25; item 12 covers 2003-04 → 2004-08.
  - 94% of ticker-years have exactly 4 releases.
  - The +364-day prediction lands within 5 trading days 89.5% of the time.
  - 92.9% agree with the vendor calendar.
  - **But it holds dates for only 42.8% of departed member-days**, because its CIK map comes from live tickers.
  - Form 345 symbols give CIKs for 321 of the 378 missing intervals, so the gap can be filled free via SEC.
- **Power** (T-410 priors; E[t] = IR·√T; bar t ≥ 2.96):

  | Window | P(pass) | MDE IR |
  |---|---|---|
  | full, with paid data | ≈ 9.2% | 0.82 |
  | 2016+ (310 qualifying weeks) | ≈ 3.7% | 1.18 |
  | 2021+ (167 qualifying weeks) | ≈ 1.6% | 1.65 |

- **What the $39 buys:** one month of Sharadar gives the full window with clean total returns. FirstRate
  reaches only 53% of the wanted-list gap in this window.
- **Checked dead end:** there is no free CRSP-built announcement-premium series. The Chen–Zimmermann
  list of 331 signals has none; see [[reference-cz-signal-list]].

**Why:** the owner declined paid data on 2026-11-20. The census showed the free substrate's hole is
outcome-correlated, and the plausible bias is the size of the effect (see
[[feedback-variance-proportional-survivorship]]).

**How to apply:**
- Do not re-propose E-2 on free data.
- If the owner ever buys the one-month Sharadar campaign, bundle E-2 with M-1, the B-6 pre-2016
  extension and the B-1 re-run.
- Make the prereg's primary statistic announcers minus non-announcers, not raw EW minus SPY (that
  carries the EW premium).
- See also [[t265-panel-not-survivorship-complete]] and [[project-t410-ideas-census-2026-11-20]].
