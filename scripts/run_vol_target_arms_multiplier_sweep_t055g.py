"""scripts/run_vol_target_arms_multiplier_sweep_t055g.py
===========================================================
T-2026-05-23-055g — vol-target multiplier sensitivity sweep on
EWMA + regime-conditional policy from T-055e.

Adapted from `scripts/run_vol_target_arms_regime_t055e.py` to
parameterize the (cautious / stressed / crisis) multiplier triple
across multiple arms. Tests whether less-aggressive multipliers
preserve T-055e's defensive value in 2024/2025 while reducing the
load-bearing 2022 -0.997 Sharpe cost.

Substrate-extension note (per T-082b):
  data/processed/ now contains Stooq+Alpaca merged history (1970+
  for blue chips). Per-year Sharpe numbers are NOT bitwise-comparable
  to T-055e's original measurement; OFF arm must be re-run fresh.

Sweep grid (5 arms, 15 cells each = 75 cells):
  arm0_off    — vol-target OFF (must re-run on extended substrate)
  arm1_t055e  — T-055e baseline: 0.85 / 0.60 / 0.40
  arm2_mild   — Mild degross:     0.95 / 0.80 / 0.65
  arm3_mod    — Moderate degross: 0.90 / 0.75 / 0.55
  arm4_asym   — Asymmetric:       0.85 / 0.70 / 0.50

Usage:
  PYTHONHASHSEED=0 python -m scripts.run_vol_target_arms_multiplier_sweep_t055g --full
  # Or a single arm for smoke-testing:
  PYTHONHASHSEED=0 python -m scripts.run_vol_target_arms_multiplier_sweep_t055g \
      --arm arm2_mild --years 2022 --reps 1
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
from typing import Dict, Iterator, List, Optional

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
RESULTS_DIR = ROOT / "data" / "measurements" / "vol_target_multiplier_sweep_t055g_2026_05_23"

SUBSTRATE_HONEST_EDGES = [
    "gap_fill_v1",
    "volume_anomaly_v1",
    "value_earnings_yield_v1",
    "value_book_to_market_v1",
    "accruals_inv_sloan_v1",
    "accruals_inv_asset_growth_v1",
]


def _ewma_patch_base() -> dict:
    """Shared EWMA + regime-aware config baseline (multipliers omitted)."""
    return {
        "portfolio_vol_target_enabled": True,
        "portfolio_vol_target_annual_vol": 0.10,
        "portfolio_vol_target_window_days": 60,    # ignored under EWMA
        "portfolio_vol_target_floor": 0.5,
        "portfolio_vol_target_ceiling": 2.0,
        "portfolio_vol_target_min_returns_required": 60,
        "portfolio_vol_target_estimator_type": "ewma",
        "portfolio_vol_target_ewma_lambda": 0.94,
        "portfolio_vol_target_regime_aware": True,
        "portfolio_vol_target_benign_multiplier": 1.0,
    }


# Sweep arm definitions. None for arm0_off (vol-target OFF).
ARMS: Dict[str, Optional[Dict[str, float]]] = {
    "arm0_off": None,
    "arm1_t055e": {"cautious": 0.85, "stressed": 0.60, "crisis": 0.40},
    "arm2_mild": {"cautious": 0.95, "stressed": 0.80, "crisis": 0.65},
    "arm3_mod":  {"cautious": 0.90, "stressed": 0.75, "crisis": 0.55},
    "arm4_asym": {"cautious": 0.85, "stressed": 0.70, "crisis": 0.50},
}

DEFAULT_YEARS = [2021, 2022, 2023, 2024, 2025]


def _reexec_if_hashseed_unset() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(
            sys.executable,
            [sys.executable, "-u", "-m",
             "scripts.run_vol_target_arms_multiplier_sweep_t055g",
             *sys.argv[1:]],
        )


@contextmanager
def vol_target_arm_patch(arm_name: str) -> Iterator[None]:
    """Patch config/risk_settings.prod.json with the arm's multiplier
    triple. arm0_off disables vol-target entirely; other arms enable
    EWMA + regime_aware with the specified multipliers."""
    arm_mults = ARMS[arm_name]
    original = RISK_CONFIG_PATH.read_text()
    try:
        cfg = json.loads(original)
        if arm_mults is None:
            cfg["portfolio_vol_target_enabled"] = False
        else:
            cfg.update(_ewma_patch_base())
            cfg["portfolio_vol_target_cautious_multiplier"] = arm_mults["cautious"]
            cfg["portfolio_vol_target_stressed_multiplier"] = arm_mults["stressed"]
            cfg["portfolio_vol_target_crisis_multiplier"] = arm_mults["crisis"]
        RISK_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
        # Sanity log so caller sees what hit disk
        cfg2 = json.loads(RISK_CONFIG_PATH.read_text())
        print(f"[T-055G] {arm_name}: vol_target_enabled="
              f"{cfg2.get('portfolio_vol_target_enabled')}, "
              f"mults=(c:{cfg2.get('portfolio_vol_target_cautious_multiplier','-')},"
              f"s:{cfg2.get('portfolio_vol_target_stressed_multiplier','-')},"
              f"x:{cfg2.get('portfolio_vol_target_crisis_multiplier','-')})",
              flush=True)
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


def _execute_grid(arm_name: str, years: list[int], reps: int,
                  exact_edge_ids: list[str],
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

    with vol_target_arm_patch(arm_name):
        for year in years:
            for rep in range(1, reps + 1):
                if (year, rep) in completed:
                    print(f"[{arm_name}] SKIP: year={year} rep={rep}", flush=True)
                    continue
                counter += 1
                elapsed = time.time() - t_start
                done_now = sum(1 for r in results if r.get("ok") and r.get("arm") == arm_name)
                avg = elapsed / max(done_now, 1) if done_now > 0 else 0
                eta = avg * (total - counter + 1)
                print(f"\n===== [{arm_name}] YEAR {year} REP {rep}/{reps} "
                      f"(run {counter}/{total}, elapsed {elapsed/60:.1f}m, "
                      f"ETA {eta/60:.1f}m) =====", flush=True)

                before = {p.name for p in TRADES_DIR.iterdir()
                          if p.is_dir() and p.name != "backup"}
                t_run = time.time()
                arm_mults = ARMS[arm_name]
                try:
                    with isolated(journal_mode=True):
                        summary = _run_one(year, exact_edge_ids)
                    run_id = _find_run_id(before) or "?"
                    record = {
                        "arm": arm_name,
                        "vol_target_on": arm_mults is not None,
                        "estimator_type": "ewma" if arm_mults is not None else "n/a",
                        "regime_aware": arm_mults is not None,
                        "cautious_multiplier": arm_mults["cautious"] if arm_mults else None,
                        "stressed_multiplier": arm_mults["stressed"] if arm_mults else None,
                        "crisis_multiplier": arm_mults["crisis"] if arm_mults else None,
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
                        "arm": arm_name,
                        "year": year, "rep": rep, "ok": False,
                        "error": f"{type(e).__name__}: {e}",
                        "wall_time_seconds": round(time.time() - t_run, 1),
                    }
                results.append(record)
                print(f"  Result: arm={record.get('arm')} year={record.get('year')} "
                      f"rep={record.get('rep')} sharpe={record.get('sharpe')} "
                      f"md5={(record.get('trades_canon_md5') or '')[:8]} "
                      f"ok={record.get('ok')}", flush=True)
                results_path.parent.mkdir(parents=True, exist_ok=True)
                results_path.write_text(json.dumps(results, indent=2, default=str))
    return results


def main() -> int:
    _reexec_if_hashseed_unset()
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true",
                        help="Run all 5 arms (75 cells).")
    parser.add_argument("--arm", type=str, default=None,
                        choices=list(ARMS.keys()),
                        help="Run a single arm.")
    parser.add_argument("--years", type=str,
                        default=",".join(str(y) for y in DEFAULT_YEARS))
    parser.add_argument("--reps", type=int, default=3)
    args = parser.parse_args()

    if not ISOLATED_ANCHOR.exists():
        print("[T-055G] No anchor — run `python -m scripts.run_isolated --save-anchor` first.",
              file=sys.stderr)
        return 1

    years = [int(y.strip()) for y in args.years.split(",") if y.strip()]

    if args.arm is not None:
        path = RESULTS_DIR / f"{args.arm}_results.json"
        _execute_grid(args.arm, years, args.reps, SUBSTRATE_HONEST_EDGES, path)
        return 0

    if args.full:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        for arm_name in ARMS.keys():
            print(f"\n[T-055G] ====== ARM {arm_name} ======", flush=True)
            path = RESULTS_DIR / f"{arm_name}_results.json"
            _execute_grid(arm_name, years, args.reps,
                          SUBSTRATE_HONEST_EDGES, path)
        sentinel = RESULTS_DIR / "FULL_DONE.txt"
        sentinel.write_text(f"T-055g grid complete at {datetime.now().isoformat(timespec='seconds')}\n")
        print(f"[T-055G] FULL DONE — see {sentinel}", flush=True)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
