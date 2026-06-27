# Bought MF-ETF vs Our Trend Overlay as the Barbell's Convex Satellite — PRE-REGISTRATION (T-253, 2026-06-27)

**Written BEFORE measurement** (`[NN-MBL]`). FREE probe. Question: as the
barbell's (C/T-251) **convex satellite** (10-20% paired with a safe core),
does a BOUGHT managed-futures ETF (DBMF / KMLM) beat OUR homegrown trend
overlay (T-204/T-236)? Endorsed by the fresh-eyes brief
(`docs/Sources/fresh_eyes_strategic_brief_2026_06_26.md`) as "a far better
convex satellite than DIY LEAPS." Measure, recommend — NO build, NO canon
change.

## The structural distinction being tested (state it up front)
- **Our trend overlay = long/FLAT** (SPY/AGG/GLD, 5mo momentum). In a crash it
  steps to CASH → it AVOIDS the loss but earns ~0; it has **no short leg → no
  right-tail crisis GAIN**. It is a DEFENSIVE shape (MaxDD cut), not a convex
  satellite. (T-204: positive skew only modest, in the diversified sleeve.)
- **DBMF / KMLM = long/SHORT managed futures** across equities/rates/FX/
  commodities. In a sustained crisis they go short the falling assets → they
  PRINT POSITIVE (the brief cites +23-45% in 2020/2022) — genuine convexity /
  right-tail crisis-alpha. This is the bought version of the T-170 MF sleeve.
So the a-priori expectation: for the **convex** role (right-tail gains), the
long/short ETF should beat our long/flat overlay; the open question is by how
much, at what carry cost, and whether the barbell actually benefits.

## Data (FREE, on-disk stooq daily adjusted closes; PIT-clean)
- DBMF `…/nyse etfs/1/dbmf.us.txt` — **2019-05-10 → 2026-05-22** (covers 2020
  COVID + 2022).
- KMLM `…/nyse etfs/1/kmlm.us.txt` — **2020-12-08 → 2026-05-22** (covers 2022;
  **POSTDATES 2020 COVID** — reported `n/a` for COVID).
- Our sleeve: SPY/AGG/GLD (2005+), evaluated on the SAME window as each ETF.
- **DATA-GAP FLAG:** the ETF window is 2019+/2020+ — it MISSES the deep crises
  (dotcom/GFC). The deep-crisis MF defense is **literature-based** (AQR; T-170);
  this probe can only judge the 2020/2022 window. Our overlay's deep-crisis
  edge is separately validated full-cycle (T-236) — that asymmetry is part of
  the honest read.

## Metrics (corrected methodology from the brief; no sweep)
Per satellite, standalone, on its window: **Sortino + block-bootstrap `ci_low`
(`[NN-SHARPE-CI]`)**, **MaxDD**, Sharpe (secondary), CAGR, and the
**crisis-window total return** (the convexity test): COVID 2020-02-19→03-23 and
2022-01-03→10-12 — does the satellite print POSITIVE when equities crash?
Plus the **calm-period return** (the carry-bleed cost of a tail hedge).

## Barbell test (the satellite's actual job)
80% **safe core** (AGG aggregate bonds — the conservative "safe" leg) + **20%
satellite**, daily-rebalanced, on the DBMF window. Compare the barbell's
Sortino / MaxDD / crisis-return with satellite ∈ {our trend sleeve, DBMF,
KMLM}. (20% is the pre-registered satellite weight; no sweep.)

## Decision rule (fixed now)
The bought MF-ETF is a **clearly-better convex satellite** iff, on the common
window, it BOTH (a) prints **materially positive crisis-window returns** in
2020 AND 2022 (the convexity our long/flat overlay structurally lacks), AND
(b) the 80/20 barbell with it has a **better Sortino AND shallower-or-equal
MaxDD** than the barbell with our overlay. → then "consider DBMF for the
barbell's convex half." **Comparable or worse → use OUR trend overlay** (free,
full-history, no carry bleed). Honest caveat to carry either way: a bought
MF-ETF **bleeds carry in calm years** — it is a tail satellite, NOT a core;
and the verdict rests on a 2019+ window (no deep crisis).

## Out of scope
- No integration / canon change / build. If DBMF wins, the recommendation is
  to consider it for C's barbell satellite — the director/user decides
  (it's a BOUGHT product → real-money, propose-first, `[NN-AI-GATE]`-adjacent).
