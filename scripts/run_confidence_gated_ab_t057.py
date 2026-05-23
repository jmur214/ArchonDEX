"""scripts/run_confidence_gated_ab_t057.py
============================================
T-057 Phase 3: 3-arm A/B harness for confidence-gated execution.

Arms:
  arm0 — enabled=False (legacy weighted_sum baseline)
  arm1 — enabled=True, n_threshold=2
  arm2 — enabled=True, n_threshold=3

Grid: 3 arms × 5 years × 3 reps = 45 backtests.

Mirrors `scripts/run_substrate_arms.py`'s pattern for the
config-patch + isolated-context approach: between arms we mutate
`config/alpha_settings.prod.json` to set the `confidence_gate`
block, then restore in finally.

Per-cell: substrate-honest historical universe, journal-mode,
reset_governor=True, 6-active set (no `exact_edge_ids` override —
uses the production registry's status='active' set after T-041c-archive
landed; the spinoff_reversion archive doesn't affect the active set
since it was paused not active).

Output:
  data/measurements/confidence_gated_t057_2026_05_22/results.json
    [{arm, year, rep, sharpe, sortino, cagr_pct, max_drawdown_pct,
      win_rate_pct, total_trades, trades_canon_md5, wall_time_seconds, ok}]

Incremental — each cell appends to results.json so a partial run is
recoverable.
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
    TRADES_DIR, isolated, _find_run_id, _trades_canon_md5,
)

ALPHA_CONFIG_PATH = ROOT / "config" / "alpha_settings.prod.json"
RESULTS_DIR = ROOT / "data" / "measurements" / "confidence_gated_t057_2026_05_22"
RESULTS_PATH = RESULTS_DIR / "results.json"

DEFAULT_YEARS = [2021, 2022, 2023, 2024, 2025]
DEFAULT_REPS = 3

ARMS = [
    {"label": "arm0_off",     "enabled": False, "n_threshold": 2},
    {"label": "arm1_n2",      "enabled": True,  "n_threshold": 2},
    {"label": "arm2_n3",      "enabled": True,  "n_threshold": 3},
]


def _reexec_if_hashseed_unset() -> None:
    if os.environ.get("PYTHONHASHSEED") != "0":
        os.environ["PYTHONHASHSEED"] = "0"
        os.execv(
            sys.executable,
            [sys.executable, "-m", "scripts.run_confidence_gated_ab_t057",
             *sys.argv[1:]],
        )


@contextmanager
def confidence_gate_patch(enabled: bool, n_threshold: int) -> Iterator[None]:
    """Temporarily set the `confidence_gate` block in alpha_settings.prod.json.

    Original file content is captured in memory before the patch so it
    can be restored even if the run errors. Same pattern as
    run_substrate_arms's HMM patch.
    """
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
    """Run a single full-calendar-year journal-mode backtest under
    substrate-honest universe. Mirrors run_substrate_arms._run_one."""
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
            f"\n===== T-057 ARM {arm_label} "
            f"(enabled={arm['enabled']}, n={arm['n_threshold']}) =====",
            flush=True,
        )
        with confidence_gate_patch(arm["enabled"], arm["n_threshold"]):
            for year in years:
                for rep in range(1, reps + 1):
                    if (arm_label, year, rep) in completed:
                        print(
                            f"[T-057] SKIP {arm_label} year={year} rep={rep}",
                            flush=True,
                        )
                        continue
                    counter += 1
                    elapsed = time.time() - t_start
                    done_now = sum(1 for r in results if r.get("ok"))
                    avg = elapsed / max(done_now, 1) if done_now > 0 else 0
                    eta = avg * (total - counter + 1)
                    print(
                        f"\n----- [T-057 {arm_label}] year={year} rep={rep}/{reps} "
                        f"(run {counter}/{total}, elapsed {elapsed/60:.1f}m, "
                        f"ETA {eta/60:.1f}m) -----",
                        flush=True,
                    )

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
                            "arm": arm_label,
                            "year": year,
                            "rep": rep,
                            "ok": False,
                            "error": f"{type(e).__name__}: {e}",
                            "wall_time_seconds": round(time.time() - t_run, 1),
                        }
                    results.append(record)
                    print(f"  Result: {record}", flush=True)
                    _persist(results)

    return 0


def main() -> int:
    _reexec_if_hashseed_unset()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", type=str,
                        default=",".join(str(y) for y in DEFAULT_YEARS),
                        help="Comma-separated years (default 2021-2025).")
    parser.add_argument("--reps", type=int, default=DEFAULT_REPS,
                        help="Reps per (arm, year) (default 3).")
    args = parser.parse_args()
    years = [int(y.strip()) for y in args.years.split(",") if y.strip()]
    print(
        f"[T-057] A/B harness — arms={[a['label'] for a in ARMS]} "
        f"years={years} reps={args.reps} → {RESULTS_PATH}",
        flush=True,
    )
    return _execute_grid(years, args.reps)


if __name__ == "__main__":
    sys.exit(main())
