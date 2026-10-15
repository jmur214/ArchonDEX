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

## 6. As built (B, 2026-10-15): what changed from §1–§4, and what it reads

**Built** on `feature/stale-holed-guard` (73b421c: the guard at 6309cb3, two fixture commits,
FISV's declaration, and R's two build-review corrections; on the rail with its split-window fix);
with R for re-approval by diff. Differences from the proposal, each forced by a measurement:

- **The calendar is proven, not assumed.** §1 named "the SPY bar dates" as the calendar. SPY's own
  file is canonical and can be wrong, so the calendar is instead the majority of the names active
  each day, PROVEN against SPY in both directions:
  - a majority day SPY lacks inside its own span means SPY is holed;
  - a day SPY traded that the majority lacks means the calendar is holed. That is a mass hole the
    per-name count cannot see. On the real cache, 244 of 248 active files lack 1999-11-16, a day
    SPY has.
  A run with no SPY has an unverified calendar, which fails. SPY's own early END is SPY's stale
  entry, never a calendar hole: the real cache's SPY ends 04-17 while 481 files run to 04-24.
- **The END test is R's correction:** per name, against the earlier of the window end and the
  member's last exit inside the window, with a 5-trading-day slack.
- **Declarations are facets, and each excuses exactly what it declares** (R's sentence: ends at
  delisting vs holed inside). `holed_inside.runs` excuse the missing days inside those runs only.
  `ends_at_delisting.last_bar` excuses an early end only when the file's last bar IS that date.
  Neither excuses the other, and a malformed declaration file raises. JNPR is why the second facet
  exists: last print 2025-07-01, the index's recorded exit 07-09, six trading days. It is declared,
  never absorbed by widening the slack.
- **One reader for the gate and the admission:** `core.census.coverage_defects`. In a measured run
  the admission is a MeasurementHalt (`halt_or_degrade`), never a silent drop.
- **The first declaration set is 46: 45 files, not 33, plus one provider gap.** §2 counted the holed
  files the cutover cannot fill at three or more missing days inside the post-seam span. At
  tolerance 0 over each file's full span, the set of files NO provider can fill is 45:
  - 32 delisted;
  - 10 files lying entirely after their PIT name's exit (later entities on the symbol);
  - the 3 class (i) names.
  That is 1,298 holes in 395 runs; 19 of the 45 also carry `ends_at_delisting`. All were built
  mechanically from the guard's own count on the post-write copy.
  **Plus FISV 2025-11-12, a PROVIDER GAP** (the director's ruling: declared with the provider's
  own reason). The universe provider lacks the bar in both modes, yet the security TRADED: Alpaca
  records a full session (SIP volume 6,244,651), on the day after Fiserv's FI → FISV ticker change.
  So the declaration says "a provider gap on a session that happened, unfilled under the
  one-provider rule", never "no provider series" or "a non-trading day".

**What it reads.** PIT, over the canonical window 2000-01-03 → 2025-12-31, with the shipped
declarations:

| substrate | stale | holed | calendar |
|---|---|---|---|
| the real cache today | 27 | 245 | proven |
| the post-write copy | **0** | **5** single days | proven |

The five on the copy are JPM, KDP, TDC, WMT and WU, the §2b span refusals awaiting the user's class
(iii)/(iv) ruling. **Over 2018 → 2025 the copy reads no defects at all: the guard's first green
reading.** So after the cutover, the guard is one user ruling from green over the full canonical
window. The real cache stays RED, as ruled.

**Formation coverage is over EVERY member on the date** (R's build-review correction). The member
set is the PIT intervals covering the date, or the static list under a static universe. A member
with no file, or with no bar on the date, is not formed. The first build took its members from
the data map, so a member with NO file dropped out of the denominator. That was A's §14.3
file-presence defect in a new form, and it read 0.66 / 0.83 / 134; R measured 0.72 / 0.87 / 89 on
another map, which is the signature of a denominator that moves with the files present.

Corrected, it reads min **0.38**, median **0.70**, with **208 of 312** month-ends below 0.80.
Those are A's numbers, and they are IDENTICAL on the real cache and the post-write copy, whichever
files are in the map. The gap is late starts and missing files (the survivorship gap); the
cutover does not move it. It is recorded, not gated (§1).

**The contract (R):** the candidate producer is executed on a clean map and window, and NO
provenance key may be an error record. Before this, its except branch's `{"error": …}` counted
as "present".

**One rule beyond §1–§4:** a run with no SPY has an UNVERIFIED calendar, and the gate fails it.
It caught 19 Discovery test fixtures whose synthetic data_maps carried only AAA, so Gate 1
refused every candidate before the gate under test ran. The fixtures were fixed additively, with
SPY on the same calendar as production always carries it; the rule was not relaxed. With R as
question 1 of the build review.
