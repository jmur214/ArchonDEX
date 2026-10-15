# Proposal: the stale/holed-files guard — admission reads BARS, never file presence

**For:** Agent R (review), then the director. **Owner:** Agent B. **Status:** PROPOSAL ONLY. Ruled
propose-first, after the level rail and ahead of the fundamentals miss-refusal unit (director,
2026-10-15). It answers the HIGH on the write-time band (health_check: "The pre-T-167 GLOBAL-median×3
band, applied at WRITE time…"), whose anchor is the admission rule this proposal changes.

## 0. The defect, in the census's own terms

The band left 33 LIVE files ending before the canonical window end (28 at their own all-time highs),
and 114 files with holes inside their span (NVDA missing 15 days, PLTR 24, SEDG 613…). Nothing
counted any of it, because every count was a count of FILES or FRAMES:
- `discover_cached_tickers` admits a file by its ROW COUNT and never reads its end date
  (`engines/data_manager/universe_resolver.py:333`);
- the run census's `n_resolved` is the number of frames HANDED to the controller
  (`backtest_controller.py:133`), and `n_in_panel` the number SURVIVING normalization (:1355). Both
  count frames, so NVDA (file ends 2024-05-10) counts as fully "in panel" for a run to 2025-12-31;
- B-1's `coverage_pct` counted a name covered when its FILE existed, not when a BAR existed at the
  month-end. True coverage was 38.4 % in 2000-01 against the 52.7 % quoted (A's §14).

**The rule this proposal installs:** coverage counts BARS, never file presence. For any consumer
that forms a cross-section, the count is the rows FORMED on the formation date (R's wording).

## 1. The census key `stale_files`, written by BOTH producers

One function, `engines/data_manager/coverage.py: stale_files_record(data_map, window, calendar,
membership, declared)`, so the two producers cannot drift. `_build_census` assigns
`census["stale_files"]` FROM it (the AST half of the two-producer lock), and
`candidate_census_block` does the same (the executed half).

```
"stale_files": {
  "window": [start, end], "calendar": "<trading calendar source>",
  "names": {T: {"first_bar", "last_bar",
                "ends_before_window_end": bool,      # live per membership, file ends early
                "missing_trading_days": n,           # inside [max(start, first), min(end, last)]
                "longest_missing_run": k,
                "declared": "<data_gaps reason>" | null}},
  "n_stale": a, "n_holed": b, "n_declared": c,
  "formation_coverage": {"rule": "rows FORMED on the formation date",
                         "dates": n, "min": x, "median": y, "dates_below_0_80": k}
}
```

- **Live** = still a member at the window end in the PIT membership (no end, or an end after the
  window). Under a static universe, every name is live unless declared.
- **Missing trading days** are counted against the trading calendar (the SPY bar dates), so exchange
  holidays never count. The end date and R's bar-every-business-week rule are special cases of this
  count.
- **`formation_coverage`** is computed only for runs that form cross-sections. It is the share of
  that date's members with a bar ON the date, never a file on disk.

## 2. The gate (`assert_census`) and the admission refusal

- **The census gate** fails a canonical run when any undeclared live name `ends_before_window_end`,
  or has `missing_trading_days` above a DECLARED tolerance. Proposed: 0 beyond the calendar; a real
  halt is declared, not tolerated. An errored `stale_files` record fails, as `data_exclusions` and
  `ticker_exclusions` do.
- **Admission** (`resolve_universe` / `discover_cached_tickers`): in a measured run
  (`core.measured.halt_or_degrade`), a live name whose file ends before the window end, or is holed
  beyond the tolerance, is REFUSED unless declared (`[NN-FAIL-CLOSED]`). It is never admitted as
  "stopped trading". Outside measured mode it is admitted, WARNed and recorded.
- **Declarations:** `data_gaps`, one entry per name: the hole count, the reason, and the source. The
  first set is the 33 holed files the cutover cannot fill (BBBY, PSKY, CPWR, and 30 unfetchable
  delisted names; reason "no provider series"). It is carried by the census under the same key, and
  it is the standing argument for option (c).

## 3. What it will read on today's cache, and after the cutover

- **Today:** red on any canonical run whose window reaches 2024–2025 and includes the stale names.
  That is the honest state; the HIGH row is the fix's name.
- **After the cutover:** the write pass restored the 32 stale live names through 2026-10-14 (identity
  1.000000) and filled all 81 written holed files. What remains is the 33 declared `data_gaps`.

## 4. Locks (reversion-proven; each drives the real entrypoint)

1. A planted live name whose file ends before the window end → the census record names it, the gate
   fails, and measured admission refuses. Reverting to row-count admission → it passes silently.
2. A planted holed file (a run of missing calendar days) → `missing_trading_days` counts it.
3. Holidays never count (a calendar-aligned file → 0).
4. A declared `data_gaps` name passes, carrying its declaration.
5. `formation_coverage` counts rows FORMED on the date: a name with a file but no bar on the date
   counts as uncovered. This is the B-1 `coverage_pct` defect, reproduced and refused.
6. Both producers write the key (CENSUS_PROVENANCE_KEYS), and an errored record fails the gate.

## 5. For R and the director

1. **The missing-day tolerance:** 0 beyond the calendar, with real halts declared (proposed).
2. **"Live" under a static universe:** every name is live unless declared (proposed).
3. **`n_resolved` / `n_in_panel` keep their frame meaning** (invariant 2's shrink check) and gain
   their bar-based companion here; they are not redefined.
