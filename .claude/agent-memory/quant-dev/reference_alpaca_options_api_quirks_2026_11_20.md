---
name: reference-alpaca-options-api-quirks-2026-11-20
description: Alpaca options market-data quirks measured live in T-416 (rate-limit headers, OPRA 403, index options without IV, stale SPX-root quotes, delayed_sip, OI lag, which contracts lack IV)
metadata:
  type: reference
---

Measured 2026-11-20 with the paper key from the main `.env` (never printed), using plain `requests` with `APCA-API-KEY-ID`/`APCA-API-SECRET-KEY` headers.

- **Rate limits (X-RateLimit-Limit header):** data.alpaca.markets returns 200/min. The paper trading host returns 200/min on `/v2/options/contracts` but 1000/min on `/v2/calendar`. `X-RateLimit-Reset` is in epoch seconds. These numbers come from the headers; I did not stress-test the limits on the shared key.
- **Feeds:** `feed=opra` returns 403 `"OPRA agreement is not signed"`; only `indicative` is free. Stock snapshots: `feed=sip` returns 403 ("subscription does not permit querying recent SIP data") and `feed=delayed_sip` works (15 min delay); `iex` works too.
- **Index options:** `/v1beta1/options/snapshots/{SPX|SPXW|XSP}` serve quotes but NEVER IV or greeks, because Alpaca has no index level. The stock snapshot has no index price either, so a band needs a proxy (SPY for XSP).
  - The SPX root is the AM-settled monthly and stops trading the day before expiry: on expiry Friday, its quotes were stamped Thursday. A freshness rule catches this; a presence rule would not.
  - `/v2/options/contracts?underlying_symbols=SPXW` returns 0 rows, because SPXW is listed under `underlying_symbols=SPX` with roots SPXW, SPX and SPXO. Contracts report `tradable: true` for SPX and XSP on the paper account (trading level not verified).
- **IV coverage:** IV and greeks are missing for 0DTE and for deep ITM/OTM contracts. In a ±20 % band over the 4 nearest expiries including 0DTE, about 55 % of contracts had IV. With Friday weeklies plus monthlies (no 0DTE), about 95 % had IV.
- **Expiries:** the ETFs have daily expiries. AAPL-class names now list Mon/Wed/Fri. "Next N expiries" therefore spans only days, so pick the last expiry of each week instead.
- **Contracts endpoint:**
  - Takes a comma list of underlyings, `limit` up to 10000, and paginates with `page_token`.
  - It carries `open_interest` plus `open_interest_date`, lagging about 2 trading days, and `close_price`.
  - 12-30 % of contracts in the band have null OI (newly listed).
- **Snapshot payload shape:**
  - Timestamps carry 9 fractional digits, mixed with "...:00Z". Parse with `format="ISO8601"` (see [[feedback-pandas3-dtypes-and-monkeypatch-defaults]]).
  - `dailyBar` can be WEEKS old for an untraded contract, so check its date before reading it as today's volume.
  - Quote condition codes seen: ' ', A, B, C, O.
  - Deep-OTM rows look like bid 0.00 / ask 0.01.
  - No ask<bid, bid==ask or 1.00-placeholder asks were seen in about 3.8k rows (one ask==1.00 on XSP).
- **Latency:** each chain call (one expiry, ±20 %) takes about 0.3-0.5 s. A full 49-underlying day was 343 calls in 109 s, with 0 × 429 at 170/min pacing.
- **Delisted strikes linger:** the chain serves contracts the active listing has dropped (COST 2026-11-24: 100 of 890, all stamped the previous session). Match against the listing and flag them; they have no style/OI.
- **Do last quotes persist?** Seen for SPX-root (Thursday's quote on Friday) and delisted COST strikes (the previous session's). NOT observed for ACTIVE contracts after midnight or over a weekend; T-416's late capture assumes it and FAILS (no fresh quotes) if it is wrong.
- **requests traps:** the read timeout is per socket read (a drip server blocks for ever); `InvalidHeader` quotes the header VALUE in its message; redirects carry custom auth headers to the new host.
- **Quote wipe at the close:** (corrected 2026-11-24: rule v1 rejected the 164 zeroed rows but admitted 144 more bid-0 XSP rows through its trade leg.) at 15:59:59 ET on 2026-11-20, 164 XSP contracts were rewritten to bid 0 / ask 0, size 0, exchange "?", with fresh timestamps. That is the "present but empty" shape. ETF options quote until 16:15 ET; a new closing quote condition `T` appears at 16:00:00 on real quotes. The feed state at 18:30 ET (the launchd time) was NOT observed.

Design that uses these: [[project-t416-options-snapshot-archive]].
