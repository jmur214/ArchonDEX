# T-176 — the combined-candidate scorecard (base / base+20% DBMF / robo)

**Date:** 2026-06-16
**Agent:** C (branch `feature/combined-candidate-scorecard-t176`)
**Status:** DONE. Reusable scorecard module + runner + contract tests shipped. Data-processing only, no UI, no real-money path. The 20% DBMF is a SIMULATED hold (STOOQ daily returns), never machine-traded. E consumes `build_scorecard()` in the paper scorecard.

---

## 0. What it does
Measures the user's deploy bar (GOAL.md: *beat the Schwab robo, net-of-cost / after-tax, paper-confirmed*). Given any base return series — a **paper** track record OR a **backtest** equity curve — it produces, per robo proxy, a 3-line block:

| line | what |
|---|---|
| `base` | the system alone |
| `base + 20% DBMF` | the REAL candidate (80% base + 20% DBMF managed-futures, SIMULATED hold) |
| `robo:<proxy>` | the benchmark |

Each line reports **Sharpe + block-bootstrap ci_low** (CLAUDE.md `[NN-SHARPE-CI]`, n=1000, seed 0, recomputed from equity per T-090 — never from rounded perf_summary), **MaxDD**, **CAGR**, vol — all **net-of-cost**.

## 1. Pre-registered robo proxy (declared before any result was selected on)
The real target — **Schwab Intelligent Portfolios** — is a ~12-asset-class *target-risk* blend (US + international equity, REITs, fixed income, TIPS, gold/commodities) with a **MANDATORY 6–30% cash allocation** that is Schwab's monetization in lieu of an advisory fee. That cash sleeve is a structural **bull-market return drag** and the single most important thing a naive proxy misses.

Two pre-registered proxies (in `ROBO_PROXIES`), reported together so the reader sees proxy sensitivity:

| proxy | weights | captures | MISSES |
|---|---|---|---|
| `60_40` | 60% SPY / 40% AGG, daily-rebal | equity/bond risk balance | multi-asset diversification AND the cash drag → it has **no cash drag**, so it flatters the robo in bull markets and is the **harder / conservative bar** for us |
| `schwab_like` | 45% SPY / 30% AGG / 5% GLD / 20% cash@rf | multi-asset blend + an **explicit cash drag** → structurally closer to the real robo | international equity / REITs / TIPS (not in our cache → **US-centric proxy**), the exact per-risk-profile cash % (real Schwab 6–30%, glides), Schwab's specific rebalance bands |

**Neither is the real robo.** `60_40` is the conservative bar; `schwab_like` is the structurally-faithful one. The only definitive test is the paper run vs the user's actual Schwab account — which is exactly the deploy gate (GOAL.md).

## 2. Honest cost model (net-of-cost)
- **base** — a backtest equity curve is already net of modeled slippage/commission; a paper series is realized net. No extra deduction.
- **DBMF overlay** — the STOOQ price series embeds DBMF's ~0.85% ER in its NAV → the returns are **already net of the fund's ER**. The 80/20 rebalance cost is charged separately (`rebalance_cost_bps`, default 2bps on turnover, monthly rebalance with realistic inter-rebalance drift — not a costless daily abstraction).
- **robo** — underlying ETF ER netted (`ETF_ER_ANNUAL`); the `_cash` sleeve earns the daily risk-free rate (the cash drag, modeled explicitly).
- **PRE-TAX.** After-tax (Roth vs taxable) is a separate layer (existing tax engine). The deploy bar is after-tax → the consumer applies that on top per account. Roth ⇒ no tax channel; taxable ⇒ the candidate's lower turnover/MaxDD matters more.

## 3. Apples-to-apples windowing (the one non-obvious design choice)
DBMF inception is 2019-05; `GLD_1d.csv` in our cache only starts **2020-04-13**. A single shared window would let GLD truncate everything and **throw away the COVID crash** — the most important crisis test for a managed-futures diversifier — for no candidate-related reason. So the scorecard emits **one self-consistent block per proxy**: each block is aligned to `base ∩ combined ∩ that-proxy`. `60_40` keeps the full 2019-05→2025 window (COVID included); `schwab_like` runs 2020-04→2025. Inside a block all three rows share one window. Windows are stamped per block.

## 4. Sample run (the v1 26yr prod base, restricted to the DBMF era)
`python -m scripts.run_combined_scorecard --snapshots <portfolio_snapshots.csv>`

**vs robo:60_40  (window 2019-05-13 .. 2025-12-31, COVID included)**

| candidate | Sharpe | ci_low | MaxDD% | CAGR% | vol% | days |
|---|---|---|---|---|---|---|
| base | 0.830 | 0.030 | −7.45 | 9.56 | 6.43 | 1669 |
| base + 20% DBMF | 0.762 | 0.013 | −5.65 | 8.66 | 5.89 | 1669 |
| robo:60_40 | 0.426 | −0.273 | −21.78 | 8.98 | 12.71 | 1669 |

→ candidate **BEATS** 60_40: Sharpe 0.762 vs 0.426; MaxDD −5.7% vs −21.8%. The candidate is the only line with a non-negative Sharpe ci_low.

**vs robo:schwab_like  (window 2020-04-13 .. 2025-12-31, no COVID)**

| candidate | Sharpe | ci_low | MaxDD% | CAGR% | vol% | days |
|---|---|---|---|---|---|---|
| base | 0.633 | −0.262 | −7.45 | 8.02 | 6.17 | 1438 |
| base + 20% DBMF | 0.578 | −0.210 | −5.65 | 7.33 | 5.58 | 1438 |
| robo:schwab_like | 0.606 | −0.135 | −15.99 | 9.22 | 8.55 | 1438 |

→ candidate **TRAILS** schwab_like on Sharpe (0.578 vs 0.606) in this benign cash-drag-friendly sub-window, but at **far smaller MaxDD (−5.7% vs −16.0%)**.

### Reads
- **The 20% DBMF overlay behaves as a crisis diversifier should:** it cuts MaxDD (−7.45%→−5.65%) and vol, at a small Sharpe/CAGR cost in a bull-heavy window. That is the diversifier trade-off, measured — not asserted.
- **The candidate clears the conservative (60_40) bar comfortably** and is the only candidate with ci_low ≥ 0 over the COVID-inclusive window. Against the cash-drag-heavy `schwab_like` proxy it edges below on Sharpe in a benign window but dominates on drawdown.
- **CAVEAT — this is a backtest sub-window, not paper, and it is short (~6.5yr / 1669 days).** None of these ci_lows clear DSR/MBL at this length; the base here is the 2019–2025 *slice* of the v1 26yr book (Sharpe 0.83 in-slice vs the full-cycle 0.751). The number that counts is the paper run vs the real Schwab account. This audit demonstrates the **tool**, not a deploy verdict.

## 5. Files
- `core/combined_candidate_scorecard.py` — logic (loaders, `combine_fixed_weight`, `robo_proxy_returns`, `score`, `build_scorecard`); data-processing only.
- `scripts/run_combined_scorecard.py` — thin runner, callable on `--snapshots` (backtest) or `--series` (paper), `--json` for E.
- `tests/test_combined_candidate_scorecard.py` — 8 contract tests (deterministic synthetic, no network), all green.
- Reuses `MetricsEngine` (sharpe/bootstrap/max_drawdown) and the `analyze_t118r.py` snapshot→metrics pattern. DBMF from the STOOQ cache (no yfinance fetch needed — already on disk).

## 6. For E
`from core.combined_candidate_scorecard import build_scorecard` → `build_scorecard(paper_equity_or_returns)` returns `{proxy: [base_row, combined_row, robo_row]}`. `rows_to_dicts()` for JSON. Apply the after-tax layer per account on top (Roth-first per CURRENT_STATE). No prod change; branch push only — director merges.
