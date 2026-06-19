# Phase 3: Autonomous Hedge Fund (Optimization & Scale)

Having successfully implemented the "Closed Loop" Learning System (Phase 2), the machine is now functionally autonomous. However, to compete with professional desks, we must upgrade its "Brain" (Portfolio Construction) and "Reach" (Universe).

## 1. Portfolio Optimization (The "Allocator")
**Current State**: "Adaptive" Mode (Inverse Volatility). This is robust but naive. It ignores correlations (e.g., buying MSFT and AAPL efficiently).
**Upgrade**: Activate **Mean-Variance Optimization (MVO)**.
- **Goal**: Maximize Sharpe Ratio, not just diversity.
- **Mechanism**: Use Solver to find weights that minimize Portfolio Variance for a given Alpha.
- **Constraints**: Sector Limits (max 30% Tech), Gross Exposure (max 100%).
- **Status**: `optimizer.py` exists. Config updated to `"mean_variance"`.

## 2. Universe Expansion (The "Reach")
**Current State**: ~40 Tickers (Dow 30 + basic).
**Upgrade**: Scaling to **S&P 500** or **Russell 1000**.
- **Data Ingestion**: Need robust batch fetching (Polygon.io / yFinance bulk).
- **Performance**: Optimize `DiscoveryEngine` to handle 500x data size (Parallel Processing).

## 3. Alpha Ensemble (The "Committee")
**Current State**: Individual Strategies (RSI, Breakout) fire signals.
**Upgrade**: **Meta-Model**.
- Train a secondary model to "Weight" the strategies based on current Regime.
- Example: In "High Vol", weight `Breakout` 80%, `MeanReversion` 20%.

## 4. Execution Algorithms (The "Trader")
**Current State**: "Fill at Next Open".
**Upgrade**: **VWAP / TWAP**.
- Break large orders into child orders to minimize market impact.
- Engine E (Execution) expansion.

## Immediate Next Steps
1.  Verify MVO is working (Run Backtest with new config).
2.  Expand Universe (Edit `universe.json`).
