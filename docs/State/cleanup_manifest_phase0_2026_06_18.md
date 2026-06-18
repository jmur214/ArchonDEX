# Phase 0 Cleanup Manifest — VERIFIED safe-to-archive (2026-06-18)

Read-only verification by the code-health agent (every file grep-checked for live imports across
all packages + `.sh`/Dockerfile + execution_manual + ledger status). **Archive to `Archive/`, never
delete. Null the dangling pointers in the SAME change. Run the suite green before committing.**
Director executes the `git mv` after this review.

## SAFE TO ARCHIVE — ~16.3K LOC, 68 files → `Archive/scripts_t_one_offs_2026_06/`
- **63 T-xxx one-off scripts** in `scripts/` (~13.2K LOC) — zero live imports; the only cross-refs are
  script→script (archive together) or docstrings. Each ties to a closed/done ledger ticket. (Full
  table in the agent transcript; key clusters: the refuted-edge harnesses T-117/122/123/129/135/137/
  144/145/149/174, the foundry T-193/195/196, the HMM T-103/105, the regime/PIT diagnostics.)
- **path_c**: `path_c_synthetic_compounder.py` (1,672, self-labeled "DESIGN-PHASE, not production") +
  `path_c_overlays.py` (323). **Dangling pointer to null in the same change:** drop the
  `("scripts.path_c_synthetic_compounder", …)` tuple from `ISOLATED_GLOBALS` in
  `scripts/run_isolated.py:156-157` (the reset is already a proven no-op), and relocate/fix
  `tests/test_path_c_real_fundamentals.py` + the path_c case in `tests/test_run_isolated_globals.py`.
- **Non-T sleeve cluster** (+1,079 LOC, not caught by the `t[0-9]` glob): `sleeve_phase0_verdict.py`
  (533), `run_diversified_futures_trend.py` (508), `run_trend_wider_universe.py` (38).

## KEEP — verified NOT safe (do NOT archive)
- **Operational (in-flight): `land_held_position_t201.py` + `first_real_fill_t186.py`** — the 6/22 CLS
  landing tools (T-202 in-flight). **`build_membership_panel_t136.py`** — `membership.py:42` instructs
  building the live PIT panel Phase 2 consumes.
- **execution_manual-documented (9):** `crisis_replay_t118b.py`, `calibrate_divergence_monitors_t152`,
  the 6 `demo_*` scripts (t139/141/146/148/151 + t139_fixture_data).
- **Borderline:** `run_paper_day_t163.py` (archivable only after nulling a docstring pointer in
  `cockpit/dashboard_v2/utils/paper_loader.py:9`).
- **Out of scope (live):** `run_isolated.py`, `engines/.../sleeves/`, `sleeve_gauntlet.py`.

## The 14 private Sharpe reimplementations (for C/T-203 to consolidate onto core)
Of the 14, #1-9 archive WITH the SAFE list; **#10-14 must be repointed onto `core/metrics_engine`:**
`run_benchmark.py` (SPY Sharpe inline), `edge_compression_t117.py`, `analyze_overnight_intraday_t135`,
`regime_sleeve_sizer_t178`, `analyze_per_edge_isolation.py` — plus the KEEP `crisis_replay_t118b.py`
(private `_annualized_from_daily` + bootstrap-CI). C audits each for custom logic before repointing.

## `live_trader/` ghost (propose-first — it's the rules file)
`live_trader/` does not exist; the real path is `paper_trader/`. Stale guard refs in **CLAUDE.md lines
247, 314, 326** (+ likely `docs/Core/NON_NEGOTIABLES.md`). DO NOT just delete — the guard may protect a
FUTURE real-money `live_trader/`; redirect/clarify it propose-first rather than dropping the protection.
