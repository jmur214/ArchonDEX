"""
scripts/run_vol_target_arms_full.py
====================================
T-2026-05-22-055c — vol-target A/B lift-verification harness.

3 reps × 5 years × 2 arms = 30 backtests. Mirrors the
run_substrate_arms.py template — same `isolated(journal_mode=True)`
discipline, same substrate-honest edges list, same per-year per-rep
incremental JSON output for resume-on-interrupt.

- Arm 0 (control): `portfolio_vol_target_enabled = False`
- Arm 1 (treatment): `portfolio_vol_target_enabled = True`
  (target 10% annual vol, window=60d, floor=0.5, ceiling=2.0)

Same substrate-honest edges as run_substrate_arms.py ARM1_EDGES so
the lift attribution is unambiguously the vol-target overlay (not a
universe / cost-model / metric-pipeline shift).

Per the T-055c dispatch:
- Substrate-honest universe (use_historical_universe=True)
- Cockpit-fixed metrics (canon md5 in T-019 reference state)
- 3-rep bitwise determinism WITHIN each cell expected
- Bootstrap CI per CLAUDE.md non-negotiable #6

Output:
  data/measurements/vol_target_t055c_2026_05_22/
    arm0_results.json (vol-target OFF — control)
    arm1_results.json (vol-target ON — treatment)

Usage:
  PYTHONHASHSEED=0 python -m scripts.run_vol_target_arms_full --full
  PYTHONHASHSEED=0 python -m scripts.run_vol_target_arms_full --arm 1 --years 2024 --reps 1
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

EMPTY_MD5 = "d41d8cd98f00b204e9800998ecf8427e"

# CRITICAL: mode_controller loads `config/risk_settings.<env>.json`
# (see orchestration/mode_controller.py:522). With env="prod" (the
# harness's default) it reads risk_settings.prod.json — NOT the
# non-env-suffixed risk_settings.json. Patching the wrong file is
# silent-failure (vol-target stays at the env-file's default, which
# omits the portfolio_vol_target_* block entirely and so the
# dataclass default `enabled=False` wins).
#
# T-055c initial grid was run against the wrong file; arm1 results
# were silently arm0-identical. Corrected here.
RISK_CONFIG_PATH = ROOT / "config" / "risk_settings.prod.json"
RESULTS_DIR = ROOT / "data" / "measurements" / "vol_target_t055c_2026_05_22"

# Same 6-edge substrate-honest set as T-002 / T-035 / run_substrate_arms.py
SUBSTRATE_HONEST_EDGES = [
    "gap_fill_v1",
    "volume_anomaly_v1",
    "value_earnings_yield_v1",
    "value_book_to_market_v1",
    "accruals_inv_sloan_v1",
    "accruals_inv_asset_growth_v1",
]

VOL_TARGET_ARM1_PATCH = {
    "portfolio_vol_target_enabled": True,
    "portfolio_vol_target_annual_vol": 0.10,
    "portfolio_vol_target_window_days": 60,
    "portfolio_vol_target_floor": 0.5,
    "portfolio_vol_target_ceiling": 2.0,
    "portfolio_vol_target_min_returns_required": 60,
}

DEFAULT_YEARS = [2021, 2022, 2023, 2024, 2025]


def _reexec_if_hashseed_unset() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(
            sys.executable,
            [sys.executable, "-u", "-m", "scripts.run_vol_target_arms_full", *sys.argv[1:]],
        )


@contextmanager
def vol_target_patch(enabled: bool) -> Iterator[None]:
    """Patch risk_settings.json to enable/disable vol-targeting, restore on exit.

    For Arm 0 (enabled=False) this is a no-op since the default is
    already off — but we explicitly write the field so a stale local
    config can't corrupt the arm.
    """
    original = RISK_CONFIG_PATH.read_text()
    try:
        cfg = json.loads(original)
        if enabled:
            for k, v in VOL_TARGET_ARM1_PATCH.items():
                cfg[k] = v
        else:
            cfg["portfolio_vol_target_enabled"] = False
        RISK_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
        yield
    finally:
        RISK_CONFIG_PATH.write_text(original)


def _run_one(year: int, exact_edge_ids: list[str]) -> dict:
    """Run a single full-calendar-year backtest under prod config."""
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
    """Run a single arm's full year × rep grid. Resume-on-interrupt
    via the incremental results.json checkpoint."""
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

    with vol_target_patch(vol_target_on):
        for year in years:
            for rep in range(1, reps + 1):
                if (year, rep) in completed:
                    print(f"[{arm_label}] SKIP (already done): year={year} rep={rep}", flush=True)
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
                        "year": year,
                        "rep": rep,
                        "run_id": run_id,
                        "sharpe": summary.get("Sharpe Ratio"),
                        "sortino": summary.get("Sortino Ratio"),
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
                        "arm": arm_label,
                        "vol_target_on": vol_target_on,
                        "year": year,
                        "rep": rep,
                        "ok": False,
                        "error": f"{type(e).__name__}: {e}",
                        "wall_time_seconds": round(time.time() - t_run, 1),
                    }
                results.append(record)
                print(f"  Result: {record}", flush=True)

                results_path.parent.mkdir(parents=True, exist_ok=True)
                results_path.write_text(json.dumps(results, indent=2, default=str))

    return results


def run_full(years: list[int], reps: int) -> int:
    if not ISOLATED_ANCHOR.exists():
        print("[T-055C] No anchor — run `python -m scripts.run_isolated --save-anchor` first.",
              file=sys.stderr)
        return 1

    arm0_path = RESULTS_DIR / "arm0_results.json"
    arm1_path = RESULTS_DIR / "arm1_results.json"

    print(f"\n[T-055C] ARM 0 (vol-target OFF) — years={years} reps={reps}", flush=True)
    _execute_grid("arm0", years, reps, SUBSTRATE_HONEST_EDGES, False, arm0_path)

    print(f"\n[T-055C] ARM 1 (vol-target ON) — years={years} reps={reps}", flush=True)
    _execute_grid("arm1", years, reps, SUBSTRATE_HONEST_EDGES, True, arm1_path)

    sentinel = RESULTS_DIR / "FULL_DONE.txt"
    sentinel.write_text(f"T-055c grid complete at {datetime.now().isoformat(timespec='seconds')}\n")
    print(f"[T-055C] FULL DONE — see {sentinel}", flush=True)
    return 0


def main() -> int:
    _reexec_if_hashseed_unset()
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true",
                        help="Run both arms 5 years × 3 reps.")
    parser.add_argument("--arm", type=int, choices=[0, 1], default=None,
                        help="Run a single arm only (debug).")
    parser.add_argument("--years", type=str,
                        default=",".join(str(y) for y in DEFAULT_YEARS),
                        help="Comma-separated years (default 2021-2025).")
    parser.add_argument("--reps", type=int, default=3,
                        help="Reps per (arm, year) (default 3).")
    args = parser.parse_args()

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
        return run_full(years, args.reps)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
