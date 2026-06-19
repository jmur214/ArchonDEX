# Technical Specification: Scope & Data Requirements
*Response to Question Set 1*

### A) Scope and instruments
1. **Asset Classes**: US Equities only (Stocks & ETFs). Options/Crypto/Futures are out of scope for Phase 2.
2. **Exchanges**: US National Exchanges (focused on NYSE/NASDAQ coverage).
3. **Symbol Universe**: ~3,000 tickers (Targeting the Russell 3000 index components).

### B) Intraday requirements
4. **Bar Size**: **1-Minute** bars are the primary requirement. (Secondary support for 5m/15m/1h aggregations).
5. **Lookback**: **6 Months** of intraday history is sufficient for our "Hunter" validation logic.
6. **Session**: Regular Market Hours (09:30 - 16:00 ET) are the priority. Extended hours are nice-to-have but not critical.
7. **Data Type**: OHLCV Candles. (Level 1 / NBBO Quotes are not required for our current strategy family).
8. **Adjustments**: Daily bars should be split/dividend adjusted. Intraday bars can be raw or adjusted, provided normalization is consistent.
9. **Accuracy**: Research-grade is ideal, but given "Free Tier" constraints, we accept retail-grade data with tolerances for occasional missing bars (interpolated).

### C) Fundamentals requirements
10. **Fields Required**:
    *   **Valuation**: P/E, P/S, P/B, PEG.
    *   **Growth**: Revenue Growth (QoQ), EPS Growth (YoY), Earnings Surprise.
    *   **Health**: Debt-to-Equity, Current Ratio.
    *   **General**: Market Cap, Float, Shares Outstanding, Sector/Industry.
11. **Frequency**: 
    *   **Quarterly**: For financial statement data (Income/Balance Sheet).
    *   **Daily**: For Price-derived ratios (e.g., P/E fluctuating with Price).
12. **Source**: "Normalized vendor numbers" are perfectly acceptable; direct EDGAR/XBRL parsing is not required.

### D) "Free" constraints and compliance
13. **Definition of "Free"**: Strictly $0 fixed monthly cost.
    *   We utilize "Free Tiers" of vendors (AlphaVantage, Polygon, Alpaca) and libraries like `yfinance` / `pandas_datareader`.
    *   We accept rate limits and occasional manual backfills.
14. **Redistribution**: None. Data is for internal proprietary use only (the "Machine" trades for itself).
15. **Scraping**: Official APIs are preferred, but established scraping libraries (like `yfinance`) are standard procedure for us.

### E) System design + operations
16. **Stack**: Pure **Python**.
17. **Storage**: **Partitioned Parquet** (Local Filesystem).
    *   Structure: `data/raw/intraday/provider=alpaca/symbol=XYZ/date=YYYY-MM-DD/*.parquet`
    *   Reason: Handles the projected ~147M rows efficiently with fast incremental updates.
18. **Cadence**:
    *   **Nightly**: Bulk data ingest (Fundamentals + Daily Bars).
    *   **Live**: Minute-level polling during market hours for candidate list only (to respect rate limits).

### F) Backtesting and strategy needs
21. **Type**: Bar-based "Assume Fill" engine (Conservative modeling using High/Low/Close).
22. **Survivorship Bias**: Desired, but effectively ignored for Phase 2 given the "Free Data" constraint. We will explicitly flag this bias in reports.
23. **Point-In-Time**: **CRITICAL REQUIREMENT**.
    *   Fundamentals stored as "As-Of Publication" records.
    *   **Logic Upgrade**: We will store `EPS_TTM` (static) and compute `Price/Earnings` dynamically (`Daily_Close / EPS_TTM`) to ensure consistency.

### G) Output format
24. **Schema**:
    *   **Intraday**: `[Symbol, Timestamp (UTC), Open, High, Low, Close, Volume]`
    *   **Fundamentals**: `[Symbol, date_published, Metric, Value]`
25. **Timezone**: **UTC** for storage. Converted to **ET** for market logic.
