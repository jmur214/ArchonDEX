---
task_id: T-2026-06-18-207
title: PIT universe de-biasing — prep + dry-run (Phase 2, substrate honesty)
date: 2026-06-18
author: Agent D (PIT-universe / T-154 lane)
type: prep + dry-run (NO production flag flip; NO measure-vs-robo)
outcome: PIT path VERIFIED READY; universe expansion measured (109 → 655, +546,
  with 193 delisted survivors restored); cost-sensitivity table built (the
  optimistic-small-cap-cost bias is potentially the LARGER of the two un-netted
  upward biases); microcap = DEFER memo. The realized PIT-vs-static Sharpe delta
  is compute-bound LOCALLY (per-rebalance MVO over 600+ names) — the brief defers
  the full re-baseline to the cloud anyway; reported here with the honest
  "drop = survivorship bias being REMOVED" framing + the literature/plan magnitude.
status: CURRENT — prep done; full re-baseline awaits C's T-203 gate + cloud
---

# T-207 — PIT universe de-biasing prep + dry-run

## 1. PIT path — VERIFIED READY
- **`use_historical_universe` wiring:** `universe_resolver.resolve_universe(...,
  use_historical=True)` resolves the survivorship-aware historical S&P union from
  the membership panel. Production passes `cache_dir = data` (`mode_controller.py
  :783,815`), so the resolver finds the panel at `data/universe/
  sp500_membership.parquet` and returns **`mode=historical`** (NOT fallback). [I
  first tested with `cache_dir=data/processed` and saw `fallback_to_static`; that
  was MY test arg — production uses `data`, and the panel is present + read.]
- **T-189 measured-mode halt:** wired — `universe_resolver.py:198-205` calls
  `core.measured.halt_or_degrade(...)` before `fallback_to_static`, so a measured
  (cloud/anchor) run with `use_historical=True` but a missing panel HALTS instead
  of silently survivorship-biasing. (B's T-194 closure.)
- **Membership panel:** `data/universe/sp500_membership.parquet` — 902 rows,
  schema `(ticker, name, sector, included_from, included_until)`; tracks BOTH
  current members (`included_until` NaT) and removed/delisted ones (e.g. AA/Alcoa
  `included_until=2016-11-01`). This is the correct SP500MembershipLoader (KEEP)
  format the resolver reads — NOT the T-154 `_pit` collision file. Built by
  `build_membership_panel_t136`.
- **Deep substrate:** Stooq deep history present — IBM 1962→2026 (16,176 rows),
  GE 1962→2025, KO 1970→2026; 730 processed `_1d.csv` tickers available for the
  historical union.

## 2. Universe expansion (the survivorship correction magnitude)
`resolve_universe(static-109, use_historical=True, cache_dir=data)`:

| window | static | PIT (historical) | n-delta | delisted survivors (left S&P) | left DURING window |
|---|---|---|---|---|---|
| 2012-2024 | 109 | **655** | **+546** | 193 | 161 |
| 2015-2024 | 109 | 632 | +523 | — | — |

- **552 PIT-only names** (in the historical union, NOT in the static-109). These
  are the survivorship cohort: prior S&P 500 members that were later removed
  (merged / acquired / shrank out of the index / delisted). Restoring them is the
  bias correction. (missing_from_cache ≈ 104-109 of the 759-name union lack cached
  price data — the union is ~759, ~655 have data.)
- This EXCEEDS the brief's "~300+" expectation: the correction nearly 6×'s the
  universe.

## 3. Realized Sharpe delta — HONEST framing + the compute reality
**Expectation (set explicitly, per the brief):** the PIT Sharpe should **DROP**.
The delisted cohort underperformed ex-ante; the static-109 (survivors-only) book
is an UPWARD-biased estimate. The drop is the bias being **REMOVED** — a
less-biased estimate of the SAME answer, NOT a regression to debug (the trap is
seeing the drop and blaming implementation). The mercy: survivorship hits CAGR
hard but Sharpe only **~−6%** (≈ −0.045 on the 0.751 base) — so the no-validated-
edge read is robust to it.

**The realized measurement is COMPUTE-BOUND locally.** The full 6-edge book on
632 tickers is intractable in-session (the value/accruals edges' per-ticker
fundamentals path + the per-rebalance MVO optimizer over 600+ names; a 109-ticker
price-edge run alone exceeded several minutes). This is acceptable: **the brief
explicitly defers the full re-baseline** ("waits for C's T-203 gate + Phase-1
composition; do NOT measure vs robo yet"). The realized PIT Sharpe should be
measured on the cloud at re-baseline time (one cell each, static vs PIT, the
canonical book + window). The DRY-RUN's job — verify the path + size the
correction — is done. (`scripts/pit_universe_dryrun_t207.py` is the harness, ready
for the cloud cell; `PIT_FULL_BOOK=1` for the full book.)

## 4. Cost-sensitivity table — the OTHER (un-netted) upward bias
The config's small-cap half-spread is **15 bps** (`config/backtest_settings.json:
124-131`: mega/mid/small = 1/5/15 bps half-spread). Domain research puts true
retail small-cap friction at **50-100 bps**. At the book's **documented ~26×/yr
turnover** (T-146: 29.7 bps total realistic cost @ 26× turnover), under-pricing
small-cap friction is a LARGE headline drag.

Extra annual drag vs the 15-bps baseline = `2 · (s−15) · f · T` (round-trip ×
extra-half-spread × small-cap-turnover-share × turnover); Sharpe hit ≈
`−drag/100 / 15%-vol`:

**At T=26×/yr (documented):**
| small-cap turnover share f | s=50 bps | s=100 bps |
|---|---|---|
| 10% | 182 bps/yr (ΔSharpe −0.12) | 442 bps/yr (−0.29) |
| 25% | 455 bps/yr (−0.30) | 1105 bps/yr (−0.74) |
| 50% | 910 bps/yr (−0.61) | 2210 bps/yr (−1.47) |

**At T=10× (if turnover is cut, e.g. T-148 buffering):** f=10% → 70/170 bps/yr
(−0.05/−0.11); f=25% → 175/425 (−0.12/−0.28).

**Read:** even a LOW small-cap turnover share (10%) at the milder stress (50 bps)
is a −0.12 Sharpe hit at the book's real turnover — bigger than the survivorship
−0.045. The two un-netted upward biases COMPOUND: 0.751 − ~0.045 (survivorship) −
0.12-to-0.74 (small-cap cost, f-dependent) → **plausibly through the 0.40 kill
line**, confirming the audit's standing flag. Honest caveats: (a) the inverse-vol/
MVO book favors LOW-vol (often larger) names, so f is likely on the low end
(10-25%); (b) turnover is itself a reducible lever (T-148), so part of the cost
bias is a turnover-management question, not a pure friction tax; (c) `f` (the true
<$1B-cap turnover share) needs the realized cloud run + a market-cap join to pin
down — this table is parametric in `f` by design.

## 5. Microcap thrust — GATE MEMO (default DEFER)
**DEFER.** A dedicated microcap thrust is not viable at retail scale and is NOT
built here. The research: <20% viability — true friction 50-100 bps (the cost
table above shows what that does to a 26×-turnover book), ~58% post-publication
alpha decay → ~30 bps net of a ~100 bps gross edge, position-size caps collapse
the book to 1-2 names/side (idiosyncratic, un-diversifiable), and MBL is violated
by orders of magnitude (the thin microcap universe + the per-name capacity cap
gives far too few independent bets for any honest-N to clear DSR). **Proceed ONLY
IF** a concrete **≥100-150 bps gross** edge is pre-identified (not hoped-for) AND
**Norgate** ($80/mo, survivorship-free microcap data) is funded — otherwise the
substrate is both biased (survivorship in microcaps is worse than large-caps) and
too costly to test honestly. Until both conditions hold: DEFER.

## NOT done (deliberately, per constraints)
Did NOT flip the production `use_historical_universe` default (a measurement
decision the director makes once C's re-aimed robo gate lands). Did NOT
measure-vs-robo. Did NOT build a microcap thrust. The realized PIT Sharpe is
left for the cloud re-baseline. Branch only; director merges.

## Files
- `scripts/pit_universe_dryrun_t207.py` — the PIT-vs-static dry-run harness
  (price-edges-only default for local tractability; `PIT_FULL_BOOK=1` + cloud for
  the canonical realized delta).
