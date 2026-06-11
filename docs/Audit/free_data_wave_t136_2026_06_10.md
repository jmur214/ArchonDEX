---
task_id: T-2026-06-10-136
title: Free data wave pt.1 — PIT membership + survivor-inflation + insider feed + positioning/alt archivers
date: 2026-06-10
author: Agent D (re-routed from A)
outcome: HEADLINE — the survivor-only substrate inflates the EW-universe CAGR by
  ~10pp/yr (18.67% survivor → 8.52% membership-correct+Shumway; band 7.2–12.7pp;
  Sharpe inflation 0.21–0.44). Norgate rule resolves: worst-case band flips NO
  standing go/no-go (all already negative/not-validated) → $630 DEFERRED.
  Insider-feed claim reconciled (my T-132 "0-byte" was a du-on-symlink artifact —
  feed existed; edge was never broken, clusters are just rare); canonical SEC
  structured feed landed (6.89M transactions, 21,057 tickers, 2006-2026) + edge
  smoke PASS. Positioning + alt-data archivers shipped and hoarding.
status: CURRENT
reproduce: |
  python -m scripts.build_membership_panel_t136
  PYTHONHASHSEED=0 python -m scripts.measure_survivor_inflation_t136  (determinism PASS ×2)
  python -m scripts.wire_sec_insider_feed_t136 --start 2006q1 --end 2026q1
  python -m scripts.archive_positioning_t136 ; python -m scripts.archive_altdata_t136
---

# T-136 — the free data wave, part 1

## Part A — PIT membership layer + the survivor-inflation number

**Panel:** fja05680/sp500 (primary) → 1,255 membership intervals, 1,202
tickers, 1996-2026, `data/universe/sp500_membership.parquet` + loader
`engines/data_manager/membership.py` (load_membership / members_on / in_index).
**Cross-checks:** repo-internal date-stamped component lists at 5 sample dates:
99.8–100% agreement; Wikipedia current constituents: 100%. Pre-2000 accuracy
caveat documented in the meta sidecar.

**The measurement (pre-registered; EW substrate object, 2000-2025):**

| universe | CAGR | Sharpe (ci) | inflation vs survivor |
|---|---|---|---|
| **survivor (status quo — what T-129/T-135 rode)** | **18.67%** | 0.915 [0.54, 1.30] | — |
| (a) membership-only | 11.51% | 0.702 [0.32, 1.07] | **−7.2pp CAGR, −0.21 Sharpe** |
| (b) + Shumway (−30/−55; missing-path × 0.49 merger prior) | 8.52% | 0.635 [0.26, 1.01] | **−10.2pp, −0.28** |
| (c) worst-case (−100% all performance+missing exits) | 6.01% | 0.474 [0.09, 0.84] | **−12.7pp, −0.44** |

Coverage: 1,081 members in-window; 684 have price files; **397 have none**
(the residual Norgate addresses). Exit classification (heuristic, flagged;
Form-25 verification deferred): 404 missing_path / 172 still_listed /
41 merger_like / 5 performance-with-path.

**The Norgate $630 decision (adopted rule):** the (b)→(c) spread is 2.5pp
CAGR / 0.16 Sharpe. NO standing go/no-go conclusion flips inside that band —
every alpha verdict (T-117→135) is already negative/zero and a more
pessimistic substrate only deepens them; the "0.81 12-yr plausibly-real"
baseline was already not-validated and moves further away. **→ imputation-
with-caveats suffices; the $630 is DEFERRED.** Standing re-trigger: a future
verdict sitting inside the band, or going small-cap/short.

**Method notes (honest record):** first cut averaged LOG returns — a −100%
imputation (log −9.2) blows past the −1/N bound a real portfolio has; fixed
to arithmetic EW with a MEMBER-COUNT denominator (a day where only an imputed
exit has data must not become a 1-name portfolio). Days with <50 members
dropped. Determinism PASS ×2 (seed 0, no wall-clock in artifact).

**Scope flag:** this is the SUBSTRATE-level inflation number. A full
PIT-correct **arm0 ENGINE** re-run needs a per-date universe hook in
`universe_resolver` (it currently returns one static union per run) — flagged
as the follow-up dispatch, not smuggled in here.

**Manifest (A4):** `data/universe/` is NOT baked into the image (Dockerfile
copies only processed/raw/governor) → no manifest regen required. Wiring it
in (Dockerfile COPY + `SUBSTRATE_DIRS` extension in
`gen_substrate_manifest.py`) is a build-infra change on the T-127-pinned
pipeline → **propose-first, director call** (same applies to `data/edgar/`,
`data/insider_sec/`, `data/positioning/`, `data/macro_data/alt/`).

## Part B — insider-feed reconciliation + SEC structured wiring

**The reconciliation (my claim to settle, settled):** my T-132 "feed is 0
bytes" was a **tooling artifact — macOS `du -sh` reports a SYMLINK as 0B
without following it.** `data/insider` in the agent worktree is a symlink to
the main worktree, which has held 641 openinsider parquets (2003-2025) since
Apr-27. The director's spot-check was right; my claim was wrong; the
correction propagates to the T-132 map (the "0-byte feed" line). Residual
truth in the original observation: the edge emitted all-zero signals in the
2021-24 panel — root cause is NOT a broken loader (index = DatetimeIndex,
`transaction_type` 'P'/'S' exactly as the edge filters): insider BUY-clusters
(≥3 distinct insiders in 60d) are genuinely RARE on large caps. The edge was
never broken — just sparse.

**Canonical SEC feed landed:** `scripts/wire_sec_insider_feed_t136.py` —
SEC Insider Transactions structured datasets (quarterly ZIPs, public domain),
2006q1→2026q1 = **6,888,032 transactions → 21,057 ticker parquets** in
`data/insider_sec/`, exact `INSIDER_TXN_COLUMNS` format. 4/A amendments
deduped (last filing per economic transaction). Junk raw symbols quarantined
(not deleted). Production repoint = a one-line
`InsiderDataManager(cache_dir=...)` flip — **propose-first, not done** (edge
logic untouched per brief).
*Why ZIPs not a fetcher form-filter:* the submissions API carries filing
METADATA only — transaction contents (shares/price/code) need the structured
sets; the T-137 fetch pattern (cache-first, rate-limited, UA) is reused.

**Edge smoke: PASS** — 5/200 universe names emit non-zero cluster signals on
the new feed at 2025-09-30 with one quarter loaded (CE, CHD, COO, COTY, EMN;
0.08-0.18). Non-zero, sparse, and direction-sensible = feed + edge verified
end-to-end. Gauntlet = next dispatch (per brief, data-engineering only here).

## Part C — positioning archivers (hoard-now)

`scripts/archive_positioning_t136.py` — idempotent, failure-isolated, cron-able.
First pulls banked in `data/positioning/`:

| source | status |
|---|---|
| FINRA Reg SHO daily short volume | ✓ 92,689 rows (8 days; CNMS consolidated; short volume ≠ short interest — documented) |
| SEC fails-to-deliver | ✓ 112,558 rows |
| FINRA bi-monthly short interest | ✓ 21,896 rows (legacy CSV path live; api.finra.org migration noted as the fallback if it dies) |
| NAAIM exposure | ✓ 1,041 rows (full since-inception) |
| FINRA margin debt | ✓ inline-table (13 rows; shallow but archiving) |
| AAII sentiment | LOGIN-WALLED (free account) — documented manual procedure, not automated (per brief) |

## Part D — alt-data + forward archivers

`scripts/archive_altdata_t136.py` (+ `scripts/_xlsx_min.py`, a 40-line stdlib
.xlsx reader written because openpyxl/xlrd are absent and new deps are
propose-first). Banked in `data/macro_data/alt/`:

| source | status |
|---|---|
| EPU daily US (1985+) | ✓ 15,135 rows + monthly 1,518 (vintage-stamped; constructed-index revision caveat) |
| GPR | **flagged:** source ships legacy binary .xls only — unparseable without xlrd → **dep approval ask** (openpyxl+xlrd, one line) or manual convert |
| GDELT tone timelines | partial: recession bucket banked (345d); others hit the 1-req/5s limiter — idempotent archiver self-heals on schedule. **1979+ bulk events = BigQuery job, flagged follow-up** |
| Polymarket snapshots | ✓ 342 macro-bucket markets (first snapshot banked) |
| Kalshi snapshots | ✓ 5 macro-bucket markets (public API worked) |

## Follow-ups for the director (ranked)

1. **Schedule the archivers** (cron: positioning daily, alt-data daily/weekly) —
   every unscheduled week loses depth.
2. **PIT universe_resolver hook** → the full membership-correct arm0 engine
   re-run (the A3 number says the substrate story changes materially).
3. **Insider repoint flip** (`cache_dir='data/insider_sec'`) + insider-cluster
   gauntlet with the T-137 StepM discipline.
4. **Dep approval ask:** openpyxl+xlrd (unlocks GPR + future Excel sources).
5. **Bake/manifest decision** for the new data dirs (Dockerfile + SUBSTRATE_DIRS).

## Files (all committed; data stays gitignored, reproducible from scripts)

scripts/{build_membership_panel,measure_survivor_inflation,wire_sec_insider_feed,
archive_positioning,archive_altdata}_t136.py, scripts/_xlsx_min.py,
engines/data_manager/membership.py, this audit.

## NOT included
Engine/edge logic edits (none); production feed repoint (propose-first);
TASK_LEDGER write (T-114); full arm0 PIT re-run (needs resolver hook);
gauntlet runs (next dispatch). N_trials += 0 (substrate measurement, no
strategy trials).
