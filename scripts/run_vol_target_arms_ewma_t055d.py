"""
scripts/run_vol_target_arms_ewma_t055d.py
==========================================
T-2026-05-22-055d — vol-target EWMA estimator A/B lift verification.

Reuses the T-055c harness structure but:
  * Arm 0 (control): vol-target OFF (identical to T-055c arm 0 — results
    SYMLINKED from the T-055c run; we re-use rather than re-run).
  * Arm 1 (treatment): vol-target ON with **estimator_type="ewma"** and
    ewma_lambda=0.94 (RiskMetrics standard).

Same substrate-honest 6-edge set, same 2021-2025 × 3-rep grid, same
isolated() discipline. Patches `config/risk_settings.prod.json`
(env-resolved per T-055c lesson).

Usage:
  PYTHONHASHSEED=0 python -m scripts.run_vol_target_arms_ewma_t055d --full

The full A/B audit doc compares vol-target rolling (T-055c) vs EWMA
(this dispatch) vs OFF (shared baseline).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_isolated import (  # noqa: E402
    ISOLATED_ANCHOR,
    TRADES_DIR,
    isolated,
    _find_run_id,
    _trades_canon_md5,
)

RISK_CONFIG_PATH = ROOT / "config" / "risk_settings.prod.json"
RESULTS_DIR = ROOT / "data" / "measurements" / "vol_target_ewma_t055d_2026_05_22"
T055C_RESULTS_DIR = ROOT / "data" / "measurements" / "vol_target_t055c_2026_05_22"

# Same substrate-honest 6-edge set as T-055c.
SUBSTRATE_HONEST_EDGES = [
    "gap_fill_v1",
    "volume_anomaly_v1",
    "value_earnings_yield_v1",
    "value_book_to_market_v1",
    "accruals_inv_sloan_v1",
    "accruals_inv_asset_growth_v1",
]

# Arm 1 treatment — EWMA estimator, λ=0.94 (RiskMetrics standard).
VOL_TARGET_ARM1_EWMA_PATCH = {
    "portfolio_vol_target_enabled": True,
    "portfolio_vol_target_annual_vol": 0.10,
    "portfolio_vol_target_window_days": 60,  # ignored when EWMA is selected
    "portfolio_vol_target_floor": 0.5,
    "portfolio_vol_target_ceiling": 2.0,
    "portfolio_vol_target_min_returns_required": 60,
    "portfolio_vol_target_estimator_type": "ewma",
    "portfolio_vol_target_ewma_lambda": 0.94,
}

DEFAULT_YEARS = [2021, 2022, 2023, 2024, 2025]


def _reexec_if_hashseed_unset() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(
            sys.executable,
            [sys.executable, "-u", "-m", "scripts.run_vol_target_arms_ewma_t055d", *sys.argv[1:]],
        )


@contextmanager
def vol_target_ewma_patch(enabled: bool) -> Iterator[None]:
    original = RISK_CONFIG_PATH.read_text()
    try:
        cfg = json.loads(original)
        if enabled:
            for k, v in VOL_TARGET_ARM1_EWMA_PATCH.items():
                cfg[k] = v
        else:
            cfg["portfolio_vol_target_enabled"] = False
        RISK_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
        yield
    finally:
        RISK_CONFIG_PATH.write_text(original)


def _run_one(year: int, exact_edge_ids: list[str]) -> dict:
    from orchestration.mode_controller import ModeController
    mc = ModeController(ROOT, env="prod")
    return mc.run_backtest(
        mode="prod",
        fresh=False,
        no_governor=False,
        reset_governor=True,
        alpha_debug=False,
        override_start=f"{year}-01-01",
        override_end=f"{year}-12-31",
        exact_edge_ids=list(exact_edge_ids),
        use_historical_universe=True,
        apply_journal_at_end=True,
        discover=False,
    )


def _execute_grid(arm_label: str, years: list[int], reps: int,
                  exact_edge_ids: list[str], vol_target_on: bool,
                  results_path: Path) -> list[dict]:
    results: list[dict] = []
    if results_path.exists():
        try:
            results = json.loads(results_path.read_text())
        except Exception:
            results = []

    completed = {(r["year"], r["rep"]) for r in results if r.get("ok")}
    total = len(years) * reps
    counter = sum(1 for r in results if r.get("ok"))
    t_start = time.time()

    with vol_target_ewma_patch(vol_target_on):
        for year in years:
            for rep in range(1, reps + 1):
                if (year, rep) in completed:
                    print(f"[{arm_label}] SKIP: year={year} rep={rep}", flush=True)
                    continue
                counter += 1
                elapsed = time.time() - t_start
                done_now = sum(1 for r in results if r.get("ok") and r.get("arm") == arm_label)
                avg = elapsed / max(done_now, 1) if done_now > 0 else 0
                eta = avg * (total - counter + 1)
                print(f"\n===== [{arm_label}] YEAR {year} REP {rep}/{reps} "
                      f"(run {counter}/{total}, elapsed {elapsed/60:.1f}m, "
                      f"ETA {eta/60:.1f}m) =====", flush=True)

                before = {p.name for p in TRADES_DIR.iterdir()
                          if p.is_dir() and p.name != "backup"}
                t_run = time.time()
                try:
                    with isolated(journal_mode=True):
                        summary = _run_one(year, exact_edge_ids)
                    run_id = _find_run_id(before) or "?"
                    record = {
                        "arm": arm_label,
                        "vol_target_on": vol_target_on,
                        "estimator_type": "ewma" if vol_target_on else "n/a",
                        "year": year,
                        "rep": rep,
                        "run_id": run_id,
                        "sharpe": summary.get("Sharpe Ratio"),
                        "sortino": summary.get("Sortino"),
                        "cagr_pct": summary.get("CAGR (%)"),
                        "max_drawdown_pct": summary.get("Max Drawdown (%)"),
                        "win_rate_pct": summary.get("Win Rate (%)"),
                        "total_trades": summary.get("Total Trades"),
                        "trades_canon_md5": _trades_canon_md5(run_id) if run_id != "?" else "(no run_id)",
                        "wall_time_seconds": round(time.time() - t_run, 1),
                        "ok": True,
                    }
                except Exception as e:
                    record = {
                        "arm": arm_label, "vol_target_on": vol_target_on,
                        "year": year, "rep": rep, "ok": False,
                        "error": f"{type(e).__name__}: {e}",
                        "wall_time_seconds": round(time.time() - t_run, 1),
                    }
                results.append(record)
                print(f"  Result: {record}", flush=True)
                results_path.parent.mkdir(parents=True, exist_ok=True)
                results_path.write_text(json.dumps(results, indent=2, default=str))
    return results


def main() -> int:
    _reexec_if_hashseed_unset()
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true",
                        help="Run arm1 EWMA (15 backtests); arm0 reused from T-055c.")
    parser.add_argument("--arm", type=int, choices=[0, 1], default=None)
    parser.add_argument("--years", type=str,
                        default=",".join(str(y) for y in DEFAULT_YEARS))
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args()

    if not ISOLATED_ANCHOR.exists():
        print("[T-055D] No anchor — run `python -m scripts.run_isolated --save-anchor` first.",
              file=sys.stderr)
        return 1

    years = [int(y.strip()) for y in args.years.split(",") if y.strip()]

    if args.arm is not None:
        vol_target_on = (args.arm == 1)
        path = RESULTS_DIR / f"arm{args.arm}_results.json"
        _execute_grid(
            f"arm{args.arm}", years, args.reps,
            SUBSTRATE_HONEST_EDGES, vol_target_on, path,
        )
        return 0

    if args.full:
        # Reuse T-055c arm0 results — identical config (vol-target OFF).
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        t055c_arm0 = T055C_RESULTS_DIR / "arm0_results.json"
        target_arm0 = RESULTS_DIR / "arm0_results.json"
        if t055c_arm0.exists() and not target_arm0.exists():
            import shutil as _sh
            _sh.copy2(t055c_arm0, target_arm0)
            print(f"[T-055D] Reused T-055c arm0 results from {t055c_arm0}", flush=True)
        print(f"\n[T-055D] ARM 1 (vol-target ON, EWMA λ=0.94) — years={years} reps={args.reps}",
              flush=True)
        _execute_grid("arm1", years, args.reps, SUBSTRATE_HONEST_EDGES, True,
                      RESULTS_DIR / "arm1_results.json")
        sentinel = RESULTS_DIR / "FULL_DONE.txt"
        sentinel.write_text(f"T-055d grid complete at {datetime.now().isoformat(timespec='seconds')}\n")
        print(f"[T-055D] FULL DONE — see {sentinel}", flush=True)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
