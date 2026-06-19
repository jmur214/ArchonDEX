# Phase 2 Implementation Plan: The Quant Factory

> **Status**: DRAFT FOR REVIEW
> **Objective**: Implement a "Hunter-Gatherer" architecture where the machine ingests massive datasets (Fundamental + Technical), discovers "Explosion" patterns using Decision Trees, and validates them in a Parallel Shadow Environment.

---

## 1. The "Megadata" Layer (Milestone 1)
**Goal**: Build a unified "Feature Matrix" that aligns Fundamentals, Technicals, and Price perfectly in time.

### 1.1 Fundamental Data Loader
- **Module**: `engines/data_manager/fundamental_loader.py`
- **Logic**:
  - Ingest CSVs/APIs (FMP/Yfinance).
  - **Logic Upgrade**: Store static TTM data (EPS, Revenue) and compute dynamic ratios (P/E) daily using Price.
  - **CRITICAL**: Implement "Point-in-Time" Forward Filling.
  - **Prevention**: Strict "Lookahead Bias" prevention.
- **Output**: `data/processed/fundamentals.parquet`

### 1.2 The Feature Engineer (Expanded)
- **Module**: `engines/engine_d_research/feature_engineering.py`
- **Function**: `compute_features(ohlc_df, fund_df) -> feature_matrix`
- **Contract**: Every feature must declare `{name, frequency, lookback, type}`.
- **Feature Set ("The Aspects")**:
  - **Trend (Technicals)**:
    - Moving Averages: `SMA_50`, `SMA_200`, `EMA_20`, `Distance_from_SMA200`.
    - Crossovers: `Golden_Cross` (50 > 200), `Death_Cross`, `EMA_Ribbon_Spread`.
    - Momentum: `RSI`, `ADX` (Trend Strength), `MACD_Hist`.
  - **Volatility & Liquidity**:
    - `ATR_Percent`, `Bollinger_Squeeze` (Width), `Beta` (vs SPY).
    - `Relative_Volume` (RVOL), `Turnover_Rate`.
  - **Fundamentals (Valuation & Health)**:
    - `PE_Ratio`, `Forward_PE`, `PEG_Ratio`.
    - `Price_to_Book`, `Price_to_Sales`.
    - `Market_Cap` (Log Scale), `Debt_to_Equity`.
  - **Growth**: `Revenue_Growth_QoQ`, `EPS_Growth_YoY`, `Earnings_Surprise`.
  - **Relative Strength**: `Rel_Strength_SPY`, `Rel_Strength_Sector`.

---

## 2. The "Hunter" (Milestone 2)
**Goal**: Automate the discovery of predictive patterns for *all* market states.

### 2.1 Target Definition ("The Crystal Ball")
- **Shift**: Move from Binary (Explosion/Noise) to **Multi-Class Classification**.
- **Labels**:
  - `Label 2 (EXPLODE)`: Return > +5% in 3 days.
  - `Label 1 (BULLISH)`: Return > +1% in 3 days.
  - `Label 0 (STABLE)`: Return between -1% and +1%.
  - `Label -1 (BEARISH)`: Return < -1% in 3 days.
  - `Label -2 (CRASH)`: Return < -5% in 3 days.
- **Why**: The machine learns "Context". High P/E might signal "Momentum" in a Bull market but "Crash Risk" in a Bear market. The machine needs to distinguish between "Going to Moon" and "Going to Zero".

### 2.2 Decision Tree Scanner (Explained)
- **Module**: `engines/engine_d_research/tree_scanner.py`
- **Algorithm**:
  - Use `sklearn.DecisionTreeClassifier` or `RandomForest`.
  - **Input**: The Feature Matrix (Milestone 1).
  - **Target**: The Explosion Labels (2.1).
- **The "Magic" Explained**:
  1.  Imagine a spreadsheet with 10,000 rows (Days) and 50 columns (Features like RSI, PE).
  2.  The "Target" column is what happened next (Explode, Crash, etc.).
  3.  The algorithm asks: *"Which Single Question splits the data best?"*
  4.  *Question 1*: "Is RSI > 70?" -> Yes: mostly Crashes. No: mostly Stables.
  5.  It repeats this recursively on the subgroups.
  6.  **Result**: It builds a flowchart logic automatically.
      - Rule #1: `IF RSI > 70 AND Volatility < 1.0 THEN Prob(CRASH) = 65%`.
      - Rule #2: `IF RSI < 30 AND Revenue_Growth > 20% THEN Prob(EXPLODE) = 70%`.

### 2.3 The "Settings" Auditor
- **Logic**: Take the discovered rule (e.g. RSI > 60) and "fuzz" it.
  - Test RSI > 55, 60, 65.
  - Test Vol_ZScore > 1.5, 2.0, 2.5.
  - Return the *Robust* sweet spot, not just the overfit peak.

---

## 3. The "Shadow Realm" (Milestone 3)
**Goal**: A safe "Staging Area" for *NEW* strategies.

### 3.1 The Distinction (Shadow vs. Paper)
**Current State**: The system only "learns" via backtesting historic data. When you run `run_live.py`, it executes *only* the strategies you have manually approved.
**New State**: We introduce **Parallel Execution**:
- **Shadow Trading (New)**: Runs *Candidate* strategies (from 2.2) that look promising but are **unproven**.
  - They execute in a separate "Virtual Portfolio".
  - They do NOT touch your main PnL.
1.  **Thread A (Production)**: Executes `active_config.json` with Real Money (or Paper Money). This is your "Bank".
2.  **Thread B (Shadow)**: Executes `shadow_config.json` (the new candidates) with "Ghost Money".
    - It places trades internally but sends nothing to the broker.
    - **Benefit**: This catches strategies that look good in backtest (History) but fail in the current market regime (Now) *before* you lose a cent.




### 3.2 Shadow Loop
- **Script**: `scripts/run_shadow_paper.py`
- **Process**:
  1.  Run daily alongside `run_live.py`.
  2.  Execute *only* the "Candidate Strategies" (from Milestone 2).
  3.  Log every trade to `data/shadow_trades.csv`.

### 3.3 The Promotion Gate
- **Logic**:
  - **Condition 1**: Shadow Profit > 0 after 20 trades.
  - **Condition 2**: Win Rate > 55%.
  - **Action**: Move strategy ID from `shadow_config.json` to `active_config.json`.

---

## 4. Metrics & Standards (Milestone 4)
**Goal**: Institutional-grade scorecard.

### 4.1 New Metrics (Expansion)
We will implement an extensible `MetricsEngine`. Candidates:
- **Calmar Ratio**: Annual Return / Max Drawdown (The "Sleep Well" score).
- **Kelly Fraction**: Optimal bet size based on edge (prevents overbetting).
- **Beta**: Correlation to S&P 500 (Are we generating Alpha or just riding the wave?).
- **VARR (Value at Risk)**: "What is the worst case loss on a standard day?"
- **Expectancy**: Average $ won per trade.
- **SQN (System Quality Number)**: Expectancy / StdDev (Van Tharp's metric).
- **Explosion Capture**: % of >5% moves caught.
- **MAE/MFE**: Max Adverse/Favorable Excursion (Perfect entry diagnostics).

---

## 5. Execution Order
1.  **Fundamental Interface**: Create the *structure* for data loading (waiting on your sources for implementation).
2.  **Feature Plug-in System**: Build the extensible factory for signals (1.2).
3.  **The Hunter**: Build the Classification Logic (2.1 & 2.2).
4.  **Shadow Loop**: Build the validation Sandbox (3.1).
