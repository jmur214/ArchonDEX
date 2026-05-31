---
task_id: T-2026-05-31-088
title: RiskConfig key mismatch fix + 4 small silent-bug fixes
date: 2026-05-31
substrate: Stooq+Alpaca merged (post-T-082b), 12-yr 2014-01-01 → 2025-12-31
scope: Engine B (propose-first APPROVED) + 4 autonomous cleanup fixes
outcome: prod risk-per-trade restored from accidental 5× (2.5% default) to intended 0.5%; max_position_value semantic fork DOCUMENTED, NOT silently guessed; filter now warns on unknown keys; 4 small silent bugs closed
---

# T-088 — RiskConfig Key-Mismatch Fix + Small Silent-Bug Sweep

## Headline

The 2026-05-31 silent-bug audit found that
`config/risk_settings.prod.json` (the only file `ModeController` loads
when `env="prod"`) used the legacy key `risk_per_trade` (no `_pct`
suffix), which `RiskEngine.__init__` filtered out silently in
`engines/engine_b_risk/risk_engine.py:132`. Production ran on
`RiskConfig.risk_per_trade_pct` **default = 0.025 (2.5%)** instead of
the intended **0.005 (0.5%)** — a 5× position-scale error in every
backtest since the prod config was authored.

This dispatch:

1. **Renames** `risk_per_trade` → `risk_per_trade_pct` in
   `config/risk_settings.{prod,dev}.json`, restoring the intended risk
   budget.
2. **Hardens** the filter in `risk_engine.py:132` so unrecognized keys
   emit `log.warning("[RiskConfig] ignoring unknown config key: %s ...")`
   instead of being silently dropped. This is the systemic fix —
   the same warning would have caught T-055g v1 patches and the
   `Sharpe` vs `Sharpe Ratio` directors-script issue.
3. **Documents the `max_position_value` semantic fork** instead of
   silently picking a side. The legacy key `max_position_value: 50000`
   is ABSOLUTE dollars; the dataclass field
   `max_pos_value_pct: 0.30` is a FRACTION of equity. These are
   different knobs, not a rename — see the dedicated section below.
4. **Closes 4 small silent-bug findings** ([1] Total Trades null,
   [2] Sortino reader-key mismatch, [7] yfinance adjustment-basis
   mixing, [9] SignalGate bare-except).
5. **Re-runs** the 12-yr baseline (arm_keyfix, 3 reps, 2014-2025) at
   the corrected risk config and reports Sharpe / CAGR / MDD vs the
   T-053b/T-055h arm0_off baseline.

## Part A — HIGH risk_per_trade key mismatch (Engine B)

### Before

`engines/engine_b_risk/risk_engine.py:132`
```python
cfg_filtered = {k: v for k, v in cfg.items() if k in RiskConfig.__annotations__}
self.cfg = RiskConfig(**cfg_filtered)
```

`config/risk_settings.prod.json` (excerpt)
```json
"risk_per_trade": 0.005,
"max_position_value": 50000,
```

`RiskConfig` (excerpt)
```python
risk_per_trade_pct: float = 0.025   # 2.5% default
max_pos_value_pct: float = 0.30     # 30% default
```

**Result:** prod runs silently dropped `risk_per_trade` AND
`max_position_value` and used `RiskConfig` defaults (2.5% per-trade
risk, 30%-of-equity max position).

### After

`config/risk_settings.prod.json` (corrected)
```json
"risk_per_trade_pct": 0.005,
"max_position_value": 50000,
```

`config/risk_settings.dev.json` (corrected)
```json
"risk_per_trade_pct": 0.01,
"max_position_value": 30000,
```

`engines/engine_b_risk/risk_engine.py:131-145` (hardened filter)
```python
known = set(RiskConfig.__annotations__)
cfg_filtered = {k: v for k, v in cfg.items() if k in known}
unknown = [k for k in cfg.keys() if k not in known]
for k in unknown:
    logger.warning(
        "[RiskConfig] ignoring unknown config key: %s (value=%r) — "
        "dataclass default will be used instead",
        k, cfg[k],
    )
self.cfg = RiskConfig(**cfg_filtered)
```

### Semantic-fork: `max_position_value` is NOT a rename — DIRECTOR DECISION REQUIRED

`max_position_value: 50000` is absolute dollars. `max_pos_value_pct: 0.30` is fraction-of-equity. With $100k initial capital, $50k = 50%-of-initial but diverges as equity grows. **These are different knobs.** Per the inbox: do NOT silently pick a side. Three defensible options:

| Option | Semantic | Behaviour | Trade-off |
|---|---|---|---|
| **(a)** Replace prod.json key with `"max_pos_value_pct": 0.50` | pct-of-equity, ≈$50k at start of 12-yr backtest | Cap scales WITH equity; on a 5× equity run, name cap becomes $250k | Matches dataclass shape; loses absolute-dollar guarantee |
| **(b)** Add `max_pos_value_abs: 50000` field to `RiskConfig` and prefer it over the pct path when present | pct OR abs, abs wins if set | Cap stays at $50k regardless of equity | Two-knob fork; needs spec for which wins; new Engine B code path |
| **(c)** Leave as-is (legacy key silently dropped, dataclass default 0.30 used) | pct-of-equity 30% | Status quo of every backtest ever | Original intent NOT honoured; the bug remains for max_position_value even after the risk_per_trade fix |

**This dispatch leaves the prod.json `max_position_value: 50000` key in place** so the director has the evidence and chooses. The corrected filter will now log `[RiskConfig] ignoring unknown config key: max_position_value (value=50000)` on every run, making the unresolved decision visible. **Director and user: which option?**

### 12-yr baseline re-run at corrected risk_per_trade_pct

Cloud campaign `t088-risk-keyfix-12yr` (1 arm × 3 reps × 12yr window,
`config_patch` adds `risk_per_trade_pct: 0.005` so the run uses the
intended 0.5% — `max_position_value` is left dropped, matching prior
behaviour, to isolate the per-trade-risk effect).

| Statistic | T-053b/T-055h arm0_off (legacy 2.5% risk_per_trade default) | T-088 arm_keyfix (corrected 0.5%) | Δ |
|-----------|---:|---:|---:|
| Sharpe (point) | 0.8102 | **PENDING — cloud run in flight** | |
| Sharpe ci_low (block-bootstrap 2.5%) | +0.265 | PENDING | |
| Sharpe ci_high (97.5%) | +1.392 | PENDING | |
| CAGR (annualized) | ~7.99 % | PENDING | |
| MDD | -14.44 % | PENDING | |

**Expectation per CLAUDE.md:** Sharpe is scale-invariant to a constant
position-size multiplier, so the corrected Sharpe should stay around
0.81 (with bootstrap-CI noise from the determinism drift surfaced in
T-055h and the partial fix in T-057c-det-followup). CAGR and MDD scale
roughly linearly with position size, so we expect both to shrink by
roughly 5× (since corrected risk is 0.5%/2.5% = 0.2× of prior). If
Sharpe shifts materially, that's a leverage-non-linearity surprise to
investigate (slippage, ADV cap, or max_pos_value_pct binding).

**MBL Gate-0 check (CLAUDE.md #7):** at N_trials ≈ 269 (post-T-088:
T-087 added 1 dispatch + per-method-and-per-stress-event signal-
validation arms ≈ 2; T-055h added 4; T-088 adds 3 backtest cells), MBL
required at SR=1.0 is `2·ln(269)/1² = 11.19 yr`. The 12-yr window
clears the gate by 0.81 yr — still passing.

## Part B — 4 small silent-bug fixes

### [1] Total Trades = null in 13 harness JSONs

**Before** (`cockpit/metrics.py:249`): `_compute_summary` emits Sharpe/Sortino/MDD/etc. but not the trade count. 13 A/B harness scripts call `summary.get("Total Trades")` and got `None`. The count IS emitted in `summary_metrics()` under legacy key `"Trades"`.

**After**: `_compute_summary` now emits `"Total Trades": int(len(self.trades))`. `summary_metrics()` keeps the legacy `"Trades"` key alive for back-compat (same value). Both consumers (dashboard cockpit + automated harnesses) now agree.

### [2] Sortino reader-key mismatch

**Before** (`core/observability/run_registry.py:118`): reader looks up `"Sortino Ratio"`. Producers in `core/metrics_engine.py:78,96` write `"Sortino"`. Registry's `sortino` column was NULL on every run.

**After**: reader looks up `"Sortino"` first, falls back to `"Sortino Ratio"` for any legacy `performance_summary.json` files. Test fixture `tests/test_run_registry.py:26` corrected to write `"Sortino"`. 8/8 tests pass.

### [7] yfinance adjustment-basis mixing

**Before** (`engines/data_manager/data_manager.py:64`): yfinance fallback fetches with `auto_adjust=True` (split + dividend total-return) and writes to the SAME cache as the Alpaca path (`data_manager.py:~671`, split-only). Result: any ticker that fell back to yfinance had dividend-adjusted prices mixed into a split-only substrate.

**After**: `auto_adjust=False` (split-only), matching the Alpaca/Stooq-merged substrate basis. `scripts/merge_stooq_alpaca_substrate.py:220` (`apply_dividend_strip`) only applies in the cross-source MERGE context where an overlap fit is possible; the yfinance fallback has no such overlap, so the right move is basis-matching at fetch.

**Blast radius:** scoped to tickers that genuinely fell back to yfinance (delisted backfill era). Most of the 12-yr substrate is Stooq+Alpaca (already dividend-stripped in T-082); the fix bounds the leak going forward but does NOT retroactively repair the cache. A `data/cache` cleanup is OUT of scope for this dispatch.

### [9] SignalGate bare-except fails open (cross-engine-contract)

**Before** (`backtester/backtest_controller.py:424-425`):
```python
except Exception as e:
    pass  # Fail open if gate errors
```
Any exception — including programmer errors (TypeError, AttributeError, NameError, AssertionError, ImportError) — was silently swallowed and ALL signals passed through unfiltered.

**After**: mirrors the sibling alpha narrow-catch at `backtest_controller.py:399-405`:
```python
except Exception as e:
    if isinstance(e, (TypeError, AttributeError, NameError, AssertionError, ImportError)):
        raise
    logger.warning(
        "[%s] SignalGate predict error (failing open): %s: %s",
        ts, type(e).__name__, e,
    )
```
Programmer errors propagate; data errors warn + fail open as before.

## Test sweep

Touched modules: `cockpit/metrics.py`, `core/observability/run_registry.py`, `backtester/backtest_controller.py`, `engines/engine_b_risk/risk_engine.py`, `engines/data_manager/data_manager.py`.

| Test set | Result |
|---|---|
| `tests/test_run_registry.py` | 8/8 PASS (Sortino fixture corrected) |
| `tests/test_backtest_controller_narrow_except.py` | 72/72 PASS |
| `tests/test_backtest_controller.py` | included in 116-test run, PASS |
| `tests/test_metrics_engine.py` | included in 116-test run, PASS |
| Full sweep (1823 tests) | 7 pre-existing failures, **0 new failures introduced** by T-088 (verified by `git stash` + re-run on clean main) |

Pre-existing failures (not T-088): `test_alpha_pipeline`, `test_anchor_no_stale_composites`, `test_discovery_gate1_caching::test_gate1_cache_invalidates_on_window_change`, `test_oos_validation_isolation_default`, `test_spinoff_reversion_edge`, `test_validate_candidate_v2`. None touch the modules T-088 modified.

## Spec acceptance check

| # | Acceptance criterion | Status |
|---|----------------------|:------:|
| A1 | risk_per_trade renamed in prod + dev config | DONE |
| A2 | max_position_value fork DOCUMENTED, not guessed | DONE (see semantic-fork section) |
| A3 | risk_engine.py:132 filter warns on unknown keys | DONE |
| A4 | 12-yr baseline re-run at corrected config | IN FLIGHT (cloud t088-risk-keyfix-12yr) |
| B1 | [1] Total Trades wired in _compute_summary | DONE |
| B2 | [2] Sortino reader key fixed + test fixture | DONE |
| B3 | [7] data_manager yfinance auto_adjust=False | DONE |
| B4 | [9] backtest_controller SignalGate narrow-catch | DONE |
| — | determinism check: any re-run uses 3 reps, canon-checked | included in cloud spec |
| — | Branch push only; director merges | pending |

## Files changed

- `config/risk_settings.prod.json` (rename risk_per_trade → risk_per_trade_pct)
- `config/risk_settings.dev.json` (same rename)
- `engines/engine_b_risk/risk_engine.py` (filter hardening; Engine B propose-first APPROVED scope only)
- `cockpit/metrics.py` (Total Trades in _compute_summary)
- `core/observability/run_registry.py` (Sortino reader key)
- `tests/test_run_registry.py` (test-fixture key)
- `engines/data_manager/data_manager.py` (yfinance auto_adjust=False)
- `backtester/backtest_controller.py` (SignalGate narrow-catch)
- `data/cloud_runs/specs/t088_risk_keyfix_12yr.json` (NEW — cloud campaign spec)
- this audit doc

## Memory updates needed (post-merge)

- New entry: "T-088 risk_per_trade keyfix — prod ran at 2.5% (dataclass default), not 0.5% (intended). 5× over-risk silently for every backtest. RiskConfig filter now warns on unknown keys (systemic fix). Sharpe ~scale-invariant so historical verdicts likely stand; CAGR/MDD absolute numbers need an asterisk pending the cloud re-run."
- Update `project_silent_bug_audit_2026_05_31.md` — [3] HIGH resolved (rename + filter-hardening); [1][2][7][9] closed; max_position_value semantic fork escalated to director.

## Forward dispatches

- **DIRECTOR DECISION**: max_position_value semantic fork — pick option (a), (b), or (c) above. Until decided, every prod run logs an `[RiskConfig] ignoring unknown config key: max_position_value` warning.
- **Image rebuild + ECR push** to ship the filter-warning into the cloud image so future cloud-side config drift surfaces in CloudWatch logs (the filter change is in the new T-088 image only after the next rebuild).
- **Cache cleanup**: any pre-T-088 yfinance-fetched cache entries are basis-mixed. Separate dispatch to enumerate + re-fetch.
- **Re-evaluation of prior absolute-CAGR / MDD claims**: T-053b, T-055h, T-087 numbers all rode on 2.5%-default risk_per_trade. The cloud re-run pinned in this dispatch establishes the corrected baseline; older numbers should be footnoted as 5×-over-risked.

## NOT done in T-088

- Image rebuild + ECR push (separate dispatch — the filter-warning code lives on this branch but does not ship to cloud until image-rebuild)
- max_position_value semantic decision (director scope)
- Cache cleanup for prior yfinance-fetched tickers (separate dispatch)
- No engines/engine_a_alpha/* changes (B collision-avoidance per inbox)
- No regime-validator changes (B's parallel task per inbox)
- No live_trader/ changes
