---
name: reference-kalshi-public-api-quirks-2026-11-19
description: Kalshi public trade-api/v2 quirks measured during T-405 (series selection, batching that silently returns 0, 429 at 4 workers, MVE parlays flooding the open list, placeholder asks)
metadata:
  type: reference
---

Measured 2026-11-19, unauthenticated, generic UA, `https://api.elections.kalshi.com/trade-api/v2`.

- `/markets?status=open` is ~all multivariate parlays (KXMVE*, category "Exotics"); paging it + title keywords archived only parlays for 5 months (T-405). Select by SERIES.
- `/series` returns ALL ~16.7k series in ONE 21 MB response (no cursor), 1.5 s. Fields: ticker, title, category (primary), categories (list), tags, frequency (one_off/custom/annual/monthly/daily/weekly/hourly/quarterly/fifteen_min). `/series?category=X` filters by membership in the `categories` LIST, not the primary `category` (Economics 947 vs 922).
- `/events?status=open&limit=200`: 21.6k open events / 5.06k series, 108 pages, ~44 s.
- `/markets` takes ONE `series_ticker`: a comma list SILENTLY returns 0 markets; a repeated param is HTTP 400. Comma `event_ticker` also returned 0. So one request per series; `/events?...&with_nested_markets=true` costs the same (0.33 vs 0.35 s median).
- Rate limit: 4 concurrent workers (~9 req/s) lost 21-30 of 384 series to HTTP 429; 2 workers + 1/2/4 s backoff: 0 errors, ~390 requests, ~85 s. 1 worker: 177 s.
- "<X> after economic events" series (KX10YRRATEEVENT etc.) are intraday point-price ladders at a release minute, 51 strikes, mostly zero volume — 58% of macro rows. Market makers quote deep-OTM strikes at bid 0.00 / ask 0.99, which passes a "0 < ask < 1" quote rule (628 of 5,681 rows are ask-only).
- MVE parlay books report 0.0 bid / 0.0 last / 0.0 ask (not 1.00) — a `notna` "priced" check reads them as priced.
- Ticker `KXCPI-26NOV-T-0.1` is "Above -0.1%" (the minus is in the ticker); easy to misread as +0.1%.
- Outcomes: `/events/{event_ticker}` (plain) returns `{"event": {...}, "markets": [...]}` with every market's status (`finalized`), result, settlement_value_dollars, settlement_ts, expiration_value (the underlying's settle value); no truncation seen (130 markets). With `with_nested_markets=true` the list moves under `event.markets` and top-level `markets` is EMPTY. A gone event is HTTP 404; `/markets?event_ticker=bogus` is an empty 200 (cannot tell gone from empty). `/events?series_ticker=X&status=settled&limit=1` lists the most recent settled event first.
- Daily series close ~750 strikes/day in ~33 events — resolve per event, not per market.
- An event's `last_updated_ts` is NOT its close (KXGDP-26OCT30 reads its creation date 08-27); `status=closed` event queries return nothing; to date a series' last activity read `/events?series_ticker=X&status=settled&limit=1&with_nested_markets=true` and take the markets' max close_time. Of 487 recurring macro candidates with no open event, only 12 settled within 120 days (most are long dead).
- Some state series use a postal code, not the name ("TX gas price"); among 52 candidate titles opening with two capitals only TX was a state (the rest US/EU/UK).

See [[project-t405-kalshi-series-archive]] for the design that uses these.
