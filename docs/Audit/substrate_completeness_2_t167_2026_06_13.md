---
task_id: T-2026-06-13-167
title: Cloud substrate completeness ROUND 2 — full SPY history + the cloud
  price-axis regime + the median*3 load-truncation landmine + the mean_variance
  allocator crash + archive the Apr-23 allocator artifact
date: 2026-06-13
author: Agent D (alpha/edge + substrate-data lane)
outcome: FIXED + PROVEN. FOUR substrate-completeness defects of the same
  "data/behaviour not reaching the engine" class as T-164, plus the director's
  artifact-archive decision. (1) GAP 3 SPY truncated to ~6yr -> regenerated full
  1993-> depth. (2) the median*3 sanity clip in _normalize_df silently truncated
  90/109 universe tickers at LOAD since the T-082 deep merge -> replaced with a
  lookahead-free strictly-additive rolling band. (3) GAP 4 the cloud price-axis
  regime was dead because trend/vol read the truncated SPY -> PROVEN live across
  the full window once SPY depth + the clip fix land. (4) CRITICAL: the
  production allocator (mean_variance) crashed on EVERY bar with an
  UnboundLocalError introduced 12h earlier by the T-140-fu2 cov->MVO probe; the
  controller's broad except swallowed it into silent 0-trades; the Apr-23
  artifact (adaptive) masked it locally; archiving the artifact (mean_variance =
  production) exposed it -> FIXED, mean_variance now trades. DUAL+ bar met:
  controller-path run 73 trades + 60/60 trend & vol live across the (pre-2020)
  window. Unblocks B's re-anchor.
status: CURRENT
reproduce: |
  python -m scripts.regen_spy_full_history_t167 --asof 2026-06-13   # full SPY
  ARCHONDEX_HERMETIC=1 python -m scripts.prove_regime_live_full_window_t167  # GAP4 A/B
  ARCHONDEX_HERMETIC=1 python -m scripts.prove_backtest_trades_regime_t167 \
     --start 2018-01-01 --end 2018-03-31                            # 73 trades + live regime
  python -m pytest tests/test_substrate_completeness_t167.py \
     tests/test_mean_variance_os_crash_t167.py -q                   # 9 pass
---

# T-167 — substrate completeness round 2

Four defects, all the T-164 class (something the engine needs not reaching it),
surfaced by B's re-anchor attempt + C's T-165. The load-bearing calendar
question is answered first because it determines whether the collapse narrative's
window was ever real.

## The calendar-driver question (acceptance #1) — ANSWERED

**The backtest CALENDAR is the UNION of every ticker's dates, NOT SPY.**
`backtester/backtest_controller.py:202-203`:
```python
all_sets = [set(df.index) for df in self.data_map.values() if not df.empty]
self.timestamps = sorted(set().union(*all_sets)) if all_sets else []
```
Verified empirically: with the static+historical universe the controller builds
`len(self.timestamps) == 16196` spanning **1962-01-02 -> 2026-05-07**. So the SPY
truncation was **benchmark-only, NOT window-invalidating** — the "26yr"/"16yr"
windows WERE real (driven by the 1962/1970-deep stock universe); only the
benchmark + the price-axis regime were degraded. SPY's first row is 2020-04-09
(an Alpaca-only pull never folded into the T-082 deep merge), so the truncation
predates and is independent of the old anchors' window length; it degraded the
regime on every long-window run (incl. the anchors) but did not shorten them.

## GAP 3 — full SPY history regenerated

`data/processed/SPY_1d.csv` was 1513 rows (2020-04-09 -> 2026-04-17). The deep
stocks (KO/JPM/XOM @1970, IBM @1962) came from the T-082 Stooq+Alpaca
dividend-strip merge; SPY only ever got the Alpaca-only tail. **Proven basis:**
the existing 2020+ rows are EXACTLY yfinance total-return (Adj Close) — ratio
alpaca/yf-TR = 1.000000 (std 0.0) over all 1513 overlap days — so extending on
the same yfinance-TR basis is a zero-convention-change, zero-seam splice. SPY's
1993-01-29 inception covers every project window (16yr=2010, 26yr=2000).

`scripts/regen_spy_full_history_t167.py` (committed, `--asof` vintage-stamped):
deep portion 1993-01-29 -> 2020-04-08 from yfinance-TR; recent rows kept
**byte-identical** (appended verbatim; parquet recent read back from the original
for bit-identity). Result: 8361 rows, recent OHLCV byte-identical (CSV + parquet
both verified in-script). Manifest re-pinned (SPY csv+parquet lines only — see
"foreign drift" below).

## BONUS BUG 1 — the median*3 load-truncation landmine (the bigger GAP)

`engines/data_manager/_normalize_df` ran a global sanity clip:
```python
median_close = df["Close"].median(skipna=True)
df = df[(df["Close"] > 0) & (df["Close"] < median_close * 3)]
df["Close"] = df["Close"].clip(lower=0.01, upper=median_close * 3)
```
On a long history whose price grows >3x its all-time median, this DROPS the
recent high-priced bars at load. Added 2025-10-21 (62c3eaf) when histories were
short (harmless), it **detonated** once T-082 baked 1970-> depth: **90 of 109
universe tickers lost their recent decade(s) at load** — AAPL cut @2009 (−17yr),
IBM @2002, JPM @2016, KO/SPY @2020, XOM @2021. Effect: every long-window run
since the deep merge ran on **per-ticker-ragged** data, and a restored SPY would
re-truncate at 2020-06 (so this had to be fixed for GAP 4).

**Fix:** a trailing (lookahead-free) rolling-median band — a real fat-finger is
>20x its local 63-bar level and reverts; sustained appreciation never is.
**Strictly additive, verified across all 109 universe tickers: 0 rows dropped,
0 values changed for every bar the old band kept; 100 tickers get their
silently-clipped recent history restored, 9 short-history names unchanged.** The
isolated-fat-finger guard is retained (a single 100x tick is still dropped —
unit-tested).

## GAP 4 — the cloud price-axis regime — PROVEN live across the full window

Mechanism (C's T-165): `trend` & `volatility` axes read ONLY the benchmark SPY
(`regime_detector.py:166-167` -> `{trend,volatility}_detector.py`); `corr` &
`breadth` read the full data_map. With SPY truncated to 2020+, every bar before
2020-04 had `slice_map.get('SPY')` empty -> trend/vol "unknown". C saw the regime
LIVE locally only because the default config window (2021-2024) sits inside the
6yr SPY; the cloud's long windows reach back before it.

**Controlled A/B** (`scripts/prove_regime_live_full_window_t167.py`, hermetic):
- POSITIVE (restored SPY + clip fix): trend & vol live **13/13** sampled dates,
  **pre-2020 both-live 9/9** (2002-2018 incl. 2008-10 crisis).
- NEGATIVE (SPY truncated to 2020+, the old cloud condition): pre-2020 NO-SPY,
  **0/9** — exactly the "cloud price-axis regime dead". Post-2020 works.
SPY depth is the SOLE cause; **no separate reach gap**. (Caveat: the sparse-date
driver carries hysteresis state across non-consecutive dates, so only liveness —
not the specific labels — is the claim there. The sequential controller-path run
below produces representative labels.)

## BONUS BUG 2 (CRITICAL) — the mean_variance allocator crashed on every bar

While verifying the directive's "local trades on mean_variance", short-window
runs produced 1 bar / 0 trades with NO error (the controller's `except Exception`
at `backtest_controller.py:1373` only prints under debug). Surfaced with
`BACKTEST_CONTROLLER_DEBUG=1`:
```
[BACKTEST] Unexpected error during backtest: cannot access local variable 'os'
```
In `policy.py` `allocate()`'s mean_variance branch: line ~220 uses
`os.environ.get("ARCHONDEX_COV_MVO_PROBE")`, but a function-local `import os` at
line ~232 made `os` LOCAL to the whole function -> UnboundLocalError on every
mean_variance bar with >=5 return rows. **Introduced 2026-06-13 (d0cdf6e,
"T-140-fu2 ... cov->MVO capture probe")** — the same cov-pin work B is
re-anchoring on, ~12h before this task. The Apr-23 artifact (adaptive) masked it
locally; the 4-year proof run (artifact present) ran fine, the post-archive
mean_variance runs crashed.

**Fix:** removed the shadowing function-local `import os` (module-level `os` at
`policy.py:4` covers it). Behaviour-preserving (un-crash only). Regression test
`tests/test_mean_variance_os_crash_t167.py` exercises the branch with and without
the probe env var set.

**Blast radius / FLAG for B + C:** any mean_variance run since d0cdf6e silently
0-trades (or 1-bars). B's recent re-anchor attempts on the cov->MVO/mean_variance
path would have hit this — possibly mis-attributed to substrate gaps. This is a
LARGE canon change (crash/0-trades -> real mean_variance trades). Re-anchor MUST
be on a build that includes this fix. (Older cloud runs — pre-d0cdf6e — predate
the bug, so the historical lottery on the cov->MVO composition is a SEPARATE,
still-open issue.)

## Director decision — archive the Apr-23 allocator artifact

`data/research/allocation_recommendations.json` (Apr-23, 2521 bytes, gitignored,
unbaked, never-manifested) is loaded fresh on every `allocate()` via
`policy.py:_apply_regime_overrides` -> sets cfg keys **including `mode`** from the
artifact (which is `adaptive` for every regime) -> silently overrode the
committed `mean_variance` LOCALLY only (the cloud lacks the file -> stays
mean_variance). Archived to `Archive/data/research/
allocation_recommendations_apr23_archived_2026-06-13_t167.json` (never deleted) —
now ABSENT from the shared data/research, so local == cloud == config-true
mean_variance. Confirmed: `_apply_regime_overrides` with a live regime_meta now
leaves `cfg.mode == "mean_variance"`. **mean_variance is the production
allocator** (committed `config/portfolio_settings.json`; T-162 1.542 > adaptive
0.464 on 2022).

**Local trades on mean_variance — VERIFIED (no governor drift):** post-archive +
os-fix, `scripts/prove_backtest_trades_regime_t167.py` 2018-Q1 hermetic:
**73 trades**, trend live 60/60, volatility live 60/60 (window is pre-2020, so
also a controller-path confirmation of GAP 4). VERDICT PASS. The governor
soft-pause state (0.25x on 4 edges) did NOT zero out trading.

## DUAL+ success bar (acceptance #4)
A controller-path cell that **TRADES (73) + FULL live regime (trend & vol 60/60,
macro emerging_expansion/robust_expansion/market_turmoil/cautious_decline, 0
unknown) + spans the pre-2020 boundary**, under hermetic (the cloud no-network
condition). Met.

## Foreign drift FLAG (not mine — report, don't fold in)
The shared `data/processed` + `data/raw/simfin` carry uncommitted simfin
fundamentals drift from another agent (6 CHANGED + 1 EXTRA `fundamentals_simfin.
parquet`). Per the T-154/T-131 discipline I did NOT fold it into my manifest
commit — the manifest diff is the **2 SPY lines only**. `manifest verify` will
still fail on simfin until whoever regenerated it commits or reverts it; that is
a coordination item for the director, orthogonal to T-167.

## Files
- `engines/data_manager/data_manager.py` — median*3 -> rolling-band fix (BONUS 1)
- `engines/engine_c_portfolio/policy.py` — remove shadowing local `import os` (BONUS 2)
- `config/substrate_manifest.sha256` — SPY csv+parquet re-pinned (2 lines only)
- `data/processed/SPY_1d.csv` + `parquet/SPY_1d.parquet` — full 1993-> (gitignored, baked via existing COPY data/processed)
- `Archive/data/research/allocation_recommendations_apr23_archived_2026-06-13_t167.json` — archived artifact (gitignored op-move)
- `scripts/regen_spy_full_history_t167.py`, `scripts/prove_regime_live_full_window_t167.py`,
  `scripts/prove_backtest_trades_regime_t167.py`
- `tests/test_substrate_completeness_t167.py` (7), `tests/test_mean_variance_os_crash_t167.py` (2)

## NOT included
No Engine B / live_trader. No TASK_LEDGER write (T-114 — row in OUTBOX). No
change to the regime/allocator LOGIC (os-fix is un-crash only; clip-fix is
strictly additive). The simfin drift is NOT touched. Branch only; director merges.
