---
title: Silent-bug audit — systematic hunt for the mismatch/lookahead/wiring bug family
date: 2026-05-31
author: director (multi-agent workflow: 6 hunters + per-finding adversarial verify + synth)
method: 21 agents, 14 candidates, 9 confirmed (5 refuted by adversarial pass)
status: CORRECTED — first write-up reconstructed findings from a truncated notification and was wrong; these are the actual parsed results
---

# Silent-bug audit — 9 confirmed defects (CORRECTED)

> **Correction note:** the first version of this doc inferred findings
> (H1/H2 Engine E + M2-M6) from the truncated task-notification + prior
> context. That was the same infer-don't-verify error as the baseline DSR
> bug. The list below is parsed from the actual workflow result
> (`result.confirmed`, 9 items). Several inferred findings were WRONG —
> e.g. the HIGH is a config-key mismatch, not a regime-lookahead; the
> lookahead findings are in validation SCRIPTS, not Engine E production.

Motivated by the recurring silent-mismatch family (cockpit peak_equity
slot, hunt() ticker=, env-config, T-055g v1 patch keys, director 'Sharpe'
vs 'Sharpe Ratio'). One hunter per bug-class; every candidate
adversarially verified (refute-by-default). 5 of 14 refuted as benign.

## Ranked punch list (real)

### HIGH

**[3] config-namespace — production risk-sizing keys silently dropped.**
`config/risk_settings.prod.json` (the only file ModeController loads)
names sizing knobs `risk_per_trade` / `max_position_value`, but the
`RiskConfig` dataclass reads `risk_per_trade_pct` / `max_pos_value_pct`.
`RiskEngine.__init__` filters unrecognized keys silently → **production
runs on dataclass DEFAULTS, not the prod-config values.** Family: T-055g
v1 / env-config. **Engine B → PROPOSE-FIRST.**
Readers: mode_controller.py:516,522,576 → risk_engine.py:131-133,878,982.
Fix: rename JSON keys to match dataclass (and reconcile absolute vs
pct-of-equity semantics for max_position_value), OR add a legacy-alias
map + make the filter `log.warning`/raise on unknown keys.
**Blast radius: every backtest's position sizing may be using default
risk_per_trade, not the configured value — needs verification of whether
defaults == intended before judging severity of past results.**

### MEDIUM

**[5] lookahead — `scripts/validate_regime_signals_vix_term.py:245`**
uses `predict_proba_sequence` (whole-panel forward-backward smoothed
posteriors) then reports regime-conditioned forward returns → future
leaks into labels. **Fix:** per-bar causal labeling (`predict_proba_at`/
filtered), mirroring `validate_regime_signals_t087.py`.

**[6] lookahead — `scripts/backtest_transition_warning.py:331`** same
non-causal smoothing; inflates the apparent warning lead-time. **Fix:**
strictly causal per-bar loop.

**[7] unit-scale — `engines/data_manager/data_manager.py:64`** yfinance
fallback uses `auto_adjust=True` (split+dividend total-return) while the
primary Alpaca path (:671) is split-only; both write the SAME cache →
mixed adjustment basis in substrate, no dividend strip on the fallback.
Same class we hit in the Stooq merge. **Fix:** fetch fallback with
`auto_adjust=False` + apply the existing `apply_dividend_strip` before
caching. **Blast: any ticker that fell back to yfinance has total-return
prices mixed into a split-only substrate.**

**[9] cross-engine-contract — `backtester/backtest_controller.py:424-425`**
`SignalGate.predict()` wrapped in bare `except Exception: pass` that fails
OPEN — silently passes ALL signals when the gate raises, and (unlike the
sibling alpha catch) does NOT re-raise programmer errors. **Fix:** mirror
the narrow-catch pattern (re-raise TypeError/AttributeError/NameError/
AssertionError/ImportError; warn + fail-open only on data errors).

### LOW

**[1] key-field — `summary.get('Total Trades')` null in 13 harnesses.**
`run_backtest` returns `summary()` (no trade count); the count is
`'Trades'` in the unused `summary_metrics()`. Every A/B JSON records
`total_trades: null`. Diagnostic only — not a gate input. **Fix:** readers
→ `'Trades'` + wire summary_metrics(), or add 'Total Trades' to
_compute_summary().

**[2] key-field — `run_registry.py:118`** reads `'Sortino Ratio'`;
producers write `'Sortino'` → registry sortino column NULL every run.
**Fix:** one-line key change + fix the test fixture key too.

**[4] lookahead — `scripts/validate_regime_signals.py:348-355`** the
base regime validator has the same non-causal smoothing as [5]/[6], with
a false "equivalent for our purposes" comment. **Fix:** use the causal
path the t087 sibling already implements.

**[8] cross-engine-contract — `live_trader/live_controller.py:20`**
[PROPOSE-FIRST — live_trader] live sizing passes `cash` as the `equity`
arg, wrong-shaped df_hist, omits target_weights/current_qty → live sizing
diverges from backtest contract. **Fix:** pass total equity (cash+MV),
per-ticker OHLC frame, forward current_qty + target_weights.

## Did any contaminate the T-053b/T-055h/T-057b cycle?

- **[3] HIGH config-key:** This is the one to worry about. If
  `risk_per_trade` from prod.json was being dropped in favor of a
  different dataclass default, the *absolute scale* of every backtest's
  positions could differ from intent. **BUT** Sharpe is scale-invariant
  to a constant position-size multiplier, so the *Sharpe-based verdicts*
  (T-057 refuted, T-055 closed, baseline ~0.81) are likely unaffected.
  CAGR/MDD absolute levels could be off. **Needs a direct check: does the
  dataclass default == the prod.json value?** If yes, zero impact; if no,
  CAGR/MDD numbers need an asterisk.
- **[7] yfinance adjustment:** only affects tickers that fell back to
  yfinance (delisted backfill era). Most of the 12-yr substrate is
  Stooq+Alpaca (already dividend-stripped in T-082). Bounded.
- **[1]/[2] total_trades + sortino null:** diagnostic fields only; no
  verdict keyed on them. Turnover claims from those JSONs unsupported.
- **[4]/[5]/[6] lookahead:** all in VALIDATION SCRIPTS, not production
  backtests. They inflate the regime-signal AUC/lead-time diagnostics —
  meaning **A's T-087 AUC 0.887 should be re-checked against the causal
  path** (the t087 script claims it used causal; verify it doesn't share
  the leaky call). This is the most important follow-up.

**Bottom line:** the cycle's Sharpe-based verdicts stand. Two real
follow-ups: (a) verify the HIGH config-key default == intended, (b)
confirm T-087's headline AUC used the causal path (findings 4-6 show the
non-causal call is widespread in the regime validators).

## Coverage
5 of 14 candidates refuted by the adversarial pass (false alarms caught,
including benign Python source-order dict cases).
