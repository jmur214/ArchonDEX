
Here is the detailed specification for the "Quant Factory" system, based on the user's requirements and current architecture.

---

### **1. System Overview**
The system is an **Autonomous Research & Trading Platform** designed for US Equities. Unlike a simple screener, it operates as a specialized "Hunter-Gatherer":
1.  **Ingest**: It consumes a massive feature set (3,000+ tickers x 50+ features).
2.  **Hunt**: It uses Machine Learning (Decision Trees) to discover "Explosion Patterns" (rules that predict outliers).
3.  **Validate**: It tests these rules in a **Shadow Live Environment** (Parallel Execution) to verify performance before risking capital.
4.  **Execute**: It trades verified strategies autonomously via Alpaca.

---

### **2. Answers to Specific Questions**

#### **A) Scope and Instruments**
1.  **Asset Classes**: US Equities only (Stocks/ETFs).
2.  **Regions**: US Markets (NYSE/NASDAQ).
3.  **Universe Size**: ~3,000 tickers (Russell 3000 coverage).

#### **B) Intraday Requirements**
4.  **Bar Size**: **1-Minute** (Preferred for granularity if free source available; will fallback to 5m if cost-prohibitive).
5.  **History**: **6 Months** rolling window (Sufficient for verification; long-term backtesting uses Daily data).
6.  **Session**: Regular Market Hours (9:30-16:00 ET).
7.  **Data Type**: OHLCV Candles are sufficient (No NBBO/Quotes needed).
8.  **Adjustments**: Daily adjusted bars are fine; intraday adjustment logic handled by internal normalization engine.
9.  **Accuracy**: Research-grade preferred, but tolerance for minor gaps (filled via linear interpolation) is acceptable for free-tier constraints.

#### **C) Fundamentals Requirements**
10. **Fields Needed**:
    *   **Valuation**: P/E, P/S, P/B, PEG.
    *   **Growth**: Revenue Growth (QoQ/YoY), EPS Growth.
    *   **Health**: Debt/Equity, Current Ratio.
    *   **Market**: Market Cap, Float, Shares Outstanding.
11. **Frequency**: Quarterly (Financials) + Daily (Market Cap/Valuation ratios).
12. **Auditability**: "Normalized vendor numbers" are acceptable.

#### **D) "Free" & Compliance**
13. **Definition of Free**: Strictly $0 fixed cost. We utilize:
    *   **YFinance**: For bulk history (Daily).
    *   **Alpaca (Free Tier)**: For live market data and recent intraday.
    *   **AlphaVantage/Polygon (Free Tiers)**: As supplemental backups.
14. **Redistribution**: Internal use only (Proprietary trading machine).
15. **Scraping**: Official APIs preferred, but reliable library wrappers (like `yfinance`) are acceptable.

#### **E) System Design**
16. **Stack**: Python 100% (Pandas, Scikit-Learn, FastAPI for webhook listeners).
17. **Storage**: **Parquet** (Local Filesystem). High performance, columnar, perfect for DataFrame ops.
18. **Cadence**:
    *   **Nightly**: Full Universe Scan & Strategy Evolution.
    *   **Live**: Minute-level execution loop.
19. **Infrastructure**: Local Machine initially; capable of Docker deployment.
20. **UI**: Backend-first; "UI" is currently a Console Dashboard + textual reports.

#### **F) Backtesting & Logic**
21. **Engine**: Bar-based "Assume Fill" (Conservative).
22. **Survivorship**: Desired but not strictly enforced for "Free" tier (Acceptable bias).
23. **Point-in-Time**: **CRITICAL**. The `FundamentalLoader` enforces strict "As-Of" date logic to prevent lookahead bias on earnings.

#### **G) Output Schema**
24. **Canonical Schema**:
    *   `processed/parquet/{ticker}_1m.parquet`: [Index=Datetime(UTC), Open, High, Low, Close, Volume]
    *   `processed/parquet/fundamentals.parquet`: [Index=Date, Ticker, Metric, Value, AsOfDate]
25. **Timezone**: UTC internal; Converted to ET for market-hour logic.

---

### **3. Operational Specifics**

#### **Strategy & Execution**
1.  **Holding Period**: Swing (Days/Weeks). Intraday data is used for *Smart Entry/Exit*, not HFT.
2.  **Strategy Type**: **Hybrid Ensemble**. (Pattern Recognition + Fundamental Filters + Technical Triggers).
3.  **Broker**: **Alpaca**.
4.  **PDT Constraints**: **Yes** (<$25k account). The system creates a "Cash Manager" module to strictly limit day trades to <3 per rolling 5 days.
5.  **Kill Switch**: No "Flatten All" switch; Individual Strategy Stop-Losses and Portfolio Allocation Limits are used instead.

#### **The "Hunter" Workflow (Discovery)**
1.  **Screening vs Ranking**: System is **Hybrid**.
    *   Stage 1: Hard Filters (e.g. Market Cap > $2B).
    *   Stage 2: ML Ranking (Prob. of Explosion).
2.  **Rule Definition**: **DSL (Domain Specific Language)**.
    *   User (or Machine) writes: `RSI(14) < 30 AND Revenue_Growth > 0.20`.
    *   System parses this into Python logic.
3.  **Events vs State**: Both supported.
    *   State: `RSI > 50`
    *   Event: `EMA_50 crosses_above EMA_200`

#### **Feature Engineering**
1.  **Feature Store**: Yes. Computed features are cached in Parquet to avoid re-calc.
2.  **Extensibility**: Plugin architecture.
    *   `def compute(df): return series`
    *   Auto-registered via `engines/features/registry.py`.
3.  **Indicators**: `pandas-ta` is the standard library.

#### **Logging & Metrics**
1.  **Shadow Mode**: A "Virtual Broker" runs alongside the real one, executing new candidate strategies with "Ghost Money" to prove viability.
2.  **Metrics**:
    *   Standard: Sharpe, Sortino, Drawdown.
    *   Advanced: SQN (System Quality Number), Expectancy, Win Rate, Beta.
    *   Drift: "OOS Degradation" tracked via Walk-Forward Optimization.
