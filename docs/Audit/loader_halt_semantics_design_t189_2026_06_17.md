---
task_id: T-2026-06-17-189
title: Loader HALT-semantics — measured-mode fail-closed at the data-load SOURCE (Phase-2 design)
date: 2026-06-17
author: Agent D (alpha/edge + Discovery lane)
type: DESIGN / propose-first (spans the data path feeding A/C/E; NO code shipped)
headline: Close the silent-fail-open disease (T-088/T-167/T-171/T-175/T-177) at the
  SOURCE. Today the loaders turn "missing load-bearing input" into a plausible
  number (abstain-to-zeros / None / static-fallback / partial panel). T-181's
  census already CATCHES this post-run (marks the run non-canonical); this design
  adds the fail-FAST complement: in an explicit MEASURED mode, a missing
  load-bearing input for an ACTIVE edge/overlay/allocator HALTS at the load site
  (exits non-zero) — while OUTSIDE measured mode (offline/paper/test) the existing
  graceful degradation stays but stamps `degraded=True`/`skip_reason` that the
  census treats as FAIL. One predicate, one helper, one exception; reuse T-181's
  degraded plumbing. Recommended first sites: simfin/fundamentals (the still-open
  T-175 0.751), universe_resolver fallback (T-167), macro→regime (T-164 GAP-2).
status: DESIGN — awaiting director + user review (propose-first)
---

# T-189 — loader HALT-semantics design

## 0. Why HALT at the source when T-181's census already gates post-run?
T-181 (`core/census.py`, merged) writes a `census` block + marks a run
NON-CANONICAL if any of 6 invariants fail (edges_blind, universe-shrink,
n_trades, fundamentals/macro/regime, zero-unaligned, config_provenance). That is
an **outcome gate**: the run completes, then is flagged. HALT-at-source is the
**fail-fast complement**: the run **exits at the exact load site** the instant a
load-bearing input is missing in a measured run. Value of adding HALT on top of
census:
- **Fails faster + cheaper** — no multi-hour cloud backtest that's non-canonical
  anyway; the failure fires in the first seconds at the loader.
- **Names the exact site** — "simfin panel absent for active value edges" beats a
  post-hoc `fundamentals_blind>0` census flag.
- **Defense-in-depth** — census can be bypassed (a caller that doesn't call
  `assert_census`); a source HALT cannot be silently skipped.
**Design principle: HALT and census share the SAME `degraded`/`skip_reason`
vocabulary** — a degraded (non-measured) run still trips the census; a measured
run halts before census. No new gate semantics, just an earlier trip-wire.

## 1. Inventory — silent-degradation sites in the data-load path
(file:line, current behavior on missing input, consumer that goes blind,
silent?/logged?, existing guard. From the T-189 code sweep.)

| # | Site (file:line) | On missing input | Consumer blinded | Silent? | Guard today |
|---|---|---|---|---|---|
| A | `data_manager._fetch_yfinance:68` | hermetic_block → empty df | ensure_data | logged | ✅ hermetic |
| B | `data_manager.fetch_historical_fundamentals:233` | hermetic_block → empty; `:246` empty income → empty | value edge → 0.0 | partly silent (`:246`) | ✅ hermetic (net only) |
| C | `data_manager.load_cached:635` | cache miss → None | ensure_data → network | silent | ❌ |
| D | `data_manager.ensure_data:843-851` | fetch exhausted → empty df/ticker | edges → 0.0 | LOUD `[FETCH-FAIL]` | ❌ |
| E | `data_manager._normalize_df:550-554` | 20× band drop rows (T-167) | overlay/regression window | logged (T-181 `[BAND_DROP]`) | ❌ |
| F | `simfin_adapter._ensure_simfin_configured:35-43` | no `SIMFIN_API_KEY` → **RAISES even for cached read** | whole panel | LOUD (wrong trigger) | ❌ (raises on fetch-cfg, not on data-missing) |
| G | `_fundamentals_helpers.get_panel:86-92` | any load error → **None (silent swallow)** | 4 value/accruals edges | **SILENT** | ❌ |
| H | `_fundamentals_helpers.top_quintile_long_signals:283-286` | panel None → `{t:0.0}` | 4 edges abstain | SILENT | ❌ |
| I | `macro_data.load_cached:224-225` | parquet missing → empty frame | forward-stress/regime | SILENT | ❌ |
| J | `macro_data.fetch_panel:306-319` | series fail → partial panel; all fail → raise | regime axes | per-series logged | ❌ |
| K | `forward_stress_detector.detect:51-56,155` | VIX missing → Tier-3 synthetic → `("calm",0.3)` | regime → de-gross/HMM | SILENT (tier flag only) | ❌ |
| L | `regime_detector.detect_regime:165-172` | macro absent → low-conf "unknown" axes (T-164 GAP-2) | Engine-B risk scaling | SILENT per-axis | ❌ |
| M | `universe_resolver.resolve_universe:192-219` | membership parquet missing → static list, `mode=fallback_to_static` | edge universe (survivorship) | logged `fallback_reason` | ❌ |
| N | `run_backtest_pure._compute_metrics:295/305` | bare `std()==0`-class guard → sharpe=0.0 | metrics headline | SILENT | ⚠ (forbidden bare guard) |
| O | `run_backtest_pure:440-455` | config load fail → one-key risk `{risk_per_trade_pct:0.01}` / `{}` | risk/alpha/policy | SILENT (T-088 class) | ❌ |

Already-guarded: A, B (network only). Census-caught post-run: G/H, I-L, M, O. The
gap is **source HALT for the load-bearing+active case** at C-O.

## 2. The measured-mode HALT flag (design)
### 2.1 One predicate — `core/measured.py::is_measured()`
- Reuse, don't proliferate. `core/hermetic.py` already reads `ARCHONDEX_HERMETIC`
  (off/warn/strict) for NETWORK fallbacks. HALT is broader (a baked input absent
  is not a network event), so add a sibling predicate:
  `is_measured() -> bool` true when `ARCHONDEX_MEASURED=1` **OR** hermetic is
  `strict` **OR** the run is a canonical/anchor/cloud run (the cloud entrypoint,
  `run_isolated.py` canonical path, and `run_substrate_arms.py` set it). Default
  OFF locally so dev/paper/test keep graceful degradation.
- **Relationship to hermetic:** hermetic governs *network* (may I fetch?);
  measured governs *halt-on-missing-baked-input* (must I stop if a load-bearing
  input for an active consumer is absent?). Cloud sets BOTH (hermetic=warn +
  measured=1). They compose; neither subsumes the other.

### 2.2 One exception + one helper
- `class MeasurementHalt(RuntimeError)` — raised at the load site; the cloud
  entrypoint / `run_isolated` PASS-gate map it to exit-non-zero (same exit code
  family as a census FAIL).
- `halt_or_degrade(site, *, load_bearing, active, reason) -> Degraded | NoReturn`:
  - if `is_measured() and load_bearing and active`: `raise MeasurementHalt(site:reason)`.
  - else: return a `Degraded(site, reason)` sentinel the caller propagates so the
    summary gets `degraded=True` + `skip_reason` (the EXACT field T-181's census
    treats as FAIL). Outside measured mode the run CONTINUES (paper's "keep going
    on a transient blip") but is non-canonical.
- This is the whole contract: **measured + load-bearing + active ⇒ HALT; else
  degrade-with-flag.** Every site below is one call to this helper.

### 2.3 The "load-bearing AND active" test (the crux)
A missing input HALTS only if a consumer that NEEDS it is ACTIVE this run — else
it's legitimately skippable. The activeness signal already exists at run assembly:
- **value/accruals edges active?** → the resolved active edge-id set (the same set
  `signal_collector`/census already knows). simfin/fundamentals sites (F,G,H) are
  load-bearing iff ≥1 of those edge_ids is active.
- **regime overlay / de-gross active?** → the regime/governor config flags. Macro
  sites (I-L) are load-bearing iff the regime overlay or HMM/de-gross consumes the
  axis (today: always, when regime is on).
- **historical universe requested?** → `use_historical_universe=True`. Site M is
  load-bearing iff that flag is set (static-mode runs legitimately use the static
  list — NOT a fallback).
- **always load-bearing:** price OHLCV for a traded name (C,D), config provenance
  (O), the metrics std-guard (N) — these feed every headline.
The helper takes `active` as an explicit bool the caller computes from the run's
active-set/flags (no global state); design provides a small
`is_consumer_active(kind, ctx)` resolver fed the run context.

## 3. Per-site mapping
| Site | Measured action | Load-bearing test | Migration risk (what starts halting — the point) |
|---|---|---|---|
| F simfin cfg | distinguish **cached-read** (no key needed → never raise) from **fetch** (key needed). Halt only if cached parquet ALSO absent AND a value edge active | value/accruals edge active | cloud images w/o baked simfin panel HALT instead of publishing 17-edge-blind 0.751 (T-175) — **intended** |
| G/H get_panel/top_quintile | `halt_or_degrade("fundamentals", load_bearing=value_edges_active, active=…, reason="panel unavailable")` instead of silent None→{t:0.0} | ≥1 value/accruals edge active | same as F; the silent swallow becomes a halt/flag |
| I/J/K/L macro→regime | halt if regime overlay/HMM/de-gross active AND VIX/macro panel absent; Tier-3 synthetic allowed ONLY outside measured (flagged) | regime overlay or de-gross active | macro-unbaked cloud runs HALT instead of silently regime-"unknown" (T-164 GAP-2) |
| M universe_resolver | `fallback_to_static` becomes a HALT when `use_historical_universe=True` in measured mode; static-mode runs unaffected | use_historical_universe=True | historical runs missing the membership panel HALT (T-167 class) instead of survivorship-biased static |
| C/D OHLCV | halt if a TRADED name has no data in measured mode (today: empty df → 0 signals) | name in active universe | a delisted/missing name HALTS a measured run unless on a manifested allowlist |
| E _normalize_df band | already logs (T-181); in measured, escalate a band-drop that removes >X% of a series to a flag/halt | series feeds an active edge | over-aggressive clip surfaces instead of a quietly-shortened window |
| N std-guard | replace bare `std()==0` with tolerance (`<1e-12 / not isfinite`) AND stamp `degraded` when it trips on a real series (not just len<2) | always (headline metric) | a near-constant-returns run flags instead of emitting a clean 0.0 |
| O config fallback | distinguish "file absent" (maybe defaults OK outside measured) from "present-but-unparseable / env-path-missing" → halt in measured; never the one-key fabricated risk dict | always (config feeds risk/alpha/policy) | a missing/`{}` config HALTS measured runs (T-088 class) instead of running 5× risk on all-defaults |

## 4. Sequence + blast-radius + determinism
**Determinism:** every site change is canon-md5'd across the toggle. OFF (not
measured) MUST be byte-identical to today (the degrade path is unchanged; only an
extra `degraded` field is stamped, which is non-canon-relevant if excluded from
the trade canon — verify it's not in `trades.csv`). The CHANGE is by-design: in
measured mode, runs that previously published a degraded number now HALT — that's
the point; enumerate each (table §3, col 4).

**Recommended first 2-3 sites (highest headline-mover, lowest contract risk):**
1. **Fundamentals (F + G/H)** — closes the still-open T-175 0.751-degraded anchor.
   **Coordinate with B's T-180:** the *bake + manifest-verify* of
   `fundamentals_simfin.parquet` is B's lane; the *loader HALT/relax* (F: allow
   cached read without the API key; G/H: halt-or-flag instead of silent None) is
   this lane. Sequence the bake first (B), then the loader change consumes a baked
   panel and HALTs only if it's genuinely absent. Phase-1 census already shows
   `fundamentals_blind>0` as the forcing evidence on the next fresh image.
2. **universe_resolver fallback (M)** — T-167 class; one clean condition
   (`use_historical_universe and membership_absent and is_measured()` → halt).
   Self-contained, no cross-engine thread.
3. **macro→regime (I/L)** — T-164 GAP-2; halt when the regime overlay is active
   and the macro panel is absent. Higher blast-radius (Engine E + the de-gross
   overlay), so third.
Defer C/D (needs the manifested missing-name allowlist), E, N, O to a later
increment — N (the bare std-guard) is already slated as a Phase-1 no-behavior
tolerance fix per the audit; do that there, not here.

**Blast-radius summary:** sites F/G/H/M/I-L feed Engine A (value edges), the
universe, and Engine E (regime)/Engine B (risk scaling via regime). The change is
propose-first precisely because a measured HALT will (correctly) start failing
cloud/anchor runs that today publish degraded numbers — B's re-anchor + the
Phase-0b discovery cycle must run on images where the inputs are actually baked.

## 5. The offline-graceful preservation guarantee
- **Outside measured mode** (local dev, paper, unit/integration tests, the
  offline-sandbox): EVERY site behaves EXACTLY as today (empty df / None /
  Tier-3 / static fallback / partial panel) — paper keeps trading through a
  transient blip; tests keep running offline. The ONLY addition is a
  `degraded=True`/`skip_reason` stamp on the run summary, which is non-canonical
  by the census but does not change execution or the trade canon.
- **Inside measured mode** (cloud/anchor/canonical/hermetic-strict): a missing
  load-bearing input for an active consumer HALTS (exit non-zero), at the source.
- Paper's contract is explicitly preserved: paper runs are NOT measured mode (they
  are live-ish, not canonical measurements), so they keep graceful degradation +
  the order-state machine's own resilience. A paper run that wants to ASSERT
  completeness can opt into measured mode; by default it does not.

## 6. Recommendation
Build in this order, each a separate propose-first PR with canon-md5 across the
toggle: **(1)** `core/measured.py` (`is_measured`, `MeasurementHalt`,
`halt_or_degrade`, `is_consumer_active`) + wire the cloud/run_isolated exit-code
mapping (no site changes yet — pure infra, OFF by default); **(2)** fundamentals
F+G/H (coordinated with B's T-180 bake); **(3)** universe_resolver M; **(4)**
macro→regime I/L. Re-run the canonical anchor after (2) with census ON — it should
HALT on a simfin-blind image instead of publishing 0.751, which is the proof the
fix bites. Defer C/D/E/N/O.

## NOT included
No code (design/propose-first per the brief). The simfin bake/manifest is B's
T-180 lane (coordinate). This complements — does not replace — T-181's census.
Branch only; director merges the design doc.
