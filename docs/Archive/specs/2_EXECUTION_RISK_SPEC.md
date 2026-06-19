# Technical Specification: Execution & Methodology
*Response to Question Set 2*

### 1) System Intent
1. **Instruments**: US Equities (Long/Short).
2. **Holding Period**: **Swing** (Multiday/Week). Intraday data is used for "Smart Entry/Exit" optimization, not HFT/Scalping.
3. **Direction**: Long and Short.
4.  **Strategy Family**: **Hybrid Ensemble**. Captures "Explosion" events using a mix of Fundamental Factors (Growth/Value) and Technical Triggers (Momentum/Volatility).
5.  **Portfolio**: Ensemble. Multiple strategies run in parallel, managed by a `StrategyGovernor` (Portfolio Allocator).

### 2) Execution & Brokerage
6. **Broker**: **Alpaca** (Paper & Live).
7.  **Orders**: Market (for immediate entry), Limit, and Bracket Orders (Stop Loss + Take Profit) supported.
8. **Constraints**:
    *   **PDT Rule (Pattern Day Trader)**: **Active**. Account < $25k. System incorporates logic to track day-trade count and block trades if limit is reached.
    *   **Shorting**: Available but constrained by "Hard to Borrow" availability via Broker API.
9. **Slippage**: Modeled as **Realistic** (Close Price +/- fixed 5bps or bid/ask spread proxy).
10. **Latency**: Assumed negligible for Swing strategies. Fills assume "Next Bar Open" or "Close" depending on trigger.

### 3) Position Sizing & Risk
11. **Sizing**: **Fixed Fractional Risk** (e.g., Risk 1% of Equity per trade) or **Volatility Targeted**.
12. **Per-Trade Cap**: Yes. Max 1.0R loss per trade via hard Stop Loss.
13. **Portfolio Risk**:
    *   Max Gross Exposure: 100% (No Leverage initially).
    *   Sector Exposure limits implemented in Portfolio Optimizer.
14. **Exits**:
    *   Hard Stop Loss (Price based).
    *   Trailing Stops (ATR based).
    *   Time Stops (Exit if thesis invalid after N days).
15. **Kill Switch**: **No "Flatten All"**. We rely on distinct Strategy-level stops and Portfolio-level allocation caps (e.g., if a strategy performs poorly, the `Governor` reduces its allocation to 0%).

### 4) Backtesting Methodology
16. **Data**: Daily for Trend/Macro logic; 1-Minute for execution timing.
17. **Corp Actions**: Handled by Data Vendor (Adjusted Prices). Delisted stocks ignored (Free tier constraint).
18. **Simulation Type**: Bar-based.
19. **Validation**: **Walk-Forward Optimization (WFO)**. Models are trained on rolling windows (e.g., Train 1 Year, Test 3 Months) to prove consistency.
20. **Lookahead**: Prevented by "Point-in-Time" fundamental loading and Next-Bar execution logic.
21. **Overfitting**: Controlled by **Probability of Backtest Overfitting (PBO)** checks using "Combinatorial Purged CV" (Synthetic data testing).

### 5) Business Objectives
22. **Target**: Consistently outperform the S&P 500 (Alpha > 0). Max Drawdown < 15%.
23. **Curve**: Preference for **Growth** (High Upside/Sortino) over purely Smooth curve. We hunt "Explosions".
24. **Frequency**: Occasional. We filter for high-quality setups -> " Sniper, not Machine Gun".
25. **Scale**: Retail (<$25k) growing to ($100k+). Structure must scale.
26. **Tax**: Agnostic for now.

### 6) Outputs & Monitoring
27. **Trade Log Upgrade**:
    *   **Core**: `[Time, Symbol, Action, Qty, Price, Strategy_ID]`
    *   **Per-Trade Metrics**: `Exit_Reason`, `Holding_Days`, `Planned_Stop`, `Realized_R`.
    *   **Diagnostic**: `MAE` (Max Adverse Excursion), `MFE` (Max Favorable Excursion), `Slippage_bps`.
    *   **Context**: `Market_Regime_Tag` (e.g. "High_Vol"), `Prediction_Probability` (for ML).
28. **Reports**: Console Dashboard (Live) + CSV Logs.
29. **Alerts**: Console Logging + potential email/webhook integration for errors.

### 7) Metrics & "The North Star"
30. **North Star Score (MachineScore)**:
    *   `w1(Alpha) + w2(Sortino) + w3(Calmar) - w4(CVaR) - w5(PBO)`
31. **Explosion Metrics** (Crucial for our strategy):
    *   **Explosion Capture Rate**: % of >5% moves we caught.
    *   **Participation Rate**: How much of the move did we capture?
32. **Trade Economics**:
    *   **Expectancy (Net R)**: `P(win)*AvgWin - P(loss)*AvgLoss - Costs`.
    *   **Gap Risk**: % of losses where gap > stop.

### 8) ML Specifics
33. **Target**: **Multi-Class Classification**. Targets: `Explode` (>5% move), `Crash` (<-5% move), `Stable`.
34. **Features**: Lagged inputs (Returns t-1, Volume t-1) + Point-in-Time Fundamentals.
35. **Drift**: Monitoring via **Regime Analytics** (Is the strategy performing differently in the current Volatility Regime?).
