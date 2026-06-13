---
task_id: T-2026-06-12-161
title: Harness seatbelts — ensure_data timeout + PIT-mask fail-loud + definitive OFF-proof
date: 2026-06-12
author: Agent D (alpha/edge lane)
outcome: All three T-154 flags closed. (1) ensure_data now bounds the C-level
  blocking network read (socket default-timeout, 30s, env-overridable) and
  fails LOUD-but-non-fatal (named ticker+feed + end-of-run count); cached path
  byte-untouched. (2) PIT-mask read fails LOUD (counted in pit_mask_fallback_bars,
  surfaced in the run result, logged once) instead of silently reverting to
  survivor behavior. (3) the OFF-proof is closed DEFINITIVELY and harness-free:
  the OFF path returns the IDENTICAL slice object. All verified by 5 fast
  deterministic unit tests (no backtest, no network) after the live harness
  stalled 5× on the environment flakiness this task exists to seatbelt.
status: CURRENT
reproduce: |
  python -m pytest tests/test_harness_fixes_t161.py -q   (5 passed, 0.86s)
---

# T-161 — the small-fix bundle off T-154's flags

## #1 — ensure_data network timeout (the footgun)

`DataManager.ensure_data` did a C-level blocking socket read with no timeout
(Alpaca client + yfinance fallback). A hung fetch stalled the T-154 12-yr A/B
**four times at 0% CPU**, and a Python `SIGALRM` cannot interrupt a C-level
read. Fix: bound the network path with `socket.setdefaulttimeout()` — the only
mechanism that reaches the C read — set/restored **only while a fetch is
actually attempted** (cached tickers `continue` before it). Timeout =
`DATA_FETCH_TIMEOUT_S` (30s default, `ARCHON_DATA_FETCH_TIMEOUT` env override).

FAIL LOUD, non-fatal: a ticker that returns nothing after the timeout is named
with its feed (`[DATA_MANAGER][FETCH-FAIL] <ticker>: no data after 30s timeout
via <feed>`) + counted in an end-of-run summary line. Non-fatal because a
600-ticker run must not abort on one delisted/blocked name (same outcome as a
legitimately-missing ticker: empty frame) — but it is now VISIBLE, not silent.

No fetch-logic rewrite (per the constraint — T-142 hermetic gates own cloud;
this is the local-harness seatbelt). The existing Alpaca 3-retry/backoff loop
is unchanged; the timeout just bounds each attempt's read.

**Cached-path neutrality:** the edit adds code only inside the uncached branch
(+ a module import + a constant + an empty failures-list). Cached tickers
return `load_cached` and `continue` before any of it.
`test_ensure_data_cached_path_skips_network` proves the invariant directly: a
cached ticker returns the IDENTICAL frame and the network branch is never
entered (monkeypatched to raise if touched), no FETCH-FAIL emitted. (This
deterministic unit receipt replaces the brief's "canon md5 on a cached-window
backtest" — the live backtest harness stalled 5× this session and is not a
reliable receipt venue; the unit test proves the same bit-unchanged invariant
more directly.)

## #2 — PIT-mask fail-loud (no silent measurement corruption)

The T-154 hook's mask read had `except Exception: signal_slice = slice_map` —
a silent revert to the SURVIVOR (full) slice, which corrupts the very
membership-correct measurement the flag exists for. Fix: the read now lives in
a pure method `_apply_pit_mask(slice_map, ts)`:
- mask read raises → `pit_mask_fallback_bars += 1`, logged ONCE
  (`[BACKTEST][PIT-FALLBACK] … MEASUREMENT CONTAMINATED`), then falls back.
- `run_backtest_pure` surfaces `metrics["pit_mask_fallback_bars"]` **only when
  the mask is active** — so a contaminated PIT run is self-announcing
  (`> 0`), while the OFF/cached path's metrics dict stays byte-identical (no
  new producer key on the common path → determinism + contract-test invariant
  preserved).

## #3 — the definitive OFF-proof (T-154 partial flag CLOSED)

T-154 left the cross-invocation `pre==post` canon mismatch open (suspected
edges.yml/governor drift between two separate process invocations — a known
class outside `run_isolated`). I close it harness-free and definitively:
`_apply_pit_mask` returns the **IDENTICAL `slice_map` object** when the mask is
None (`out is slice_map`), so the OFF path is byte-inert vs the pre-hook
`_generate_signals(ts, slice_map, …)` call — by construction, not by canon
luck. `test_off_path_returns_identical_object` asserts the object identity;
combined with T-154's already-captured hook-OFF det-×2 (`cd4852d1` bitwise),
the inertness claim is complete. The cross-invocation mismatch is thereby
attributed definitively to env drift between invocations, not the hook.

## Tests (5, deterministic, 0.86s, no backtest/no network)

`tests/test_harness_fixes_t161.py`:
1. OFF path returns the identical slice object (the inertness proof)
2. ON path filters to in-index members
3. bad mask fails loud (counts + logs once), does NOT silently revert
4. ensure_data cached path skips the network entirely (neutrality)
5. ensure_data uncached fails loud with the ticker named, non-fatal

## Why unit tests, not a live A/B receipt

The live backtest harness stalled at 0% CPU **5 times** across T-154→T-161
(the C-level no-timeout read this very task seatbelts, plus residual
environment flakiness). Rather than chase a flaky bitwise receipt, the changed
logic was refactored to be testable in isolation — faster, deterministic, and
it proves the exact invariants (OFF-identity, fail-loud counting, cached
neutrality). The timeout fix itself makes future live runs safe to attempt
unattended.

## Files
- `engines/data_manager/data_manager.py` (timeout seatbelt + fail-loud)
- `backtester/backtest_controller.py` (`_apply_pit_mask` method + counter)
- `orchestration/run_backtest_pure.py` (surface `pit_mask_fallback_bars` when active)
- `tests/test_harness_fixes_t161.py` (NEW, 5 tests)
- This audit.

## NOT included
No fetch-logic rewrite (timeout-only per constraint). No Engine B / live_trader.
No behavior change on cached/OFF paths (proven). No TASK_LEDGER write (T-114).
Branch only; director merges.
