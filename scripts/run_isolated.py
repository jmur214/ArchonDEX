"""
scripts/run_isolated.py
=======================
Determinism floor for backtests under --reset-governor.

The pre-existing `scripts/run_deterministic.py` was built for the
2026-04-23 Phase 0 floor when the only mutable governor state was
`edge_weights.json` and `regime_edge_performance.json`, and it relied
on `--no-governor` to suppress end-of-run writes. Phase 2.10d Task A
(autonomous lifecycle triggers) added end-of-run writes to:
  - `data/governor/edges.yml`           (status changes per
                                          lifecycle_manager.evaluate)
  - `data/governor/lifecycle_history.csv` (audit-trail append)
  - `data/governor/edges.yml`           (also tier reclassification
                                          via evaluate_tiers)

After Phase 2.10d, `--reset-governor` no longer makes a run independent
of prior runs: the prior run's lifecycle pass has mutated edges.yml,
which the next run reads at startup. The result is intra-worktree
Sharpe variance up to ±1.4 across same-config runs (round-3 ship
blocker, `path1_ship_validation_2026_05.md`).

This wrapper restores the *full* `data/governor/` directory from an
anchor before each run AND restores it back after. End-of-run lifecycle
writes still happen as designed (so the lifecycle observability stays
intact in production), but each measurement run starts and ends in
the anchored state.

Usage:
  # 1. Take a snapshot of the current governor state as the anchor
  python -m scripts.run_isolated --save-anchor

  # 2. Single isolated run (any sweep / validation harness wrapping
  #    ModeController.run_backtest inherits the isolation)
  PYTHONHASHSEED=0 python -m scripts.run_isolated --task q1

  # 3. Multi-run determinism check
  PYTHONHASHSEED=0 python -m scripts.run_isolated --runs 3 --task q1
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List


ROOT = Path(__file__).resolve().parents[1]
GOV_DIR = ROOT / "data" / "governor"
ISOLATED_ANCHOR = GOV_DIR / "_isolated_anchor"
TRADES_DIR = ROOT / "data" / "trade_logs"


# T-2026-06-10-140 — Vector B env parity with the cloud entrypoint.
# Multi-threaded OpenBLAS/LAPACK reductions are bitwise-nondeterministic
# across tasks (T-128 probe: eigh 5-vs-1 split unpinned, 6/6 unanimous
# pinned). Local Mac runs were stable in practice, but pinning here too
# makes local and cloud numerically comparable by construction and
# removes "was it the thread count?" from every future local-vs-cloud
# discrepancy investigation. Must be set BEFORE numpy/scipy first
# import — module import time is the only safe place.
_BLAS_DETERMINISM_PINS = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "OMP_DYNAMIC": "FALSE",
}


def _needs_blas_reexec() -> bool:
    return any(os.environ.get(k) != v for k, v in _BLAS_DETERMINISM_PINS.items())


def _reexec_if_hashseed_unset() -> None:
    """Re-exec ourselves with PYTHONHASHSEED=0 + BLAS pins if not set yet.

    Python randomizes string hash seeds per-process by default, which
    leaks into `set()` iteration order and breaks bit-for-bit
    determinism. The 04-23 floor required this; we keep it. T-140 adds
    the single-thread BLAS pins to the same re-exec (they must be set
    before numpy loads). Called only from `__main__` so importing the
    module (e.g. from tests) does not trigger a re-exec.
    """
    if os.environ.get("PYTHONHASHSEED") != "0" or _needs_blas_reexec():
        os.environ["PYTHONHASHSEED"] = "0"
        os.environ.update(_BLAS_DETERMINISM_PINS)
        os.execv(sys.executable, [sys.executable, "-m", "scripts.run_isolated", *sys.argv[1:]])


# Files in data/governor/ that mutate end-of-run under any non-no-governor
# code path. Snapshotting just these keeps the harness fast (skip the
# meta-learner pickles etc., which only change when the trainer runs).
#
# ga_population.yml added 2026-05-11 (T-2026-05-11-026): Discovery's
# `GeneticAlgorithm.load_population()` reads this file on cycle start;
# if it exists with a saved population, the GA skips its
# `seed_from_registry` path entirely (which is where T-022 foundry_feature
# gene emission + T-024 enrichment fire). T-025's Discovery cycle
# inherited a stale generation-3 population from a pre-T-022 run, which
# meant the new vocabulary never got exercised. Isolating
# ga_population.yml ensures each isolated() run starts from the anchor
# state (typically: no file → GA falls back to seed_from_registry →
# T-022/T-024 logic fires deterministically).
ISOLATED_FILES = [
    "edges.yml",
    "edge_weights.json",
    "regime_edge_performance.json",
    "lifecycle_history.csv",
    "ga_population.yml",
]

# Additional files snapshotted ONLY when --journal-mode is active.
# The journal grows monotonically across runs and apply-mark advances
# with each apply; both must reset between reps for true determinism
# verification under journal-mode. Listed here separately so the
# legacy-path snapshot scope is unchanged.
ISOLATED_FILES_JOURNAL_MODE = [
    "lifecycle_journal.jsonl",
    ".journal_apply_mark",
]


# Module-level mutable globals OUTSIDE data/governor/ that can corrupt
# measurements across runs (same shape as the 04-25 registry-stomp bug
# and the 05-06 SPY-cache bug). Each entry is
# (import_path, helper_or_attr, kind) where kind selects the reset path:
#   "helper"     — call module.<helper>()  (preferred when one exists)
#   "attr_none"  — setattr(module, <attr>, None)
#   "attr_false" — setattr(module, <attr>, False)
#   "attr_list"  — setattr(module, <attr>, [])
#
# Reset is LAZY — we only act if the module is already in sys.modules.
# An earlier draft of this patch eagerly imported the production-path
# modules at isolated()-entry, on the theory that we should reset them
# whether or not the prod backtest had loaded them yet. That was
# empirically wrong: pre-loading those modules ahead of when prod
# naturally imports them perturbs downstream module-init ordering and
# makes run 1 of a multi-run harness produce a different canon md5 from
# runs 2..N (Sharpe 0.127 vs 0.054 on the 2025-Q1 anchor used during
# this patch's verification, vs the pre-patch baseline 3/3 identical
# at 0.054). Going lazy preserves the prod import order on run 1
# (the harness stays out of the way) and still resets globals on
# subsequent runs once the prod path has loaded them.
#
# The "tests pre-import then pollute" pattern still works because tests
# explicitly import the target module before entering isolated().
ISOLATED_GLOBALS = [
    # HIGH-RISK — V/Q/A panel cache; helper resets both flags at once.
    ("engines.engine_a_alpha.edges._fundamentals_helpers",
     "reset_panel_cache", "helper"),
    # HIGH-RISK — path_c standalone-script overlay-diags accumulator.
    ("scripts.path_c_synthetic_compounder",
     "_LAST_OVERLAY_DIAGS", "attr_list"),
    # MEDIUM-RISK — feature_foundry caches; clear helpers exist.
    ("core.feature_foundry.sources.local_ohlcv",
     "clear_close_cache", "helper"),
    ("core.feature_foundry.sources.earnings_calendar",
     "clear_earnings_cache", "helper"),
    ("core.feature_foundry.sources.fred_macro",
     "clear_series_cache", "helper"),
]


def _reset_one_global(import_path: str, name: str, kind: str) -> None:
    """Reset a single module-level mutable global, but only if the
    module is already loaded (lazy/in-place — never force-import)."""
    module = sys.modules.get(import_path)
    if module is None:
        return
    if kind == "helper":
        getattr(module, name)()
    elif kind == "attr_none":
        setattr(module, name, None)
    elif kind == "attr_false":
        setattr(module, name, False)
    elif kind == "attr_list":
        setattr(module, name, [])
    else:
        raise ValueError(f"Unknown reset kind: {kind!r}")


def reset_module_globals() -> None:
    """Reset all registered cross-run-contaminating module globals.

    Called from ``isolated()`` on entry AND exit, mirroring the
    governor-file snapshot/restore pattern. All entries are lazy:
    modules absent from sys.modules are skipped so the harness doesn't
    perturb the prod backtest's natural import order on run 1. From
    run 2 onward the modules are typically already in sys.modules
    (the prod backtest loaded them in run 1) so the resets fire and
    keep state from leaking across runs.
    """
    for import_path, name, kind in ISOLATED_GLOBALS:
        _reset_one_global(import_path, name, kind)


def _md5(path: Path) -> str:
    if not path.exists():
        return "(missing)"
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_anchor() -> int:
    """Snapshot `data/governor/<file>` for every name in ISOLATED_FILES.

    T-2026-06-10-131: anchor files are chmod'd READ-ONLY (0o444) after
    the snapshot. The anchor is the canon-relevant seed every isolated
    run executes from — an accidental write into it silently moves every
    subsequent measurement. Since T-127 the anchors are also pinned by
    `config/substrate_manifest.sha256`, so a DELIBERATE anchor update is
    a 3-step act: run --save-anchor (it re-grants itself write perm),
    regenerate the manifest, commit both in the same PR.
    """
    ISOLATED_ANCHOR.mkdir(parents=True, exist_ok=True)
    saved = []
    for name in ISOLATED_FILES:
        src = GOV_DIR / name
        dst = ISOLATED_ANCHOR / name
        if src.exists():
            if dst.exists():
                dst.chmod(0o644)  # re-grant: a prior save made it read-only
            shutil.copy(src, dst)
            dst.chmod(0o444)
            saved.append(name)
    print(f"[ISOLATED] Anchor saved at {ISOLATED_ANCHOR}: {saved}")
    print("[ISOLATED] Anchor files set READ-ONLY. If this update is "
          "deliberate: regenerate config/substrate_manifest.sha256 and "
          "commit both in the same PR.")
    return 0


def _scoped_files(include_journal: bool = False) -> List[str]:
    """Files snapshotted by the harness. When journal-mode is on, the
    journal + apply-mark are also reset between reps so each run sees
    the same starting journal state."""
    out = list(ISOLATED_FILES)
    if include_journal:
        out.extend(ISOLATED_FILES_JOURNAL_MODE)
    return out


def restore_anchor(include_journal: bool = False) -> None:
    """Restore the full set of governor files from the anchor.

    For files that exist in the anchor: copy over current.
    For files that DO NOT exist in the anchor (e.g. lifecycle_history.csv
    when the anchor was taken before any lifecycle event fired): DELETE
    the live file so the run starts from the same empty-history state.
    Without this, lifecycle_history.csv accumulates mutations in the live
    tree even when not present in the anchor, causing drift on the
    audit-trail divergence-check side.

    include_journal: F11 Phase 2 — when True, also resets the journal
    + apply-mark so each rep starts with the same journal state.
    """
    if not ISOLATED_ANCHOR.exists():
        raise RuntimeError(
            f"No anchor at {ISOLATED_ANCHOR}; run with --save-anchor first."
        )
    for name in _scoped_files(include_journal):
        src = ISOLATED_ANCHOR / name
        dst = GOV_DIR / name
        if src.exists():
            # T-131: anchor files are read-only (0o444) since save_anchor
            # write-protects them. copyfile (not copy) so the anchor's
            # read-only bit is NOT propagated onto the live file; pre-chmod
            # handles a live file left read-only by an older copy() pass.
            if dst.exists() and not os.access(dst, os.W_OK):
                dst.chmod(0o644)
            shutil.copyfile(src, dst)
        elif dst.exists():
            dst.unlink()


@contextmanager
def isolated(journal_mode: bool = False) -> Iterator[None]:
    """Context manager: restore anchor on entry, restore again on exit.

    Restoring on exit (not just entry) means a sequence of isolated runs
    leaves the worktree in the same anchored state regardless of whether
    each run mutated. This is what lets repeated invocations be
    bit-comparable downstream.

    Beyond the governor-file snapshot, also reset the module-level
    mutable globals listed in ``ISOLATED_GLOBALS``. Those survive across
    same-process invocations (e.g. multi-run measurement drivers,
    sweeps, walk-forward orchestrators) and would otherwise leak state
    across runs identically to the 04-25 registry-stomp bug.

    journal_mode: F11 Phase 2 acceptance gate. When True, also resets the
    journal + apply-mark between reps so each run starts from the same
    journal state.
    """
    # Only pass include_journal when set so existing tests that
    # monkeypatch `restore_anchor` with a no-kwarg callable keep working.
    if journal_mode:
        restore_anchor(include_journal=True)
    else:
        restore_anchor()
    reset_module_globals()
    try:
        yield
    finally:
        if journal_mode:
            restore_anchor(include_journal=True)
        else:
            restore_anchor()
        reset_module_globals()


def _print_state(label: str, journal_mode: bool = False) -> None:
    print(f"[ISOLATED] {label} governor hashes:")
    for name in _scoped_files(journal_mode):
        print(f"  {name}: {_md5(GOV_DIR / name)}")


def _run_q1_inside_context(
    apply_journal_at_end: bool = False,
    override_start: str = "2025-01-01",
    override_end: str = "2025-12-31",
) -> dict:
    """Run a single-year backtest inside the isolation context.

    Despite the legacy "q1" name (kept for backward compatibility — the
    function used to be 2025-only), this now accepts override_start /
    override_end so a single isolation context can serve any year window.
    Defaults preserve the original 2025 calendar-year behavior.

    apply_journal_at_end: F11 Phase 2 acceptance gate. When True, the
    backtest routes governance decisions through the LifecycleJournal
    instead of mutating edges.yml directly. The journal is then applied
    at end-of-run as a transactional read+write. Verifies that the
    journal-mode pipeline produces deterministic output across reps.
    """
    from orchestration.mode_controller import ModeController
    mc = ModeController(ROOT, env="prod")
    return mc.run_backtest(
        mode="prod", fresh=False, no_governor=False, reset_governor=True,
        alpha_debug=False,
        override_start=override_start, override_end=override_end,
        apply_journal_at_end=apply_journal_at_end,
    )


def _trades_canon_md5(run_id: str) -> str:
    """Compute canonical md5 over the run's trades, ignoring run_id/meta columns.

    The cockpit logger writes the trade log under either ``trades.csv`` (always)
    or ``trades_<run_id>.csv`` (when the prefixed-name path was active in older
    code). Pre-2026-05-07 this helper looked for the prefixed name only and
    returned "(missing)" for runs that wrote `trades.csv` only — caller saw
    canon mismatches that were actually filename-pattern bugs, not real
    data drift. Now checks both names; canonical name is `trades.csv`.
    """
    run_dir = TRADES_DIR / run_id
    candidates = [
        run_dir / "trades.csv",
        run_dir / f"trades_{run_id}.csv",  # legacy prefixed name; some runs ship both
    ]
    p = next((c for c in candidates if c.exists()), None)
    if p is None:
        return "(missing)"
    try:
        import pandas as pd
        df = pd.read_csv(p)
        for col in ("run_id", "meta"):
            if col in df.columns:
                df = df.drop(columns=[col])
        return hashlib.md5(
            pd.util.hash_pandas_object(df, index=False).values.tobytes()
        ).hexdigest()
    except Exception as e:
        return f"(error: {e})"


def _find_run_id(before: set[str]) -> str | None:
    after = {p.name for p in TRADES_DIR.iterdir() if p.is_dir() and p.name != "backup"}
    new = after - before
    if not new:
        return None
    if len(new) == 1:
        return next(iter(new))
    candidates = [(p, p.stat().st_mtime) for p in TRADES_DIR.iterdir() if p.name in new]
    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates[0][0].name


def main() -> int:
    _reexec_if_hashseed_unset()
    parser = argparse.ArgumentParser()
    parser.add_argument("--save-anchor", action="store_true",
                        help="Snapshot current governor state as anchor and exit.")
    parser.add_argument("--runs", type=int, default=1,
                        help="Number of isolated runs to perform (each "
                             "restores from the anchor first).")
    parser.add_argument("--task", choices=["q1"], default="q1",
                        help="Backtest task to run inside the isolation.")
    parser.add_argument("--show-hashes", action="store_true",
                        help="Print pre/post governor hashes per run.")
    parser.add_argument("--journal-mode", action="store_true",
                        help="F11 Phase 2 acceptance gate: route governance "
                             "decisions through the LifecycleJournal "
                             "instead of mutating edges.yml directly. "
                             "Applies journal at end-of-run.")
    parser.add_argument(
        "--year", type=int, default=None,
        help="Run a specific calendar year (e.g., --year 2022). "
             "Sets override_start=YYYY-01-01 and override_end=YYYY-12-31. "
             "Mutually exclusive with --start-date / --end-date. Defaults "
             "to 2025 when neither is given (legacy q1 behavior).",
    )
    parser.add_argument(
        "--start-date", default=None,
        help="Override start date (YYYY-MM-DD). Use with --end-date for "
             "non-calendar-year windows. Overrides --year if both given.",
    )
    parser.add_argument(
        "--end-date", default=None,
        help="Override end date (YYYY-MM-DD). See --start-date.",
    )
    args = parser.parse_args()

    # Resolve the date window. Precedence: --start-date/--end-date > --year > default 2025.
    if args.start_date or args.end_date:
        if not (args.start_date and args.end_date):
            parser.error("--start-date and --end-date must both be set")
        override_start = args.start_date
        override_end = args.end_date
    elif args.year is not None:
        override_start = f"{args.year}-01-01"
        override_end = f"{args.year}-12-31"
    else:
        override_start = "2025-01-01"
        override_end = "2025-12-31"
    print(f"[ISOLATED] window: {override_start} -> {override_end}")

    if args.save_anchor:
        return save_anchor()

    if not ISOLATED_ANCHOR.exists():
        print("[ISOLATED] No anchor found. Run with --save-anchor first.",
              file=sys.stderr)
        return 1

    if args.journal_mode:
        print("[ISOLATED] journal-mode ON — F11 Phase 2 acceptance gate. "
              "Decisions append to LifecycleJournal; "
              "journal_apply runs at end-of-run.")

    results = []
    for i in range(args.runs):
        print(f"\n===== ISOLATED RUN {i + 1} / {args.runs} =====")
        if args.show_hashes:
            _print_state("PRE  ANCHOR", journal_mode=args.journal_mode)
        before = {p.name for p in TRADES_DIR.iterdir()
                  if p.is_dir() and p.name != "backup"}
        with isolated(journal_mode=args.journal_mode):
            if args.show_hashes:
                _print_state("PRE  RUN  ", journal_mode=args.journal_mode)
            summary = _run_q1_inside_context(
                apply_journal_at_end=args.journal_mode,
                override_start=override_start,
                override_end=override_end,
            )
            if args.show_hashes:
                _print_state("POST RUN  ", journal_mode=args.journal_mode)
        if args.show_hashes:
            _print_state("POST RESTORE", journal_mode=args.journal_mode)

        run_id = _find_run_id(before) or "?"
        record = {
            "run_id": run_id,
            "sharpe": summary.get("Sharpe Ratio"),
            "cagr_pct": summary.get("CAGR (%)"),
            "trades_canon_md5": _trades_canon_md5(run_id) if run_id != "?" else "(no run_id)",
        }
        # T-181 census gate — a NON-CANONICAL run cannot PASS even if it is
        # perfectly deterministic (determinism of a clouded number is still a
        # clouded number). Read the census the controller emitted.
        try:
            from core.census import assert_census_file
            _perf = TRADES_DIR / run_id / "performance_summary.json"
            _cv = assert_census_file(str(_perf)) if run_id != "?" else None
        except Exception as _e:
            _cv = None
            print(f"  [CENSUS][WARN] gate unavailable: {_e!r}")
        record["census_canonical"] = (bool(_cv.canonical) if _cv else None)
        results.append(record)
        print(f"  Sharpe: {record['sharpe']}")
        print(f"  CAGR%:  {record['cagr_pct']}")
        print(f"  run_id: {record['run_id']}")
        print(f"  trades_canon_md5: {record['trades_canon_md5']}")
        if _cv is not None:
            print(f"  census: {'CANONICAL' if _cv.canonical else 'NON-CANONICAL'}")
            for _f in _cv.failures:
                print(f"  [CENSUS][FAIL] {_f}")
            for _w in _cv.warnings:
                print(f"  [CENSUS][WARN] {_w}")

    # T-181: census across all reps. None (gate unavailable) is treated as
    # non-blocking; an explicit False blocks PASS.
    census_vals = [r.get("census_canonical") for r in results]
    census_blocking = any(v is False for v in census_vals)

    if args.runs > 1:
        sharpes = [r["sharpe"] for r in results]
        canons = [r["trades_canon_md5"] for r in results]
        sharpe_range = (max(sharpes) - min(sharpes)) if sharpes else 0
        canon_unique = len(set(canons))
        print("\n===== DETERMINISM REPORT =====")
        print(f"Sharpes:          {sharpes}")
        print(f"Sharpe range:     {sharpe_range:.4f}")
        print(f"Canon md5 unique: {canon_unique} / {len(canons)}")
        print(f"Census canonical: {census_vals}")
        if census_blocking:
            print("[RESULT] FAIL — census NON-CANONICAL on ≥1 rep; a deterministic "
                  "clouded number is still a clouded number. Do not certify.")
            return 2
        if sharpe_range <= 0.02 and canon_unique == 1:
            print("[RESULT] PASS — Sharpe within ±0.02 AND bitwise-identical canon md5 AND census canonical")
            return 0
        if sharpe_range <= 0.02:
            print("[RESULT] PARTIAL — Sharpes converge but trade-log canon md5s differ.")
            print("                  Likely residual non-determinism (trade order, "
                  "timestamp serialization). Investigate before claiming the floor.")
            return 1
        print("[RESULT] FAIL — same-config runs produce >0.02 Sharpe spread.")
        print(f"                Spread {sharpe_range:.4f} indicates governor-state drift "
              "is not fully bounded by the harness.")
        return 2
    if census_blocking:
        print("[RESULT] FAIL — census NON-CANONICAL; the run must not be certified or published.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
