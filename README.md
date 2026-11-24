<p align="center">
  <img src="https://img.shields.io/badge/Status-Research_%2B_Paper_Trading-blue.svg" alt="Status">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Broker-Alpaca_(paper)-FFDC00.svg" alt="Broker">
  <img src="https://img.shields.io/badge/Architecture-6_Engine_Quant_System-00C853.svg" alt="Architecture">
  <img src="https://img.shields.io/badge/Tests-5%2C300%2B_passing-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Real_money-none-lightgrey.svg" alt="Real money">
</p>

# ArchonDEX

A research platform and paper-trading system for systematic investing, built like a small trading firm: six engines with separate jobs, a measurement stack that is hard to fool, and a rule that nothing gets real money until it has honestly earned it.

> **This is not a script that runs a strategy.** It is a system for finding strategies, trying to disprove them, running the survivors on paper, and keeping an honest record of what happened.

**The honest headline:** after a year of work and about 300 logged research tasks, no strategy here has yet cleared the project's own bar for beating a plain passive index portfolio. So no real money trades. What the project has to show is the machinery that makes that verdict trustworthy, and a public record of every idea it killed.

---

## Where it stands

| | |
|---|---|
| **Research record** | About 300 logged tasks in [`TASK_LEDGER.md`](docs/State/TASK_LEDGER.md). 45 strategy ideas refuted by pre-registered tests; many more closed before running because the arithmetic showed the test could not succeed. |
| **Evidence bar** | Every result needs a block-bootstrap confidence interval, and gates read the interval's lower bound. The bar is corrected for every backtest ever run on the same data (about 370 effective trials). |
| **Paper trading** | Three paper accounts run daily on AWS Batch against Alpaca's paper API: a trend-following sleeve, an index-plus-momentum book, and an LLM-analyst experiment on a separate track. Each run reconciles against the broker and fails loudly if it cannot explain its positions. |
| **Data** | Multi-decade price history, plus daily archives of prediction markets (Kalshi, Polymarket), SEC filings, short interest, credit spreads and option quotes. |
| **Tests** | 5,300+ automated tests. A merge needs the full suite green and an independent review that re-runs the work. |
| **Real money** | None. Deployment waits for clear outperformance of a passive benchmark, net of costs and taxes. |

### What the project found out the hard way

- **Most retail-accessible signals do not survive honest testing.** Momentum and factor tilts, small-cap momentum, insider-filing signals, filing-text changes, closed-end-fund discounts, levered-ETF stacks, gold overlays, put-writing and regime timing were all tested and refuted. The verdicts are in [`docs/Audit/`](docs/Audit/).
- **Short backtests cannot see small edges.** At the project's corrected bar, a real 2%-a-year edge passes a 26-year backtest only about 3% of the time ([audit](docs/Audit/fresh_eyes_and_salvage_audits_2026-11-14.md)). New work therefore goes to per-event designs, century-long data and structural decisions such as costs, taxes and risk.
- **The measurement stack was the hardest part.** Several early "wins" were measurement defects: capital that was sized twice, a significance test whose null was a point mass, survivorship holes in the price history. Each fix is locked by a test that fails if the defect returns.
- **Good forecasts are not the same as tradeable ones.** Prediction-market prices forecast inflation and Fed decisions well, but stocks and bonds price the same information before a daily strategy can act on it.
- **The six engines are a research architecture, not yet a trading desk.** A [code-level audit](docs/Audit/trade_desk_gap_analysis_t411_2026-11-20.md) found that most collected information never reaches a trading decision. Closing that gap is the current build.

---

## The Concept

Most algorithmic trading codebases are built around a single idea: take a signal, size a trade, place an order. ArchonDEX is built around a different premise:

**No single person runs a hedge fund alone.** The best-performing market organizations divide cognitive labor across specialized roles — a researcher, a risk manager, a portfolio manager, a macro analyst, and a performance reviewer — each with strict authority boundaries and clear accountability.

ArchonDEX models this. It decomposes the investment process into **6 independent engines**, each mapped to a real-world market professional, communicating through explicit contracts and never overstepping their mandate. A seventh role, the referee, belongs to no engine: the measurement stack that decides what counts as evidence.

---

## Architecture — The 6-Engine System

```
┌──────────────────────────────────────────────────────────────────────┐
│                        DATA MANAGER (The Librarian)                  │
│         OHLCV • ATR • Fundamentals • Caching • Normalization         │
└──────────────┬──────────────────┬──────────────────┬─────────────────┘
               │                  │                  │
               ▼                  ▼                  ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────────┐
│  ENGINE E        │  │  ENGINE A        │  │  ENGINE B                │
│  Regime Intel    │─▶│  Forecast        │─▶│  Trade Construction      │
│  (Macro Thinker) │  │  (The Researcher)│  │  (The Risk Manager)      │
│                  │  │                  │  │                          │
│  "What kind of   │  │  "What's a good  │  │  "How do we survive if   │
│   market is it?" │  │   opportunity?"  │  │   the researcher is      │
│                  │  │                  │  │   wrong?"                │
└────────┬─────────┘  └────────▲─────────┘  └────────────┬─────────────┘
         │                     │ weights                  │
         │ regime context      │                          ▼
         │                ┌────┴─────────────┐  ┌──────────────────────────┐
         │                │  ENGINE F        │  │  ENGINE C                │
         ▼                │  Strategy        │  │  Portfolio State          │
┌──────────────────┐      │  Governance      │  │  (Accountant + Allocator)│
│  ENGINE D        │      │  (Perf Reviewer) │  │                          │
│  Discovery &     │      │                  │  │  "What do we own and     │
│  Evolution       │─────▶│  "Which edges    │  │   where should capital   │
│  (The Lab)       │edges │   earned trust?" │  │   go?"                   │
│                  │      └──────────────────┘  └──────────────────────────┘
│  "What new edges │
│   can we find?"  │
└──────────────────┘
```

| Engine | Role | Core Question |
|--------|------|---------------|
| **Engine A — Forecast** | The Researcher | *"Given market data, what is the directional forecast and how strongly do I believe it?"* |
| **Engine B — Trade Construction** | The Risk Manager | *"How do we express this trade without risking ruin?"* |
| **Engine C — Portfolio State** | The Accountant + PM | *"What do we actually own, and where should capital be allocated?"* |
| **Engine D — Discovery & Evolution** | The Edge Hunter | *"What new patterns, strategies, and edges can we find?"* |
| **Engine E — Regime Intelligence** | The Macro Thinker | *"What kind of market environment are we operating in?"* |
| **Engine F — Strategy Governance** | The Performance Reviewer | *"Which edges are earning trust, and which should be retired?"* |

### The Golden Rule
> **No engine is allowed to do another engine's job.** A identifies opportunities. B makes them safe. C tracks the books. D grades performance. E reads the weather. If A starts making risk decisions or B starts predicting returns, the system architecture has failed.

---

## How an idea is judged

Every idea goes through the same path, and most stop early.

1. **Census.** What data exists, how many independent observations it holds, and what the idea would be worth if real.
2. **Power check.** The chance the test could pass, computed before any result is seen. A test that cannot pass is closed unrun and costs nothing.
3. **Pre-registration.** The hypothesis, the statistic, the pass conditions and what a failure rules out are frozen in a committed file before the run.
4. **Independent review by execution.** A second agent rebuilds the work from a clean copy, plants defects to see whether the tests catch them, and tries to break the code with hostile inputs.
5. **One run.** Each run is counted against the trial budget, so later results face a higher bar.
6. **Paper, then nothing more until it earns it.** A pass earns a forward paper record, never money.

The non-negotiable rules are in [`CLAUDE.md`](CLAUDE.md) and [`NON_NEGOTIABLES.md`](docs/Core/NON_NEGOTIABLES.md). The most important ones:

- **No bare point estimates.** A risk-adjusted number without a bootstrap interval is not a measurement.
- **Fail closed.** A missing or stale input halts the run. It never produces a plausible number.
- **Nothing is done until its first real output has been read.** Passing tests prove the logic, not the integration.
- **Archive, never delete.** Refuted code and superseded documents are kept.
- **AI is an addition to a working system, never a rescue for a broken one.** The LLM analyst runs on its own account and is held to the same gates.

---

## Key Capabilities

### Research and measurement
- Walk-forward backtesting with a realistic cost model, integer share sizing and cash accounting
- Block-bootstrap confidence intervals, deflated-Sharpe and minimum-backtest-length gates, and a registry that counts every trial
- A multi-gate validation gauntlet for discovered strategies (out-of-sample, robustness, factor decomposition, significance)
- Deterministic runs: the same inputs give byte-identical results, checked nightly

### Signal library (Engine A)
Pluggable "edges" across technical, fundamental, event-driven, statistical and behavioural families, each producing a normalized score. They are research inputs: under the current evidence, none carries real capital.

### Discovery and governance (Engines D and F)
- Feature screening with LightGBM, rule extraction, and genetic search over composite strategies
- Edge lifecycle management (candidate → active → paused → retired) driven by measured performance, not by hand

### Risk and portfolio (Engines B and C)
- Volatility-based position sizing, exposure caps, liquidity filters and a wash-sale guard
- A double-entry ledger that must reconcile against the broker on every run

### Paper-trading operations
- Scheduled daily runs on AWS Batch, with state in S3 and revision-pinned deployments
- Broker reconciliation, corporate-action handling (splits are detected and applied, or the affected position is frozen), heartbeats and alarms
- A fleet health check that reads each account's actual output

### Data archives
- Prices: a multi-decade total-return history with documented seams
- Daily forward archives: Kalshi and Polymarket prices and outcomes, EDGAR filing indexes, short volume and short interest, fails-to-deliver, margin debt, policy-uncertainty indexes, credit spreads
- Each archive has a freshness check that judges whether the values are usable, not just present

---

## Dashboard

A dark-themed Plotly Dash control center (`cockpit/dashboard_v2`) with account summaries, equity and drawdown curves, rolling performance, edge attribution, governance scorecards and market intelligence.

---

## Project Structure

```
archondex/
├── engines/
│   ├── engine_a_alpha/        # Signal generation and edge aggregation
│   ├── engine_b_risk/         # Position sizing, stops, exposure limits
│   ├── engine_c_portfolio/    # Ledger, allocation policies, state
│   ├── engine_d_discovery/    # Strategy search and the validation gauntlet
│   ├── engine_e_regime/       # Market regime detection
│   ├── engine_f_governance/   # Edge lifecycle and performance scoring
│   └── data_manager/          # Price ingestion, caching, normalization
│
├── core/                      # Measurement stack: metrics, bootstrap, gates
├── backtester/                # Walk-forward backtesting
├── paper_trader/              # The daily paper run: reconcile, books, heartbeats
├── intelligence/              # News, filings and the LLM-analyst track
├── cockpit/                   # Dash dashboard (v2)
├── scripts/                   # CLI tools, archivers, research studies
├── config/                    # Universes, settings, the trial registry
├── tests/                     # 5,300+ tests
│
└── docs/
    ├── State/                 # Current truth: state, ledger, health, plan
    ├── Core/                  # Stable design: charters, rules, manual
    ├── Audit/                 # Verdicts and audits, one file per study
    ├── Sources/               # Pre-registrations and design notes
    └── Sessions/              # Per-session summaries
```

---

## Quick Start

### Prerequisites
- Python 3.10+
- [Alpaca Markets](https://alpaca.markets/) account (free, paper trading supported)

### Installation

```bash
# Clone the repository
git clone https://github.com/jmur214/archondex.git
cd archondex

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file at the project root:

```env
APCA_API_KEY_ID=your_alpaca_api_key
APCA_API_SECRET_KEY=your_alpaca_secret_key
APCA_API_BASE_URL=https://paper-api.alpaca.markets
APCA_API_DATA_URL=https://data.alpaca.markets
```

> ⚠️ **Never commit your `.env` file.** It is already listed in `.gitignore`.

### Running the System

```bash
# STEP ONE on a fresh checkout: build the edge registry (data/governor/edges.yml) from the edge
# modules. Importing a module never writes it; this is the one explicit writer, and every run
# refuses an absent or empty registry until it has run once.
python scripts/sync_edge_registry.py

# Run a full backtest with fresh data
python scripts/run_backtest.py --fresh --alpha-debug

# Run system health diagnostics
python -m scripts.run_diagnostics

# Launch the dashboard
python -m cockpit.dashboard_v2.app --port 8050

# Read the paper fleet's health from its real outputs
python -m scripts.fleet_health
```

> For the complete command reference, see [`docs/Core/execution_manual.md`](docs/Core/execution_manual.md).

---

## Documentation

The docs are organized by lifecycle. Start with the navigation index.

| Document | Purpose |
|----------|---------|
| [`docs/README.md`](docs/README.md) | Navigation index |
| [`CURRENT_STATE.md`](docs/State/CURRENT_STATE.md) | What is true right now |
| [`TASK_LEDGER.md`](docs/State/TASK_LEDGER.md) | Every task, its verdict and its trial count |
| [`health_check.md`](docs/State/health_check.md) | Known defects, open and resolved |
| [`GOAL.md`](docs/State/GOAL.md) | The goal and the deployment gate |
| [`forward_plan.md`](docs/State/forward_plan.md) | Strategy and what comes next |
| [`engine_charters.md`](docs/Core/engine_charters.md) | What each engine may and may not do |
| [`NON_NEGOTIABLES.md`](docs/Core/NON_NEGOTIABLES.md) | The rules, with their reasons |
| [`execution_manual.md`](docs/Core/execution_manual.md) | Every CLI command |

---

## How it is built

ArchonDEX is developed by one person directing AI coding agents (Claude Code). A director session plans and decides. Builder agents work in isolated git worktrees. Fresh-context reviewer agents check each piece by running it. Merges go through a gate that runs the full test suite. Decisions about money, risk limits and deployment stay with the human.

---

## Development Philosophy

1. **Divide cognitive labor.** No engine does another engine's job. Boundaries are enforced through explicit contracts.
2. **Try to disprove it first.** An idea is tested to be killed, and the kill is recorded as carefully as a win would be.
3. **Brutal realism over optimism.** Problems are named plainly. A result that looks too good is treated as a defect until shown otherwise.
4. **Archive, never delete.** Institutional memory is preserved, including the mistakes.
5. **The system is the edge.** Signals, risk, costs, taxes and execution are judged together, against a passive benchmark.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Data | Pandas, NumPy, Parquet |
| Broker API | Alpaca Markets (alpaca-py), paper endpoints |
| Cloud | AWS Batch, S3, EventBridge Scheduler, ECR |
| Dashboard | Dash, Plotly |
| ML / Statistics | scikit-learn, LightGBM, SciPy |
| Testing | pytest |

---

## Security

- API credentials are loaded from environment variables and are never committed
- The system uses **paper trading** endpoints; live execution is not enabled
- Outbound requests carry no personal details, except the contact header the SEC requires on its own hosts

---
<p align="center"><i>
The edge isn't in the signal. It's in the system that finds it, sizes it, survives being wrong about it,<br>
and is honest about which signals were never there.
</i></p>

---

<p align="center"><sub>
<b>Disclaimer:</b> This software is for educational and research purposes. It is not financial advice. Trading involves substantial risk of loss. Past performance does not guarantee future results.
</sub></p>
