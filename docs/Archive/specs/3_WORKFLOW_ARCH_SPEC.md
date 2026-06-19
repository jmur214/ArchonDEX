# Technical Specification: Workflow & Features
*Response to Question Set 3*

### A) Product Intent
1. **Users**: Single User (Developer/Trader). The Machine is an "Autonomous Partner".
2. **Goal**: **Hybrid**. 
    *   **Hunt**: Screen & Rank candidates (ML).
    *   **Validate**: Test in Shadow Mode.
    *   **Execute**: Auto-trade promoted strategies.
3.  **Output**: Trade Signals -> Automated Order Placement.

### B) Universe & Filtering
4. **Universe**: Russell 3000 (~3,000 tickers).
5. **Pipeline**: **Two-Stage**.
    *   **Stage 1 (Fast)**: Hard Filters (e.g., Price > $5, AvgVol > 500k, Market Cap > $100M).
    *   **Stage 2 (Slow)**: Compute Heavy Features (Indicators + ML Scoring) on survivors.
6.  **Survivorship**: Acknowledged Bias (Free Data limitation).

### C) "Aspects" (Feature Catalog)
7.  **Versioning**: Yes. Grouped by Family (e.g., `trend.*`, `value.*`).
8.  **Multi-Timeframe**: Yes. (e.g., `RSI_14_Daily`, `RSI_14_Hourly`).
9.  **Types**: Numeric (RSI=70) and Boolean/State (Golden_Cross=True).
10. **Composed Aspects**: Yes. (e.g., "Squeeze" = Bollinger Bandwidth < Threshold).
11. **Sub-Features**: Yes. (e.g., MACD returns `Line`, `Signal`, `Hist`).

### D) Rules Engine
12. **Definition**: **DSL (Domain Specific Language)** string parsing.
    *   *Example*: `"RSI(14) > 60 AND PE_Ratio < 20"` -> Parsed into Python logic.
13. **Operators**: Standard comparison (`>`, `<`, `==`) + `crosses_above`, `crosses_below`.
14. **Events vs State**: **Both**.
    *   *Event*: `EMA50 crosses_above EMA200`.
    *   *State*: `Price > SMA200`.
15. **Nesting**: Yes (Boolean Logic `AND/OR/NOT`).
16. **Output**: Pass/Fail (Binary) + Confidence Score (ML Probability).

### E) Time & Alignment
17. **Eval Time**: EOD (End of Day scanning) + 1-Minute (Intraday gating).
18. **Point-In-Time**: Required.
19. **Fundamentals Treatment**: **Forward-Fill** from Filing Date (or Publication Date). Strictly no lookahead.
20. **Surprise Logic**: Surprise data only available AFTER release timestamp.

### F) Libraries
21. **Source of Truth**: `pandas-ta` (Python wrapper for common TA indicators).
22. **Equivalence**: **TradingView Match**. We aim for parity with standard TV logic so visual confirmation aligns with bot logic.
23. **Variants**: Standard defaults (RSI Wilder Smoothing, etc.).

### G) Performance
24. **Workload**: 3,000 Symbols x ~500 bars x 50 indicators.
25. **Feature Store**: **Yes**. Computed features cached in Parquet (`data/processed/features/`) to enable rapid ML training without re-computation.
26. **Compute**:
    *   **Batch**: Nightly full-universe update.
    *   **Incremental**: Intraday updates.
27. **Parallelism**: Single-Machine Multiprocessing (Python `multiprocessing` or `concurrent.futures`) is sufficient for 3,000 tickers.

### H) Missing Data
28. **Policy**:
    *   **Training**: Drop row if critical features missing.
    *   **Live**: Skip signal generation if data is invalid/stale/missing (Fail Safe).
29. **Liquidity Gate**: Yes. Min Dollar Volume filter applied *before* any feature compute.

### I) Normalization
30. **Types**:
    *   **Z-Scores**: (Value - Mean)/StdDev (for ML inputs).
    *   **Relative**: vs SPY or Sector ETF.
31. **Default**: Relative Strength is a core component.

### J) Extensibility
32. **Interface**: Plugin system.
    *   `def compute(df: pd.DataFrame) -> pd.Series:`
    *   Metadata: `{name, lookback, category}`.
33. **Contract**: Enforced via Base Class `FeatureProvider`.
34. **Registry**: Auto-discovery of feature scripts in `engines/features/`.

### K) Outputs & Debugging
35. **Explainability**: **Yes**.
    *   Output: *"Signal Generated because: RSI(30) < 30 [Actual: 28] AND PE < 15 [Actual: 12]"*.
36. **Exports**: Full CSV Report of every scan run.
