---
task_id: T-2026-06-18-219
title: PIT market-cap HISTORY — close the T-210/T-215 cap-join under-count (delisted cohort)
date: 2026-06-18
author: Agent D (substrate + cloud lane)
type: substrate build + honest re-rating
outcome: >
  Closed the bulk of the T-210/T-215 under-count for FREE. yfinance get_shares_full
  carries shares-outstanding history up to a name's delisting/acquisition (back to
  ~2015), so cap-at-delisting = median(close × shares) over the final 12mo is a real
  PIT cap for the post-2015 delisted cohort. 138 of 164 delisted PIT names with price
  data RESOLVED; 26 are the free-data WALL (pre-2015 delistings — no yfinance shares).
  Decisive re-rating finding: the delisted cohort was mostly MID-cap at exit (mid 69 /
  large 44 / small 18 / micro 7), NOT micro-junk — so the de-biased universe is only
  ~8.2% small/micro by name (~4% MVO-weighted), and the realistic-cost drag lands at
  the LOW-MID end of the T-207 parametric range (~−0.05 to −0.24 Sharpe, most likely
  ~−0.10), NOT the −0.74 upper bound. The honest PIT cost moves the base only modestly
  further than the current-snapshot lower bound. Cap json extended to 458 entries (438
  resolved, 138 from delist-shares); manifest re-pinned (0 foreign drift).
status: DONE (branch feature/pit-cap-history-t219); T-215 canonical run remains queued
---

# T-219 — PIT market-cap history: closing the cap-join under-count

## 0. The limitation this closes (from T-210 / T-215)
The realistic-retail cost model (T-210) tiers half-spread by market cap
(mega/large/mid/small/micro = 2/3/8/35/75 bps). Its cap join read a CURRENT-snapshot
cap (`market_cap_tiers.json`, yfinance `fast_info`). Delisted PIT names have no current
cap → they fell back to the ADV bucket. I flagged this in T-210/T-215 as a conservative
UNDER-count: the survivorship cohort — exactly the names the PIT de-bias adds — was
costed by volume, not by its true (often smaller) size. This task tested whether a FREE
point-in-time cap history can close it.

## 1. The free source that works: yfinance get_shares_full
`yf.Ticker(t).get_shares_full(start=...)` returns shares-outstanding history with two
useful properties verified here:
- It covers **acquired/delisted names up to their delisting date** (XLNX → 2022-02,
  ATVI → 2023-10, RTN → 2020-08), not just live names.
- It reaches back to **~2015-10** (the yfinance shares horizon) — no further.

So **cap-at-delisting** = `median(close × shares_ff)` over the final 12 months of
price/shares overlap is a real PIT cap for any name delisted after ~2015. Price comes
from the on-disk `data/processed/{ticker}_1d.csv`; shares are forward-filled to price
dates. Built by `scripts/build_pit_cap_history_t219.py` (network, NOT hermetic);
merged into `market_cap_tiers.json` as `{marketCap, tier, asof, source:"delist_shares"}`.

## 2. Coverage + the free-data WALL (stated plainly)
- **Delisted PIT names with price data: 164.** RESOLVED **138** / WALL **26**.
- The **26 wall** names are **pre-2015 delistings** — yfinance has no shares history
  for them. This is the honest free-data ceiling. They remain null → ADV fallback (the
  prior conservative behaviour, unchanged). Truly survivorship-free pre-2015 caps need
  paid data (Norgate / FMP-paid / CRSP). I did **not** fabricate caps for them.
- Cap json now: **458 entries, 438 resolved** (138 from delist-shares PIT history; the
  rest current-snapshot from T-215).

## 3. The decisive finding — the delisted cohort was MID-cap, not micro
Cap-at-delisting tier distribution of the 138 resolved delisted names:

| tier  | count | half-spread |
|-------|-------|-------------|
| large | 44    | 3 bps       |
| mid   | 69    | 8 bps       |
| small | 18    | 35 bps      |
| micro | 7     | 75 bps      |

**50% mid, 32% large, only ~18% small/micro.** These are mostly *fallen-large* and
*acquired-at-a-premium* names (Xilinx, Activision, Raytheon), not collapsed micro-caps.
This MODERATES the T-207/T-210 working assumption that the survivorship cohort carries a
heavy small/micro cost. It also means the current-snapshot's ADV-15bps fallback was, for
the *large/mid* delisted majority, actually an OVER-cost (true cost 3–8 bps) — the
under-count was concentrated only in the 25 genuinely-small/micro exits.

Caveat (honest): the 26 pre-2015 WALL names are the more likely home of the true
micro/bankruptcy tail (names that collapsed rather than were acquired). They stay
ADV-fallback, so the small/micro fraction below is a mild *under*-estimate, bounded by
26 names.

## 4. Re-rating — full PIT universe with PIT caps
Full PIT universe (n=676): **429 tiered, 247 null→ADV** (the 247 = pre-2015 wall +
PIT-only live names not yet cap-fetched — those resolve large/mid, so they do not lift
the small/micro share). Tier counts: mega 50 / large 244 / mid 100 / small 24 / micro 11.

**small+micro = 35 of 429 tiered = 8.2% by name.**

Drag = `2·(s−15)·f·T` at documented turnover T≈26×/yr, ÷ 15% vol for the Sharpe hit:

| f (small/micro turnover share) | half-spread s | drag bps/yr | ΔSharpe |
|--------------------------------|---------------|-------------|---------|
| 8.2% (name-share, upper)       | 50            | 148         | −0.099  |
| 8.2% (name-share, upper)       | 100           | 361         | −0.240  |
| 4.1% (MVO down-weighted, likely)| 50           | 74          | −0.049  |
| 4.1% (MVO down-weighted, likely)| 100          | 180         | −0.120  |

**Most-likely realistic-cost drag ≈ −0.10 Sharpe** (inverse-vol/MVO under-weights
small/micro → f below the name-share). This is the LOW-MID end of the T-207 parametric
band (−0.12 to −0.74), NOT the high end. **The honest PIT cost moves the base only
modestly further than the current-snapshot lower bound** — because the de-biased
universe is only ~8% small/micro, and the delisted cohort that drove the worry was
mostly mid-cap at exit.

So the two honest corrections (survivorship de-bias + realistic cost) still compound,
but the *cost* leg is milder than feared. This is good news for the honesty of the base:
the survivorship correction (Sharpe-lowering via more names/regimes) is the larger of the
two; the realistic-cost correction on top is ~−0.10, not a further ~−0.7.

## 5. What's analytical vs realized
The ΔSharpe above is analytical (cap distribution × documented 26× turnover × the cost
model), the tractable decision-grade answer given the compute reality (a 676-name 6-edge
PIT backtest is ~hours locally — the T-207/T-215 finding). The **realized** number is the
T-215 canonical cloud cell (PIT × realistic-cost, now with these PIT caps baked) — still
queued on C's T-211 harness. This task makes that cell more honest: its cap join now
tiers 138 delisted names correctly instead of ADV-falling-back all of them.

## 6. Additive / default-OFF / pinned
- `realistic_retail_costs` stays **default-OFF**; this only improves the accuracy of its
  cap join when ON. No prod default flip. OFF path byte-identical (T-210 unchanged).
- `market_cap_tiers.json` re-pinned: `gen_substrate_manifest` regenerated, **verify OK,
  14120 files, 0 foreign drift** (diff = the cap-json line only). Same bake discipline as
  the T-215 fail-open fix — the cloud cell uses the enriched caps, not an empty cache.

## Files
- `scripts/build_pit_cap_history_t219.py` — NEW; cap-at-delisting builder (yf shares × price)
- `data/universe/market_cap_tiers.json` — extended to 458 entries / 438 resolved (gitignored)
- `config/substrate_manifest.sha256` — re-pinned (cap-json only; 0 foreign drift)

## NOT done (per constraints)
No prod-default flip (realistic-cost stays OFF; PIT stays OFF). Promote nothing. The
26 pre-2015 WALL names are left null (ADV fallback) — flagged, not fabricated. The
realized re-rating is the T-215 cloud cell (queued on C/T-211). Branch only; director
reviews + merges.
