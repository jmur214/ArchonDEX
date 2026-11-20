---
name: reference-cz-signal-list
description: Open Source Asset Pricing (Chen–Zimmermann) SignalDoc.csv — 331 CRSP/Compustat-built signals with free portfolio returns; checked 2026-11-20 for an announcement-premium predictor (none)
metadata:
  type: reference
---

**The list:** `https://raw.githubusercontent.com/OpenSourceAP/CrossSection/master/SignalDoc.csv` (public
GitHub; fetched with the generic UA on 2026-11-20, 183 kB, 331 rows).
- It has the original paper, the sample years and the portfolio construction for each signal.
- Its portfolio returns are built from CRSP, so they are survivorship-free, and they are free.
- That makes it the cheapest route to a free survivorship-free series for any cross-sectional anomaly
  the project wants to check for persistence.

**What is in it (earnings and calendar):**
- AnnouncementReturn (Chan–Jegadeesh–Lakonishok 1996, PEAD-type).
- EarningsSurprise, EarningsStreak, EarnSupBig.
- DivSeason.
- The Heston–Sadka MomSeason family.

**What is NOT in it:** a Frazzini–Lamont or Savor–Wilson earnings-announcement premium. MomSeasonShort is
related but is not that premium.

**How to apply:**
- Before calling an anomaly "blocked on survivorship-free data", grep this list.
- Download its portfolio returns only under a prereg, because they are outcome data.
- Used by [[project-t415-e2-blocked-survivorship-2026-11-20]].
