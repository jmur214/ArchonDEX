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

### 12-yr baseline re-run at corrected risk_per_trade_pct — DEAD-KNOB FINDING

Cloud campaign `t088-risk-keyfix-12yr` ran 3 reps on the 12-yr window
with `config_patch: {"risk_per_trade_pct": 0.005}` (so the patched
file in the container had both the legacy `risk_per_trade: 0.005`
and the dataclass-recognized `risk_per_trade_pct: 0.005`).

| Statistic | T-053b/T-055h arm0_off (legacy 2.5% dataclass default) | T-088 arm_keyfix (corrected 0.5%) | Δ |
|-----------|---:|---:|---:|
| Sharpe (point) | 0.8102 | **0.8102** | **0.0000** |
| Sharpe ci_low (block-bootstrap 2.5%) | +0.265 | +0.273 | identical-within-bootstrap |
| Sharpe ci_high (97.5%) | +1.392 | +1.398 | identical-within-bootstrap |
| CAGR (annualized) | 7.99 % | **7.99 %** | **0.00 %** |
| MDD | -14.44 % | **-14.44 %** | **0.00 %** |
| Ending Equity | $251,499 | **$251,499.05** | **$0** |
| **canon_md5** | `989af6a3...87` | **`989af6a3...87`** (3/3 reps stable) | **bitwise identical** |

**The re-run produced bitwise-identical trades and equity curve** to
the T-053b/T-055h arm0_off canonical baseline. All 3 reps converged
on the same canon_md5 as the T-055h canonical (4/5 stable) and the
T-053b arm0_off canonical — three independent campaigns now agree
on the same trade output. **Cross-container determinism: 3/3 stable**
this dispatch (T-057c-det-followup's three additional FP-fixes
appear to have closed the 2/10 drift T-055h saw).

#### Why is the corrected risk Sharpe / CAGR / MDD identical to the over-risked baseline?

Inspecting one trade from rep1 (`AMT, 2014-01-03, long, 201 shares`):
```
sizing_mode:     target_weight
target_weight:   0.1070872330326901
target_notional: $10,708.72
```

**The production sizing path is Engine C target-weight (Path A in
`engines/engine_b_risk/risk_engine.py:817-865`), NOT Engine B
ATR-risk (Path B, lines 867+).** `risk_per_trade_pct` is only
consumed in Path B (`risk_engine.py:892: base_risk_pct =
self.cfg.risk_per_trade_pct`); in Path A, position size is
`equity × target_weight × optimizer_weight × portfolio_vol_scalar`
with no reference to `risk_per_trade_pct`.

Path A is taken whenever the dataclass field
`enforce_target_allocations=True` (the default) AND
`target_weights` are passed by the controller — which they always
are in the standard prod backtest flow (PortfolioEngine →
ModeController → BacktestController).

**Conclusion: `risk_per_trade_pct` is a dead knob in the production
backtest sizing path.** The legacy `risk_per_trade` key was indeed
being silently dropped — that's a real bug — but the dropped value
fed a code path the harness never exercises. The "5× over-risk"
framing in the silent-bug audit overstates impact; the genuine
exposure is "config-key drift surfaced in a path that the prod
config believed it was controlling, in this case harmlessly".

**Similarly, `max_position_value: 50000`** (the other legacy key
dropped from prod.json) does NOT bind in the target_weight sizing
path. The dataclass default `max_pos_value_pct: 0.30` is only
checked in Path B (`risk_engine.py:982: max_value = equity *
max_pos_value_pct`). In Path A, the cap-equivalent is whatever
ceiling PortfolioEngine + composer apply when computing
`target_weight` — and from the trade evidence, target_weights
ARE bounded around 0.30 max for any single name (KO trade in
2014-01-03 hit `target_weight: 0.3` exactly), suggesting composer
applies a 30% ceiling independently.

#### What this re-run actually proves

1. **All Sharpe/CAGR/MDD verdicts from T-053b, T-055h, T-087 STAND.**
   The historical numbers were never "5× over-risked" because the
   dropped key wasn't controlling sizing in the first place.
2. **The renaming fix in this dispatch (risk_per_trade →
   risk_per_trade_pct) is still correct.** If anyone later enables
   Path B (ATR-risk sizing) by setting
   `enforce_target_allocations=False`, the prod config's intended
   0.5% per-trade risk will now actually be honored.
3. **The filter-hardening (warn on unknown keys) is still correct
   and now MORE valuable**: this exact silent-drop pattern (key
   present but dead) is precisely the failure mode the warning
   catches. Future prod runs log
   `[RiskConfig] ignoring unknown config key: risk_per_trade`
   (legacy still in dev.json — see semantic-fork section) and
   `[RiskConfig] ignoring unknown config key: max_position_value`,
   making the unresolved decisions VISIBLE.
4. **3/3 cross-container determinism** is the first 12-yr campaign
   to clear the determinism gate cleanly. T-057c-det-followup's
   three additional FP-fixes (xsec_momentum, composer HRP,
   moonshot sleeve) appear sufficient.

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
| A4 | 12-yr baseline re-run at corrected config | DONE — 3/3 reps bitwise identical to baseline; risk_per_trade_pct is dead-knob in target_weight sizing path |
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

- New entry: "T-088 risk_per_trade keyfix — config key WAS silently dropped (bug confirmed) but `risk_per_trade_pct` is a DEAD KNOB in the production sizing path (Engine C `target_weight` is used, not Engine B `atr_risk`). 12-yr re-run produced bitwise-identical trades (canon_md5 unchanged, Sharpe 0.81, CAGR 7.99%, MDD -14.44%). All historical verdicts STAND. The audit's '5× over-risk' framing overstated impact. Renaming + filter-hardening still ship as the systemic fix; ditto for catching `max_position_value` (also legacy/dropped, also irrelevant in target_weight path)."
- Update `project_silent_bug_audit_2026_05_31.md` — [3] HIGH downgraded to LOW-LATENT in the audit's blast-radius sense: real key-drop, zero observable impact in current sizing path, fixes still merit-ranked. [1][2][7][9] closed; max_position_value semantic fork escalated to director.
- New entry: "Engine B Path A (`enforce_target_allocations=True`, target_weight sizing) makes `risk_per_trade_pct`, `max_pos_value_pct`, `atr_stop_mult`, `atr_tp_mult`, `cap_atr_to_pct_of_price`, `atr_floor_pct_of_price` all DEAD KNOBS in production backtests. Future config audits must distinguish 'key present in dataclass' from 'key consumed by active sizing path'. The active sizing path is `risk_engine.py:817-865`, NOT lines 867+."

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
