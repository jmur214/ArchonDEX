---
name: project-t405-kalshi-series-archive
description: T-405 Kalshi archive rebuild (merged to main 49331c7) — series list in config/kalshi_macro_series.json, selection rule, real-quote rule, the per-event + historical-API resolver, and the alarm/rc contract
metadata:
  type: project
---

T-405 (2026-11-19, merged to main as 49331c7): `snapshot_kalshi` reads ONLY `config/kalshi_macro_series.json` (~400 series, ~5.7k rows/day) and fails closed without it. `--discover-kalshi-series` regenerates it (one line per series, diffable). Old 21,294 rows stay (selector null, KXMVE); new rows carry `selector="series_v1"`, `series_ticker`, strike fields.

**Why:** the user wants the archive as an INFORMATION source to direct trades — macro/market-relevant over breadth.

**How to apply (current rules — earlier versions of this note were superseded):**
- Selection: Economics/Financials/Commodities by whole-word title keyword or exact tag; Politics by exact policy tags {federal reserve, trade & tariffs, budget & shutdowns} OR a narrow title phrase (fed chair / fomc / federal reserve / government shutdown / shutdown by / this year / vote), EXCEPT visit/attend/dinner/lunch/golf novelty (Politics only); Crypto BTC/ETH only. Excluded: Elections, World, Sports etc.; hourly/fifteen_min; "after economic events" ladders; state/city titles + local tags (a postal-code prefix counts only before a local retail price — gas/diesel/home/rent/electricity — because codes collide with countries: IN, DE, CA, ID); *COMBO; KXFED.
- Kept: an open event, OR a recurring series whose latest settled event closed ≤ 120 d (read from the historical API when the live nested list is empty).
- Real quote = bid > 0 | last > 0 | 0 < ask < 1; ask-only placeholders stay (director ruling).
- Resolver: series_v1 rows only; ONE live GET per event (≤150 events/run); tickers the live listing lacks (or in a 404 event) → `/historical/markets?event_ticker=` (one GET per event; markets settled before `/historical/cutoff`, ~2 months back, live there) → then per ticker live `/markets/{t}`, and on its 404 `/historical/markets/{t}` (≤50 tickers/run). `not_found` final ONLY when live AND historical single-market both 404 (`resolved_via="market+historical"`). New-before-re-ask ordering; stale (>30 d) non-final events re-asked weekly.
- Alarms: a PARTIAL day keeps rows but says FAILED; main() exits 1 only on FAILED kalshi / kalshi_resolve / polymarket_resolve lines. Price outside [0,1] or <50 % quoted → nothing written.
- Dormant-but-matching Politics series (KXFEDCHAIRNOM, KXFOMCVOTE, KXSHUTDOWNBY, KXGOVSHUT): no open and no settled event on 2026-11-19, so not listed until one appears.
- Cloud redeploy is the user's call (the config IS in the paper image context).
- Lock tests: tests/test_archive_kalshi_series.py (committed-config tests re-run the rule on the committed rows).

Related: [[reference-kalshi-public-api-quirks-2026-11-19]].
