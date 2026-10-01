"""RR-1 RE-SCORE driver — one cell, one arm, one record.

RE-SCORE, not a new trial (N_trials 0): the same historical cell run under the
uncorrected and corrected controller, so the before/after pair differs ONLY by the fix.

THE "BEFORE" ARM. The only runtime difference between `main` and the RR-1 branch is
`BacktestController.get_portfolio_capital`. The before arm restores its old semantics
in-process — it returned the seed capital, never updated. That restoration was PROVEN
equivalent to main's code before any cell ran: a patched run reproduces main's golden
master bit-for-bit (Sharpe 0.04946327837452345, 171 trades, identical turnover and max
position). Running both arms in one tree is what makes the pair a clean measurement:
same machine, same substrate, same day.

RAILS (director ruling, 2026-09-30):
  * run SEQUENTIALLY — run_isolated and the foundry harness both write this worktree's
    live governor files on entry, so two cells at once would collide;
  * wrap every invocation in `caffeinate -i` — a sleeping Mac kills a multi-hour cell;
  * a DISK FLOOR — refuse to start below MIN_FREE_GB, never push through.

Usage:
  caffeinate -i python scripts/rescore_rr1.py --arm before --cell baseline \
      --start 2000-01-01 --end 2025-12-31 --label anchor26
  caffeinate -i python scripts/rescore_rr1.py --arm after --cell feature \
      --feature mom_12_1 --label t196_mom
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

MIN_FREE_GB = 5.0
OUT_DIR = REPO / "docs" / "Measurements" / "2026-09" / "rr1_rescore"


# run_isolated.main() RE-EXECS ITSELF (os.execv) unless these are already set — its first
# line is _reexec_if_hashseed_unset(). An exec replaces the process image, so it discards
# everything this driver did in-process — INCLUDING the before arm's restored getter. The
# re-exec'd process loads the FIXED controller from disk. So without these, the BEFORE arm
# silently runs the AFTER code, the pair is identical, and the RE-SCORE reports that the
# fix changes nothing: a confident null manufactured by the harness. (It also took two
# calibration records with it, which is how it was found.)
# They must be set before numpy loads, i.e. in the LAUNCHING environment — never here.
REQUIRED_ENV = {"PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1", "OMP_DYNAMIC": "FALSE"}


def _missing_reexec_env() -> dict:
    return {k: os.environ.get(k) for k, v in REQUIRED_ENV.items() if os.environ.get(k) != v}


def _free_gb() -> float:
    return shutil.disk_usage(REPO).free / 1e9


def _restore_old_getter() -> None:
    """The BEFORE arm: the getter as it was on main — the seed capital, never updated.

    Bare objects without `initial_capital` (the probe's side detector builds one) fall
    through to cash; a real controller always has it, set at __init__."""
    import backtester.backtest_controller as bc
    bc.BacktestController.get_portfolio_capital = (
        lambda self: float(getattr(self, "initial_capital", 0.0) or self.portfolio.cash))


def _git(*a: str) -> str:
    return subprocess.run(["git", *a], cwd=REPO, capture_output=True, text=True).stdout.strip()


def _baseline(start: str, end: str) -> dict:
    """run_isolated over the window; read point + block-bootstrap CI from the artifact."""
    from scripts import run_isolated as ri
    before = set(p.name for p in ri.TRADES_DIR.iterdir()) if ri.TRADES_DIR.exists() else set()
    sys.argv = ["run_isolated", "--runs", "1", "--start-date", start, "--end-date", end]
    try:
        rc = ri.main()
    except SystemExit as e:                      # never let an exit path eat the record
        rc = int(e.code or 0)
    new = sorted(d for d in set(p.name for p in ri.TRADES_DIR.iterdir()) - before
                 if (ri.TRADES_DIR / d).is_dir())
    # Identify the run by its ARTIFACT, not by recency: a cell can leave more than one new
    # directory (a partial one holding only trades.csv + a snapshot was observed per cell),
    # and the harness's own fallback picks the most recently modified, which could be the
    # partial. The measurement is the directory that holds performance_summary.json.
    measured = [d for d in new if (ri.TRADES_DIR / d / "performance_summary.json").exists()]
    if len(measured) != 1:
        return {"status": "FAILED", "rc": rc, "new_run_dirs": new,
                "why": f"expected exactly one new run dir with performance_summary.json, "
                       f"found {len(measured)}"}
    run_id = measured[0]
    # A census failure (rc 2) does NOT discard the numbers: they are recorded and LABELED
    # non-canonical. Losing a measurement silently is the worse failure.
    perf = json.loads((ri.TRADES_DIR / run_id / "performance_summary.json").read_text())
    b = perf.get("bootstrap_distribution", {})
    cen = perf.get("census") if isinstance(perf.get("census"), dict) else {}
    return {"status": "ok" if rc == 0 else ("ok-NONCANONICAL" if rc == 2 else "FAILED"),
            "rc": rc, "run_id": run_id,
            "partial_run_dirs": [d for d in new if d != run_id],
            "census_canonical": cen.get("canonical"),
            "census_edges_blind_raw_pre_allowlist": cen.get("edges_blind"),
            "trades_canon_md5": ri._trades_canon_md5(run_id),
            "sharpe": b.get("sharpe", {}).get("point_estimate"),
            "sharpe_ci_low": b.get("sharpe", {}).get("ci_low"),
            "sharpe_ci_high": b.get("sharpe", {}).get("ci_high"),
            "sortino": b.get("sortino", {}).get("point_estimate"),
            "sortino_ci_low": b.get("sortino", {}).get("ci_low"),
            "block_length": b.get("sharpe", {}).get("block_length"),
            "n_iterations": b.get("sharpe", {}).get("n_iterations"),
            "cagr_pct": perf.get("CAGR (%)"), "mdd_pct": perf.get("Max Drawdown (%)")}


def _feature(name: str, out: Path) -> dict:
    """The T-196 foundry harness on ONE feature. Its gate verdicts remain RR-2-affected
    on this branch (Gate 4 forced-false is not fixed here) — read the NUMBERS, not the
    pass/fail."""
    os.environ["T195_FEATURES"] = name
    os.environ["T195_OUT"] = str(out)
    import runpy
    try:
        runpy.run_path(str(REPO / "scripts" / "run_foundry_eval_t195.py"), run_name="__main__")
        rc = 0
    except SystemExit as e:
        rc = int(e.code or 0)
    rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()] if out.exists() else []
    return {"status": "ok" if rows else "FAILED", "rc": rc, "harness_rows": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=["before", "after"])
    ap.add_argument("--cell", required=True, choices=["baseline", "feature"])
    ap.add_argument("--start", default="2000-01-01")
    ap.add_argument("--end", default="2025-12-31")
    ap.add_argument("--feature")
    ap.add_argument("--label", required=True)
    ap.add_argument("--census-expected-dormant", default=None,
                    help="Per-run census allowlist (core/census.py CENSUS_EXPECTED_DORMANT). "
                         "Director ruling 2026-09-30: news_sentiment_edge, for the eight RR-1 "
                         "cells ONLY, both arms identically. Recorded verbatim in every record.")
    a = ap.parse_args()

    missing = _missing_reexec_env()
    if missing:
        print("[RESCORE] REFUSING TO START: the re-exec environment is not set "
              f"({missing}). run_isolated would os.execv itself, discard this process, and "
              "run the FIXED controller in BOTH arms — a silent null. Export: "
              + " ".join(f"{k}={v}" for k, v in REQUIRED_ENV.items()))
        return 4

    free0 = _free_gb()
    if free0 < MIN_FREE_GB:
        print(f"[RESCORE] REFUSING TO START: {free0:.1f} GB free < {MIN_FREE_GB} GB floor. "
              f"Free space first — this script never pushes through.")
        return 3

    if a.census_expected_dormant:
        # The referee's OWN per-run mechanism — not a referee edit, not an allowlist edit,
        # not a standing exemption. Justified for these cells by the inertness proof
        # (run b3f03d85: 0 signals, no entry under either name, 0 attributed trades).
        os.environ["CENSUS_EXPECTED_DORMANT"] = a.census_expected_dormant

    if a.arm == "before":
        _restore_old_getter()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rec = {"rescore": "RR-1", "label": "RE-SCORE (not a new trial; N_trials 0)",
           "cell": a.label, "arm": a.arm, "kind": a.cell,
           "window": [a.start, a.end] if a.cell == "baseline" else None,
           "feature": a.feature, "branch_head": _git("rev-parse", "--short", "HEAD"),
           "getter": "seed capital (main semantics, proven ≡ main golden)" if a.arm == "before"
                     else "cash (RR-1 fix)",
           "started": dt.datetime.now().isoformat(timespec="seconds"),
           "disk_free_gb_start": round(free0, 1),
           # The condition travels WITH the number (director ruling, condition 1).
           "census_expected_dormant": a.census_expected_dormant}
    if a.cell == "feature" and not a.feature:
        ap.error("--feature is required for --cell feature")
    t0 = time.time()
    out = OUT_DIR / f"{a.label}_{a.arm}.json"
    rec["status"] = "INCOMPLETE — the cell did not finish; this record was written by the finally block"
    try:
        if a.cell == "baseline":
            rec.update(_baseline(a.start, a.end))
        else:
            rec.update(_feature(a.feature, OUT_DIR / f"{a.label}_{a.arm}.jsonl"))
    except BaseException as e:                   # incl. KeyboardInterrupt / SystemExit
        rec["status"] = f"FAILED: {type(e).__name__}: {e}"
        raise
    finally:
        # THE RECORD SURVIVES EVERY EXIT PATH. The first calibration run lost its record
        # to an unexplained early end; a measurement that can vanish without a trace is
        # the exact failure this program keeps closing.
        rec["wall_min"] = round((time.time() - t0) / 60, 1)
        rec["disk_free_gb_end"] = round(_free_gb(), 1)
        # THE VERDICT COMES FROM THE HARNESS'S OWN EXIT CODE, never from a template. A first
        # version stamped "canonical under ..." on every record, including one the census
        # had FAILED — a non-canonical cell wearing a certified label. rc 0 = the census
        # passed with the per-run allowlist applied; rc 2 = it did not.
        rc = rec.get("rc")
        setting = (f"CENSUS_EXPECTED_DORMANT={a.census_expected_dormant}"
                   if a.census_expected_dormant else "no per-run allowlist")
        rec["census_canonical"] = (rc == 0) if rc in (0, 2) else None
        rec["census_condition"] = (
            f"CANONICAL under {setting}" if rc == 0 else
            f"NON-CANONICAL under {setting} — not quotable ([NN-CENSUS])" if rc == 2 else
            f"UNKNOWN (rc={rc}) — the cell did not reach a census verdict")
        out.write_text(json.dumps(rec, indent=1, default=str))
    print(f"[RESCORE] {a.label}/{a.arm}: {rec.get('status')} — "
          f"sharpe {rec.get('sharpe')} ci_low {rec.get('sharpe_ci_low')} "
          f"({rec['wall_min']} min, {rec['disk_free_gb_end']} GB free) -> {out}")
    return 0 if str(rec.get("status", "")).startswith("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
