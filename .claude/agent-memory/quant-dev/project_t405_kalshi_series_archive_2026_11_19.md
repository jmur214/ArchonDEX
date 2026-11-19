---
name: project-t405-kalshi-series-archive
description: T-405 Kalshi archive rebuild — series list in config/kalshi_macro_series.json, real-quote rule, what was excluded and why, and the open questions handed to the director
metadata:
  type: project
---

T-405 (2026-11-19): `snapshot_kalshi` now reads ONLY `config/kalshi_macro_series.json` (384 series: Economics 169, Financials 97, Politics 64, Crypto 31, Commodities 23; ~5.7k rows/day) and fails closed without it. `--discover-kalshi-series` regenerates it (one line per series for diffable review). Old 21,294 rows stay (selector null, KXMVE); new rows carry `selector="series_v1"`, `series_ticker`, plus strike fields (floor/cap_strike, strike_type, yes_sub_title).

**Why:** the user wants the archive as an INFORMATION source to direct trades — macro/market-relevant over breadth.

**How to apply:**
- Excluded by stated rule: Elections, World, Sports/Entertainment/Mentions/Exotics/Climate/Companies; hourly + fifteen_min; "after economic events" ladders; state/city titles + local tags; *COMBO; KXFED (snapshot_kxfed has it). Politics only via exact tags {federal reserve, trade & tariffs, budget & shutdowns}; Crypto BTC/ETH only.
- Real quote = bid > 0 | last > 0 | 0 < ask < 1 (director's rule). Polymarket `_pending` also accepts an outcomePrices value strictly inside (0,1) for pre-11-17 rows; Polymarket SNAPSHOT fail-closed uses the book fields only (keeps the old test contract).
- Open questions handed back: ask-only rows (628/5,681, many 0.99 placeholders) pass the rule; 36 of the 11-18 parlays pass by a tiny ask (0.0006–0.06) so the resolver will look them up once; cloud redeploy is the user's call (config IS in the paper image context once committed).
- Lock tests: tests/test_archive_kalshi_series.py (committed-config tests re-run the rule on the committed rows).

Related: [[reference-kalshi-public-api-quirks-2026-11-19]].
