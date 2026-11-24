<p align="center">
  <img src="https://img.shields.io/badge/Status-Research_%2B_Paper_Trading-blue.svg" alt="Status">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Broker-Alpaca_(paper)-FFDC00.svg" alt="Broker">
  <img src="https://img.shields.io/badge/Architecture-6_Engine_Quant_System-00C853.svg" alt="Architecture">
  <img src="https://img.shields.io/badge/Tests-5%2C600%2B_passing-brightgreen.svg" alt="Tests">
  <img src="https://img.shields.io/badge/Capital-paper_only-lightgrey.svg" alt="Capital">
</p>

# ArchonDEX

**An autonomous quant research lab and paper-trading system, built like a small trading firm.** Six engines with separate jobs find, size, track and govern strategies. A measurement stack built to be hard to fool decides which ones are real. A fleet of cloud paper accounts trades every market day and checks itself against the broker.

> **This is not a script that runs a strategy.** It is a system that discovers strategies, tries to disprove them, runs the survivors on paper, and keeps a public record of every result.

| | |
|---|---|
| **2,600+** commits over 13 months | **5,600+** automated tests gate every merge |
| **~300** logged research tasks, each with a verdict | **3** paper accounts trading daily on AWS |
| **45** strategy ideas tested and refuted on the record | **100 years** of market data behind the longest studies |

## What makes it different

**It holds itself to an institutional evidence bar.** Every result needs a block-bootstrap confidence interval, and decisions read the interval's lower bound, not the headline number. The bar rises with every backtest ever run on the same data (about 370 effective trials so far), so the system cannot fool itself by trying many things.

**Ideas are pre-registered and reviewed by execution.** The hypothesis, the statistic and the pass conditions are frozen in a committed file before a test runs. A second AI agent then rebuilds the work from a clean copy, plants defects to see whether the tests catch them, and attacks the code with hostile inputs.

**The paper fleet proves the plumbing every day.** Each account reconciles its books against the broker on every run and fails loudly if it cannot explain a position. It handles stock splits, saves its order journal before anything slow, and reports which information sources each decision step actually read.

**It publishes what did not work.** No strategy has yet earned real capital under this bar, so none trades real money. The [task ledger](docs/State/TASK_LEDGER.md), the [verdicts](docs/Audit/) and the [open-defect log](docs/State/health_check.md) are all in this repo. A null result here has been measured and recorded.

### What the research has established

- **Most retail-accessible signals do not survive honest testing.** Momentum and factor tilts, small-cap momentum, insider-filing signals, filing-text changes, closed-end-fund discounts, levered-ETF stacks, gold overlays, put-writing and regime timing were each tested and refuted. Every verdict is in [`docs/Audit/`](docs/Audit/).
- **Short backtests cannot see small edges.** At the corrected bar, a real 2%-a-year edge passes a 26-year backtest only about 3% of the time ([audit](docs/Audit/fresh_eyes_and_salvage_audits_2026-11-14.md)). The research now targets per-event designs, century-long data and structural decisions such as costs and taxes.
- **Measurement is the hardest part.** Several early "wins" were measurement defects: capital sized twice, a significance test whose null was a point mass, survivorship holes in the price history. Each fix is locked by a test that fails if the defect returns.
- **Good forecasts are not always tradeable.** Prediction markets forecast inflation and Fed decisions well, but stocks and bonds price the same information before a daily strategy can act.
- **Information has to reach decisions.** A [code-level audit](docs/Audit/trade_desk_gap_analysis_t411_2026-11-20.md) traced every data source to the decision it feeds. Wiring the collected information into desk-style decisions is the current build.

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
Pluggable "edges" across technical, fundamental, event-driven, statistical and behavioural families, each producing a normalized score. They are research inputs, and each must pass the evidence bar before it carries capital.

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
├── tests/                     # 5,600+ tests
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
