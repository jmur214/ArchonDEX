---
task_id: T-383 (B-6)
title: B-6 Lazy Prices — verdict (S&P arm section; T-265 arm pending its census and freeze)
date: 2026-11-12
author: ml-architect subagent (director-dispatched)
outcome: "S&P ARM: NOT EVALUATED — the frozen fail-closed census HALTED (exit 2) before any return; 13 of 40 gate rebalances below the 80%-of-members floor (min 67.9%). No return computed. T-265 arm: stream running, not frozen."
status: S&P arm HALTED AT CENSUS — awaiting the director's ruling (prereg AMENDMENT 1, A1.11 options i–iv). Nothing quoted; no N_trials consumed (the arm did not run).
reproduce: "python -m scripts.lazy_prices.b6_harness_sp --census-only --spec gate_similarity --out data/b6_local/harness_sp/census_run1  # exit 2; census CSV md5 c3effa85be82e4f5941051cd97dac980 (x2)"
---

# B-6 Lazy Prices — verdict

Pre-registration: `docs/Sources/prereg_b6_lazy_prices_2026-11-11.md` (draft + AMENDMENT 1, committed
alone at `fc28a7d` before any return). Harness: `scripts/lazy_prices/b6_harness_sp.py` (standalone,
never `BacktestController`; locks `tests/test_b6_harness_sp.py`).

## S&P arm — NOT EVALUATED: the frozen census halted before any return

**What ran.** The harness built the 40 gate rebalances (2016-03-31 → 2025-12-31) from the text
signals (R6: 10-K combo, 10-Q MD&A; latest filing with `decision_floor_date` ≤ t, accepted within 6
months) and the declared price source (R1 (d): T-265 Alpaca TR bars by CIK; `data/processed` fill
only from 2020-06-30), then ran the frozen fail-closed checks (§7.7, §11) BEFORE touching any return.

**What it found.** §11's floor — ranked names ≥ 80% of the PIT members with a CIK — fails in **13 of
40 quarters**, for both signals (similarity and Δtone):

| rebalance | ranked share | | rebalance | ranked share |
|---|---|---|---|---|
| 2016-03-31 | **0.679** | | 2017-12-29 | 0.778 |
| 2016-06-30 | 0.741 | | 2018-03-29 | 0.742 |
| 2016-09-30 | 0.747 | | 2018-09-28 | 0.792 |
| 2016-12-30 | 0.753 | | 2018-12-31 | 0.795 |
| 2017-03-31 | 0.724 | | 2019-03-29 | 0.761 |
| 2017-06-30 | 0.767 | | 2020-03-31 | 0.782 |
| 2017-09-29 | 0.772 | | | |

Every other gate condition holds (ranked names ≥ 338 every quarter; terciles ≥ 112). From 2020-06-30
every quarter clears (87–97%). The (c) sensitivity's census (2020-06-30 → 2025-12-31, `data/processed`)
PASSES — and was deliberately NOT run for returns: a sensitivity result seen before the director rules
on the gate would be a forking path.

**Why.** T-265 holds no bars for 14–20% of S&P members in 2016–2019 — acquired or failed names (AET,
ANDV, ATVI, CELG, RHT, TWX, MON …), the survivorship hole B-2 §3.1 documented. A ticker-based join does
not recover them (the bars do not exist; 17 quarters fail that way). Text coverage is not the
constraint (86–97% of members carry a usable signal every quarter).

**Determinism.** The census ran twice: identical md5 (`c3effa85be82e4f5941051cd97dac980` for the
census CSV, `8f80dc57c89739fbae9ea976c86fe1e2` for the HALT list), exit 2 both times.

**Consequence.** No return, no smoke on real data, no headline, no N_trials consumed. The director
rules among A1.11's options: (i) keep the rule — the S&P arm is NOT EVALUABLE on (d); (ii) lower the
floor for 2016-Q1 → 2020-Q1 under the asymmetric survivorship rule; (iii) make (c) the gate (5.75 yr,
MinBTL SR ≈ 0.90) with (d) a diagnostic; (iv) wait for price data that closes the hole (B-2's measured
one-time Alpaca SIP fetch of dead symbols, or the T-384 cutover).

## T-265 arm — pending
The signals-only stream restarted 2026-11-12 19:48 UTC (R8). Its census and freeze follow its
completion; nothing has been run.
