---
task_id: T-2026-06-10-141
title: After-tax Sharpe GATE (reporting) + Roth/taxable account ROUTER
date: 2026-06-10
substrate: n/a (additive reporting + config/validation; no backtest measurement, zero N_trials)
scope: backtester/cockpit/core/config/tests only — NO engine behavior changes; gate is REPORTING, not enforcement; router is CONFIG+CHECK, not execution
outcome: **Delivered, mostly by REPOINT.** A complete after-tax engine already existed (`backtester/tax_drag_model.py` — FIFO lots, ST/LT, wash-sale, carry-forward) but was unwired into any metric. T-141 added state rates (IL 4.95%), a report-only composition module, three flat summary fields (`after_tax_sharpe_taxable`, `sharpe_roth`, `tax_drag_pct`) + detail block in the single producer (contract suite extended atomically, green), the Roth/taxable router (config + two research rules + 31-day blackout checker stub), and 36 tests. Demonstration on the 2024 6-edge book: **pre-tax Sharpe 0.991 → after-tax (taxable-IL) −0.658; CAGR +5.66% → −13.34%; the $18,934 tax bill EXCEEDS the pre-tax profit** (845 lots, 100% short-term, $27,713 wash-sale-disallowed losses). One pre-existing correctness bug found and fixed: the wash-sale scan was blind to repurchases that never closed.
---

# T-141 — After-tax gate + account router

## Headline

The after-tax number now exists everywhere a performance summary is
written, and it says what the 2026-05-02 measurement said on a
different substrate (0.984 → −0.577): **this book, at this turnover,
is uneconomic after tax in the taxable-IL account even when pre-tax
profitable.** On the canonical 2024 6-edge cell:

|  | Sharpe | 95% block-bootstrap CI | CAGR |
|---|---:|---|---:|
| pre-tax (= Roth) | 0.991 | [−1.310, +3.290] | +5.66% |
| after-tax (taxable-IL) | **−0.658** | [−1.339, +3.238] | **−13.34%** |

`tax_drag_pct` = 335.9% of pre-tax CAGR. $18,934 owed on $54,176 ST
taxable gains — the tax bill exceeds the ~$5.7K profit because the
strategy realizes large gross gains against losses that the wash-sale
rule disallows ($27,713 — systematic re-entries inside 30 days are this
book's normal behavior).

**Honest caveats (also printed by the demo):** (1) the conservative
wash-sale treatment (disallow-forever instead of defer-into-basis)
overstates drag at this turnover; (2) on a 1-year window the whole
annual tax lands as one year-end return observation, so the Sharpe
delta is shape-sensitive — the CAGR drag is the robust number; (3) both
CIs straddle zero (single-year cells are diagnostic, never deployment
evidence — house rule); (4) rates are config-driven planning estimates,
not tax advice. Direction is unambiguous despite all four.

This is REPORTING, not enforcement. Nothing blocks a deploy yet; the
gate criterion ("deploy only if after-tax, portfolio-level edge
survives") is a later user-gated step — T-141 makes the number exist.

## What was found (repoint-over-rebuild)

`backtester/tax_drag_model.py` already implemented the hard 80%: FIFO
lot matching, holding-period classification, wash-sale flagging, yearly
tax with carry-forward, year-end equity debits — shipped 2026-05-02-era,
default-OFF, **wired only into `cost_aggregator`'s C-layer curve and no
metric anywhere**. The capability was buried, not absent. T-141 built
the missing 20%:

1. **State rates** (`state_st_rate`/`state_lt_rate`, default 0.0 =
   bitwise back-compat; config carries IL 0.0495 on BOTH buckets — IL
   taxes capital gains as ordinary income). Effective rates: ST 34.95%,
   LT 19.95%.
2. **`backtester/after_tax_metrics.py`** (NEW) — report-only
   composition: TaxDragModel (a local `enabled=True` COPY — the config's
   `enabled` flag remains the canon-changing equity-mutation switch and
   is deliberately NOT consulted) + MetricsEngine on the adjusted curve.
   Fail-open contract: any precluding input returns the same keys as
   None + `skip_reason`; reporting can never fail a backtest.
3. **Producer fields** in `cockpit/metrics.py::_compute_summary` (the
   single producer — BOTH `performance_summary.json` writers flow
   through `metrics.summary()`): `after_tax_sharpe_taxable`,
   `sharpe_roth` (= pre-tax; Roth carries no drag), `tax_drag_pct`
   (share of pre-tax CAGR consumed; None when pre-tax CAGR ≈ 0 —
   tolerance-guarded), + `after_tax_detail` (full accounting: tax USD,
   ST/LT split, wash-sale disallowed, lot counts, effective rates,
   assumptions list, `tax_rates_source` so a config-read fallback is
   observable, `skip_reason`). Rates load from
   `backtest_settings.json::tax_drag_model` via a repo-root-anchored
   path (env-suffix lesson: this file is not env-suffixed; verified).
4. **Contract suite extended atomically** —
   `tests/test_contracts.py::PRODUCER_SUMMARY_KEYS` + the static scrape
   stay in lockstep; 14 passed + known xfail (layer2b RED tracker).
   Layer-1 does not cover backtest_settings.json (verified), so the new
   config keys are contract-safe.

### Pre-existing bug found & fixed (wash-sale blindness)

`apply_wash_sale_rule` indexed re-opens from REALIZED lots only — a
repurchase still held at run end was invisible to the scan, which is
exactly the case the IRS rule targets, and missing it UNDERSTATES drag
(against the module's own documented conservative intent). Fixed:
`reconstruct_trades` now records every open event
(`self._last_open_events`); the scan prefers that log and falls back to
realized-entries for callers that built trades elsewhere (public API
unchanged). Canon impact: zero (`enabled=false` everywhere); the
C-layer cost curve and this report change only in the
more-losses-disallowed direction (2024 cell: disallowed $25,135 →
$27,713; tax $18,034 → $18,934).

## The router (config + check, not execution)

`core/account_router.py` + `config/account_routing.json`:

- **Schema**: `sleeves.<id> → {account: taxable|roth|either, st_heavy,
  universe[]}` + `rules.cross_account_wash_sale ∈ {disjoint_universes,
  blackout_31d}`.
- **RULE A** (research: ST-heavy doesn't belong in taxable): an
  `st_heavy` sleeve routed to taxable/either violates unless after-tax
  evidence clears — **CI-aware**: `ci_low > 0` clears; a point-estimate
  with no CI only downgrades to a warning (CLAUDE.md kill-threshold
  discipline applied to routing).
- **RULE B** (Rev. Rul. 2008-5 — taxable loss + substantially-identical
  IRA purchase within the window = loss disallowed PERMANENTLY):
  `disjoint_universes` mode statically validates a ticker lives in
  exactly one account's universe; `blackout_31d` mode ships
  `CrossAccountWashSaleChecker` — a backtest-time STUB (records taxable
  losses, answers allowed/blocked for Roth buys inside the 31-day
  window, logs every verdict, **never blocks**). Live enforcement is a
  later user-gated step with the paper-trading milestone (order-path
  wiring = Engine B coordination).
- **Shipped config** routes the current 6-edge core book
  (`st_heavy: true`) to taxable WITHOUT evidence — deliberately: that
  standing RULE A violation IS the deploy-gate signal this task exists
  to surface (asserted in `TestShippedConfig`). The T-120 spot-ETF
  sleeve routes taxable (`st_heavy: false` — slow tilt, harvestable
  losses), per the research allocation rule.

## Tests

36 new (`tests/test_after_tax_t141.py`), all green:
- state-rate arithmetic (0.0 = pre-T-141 back-compat; IL adds per
  bucket; LT bucket; factory defaults; carry-forward × state rates)
- holding-period boundaries (same-day / T+1 / 364 / **365 = LT under
  the model's ≥365 semantics — technically optimistic vs the IRS
  "more than one year"; pre-existing, documented, NOT changed (would
  alter enabled=True results beyond additive scope)** / 366), FIFO lot
  splitting across partial exits, FIFO ordering, wash-sale flag
- report module (ignores `enabled:false`; taxable < roth when gains
  taxed; no-trades ⇒ zero drag; fail-open; JSON-native)
- producer emission (keys present; `summary_metrics()` JSON-round-trips
  — a top-level LIST would break `_to_native` via `pd.isna` truthiness,
  so lists stay nested; verified `pd.isna(dict)` is safe)
- router RULE A ×6, RULE B ×5, blackout checker ×5 (day-30 blocked /
  day-31 allowed boundary), shipped-config validation

Full suite: **2160 passed**; the same 5 failures as T-139's run, all
verified pre-existing on origin/main (stash re-run, 2026-06-10).
Contract suite green.

## What live enforcement needs later (user-gated path)

1. **Gate enforcement**: consume `after_tax_sharpe_taxable` (ci_low
   form) in the deploy-decision path — natural home is the same place
   the DSR/MBL gates live; requires the multi-year after-tax number
   (single-year is shape-distorted; see caveat 2).
2. **Router enforcement**: wire `CrossAccountWashSaleChecker` into the
   order path at the paper-trading milestone (Engine B / live_trader —
   propose-first territory) + feed it realized-loss events from the
   fill stream.
3. **Wash-sale fidelity** (optional): basis-deferral instead of
   disallow-forever would tighten the drag estimate at this turnover —
   only worth it if the gate decision ever becomes marginal (today it
   is not: the book fails by 3×, not by 10%).
4. **Multi-year demo**: re-run `python -m scripts.demo_after_tax_t141
   <run_dir>` on a 12/26-yr run dir when one is on disk — year-end
   debits distribute and the Sharpe delta becomes shape-honest.

## Files

- `backtester/tax_drag_model.py` — state rates + wash-sale open-event fix
- `backtester/after_tax_metrics.py` — NEW; report-only composition
- `cockpit/metrics.py` — `_after_tax_report()` + 4 summary keys
- `config/backtest_settings.json` — IL state rates in `tax_drag_model`
- `core/account_router.py` + `config/account_routing.json` — NEW; router
- `tests/test_after_tax_t141.py` — NEW; 36 tests
- `tests/test_contracts.py` — PRODUCER_SUMMARY_KEYS + comments
- `scripts/demo_after_tax_t141.py` — NEW; the demonstration
- this audit

## NOT done (out of scope)

- Gate ENFORCEMENT (reporting only; criterion lands with user approval)
- Router execution/blocking (stub logs only; paper-trading milestone)
- Basis-deferral wash-sale model (conservative disallowance retained)
- Quarterly estimated-tax cadence (year-end withdrawal only)
- Changing the ≥365-day LT boundary (pre-existing semantics kept)
- Any engine behavior change (verified: backtester/cockpit/core only)
