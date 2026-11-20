---
name: reference-options-data-sources-2026-11-20
description: Verified 2026-11-20 what free options data exists — Alpaca has option bars/trades from ~2024-01 incl. expired contracts but NO historical quotes; Cboe CDN index list and spans; put/call archive ends 2019-10; SqueezeMetrics GEX free 2011+
metadata:
  type: reference
---

All verified by probe on 2026-11-20 (generic UA; counts and field names only).

**Alpaca (paper key from `.env`, never printed)**
- `/v1beta1/options/bars`: OHLC, volume, VWAP and trade count. It works for **expired** contracts; a Feb-2024 SPY contract had bars from 2024-01-18. There is no `feed` parameter.
- `/v1beta1/options/trades`: historical prints with price, size, exchange and condition. Also works for expired contracts.
- **No historical quotes.** `/v1beta1/options/quotes` returns 404, and `docs.alpaca.markets/us/llms.txt` lists only bars, trades, latest quotes, latest trades, snapshots and chain.
- Snapshots and chain carry `impliedVolatility` and greeks for near-ATM contracts, **current values only**, so they can be archived going forward.
- Plans:
  - Basic (free): an indicative real-time feed ("not actual OPRA quotes"), history except the latest 15 minutes, 200 calls/min.
  - Algo Trader Plus, $99/mo: OPRA, 10,000 calls/min.
- Trading:
  - Level 3 multi-leg orders exist on the Trading API.
  - Index options (SPX, SPXW, XSP, VIX, DJX) appear in the **Broker API** docs. Whether retail or IRA accounts can trade them is unverified.

**Cboe, free:** `cdn.cboe.com/api/global/us_indices/daily_prices/<SYM>_History.csv`
- VIX and SKEW from 1990.
- VIX1D from 2022-05; VIX9D 2011; VIX3M 2009-09; VIX6M 2008; VIX1Y 2007; VVIX 2006-03; VXTH 2006.
- PUT 1991 on the CDN (1986 via the Wayback copy on disk); BXM 2002.
- BXMD, BFLY, CNDR, CLLZ, CMBO and PPUT from 1986-06; BXY 1988; WPUT 2006; BXMW 2012; CLL 2008.
- COR1M and COR3M 2006; DSPX and VIXEQ 2014.
- VXST returns 403.
- Trap: the strategy indices are gross, use VWAP-window fills, and were backfilled at launch.

**Other sources**
- Cboe put/call CSVs (`cdn.cboe.com/resources/options/volume_and_call_put_ratios/{total,equity,index,vix,etp}pc.csv`) cover **2006-11 to 2019-10 only**.
- SqueezeMetrics `squeezemetrics.com/monitor/static/DIX.csv` (date, price, dix, gex) runs 2011-05-02 to the present.
- FINRA consolidated (CNMS) daily short-volume files are served for 2018-08. CNMS for 2009–2010 returns 403.
- The local `data/macro/VIX*` files ended 2026-06/07; they were stale.
- No option-chain history exists on disk.
- Minneapolis Fed market-based probabilities: every URL tried returned 404.

**IRS Pub 550** (`irs.gov/publications/p550`): §1256 includes broad-based index options, with 60/40 treatment and a year-end mark-to-market. It also covers the straddle rules (with the qualified-covered-call exception) and constructive sales.

**How to apply:** an options test on free data can measure *gross* premia from trade prints. A *net-of-spread* claim needs real fills or a paid quote source (OptionMetrics/WRDS, ORATS, Databento). See [[project-t410-ideas-census-2026-11-20]].
