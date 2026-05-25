"""scripts/run_confidence_gated_t057b.py
========================================
T-2026-05-23-057b verification campaign on the extended substrate.

Re-runs the T-057 arm0 vs arm2_n3 comparison with 5 reps per cell
(instead of 3) on the new Stooq+Alpaca extended substrate (post-T-082b
data swap). Verifies whether T-057's +0.793 Sharpe lift holds on
deeper history, and produces the evidence package for the flag-flip
user-decision gate.

Arms:
  arm0_off   — confidence_gate.enabled=False (baseline)
  arm2_n3    — confidence_gate.enabled=True, n_threshold=3

Grid: 2 arms × 5 years × 5 reps = 50 backtests.

Mirrors T-057's harness (`scripts/run_confidence_gated_ab_t057.py`)
config-patch + isolated-context pattern. arm0 is RE-RUN (not reused
from T-057) because the substrate swap means the OFF baseline is no
longer comparable bitwise.

Patches `config/alpha_settings.prod.json` per the T-055c env-resolved-
config lesson.

Output:
  data/measurements/confidence_gated_t057b_2026_05_23/results.json

Verdict gate per CLAUDE.md non-negotiable #6:
  * FLIP if ci_low(Δ Sharpe arm2_n3 vs arm0_off) > 0
  * DEFER if ci_low(Δ Sharpe) <= 0 or collapse vs T-057

Usage:
  PYTHONHASHSEED=0 python -m scripts.run_confidence_gated_t057b --full
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.run_isolated import (  # noqa: E402
    ISOLATED_ANCHOR, TRADES_DIR, isolated, _find_run_id, _trades_canon_md5,
)

ALPHA_CONFIG_PATH = ROOT / "config" / "alpha_settings.prod.json"
RESULTS_DIR = ROOT / "data" / "measurements" / "confidence_gated_t057b_2026_05_23"
RESULTS_PATH = RESULTS_DIR / "results.json"

DEFAULT_YEARS = [2021, 2022, 2023, 2024, 2025]
DEFAULT_REPS = 5

# Two-arm verification grid. arm1_n2 from T-057 omitted per the
# dispatch's focus: arm0 vs arm2_n3 is the load-bearing comparison.
ARMS = [
    {"label": "arm0_off",  "enabled": False, "n_threshold": 2},
    {"label": "arm2_n3",   "enabled": True,  "n_threshold": 3},
]


def _reexec_if_hashseed_unset() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(
            sys.executable,
            [sys.executable, "-u", "-m", "scripts.run_confidence_gated_t057b",
             *sys.argv[1:]],
        )


@contextmanager
def confidence_gate_patch(enabled: bool, n_threshold: int) -> Iterator[None]:
    """Patch the `confidence_gate` block in alpha_settings.prod.json,
    restore in finally. Same pattern as the T-057 harness."""
    original = ALPHA_CONFIG_PATH.read_text()
    try:
        cfg = json.loads(original)
        cfg["confidence_gate"] = {
            "enabled": bool(enabled),
            "n_threshold": int(n_threshold),
        }
        ALPHA_CONFIG_PATH.write_text(json.dumps(cfg, indent=2))
        yield
    finally:
        ALPHA_CONFIG_PATH.write_text(original)


def _run_one_year(year: int) -> dict:
    """Single full-calendar-year backtest under prod config."""
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
        use_historical_universe=True,
        apply_journal_at_end=True,
        discover=False,
    )


def _load_existing() -> list:
    if RESULTS_PATH.exists():
        try:
            return json.loads(RESULTS_PATH.read_text())
        except Exception:
            return []
    return []


def _persist(results: list) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RESULTS_PATH.write_text(json.dumps(results, indent=2, default=str))


def _execute_grid(years: list, reps: int) -> int:
    results = _load_existing()
    completed = {
        (r["arm"], r["year"], r["rep"]) for r in results if r.get("ok")
    }
    total = len(ARMS) * len(years) * reps
    counter = sum(1 for r in results if r.get("ok"))
    t_start = time.time()

    for arm in ARMS:
        arm_label = arm["label"]
        print(
            f"\n===== T-057b ARM {arm_label} "
            f"(enabled={arm['enabled']}, n={arm['n_threshold']}) =====",
            flush=True,
        )
        with confidence_gate_patch(arm["enabled"], arm["n_threshold"]):
            for year in years:
                for rep in range(1, reps + 1):
                    if (arm_label, year, rep) in completed:
                        print(f"[T-057b] SKIP {arm_label} y={year} rep={rep}",
                              flush=True)
                        continue
                    counter += 1
                    elapsed = time.time() - t_start
                    done_now = sum(1 for r in results if r.get("ok"))
                    avg = elapsed / max(done_now, 1) if done_now > 0 else 0
                    eta = avg * (total - counter + 1)
                    print(
                        f"\n----- [{arm_label}] y={year} rep={rep}/{reps} "
                        f"(run {counter}/{total}, elapsed {elapsed/60:.1f}m, "
                        f"ETA {eta/60:.1f}m) -----", flush=True)

                    before = {p.name for p in TRADES_DIR.iterdir()
                              if p.is_dir() and p.name != "backup"}
                    t_run = time.time()
                    try:
                        with isolated(journal_mode=True):
                            summary = _run_one_year(year)
                        run_id = _find_run_id(before) or "?"
                        record = {
                            "arm": arm_label,
                            "enabled": arm["enabled"],
                            "n_threshold": arm["n_threshold"],
                            "year": year,
                            "rep": rep,
                            "run_id": run_id,
                            "sharpe": summary.get("Sharpe Ratio"),
                            "sortino": summary.get("Sortino Ratio"),
                            "cagr_pct": summary.get("CAGR (%)"),
                            "max_drawdown_pct": summary.get("Max Drawdown (%)"),
                            "win_rate_pct": summary.get("Win Rate (%)"),
                            "total_trades": summary.get("Total Trades"),
                            "trades_canon_md5": (
                                _trades_canon_md5(run_id)
                                if run_id != "?" else "(no run_id)"
                            ),
                            "wall_time_seconds": round(time.time() - t_run, 1),
                            "ok": True,
                        }
                    except Exception as e:
                        record = {
                            "arm": arm_label, "year": year, "rep": rep,
                            "ok": False,
                            "error": f"{type(e).__name__}: {e}",
                            "wall_time_seconds": round(time.time() - t_run, 1),
                        }
                    results.append(record)
                    print(f"  Result: {record}", flush=True)
                    _persist(results)

    sentinel = RESULTS_DIR / "FULL_DONE.txt"
    sentinel.write_text(f"T-057b grid complete at {time.time()}\n")
    print(f"[T-057b] FULL DONE — see {sentinel}", flush=True)
    return 0


def main() -> int:
    _reexec_if_hashseed_unset()
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true",
                        help="Run 5 reps × 5 years × 2 arms = 50 backtests.")
    parser.add_argument("--arm", type=str, choices=["arm0_off", "arm2_n3"],
                        default=None)
    parser.add_argument("--years", type=str,
                        default=",".join(str(y) for y in DEFAULT_YEARS))
    parser.add_argument("--reps", type=int, default=DEFAULT_REPS)
    args = parser.parse_args()

    if not ISOLATED_ANCHOR.exists():
        print("[T-057b] No anchor — run `scripts.run_isolated --save-anchor` first.",
              file=sys.stderr)
        return 1

    years = [int(y.strip()) for y in args.years.split(",") if y.strip()]

    if args.arm is not None:
        # Single-arm smoke / debug path.
        global ARMS
        ARMS = [a for a in ARMS if a["label"] == args.arm]

    if args.full or args.arm is not None:
        return _execute_grid(years, args.reps)

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
