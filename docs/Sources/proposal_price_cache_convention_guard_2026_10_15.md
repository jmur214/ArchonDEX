# Proposal: every write into the price cache carries its MEASURED convention and refuses any other

**For:** Agent R, then the director. **Status:** PROPOSE-FIRST. It changes fetch behaviour in
`engines/data_manager/` and the substrate the backtester reads. Nothing is edited. **N_trials: 0.**
**Implements:** the director's ruling of 2026-10-15, stated for the user to override:
*"the substrate convention is TOTAL RETURN"*, items (a) and (b). Item (c), not re-running the
equity book, is the director's record. Item (d), the price-level filter scan, is its own unit (§6).

## 0. Corrections absorbed before code: Agent R's design read, 2026-10-15, all adopted as rulings

The design read is `docs/Audit/price_cache_convention_guard_design_read_agent_r_2026_10_15.md` on
`review/agent-r-cache-guard`.

- **C-1, sequencing: the WRITER comes first, proven on a copy; the guard is switched on second.**
  No total-return writer exists in current code (`:765` is `adjustment="split"`; the yfinance
  fallback is `auto_adjust=False`). If the guard went live first, the first ex-date would refuse an
  append that nothing could satisfy, and the cache would stall stale across the universe.
  - **One provider per file, whole-file replace.** Files whose cached span starts on or after 2016
    are re-fetched from Alpaca (`adjustment="all"`). DEEP files (single names from 1970, SPY from
    1993) are re-fetched from yfinance (`auto_adjust=True`), because Alpaca's history cannot cover
    their span.
  - **A re-fetch that does not cover the cached span is refused.**
  - Mixing two providers' back-adjustments at a seam would be the T-082b class again.
- **C-2, cadence in numbers: the re-fetch branch is the STEADY STATE.** 33 of 39 names twinned over
  2023–2025 step at ex-dates, and 31 of those step quarterly.
  - Scaled to the cache, that is about 80% of ~730 files, roughly **580 whole-file re-fetches per
    quarter**.
  - Budget: at about 1–2 s per yfinance full-history download, that is **~10–20 min of network per
    quarter**, plus Alpaca for post-2016 files.
  - Every such pass is a **substrate re-pin**. The manifest's exact-match verify trips by design, so
    the re-pin is routine and quarterly, not an exception.
- **C-3, two rails the overlap test lacks, plus pair atomicity.**
  - **(a) The fetch MODE is asserted in a write record**, not assumed.
  - **(b) A seam-return rail:** the first appended bar's return against the last cached close must
    satisfy |r| < 25%, unless the overlap test itself reported a rescale. This catches an UNADJUSTED
    provider across a split. In that case the overlap matches and post-split bars append at a fraction
    of the price; `data/raw` WMT and AVGO show 66% and 90% one-day moves today.
  - **(c) The parquet + csv pair is written ATOMICALLY.** Both temp files are written first; a failure
    of either leaves both originals untouched. Readers use parquet first.
- **C-4, measure, don't record.**
  - **First write of a NEW ticker:** a two-mode ~60-day fetch (adjusted vs unadjusted). A stepped or
    drifting ratio records "measured TR"; an identical one records "unverified: no ex-date in window".
  - **Tolerance from the measured floor.** Quiet-day |Δ log ratio| is ≤ 3.7e-7 for SPY, XOM and KO,
    but 2.9e-5 for AAPL, because two-decimal adjusted closes round at 0.005/price. The floor is
    `0.005/price` per bar plus FP noise. "Constant ≠ 1" means the median departs from 1 by more than
    the floor. "Drift" is a SLOPE test on log ratio over time.
  - The §5 Stooq paragraph is rewritten below.

## 1. What the ruling rests on (merged at 0f7a013)

- **The cache is total return, measured.** The cache is dividend back-adjusted: processed/raw drift
  equals each name's yield. This was already true before T-082b: the pre-merge backup is identical
  on 1,513 days. The lock is `tests/test_processed_cache_adjustment_class_2026_10_15.py`.
- **Every stated intent says split-only.** The fetch requests `adjustment="split"`
  (`data_manager.py:765`), the yfinance fallback uses `auto_adjust=False`, and the comments and the
  T-082b merge premise say the same.
- **No double count under total return.** No dividend handling exists anywhere in `backtester/`,
  `engines/engine_c_portfolio/` or `orchestration/` (0 files match). The adjusted price is the only
  dividend channel, so equity-book PnL is total return, implicitly and consistently.
- **The fleet is already on the ruled convention.** `paper_trader/paper_client.py:298` fetches with
  `Adjustment.ALL`.

## 2. The design constraint the hazard implies: a back-adjusted series is NOT append-only

Every new ex-dividend date makes the provider rescale the series' **entire past**. So appending
freshly fetched total-return bars to a cached total-return history is a silent mix after any
dividend: the cached past is on the old scale and the new rows are on the new one. Checking the
adjustment *parameter* cannot catch this. The guard has to **measure an overlap window on every
write**.

## 3. The guard: one function, called by every writer

`check_cache_convention(cached, fetched, overlap_days=N)` sits in `data_manager`. Every refresh
fetches with the ruled convention (Alpaca `adjustment="all"`, yfinance `auto_adjust=True`) and
**includes an overlap of the last N cached days**. The function computes
`ratio = fetched_close / cached_close` on that overlap:

| overlap reads | meaning | action |
|---|---|---|
| ratio ≈ 1 on every day (within tolerance) | same convention, no rescale since last fetch | **append** |
| ratio constant ≠ 1 | a dividend or split since the last fetch rescaled history | **REFUSE the append**; the only valid write is a FULL re-fetch of the series, which is itself checked to cover the cached span. Never a local rescale guess |
| ratio drifts across the overlap | a different convention (split-only vs total return) | **REFUSE, fail-closed**, quoting the measured drift (%/yr) |
| no overlap (a new ticker) | nothing to compare against | write, and record the source + adjustment parameter in the write log, so the next write has an overlap |

- **Fail-closed means the cache keeps its last consistent state** and the refresh reports
  REFUSED/STALE loudly. A stale cache is visible; a mixed one is not.
- **The yfinance fallback is the live hazard today:** it writes split-only rows into a
  total-return cache. It moves to `auto_adjust=True` and goes through the same guard.
- **A full re-fetch changes the substrate**, so it trips the substrate manifest's exact-match verify.
  That is correct: a refreshed cache is a re-pin event, not a silent drift.

## 4. Who writes into the cache: step 1 of the unit, completed, not assumed

Found so far, by grepping write statements near `_1d` and processed/cache paths. This is **at
least** the list:
- `data_manager.save_cache` (`:658-690`) and the parquet write at `:386`;
- `scripts/fetch_data.py:63`;
- `scripts/fetch_missing_delisted.py:416`;
- `scripts/ingest_stooq_us_daily.py:169`;
- `scripts/build_multidecade_substrate_t306.py:77,82` (target dir to confirm);
- `scripts/merge_stooq_alpaca_substrate.py`;
- `scripts/regen_spy_full_history_t167.py`.

The unit completes the list with a grep plus an import trace. **Rule:** a script that writes into
the cache goes through `save_cache` and so through the guard; a direct writer is either routed
through it or retired to `Archive/`.

## 5. Statements corrected to match the ruling (item b), each citing 0f7a013 as the receipt

| where | now says | becomes |
|---|---|---|
| `data_manager.py:765` | `adjustment="split"`, "CRITICAL FIX" | `adjustment="all"`, behind the §3 guard (behaviour) |
| `data_manager.py` yfinance fallback | `auto_adjust=False` + the T-088 split-only rationale | `auto_adjust=True` + the guard; rationale rewritten (behaviour) |
| `scripts/merge_stooq_alpaca_substrate.py:1-40` | "Alpaca is split-only; Stooq is total-return" | **both premises inverted** (see below) |
| merge docstring's "price changes only; no dividend reinvestment" PnL text | price-only | total return via adjusted prices; no separate dividend channel exists (0 files) |
| `core/hermetic.py:10`, `scripts/submit_arms_campaign.py:157` | "the split-only cache" | "the total-return cache" |

**The Stooq record, corrected per era (R §3.4; the first version of this paragraph was wrong in
mechanism).** T-082b's `apply_dividend_strip` multiplies pre-seam Stooq by a smooth
`exp(a + b·t)`. That smears a constant yield into every pre-seam day: "price-only plus a daily
drip". It is approximately total return in level and over long windows, but every ex-date STEP is
replaced by a drift. A constant rescale could not have added dividend returns, and the sentence that
said it "converted" Stooq into total return is withdrawn.

- **The extent.** `data/processed/_merge_meta.json` records 626 of 730 files as `both`. Seams fall at
  2018-01-02 (484 names) and 2020-04-09 (108). For the median seam, about 70% of the 2000–2025 window
  is pre-seam.
- **Stooq itself is not one convention.** Stooq SPY carries dividends from about 2011, and not
  before: merged/Stooq drifts from 0.892 (2005) to 0.989 (2011), then holds flat. So T-256's
  "split-only" is true per era, not per provider. The unit's check is per ticker AND per era.
- **The convention, exactly:** total return EXACT post-seam; a constant-yield APPROXIMATION pre-seam.
  The director's record now says this on main.

**Tests (all execution, reversion-proven):**
- A fake provider covers the four overlap cases: append, refuse with re-fetch required, refuse with
  drift quoted, and a first write.
- Every writer in §4 is driven through the guard.
- The 0f7a013 data lock stays, and must still pass after the change.

## 6. Item (d), its own unit: the price-level filter scan

A read-only scan enumerating every rule that reads a price **level** rather than a return:
- minimum-price filters;
- dollar-volume and ADV thresholds;
- round-number or 52-week-high logic;
- any `close > X` predicate.

For each one: the site, what it reads, and how a deflated early-history level changes its output.
Each is then ruled one by one: keep, switch to the unadjusted level, or drop. Propose-first. I can
take it next.

## 7. Decisions requested

1. Approve §3–§5 as one propose-first unit. It runs after C's cells, because a refresh is a
   substrate change.
2. Assign item (d), the price-level scan.

## 8. Proof on a COPY: XOM (R's lock 2), 2026-10-15, real cache untouched (md5 verified)

`full_refetch("XOM", <scratch copy>, DEFAULT_PROVIDERS, today=2026-10-14)`:

- **Write record:**
  - provider `yfinance` (the span starts 1970, so not Alpaca);
  - mode `adjusted`;
  - span `1970-01-02 → 2026-10-14`, covering the cached `1970-01-02 → 2026-04-17`;
  - 14,318 rows;
  - basis **`measured_tr`** (a step on 2026-08-17 inside the 90-day window).
- **Ex-date steps against the split-only Alpaca raw bars, 2023–2025:** **12** in the re-fetch,
  **12** in the current cache, **on the same dates**.
- **Post-seam, re-fetch/cache = constant 0.98687 (2024–2026 median).** That is the rescale from the
  dividends since the cache's last bar. It is exactly the `RESCALED → full re-fetch` case, and the
  reason the re-fetch branch is the steady state.
- **Pre-seam, re-fetch/cache ≈ 1.10 (1990s median).** The writer replaces T-082b's constant-yield
  drip with exact ex-date total return. **The first full pass is therefore not a cosmetic refresh: it
  rewrites roughly 2000–2018 history for the ~626 `both` files** (about 10% in level for XOM in the
  1990s). Every deep-history measurement on this substrate becomes a re-pin event, and the B-1 panel
  md5 will change by design (R's lock 7: visible as a re-pin, never silent).

**Still to do (the full pass is ruled separately):**
- the writer inventory (§4, partial);
- the full pass on a copy of all ~730 files (lock 7: the 0f7a013 class lock holds; the B-1 panel md5
  moves visibly);
- only then, switching the guard on at the refresh paths.
