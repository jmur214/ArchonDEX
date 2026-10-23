# Session Summary: 2026-10-22 — Agent D, the L4 integer-share unit (Engine B)

## What was worked on

- **L4 (item (d) scan, `docs/Sources/scan_price_level_consumers_item_d_2026_10_15.md`):** share
  counts were computed from the TOTAL-RETURN close (`int(delta_notional / price)` at Engine B Path A,
  `max_qty_by_value` on Path B, the optimizer's parity baseline), so deep-history backtests bought
  more "shares" per dollar than the print allowed (SPY 2000: 1.6×; the DAL $4,000 case: 4 units where
  2 shares traded). Built on branch `worktree-agent-ac8cc62048d036de9` in an isolated worktree;
  user-approved 2026-10-22 (the propose-first gate), R-reviewed before merge.
- ONE helper, `core/share_sizing.py`: `trunc_shares` (the arithmetic, vectorised), `size_shares`
  (dollars → units, Path A), `size_units` (units → units, Path B), `size_real_shares` (a 1-share
  probe, an ADV clip), `read_close_unadj` (the one reader; halts a measured run on a hole),
  `share_price_basis_summary` (the census record). Engine B's Path A, Path B, both probes and the
  ADV clip read it; the ADV check runs on real shares where known.
- The census field `share_price_basis` (`{"basis", "counts", "n_sized"}`) is written by BOTH
  producers (`_build_census` from `RiskEngine.share_price_basis_counts`; `candidate_census_block`
  from the counter carried on `PureBacktestResult`), named in `CENSUS_PROVENANCE_KEYS`,
  `CENSUS_GATING_KEYS` and the producer map; `assert_census` fails an errored record, warns when
  the record is absent, never judges the value.
- Engine C: `naive_rounded_positions` reads the helper (parity by construction);
  `optimize_integer_positions` takes `prices_unadj` and REFUSES the real-share lattice (measured:
  `MeasurementHalt`; otherwise pass-through, `skip_reason = unadjusted_basis_lattice_unsupported`);
  `portfolio_engine` passes the bars' `close_unadj` through the same reader. The flag is OFF in prod.

## What was decided

- **The ledger-unit carry.** The ruling reads "size on split-only price as the shares that actually
  traded, then value at the adjusted price". Carrying the real count AS the ledger qty and marking
  it at the adjusted Close deploys only `close_unadj/Close` of the ticket (SPY 2000: 71 shares ×
  $87.5 = $6,212 of a $10,000 ticket; the rest sits in cash) — a yield-correlated under-investment
  larger than the truncation defect. The ledger (`Position.qty`, every mark, fill at the adjusted
  next-bar Open, cash) is in adjusted units, so the consistent form is: `shares_traded = trunc(
  notional / close_unadj)` (the integer constraint reality imposes), `qty = trunc(shares_traded ×
  close_unadj / Close)` (their value, in units) — `qty × Close == shares_traded × close_unadj` to
  within one unit. The order meta carries `shares_traded`, `close_unadj`, `share_price_basis`; the
  trades canon drops the meta column, so no canon md5 moves. **The director/user can overrule to the
  literal reading with a one-line change in `trunc_shares` (return `shares` as the units) and the
  second assertion of lock 1.**
- **Pre-cutover: byte-identical.** With no `close_unadj` column the count is `int(notional /
  Close)` exactly (20k random inputs, lock 7) and the basis is RECORDED `total_return` — a census
  fact, not a failure, in measured runs too, until the cutover lands (stated in the helper's
  docstring and the census docstring). A PRESENT column with a NaN/non-positive bar is a hole in a
  declared load-bearing input: measured → halt; otherwise recorded `unadjusted_nan`.
- **An unmeasured basis is an error record.** `share_price_basis_summary(None)` → `{"error": …}`
  → the gate refuses; the three fixtures that hand-build a census, a controller stub, or a candidate
  block now carry the field, as a real run leaves it.
- **The optimizer refuses rather than walks the wrong lattice.** Its lattice is adjusted units; the
  real-share lattice has a fractional prior (DRIP), a redesign beyond this unit (Engine C, flagged).
- `[NN-FP-GUARDS]`-class tolerance on the unadjusted path only: `(k × Close) / Close` is not always
  `k` — measured 5.4 % of random `(k, p)` pairs truncate to `k − 1` — so the unadjusted path nudges
  `1e-9` share toward the trade direction; the total-return path carries NO tolerance (byte-identity).

## What was learned

- `risk_engine.py` defines `prepare_order` TWICE (a dead placeholder stub at `:363`; the live method
  at `:673`). An AST lock that takes the first definition reads the stub. LOW row added.
- Path A's forced 1-share probe turns a sub-share TRIM into a one-share BUY (pre-existing; LOW row).
- Harness worktrees carry no `data/` directory: `data/governor/edges.yml`-class contract tests and
  the data-depth tests fail environmentally at base. Per the coordinator: uncommitted symlinks for
  `data/{processed,logs,macro,universe,research,observability,trade_logs}` → the main tree, and an
  empty REAL `data/state`; planted price files live in pytest tmp dirs only.
- `DataManager._normalize_df` preserves unknown columns, so `close_unadj` survives the loader
  unchanged (proven by lock 1 through `load_cached`).

## Reversion proofs (each lock failed on the reverted line; restored by byte copy; passed again)

| lock | reverted line | reverted | restored |
|---|---|---|---|
| L1 | `trunc_shares`: `have = … & False` | 2 failed | 2 passed |
| L1-B | Path B `size_units(…, price, None)` | 1 failed | 1 passed |
| L2 | `read_close_unadj`: absent column → `float(row["Close"])` | 1 failed | 1 passed |
| L2b | the `halt_or_degrade` call removed | 1 failed | 1 passed |
| L3a | `_build_census` no longer assigns the key | 2 failed | 2 passed |
| L3b | candidate block writes a hard-coded record | 1 failed | 1 passed |
| L3c | the pure result stops carrying the counter | 1 failed | 1 passed |
| L4 | `add_qty = int(delta_notional / price)` restored | 2 failed | 2 passed |
| L4b | the optimizer's own `np.trunc` restored | 2 failed | 2 passed |
| L4c | the optimizer's refusal removed | 1 failed | 1 passed |
| L5 | `from core.share_sizing import size_shares` planted in `paper_trader/order_construction.py` | 1 failed | 1 passed |
| L7 | total-return path `np.round` | 1 failed | 1 passed |

## The full suite (worktree, with the coordinator's data/ symlinks)

`python -m pytest tests/ -q -p no:cacheprovider` on the final tree: **18 failed, 4389 passed,
32 skipped, 5 deselected, 11 xfailed in 2:32** (`doc_lint.py` exit 0). The 18 are all data-bound
in this worktree and name no file this unit touched: `tests/test_combined_candidate_scorecard.py`
×11 and `tests/test_phase1_composition.py` ×3 (`FileNotFoundError: data/raw/stooq/...` — not in the
symlink list); `tests/test_contracts.py::test_layer3a_capability_ledger_source_lines_in_range` and
`tests/test_edge_weight_keys_rr7.py` ×2 (they read `data/governor/edges.yml`, which an import-time
registry writer regenerated here at 309 lines; the ledger cites `:1755`/`:1778` of the real file —
`data/governor` is a WRITE target and was deliberately not symlinked); and
`tests/test_composite_edge_macro_earnings.py::test_calc_earnings_aapl_returns_float`
(`data/earnings/` not symlinked). The log holds zero mentions of `share_price_basis` or
`DiscoveryCandidateCensusError` on the final run. The first full run had 20 more failures — the
Discovery-gate tests' four stubs of `run_backtest_pure` lacked the new counter, so the candidate
census refused them; the stubs were made faithful (`b656fab`), the guard kept.

## Follow-ups after the reviewer's APPROVE at `949a585` (same night; commits on top, never amended)

- The reviewer approved by execution: the ruled form on a planted ex-date file (69 real shares
  carried as 110 units, 98.3 % deployed vs 61.7 % under the literal form); byte-identical trade logs
  vs main without the column; both producers; the optimizer paths; paper_trader unchanged by AST.
- **(1) ADV lock.** The reviewer's reversion R5 (the liquidity check back on units) survived the
  suite: correct behaviour, unlocked. Two locks added — the check runs on real shares (71 pass an
  80-share limit where 113 units would clip) and the clip is in real shares carried as units (10
  shares → 16 units); both reversion-proven (check on `add_qty`: 1 failed / 1 passed; clip
  `add_qty = limit_qty`: 1 failed / 1 passed).
- **(2) HIGH row, anchored:** `_fail("non_positive_risk_budget")` at `risk_engine.py:1287` has no
  `return` — Path B with a zero budget (`risk_per_trade_pct 0`, or a killed edge's
  `governor_weight 0.0`) emits `{side: long, qty: 1, forced_min_qty: True}` while the skip channel
  says rejected. When the fleet reaches Path B is stated in the row (only through gaps in the
  policy's weight dict; the sleeve passes target weights on every call). NOT fixed: Engine B
  outside the L4 approval; the one-line fix is named for the user.
- **(3) trim→buy re-rated MEDIUM** on the reviewer's evidence (Close 630, hold 2, target 1 % →
  delta −260 → LONG 1 with no meta marker; 2 → 3 → 2 → 3 across bars — a one-share round trip every
  two bars on the production path); moved into the MEDIUM region.
- **Record:** no writer lands `close_unadj` yet; the cutover unit must write that exact column name
  (`core.share_sizing.CLOSE_UNADJ_COLUMN`).
- **Suite layout corrected per the coordinator:** a plain `data/processed` symlink lets a suite
  write into the main tree's pinned cache. Replaced by a REAL `data/processed/` holding 730
  per-file symlinks to the main tree's `*_1d.csv`, a `tr_reconciled` symlink and an EMPTY real
  `parquet/`; the full suite re-run on that layout (line below).

## Pick up next time

- R's review; merge only with the full suite green (the known environmental rows named in the
  report). On cutover day the field flips to `unadjusted` by itself when the writer lands
  `close_unadj`; the first canonical run's `share_price_basis` is the field's first artifact.
- Engine C follow-up (not this unit): rebuild the dynamic optimizer's walk on the real-share lattice
  (prior in units, trades in integer real shares) before enabling it on the new substrate.
- Engine B propose-first items from the LOW rows: archive the dead `prepare_order` stub; rule the
  forced-probe trim→buy flip after measuring its frequency.

## Files touched

```
backtester/backtest_controller.py
core/census.py
core/share_sizing.py
docs/Sessions/2026-10/2026-10-22_session_agent_l4_share_sizing.md
docs/State/health_check.md
engines/engine_b_risk/risk_engine.py
engines/engine_c_portfolio/dynamic_optimizer.py
engines/engine_c_portfolio/portfolio_engine.py
engines/engine_d_discovery/discovery.py
orchestration/run_backtest_pure.py
tests/test_census.py
tests/test_census_fail_closed.py
tests/test_contracts.py
tests/test_discovery_gate_remediation.py
tests/test_discovery_gates_7_8.py
tests/test_gate1_candidate_census_t347.py
tests/test_rr6a_gate_verdicts.py
tests/test_share_sizing_l4_2026_10_22.py
(scripts/sync_docs.py run; the engine index.md files were already in sync)
```

## Subagents invoked

None — the unit was built directly in the isolated worktree.
